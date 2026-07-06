---
phase_loop_plan_version: 1
phase: MCPSTRUCT
roadmap: specs/phase-plans-v8.md
roadmap_sha256: 25aa1501b52e5038cbcc0356638d2a5de5aaaea75c32e21c03de8a1db6a99a11
---
# MCPSTRUCT: Structured Tool Results

## Context

MCPSTRUCT is the v8 phase that turns the existing MCPMETA catalog work into a
real structured `tools/call` surface while preserving the current JSON text
fallback for older clients.

Current repo state gathered during planning:

- `specs/phase-plans-v8.md` is the active tracked roadmap, and
  `sha256sum specs/phase-plans-v8.md` matches the required
  `25aa1501b52e5038cbcc0356638d2a5de5aaaea75c32e21c03de8a1db6a99a11`.
- Canonical runner files exist under `.phase-loop/`, but
  `.phase-loop/state.json` still points at `c2e8393` and marks `MCPMETA` as
  `unplanned`. Git reality has moved past that snapshot:
  `git log --oneline -6` shows later `phase-loop closeout: MCPMETA` commits
  `1b693b1` and `08c1384`, the worktree is currently clean, and `HEAD` already
  contains MCPMETA-era code and tests. Per shared runtime-state reconciliation,
  filesystem and git reality win over stale ledger claims, so planning
  MCPSTRUCT against `HEAD` is safe.
- `mcp_server/cli/stdio_runner.py::_build_tool_list()` already advertises
  `title`, `annotations`, and `outputSchema` for all eight public tools, but
  the runtime `call_tool()` surface is still text-only and returns
  `Sequence[types.TextContent | types.ImageContent | types.EmbeddedResource]`.
- `uv run python` inspection of the locked SDK shows
  `mcp.types.CallToolResult(content=[...], structuredContent=dict | None, isError=bool)`.
  The critical constraint is that `structuredContent` is an object, not a raw
  array or string.
- That object-only constraint does not match every current MCPMETA schema
  branch. `search_code` still advertises a top-level array success branch, and
  `reindex` still advertises a top-level string branch for single-file success
  and failure paths.
- `mcp_server/cli/tool_handlers.py` is already close to a structured surface
  because most handlers emit JSON dictionaries through `_ensure_response(...)`,
  but `handle_reindex()` still returns free-form strings for single-file
  success and error branches, and several error families are inconsistent about
  `code` and `message`.
- `tests/test_mcp_server_cli.py` and the handler/readiness suites currently
  assume `call_tool()` returns text content and parse `result[0].text`.
- `README.md` still states that richer metadata is present now while structured
  `call_tool` payloads remain deferred to `MCPSTRUCT`. That wording must flip
  in this phase without widening into task, transport, or auth claims.

Practical planning boundary:

- MCPSTRUCT may update `stdio_runner.py`, `tool_handlers.py`, their direct
  tests, and the narrow README surface that documents `tools/call`.
- MCPSTRUCT must preserve the current JSON text fallback content for
  compatibility, keep readiness fail-closed semantics intact, and avoid
  introducing task execution, Streamable HTTP transport, or auth changes.

## Interface Freeze Gates

- [ ] IF-0-MCPSTRUCT-1 - Structured `tools/call` contract:
      every public tool returns an SDK-native `mcp.types.CallToolResult`
      carrying `structuredContent` plus text JSON fallback content, rather than
      a text-only content sequence.
- [ ] IF-0-MCPSTRUCT-2 - Object-envelope schema contract:
      every tool `outputSchema` used for structured results is object-shaped
      and compatible with `CallToolResult.structuredContent`, even when legacy
      text fallback content remains a top-level array or string.
- [ ] IF-0-MCPSTRUCT-3 - Handler payload normalization contract:
      tool handler success and error families are JSON-object compatible with
      the structured adapter, including single-file `reindex` paths and other
      previously free-form text branches.
