---
phase_loop_plan_version: 1
phase: MCPEVAL
roadmap: specs/phase-plans-v8.md
roadmap_sha256: 25aa1501b52e5038cbcc0356638d2a5de5aaaea75c32e21c03de8a1db6a99a11
---
# MCPEVAL: MCP Compatibility Evidence And Evaluations

## Context

MCPEVAL is the closing v8 phase. `.phase-loop/tui-handoff.md` and
`.phase-loop/state.json` both mark `MCPEVAL` as the current unplanned phase
after `MCPBASE`, `MCPMETA`, `MCPSTRUCT`, `MCPTASKS`, `MCPTRANSPORT`, and
`MCPAUTH` completed, so this artifact needs to turn the already-landed protocol
work into client-visible proof rather than reopen those contracts.

Current repo state gathered during planning:

- `specs/phase-plans-v8.md` is the active tracked roadmap and its current
  `sha256` matches the user-provided `25aa1501b52e5038cbcc0356638d2a5de5aaaea75c32e21c03de8a1db6a99a11`.
- MCPBASE already produced `docs/status/MCP_BASELINE_COMPATIBILITY_AUDIT.md`
  plus `tests/smoke/test_mcpbase_stdio_smoke.py`, which proves the official
  Python SDK can complete `initialize`, `tools/list`, and representative
  baseline `tools/call` flows over STDIO.
- The implementation side of the later v8 phases is present:
  `mcp_server/cli/stdio_runner.py` now emits deterministic tool metadata with
  `title`, `inputSchema`, `outputSchema`, and `execution.taskSupport` for
  `reindex` and `write_summaries`; `CallToolResult` uses
  `structuredContent` plus JSON text fallback; and
  `server.experimental.enable_tasks(store=_task_registry)` exposes the MCP
  tasks surface.
- The repo has good contract-unit coverage for those capabilities
  (`tests/docs/test_mcpmeta_tool_metadata_contract.py`,
  `tests/docs/test_mcpstruct_call_tool_contract.py`,
  `tests/docs/test_mcptasks_protocol_contract.py`,
  `tests/test_mcptasks_reindex.py`, and
  `tests/test_mcptasks_write_summaries.py`), but there is not yet one
  SDK-level smoke that proves metadata, structured results, readiness failures,
  and task-backed execution from the client perspective in one place.
- The transport and auth boundary decisions are already explicit in
  `docs/validation/mcp-transport-decision.md` and
  `docs/validation/mcp-auth-boundary.md`, and public docs already say STDIO is
  primary while FastAPI is admin/debug only.
- Public claim surfaces still outrun the current evidence bundle. For example,
  `README.md` currently says "Full compatibility with Claude Code and other MCP
  clients", but there is no final compatibility matrix or MCPEVAL closeout
  artifact tying named clients and supported surfaces to fresh, phase-owned
  proof.
- There is no `evaluations/` or `docs/evaluations/` prompt corpus yet, so the
  roadmap exit criterion requiring at least ten stable read-only evaluation
  prompts is still open.

Practical planning boundary:

- MCPEVAL should close with evidence, evaluation prompts, and narrowly-scoped
  doc truth. It may include small client-surface fixes discovered by the new
  SDK smoke if they are necessary to make existing v8 contracts observable from
  the client side.
- MCPEVAL must not redesign metadata, structured results, task semantics,
  transport, or auth. Any runtime edits in this phase must stay limited to
  smoke-discovered compatibility gaps in the already-supported STDIO client
  surface.

## Interface Freeze Gates

- [ ] IF-0-MCPEVAL-1 - SDK-level compatibility evidence contract:
      official Python SDK or Inspector-equivalent STDIO smokes prove
      `initialize`, `tools/list`, structured `tools/call` responses, fail-closed
      readiness behavior, and task-backed `reindex` or `write_summaries`
      behavior from the client perspective.
- [ ] IF-0-MCPEVAL-2 - Evaluation prompt corpus contract:
      at least ten read-only prompts with stable expected answers exist under a
      repo-owned evaluation artifact, cover code search, symbol lookup,
      readiness failure handling, multi-repo scoping, and semantic-query
      posture, and require no secrets.
- [ ] IF-0-MCPEVAL-3 - Compatibility matrix and release-posture contract:
      docs include one current compatibility matrix covering STDIO, FastAPI
      admin/debug HTTP, deferred Streamable HTTP MCP, and explicitly named
      client surfaces without claiming support broader than the verified
      evidence.
