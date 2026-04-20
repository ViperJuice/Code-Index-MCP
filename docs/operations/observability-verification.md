# Observability Verification Procedure

This document describes how to verify that a Code-Index-MCP gateway instance emits
structured JSON logs, exposes Prometheus metrics, and redacts secrets from error
responses.  It covers both local staging (docker-compose) and pointing the test suite
at an existing staging gateway.

Cross-links:
- [Gateway Startup Checklist](gateway-startup-checklist.md) — prerequisite env-var setup
- `scripts/preflight_upgrade.sh` — env-file validation before upgrade (exits 0 on pass, 1 on fatal)

---

## 1. Prerequisites

### 1.1 Required environment variables

The gateway must be running with the following environment variables:

```
MCP_ENVIRONMENT=production
MCP_LOG_FORMAT=json
JWT_SECRET_KEY=<minimum 32 random bytes, base64>
DEFAULT_ADMIN_PASSWORD=<strong password>
```

Generate secure values:

```bash
export JWT_SECRET_KEY="$(openssl rand -base64 32)"
export DEFAULT_ADMIN_PASSWORD="$(openssl rand -base64 18)"
```

### 1.2 Gateway port

The gateway HTTP port defaults to `8080` (uvicorn `--port`).  The separate Prometheus
scrape server port is controlled by `PROMETHEUS_PORT` (env var, default `8001`).

---

## 2. Local staging with docker-compose

The infra directory `tests/integration/obs/infra/` ships a minimal Prometheus + Loki
stack.  This is NOT required for the smoke assertions — the compose stack is provided
so operators can visually inspect scraped metrics and ingested logs on a laptop before
promoting to staging.

### 2.1 Start the compose stack

```bash
docker compose -f tests/integration/obs/infra/docker-compose.yml up -d
```

Services started:
- **Prometheus** on port `9091` (scrapes `host.docker.internal:8001`)
- **Loki** on port `3100`

### 2.2 Start the gateway

```bash
export JWT_SECRET_KEY="$(openssl rand -base64 32)"
export DEFAULT_ADMIN_PASSWORD="$(openssl rand -base64 18)"
export MCP_ENVIRONMENT=production
export MCP_LOG_FORMAT=json
export PROMETHEUS_PORT=8001

uvicorn mcp_server.gateway:app \
  --host 127.0.0.1 \
  --port 8080 \
  --log-level warning \
  2> gateway-stderr.log &
GATEWAY_PID=$!
```

The gateway writes JSON-formatted logs to stderr (via `mcp_server/core/logging.py:63`
`StreamHandler(sys.stderr)`).  The `2> gateway-stderr.log` redirect captures them.

### 2.3 Verify JSON log output

Wait for the gateway to become healthy, then check the log file:

```bash
# Poll until healthy (max 45 s)
for i in $(seq 1 45); do
  curl -sf http://127.0.0.1:8080/health && break || sleep 1
done

# Verify every non-empty stderr line parses as JSON
python3 -c "
import json, sys
failures = []
with open('gateway-stderr.log') as f:
    for i, line in enumerate(f, 1):
        line = line.strip()
        if not line:
            continue
        try:
            json.loads(line)
        except json.JSONDecodeError as e:
            failures.append(f'line {i}: {e}  →  {line[:120]}')
if failures:
    print('FAIL: Non-JSON lines found:')
    for f in failures[:5]:
        print(' ', f)
    sys.exit(1)
else:
    print('OK: all lines are valid JSON')
"
```

Expected output: `OK: all lines are valid JSON`

### 2.4 Verify Prometheus metrics endpoint

The `/metrics` endpoint requires ADMIN-level authentication.  Obtain a token first:

```bash
TOKEN=$(curl -sf \
  -H 'Content-Type: application/json' \
  -d "{\"username\":\"admin\",\"password\":\"$DEFAULT_ADMIN_PASSWORD\"}" \
  http://127.0.0.1:8080/api/v1/auth/login \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['access_token'])")

curl -sf \
  -H "Authorization: Bearer $TOKEN" \
  http://127.0.0.1:8080/metrics | head -40
```

Expected: HTTP 200 with Prometheus exposition format beginning with `# HELP`.

Make 5 requests to generate counter increments, then check for `mcp_requests_total`:

