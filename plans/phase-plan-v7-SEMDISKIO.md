---
phase_loop_plan_version: 1
phase: SEMDISKIO
roadmap: specs/phase-plans-v7.md
roadmap_sha256: 2dbb733207a703d5bb0ffec1d39c8e2785464df56ba93bfa2912e8d85506b5aa
---
# SEMDISKIO: Force-Full Semantic Closeout Disk I/O Recovery

## Context

SEMDISKIO is the phase-35 follow-up for the v7 semantic hardening roadmap.
SEMSCRIPTREBOUND proved the live repo-local `repository sync --force-full`
rerun no longer remains on the renewed
`scripts/quick_mcp_vs_native_validation.py` lexical seam, but the same rerun
now exits later in final semantic closeout with `disk I/O error` before any
authoritative summaries or vectors are written.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is the active roadmap, it is tracked and clean in
  this worktree, and `sha256sum specs/phase-plans-v7.md` matches the required
  `2dbb733207a703d5bb0ffec1d39c8e2785464df56ba93bfa2912e8d85506b5aa`.
- Canonical phase-loop state exists under `.phase-loop/`; both
  `.phase-loop/tui-handoff.md` and `.phase-loop/state.json` mark `SEMDISKIO`
  as the current `unplanned` phase on the same roadmap SHA, with
  `SEMSCRIPTREBOUND` complete, a clean worktree before this plan write, and
  `HEAD` `bf04bb62c1a2` on `main...origin/main [ahead 65]`.
- The target artifact `plans/phase-plan-v7-SEMDISKIO.md` did not exist before
  this planning run.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the active dogfood evidence
  anchor. Its latest SEMSCRIPTREBOUND snapshot (`2026-04-29T10:13:12Z`,
  observed commit `1e7a2a10`) records that the refreshed live rerun advanced
  past the earlier `.devcontainer/devcontainer.json` and
  `scripts/quick_mcp_vs_native_validation.py` seams, then exited with
  `disk I/O error` while the durable trace reported
  `Trace status: completed`,
  `Trace stage: force_full_failed`,
  `Trace stage family: final_closeout`, and
  `Trace blocker source: final_closeout`.
- That same evidence snapshot still shows lexical/runtime progress well beyond
  the earlier rebound family:
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/mcp_server/document_processing/__init__.py`,
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/mcp_server/document_processing/chunk_optimizer.py`,
  `chunk_summaries = 0`, and `semantic_points = 0`.
- `mcp_server/storage/sqlite_store.py` already treats `"disk I/O error"` and
  `"database or disk is full"` as storage-failure signals inside
  `_get_connection()`: it rolls back, flips the store into `_readonly = True`,
  increments `mcp_storage_readonly_total`, and raises
  `TransientArtifactError(...)`. `tests/test_disk_full.py` currently freezes
  the ENOSPC/read-only transition, read-after-readonly behavior, and
  write-after-readonly refusal, but it does not yet freeze the exact
  force-full closeout lineage exposed by the live semantic rerun.
- `mcp_server/dispatcher/dispatcher_enhanced.py` already records
  lexical-phase storage blockers with `storage_diagnostics`, then hands the
  repo-local semantic stage to `rebuild_semantic_for_paths(...)` and emits the
  final `force_full_closeout_handoff` snapshot. Its current broad
  `Batch semantic indexing failed: ...` path should be reviewed against
  `TransientArtifactError` and exact closeout-stage storage failures.
- `mcp_server/storage/git_index_manager.py` already snapshots the runtime
  before force-full work, preserves a durable `force_full_exit_trace.json`,
  computes blocker source through `_trace_blocker_source(...)`, and restores
  the runtime only for the current `blocked_summary_call_timeout` +
  zero-summary + zero-vector case. A post-lexical disk-I/O failure with zero
  summaries/vectors currently lands as a generic final-closeout failure rather
  than an exact storage-closeout/runtime-preservation contract.
- `mcp_server/cli/repository_commands.py` already prints `Force-full exit
  trace`, `Last sync error`, semantic summary/vector counts, and the exact
  lexical boundary lines accumulated by prior phases, including
  `scripts/quick_mcp_vs_native_validation.py`. This phase should keep those
  earlier boundary lines intact while making the downstream closeout/storage
  verdict more exact.

