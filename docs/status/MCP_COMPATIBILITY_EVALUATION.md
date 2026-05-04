# MCP Compatibility Evaluation

MCPEVAL is the closing reducer for the v8 MCP modernization roadmap. This
artifact turns the previously landed metadata, structured-result, task,
transport, and auth changes into one current client-facing compatibility
statement.

## Scope

- MCP spec target: `2025-11-25`
- Locked official Python SDK observed in this repo: `mcp==1.27.0`
- Primary MCP surface evaluated here: `mcp-index stdio` /
  `python -m mcp_server.cli.stdio_runner`
- Secondary HTTP surface: FastAPI admin/debug only; not an MCP transport.
  FastAPI is the admin/debug HTTP surface for this repository.

## Observed client evidence

The phase-owned smoke `tests/smoke/test_mcpeval_sdk_surface.py` proves the
official Python SDK can:

- initialize the STDIO server and observe MCP task capabilities
- list tools with deterministic metadata including `title`, `outputSchema`, and
  `execution.taskSupport`
- call ready-path tools and receive object-shaped `structuredContent` plus JSON
  text fallback
- observe fail-closed readiness behavior with `index_unavailable` and
  `safe_fallback: "native_search"` for an unsupported linked worktree
- create a task-backed `reindex`, poll `tasks/get`, inspect `tasks/list`, and
  retrieve the terminal `tasks/result` payload

## Compatibility matrix

| Surface | Current posture | Evidence | Notes |
|---|---|---|---|
| Official Python MCP SDK over STDIO | Verified | `tests/smoke/test_mcpbase_stdio_smoke.py`, `tests/smoke/test_mcpeval_sdk_surface.py` | Phase-owned end-to-end evidence for initialize, tools/list, tools/call, and tasks |
| Claude Code over STDIO | Documented, contract-aligned | `README.md`, `docs/GETTING_STARTED.md`, `docs/MCP_CONFIGURATION.md` | Inference from the same STDIO server contract and checked config examples; no separate vendor-harness smoke in MCPEVAL |
| Cursor or another editor that launches STDIO MCP servers | Documented, not separately phase-smoked | `docs/GETTING_STARTED.md`, `docs/MCP_CONFIGURATION.md` | Expected only if the client honors the standard STDIO MCP tools/tasks contract |
| FastAPI admin/debug HTTP gateway | Supported as admin/debug HTTP only | `docs/validation/mcp-transport-decision.md` | Not an MCP transport and not a Streamable HTTP endpoint |
| Streamable HTTP MCP | Deferred | `docs/validation/mcp-transport-decision.md` | Requires a distinct remote MCP phase, endpoint, tests, and auth story before support claims expand |

## Prompt-pack coverage

`docs/evaluations/mcpeval-prompt-pack.md` freezes a read-only prompt corpus with
stable answer constraints for:

- `get_status` posture
- ready-path `search_code`
- ready-path `symbol_lookup`
- readiness failure handling with `index_unavailable`
- multi-repo scoping with the `repository` argument
- unsupported sibling worktrees
- semantic-query refusal posture
- task-oriented `reindex` guidance
- transport and auth boundary reminders

## Unsupported or deferred surfaces

- Remote MCP transport is intentionally deferred in v8.
- The FastAPI gateway is intentionally documented as admin/debug HTTP, not MCP.
- `MCP_CLIENT_SECRET` is a local STDIO handshake guard only; it is not remote
  MCP authorization.
- Same-repo sibling worktrees and non-ready repository states remain fail-closed
  for query trust. Clients must honor `index_unavailable` instead of treating
  the repo as queried successfully.
- Semantic query support remains readiness-gated and may refuse with
  semantic-specific metadata when summaries or vectors are not ready.

## Verification commands

```bash
uv run pytest \
  tests/smoke/test_mcpbase_stdio_smoke.py \
  tests/smoke/test_mcpeval_sdk_surface.py \
  tests/docs/test_mcpeval_prompt_pack.py \
  tests/docs/test_mcpeval_surface_matrix.py \
  tests/docs/test_mcpeval_evidence_contract.py \
  -q --no-cov
```
