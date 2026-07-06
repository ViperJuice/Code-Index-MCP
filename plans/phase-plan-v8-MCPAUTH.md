---
phase_loop_plan_version: 1
phase: MCPAUTH
roadmap: specs/phase-plans-v8.md
roadmap_sha256: 25aa1501b52e5038cbcc0356638d2a5de5aaaea75c32e21c03de8a1db6a99a11
---
# MCPAUTH: Authorization And Secret Boundary Modernization

## Context

MCPAUTH is the v8 phase that freezes this repo's actual authentication
boundary after the transport decision. In this checkout, that boundary is
already split between a local STDIO handshake secret and a separate FastAPI
admin/debug bearer-token stack, but the split is not yet documented or tested
cleanly enough for the current roadmap contract.

Current repo state gathered during planning:

- `specs/phase-plans-v8.md` is the active tracked roadmap with the requested
  `roadmap_sha256`. `MCPTRANSPORT` is now complete under the canonical
  `.phase-loop/` ledger, and `MCPAUTH` is the current downstream phase.
  This artifact was first written while `MCPTRANSPORT` was still pending, so
  the stale downstream block at the end of the file must not be treated as the
  current DAG state.
- `docs/validation/mcp-transport-decision.md` already records the current v8
  transport decision: remote MCP is deferred, `mcp-index stdio` remains the
  supported MCP client transport, and the existing FastAPI gateway remains an
  admin/debug HTTP surface rather than a Streamable HTTP MCP endpoint.
- `mcp_server/cli/handshake.py` already implements `HandshakeGate` around the
  environment-backed `MCP_CLIENT_SECRET`, and `mcp_server/cli/stdio_runner.py`
  already exposes a `handshake` tool for local STDIO sessions.
- The highest-leverage hardening gap is concrete, not theoretical:
  `mcp_server/cli/stdio_runner.py:1259-1270` says the gate check happens
  before logging to avoid secret leakage, but the next line still logs
  `args={arguments}` for every tool call, including the `handshake` tool's raw
  `secret`.
- The HTTP admin surface already has a response redaction middleware in
  `mcp_server/security/security_middleware.py`, but its current patterns cover
  `Bearer`, `JWT_SECRET_KEY`, and `GITHUB_TOKEN` only. There is no coverage
  yet for `MCP_CLIENT_SECRET`, and no test that ties STDIO handshake failures
  to the repo's broader no-secret-leak contract.
- Existing tests are useful but fragmented: `tests/test_handshake.py` covers
  `HandshakeGate`, `tests/test_secret_redaction.py` covers HTTP response-body
  redaction, and `tests/security/test_metrics_auth.py` plus
  `tests/security/test_route_auth_coverage.py` cover the admin/debug bearer
  auth surface. None of them currently freeze the intended separation between
  local STDIO auth, admin HTTP auth, and deferred remote MCP auth.
- User-facing docs already describe STDIO as the primary MCP surface and the
  FastAPI gateway as secondary/admin-debug infrastructure, but they do not yet
  explicitly say that `MCP_CLIENT_SECRET` is a local STDIO guard rather than a
  spec-aligned remote authorization design, and they do not yet say that no
  remote MCP auth is implemented while remote MCP itself is deferred.

Practical planning boundary:

- MCPAUTH may harden the local handshake path, broaden secret-redaction
  coverage where the current implementation can leak auth material, preserve
  the existing FastAPI admin/debug bearer auth surface, and make the current
  remote-auth deferment explicit in docs and tests.
- MCPAUTH must not invent a remote MCP transport, must not add OAuth/OIDC or
  protected-resource flows for an endpoint that does not exist, must not add a
  new secret storage system, and must not broaden into unrelated security,
  release, or task-execution work.

## Interface Freeze Gates

- [ ] IF-0-MCPAUTH-1 - Local STDIO auth contract:
      `MCP_CLIENT_SECRET` remains an environment-backed local STDIO guard
      implemented through `HandshakeGate` and the `handshake` tool, and
      `call_tool()` must not log or echo the raw handshake secret while
      processing that tool.
- [ ] IF-0-MCPAUTH-2 - Secret-leak prevention contract:
      handshake failures, startup warnings, and admin/debug authorization
      failures fail closed without exposing raw secret values; response-body
      redaction covers `MCP_CLIENT_SECRET=` alongside the existing bearer/JWT
      and GitHub token patterns when those values appear in 4xx/5xx surfaces.
