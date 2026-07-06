---
phase_loop_plan_version: 1
phase: PYCLIENT
roadmap: specs/phase-plans-v9.md
roadmap_sha256: 57848534176ac820595f4193459b86b5fdef9f5bfe5bff60a5739d8d9e192d2b
---
# PYCLIENT: Programmatic Python Search Client

## Context

PYCLIENT is Phase 8 in `specs/phase-plans-v9.md`. The canonical
`.phase-loop/state.json` reports PUBNAME, REPOCLEAN, LOCALCI, COVERAGE,
PROCENV, FRICTION, and HISTORY complete; `PYCLIENT` is current/unplanned; the
worktree was clean at planner reconciliation time; and the roadmap SHA-256 is
`57848534176ac820595f4193459b86b5fdef9f5bfe5bff60a5739d8d9e192d2b`.
Legacy `.codex/phase-loop/` files are compatibility artifacts only and are not
used to supersede canonical `.phase-loop/` state.

Planning observations:

- `mcp_server/plugin_base.py::SearchOpts` already exposes source filters for
  `source_type`, `friction_categories`, `history_labels`, `history_repos`, and
  `include_source_metadata` after the FRICTION and HISTORY phases.
- `mcp_server/dispatcher/dispatcher_enhanced.py::EnhancedDispatcher.search()`
  accepts `RepoContext` plus the source filters, but
  `mcp_server/dispatcher/protocol.py::DispatcherProtocol.search()` is narrower
  than the concrete dispatcher surface.
- `mcp_server/cli/tool_handlers.py::handle_search_code()` and
  `mcp_server/gateway.py::search()` currently perform their own argument
  normalization and dispatcher calls; PYCLIENT should move that behavior behind
  a shared Python client/service API instead of adding another search path.
- `mcp_server/__init__.py` currently exports legacy internals only; the public
  package surface needs explicit client exports while preserving the canonical
  distribution name `index-it-mcp` and existing import package `mcp_server`.
- Direct client tests can use the existing repo-resolver/bootstrap fixtures and
  SQLite-backed dispatcher paths; they must not start the MCP STDIO server or a
  remote service.

Planning boundary:

- PYCLIENT may add a public `mcp_server.client` API, typed option/result models,
  package exports, local search/status/reindex helpers, shared source-filter
  normalization, MCP/FastAPI wrapper delegation to the shared client surface,
  and metadata-only docs/evidence.
- PYCLIENT must not remove MCP tools, rename the distribution or import package,
  add a remote hosted service client, dispatch a release, require live provider
  credentials for tests, or change FRICTION/HISTORY metadata schemas.

## Interface Freeze Gates

- [ ] IF-0-PYCLIENT-1 — Python client API contract: `mcp_server.client` exposes
      a supported local programmatic API for `search_code`, `symbol_lookup`,
      `reindex`, and `get_status` with typed option/result objects, stable
      source filters for code/friction/history records, readiness-aware
      `index_unavailable` responses, and clear stability notes; direct client
      use works without starting MCP STDIO or FastAPI; MCP `search_code` and
      FastAPI `/search` delegate to the same shared client/service behavior
      instead of forking search logic; package exports from `mcp_server` align
      with the canonical `index-it-mcp` distribution; existing MCP STDIO tests
      remain compatible; and docs explain when to use the Python client versus
      MCP tools.

## Spec Closeout Plan

- schema: `spec_delta_closeout.v1`
- decision: `canonical_spec_update`
- target surfaces: `mcp_server/client.py`, `mcp_server/client_types.py`,
  `mcp_server/__init__.py`, `mcp_server/dispatcher/protocol.py`,
  `mcp_server/cli/tool_handlers.py`, `mcp_server/gateway.py`, `README.md`,
  `docs/api/API-REFERENCE.md`, `docs/SUPPORT_MATRIX.md`,
  `docs/status/python-client-api.md`
- evidence paths: `docs/status/python-client-api.md`, direct Python client
  tests, MCP wrapper compatibility tests, MCP STDIO smoke tests
- redaction posture: `metadata_only`
- downstream handling: `none`

## Lane Index & Dependencies

SL-0 — Public client contract and package exports
  Depends on: (none)
  Blocks: SL-1, SL-2, SL-3, SL-4
  Parallel-safe: no
SL-1 — Local Python client implementation
  Depends on: SL-0
  Blocks: SL-2, SL-3, SL-4
  Parallel-safe: no
