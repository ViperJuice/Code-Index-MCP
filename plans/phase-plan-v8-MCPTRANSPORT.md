---
phase_loop_plan_version: 1
phase: MCPTRANSPORT
roadmap: specs/phase-plans-v8.md
roadmap_sha256: 25aa1501b52e5038cbcc0356638d2a5de5aaaea75c32e21c03de8a1db6a99a11
---
# MCPTRANSPORT: Transport Boundary And Optional Streamable HTTP Decision

## Context

MCPTRANSPORT is the next v8 planning target after the repo already closed out
`MCPBASE`, `MCPMETA`, `MCPSTRUCT`, and `MCPTASKS`. Its job is to make the
transport story explicit and decide whether this roadmap should add a remote
MCP transport now or defer it cleanly.

Current repo state gathered during planning:

- `specs/phase-plans-v8.md` is tracked and clean in this worktree, and
  `sha256sum specs/phase-plans-v8.md` matches the required
  `25aa1501b52e5038cbcc0356638d2a5de5aaaea75c32e21c03de8a1db6a99a11`.
- Canonical runner state exists under `.phase-loop/`, but
  `.phase-loop/state.json` and `.phase-loop/tui-handoff.md` are stale relative
  to git reality: they still name `MCPTASKS` as the current `unplanned` phase,
  while `git log --oneline -8` shows `MCPTASKS` closeout commits `6eb0234` and
  `e860975`, the worktree is currently clean, and
  `plans/phase-plan-v8-MCPTASKS.md` already exists. Per the repo-local phase
  loop contract, filesystem and git reality are safe to plan against when the
  ledger lags; legacy `.codex/phase-loop/` artifacts remain compatibility-only
  and are not authoritative for this run.
- The target artifact `plans/phase-plan-v8-MCPTRANSPORT.md` did not exist
  before this planning run.
- `mcp_server/cli/server_commands.py` already keeps the startup split concrete:
  `stdio()` starts the primary MCP STDIO server, while `serve()` launches
  `uvicorn.run("mcp_server.gateway:app", ...)` and prints FastAPI
  admin/debug gateway wording.
- `mcp_server/gateway.py` is a FastAPI admin surface with REST endpoints,
  middleware, health, metrics, and auth helpers. It does not currently expose
  an MCP Streamable HTTP endpoint, SDK transport adapter, or distinct remote
  MCP lifecycle.
- User-facing docs already trend in the right direction:
  `README.md`, `docs/GETTING_STARTED.md`, and `docs/MCP_CONFIGURATION.md`
  state that STDIO is primary and that `mcp-index serve` is not the repo's MCP
  Streamable HTTP transport.
- Client registration templates already reinforce the STDIO-first posture:
  `.mcp.json.templates/native.json` and `.mcp.json.templates/auto-detect.json`
  invoke `python -m mcp_server.cli stdio`, and no template currently registers
  `mcp-index serve` as an MCP client transport target.
- Existing tests cover pieces of this boundary, but the contract is still
  fragmented: `tests/test_server_commands.py` checks the CLI wording, and
  `tests/docs/test_mcpbase_baseline_audit.py` freezes one negative transport
  claim, but there is no single MCPTRANSPORT decision artifact or focused test
  that binds CLI help, docs, templates, and gateway route posture together.

Practical planning boundary:

- MCPTRANSPORT can close cleanly as a docs-and-tests phase if the product
  decision remains "STDIO only for MCP clients for now." That is the likely
  execution path given the current repo shape and the downstream dependency
  that `MCPAUTH` should only design remote auth after a deliberate remote
  transport decision.
- MCPTRANSPORT should not add OAuth, rewrite the FastAPI admin surface, or
  silently treat `mcp-index serve` as remote MCP.
- If execution uncovers an already-started, in-scope Streamable HTTP slice,
  that work must live behind a distinct endpoint/module/test surface rather
  than by repurposing the existing admin/debug gateway in place.

## Interface Freeze Gates

- [ ] IF-0-MCPTRANSPORT-1 - Startup boundary contract:
      `mcp-index stdio` remains the primary supported MCP transport entrypoint,
      while `mcp-index serve` and `mcp_server.gateway:app` remain
      FastAPI admin/debug HTTP surfaces and are not described as the repo's
      MCP Streamable HTTP transport.
- [ ] IF-0-MCPTRANSPORT-2 - Client registration contract:
      README, getting-started guidance, and repo-shipped `.mcp.json` templates
      register the MCP server through STDIO only and do not imply that an HTTP
      admin endpoint should be configured as an MCP client transport target.
- [ ] IF-0-MCPTRANSPORT-3 - Remote transport decision contract:
      one implementation-owned decision record states whether remote MCP is
      deferred or implemented in v8, and if deferred it names the minimum
      future prerequisites for a distinct Streamable HTTP endpoint
      (separate routing/lifecycle, transport-specific tests, and downstream
      auth work in `MCPAUTH`).
