# Phase roadmap v8

## Context

The v7 roadmap closed the semantic dogfood hardening track. The next product
question is whether Code-Index-MCP is current with the latest Model Context
Protocol specification and how to modernize the exposed MCP surface without
destabilizing the local-first indexing runtime.

As of the latest checked official specification, the stable MCP revision is
`2025-11-25`. This repository already consumes the official Python MCP SDK and
locks `mcp==1.27.0` in `uv.lock`, so the likely gap is not basic protocol
negotiation. The gap is the quality and completeness of the MCP-facing surface:
modern tool metadata, typed structured results, task support for long-running
operations, clear STDIO versus HTTP transport boundaries, and remote auth only
if remote MCP is intentionally supported.

Current repo facts:

- `mcp_server/cli/stdio_runner.py` is the primary MCP STDIO server.
- `mcp_server/cli/server_commands.py` starts the FastAPI admin/debug API; that
  API should not be treated as MCP Streamable HTTP unless explicitly adapted.
- Tool definitions currently advertise `name`, `description`, and
  `inputSchema`; they do not yet freeze `title`, annotations, output schemas,
  task support, deterministic ordering, or structured result compatibility.
- `reindex` and `write_summaries` are the natural long-running MCP operations.

Specification references to preserve in implementation notes:

- `https://modelcontextprotocol.io/specification/2025-11-25`
- `https://modelcontextprotocol.io/specification/2025-11-25/server/tools`
- `https://modelcontextprotocol.io/specification/2025-11-25/basic/utilities/tasks`
- `https://modelcontextprotocol.io/specification/2025-11-25/basic/transports`
- `https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization`
- `https://modelcontextprotocol.io/specification/draft/changelog`

## Architecture North Star

Code-Index-MCP should remain a local-first MCP server with STDIO as the
default and best-supported transport. The MCP tool surface should be explicit,
typed, discoverable, and backward compatible:

```text
official Python SDK -> STDIO initialize/tools/list/tools/call
                    -> typed tool schemas and annotations
                    -> structuredContent plus text fallback
                    -> task-capable long-running mutations
                    -> optional separate Streamable HTTP MCP surface only if needed
```

The FastAPI admin/debug API may continue to exist, but it must be documented as
non-MCP unless a later phase deliberately adds a spec-compliant Streamable HTTP
MCP endpoint with appropriate authorization.

## Assumptions

- `mcp==1.27.0` or newer remains the Python SDK dependency during this roadmap.
- The primary supported client path remains STDIO through `python -m
  mcp_server.cli.stdio_runner`.
- Existing tool names remain stable for backward compatibility:
  `symbol_lookup`, `search_code`, `get_status`, `list_plugins`, `reindex`,
  `write_summaries`, `summarize_sample`, and `handshake`.
- Existing JSON payload shapes should remain available in text content until
  downstream clients prove they only consume `structuredContent`.
- `MCP_CLIENT_SECRET` remains a local STDIO guard, not a replacement for
  spec-compliant remote MCP authorization.
- Remote MCP is a product decision; it should not be implied by the existing
  FastAPI admin API.

## Non-Goals

- No package release dispatch.
- No change to indexing semantics, semantic dogfood contracts, or multi-repo
  readiness contracts except where MCP output schemas must describe them.
- No replacement of the Python SDK with another framework.
- No removal of JSON text fallback responses.
- No OAuth provider implementation unless the remote MCP decision phase chooses
  to build a Streamable HTTP MCP endpoint.
- No broad rewrite of the FastAPI admin/debug API.

## Cross-Cutting Principles

- Preserve current client compatibility while adding modern MCP affordances.
- Prefer typed contracts over prose-only payloads.
- Keep long-running mutable operations cancellable and inspectable.
- Keep STDIO and remote MCP transport claims separate.
- Make every metadata addition testable through `tools/list`.
- Make every structured result addition testable through direct `tools/call`
  handler tests and at least one SDK-level STDIO smoke.
- Treat MCP spec references as living sources; pin behavior to the stable
  `2025-11-25` contract unless a later phase explicitly opts into draft fields.

## Top Interface-Freeze Gates

- IF-0-MCPBASE-1 — Stable MCP baseline contract: STDIO startup, initialize,
  `tools/list`, and representative `tools/call` behavior are verified against
  the official Python SDK path and documented as targeting MCP `2025-11-25`.