Practical planning boundary:

- SEMDISKIO may tighten storage-failure classification, runtime preservation,
  final-closeout trace semantics, repository-status rendering, and the live
  dogfood evidence needed to prove the post-lexical disk-I/O blocker is either
  repaired or truthfully narrowed.
- SEMDISKIO must stay on the post-lexical semantic closeout failure. It must
  not reopen `.devcontainer/devcontainer.json`,
  `scripts/quick_mcp_vs_native_validation.py`,
  `tests/test_artifact_publish_race.py`, `ai_docs/jedi.md`,
  `ai_docs/*_overview.md`, fast-test report handling, summary timeout tuning,
  or semantic ranking unless a refreshed rerun directly re-anchors there
  again.

## Interface Freeze Gates

- [ ] IF-0-SEMDISKIO-1 - Storage failure classification contract:
      post-lexical SQLite closeout failures caused by `disk I/O error`,
      `database or disk is full`, or the store's follow-on read-only posture
      are surfaced as an exact storage/closeout blocker through
      `SQLiteStore`, `EnhancedDispatcher`, and `GitAwareIndexManager` rather
      than collapsing into an unqualified generic failure.
- [ ] IF-0-SEMDISKIO-2 - Force-full runtime preservation contract:
      when a force-full semantic rebuild reaches final closeout and exits on
      the SEMDISKIO storage blocker before any summaries or vectors are
      durably written, the active runtime is either preserved/restored
      explicitly or the closeout blocker reports why restoration was unsafe;
      indexed-commit freshness must not advance on that failure path.
- [ ] IF-0-SEMDISKIO-3 - Operator status contract:
      `force_full_exit_trace.json` and `uv run mcp-index repository status`
      distinguish this post-lexical storage-closeout failure from lexical
      blockers and summary-call timeouts, preserve storage diagnostics or
      runtime-restore context where available, and keep all earlier exact
      lexical boundary lines intact.
