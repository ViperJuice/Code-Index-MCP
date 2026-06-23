---
phase_loop_plan_version: 1
phase: MCPMETA
roadmap: specs/phase-plans-v8.md
roadmap_sha256: 25aa1501b52e5038cbcc0356638d2a5de5aaaea75c32e21c03de8a1db6a99a11
---
# MCPMETA: Modern Tool Metadata And Schemas

## Context

MCPMETA is the next execution phase after the completed MCPBASE baseline
freeze. Its job is to modernize `tools/list` metadata without changing current
`call_tool` behavior.

Current repo state gathered during planning:

- `specs/phase-plans-v8.md` is the active tracked roadmap, and
  `sha256sum specs/phase-plans-v8.md` matches the required
  `25aa1501b52e5038cbcc0356638d2a5de5aaaea75c32e21c03de8a1db6a99a11`.
- Canonical runner state exists under `.phase-loop/`. `.phase-loop/state.json`
  marks `MCPBASE` as `complete`, `MCPMETA` as the current `unplanned` phase,
  the worktree as clean, and the branch as `roadmap-v8-mcp-modernization`.
  Legacy `.codex/phase-loop/` artifacts are compatibility-only and are not
  authoritative for this run.
- `plans/phase-plan-v8-MCPBASE.md` already established the v8 planning style
  in this checkout and records `MCPMETA` as the next downstream planning step.
- `mcp_server/cli/stdio_runner.py::_build_tool_list()` currently returns the
  eight public tools in a list literal order:
  `symbol_lookup`, `search_code`, `get_status`, `list_plugins`, `reindex`,
  `write_summaries`, `summarize_sample`, and `handshake`.
- The current tool entries expose `name`, `description`, and `inputSchema`,
  but do not yet populate the SDK-supported `title`, `annotations`, or
  `outputSchema` fields. Runtime inspection of the locked MCP SDK shows
  `mcp.types.Tool` already supports `title`, `annotations`, and
  `outputSchema`, and `mcp.types.ToolAnnotations` supports
  `title`, `readOnlyHint`, `destructiveHint`, `idempotentHint`, and
  `openWorldHint`.
- Existing tests already freeze useful pieces of the contract:
  `tests/test_stdio_tool_descriptions.py` covers readiness wording and the
  empty-object contract for `get_status` and `list_plugins`;
  `tests/test_tool_schema_handler_parity.py` checks repository-property parity
  between schemas and handlers; and `tests/docs/test_p7_schema_alignment.py`
  freezes repository-property presence and wording.
- `mcp_server/cli/tool_handlers.py` still returns text-only JSON payloads with
  several distinct response families: read-only success payloads, ready-but-miss
  payloads, readiness refusals such as `index_unavailable`, path sandbox
  failures such as `path_outside_allowed_roots`, and mutation summaries for
  `reindex`, `write_summaries`, and `summarize_sample`. `search_code` is
  especially polymorphic because its success payload differs between plain and
  semantic searches. MCPMETA therefore needs output-schema drafts that are
  faithful to current handler families without changing runtime emission yet.
- `README.md` already documents STDIO as the primary MCP surface and FastAPI as
  secondary/admin. MCPMETA should extend the docs only enough to describe the
  richer `tools/list` metadata contract and the fact that `call_tool` payload
  changes remain deferred to `MCPSTRUCT`.

Practical planning boundary:

- MCPMETA may refactor tool construction inside `stdio_runner.py`, add helper
  schema/annotation builders there, extend tool metadata tests, and tighten
  README truth around discoverable metadata.
- MCPMETA must not change `tool_handlers.py` return payloads, add
  `structuredContent`, introduce task execution, or broaden the transport/auth
  story.

## Interface Freeze Gates

- [ ] IF-0-MCPMETA-1 - Deterministic tool catalog contract:
      `tools/list` preserves the current public tool order
      `symbol_lookup -> search_code -> get_status -> list_plugins -> reindex -> write_summaries -> summarize_sample -> handshake`,
      and that order is frozen by tests rather than relying on incidental list
      construction.
