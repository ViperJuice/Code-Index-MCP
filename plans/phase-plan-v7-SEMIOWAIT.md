---
phase_loop_plan_version: 1
phase: SEMIOWAIT
roadmap: specs/phase-plans-v7.md
roadmap_sha256: e2b93b3f66003ead9e4a93e54374e22b5740354382482fd71302bf27cc5654b6
---
# SEMIOWAIT: Low-Level Force-Full Stall Forensics

## Context

SEMIOWAIT is the phase-14 follow-up for the v7 semantic hardening roadmap.
SEMSTALLFIX tightened dispatcher-stage and git-index-manager closeout contracts,
but the real repo-local `repository sync --force-full` path still does not
finish cleanly enough to refresh indexed freshness or surface a precise blocker
below the semantic-stage accounting layer.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is tracked and clean in this worktree, and
  `.phase-loop/state.json` records the same live roadmap SHA the user
  requested here:
  `e2b93b3f66003ead9e4a93e54374e22b5740354382482fd71302bf27cc5654b6`.
- The checkout is on `main` at `02e72bfebee2`, `main...origin/main` is ahead
  by 18 commits, the worktree is clean before writing this plan, and
  `plans/phase-plan-v7-SEMIOWAIT.md` did not exist before this run.
- `.phase-loop/state.json` already marks `SEMIOWAIT` as the current
  unplanned phase for roadmap `specs/phase-plans-v7.md`, and its closeout
  summary records `SEMSTALLFIX` complete on the current `HEAD`. This artifact
  is the missing execution handoff for the next blocked-downstream phase, not
  a speculative side plan.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is still the live blocker artifact.
  It currently cites `plans/phase-plan-v7-SEMSTALLFIX.md`, records an observed
  commit of `340008a5`, and shows the latest live rerun stayed active for more
  than three minutes while `chunk_summaries` remained `3018`,
  `semantic_points` remained `0`, repository readiness stayed `stale_commit`,
  and none of the bounded semantic-stage outcomes added by SEMSTALLFIX were
  emitted.
- `EnhancedDispatcher.rebuild_semantic_for_paths(...)` already has bounded
  summary and semantic-stage outcomes including `blocked_summary_timeout`,
  `blocked_summary_plateau`, `blocked_preflight`,
  `blocked_semantic_batch_timeout`, and `blocked_semantic_batch`. The residual
  live hang therefore appears earlier than that strict semantic path.
- `GitAwareIndexManager._full_index(...)` and
  `sync_repository_index(..., force_full=True)` already carry semantic-stage
  metadata forward and refuse to advance `last_indexed_commit` on
  non-success semantic-stage outcomes. That closeout path is now fail-closed
  in tests, but it still cannot classify the live rerun because the run never
  reaches the bounded semantic-stage result.
- `EnhancedDispatcher.index_directory(...)` still walks the repo and indexes
  files serially before `rebuild_semantic_for_paths(...)` runs. That lexical
  path currently counts indexed/failed files, but it does not yet freeze a
  precise low-level force-full contract for "no forward progress below
  semantic-stage accounting" or expose the last in-flight file/storage step.
- `SQLiteStore.health_check()` currently reports table existence, FTS5 support,
  WAL mode, and schema version. It does not yet surface bounded diagnostics for
  low-level force-full blockers such as SQLite busy/lock pressure, checkpoint
  failures, or other storage/runtime evidence that would explain a live stall
  with unchanged durable counts.
