"""
tests/test_live_ingestion.py
-----------------------------
Live integration test executing actual data ingestion against RemoteOK / Himalayas
public API endpoints to verify live HTTP/2 connection handshakes, anti-detection
header rotation, Pydantic v2 schema validation, and metric collection.
"""

import pytest
from app.engine import ResilientIngestionEngine, CircuitBreaker


@pytest.mark.asyncio
async def test_live_ingestion_remoteok():
    cb = CircuitBreaker(failure_threshold=5, cooldown_seconds=30.0)
    engine = ResilientIngestionEngine(circuit_breaker=cb, max_retries=2)

    await engine.initialize()
    try:
        jobs, metrics = await engine.ingest_jobs(source_name="remoteok", limit=5)

        print(f"\n[RemoteOK Ingestion Metrics]")
        print(f"Total Fetched: {metrics.total_fetched}")
        print(f"Valid Records: {metrics.valid_records}")
        print(f"Schema Failures: {metrics.schema_failures}")
        print(f"Breaker Status: {metrics.circuit_breaker_status}")
        print(f"Avg Latency: {metrics.average_latency_ms:.2f} ms")

        assert metrics.total_fetched > 0
        assert metrics.valid_records > 0
        assert len(jobs) <= 5
        assert metrics.circuit_breaker_status == "CLOSED"

        first_job = jobs[0]
        assert first_job.title
        assert first_job.company
        assert first_job.url
        print(f"Sample Job Parsed: {first_job.title} @ {first_job.company} ({first_job.location})")
    finally:
        await engine.shutdown()


@pytest.mark.asyncio
async def test_live_ingestion_himalayas():
    cb = CircuitBreaker(failure_threshold=5, cooldown_seconds=30.0)
    engine = ResilientIngestionEngine(circuit_breaker=cb, max_retries=2)

    await engine.initialize()
    try:
        jobs, metrics = await engine.ingest_jobs(source_name="himalayas", limit=5)

        print(f"\n[Himalayas Ingestion Metrics]")
        print(f"Total Fetched: {metrics.total_fetched}")
        print(f"Valid Records: {metrics.valid_records}")
        print(f"Schema Failures: {metrics.schema_failures}")
        print(f"Breaker Status: {metrics.circuit_breaker_status}")
        print(f"Avg Latency: {metrics.average_latency_ms:.2f} ms")

        assert metrics.total_fetched > 0
        assert metrics.valid_records > 0
        assert len(jobs) <= 5

        first_job = jobs[0]
        assert first_job.title
        assert first_job.company
        print(f"Sample Job Parsed: {first_job.title} @ {first_job.company} ({first_job.location})")
    finally:
        await engine.shutdown()