- [ ] IF-0-MCPMETA-2 - Tool identity metadata contract:
      every public tool advertises a stable `name` plus a human-friendly
      `title`, and the title map is frozen in repo tests so later phases can
      add behavior without silently renaming the MCP surface.
- [ ] IF-0-MCPMETA-3 - Input schema strictness contract:
      every tool input schema explicitly declares `type`, `properties`,
      `required`, defaults where applicable, and `additionalProperties`
      behavior; zero-argument tools remain callable via `{}` with no newly
      required fields.
- [ ] IF-0-MCPMETA-4 - Annotation posture contract:
      every public tool has an explicit `annotations` object whose
      `readOnlyHint`, `destructiveHint`, `idempotentHint`, and
      `openWorldHint` values match current local-first behavior and mutation
      boundaries rather than generic defaults.
- [ ] IF-0-MCPMETA-5 - Output schema draft contract:
      every public tool exposes an implementation-owned `outputSchema` in
      `tools/list` that matches current handler response families closely
      enough for downstream clients and `MCPSTRUCT` planning, while
      `call_tool` itself remains text-only in this phase.
- [ ] IF-0-MCPMETA-6 - No-runtime-migration contract:
      MCPMETA does not change `call_tool` response values, task behavior,
      transport behavior, or auth flows; it only makes metadata and schemas
      more explicit and testable.

## Lane Index & Dependencies

- SL-0 - Tool catalog metadata builders in `stdio_runner`; Depends on: (none); Blocks: SL-1, SL-2; Parallel-safe: yes
- SL-1 - Schema parity and output-draft contract tests; Depends on: SL-0; Blocks: SL-2; Parallel-safe: yes
- SL-2 - README metadata truth and phase closeout docs; Depends on: SL-0, SL-1; Blocks: MCPMETA acceptance; Parallel-safe: no

Lane DAG:

```text
SL-0 -----> SL-1 ----\
   \                  -> SL-2 -> MCPMETA acceptance
    -----------------/
```

## Lanes

### SL-0 - Tool Catalog Metadata Builders In `stdio_runner`

- **Scope**: Refactor `_build_tool_list()` just enough to emit deterministic
  modern metadata for all eight public tools while keeping names and handler
  dispatch unchanged.
- **Owned files**: `mcp_server/cli/stdio_runner.py`, `tests/test_stdio_tool_descriptions.py`
- **Interfaces provided**: IF-0-MCPMETA-1 deterministic tool order contract;
  IF-0-MCPMETA-2 tool identity metadata contract;
  IF-0-MCPMETA-3 input schema strictness contract;
  IF-0-MCPMETA-4 annotation posture contract;
  IF-0-MCPMETA-5 output schema draft definitions consumed by SL-1 and SL-2
- **Interfaces consumed**: existing public tool names from MCPBASE;
  current handler payload families from `mcp_server/cli/tool_handlers.py`;
  `mcp.types.Tool` and `mcp.types.ToolAnnotations` support in the locked SDK;
  the preserved empty-object behavior for `get_status({})` and
  `list_plugins({})`
