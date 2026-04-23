# P32: Runtime Isolation & Dispatcher State Cleanup

> Plan doc produced by `codex-plan-phase specs/phase-plans-v3.md P32` on 2026-04-23.
> Source roadmap `specs/phase-plans-v3.md` is clean in this worktree (`git status --short -- specs/phase-plans-v3.md` produced no output).

## Context

P32 consumes P27's repository readiness and unsupported-worktree contract, plus P29's
ctx-first dispatcher mutation contract. Implementation should not start until P29 has
proved that `GitAwareIndexManager` and `IncrementalIndexer` pass a resolved
`RepoContext` into every dispatcher mutation. P32 may overlap with P30/P31 only if the
active implementation plan avoids shared files such as `dispatcher_enhanced.py`,
`watcher_multi_repo.py`, `gateway.py`, and `cli/bootstrap.py`.

The current runtime still has several process-global or partially-scoped surfaces:

- `RepoResolver.resolve()` returns the caller's requested path as `workspace_root`, so a
  nested request can make mutation path normalization relative to a subdirectory instead
  of the registered repository root.
- `EnhancedDispatcher.remove_file()` and `move_file()` pass `repository_id=1` into
  `SQLiteStore`, even though each per-repo SQLite database can have a different internal
  integer row for the repository.
- `SemanticIndexerRegistry` exists and `EnhancedDispatcher` can accept it, but normal
  bootstrap does not inject it. The dispatcher can also construct a process-global
  semantic fallback from `QDRANT_PATH`, which is unsafe for registered multi-repo use.
- Graph nodes, graph edges, analyzers, and context selectors are stored on the dispatcher
  as process-global fields, while graph methods are exposed as per-`RepoContext` APIs.
- `PluginSetRegistry.evict(repo_id)` exists, but repository unregister/remove paths do
  not consistently evict plugin, semantic, SQLite, dispatcher file-cache, or graph state.
- `get_status`, FastAPI `/status`, and cross-repo statistics expose readiness rows, but
  they do not clearly report per-repo lexical, semantic, graph, plugin-cache, and
  cross-repo feature availability.

P32's practical rule is conservative: if a feature is not correctly repo-scoped, it must
be reported as unavailable for that repo instead of behaving like an empty result.

## Interface Freeze Gates

- [ ] IF-0-P32-1 - Runtime isolation contract: repository-scoped SQLite, semantic,
      graph, plugin, and mutation state is either correctly scoped by `RepoContext.repo_id`
      and registered repository root, or explicitly reports `status: "unavailable"` with
      a deterministic `reason`.
- [ ] IF-0-P32-2 - RepoContext path contract: `RepoResolver.resolve(path)` returns
      `RepoContext.workspace_root == registry_entry.path` for registered repos and
      preserves the original requested path in `RepoContext.requested_path` for
      diagnostics; unsupported worktrees still resolve to `None`.
- [ ] IF-0-P32-3 - SQLite repository-row contract: dispatcher mutation paths resolve the
      internal SQLite `repositories.id` row from `ctx.registry_entry.path` or create it
      for that repo before calling `SQLiteStore.remove_file()` or `SQLiteStore.move_file()`;
      no dispatcher mutation call hard-codes `repository_id=1`.
- [ ] IF-0-P32-4 - Semantic runtime contract: normal STDIO/bootstrap and FastAPI startup
      inject `SemanticIndexerRegistry(repository_registry)` into `EnhancedDispatcher`
      when semantic search is enabled and preflight passes; registered repos never use a
      process-global semantic fallback, and unavailable semantic search is reported per
      repo with a reason.
- [ ] IF-0-P32-5 - Graph runtime contract: graph state is keyed by `repo_id` and repo
      root, or graph APIs return an explicit unavailable payload/status; registered repos
      never read process-global graph nodes/edges built for another repository.
- [ ] IF-0-P32-6 - Repository eviction contract: unregister/remove closes the repo's
      `SQLiteStore`, evicts its plugin set, semantic indexer, dispatcher file-cache
      entries, and graph state, and leaves other repos' runtime state intact.
