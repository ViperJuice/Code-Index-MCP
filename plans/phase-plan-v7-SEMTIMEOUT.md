---
phase_loop_plan_version: 1
phase: SEMTIMEOUT
roadmap: specs/phase-plans-v7.md
roadmap_sha256: 131107529fcd6ce64f2d801565a899a0b0a5fe5bf07592a08095c0c486d6506a
---
# SEMTIMEOUT: Semantic Summary Timeout Recovery

## Context

SEMTIMEOUT is the phase-21 follow-up for the v7 semantic hardening roadmap.
SEMCLOSEOUT proved that the post-lexical semantic path now persists
authoritative summaries, but the live repo-wide force-full rerun still times
out before strict semantic vector linkage can start.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is tracked and clean in this worktree, and its
  live bytes match the required
  `131107529fcd6ce64f2d801565a899a0b0a5fe5bf07592a08095c0c486d6506a`.
- The checkout is on `main` at `39a029fbbbfc`, `main...origin/main` is ahead
  by `34` commits, the worktree is clean before writing this artifact, and
  `plans/phase-plan-v7-SEMTIMEOUT.md` did not exist before this run.
- There is no existing repo-local `.codex/phase-loop/state.json` or
  `.codex/phase-loop/events.jsonl` to update, so this artifact is the direct
  execution handoff for the next blocked-downstream phase rather than a phase
  loop state repair.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` already records the SEMCLOSEOUT
  evidence snapshot that narrowed the live blocker to semantic summary
  timeout. That report shows the dispatcher now uses bounded one-batch summary
  passes plus timeout backoff, but the force-full rerun still ends with
  `Summary generation timed out before strict semantic indexing could start`,
  leaving lexical readiness `stale_commit`, semantic readiness
  `summaries_missing`, `chunk_summaries` at `234`, `semantic_points` at `0`,
  and `32996` chunks still missing summaries.
- `docs/guides/semantic-onboarding.md` already instructs operators to route
  the next execution step through `SEMTIMEOUT` when SEMCLOSEOUT proves partial
  summary persistence is live but the repo still times out before vector
  linkage.
- The relevant implementation surfaces are now narrower than the earlier
  lexical repair chain. `mcp_server/indexing/summarization.py` owns
  authoritative backlog selection and `ComprehensiveChunkWriter.process_scope(...)`;
  `mcp_server/dispatcher/dispatcher_enhanced.py` owns the repo-scope summary
  retry loop, timeout/backoff behavior, and semantic-stage accounting; and
  `mcp_server/storage/git_index_manager.py` carries the force-full closeout
  verdict into indexed-commit freshness and operator-facing status surfaces.
- The current code already includes the SEMCLOSEOUT bounded-pass shape:
  `process_scope(..., max_batches=1)` exists, dispatcher retries summary
  timeout with smaller limits, and the git-index-manager test surface already
  preserves `summary_passes`, `summary_missing_chunks`, and the exact
  semantic-stage blocker. SEMTIMEOUT therefore must target repo-wide summary
  drain completion and exact downstream handoff, not repeat the earlier
  one-batch/backoff change.

Practical planning boundary:

- SEMTIMEOUT may tighten repo-wide summary scheduling, progress accounting,
  timeout recovery, force-full closeout semantics, and the repo-local dogfood
  evidence needed to prove the summary-timeout blocker is gone.
- SEMTIMEOUT must stay narrowly on repo-wide summary timeout recovery. It must
  not reopen lexical Markdown timeout work, semantic ranking redesign, or
  broader multi-repo rollout expansion beyond this repo-local dogfood path.

## Interface Freeze Gates

- [ ] IF-0-SEMTIMEOUT-1 - Repo-wide summary timeout recovery contract:
      a clean `uv run mcp-index repository sync --force-full` on the active
      repo no longer exits with `Summary generation timed out before strict
      semantic indexing could start`, and the summary stage either drains to
      completion or surfaces a new exact downstream blocker after summaries
      are no longer the timeout gate.
- [ ] IF-0-SEMTIMEOUT-2 - Bounded summary progress contract:
      `ComprehensiveChunkWriter.process_scope(...)` plus dispatcher orchestration
      expose deterministic one-batch progress for repo-wide summary drain,
      including enough remaining-backlog or continuation evidence for the
      force-full path to distinguish live progress, plateau, timeout backoff,
      and downstream handoff without claiming success early.
- [ ] IF-0-SEMTIMEOUT-3 - Force-full closeout and status contract:
      `GitAwareIndexManager` preserves exact summary-pass and blocker details,
      does not advance indexed commit while summary drain is incomplete, and
      once the timeout gate is removed either advances to the current commit
      or records a narrower semantic-stage blocker than summary timeout.
- [ ] IF-0-SEMTIMEOUT-4 - Evidence contract:
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` and
      `docs/guides/semantic-onboarding.md` record the timeout recovery rerun,
      current summary/vector counts, repo-vs-indexed commit evidence, and the
      new exact downstream blocker or ready-path verdict after summary timeout
      is removed.

