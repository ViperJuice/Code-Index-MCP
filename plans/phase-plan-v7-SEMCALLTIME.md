---
phase_loop_plan_version: 1
phase: SEMCALLTIME
roadmap: specs/phase-plans-v7.md
roadmap_sha256: e898ff768d7195ac51125cf9370020a7854b98e8e22afe6c07e8dc444e904a23
---
# SEMCALLTIME: Single-Call Summary Timeout Recovery

## Context

SEMCALLTIME is the phase-23 follow-up for the v7 semantic hardening roadmap.
SEMPASSSTALL proved that repo-scope summary work is now narrowed to one file
per pass and one doc-like chunk per file, but the latest live dogfood rerun
still exposed a narrower failure mode: the very first repo-scope summary call
can remain in flight long enough that no authoritative summary row is written
and no exact continuation or timeout blocker is returned promptly.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is tracked and clean in this worktree, and its
  live SHA matches the required
  `e898ff768d7195ac51125cf9370020a7854b98e8e22afe6c07e8dc444e904a23`.
- The checkout is on `main` at `28c9e06ba997`, `main...origin/main` is ahead
  by `41` commits, the worktree is clean before writing this artifact, and
  `plans/phase-plan-v7-SEMCALLTIME.md` did not exist before this run.
- Repo-local phase-loop state already targets `SEMCALLTIME` in
  `.phase-loop/state.json`; the roadmap provenance in that state matches the
  requested roadmap SHA and currently marks `SEMCALLTIME` as `unplanned`.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is still the live blocker artifact
  carried forward from SEMPASSSTALL. Its latest evidence snapshot
  (`2026-04-28T18:45:19Z`, observed commit `7f2c9afb`) shows that a fresh
  force-full rerun rebuilt lexical rows (`666` files, `8934` chunks) but left
  `chunk_summaries = 0` and `semantic_points = 0` because the run stayed in
  flight inside the first repo-scope summary invocation until it was stopped.
- `mcp_server/indexing/summarization.py` already applies the SEMPASSSTALL
  narrowing contract: repo-scope doc work uses
  `_REPO_SCOPE_FILE_LIMIT = 1`,
  `_REPO_SCOPE_DOC_PROCESS_SCOPE_CHUNK_LIMIT = 4`,
  `_REPO_SCOPE_DOC_FILE_CHUNK_WINDOW = 1`, and
  `process_scope(..., max_batches=1)`. The remaining gap is that
  `process_scope(...)` still waits for a full `summarize_file_chunks(...)`
  return, and `summarize_file_chunks(...)` still awaits one batch or recovery
  call for the selected chunk set before any exact timeout verdict is emitted.
- `mcp_server/dispatcher/dispatcher_enhanced.py` already wraps each summary
  pass in `asyncio.wait_for(...)`, halves `summary_limit`, and surfaces
  `blocked_summary_timeout`, `blocked_summary_plateau`, and
  `blocked_missing_summaries`. The live evidence shows that this broader pass
  timeout surface is still too coarse when the first summary call never
  returns promptly enough to write one authoritative row or expose a narrower
  timed-out-call contract.
- `mcp_server/storage/git_index_manager.py` already preserves dispatcher
  semantic stats such as `summary_passes`, `summary_remaining_chunks`,
  `summary_scope_drained`, `summary_continuation_required`, `semantic_stage`,
  and `semantic_error`. This phase should extend that closeout and status
  surfacing only as needed to prove the remaining blocker is now bounded and
  exact rather than an indefinitely in-flight first call.

Practical planning boundary:

- SEMCALLTIME may add a bounded single-call timeout or cancellation contract
  inside the repo-scope summary path, carry that exact blocker through the
  dispatcher and repository-status surfaces, rerun the live force-full
  sequence, and refresh the durable dogfood evidence artifact.
- SEMCALLTIME must stay narrowly on the first-call summary hang. It must not
  reopen repo-wide pass-budget design, semantic ranking, multi-repo rollout
  expansion, artifact publishing, or release workflow work.

## Interface Freeze Gates

- [ ] IF-0-SEMCALLTIME-1 - Single-call summary timeout contract:
      `SummaryGenerationResult`, `ComprehensiveChunkWriter.process_scope(...)`,
      and `FileBatchSummarizer.summarize_file_chunks(...)` expose an exact
      bounded timeout or cancellation result for the selected repo-scope
      file/chunk window instead of allowing the first summary invocation to
      stay in flight indefinitely.
- [ ] IF-0-SEMCALLTIME-2 - Dispatcher blocker contract:
      `EnhancedDispatcher.rebuild_semantic_for_paths(...)` distinguishes a
      first-call summary timeout from repo-wide pass-budget exhaustion and
      returns an exact fail-closed semantic-stage blocker with current
      summary-pass counters and remaining-summary counts.
