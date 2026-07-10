---
phase_loop_plan_version: 1
phase: AUTHBOUND
roadmap: specs/phase-plans-v10.md
roadmap_sha256: 7741ebf13c8598c35f57eac09bfeccf8bbbec7e202d2709526256c1c99b8966e
---
# AUTHBOUND: FastAPI Authentication Boundary

## Context

AUTHBOUND is Phase 1 in `specs/phase-plans-v10.md`. The canonical `.phase-loop/state.json` reports `AUTHBOUND` as the current unplanned phase, no pre-existing dirty paths, branch `codex/comprehensive-hardening-v10`, and roadmap SHA-256 `7741ebf13c8598c35f57eac09bfeccf8bbbec7e202d2709526256c1c99b8966e`. Legacy `.codex/phase-loop/` files are compatibility artifacts only and are not used to supersede canonical `.phase-loop/` state.

Planning observations:

- The concrete defect is in `mcp_server/security/security_middleware.py`: `get_current_user()` falls back to any non-empty `Authorization: Bearer ...` header, synthesizes `fallback-user`, grants `UserRole.ADMIN`, and grants `list(Permission)` when middleware did not populate `request.state.token_data`.
- `mcp_server/gateway.py` currently configures most of the security stack inside `startup_event()` and catches Starlette's `Cannot add middleware after an application has started` runtime error as a warning, which can leave dependency-level fallback auth as the effective protected-route behavior.
- `tests/conftest.py` currently creates the shared API `TestClient` with `Authorization: Bearer test-token`, explicitly depending on the fallback auth shortcut. AUTHBOUND must replace that with validated-token fixtures or unauthenticated clients that assert refusal.
- Existing route coverage in `tests/security/test_route_auth_coverage.py`, metrics coverage in `tests/security/test_metrics_auth.py`, and MCPAUTH boundary coverage are useful but not enough for forged signatures, wrong or none algorithm, missing subject, unknown user, expiry, OpenAPI auth metadata, low-privilege mutations, and browser-visible unauthorized behavior.
- The roadmap names `mcp_server/security/authentication.py`, but this checkout's implemented auth manager is `mcp_server/security/auth_manager.py`; AUTHBOUND should update the implemented module rather than adding a parallel authentication stack.

Planning boundary:

- AUTHBOUND may change FastAPI gateway security wiring, authentication and authorization dependencies, token verification hardening, test fixtures, route inventory tests, protected endpoint regressions, OpenAPI/browser smoke coverage, and metadata-only security docs/evidence.
- AUTHBOUND must not redesign STDIO `MCP_CLIENT_SECRET` handshake behavior, add an external identity provider, weaken existing permission dependencies, delete valid tests to get green, or broaden into repository selection, readiness recovery, semantic status, release, or plugin lifecycle fixes.

## Interface Freeze Gates

- [ ] IF-0-AUTHBOUND-1 - Validated JWT-only protected routes: every FastAPI route outside the explicit public allowlist rejects missing, malformed, forged, expired, wrong-algorithm, none-algorithm, missing-subject, unknown-user, inactive-user, or insufficient-permission tokens with `401` or `403`; no route or dependency creates `fallback-user`, grants `UserRole.ADMIN`, or grants every `Permission` from header presence; valid tokens expose only the persisted active user's declared role and permissions.
- [ ] IF-0-AUTHBOUND-2 - Pre-startup security wiring: FastAPI security middleware, dependencies, OpenAPI auth metadata, and required JWT/admin configuration are installed before application startup or fail closed; late middleware registration errors are not swallowed as success; missing or invalid JWT signing configuration never selects a permissive mode; `/docs`, `/redoc`, `/openapi.json`, `/health`, `/ready`, and `/liveness` remain the only public admin-surface routes unless explicitly listed in the route inventory test.

## Spec Closeout Plan

