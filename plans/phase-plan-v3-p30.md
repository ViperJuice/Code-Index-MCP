# P30: Branch Drift, Reversions & Watcher Recovery

> Plan doc produced by `codex-plan-phase specs/phase-plans-v3.md P30` on 2026-04-23.
> Source roadmap `specs/phase-plans-v3.md` is staged in this worktree (`git status --short` shows `A  specs/phase-plans-v3.md`).

## Context

P30 consumes P27's readiness vocabulary and P29's ctx-first durable mutation contract. It
should not execute until P27 and P29 targeted tests pass, because this phase deliberately
routes branch, ref-poller, revert, rename, delete, and sweeper recovery behavior through
those contracts.

The current implementation already has a branch comparison helper, but the wrong-branch
path still returns `IndexSyncResult(action="up_to_date")` and calls the watcher drift
callback. `MultiRepositoryWatcher._on_branch_drift()` then enqueues a full rescan with
`bypass_branch_guard=True`, which can mutate the index while the checkout is on a
non-tracked branch. That violates the v3 policy: wrong branch is a readiness/sync state,
not a repair trigger.

The current `RefPoller` polls tracked branch refs but still uses direct `.git/refs` lookup
before falling back to `git --git-dir`, which is fragile for packed refs, linked
worktrees, and explicit worktree rejection diagnostics. It also treats detached or missing
tracked refs as full-rescan triggers. P30 should make ref polling boring: if the current
checkout is on the tracked branch and the tracked ref fast-forwards, run incremental
repair; if the tracked ref diverges from the indexed commit, run a guarded full rebuild;
otherwise return or preserve a non-mutating readiness state.

The change detection code has a separate risk: `ChangeDetector.get_changes_since_commit()`
does one diff pass with `--no-renames` and another with `--find-renames`, so a rename can
be reported as delete/add and rename. P30 freezes a single classification rule so reverts,
deletes, and renames are applied once.

The sweeper exists and is claimed in documentation, but it is only injectable today and
only detects files present on disk but absent from SQLite. P30 should wire it by default
through `MultiRepositoryWatcher` and expand recovery to missed creates, deletes, and
renames, or the audit lane must remove the production claim. This plan chooses wiring by
default so the existing claim becomes true.

External phase dependencies: P27 must complete IF-0-P27-1 through IF-0-P27-6, and P29 must
complete IF-0-P29-1 through IF-0-P29-6, before any P30 implementation lane starts.

## Interface Freeze Gates

- [ ] IF-0-P30-1 - Tracked-branch sync contract: `GitAwareIndexManager.sync_repository_index()` returns `IndexSyncResult(action="wrong_branch", code="wrong_branch", readiness=RepositoryReadiness.to_dict())` when `current_branch != tracked_branch`, and it does not call `_full_index()`, `_incremental_index_update()`, `registry.update_indexed_commit()`, artifact download, or any drift callback in that state.
- [ ] IF-0-P30-2 - Full-repair guard contract: `force_full=True` and `enqueue_full_rescan(repo_id)` still respect the tracked-branch guard; there is no production `bypass_branch_guard=True` path that can index a non-tracked checkout.
- [ ] IF-0-P30-3 - Ref-poller decision contract: ref polling resolves refs with `git -C <repo>` or git-common-dir-safe commands, skips unsupported worktrees safely, calls `sync_repository_index(repo_id)` only for same tracked-branch fast-forwards, calls guarded `enqueue_full_rescan(repo_id)` only for same tracked-branch divergent history, and performs no mutation for detached HEAD, missing tracked refs, or wrong-branch checkouts.
- [ ] IF-0-P30-4 - Single change classification contract: committed and uncommitted change parsing uses one rename-aware `git diff --name-status --find-renames` classification path, so a path is reported exactly once as `added`, `modified`, `deleted`, or `renamed`.
- [ ] IF-0-P30-5 - Incremental application contract: revert commits, deletes, and renames are applied once through P29 ctx-first dispatcher calls; a rename is never also processed as a delete plus add in the same change set.
- [ ] IF-0-P30-6 - Watcher event contract: filesystem events and sweeper recovery mutate only when the current checkout is on the tracked branch; dropped-event recovery is wired by default and detects missed creates, deletes, and renames.
- [ ] IF-0-P30-7 - Documentation truth contract: active production claims about `WatcherSweeper` are either true after default wiring or narrowed in docs during the audit lane.

## Lane Index & Dependencies

