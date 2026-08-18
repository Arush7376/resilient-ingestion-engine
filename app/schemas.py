"""
app/schemas.py
--------------
Pydantic v2 data models for job records, execution metrics, circuit breaker status,
and API responses. Enforces strict type safety and schema validation across the ingestion pipeline.
"""

from enum import Enum
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, model_validator, ConfigDict


class CircuitBreakerStateEnum(str, Enum):
    """
    Finite states for the Circuit Breaker pattern.
    """
    CLOSED = "CLOSED"      # Normal operation: outbound HTTP requests allowed
    OPEN = "OPEN"          # Faulted: outbound HTTP requests blocked immediately (fast-fail)
    HALF_OPEN = "HALF_OPEN"# Recovery probe: trial request allowed to test target health


class CircuitBreakerMetrics(BaseModel):
    """
    Telemetry and runtime counters for the Circuit Breaker state machine.
    """
    model_config = ConfigDict(use_enum_values=True)

    state: CircuitBreakerStateEnum = Field(
        ..., description="Current finite state of the circuit breaker FSM"
    )
    consecutive_failures: int = Field(
        ..., ge=0, description="Current tally of consecutive network/HTTP failures"
    )
    failure_threshold: int = Field(
        ..., ge=1, description="Number of consecutive failures required to trip breaker OPEN"
    )
    success_count: int = Field(
        ..., ge=0, description="Total successful requests completed since initialization"
    )
    total_failures: int = Field(
        ..., ge=0, description="Total cumulative failures recorded since initialization"
    )
    last_state_change: str = Field(
        ..., description="ISO 8601 timestamp of the most recent state transition"
    )
    cooldown_seconds: float = Field(
        ..., ge=0.0, description="Configured cooldown duration when OPEN before probing HALF-OPEN"
    )
    cooldown_remaining_seconds: float = Field(
        ..., ge=0.0, description="Time remaining in OPEN cooldown period before recovery probe"
    )


class IngestionMetrics(BaseModel):
    """
    Performance and data quality metrics collected during an ingestion run.
    """
    model_config = ConfigDict(use_enum_values=True)

    total_fetched: int = Field(
        ..., ge=0, description="Total raw job payload objects received from upstream source"
    )
    valid_records: int = Field(
        ..., ge=0, description="Count of job records successfully validated against Pydantic schema"
    )
    schema_failures: int = Field(
        ..., ge=0, description="Count of malformed or invalid job records rejected during validation"
    )
    circuit_breaker_status: CircuitBreakerStateEnum = Field(
        ..., description="State of the Circuit Breaker at execution time"
    )
    average_latency_ms: float = Field(
        ..., ge=0.0, description="Average HTTP request-response round-trip latency in milliseconds"
    )