- [ ] IF-0-SEMCALLTIME-3 - Force-full closeout and status contract:
      `GitAwareIndexManager._full_index(...)`,
      `GitAwareIndexManager.sync_repository_index(...)`, and
      `uv run mcp-index repository status` preserve the exact single-call
      timeout blocker together with current summary/vector counts and do not
      advance indexed-commit freshness on a zero-summary partial run.
- [ ] IF-0-SEMCALLTIME-4 - Evidence contract:
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` cites
      `plans/phase-plan-v7-SEMCALLTIME.md`, records the repaired rerun,
      summary/vector counts, current-versus-indexed commit evidence, and
      whether the active repo now persists at least one authoritative summary
      or fails closed with the exact single-call timeout blocker.

## Lane Index & Dependencies

- SL-0 - Single-call timeout contract tests and fixture freeze; Depends on: SEMPASSSTALL; Blocks: SL-1, SL-2, SL-3; Parallel-safe: no
- SL-1 - Repo-scope single-call timeout and cancellation repair; Depends on: SL-0; Blocks: SL-2, SL-3; Parallel-safe: no
- SL-2 - Dispatcher blocker surfacing and repository-status closeout; Depends on: SL-0, SL-1; Blocks: SL-3; Parallel-safe: no
- SL-3 - Repo-local rerun evidence reducer and status refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SEMCALLTIME acceptance; Parallel-safe: no

Lane DAG:

```text
SEMPASSSTALL
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SEMCALLTIME acceptance
```

## Lanes

### SL-0 - Single-Call Timeout Contract Tests And Fixture Freeze

- **Scope**: Freeze the exact first-call hang contract before runtime changes
  so this phase proves a bounded timed-out-call result or first-summary
  persistence instead of only reducing the same broad pass timeout indirectly.
- **Owned files**: `tests/test_summarization.py`, `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMCALLTIME-1 through IF-0-SEMCALLTIME-3
- **Interfaces consumed**: existing
  `SummaryGenerationResult`,
  `FileBatchSummarizer.summarize_file_chunks(...)`,
  `ComprehensiveChunkWriter.process_scope(...)`,
  `EnhancedDispatcher.rebuild_semantic_for_paths(...)`,
  `EnhancedDispatcher._count_missing_summaries_for_paths(...)`,
  `GitAwareIndexManager._full_index(...)`, and
  `GitAwareIndexManager.sync_repository_index(...)`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_summarization.py` so repo-scope doc-like cases
    prove that the first `summarize_file_chunks(...)` invocation can return a
    bounded timed-out-call result or exact partial-progress result instead of
    leaving `process_scope(..., max_batches=1)` waiting indefinitely.
  - test: Extend `tests/test_dispatcher.py` so the dispatcher distinguishes
    "first call timed out before any authoritative summary write" from broader
    repo-wide pass-budget continuation, plateau, and downstream semantic-stage
    blockers.
  - test: Extend `tests/test_git_index_manager.py` so force-full closeout and
    repository status preserve the exact first-call timeout blocker, current
    summary/vector counts, and zero-summary freshness refusal after a bounded
    failed call.
  - impl: Keep fixtures deterministic with monkeypatched summarizer coroutines,
    synthetic timeout/cancellation behavior, and SQLite-backed stores; do not
    introduce live network waits into unit coverage.
  - impl: Keep this lane focused on first-call timeout semantics only. Do not
    update docs or run the live repo-local rerun here.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_summarization.py tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov`

### SL-1 - Repo-Scope Single-Call Timeout And Cancellation Repair

- **Scope**: Repair the repo-scope summary path so the first selected
  file/chunk window cannot monopolize the entire semantic stage without
  returning an exact timed-out-call result or authoritative progress.
- **Owned files**: `mcp_server/indexing/summarization.py`
- **Interfaces provided**: IF-0-SEMCALLTIME-1 through
  `SummaryGenerationResult`,
  `FileBatchSummarizer.summarize_file_chunks(...)`, and
  `ComprehensiveChunkWriter.process_scope(...)`
- **Interfaces consumed**: SL-0 single-call timeout tests; existing
  `_call_profile_batch_api(...)`, `_call_batch_api(...)`,
  `_recover_with_profile_or_topological(...)`,
  `_file_chunk_window_for_language(...)`, authoritative `chunk_summaries`
  persistence, and repo-scope doc-like narrowing
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 summarization slice first and confirm the current
    repo-scope doc-like path can still wait on one first-call summary
    invocation long enough that no authoritative summary row is written.
  - impl: Extend `SummaryGenerationResult` with exact timed-out-call metadata
    needed by downstream code so the summarizer can fail closed without
    throwing away current file/chunk context.
  - impl: Add a bounded timeout or equivalent cancellation helper around the
    first repo-scope summary invocation inside `summarize_file_chunks(...)`
    and/or `process_scope(...)`, returning an exact timed-out-call result when
    the selected file/chunk window does not complete promptly.
  - impl: Preserve authoritative persistence, partial-progress accounting,
    `missing_chunk_ids`, topological recovery, and targeted single-file
    behavior. This lane must not hide true failures or broaden into prompt,
    preflight, or vector-write changes.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_summarization.py -q --no-cov`

### SL-2 - Dispatcher Blocker Surfacing And Repository-Status Closeout

- **Scope**: Carry the repaired single-call timeout contract through the real
  force-full semantic path so the active repo records an exact blocker or
  first-summary progress instead of appearing stuck inside one in-flight call.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/storage/git_index_manager.py`
