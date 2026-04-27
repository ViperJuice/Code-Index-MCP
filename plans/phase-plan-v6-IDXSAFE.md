---
phase_loop_plan_version: 1
phase: IDXSAFE
roadmap: specs/phase-plans-v6.md
roadmap_sha256: 032aefa89b2aa288d9d28ea7473738e926a66aadef4852b9cf3b3832d7e8fd77
---
# IDXSAFE: Index Commit Advancement Safety

## Context

IDXSAFE is the second phase in the v6 multi-repo hardening roadmap. It is the
mutation-truth contract for local indexing, and WATCH depends on it before
hardening live multi-repo file events. The selected roadmap
`specs/phase-plans-v6.md` is tracked and clean in this worktree, and its live
SHA matches the required
`032aefa89b2aa288d9d28ea7473738e926a66aadef4852b9cf3b3832d7e8fd77`.

Current repo state gathered during planning:

- The checkout is on `main` at `ce4890d`, clean in content but ahead of
  `origin/main` by one commit.
- `plans/phase-plan-v6-IDXSAFE.md` did not exist before this planning run.
- `plans/phase-plan-v6-ARTPUB.md` already exists for the sibling v6 phase, and
  the roadmap explicitly allows ARTPUB and IDXSAFE to be planned independently.
- `EnhancedDispatcher.index_file_guarded()` already returns explicit
  `IndexResult` statuses for watcher-driven add/modify paths, but
  `EnhancedDispatcher.index_file()`, `remove_file()`, and `move_file()` still
  use `None` plus logs/raised exceptions as their success surface.
- `EnhancedDispatcher.index_file()` swallows plugin and read failures and
  returns `None`, so `_incremental_index_update()` currently counts add/modify
  work as successful whenever no exception escapes the call site.
- `EnhancedDispatcher.remove_file()` catches and logs internal failures without
  returning whether the requested repository row was actually removed.
- `EnhancedDispatcher.move_file()` raises on two-phase semantic rollback
  failures, but the happy-path return still does not tell callers whether the
  intended SQLite row existed and moved.
- `SQLiteStore.remove_file()` logs `File not found for removal` and returns
  `None`, and `SQLiteStore.move_file()` records a move row without checking
  whether the primary `files` row update affected the expected repository path.
- `GitAwareIndexManager.UpdateResult.clean` currently ignores `skipped`, and
  `_incremental_index_update()` increments `deleted`, `moved`, or `indexed`
  counters from dispatcher calls that can silently no-op or swallow failures.
- Existing wrong-branch, unsupported-worktree, and missing-index fail-closed
  behavior is already covered elsewhere and must remain unchanged by this phase.

## Interface Freeze Gates

- [ ] IF-0-IDXSAFE-1 - Dispatcher mutation result contract:
      `EnhancedDispatcher.index_file(...)`, `index_file_guarded(...)`,
      `remove_file(...)`, and `move_file(...)` expose explicit mutation
      outcomes for required add/modify/delete/move work, and callers no longer
      infer success from the absence of an exception.
- [ ] IF-0-IDXSAFE-2 - Store affected-row contract:
      `SQLiteStore.remove_file(...)` and `move_file(...)` report whether the
      expected `files` row for the requested `repository_id` was actually
      removed or moved, distinguishing success from not-found/no-op state.
- [ ] IF-0-IDXSAFE-3 - Incremental clean-state contract:
      `GitAwareIndexManager._incremental_index_update()` treats failed,
      skipped-required, or unknown required mutations as non-clean and counts
      delete/move/index success only from explicit positive mutation outcomes
      or an explicit safe recovery path.
- [ ] IF-0-IDXSAFE-4 - Commit advancement contract:
      `sync_repository_index()` must not call `registry.update_indexed_commit()`
      or update `last_indexed_commit` after any partial incremental failure,
      skipped-required mutation, or unknown mutation outcome; existing
      wrong-branch and missing-index fail-closed behavior remains unchanged.

## Lane Index & Dependencies

- SL-0 - IDXSAFE contract freeze tests; Depends on: (none); Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Dispatcher mutation outcome implementation; Depends on: SL-0; Blocks: SL-3, SL-4; Parallel-safe: yes
- SL-2 - SQLite affected-row accounting; Depends on: SL-0; Blocks: SL-3, SL-4; Parallel-safe: yes
- SL-3 - Git-aware incremental safety and commit gate; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4; Parallel-safe: no
- SL-4 - Docs impact and execution reducer; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: IDXSAFE acceptance; Parallel-safe: no

## Lanes

### SL-0 - IDXSAFE Contract Freeze Tests