- The acceptance and evidence surfaces already exist in
  `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`,
  `tests/test_sqlite_store.py`, `tests/docs/test_semdogfood_evidence_contract.py`,
  `tests/real_world/test_semantic_search.py`,
  `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, and
  `docs/guides/semantic-onboarding.md`. SEMIOWAIT should tighten those
  surfaces around low-level force-full progress, storage diagnostics, exact
  blocker surfacing, and current-commit evidence rather than reopening ranking,
  profile, or multi-repo rollout work.

Practical planning boundary:

- SEMIOWAIT may instrument the live lexical/storage/runtime path below
  semantic-stage accounting, add bounded storage diagnostics, repair the exact
  force-full blocker if it is local to that path, rerun the clean rebuild, and
  refresh the operator evidence with either a semantic-ready verdict or a new
  exact low-level blocker.
- SEMIOWAIT must stay narrowly on the repo-local force-full execution path,
  low-level storage/runtime forensics, and deterministic blocker surfacing. It
  must not widen into semantic ranking redesign, earlier summary/runtime phases,
  or multi-repo rollout policy.

## Interface Freeze Gates

- [ ] IF-0-SEMIOWAIT-1 - Low-level lexical progress contract:
      `EnhancedDispatcher.index_directory(...)` records enough exact force-full
      progress to diagnose stalls before `semantic_stage`, including
      `lexical_stage`, `lexical_files_attempted`, `lexical_files_completed`,
      and `last_progress_path`.
- [ ] IF-0-SEMIOWAIT-2 - Storage diagnostics contract:
      the low-level force-full path can surface bounded SQLite/storage evidence
      when it is the blocker, including journal/WAL posture, busy-timeout
      posture, and exact lock/checkpoint/runtime failure metadata without
      requiring destructive resets.
- [ ] IF-0-SEMIOWAIT-3 - Force-full bounded exit contract:
      `GitAwareIndexManager.sync_repository_index(..., force_full=True)` either
      finishes lexical, summary, semantic, and indexed-commit closeout on the
      active commit, or returns a fail-closed low-level blocker that is
      narrower than SEMSTALLFIX's semantic-stage vocabulary.
- [ ] IF-0-SEMIOWAIT-4 - Indexed-freshness and query contract:
      a successful SEMIOWAIT rebuild refreshes the indexed commit to the
      current commit and restores repo-local indexed semantic queries, while a
      blocked run keeps the indexed commit unchanged and reports the exact
      low-level blocker instead of an unexplained long-running sync.
- [ ] IF-0-SEMIOWAIT-5 - Evidence contract:
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` and
      `docs/guides/semantic-onboarding.md` record the SEMSTALLFIX repair, the
      residual low-level stall evidence, the exact SEMIOWAIT blocker or fix,
      and the final ready or still-blocked verdict on the current commit.

## Lane Index & Dependencies

- SL-0 - Low-level stall contract tests and fixture freeze; Depends on: SEMSTALLFIX; Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Dispatcher lexical progress and bounded pre-semantic instrumentation; Depends on: SL-0; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-2 - SQLite storage diagnostics and low-level blocker probes; Depends on: SL-0; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-3 - Full-index closeout and indexed-freshness refusal mapping; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4; Parallel-safe: no
- SL-4 - Dogfood evidence reducer and operator guide refresh; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: SEMIOWAIT acceptance; Parallel-safe: no

Lane DAG:

```text
SEMSTALLFIX
  -> SL-0
  -> SL-1
  -> SL-2
  -> SL-3
  -> SL-4
  -> SEMIOWAIT acceptance
```

## Lanes

### SL-0 - Low-Level Stall Contract Tests And Fixture Freeze

- **Scope**: Freeze the exact below-semantic stall contract before runtime
  changes so this phase proves a bounded live force-full repair instead of only
  collecting another long blocked rerun.
- **Owned files**: `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`, `tests/test_sqlite_store.py`
- **Interfaces provided**: executable assertions for IF-0-SEMIOWAIT-1 through
  IF-0-SEMIOWAIT-4
- **Interfaces consumed**: existing
  `EnhancedDispatcher.index_directory(...)`,
  `EnhancedDispatcher.rebuild_semantic_for_paths(...)`,
  `GitAwareIndexManager.sync_repository_index(...)`,
  `GitAwareIndexManager._full_index(...)`, `SQLiteStore.health_check()`, and
  the current SEMSTALLFIX semantic-stage outcome vocabulary
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with deterministic cases where the
    force-full path never reaches `rebuild_semantic_for_paths(...)`, and
    require a bounded `lexical_stage` plus `last_progress_path` result instead
    of an opaque long-running sync.
  - test: Extend `tests/test_git_index_manager.py` so force-full sync
    distinguishes a successful semantic-ready rebuild from a new
    pre-semantic low-level blocker, and proves the indexed commit is not
    advanced when the dispatcher reports that bounded low-level failure.
  - test: Extend `tests/test_sqlite_store.py` so storage diagnostics freeze the
    expected metadata surface for WAL/journal mode, busy-timeout posture, and
    exact checkpoint or lock-shaped failures used by the force-full blocker
    path.
  - impl: Keep fixtures deterministic with monkeypatched dispatcher/store
    helpers and synthetic `sqlite3.OperationalError` cases rather than real
    multi-minute waits or destructive DB mutation.
  - impl: Keep this lane focused on the low-level stall contract and exact
    blocker vocabulary; do not update docs or operator guidance here.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_sqlite_store.py -q --no-cov`

### SL-1 - Dispatcher Lexical Progress And Bounded Pre-Semantic Instrumentation

- **Scope**: Repair the repo-wide indexing loop so a force-full rebuild that
  stalls before semantic-stage accounting still emits exact lexical progress
  and exits through a bounded blocker path instead of staying active with no
  diagnosable state change.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`
- **Interfaces provided**: IF-0-SEMIOWAIT-1 low-level lexical progress
  contract; the dispatcher-side portion of IF-0-SEMIOWAIT-3