- [ ] IF-0-MCPAUTH-3 - Auth-boundary documentation contract:
      README, MCP configuration guidance, and validation docs explicitly
      distinguish local STDIO handshake auth from FastAPI admin/debug bearer
      auth and explicitly state that no remote MCP authorization is implemented
      while `docs/validation/mcp-transport-decision.md` continues to defer
      remote MCP.
- [ ] IF-0-MCPAUTH-4 - Regression coverage contract:
      tests prove handshake success/failure behavior, log redaction, response
      redaction, and admin/debug authorization failures without widening the
      supported auth story beyond the current local-STDIO-plus-admin-HTTP
      boundary.

## Lane Index & Dependencies

- SL-0 - STDIO handshake contract and log-safety hardening; Depends on: (none); Blocks: SL-2; Parallel-safe: yes
- SL-1 - HTTP/admin auth redaction coverage and boundary-preservation regressions; Depends on: (none); Blocks: SL-2; Parallel-safe: yes
- SL-2 - Auth-boundary documentation and MCPAUTH closeout record; Depends on: SL-0, SL-1; Blocks: MCPAUTH acceptance; Parallel-safe: no

Lane DAG:

```text
SL-0 ----\
          -> SL-2 -> MCPAUTH acceptance
SL-1 ----/
```

## Lanes

### SL-0 - STDIO Handshake Contract And Log-Safety Hardening

- **Scope**: Harden the local STDIO handshake path so `MCP_CLIENT_SECRET`
  stays a local guard only, the handshake tool never logs raw secret material,
  and the public STDIO tool contract says exactly that.
- **Owned files**: `mcp_server/cli/handshake.py`, `mcp_server/cli/stdio_runner.py`, `tests/test_handshake.py`, `tests/test_mcp_server_cli.py`, `tests/test_stdio_tool_descriptions.py`, `tests/test_mcpauth_stdio_contract.py`
- **Interfaces provided**: IF-0-MCPAUTH-1 local STDIO auth contract;
  STDIO handshake/logging evidence consumed by SL-2
- **Interfaces consumed**: current `HandshakeGate` behavior;
  current `call_tool()` logging and `handshake` tool schema in
  `mcp_server/cli/stdio_runner.py`; current public tool ordering and metadata
  frozen by `tests/test_stdio_tool_descriptions.py`
- **Parallel-safe**: yes
- **Tasks**:
  - test: Extend `tests/test_handshake.py` so enabled-gate failures and
    successful handshakes are checked for stable fail-closed behavior without
    requiring raw secret echoes.
  - test: Extend `tests/test_mcp_server_cli.py` or add
    `tests/test_mcpauth_stdio_contract.py` to capture the concrete leak path in
    `call_tool()`: the `handshake` tool must not emit log records containing
    the submitted secret, while non-handshake tools can keep ordinary argument
    logging.
  - test: Update `tests/test_stdio_tool_descriptions.py` only as needed to
    freeze the local-only handshake description and to ensure `handshake`
    remains outside task-support or remote-transport advertising.
  - impl: Sanitize or suppress handshake argument logging in
    `mcp_server/cli/stdio_runner.py` instead of logging `args={arguments}` for
    the `handshake` tool path.
  - impl: Keep `HandshakeGate` local and minimal. Do not turn it into bearer
    auth, OAuth, or cross-request credential storage; preserve the current
    environment-backed contract.
  - impl: If execution adjusts handshake error text, keep the payload
    deterministic and non-secret while preserving the existing
    `handshake_required` code family.
  - verify: `uv run pytest tests/test_handshake.py tests/test_mcp_server_cli.py tests/test_stdio_tool_descriptions.py tests/test_mcpauth_stdio_contract.py -q --no-cov`
  - verify: `uv run python - <<'PY'\nfrom mcp_server.cli.stdio_runner import _build_tool_list\nprint([tool.name for tool in _build_tool_list()])\nprint(_build_tool_list()[-1].description)\nPY`

### SL-1 - HTTP/Admin Auth Redaction Coverage And Boundary-Preservation Regressions