- SL-0 - Change classification contract; Depends on: P29; Blocks: SL-1, SL-5; Parallel-safe: yes
- SL-1 - Tracked-branch sync gate; Depends on: P27, P29, SL-0; Blocks: SL-2, SL-4, SL-5; Parallel-safe: no
- SL-2 - Ref-poller tracked-ref decisions; Depends on: P27, SL-1; Blocks: SL-5; Parallel-safe: yes
- SL-3 - Sweeper recovery surface; Depends on: P29; Blocks: SL-4, SL-5; Parallel-safe: yes
- SL-4 - Watcher orchestration and default sweeper wiring; Depends on: P27, P29, SL-1, SL-3; Blocks: SL-5; Parallel-safe: mixed
- SL-5 - P30 contract audit and docs decision; Depends on: SL-0, SL-1, SL-2, SL-3, SL-4; Blocks: P31, P33; Parallel-safe: no

Lane DAG:

```text
P27 + P29
  ├─> SL-0 ─> SL-1 ─> SL-2 ─┐
  │             └────> SL-4 ─┤
  ├─> SL-3 ──────────> SL-4 ─┤
  └─────────────────────────> SL-5
```

## Lanes

### SL-0 - Change Classification Contract

- **Scope**: Make committed and uncommitted change parsing classify every path once, with rename detection enabled in the primary diff path.
- **Owned files**: `mcp_server/indexing/change_detector.py`, `tests/test_git_integration.py`
- **Interfaces provided**: `FileChange` single-classification semantics; rename-aware committed diff parsing; uncommitted diff parsing that does not duplicate renamed paths; IF-0-P30-4 test evidence
- **Interfaces consumed**: P29 ctx-first mutation contract only as downstream context; existing `get_all_extensions()` supported-extension filtering; existing `TestRepositoryBuilder` integration helpers
- **Parallel-safe**: yes
- **Tasks**:
  - test: Update `test_change_detection_renames` so a rename returns exactly one `FileChange(change_type="renamed")` and no matching `added` / `deleted` entries for the same old/new paths.
  - test: Add committed revert coverage where a file added after the indexed commit is reverted before `to_commit`; assert the net diff either has no entry or one deterministic `deleted` entry according to the actual git diff range, not a duplicate add/delete pair.
  - test: Add committed delete coverage proving deletes remain `deleted` and are not filtered out when the deleted path had a supported extension.
  - test: Add uncommitted rename coverage for staged and unstaged rename output, asserting `_parse_status_line()` keeps rename paths even when only one side has a supported extension.
  - impl: Replace the two-pass `--no-renames` plus `--find-renames` committed diff flow with one `git diff --name-status --find-renames from_commit to_commit` pass.
  - impl: Centralize name-status line parsing so committed and uncommitted flows share the same `A`, `M`, `D`, and `R*` rules.
  - impl: Preserve supported-extension filtering by accepting renames when either old or new path is supported.
  - verify: `uv run pytest tests/test_git_integration.py -k "change_detection or revert or rename or delete" -v --no-cov`

### SL-1 - Tracked-Branch Sync Gate