class JobItem(BaseModel):
    """
    Normalized Pydantic v2 job listing schema. Accepts diverse payload formats
    from upstream providers (e.g. RemoteOK, Himalayas) and standardizes them.
    """
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: str = Field(..., description="Unique job identifier")
    title: str = Field(..., min_length=1, description="Job title / position name")
    company: str = Field(..., min_length=1, description="Hiring company name")
    location: str = Field(default="Remote", description="Geographic location or remote policy")
    url: str = Field(..., description="Direct link or application URL")
    salary_min: Optional[int] = Field(default=None, ge=0, description="Minimum annual salary in USD")
    salary_max: Optional[int] = Field(default=None, ge=0, description="Maximum annual salary in USD")
    tags: List[str] = Field(default_factory=list, description="Associated skills, tech stack, or tags")
    source: str = Field(default="RemoteOK", description="Data source provider name")
    date_posted: Optional[str] = Field(default=None, description="ISO format publication date string")

    @model_validator(mode="before")
    @classmethod
    def normalize_raw_job_payload(cls, data: Any) -> Any:
        """
        Pre-processing model validator that standardizes raw incoming dicts
        from either RemoteOK or Himalayas endpoints into the unified JobItem shape.
        """
        if not isinstance(data, dict):
            raise ValueError("Raw job payload must be a dictionary")

        # Skip RemoteOK legal disclaimer meta object
        if "legal" in data or "0" in data and len(data) == 1:
            raise ValueError("RemoteOK API legal disclaimer element skipped")

        normalized: Dict[str, Any] = {}

        # 1. Standardize ID
        raw_id = data.get("id") or data.get("guid") or data.get("slug")
        if raw_id:
            normalized["id"] = str(raw_id)
        else:
            # Fallback identifier based on title and company
            comp = data.get("company") or data.get("companyName") or "unknown"
            pos = data.get("position") or data.get("title") or "unknown"
            normalized["id"] = f"{comp}-{pos}".lower().replace(" ", "-")

        # 2. Standardize Title / Position
        title = data.get("position") or data.get("title")
        if not title or not isinstance(title, str) or not title.strip():
            raise ValueError("Job record missing valid position/title string")
        normalized["title"] = title.strip()

        # 3. Standardize Company Name
        company = data.get("company") or data.get("companyName")
        if not company or not isinstance(company, str) or not company.strip():
            raise ValueError("Job record missing valid company name")
        normalized["company"] = company.strip()

        # 4. Standardize Location
        location = data.get("location")
        if not location and "locationRestrictions" in data:
            loc_restrictions = data["locationRestrictions"]
            if isinstance(loc_restrictions, list) and loc_restrictions:
                location = ", ".join(loc_restrictions)
            elif isinstance(loc_restrictions, str):
                location = loc_restrictions
        normalized["location"] = (location or "Remote").strip()

        # 5. Standardize Application URL
        url = data.get("url") or data.get("applicationUrl")
        if url and isinstance(url, str) and url.startswith("/"):
            url = f"https://remoteok.com{url}"
        if not url or not isinstance(url, str):
            url = f"https://remoteok.com/remote-jobs/{normalized['id']}"
        normalized["url"] = url.strip()

        # 6. Standardize Salaries
        def parse_salary(val: Any) -> Optional[int]:
            if val is None or val == "":
                return None
            try:
                num = int(float(val))
                return num if num >= 0 else None
            except (ValueError, TypeError):
                return None

        normalized["salary_min"] = parse_salary(data.get("salary_min") or data.get("minSalary"))
        normalized["salary_max"] = parse_salary(data.get("salary_max") or data.get("maxSalary"))

        # 7. Standardize Tags / Categories
        raw_tags = data.get("tags") or data.get("categories") or []
        if isinstance(raw_tags, list):
            normalized["tags"] = [str(t).strip().lower() for t in raw_tags if t and str(t).strip()]
        elif isinstance(raw_tags, str):
            normalized["tags"] = [t.strip().lower() for t in raw_tags.split(",") if t.strip()]
        else:
            normalized["tags"] = []

        # 8. Standardize Source & Date Posted
        normalized["source"] = str(data.get("source") or "RemoteOK")
        raw_date = data.get("date") or data.get("pubDate")
        if raw_date:
            if isinstance(raw_date, (int, float)):
                normalized["date_posted"] = datetime.fromtimestamp(raw_date).isoformat()
            else:
                normalized["date_posted"] = str(raw_date)
        else:
            normalized["date_posted"] = None

        return normalized


class HealthStatusResponse(BaseModel):
    """
    System health and telemetry payload returned by GET /health.
    """
    status: str = Field(..., description="Overall health status: healthy, degraded, or unhealthy")
    timestamp: str = Field(..., description="ISO 8601 current timestamp")
    engine_version: str = Field(..., description="Ingestion engine software version")
    circuit_breaker: CircuitBreakerMetrics = Field(..., description="Circuit breaker runtime metrics")
    available_endpoints: List[str] = Field(..., description="Directory of active API routes")


class IngestionResponse(BaseModel):
    """
    Main payload returned by GET /jobs detailing ingestion results.
    """
    status: str = Field(default="success", description="Pipeline execution result status")
    source: str = Field(..., description="Remote job API target ingested")
    metrics: IngestionMetrics = Field(..., description="Detailed execution telemetry")
    jobs: List[JobItem] = Field(..., description="Array of validated Pydantic job records")


class EasterEggResponse(BaseModel):
    """
    Interactive response for GET /easter-egg or X-Pipeline-State header trigger.
    """
    mode: str = Field(default="Antigravity-Engaged", description="Pipeline operation mode")
    quote: str = Field(..., description="Engineering motto")
    ascii_art: str = Field(..., description="Antigravity telemetry banner")
    telemetry: Dict[str, Any] = Field(..., description="System operational state & resilience features")