- [ ] IF-0-P32-7 - Cross-repo status contract: `get_status`, FastAPI `/status`, and
      `CrossRepositorySearchCoordinator.get_search_statistics()` include per-repo
      readiness plus feature availability for lexical, semantic, graph, plugin cache, and
      cross-repo search fanout.

## Lane Index & Dependencies

- SL-0 - RepoContext root and SQLite row helpers; Depends on: P27, P29; Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Dispatcher mutation, graph, and cache isolation; Depends on: SL-0; Blocks: SL-3, SL-4, SL-5; Parallel-safe: no
- SL-2 - Semantic registry bootstrap and lifecycle; Depends on: SL-0; Blocks: SL-3, SL-4, SL-5; Parallel-safe: yes
- SL-3 - Status and cross-repo feature reporting; Depends on: SL-1, SL-2; Blocks: SL-5; Parallel-safe: yes
- SL-4 - Repository unregister/remove eviction wiring; Depends on: SL-1, SL-2; Blocks: SL-5; Parallel-safe: yes
- SL-5 - P32 contract audit and docs decision; Depends on: SL-0, SL-1, SL-2, SL-3, SL-4; Blocks: P33; Parallel-safe: no

Lane DAG:

```text
P27 + P29
  └─> SL-0
       ├─> SL-1 ─┬─> SL-3 ─┐
       │         └─> SL-4 ─┤
       └─> SL-2 ─┬─> SL-3 ─┤
                 └─> SL-4 ─┘
SL-0 + SL-1 + SL-2 + SL-3 + SL-4 ─> SL-5 ─> P33
```

## Lanes

### SL-0 - RepoContext Root And SQLite Row Helpers

- **Scope**: Make resolved contexts carry the registered repository root for mutation
  paths and provide a single SQLite helper for the internal repository row id.
- **Owned files**: `mcp_server/core/repo_context.py`, `mcp_server/core/repo_resolver.py`,
  `mcp_server/storage/sqlite_store.py`, `tests/test_repo_resolver.py`,
  `tests/test_sqlite_store.py`, `tests/test_persistence.py`
- **Interfaces provided**: `RepoContext.requested_path: Path | None`;
  `RepoContext.workspace_root` as registered repo root; `SQLiteStore.ensure_repository_row(
  repo_path, name=None, metadata=None) -> int` or equivalent helper returning the internal
  integer `repositories.id`; IF-0-P32-2 and IF-0-P32-3 helper evidence
- **Interfaces consumed**: P27 `ReadinessClassifier.classify_path()` and
  `RepositoryRegistry.get()`; P29 ctx-first mutation contract; existing
  `SQLiteStore.create_repository()` and `get_repository()` behavior
- **Parallel-safe**: no
- **Tasks**:
  - test: Update `test_resolve_from_nested_subdir` so `ctx.workspace_root` equals the
    registered repo root and `ctx.requested_path` equals the nested request path.
  - test: Add a resolver test proving a file path inside a repo returns the repo root as
    `workspace_root` and preserves the file path in `requested_path`.
  - test: Add SQLite helper tests where the repository row id is not `1`, and the helper
    returns the correct row by registered path without creating duplicates.
  - test: Keep unsupported-worktree and unregistered-path resolver behavior unchanged:
    both return `None` from `resolve()` and readiness still carries diagnostics.
  - impl: Extend `RepoContext` with an optional `requested_path` field while preserving
    existing test fixture construction through a default value.
  - impl: Change `RepoResolver.resolve()` to set `workspace_root=Path(info.path).resolve()`
    and `requested_path=path.resolve()`.
  - impl: Add the SQLite repository-row helper using structured `repositories` table
    operations instead of ad hoc SQL in dispatcher code.
  - verify: `uv run pytest tests/test_repo_resolver.py tests/test_sqlite_store.py tests/test_persistence.py -v --no-cov`

### SL-1 - Dispatcher Mutation, Graph, And Cache Isolation

