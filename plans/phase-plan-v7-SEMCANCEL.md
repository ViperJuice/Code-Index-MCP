---
phase_loop_plan_version: 1
phase: SEMCANCEL
roadmap: specs/phase-plans-v7.md
roadmap_sha256: 806890f73e55f7b8c348d7dea97e49d5b5ee751de85bf478d7bb47b29a338d14
---
# SEMCANCEL: Timed-Out Summary Call Exit Recovery

## Context

SEMCANCEL is the phase-24 follow-up for the v7 semantic hardening roadmap.
SEMCALLTIME proved the exact per-call timeout blocker in unit coverage and
landed the status vocabulary for `blocked_summary_call_timeout`, but the live
repo-local force-full rerun still does not exit promptly and can leave the
active runtime in a larger lexical-only partial state after manual
termination.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is tracked and clean in this worktree, and its
  live SHA matches the required
  `806890f73e55f7b8c348d7dea97e49d5b5ee751de85bf478d7bb47b29a338d14`.
- The checkout is on `main` at `fc30a8ca815b`, `main...origin/main` is ahead
  by `43` commits, the worktree is clean before writing this artifact, and
  `plans/phase-plan-v7-SEMCANCEL.md` did not exist before this run.
- `.phase-loop/state.json` already marks `SEMCANCEL` as the current
  unplanned phase for the same roadmap SHA. The immediately prior
  `SEMCALLTIME` phase was manually repaired and committed at
  `fc30a8ca815bf38a77fec2bd526df2b4c9cf1e0d`, so this artifact is the missing
  execution handoff for the next verified downstream blocker rather than a
  speculative side plan.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the live blocker artifact for
  this phase. Its latest SEMCALLTIME evidence snapshot
  (`2026-04-29T06:24:13Z`, observed commit `7ec6351`) records that a fresh
  `repository sync --force-full` started at `2026-04-29T06:19:36Z`, remained
  in flight for more than three minutes with `chunk_summaries = 0` and
  `semantic_points = 0`, then had to be terminated manually.
- The same evidence artifact proves the residual gap is now narrower than
  SEMCALLTIME's vocabulary work: lexical rows in `.mcp-index/current.db`
  expanded to `1046` files and `29194` chunks while semantic progress stayed
  at zero, repository status still reported lexical readiness `stale_commit`,
  semantic readiness `summaries_missing`, query surface `index_unavailable`,
  current commit `7ec6351`, and indexed commit `e2e95198`, and no exact
  timed-out-call blocker was persisted because the force-full sync never
  returned cleanly enough to finish closeout.
- The implementation already contains the exact contract surfaces added by
  SEMCALLTIME: `mcp_server/indexing/summarization.py` exposes timed-out-call
  metadata on `SummaryGenerationResult`, `mcp_server/dispatcher/dispatcher_enhanced.py`
  distinguishes `blocked_summary_call_timeout`, and
  `mcp_server/storage/git_index_manager.py` plus
  `mcp_server/cli/repository_commands.py` can preserve and print exact
  timeout-blocker details once the sync path actually exits.
- The remaining runtime gap is two-layered. First, the timed-out repo-scope
  summary call still does not unwind the live force-full path promptly enough
  for `sync_repository_index(...)` to return. Second, the active runtime is
  still mutated in place: `GitAwareIndexManager._full_index(...)` drives
  `dispatcher.index_directory(...)` directly against the registered
  `.mcp-index/current.db` and `.mcp-index/semantic_qdrant` paths, and there is
  no existing scratch-runtime promotion or automatic rollback when a zero-
  summary timed-out-call failure occurs.

Practical planning boundary:

- SEMCANCEL may tighten timeout cancellation and unwind behavior, add bounded
  active-runtime containment or rollback for zero-summary failures, preserve
  exact blocker/status reporting, rerun the repo-local force-full sequence,
  and refresh the durable dogfood evidence.
- SEMCANCEL must stay narrowly on timed-out summary-call exit and partial-state
  closeout. It must not reopen semantic ranking, multi-repo rollout policy,
  release work, or broader semantic-profile changes already handled by earlier
  v7 phases.

## Interface Freeze Gates