- **Scope**: Make git-aware sync return a non-mutating wrong-branch result and keep all full or incremental repair paths on the tracked branch only.
- **Owned files**: `mcp_server/storage/git_index_manager.py`, `tests/test_git_index_manager.py`, `tests/test_branch_drift_rescan.py`
- **Interfaces provided**: `IndexSyncResult(action="wrong_branch", code="wrong_branch", readiness: dict | None)`; `enqueue_full_rescan(repo_id)` without a branch-guard bypass; `GitAwareIndexManager._get_changed_files()` using IF-0-P30-4 single classification
- **Interfaces consumed**: P27 `RepositoryReadinessState.WRONG_BRANCH`, `ReadinessClassifier.classify_registered()`, and `RepositoryReadiness.to_dict()`; P29 ctx-first `_incremental_index_update(repo_id, ctx, changes)` and `_full_index(repo_id, ctx)`; SL-0 change classification semantics
- **Parallel-safe**: no
- **Tasks**:
  - test: Change branch-switch expectations from `up_to_date` to `wrong_branch`, and assert the result includes `code == "wrong_branch"` plus readiness metadata with `state == "wrong_branch"`.
  - test: Assert wrong-branch sync never calls `_full_index()`, `_incremental_index_update()`, `_has_remote_artifact()`, `_download_commit_index()`, `registry.update_indexed_commit()`, or `on_branch_drift`.
  - test: Replace older drift-callback tests in `tests/test_branch_drift_rescan.py` with non-mutating wrong-branch tests; remove expectations that drift enqueues a full rescan.
  - test: Add a `force_full=True` wrong-branch case proving force-full does not bypass the branch guard.
  - test: Add an `enqueue_full_rescan()` wrong-branch case proving it returns or records `wrong_branch` and does not mutate the index.
  - test: Add same tracked-branch fast-forward coverage proving incremental repair still runs through P29 ctx-first mutation and advances commit only on clean durable success.
  - test: Add same tracked-branch divergent-history coverage proving the guarded full rebuild path runs only when the current branch equals the tracked branch.
  - test: Add manager-level rename/delete/revert change-set coverage proving `_incremental_index_update()` applies each path once through remove, move, or index calls.
  - impl: Extend `IndexSyncResult` with optional `code` and `readiness` fields while preserving existing action handling for `downloaded`, `incremental_update`, `full_index`, `up_to_date`, and `failed`.
  - impl: In `sync_repository_index()`, classify branch mismatch before artifact download or mutation and return `action="wrong_branch"` without invoking the drift callback.
  - impl: Remove or deprecate `bypass_branch_guard` from production full-rescan paths; keep any compatibility parameter inert or test-only until call sites are migrated.
  - impl: Update `enqueue_full_rescan()` so it does not clear `last_indexed_commit` until after the tracked-branch guard passes and a guarded full rebuild is actually attempted.
  - impl: Change `_get_changed_files()` to use the same single rename-aware classification semantics as SL-0, returning `ChangeSet` entries without delete/add duplication for renames.
  - verify: `uv run pytest tests/test_git_index_manager.py tests/test_branch_drift_rescan.py -v --no-cov`

### SL-2 - Ref-Poller Tracked-Ref Decisions

- **Scope**: Make ref polling safe for ordinary repos, packed refs, linked-worktree diagnostics, fast-forwards, force-pushes, and wrong-branch checkouts.
- **Owned files**: `mcp_server/watcher/ref_poller.py`, `tests/test_ref_poller.py`, `tests/test_ref_poller_edges.py`
- **Interfaces provided**: `RefPoller._read_ref(repo_path, branch) -> str | None` using `git -C`; `RefPoller._current_branch(repo_path) -> str | None`; tracked-ref decision table from IF-0-P30-3
- **Interfaces consumed**: SL-1 `sync_repository_index()` and guarded `enqueue_full_rescan()` behavior; P27 unsupported-worktree readiness when `repo_resolver.classify()` is available; existing registry `list_all()` and `RepositoryInfo.tracked_branch`
- **Parallel-safe**: yes
- **Tasks**:
  - test: Update detached-HEAD and missing-tracked-ref tests so they assert no `enqueue_full_rescan()` or `sync_repository_index()` call.
  - test: Add a wrong-branch poller case where `current_branch != tracked_branch`; assert no sync or full rescan is scheduled.
  - test: Keep normal fast-forward coverage: old indexed commit is an ancestor of the new tracked tip, current branch equals tracked branch, and `sync_repository_index(repo_id)` is called exactly once.
  - test: Keep force-push/divergent coverage: old indexed commit is not an ancestor of the tracked tip, current branch equals tracked branch, and guarded `enqueue_full_rescan(repo_id)` is called exactly once.
  - test: Add packed-ref coverage proving `_read_ref()` uses `git -C <repo> rev-parse --verify refs/heads/<branch>` instead of assuming `.git/refs/heads/<branch>` is a file.
  - test: Add a linked-worktree or fake unsupported-worktree readiness case where the poller does not mutate and logs/skips safely.
  - impl: Replace direct `.git/refs` reads and `git --git-dir <repo>/.git` fallback with `git -C <repo> rev-parse --verify refs/heads/<branch>`.
  - impl: Add a current-branch check before fast-forward/divergent decisions; non-matching branches are skipped because SL-1 will expose `wrong_branch` through explicit sync.
  - impl: Treat detached HEAD, missing tracked refs, and unsupported worktrees as non-mutating poll outcomes, not full-rescan triggers.
  - impl: Keep `_is_ancestor()` on `git -C <repo> merge-base --is-ancestor old new`.
  - verify: `uv run pytest tests/test_ref_poller.py tests/test_ref_poller_edges.py -v --no-cov`

### SL-3 - Sweeper Recovery Surface