- **Scope**: Remove process-global mutation assumptions from `EnhancedDispatcher` and
  make graph/cache behavior repo-scoped or explicitly unavailable.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`,
  `tests/test_dispatcher.py`, `tests/test_dispatcher_advanced.py`,
  `tests/test_dispatcher_p3_integration.py`, `tests/test_rename_atomicity.py`,
  `tests/test_hot_path_histograms.py`
- **Interfaces provided**: `EnhancedDispatcher._sqlite_repository_id(ctx) -> int`;
  no `repository_id=1` in `remove_file()` / `move_file()`; registered-repo semantic lookup
  does not fall back to process-global Qdrant; `get_runtime_feature_status(ctx) -> dict`;
  `evict_repository_state(repo_id, repo_root=None) -> dict`; repo-scoped graph cache or
  explicit graph unavailable status; IF-0-P32-1, IF-0-P32-3, IF-0-P32-5, and the
  dispatcher side of IF-0-P32-6
- **Interfaces consumed**: SL-0 SQLite row helper and `RepoContext.requested_path`;
  existing `PluginSetRegistry.plugins_for(ctx.repo_id)`; existing
  `SemanticIndexerRegistry.get(ctx.repo_id)`; existing `two_phase_commit()` rollback
  behavior
- **Parallel-safe**: no
- **Tasks**:
  - test: Add dispatcher mutation tests with a SQLite store whose correct repository row
    id is not `1`; assert `remove_file(ctx, path)` deletes only that repo's row.
  - test: Update rename atomicity tests so `move_file()` uses the row returned by the
    SQLite helper and rollback also targets the same row.
  - test: Add a regression test that two repos with same relative filename do not delete
    or move each other's SQLite records.
  - test: Add semantic tests proving registered repo calls return `None` or unavailable
    status when `SemanticIndexerRegistry.get(repo_id)` fails, without using the fallback
    indexer.
  - test: Add graph tests proving one repo's initialized graph is not visible to another
    repo, or that graph methods return explicit unavailable status when repo-scoped graph
    state is not implemented.
  - test: Add eviction tests proving `evict_repository_state(repo_id, repo_root)` clears
    only cache entries under that repo and leaves other repo cache entries intact.
  - impl: Replace hard-coded SQLite repository ids in `remove_file()`, `move_file()`, and
    move rollback with the SL-0 helper.
  - impl: Make `_get_semantic_indexer(ctx)` distinguish registered-repo unavailable from
    legacy local fallback; restrict fallback to explicitly local/non-registered contexts.
  - impl: Replace process-global graph fields with per-repo graph state keyed by
    `ctx.repo_id`, or disable graph methods for registered repos with an explicit
    unavailable result and status.
  - impl: Add dispatcher runtime feature status and eviction methods for status and
    unregister lanes to consume.
  - verify: `uv run pytest tests/test_dispatcher.py tests/test_dispatcher_advanced.py tests/test_dispatcher_p3_integration.py tests/test_rename_atomicity.py tests/test_hot_path_histograms.py -v --no-cov`

### SL-2 - Semantic Registry Bootstrap And Lifecycle

- **Scope**: Wire per-repo semantic indexers through normal server bootstrap and add a
  lifecycle API for semantic cache eviction.
- **Owned files**: `mcp_server/utils/semantic_indexer_registry.py`,
  `mcp_server/cli/bootstrap.py`, `mcp_server/cli/stdio_runner.py`,
  `tests/test_semantic_indexer_registry.py`, `tests/test_bootstrap.py`,
  `tests/test_multi_repo_bootstrap_order.py`, `tests/test_singleton_reset.py`
- **Interfaces provided**: `SemanticIndexerRegistry.get(repo_id)` constructs from
  `RepositoryInfo.index_location` or an explicitly documented per-repo semantic path;
  `SemanticIndexerRegistry.evict(repo_id) -> bool`; bootstrap-created
  `EnhancedDispatcher(semantic_indexer_registry=...)` when semantic runtime is enabled;
  semantic unavailable status when disabled/preflight fails; IF-0-P32-4 and the semantic
  side of IF-0-P32-6
- **Interfaces consumed**: SL-0 repo root/path contract; existing
  `RepositoryInfo.index_location`, `current_commit`, and `tracked_branch`;
  `Settings.semantic_search_enabled` and existing semantic preflight behavior
- **Parallel-safe**: yes
- **Tasks**:
  - test: Extend `test_semantic_indexer_registry.py` so per-repo indexers use distinct
    per-repo storage/collection identity derived from repository metadata, not `:memory:`
    or process-global `QDRANT_PATH`.
  - test: Add `evict(repo_id)` tests proving the target indexer is closed and rebuilt on
    next `get()`, while other repo indexers remain cached.
  - test: Add bootstrap tests asserting `initialize_stateless_services()` injects a
    `SemanticIndexerRegistry` into `EnhancedDispatcher` when semantic search is enabled.
  - test: Add bootstrap tests for semantic-disabled/preflight-failed mode proving the
    dispatcher reports semantic unavailable instead of constructing a global fallback for
    registered repos.
  - test: Add STDIO runner wiring coverage where the stateless boot path preserves the
    same repository registry for resolver, store registry, semantic registry, dispatcher,
    watcher, and index manager.
  - impl: Add `SemanticIndexerRegistry.evict(repo_id)` and make `shutdown()` reuse the
    same close path.
  - impl: Change registry construction to use repo-scoped Qdrant/semantic paths under
    `RepositoryInfo.index_location`, with deterministic branch/profile collection names.
  - impl: Update `initialize_stateless_services()` and STDIO initialization to pass the
    semantic registry into `EnhancedDispatcher` when semantic runtime is enabled.
  - impl: Preserve legacy local single-repo startup behavior only when no repository
    registry/resolver is active.
  - verify: `uv run pytest tests/test_semantic_indexer_registry.py tests/test_bootstrap.py tests/test_multi_repo_bootstrap_order.py tests/test_singleton_reset.py -v --no-cov`

### SL-3 - Status And Cross-Repo Feature Reporting

- **Scope**: Make status surfaces report per-repo runtime readiness and feature
  availability instead of only process-global booleans.
- **Owned files**: `mcp_server/cli/tool_handlers.py`, `mcp_server/gateway.py`,
  `mcp_server/health/repo_status.py`, `mcp_server/dispatcher/cross_repo_coordinator.py`,
  `tests/test_tool_handlers_readiness.py`, `tests/test_p24_list_plugins_status.py`,
  `tests/test_gateway.py`, `tests/test_cross_repo_coordinator.py`
- **Interfaces provided**: repository health rows include `features.lexical`,
  `features.semantic`, `features.graph`, `features.plugins`, and `features.cross_repo`;
  FastAPI `/status`, `/search/capabilities`, `/graph/status`, and STDIO `get_status`
  expose the same feature status vocabulary; cross-repo statistics include
  `repository_details[*].readiness` and `feature_availability`; IF-0-P32-7
- **Interfaces consumed**: SL-1 `get_runtime_feature_status(ctx)` or unavailable fallback;
  SL-2 semantic unavailable reasons; P27 `build_health_row()` readiness vocabulary;
  existing FastAPI `get_repo_ctx(request)` resolution behavior
- **Parallel-safe**: yes
- **Tasks**:
  - test: Extend STDIO `get_status` tests so every repository row includes readiness and
    per-feature statuses, including semantic unavailable and graph unavailable reasons.
  - test: Fix the current `semantic_indexer_active` status check to reflect
    `_semantic_registry`/runtime feature status instead of the stale `_semantic_indexer`
    attribute.
  - test: Add FastAPI `/status` tests for two registered repos with different readiness
    and semantic availability; assert process-global search capabilities do not hide
    per-repo unavailability.
  - test: Add `/graph/status` tests proving unavailable graph support returns an explicit
    status/reason and does not imply an empty initialized graph.
  - test: Extend cross-repo coordinator statistics tests so each repository detail
    includes readiness and feature availability, and unavailable repos are visible in
    status even when not searched.
  - impl: Extend `build_health_row()` to merge dispatcher/runtime feature availability
    when provided, while keeping existing readiness fields stable.
  - impl: Update STDIO `handle_get_status()` and FastAPI status/capability endpoints to
    build feature rows from resolved repo contexts when possible and from registry
    metadata otherwise.
  - impl: Update cross-repo statistics to include readiness and feature availability
    fields without changing existing count totals.
  - verify: `uv run pytest tests/test_tool_handlers_readiness.py tests/test_p24_list_plugins_status.py tests/test_gateway.py tests/test_cross_repo_coordinator.py -v --no-cov`

### SL-4 - Repository Unregister/Remove Eviction Wiring

- **Scope**: Ensure every repository removal path evicts runtime state for that repo and
  leaves unrelated repositories untouched.
- **Owned files**: `mcp_server/storage/store_registry.py`,
  `mcp_server/watcher_multi_repo.py`, `mcp_server/cli/repository_commands.py`,
  `tests/test_watcher_multi_repo.py`, `tests/test_repository_commands.py`,
  `tests/test_repository_management.py`
- **Interfaces provided**: unregister/remove calls `StoreRegistry.close(repo_id)`,
  `SemanticIndexerRegistry.evict(repo_id)`, `PluginSetRegistry.evict(repo_id)`, and
  `EnhancedDispatcher.evict_repository_state(repo_id, repo_root)` when those components
  are available; IF-0-P32-6 end-to-end evidence
- **Interfaces consumed**: SL-1 dispatcher eviction API; SL-2 semantic eviction API;
  existing `PluginSetRegistry.evict(repo_id)`; existing `StoreRegistry.close(repo_id)`;
  `RepositoryRegistry.unregister_repository(repo_id)`
- **Parallel-safe**: yes
- **Tasks**:
  - test: Add watcher `remove_repository()` tests proving observer shutdown, store close,
    plugin eviction, semantic eviction, and dispatcher cache eviction are called for the
    target repo only.
  - test: Add repository CLI unregister tests proving runtime eviction hooks run before
    or with registry removal and that missing repo ids remain no-ops with clear output.
  - test: Add store registry tests proving `close(repo_id)` also clears any per-key build
    lock or stale construction state that would keep removed repo state alive.
  - test: Add management tests for two repos where unregistering repo A does not evict
    repo B's store/plugin/semantic state.
  - impl: Thread optional `store_registry`, `plugin_set_registry`, and
    `semantic_indexer_registry` references into watcher/removal paths, or expose a single
    runtime cleanup callback from bootstrap to keep constructor churn small.
  - impl: Call dispatcher and registry eviction hooks with the repo id and registered
    repo root before dropping the registry entry when root/path data is still available.
  - impl: Preserve current observer stop/join behavior and avoid changing branch-drift or
    artifact-publish behavior owned by P30/P31.
  - verify: `uv run pytest tests/test_watcher_multi_repo.py tests/test_repository_commands.py tests/test_repository_management.py -v --no-cov`

### SL-5 - P32 Contract Audit And Docs Decision

- **Scope**: Run the reducer checks, confirm all P32 runtime surfaces either scope state
  by repo or report unavailable, and record whether docs need a follow-up in P34.
- **Owned files**: (none)
- **Interfaces provided**: completed IF-0-P32-1 through IF-0-P32-7 evidence for P33
- **Interfaces consumed**: SL-0 root/SQLite helper; SL-1 dispatcher runtime status and
  eviction behavior; SL-2 semantic registry lifecycle; SL-3 status payloads; SL-4
  unregister/remove eviction; roadmap exit criteria from `specs/phase-plans-v3.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Run all P32 targeted tests after implementation lanes land.
  - verify: `uv run pytest tests/test_dispatcher.py tests/test_dispatcher_p3_integration.py tests/test_semantic_indexer_registry.py -v --no-cov`
  - verify: `uv run pytest tests/test_repo_resolver.py tests/test_sqlite_store.py tests/test_rename_atomicity.py tests/test_tool_handlers_readiness.py tests/test_gateway.py tests/test_cross_repo_coordinator.py tests/test_watcher_multi_repo.py tests/test_repository_commands.py -v --no-cov`
  - verify: `rg -n "repository_id\\s*=\\s*1|_semantic_indexer\\b|QDRANT_PATH|_graph_nodes|_graph_edges|_context_selector|_graph_analyzer|workspace_root == nested|workspace_root\\s*=\\s*path" mcp_server tests`
  - verify: `rg -n "semantic_indexer_active|graph_initialized|feature_availability|runtime_feature" mcp_server tests`
  - impl: Review grep results and document every remaining process-global reference as
    either legacy local-mode only, intentionally unavailable for registered repos, or a
    follow-up blocker for P33.
  - impl: Record docs decision in the phase handoff: P32 is primarily runtime cleanup;
    P34 owns public docs, but P32 must pass feature-status vocabulary to P33/P34.