## Lane Index & Dependencies

- SL-0 - Summary timeout contract tests and fixture freeze; Depends on: SEMCLOSEOUT; Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Repo-wide summary backlog progress and continuation repair; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4; Parallel-safe: no
- SL-2 - Dispatcher timeout recovery and force-full closeout wiring; Depends on: SL-0, SL-1; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-3 - Repo-local dogfood acceptance and downstream-blocker handoff; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4; Parallel-safe: no
- SL-4 - Timeout recovery evidence reducer and operator guide refresh; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: SEMTIMEOUT acceptance; Parallel-safe: no

Lane DAG:

```text
SEMCLOSEOUT
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SL-4 -> SEMTIMEOUT acceptance
```

## Lanes

### SL-0 - Summary Timeout Contract Tests And Fixture Freeze

- **Scope**: Freeze the exact repo-wide summary-timeout contract before runtime
  changes so this phase proves durable repo-wide summary drain and an exact
  downstream handoff instead of only shrinking the same timeout window.
- **Owned files**: `tests/test_summarization.py`, `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMTIMEOUT-1 through IF-0-SEMTIMEOUT-3
- **Interfaces consumed**: existing
  `ComprehensiveChunkWriter.process_scope(...)`,
  `ComprehensiveChunkWriter._fetch_unsummarized_rows(...)`,
  `EnhancedDispatcher.index_directory(...)`,
  `EnhancedDispatcher._count_missing_summaries_for_paths(...)`,
  `GitAwareIndexManager._full_index(...)`, and
  `GitAwareIndexManager.sync_repository_index(...)`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_summarization.py` so repo-scope bounded passes
    prove more than `max_batches=1`: the summary path must expose deterministic
    pass-level progress for a large backlog and must not silently report
    completion when unsummarized chunks remain outside the first fetched slice.
  - test: Tighten `tests/test_dispatcher.py` so the force-full summary loop
    distinguishes four cases explicitly: live progress with more backlog,
    summary plateau, timeout backoff with continued recovery, and the first
    exact downstream blocker after summary timeout is removed.
  - test: Tighten `tests/test_git_index_manager.py` so force-full closeout
    preserves `summary_passes`, `summary_missing_chunks`, and the exact
    semantic-stage blocker while refusing indexed-commit advancement until the
    summary drain actually finished.
  - impl: Keep fixtures deterministic with monkeypatched summary writers,
    synthetic backlog counters, and SQLite-backed stores rather than long live
    rebuilds inside unit coverage.
  - impl: Keep this lane focused on repo-wide timeout recovery contracts only;
    do not update docs or the live dogfood report here.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_summarization.py tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov`

### SL-1 - Repo-Wide Summary Backlog Progress And Continuation Repair

- **Scope**: Repair authoritative repo-wide summary backlog draining so bounded
  one-batch passes can continue making durable progress across the active repo
  instead of timing out before the summary stage can hand off to strict
  semantic indexing.
- **Owned files**: `mcp_server/indexing/summarization.py`
- **Interfaces provided**:
  `SummaryGenerationResult`,
  `ComprehensiveChunkWriter._fetch_unsummarized_rows(...)`, and
  `ComprehensiveChunkWriter.process_scope(...)` as the bounded repo-wide
  summary progress contract
- **Interfaces consumed**: SL-0 summary-timeout tests; existing authoritative
  `chunk_summaries` persistence, large-file profile-batch recovery,
  per-file fallback logic, and summary audit metadata
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 summarization slice first and confirm the current
    repo-scope path still only proves partial progress on the first backlog
    windows while the live force-full rerun remains vulnerable to repo-wide
    timeout.
  - impl: Audit unsummarized-row selection, pass-level result accounting, and
    repo-scope continuation semantics so each bounded summary pass exposes
    enough deterministic progress or remaining-backlog evidence for the
    dispatcher to keep draining the repo without guessing from aggregate
    counts alone.
  - impl: Prevent silent no-op success when unsummarized chunks still remain
    outside the current fetched slice, and preserve exact missing-chunk
    reporting when a pass fails or only partially persists summaries.
  - impl: Preserve target-path filtering, large-file profile-batch recovery,
    and authoritative summary audit metadata; do not widen this lane into
    prompt redesign, new CLI surface, or vector-write behavior.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_summarization.py -q --no-cov`