- [ ] IF-0-MCPTRANSPORT-4 - Admin surface preservation contract:
      the phase keeps the current FastAPI admin/debug surface intact; existing
      admin gateway regressions continue to pass, and no docs or tests claim
      `/symbol`, `/search`, `/status`, `/plugins`, or `/reindex` are MCP
      Streamable HTTP routes.

## Lane Index & Dependencies

- SL-0 - CLI and gateway transport-boundary freeze; Depends on: (none); Blocks: SL-2; Parallel-safe: yes
- SL-1 - User-facing transport docs and client-template truth; Depends on: (none); Blocks: SL-2; Parallel-safe: yes
- SL-2 - Remote transport decision record and MCPTRANSPORT closeout; Depends on: SL-0, SL-1; Blocks: MCPTRANSPORT acceptance; Parallel-safe: no

Lane DAG:

```text
SL-0 ----\
          -> SL-2 -> MCPTRANSPORT acceptance
SL-1 ----/
```

## Lanes

### SL-0 - CLI And Gateway Transport-Boundary Freeze

- **Scope**: Tighten the executable transport boundary at the CLI and test
  level so the current FastAPI admin surface cannot be mistaken for a remote
  MCP transport, without changing endpoint behavior.
- **Owned files**: `mcp_server/cli/server_commands.py`, `tests/test_server_commands.py`, `tests/test_gateway_transport_boundary.py`
- **Interfaces provided**: IF-0-MCPTRANSPORT-1 startup boundary contract;
  gateway-route/admin-surface evidence consumed by SL-2
- **Interfaces consumed**: current `serve()` and `stdio()` command wiring;
  current `mcp_server.gateway.app` route table and endpoint surface;
  current CLI help strings and startup banner text
- **Parallel-safe**: yes
- **Tasks**:
  - test: Extend `tests/test_server_commands.py` so `serve --help` and
    `stdio --help` freeze the primary-versus-secondary transport wording and
    continue to reject Streamable HTTP framing for `serve`.
  - test: Add `tests/test_gateway_transport_boundary.py` to assert the current
    FastAPI route table exposes only the documented admin/debug surface and
    does not grow a hidden `/mcp` or Streamable HTTP transport route in this
    phase.
  - impl: Adjust `mcp_server/cli/server_commands.py` help text or startup echo
    only if the current wording is not explicit enough for the new tests.
  - impl: Keep this lane behavior-preserving. Do not add new FastAPI routes,
    do not rename commands, and do not introduce a remote transport adapter
    here.
  - verify: `uv run pytest tests/test_server_commands.py tests/test_gateway_transport_boundary.py -q --no-cov`
  - verify: `rg -n "admin/debug|STDIO|Streamable HTTP|serve|stdio" mcp_server/cli/server_commands.py tests/test_server_commands.py tests/test_gateway_transport_boundary.py`

### SL-1 - User-Facing Transport Docs And Client-Template Truth

- **Scope**: Bring the user-facing startup/configuration surfaces into one
  explicit transport story: STDIO is the MCP client path, while FastAPI HTTP
  remains secondary admin/debug infrastructure.
- **Owned files**: `README.md`, `docs/GETTING_STARTED.md`, `docs/MCP_CONFIGURATION.md`, `.mcp.json.templates/*.json`, `tests/docs/test_mcptransport_surface_alignment.py`
- **Interfaces provided**: IF-0-MCPTRANSPORT-2 client registration contract;
  doc/template truth consumed by SL-2
- **Interfaces consumed**: current README quick-start and tool-surface prose;
  current getting-started startup steps; current MCP configuration template
  commands; current STDIO-primary/FastAPI-secondary baseline from MCPBASE and
  customer-doc alignment tests
- **Parallel-safe**: yes
- **Tasks**:
  - test: Add `tests/docs/test_mcptransport_surface_alignment.py` to freeze
    that `README.md`, `docs/GETTING_STARTED.md`, and
    `docs/MCP_CONFIGURATION.md` all describe STDIO as the MCP client
    registration path and describe `mcp-index serve` as admin/debug only.
  - test: In the same alignment test, assert repo-shipped
    `.mcp.json.templates/*.json` continue to launch the server through STDIO
    invocations and do not suggest `serve`, HTTP URLs, or REST endpoint
    registration as MCP client configuration.
  - impl: Update only the transport-facing paragraphs that are still ambiguous
    or duplicated. Keep the doc edits narrow and consistent across the three
    surfaces.
  - impl: If any template comments or example names need cleanup, keep the
    actual transport commands STDIO-only unless SL-2 deliberately records a
    remote-transport build decision.
  - impl: Do not broaden this lane into auth guidance, task usage, or release
    packaging changes.
  - verify: `uv run pytest tests/docs/test_mcptransport_surface_alignment.py -q --no-cov`
  - verify: `rg -n "Streamable HTTP|mcp-index serve|mcp-index stdio|admin/debug|secondary|STDIO" README.md docs/GETTING_STARTED.md docs/MCP_CONFIGURATION.md .mcp.json.templates`

### SL-2 - Remote Transport Decision Record And MCPTRANSPORT Closeout

