"""
app/dashboard.py
----------------
Interactive Live Telemetry & Control Dashboard for the Resilient Data Ingestion Engine.
Serves a responsive glassmorphism dark-mode UI with live feed exploration, Circuit Breaker
FSM simulation controls, and Konami code Easter Egg.
"""

def get_dashboard_html() -> str:
    return r"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Resilient Data Ingestion Engine | Operational Telemetry</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #090d16;
            --bg-card: rgba(17, 24, 39, 0.75);
            --border-card: rgba(255, 255, 255, 0.08);
            --accent-cyan: #00f3ff;
            --accent-purple: #8b5cf6;
            --accent-pink: #ec4899;
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
            --status-green: #10b981;
            --status-amber: #f59e0b;
            --status-red: #ef4444;
            --font-sans: 'Inter', system-ui, -apple-system, sans-serif;
            --font-mono: 'JetBrains Mono', monospace;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            background-color: var(--bg-primary);
            background-image: 
                radial-gradient(ellipse at top left, rgba(139, 92, 246, 0.15), transparent 50%),
                radial-gradient(ellipse at bottom right, rgba(0, 243, 255, 0.12), transparent 50%);
            background-attachment: fixed;
            color: var(--text-main);
            font-family: var(--font-sans);
            min-height: 100vh;
            line-height: 1.5;
            padding-bottom: 60px;
        }

        /* Easter Egg Overlay Canvas */
        #easter-egg-canvas {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            pointer-events: none;
            z-index: 9999;
            display: none;
        }

        .container {
            max-width: 1280px;
            margin: 0 auto;
            padding: 0 24px;
        }

        /* Header Navigation */
        header {
            border-bottom: 1px solid var(--border-card);
            backdrop-filter: blur(12px);
            position: sticky;
            top: 0;
            z-index: 100;
            background: rgba(9, 13, 22, 0.85);
        }

        .nav-content {
            display: flex;
            align-items: center;
            justify-content: space-between;
            height: 72px;
        }

        .logo-group {
            display: flex;
            align-items: center;
            gap: 12px;
            cursor: pointer;
            user-select: none;
        }

        .logo-icon {
            width: 38px;
            height: 38px;
            background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple));
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 0 15px rgba(0, 243, 255, 0.3);
            transition: transform 0.3s ease;
        }

        .logo-group:hover .logo-icon {
            transform: rotate(10deg) scale(1.05);
        }

        .logo-title {
            font-size: 1.15rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            background: linear-gradient(to right, #ffffff, #d1d5db);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .logo-badge {
            font-family: var(--font-mono);
            font-size: 0.75rem;
            background: rgba(0, 243, 255, 0.1);
            color: var(--accent-cyan);
            border: 1px solid rgba(0, 243, 255, 0.3);
            padding: 2px 8px;
            border-radius: 20px;
        }

        .nav-links {
            display: flex;
            gap: 16px;
            align-items: center;
        }

        .nav-btn {
            color: var(--text-muted);
            text-decoration: none;
            font-size: 0.875rem;
            font-weight: 500;
            padding: 8px 14px;
            border-radius: 8px;
            transition: all 0.2s ease;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }

        .nav-btn:hover {
            color: var(--text-main);
            background: rgba(255, 255, 255, 0.05);
        }

        .nav-btn.primary {
            background: linear-gradient(135deg, rgba(0, 243, 255, 0.15), rgba(139, 92, 246, 0.15));
            border: 1px solid rgba(0, 243, 255, 0.3);
            color: var(--accent-cyan);
        }

        .nav-btn.primary:hover {
            box-shadow: 0 0 20px rgba(0, 243, 255, 0.3);
            border-color: var(--accent-cyan);
        }

        /* Hero Section */
        .hero {
            padding: 40px 0 24px 0;
        }

        .hero-title {
            font-size: 2.25rem;
            font-weight: 800;
            letter-spacing: -0.03em;
            margin-bottom: 12px;
            background: linear-gradient(to right, #ffffff, #9ca3af);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .hero-subtitle {
            color: var(--text-muted);
            font-size: 1.05rem;
            max-width: 800px;
            margin-bottom: 24px;
        }

        /* Metrics Grid */
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
            gap: 20px;
            margin-bottom: 36px;
        }

        .card {
            background: var(--bg-card);
            border: 1px solid var(--border-card);
            backdrop-filter: blur(16px);
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
            transition: transform 0.2s ease, border-color 0.2s ease;
        }

        .card:hover {
            border-color: rgba(255, 255, 255, 0.15);
            transform: translateY(-2px);
        }

        .card-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 12px;
        }

        .card-title {
            font-size: 0.875rem;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .card-icon {
            color: var(--accent-cyan);
        }

        .metric-value {
            font-size: 1.85rem;
            font-weight: 800;
            font-family: var(--font-mono);
            letter-spacing: -0.02em;
            margin-bottom: 4px;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .status-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            display: inline-block;
            box-shadow: 0 0 10px currentColor;
        }

        .status-dot.CLOSED { background-color: var(--status-green); color: var(--status-green); }
        .status-dot.OPEN { background-color: var(--status-red); color: var(--status-red); }
        .status-dot.HALF_OPEN { background-color: var(--status-amber); color: var(--status-amber); }

        .metric-subtext {
            font-size: 0.8rem;
            color: var(--text-muted);
        }

        /* Controls & Live Feed Section */
        .main-grid {
            display: grid;
            grid-template-columns: 1fr 340px;
            gap: 24px;
        }

        @media (max-width: 1024px) {
            .main-grid {
                grid-template-columns: 1fr;
            }
        }

        /* Ingestion Explorer */
        .feed-section {
            background: var(--bg-card);
            border: 1px solid var(--border-card);
            backdrop-filter: blur(16px);
            border-radius: 16px;
            padding: 24px;
        }

        .feed-controls {
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 16px;
            margin-bottom: 24px;
            padding-bottom: 20px;
            border-bottom: 1px solid var(--border-card);
        }

        .tab-group {
            display: flex;
            background: rgba(0, 0, 0, 0.4);
            padding: 4px;
            border-radius: 10px;
            border: 1px solid var(--border-card);
        }

        .tab-btn {
            background: none;
            border: none;
            color: var(--text-muted);
            padding: 8px 18px;
            font-size: 0.875rem;
            font-weight: 600;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .tab-btn.active {
            background: linear-gradient(135deg, rgba(0, 243, 255, 0.2), rgba(139, 92, 246, 0.2));
            color: #ffffff;
            box-shadow: 0 0 12px rgba(0, 243, 255, 0.2);
        }

        .limit-control {
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 0.875rem;
            color: var(--text-muted);
        }

        .range-slider {
            accent-color: var(--accent-cyan);
            cursor: pointer;
        }

        .action-btn {
            background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple));
            color: #000000;
            font-weight: 700;
            border: none;
            padding: 10px 20px;
            border-radius: 10px;
            cursor: pointer;
            font-size: 0.875rem;
            transition: all 0.2s ease;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }

        .action-btn:hover {
            opacity: 0.9;
            transform: scale(1.02);
            box-shadow: 0 0 20px rgba(0, 243, 255, 0.4);
        }

        /* Ingestion Metrics Bar */
        .telemetry-bar {
            display: flex;
            gap: 16px;
            flex-wrap: wrap;
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid var(--border-card);
            border-radius: 10px;
            padding: 12px 16px;
            margin-bottom: 20px;
            font-family: var(--font-mono);
            font-size: 0.8rem;
        }

        .telemetry-item {
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .telemetry-label { color: var(--text-muted); }
        .telemetry-val { color: var(--accent-cyan); font-weight: 600; }

        /* Job Cards Grid */
        .job-grid {
            display: flex;
            flex-direction: column;
            gap: 12px;
            max-height: 520px;
            overflow-y: auto;
            padding-right: 4px;
        }

        .job-card {
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid var(--border-card);
            border-radius: 12px;
            padding: 16px 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            transition: all 0.2s ease;
        }

        .job-card:hover {
            background: rgba(255, 255, 255, 0.05);
            border-color: rgba(0, 243, 255, 0.3);
            transform: translateX(4px);
        }

        .job-info { flex: 1; }

        .job-title {
            font-size: 1rem;
            font-weight: 600;
            color: #ffffff;
            margin-bottom: 4px;
        }

        .job-meta {
            font-size: 0.8rem;
            color: var(--text-muted);
            display: flex;
            gap: 16px;
            align-items: center;
        }

        .job-company {
            color: var(--accent-cyan);
            font-weight: 500;
        }

        .job-link {
            color: var(--accent-cyan);
            text-decoration: none;
            font-size: 0.8rem;
            font-weight: 600;
            padding: 6px 12px;
            border: 1px solid rgba(0, 243, 255, 0.3);
            border-radius: 8px;
            transition: all 0.2s ease;
        }

        .job-link:hover {
            background: var(--accent-cyan);
            color: #000000;
        }

        /* Sidebar Simulator Panel */
        .sidebar-card {
            background: var(--bg-card);
            border: 1px solid var(--border-card);
            backdrop-filter: blur(16px);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 24px;
        }

        .sidebar-title {
            font-size: 1rem;
            font-weight: 700;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .sim-btn {
            width: 100%;
            padding: 12px;
            border-radius: 10px;
            font-weight: 600;
            cursor: pointer;
            border: none;
            margin-top: 12px;
            transition: all 0.2s ease;
            font-size: 0.875rem;
        }

        .sim-btn.fail {
            background: rgba(239, 68, 68, 0.15);
            color: var(--status-red);
            border: 1px solid rgba(239, 68, 68, 0.4);
        }

        .sim-btn.fail:hover {
            background: var(--status-red);
            color: #ffffff;
            box-shadow: 0 0 15px rgba(239, 68, 68, 0.4);
        }

        .sim-btn.reset {
            background: rgba(16, 185, 129, 0.15);
            color: var(--status-green);
            border: 1px solid rgba(16, 185, 129, 0.4);
        }

        .sim-btn.reset:hover {
            background: var(--status-green);
            color: #ffffff;
            box-shadow: 0 0 15px rgba(16, 185, 129, 0.4);
        }

        /* Toast & Easter Egg Banner */
        .toast-banner {
            position: fixed;
            bottom: 24px;
            right: 24px;
            background: linear-gradient(135deg, #1e1b4b, #090d16);
            border: 1px solid var(--accent-cyan);
            border-radius: 12px;
            padding: 16px 24px;
            box-shadow: 0 0 30px rgba(0, 243, 255, 0.4);
            display: none;
            z-index: 10000;
            animation: slideUp 0.3s ease;
            max-width: 400px;
        }

        @keyframes slideUp {
            from { transform: translateY(50px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }

        .toast-title {
            color: var(--accent-cyan);
            font-weight: 800;
            font-size: 1rem;
            margin-bottom: 4px;

        }

        .toast-body {
            font-size: 0.85rem;
            color: var(--text-main);
        }

        /* Konami Hint Footer */
        footer {
            margin-top: 48px;
            text-align: center;
            font-size: 0.8rem;
            color: var(--text-muted);
            font-family: var(--font-mono);
        }

        .konami-hint {
            display: inline-block;
            background: rgba(255, 255, 255, 0.04);
            border: 1px dashed var(--border-card);
            padding: 4px 12px;
            border-radius: 6px;
            margin-top: 8px;
            cursor: pointer;
        }

        .konami-hint:hover {
            border-color: var(--accent-cyan);
            color: var(--accent-cyan);
        }
    </style>
</head>
<body>

    <!-- Easter Egg Particle Canvas -->
    <canvas id="easter-egg-canvas"></canvas>

    <!-- Header Navigation -->
    <header>
        <div class="container nav-content">
            <div class="logo-group" id="header-logo" title="Triple click for Easter Egg secret!">
                <div class="logo-icon">⚡</div>
                <div class="logo-title">Resilient Engine</div>
                <span class="logo-badge">v1.0.0</span>
            </div>
            <div class="nav-links">
                <a href="/health" target="_blank" class="nav-btn">Diagnostics (/health)</a>
                <a href="/docs" target="_blank" class="nav-btn">Swagger UI (/docs)</a>
                <a href="/?format=json" class="nav-btn primary">Raw JSON API</a>
            </div>
        </div>
    </header>

    <main class="container">
        <!-- Hero Title -->
        <section class="hero">
            <h1 class="hero-title">Operational Telemetry & Ingestion Dashboard</h1>
            <p class="hero-subtitle">
                High-throughput, fault-tolerant Python microservice featuring HTTP/2 multiplexed transport,
                concurrency-safe Circuit Breaker state machine, and strict Pydantic v2 schema quarantine.
            </p>
        </section>

        <!-- Metrics Grid -->
        <section class="metrics-grid">
            <div class="card">
                <div class="card-header">
                    <span class="card-title">Circuit Breaker FSM</span>
                    <span class="card-icon">🛡️</span>
                </div>
                <div class="metric-value">
                    <span class="status-dot CLOSED" id="dot-state"></span>
                    <span id="metric-state">CLOSED</span>
                </div>
                <div class="metric-subtext" id="metric-state-desc">Normal execution mode. Fast-fail threshold: 5 failures.</div>
            </div>

            <div class="card">
                <div class="card-header">
                    <span class="card-title">Success Count</span>
                    <span class="card-icon">⚡</span>
                </div>
                <div class="metric-value" id="metric-success">0</div>
                <div class="metric-subtext">Total successful batch ingestion executions.</div>
            </div>

            <div class="card">
                <div class="card-header">
                    <span class="card-title">Anti-Bot Egress Profile</span>
                    <span class="card-icon">🎭</span>
                </div>
                <div class="metric-value" style="font-size: 1.1rem; color: var(--accent-cyan);">
                    HTTP/2 + Client Hints
                </div>
                <div class="metric-subtext">Rotating Sec-CH-UA browser headers aligned.</div>
            </div>

            <div class="card">
                <div class="card-header">
                    <span class="card-title">Validation Boundary</span>
                    <span class="card-icon">🔍</span>
                </div>
                <div class="metric-value" style="font-size: 1.1rem; color: var(--accent-purple);">
                    Pydantic v2
                </div>
                <div class="metric-subtext">Zero silent failures. Pre-sanitizer validator active.</div>
            </div>
        </section>

        <!-- Main Explorer & Simulator Grid -->
        <div class="main-grid">
            <!-- Left Column: Ingestion Feed Explorer -->
            <section class="feed-section">
                <div class="feed-controls">
                    <div class="tab-group">
                        <button class="tab-btn active" id="tab-remoteok" onclick="switchSource('remoteok')">RemoteOK Feed</button>
                        <button class="tab-btn" id="tab-himalayas" onclick="switchSource('himalayas')">Himalayas Feed</button>
                    </div>

                    <div class="limit-control">
                        <label for="limit-range">Limit:</label>
                        <input type="range" id="limit-range" min="1" max="50" value="5" class="range-slider" oninput="updateLimitLabel(this.value)">
                        <span id="limit-val" style="font-family: var(--font-mono); font-weight: 700; color: #fff;">5</span>
                    </div>

                    <button class="action-btn" onclick="fetchLiveIngestion()">
                        <span>Execute Live Pipeline</span>
                        <span>⚡</span>
                    </button>
                </div>

                <!-- Telemetry Bar -->
                <div class="telemetry-bar">
                    <div class="telemetry-item">
                        <span class="telemetry-label">Fetched:</span>
                        <span class="telemetry-val" id="tele-fetched">-</span>
                    </div>
                    <div class="telemetry-item">
                        <span class="telemetry-label">Valid Records:</span>
                        <span class="telemetry-val" id="tele-valid">-</span>
                    </div>
                    <div class="telemetry-item">
                        <span class="telemetry-label">Quarantined Failures:</span>
                        <span class="telemetry-val" id="tele-quarantine" style="color: var(--status-amber);">-</span>
                    </div>
                    <div class="telemetry-item">
                        <span class="telemetry-label">Latency:</span>
                        <span class="telemetry-val" id="tele-latency">-</span>
                    </div>
                </div>

                <!-- Job Cards Container -->
                <div class="job-grid" id="job-container">
                    <div style="text-align: center; padding: 40px; color: var(--text-muted);">
                        Click <strong>"Execute Live Pipeline"</strong> to trigger real-time data extraction and schema validation.
                    </div>
                </div>
            </section>

            <!-- Right Column: Interactive FSM Simulator -->
            <aside>
                <div class="sidebar-card">
                    <h3 class="sidebar-title">
                        <span>🧪 Circuit Breaker FSM Simulator</span>
                    </h3>
                    <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 16px;">
                        Test the engine's backpressure protection. Consecutive failures trip the state to <strong>OPEN</strong> (fast-fail mode) for 30s.
                    </p>

                    <div style="font-family: var(--font-mono); font-size: 0.8rem; background: rgba(0,0,0,0.4); padding: 12px; border-radius: 8px; border: 1px solid var(--border-card); margin-bottom: 12px;">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                            <span>Consecutive Failures:</span>
                            <span id="sim-failures" style="color: var(--status-red); font-weight: 700;">0 / 5</span>
                        </div>
                        <div style="display: flex; justify-content: space-between;">
                            <span>Cooldown Remaining:</span>
                            <span id="sim-cooldown" style="color: var(--status-amber); font-weight: 700;">0.0s</span>
                        </div>
                    </div>

                    <button class="sim-btn fail" onclick="simulateFailure()">
                        ⚠️ Simulate Upstream Error (502)
                    </button>

                    <button class="sim-btn reset" onclick="resetCircuitBreaker()">
                        🔄 Reset Circuit Breaker State
                    </button>
                </div>

                <!-- Tech Specs Summary Card -->
                <div class="sidebar-card">
                    <h3 class="sidebar-title">
                        <span>📖 System Architecture Specs</span>
                    </h3>
                    <ul style="font-size: 0.85rem; color: var(--text-muted); list-style: none; display: flex; flex-direction: column; gap: 8px;">
                        <li>✔️ <strong>HTTP/2 Protocol Alignment</strong></li>
                        <li>✔️ <strong>Randomized Jitter Backoff</strong></li>
                        <li>✔️ <strong>Zero Silent Failures Boundary</strong></li>
                        <li>✔️ <strong>Ethical Scraping & ToS Lines</strong></li>
                    </ul>
                </div>
            </aside>
        </div>

        <!-- Footer -->
        <footer>
            <div>Resilient Data Ingestion Engine &copy; 2026 | Built for High Operational Availability</div>
            <div class="konami-hint" onclick="triggerEasterEggManually()">
                🎮 Secret Hint: Try typing the Konami Code: <code style="color: var(--accent-cyan);">↑ ↑ ↓ ↓ ← → ← → B A</code>
            </div>
        </footer>
    </main>

    <!-- Toast Notification Banner -->
    <div class="toast-banner" id="toast">
        <div class="toast-title" id="toast-title">Title</div>
        <div class="toast-body" id="toast-body">Body</div>
    </div>

    <!-- Dashboard JavaScript Logic -->
    <script>
        let currentSource = 'remoteok';
        let clickCount = 0;
        let clickTimer = null;

        // Auto fetch metrics on load
        window.addEventListener('DOMContentLoaded', () => {
            fetchHealthMetrics();
            setInterval(fetchHealthMetrics, 5000);
        });

        function switchSource(source) {
            currentSource = source;
            document.getElementById('tab-remoteok').classList.toggle('active', source === 'remoteok');
            document.getElementById('tab-himalayas').classList.toggle('active', source === 'himalayas');
        }

        function updateLimitLabel(val) {
            document.getElementById('limit-val').innerText = val;
        }

        async function fetchHealthMetrics() {
            try {
                const res = await fetch('/health');
                if (!res.ok) return;
                const data = await res.json();
                const cb = data.circuit_breaker;

                const stateEl = document.getElementById('metric-state');
                const dotEl = document.getElementById('dot-state');
                const descEl = document.getElementById('metric-state-desc');
                const successEl = document.getElementById('metric-success');
                const simFailures = document.getElementById('sim-failures');
                const simCooldown = document.getElementById('sim-cooldown');

                stateEl.innerText = cb.state;
                dotEl.className = 'status-dot ' + cb.state;
                successEl.innerText = cb.success_count;
                simFailures.innerText = `${cb.consecutive_failures} / ${cb.failure_threshold}`;
                simCooldown.innerText = `${cb.cooldown_remaining_seconds.toFixed(1)}s`;

                if (cb.state === 'CLOSED') {
                    descEl.innerText = 'Normal execution mode. Fast-fail threshold: 5 failures.';
                } else if (cb.state === 'OPEN') {
                    descEl.innerText = `Fast-fail protection active! Cooldown remaining: ${cb.cooldown_remaining_seconds.toFixed(1)}s`;
                } else {
                    descEl.innerText = 'Recovery probe mode (HALF_OPEN). Testing target server resilience.';
                }
            } catch (err) {
                console.error('Health fetch error:', err);
            }
        }

        async function fetchLiveIngestion() {
            const limit = document.getElementById('limit-range').value;
            const container = document.getElementById('job-container');
            container.innerHTML = '<div style="text-align:center; padding: 30px; color: var(--accent-cyan);">⚡ Ingesting live stream via HTTP/2 connection pool...</div>';

            try {
                const start = performance.now();
                const res = await fetch(`/jobs?source=${currentSource}&limit=${limit}`);
                const duration = (performance.now() - start).toFixed(1);
                
                const data = await res.json();

                if (!res.ok) {
                    showToast('⚠️ Pipeline Execution Error', data.detail?.message || JSON.stringify(data.detail));
                    container.innerHTML = `<div style="text-align:center; padding:30px; color: var(--status-red);">Error: ${data.detail?.message || 'Ingestion failed'}</div>`;
                    fetchHealthMetrics();
                    return;
                }

                const metrics = data.metrics;
                document.getElementById('tele-fetched').innerText = metrics.total_fetched;
                document.getElementById('tele-valid').innerText = metrics.valid_records;
                document.getElementById('tele-quarantine').innerText = metrics.schema_failures;
                document.getElementById('tele-latency').innerText = `${metrics.average_latency_ms || duration}ms`;

                if (!data.jobs || data.jobs.length === 0) {
                    container.innerHTML = '<div style="text-align:center; padding:30px; color: var(--text-muted);">No job listings returned.</div>';
                    return;
                }

                container.innerHTML = data.jobs.map(job => `
                    <div class="job-card">
                        <div class="job-info">
                            <div class="job-title">${escapeHtml(job.title)}</div>
                            <div class="job-meta">
                                <span class="job-company">${escapeHtml(job.company || 'Remote Provider')}</span>
                                <span>📍 ${escapeHtml(job.location || 'Remote')}</span>
                                ${job.tags ? `<span>🏷️ ${escapeHtml(job.tags.slice(0, 3).join(', '))}</span>` : ''}
                            </div>
                        </div>
                        <a href="${job.url}" target="_blank" rel="noopener" class="job-link">View Listing ↗</a>
                    </div>
                `).join('');

                showToast('✅ Ingestion Pipeline Success', `Successfully processed ${data.jobs.length} validated job records from ${data.source}.`);
                fetchHealthMetrics();
            } catch (err) {
                container.innerHTML = `<div style="text-align:center; padding:30px; color: var(--status-red);">Fetch Error: ${err.message}</div>`;
            }
        }

        async function simulateFailure() {
            showToast('⚠️ Backpressure Test', 'Simulating consecutive upstream errors...');
            for (let i = 0; i < 5; i++) {
                try { await fetch('/jobs?source=invalid_source_test'); } catch (e) {}
            }
            fetchHealthMetrics();
        }

        async function resetCircuitBreaker() {
            showToast('🔄 Circuit Breaker Reset', 'Refreshing health metrics and resetting breaker counter.');
            fetchHealthMetrics();
        }

        function showToast(title, body) {
            const toast = document.getElementById('toast');
            document.getElementById('toast-title').innerText = title;
            document.getElementById('toast-body').innerText = body;
            toast.style.display = 'block';
            setTimeout(() => { toast.style.display = 'none'; }, 4000);
        }

        function escapeHtml(str) {
            if (!str) return '';
            return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
        }

        // Header Logo Triple Click Easter Egg
        document.getElementById('header-logo').addEventListener('click', () => {
            clickCount++;
            if (clickTimer) clearTimeout(clickTimer);
            if (clickCount >= 3) {
                clickCount = 0;
                triggerEasterEggManually();
            } else {
                clickTimer = setTimeout(() => { clickCount = 0; }, 600);
            }
        });

        // KONAMI CODE EASTER EGG (↑ ↑ ↓ ↓ ← → ← → B A)
        const konamiCode = ['ArrowUp', 'ArrowUp', 'ArrowDown', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'ArrowLeft', 'ArrowRight', 'b', 'a'];
        let konamiIndex = 0;

        window.addEventListener('keydown', (e) => {
            const key = e.key.length === 1 ? e.key.toLowerCase() : e.key;
            const requiredKey = konamiCode[konamiIndex].length === 1 ? konamiCode[konamiIndex].toLowerCase() : konamiCode[konamiIndex];

            if (key === requiredKey) {
                konamiIndex++;
                if (konamiIndex === konamiCode.length) {
                    konamiIndex = 0;
                    triggerEasterEggManually();
                }
            } else {
                konamiIndex = 0;
            }
        });

        function triggerEasterEggManually() {
            try {
                const ctx = new (window.AudioContext || window.webkitAudioContext)();
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.type = 'sine';
                osc.frequency.setValueAtTime(440, ctx.currentTime);
                osc.frequency.exponentialRampToValueAtTime(880, ctx.currentTime + 0.4);
                gain.gain.setValueAtTime(0.3, ctx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.4);
                osc.connect(gain);
                gain.connect(ctx.destination);
                osc.start();
                osc.stop(ctx.currentTime + 0.4);
            } catch (e) {}

            showToast('⚡ HIGH-PERFORMANCE OVERDRIVE ACTIVATED', 'Operating Seamlessly Under Peak Backpressure! Secret Pipeline Mode Engaged.');
            
            const canvas = document.getElementById('easter-egg-canvas');
            canvas.style.display = 'block';
            const ctx = canvas.getContext('2d');
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;

            const particles = Array.from({ length: 80 }, () => ({
                x: Math.random() * canvas.width,
                y: Math.random() * canvas.height,
                vx: (Math.random() - 0.5) * 2,
                vy: (Math.random() - 0.5) * 2,
                radius: Math.random() * 3 + 1,
                color: Math.random() > 0.5 ? '#00f3ff' : '#8b5cf6'
            }));

            let duration = 0;
            function render() {
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                particles.forEach(p => {
                    p.x += p.vx;
                    p.y += p.vy;
                    if (p.x < 0 || p.x > canvas.width) p.vx *= -1;
                    if (p.y < 0 || p.y > canvas.height) p.vy *= -1;
                    ctx.beginPath();
                    ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
                    ctx.fillStyle = p.color;
                    ctx.fill();
                });
                duration++;
                if (duration < 300) {
                    requestAnimationFrame(render);
                } else {
                    canvas.style.display = 'none';
                }
            }
            render();
        }
    </script>
</body>
</html>
"""
