---
phase_loop_plan_version: 1
phase: MCPTASKS
roadmap: specs/phase-plans-v8.md
roadmap_sha256: 25aa1501b52e5038cbcc0356638d2a5de5aaaea75c32e21c03de8a1db6a99a11
---
# MCPTASKS: MCP Task Support For Long-Running Operations

## Context

MCPTASKS is the next execution phase after the completed MCPSTRUCT result-shape
work. Its job is to make long-running mutable MCP operations task-capable
without regressing the current fail-closed readiness behavior or the existing
sync compatibility path.

Current repo state gathered during planning:

- `specs/phase-plans-v8.md` is the active tracked roadmap, and canonical
  `.phase-loop/state.json` marks `MCPBASE`, `MCPMETA`, and `MCPSTRUCT` as
  complete, `MCPTASKS` as the current `unplanned` phase, the branch as
  `roadmap-v8-mcp-modernization`, and the worktree as clean.
- `plans/phase-plan-v8-MCPTASKS.md` did not exist before this run.
- `mcp_server/cli/stdio_runner.py` already returns structured
  `types.CallToolResult` objects, but `_serve()` only registers `list_tools`
  and `call_tool`; it does not yet enable the SDK task surface.
- The locked MCP SDK already supports the native task contract needed here:
  `Tool.execution.taskSupport`, request-side `params.task`, server-side
  `types.CreateTaskResult`, and the experimental `server.experimental`
  helpers that auto-register `tasks/get`, `tasks/list`, `tasks/result`, and
  `tasks/cancel`.
- `mcp_server/cli/tool_handlers.py` still executes `reindex` and
  `write_summaries` synchronously. `handle_reindex()` can block on directory
  indexing, and `handle_write_summaries()` can block on
  `ComprehensiveChunkWriter.process_scope(...)`.
- Reindex already has reusable progress and durability primitives:
  `EnhancedDispatcher.index_directory(..., progress_callback=...)` emits
  lexical and semantic progress snapshots, and
  `mcp_server/indexing/checkpoint.py` persists `.reindex-state` resume data.
- Worker-side cancellation is not wired today. The SDK task helpers manage task
  status/result transport, but task cancellation still needs repo-local polling
  at safe boundaries inside the actual reindex and summarization work.
- MCPMETA tests currently freeze the absence of execution metadata, so this
  phase must deliberately update tool metadata tests when `reindex` and
  `write_summaries` begin advertising task support.

Practical planning boundary:

- MCPTASKS may enable the native SDK task surface, add a repo-local task
  registry/store adapter, route `reindex` and `write_summaries` through
  task-backed execution when the request asks for it, and preserve sync
  execution when task augmentation is absent or intentionally bypassed.
- MCPTASKS must not route read-only tools through tasks, must not add remote
  transport behavior, and must not broaden into release, phase-loop, or
  distributed worker orchestration.

## Interface Freeze Gates

- [ ] IF-0-MCPTASKS-1 - Native task capability contract:
      `reindex` and `write_summaries` advertise
      `Tool.execution.taskSupport = "optional"`, all other public tools remain
      non-task tools, and the STDIO server exposes the MCP task capability set
      (`tasks/list`, `tasks/get`, `tasks/result`, `tasks/cancel`) only through
      the SDK-supported task surface.
- [ ] IF-0-MCPTASKS-2 - Task registry contract:
      every task-backed mutation records task ID, tool name, repository scope,
      creation/update timestamps, status message, cancellation-requested state,
      latest progress snapshot, terminal structured result, and terminal error
      details in one implementation-owned registry/store surface.
- [ ] IF-0-MCPTASKS-3 - Reindex task execution contract:
      task-augmented `reindex` can return `types.CreateTaskResult`, surface
      progress derived from dispatcher/checkpoint state, support best-effort
      cancellation at safe lexical or semantic boundaries, and return a
      terminal payload through `tasks/result` that matches the existing
      structured/text sync contract.
- [ ] IF-0-MCPTASKS-4 - Write-summaries task execution contract:
      task-augmented `write_summaries` can return `types.CreateTaskResult`,
      surface bounded summary progress, support best-effort cancellation
      without corrupting persisted summary state, and return terminal payloads
      through `tasks/result` that match the existing sync contract.