- **Scope**: Preserve the existing FastAPI admin/debug bearer-auth surface
  while broadening redaction coverage and regression tests so auth failures
  cannot leak `MCP_CLIENT_SECRET` or raw bearer values through HTTP responses.
- **Owned files**: `mcp_server/security/security_middleware.py`, `tests/test_secret_redaction.py`, `tests/security/test_metrics_auth.py`, `tests/security/test_route_auth_coverage.py`, `tests/security/test_mcpauth_boundary.py`
- **Interfaces provided**: IF-0-MCPAUTH-2 secret-leak prevention contract;
  admin/debug auth-boundary evidence consumed by SL-2
- **Interfaces consumed**: current FastAPI authentication and authorization
  middleware; existing `_REDACTION_PATTERNS`; current `/metrics` and protected
  route auth coverage
- **Parallel-safe**: yes
- **Tasks**:
  - test: Extend `tests/test_secret_redaction.py` to add an
    `MCP_CLIENT_SECRET=` redaction case and to keep the existing bearer/JWT and
    GitHub token redaction expectations passing.
  - test: Add `tests/security/test_mcpauth_boundary.py` or extend
    `tests/security/test_metrics_auth.py` so HTTP authorization failures remain
    bearer-token based, redacted, and explicitly separate from the STDIO
    `handshake` tool contract.
  - test: Keep `tests/security/test_route_auth_coverage.py` as the guard that
    the admin/debug surface still fails closed without credentials and is not
    silently widened into a public remote MCP auth surface.
  - impl: Expand `_REDACTION_PATTERNS` only as far as needed for the current
    roadmap contract, likely including `MCP_CLIENT_SECRET=`. Do not broaden the
    middleware into a speculative full secret-scanner.
  - impl: Preserve the existing FastAPI bearer-auth permission mapping and
    route protection semantics. This lane is about secret-boundary hardening,
    not replacing the admin/debug auth stack.
  - verify: `uv run pytest tests/test_secret_redaction.py tests/security/test_metrics_auth.py tests/security/test_route_auth_coverage.py tests/security/test_mcpauth_boundary.py -q --no-cov`
  - verify: `rg -n "MCP_CLIENT_SECRET|REDACTED|Bearer|metrics|handshake" mcp_server/security/security_middleware.py tests/test_secret_redaction.py tests/security/test_metrics_auth.py tests/security/test_route_auth_coverage.py tests/security/test_mcpauth_boundary.py`

### SL-2 - Auth-Boundary Documentation And MCPAUTH Closeout Record

- **Scope**: Reduce the code and test findings into one explicit operator and
  user-facing auth story: local STDIO handshake is supported, admin/debug HTTP
  bearer auth is separate, and remote MCP auth remains unimplemented while
  remote MCP transport is deferred.
- **Owned files**: `README.md`, `docs/GETTING_STARTED.md`, `docs/MCP_CONFIGURATION.md`, `docs/validation/mcp-auth-boundary.md`, `tests/docs/test_mcpauth_surface_alignment.py`
- **Interfaces provided**: IF-0-MCPAUTH-3 auth-boundary documentation
  contract; IF-0-MCPAUTH-4 regression-coverage closeout
- **Interfaces consumed**: SL-0 STDIO handshake/logging evidence;
  SL-1 redaction and admin/debug auth evidence;
  `docs/validation/mcp-transport-decision.md` remote-deferment decision
- **Parallel-safe**: no
- **Tasks**:
  - test: Add `tests/docs/test_mcpauth_surface_alignment.py` to freeze the
    exact documentation posture across `README.md`,
    `docs/GETTING_STARTED.md`, `docs/MCP_CONFIGURATION.md`, and
    `docs/validation/mcp-auth-boundary.md`.
  - test: In that alignment test, assert the docs describe
    `MCP_CLIENT_SECRET` as a local STDIO guard, describe FastAPI bearer auth as
    admin/debug only, and explicitly state that no remote MCP authorization is
    implemented while `docs/validation/mcp-transport-decision.md` defers remote
    MCP transport.
  - impl: Add `docs/validation/mcp-auth-boundary.md` as the single MCPAUTH
    closeout artifact. It should explain the supported auth surfaces, the
    remote-auth deferment, and the no-secret-leak expectations grounded in the
    implemented tests.
  - impl: Update only the auth-facing paragraphs in `README.md`,
    `docs/GETTING_STARTED.md`, and `docs/MCP_CONFIGURATION.md` that are
    currently silent or ambiguous about `MCP_CLIENT_SECRET`, handshake usage,
    or remote-auth absence.
  - impl: Do not write OAuth/OIDC setup instructions, protected-resource
    metadata guides, or remote token acquisition flows while the transport
    decision still says remote MCP is deferred.
  - verify: `uv run pytest tests/docs/test_mcpauth_surface_alignment.py -q --no-cov`
  - verify: `rg -n "MCP_CLIENT_SECRET|handshake|local STDIO|admin/debug|Bearer|remote MCP auth|not implemented" README.md docs/GETTING_STARTED.md docs/MCP_CONFIGURATION.md docs/validation/mcp-auth-boundary.md docs/validation/mcp-transport-decision.md`

