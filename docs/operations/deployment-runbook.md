# Deployment Runbook (1.2.0-rc3 beta)

## Overview

This runbook is the operator's playbook for the Code-Index-MCP `1.2.0-rc3`
beta release candidate. It is a staged rollout guide, not a GA production
claim. The documented container package is `ghcr.io/viperjuice/code-index-mcp`.
Language and sandbox limitations are tracked in
[`../SUPPORT_MATRIX.md`](../SUPPORT_MATRIX.md).

It covers four stages — **dev → staging → canary → full-prod** — each with measurable
pass criteria, a bake window, rollback triggers, and a rollback procedure.

Execute stages in order. Each stage is a gate: do not advance until all pass criteria
are met and the bake window has elapsed without a rollback trigger firing.

**Related files**:
- Pre-flight validation: [`scripts/preflight_upgrade.sh`](../../scripts/preflight_upgrade.sh)
- Observability verification: [`docs/operations/observability-verification.md`](observability-verification.md)
- Gateway startup: [`docs/operations/gateway-startup-checklist.md`](gateway-startup-checklist.md)
- P18 upgrade notes: [`docs/operations/p18-upgrade.md`](p18-upgrade.md)

---

## Public Alpha Release Gate Checklist

The public alpha release cannot advance until each required job below is green.
Slow, credentialed, cross-platform, benchmark, scan, signing, cleanup, and
publication jobs are informational unless this table explicitly names them as a
blocker.

| Required job | Operator decision | Command/workflow source | Block/fallback behavior |
|---|---|---|---|
| Alpha Gate - Dependency Sync | Dependency metadata and `uv.lock` are in sync before release qualification. | `.github/workflows/lockfile-check.yml` -> `make alpha-dependency-sync` | Blocks release on failure; no fallback for public alpha. |
| Alpha Gate - Format And Lint | Focused formatting and lint checks are clean enough to trust the release branch. | `.github/workflows/ci-cd-pipeline.yml` -> `make alpha-format-lint` | Blocks release on failure; fix code or lint configuration before continuing. |
| Alpha Gate - Unit And Release Smoke | Unit coverage and P22 wheel/stdio release smoke pass on the release candidate. | `.github/workflows/ci-cd-pipeline.yml` -> `make alpha-unit-release-smoke` and `make release-smoke` | Blocks release on failure; no promotion until smoke is green. |
| Alpha Gate - Integration Smoke | Integration and slow smoke coverage still works against the current repository state. | `.github/workflows/ci-cd-pipeline.yml` -> `make alpha-integration-smoke` | Blocks release on failure; quarantine only with a tracked release-blocker decision. |
| Alpha Gate - Docker Build And Smoke | The production container image builds locally in CI and passes the P22 container smoke. | `.github/workflows/container-registry.yml` -> `make release-smoke-container` | Blocks release on failure; scan/sign/publish jobs remain informational until publication. |
| Alpha Gate - Docs Truth | Release metadata, dependency source-of-truth, smoke contract, and customer docs truth checks are current. | `.github/workflows/ci-cd-pipeline.yml` -> `make alpha-docs-truth` | Blocks release on failure; docs must be corrected before release evidence is accepted. |
| Alpha Gate - Required Gates Passed | The required main CI gates completed successfully and are ready to combine with dependency/container gates. | `.github/workflows/ci-cd-pipeline.yml` aggregator job | Blocks release on failure; rerun only after the failed upstream gate is understood. |

## Stages

### Stage: dev

Single-node local environment. Purpose: validate that the build and unit/integration
test suite pass on the release candidate before any shared infrastructure is touched.

#### Pass criteria

| # | Criterion | Command | Expected result |
|---|-----------|---------|----------------|
| 1 | Full test suite passes | `pytest tests/ --no-cov --ignore=tests/real_world` | Exit code 0 |
| 2 | No import errors | `python -c "import mcp_server"` | No traceback |
| 3 | Pre-flight checks pass | `bash scripts/preflight_upgrade.sh` | Exit code 0 |

#### Bake window

None. Dev is ephemeral — once all pass criteria are green, advance immediately.

#### Rollback trigger

Any test failure in the pass criteria commands above.

#### Rollback procedure