- IF-0-MCPMETA-1 — Tool metadata contract: each public tool has deterministic
  ordering, `title`, JSON Schema input constraints, annotations, and an
  implementation-owned output schema.
- IF-0-MCPSTRUCT-1 — Structured result contract: each public tool can return
  machine-readable `structuredContent` while preserving text JSON fallback for
  compatibility.
- IF-0-MCPTASKS-1 — Task-capable operation contract: long-running `reindex`
  and `write_summaries` can advertise and execute task-backed progress,
  polling, cancellation, and terminal result retrieval.
- IF-0-MCPTRANSPORT-1 — Transport boundary contract: STDIO remains primary;
  FastAPI admin endpoints are documented as non-MCP unless a distinct
  Streamable HTTP MCP endpoint is implemented.
- IF-0-MCPAUTH-1 — Authorization contract: local STDIO auth and any remote MCP
  auth are separate, documented, and fail closed without exposing secrets.
- IF-0-MCPEVAL-1 — Compatibility evidence contract: MCP Inspector or
  equivalent SDK-level smokes prove modern metadata, structured results, and
  task behavior from the client perspective.

## Phases

### Phase 1 — MCP Baseline Compatibility Audit (MCPBASE)

**Objective**

Freeze the current MCP baseline and add explicit compatibility evidence before
changing the public tool surface.

**Exit criteria**
- [ ] A focused SDK-level smoke proves STDIO `initialize`, `tools/list`, and
      representative `tools/call` still work through the official Python SDK.
- [ ] The current `mcp` SDK version and targeted MCP spec revision are surfaced
      in a docs/status artifact.
- [ ] Existing tool names and no-argument tool behavior are documented as
      compatibility constraints.
- [ ] Tests prove `mcp-index serve` is not documented or advertised as MCP
      Streamable HTTP.
- [ ] No tool metadata or result-shape migration is performed in this phase.

**Scope notes**

This is an evidence and contract phase. It should add tests and documentation
that make later changes safer.

**Non-goals**

- No structured result migration.
- No task implementation.
- No remote MCP endpoint.

**Key files**

- `mcp_server/cli/stdio_runner.py`
- `mcp_server/cli/server_commands.py`
- `tests/test_mcp_server_cli.py`
- `tests/test_stdio_tool_descriptions.py`
- `docs/status/`
- `README.md`

**Depends on**
- (none)

**Produces**
- IF-0-MCPBASE-1 — Stable MCP baseline contract.

### Phase 2 — Modern Tool Metadata And Schemas (MCPMETA)

**Objective**

Upgrade `tools/list` to advertise modern, deterministic, agent-friendly tool
metadata while preserving tool names and handler behavior.

**Exit criteria**
- [ ] `tools/list` ordering is deterministic and covered by tests.
- [ ] Every public tool has a human-friendly `title`.
- [ ] Every tool input schema is explicit about accepted fields, required
      fields, defaults, and additional-property behavior where SDK support
      allows it.
- [ ] Read-only versus mutating tools advertise annotations such as read-only,
      destructive, idempotent, and open-world posture where supported by the
      SDK type model.
- [ ] Every tool has a documented output schema draft, even if structured
      result emission is deferred to `MCPSTRUCT`.
- [ ] Existing handler tests and tool-schema parity tests pass unchanged except
      for new metadata assertions.

**Scope notes**

This phase should focus on `types.Tool` construction and schema tests. It may
add helper builders to avoid duplicating schema fragments.

**Non-goals**

- No change to `call_tool` response values.
- No task execution.
- No transport changes.

**Key files**

- `mcp_server/cli/stdio_runner.py`
- `tests/test_stdio_tool_descriptions.py`
- `tests/test_tool_schema_handler_parity.py`
- `tests/docs/test_p7_schema_alignment.py`
- `README.md`

**Depends on**
- MCPBASE

**Produces**
- IF-0-MCPMETA-1 — Tool metadata contract.

### Phase 3 — Structured Tool Results (MCPSTRUCT)

**Objective**

Return typed `structuredContent` for public tools while retaining text JSON
fallback payloads for older clients.

**Exit criteria**
- [ ] `symbol_lookup`, `search_code`, `get_status`, `list_plugins`,
      `summarize_sample`, `reindex`, `write_summaries`, and `handshake` each
      have an output schema aligned with their actual payload.
- [ ] Tool handlers can produce structured payloads without losing the current
      text JSON content.
- [ ] Error responses have a consistent structured shape with `code`,
      `message`, remediation, readiness, and safe fallback fields where
      applicable.