- [ ] IF-0-MCPTASKS-5 - Fail-closed and sync-compatibility contract:
      readiness refusals, path sandbox errors, conflicting scope errors, and
      summarizer-unavailable preflights still fail synchronously before task
      creation, while small or non-task requests retain a working synchronous
      execution path.

## Lane Index & Dependencies

- SL-0 - Native MCP task protocol enablement and registry scaffolding; Depends on: (none); Blocks: SL-1, SL-2, SL-3; Parallel-safe: no
- SL-1 - Reindex background execution, progress capture, and safe cancellation; Depends on: SL-0; Blocks: SL-3; Parallel-safe: yes
- SL-2 - Write-summaries background execution and bounded cancellation; Depends on: SL-0; Blocks: SL-3; Parallel-safe: yes
- SL-3 - Public tool routing, fail-closed preflight preservation, and docs closeout; Depends on: SL-0, SL-1, SL-2; Blocks: MCPTASKS acceptance; Parallel-safe: no

Lane DAG:

```text
SL-0 -----> SL-1 ----\
   \                  \
    \-----> SL-2 ------> SL-3 -> MCPTASKS acceptance
```

## Lanes

### SL-0 - Native MCP Task Protocol Enablement And Registry Scaffolding

- **Scope**: Enable the SDK-native MCP task surface, expose task support in the
  two long-running tool definitions, and add one implementation-owned registry
  layer that background workers can use for status, progress, result, and
  cancellation bookkeeping.
- **Owned files**: `mcp_server/cli/stdio_runner.py`, `mcp_server/storage/mcp_task_registry.py`, `tests/test_mcp_server_cli.py`, `tests/test_stdio_tool_descriptions.py`, `tests/docs/test_mcpmeta_tool_metadata_contract.py`, `tests/docs/test_mcptasks_protocol_contract.py`
- **Interfaces provided**: IF-0-MCPTASKS-1 native task capability contract;
  IF-0-MCPTASKS-2 task registry contract;
  task-creation/task-context helpers consumed by SL-1, SL-2, and SL-3
