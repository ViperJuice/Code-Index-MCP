---
phase_loop_plan_version: 1
phase: SEMSTALLFIX
roadmap: specs/phase-plans-v7.md
roadmap_sha256: 6020baac9b1c9b872386564d0ac3f420fced6ad0284641130b57f08265634b54
---
# SEMSTALLFIX: Force-Full Semantic Stall Recovery

## Context

SEMSTALLFIX is the phase-13 follow-up for the v7 semantic hardening roadmap.
SEMTHROUGHPUT repaired the oversized markdown/plaintext summary path and
raised durable summary coverage, but the real `repository sync --force-full`
path still does not finish cleanly enough to refresh indexed commit freshness
or prove the semantic-stage handoff.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is tracked and clean in this worktree, and its
  live SHA matches the required
  `6020baac9b1c9b872386564d0ac3f420fced6ad0284641130b57f08265634b54`.
- The checkout is on `main` at `b3eb7ffd93c2`, `main...origin/main` is ahead
  by 16 commits, the worktree is clean before writing this plan, and
  `plans/phase-plan-v7-SEMSTALLFIX.md` did not exist before this run.
- `.phase-loop/state.json` already marks `SEMSTALLFIX` as the current
  unplanned phase for roadmap `specs/phase-plans-v7.md`, so this artifact is
  the missing execution handoff for the next blocked-downstream phase, not a
  speculative side plan.
- The upstream v7 planning and execution chain already exists through
  `plans/phase-plan-v7-SEMTHROUGHPUT.md`, and the repo-local phase-loop
  ledger records a `manual_repair` closeout for SEMTHROUGHPUT on
  `2026-04-28T12:39:31Z` after commit `b3eb7ffd93c2c3dc6092878152760be9a8f8a692`
  preserved the completed throughput slice and carried the remaining blocker
  forward to `SEMSTALLFIX`.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the live blocker artifact for
  this phase. Its evidence snapshot at `2026-04-28T12:30:53Z` on observed
  commit `340008a5` records the post-SEMTHROUGHPUT state precisely:
  `chunk_summaries=3018`, `semantic_points=0`, lexical readiness
  `stale_commit`, semantic readiness `summaries_missing`, active-profile
  preflight `ready`, active collection `code_index__oss_high__v1`, and a
  repo-local semantic query now failing closed with `code: "index_unavailable"`
  because indexed freshness never returned to `ready`.
- The same evidence artifact narrows the residual problem beyond summary
  throughput: a force-full rebuild stayed active for about 22 minutes, summary
  counts plateaued after the throughput repair, no semantic vectors became
  durable, and the run had to be interrupted before any indexed-commit
  refresh.
- `EnhancedDispatcher.index_directory(...)` still queues every successfully
  indexed path and then calls
  `rebuild_semantic_for_paths(ctx, semantically_indexed_paths)` once for the
  full repo-sized scope. Inside that strict semantic path,
  `rebuild_semantic_for_paths(...)` only breaks the summary loop when a pass
  writes `0` summaries, then immediately decides between
  `blocked_missing_summaries`, preflight bootstrap, or semantic batch writes.
  That means SEMSTALLFIX should instrument and bound the post-summary handoff
  rather than invent another indexing workflow.
- `GitAwareIndexManager.sync_repository_index(...)` advances
  `last_indexed_commit` only after `_full_index(...)` returns and durable rows
  exist, while `_full_index(...)` currently preserves additive semantic-stage
  stats from `dispatcher.index_directory(...)` but does not yet own an exact
  contract for "force-full stalled after summary progress" versus "semantic
  stage failed cleanly and exited with a precise blocker."
