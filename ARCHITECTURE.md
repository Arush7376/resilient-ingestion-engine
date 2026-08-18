# Technical Architecture & Resilient Ingestion Specification

## Executive Summary

This document provides a comprehensive system architecture reference for the **Resilient Data Ingestion Engine**. Designed to operate in complex target environments, the engine ingests public structured feeds while maintaining high availability, low latency, and zero silent failures. 

The architecture combines an asynchronous **HTTP/2 transport layer**, a thread-safe **Circuit Breaker Finite State Machine (FSM)**, **Anti-Detection Header Profile Alignment**, **Exponential Backoff with Randomized Jitter Pacing**, and a strict **Pydantic v2 Schema Validation Boundary**.

---

## 1. High-Level System Architecture

```
                                 +-------------------------------------------------+
                                 |              Client / API Consumer              |
                                 +-------------------------------------------------+
                                                          |
                                                          | GET /jobs, GET /health
                                                          v
                                 +-------------------------------------------------+
                                 |            FastAPI Application Router           |
                                 |                   (app/main.py)                 |
                                 +-------------------------------------------------+
                                                          |
                                                          v
                                 +-------------------------------------------------+
                                 |            Resilient Ingestion Engine           |
                                 |                  (app/engine.py)                |
                                 +-------------------------------------------------+
                                    /                     |                     \
                                   /                      |                      \
                                  v                       v                       v
            +---------------------------+   +---------------------------+   +---------------------------+
            |   Circuit Breaker FSM     |   | Anti-Detection Rotator    |   |    HTTPX AsyncClient      |
            | (CLOSED / OPEN / HALF_OPEN|   | (Browser Profile Hints)   |   |   (HTTP/2 Transport Pool) |
            +---------------------------+   +---------------------------+   +---------------------------+
                                                                                          |
                                                                                          | HTTP/2 TLS Requests
                                                                                          v
                                                                            +---------------------------+
                                                                            |  Upstream Target APIs     |
                                                                            | (RemoteOK / Himalayas)    |
                                                                            +---------------------------+
                                                                                          |
                                                                                          | Raw JSON Payloads
                                                                                          v
                                 +-------------------------------------------------+
                                 |       Pydantic v2 Schema Validation Boundary     |
                                 |                 (app/schemas.py)                |
                                 +-------------------------------------------------+
                                    /                                           \
                                   v                                             v
                    +-----------------------------+               +-----------------------------+
                    | Validated JobItem Records   |               | Schema Failures Quarantined |
                    | (Returned in API Response)  |               | (Logged & Tracked Metric)   |
                    +-----------------------------+               +-----------------------------+
```

---

## 2. Detection Surface & Anti-Fingerprinting Architecture

Modern Web Application Firewalls (WAFs) and bot detection vendors (Cloudflare Bot Management, DataDome, Akamai Bot Manager, Kasada) analyze incoming connections across multiple OSI model layers. Automated ingestion clients that rely on default HTTP libraries are trivially fingerprinted and blocked.

### 2.1 Detection Layers & WAF Heuristics

#### Network Layer Fingerprinting
1. **JA3 / JA4 TLS Handshake Signatures**:
   - **Mechanism**: WAFs compute MD5/SHA256 hashes of the Client Hello packet parameters: TLS Version, Accepted Cipher Suites, TLS Extensions, Elliptic Curves (`supported_groups`), and Point Formats.
   - **Anomalies**: Default OpenSSL stacks in Python (`urllib`, `requests`) offer cipher suites in an order distinct from standard desktop web browsers. A client advertising `User-Agent: Chrome/124` but presenting a standard OpenSSL JA3 hash is instantly flagged for OS/Browser mismatch.
2. **HTTP/2 Frame Ordering & SETTINGS Alignment**:
   - **Mechanism**: Upon establishing an HTTP/2 session, browsers transmit specific SETTINGS frames, WINDOW_UPDATE frames, and PRIORITY tree nodes.
   - **Anomalies**: Cloudflare and Akamai check the exact parameters (`HEADER_TABLE_SIZE`, `ENABLE_PUSH`, `MAX_CONCURRENT_STREAMS`, `INITIAL_WINDOW_SIZE`) and frame order. Non-browser HTTP/2 stacks send frames in different sequences or omit browser-standard settings.