- [ ] IF-0-SEMDISKIO-4 - Evidence contract:
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` cites
      `plans/phase-plan-v7-SEMDISKIO.md`, records the rerun command and
      outcome, current-versus-indexed commit evidence, summary/vector counts,
      force-full trace fields, and whether the repaired run now writes
      authoritative summaries or exits with a narrower truthful storage or
      semantic closeout blocker.

## Lane Index & Dependencies

- SL-0 - Disk-I/O closeout contract and fixture freeze; Depends on: SEMSCRIPTREBOUND; Blocks: SL-1, SL-2, SL-3; Parallel-safe: no
- SL-1 - SQLite storage failure classification and read-only provenance repair; Depends on: SL-0; Blocks: SL-2, SL-3; Parallel-safe: no
- SL-2 - Force-full closeout runtime preservation and trace/status propagation; Depends on: SL-0, SL-1; Blocks: SL-3; Parallel-safe: no
- SL-3 - Repo-local rerun evidence reducer and operator closeout refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SEMDISKIO acceptance; Parallel-safe: no

Lane DAG:

```text
SEMSCRIPTREBOUND
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SEMDISKIO acceptance
```

## Lanes

### SL-0 - Disk-I/O Closeout Contract And Fixture Freeze

- **Scope**: Freeze the current post-lexical disk-I/O closeout failure in unit
  coverage so this phase proves exact storage-blocker, runtime-preservation,
  and status-surface behavior instead of only shifting the generic
  `final_closeout` wording.
- **Owned files**: `tests/test_disk_full.py`, `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMDISKIO-1 through IF-0-SEMDISKIO-3
- **Interfaces consumed**: existing
  `SQLiteStore._get_connection()`,
  `TransientArtifactError`,
  `EnhancedDispatcher.index_directory(...)`,
  `EnhancedDispatcher.rebuild_semantic_for_paths(...)`,
  `GitAwareIndexManager.sync_repository_index(...)`,
  `GitAwareIndexManager._restore_zero_summary_runtime_if_needed(...)`,
  `GitAwareIndexManager._trace_blocker_source(...)`,
  `GitAwareIndexManager._write_force_full_exit_trace(...)`,
  `_print_force_full_exit_trace(...)`, and the current SEMSCRIPTREBOUND
  blocker vocabulary from `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_disk_full.py` so disk-I/O-style operational
    errors are frozen as the same storage-failure family as ENOSPC and expose
    any new read-only provenance or diagnostic fields this phase adds.
  - test: Extend `tests/test_dispatcher.py` with a semantic-closeout fixture
    that raises `TransientArtifactError("disk I/O error")` after lexical work
    has already completed, and require the dispatcher result to preserve exact
    post-lexical storage blocker semantics instead of looking like a lexical
    timeout or generic unclassified semantic crash.
  - test: Extend `tests/test_git_index_manager.py` so force-full sync on a
    post-lexical disk-I/O failure preserves the correct `final_closeout`
    lineage, does not advance indexed commit freshness, and freezes whether a
    zero-summary/zero-vector runtime restore must occur or be explicitly
    declined with a truthful reason.
  - test: Extend `tests/test_repository_commands.py` so `repository status`
    prints the repaired disk-I/O closeout trace and any new restore or
    diagnostics context while preserving the existing exact lexical boundary
    lines from earlier phases.
  - impl: Use synthetic dispatcher/store fixtures and temp SQLite runtimes
    rather than live disk exhaustion or long-running semantic rebuilds in unit
    coverage.
  - impl: Keep this lane focused on contract freeze only. Do not edit the
    dogfood evidence artifact or run the live repo-local rerun here.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_disk_full.py tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "disk or readonly or transient or closeout or force_full or trace or repository_status"`

### SL-1 - SQLite Storage Failure Classification And Read-Only Provenance Repair

- **Scope**: Tighten the storage layer so post-lexical disk-I/O failures carry
  stable classification and diagnostics upstream instead of becoming only raw
  exception strings at final closeout.
- **Owned files**: `mcp_server/storage/sqlite_store.py`
- **Interfaces provided**: IF-0-SEMDISKIO-1 storage failure classification
  contract
- **Interfaces consumed**: SL-0 storage-layer tests; existing
  `TransientArtifactError`,
  `_readonly`,
  `mcp_storage_readonly_total`,
  `_get_connection()`, and `health_check()`
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 `tests/test_disk_full.py` slice first and confirm the
    current store behavior still exposes disk-I/O failures only through the
    coarse read-only transition and generic error text.
  - impl: Factor or tighten the existing disk-I/O/ENOSPC detection so
    `disk I/O error`, `database or disk is full`, and any equivalent
    read-only follow-on state are classified consistently in one place.
  - impl: Preserve the current safety posture: writes fail closed after the
    store becomes read-only, reads still work where the code already relies on
    them, and no secret-bearing diagnostics are introduced.
  - impl: Expose only the minimum new metadata needed by downstream closeout
    code, such as a stable storage-failure family or read-only reason, instead
    of inventing a broad new storage telemetry schema.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_disk_full.py -q --no-cov`

### SL-2 - Force-Full Closeout Runtime Preservation And Trace/Status Propagation