- The acceptance and evidence surfaces already exist in
  `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`,
  `tests/real_world/test_semantic_search.py`,
  `tests/docs/test_semdogfood_evidence_contract.py`,
  `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, and
  `docs/guides/semantic-onboarding.md`. SEMSTALLFIX should tighten those
  surfaces around force-full completion, indexed-commit freshness, and exact
  post-summary blockers rather than reopening ranking or earlier profile
  configuration phases.

Practical planning boundary:

- SEMSTALLFIX may instrument or bound the repo-wide force-full semantic-stage
  loop, repair the exact dispatcher or git-index-manager handoff that leaves
  the run hanging after summary progress plateaus, rerun the clean rebuild,
  and refresh the dogfood/operator evidence with either a semantic-ready
  verdict or a new exact post-summary blocker.
- SEMSTALLFIX must stay narrowly on force-full completion, indexed-commit
  freshness, and post-summary semantic-stage handoff. It must not widen into
  semantic ranking redesign, multi-repo rollout expansion, or unrelated
  enrichment/profile changes already handled by earlier v7 phases.

## Interface Freeze Gates

- [ ] IF-0-SEMSTALLFIX-1 - Force-full completion contract: a clean
      `uv run mcp-index repository sync --force-full` either finishes the
      lexical -> summaries -> semantic pipeline on the active commit without
      hanging after summary counts plateau, or exits fail-closed with an exact
      post-summary blocker that names the stage that stopped progress.
- [ ] IF-0-SEMSTALLFIX-2 - Indexed-commit freshness contract:
      `GitAwareIndexManager.sync_repository_index(..., force_full=True)`
      refreshes the repository's indexed commit to the current commit when the
      repaired force-full run completes successfully, and it does not leave
      readiness at `stale_commit` after a successful rebuild.
- [ ] IF-0-SEMSTALLFIX-3 - Post-summary blocker contract: dispatcher and
      full-index result surfaces distinguish summary progress, summary
      plateau/no-progress, semantic preflight blockers, semantic batch-write
      blockers, and commit-refresh blockers precisely enough that the residual
      blocker is narrower than SEMTHROUGHPUT.
- [ ] IF-0-SEMSTALLFIX-4 - Repo-local dogfood contract: after the repaired
      rebuild, repo-local semantic prompts return semantic-path results with
      `semantic_source: "semantic"` and
      `semantic_collection_name: "code_index__oss_high__v1"`, or they surface
      the exact new blocker contract without ambiguous `index_unavailable`
      versus `semantic_not_ready` confusion.
- [ ] IF-0-SEMSTALLFIX-5 - Evidence contract:
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the force-full stall
      evidence, remediation, indexed-commit freshness outcome, semantic
      counts, and final ready or still-blocked verdict, while
      `docs/guides/semantic-onboarding.md` explains how to recognize the
      repaired force-full completion path.

## Lane Index & Dependencies

- SL-0 - Force-full stall contract tests and live blocker fixtures; Depends on: SEMTHROUGHPUT; Blocks: SL-1, SL-2, SL-3; Parallel-safe: no
- SL-1 - Dispatcher semantic-stage completion and bounded handoff repair; Depends on: SL-0; Blocks: SL-2, SL-3; Parallel-safe: no
- SL-2 - Git-index-manager freshness and force-full closeout repair; Depends on: SL-0, SL-1; Blocks: SL-3; Parallel-safe: no
- SL-3 - Dogfood evidence reducer and operator guide refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SEMSTALLFIX acceptance; Parallel-safe: no

Lane DAG:

```text
SEMTHROUGHPUT
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SEMSTALLFIX acceptance
```

## Lanes

### SL-0 - Force-Full Stall Contract Tests And Live Blocker Fixtures

- **Scope**: Freeze the exact post-SEMTHROUGHPUT stall contract before runtime
  changes so this phase proves a force-full completion repair instead of only
  reporting different counts from another long dogfood run.
- **Owned files**: `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`, `tests/real_world/test_semantic_search.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMSTALLFIX-1 through IF-0-SEMSTALLFIX-4
- **Interfaces consumed**: existing `EnhancedDispatcher.index_directory(...)`,
  `EnhancedDispatcher.rebuild_semantic_for_paths(...)`,
  `GitAwareIndexManager.sync_repository_index(...)`,
  `GitAwareIndexManager._full_index(...)`, and the repo-local dogfood query
  harness in `tests/real_world/test_semantic_search.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with deterministic cases that
    freeze the current "summary progress improves, then semantic handoff does
    not complete" behavior and require a bounded exit with an exact stage
    outcome instead of an indefinite repo-wide semantic pass.
  - test: Extend `tests/test_git_index_manager.py` so force-full sync
    distinguishes a completed `semantic_stage="indexed"` success from a
    post-summary blocked or stalled run, and so indexed-commit advancement is
    asserted against those exact outcomes.
  - test: Tighten `tests/real_world/test_semantic_search.py` so the repo-local
    dogfood case treats `index_unavailable` due to `stale_commit` as the
    SEMSTALLFIX blocker to clear, while still allowing execution to surface a
    narrower exact post-summary blocker if force-full rebuild completion is
    still not restored.
  - impl: Keep fixtures deterministic with monkeypatched summary counts,
    semantic batch results, and git-index-manager return objects rather than
    introducing new long-running unit-time waits.
  - impl: Keep this lane focused on the stall contract and exact blocker
    vocabulary; do not update docs or operator guidance here.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov`
  - verify: `RUN_REAL_WORLD_TESTS=1 SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. OPENAI_API_KEY=dummy-local-key uv run --extra dev python -m pytest tests/real_world/test_semantic_search.py -q --no-cov -k repo_local_dogfood_queries_stay_on_semantic_path -rs`