SL-2 — MCP and FastAPI wrapper delegation
  Depends on: SL-0, SL-1
  Blocks: SL-3, SL-4
  Parallel-safe: no
SL-3 — PYCLIENT contract verification
  Depends on: SL-0, SL-1, SL-2
  Blocks: SL-4
  Parallel-safe: no
SL-4 — PYCLIENT docs and evidence reducer
  Depends on: SL-0, SL-1, SL-2, SL-3
  Blocks: (none)
  Parallel-safe: no

Lane DAG:

```text
SL-0 -> SL-1 -> SL-2 -> SL-3 -> SL-4 -> PYCLIENT acceptance
```

## Lanes

### SL-0 — Public Client Contract And Package Exports

- **Scope**: Freeze the public Python client names, typed data contracts, and
  package exports before implementation or wrapper migration begins.
- **Owned files**: `mcp_server/client_types.py`, `mcp_server/__init__.py`,
  `mcp_server/dispatcher/protocol.py`, `tests/test_python_client_contract.py`
- **Interfaces provided**: `ClientSearchOptions`, `ClientSearchResult`, `ClientSymbolResult`, `ClientReindexResult`, `ClientStatusResult`, `SourceType`, `IndexUnavailable`, `DispatcherProtocol.search source-filter signature`, `mcp_server.__all__ client exports`, `SL-0 public client contract`
- **Interfaces consumed**: `SearchOpts` source-filter vocabulary (pre-existing), `RepositoryReadiness` states (pre-existing), `search_source_metadata.v1` records (pre-existing), canonical distribution name `index-it-mcp` (pre-existing)
- **Parallel-safe**: no
- **Tasks**:
  - test: Add `tests/test_python_client_contract.py` to assert the exported
    names, import paths, dataclass or typed-model fields, allowed `SourceType`
    values, readiness/index-unavailable shape, and package export alignment
    from `mcp_server`.
  - test: Cover that `ClientSearchOptions` includes code/friction/history
    source filters and that invalid source types fail with a typed validation
    error before reaching a dispatcher.
  - impl: Add `mcp_server/client_types.py` with narrow typed option/result
    objects and source-filter validation helpers; keep secret-bearing values out
    of `repr` and error payloads.
  - impl: Update `mcp_server/dispatcher/protocol.py` so the protocol signature
    matches the concrete dispatcher source-filter arguments used by the client.
  - impl: Export the supported client contract from `mcp_server/__init__.py`
    without removing existing lazy exports.
  - verify: `uv run pytest tests/test_python_client_contract.py -q --no-cov`

### SL-1 — Local Python Client Implementation

- **Scope**: Implement the local Python client as a thin service over repo
  resolution, readiness checks, dispatcher search/lookup, and local reindex
  mutation paths.
- **Owned files**: `mcp_server/client.py`, `tests/test_python_client_search.py`,
  `tests/test_python_client_indexing.py`, `tests/test_python_client_sources.py`
- **Interfaces provided**: `IndexItClient`, `open_client`, `IndexItClient.search_code`, `IndexItClient.symbol_lookup`, `IndexItClient.reindex`, `IndexItClient.get_status`, `SL-1 shared local search service`, `SL-1 direct client evidence`
- **Interfaces consumed**: `SL-0 public client contract`, `initialize_stateless_services` (pre-existing), `RepoResolver` (pre-existing), `ReadinessClassifier` fail-closed behavior (pre-existing), `EnhancedDispatcher.search` source filters (pre-existing), `EnhancedDispatcher.lookup` (pre-existing), `EnhancedDispatcher.index_file` and `EnhancedDispatcher.index_directory` (pre-existing), SQLite durable store paths (pre-existing)
- **Parallel-safe**: no
- **Tasks**:
  - test: Add `tests/test_python_client_search.py` proving direct client search
    returns typed results for lexical code search and preserves source metadata
    only when requested.
  - test: Add `tests/test_python_client_sources.py` proving direct client
    filtering supports `source_type="friction"`, `source_type="history"`,
    friction categories, history labels, and history repos using fixture-backed
    SQLite records.
  - test: Add `tests/test_python_client_indexing.py` proving direct client
    `reindex` and `get_status` operate on a registered local repo without
    starting MCP STDIO or FastAPI, and non-ready repositories return typed
    `index_unavailable` data rather than dispatching.
  - impl: Add `mcp_server/client.py` with an `IndexItClient` context manager or
    closeable object that owns the bootstrapped service pool and resolves a
    repository per operation.
  - impl: Delegate search and lookup to the dispatcher with the exact source
    filters from `ClientSearchOptions`; do not duplicate lexical, semantic,
    friction, or history ranking logic.
  - impl: Keep reindex local and readiness-aware, returning typed mutation
    results with counts compatible with existing `reindex` tool payloads.
  - verify: `uv run pytest tests/test_python_client_search.py tests/test_python_client_sources.py tests/test_python_client_indexing.py -q --no-cov`

