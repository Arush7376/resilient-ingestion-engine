# Architectural Decisions & Trade-Off Engineering Log

This document records the key architectural decisions behind the **Resilient Data Ingestion & Telemetry Engine**, including the engineering trade-offs, current limitations, production-scaling roadmap, and the division between AI-assisted development and manual engineering.

---

## 1. Direct HTTP/2 Transport vs. Headless Browsers

### The Decision

For the primary ingestion path, we chose **asynchronous HTTP/2 using `httpx`**, combined with aligned Client Hint headers and **Pydantic v2** validation.

Headless browsers such as Playwright and Puppeteer are reserved for a fallback tier when JavaScript-based challenges prevent direct HTTP ingestion.

### Why We Chose Direct HTTP/2

| Dimension                  | Direct HTTP/2 (`httpx`)                              | Headless Browsers                                                         |
| -------------------------- | ---------------------------------------------------- | ------------------------------------------------------------------------- |
| **Resource Usage**         | Low memory and CPU overhead                          | High memory and CPU overhead                                              |
| **Latency**                | Typically tens to hundreds of milliseconds per batch | Typically seconds due to browser startup, rendering, and script execution |
| **Infrastructure Cost**    | Low and easy to scale                                | Significantly higher at scale                                             |
| **Concurrency**            | High concurrency through HTTP/2 multiplexing         | Limited by browser instance resources                                     |
| **Operational Complexity** | Relatively simple                                    | Requires browser lifecycle and cluster management                         |
| **JavaScript Support**     | None                                                 | Full browser execution                                                    |

### Engineering Rationale

A direct HTTP client eliminates the rendering overhead of a full browser and provides a significantly smaller resource footprint for high-throughput ingestion.

However, this approach is not universally applicable. Some modern platforms require JavaScript execution or browser-specific behavior. For those cases, the architecture provides a **Plan B browser-based fallback** rather than making browsers the default transport layer.

> **Key takeaway:** Headless browsers provide compatibility, but direct HTTP/2 provides better efficiency for workloads that do not require browser execution.

---

## 2. In-Memory State vs. Distributed Production Roadmap

### Current MVP Architecture

The MVP implements the **Circuit Breaker finite-state machine (FSM)** and exponential backoff using in-memory primitives such as `asyncio.Lock`.

The circuit breaker supports the standard:

**CLOSED → OPEN → HALF_OPEN → CLOSED**

state lifecycle.

Within a single process, locking ensures that concurrent requests cannot perform conflicting state transitions.

### Current Limitation

Because the state is stored in memory, it is isolated to individual processes.

For example, if the service is deployed across ten containers, each container maintains its own:

* Circuit breaker state
* Failure counters
* Rate-limiting state
* Recovery information

This is acceptable for the MVP but is not sufficient for a distributed production environment.

### Production Scaling Roadmap

#### Phase 1 — Distributed State

Introduce **Redis** as the shared state layer for:

* Circuit breaker state
* Sliding-window rate limiting
* Failure counters
* Atomic state transitions

Background ingestion workloads can then be decoupled using **Temporal or Celery**.

#### Phase 2 — Resilient Egress Management

Introduce managed outbound egress infrastructure with:

* Health-aware routing
* Per-destination rate controls
* Failure and latency monitoring
* Automatic removal of unhealthy routes

This layer should operate within the target platform's terms of service and applicable usage policies.

#### Phase 3 — Adaptive Schema Recovery

Introduce an LLM-assisted fallback parser that activates when upstream schema changes cause Pydantic validation failures.

The system can then:

1. Detect schema drift.
2. Analyze the changed payload structure.
3. Propose updated field mappings or selectors.
4. Validate the proposed transformation.
5. Require controlled deployment before applying parser changes.

This prevents upstream changes from immediately breaking the ingestion pipeline while maintaining a controlled validation boundary.

---

## 3. AI Assistance vs. Manual Engineering

AI tools were used primarily to accelerate scaffolding and documentation. Critical concurrency, reliability, validation, and integration logic was manually reviewed and hardened.

```text
+--------------------------------------------------------------------------------+
|                         AI-Assisted Scaffolding                                |
|                                                                                |
|  • Initial FastAPI route structure                                             |
|  • Basic Pydantic v2 schema definitions                                       |
|  • Initial documentation structure                                            |
+--------------------------------------------------------------------------------+
                                      |
                                      v
+--------------------------------------------------------------------------------+
|                         Manual Engineering & Hardening                         |
|                                                                                |
|  • Circuit breaker concurrency control                                        |
|  • Retry and jitter verification                                              |
|  • HTTP client configuration and consistency checks                            |
|  • Schema pre-processing and edge-case handling                              |
|  • Integration testing and validation                                         |
+--------------------------------------------------------------------------------+
```

### AI-Assisted Work

AI was primarily used for:

* Generating initial FastAPI endpoints such as `/jobs` and `/health`.
* Drafting Pydantic v2 models for job-related payloads.
* Creating the initial Markdown documentation structure.
* Accelerating repetitive boilerplate development.

### Manual Engineering Work

#### 1. Concurrent Circuit Breaker State Management

Naive implementations can perform state checks and mutations independently, creating race conditions under high concurrency.

The final implementation uses explicit `asyncio.Lock` protection around critical state transitions to ensure that circuit-breaker decisions remain consistent.

#### 2. Retry Backoff and Jitter

Deterministic retry intervals can cause multiple workers to retry simultaneously, producing a **thundering-herd effect**.

The implementation uses exponential backoff combined with randomized jitter:

$$
delay = \min(max_backoff,\ base \times 2^{attempt-1}) + U(0.05,0.5)
$$

This distributes retry attempts over time and reduces synchronized request bursts.

#### 3. HTTP Header Consistency

HTTP request metadata must remain internally consistent. The implementation therefore validates the relationship between browser-related headers rather than treating individual headers independently.

The `AntiDetectionHeaderRotator` maintains consistent values across fields such as:

* `Sec-CH-UA`
* `Sec-Fetch-Dest`
* `Sec-Fetch-Mode`
* `Sec-Fetch-Site`
* `Sec-Fetch-User`

The goal is **protocol and client-profile consistency**, not bypassing access controls or security mechanisms.

#### 4. Schema Pre-Processing and Data Hygiene

Real-world upstream feeds frequently contain metadata or non-standard objects alongside the expected records.

For example, a job feed may include a legal notice or metadata object before the actual job records.

To handle these cases, `app/schemas.py` uses Pydantic's:

`@model_validator(mode="before")`

to normalize, filter, and transform incoming data before it reaches the strict validation layer.

This keeps the downstream data model predictable while allowing the ingestion layer to tolerate minor upstream inconsistencies.

---

## 4. Engineering Principles

The architecture follows four core principles:

1. **Use the lightest transport that satisfies the workload.**
2. **Keep the MVP simple while designing clear upgrade paths for distributed deployment.**
3. **Protect reliability-critical state transitions from concurrency issues.**
4. **Use AI to accelerate development while retaining human ownership of validation, security, and production hardening.**

The result is a lightweight ingestion architecture that prioritizes **performance, resilience, maintainability, and controlled scalability** without introducing unnecessary infrastructure into the initial deployment.

---

## Implementation References

The primary implementation is maintained alongside:

* `app/engine.py` — ingestion and resilience logic
* `app/schemas.py` — validation and data normalization
* `ARCHITECTURE.md` — system-level architecture and design decisions
