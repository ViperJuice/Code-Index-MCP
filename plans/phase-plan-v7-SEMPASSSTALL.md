---
phase_loop_plan_version: 1
phase: SEMPASSSTALL
roadmap: specs/phase-plans-v7.md
roadmap_sha256: 58803caaf5bf2cb323e15b51281494757742813dfd71db233b3914db928115af
---
# SEMPASSSTALL: Single-Pass Summary Stall Recovery

## Context

SEMPASSSTALL is the phase-22 follow-up for the v7 semantic hardening roadmap.
SEMTIMEOUT proved that the repo-wide summary loop can now persist
authoritative summaries and surface bounded continuation pressure across
multiple passes, but the live repo-local rerun still has a narrower failure
mode left: one doc-heavy summary call can consume an entire bounded pass
before the dispatcher can report the continuation blocker promptly.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is tracked and clean in this worktree, and its
  live SHA matches the required
  `58803caaf5bf2cb323e15b51281494757742813dfd71db233b3914db928115af`.
- The checkout is on `main` at `bf4bc95d0e78`, `main...origin/main` is ahead
  by `39` commits, the worktree is clean before writing this artifact, and
  `plans/phase-plan-v7-SEMPASSSTALL.md` did not exist before this run.
- Repo-local phase-loop state exists in `.phase-loop/state.json` and
  `.phase-loop/events.jsonl`, but the reconciled state currently points back
  to `SEMCONTRACT` and carries repeated `SEMTIMEOUT` phase-mismatch warnings.
  This artifact is therefore an explicit user-directed downstream handoff for
  `SEMPASSSTALL`, not the runner's default next-phase selection.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is still the live blocker
  artifact carried forward from SEMTIMEOUT. Its latest evidence snapshot
  (`2026-04-28T17:19:00Z`, observed commit `57bcec0d`) shows that the latest
  force-full rerun increased `chunk_summaries` from `0` to `269` while
  `semantic_points` remained `0`, semantic preflight stayed `ready`, lexical
  freshness regressed to `stale_commit`, and the remaining hot backlog stayed
  concentrated in `.claude/*.md` documents.
- The same evidence proves the repo-wide handoff gap from older phases is no
  longer the main issue: dispatcher retries now persist non-zero summaries,
  repository status reports exact `summaries_missing` counters, and the
  remaining blocker is specifically that the repo can still spend too long
  inside one doc-heavy summary pass before returning the bounded continuation
  verdict.
- `mcp_server/indexing/summarization.py` already narrows repo-scope doc work
  with `_REPO_SCOPE_DOC_PROCESS_SCOPE_CHUNK_LIMIT = 4` and
  `process_scope(..., max_batches=1)`, but each selected file still flows
  through a full `summarize_file_chunks(...)` call. For a large markdown or
  plaintext file, that single call can still monopolize the pass before
  `SummaryGenerationResult` returns updated `remaining_chunks`.
- `mcp_server/dispatcher/dispatcher_enhanced.py` already halves
  `summary_limit`, tracks `summary_passes`, and returns
  `blocked_missing_summaries`, `blocked_summary_plateau`, or
  `blocked_summary_timeout`. SEMPASSSTALL must stay inside the narrower
  single-pass file-boundary gap rather than reopening repo-wide retry logic,
  preflight, semantic ranking, or earlier lexical timeout work.
- `mcp_server/storage/git_index_manager.py` already preserves dispatcher
  semantic stats such as `summary_passes`, `summary_remaining_chunks`, and
  `summary_continuation_required`. This phase should extend closeout/status
  surfacing only as needed so a live rerun that no longer hangs inside one
  doc-heavy pass reports the exact semantic-stage continuation or downstream
  blocker.

Practical planning boundary:

- SEMPASSSTALL may bound single-file summary work inside
  `summarize_file_chunks(...)` / `process_scope(...)`, carry that bounded exit
  through dispatcher and repository-sync status surfaces, rerun the live
  force-full rebuild, and refresh the durable dogfood evidence artifact.
- SEMPASSSTALL must stay narrowly on the remaining single-pass doc-heavy stall
  path. It must not widen into semantic ranking redesign, multi-repo rollout
  expansion, artifact publishing, or new release workflow work.

## Interface Freeze Gates

- [ ] IF-0-SEMPASSSTALL-1 - Single-pass file-bounded summary contract:
      `ComprehensiveChunkWriter.process_scope(..., max_batches=1)` returns a
      bounded result even when the next unsummarized file is markdown,
      plaintext, text, or rst-heavy, and it exposes durable progress or
      remaining-backlog metadata instead of letting one file monopolize the
      full pass timeout.
- [ ] IF-0-SEMPASSSTALL-2 - Dispatcher continuation verdict contract:
      `EnhancedDispatcher.rebuild_semantic_for_paths(...)` translates the
      bounded single-file exit into an exact semantic-stage verdict
      (`blocked_missing_summaries` with continuation details or a narrower
      downstream blocker) instead of a generic summary timeout when progress
      exists but the repo backlog is not yet drained.