- **Scope**: Repair the force-full semantic closeout path so a post-lexical
  disk-I/O failure produces an exact blocker, preserves or restores the active
  runtime when required, and keeps durable trace semantics aligned with the
  true closeout failure.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/storage/git_index_manager.py`
- **Interfaces provided**: IF-0-SEMDISKIO-1 storage failure classification
  contract; IF-0-SEMDISKIO-2 force-full runtime preservation contract;
  IF-0-SEMDISKIO-3 trace/status propagation contract
- **Interfaces consumed**: SL-0 dispatcher and index-manager tests; SL-1
  storage-failure classification; existing
  `storage_diagnostics`,
  `rebuild_semantic_for_paths(...)`,
  `semantic_error`,
  `_snapshot_active_runtime(...)`,
  `_restore_zero_summary_runtime_if_needed(...)`,
  `_format_sync_error_with_restore_context(...)`,
  `_trace_blocker_source(...)`,
  `_make_force_full_progress_callback(...)`, and
  `force_full_exit_trace.json`
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 dispatcher and git-index-manager slices first and
    confirm the current failure still lands as a generic post-lexical
    `final_closeout` error without a dedicated disk-I/O closeout/runtime
    preservation contract.
  - impl: Teach the dispatcher's semantic closeout error path to preserve
    exact storage-failure semantics and diagnostics when the semantic stage
    raises `TransientArtifactError` or equivalent disk-I/O storage failures
    after lexical walking is already complete.
  - impl: Tighten `GitAwareIndexManager` so force-full sync can distinguish
    summary-call timeout restore cases from SEMDISKIO storage-closeout cases,
    and either reuse or extend runtime restoration when zero summaries and
    zero vectors would otherwise leave the active runtime degraded.
  - impl: Preserve current fail-closed behavior: indexed-commit freshness must
    not advance on disk-I/O closeout failure, and the trace/status surfaces
    must not pretend lexical or semantic readiness succeeded.
  - impl: Keep the blocker vocabulary exact. If the repaired rerun still
    fails, the closeout trace should name storage or restore truthfully rather
    than collapsing back into `scripts/quick_mcp_vs_native_validation.py`,
    `.devcontainer/devcontainer.json`, summary timeout, or a generic
    unqualified `Full index failed`.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov -k "disk or transient or closeout or runtime_restore or force_full"`
  - verify: `env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - verify: `sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'`

### SL-3 - Repo-Local Rerun Evidence Reducer And Operator Closeout Refresh

- **Scope**: Re-run the repaired repo-local force-full path, reduce the
  outcome into the durable dogfood evidence artifact, and keep the
  operator-facing closeout narrative aligned with the real rerun result.
- **Owned files**: `mcp_server/cli/repository_commands.py`, `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMDISKIO-3 operator status contract;
  IF-0-SEMDISKIO-4 evidence contract
- **Interfaces consumed**: SL-0 repository-status expectations; SL-1
  storage-failure provenance; SL-2 force-full rerun result, trace fields,
  runtime-restore outcome, summary/vector counts, and current-versus-indexed
  commit evidence
- **Parallel-safe**: no
- **Tasks**:
  - test: Update `tests/docs/test_semdogfood_evidence_contract.py` so the
    refreshed report must cite `plans/phase-plan-v7-SEMDISKIO.md`, preserve
    the earlier lexical-boundary lineage, and record whether the live rerun
    now writes authoritative summaries or exits with the narrower repaired
    storage/semantic closeout verdict.
  - impl: Tighten `mcp_server/cli/repository_commands.py` only as needed so
    `repository status` prints the exact SEMDISKIO closeout truth, including
    any new restore or storage diagnostics surfaced by SL-2, while preserving
    the existing exact lexical boundary lines from prior phases.
  - impl: Re-run the repo-local force-full command with the same strict
    watchdog posture used by recent semantic dogfood phases and capture the
    outcome in `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`.
  - impl: Refresh the status artifact with the rerun command, status output,
    `force_full_exit_trace.json` fields, current-versus-indexed commit
    evidence, SQLite counts, and the repaired verdict. If no broader docs are
    needed, record that decision in the status artifact rather than widening
    this phase's docs scope.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
  - verify: `env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - verify: `sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'`

## Verification

- `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_disk_full.py tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_repository_commands.py tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
- `env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full`
- `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
- `sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'`

## Acceptance Criteria

- [ ] Unit coverage proves that post-lexical `disk I/O error` and equivalent
      store read-only failures are classified as an exact SEMDISKIO
      storage/closeout blocker instead of being rendered as a lexical blocker,
      summary timeout, or generic unqualified failure.
- [ ] A force-full rebuild on the active repo does not advance indexed-commit
      freshness when final semantic closeout fails on the SEMDISKIO storage
      path, and it preserves or restores the runtime explicitly when zero
      summaries and zero vectors would otherwise leave the runtime degraded.
- [ ] `force_full_exit_trace.json` and `uv run mcp-index repository status`
      report the repaired closeout truthfully, preserve prior lexical boundary
      lines, and include any exact storage or runtime-restore context added by
      this phase.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` cites
      `plans/phase-plan-v7-SEMDISKIO.md` and records either a successful rerun
      with non-zero summary progress or the narrower truthful post-lexical
      storage/semantic closeout blocker that remains.