- **Scope**: Expand `WatcherSweeper` from create-only drift detection to create, delete, and rename recovery without mutating indexes directly.
- **Owned files**: `mcp_server/watcher/sweeper.py`, `tests/test_watcher_sweep.py`, `tests/test_sweeper_observability.py`
- **Interfaces provided**: `WatcherSweeper` callbacks for missed creates, deletes, and renames; deterministic drift return values for repo ids with missed events; IF-0-P30-6 sweeper recovery evidence
- **Interfaces consumed**: P29 durable SQLite file records and relative paths; existing `build_walker_filter()` gitignore filtering; existing `_CODE_EXTENSIONS` or a shared extension source if introduced inside this file
- **Parallel-safe**: yes
- **Tasks**:
  - test: Keep missed-create coverage and assert the create callback receives `(repo_id, relative_path)`.
  - test: Add missed-delete coverage where SQLite contains a code file absent from disk; assert the delete callback receives the indexed relative path exactly once.
  - test: Add missed-rename coverage where one indexed path disappears and one unindexed path appears with the same content hash when hashes are available; assert the rename callback receives `(repo_id, old_relative_path, new_relative_path)` instead of separate delete/create callbacks.
  - test: Add a fallback case where hash data is unavailable or ambiguous; assert the sweeper emits separate create/delete callbacks rather than guessing a rename.
  - test: Preserve start/stop and exception-observability tests.
  - impl: Extend `WatcherSweeper.__init__()` with explicit callbacks for missed create, delete, and rename while preserving `on_missed_path` as a compatibility alias for create-only tests during migration.
  - impl: Build filesystem and SQLite relative-path maps, then compute `created = fs - db`, `deleted = db - fs`, and unambiguous `renamed` pairs before invoking callbacks.
  - impl: Keep sweeper side-effect-free beyond callbacks; it should not call dispatcher methods directly.
  - impl: Respect gitignore and supported-extension filtering for filesystem paths, and avoid reporting ignored indexed paths as deletes unless existing tests establish that behavior.
  - verify: `uv run pytest tests/test_watcher_sweep.py tests/test_sweeper_observability.py -v --no-cov`

### SL-4 - Watcher Orchestration And Default Sweeper Wiring

- **Scope**: Remove branch-drift full-rescan orchestration from the watcher and wire the expanded sweeper by default through ctx-aware, tracked-branch-guarded handlers.
- **Owned files**: `mcp_server/watcher_multi_repo.py`, `tests/test_watcher_multi_repo.py`
- **Interfaces provided**: `MultiRepositoryWatcher` default `WatcherSweeper` construction; tracked-branch-guarded missed create/delete/rename handlers; no drift callback that enqueues wrong-branch full rescans
- **Interfaces consumed**: SL-1 wrong-branch sync and guarded full-rescan behavior; SL-3 sweeper callback API; P29 ctx-first dispatcher methods; existing `lock_registry.acquire(repo_id)`; existing `MultiRepositoryHandler` branch and gitignore filters
- **Parallel-safe**: mixed
- **Tasks**:
  - test: Add watcher construction coverage proving a sweeper is created by default when the watcher has access to a store provider, and an explicitly supplied sweeper is still honored.
  - test: Add start/stop coverage proving the default sweeper starts and stops with `start_watching_all()` and `stop_watching_all()`.
  - test: Add branch-drift callback coverage proving `GitAwareIndexManager.on_branch_drift` is not wired to `enqueue_full_rescan()` for wrong branches.
  - test: Add missed-create callback coverage that routes through the same tracked-branch and gitignore guards as live create/modify events before calling `remove_file(ctx, path)` and `index_file_guarded(ctx, path, observed_hash)`.
  - test: Add missed-delete callback coverage that calls `remove_file(ctx, path)` once on the tracked branch and does nothing on wrong branches.
  - test: Add missed-rename callback coverage that calls `move_file(ctx, old_path, new_path)` once on the tracked branch and does nothing on wrong branches.
  - test: Update live event tests so `mark_repository_changed(repo_id)` is called only when a mutation was actually attempted or applied, not after a dropped wrong-branch event.
  - impl: Remove `_on_branch_drift()` behavior that enqueues a full rescan, or make the callback record diagnostics only without scheduling mutation.
  - impl: Have handler mutation helpers return a boolean indicating whether a mutation was attempted, and mark repositories changed only when the boolean is true.
  - impl: Add internal missed create/delete/rename methods that reuse `MultiRepositoryHandler` guarded mutation logic instead of duplicating branch and gitignore checks.
  - impl: Construct a default `WatcherSweeper` from registered repo roots and per-repo stores when `sweeper` is omitted and required store access is available; log a clear local-only warning if default wiring cannot be built.
  - verify: `uv run pytest tests/test_watcher_multi_repo.py tests/test_branch_drift_rescan.py -v --no-cov`

