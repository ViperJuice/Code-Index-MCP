---
phase_loop_plan_version: 1
phase: SEMEXITTRACE
roadmap: specs/phase-plans-v7.md
roadmap_sha256: 281e159cb20594416bc9aa7f8c9114d5ccec1bc7a800b77d0ef98e069bef60d1
---
# SEMEXITTRACE: Live Force-Full Exit Trace Recovery

## Context

SEMEXITTRACE is the phase-25 follow-up for the v7 semantic hardening roadmap.
SEMCANCEL narrowed the known blocker: unit coverage now proves bounded
summary-call timeout settlement and zero-summary runtime restore, but the live
repo-local `repository sync --force-full` dogfood rerun can still stay in
flight long enough that operators terminate it before closeout persists the
exact blocker.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is tracked and clean in this worktree, and its
  live SHA matches the required
  `281e159cb20594416bc9aa7f8c9114d5ccec1bc7a800b77d0ef98e069bef60d1`.
- The checkout is on `main` at `af5774ca8bad0f582b3a7774539a0f14886cde3a`,
  `main...origin/main` is ahead by `45` commits, the worktree is clean before
  writing this artifact, and `plans/phase-plan-v7-SEMEXITTRACE.md` did not
  exist before this run.
- `.phase-loop/state.json` already marks `SEMEXITTRACE` as the current
  unplanned phase for the same roadmap SHA, so this plan is the missing
  execution handoff for the active downstream blocker rather than a side plan.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the live blocker artifact for
  this phase. Its latest SEMCANCEL evidence snapshot
  (`2026-04-29T06:47:14Z`, observed commit `0032c46a`) records that a fresh
  `repository sync --force-full` stayed in flight for `1:43`, recreated
  lexical rows, persisted `chunk_summaries = 0` and `semantic_points = 0`,
  and then had to be terminated manually.
- `EnhancedDispatcher.index_directory(...)` and
  `rebuild_semantic_for_paths(...)` already maintain useful in-memory
  progress/blocker fields such as `lexical_stage`, `lexical_files_attempted`,
  `lexical_files_completed`, `last_progress_path`, `in_flight_path`,
  `summary_call_timed_out`, `summary_call_file_path`,
  `summary_call_chunk_ids`, `summary_call_timeout_seconds`, and
  `semantic_stage`.
- `GitAwareIndexManager._full_index(...)` already lifts those fields into
  `UpdateResult.semantic` and `UpdateResult.low_level`, but
  `sync_repository_index(...)` only persists `staleness_reason` and
  `last_sync_error` after `_full_index(...)` returns. If the live force-full
  process is terminated first, the exact stage evidence remains transient.
- `uv run mcp-index repository status` currently prints readiness, semantic
  readiness, preflight, `last_sync_error`, and semantic evidence counts, but
  it does not surface a durable repo-local live trace that survives an
  externally terminated force-full run.
- The current dogfood evidence already says the remaining gap is below the
  bounded timeout wording added by SEMCALLTIME and the code-side restore added
  by SEMCANCEL. This phase therefore owns live stage tracing and persisted
  blocker visibility, not another semantic-pipeline redesign.

Practical planning boundary:

- SEMEXITTRACE may add repo-local force-full trace persistence, dispatcher
  stage callbacks, closeout-stage markers, repository-status rendering, and a
  refreshed dogfood evidence report.
- SEMEXITTRACE must stay narrowly on live force-full observability and
  persisted blocker reporting. It must not reopen semantic ranking, semantic
  throughput, general watchdog redesign, release work, or multi-repo topology
  changes.

## Interface Freeze Gates

- [ ] IF-0-SEMEXITTRACE-1 - Force-full trace persistence contract:
      `GitAwareIndexManager.sync_repository_index(..., force_full=True)` keeps
      a repo-scoped durable trace at `<index_location>/force_full_exit_trace.json`
      from force-full start through final closeout. The trace records at least
      the active stage, stage family (`lexical`, `summary_shutdown`,
      `semantic_closeout`, or `final_closeout`), `current_commit`,
      `indexed_commit_before`, `last_progress_path`, `in_flight_path`,
      summary-timeout metadata, and a trace timestamp.