### SL-1 - Dispatcher Semantic-Stage Completion And Bounded Handoff Repair

- **Scope**: Repair the strict semantic path in the dispatcher so a repo-wide
  force-full rebuild exits cleanly after summary progress either hands off to
  semantic vector writes or returns a precise post-summary blocker instead of
  hanging mid-run.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`
- **Interfaces provided**: IF-0-SEMSTALLFIX-1 force-full completion contract;
  IF-0-SEMSTALLFIX-3 post-summary blocker contract at the dispatcher layer
- **Interfaces consumed**: SL-0 contract tests; existing
  `index_directory(...)`, `rebuild_semantic_for_paths(...)`,
  `_count_missing_summaries_for_paths(...)`, semantic preflight/bootstrap
  helpers, and semantic batch-write statistics from `SemanticIndexer`
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 dispatcher slice first and confirm it reproduces the
    current post-summary handoff gap before mutating runtime code.
  - impl: Bound the repo-wide summary/semantic handoff explicitly inside
    `rebuild_semantic_for_paths(...)` so repeated summary passes, zero-progress
    passes, semantic-preflight blockers, semantic batch blockers, and final
    semantic-stage outcomes are surfaced as exact stage results instead of
    leaving the force-full run effectively hung without a narrow diagnosis.
  - impl: Adjust `index_directory(...)` additive semantic stats only as needed
    so force-full callers can tell whether the repo-wide semantic pass ended in
    `indexed`, `blocked_missing_summaries`, `blocked_preflight`, a new bounded
    post-summary stall state, or another exact failure class.
  - impl: Preserve strict summary-before-vector ordering and fail-closed
    behavior. This lane should make the existing force-full path finish, not
    weaken readiness gates or introduce a second rebuild workflow.
  - impl: Keep semantic query routing unchanged. This lane only repairs the
    force-full semantic-stage handoff and its accounting.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py -q --no-cov -k "index_directory_runs_lexical_then_summaries_then_semantic or index_directory_blocks_semantic_stage_when_summaries_missing or index_directory_retries_summary_generation_until_scope_is_drained or index_directory_bootstraps_missing_collection_before_semantic_writes"`

### SL-2 - Git-Index-Manager Freshness And Force-Full Closeout Repair

- **Scope**: Repair the full-index closeout path so a completed force-full
  rebuild refreshes indexed commit freshness, while blocked post-summary runs
  return an exact closeout blocker instead of falling back to stale readiness
  without attribution.
- **Owned files**: `mcp_server/storage/git_index_manager.py`
- **Interfaces provided**: IF-0-SEMSTALLFIX-2 indexed-commit freshness
  contract; IF-0-SEMSTALLFIX-3 post-summary blocker contract at the
  repository-sync layer
- **Interfaces consumed**: SL-0 contract tests; SL-1 dispatcher semantic-stage
  outcomes; existing `sync_repository_index(...)`, `_full_index(...)`,
  `_index_exists(...)`, durable-row checks, and
  `registry.update_indexed_commit(...)`
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 git-index-manager slice first and confirm the current
    force-full closeout still leaves the repo at `stale_commit` after the
    SEMTHROUGHPUT summary improvement evidence.
  - impl: Tighten `_full_index(...)` and any surrounding force-full closeout
    logic so additive semantic-stage stats propagate a precise post-summary
    outcome into `sync_repository_index(...)`, instead of collapsing the run
    into a stale indexed-commit state without a narrow blocker explanation.
  - impl: Refresh `last_indexed_commit` only when the repaired force-full run
    actually finishes its accepted success contract, and return an exact
    blocked/failed action shape when the semantic-stage handoff still stops
    short after summary progress.
  - impl: Preserve existing durable-row protection from
    `test_full_index_without_durable_rows_does_not_advance_commit`; this lane
    must not "fix" `stale_commit` by advancing the indexed commit on partial
    or non-durable runs.
  - impl: Keep this lane local to repository-sync closeout and readiness
    freshness. Do not reopen repository registration, branch-drift policy, or
    semantic ranking behavior.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py -q --no-cov`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - verify: `sqlite3 .mcp-index/current.db 'select count(*) as chunk_summaries from chunk_summaries; select count(*) as semantic_points from semantic_points;'`

### SL-3 - Dogfood Evidence Reducer And Operator Guide Refresh

- **Scope**: Refresh the durable dogfood report and operator guide so the repo
  records whether SEMSTALLFIX restored force-full completion and indexed
  freshness or exactly which narrower post-summary blocker remains.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `docs/guides/semantic-onboarding.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMSTALLFIX-4 repo-local dogfood contract;
  IF-0-SEMSTALLFIX-5 evidence contract