### SL-5 - P30 Contract Audit And Docs Decision

- **Scope**: Run the P30 reducer checks, confirm every exit criterion is covered, and either keep or narrow active sweeper production claims based on the implemented wiring.
- **Owned files**: (none)
- **Interfaces provided**: completed IF-0-P30-1 through IF-0-P30-7 evidence for P31 and P33 planning
- **Interfaces consumed**: SL-0 through SL-4 outputs; roadmap exit criteria from `specs/phase-plans-v3.md`; P27 readiness vocabulary; P29 ctx-first durable mutation contract; active docs claims about `WatcherSweeper`
- **Parallel-safe**: no
- **Tasks**:
  - test: Run all P30 targeted tests after implementation lanes land.
  - verify: `uv run pytest tests/test_git_index_manager.py tests/test_branch_drift_rescan.py tests/test_ref_poller.py tests/test_ref_poller_edges.py tests/test_watcher_sweep.py tests/test_watcher_multi_repo.py tests/test_git_integration.py -v --no-cov`
  - verify: `uv run pytest tests/test_sweeper_observability.py tests/test_incremental_indexer.py -v --no-cov`
  - verify: `rg -n "bypass_branch_guard|on_branch_drift|enqueue_full_rescan|wrong_branch|--no-renames|--find-renames|WatcherSweeper" mcp_server tests AGENTS.md README.md docs`
  - verify: `rg -n "branch\\.drift\\.detected|force_full=True.*bypass|detached HEAD.*enqueueing full rescan|branch disappeared.*enqueueing full rescan" mcp_server tests`
  - impl: Review grep results and confirm there is no production path that can index a wrong-branch checkout.
  - impl: If SL-4 cannot wire sweeper by default, create a follow-up docs change in the smallest active docs surface to remove or qualify the production claim; otherwise record that no docs change is required because the claim is now true.
  - impl: Record P31 follow-up only for artifact publish/freshness behavior; do not broaden P30 into artifact identity work.

## Verification

Required P30 targeted checks:

```bash
uv run pytest tests/test_git_index_manager.py tests/test_branch_drift_rescan.py -v --no-cov
uv run pytest tests/test_ref_poller.py tests/test_ref_poller_edges.py -v --no-cov
uv run pytest tests/test_watcher_sweep.py tests/test_watcher_multi_repo.py tests/test_sweeper_observability.py -v --no-cov
uv run pytest tests/test_git_integration.py -k "change_detection or revert or rename or delete" -v --no-cov
```

P29 compatibility checks:

```bash
uv run pytest tests/test_incremental_indexer.py tests/test_git_integration.py tests/test_git_index_manager.py -v --no-cov
```

Contract searches:

```bash
rg -n "bypass_branch_guard|on_branch_drift|enqueue_full_rescan|wrong_branch|--no-renames|--find-renames|WatcherSweeper" \
  mcp_server tests AGENTS.md README.md docs

rg -n "branch\\.drift\\.detected|force_full=True.*bypass|detached HEAD.*enqueueing full rescan|branch disappeared.*enqueueing full rescan" \
  mcp_server tests
```

Whole-phase optional regression:

```bash
make test
```

## Acceptance Criteria

- [ ] Branch drift returns a non-mutating `wrong_branch` readiness/sync result and does not enqueue or run a full rescan.
- [ ] `force_full=True` and `enqueue_full_rescan(repo_id)` cannot bypass the tracked-branch guard in production.
- [ ] Ref polling uses `git -C <repo>` or git-common-dir-safe commands and behaves correctly for ordinary repos, packed refs, and explicitly rejected worktrees.
- [ ] Same tracked-branch fast-forwards run incremental repair through P29 ctx-first mutation and commit advancement rules.
- [ ] Same tracked-branch divergent history or force-push runs a guarded full rebuild.
- [ ] Detached HEAD, missing tracked refs, unsupported worktrees, and wrong-branch checkouts do not mutate indexes through the poller.
- [ ] Revert commits, deletes, and renames are classified once and applied once, not double-counted as both delete/add and rename.
- [ ] Dropped-event recovery is wired by default through `MultiRepositoryWatcher`.
- [ ] Sweeper recovery detects missed creates, deletes, and unambiguous renames, and all callbacks respect tracked-branch and gitignore guards before mutation.
- [ ] Active docs claims about watcher sweep recovery are true after implementation or explicitly narrowed by the audit lane.
