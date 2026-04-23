# P29: Incremental Indexing Interface Repair

> Plan doc produced by `codex-plan-phase specs/phase-plans-v3.md P29` on 2026-04-23.
> Source roadmap `specs/phase-plans-v3.md` is staged in this worktree (`git status --short` shows `A  specs/phase-plans-v3.md`).

## Context

P29 consumes P27's repository-readiness and resolver contract. It should not execute until
P27's `RepositoryReadiness`, `ReadinessClassifier`, `RepoResolver.classify()`, and
unsupported-worktree behavior are final and their targeted tests pass.

The current mutation path is split across two interface generations. `DispatcherProtocol`
and `EnhancedDispatcher` expose ctx-first mutation methods:
`index_file(ctx, path)`, `index_directory(ctx, directory)`, `remove_file(ctx, path)`, and
`move_file(ctx, old_path, new_path, content_hash=None)`. `GitAwareIndexManager` still calls
those methods with only paths, and `IncrementalIndexer` does the same through its optional
dispatcher path. That means real incremental/full indexing can fail at runtime or silently
avoid the per-repo store selected by `RepoContext`.

The second current gap is durability accounting. `_incremental_index_update()` dry-runs
success when `.mcp-index/current.db` is missing, and `sync_repository_index()` advances
`last_indexed_commit` after incremental updates without checking per-file failures. Full
indexing also returns a plain file count, so the caller cannot distinguish a clean full
rebuild from a partial or failed durable mutation.

P29 freezes one rule: commit state follows durable index state. The manager must resolve a
`RepoContext` before any mutation, every dispatcher mutation call must use the ctx-first
contract, and `last_indexed_commit` must advance only after an artifact download, a clean
incremental update, or a clean full rebuild has durably succeeded.

External phase dependency: P27 must complete IF-0-P27-1 through IF-0-P27-6 before any P29
implementation lane starts. P28 can proceed in parallel because it owns query/handoff paths;
P30 must wait for P29 so branch drift, revert, rename, and watcher-recovery tests exercise
the repaired mutation contract.

## Interface Freeze Gates

- [ ] IF-0-P29-1 - Mutation context contract: `GitAwareIndexManager` resolves exactly one
      `RepoContext` for the target registered repository before indexing, deleting, moving,
      or full-indexing files, and every dispatcher mutation call passes that ctx as the
      first positional argument.
- [ ] IF-0-P29-2 - Manager construction contract: production wiring can provide the same
      `RepoResolver` and `StoreRegistry` returned by `initialize_stateless_services()`;
      test and legacy construction remain possible without capturing cwd or preloading a
      global SQLite store into the dispatcher.
- [ ] IF-0-P29-3 - Incremental result contract: `UpdateResult` reports `indexed`,
      `deleted`, `moved`, `failed`, `skipped`, and `errors`; `sync_repository_index()` does
      not call `update_indexed_commit()` when `failed > 0` or any mutation error is present.
- [ ] IF-0-P29-4 - Missing-index contract: when the registered `current.db` is missing,
      incremental sync either runs a real ctx-first full rebuild or returns
      `IndexSyncResult(action="failed", error=...)`; it never returns dry-run success and
      never advances `last_indexed_commit`.
- [ ] IF-0-P29-5 - Full-index durability contract: full indexing returns a structured
      result that distinguishes clean success from partial failure; `last_indexed_commit`
      advances only when `failed_files == 0` and the durable SQLite index exists.
- [ ] IF-0-P29-6 - Legacy incremental-indexer contract: `IncrementalIndexer` either
      accepts/resolves a `RepoContext` and uses ctx-first dispatcher calls, or its
      dispatcher path is retired behind `GitAwareIndexManager` so no live code calls
      dispatcher mutation methods without ctx.

## Lane Index & Dependencies

- SL-0 - Git-aware manager ctx and durability contract; Depends on: P27; Blocks: SL-1, SL-2, SL-3, SL-4, SL-5; Parallel-safe: no
- SL-1 - IncrementalIndexer ctx-first cleanup; Depends on: SL-0; Blocks: SL-3, SL-5; Parallel-safe: yes
- SL-2 - Production manager wiring; Depends on: SL-0; Blocks: SL-4, SL-5; Parallel-safe: yes
- SL-3 - Real-repo integration coverage; Depends on: SL-0, SL-1; Blocks: SL-5; Parallel-safe: no
- SL-4 - Bootstrap and command compatibility coverage; Depends on: SL-0, SL-2; Blocks: SL-5; Parallel-safe: no
- SL-5 - P29 contract audit and docs decision; Depends on: SL-0, SL-1, SL-2, SL-3, SL-4; Blocks: P30, P32, P33; Parallel-safe: no