### SL-2 — MCP And FastAPI Wrapper Delegation

- **Scope**: Route MCP `search_code` and FastAPI `/search` through the shared
  client/service normalization while preserving existing tool schemas and
  response compatibility.
- **Owned files**: `mcp_server/cli/tool_handlers.py`, `mcp_server/gateway.py`,
  `tests/test_python_client_mcp_wrapper.py`, `tests/test_friction_tool_handlers.py`,
  `tests/test_history_tool_handlers.py`, `tests/test_gateway.py`
- **Interfaces provided**: `search_code shared-client delegation evidence`, `FastAPI /search shared-client delegation evidence`, `legacy MCP search response compatibility`, `SL-2 wrapper compatibility evidence`
- **Interfaces consumed**: `SL-1 shared local search service`, existing `search_code` input schema (pre-existing), existing FastAPI `/search` query parameters (pre-existing), `source_type="friction"` behavior (pre-existing), `source_type="history"` behavior (pre-existing), semantic readiness refusal contract (pre-existing)
- **Parallel-safe**: no
- **Tasks**:
  - test: Add `tests/test_python_client_mcp_wrapper.py` proving
    `handle_search_code()` delegates normalized query/source-filter options to
    the shared client/service path and preserves ordinary unfiltered legacy list
    responses, semantic metadata responses, and `index_unavailable` refusals.
  - test: Extend `tests/test_friction_tool_handlers.py` and
    `tests/test_history_tool_handlers.py` only as needed to prove source-filter
    behavior still matches the FRICTION/HISTORY contracts after delegation.
  - test: Extend `tests/test_gateway.py` only as needed to prove `/search`
    source-filter and include-source-metadata responses use the shared
    client/service path and retain admin/debug response shape.
  - impl: Refactor `mcp_server/cli/tool_handlers.py::handle_search_code()` to
    use the shared client/service option normalization and result adaptation
    instead of maintaining a parallel dispatcher call path.
  - impl: Refactor `mcp_server/gateway.py::search()` to use the same shared
    client/service behavior for search execution while keeping FastAPI auth,
    metrics, and HTTP error handling local to the gateway.
  - verify: `uv run pytest tests/test_python_client_mcp_wrapper.py tests/test_friction_tool_handlers.py tests/test_history_tool_handlers.py tests/test_gateway.py -q --no-cov`

### SL-3 — PYCLIENT Contract Verification

- **Scope**: Run the targeted verification suite across the public client,
  wrapper compatibility, smoke, and docs contracts before the evidence reducer.
- **Owned files**: none
- **Interfaces provided**: `SL-3 verification evidence`, `PYCLIENT acceptance pre-verdict`, `phase-owned dirty-path audit`
- **Interfaces consumed**: `SL-0 public client contract`, `SL-1 direct client evidence`, `SL-2 wrapper compatibility evidence`, roadmap verification commands (pre-existing)
- **Parallel-safe**: no
- **Tasks**:
  - test: Re-run every PYCLIENT-targeted test plus MCP wrapper compatibility,
    smoke, and docs contract tests.
  - impl: No source edits unless verification identifies a PYCLIENT-owned
    repair; any repair must stay inside the owned file sets of SL-0 through
    SL-2 or trigger plan repair before closeout.
  - verify: `uv sync --locked --extra dev`
  - verify: `uv run pytest tests/test_python_client_contract.py tests/test_python_client_search.py tests/test_python_client_sources.py tests/test_python_client_indexing.py tests/test_python_client_mcp_wrapper.py tests/test_friction_tool_handlers.py tests/test_history_tool_handlers.py tests/test_gateway.py tests/test_tool_schema_handler_parity.py tests/test_stdio_tool_descriptions.py tests/docs/test_pyclient_api_contract.py tests/docs/test_pyclient_public_docs.py -q --no-cov`
  - verify: `uv run pytest tests/smoke/test_mcpbase_stdio_smoke.py tests/smoke/test_secondary_tool_readiness_smoke.py -q --no-cov`
  - verify: `make agent-full`
  - verify: `phase-loop validate-roadmap specs/phase-plans-v9.md`
  - verify: `git status --short -- mcp_server/client_types.py mcp_server/client.py mcp_server/__init__.py mcp_server/dispatcher/protocol.py mcp_server/cli/tool_handlers.py mcp_server/gateway.py README.md docs/api/API-REFERENCE.md docs/SUPPORT_MATRIX.md docs/status/python-client-api.md tests/test_python_client_contract.py tests/test_python_client_search.py tests/test_python_client_sources.py tests/test_python_client_indexing.py tests/test_python_client_mcp_wrapper.py tests/test_friction_tool_handlers.py tests/test_history_tool_handlers.py tests/test_gateway.py tests/docs/test_pyclient_api_contract.py tests/docs/test_pyclient_public_docs.py plans/phase-plan-v9-PYCLIENT.md`