- [ ] IF-0-SEMEXITTRACE-2 - Abort-visible blocker contract: if a live
      force-full run is interrupted or terminated before `_full_index(...)`
      returns, the most recent durable trace remains available to
      `repository status` and does not advance the indexed commit or claim
      semantic success. Successful full-sync closeout or explicit runtime
      restore must mark the trace as completed or clear it so stale trace data
      does not masquerade as a current blocker.
- [ ] IF-0-SEMEXITTRACE-3 - Dispatcher stage-emission contract:
      `EnhancedDispatcher.index_directory(...)` and
      `rebuild_semantic_for_paths(...)` emit stable progress snapshots when
      lexical walking advances, when repo-scope summary-call shutdown begins or
      times out, when semantic writes are blocked or finish, and when the
      semantic stage hands control back to force-full closeout.
- [ ] IF-0-SEMEXITTRACE-4 - Operator surface contract:
      `uv run mcp-index repository status` reports whether the last blocked
      live force-full path was still in lexical indexing, summary-call
      shutdown, runtime restore, or later closeout when execution stopped,
      together with the trace timestamp and the exact blocker source.
- [ ] IF-0-SEMEXITTRACE-5 - Evidence contract:
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the live trace
      evidence, whether runtime containment occurred before process exit or
      only after external termination, and the updated SEMEXITTRACE steering.

## Lane Index & Dependencies

- SL-0 - Force-full trace contract tests; Depends on: SEMCANCEL; Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Dispatcher live-stage emission; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4; Parallel-safe: no
- SL-2 - Git-aware trace persistence and abort-safe closeout; Depends on: SL-0, SL-1; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-3 - Repository-status trace rendering; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4; Parallel-safe: no
- SL-4 - Dogfood evidence reducer and live trace refresh; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: SEMEXITTRACE acceptance; Parallel-safe: no

Lane DAG:

```text
SEMCANCEL
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SL-4 -> SEMEXITTRACE acceptance
```

## Lanes

### SL-0 - Force-Full Trace Contract Tests

- **Scope**: Freeze the durable live-trace and operator-surface expectations
  before implementation so this phase proves exactly where a live force-full
  run stopped instead of relying on manual SQLite inspection after termination.
- **Owned files**: `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`, `tests/test_repository_commands.py`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMEXITTRACE-1 through IF-0-SEMEXITTRACE-5
- **Interfaces consumed**: existing dispatcher lexical/semantic stats,
  `GitAwareIndexManager._full_index(...)`,
  `GitAwareIndexManager.sync_repository_index(...)`,
  `GitAwareIndexManager.get_repository_status(...)`,
  `repository status` CLI output, and the current
  `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` evidence structure
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` so a force-full semantic-stage
    fixture proves dispatcher progress snapshots distinguish lexical walking,
    timed-out summary-call shutdown, semantic-stage return, and later closeout
    handoff without depending on the outer sync path to finish.
  - test: Extend `tests/test_git_index_manager.py` so force-full sync proves
    the repo-scoped durable trace is created before lexical mutation, updated
    as the dispatcher advances, preserved on synthetic interrupt/abort paths,
    and cleared or marked complete on clean closeout.
  - test: Extend `tests/test_repository_commands.py` so `repository status`
    prints the durable trace stage, trace timestamp, and exact blocker source
    for a repo whose last force-full run stopped mid-flight.
  - test: Extend `tests/docs/test_semdogfood_evidence_contract.py` so the
    evidence report must cite SEMEXITTRACE, the traced live stage, and whether
    runtime containment happened before process exit or only after manual
    termination.
  - impl: Keep fixtures synthetic with mocked trace files, monkeypatched
    interrupts, and SQLite-backed stores. Do not add long live waits or real
    SIGTERM dependence to unit coverage.
  - impl: Keep this lane focused on stage persistence and operator evidence.
    Do not rerun the live dogfood command or edit docs here.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_repository_commands.py tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`