```bash
for i in $(seq 1 5); do
  curl -sf -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8080/health > /dev/null
done

curl -sf -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8080/metrics \
  | grep '^mcp_requests_total'
```

Expected output (example): `mcp_requests_total{endpoint="/health",method="GET",status="200"} 5.0`

Additionally confirm the three plan-specified counters appear in `/metrics`:

```bash
curl -sf -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8080/metrics \
  | grep -E '^# (HELP|TYPE) (mcp_tool_calls_total|mcp_rate_limit_sleeps_total|mcp_artifact_errors_by_class_total)\b'
```

Expected: six lines — HELP and TYPE for each of the three counters.  These counters
share a module-level `CollectorRegistry` with the gateway's `PrometheusExporter`, so
any increment (stdio tool calls, artifact provider rate-limit back-offs, artifact
error taxonomy) is directly observable over HTTP scrape.

### 2.5 Verify secret redaction

`SecretRedactionResponseMiddleware` (`mcp_server/security/security_middleware.py:465`)
is registered at module import time in `mcp_server/gateway.py` so it applies to
every 4xx/5xx response regardless of how the app is launched.  The patterns are:

- `Bearer\s+\S+` → `Bearer [REDACTED]`
- `JWT_SECRET_KEY=\S+` → `JWT_SECRET_KEY=[REDACTED]`
- `GITHUB_TOKEN=\S+` → `GITHUB_TOKEN=[REDACTED]`

Verify over HTTP by POSTing a malformed body containing a synthetic token.  The
422 validation error echoes the input dict and the middleware must rewrite the
token before the response leaves the process:

```bash
curl -s -X POST \
  -H 'Content-Type: application/json' \
  -d '{"query":"Bearer SYNTH_ABC123"}' \
  http://127.0.0.1:8080/api/v1/auth/login
```

Expected: HTTP 422 body contains `Bearer [REDACTED]` and does NOT contain the
raw `SYNTH_ABC123` string.

### 2.6 Tear down

```bash
kill $GATEWAY_PID 2>/dev/null || true
docker compose -f tests/integration/obs/infra/docker-compose.yml down
```

---

## 3. Running the automated smoke suite

The smoke suite at `tests/integration/obs/test_obs_smoke.py` automates all three
checks (JSON parse rate, metrics reachability, redaction patterns).  It spawns a
gateway subprocess internally — no external gateway or Docker is needed for the core
assertions.

```bash
pytest tests/integration/obs/test_obs_smoke.py -v --no-cov
```

Note: `--no-cov` is required — the project enforces `--cov-fail-under=35` and the
test coverage instrumentation conflicts with subprocess spawning (`pytest.ini`).

Expected result (Docker absent): all tests PASS or SKIP (compose-dependent portions
are marked `skipif_no_docker`).

Expected result (Docker present):

```
tests/integration/obs/test_obs_smoke.py::test_json_log_parse_rate PASSED
tests/integration/obs/test_obs_smoke.py::test_metrics_endpoint_reachable PASSED
tests/integration/obs/test_obs_smoke.py::test_secret_redaction_via_http PASSED
```

---

## 4. Pointing the suite at an existing staging gateway

Set `GATEWAY_URL` to skip spawning a subprocess and instead target a running gateway:

```bash
export GATEWAY_URL=https://staging.example.internal
export ADMIN_PASSWORD=<staging-admin-password>
pytest tests/integration/obs/test_obs_smoke.py -v --no-cov
```

The `gateway_proc` fixture respects `GATEWAY_URL` when set; the process-management
steps are skipped and the URL is used directly.

---

## 5. Prometheus scrape verification (staging)

After pointing Prometheus at the staging gateway's `/metrics` endpoint, confirm the
scrape target is healthy in the Prometheus UI:

```
http://localhost:9091/targets
```

The `mcp-gateway` job should show `State: UP`.

Query example (PromQL):

```
rate(mcp_requests_total[5m])
```

---

## 6. Preflight validation before upgrade

Always run the preflight script before promoting a new gateway build:

```bash
./scripts/preflight_upgrade.sh /path/to/staging.env
```

Exit code 0 = no fatal errors (warnings printed to stderr are non-blocking).
Exit code 1 = fatal configuration error; do not proceed with upgrade.

See [deployment-runbook.md](deployment-runbook.md) for the full staged bake-gate criteria.