- **Interfaces consumed**: current MCPSTRUCT `call_tool()` contract;
  locked SDK `Tool.execution.taskSupport`, `TaskMetadata`,
  `CreateTaskResult`, `Server.experimental.enable_tasks()`,
  `ServerTaskContext`, and `GetTaskPayloadResult`;
  current public tool catalog from `_build_tool_list()`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_stdio_tool_descriptions.py` and
    `tests/docs/test_mcpmeta_tool_metadata_contract.py` so `reindex` and
    `write_summaries` now advertise `execution.taskSupport="optional"` while
    all other public tools remain task-forbidden or omit execution metadata.
  - test: Add `tests/docs/test_mcptasks_protocol_contract.py` to freeze the
    server capability contract: task support is enabled in initialization
    options, `call_tool()` accepts task-augmented requests, and non-task tool
    definitions remain unchanged apart from the two intended mutations.
  - test: Extend `tests/test_mcp_server_cli.py` so direct module-level calls
    cover the `CreateTaskResult` branch and the presence of a repo-local task
    registry/store instead of only `CallToolResult`.
  - impl: Enable `server.experimental.enable_tasks(...)` in `_serve()` with a
    repo-local registry/store wrapper that can retain progress snapshots,
    cancellation-requested state, and terminal `Result` payloads, rather than
    relying on the bare default in-memory task store alone.
  - impl: Update `_build_tool_list()` so only `reindex` and `write_summaries`
    advertise task support. Do not make `symbol_lookup`, `search_code`,
    `get_status`, `list_plugins`, `summarize_sample`, or `handshake`
    task-augmented.
  - impl: Extend `call_tool()` so it extracts `request_ctx.experimental`
    task metadata, passes that execution intent downstream, and can return
    either `CallToolResult` or `CreateTaskResult` without changing the current
    sync behavior when no task request is present.
  - impl: Keep this lane focused on protocol wiring and shared registry
    plumbing. Do not embed reindex- or summarization-specific worker logic in
    `stdio_runner.py`.
  - verify: `uv run pytest tests/test_mcp_server_cli.py tests/test_stdio_tool_descriptions.py tests/docs/test_mcpmeta_tool_metadata_contract.py tests/docs/test_mcptasks_protocol_contract.py -q --no-cov`
  - verify: `uv run python - <<'PY'\nfrom mcp_server.cli.stdio_runner import _build_tool_list\nfor tool in _build_tool_list():\n    print(tool.name, getattr(getattr(tool, 'execution', None), 'taskSupport', None))\nPY`

### SL-1 - Reindex Background Execution, Progress Capture, And Safe Cancellation

- **Scope**: Add a task-backed `reindex` worker that reuses current dispatcher
  progress and checkpoint semantics, returns the same terminal payload family
  as sync `reindex`, and supports best-effort cancellation only at safe
  lexical or semantic boundaries.
- **Owned files**: `mcp_server/cli/task_reindex.py`, `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/indexing/checkpoint.py`, `tests/test_reindex_resume.py`, `tests/test_mcptasks_reindex.py`
- **Interfaces provided**: IF-0-MCPTASKS-3 reindex task execution contract;
  reindex progress and cancellation hooks consumed by SL-3
- **Interfaces consumed**: SL-0 task registry/task-context helpers;
  existing `EnhancedDispatcher.index_directory(..., progress_callback=...)`;
  existing `.reindex-state` checkpoint helpers;
  current `reindex` terminal payload shape from `tool_handlers.handle_reindex()`
- **Parallel-safe**: yes
- **Tasks**:
  - test: Add `tests/test_mcptasks_reindex.py` to cover task-backed reindex
    success, `tasks/get` working/completed transitions, `tasks/result`
    terminal payload parity with sync reindex, and cancellation requests that
    stop the worker at a safe boundary.
  - test: Extend `tests/test_reindex_resume.py` so task-mode cancellation or
    crash/retry paths do not break existing `.reindex-state` durability and
    resume semantics.
  - impl: Add a dedicated reindex task worker helper that can spawn background
    work from a `ServerTaskContext`, mirror dispatcher progress snapshots into
    the task registry/status message, and complete with the same structured
    result envelope currently returned by synchronous `reindex`.
  - impl: Thread a best-effort cancel probe through the lexical walk and
    semantic closeout path in `dispatcher_enhanced.py` so task cancellation is
    observed between safe units of work instead of force-killing indexing in
    the middle of a file or database mutation.
  - impl: Preserve the current synchronous single-file and non-task path.
    Task mode should be additive, not a replacement for all `reindex` calls.
  - impl: Ensure cancelled reindex tasks report a stable terminal payload and
    do not mark `mutation_performed` or `persisted` incorrectly when work was
    aborted before safe completion.
  - verify: `uv run pytest tests/test_reindex_resume.py tests/test_mcptasks_reindex.py -q --no-cov`
  - verify: `rg -n "progress_callback|last_progress_path|summary_call|cancel" mcp_server/dispatcher/dispatcher_enhanced.py mcp_server/cli/task_reindex.py mcp_server/indexing/checkpoint.py tests/test_reindex_resume.py tests/test_mcptasks_reindex.py`

### SL-2 - Write-Summaries Background Execution And Bounded Cancellation

- **Scope**: Add a task-backed `write_summaries` worker that runs summary
  generation in bounded background passes, surfaces summary progress, and
  supports cancellation between safe summarization boundaries while preserving
  the current sync path.
- **Owned files**: `mcp_server/cli/task_write_summaries.py`, `mcp_server/indexing/summarization.py`, `tests/test_mcptasks_write_summaries.py`
- **Interfaces provided**: IF-0-MCPTASKS-4 write-summaries task execution
  contract; bounded summarization progress consumed by SL-3
- **Interfaces consumed**: SL-0 task registry/task-context helpers;
  existing `ComprehensiveChunkWriter.process_scope(...)`;
  current `write_summaries` terminal payload shape from
  `tool_handlers.handle_write_summaries()`
- **Parallel-safe**: yes
- **Tasks**:
  - test: Add `tests/test_mcptasks_write_summaries.py` to cover successful
    task-backed summarization, `tasks/result` payload parity with sync
    `write_summaries`, summarizer-unavailable preflight refusal, and
    cancellation before the next bounded summary pass.
  - impl: Add a dedicated write-summaries task worker helper that records
    `chunks_summarized`, `summary_chunks_attempted`, `summary_missing_chunks`,
    `model_used`, and persistence status as task progress and terminal result.
  - impl: Bound cancellation to safe summarization checkpoints instead of
    interrupting an in-flight provider call or leaving ambiguous persistence
    state; if a provider timeout already exists, reuse that boundary rather
    than inventing a second cancellation mechanism.
  - impl: Preserve the current synchronous path when task augmentation is not
    requested.
  - impl: Keep this lane focused on `write_summaries`. Do not route
    `summarize_sample` through tasks in this phase.
  - verify: `uv run pytest tests/test_mcptasks_write_summaries.py -q --no-cov`
  - verify: `rg -n "process_scope|summaries_written|missing_chunk|cancel" mcp_server/indexing/summarization.py mcp_server/cli/task_write_summaries.py tests/test_mcptasks_write_summaries.py`

### SL-3 - Public Tool Routing, Fail-Closed Preflight Preservation, And Docs Closeout

- **Scope**: Route the public `reindex` and `write_summaries` tool handlers
  through sync-or-task execution without weakening readiness/path validation,
  and update the narrow README surface so the MCP task contract is discoverable
  to clients.
- **Owned files**: `mcp_server/cli/tool_handlers.py`, `README.md`, `tests/test_tool_handlers_readiness.py`, `tests/test_tool_readiness_fail_closed.py`, `tests/test_handler_path_sandbox.py`, `tests/docs/test_mcptasks_readme_alignment.py`
- **Interfaces provided**: IF-0-MCPTASKS-5 fail-closed and sync-compatibility
  contract; user-facing docs truth for task-augmented execution
- **Interfaces consumed**: SL-0 task-request detection and registry helpers;
  SL-1 reindex task worker;
  SL-2 write-summaries task worker;
  current readiness/path sandbox/conflicting-scope refusal helpers in
  `tool_handlers.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_tool_handlers_readiness.py`,
    `tests/test_tool_readiness_fail_closed.py`, and
    `tests/test_handler_path_sandbox.py` so readiness, path sandbox, and
    conflicting-scope failures still occur before task creation and still
    preserve the current fail-closed payload semantics.
  - test: Add `tests/docs/test_mcptasks_readme_alignment.py` to freeze README
    claims about task-augmented `reindex` and `write_summaries`, native
    `tasks/result` retrieval, sync fallback behavior, and best-effort
    cancellation.
  - impl: Update `handle_reindex()` and `handle_write_summaries()` so they
    choose task-backed execution only when the MCP request actually carries
    task metadata and preflight validation has already passed.
  - impl: Preserve existing sync behavior for non-task calls, including
    synchronous readiness refusals, file-path sandbox checks, repository/path
    conflict checks, and summarizer-unavailable errors.
  - impl: Update `README.md` only where the MCP tool surface is documented.
    Explain that `reindex` and `write_summaries` now support task-augmented
    execution, how results are retrieved, and that cancellation is best-effort.
  - impl: Keep the docs narrow. Do not imply remote task execution,
    distributed workers, or task support for unrelated tools.
  - verify: `uv run pytest tests/test_tool_handlers_readiness.py tests/test_tool_readiness_fail_closed.py tests/test_handler_path_sandbox.py tests/docs/test_mcptasks_readme_alignment.py -q --no-cov`
  - verify: `rg -n "taskSupport|CreateTaskResult|tasks/result|best-effort|reindex|write_summaries" README.md mcp_server/cli/tool_handlers.py tests/test_tool_handlers_readiness.py tests/test_tool_readiness_fail_closed.py tests/test_handler_path_sandbox.py tests/docs/test_mcptasks_readme_alignment.py`

## Verification

Planning-only work is complete once this artifact is written and staged. Do
not execute the commands below during plan creation; run them during
`codex-execute-phase` or manual MCPTASKS execution.

Lane-specific checks:

```bash
uv run pytest \
  tests/test_mcp_server_cli.py \
  tests/test_stdio_tool_descriptions.py \
  tests/docs/test_mcpmeta_tool_metadata_contract.py \
  tests/docs/test_mcptasks_protocol_contract.py \
  -q --no-cov