### SL-2 - Dispatcher Timeout Recovery And Force-Full Closeout Wiring

- **Scope**: Carry the repaired summary-progress contract through the real
  force-full semantic path so repo-local rebuilds can finish authoritative
  summary drain or fail with a narrower semantic-stage blocker than summary
  timeout.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/storage/git_index_manager.py`
- **Interfaces provided**: IF-0-SEMTIMEOUT-1 repo-wide summary timeout
  recovery contract; IF-0-SEMTIMEOUT-3 force-full closeout and status contract
- **Interfaces consumed**: SL-0 dispatcher and git-index-manager tests;
  SL-1 bounded summary progress metadata; existing semantic preflight,
  `SemanticIndexer.index_files_batch(...)`, and indexed-commit closeout rules
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 dispatcher and git-index-manager slice first and
    confirm the current live failure is still the SEMCLOSEOUT summary-timeout
    blocker rather than a reopened lexical or preflight gate.
  - impl: Tighten the dispatcher summary loop so it consumes the SL-1 progress
    surface directly, applies adaptive timeout backoff only while repo-wide
    progress is real, and hands off to the next exact semantic-stage blocker
    once summaries are no longer the limiting stage.
  - impl: Preserve fail-closed semantics for true plateau, true timeout, and
    downstream semantic failures. Removing the generic summary-timeout blocker
    must not let lexical-only or summary-partial success advance into a false
    semantic-ready verdict.
  - impl: Tighten `GitAwareIndexManager` only as needed so force-full closeout
    preserves the richer summary-pass evidence, refuses indexed-commit
    advancement while summary drain is incomplete, and advances to the current
    commit only after the repaired rerun either finishes cleanly or narrows
    the blocker beyond summary timeout.
  - impl: Keep this lane local to summary-stage orchestration and closeout.
    Do not widen into semantic ranking, readiness taxonomy redesign, or a
    broad storage-diagnostics rewrite.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov`
  - verify: `env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index index check-semantic`

### SL-3 - Repo-Local Dogfood Acceptance And Downstream-Blocker Handoff

- **Scope**: Make the repo-local semantic dogfood harness prove that
  SEMTIMEOUT really clears the repo-wide summary-timeout gate instead of only
  changing counters or summary-loop wording.
- **Owned files**: `tests/real_world/test_semantic_search.py`
- **Interfaces provided**: acceptance checks for IF-0-SEMTIMEOUT-1 and
  IF-0-SEMTIMEOUT-3
- **Interfaces consumed**: SL-0 timeout-contract wording; SL-1 summary-progress
  repair; SL-2 repaired force-full rerun, repository status, and semantic
  preflight outcome
- **Parallel-safe**: no
- **Tasks**:
  - test: Update the repo-local dogfood case so it treats
    `Summary generation timed out before strict semantic indexing could start`
    as the exact SEMTIMEOUT blocker to clear, and after the repair expects
    either semantic-path results on the active commit or a narrower exact
    downstream blocker than repo-wide summary timeout.
  - impl: Keep this lane bounded to acceptance semantics and blocker wording;
    do not add a new production command or duplicate the force-full rebuild
    logic.
  - impl: Reuse the existing real-world env gating and repo-local dogfood
    prompt surface rather than creating a SEMTIMEOUT-only harness.
  - verify: `RUN_REAL_WORLD_TESTS=1 SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. OPENAI_API_KEY=dummy-local-key uv run --extra dev python -m pytest tests/real_world/test_semantic_search.py -q --no-cov -k repo_local_dogfood_queries_stay_on_semantic_path -rs`