## Verification

```bash
uv run pytest tests/test_repo_resolver.py tests/test_sqlite_store.py tests/test_persistence.py -v --no-cov
uv run pytest tests/test_dispatcher.py tests/test_dispatcher_advanced.py tests/test_dispatcher_p3_integration.py tests/test_rename_atomicity.py tests/test_hot_path_histograms.py -v --no-cov
uv run pytest tests/test_semantic_indexer_registry.py tests/test_bootstrap.py tests/test_multi_repo_bootstrap_order.py tests/test_singleton_reset.py -v --no-cov
uv run pytest tests/test_tool_handlers_readiness.py tests/test_p24_list_plugins_status.py tests/test_gateway.py tests/test_cross_repo_coordinator.py -v --no-cov
uv run pytest tests/test_watcher_multi_repo.py tests/test_repository_commands.py tests/test_repository_management.py -v --no-cov
uv run pytest tests/test_dispatcher.py tests/test_dispatcher_p3_integration.py tests/test_semantic_indexer_registry.py -v --no-cov
rg -n "repository_id\\s*=\\s*1|_semantic_indexer\\b|QDRANT_PATH|_graph_nodes|_graph_edges|_context_selector|_graph_analyzer|workspace_root == nested|workspace_root\\s*=\\s*path" mcp_server tests
rg -n "semantic_indexer_active|graph_initialized|feature_availability|runtime_feature" mcp_server tests
```