- [ ] IF-0-MCPEVAL-4 - Unsupported-surface closeout contract:
      release-readiness docs explicitly state what remains intentionally
      unsupported or deferred after v8 closeout, including remote MCP
      transport/auth work that was intentionally left out of scope.

## Lane Index & Dependencies

- SL-0 - SDK smoke expansion and client-surface repair; Depends on: (none); Blocks: SL-2; Parallel-safe: yes
- SL-1 - Read-only evaluation prompt pack and expected-answer contract; Depends on: (none); Blocks: SL-2; Parallel-safe: yes
- SL-2 - Compatibility matrix, closeout evidence, and public-claim alignment; Depends on: SL-0, SL-1; Blocks: MCPEVAL acceptance; Parallel-safe: no

Lane DAG:

```text
SL-0 ----\
          -> SL-2 -> MCPEVAL acceptance
SL-1 ----/
```

## Lanes

### SL-0 - SDK Smoke Expansion And Client-Surface Repair

- **Scope**: Add one MCPEVAL-owned SDK smoke that proves the modern STDIO client
  surface end to end, and limit any code edits to small compatibility fixes
  that the smoke exposes in already-supported metadata, structured-result, or
  task flows.
- **Owned files**: `tests/smoke/test_mcpeval_sdk_surface.py`, `tests/fixtures/multi_repo.py`, `mcp_server/cli/stdio_runner.py`, `mcp_server/cli/tool_handlers.py`, `mcp_server/cli/task_reindex.py`, `mcp_server/cli/task_write_summaries.py`
- **Interfaces provided**: IF-0-MCPEVAL-1 SDK-level compatibility evidence;
  client-visible smoke findings consumed by SL-2
- **Interfaces consumed**: `_build_tool_list()` metadata and `outputSchema`
  surface in `mcp_server/cli/stdio_runner.py`; `_to_call_tool_result()`
  structured-result behavior; task-backed `reindex` and `write_summaries`
  paths in `mcp_server/cli/tool_handlers.py`; current readiness fail-closed
  vocabulary from `tests/test_tool_readiness_fail_closed.py` and
  `tests/test_multi_repo_failure_matrix.py`
- **Parallel-safe**: yes
- **Tasks**:
  - test: Add `tests/smoke/test_mcpeval_sdk_surface.py` using the official
    Python SDK STDIO client to verify `initialize`, `tools/list`, metadata
    visibility (`title`, task-support, input/output schema presence), one or
    more structured `tools/call` responses with `structuredContent` plus JSON
    text fallback, and `isError` behavior for a fail-closed readiness path.
  - test: In the same smoke or a companion case, exercise one task-backed
    client flow for `reindex` or `write_summaries` from the SDK side so the
    phase proves `task` submission and terminal retrieval rather than relying
    only on handler-unit tests.
  - test: Reuse or minimally extend `tests/fixtures/multi_repo.py` if the smoke
    needs a ready repo plus a non-ready repo/worktree to prove multi-repo
    scoping and readiness failures from a real client session.
  - impl: Touch runtime files only if the smoke exposes a real compatibility
    gap in the already-supported STDIO surface. Keep any fix bounded to client
    observability, not protocol redesign.
  - impl: Do not add new public tools, new remote transport behavior, or new
    task semantics in this lane.
  - verify: `uv run pytest tests/smoke/test_mcpbase_stdio_smoke.py tests/smoke/test_mcpeval_sdk_surface.py tests/test_mcptasks_reindex.py tests/test_mcptasks_write_summaries.py tests/test_tool_readiness_fail_closed.py tests/test_multi_repo_failure_matrix.py -q --no-cov`
  - verify: `rg -n "outputSchema|taskSupport|structuredContent|isError|index_unavailable|safe_fallback|tasks/result|tasks/cancel" mcp_server/cli/stdio_runner.py mcp_server/cli/tool_handlers.py tests/smoke/test_mcpeval_sdk_surface.py`

### SL-1 - Read-Only Evaluation Prompt Pack And Expected-Answer Contract

- **Scope**: Create the phase-owned prompt corpus that operators or downstream
  agents can run against the supported MCP surface without secrets, with stable
  expected answers and explicit coverage of the required behavior categories.
- **Owned files**: `docs/evaluations/mcpeval-prompt-pack.md`, `tests/docs/test_mcpeval_prompt_pack.py`
- **Interfaces provided**: IF-0-MCPEVAL-2 evaluation prompt corpus contract;
  prompt inventory and expected-answer inputs consumed by SL-2