- **Interfaces consumed**: SL-0 blocker vocabulary; SL-1 dispatcher stage
  accounting; SL-2 force-full closeout outcome, indexed-commit freshness
  status, rebuild timings, summary/vector counts, and repo-local semantic
  query results
- **Parallel-safe**: no
- **Tasks**:
  - test: Update `tests/docs/test_semdogfood_evidence_contract.py` so the
    refreshed report must cite `plans/phase-plan-v7-SEMSTALLFIX.md`, capture
    force-full stall remediation, record post-run `chunk_summaries`,
    `semantic_points`, current commit versus indexed commit, and state the
    final semantic-ready or exact still-blocked verdict.
  - test: Require `docs/guides/semantic-onboarding.md` to explain how to
    distinguish `stale_commit` due to unfinished force-full closeout from
    earlier `summaries_missing`, preflight, or collection bootstrap blockers.
  - impl: Refresh `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` after the
    SEMSTALLFIX rebuild with timings, indexed-commit freshness evidence,
    semantic-stage outcome, repo-local semantic query outcome, and the final
    ready or still-blocked verdict.
  - impl: Update `docs/guides/semantic-onboarding.md` so the troubleshooting
    section points operators at the repaired force-full verification sequence
    and the exact downstream blocker language if one still remains.
  - impl: If execution still cannot reach semantic readiness `ready`, record
    the exact residual blocker and command evidence instead of widening into
    ranking or rollout policy work.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
  - verify: `rg -n "SEMSTALLFIX|stale_commit|indexed commit|chunk_summaries|semantic_points|semantic readiness" docs/status/SEMANTIC_DOGFOOD_REBUILD.md docs/guides/semantic-onboarding.md tests/docs/test_semdogfood_evidence_contract.py`

## Verification

Planning-only run: do not execute these during plan creation. Run them during
`codex-execute-phase` or manual SEMSTALLFIX execution.

Focused verification sequence:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov
RUN_REAL_WORLD_TESTS=1 SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. OPENAI_API_KEY=dummy-local-key uv run --extra dev python -m pytest tests/real_world/test_semantic_search.py -q --no-cov -k repo_local_dogfood_queries_stay_on_semantic_path -rs
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
env OPENAI_API_KEY=dummy-local-key uv run mcp-index index check-semantic
sqlite3 .mcp-index/current.db 'select count(*) as chunk_summaries from chunk_summaries; select count(*) as semantic_points from semantic_points;'
git status --short -- specs/phase-plans-v7.md plans/phase-plan-v7-SEMSTALLFIX.md
```

Whole-phase regression guard:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov
RUN_REAL_WORLD_TESTS=1 SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. OPENAI_API_KEY=dummy-local-key uv run --extra dev python -m pytest tests/real_world/test_semantic_search.py -q --no-cov -k repo_local_dogfood_queries_stay_on_semantic_path -rs
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
```

## Acceptance Criteria

- [ ] A clean `uv run mcp-index repository sync --force-full` no longer
      plateaus indefinitely after summary counts stop moving on the large-file
      backlog.
- [ ] The repaired force-full rebuild either finishes with indexed commit
      freshness on the current commit or exits fail-closed with an exact
      post-summary blocker narrower than SEMTHROUGHPUT.
- [ ] `uv run mcp-index repository status` no longer reports
      `stale_commit` after a successful SEMSTALLFIX rebuild.
- [ ] Repo-local semantic dogfood queries return semantic-path results, or
      they surface the exact new blocker contract without ambiguous fallback
      behavior.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the force-full stall
      remediation, indexed-commit freshness outcome, semantic counts, and
      final ready or still-blocked verdict.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v7-SEMSTALLFIX.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMSTALLFIX.md
  artifact_state: staged
```