Whole-phase regression recommended before P33:

```bash
uv run pytest tests/test_repository_readiness.py tests/test_tool_readiness_fail_closed.py tests/test_git_index_manager.py tests/test_git_integration.py tests/test_incremental_indexer.py tests/test_dispatcher.py tests/test_dispatcher_p3_integration.py tests/test_semantic_indexer_registry.py -v --no-cov
```

## Acceptance Criteria

- [ ] `remove_file` and `move_file` resolve the correct SQLite repository row instead of
      hard-coding `repository_id=1`, including rollback paths.
- [ ] `RepoResolver` returns the registered repository root as `workspace_root` for ctx
      mutation paths and preserves the original requested path in `requested_path` for
      diagnostics.
- [ ] `SemanticIndexerRegistry` is wired through normal STDIO/bootstrap and FastAPI
      startup when semantic search is enabled, or semantic search reports unavailable per
      repo with a reason.
- [ ] Registered repos never use a process-global semantic fallback or graph state from a
      different repo.
- [ ] Graph search/context features are repo-scoped or disabled with explicit status.
- [ ] Plugin, semantic, graph, SQLite, and dispatcher file-cache state is evicted on
      repository unregister/remove and does not bleed mutable state between repos.
- [ ] Cross-repo search status clearly reports which repos are ready and which features
      are unavailable.
- [ ] P32 reducer greps have no unexplained hard-coded repository ids, stale semantic
      status checks, or unscoped graph state in registered-repo paths.