- **Interfaces provided**: IF-0-SEMCALLTIME-2 dispatcher blocker contract;
  IF-0-SEMCALLTIME-3 force-full closeout and status contract
- **Interfaces consumed**: SL-0 dispatcher and git-index-manager tests;
  SL-1 timed-out-call metadata; existing `asyncio.wait_for(...)` summary-pass
  orchestration, `summary_limit` backoff, `summary_passes`,
  `summary_remaining_chunks`, `summary_scope_drained`,
  `summary_continuation_required`, semantic preflight, and indexed-commit
  freshness rules
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 dispatcher and git-index-manager slices first and
    confirm the current live blocker is specifically the first summary call,
    not a reopened repo-wide pass-budget, lexical, or semantic-query
    regression.
  - impl: Teach `rebuild_semantic_for_paths(...)` to consume the SL-1
    timed-out-call metadata directly and surface an exact fail-closed blocker
    when the first summary invocation times out before authoritative summary
    persistence.
  - impl: Preserve the existing continuation and plateau behavior for true
    multi-pass progress. This lane should narrow the blocker vocabulary for
    the first-call hang without softening readiness gating or advancing into a
    false semantic-ready verdict.
  - impl: Tighten `GitAwareIndexManager` only as needed so `_full_index(...)`
    and `sync_repository_index(...)` preserve the exact first-call timeout
    blocker, current summary/vector counts, and zero-summary freshness refusal
    through force-full closeout and `repository status`.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov`
  - verify: `env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - verify: `sqlite3 .mcp-index/current.db 'select count(*) from chunk_summaries; select count(*) from semantic_points;'`

### SL-3 - Repo-Local Rerun Evidence Reducer And Status Refresh

- **Scope**: Re-run the repaired repo-local force-full path, reduce the
  outcome into the durable dogfood evidence artifact, and refresh the status
  proof so this phase records the bounded first-call outcome explicitly.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMCALLTIME-4 evidence contract
- **Interfaces consumed**: SL-0 blocker vocabulary; SL-1 timed-out-call or
  first-summary result semantics; SL-2 rerun outcome, repository-status
  verdict, current-versus-indexed commit evidence, and SQLite summary/vector
  counts
- **Parallel-safe**: no
- **Tasks**:
  - test: Update `tests/docs/test_semdogfood_evidence_contract.py` so the
    refreshed report must cite `plans/phase-plan-v7-SEMCALLTIME.md`, record
    whether the active repo now persists at least one authoritative summary or
    fails closed with the exact single-call timeout blocker, and capture
    current summary/vector counts plus current-versus-indexed commit evidence.
  - impl: Re-run the repo-local force-full rebuild with the same strict
    watchdog posture used by SEMTIMEOUT and SEMPASSSTALL, and record whether
    the repaired code now writes at least one authoritative summary row before
    returning or instead yields the exact bounded single-call timeout blocker.
  - impl: Refresh `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` with the rerun
    command, status output, SQLite counts, current-versus-indexed commit
    evidence, and the repaired verdict. If no broader guide or support-matrix
    change is needed, record that decision in the status artifact rather than
    widening this phase's docs scope.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
  - verify: `env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - verify: `sqlite3 .mcp-index/current.db 'select count(*) from chunk_summaries; select count(*) from semantic_points;'`

## Verification

- `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_summarization.py tests/test_dispatcher.py tests/test_git_index_manager.py tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
- `env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full`
- `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
- `sqlite3 .mcp-index/current.db 'select count(*) from chunk_summaries; select count(*) from semantic_points;'`

## Acceptance Criteria

- [ ] A force-full rebuild on the active repo no longer spends multiple
      minutes inside the first repo-scope summary invocation with zero new
      `chunk_summaries`.
- [ ] Repo-scope summary execution applies a bounded per-call timeout or
      equivalent cancellation path that returns an exact blocker when one
      summary call does not complete promptly.
- [ ] `uv run mcp-index repository status` and
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` record the repaired per-call
      behavior together with current summary/vector counts and the exact
      follow-on blocker, if any.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v7-SEMCALLTIME.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMCALLTIME.md
  artifact_state: staged
```