- **Interfaces consumed**: current query/readiness vocabulary from
  `README.md`, `docs/GETTING_STARTED.md`, `docs/MCP_CONFIGURATION.md`,
  `docs/SUPPORT_MATRIX.md`, `docs/validation/mcp-transport-decision.md`,
  `docs/validation/mcp-auth-boundary.md`, and the stable behaviors proven or
  preserved by SL-0
- **Parallel-safe**: yes
- **Tasks**:
  - test: Add `tests/docs/test_mcpeval_prompt_pack.py` to freeze a prompt pack
    with at least ten prompts plus expected answers or answer constraints.
  - test: Require explicit coverage for:
    `search_code`, `symbol_lookup`, ready-path `get_status`,
    readiness failure handling with `index_unavailable`,
    multi-repo scoping or unsupported-worktree behavior, semantic query posture
    (including when semantic support is unavailable or gated), and at least one
    task-oriented prompt whose expected answer is based on documented task
    surfaces rather than secrets.
  - impl: Write `docs/evaluations/mcpeval-prompt-pack.md` as the canonical
    prompt pack with no secret-bearing steps, no external service requirements,
    and expected answers that remain stable across local test fixtures.
  - impl: Keep the artifact read-only and evaluation-oriented. Do not turn it
    into an operator runbook, benchmark report, or release checklist.
  - verify: `uv run pytest tests/docs/test_mcpeval_prompt_pack.py -q --no-cov`
  - verify: `rg -n "search_code|symbol_lookup|get_status|index_unavailable|safe_fallback|semantic|worktree|task" docs/evaluations/mcpeval-prompt-pack.md tests/docs/test_mcpeval_prompt_pack.py`

### SL-2 - Compatibility Matrix, Closeout Evidence, And Public-Claim Alignment

- **Scope**: Reduce the smoke results and prompt pack into one final
  compatibility/evidence story that updates public claim surfaces, publishes a
  current compatibility matrix, and explicitly records what v8 still does not
  support.
- **Owned files**: `docs/status/MCP_COMPATIBILITY_EVALUATION.md`, `README.md`, `docs/GETTING_STARTED.md`, `docs/MCP_CONFIGURATION.md`, `docs/SUPPORT_MATRIX.md`, `tests/docs/test_mcpeval_surface_matrix.py`, `tests/docs/test_mcpeval_evidence_contract.py`
- **Interfaces provided**: IF-0-MCPEVAL-3 compatibility matrix and
  release-posture contract; IF-0-MCPEVAL-4 unsupported-surface closeout
  contract
- **Interfaces consumed**: SL-0 SDK smoke findings; SL-1 prompt-pack coverage;
  existing phase artifacts `docs/status/MCP_BASELINE_COMPATIBILITY_AUDIT.md`,
  `docs/validation/mcp-transport-decision.md`, and
  `docs/validation/mcp-auth-boundary.md`; current support-tier and topology
  language already frozen in `docs/SUPPORT_MATRIX.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Add `tests/docs/test_mcpeval_surface_matrix.py` to freeze a current
    compatibility matrix across STDIO, FastAPI admin/debug HTTP, deferred
    Streamable HTTP MCP, and explicitly named client surfaces that the repo is
    willing to claim after reviewing the SDK smoke evidence.
  - test: Add `tests/docs/test_mcpeval_evidence_contract.py` to require one
    MCPEVAL closeout artifact with sections for scope, observed client evidence,
    prompt-pack coverage, unsupported or deferred surfaces, and verification
    commands.
  - impl: Write `docs/status/MCP_COMPATIBILITY_EVALUATION.md` as the single
    MCPEVAL reducer artifact. It should point to the exact smoke and docs tests,
    describe the verified client/surface matrix, summarize the prompt-pack
    coverage, and state remaining intentional limitations without expanding the
    support claim.
  - impl: Update `README.md`, `docs/GETTING_STARTED.md`,
    `docs/MCP_CONFIGURATION.md`, and `docs/SUPPORT_MATRIX.md` only where needed
    to align public claims with the new matrix and evidence. Narrow broad
    language such as "other MCP clients" if the phase evidence only supports a
    more specific statement.
  - impl: Make unsupported or deferred surfaces explicit, including the current
    remote MCP transport deferment, FastAPI not being an MCP transport, and any
    remaining readiness/topology or semantic prerequisites that affect client
    expectations.
  - verify: `uv run pytest tests/docs/test_mcpeval_surface_matrix.py tests/docs/test_mcpeval_evidence_contract.py -q --no-cov`
  - verify: `rg -n "compatibility|matrix|STDIO|FastAPI|Streamable HTTP|Claude Code|Cursor|Inspector|unsupported|deferred|index_unavailable|safe_fallback" README.md docs/GETTING_STARTED.md docs/MCP_CONFIGURATION.md docs/SUPPORT_MATRIX.md docs/status/MCP_COMPATIBILITY_EVALUATION.md tests/docs/test_mcpeval_surface_matrix.py tests/docs/test_mcpeval_evidence_contract.py`

## Verification

Planning-only work is complete once this artifact is written and staged. Do
not execute the commands below during plan creation; run them during
`codex-execute-phase` or manual MCPEVAL execution.

Lane-specific checks:

```bash
uv run pytest \
  tests/smoke/test_mcpbase_stdio_smoke.py \
  tests/smoke/test_mcpeval_sdk_surface.py \
  tests/test_mcptasks_reindex.py \
  tests/test_mcptasks_write_summaries.py \
  tests/test_tool_readiness_fail_closed.py \
  tests/test_multi_repo_failure_matrix.py \
  -q --no-cov