- [ ] Readiness-related responses preserve existing `index_unavailable`,
      `path_outside_allowed_roots`, and `safe_fallback: native_search`
      semantics.
- [ ] Tests cover both direct handler calls and MCP `tools/call` results for
      structured and text fallback content.

**Scope notes**

Prefer a small response adapter layer over changing every handler at once.
Keep payload contracts close to current dictionaries so downstream clients do
not need a migration.

**Non-goals**

- No task-backed execution.
- No remote MCP endpoint.
- No deletion of legacy text content.

**Key files**

- `mcp_server/cli/stdio_runner.py`
- `mcp_server/cli/tool_handlers.py`
- `tests/test_mcp_server_cli.py`
- `tests/test_tool_handlers_readiness.py`
- `tests/test_tool_readiness_fail_closed.py`
- `tests/test_handler_path_sandbox.py`

**Depends on**
- MCPMETA

**Produces**
- IF-0-MCPSTRUCT-1 — Structured result contract.

### Phase 4 — MCP Task Support For Long-Running Operations (MCPTASKS)

**Objective**

Make long-running mutable operations task-capable so clients can observe,
poll, cancel, and retrieve terminal results instead of blocking blindly.

**Exit criteria**
- [ ] `reindex` and `write_summaries` advertise task support in tool metadata
      where supported by the SDK/spec.
- [ ] A task registry records task ID, tool name, repository, start time,
      progress, cancellation state, terminal status, structured result, and
      error details.
- [ ] Task operations support at least get/list/cancel behavior through the
      SDK-supported MCP task surface or a compatibility tool surface if the SDK
      task API is not yet stable.
- [ ] Cancellation is best-effort and never corrupts index state.
- [ ] Synchronous compatibility remains available for small or immediate
      operations.
- [ ] Tests cover successful task completion, cancellation, failed readiness
      preflight, and terminal result retrieval.

**Scope notes**

Implement task behavior for `reindex` before `write_summaries` if a split is
needed. Do not route short read-only tools through tasks.

**Non-goals**

- No distributed task queue.
- No remote worker orchestration.
- No change to phase-loop task concepts; this is MCP client-facing task
      support only.

**Key files**

- `mcp_server/cli/stdio_runner.py`
- `mcp_server/cli/tool_handlers.py`
- `mcp_server/indexing/`
- `mcp_server/storage/`
- `tests/test_mcp_server_cli.py`
- `tests/test_reindex_resume.py`

**Depends on**
- MCPSTRUCT

**Produces**
- IF-0-MCPTASKS-1 — Task-capable operation contract.

### Phase 5 — Transport Boundary And Optional Streamable HTTP Decision (MCPTRANSPORT)

**Objective**

Make the transport story unambiguous and decide whether to implement a
spec-compliant remote MCP transport.

**Exit criteria**
- [ ] Documentation clearly states that STDIO is the primary MCP transport.
- [ ] Documentation clearly states that current FastAPI endpoints are
      admin/debug endpoints, not MCP Streamable HTTP.
- [ ] If remote MCP is not selected, CLI help and README examples avoid
      implying `mcp-index serve` is MCP transport.
- [ ] If remote MCP is selected, a distinct Streamable HTTP MCP endpoint is
      added with separate routing, lifecycle, and tests.
- [ ] Existing FastAPI admin tests continue to pass.
- [ ] A product decision record explains why remote MCP is deferred or
      implemented.

**Scope notes**

This phase can close as documentation-only if the product decision is to keep
STDIO-only MCP for now.

**Non-goals**

- No OAuth implementation unless remote MCP is selected.
- No rewrite of existing admin endpoints.

**Key files**

- `mcp_server/cli/server_commands.py`
- `mcp_server/gateway.py`
- `README.md`
- `docs/GETTING_STARTED.md`
- `.mcp.json.templates/`
- `tests/`

**Depends on**
- MCPBASE

**Produces**
- IF-0-MCPTRANSPORT-1 — Transport boundary contract.

### Phase 6 — Authorization And Secret Boundary Modernization (MCPAUTH)

**Objective**

Clarify and harden authentication boundaries for local STDIO and any selected
remote MCP surface.

**Exit criteria**
- [ ] `MCP_CLIENT_SECRET` is documented as a local STDIO guard, not
      spec-compliant remote authorization.
- [ ] STDIO credential guidance follows the spec posture of environment-backed
      secrets and no secret leakage in logs or tool output.