- **Scope**: Freeze the explicit mutation-outcome contract before changing dispatcher, store, or commit-advancement logic.
- **Owned files**: `tests/test_dispatcher.py`, `tests/test_dispatcher_advanced.py`, `tests/test_dispatcher_toctou.py`, `tests/test_rename_atomicity.py`, `tests/test_sqlite_store.py`, `tests/test_git_index_manager.py`
- **Interfaces provided**: IF-0-IDXSAFE-1, IF-0-IDXSAFE-2, IF-0-IDXSAFE-3, IF-0-IDXSAFE-4
- **Interfaces consumed**: pre-existing `IndexResult`, `IndexResultStatus`, `IndexingError`, `RepoContext`, `RepositoryReadinessState`, and the current wrong-branch / missing-index contracts
- **Parallel-safe**: no
- **Tasks**:
  - test: Add dispatcher tests that prove add/modify/delete/move paths return explicit mutation results instead of `None`, including swallowed plugin/read failures, no-plugin cases, unchanged files, missing files, and semantic rollback failures.
  - test: Add SQLite-store tests that prove `remove_file()` and `move_file()` distinguish success from not-found rows for the requested `repository_id`, and that rename bookkeeping does not claim success when the primary row never moved.
  - test: Extend `tests/test_git_index_manager.py` so incremental add/modify/delete/move batches fail closed when a required mutation returns `error`, `skipped`, or `not_found`, and so `registry.update_indexed_commit()` is never called after those outcomes.
  - test: Keep existing watcher `index_file_guarded()` tests as the baseline for add/modify statuses rather than redefining a second status vocabulary.
  - impl: Keep this lane test-only; it should freeze the intended caller-visible contract and leave runtime changes to SL-1 through SL-3.
  - verify: `uv run pytest tests/test_dispatcher.py tests/test_dispatcher_advanced.py tests/test_dispatcher_toctou.py tests/test_rename_atomicity.py tests/test_sqlite_store.py tests/test_git_index_manager.py -q --no-cov`

### SL-1 - Dispatcher Mutation Outcome Implementation

