# Architectural Decisions & Trade-offs

## 1. Direct HTTP/2 Client Architecture vs. Heavy Headless Browsers

**Decision**: Lightweight asynchronous HTTP/2 (`httpx`) transport paired with consistent Client Hint header profiles and Pydantic v2 validation over headless browser clusters (Playwright / Puppeteer).

**Trade-off Analysis**:
- **Compute Footprint**: Headless browsers require ~300MB–500MB RAM and 1–2 CPU cores per worker process. `httpx` operates at ~15MB RAM per process, supporting thousands of concurrent HTTP/2 connections per node.
- **Latency & Throughput**: Direct HTTP requests yield 50ms–200ms latency versus 2s–5s for headless DOM rendering and script execution.
- **Operational Cost**: Running browser clusters at 10M requests/day costs orders of magnitude more in cloud infrastructure.
- **Detection Surface**: Headless browsers leak Chrome DevTools Protocol (CDP) artifacts, `navigator.webdriver`, and hardware canvas signatures. HTTP/2 protocol-aligned headers bypass basic-to-intermediate WAF checks cleanly without automation flag surface area.

---

## 2. In-Memory State vs. Distributed Production Roadmap

**Time Limit Trade-off**: Implemented an in-memory Circuit Breaker (`asyncio.Lock`) and single-process exponential backoff pacing instead of a distributed state store. While thread-safe for a single node, breaker state and rate limits do not synchronize across horizontal workers.

**1-Week Production Roadmap**:
1. **Distributed State Machine**: Migrate Circuit Breaker state and sliding-window rate limiters to Redis cluster backed by Celery/Temporal task workers.
2. **Residential Proxy Orchestration**: Integrate automated proxy pool rotation with real-time health-scoring and fallback egress IP routing.
3. **DOM & Schema Self-Healing**: Deploy LLM-assisted schema fallback parsers to automatically adjust to upstream JSON structure drift or HTML markup changes.

---

## 3. AI Assistance & Manual Engineering Audits

**AI Scaffolding**: Leveraged AI for initial boilerplate generation across FastAPI routes, standard Pydantic schema field definitions, and markdown outline structures.

**Manual Verification & Hardening**:
- **Circuit Breaker Concurrency**: Hand-crafted `asyncio.Lock` state mutations to guarantee zero race conditions during fast-fail transitions (`CLOSED` -> `OPEN` -> `HALF_OPEN`).
- **Jitter Pacing Math**: Audited retry pacing to enforce uniform randomized jitter bounds ($\min(\text{max\_backoff}, \text{base} \times 2^{\text{attempt}-1}) + U(0.05, 0.5)$), preventing synchronization thundering herds.
- **Header Profile Consistency**: Verified Client Hint alignment (`Sec-CH-UA`, `Sec-Fetch-*`) across Chrome, Firefox, Edge, and Safari profiles.
- **Edge Case Filtering**: Engineered the `@model_validator` pre-processor to catch non-job metadata (such as RemoteOK's legal disclaimer header object), preventing validation failures.