### SL-1 - Dispatcher Live-Stage Emission

- **Scope**: Expose stable progress snapshots from the force-full lexical and
  semantic paths so the outer sync layer can persist the exact live stage even
  if the process is terminated before closeout returns.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`
- **Interfaces provided**: IF-0-SEMEXITTRACE-3 via dispatcher-owned progress
  snapshots that report lexical stage changes, summary-call shutdown state,
  semantic-stage return, and closeout handoff metadata to the sync layer
- **Interfaces consumed**: SL-0 dispatcher trace tests; existing
  `index_directory(...)`, `_index_file_with_lexical_timeout(...)`,
  `rebuild_semantic_for_paths(...)`, lexical progress counters, summary-call
  timeout metadata, and semantic-stage blocker vocabulary from SEMCALLTIME and
  SEMCANCEL
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 dispatcher slice first and confirm the current gap is
    not missing per-stage vocabulary but missing durable emission of that
    vocabulary while force-full is still in flight.
  - impl: Add one dispatcher-owned progress callback or equivalent structured
    hook so lexical file progress, summary-call shutdown, semantic blocked
    return, and semantic completion can be emitted incrementally to the outer
    force-full path.
  - impl: Preserve the existing aggregate stats contract returned from
    `index_directory(...)`. This lane should expose stage snapshots, not
    replace the current semantic and low-level summary fields.
  - impl: Keep non-force-full call sites compatible. The new progress hook
    must degrade cleanly when no live trace sink is supplied.
  - impl: Do not broaden into new timeout budgets, semantic ranking changes,
    or runtime restore logic. This lane owns stage emission only.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py -q --no-cov`

### SL-2 - Git-Aware Trace Persistence And Abort-Safe Closeout

- **Scope**: Persist a repo-scoped durable force-full trace around the live
  sync path, preserve the latest stage on interrupted runs, and clear or mark
  the trace complete only after force-full truly finishes or restore
  concludes.
- **Owned files**: `mcp_server/storage/git_index_manager.py`
- **Interfaces provided**: IF-0-SEMEXITTRACE-1; IF-0-SEMEXITTRACE-2; the
  status payload consumed by `get_repository_status(...)` for active or stale
  force-full traces
- **Interfaces consumed**: SL-0 git-index-manager tests; SL-1 dispatcher stage
  snapshots; existing `_full_index(...)`, `_snapshot_active_runtime(...)`,
  `_restore_zero_summary_runtime_if_needed(...)`,
  `_format_sync_error_with_restore_context(...)`,
  `sync_repository_index(...)`, `get_repository_status(...)`, and repo
  `index_location` runtime layout
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 git-index-manager slice first and confirm the current
    live blocker is the persistence boundary: exact stage information exists in
    memory during force-full but is lost when the process is terminated before
    `_full_index(...)` returns.
  - impl: Add one repo-scoped durable trace file contract under the active
    index location and write it at force-full start, on each dispatcher stage
    snapshot, when runtime restore begins, and when final closeout either
    succeeds or fails.
  - impl: Preserve the latest durable trace on synthetic interrupt or abort
    paths so a later `repository status` call can report the stage even when
    `last_sync_error` was never updated by normal closeout.
  - impl: Keep indexed-commit advancement fail-closed and keep restore
    semantics exact. A preserved trace must never imply semantic success or a
    completed indexed commit.
  - impl: Mark the trace complete or clear it only when closeout really
    finished, so stale mid-flight traces do not remain authoritative after a
    successful rerun.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py -q --no-cov`

### SL-3 - Repository-Status Trace Rendering

- **Scope**: Surface the durable force-full trace in the operator CLI so a
  follow-up `repository status` call explains whether the last blocked live run
  stopped in lexical indexing, summary-call shutdown, runtime restore, or
  later closeout.
- **Owned files**: `mcp_server/cli/repository_commands.py`
- **Interfaces provided**: IF-0-SEMEXITTRACE-4 via a repository-status
  rendering contract for durable force-full trace stage, timestamp, and blocker
  source
- **Interfaces consumed**: SL-0 repository-status tests; SL-2 durable trace
  payload from `GitAwareIndexManager.get_repository_status(...)`; existing
  readiness, semantic preflight, and semantic evidence output sections
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 repository-status slice first and confirm the current
    CLI has no durable mid-flight trace surface even when semantic readiness
    remains blocked after manual termination.
  - impl: Extend `repository status` to print the durable force-full trace
    stage, stage family, trace timestamp, and whether the latest blocker came
    from lexical mutation, summary-call shutdown, runtime restore, or later
    closeout.
  - impl: Keep the current readiness, preflight, and semantic evidence output
    intact. This lane should add trace visibility, not redefine readiness or
    semantic blocker vocabulary.
  - impl: Ensure the CLI remains useful both when the trace shows an unfinished
    run and when a later successful rerun has marked the trace complete or
    cleared it.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_repository_commands.py -q --no-cov`