- **Parallel-safe**: yes
- **Tasks**:
  - test: Extend `tests/test_stdio_tool_descriptions.py` to freeze the exact
    public tool order, assert every tool has a non-empty `title`, and assert
    zero-argument tools still accept `{}` with explicit
    `additionalProperties` behavior.
  - test: Add assertions there for per-tool annotation posture and for the
    presence of `outputSchema` without asserting `structuredContent` or any
    runtime response migration.
  - impl: Rework `_build_tool_list()` into explicit local builders or constants
    inside `mcp_server/cli/stdio_runner.py` so shared schema fragments,
    titles, annotations, and output-schema drafts are defined once and remain
    readable. Keep the helpers in this file unless duplication proves
    unmanageable; do not create a speculative new metadata module.
  - impl: Make each `inputSchema` fully explicit, including `required: []`
    where empty, defaults for optional booleans/integers, and
    `additionalProperties: false` wherever the current handler contract should
    reject undisclosed inputs.
  - impl: Classify tool annotations against actual behavior, not convenience:
    read-only query/status tools should not share mutation hints with
    `reindex`, `write_summaries`, `summarize_sample`, or `handshake`, and
    tools with optional persistence or session mutation should be annotated
    accordingly.
  - impl: Add an `outputSchema` draft for every tool that tracks current text
    JSON payload families closely enough for downstream use but stops short of
    changing `call_tool` emission. Use shared envelope fragments where that
    reduces duplication without hiding tool-specific differences.
  - impl: Preserve the current tool names, descriptions, and dispatch wiring.
    Do not change `_SERVER_INSTRUCTIONS`, `call_tool`, or any handler behavior
    beyond metadata construction.
  - verify: `uv run pytest tests/test_stdio_tool_descriptions.py -q --no-cov`
  - verify: `uv run python - <<'PY'\nfrom mcp_server.cli.stdio_runner import _build_tool_list\nfor tool in _build_tool_list():\n    print(tool.name, bool(tool.title), bool(tool.annotations), bool(tool.outputSchema))\nPY`

### SL-1 - Schema Parity And Output-Draft Contract Tests

- **Scope**: Extend the existing schema parity tests so the richer catalog
  metadata stays aligned with handler reality, especially repository inputs,
  annotation posture, and output-schema draft coverage.
- **Owned files**: `tests/test_tool_schema_handler_parity.py`, `tests/docs/test_p7_schema_alignment.py`, `tests/docs/test_mcpmeta_tool_metadata_contract.py`
- **Interfaces provided**: regression coverage for IF-0-MCPMETA-1 through
  IF-0-MCPMETA-5; proof that the new metadata is implementation-owned and
  remains aligned with the current handlers
- **Interfaces consumed**: SL-0 tool catalog metadata builders;
  current handler signatures and response families in
  `mcp_server/cli/tool_handlers.py`; existing repository-property wording
  already frozen by P7/P28-era tests
- **Parallel-safe**: yes
- **Tasks**:
  - test: Extend `tests/test_tool_schema_handler_parity.py` with metadata
    assertions instead of replacing its existing repository-property checks.
    At minimum, verify every public tool has an `outputSchema`, that
    repository-aware tools still advertise repository consistently, and that
    zero-argument tools remain zero-argument after the metadata refactor.
  - test: Extend `tests/docs/test_p7_schema_alignment.py` so the repository
    property tests continue to pass under stricter schemas, including
    `additionalProperties` and preserved repository descriptions.
  - test: Add `tests/docs/test_mcpmeta_tool_metadata_contract.py` to freeze the
    exact tool order, title map, explicit annotation posture, and the phase
    boundary that `outputSchema` drafts exist in `tools/list` before
    `structuredContent` lands in `MCPSTRUCT`.
  - impl: Keep this lane test-only. If the new assertions expose a contract gap
    that requires code changes, route those fixes back through SL-0’s owned
    `stdio_runner.py` surface instead of duplicating metadata logic in tests.
  - impl: Where output schemas need looser assertions because handler payloads
    are polymorphic, freeze the required top-level fields and variant families
    explicitly rather than writing fragile deep snapshots of every possible
    payload.
  - verify: `uv run pytest tests/test_tool_schema_handler_parity.py tests/docs/test_p7_schema_alignment.py tests/docs/test_mcpmeta_tool_metadata_contract.py -q --no-cov`
  - verify: `rg -n "outputSchema|annotations|additionalProperties|repository" tests/test_tool_schema_handler_parity.py tests/docs/test_p7_schema_alignment.py tests/docs/test_mcpmeta_tool_metadata_contract.py`

### SL-2 - README Metadata Truth And Phase Closeout Docs

- **Scope**: Update the user-facing README so the repo documents the richer
  `tools/list` metadata surface while explicitly deferring response-shape
  changes to `MCPSTRUCT`.
- **Owned files**: `README.md`, `tests/docs/test_mcpmeta_readme_alignment.py`
- **Interfaces provided**: README truth for IF-0-MCPMETA-5 and
  IF-0-MCPMETA-6; human-facing closeout evidence that modern metadata is now
  discoverable without implying runtime response migration