- [ ] IF-0-MCPSTRUCT-4 - Fail-closed readiness contract:
      `index_unavailable`, `path_outside_allowed_roots`,
      `conflicting_path_and_repository`, and secondary readiness refusals keep
      their current semantics, `safe_fallback: "native_search"` behavior where
      applicable, and readiness/remediation metadata.
- [ ] IF-0-MCPSTRUCT-5 - Public contract docs gate:
      `README.md` accurately states that structured `tools/call` results now
      exist, while legacy JSON text fallback remains available and task,
      transport, and auth work remain deferred to later phases.

## Lane Index & Dependencies

- SL-0 - `CallToolResult` adapter and object-envelope schema freeze; Depends on: (none); Blocks: SL-1, SL-2; Parallel-safe: yes
- SL-1 - Handler payload normalization for structured result parity; Depends on: SL-0; Blocks: SL-2; Parallel-safe: yes
- SL-2 - README truth and MCPSTRUCT closeout docs; Depends on: SL-0, SL-1; Blocks: MCPSTRUCT acceptance; Parallel-safe: no

Lane DAG:

```text
SL-0 -----> SL-1 ----\
   \                  -> SL-2 -> MCPSTRUCT acceptance
    -----------------/
```

## Lanes

### SL-0 - `CallToolResult` Adapter And Object-Envelope Schema Freeze

- **Scope**: Convert the module-level MCP `call_tool()` surface to return
  `mcp.types.CallToolResult` with object-shaped `structuredContent`, while
  preserving the existing JSON text fallback payloads and aligning
  `outputSchema` branches to the object-only SDK contract.
- **Owned files**: `mcp_server/cli/stdio_runner.py`, `tests/test_mcp_server_cli.py`, `tests/test_stdio_tool_descriptions.py`, `tests/test_tool_schema_handler_parity.py`, `tests/docs/test_mcpstruct_call_tool_contract.py`
- **Interfaces provided**: IF-0-MCPSTRUCT-1 structured `tools/call` contract;
  IF-0-MCPSTRUCT-2 object-envelope schema contract;
  structured adapter rules consumed by SL-1 and SL-2
- **Interfaces consumed**: current MCPMETA tool catalog from
  `_build_tool_list()`; current text JSON payloads returned by
  `mcp_server/cli/tool_handlers.py`; locked SDK `mcp.types.CallToolResult`;
  existing `call_tool()` handshake, initialization-failure, unknown-tool, and
  top-level exception branches
- **Parallel-safe**: yes
- **Tasks**:
  - test: Add `tests/docs/test_mcpstruct_call_tool_contract.py` to freeze that
    public `call_tool()` responses are `CallToolResult` objects with populated
    `content`, object-shaped `structuredContent`, and `isError` set on error
    families.
  - test: Extend `tests/test_mcp_server_cli.py` so direct `call_tool()` tests
    no longer assume `result[0].text`; they should assert both the preserved
    text JSON fallback and the new structured object view.
  - test: Extend `tests/test_stdio_tool_descriptions.py` and
    `tests/test_tool_schema_handler_parity.py` so `search_code` and `reindex`
    no longer advertise top-level array or string structured-result branches.
  - impl: Add a narrow adapter in `mcp_server/cli/stdio_runner.py` that turns
    current JSON text payloads into `CallToolResult` objects without moving
    business logic out of the handlers.
  - impl: Wrap legacy top-level array success payloads such as lexical
    `search_code` results into object-shaped `structuredContent`
    envelopes, while preserving the original text JSON payload unchanged in the
    fallback `content`.
  - impl: Route initialization failure, handshake failure/success, unknown tool
    responses, and top-level exception handling through the same adapter so all
    public tools share one structured result path.
  - impl: Update `outputSchema` branches in `_build_tool_list()` so structured
    result schemas match the object envelopes actually emitted through
    `CallToolResult.structuredContent`.
  - impl: Do not add task execution metadata, transport behavior, or auth
    changes here; this lane is strictly about result shape and adapter wiring.
  - verify: `uv run pytest tests/test_mcp_server_cli.py tests/test_stdio_tool_descriptions.py tests/test_tool_schema_handler_parity.py tests/docs/test_mcpstruct_call_tool_contract.py -q --no-cov`
  - verify: `uv run python - <<'PY'\nfrom mcp_server.cli import stdio_runner\nresult = stdio_runner.call_tool\nprint(result)\nPY`