```bash
# Identify the last known-good tag
PREV_TAG=$(git describe --tags --abbrev=0 HEAD~1)

git checkout "$PREV_TAG"
pytest tests/ --no-cov
```

---

### Stage: staging

Shared staging environment. Purpose: validate runtime behaviour under realistic load
with full observability. Run for at least 30 minutes after deployment.

#### Pass criteria

All of the following must be true over the 30-minute bake window:

| # | Metric | Source | Threshold |
|---|--------|--------|-----------|
| 1 | HTTP error rate | Prometheus `mcp_http_requests_total{status=~"5.."}` / total | < 1 % |
| 2 | 99th-percentile latency | `histogram_quantile(0.99, mcp_request_duration_seconds_bucket)` | < 500 ms |
| 3 | JSON log parse rate | Log pipeline parse-error counter | ≥ 99 % lines parseable |
| 4 | MCP tool call counter | `mcp_tool_calls_total` | Increments > 0 per every 5-min window |

Verify metrics:

```bash
# Error rate — should be < 0.01 (1 %)
curl -sg "http://prometheus:9090/api/v1/query?query=sum(rate(mcp_http_requests_total{status=~'5..'}[5m]))/sum(rate(mcp_http_requests_total[5m]))" | jq '.data.result[0].value[1]'

# 99p latency — should be < 0.5
curl -sg "http://prometheus:9090/api/v1/query?query=histogram_quantile(0.99,sum(rate(mcp_request_duration_seconds_bucket[5m]))by(le))" | jq '.data.result[0].value[1]'

# Tool call counter delta
curl -sg "http://prometheus:9090/api/v1/query_range?query=mcp_tool_calls_total&start=$(date -d '-5 min' -Iseconds)&end=$(date -Iseconds)&step=60" | jq '.data.result[0].values | length'
```

#### Bake window

**30 minutes** after the new version receives its first request in staging.

#### Rollback trigger

Any single pass criterion breached for **> 2 consecutive 1-minute windows**.

#### Rollback procedure

```bash
# Delete the RC tag and roll back the Kubernetes deployment
git tag --delete v1.2.0-rc3
kubectl rollout undo deploy/mcp-gateway -n staging

# Confirm rollback is live
kubectl rollout status deploy/mcp-gateway -n staging
```

---

### Stage: canary

5 % of production traffic is routed to the new version. Purpose: validate production
behaviour at real scale before full cutover. Run for at least 2 hours.

#### Pass criteria

All of the following must be true over the 2-hour bake window for the canary pods:

| # | Metric | Source | Threshold |
|---|--------|--------|-----------|
| 1 | HTTP error rate (canary pods) | `mcp_http_requests_total{pod=~"mcp-canary.*",status=~"5.."}` / total | < 0.5 % |
| 2 | 99th-percentile latency (canary pods) | `histogram_quantile(0.99, …{pod=~"mcp-canary.*"})` | < 400 ms |
| 3 | JSON log parse rate | Log pipeline (canary log stream) | ≥ 99.5 % lines parseable |

Verify metrics:

```bash
# Error rate for canary pods — should be < 0.005
curl -sg "http://prometheus:9090/api/v1/query?query=sum(rate(mcp_http_requests_total{pod=~'mcp-canary.*',status=~'5..'}[5m]))/sum(rate(mcp_http_requests_total{pod=~'mcp-canary.*'}[5m]))" | jq '.data.result[0].value[1]'

# 99p latency for canary — should be < 0.4
curl -sg "http://prometheus:9090/api/v1/query?query=histogram_quantile(0.99,sum(rate(mcp_request_duration_seconds_bucket{pod=~'mcp-canary.*'}[5m]))by(le))" | jq '.data.result[0].value[1]'
```

#### Bake window

**2 hours** after canary pods first receive traffic.

#### Rollback trigger

Any pass criterion breached for **> 2 minutes sustained**.

#### Rollback procedure

```bash
# Remove canary target from the load balancer
kubectl patch svc mcp-gateway -n prod --type=json \
  -p '[{"op":"remove","path":"/spec/selector/track"}]'

# Scale canary deployment to zero
kubectl scale deploy/mcp-gateway-canary -n prod --replicas=0

# Verify no traffic is hitting canary
kubectl get endpoints mcp-gateway-canary -n prod
```