Lane DAG:

```text
P27
 └─> SL-0
      ├─> SL-1 ─> SL-3 ─┐
      ├─> SL-2 ─> SL-4 ─┤
      └─────────────────> SL-5
```

## Lanes

### SL-0 - Git-Aware Manager Ctx And Durability Contract

- **Scope**: Repair `GitAwareIndexManager` so every incremental/full mutation uses a resolved `RepoContext` and commit advancement is gated by clean durable mutation results.
- **Owned files**: `mcp_server/storage/git_index_manager.py`, `tests/test_git_index_manager.py`
- **Interfaces provided**: `GitAwareIndexManager(..., repo_resolver: RepoResolver | None = None, store_registry: StoreRegistry | None = None)`; `_resolve_ctx(repo_id) -> RepoContext | None`; `_incremental_index_update(repo_id, ctx, changes) -> UpdateResult`; `_full_index(repo_id, ctx) -> UpdateResult`; `IndexSyncResult.action` values `downloaded`, `incremental_update`, `full_index`, `up_to_date`, and `failed`
- **Interfaces consumed**: P27 `RepoResolver.resolve()` / `RepoResolver.classify()` semantics; `StoreRegistry.get(repo_id)`; `RepositoryInfo.index_path`; ctx-first dispatcher mutation methods from `DispatcherProtocol`
- **Parallel-safe**: no
- **Tasks**:
  - test: Add manager tests with a fake ctx-signature dispatcher proving `_incremental_index_update()` calls `remove_file(ctx, path)`, `move_file(ctx, old, new, content_hash)`, and `index_file(ctx, path)` with the same resolved `RepoContext`.
  - test: Add a missing-`current.db` sync test proving incremental sync does not dry-run counts and either attempts `_full_index(repo_id, ctx)` or returns `action == "failed"` without calling `registry.update_indexed_commit()`.
  - test: Add a partial-failure test where one changed file fails and `sync_repository_index()` returns `action == "failed"` or a failure-bearing result without advancing `last_indexed_commit`.
  - test: Add a clean full-rebuild test proving `update_indexed_commit(repo_id, current_commit, branch=current_branch)` is called only when `_full_index()` reports zero failures and `current.db` exists.
  - impl: Extend `GitAwareIndexManager.__init__()` to accept optional resolver/store dependencies while preserving existing call sites during the transition.
  - impl: Add `_resolve_ctx()` that uses the injected resolver when available and otherwise constructs or uses a `StoreRegistry` to build a `RepoContext` for the registered path; return a failed sync result when no ctx can be resolved.
  - impl: Change all dispatcher calls in `_incremental_index_update()` and `_full_index()` to ctx-first calls.
  - impl: Replace missing-index dry-run accounting with a full-rebuild path or a failed `IndexSyncResult`; do not count unmutated files as processed.
  - impl: Promote `UpdateResult` to carry skipped/error details needed by tests while keeping existing `indexed`, `deleted`, `moved`, and `failed` fields stable for callers.
  - impl: Gate every `registry.update_indexed_commit()` call after incremental/full mutation on zero failures and successful durable index existence.
  - verify: `uv run pytest tests/test_git_index_manager.py -v --no-cov`

### SL-1 - IncrementalIndexer Ctx-First Cleanup

- **Scope**: Bring the standalone `IncrementalIndexer` dispatcher path in line with the ctx-first contract or remove it from live dispatcher mutation responsibility.
- **Owned files**: `mcp_server/indexing/incremental_indexer.py`, `tests/test_incremental_indexer.py`
- **Interfaces provided**: `IncrementalIndexer(..., ctx: RepoContext | None = None)` or equivalent explicit ctx resolver hook; ctx-first calls for `index_file`, `remove_file`, and `move_file`; no no-ctx dispatcher mutation calls remain in this module
- **Interfaces consumed**: SL-0 `UpdateResult` failure semantics where applicable; existing `SQLiteStore` direct mutation fallback; `RepoContext.sqlite_store`; `PathResolver(repo_path)` behavior
- **Parallel-safe**: yes
- **Tasks**:
  - test: Update `DummyDispatcher` to require ctx-first signatures and assert all add, modify, delete, and rename tests receive the fixture `RepoContext`.
  - test: Add a regression test that constructing `IncrementalIndexer` with a dispatcher but without ctx raises a clear `ValueError` or returns errors instead of calling dispatcher methods without ctx.
  - test: Keep the direct-`SQLiteStore` no-dispatcher path covered so existing cleanup, semantic stale-vector removal, and two-phase move behavior continue to work.
  - impl: Add an explicit ctx dependency for dispatcher-backed incremental indexing, or remove dispatcher usage and route all durable mutation through direct store methods for this class.
  - impl: Replace `self.dispatcher.remove_file(full_path)`, `move_file(old, new, hash)`, and `index_file(full_path)` with ctx-first calls when dispatcher usage remains.
  - impl: Keep `_get_repository_id()` overrides in tests local to direct store lookup and avoid introducing a second repo identity source for dispatcher calls.
  - verify: `uv run pytest tests/test_incremental_indexer.py -v --no-cov`