## Verification

Planning-only work is complete once this artifact is written and staged. Do
not execute the commands below during plan creation; run them during
`codex-execute-phase` or manual MCPAUTH execution.

Lane-specific checks:

```bash
uv run pytest \
  tests/test_handshake.py \
  tests/test_mcp_server_cli.py \
  tests/test_stdio_tool_descriptions.py \
  tests/test_mcpauth_stdio_contract.py \
  -q --no-cov

uv run pytest \
  tests/test_secret_redaction.py \
  tests/security/test_metrics_auth.py \
  tests/security/test_route_auth_coverage.py \
  tests/security/test_mcpauth_boundary.py \
  -q --no-cov

uv run pytest \
  tests/docs/test_mcpauth_surface_alignment.py \
  -q --no-cov
```

Whole-phase verification after code and docs changes:

```bash
uv run pytest \
  tests/test_handshake.py \
  tests/test_mcp_server_cli.py \
  tests/test_stdio_tool_descriptions.py \
  tests/test_mcpauth_stdio_contract.py \
  tests/test_secret_redaction.py \
  tests/security/test_metrics_auth.py \
  tests/security/test_route_auth_coverage.py \
  tests/security/test_mcpauth_boundary.py \
  tests/docs/test_mcpauth_surface_alignment.py \
  -q --no-cov

git status --short -- \
  mcp_server/cli/handshake.py \
  mcp_server/cli/stdio_runner.py \
  mcp_server/security/security_middleware.py \
  README.md \
  docs/GETTING_STARTED.md \
  docs/MCP_CONFIGURATION.md \
  docs/validation/mcp-auth-boundary.md \
  tests/test_handshake.py \
  tests/test_mcp_server_cli.py \
  tests/test_stdio_tool_descriptions.py \
  tests/test_mcpauth_stdio_contract.py \
  tests/test_secret_redaction.py \
  tests/security/test_metrics_auth.py \
  tests/security/test_route_auth_coverage.py \
  tests/security/test_mcpauth_boundary.py \
  tests/docs/test_mcpauth_surface_alignment.py \
  plans/phase-plan-v8-MCPAUTH.md
```

## Acceptance Criteria

- [ ] `MCP_CLIENT_SECRET` remains an environment-backed local STDIO guard, and
      the `handshake` tool path no longer logs or echoes the raw submitted
      secret.
- [ ] Handshake failures and startup/auth errors stay fail closed with
      deterministic non-secret payloads, preserving the existing
      `handshake_required` contract where it already exists.
- [ ] HTTP secret-redaction coverage includes `MCP_CLIENT_SECRET=` in addition
      to the existing bearer/JWT/GitHub token patterns, without broadening into
      a speculative generic secret scanner.
- [ ] FastAPI `/metrics` and other protected admin/debug routes continue to use
      the existing bearer-auth permission model and remain separate from the
      STDIO handshake mechanism.
- [ ] README, getting-started guidance, configuration guidance, and one MCPAUTH
      validation artifact all state the same auth boundary: local STDIO
      handshake is supported, admin/debug HTTP bearer auth is separate, and no
      remote MCP auth is implemented while remote MCP transport remains
      deferred.
- [ ] The phase does not add a remote MCP endpoint, OAuth/OIDC flow,
      protected-resource metadata exchange, or a new secret storage backend.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v8-MCPAUTH.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v8-MCPAUTH.md
  artifact_state: staged
```