- **Interfaces consumed**: SL-0 contract tests; existing `index_directory(...)`,
  `index_file(...)`, file-walk filtering, per-file mutation results, and the
  existing SEMSTALLFIX semantic-stage accounting surface
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 dispatcher slice first and confirm it reproduces the
    current "below semantic-stage hang" contract before mutating runtime code.
  - impl: Add exact pre-semantic progress bookkeeping inside
    `index_directory(...)` so force-full callers can tell which lexical stage
    was active, how many files were attempted versus completed, and which path
    last produced forward progress before any stall or timeout.
  - impl: Bound any pre-semantic no-progress path with an exact blocker result
    that is separate from the SEMSTALLFIX semantic-stage vocabulary and can be
    carried into full-index closeout.
  - impl: Preserve existing summary-first and semantic fail-closed behavior.
    This lane only instruments or repairs the lexical/runtime path below
    `rebuild_semantic_for_paths(...)`; it must not weaken semantic readiness
    gates or create a second indexing workflow.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py -q --no-cov -k "index_directory"`

### SL-2 - SQLite Storage Diagnostics And Low-Level Blocker Probes

- **Scope**: Surface bounded SQLite/storage evidence for the live force-full
  path so lock, checkpoint, WAL, or other local storage/runtime failures can
  be diagnosed and fail closed without destructive intervention.
- **Owned files**: `mcp_server/storage/sqlite_store.py`
- **Interfaces provided**: IF-0-SEMIOWAIT-2 storage diagnostics contract
- **Interfaces consumed**: SL-0 storage contract tests; existing
  `_get_connection()`, `health_check()`, database initialization pragmas, and
  the active `.mcp-index/current.db` layout used by repo-local force-full runs
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 SQLite slice first and confirm the current health
    surface lacks the low-level blocker metadata SEMIOWAIT needs.
  - impl: Extend the store-level diagnostics surface with bounded metadata
    useful to force-full forensics, such as effective journal mode, busy-timeout
    posture, WAL presence or checkpoint probe outcome, and exact
    `sqlite3.OperationalError` classification when the storage layer is the
    blocker.
  - impl: Keep diagnostics read-only or metadata-only with respect to indexed
    content. This lane may probe storage posture, but it must not delete or
    rebuild the active store outside the normal force-full path.
  - impl: Keep the surface generic enough for dispatcher/git-index-manager
    consumers, but local to `sqlite_store.py`; do not widen into artifact or
    multi-repo health policy.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_sqlite_store.py -q --no-cov`
  - verify: `sqlite3 .mcp-index/current.db 'PRAGMA journal_mode; PRAGMA wal_checkpoint(PASSIVE); SELECT COUNT(*) AS chunk_summaries FROM chunk_summaries; SELECT COUNT(*) AS semantic_points FROM semantic_points;'`

### SL-3 - Full-Index Closeout And Indexed-Freshness Refusal Mapping

- **Scope**: Carry the dispatcher and storage diagnostics into the real
  `repository sync --force-full` closeout path so successful rebuilds refresh
  the indexed commit, while low-level blocked runs return exact failure context
  instead of an unexplained long-running sync followed by stale readiness.
- **Owned files**: `mcp_server/storage/git_index_manager.py`
- **Interfaces provided**: IF-0-SEMIOWAIT-3 force-full bounded exit contract;
  IF-0-SEMIOWAIT-4 indexed-freshness and query contract at the
  repository-sync layer
- **Interfaces consumed**: SL-0 contract tests; SL-1 dispatcher lexical-stage
  output; SL-2 storage diagnostics; existing `_full_index(...)`,
  `sync_repository_index(...)`, durable-row checks, and
  `registry.update_indexed_commit(...)`
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 git-index-manager slice first and confirm the current
    force-full closeout cannot explain the live below-semantic hang even
    though semantic-stage blockers are now bounded.
  - impl: Propagate the new low-level lexical/storage blocker shape through
    `_full_index(...)` and `sync_repository_index(...)` so force-full sync
    returns an exact fail-closed outcome when the live run stops below the
    semantic-stage path.
  - impl: Refresh `last_indexed_commit` only when the repaired force-full run
    truly completes its accepted success contract, and keep the indexed commit
    unchanged when the new low-level blocker fires.
  - impl: Preserve the existing SEMSTALLFIX semantic-stage error mapping and
    durable-row protection. This lane must explain the lower-level blocker, not
    paper over it by advancing freshness on partial work.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py -q --no-cov`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`

### SL-4 - Dogfood Evidence Reducer And Operator Guide Refresh