- **Scope**: Reduce the CLI, gateway, docs, and template findings into one
  explicit product decision record that closes MCPTRANSPORT either as a
  deliberate deferment of remote MCP or as a distinct implementation choice
  with follow-on constraints.
- **Owned files**: `docs/validation/mcp-transport-decision.md`, `tests/docs/test_mcptransport_decision_record.py`
- **Interfaces provided**: IF-0-MCPTRANSPORT-3 remote transport decision
  contract; IF-0-MCPTRANSPORT-4 admin surface preservation contract
- **Interfaces consumed**: SL-0 startup and gateway-boundary assertions;
  SL-1 doc/template truth; roadmap scope note that MCPTRANSPORT may close
  docs-only; downstream `MCPAUTH` dependency that remote auth should not be
  designed before the transport decision is explicit
- **Parallel-safe**: no
- **Tasks**:
  - test: Add `tests/docs/test_mcptransport_decision_record.py` to freeze one
    final decision record, the explicit current-state statement that STDIO is
    primary and FastAPI remains admin/debug, and the future prerequisites for
    any later Streamable HTTP work.
  - impl: Write `docs/validation/mcp-transport-decision.md` as the single
    MCPTRANSPORT decision artifact. The likely closeout path is to defer remote
    MCP for v8 and record why: the current gateway is admin/debug only, a
    transport-specific endpoint would require separate lifecycle/routing and
    MCP client smokes, and remote auth belongs in `MCPAUTH` only after a
    transport exists.
  - impl: If execution does choose to implement remote MCP instead of
    deferring it, rewrite this lane so the decision record points at the new
    dedicated endpoint and test surface; do not repurpose the existing admin
    gateway documentation to pretend the distinction no longer matters.
  - impl: Keep the decision artifact operational rather than speculative. It
    should help the next phase know whether `MCPAUTH` is documenting "no remote
    MCP auth yet" or designing auth for a newly added dedicated endpoint.
  - verify: `uv run pytest tests/docs/test_mcptransport_decision_record.py -q --no-cov`
  - verify: `rg -n "STDIO|FastAPI|admin/debug|Streamable HTTP|defer|MCPAUTH|MCPEVAL" docs/validation/mcp-transport-decision.md tests/docs/test_mcptransport_decision_record.py`

## Verification

Planning-only work is complete once this artifact is written and staged. Do
not execute the commands below during plan creation; run them during
`codex-execute-phase` or manual MCPTRANSPORT execution.

Lane-specific checks:

```bash
uv run pytest \
  tests/test_server_commands.py \
  tests/test_gateway_transport_boundary.py \
  -q --no-cov

uv run pytest \
  tests/docs/test_mcptransport_surface_alignment.py \
  -q --no-cov

uv run pytest \
  tests/docs/test_mcptransport_decision_record.py \
  -q --no-cov
```

Whole-phase verification after code and docs changes:

```bash
uv run pytest \
  tests/test_server_commands.py \
  tests/test_gateway_transport_boundary.py \
  tests/test_gateway.py \
  tests/test_health_surface.py \
  tests/docs/test_mcptransport_surface_alignment.py \
  tests/docs/test_mcptransport_decision_record.py \
  -q --no-cov

git status --short -- \
  mcp_server/cli/server_commands.py \
  README.md \
  docs/GETTING_STARTED.md \
  docs/MCP_CONFIGURATION.md \
  .mcp.json.templates \
  docs/validation/mcp-transport-decision.md \
  tests/test_server_commands.py \
  tests/test_gateway_transport_boundary.py \
  tests/docs/test_mcptransport_surface_alignment.py \
  tests/docs/test_mcptransport_decision_record.py \
  plans/phase-plan-v8-MCPTRANSPORT.md
```

## Acceptance Criteria

- [ ] `mcp-index stdio` is the only documented MCP client transport entrypoint,
      and `mcp-index serve` remains explicitly documented and tested as a
      FastAPI admin/debug gateway rather than the repo's MCP Streamable HTTP
      transport.
- [ ] README, getting-started guidance, and repo-shipped `.mcp.json` templates
      all register the MCP server through STDIO and do not imply that HTTP
      admin endpoints should be used as MCP client configuration.
- [ ] A single decision record states whether remote MCP is deferred or
      implemented for v8; if deferred, it lists the minimum future
      prerequisites for a separate Streamable HTTP endpoint and makes clear
      that `MCPAUTH` owns any later remote-authorization work.
- [ ] Existing FastAPI admin/debug regressions still pass, and no new docs or
      route tests claim `/symbol`, `/search`, `/status`, `/plugins`, or
      `/reindex` are MCP Streamable HTTP routes.
- [ ] The phase stays within the roadmap's docs-only allowance unless
      execution finds a real, already-started dedicated remote MCP endpoint
      slice in the checkout. It does not silently repurpose the current admin
      gateway into remote MCP.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v8-MCPTRANSPORT.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v8-MCPTRANSPORT.md
  artifact_state: staged
```