---

### Stage: full-prod

100 % of production traffic served by v1.2.0. Bake window: 72 hours. During this window
the on-call engineer monitors the dashboards listed under pass criteria.

#### Pass criteria

All of the following must be true continuously over the 72-hour bake window:

| # | Metric | Source | Threshold |
|---|--------|--------|-----------|
| 1 | HTTP error rate | `mcp_http_requests_total{status=~"5.."}` / total | < 0.1 % |
| 2 | 99th-percentile latency | `histogram_quantile(0.99, mcp_request_duration_seconds_bucket)` | < 300 ms |
| 3 | JSON log parse rate | Log pipeline (prod log stream) | 100 % lines parseable |

Verify metrics:

```bash
# Error rate — should be < 0.001 (0.1 %)
curl -sg "http://prometheus:9090/api/v1/query?query=sum(rate(mcp_http_requests_total{status=~'5..'}[5m]))/sum(rate(mcp_http_requests_total[5m]))" | jq '.data.result[0].value[1]'

# 99p latency — should be < 0.3
curl -sg "http://prometheus:9090/api/v1/query?query=histogram_quantile(0.99,sum(rate(mcp_request_duration_seconds_bucket[5m]))by(le))" | jq '.data.result[0].value[1]'
```

#### Bake window

**72 hours** post full-prod rollout.

#### Rollback trigger

Either of:
- Error rate criterion (< 0.1 %) breached for **> 1 minute sustained**, OR
- Any 5xx spike **> 10× the 7-day baseline rate**.

#### Rollback procedure

```bash
# Roll back the production deployment
kubectl rollout undo deploy/mcp-gateway -n prod

# Tag the rollback point for traceability
git tag v1.2.0-rollback "$(git rev-parse HEAD~1)" \
  -m "rollback of v1.2.0 at $(date -Iseconds)"

# Confirm rollback is live
kubectl rollout status deploy/mcp-gateway -n prod

# Verify error rate dropped
curl -sg "http://prometheus:9090/api/v1/query?query=sum(rate(mcp_http_requests_total{status=~'5..'}[5m]))/sum(rate(mcp_http_requests_total[5m]))" | jq '.data.result[0].value[1]'
```

---

## Bake-gate criteria

Summary table for at-a-glance reference:

| Stage | Error rate | 99p latency | Log parse rate | Bake window |
|-------|-----------|------------|---------------|-------------|
| dev | — (test suite) | — | — | None |
| staging | < 1 % | < 500 ms | ≥ 99 % | 30 min |
| canary | < 0.5 % | < 400 ms | ≥ 99.5 % | 2 h |
| full-prod | < 0.1 % | < 300 ms | 100 % | 72 h |

---

## Rollback triggers

Summary of rollback triggers per stage:

| Stage | Trigger |
|-------|---------|
| dev | Any test failure |
| staging | Any criterion breached > 2 consecutive 1-min windows |
| canary | Any criterion breached > 2 min sustained |
| full-prod | Error rate > 0.1 % for > 1 min OR 5xx spike > 10× baseline |

---

## Rollback procedure

See per-stage rollback procedures above. General principle:

1. Revert the Kubernetes deployment (`kubectl rollout undo`).
2. Remove or delete any tags associated with the failed release.
3. Page the on-call engineer and open a postmortem issue.
4. Do **not** re-attempt the rollout until the root cause is identified and fixed.

---

## Preflight checklist (cross-link to scripts/preflight_upgrade.sh)

Before beginning any stage, run the pre-flight validation script:

```bash
bash scripts/preflight_upgrade.sh
```

The script (`scripts/preflight_upgrade.sh`) checks:
- Required environment variables are set (`MCP_ENVIRONMENT`, `MCP_SERVER_HOST`, `MCP_SERVER_PORT`, `MCP_LOG_FORMAT`, `VOYAGEAI_API_KEY`).
- The target service responds to a health probe.
- No conflicting processes are bound to the service port.

Exit code 0 means all checks passed; non-zero means at least one check failed (error
message printed to stderr). Do **not** proceed with a stage if this script exits non-zero.