3. **TCP/IP Stack Anomalies (Passive OS Fingerprinting / p0f)**:
   - **Mechanism**: WAFs inspect TCP SYN packet parameters: initial TCP Window Size, Time To Live (TTL), IP Options, and TCP MSS (Maximum Segment Size).
   - **Anomalies**: A client claiming to be Windows 11 Chrome but exhibiting Linux kernel TCP SYN packet characteristics (e.g., TTL=64 instead of TTL=128) is flagged via passive OS fingerprinting.

#### Browser & Runtime Layer Fingerprinting
1. **`navigator.webdriver` Flag**:
   - Automated browser drivers (Selenium, Puppeteer, ChromeDriver) expose `navigator.webdriver = true` or leak automation properties on `window` (`window.cdc_adoQaqTerminal_...`).
2. **Chrome DevTools Protocol (CDP) Artifacts**:
   - CDP commands leave measurable side-effects in Javascript runtime execution stacks and variable scoping.
3. **Canvas & WebGL Rendering Hashes**:
   - Browsers render offscreen Canvas primitives or 3D WebGL scenes. Variations in GPU hardware, drivers, sub-pixel antialiasing, and font rendering produce deterministic hash signatures. Headless environments without dedicated GPU rendering yield generic software renderer signatures (`llvmpipe`, `Mesa`).
4. **AudioContext Fingerprinting**:
   - WAF scripts process audio signal oscillations via `DynamicsCompressorNode` and measure rendering frequency variations across system audio stacks.
5. **Iframe Sandbox Leaks**:
   - Detecting missing browser features or discrepancies between `window.top` and `window.self` inside nested cross-origin iframe sandboxes.

#### Behavioral & Timing Layer Fingerprinting
1. **Fixed Polling Cadences**: Automated scripts making requests at exact intervals (e.g., exactly every 60.0 seconds) exhibit zero variance.
2. **Missing Secondary Static Assets**: A standard browser fetching an HTML document immediately triggers secondary parallel HTTP/2 streams for CSS stylesheets, JavaScript bundles, Web Fonts (`.woff2`), images, and favicons. Scrapers fetching only single endpoints stand out.
3. **Unnatural Interaction Trajectories**: Linear mouse movement vectors, instantaneous field typing, and sub-millisecond request sequences betray non-human execution.

### 2.2 Client Profile Alignment Countermeasures

The `AntiDetectionHeaderRotator` module in `app/engine.py` addresses detection vectors by enforcing **strict profile alignment** across Client Hints, User Agents, and HTTP/2 transport settings:

```python
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
}
```

- **Client Hint Synchronization**: The `Sec-CH-UA` and `Sec-CH-UA-Platform` headers precisely match the underlying browser version and operating system declared in the `User-Agent`.
- **Navigation Context**: `Sec-Fetch-*` headers replicate genuine top-level browser navigation actions (`Sec-Fetch-Mode: navigate`, `Sec-Fetch-Dest: document`).
- **HTTP/2 Transport Integration**: `ResilientIngestionEngine` utilizes `httpx.AsyncClient(http2=True)`, ensuring requests are multiplexed over HTTP/2 connections matching standard browser negotiation flows.

---

## 3. Ingestion Strategy & Plan B Architecture

### 3.1 Pacing, Backoff, and Connection Pooling

To prevent trigger thresholds on target rate limiters (HTTP 429) while preserving high throughput, the engine uses exponential backoff augmented with uniform randomized jitter:

$$\text{delay} = \min\left(\text{max\_backoff},\; \text{base} \times 2^{\text{attempt} - 1}\right) + \text{jitter}$$

Where $\text{jitter} \sim U(0.05,\, \text{jitter\_max})$.