- schema: `spec_delta_closeout.v1`
- decision: `canonical_spec_update`
- target surfaces: `mcp_server/security/auth_manager.py`, `mcp_server/security/security_middleware.py`, `mcp_server/gateway.py`, `tests/conftest.py`, `tests/security/test_auth_boundary.py`, `tests/security/test_auth_startup_wiring.py`, `tests/security/test_startup_config_validation.py`, `tests/security/test_route_auth_coverage.py`, `tests/security/test_metrics_auth.py`, `tests/security/test_mcpauth_boundary.py`, `tests/security/test_openapi_auth_metadata.py`, `tests/test_gateway.py`, `tests/test_gateway_auth_boundary.py`, `scripts/admin_browser_smoke.py`, `docs/security/auth-boundary.md`, `docs/operations/gateway-startup-checklist.md`, `docs/validation/mcp-auth-boundary.md`, `docs/status/authbound-verification.md`
- evidence paths: `docs/status/authbound-verification.md`, `tests/security/test_auth_boundary.py`, `tests/security/test_auth_startup_wiring.py`, `tests/security/test_route_auth_coverage.py`, `tests/security/test_openapi_auth_metadata.py`, `scripts/admin_browser_smoke.py`, runner-stamped `AUTHBOUND` `verification.json`
- redaction posture: `metadata_only`
- downstream handling: `none`

## Lane Index & Dependencies

- SL-0 - Core JWT dependency boundary and shared API fixtures; Depends on: (none); Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Gateway startup security wiring; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4; Parallel-safe: no
- SL-2 - Protected route, OpenAPI, and browser evidence; Depends on: SL-0, SL-1; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-3 - Security documentation reducer; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4; Parallel-safe: no
- SL-4 - AUTHBOUND acceptance verification and metadata closeout; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: AUTHBOUND acceptance; Parallel-safe: no

Lane DAG:

```text
SL-0 -> SL-1 -> SL-2 -> SL-3 -> SL-4 -> AUTHBOUND acceptance
```

## Lanes

### SL-0 - Core JWT Dependency Boundary And Shared API Fixtures

- **Scope**: Remove the synthetic-admin dependency fallback, harden JWT decoding, and replace shared API test clients that depend on arbitrary bearer acceptance.
- **Owned files**: `mcp_server/security/auth_manager.py`, `mcp_server/security/security_middleware.py`, `tests/conftest.py`, `tests/security/test_auth_boundary.py`
- **Interfaces provided**: `get_current_user()` requires middleware-populated validated `TokenData`; `get_current_active_user()` materializes only validated active users; `AuthManager.verify_token()` returns `None` or a typed auth failure for malformed claims instead of raising or trusting forged claims; shared `TestClient` fixtures expose explicit unauthenticated and validated-token modes.
- **Interfaces consumed**: existing `AuthManager`, `TokenData`, `User`, `UserRole`, `Permission`, `SecurityConfig`, existing FastAPI dependency helpers, existing password and token creation behavior, and roadmap IF-0-AUTHBOUND-1.
- **Parallel-safe**: no
- **Tasks**:
  - test: Add `tests/security/test_auth_boundary.py` reproducing the current bug: a route protected by `Depends(require_role(UserRole.ADMIN))` or `Depends(require_permission(Permission.ADMIN))` must reject arbitrary non-empty bearer tokens when `request.state.token_data` is absent, and must not create `fallback-user` or `permissions=list(Permission)`.
  - test: Cover missing bearer, malformed bearer, forged signature, wrong algorithm, none algorithm, expired token, missing subject/user id, unknown user, inactive user, invalid role, invalid permission claim, and a low-privilege token attempting an admin or mutation endpoint.
  - test: Update shared fixture expectations so legacy tests cannot pass only because `tests/conftest.py` sends `Authorization: Bearer test-token`; tests that need access must request a real token fixture tied to an `AuthManager` user.
  - impl: Remove the fallback-token construction path from `get_current_user()` and make missing `request.state.token_data` a fail-closed `401`.
  - impl: Harden `AuthManager.verify_token()` around required claims, algorithm restrictions, expired signatures, invalid token types, unknown users, inactive users, invalid roles, and invalid permissions while keeping successful token creation behavior compatible.
  - impl: Keep role and permission checks separate: valid low-privilege users authenticate successfully but receive `403` for insufficient protected operations.
  - verify: `uv run pytest tests/security/test_auth_boundary.py -q --no-cov`
  - verify: `rg -n "fallback-user|username=\"fallback\"|list\(Permission\)|Using fallback auth path|Bearer test-token" mcp_server/security tests/conftest.py`

### SL-1 - Gateway Startup Security Wiring