- [ ] IF-0-SEMCANCEL-1 - Timed-out summary-call exit contract:
      a clean `uv run mcp-index repository sync --force-full` on the active
      repo returns promptly after the first timed-out repo-scope summary call
      instead of remaining in flight until manual termination, and the exact
      blocker remains `blocked_summary_call_timeout` or a still narrower
      follow-on blocker produced by the repaired exit path.
- [ ] IF-0-SEMCANCEL-2 - Zero-summary partial-state containment contract:
      when the repaired force-full run exits before any authoritative summary
      or vector persistence, the active `.mcp-index/current.db` and
      `.mcp-index/semantic_qdrant` runtime is restored or preserved so lexical
      row counts do not inflate while `chunk_summaries = 0` and
      `semantic_points = 0`.
- [ ] IF-0-SEMCANCEL-3 - Force-full closeout and status contract:
      `GitAwareIndexManager.sync_repository_index(...)`,
      `RepositoryRegistry.update_last_sync_error(...)`, and
      `uv run mcp-index repository status` preserve the exact timed-out-call
      blocker or `partial_index_failure` follow-on state together with current
      summary/vector counts and current-versus-indexed commit evidence, while
      refusing indexed-commit advancement on a restored or blocked partial run.
- [ ] IF-0-SEMCANCEL-4 - Evidence contract:
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` cites
      `plans/phase-plan-v7-SEMCANCEL.md`, records the repaired rerun command,
      whether prompt exit occurred, pre/post SQLite counts, current-versus-
      indexed commit evidence, and whether the active runtime stayed free of
      enlarged zero-summary partial state.

## Lane Index & Dependencies

- SL-0 - Timeout-exit and zero-summary partial-state contract tests; Depends on: SEMCALLTIME; Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Repo-scope summary-call cancellation and unwind repair; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4; Parallel-safe: no
- SL-2 - Dispatcher force-full exit and mutation-stop wiring; Depends on: SL-0, SL-1; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-3 - Active-runtime rollback and status closeout repair; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4; Parallel-safe: no
- SL-4 - Dogfood evidence reducer and exit-proof refresh; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: SEMCANCEL acceptance; Parallel-safe: no

Lane DAG:

```text
SEMCALLTIME
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SL-4 -> SEMCANCEL acceptance
```

## Lanes

### SL-0 - Timeout-Exit And Zero-Summary Partial-State Contract Tests

- **Scope**: Freeze the exact live exit gap and zero-summary partial-state
  regression before runtime changes so this phase proves prompt force-full
  exit and runtime containment instead of only adding new timeout wording.
- **Owned files**: `tests/test_summarization.py`, `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMCANCEL-1 through IF-0-SEMCANCEL-3
- **Interfaces consumed**: existing `SummaryGenerationResult`,
  `FileBatchSummarizer.summarize_file_chunks(...)`,
  `ComprehensiveChunkWriter.process_scope(...)`,
  `EnhancedDispatcher.rebuild_semantic_for_paths(...)`,
  `EnhancedDispatcher.index_directory(...)`,
  `GitAwareIndexManager._full_index(...)`,
  `GitAwareIndexManager.sync_repository_index(...)`, and
  `RepositoryRegistry.update_last_sync_error(...)`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_summarization.py` so a repo-scope timed-out-call
    fixture proves the summarization layer does not leave late in-flight work
    behind after returning a timeout result, and does not emit post-timeout
    writes that would make zero-summary closeout ambiguous.
  - test: Extend `tests/test_dispatcher.py` so the dispatcher proves the
    semantic stage stops immediately on the first timed-out repo-scope summary
    call, records the exact blocker once, and does not continue into extra
    summary passes or semantic writes after that timeout result.
  - test: Extend `tests/test_git_index_manager.py` so force-full sync proves
    zero-summary timed-out-call failures either preserve or restore the
    pre-run active runtime state, keep indexed-commit freshness unchanged, and
    persist the exact blocker or partial-index-failure follow-on state for
    repository status surfaces.
  - impl: Keep fixtures deterministic with monkeypatched summarizer
    coroutines, synthetic runtime-count snapshots, and SQLite-backed stores;
    do not introduce multi-minute live waits into unit coverage.
  - impl: Keep this lane focused on prompt exit, mutation stop, and partial-
    state containment. Do not update docs or rerun the live dogfood command
    here.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_summarization.py tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov`