uv run pytest \
  tests/docs/test_mcpeval_prompt_pack.py \
  -q --no-cov

uv run pytest \
  tests/docs/test_mcpeval_surface_matrix.py \
  tests/docs/test_mcpeval_evidence_contract.py \
  -q --no-cov
```

Whole-phase verification after code and docs changes:

```bash
uv run pytest \
  tests/smoke/test_mcpbase_stdio_smoke.py \
  tests/smoke/test_mcpeval_sdk_surface.py \
  tests/docs/test_mcpmeta_tool_metadata_contract.py \
  tests/docs/test_mcpstruct_call_tool_contract.py \
  tests/docs/test_mcptasks_protocol_contract.py \
  tests/docs/test_mcpauth_surface_alignment.py \
  tests/docs/test_mcptransport_decision_record.py \
  tests/test_mcptasks_reindex.py \
  tests/test_mcptasks_write_summaries.py \
  tests/test_tool_readiness_fail_closed.py \
  tests/test_multi_repo_failure_matrix.py \
  tests/docs/test_mcpeval_prompt_pack.py \
  tests/docs/test_mcpeval_surface_matrix.py \
  tests/docs/test_mcpeval_evidence_contract.py \
  -q --no-cov

git status --short -- \
  mcp_server/cli/stdio_runner.py \
  mcp_server/cli/tool_handlers.py \
  mcp_server/cli/task_reindex.py \
  mcp_server/cli/task_write_summaries.py \
  tests/fixtures/multi_repo.py \
  tests/smoke/test_mcpeval_sdk_surface.py \
  docs/evaluations/mcpeval-prompt-pack.md \
  tests/docs/test_mcpeval_prompt_pack.py \
  docs/status/MCP_COMPATIBILITY_EVALUATION.md \
  README.md \
  docs/GETTING_STARTED.md \
  docs/MCP_CONFIGURATION.md \
  docs/SUPPORT_MATRIX.md \
  tests/docs/test_mcpeval_surface_matrix.py \
  tests/docs/test_mcpeval_evidence_contract.py \
  plans/phase-plan-v8-MCPEVAL.md
```

## Acceptance Criteria

- [ ] One SDK-level STDIO smoke proves the modern client surface from the
      client side: `initialize`, `tools/list`, metadata visibility, structured
      `tools/call` results, a fail-closed readiness case, and task-backed
      operation behavior.
- [ ] At least ten read-only evaluation prompts with stable expected answers
      exist in a repo-owned prompt-pack artifact and cover search, symbol
      lookup, readiness failures, multi-repo behavior, semantic posture, and
      task-surface expectations without requiring secrets.
- [ ] Public docs and one compatibility matrix now describe exactly which MCP
      and admin surfaces are supported, which client claims are evidence-backed,
      and which surfaces remain deferred or unsupported.
- [ ] The MCPEVAL closeout artifact explicitly records remaining intentional
      gaps, including deferred remote MCP transport/auth work and any
      readiness/topology or semantic prerequisites that still limit support.
- [ ] Any runtime edits made during MCPEVAL are limited to small
      smoke-discovered compatibility fixes in the existing STDIO client surface
      and do not reopen metadata, task, transport, or auth design.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v8-MCPEVAL.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v8-MCPEVAL.md
  artifact_state: staged
```