- **Scope**: Refresh the durable dogfood report and operator guide so the repo
  records whether SEMIOWAIT restored a complete force-full rebuild on the
  current commit or exactly which low-level blocker still remains.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `docs/guides/semantic-onboarding.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMIOWAIT-5 evidence contract; operator-facing
  expression of IF-0-SEMIOWAIT-4
- **Interfaces consumed**: SL-0 blocker vocabulary; SL-1 lexical progress
  evidence; SL-2 storage diagnostics; SL-3 force-full closeout outcome,
  indexed-commit freshness result, current-versus-indexed commit evidence,
  durable summary/vector counts, and repo-local semantic query outcome
- **Parallel-safe**: no
- **Tasks**:
  - test: Update `tests/docs/test_semdogfood_evidence_contract.py` so the
    refreshed report must cite `plans/phase-plan-v7-SEMIOWAIT.md`, record the
    residual low-level stall evidence from SEMSTALLFIX, capture the current
    commit, indexed commit, exact low-level blocker or fix, and state the final
    ready or still-blocked verdict.
  - test: Require `docs/guides/semantic-onboarding.md` to explain how to
    distinguish semantic-stage blockers from below-semantic lexical/storage
    blockers and where to read the new low-level diagnostics during force-full
    recovery.
  - impl: Refresh `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` after the SEMIOWAIT
    rerun with timings, lexical-progress evidence, storage diagnostics,
    indexed-commit freshness outcome, durable counts, repo-local semantic query
    outcome, and the final verdict on the current commit.
  - impl: Update `docs/guides/semantic-onboarding.md` so the troubleshooting
    section points operators at the repaired force-full verification sequence
    and the exact low-level blocker language if one still remains.
  - impl: If execution still cannot reach semantic readiness `ready`, record
    the exact residual blocker and command evidence instead of widening into
    ranking, earlier summary phases, or rollout policy.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
  - verify: `RUN_REAL_WORLD_TESTS=1 SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. OPENAI_API_KEY=dummy-local-key uv run --extra dev python -m pytest tests/real_world/test_semantic_search.py -q --no-cov -k repo_local_dogfood_queries_stay_on_semantic_path -rs`
  - verify: `rg -n "SEMIOWAIT|lexical_stage|last_progress_path|stale_commit|indexed commit|chunk_summaries|semantic_points|sqlite|checkpoint|lock|semantic readiness" docs/status/SEMANTIC_DOGFOOD_REBUILD.md docs/guides/semantic-onboarding.md tests/docs/test_semdogfood_evidence_contract.py`

## Verification

Planning-only run: do not execute these during plan creation. Run them during
`codex-execute-phase` or manual SEMIOWAIT execution.

Focused verification sequence:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_sqlite_store.py -q --no-cov
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
env OPENAI_API_KEY=dummy-local-key uv run mcp-index index check-semantic
RUN_REAL_WORLD_TESTS=1 SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. OPENAI_API_KEY=dummy-local-key uv run --extra dev python -m pytest tests/real_world/test_semantic_search.py -q --no-cov -k repo_local_dogfood_queries_stay_on_semantic_path -rs
sqlite3 .mcp-index/current.db 'PRAGMA journal_mode; PRAGMA wal_checkpoint(PASSIVE); SELECT COUNT(*) AS chunk_summaries FROM chunk_summaries; SELECT COUNT(*) AS semantic_points FROM semantic_points;'
git status --short -- specs/phase-plans-v7.md plans/phase-plan-v7-SEMIOWAIT.md
```

Whole-phase regression guard:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_sqlite_store.py -q --no-cov
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
RUN_REAL_WORLD_TESTS=1 SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. OPENAI_API_KEY=dummy-local-key uv run --extra dev python -m pytest tests/real_world/test_semantic_search.py -q --no-cov -k repo_local_dogfood_queries_stay_on_semantic_path -rs
```

## Acceptance Criteria

- [ ] A clean `uv run mcp-index repository sync --force-full` either completes
      through lexical, summary, semantic, and indexed-commit closeout, or
      exits fail-closed with an exact low-level blocker narrower than
      SEMSTALLFIX's semantic-stage vocabulary.
- [ ] The live repo-local rebuild no longer remains active for minutes with
      unchanged `chunk_summaries` and `semantic_points` counts without also
      surfacing bounded lexical/storage/runtime progress or an exact blocker.
- [ ] If the residual blocker is in SQLite, WAL/checkpoint, file-read, or
      another pre-semantic storage/runtime layer, that layer now exposes
      deterministic diagnostics and a bounded refusal path in tests and live
      operator evidence.
- [ ] Successful SEMIOWAIT execution refreshes the indexed commit to the
      current commit and restores repo-local indexed semantic queries; blocked
      execution keeps the indexed commit unchanged and records the exact
      low-level blocker instead of an unexplained `stale_commit`.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the SEMSTALLFIX repair,
      the SEMIOWAIT low-level stall evidence or fix, current-versus-indexed
      commit evidence, durable counts, and the final ready or still-blocked
      verdict on the current commit.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v7-SEMIOWAIT.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMIOWAIT.md
  artifact_state: staged
```