- **Scope**: Make the real gateway install or validate security before startup so late middleware registration cannot be logged as a successful protected configuration.
- **Owned files**: `mcp_server/gateway.py`, `tests/security/test_auth_startup_wiring.py`, `tests/security/test_startup_config_validation.py`
- **Interfaces provided**: pre-startup or fail-closed gateway security installation; startup refusal for missing/invalid JWT/admin config; no swallowed late-registration success path for IF-0-AUTHBOUND-2.
- **Interfaces consumed**: SL-0 validated dependency behavior; existing `SecurityMiddlewareStack`, `SecretRedactionResponseMiddleware`, `_parse_cors_origins_from_env()`, `validate_production_config()`, `WEAK_CREDENTIAL_BLOCKLIST`, `TokenValidator.validate_scopes()`, and current gateway startup/shutdown lifecycle.
- **Parallel-safe**: no
- **Tasks**:
  - test: Add `tests/security/test_auth_startup_wiring.py` to prove the imported gateway app has the required security middleware/dependency posture before serving protected routes and that a simulated late middleware registration error is not swallowed as a green startup.
  - test: Extend `tests/security/test_startup_config_validation.py` to cover missing `JWT_SECRET_KEY`, invalid/too-short JWT secret, weak production signing config, missing `DEFAULT_ADMIN_PASSWORD`, and blocklisted admin password as fail-closed startup or protected-route-unavailable behavior.
  - test: Prove `SecretRedactionResponseMiddleware` remains available on startup failure paths without requiring the rest of the security stack to register late.
  - impl: Move security-stack construction or security-dependency binding out of the late startup-only success path, or make startup abort when middleware cannot be added before the app starts.
  - impl: Preserve public health/docs routes and the existing admin user creation semantics, but do not allow missing signing/admin config to choose permissive mode.
  - impl: Keep STDIO `MCP_CLIENT_SECRET` handshake code untouched; this lane only affects FastAPI admin/debug startup security.
  - verify: `uv run pytest tests/security/test_auth_startup_wiring.py tests/security/test_startup_config_validation.py -q --no-cov`
  - verify: `rg -n "Cannot add middleware after an application has started|Skipping late middleware registration|JWT_SECRET_KEY env var must be set|DEFAULT_ADMIN_PASSWORD env var must be set|SecurityMiddlewareStack" mcp_server/gateway.py tests/security/test_auth_startup_wiring.py tests/security/test_startup_config_validation.py`

### SL-2 - Protected Route, OpenAPI, And Browser Evidence

- **Scope**: Expand API-level regressions so every protected FastAPI route, OpenAPI auth metadata, and a browser-visible unauthorized operation prove the fixed boundary.
- **Owned files**: `tests/security/test_route_auth_coverage.py`, `tests/security/test_metrics_auth.py`, `tests/security/test_mcpauth_boundary.py`, `tests/security/test_openapi_auth_metadata.py`, `tests/test_gateway.py`, `tests/test_gateway_auth_boundary.py`, `scripts/admin_browser_smoke.py`
- **Interfaces provided**: route inventory public allowlist; protected read/mutation regression coverage; OpenAPI security metadata assertions; browser smoke command for `/docs` plus a visible unauthorized protected operation.
- **Interfaces consumed**: SL-0 real-token fixtures and fail-closed dependencies; SL-1 gateway startup wiring; existing FastAPI routes in `mcp_server/gateway.py`; existing metrics, reindex, cache/config, plugin administration, search, symbol, status, and graph endpoints.
- **Parallel-safe**: no
- **Tasks**:
  - test: Update `tests/security/test_route_auth_coverage.py` so it walks every `APIRoute`, applies one explicit public allowlist, and requires all other routes to reject unauthenticated requests with `401` or `403` before request-body validation or service-readiness shortcuts can mask auth bypass.
  - test: Extend metrics and MCPAUTH boundary tests so `/metrics` requires admin, protected read endpoints accept a valid read/admin token, and mutation endpoints such as `/reindex`, cache/config mutations, and plugin administration reject readonly or user tokens with `403`.
  - test: Add `tests/security/test_openapi_auth_metadata.py` to assert OpenAPI declares bearer/JWT security on protected operations while `/docs`, `/redoc`, `/openapi.json`, health, readiness, and liveness stay public.
  - test: Update `tests/test_gateway.py` or add `tests/test_gateway_auth_boundary.py` so gateway endpoint tests use validated token fixtures instead of arbitrary bearer headers and include invalid-token refusal for representative read and mutation endpoints.
  - impl: Add `scripts/admin_browser_smoke.py` as a metadata-only browser/API smoke that starts or targets the FastAPI app, confirms `/docs` renders, and records a visible unauthorized response for a protected operation without printing token values or secrets.
  - impl: Keep the public route allowlist small and explicit; adding a new public route requires changing the inventory test and docs.
  - verify: `uv run pytest tests/security/test_route_auth_coverage.py tests/security/test_metrics_auth.py tests/security/test_mcpauth_boundary.py tests/security/test_openapi_auth_metadata.py tests/test_gateway.py tests/test_gateway_auth_boundary.py -q --no-cov`
  - verify: `uv run python scripts/admin_browser_smoke.py --base-url http://127.0.0.1:8000 --docs-path /docs --protected-path /metrics --expect-unauthorized`