### SL-2 - Production Manager Wiring

- **Scope**: Wire production and operator entry points so `GitAwareIndexManager` shares the same resolver/store context used by query tools.
- **Owned files**: `mcp_server/cli/bootstrap.py`, `mcp_server/cli/repository_commands.py`, `mcp_server/gateway.py`, `mcp_server/watcher_multi_repo.py`
- **Interfaces provided**: `initialize_stateless_services()` returns a `GitAwareIndexManager` constructed with the bootstrapped `RepoResolver` and `StoreRegistry`; repository sync/watch and gateway startup instantiate managers without old `EnhancedDispatcher(sqlite_store=...)` mutation assumptions
- **Interfaces consumed**: SL-0 manager constructor contract; existing bootstrap 5-tuple shape; existing `MultiRepositoryWatcher(..., repo_resolver=repo_resolver)` optional dependency
- **Parallel-safe**: yes
- **Tasks**:
  - test: Defer assertions to SL-4, but note every modified constructor call must be covered by existing bootstrap, repository command, gateway, or watcher tests.
  - impl: Update `initialize_stateless_services()` to pass `repo_resolver=repo_resolver` and `store_registry=store_registry` into `GitAwareIndexManager`.
  - impl: Update repository CLI sync/watch construction to build or reuse a `StoreRegistry` and `RepoResolver` instead of relying on `EnhancedDispatcher(sqlite_store=store)` for mutation routing.
  - impl: Update gateway startup manager construction to pass the gateway `repo_resolver` and its matching store registry when available.
  - impl: Preserve existing constructor compatibility for branch-drift and watcher tests that instantiate `GitAwareIndexManager(registry, dispatcher)` directly.
  - verify: `uv run pytest tests/test_bootstrap.py tests/test_repository_commands.py tests/test_gateway.py tests/test_watcher_multi_repo.py -v --no-cov`

### SL-3 - Real-Repo Integration Coverage

- **Scope**: Exercise P29 behavior against a real temporary git repository, real registry, real store, and a ctx-signature dispatcher surface.
- **Owned files**: `tests/test_git_integration.py`
- **Interfaces provided**: Integration evidence for IF-0-P29-1 through IF-0-P29-5
- **Interfaces consumed**: SL-0 `GitAwareIndexManager` ctx and durability behavior; SL-1 `IncrementalIndexer` ctx behavior where integration coverage still uses it; existing `TestRepositoryBuilder` and `RepositoryRegistry` fixtures
- **Parallel-safe**: no
- **Tasks**:
  - test: Update existing incremental-vs-full tests so the dispatcher fixture requires ctx-first signatures and records `ctx.repo_id` for every mutation.
  - test: Add a real-repo missing-index case where a registered repo has `last_indexed_commit` but no `current.db`; assert sync does not report incremental dry-run success and does not advance the commit unless a full rebuild actually creates a durable index.
  - test: Add a real-repo partial mutation failure where one file mutation raises; assert `last_indexed_commit` remains at the previous commit.
  - test: Keep large-change full-reindex coverage and assert full rebuild failures do not look like clean `full_index` success.
  - impl: Adjust integration fixtures to use `StoreRegistry.for_registry(registry)` and `RepoResolver(registry, store_registry)` when constructing the manager.
  - verify: `uv run pytest tests/test_git_integration.py -v --no-cov`

### SL-4 - Bootstrap And Command Compatibility Coverage