### SL-1 - Repo-Scope Summary-Call Cancellation And Unwind Repair

- **Scope**: Repair the repo-scope summary path so the first timed-out
  summary call cannot keep the force-full semantic stage alive after an exact
  timeout result has already been determined.
- **Owned files**: `mcp_server/indexing/summarization.py`
- **Interfaces provided**: IF-0-SEMCANCEL-1 at the summarization layer via
  `SummaryGenerationResult`,
  `FileBatchSummarizer.summarize_file_chunks(...)`, and
  `ComprehensiveChunkWriter.process_scope(...)`
- **Interfaces consumed**: SL-0 summarization timeout-exit tests; existing
  `_call_profile_batch_api(...)`, `_call_batch_api(...)`,
  `_recover_with_profile_or_topological(...)`, repo-scope doc-like narrowing,
  authoritative `chunk_summaries` persistence, and timed-out-call metadata
  from SEMCALLTIME
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 summarization slice first and confirm the current
    repo-scope timed-out-call path can still leave in-flight work alive long
    enough that the caller returns too late or the force-full run never
    unwinds cleanly.
  - impl: Tighten the bounded timeout or cancellation helper around the first
    repo-scope summary invocation so the summarization layer returns only
    after the in-flight work is cancelled or definitively settled, not merely
    after recording timeout metadata.
  - impl: Preserve exact timed-out-call context including file path, chunk
    IDs, timeout seconds, and whether zero summaries were written, so
    downstream closeout can make a deterministic rollback decision.
  - impl: Preserve authoritative persistence, targeted single-file behavior,
    topological recovery, and true partial-progress accounting. This lane must
    not hide real failures or broaden into preflight, vector-write, or status
    formatting changes.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_summarization.py -q --no-cov`

### SL-2 - Dispatcher Force-Full Exit And Mutation-Stop Wiring

- **Scope**: Carry the repaired summarization unwind contract through the real
  semantic-stage orchestration so a timed-out repo-scope summary call ends the
  force-full run promptly instead of leaving repo mutation or semantic-stage
  bookkeeping in flight.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`
- **Interfaces provided**: IF-0-SEMCANCEL-1 timed-out summary-call exit
  contract at the dispatcher layer; mutation-stop bookkeeping consumed by
  closeout
- **Interfaces consumed**: SL-0 dispatcher tests; SL-1 settled timed-out-call
  metadata; existing `rebuild_semantic_for_paths(...)`,
  `index_directory(...)`, `summary_passes`, `summary_remaining_chunks`,
  `summary_call_timed_out`, `summary_call_file_path`,
  `summary_call_chunk_ids`, `summary_call_timeout_seconds`, and semantic-stage
  blocker vocabulary from SEMCALLTIME
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 dispatcher slice first and confirm the current live
    blocker is no longer missing vocabulary but missing prompt unwind after
    the first timed-out summary call.
  - impl: Tighten `rebuild_semantic_for_paths(...)` so a timed-out-call result
    is terminal for the active force-full semantic stage, stops further passes
    or semantic writes immediately, and returns a single exact blocker with
    current summary counters.
  - impl: Preserve existing continuation, plateau, and downstream semantic
    failure behavior for non-timeout cases. This lane should stop live
    mutation after a timed-out call, not weaken readiness gates or convert a
    blocked run into false success.
  - impl: Keep additive semantic stats aligned with the repaired exit path so
    closeout can distinguish "timed out and unwound cleanly" from "timed out
    but runtime containment failed."
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py -q --no-cov`

### SL-3 - Active-Runtime Rollback And Status Closeout Repair

- **Scope**: Repair force-full closeout so zero-summary timed-out-call
  failures do not leave a larger active lexical-only runtime behind, while
  still preserving exact status and blocker reporting for operators.
- **Owned files**: `mcp_server/storage/git_index_manager.py`, `mcp_server/cli/repository_commands.py`, `mcp_server/storage/repository_registry.py`, `mcp_server/storage/multi_repo_manager.py`
- **Interfaces provided**: IF-0-SEMCANCEL-2 zero-summary partial-state
  containment contract; IF-0-SEMCANCEL-3 force-full closeout and status
  contract
- **Interfaces consumed**: SL-0 git-index-manager tests; SL-1 zero-summary
  timed-out-call metadata; SL-2 terminal dispatcher exit result; existing
  `.mcp-index/current.db` and `.mcp-index/semantic_qdrant` runtime layout,
  `sync_repository_index(...)`, `_full_index(...)`,
  `RepositoryRegistry.update_staleness_reason(...)`,
  `RepositoryRegistry.update_last_sync_error(...)`, and repository-status
  output formatting
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 git-index-manager slice first and confirm the current
    failure mode still mutates the active runtime in place: zero summary and
    vector rows, larger lexical counts, stale indexed commit, and no prompt
    closeout after a timed-out summary call.
  - impl: Add one bounded containment path for force-full mutation and keep it
    singular: either snapshot and restore the active SQLite/Qdrant runtime for
    zero-summary timed-out-call exits, or stage the force-full runtime in a
    scratch location and promote it only after semantic-stage success. Choose
    one approach and keep the success and rollback conditions explicit.
  - impl: Preserve the exact blocker surface through
    `sync_repository_index(...)`, `RepositoryRegistry`, and
    `repository status`, including current-versus-indexed commit evidence,
    summary/vector counts, and whether rollback or restore occurred.
  - impl: Keep indexed-commit advancement fail-closed on every blocked or
    restored partial run. This lane must not "fix" `stale_commit` by
    accepting a larger lexical-only runtime as success.
  - impl: Keep this lane local to force-full runtime containment and status
    closeout. Do not widen into artifact publishing, branch-drift policy, or
    semantic query ranking changes.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py -q --no-cov`
  - verify: `env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - verify: `sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'`

