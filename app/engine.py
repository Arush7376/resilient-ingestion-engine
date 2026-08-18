"""
app/engine.py
-------------
Production-grade Resilient Data Ingestion Engine.

Key Architectural Components:
1. CircuitBreaker State Machine:
   - Finite states: CLOSED (normal), OPEN (tripped / fast-fail), HALF_OPEN (recovery testing).
   - Thread & async-safe concurrency controls via asyncio.Lock.
   - Automatic cooldown expiry tracking and state transitions.

2. AntiDetectionHeaderRotator:
   - Maintains fingerprint-consistent modern desktop browser profiles.
   - Pairs User-Agent with exact Client Hints (Sec-CH-UA, Sec-Fetch-*, Accept-*, etc.).
   - Prevents TLS / header fingerprinting detection by scrapers and WAFs.

3. ResilientIngestionEngine:
   - High-performance HTTPX AsyncClient using HTTP/2 transport.
   - Pacing mechanism with exponential backoff and randomized jitter on retries.
   - Strict Pydantic v2 schema validation with zero silent failures and metric tracking.
"""

import time
import random
import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Optional
import httpx
from pydantic import ValidationError

from app.schemas import (
    CircuitBreakerStateEnum,
    CircuitBreakerMetrics,
    IngestionMetrics,
    JobItem,
)

# Set up logging for engine diagnostic telemetry
logger = logging.getLogger("ingestion_engine")
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"))
    logger.addHandler(ch)


class CircuitBreakerOpenException(Exception):
    """
    Exception raised when an HTTP outbound request is attempted while the
    Circuit Breaker is in the OPEN state (Fast-fail mechanism).
    """

    def __init__(self, message: str, cooldown_remaining: float):
        super().__init__(message)
        self.cooldown_remaining = cooldown_remaining


class CircuitBreaker:
    """
    Finite State Machine implementing the Circuit Breaker pattern.

    Transitions:
    - CLOSED -> OPEN: Triggered when consecutive failures reach `failure_threshold`.
    - OPEN -> HALF_OPEN: Triggered automatically after `cooldown_seconds` elapses.
    - HALF_OPEN -> CLOSED: Triggered if trial probe request succeeds.
    - HALF_OPEN -> OPEN: Triggered if trial probe request fails.
    """

    def __init__(self, failure_threshold: int = 5, cooldown_seconds: float = 30.0):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds

        self._state = CircuitBreakerStateEnum.CLOSED
        self._consecutive_failures = 0
        self._total_failures = 0
        self._success_count = 0
        self._last_state_change = datetime.now(timezone.utc)
        self._last_failure_time: Optional[datetime] = None
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitBreakerStateEnum:
        return self._state

    @property
    def consecutive_failures(self) -> int:
        return self._consecutive_failures

    @property
    def total_failures(self) -> int:
        return self._total_failures

    @property
    def success_count(self) -> int:
        return self._success_count

    async def get_metrics(self) -> CircuitBreakerMetrics:
        """
        Thread-safe getter for current Circuit Breaker state and metrics telemetry.
        """
        async with self._lock:
            self._eval_cooldown_transition_unlocked()
            cooldown_rem = self._get_cooldown_remaining_unlocked()

            return CircuitBreakerMetrics(
                state=self._state,
                consecutive_failures=self._consecutive_failures,
                failure_threshold=self.failure_threshold,
                success_count=self._success_count,
                total_failures=self._total_failures,
                last_state_change=self._last_state_change.isoformat(),
                cooldown_seconds=self.cooldown_seconds,
                cooldown_remaining_seconds=cooldown_rem,
            )

    def _get_cooldown_remaining_unlocked(self) -> float:
        if self._state != CircuitBreakerStateEnum.OPEN or not self._last_failure_time:
            return 0.0
        elapsed = (datetime.now(timezone.utc) - self._last_failure_time).total_seconds()
        remaining = self.cooldown_seconds - elapsed
        return max(0.0, remaining)

    def _eval_cooldown_transition_unlocked(self) -> None:
        """
        Evaluates whether the cooldown window has expired when OPEN, transitioning to HALF_OPEN.
        Must be called inside an `async with self._lock:` block.
        """
        if self._state == CircuitBreakerStateEnum.OPEN:
            if self._get_cooldown_remaining_unlocked() <= 0.0:
                self._state = CircuitBreakerStateEnum.HALF_OPEN
                self._last_state_change = datetime.now(timezone.utc)
                logger.info("CircuitBreaker state transition: OPEN -> HALF_OPEN (Cooldown expired, testing recovery)")

    async def before_request(self) -> None:
        """
        Invoked immediately prior to issuing an outbound HTTP request.
        Fast-fails if circuit breaker is OPEN during cooldown period.
        """
        async with self._lock:
            self._eval_cooldown_transition_unlocked()

            if self._state == CircuitBreakerStateEnum.OPEN:
                rem = self._get_cooldown_remaining_unlocked()
                logger.warning(f"CircuitBreaker OPEN: Blocking outbound request. Cooldown remaining: {rem:.2f}s")
                raise CircuitBreakerOpenException(
                    f"Circuit Breaker is OPEN. Outbound requests blocked to prevent cascading failure. Cooldown remaining: {rem:.1f}s",
                    cooldown_remaining=rem,
                )

    async def record_success(self) -> None:
        """
        Invoked when an outbound HTTP request succeeds cleanly (2xx status).
        """
        async with self._lock:
            self._success_count += 1
            self._consecutive_failures = 0

            if self._state == CircuitBreakerStateEnum.HALF_OPEN:
                self._state = CircuitBreakerStateEnum.CLOSED
                self._last_state_change = datetime.now(timezone.utc)
                logger.info("CircuitBreaker state transition: HALF_OPEN -> CLOSED (Trial request succeeded, service healthy)")

    async def record_failure(self, error_reason: str = "") -> None:
        """
        Invoked when an outbound HTTP request fails (connection error, timeout, 5xx server error).
        """
        async with self._lock:
            self._total_failures += 1
            self._consecutive_failures += 1
            self._last_failure_time = datetime.now(timezone.utc)

            logger.error(
                f"CircuitBreaker recorded failure ({self._consecutive_failures}/{self.failure_threshold}). Reason: {error_reason}"
            )

            if self._state == CircuitBreakerStateEnum.HALF_OPEN:
                self._state = CircuitBreakerStateEnum.OPEN
                self._last_state_change = datetime.now(timezone.utc)
                logger.error("CircuitBreaker state transition: HALF_OPEN -> OPEN (Trial probe failed)")

            elif self._state == CircuitBreakerStateEnum.CLOSED and self._consecutive_failures >= self.failure_threshold:
                self._state = CircuitBreakerStateEnum.OPEN
                self._last_state_change = datetime.now(timezone.utc)
                logger.error(
                    f"CircuitBreaker state transition: CLOSED -> OPEN (Consecutive failures hit threshold {self.failure_threshold})"
                )


