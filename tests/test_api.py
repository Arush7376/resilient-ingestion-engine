"""
tests/test_api.py
------------------
Async integration test suite for FastAPI routes and headers.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app, global_circuit_breaker
from app.schemas import CircuitBreakerStateEnum


@pytest.mark.asyncio
async def test_root_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["engine"] == "Resilient Ingestion Engine"
        assert "available_endpoints" in data


@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "degraded", "unhealthy"]
        assert "circuit_breaker" in data
        assert data["circuit_breaker"]["failure_threshold"] == 5


@pytest.mark.asyncio
async def test_easter_egg_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/easter-egg")
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "High-Performance-Active"
        assert "quote" in data
        assert "ascii_art" in data


@pytest.mark.asyncio
async def test_custom_header_middleware():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        headers = {"X-Pipeline-State": "Telemetry-Engaged"}
        response = await ac.get("/", headers=headers)
        assert response.status_code == 200
        assert response.headers.get("X-Pipeline-Mode") == "High-Performance-Active"
        assert response.headers.get("X-Resilience-Rating") == "Production-Grade (5/5)"