uv run pytest \
  tests/test_reindex_resume.py \
  tests/test_mcptasks_reindex.py \
  -q --no-cov

uv run pytest \
  tests/test_mcptasks_write_summaries.py \
  -q --no-cov

uv run pytest \
  tests/test_tool_handlers_readiness.py \
  tests/test_tool_readiness_fail_closed.py \
  tests/test_handler_path_sandbox.py \
  tests/docs/test_mcptasks_readme_alignment.py \
  -q --no-cov
```

Whole-phase verification after code changes:

```bash
uv run pytest \
  tests/test_mcp_server_cli.py \
  tests/test_stdio_tool_descriptions.py \
  tests/docs/test_mcpmeta_tool_metadata_contract.py \
  tests/docs/test_mcptasks_protocol_contract.py \
  tests/test_reindex_resume.py \
  tests/test_mcptasks_reindex.py \
  tests/test_mcptasks_write_summaries.py \
  tests/test_tool_handlers_readiness.py \
  tests/test_tool_readiness_fail_closed.py \
  tests/test_handler_path_sandbox.py \
  tests/docs/test_mcptasks_readme_alignment.py \
  -q --no-cov

git status --short -- \
  mcp_server/cli/stdio_runner.py \
  mcp_server/storage/mcp_task_registry.py \
  mcp_server/cli/task_reindex.py \
  mcp_server/cli/task_write_summaries.py \
  mcp_server/cli/tool_handlers.py \
  mcp_server/dispatcher/dispatcher_enhanced.py \
  mcp_server/indexing/checkpoint.py \
  mcp_server/indexing/summarization.py \
  README.md \
  tests/test_mcp_server_cli.py \
  tests/test_stdio_tool_descriptions.py \
  tests/docs/test_mcpmeta_tool_metadata_contract.py \
  tests/docs/test_mcptasks_protocol_contract.py \
  tests/test_reindex_resume.py \
  tests/test_mcptasks_reindex.py \
  tests/test_mcptasks_write_summaries.py \
  tests/test_tool_handlers_readiness.py \
  tests/test_tool_readiness_fail_closed.py \
  tests/test_handler_path_sandbox.py \
  tests/docs/test_mcptasks_readme_alignment.py \
  plans/phase-plan-v8-MCPTASKS.md