### SL-3 - Security Documentation Reducer

- **Scope**: Reduce the implementation and API evidence into operator-facing FastAPI auth docs without changing the STDIO auth story.
- **Owned files**: `docs/security/auth-boundary.md`, `docs/operations/gateway-startup-checklist.md`, `docs/validation/mcp-auth-boundary.md`, `tests/docs/test_authbound_security_docs.py`
- **Interfaces provided**: canonical FastAPI authentication contract documentation; updated startup checklist; preserved MCPAUTH STDIO-versus-admin-HTTP boundary.
- **Interfaces consumed**: SL-0 validated JWT dependency contract; SL-1 startup wiring; SL-2 route, OpenAPI, and browser evidence; existing `docs/validation/mcp-auth-boundary.md`; roadmap spec closeout policy.
- **Parallel-safe**: no
- **Tasks**:
  - test: Add `tests/docs/test_authbound_security_docs.py` to require docs to state that FastAPI protected routes accept only validated JWTs, arbitrary bearer headers are rejected, missing/invalid signing config fails closed, and public routes are explicitly allowlisted.
  - test: Require docs to preserve the existing STDIO `MCP_CLIENT_SECRET` handshake distinction and not imply a remote identity-provider integration was added.
  - impl: Add `docs/security/auth-boundary.md` with the FastAPI bearer/JWT contract, public route allowlist, startup-failure behavior, endpoint classes that require admin versus read/execute permissions, and redaction posture.
  - impl: Update `docs/operations/gateway-startup-checklist.md` so startup validation and smoke steps match the fixed fail-closed behavior and do not present placeholder arbitrary bearer tokens as valid proof.
  - impl: Update `docs/validation/mcp-auth-boundary.md` only where needed to say AUTHBOUND hardened the FastAPI admin/debug JWT boundary while leaving STDIO handshake behavior separate.
  - verify: `uv run pytest tests/docs/test_authbound_security_docs.py -q --no-cov`
  - verify: `rg -n "validated JWT|arbitrary bearer|fallback-user|public allowlist|MCP_CLIENT_SECRET|admin/debug|fail closed|/docs|/metrics" docs/security/auth-boundary.md docs/operations/gateway-startup-checklist.md docs/validation/mcp-auth-boundary.md tests/docs/test_authbound_security_docs.py`

### SL-4 - AUTHBOUND Acceptance Verification And Metadata Closeout