- **Interfaces consumed**: SL-0 tool titles, annotations, and output-schema
  drafts; SL-1 contract assertions; existing README posture that STDIO is
  primary and FastAPI is secondary/admin
- **Parallel-safe**: no
- **Tasks**:
  - test: Add `tests/docs/test_mcpmeta_readme_alignment.py` to freeze the
    README claims that `tools/list` now carries richer metadata
    (`title`, annotations, explicit schemas, and output-schema drafts) while
    `call_tool` structured results are still deferred to `MCPSTRUCT`.
  - impl: Update `README.md` only where the public MCP surface is described.
    Add a concise note about deterministic tool metadata and discoverable
    schema drafts; avoid broad README cleanup unrelated to the MCP surface.
  - impl: Keep the phase boundary explicit: MCPMETA improves discoverability
    and schema declaration only. It must not claim `structuredContent`, task
    progress, Streamable HTTP, or remote auth support.
  - impl: If the README already contains enough accurate wording after SL-0 and
    SL-1, limit the change to the narrowest diff that lets the new doc test
    pass.
  - verify: `uv run pytest tests/docs/test_mcpmeta_readme_alignment.py -q --no-cov`
  - verify: `rg -n "tools/list|title|annotations|outputSchema|structuredContent|MCPSTRUCT" README.md tests/docs/test_mcpmeta_readme_alignment.py`

## Verification

Planning-only work is complete once this artifact is written and staged. Do
not execute the commands below during plan creation; run them during
`codex-execute-phase` or manual MCPMETA execution.

Lane-specific checks:

```bash
uv run pytest tests/test_stdio_tool_descriptions.py -q --no-cov
uv run pytest \
  tests/test_tool_schema_handler_parity.py \
  tests/docs/test_p7_schema_alignment.py \
  tests/docs/test_mcpmeta_tool_metadata_contract.py \
  -q --no-cov
uv run pytest tests/docs/test_mcpmeta_readme_alignment.py -q --no-cov
uv run python - <<'PY'
from mcp_server.cli.stdio_runner import _build_tool_list
for tool in _build_tool_list():
    print(tool.name, tool.title, tool.annotations, bool(tool.outputSchema))
PY
```

Whole-phase verification after code changes:

```bash
uv run pytest \
  tests/test_stdio_tool_descriptions.py \
  tests/test_tool_schema_handler_parity.py \
  tests/docs/test_p7_schema_alignment.py \
  tests/docs/test_mcpmeta_tool_metadata_contract.py \
  tests/docs/test_mcpmeta_readme_alignment.py \
  -q --no-cov
git status --short -- \
  mcp_server/cli/stdio_runner.py \
  README.md \
  tests/test_stdio_tool_descriptions.py \
  tests/test_tool_schema_handler_parity.py \
  tests/docs/test_p7_schema_alignment.py \
  tests/docs/test_mcpmeta_tool_metadata_contract.py \
  tests/docs/test_mcpmeta_readme_alignment.py \
  plans/phase-plan-v8-MCPMETA.md
```

## Acceptance Criteria

- [ ] `tools/list` order is deterministic and frozen by tests for the current
      eight public tools.
- [ ] Every public tool has a stable `name`, a human-friendly `title`, and an
      explicit annotation posture that matches its current read-only or
      mutating behavior.
- [ ] Every tool input schema makes accepted fields, required fields, defaults,
      and `additionalProperties` behavior explicit without breaking
      `get_status({})` or `list_plugins({})`.
- [ ] Every public tool advertises an implementation-owned `outputSchema`
      draft in `tools/list`, and the draft is covered by parity/contract tests
      without changing `call_tool` runtime payloads.
- [ ] Existing schema-parity and handler-adjacent tests still pass with added
      metadata assertions instead of being replaced by weaker coverage.
- [ ] `README.md` accurately states that richer metadata is discoverable now,
      while structured results remain deferred to `MCPSTRUCT`.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v8-MCPMETA.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v8-MCPMETA.md
  artifact_state: staged
```