- **Scope**: Prove the new manager constructor and production wiring remain compatible with existing bootstrap, CLI, gateway, and branch-drift tests.
- **Owned files**: `tests/test_bootstrap.py`, `tests/test_multi_repo_bootstrap_order.py`, `tests/test_repository_commands.py`, `tests/test_gateway.py`, `tests/test_branch_drift_rescan.py`, `tests/test_watcher_multi_repo.py`
- **Interfaces provided**: Compatibility coverage for IF-0-P29-2 and non-P30 branch-drift behavior
- **Interfaces consumed**: SL-0 constructor compatibility and failure results; SL-2 production wiring changes; existing P30-owned branch guard semantics are observed but not changed
- **Parallel-safe**: no
- **Tasks**:
  - test: Add bootstrap assertions that the returned `GitAwareIndexManager` carries the same `RepoResolver` / `StoreRegistry` instances returned earlier in the tuple, without changing tuple order.
  - test: Update repository command sync tests so fake managers tolerate the new constructor kwargs and sync output handles `incremental_update`, `full_index`, and `failed` actions correctly.
  - test: Add or adjust gateway startup tests to ensure manager construction passes resolver/store dependencies when watcher startup is enabled.
  - test: Keep branch-drift guard expectations unchanged: wrong branch should still short-circuit before mutation, and bypass behavior remains P30-owned.
  - impl: Make only test adjustments needed by SL-2 wiring; do not add branch policy changes here.
  - verify: `uv run pytest tests/test_bootstrap.py tests/test_multi_repo_bootstrap_order.py tests/test_repository_commands.py tests/test_gateway.py tests/test_branch_drift_rescan.py tests/test_watcher_multi_repo.py -v --no-cov`

### SL-5 - P29 Contract Audit And Docs Decision

- **Scope**: Run the P29 reducer checks, confirm there are no remaining no-ctx dispatcher mutation calls, and record that no user-facing docs change is required for this internal repair phase.
- **Owned files**: (none)
- **Interfaces provided**: completed IF-0-P29-1 through IF-0-P29-6 evidence for P30, P32, and P33 planning
- **Interfaces consumed**: SL-0 through SL-4 outputs; roadmap exit criteria from `specs/phase-plans-v3.md`; P27 readiness vocabulary; active P28 query/handoff work only as a non-overlap check
- **Parallel-safe**: no
- **Tasks**:
  - test: Run all P29 targeted tests after implementation lanes land.
  - verify: `uv run pytest tests/test_git_index_manager.py tests/test_git_integration.py tests/test_incremental_indexer.py -v --no-cov`
  - verify: `uv run pytest tests/test_bootstrap.py tests/test_multi_repo_bootstrap_order.py tests/test_repository_commands.py tests/test_gateway.py tests/test_branch_drift_rescan.py tests/test_watcher_multi_repo.py -v --no-cov`
  - verify: `rg -n "dispatcher\\.(index_file|remove_file|move_file|index_directory)\\([^c]" mcp_server tests`
  - verify: `rg -n "dry-run accounting|applying incremental dry-run|update_indexed_commit\\(" mcp_server/storage/git_index_manager.py tests/test_git_index_manager.py tests/test_git_integration.py`
  - impl: Review the grep results and confirm any remaining no-ctx patterns are false positives or intentionally non-dispatcher calls.
  - impl: Record docs decision in the phase handoff: no docs changes are required because P29 changes internal mutation interfaces; P28 owns model-facing query/handoff wording and P30/P33 own branch/revert/release evidence.

## Verification

Required P29 targeted checks:

```bash
uv run pytest tests/test_git_index_manager.py tests/test_git_integration.py tests/test_incremental_indexer.py -v --no-cov
```

Production wiring and branch-guard compatibility checks:

```bash
uv run pytest tests/test_bootstrap.py tests/test_multi_repo_bootstrap_order.py tests/test_repository_commands.py tests/test_gateway.py tests/test_branch_drift_rescan.py tests/test_watcher_multi_repo.py -v --no-cov
```

Contract searches:

```bash
rg -n "dispatcher\\.(index_file|remove_file|move_file|index_directory)\\([^c]" mcp_server tests
rg -n "dry-run accounting|applying incremental dry-run|update_indexed_commit\\(" mcp_server/storage/git_index_manager.py tests/test_git_index_manager.py tests/test_git_integration.py
```

Whole-phase optional regression:

```bash
make test
```

## Acceptance Criteria

- [ ] `GitAwareIndexManager` resolves a `RepoContext` before indexing, deleting, moving, or full-indexing files.
- [ ] Every dispatcher mutation call in `GitAwareIndexManager` and `IncrementalIndexer` uses the ctx-first dispatcher contract.
- [ ] `IncrementalIndexer` no longer has a live dispatcher-backed path that can call `index_file`, `remove_file`, or `move_file` without ctx.
- [ ] Missing `.mcp-index/current.db` forces a real full rebuild or returns a failed sync/readiness state; it does not dry-run success.
- [ ] Any per-file incremental mutation failure prevents `last_indexed_commit` from advancing.
- [ ] Full indexing advances `last_indexed_commit` only after a clean durable rebuild with zero failed files and an existing SQLite index.
- [ ] Integration tests use a real temporary repo, registry, store, and ctx-signature dispatcher surface.
- [ ] Bootstrap, CLI, gateway, watcher, and branch-drift compatibility tests pass without changing P30-owned branch policy.
- [ ] No user-facing docs change is required for P29; the docs decision is recorded in the contract audit.