- [ ] IF-0-SEMPASSSTALL-3 - Repository status contract:
      `GitAwareIndexManager._full_index(...)`,
      `GitAwareIndexManager.sync_repository_index(...)`, and
      `uv run mcp-index repository status` preserve the current semantic
      readiness verdict together with summary/vector counts after the live
      rerun that no longer hangs inside one doc-heavy pass.
- [ ] IF-0-SEMPASSSTALL-4 - Evidence contract:
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` cites
      `plans/phase-plan-v7-SEMPASSSTALL.md`, records the repaired rerun,
      current-versus-indexed commit evidence, summary/vector counts, and
      whether the repo now reaches the bounded continuation verdict or a
      narrower downstream blocker.

## Lane Index & Dependencies

- SL-0 - Single-pass stall contract tests and fixture freeze; Depends on: SEMTIMEOUT; Blocks: SL-1, SL-2, SL-3; Parallel-safe: no
- SL-1 - Doc-heavy per-file checkpoint and bounded pass return; Depends on: SL-0; Blocks: SL-2, SL-3; Parallel-safe: no
- SL-2 - Dispatcher continuation surfacing and repository-status closeout; Depends on: SL-0, SL-1; Blocks: SL-3; Parallel-safe: no
- SL-3 - Repo-local rerun evidence reducer and status refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SEMPASSSTALL acceptance; Parallel-safe: no

Lane DAG:

```text
SEMTIMEOUT
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SEMPASSSTALL acceptance
```

## Lanes

### SL-0 - Single-Pass Stall Contract Tests And Fixture Freeze

- **Scope**: Freeze the exact doc-heavy single-pass stall contract before
  runtime changes so this phase proves a bounded continuation return from one
  repo-scope pass instead of only shrinking the same timeout indirectly.
- **Owned files**: `tests/test_summarization.py`, `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMPASSSTALL-1 through IF-0-SEMPASSSTALL-3
- **Interfaces consumed**: existing
  `ComprehensiveChunkWriter.process_scope(...)`,
  `ComprehensiveChunkWriter.summarize_file_chunks(...)`,
  `EnhancedDispatcher.rebuild_semantic_for_paths(...)`,
  `EnhancedDispatcher._count_missing_summaries_for_paths(...)`,
  `GitAwareIndexManager._full_index(...)`, and
  `GitAwareIndexManager.sync_repository_index(...)`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_summarization.py` so repo-scope markdown/plaintext
    cases prove that a single `process_scope(..., max_batches=1)` pass can
    return after bounded work on one large doc-like file, preserving
    `remaining_chunks`, `scope_drained`, and any partial authoritative writes
    instead of waiting for a whole-file summary drain.
  - test: Extend `tests/test_dispatcher.py` so the dispatcher treats the
    repaired single-file bounded exit as continuation-worthy progress and does
    not collapse it back into `blocked_summary_timeout` when exact
    continuation metadata is available.
  - test: Extend `tests/test_git_index_manager.py` so force-full closeout and
    repository status preserve the new bounded-continuation details after a
    single-pass doc-heavy rerun rather than returning only an ambiguous stale
    state.
  - impl: Keep fixtures deterministic with monkeypatched summary writers,
    synthetic remaining-count transitions, and SQLite-backed stores; do not
    introduce live network waits into unit coverage.
  - impl: Keep this lane focused on the doc-heavy single-pass stall contract.
    Do not update docs or rerun the live repo here.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_summarization.py tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov`

### SL-1 - Doc-Heavy Per-File Checkpoint And Bounded Pass Return

- **Scope**: Repair the summarizer so one repo-scope pass can checkpoint or
  bound work inside a single large doc-like file and return progress/remaining
  metadata promptly instead of spending the whole pass inside one
  `summarize_file_chunks(...)` call.
- **Owned files**: `mcp_server/indexing/summarization.py`
- **Interfaces provided**: IF-0-SEMPASSSTALL-1 single-pass file-bounded
  summary contract through `SummaryGenerationResult`,
  `ComprehensiveChunkWriter.process_scope(...)`, and
  `ComprehensiveChunkWriter.summarize_file_chunks(...)`