- **Scope**: Make the dispatcher return explicit mutation outcomes for required add/modify/delete/move work without widening the query or watcher surfaces.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`
- **Interfaces provided**: IF-0-IDXSAFE-1
- **Interfaces consumed**: SL-0 dispatcher contract tests; existing `IndexResult` / `IndexResultStatus`; `RepoContext`; `IndexingError`; `two_phase_commit`
- **Parallel-safe**: yes
- **Tasks**:
  - test: Run the SL-0 dispatcher-focused tests first and confirm the current `None` / log-only behavior fails them.
  - impl: Either widen the existing `IndexResult` family or add one small sibling result type so `index_file()`, `remove_file()`, and `move_file()` share an explicit status surface with `index_file_guarded()` instead of inventing lane-local booleans.
  - impl: Change `index_file()` so read failures, missing plugins, unchanged files, missing files, and plugin indexing failures become explicit outcomes rather than swallowed side effects.
  - impl: Change `remove_file()` so it reports whether the requested indexed path was actually removed for the repo-scoped SQLite row and whether any semantic/plugin cleanup failure changed the required mutation outcome.
  - impl: Change `move_file()` so successful return means the primary SQLite rename actually moved the intended row; keep `IndexingError` for semantic rollback failure, but also surface a non-success outcome when the source row was never present.
  - impl: Preserve the existing watcher-facing `index_file_guarded()` behavior and current semantic best-effort logging where that work is intentionally shadow-only rather than primary.
  - verify: `uv run pytest tests/test_dispatcher.py tests/test_dispatcher_advanced.py tests/test_dispatcher_toctou.py tests/test_rename_atomicity.py -q --no-cov`
  - verify: `rg -n "IndexResult|IndexResultStatus|def index_file\\(|def remove_file\\(|def move_file\\(" mcp_server/dispatcher/dispatcher_enhanced.py`

### SL-2 - SQLite Affected-Row Accounting

- **Scope**: Give the storage layer the minimum affected-row truth needed for IDXSAFE without changing schema shape or query behavior.
- **Owned files**: `mcp_server/storage/sqlite_store.py`
- **Interfaces provided**: IF-0-IDXSAFE-2
- **Interfaces consumed**: SL-0 store contract tests; existing `files`, `file_moves`, and repository-row invariants; `PathResolver`-normalized relative paths
- **Parallel-safe**: yes
- **Tasks**:
  - test: Use the SL-0 store tests to confirm the current store layer cannot distinguish a real delete/move from a no-op.
  - impl: Return explicit affected-row information from `remove_file()` so callers can tell whether the requested repo-scoped file row existed and was actually removed.
  - impl: Return explicit affected-row information from `move_file()` so callers can tell whether the primary `files` row moved before the `file_moves` audit row is treated as a successful rename.
  - impl: Keep repository scoping strict; this lane must not weaken the existing per-repository row isolation or soft-delete semantics elsewhere.
  - impl: Avoid schema churn unless execution proves a small metadata field is strictly required for caller truth; prefer rowcount-driven results over broader table changes.
  - verify: `uv run pytest tests/test_sqlite_store.py tests/test_rename_atomicity.py -q --no-cov`
  - verify: `rg -n "def remove_file|def move_file|rowcount|file_moves" mcp_server/storage/sqlite_store.py`

### SL-3 - Git-Aware Incremental Safety And Commit Gate

- **Scope**: Consume the dispatcher/store mutation results so incremental sync advances commits only after a clean required-mutation batch.
- **Owned files**: `mcp_server/storage/git_index_manager.py`, `tests/test_incremental_indexer.py`
- **Interfaces provided**: IF-0-IDXSAFE-3, IF-0-IDXSAFE-4
- **Interfaces consumed**: SL-0 git-manager tests; SL-1 dispatcher mutation outcomes; SL-2 store affected-row results; pre-existing `RepositoryRegistry.update_indexed_commit()`, `RepoContext`, and wrong-branch / missing-index behavior
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 git-manager tests first and confirm that current add/modify/delete/move paths can still mark incremental work clean after swallowed or no-op mutations.
  - impl: Refine `UpdateResult` so required skipped or unknown mutation outcomes are non-clean, not merely informational counters.
  - impl: Update `_incremental_index_update()` to consume explicit dispatcher/store results, count `indexed`, `deleted`, and `moved` only from positive mutation outcomes, and record structured failures when a required mutation returns `error`, `not_found`, `skipped`, or another non-success state.
  - impl: Treat rename-destination-missing as clean only when the explicit safe recovery path is a successful delete of the old indexed path; otherwise keep the batch non-clean.
  - impl: Keep the existing missing-durable-index fallback and wrong-branch refusal behavior intact; this lane should only harden truth around required mutation outcomes.
  - impl: Update any incremental-indexer tests that assume dispatcher `None` means success so they instead assert the explicit result contract.
  - verify: `uv run pytest tests/test_git_index_manager.py tests/test_incremental_indexer.py -q --no-cov`
  - verify: `rg -n "UpdateResult|clean|_incremental_index_update|update_indexed_commit|last_indexed_commit" mcp_server/storage/git_index_manager.py tests/test_incremental_indexer.py`

### SL-4 - Docs Impact And Execution Reducer

- **Scope**: Reduce the internal safety contract into an execution-ready closeout and explicitly record the docs decision for this phase.
- **Owned files**: `none`
- **Interfaces provided**: conscious documentation-impact handling for IDXSAFE execution
- **Interfaces consumed**: SL-0 through SL-3 results; roadmap exit criteria; existing support/readiness docs that already describe wrong-branch and unavailable-index behavior
- **Parallel-safe**: no
- **Tasks**:
  - test: Review whether any SL-1 through SL-3 behavior changes a documented public contract; only schedule docs edits if execution proves externally visible wording drift.
  - impl: Record that IDXSAFE is expected to stay internal-only unless the final mutation-result vocabulary leaks into public operator or tool docs.
  - impl: Reduce the final execution checklist to the targeted dispatcher/store/git-manager tests plus a broader regression pass, without inventing a new evidence artifact in this planning phase.
  - verify: `git diff --stat`
  - verify: `git status --short --branch`

## Verification

Planning-only run: do not execute these during plan creation. Run them during
`codex-execute-phase` or manual IDXSAFE execution.

Lane-specific contract checks:

```bash
uv run pytest tests/test_dispatcher.py tests/test_dispatcher_advanced.py tests/test_dispatcher_toctou.py tests/test_rename_atomicity.py tests/test_sqlite_store.py tests/test_git_index_manager.py -q --no-cov
uv run pytest tests/test_incremental_indexer.py -q --no-cov
rg -n "IndexResult|IndexResultStatus|def index_file\\(|def remove_file\\(|def move_file\\(|UpdateResult|update_indexed_commit|last_indexed_commit|rowcount|file_moves" \
  mcp_server/dispatcher/dispatcher_enhanced.py \
  mcp_server/storage/sqlite_store.py \
  mcp_server/storage/git_index_manager.py
```

Whole-phase regression commands:

```bash
uv run pytest tests/test_dispatcher.py tests/test_dispatcher_advanced.py tests/test_dispatcher_toctou.py tests/test_rename_atomicity.py tests/test_sqlite_store.py tests/test_git_index_manager.py tests/test_incremental_indexer.py -q --no-cov
make test
git status --short --branch
```

## Acceptance Criteria

- [ ] Dispatcher add/modify/delete/move paths expose explicit mutation outcomes or raise consistently on failed required mutations.
- [ ] `GitAwareIndexManager._incremental_index_update()` treats skipped, failed, or unknown required mutations as non-clean.
- [ ] `last_indexed_commit` is not advanced after any partial incremental failure.
- [ ] Delete and move accounting verifies that the intended store mutation actually affected the indexed path when that path was expected to exist.
- [ ] Tests cover the real dispatcher behavior where errors may otherwise be logged and swallowed.
- [ ] Existing wrong-branch and missing-index fail-closed behavior remains unchanged.
- [ ] Documentation impact is reviewed explicitly, and no public-doc changes are made unless execution proves the externally documented contract changed.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v6-IDXSAFE.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v6-IDXSAFE.md
  artifact_state: staged
```