- [ ] If remote MCP was selected, the remote endpoint has a spec-aligned
      authorization design using protected resource metadata and OAuth/OIDC
      semantics before accepting non-local traffic.
- [ ] If remote MCP was deferred, docs explicitly say no remote MCP auth is
      implemented.
- [ ] Tests prove handshake errors and authorization failures do not leak
      secrets.

**Scope notes**

Run after the transport decision so the phase does not implement OAuth for a
transport we may not ship.

**Non-goals**

- No new secret storage backend.
- No printed secret values in docs, tests, or logs.

**Key files**

- `mcp_server/cli/handshake.py`
- `mcp_server/cli/stdio_runner.py`
- `mcp_server/security/`
- `tests/test_handshake.py`
- `tests/security/`
- `README.md`

**Depends on**
- MCPTRANSPORT

**Produces**
- IF-0-MCPAUTH-1 — Authorization contract.

### Phase 7 — MCP Compatibility Evidence And Evaluations (MCPEVAL)

**Objective**

Close the modernization roadmap with client-visible proof that the MCP surface
is current, discoverable, structured, and useful.

**Exit criteria**
- [ ] MCP Inspector or equivalent SDK-level smoke covers `initialize`,
      `tools/list`, structured `tools/call`, and task behavior.
- [ ] Documentation includes a compatibility matrix for STDIO, FastAPI admin,
      optional Streamable HTTP MCP if selected, and supported clients.
- [ ] At least ten read-only evaluation prompts exercise code search, symbol
      lookup, readiness failure handling, multi-repo scoping, and semantic
      query behavior.
- [ ] Evaluation expected answers are stable and do not require secrets.
- [ ] Release-readiness docs state what remains intentionally unsupported.

**Scope notes**

This phase should collect evidence and polish docs. It should not introduce new
protocol behavior except small fixes found by client smokes.

**Non-goals**

- No release dispatch.
- No broad product claims beyond verified compatibility.

**Key files**

- `docs/status/`
- `docs/GETTING_STARTED.md`
- `README.md`
- `tests/smoke/`
- `tests/docs/`
- `evaluations/` or `docs/evaluations/`

**Depends on**
- MCPTASKS
- MCPAUTH

**Produces**
- IF-0-MCPEVAL-1 — Compatibility evidence contract.

## Phase Dependency DAG

```text
MCPBASE
  -> MCPMETA
     -> MCPSTRUCT
        -> MCPTASKS
           -> MCPEVAL
  -> MCPTRANSPORT
     -> MCPAUTH
        -> MCPEVAL
```

## Execution Notes

- `MCPBASE` should be planned first because it freezes the evidence baseline.
- After `MCPBASE`, `MCPMETA` and `MCPTRANSPORT` can be planned independently.
- `MCPSTRUCT` depends on `MCPMETA` because output schemas should be frozen
  before response adapters are changed.
- `MCPTASKS` depends on `MCPSTRUCT` because terminal task results should reuse
  structured result contracts.
- `MCPAUTH` depends on `MCPTRANSPORT` because remote authorization scope should
  follow the transport decision.
- `MCPEVAL` should close the roadmap after task and auth/transport decisions
  have settled.

## Verification

Roadmap-level verification commands to plan into later phases:

```bash
uv run pytest tests/test_stdio_tool_descriptions.py tests/test_tool_schema_handler_parity.py -q --no-cov
uv run pytest tests/test_mcp_server_cli.py tests/test_tool_handlers_readiness.py tests/test_tool_readiness_fail_closed.py -q --no-cov
uv run pytest tests/test_handshake.py tests/security/test_route_auth_coverage.py tests/security/test_metrics_auth.py -q --no-cov
uv run pytest tests/smoke -q --no-cov
python -m mcp_server.cli.stdio_runner
```

For any Streamable HTTP MCP implementation phase, add an SDK or inspector smoke
that connects over the new transport rather than only testing FastAPI routes.

## Next Step

Next phase: MCPBASE - MCP Baseline Compatibility Audit
Next command: codex-plan-phase specs/phase-plans-v8.md MCPBASE

```yaml
automation:
  status: unplanned
  next_skill: codex-plan-phase
  next_command: codex-plan-phase specs/phase-plans-v8.md MCPBASE
  next_model_hint: plan
  next_effort_hint: high
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/specs/phase-plans-v8.md
  artifact_state: untracked
```