### SL-1 - Handler Payload Normalization For Structured Result Parity

- **Scope**: Normalize the remaining handler-side payload families so the
  structured adapter can surface every public tool through a stable object
  contract without losing current fail-closed behavior.
- **Owned files**: `mcp_server/cli/tool_handlers.py`, `tests/test_tool_handlers_readiness.py`, `tests/test_tool_readiness_fail_closed.py`, `tests/test_handler_path_sandbox.py`
- **Interfaces provided**: IF-0-MCPSTRUCT-3 handler payload normalization
  contract; IF-0-MCPSTRUCT-4 fail-closed readiness contract;
  object-compatible payload families consumed by SL-0 and documented by SL-2
- **Interfaces consumed**: SL-0 object-envelope rules; existing readiness
  helpers `_index_unavailable_response(...)`,
  `_secondary_readiness_refusal_response(...)`, and path/conflict error
  branches; current `handle_reindex()` single-file success/error branches
- **Parallel-safe**: yes
- **Tasks**:
  - test: Extend `tests/test_tool_handlers_readiness.py` and
    `tests/test_tool_readiness_fail_closed.py` so the structured-eligible
    payload families assert explicit `code`, `message`, readiness, remediation,
    `safe_fallback`, `mutation_performed`, or `persisted` fields where the
    roadmap requires them.
  - test: Extend `tests/test_handler_path_sandbox.py` so path sandbox and
    conflicting-scope responses remain fail-closed while becoming easier to map
    into structured result envelopes.
  - impl: Replace `handle_reindex()` single-file success and failure string
    responses with JSON-object payloads that still preserve the current user
    information but align with `outputSchema` and structured result emission.
  - impl: Normalize any remaining handler-side error families that are missing
    `code` or `message` when that omission would force the adapter to invent
    semantics upstream.
  - impl: Preserve existing readiness codes and contracts exactly where they
    already matter: `index_unavailable`, `path_outside_allowed_roots`,
    `conflicting_path_and_repository`, and the `safe_fallback: "native_search"`
    surface on read-only query refusals.
  - impl: Keep legacy text JSON fallback viable. This lane should make payloads
    more regular, not replace them with a brand-new schema family.
  - verify: `uv run pytest tests/test_tool_handlers_readiness.py tests/test_tool_readiness_fail_closed.py tests/test_handler_path_sandbox.py -q --no-cov`
  - verify: `rg -n "Reindexed file:|Error reindexing|path_outside_allowed_roots|index_unavailable|conflicting_path_and_repository" mcp_server/cli/tool_handlers.py tests/test_tool_handlers_readiness.py tests/test_tool_readiness_fail_closed.py tests/test_handler_path_sandbox.py`

### SL-2 - README Truth And MCPSTRUCT Closeout Docs

- **Scope**: Update the narrow README surface that documents `tools/call` so
  users can see that structured results now exist and that JSON text fallback
  is preserved for compatibility.
- **Owned files**: `README.md`, `tests/docs/test_mcpmeta_readme_alignment.py`, `tests/docs/test_mcpstruct_readme_alignment.py`
- **Interfaces provided**: IF-0-MCPSTRUCT-5 public contract docs gate;
  closeout proof that MCPSTRUCT changed result shape but not task, transport,
  or auth posture
- **Interfaces consumed**: SL-0 `CallToolResult` behavior and object-envelope
  rules; SL-1 preserved readiness/fallback semantics; current README sentence
  that defers structured results to MCPSTRUCT