### SL-4 - Dogfood Evidence Reducer And Exit-Proof Refresh

- **Scope**: Re-run the repaired repo-local force-full path, reduce the
  outcome into the durable dogfood evidence artifact, and prove whether
  SEMCANCEL restored prompt exit and zero-summary containment on the active
  runtime.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMCANCEL-4 evidence contract
- **Interfaces consumed**: SL-0 blocker vocabulary and runtime-containment
  assertions; SL-1 timed-out-call context; SL-2 prompt exit semantics; SL-3
  rerun outcome, repository-status verdict, rollback or restore evidence, and
  pre/post SQLite counts
- **Parallel-safe**: no
- **Tasks**:
  - test: Update `tests/docs/test_semdogfood_evidence_contract.py` so the
    refreshed report must cite `plans/phase-plan-v7-SEMCANCEL.md`, record
    whether the repaired rerun exited promptly after the first timed-out
    summary call, and capture pre/post SQLite counts together with current-
    versus-indexed commit evidence and the final exact blocker, if any.
  - impl: Re-run the repo-local force-full rebuild with the same strict
    watchdog posture used by SEMCALLTIME and record whether the repaired code
    now exits promptly, whether zero-summary active-runtime inflation was
    prevented, and whether the blocker remains
    `blocked_summary_call_timeout` or narrows again.
  - impl: Refresh `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` with the rerun
    command, repository-status output, pre/post SQLite counts, current-
    versus-indexed commit evidence, and the runtime-containment verdict. If no
    broader guide or support-matrix update is needed, record that decision in
    the status artifact rather than widening this phase's docs scope.
  - impl: Keep this lane as the final reducer only. It must depend on every
    producer lane and must not speculate about success before the repaired
    rerun actually returns.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
  - verify: `env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - verify: `sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'`

## Verification

Lane-focused verification sequence:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_summarization.py tests/test_dispatcher.py tests/test_git_index_manager.py tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'
```

Whole-phase regression guard:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_summarization.py tests/test_dispatcher.py tests/test_git_index_manager.py tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'
```

## Acceptance Criteria

- [ ] A force-full rebuild on the active repo returns promptly after the first
      timed-out repo-scope summary call instead of staying in flight until
      manual termination.
- [ ] `uv run mcp-index repository status` records the exact timed-out-call
      blocker or partial-index-failure follow-on state after the repaired live
      rerun.
- [ ] A terminated or timed-out force-full rerun no longer inflates lexical
      row counts while leaving `chunk_summaries = 0` and
      `semantic_points = 0`.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v7-SEMCANCEL.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMCANCEL.md
  artifact_state: staged
```
