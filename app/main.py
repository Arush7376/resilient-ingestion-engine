"""
app/main.py
-----------
FastAPI application router and HTTP service entrypoint.

Exposes endpoints:
- GET /           : Health overview and available endpoints registry
- GET /health     : Deep system diagnostics & circuit breaker metrics
- GET /jobs       : Triggers resilient ingestion pipeline with live remote listings
- GET /easter-egg : Interactive telemetry bonus payload

Middleware & Lifespan:
- Lifespan context manager initializes and closes AsyncClient connection pool cleanly.
- Header middleware intercepts 'X-Pipeline-State: Antigravity-Engaged' header for custom response.
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Query, HTTPException, Request, Response
from fastapi.responses import JSONResponse, HTMLResponse

from app.schemas import (
    HealthStatusResponse,
    IngestionResponse,
    EasterEggResponse,
    CircuitBreakerStateEnum,
)
from app.engine import (
    ResilientIngestionEngine,
    CircuitBreaker,
    CircuitBreakerOpenException,
)
from app.dashboard import get_dashboard_html

# Global CircuitBreaker instance shared across application requests
global_circuit_breaker = CircuitBreaker(failure_threshold=5, cooldown_seconds=30.0)

# Global Resilient Ingestion Engine instance
engine = ResilientIngestionEngine(circuit_breaker=global_circuit_breaker)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan manager for async resource management.
    Ensures HTTPX AsyncClient connection pool is initialized on startup
    and closed gracefully on shutdown.
    """
    await engine.initialize()
    yield
    await engine.shutdown()


app = FastAPI(
    title="Resilient Data Ingestion Engine",
    description=(
        "Production-grade, highly resilient data ingestion pipeline written in Python "
        "using FastAPI, HTTPX (with HTTP/2 transport support), and Pydantic v2."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def easter_egg_middleware(request: Request, call_next):
    """
    Middleware checking for custom header 'X-Pipeline-State'.
    Injects custom response telemetry headers and handles custom bonus flow.
    """
    header_val = request.headers.get("X-Pipeline-State")
    response: Response = await call_next(request)

    if header_val in ["Antigravity-Engaged", "Telemetry-Engaged", "High-Performance"]:
        response.headers["X-Pipeline-Mode"] = "High-Performance-Active"
        response.headers["X-Resilience-Rating"] = "Production-Grade (5/5)"
        response.headers["X-Anti-Detection"] = "HTTP/2 + Browser Profile Consistent"

    return response


@app.get("/", summary="API Root Directory & Health Summary")
async def root(request: Request, format: Optional[str] = Query(default=None)):
    """
    Root endpoint listing API capabilities, system status, and available routes.
    Renders interactive telemetry dashboard for browser navigation (`Accept: text/html`)
    and raw JSON for API clients and test runners.
    """
    accept_header = request.headers.get("accept", "")
    if "text/html" in accept_header and format != "json":
        return HTMLResponse(content=get_dashboard_html())

    cb_metrics = await global_circuit_breaker.get_metrics()
    return {
        "engine": "Resilient Ingestion Engine",
        "status": "online" if cb_metrics.state != CircuitBreakerStateEnum.OPEN else "circuit_open",
        "version": "1.0.0",
        "documentation": "/docs",
        "available_endpoints": [
            "GET /",
            "GET /health",
            "GET /jobs?source=remoteok&limit=20",
        ],
        "circuit_breaker_state": cb_metrics.state,
    }


@app.get("/health", response_model=HealthStatusResponse, summary="Detailed Engine Diagnostics")
async def health_check():
    """
    Provides deep health diagnostics including Circuit Breaker state,
    consecutive failures, total successes/failures, and cooldown remaining.
    """
    cb_metrics = await global_circuit_breaker.get_metrics()

    if cb_metrics.state == CircuitBreakerStateEnum.OPEN:
        status_str = "unhealthy"
    elif cb_metrics.state == CircuitBreakerStateEnum.HALF_OPEN:
        status_str = "degraded"
    else:
        status_str = "healthy"

    return HealthStatusResponse(
        status=status_str,
        timestamp=datetime.now(timezone.utc).isoformat(),
        engine_version="1.0.0",
        circuit_breaker=cb_metrics,
        available_endpoints=["/", "/health", "/jobs"],
    )


@app.get("/jobs", response_model=IngestionResponse, summary="Ingest Live Remote Jobs")
async def ingest_jobs(
    source: str = Query(
        default="remoteok",
        description="Target job provider endpoint to ingest ('remoteok' or 'himalayas')",
    ),
    limit: Optional[int] = Query(
        default=None, ge=1, le=200, description="Optional upper limit on returned job listings"
    ),
):
    """
    Executes live data ingestion pipeline from public remote job APIs with resilience controls:
    - HTTP/2 transport protocol alignment
    - Anti-detection header rotation with browser profile consistency
    - Exponential backoff with randomized jitter retry pacing
    - Circuit Breaker state protection & fast-fail
    - Strict Pydantic v2 schema validation & detailed telemetry
    """
    if source.lower() not in engine.SOURCES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid target source '{source}'. Supported sources: {list(engine.SOURCES.keys())}",
        )

    try:
        jobs, metrics = await engine.ingest_jobs(source_name=source, limit=limit)
        return IngestionResponse(
            status="success",
            source=source.capitalize(),
            metrics=metrics,
            jobs=jobs,
        )
    except CircuitBreakerOpenException as cbe:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Service Unavailable",
                "message": str(cbe),
                "circuit_breaker_status": "OPEN",
                "cooldown_remaining_seconds": cbe.cooldown_remaining,
            },
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Ingestion pipeline execution failure: {str(exc)}",
        )


@app.get("/easter-egg", response_model=EasterEggResponse, include_in_schema=False, summary="Hidden High-Performance Telemetry Route")
async def easter_egg():
    """
    Interactive hidden Easter Egg route revealing system telemetry, engineering motto,
    and ASCII art banner.
    """
    cb_metrics = await global_circuit_breaker.get_metrics()

    art = r"""
     ____  _____ ____ _____ _     ___ _____ _   _ _____ 
    |  _ \| ____/ ___|_   _| |   |_ _| ____| \ | |_   _|
    | |_) |  _| \___ \ | | | |    | ||  _| |  \| | | |  
    |  _ <| |___ ___) || | | |___ | || |___| |\  | | |  
    |_| \_\_____|____/ |_| |_____|___|_____|_| \_| |_|  
    """

    return EasterEggResponse(
        mode="High-Performance-Active",
        quote="Build systems so resilient they operate seamlessly under peak backpressure.",
        ascii_art=art,
        telemetry={
            "http_version": "HTTP/2 (Multiplexed)",
            "pacing_algorithm": "Exponential Backoff + Randomized Jitter",
            "validation": "Strict Pydantic v2 (Zero Silent Failures)",
            "circuit_breaker": {
                "state": cb_metrics.state,
                "consecutive_failures": cb_metrics.consecutive_failures,
                "failure_threshold": cb_metrics.failure_threshold,
                "success_count": cb_metrics.success_count,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