- **Scope**: Run the targeted AUTHBOUND suite, compare against the known-failure baseline, and write a metadata-only closeout evidence record for downstream phases.
- **Owned files**: `docs/status/authbound-verification.md`, `tests/docs/test_authbound_verification_record.py`
- **Interfaces provided**: AUTHBOUND verification evidence; runner-stamped inputs for AUTHBOUND `verification.json`; no-new-failures baseline comparison for downstream phase entry.
- **Interfaces consumed**: SL-0 through SL-3 code, tests, browser smoke, docs, and verification outputs; roadmap requirement that every behavioral phase captures a failing-at-base reproduction and the same regression passing after implementation; known red baseline policy until QUALITY removes it.
- **Parallel-safe**: no
- **Tasks**:
  - test: Add `tests/docs/test_authbound_verification_record.py` to require `docs/status/authbound-verification.md` to include the roadmap hash, IF gates, failing-at-base reproduction command, targeted passing commands, browser smoke result, auth diff summary, no-new-failures baseline comparison, redaction posture, and non-goals.
  - impl: Write `docs/status/authbound-verification.md` as metadata-only evidence. Summarize command names, pass/fail status, and changed surfaces; do not include raw tokens, JWTs, passwords, or secret values.
  - impl: If targeted tests pass but the baseline comparison finds new failures in phase-owned surfaces, keep closeout blocked with `blocker_class=verification_evidence_missing` or the runner's equivalent frozen class rather than claiming acceptance.
  - verify: `uv run pytest tests/docs/test_authbound_verification_record.py tests/docs/test_authbound_security_docs.py -q --no-cov`
  - verify: `uv run pytest tests/security/test_auth_boundary.py tests/security/test_auth_startup_wiring.py tests/security/test_route_auth_coverage.py tests/security/test_metrics_auth.py tests/security/test_mcpauth_boundary.py tests/security/test_openapi_auth_metadata.py tests/test_gateway.py tests/test_gateway_auth_boundary.py -q --no-cov`
  - verify: `uv run python scripts/admin_browser_smoke.py --base-url http://127.0.0.1:8000 --docs-path /docs --protected-path /metrics --expect-unauthorized`
  - verify: `phase-loop validate-roadmap specs/phase-plans-v10.md`
  - verify: `git diff --check`
  - verify: `git status --short -- mcp_server/security/auth_manager.py mcp_server/security/security_middleware.py mcp_server/gateway.py tests/conftest.py tests/security/test_auth_boundary.py tests/security/test_auth_startup_wiring.py tests/security/test_startup_config_validation.py tests/security/test_route_auth_coverage.py tests/security/test_metrics_auth.py tests/security/test_mcpauth_boundary.py tests/security/test_openapi_auth_metadata.py tests/test_gateway.py tests/test_gateway_auth_boundary.py scripts/admin_browser_smoke.py docs/security/auth-boundary.md docs/operations/gateway-startup-checklist.md docs/validation/mcp-auth-boundary.md docs/status/authbound-verification.md tests/docs/test_authbound_security_docs.py tests/docs/test_authbound_verification_record.py plans/phase-plan-v10-AUTHBOUND.md`

## Execution Policy

- work-unit defaults: work-unit=`lane_execute`, effort=`medium`, unsupported=`inherit_default`, inherit-default=`true`
- SL-3: executor=`codex`, effort=`medium`, work-unit=`phase_reducer`, unsupported=`inherit_default`, inherit-default=`true`
- SL-4: executor=`codex`, effort=`medium`, work-unit=`phase_verify`, unsupported=`inherit_default`, inherit-default=`true`

## Execution Notes

- Use `uv sync --locked --extra dev --extra semantic` before targeted test execution. If the local default interpreter selects a lock-incompatible CPython, use the repo-supported CPython 3.12 environment rather than changing `uv.lock` in AUTHBOUND.
- Preserve the STDIO `MCP_CLIENT_SECRET` handshake contract. AUTHBOUND fixes the FastAPI admin/debug JWT boundary only.
- Keep authentication and authorization separate: invalid or missing JWTs are `401`; valid users without required role/permission are `403`.
- Treat `/docs`, `/redoc`, `/openapi.json`, `/health`, `/ready`, and `/liveness` as the initial public allowlist. Any additional public route must be justified in the route inventory test and docs.
- Do not print raw JWTs, admin passwords, bearer values, 1Password values, local env values, or secret payloads in docs, smoke output, or closeout evidence.
- The failing-at-base reproduction for finding F1 is `uv run pytest tests/security/test_auth_boundary.py -q --no-cov` before SL-0 implementation; the same command must pass after implementation.
- Until QUALITY removes the known red baseline, run the targeted AUTHBOUND suite plus a no-new-failures baseline comparison and record both in `docs/status/authbound-verification.md` and the runner-stamped AUTHBOUND `verification.json`.

## Verification

`automation.suite_command`: `uv run pytest tests/security/test_auth_boundary.py tests/security/test_auth_startup_wiring.py tests/security/test_route_auth_coverage.py tests/security/test_metrics_auth.py tests/security/test_mcpauth_boundary.py tests/security/test_openapi_auth_metadata.py tests/test_gateway.py tests/test_gateway_auth_boundary.py tests/docs/test_authbound_security_docs.py tests/docs/test_authbound_verification_record.py -q --no-cov`

Plan artifact creation is complete once this artifact is written and staged. Do not execute the commands below during `codex-plan-phase`; run them during `codex-execute-phase` or manual AUTHBOUND execution.

Lane-specific verification commands are listed under each lane. Whole-phase verification after AUTHBOUND changes:

```bash
uv sync --locked --extra dev --extra semantic
uv run pytest tests/security/test_auth_boundary.py -q --no-cov
uv run pytest tests/security/test_auth_startup_wiring.py tests/security/test_startup_config_validation.py -q --no-cov
uv run pytest tests/security/test_route_auth_coverage.py tests/security/test_metrics_auth.py tests/security/test_mcpauth_boundary.py tests/security/test_openapi_auth_metadata.py tests/test_gateway.py tests/test_gateway_auth_boundary.py -q --no-cov
uv run pytest tests/docs/test_authbound_security_docs.py tests/docs/test_authbound_verification_record.py -q --no-cov
uv run python scripts/admin_browser_smoke.py --base-url http://127.0.0.1:8000 --docs-path /docs --protected-path /metrics --expect-unauthorized
phase-loop validate-roadmap specs/phase-plans-v10.md
git diff --check
git status --short -- \
  mcp_server/security/auth_manager.py \
  mcp_server/security/security_middleware.py \
  mcp_server/gateway.py \
  tests/conftest.py \
  tests/security/test_auth_boundary.py \
  tests/security/test_auth_startup_wiring.py \
  tests/security/test_startup_config_validation.py \
  tests/security/test_route_auth_coverage.py \
  tests/security/test_metrics_auth.py \
  tests/security/test_mcpauth_boundary.py \
  tests/security/test_openapi_auth_metadata.py \
  tests/test_gateway.py \
  tests/test_gateway_auth_boundary.py \
  scripts/admin_browser_smoke.py \
  docs/security/auth-boundary.md \
  docs/operations/gateway-startup-checklist.md \
  docs/validation/mcp-auth-boundary.md \
  docs/status/authbound-verification.md \
  tests/docs/test_authbound_security_docs.py \
  tests/docs/test_authbound_verification_record.py \
  plans/phase-plan-v10-AUTHBOUND.md
```

Full baseline comparison when execution time allows:

```bash
uv run pytest -q --no-cov --benchmark-skip
```

## Acceptance Criteria

- [ ] Every FastAPI protected route outside the explicit public allowlist rejects missing, malformed, invalid-signature, expired, wrong-algorithm, none-algorithm, missing-subject, unknown-user, inactive-user, and insufficient-permission tokens with `401` or `403` as appropriate.
- [ ] No code path in `mcp_server/security/auth_manager.py`, `mcp_server/security/security_middleware.py`, `mcp_server/gateway.py`, or `tests/conftest.py` creates `fallback-user`, grants `UserRole.ADMIN`, grants every `Permission`, or relies on `Authorization: Bearer test-token` as authentication.
- [ ] Valid JWTs receive only the persisted user's declared role and permissions; low-privilege valid users authenticate but cannot perform admin or mutation operations.
- [ ] Security middleware or equivalent validated-token dependencies are installed before startup or fail closed; late Starlette middleware registration errors cannot be logged as successful security setup.
- [ ] Missing or invalid JWT signing configuration and missing or blocklisted default admin password fail startup or make protected routes unavailable; they never select a permissive mode.
- [ ] Route inventory coverage proves all non-public FastAPI routes reject unauthenticated requests, including protected read endpoints and mutation/admin endpoints such as `/metrics`, `/reindex`, cache/config mutations, plugin administration, and graph/search administration.
- [ ] OpenAPI metadata advertises bearer/JWT auth for protected operations while `/docs` renders publicly, and `scripts/admin_browser_smoke.py` records a visible unauthorized response for a protected operation without leaking token values.
- [ ] `docs/security/auth-boundary.md`, `docs/operations/gateway-startup-checklist.md`, `docs/validation/mcp-auth-boundary.md`, and `docs/status/authbound-verification.md` record the fail-closed FastAPI auth contract, public allowlist, verification commands, auth diff, browser smoke result, redaction posture, and non-goals.
- [ ] Targeted AUTHBOUND tests, docs tests, browser smoke, `phase-loop validate-roadmap specs/phase-plans-v10.md`, `git diff --check`, and the no-new-failures baseline comparison are recorded in metadata-only closeout evidence.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v10-AUTHBOUND.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /mnt/HC_Volume_105438154/worktrees/Code-Index-MCP-comprehensive-hardening/plans/phase-plan-v10-AUTHBOUND.md
  artifact_state: staged
```