### SL-4 - Dogfood Evidence Reducer And Live Trace Refresh

- **Scope**: Refresh the SEMDOGFOOD evidence with the new trace surface and
  live force-full rerun outcome so operators can see exactly where the repo-
  local rebuild stopped and whether containment happened before exit.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- **Interfaces provided**: IF-0-SEMEXITTRACE-5; refreshed operator evidence for
  downstream roadmap or review work
- **Interfaces consumed**: SL-0 evidence-contract tests; SL-1 dispatcher stage
  names; SL-2 durable force-full trace payload; SL-3 repository-status output;
  the live `repository sync --force-full` rerun and post-run SQLite/status
  counts
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 docs-contract slice first and confirm the evidence
    report currently records manual termination without a precise durable stage
    breadcrumb.
  - impl: Rerun the repo-local `repository sync --force-full` verification
    command during execution and capture the durable trace stage, current-
    versus-indexed commit evidence, and whether runtime containment happened
    before process exit or only after external termination.
  - impl: Update `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` so the SEMEXITTRACE
    report names the trace stage, the live rerun duration, the repository-
    status output, and the exact steering outcome after the traced rerun.
  - impl: Keep this lane as a reducer. Do not broaden it into support-matrix,
    onboarding-guide, or release-note changes unless the live evidence proves a
    direct contract drift that must be documented immediately.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`

## Verification

Lane-specific checks:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py -q --no-cov
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py -q --no-cov
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_repository_commands.py -q --no-cov
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
```

Whole-phase regression commands:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest \
  tests/test_dispatcher.py \
  tests/test_git_index_manager.py \
  tests/test_repository_commands.py \
  tests/docs/test_semdogfood_evidence_contract.py \
  -q --no-cov
env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'
git status --short -- specs/phase-plans-v7.md plans/phase-plan-v7-SEMEXITTRACE.md docs/status/SEMANTIC_DOGFOOD_REBUILD.md
```

## Acceptance Criteria

- [ ] A live repo-local force-full rerun that still fails to complete now
      leaves a precise durable stage trace or in-flight blocker instead of
      requiring manual interpretation of partial SQLite growth.
- [ ] `uv run mcp-index repository status` reports whether the hung path was
      still in lexical indexing, summary-call shutdown, runtime restore, or
      later closeout when execution stopped.
- [ ] Successful or restored closeout clears or marks the durable trace
      complete so stale mid-flight trace data does not remain authoritative.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` captures the trace evidence and
      whether runtime containment happened before process exit or only after
      external termination.
- [ ] Force-full indexed-commit advancement remains fail-closed on every
      blocked or externally terminated rerun.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v7-SEMEXITTRACE.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMEXITTRACE.md
  artifact_state: staged
```