```
Attempt 1 (Initial Request):  0.0s delay
Attempt 2 (Retry 1):          min(10.0, 1.0 * 2^0) + rand(0.05, 0.5)  =  1.0s + ~0.27s  = 1.27s delay
Attempt 3 (Retry 2):          min(10.0, 1.0 * 2^1) + rand(0.05, 0.5)  =  2.0s + ~0.41s  = 2.41s delay
Attempt 4 (Retry 3):          min(10.0, 1.0 * 2^2) + rand(0.05, 0.5)  =  4.0s + ~0.15s  = 4.15s delay
```

**Connection Pooling Configuration**:
- Persistent HTTP/2 connection reuse reduces TCP socket setup overhead and TLS handshake latency.
- Pool Limits: `max_keepalive_connections=20`, `max_connections=100`.
- Timeout Strategy: 15.0s read timeout with a strict 5.0s connect timeout to prune stale sockets fast.

### 3.2 Identity & Session Management

- **Session Isolation**: Each request context maintains decoupled cookie jars to prevent cross-request tracking state leakage.
- **Residential Proxy Rotation**: In production environments requiring IP distribution, outbound requests pass through an upstream proxy pool utilizing sticky sessions or per-request IP rotation across residential ASN subnets, preventing IP-based velocity blocking.

### 3.3 Plan B: Fallback Execution Strategy

When direct HTTP/2 REST ingestion encounters aggressive JavaScript challenges (Cloudflare Turnstile, Kasada, Akamai Bot Manager), the engine falls back to an automated headless rendering tier ("Plan B"):

```
+-----------------------------------------------------------------------------------+
|                            PLAN A: Direct HTTP/2 Pipeline                         |
|  Async HTTPX Client --> Header Rotator --> Target REST API --> Schema Validation  |
+-----------------------------------------------------------------------------------+
                                          |
                                          | HTTP 403 / 429 / WAF Challenge Detected
                                          v
+-----------------------------------------------------------------------------------+
|                       PLAN B: Headless Browser & Hydration Tier                   |
+-----------------------------------------------------------------------------------+
                                          |
        +---------------------------------+---------------------------------+
        |                                 |                                 |
        v                                 v                                 v
+-----------------------+     +-----------------------+     +-----------------------+
|  Headless Cluster     |     |   DOM Hydration State |     |  JSON-LD Schema Block |
|  (Playwright/Stealth) |     |  Extraction           |     |  Parsing              |
| - evasive-plugins     |     | - __NEXT_DATA__       |     | - <script type=       |
| - canvas/audio patches|     | - __INITIAL_STATE__   |     |   "application/ld+json|
+-----------------------+     +-----------------------+     +-----------------------+
        |                                 |                                 |
        +---------------------------------+---------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                        Pydantic v2 Schema Validation Boundary                     |
+-----------------------------------------------------------------------------------+
```

1. **Headless Browser Clusters with Stealth Patches**:
   - Deploys Playwright / Puppeteer browser instances configured with stealth evasion libraries (`playwright-stealth`, `puppeteer-extra-plugin-stealth`).
   - Overrides `navigator.webdriver`, spoofs `languages`, injects real Chrome plugin arrays, and passes Chrome DevTools evasions.
2. **DOM Hydration State Extraction**:
   - Instead of parsing fragile visual HTML markup, the browser evaluates the initial DOM to extract server-rendered hydration state blocks:
     - **Next.js**: `<script id="__NEXT_DATA__" type="application/json">`
     - **Nuxt / Vue / React**: `<script>window.__INITIAL_STATE__=...</script>`
3. **JSON-LD & Microdata Extraction**:
   - Parses `<script type="application/ld+json">` embedded schemas (`JobPosting`, `Organization`) directly into the Pydantic parser, guaranteeing structured data extraction even when visible visual markup alters significantly.

---

## 4. Resilience, Fault Tolerance & State Machine Architecture

### 4.1 Zero Silent Failures & Schema Validation

To prevent malformed target payloads or DOM structural changes from polluting downstream data repositories, all raw payloads pass through the `JobItem` Pydantic v2 validation boundary.