```

## Acceptance Criteria

- [ ] `reindex` and `write_summaries` advertise
      `Tool.execution.taskSupport="optional"`, and the STDIO server exposes the
      native MCP task capability surface through the SDK-supported path.
- [ ] Task-augmented requests return `types.CreateTaskResult` immediately, and
      `tasks/get`, `tasks/list`, `tasks/result`, and `tasks/cancel` behave
      consistently for the two long-running mutation tools.
- [ ] The implementation-owned task registry/store retains task identity,
      repository scope, progress snapshots, cancellation-requested state,
      terminal structured result payloads, and terminal error details.
- [ ] Task-backed `reindex` reuses existing dispatcher/checkpoint progress,
      preserves the current terminal payload shape through `tasks/result`, and
      only cancels at safe lexical or semantic boundaries.
- [ ] Task-backed `write_summaries` exposes bounded summary progress, preserves
      the current terminal payload shape through `tasks/result`, and supports
      best-effort cancellation without corrupting persisted summary state.
- [ ] Readiness refusals, sandbox/path conflicts, and summarizer-unavailable
      failures still occur synchronously before task creation, and non-task
      requests retain a working synchronous execution path.
- [ ] `README.md` accurately documents task-augmented execution for the two
      supported mutation tools and does not imply broader task support,
      distributed execution, or transport/auth changes.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v8-MCPTASKS.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v8-MCPTASKS.md
  artifact_state: staged
```
