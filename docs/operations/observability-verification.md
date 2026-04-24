# Observability Verification Procedure

This document defines the GAOPS observability contract for Code-Index-MCP.
It covers the supported local-first verification surface: structured JSON logs,
the authenticated `/metrics` endpoint, response redaction, and the exact
preflight invocation operators use before promotion.

Cross-links:

- [`deployment-runbook.md`](deployment-runbook.md) for rollout and rollback
  decisions
- [`../validation/ga-readiness-checklist.md`](../validation/ga-readiness-checklist.md)
  for the GA boundary
- [`../validation/ga-governance-evidence.md`](../validation/ga-governance-evidence.md)
  and [`../validation/ga-e2e-evidence.md`](../validation/ga-e2e-evidence.md)
  for the upstream governance and release-surface inputs

## 1. Operator posture

- This procedure is local-first and operator-owned.
- `/metrics` is part of the supported deployment surface only when the gateway
  is running with the authenticated admin path enabled.
- Secret values must never be copied into committed evidence. Evidence remains
  either `local`, `CI`, or `metadata-only`.
- The automated smoke at `tests/integration/obs/test_obs_smoke.py` is the
  CI-validated contract for JSON logs, metrics reachability, and secret
  redaction.

## 2. Manual verification steps

### 2.1 Start the gateway

Run the gateway in a local or staging environment with operator-provided env
values. The exact secret values stay out of the evidence artifact.

### 2.2 Verify JSON logs

Confirm that stderr log lines emitted by the gateway parse as JSON and that the
service becomes healthy.

### 2.3 Verify the `/metrics` endpoint

The `/metrics endpoint requires ADMIN-level authentication`. Obtain an admin
token through the login route, then query `/metrics` with:

```text
Authorization: Bearer <token>
```

Check for:

- HTTP 200 from `/metrics`
- expected HELP/TYPE lines for the exported counters
- request counters incrementing after live HTTP calls

### 2.4 Verify response redaction

Send a malformed request containing a synthetic bearer token and confirm the
response body contains the redacted form rather than the raw secret-shaped
string.

## 3. Automated verification

Run the CI-validated smoke directly:

```bash
uv run pytest tests/integration/obs/test_obs_smoke.py -v --no-cov
```

The smoke covers JSON log parsing, `/metrics` reachability, and redaction
patterns. If Docker or another local dependency is absent, the suite may skip
environment-specific parts while still preserving the contract for the core
gateway checks.

## 4. Evidence handling

Use exactly one evidence mode per observation:

- `local`: a human operator ran the procedure in a real environment
- `CI`: the automated smoke or equivalent test-backed flow passed
- `metadata-only`: the operator recorded non-secret posture, such as the
  selected env file path, the presence of required settings, or the reason a
  check was deferred

Record those decisions in `docs/validation/ga-operations-evidence.md`.

## 5. Preflight validation before upgrade

Always run the preflight script before promoting a new gateway build:

```bash
./scripts/preflight_upgrade.sh /path/to/staging.env
```

Exit code 0 means no fatal errors. Exit code 1 means fatal configuration drift;
do not proceed. Warning-only output is metadata-only evidence and does not by
itself qualify the environment for promotion.

See [`deployment-runbook.md`](deployment-runbook.md) for the full staged
qualification, rollback, index rebuild, incident response, and support triage
contract.