- **Interfaces consumed**: SL-0 single-pass stall tests; existing
  `_process_scope_chunk_limit_for_language(...)`,
  `_recover_with_profile_or_topological(...)`,
  `_summarize_topological(...)`, authoritative `chunk_summaries` persistence,
  and doc-like file-context truncation
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 summarization slice first and confirm the current
    repo-scope doc-heavy path can still spend a whole pass inside one large
    file before `remaining_chunks` and continuation metadata return.
  - impl: Bound per-file work for repo-scope doc-like files so one
    `summarize_file_chunks(...)` invocation can checkpoint after a limited
    chunk subset or equivalent bounded unit of authoritative progress and let
    `process_scope(...)` return promptly with exact remaining backlog.
  - impl: Preserve authoritative persistence, `missing_chunk_ids`, large-file
    recovery, and targeted-path filtering. The repair must expose partial
    progress cleanly without weakening summary correctness or hiding true
    failures.
  - impl: Keep single-file targeted runs and non-doc languages compatible with
    the existing behavior unless the new bounded-return contract requires a
    shared helper. Do not widen this lane into prompt redesign, preflight, or
    vector-write behavior.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_summarization.py -q --no-cov`

### SL-2 - Dispatcher Continuation Surfacing And Repository-Status Closeout

- **Scope**: Carry the bounded single-file summary return through the real
  force-full path so the active repo reports the semantic-stage continuation
  verdict or a narrower downstream blocker instead of hanging inside one
  summary pass.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/storage/git_index_manager.py`
- **Interfaces provided**: IF-0-SEMPASSSTALL-2 dispatcher continuation
  verdict contract; IF-0-SEMPASSSTALL-3 repository status contract
- **Interfaces consumed**: SL-0 dispatcher and git-index-manager tests;
  SL-1 bounded summary result metadata; existing summary-pass budget,
  `summary_limit` backoff, semantic preflight/bootstrap, and indexed-commit
  freshness rules
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 dispatcher and git-index-manager slices first and
    confirm the current live blocker is still the single doc-heavy pass rather
    than a reopened repo-wide timeout taxonomy or semantic-query regression.
  - impl: Teach `rebuild_semantic_for_paths(...)` to treat the SL-1 bounded
    per-file exit as an exact continuation or downstream-blocker surface,
    preserving `summary_passes`, `summary_remaining_chunks`,
    `summary_scope_drained`, and `summary_continuation_required` without
    forcing a generic timeout when progress already exists.
  - impl: Tighten `GitAwareIndexManager` only as needed so `_full_index(...)`
    and `sync_repository_index(...)` carry the repaired continuation verdict
    through force-full closeout and keep `repository status` aligned with the
    live summary/vector counters after the rerun.
  - impl: Preserve fail-closed semantics for true timeout, true plateau, and
    downstream semantic blockers. This lane should narrow the remaining stall,
    not soften readiness gating or advance indexed commits on partial runs.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov`
  - verify: `env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - verify: `sqlite3 .mcp-index/current.db 'select count(*) from chunk_summaries; select count(*) from semantic_points;'`

### SL-3 - Repo-Local Rerun Evidence Reducer And Status Refresh

- **Scope**: Re-run the repaired repo-local force-full sequence, reduce the
  outcome into the durable dogfood evidence artifact, and refresh the status
  proof so this phase records the single-pass repair outcome explicitly.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMPASSSTALL-4 evidence contract
- **Interfaces consumed**: SL-0 blocker vocabulary; SL-1 bounded per-file
  progress semantics; SL-2 rerun outcome, repository-status verdict,
  current-versus-indexed commit evidence, and SQLite summary/vector counts
- **Parallel-safe**: no
- **Tasks**:
  - test: Update `tests/docs/test_semdogfood_evidence_contract.py` so the
    refreshed report must cite `plans/phase-plan-v7-SEMPASSSTALL.md`, record
    whether the repo reaches the semantic-stage bounded continuation verdict
    promptly after the rerun, and capture current summary/vector counts plus
    current-versus-indexed commit evidence.
  - impl: Re-run the repo-local force-full rebuild with the same strict
    watchdog posture used by SEMTIMEOUT, record whether the single-pass
    doc-heavy stall is gone, and capture the exact continuation or downstream
    blocker returned after the repaired run.
  - impl: Refresh `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` with the repaired
    rerun command, status output, SQLite counts, and verdict. If no broader
    guide or support-matrix text changes are needed, record that decision in
    the status artifact rather than widening this phase's docs scope.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
  - verify: `env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - verify: `sqlite3 .mcp-index/current.db 'select count(*) from chunk_summaries; select count(*) from semantic_points;'`

## Verification

- `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_summarization.py tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov`
- `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
- `env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full`
- `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
- `sqlite3 .mcp-index/current.db 'select count(*) from chunk_summaries; select count(*) from semantic_points;'`

## Acceptance Criteria

- [ ] A force-full rebuild on the active repo reaches the semantic-stage
      bounded continuation verdict or a narrower downstream blocker instead of
      stalling inside one doc-heavy summary pass.
- [ ] Repo-wide doc-like summary work is checkpointed or otherwise bounded so
      one file cannot prevent `process_scope(..., max_batches=1)` from
      returning continuation metadata promptly.
- [ ] `uv run mcp-index repository status` reports the current exact semantic
      readiness verdict with summary/vector counts after the live rerun.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is refreshed with
      SEMPASSSTALL evidence, current-versus-indexed commit proof, and the
      current continuation or downstream-blocker verdict.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v7-SEMPASSSTALL.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMPASSSTALL.md
  artifact_state: staged
```
