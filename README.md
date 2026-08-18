# Resilient Data Ingestion & Telemetry Engine

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110.0%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![HTTPX](https://img.shields.io/badge/HTTPX-HTTP%2F2-0055ff.svg)](https://www.python-httpx.org/)
[![Pydantic](https://img.shields.io/badge/Pydantic-v2-e91e63.svg)](https://docs.pydantic.dev/)
[![Tests](https://img.shields.io/badge/Tests-14%20Passing-brightgreen.svg)]()

## Overview

The **Resilient Data Ingestion & Telemetry Engine** is a high-throughput, fault-tolerant Python microservice built with **FastAPI**, **HTTPX (with HTTP/2 transport)**, and **Pydantic v2**. It is engineered to extract public data from upstream APIs and remote job feeds reliably without tripping anti-bot heuristics or suffering from silent failure modes.

By combining browser Client Hint profile alignment, an thread-safe Circuit Breaker Finite State Machine (FSM), randomized exponential backoff pacing, and strict schema validation boundaries, the system ensures zero silent failures and high operational availability.

---

## Core Architecture & Key Features

- ⚡ **HTTP/2 Transport & Anti-Detection Fingerprinting**: Multiplexed HTTP/2 connection pooling (`httpx.AsyncClient`) paired with consistent Client Hint headers (`Sec-CH-UA`, `Sec-Fetch-*`) matching real desktop browser profiles to pass WAF header heuristics.
- 🛡️ **Finite State Machine Circuit Breaker**: Concurrency-safe (`asyncio.Lock`) state machine transitioning across `CLOSED`, `OPEN` (fast-fail), and `HALF_OPEN` (recovery probe) states to prevent cascading downstream failures.
- ⏱️ **Exponential Backoff with Randomized Jitter**: Pacing mechanism enforcing delay bounds ($\min(\text{max\_backoff}, \text{base} \times 2^{\text{attempt}-1}) + \text{jitter}$) to prevent thundering herd API rate-limiting (HTTP 429).
- 🔍 **Strict Pydantic v2 Schema Quarantine**: Zero silent failures via pre-validation payload normalization (`@model_validator`). Invalid items are quarantined and logged into execution telemetry (`schema_failures`) without disrupting valid batch records.
- 📊 **Deep Diagnostic Telemetry**: Continuous operational monitoring exposed via interactive `/health` and telemetry endpoints.

---

## API Endpoints Directory

| Method | Endpoint | Description | Query Parameters |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | API Root directory & system operational overview | None |
| `GET` | `/health` | Deep diagnostic metrics, circuit breaker state & cooldown counters | None |
| `GET` | `/jobs` | Triggers resilient live data ingestion pipeline | `source` (default: `"remoteok"`, options: `"remoteok"`, `"himalayas"`), `limit` (e.g. `20`) |
| `GET` | `/easter-egg` | Interactive Antigravity telemetry bonus route (`X-Pipeline-State` header) | None |

---

## Quickstart Guide

### Prerequisites
- Python 3.10+ installed
- Virtual environment support (`venv`)

### 1. Repository Setup & Environment Installation

```bash
# Clone repository
git clone https://github.com/user/resilient-ingestion-engine.git
cd resilient-ingestion-engine

# Create and activate virtual environment
python -m venv .venv
# On Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Running the Development Server

Start the local server using `uvicorn`:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Access the interactive API documentation at:
- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

### 3. Running the Automated Test Suite

Execute the comprehensive test suite verifying the Circuit Breaker FSM, Anti-Detection Rotator, Pydantic v2 validation boundary, and FastAPI routes:

```bash
pytest -v
```

Output:
```text
============================= test session starts =============================
tests/test_api.py ....                                                   [ 28%]
tests/test_circuit_breaker.py ....                                       [ 57%]
tests/test_live_ingestion.py ..                                          [ 71%]
tests/test_schemas.py ....                                               [100%]
============================= 14 passed in 4.68s ==============================
```

---

## Production Deployment

The repository includes a ready-to-deploy `Procfile` configured for deployment on platforms like **Render**, **Railway**, or **Heroku**:

```text
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### Deploying to Render / Railway:
1. Connect your repository to Render or Railway.
2. Select **Python 3 Web Service**.
3. Set Build Command: `pip install -r requirements.txt`.
4. Set Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT` (or let platform auto-detect `Procfile`).

---

## Technical Documentation & Architecture Deep-Dive

For complete technical specifications, security analysis, anti-detection details, and trade-off rationales:

- 📖 [**ARCHITECTURE.md**](./ARCHITECTURE.md): Technical Architecture & Resilient Ingestion Specification (WAF Detection Surfaces, HTTP/2 Alignment, Circuit Breaker FSM, Plan B Headless Browser Hydration Tier, Ethical Boundaries).
- ⚖️ [**DECISIONS.md**](./DECISIONS.md): Architectural Decisions & Trade-off Analysis (Lightweight HTTP/2 vs Headless Browser clusters, 1-Week Production Roadmap, AI Assistance & Manual Engineering Verification).