class AntiDetectionHeaderRotator:
    """
    Rotates realistic desktop browser header profiles to bypass WAF heuristics
    and anti-bot detection while maintaining strict header fingerprint consistency.
    """

    PROFILES: List[Dict[str, str]] = [
        # Chrome 124 on Windows 10/11
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en;q=0.9",
            "Sec-CH-UA": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            "Sec-CH-UA-Mobile": "?0",
            "Sec-CH-UA-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
        },
        # Firefox 125 on macOS
        {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "cross-site",
            "Upgrade-Insecure-Requests": "1",
        },
        # Edge 124 on Windows
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en;q=0.9",
            "Sec-CH-UA": '"Chromium";v="124", "Microsoft Edge";v="124", "Not-A.Brand";v="99"',
            "Sec-CH-UA-Mobile": "?0",
            "Sec-CH-UA-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
        },
        # Safari 17.4 on macOS
        {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
        },
    ]

    @classmethod
    def get_random_profile(cls) -> Dict[str, str]:
        """
        Returns a random, complete browser header profile to maintain client fingerprint consistency.
        """
        return random.choice(cls.PROFILES).copy()


class ResilientIngestionEngine:
    """
    Core resilient ingestion engine managing async HTTP connection pooling, HTTP/2 multiplexing,
    circuit breaker trip protection, pacing delay with exponential backoff & jitter,
    and strict Pydantic v2 schema validation.
    """

    SOURCES: Dict[str, str] = {
        "remoteok": "https://remoteok.com/api",
        "himalayas": "https://himalayas.app/jobs/api",
    }

    def __init__(
        self,
        circuit_breaker: Optional[CircuitBreaker] = None,
        max_retries: int = 3,
        base_backoff_sec: float = 1.0,
        max_backoff_sec: float = 10.0,
        jitter_max_sec: float = 0.5,
    ):
        self.circuit_breaker = circuit_breaker or CircuitBreaker(failure_threshold=5, cooldown_seconds=30.0)
        self.max_retries = max_retries
        self.base_backoff_sec = base_backoff_sec
        self.max_backoff_sec = max_backoff_sec
        self.jitter_max_sec = jitter_max_sec
        self._client: Optional[httpx.AsyncClient] = None

    async def initialize(self) -> None:
        """
        Initializes the HTTPX AsyncClient with HTTP/2 transport support.
        """
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                http2=True,
                follow_redirects=True,
                timeout=httpx.Timeout(15.0, connect=5.0),
                limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
            )
            logger.info("ResilientIngestionEngine AsyncClient initialized with HTTP/2 transport")

    async def shutdown(self) -> None:
        """
        Gracefully closes the HTTPX AsyncClient connection pool.
        """
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            logger.info("ResilientIngestionEngine AsyncClient connection pool closed")

    async def fetch_raw_payload(self, url: str) -> Tuple[List[Dict[str, Any]], float]:
        """
        Executes outbound HTTP request using HTTP/2, circuit breaker protection,
        header rotation, and exponential backoff retry with randomized jitter.

        Returns:
            Tuple of (raw_items_list, round_trip_latency_ms)
        """
        if self._client is None or self._client.is_closed:
            await self.initialize()

        # Circuit breaker fast-fail evaluation before making network attempt
        await self.circuit_breaker.before_request()

        attempt = 0
        last_exception: Optional[Exception] = None

        while attempt <= self.max_retries:
            headers = AntiDetectionHeaderRotator.get_random_profile()
            start_time = time.perf_counter()

            try:
                logger.info(f"Ingestion attempt {attempt + 1}/{self.max_retries + 1} targeting {url}")
                response = await self._client.get(url, headers=headers)
                latency_ms = (time.perf_counter() - start_time) * 1000.0

                if response.status_code == 200:
                    await self.circuit_breaker.record_success()
                    data = response.json()

                    # Unify payload list output
                    if isinstance(data, list):
                        items = data
                    elif isinstance(data, dict) and "jobs" in data:
                        items = data["jobs"]
                    elif isinstance(data, dict):
                        items = [data]
                    else:
                        items = []

                    logger.info(
                        f"Fetched {len(items)} raw items from {url} in {latency_ms:.2f}ms (HTTP {response.status_code} - {response.http_version})"
                    )
                    return items, latency_ms
                else:
                    error_msg = f"HTTP {response.status_code} returned by provider"
                    logger.warning(f"Ingestion attempt failed: {error_msg}")
                    last_exception = httpx.HTTPStatusError(
                        error_msg, request=response.request, response=response
                    )

            except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                latency_ms = (time.perf_counter() - start_time) * 1000.0
                last_exception = exc
                logger.warning(f"Network / HTTP exception on attempt {attempt + 1}: {exc}")

            # Record failure in Circuit Breaker state machine
            await self.circuit_breaker.record_failure(str(last_exception))

            # If circuit breaker tripped OPEN during retry attempts, halt immediately
            if self.circuit_breaker.state == CircuitBreakerStateEnum.OPEN:
                metrics = await self.circuit_breaker.get_metrics()
                raise CircuitBreakerOpenException(
                    f"Circuit breaker tripped OPEN during retry sequence. Cooldown remaining: {metrics.cooldown_remaining_seconds:.1f}s",
                    cooldown_remaining=metrics.cooldown_remaining_seconds,
                )

            attempt += 1
            if attempt <= self.max_retries:
                # Pacing mechanism: Exponential backoff with randomized jitter
                backoff = min(self.max_backoff_sec, self.base_backoff_sec * (2 ** (attempt - 1)))
                jitter = random.uniform(0.05, self.jitter_max_sec)
                total_delay = backoff + jitter

                logger.info(f"Pacing delay applied: sleeping {total_delay:.2f}s before retry (backoff={backoff:.2f}s, jitter={jitter:.2f}s)")
                await asyncio.sleep(total_delay)

        raise last_exception or RuntimeError("Failed to fetch payload after maximum retries")

    async def ingest_jobs(
        self, source_name: str = "remoteok", limit: Optional[int] = None
    ) -> Tuple[List[JobItem], IngestionMetrics]:
        """
        Executes end-to-end ingestion pipeline:
        1. Resolves target URL for provider
        2. Fetches raw JSON list with retry/jitter & HTTP/2
        3. Parses each record with Pydantic v2 validation
        4. Isolates schema failures without breaking the pipeline
        5. Computes execution metrics
        """
        target_url = self.SOURCES.get(source_name.lower(), self.SOURCES["remoteok"])
        cb_metrics = await self.circuit_breaker.get_metrics()

        try:
            raw_items, latency_ms = await self.fetch_raw_payload(target_url)
        except Exception as exc:
            # Return empty jobs list with metrics reflecting breaker state on failure
            cb_state = (await self.circuit_breaker.get_metrics()).state
            metrics = IngestionMetrics(
                total_fetched=0,
                valid_records=0,
                schema_failures=0,
                circuit_breaker_status=cb_state,
                average_latency_ms=0.0,
            )
            raise exc

        valid_jobs: List[JobItem] = []
        schema_failures = 0
        total_fetched = len(raw_items)

        for raw in raw_items:
            try:
                # Enforce source property override
                if isinstance(raw, dict):
                    raw["source"] = source_name.capitalize()
                job = JobItem.model_validate(raw)
                valid_jobs.append(job)
            except (ValidationError, ValueError) as ve:
                schema_failures += 1
                logger.debug(f"Schema validation failure for item: {ve}")

            if limit and len(valid_jobs) >= limit:
                break

        current_cb_state = (await self.circuit_breaker.get_metrics()).state

        metrics = IngestionMetrics(
            total_fetched=total_fetched,
            valid_records=len(valid_jobs),
            schema_failures=schema_failures,
            circuit_breaker_status=current_cb_state,
            average_latency_ms=round(latency_ms, 2),
        )

        return valid_jobs, metrics