### SL-4 — PYCLIENT Docs And Evidence Reducer

- **Scope**: Document the supported Python client surface, when to use it, and
  the compatibility boundary with MCP tools using evidence from all producer
  lanes.
- **Owned files**: `README.md`, `docs/api/API-REFERENCE.md`,
  `docs/SUPPORT_MATRIX.md`, `docs/status/python-client-api.md`,
  `tests/docs/test_pyclient_api_contract.py`,
  `tests/docs/test_pyclient_public_docs.py`
- **Interfaces provided**: `IF-0-PYCLIENT-1 evidence`, `PYCLIENT acceptance verdict`, `docs/status/python-client-api.md`, `Python client versus MCP usage guidance`, `public client stability notes`
- **Interfaces consumed**: `SL-0 public client contract`, `SL-1 direct client evidence`, `SL-2 wrapper compatibility evidence`, `SL-3 verification evidence`, roadmap non-goals (pre-existing), canonical `index-it-mcp` package identity (pre-existing)
- **Parallel-safe**: no
- **Tasks**:
  - test: Add `tests/docs/test_pyclient_api_contract.py` to require docs for
    the supported import path, typed search/status/reindex results, source
    filters, readiness/index-unavailable behavior, and no remote service client.
  - test: Add `tests/docs/test_pyclient_public_docs.py` to require README/API
    guidance that distinguishes direct Python client use from MCP tools and
    keeps `index-it-mcp` as the distribution name.
  - impl: Update `README.md` and `docs/api/API-REFERENCE.md` with concise
    examples for direct Python client use, source filters, readiness handling,
    and when MCP STDIO remains the preferred LLM tool surface.
  - impl: Update `docs/SUPPORT_MATRIX.md` to list the Python client API as a
    supported beta local API without upgrading STDIO/multi-repo beta status.
  - impl: Write `docs/status/python-client-api.md` with metadata-only evidence:
    phase plan reference, API names, source-filter scope, wrapper compatibility,
    verification commands, non-goals, and redaction posture.
  - verify: `uv run pytest tests/docs/test_pyclient_api_contract.py tests/docs/test_pyclient_public_docs.py -q --no-cov`
  - verify: `phase-loop validate-roadmap specs/phase-plans-v9.md`

## Execution Policy

- work-unit defaults: work-unit=`lane_execute`, effort=`medium`, unsupported=`inherit_default`, inherit-default=`true`
- SL-3: executor=`codex`, effort=`medium`, work-unit=`phase_verify`, unsupported=`inherit_default`, inherit-default=`true`
- SL-4: executor=`codex`, effort=`medium`, work-unit=`phase_reducer`, unsupported=`inherit_default`, inherit-default=`true`

## Execution Notes

- Use `uv sync --locked --extra dev` before targeted test execution;
  `pyproject.toml` and `uv.lock` remain dependency truth.
- Preserve STDIO as the primary LLM tool surface. The Python client is a local
  programmatic API for applications/scripts, not a replacement transport for
  assistant tool calls.
- Do not add a remote service client, rename `mcp_server`, change the
  `index-it-mcp` distribution name, remove MCP tools, or alter FRICTION/HISTORY
  source metadata schemas.
- Keep source-filter vocabulary shared across the Python client, MCP
  `search_code`, and FastAPI `/search`; invalid source filters must fail with
  metadata-only typed errors, not silent empty results.