- **Payload Normalization**: The `@model_validator(mode="before")` pre-processor normalizes inconsistent schema naming patterns across different providers:
  - IDs: maps `id`, `guid`, or `slug` (generating fallback slugs from title/company when missing).
  - Positions: normalizes `position` and `title`.
  - Compensation: extracts `salary_min`, `salary_max`, `minSalary`, `maxSalary`.
- **Error Quarantine**: Validation errors (`ValidationError`, `ValueError`) increment the `schema_failures` counter in `IngestionMetrics` and quarantine the individual invalid record without breaking the execution run or discarding valid records in the same batch.

### 4.2 Circuit Breaker Finite State Machine (FSM)

The `CircuitBreaker` class in `app/engine.py` protects downstream systems and prevents waste of connection resources during upstream target outages.

#### State Transition Diagram

```
                 +---------------------------------------------------+
                 |                                                   |
                 |                 CLOSED (Normal)                   |
                 |      Outbound HTTP requests executed normally     |
                 |                                                   |
                 +---------------------------------------------------+
                                    |               ^
                                    |               |
         Consecutive Failures       |               | Trial Probe Succeeded
       >= failure_threshold (5)     |               | (record_success)
                                    v               |
                 +---------------------------------------------------+
                 |                                                   |
                 |                   OPEN (Tripped)                  |
                 |        Fast-fails all outbound requests           |
                 |        Returns HTTP 503 Service Unavailable       |
                 |                                                   |
                 +---------------------------------------------------+
                                    |
                                    | Cooldown Expired
                                    | (cooldown_seconds = 30.0s)
                                    v
                 +---------------------------------------------------+
                 |                                                   |
                 |                HALF_OPEN (Testing)                |
                 |      Allows single trial probe request            |
                 |                                                   |
                 +---------------------------------------------------+
                                    |
                                    | Trial Probe Failed
                                    | (record_failure)
                                    +-----------------------+
                                                            |
                                                            v
                                            (Re-enters OPEN State)
```

#### Finite States & Behaviors

| State | Outbound Request Policy | Transition Condition | Action on Success | Action on Failure |
| :--- | :--- | :--- | :--- | :--- |
| **`CLOSED`** | **Allowed** | Initial default state. | Reset `consecutive_failures = 0`. | Increment `consecutive_failures`. If threshold (5) reached $\rightarrow$ transition to **`OPEN`**. |
| **`OPEN`** | **Blocked (Fast-Fail)** | Consecutive failures hit threshold. | N/A (Requests blocked immediately; raises `CircuitBreakerOpenException`). | N/A |
| **`HALF_OPEN`** | **Trial Probe Allowed** | Cooldown timer (30.0s) elapses while in `OPEN`. | Trial probe succeeds $\rightarrow$ transition to **`CLOSED`**. | Trial probe fails $\rightarrow$ transition to **`OPEN`** (restarts cooldown). |

#### Concurrency & Safety Controls
- **Thread & Async Safety**: State evaluations and transitions operate within an `asyncio.Lock()` context to prevent race conditions during parallel asynchronous request execution.
- **Fast-Fail Exceptions**: Attempts to execute requests while `OPEN` raise a `CircuitBreakerOpenException` containing telemetry detailing remaining cooldown seconds.

---

## 5. Boundaries & Ethical Compliance

The architecture enforces strict technical and ethical boundaries:

1. **Public Unauthenticated Feeds Only**:
   - Ingestion targets are strictly confined to publicly exposed, unauthenticated data feeds (e.g., public REST APIs, public job boards).
2. **Prohibition of Paywall and Access Control Bypass**:
   - The engine does not perform credential stuffing, account creation, CAPTCHA solving against authenticated portals, or session hijacking to bypass subscription paywalls.
3. **Concurrency & Rate Limit Conformance**:
   - Outbound connection pools enforce strict upper limits (`max_connections=100`, bounded request rates) to eliminate denial-of-service risks against target servers. Respects HTTP 429 backoff headers (`Retry-After`).
4. **PII Filtering & Data Minimization**:
   - Schemas reject personal identifiable information (PII) of candidate applicants. Only public job metadata (title, salary range, company, description tags) is extracted and stored.