### SL-4 - Timeout Recovery Evidence Reducer And Operator Guide Refresh

- **Scope**: Re-run the repaired repo-local force-full sequence, reduce the
  outcome into the durable dogfood evidence artifact, and refresh operator
  guidance so summary-timeout recovery is clearly separated from the earlier
  SEMCLOSEOUT partial-progress state.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `docs/guides/semantic-onboarding.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMTIMEOUT-4 evidence contract
- **Interfaces consumed**: SL-0 timeout-contract wording; SL-1 repo-wide
  summary progress evidence; SL-2 rerun command, repository status, and
  semantic preflight results; SL-3 repo-local dogfood acceptance verdict
- **Parallel-safe**: no
- **Tasks**:
  - test: Update `tests/docs/test_semdogfood_evidence_contract.py` so the
    refreshed report must cite `plans/phase-plan-v7-SEMTIMEOUT.md`, require
    summary-timeout recovery evidence plus current summary/vector counts, and
    require the exact new downstream blocker or semantic-ready verdict on the
    current commit.
  - impl: Re-run the repo-local force-full rebuild with the same strict
    watchdog posture used by SEMREADME and SEMCLOSEOUT, record whether the
    summary stage now drains cleanly, and capture current-versus-indexed
    commit evidence together with `chunk_summaries`, `semantic_points`, and
    the next exact blocker if vector linkage still fails downstream.
  - impl: Refresh `docs/guides/semantic-onboarding.md` so operators can tell
    the difference between SEMCLOSEOUT partial summary persistence and
    SEMTIMEOUT summary-timeout recovery, including which status fields and
    evidence lines to inspect if the rerun still blocks downstream.
  - impl: Keep this lane as the final reducer only. It must depend on every
    producer lane and must not speculate about a semantic-ready verdict before
    the repaired rerun actually runs.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
  - verify: `env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index index check-semantic`
  - verify: `RUN_REAL_WORLD_TESTS=1 SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. OPENAI_API_KEY=dummy-local-key uv run --extra dev python -m pytest tests/real_world/test_semantic_search.py -q --no-cov -k repo_local_dogfood_queries_stay_on_semantic_path -rs`

## Verification

Lane-focused verification sequence:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_summarization.py tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov
env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
env OPENAI_API_KEY=dummy-local-key uv run mcp-index index check-semantic
RUN_REAL_WORLD_TESTS=1 SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. OPENAI_API_KEY=dummy-local-key uv run --extra dev python -m pytest tests/real_world/test_semantic_search.py -q --no-cov -k repo_local_dogfood_queries_stay_on_semantic_path -rs
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
```

Whole-phase regression guard:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_summarization.py tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
RUN_REAL_WORLD_TESTS=1 SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. OPENAI_API_KEY=dummy-local-key uv run --extra dev python -m pytest tests/real_world/test_semantic_search.py -q --no-cov -k repo_local_dogfood_queries_stay_on_semantic_path -rs
```

## Acceptance Criteria

- [ ] A clean `uv run mcp-index repository sync --force-full` on the active
      repo no longer exits with
      `Summary generation timed out before strict semantic indexing could start`.
- [ ] Dispatcher summary recovery uses bounded one-batch passes plus timeout
      backoff and preserves enough progress evidence to distinguish continued
      repo-wide summary drain from plateau or true timeout.
- [ ] `uv run mcp-index repository status` either advances indexed commit to
      the current commit after the repo-local semantic rerun or records a
      narrower post-timeout downstream blocker than summary timeout.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is refreshed with timeout
      recovery evidence, current summary/vector counts, and the new exact
      downstream blocker or ready-path verdict.
- [ ] The repo-local semantic dogfood harness no longer treats repo-wide
      summary timeout as the terminal blocker for the active commit.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v7-SEMTIMEOUT.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMTIMEOUT.md
  artifact_state: staged
```