- Treat semantic provider credentials as optional runtime configuration. Tests
  must prove lexical/source-filter paths without live provider keys.

## Acceptance Criteria

- [ ] `tests/test_python_client_contract.py` and
      `tests/test_python_client_search.py` prove `mcp_server.client` exposes
      supported typed local APIs for `search_code`, `symbol_lookup`, `reindex`,
      and `get_status` without starting MCP STDIO, FastAPI, or any remote
      service client.
- [ ] The direct Python client supports source filters for ordinary code,
      friction metadata, and historical issue records, including optional source
      metadata inclusion, as proved by `tests/test_python_client_sources.py`.
- [ ] `tests/test_python_client_indexing.py` proves non-ready or
      unsupported-worktree repositories return typed readiness-aware
      `index_unavailable` data with `safe_fallback="native_search"` rather than
      dispatching against a stale index.
- [ ] `tests/test_python_client_mcp_wrapper.py`, `tests/test_gateway.py`,
      `tests/test_friction_tool_handlers.py`, and
      `tests/test_history_tool_handlers.py` prove MCP `search_code` and FastAPI
      `/search` use the shared client/service behavior while preserving schemas,
      source filters, semantic metadata, and legacy unfiltered response shape.
- [ ] `tests/test_python_client_contract.py` proves `mcp_server.__init__`
      exports the supported client names while preserving existing lazy exports
      and the canonical `index-it-mcp` distribution identity.
- [ ] `uv run pytest tests/test_python_client_search.py tests/test_python_client_sources.py tests/test_python_client_indexing.py -q --no-cov`
      passes without live provider credentials, live GitHub access, MCP STDIO
      startup, or FastAPI startup.
- [ ] `uv run pytest tests/smoke/test_mcpbase_stdio_smoke.py tests/smoke/test_secondary_tool_readiness_smoke.py -q --no-cov`
      proves existing MCP STDIO and secondary readiness smoke tests still pass.
- [ ] `tests/docs/test_pyclient_api_contract.py` and
      `tests/docs/test_pyclient_public_docs.py` prove README, API docs, support
      matrix, and `docs/status/python-client-api.md` explain when to use the
      Python client versus MCP tools and record metadata-only verification
      evidence.
- [ ] `make agent-full` and `phase-loop validate-roadmap specs/phase-plans-v9.md`
      pass without package renames, MCP tool removal, hosted CI changes, or
      release dispatch.

## Verification

`automation.suite_command`: `make agent-full`

Lane-specific verification commands are listed under each lane. Whole-phase
verification:

```bash
uv sync --locked --extra dev
uv run pytest tests/test_python_client_contract.py tests/test_python_client_search.py tests/test_python_client_sources.py tests/test_python_client_indexing.py tests/test_python_client_mcp_wrapper.py tests/test_friction_tool_handlers.py tests/test_history_tool_handlers.py tests/test_gateway.py tests/test_tool_schema_handler_parity.py tests/test_stdio_tool_descriptions.py tests/docs/test_pyclient_api_contract.py tests/docs/test_pyclient_public_docs.py -q --no-cov
uv run pytest tests/smoke/test_mcpbase_stdio_smoke.py tests/smoke/test_secondary_tool_readiness_smoke.py -q --no-cov
make agent-full
phase-loop validate-roadmap specs/phase-plans-v9.md
git status --short -- \
  mcp_server/client_types.py \
  mcp_server/client.py \
  mcp_server/__init__.py \
  mcp_server/dispatcher/protocol.py \
  mcp_server/cli/tool_handlers.py \
  mcp_server/gateway.py \
  README.md \
  docs/api/API-REFERENCE.md \
  docs/SUPPORT_MATRIX.md \
  docs/status/python-client-api.md \
  tests/test_python_client_contract.py \
  tests/test_python_client_search.py \
  tests/test_python_client_sources.py \
  tests/test_python_client_indexing.py \
  tests/test_python_client_mcp_wrapper.py \
  tests/test_friction_tool_handlers.py \
  tests/test_history_tool_handlers.py \
  tests/test_gateway.py \
  tests/docs/test_pyclient_api_contract.py \
  tests/docs/test_pyclient_public_docs.py \
  plans/phase-plan-v9-PYCLIENT.md
```

Next phase: PYCLIENT - execution ready
Next command: codex-execute-phase plans/phase-plan-v9-PYCLIENT.md

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v9-PYCLIENT.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v9-PYCLIENT.md
  artifact_state: staged
```