- **Parallel-safe**: no
- **Tasks**:
  - test: Add `tests/docs/test_mcpstruct_readme_alignment.py` to freeze the
    README claims that `tools/call` now returns structured results, preserves
    JSON text fallback content, and retains the readiness/native-search
    fallback story for non-ready indexes.
  - impl: Replace the current MCPMETA-era deferral wording in `README.md` with
    a concise MCPSTRUCT explanation of `structuredContent`, `content` fallback,
    and `isError`.
  - impl: Keep this doc edit narrow. Do not claim task progress, Streamable
    HTTP, remote auth, or any other later-roadmap behavior here.
  - impl: If additional wording is needed to explain object-wrapped structured
    results for legacy array/string payloads, keep it limited to one concise
    paragraph near the existing MCP tool-surface section.
  - verify: `uv run pytest tests/docs/test_mcpstruct_readme_alignment.py -q --no-cov`
  - verify: `rg -n "structuredContent|CallToolResult|JSON text fallback|native_search|MCPSTRUCT" README.md tests/docs/test_mcpstruct_readme_alignment.py`

## Verification

Planning-only work is complete once this artifact is written and staged. Do
not execute the commands below during plan creation; run them during
`codex-execute-phase` or manual MCPSTRUCT execution.

Lane-specific checks:

```bash
uv run pytest \
  tests/test_mcp_server_cli.py \
  tests/test_stdio_tool_descriptions.py \
  tests/test_tool_schema_handler_parity.py \
  tests/docs/test_mcpstruct_call_tool_contract.py \
  -q --no-cov

uv run pytest \
  tests/test_tool_handlers_readiness.py \
  tests/test_tool_readiness_fail_closed.py \
  tests/test_handler_path_sandbox.py \
  -q --no-cov

uv run pytest tests/docs/test_mcpstruct_readme_alignment.py -q --no-cov
```

Whole-phase verification after code changes:

```bash
uv run pytest \
  tests/test_mcp_server_cli.py \
  tests/test_stdio_tool_descriptions.py \
  tests/test_tool_schema_handler_parity.py \
  tests/test_tool_handlers_readiness.py \
  tests/test_tool_readiness_fail_closed.py \
  tests/test_handler_path_sandbox.py \
  tests/docs/test_mcpstruct_call_tool_contract.py \
  tests/docs/test_mcpstruct_readme_alignment.py \
  -q --no-cov

git status --short -- \
  mcp_server/cli/stdio_runner.py \
  mcp_server/cli/tool_handlers.py \
  README.md \
  tests/test_mcp_server_cli.py \
  tests/test_stdio_tool_descriptions.py \
  tests/test_tool_schema_handler_parity.py \
  tests/test_tool_handlers_readiness.py \
  tests/test_tool_readiness_fail_closed.py \
  tests/test_handler_path_sandbox.py \
  tests/docs/test_mcpstruct_call_tool_contract.py \
  tests/docs/test_mcpstruct_readme_alignment.py \
  plans/phase-plan-v8-MCPSTRUCT.md
```

## Acceptance Criteria

- [ ] Every public tool returns `mcp.types.CallToolResult` with object-shaped
      `structuredContent`, preserved text JSON fallback content, and correct
      `isError` behavior for error families.
- [ ] Tool `outputSchema` branches are compatible with
      `CallToolResult.structuredContent` and no longer depend on top-level
      array or string structured-result shapes.
- [ ] `handle_reindex()` and any remaining handler-side free-form text branches
      are normalized into JSON-object payload families that the structured
      adapter can expose without inventing semantics.
- [ ] Readiness-related responses preserve current fail-closed behavior,
      including `index_unavailable`, `path_outside_allowed_roots`,
      `conflicting_path_and_repository`, and
      `safe_fallback: "native_search"` where already applicable.
- [ ] Direct `call_tool()` tests and handler/readiness suites cover both the
      structured result surface and the preserved text fallback surface.
- [ ] `README.md` accurately states that structured results now exist and that
      JSON text fallback remains available for older clients.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v8-MCPSTRUCT.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v8-MCPSTRUCT.md
  artifact_state: staged
```
