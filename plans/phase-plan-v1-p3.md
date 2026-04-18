# PHASE-3-per-repo-plugins-stores-memory: Phase 3 — Per-Repo Plugins, Stores & Memory

> Plan doc produced by `/plan-phase P3 --consensus` against `specs/phase-plans-v1.md` lines 252–290. On approval, saved to `plans/phase-plan-v1-p3.md` and handed off to `/execute-phase p3`.

## Context

P1 + P2A + P2B + P6A are merged. Post-P2B the dispatcher takes `ctx: RepoContext` on every public method and routes storage through `ctx.sqlite_store`. But the non-sqlite global state (`_plugins`, `_semantic_indexer`, `_reranker`, `_file_cache`, `_graph_*`) is still dispatcher-instance-global. P3 extracts plugins + semantic indexer + memory accounting into per-repo registries, finishes the per-repo serving story for query/index paths, and freezes `IF-0-P3-1` (PluginSetRegistry) that P4 (watcher) consumes on repo-removal events.

### What exists

**Plugin lifecycle:**
- `mcp_server/plugins/memory_aware_manager.py` (387 LOC). `psutil` imported optionally (L19-22); `_process = psutil.Process()` at L95; `_get_current_memory()` at L254-258 already calls `psutil.Process().memory_info().rss` — but eviction at `_ensure_memory_available()` L179-205 uses sum of tracked `PluginMemoryInfo.memory_bytes` (L189) instead of real RSS. psutil-unavailable path logs a warning and silently returns 0 at L257. Thread-safe via `threading.RLock` (L84). Singleton at L346-350 via `get_memory_aware_manager()`.
- `mcp_server/plugins/repository_plugin_loader.py` (517 LOC). `_profiles: Dict[str, RepositoryProfile]` at L72 keyed by repo_id. **No thread-safety** — concurrent `analyze_repository()` L158-211 will race on L175, 202. Read/write call-sites: L175, 202 (write), L279, 299, 360, 364 (read).
- `mcp_server/plugins/plugin_factory.py` (285 LOC). `create_plugin()` L146-192, `get_plugin()` alias L195-211, `create_all_plugins()` L266-284. **Synchronous construction**, blocks the event loop when cold.
- `mcp_server/plugin_system/loader.py:38` already has `ThreadPoolExecutor(max_workers=4)` — reusable for async warming.
- `mcp_server/dispatcher/dispatcher_enhanced.py` imports memory_aware_manager (L30), RepositoryPluginLoader (L32), PluginFactory (L31). `_repo_plugin_loader=None` (L183), `_memory_manager=None` (L184), lazy. `_load_all_plugins()` at L333 synchronous with a signal-based timeout.

**Plugin-level stores:**
- Post-P2B, the dispatcher calls `PluginFactory.create_plugin(..., sqlite_store=None, ...)` (L378, L392, L443). Plugins store `None` in `self._sqlite_store` — the attribute is vestigial for most plugins.
- In-scope per spec:
  - `mcp_server/plugins/js_plugin/plugin.py:49` holds None; uses at L64-67, 128-141, 239-246, 248-252, 322-329, 358-365 route through SQLiteStore methods (no raw SQL).
  - `mcp_server/plugins/bm25_adapter_plugin.py:33,34` captures the store AND `sqlite_store.db_path`. L50, L127 open fresh raw `sqlite3.connect(self._db_path)` for FTS5 queries — bypasses the store wrapper entirely. This is the only plugin that meaningfully uses the per-plugin store.
  - `mcp_server/plugins/plugin_base_enhanced.py:50` captures the store but doesn't use it.
- 7 other language plugins (`python`, `cpp`, `dart`, `c`, `typescript`, `html_css`, `simple_text`) follow the same vestigial pattern — per the spec these are checked but only patched if found meaningfully coupled (they aren't).
- `IPlugin` at `mcp_server/plugin_base.py:80-101` — 5 abstract methods, no `ctx` in signature. No existing fixtures mock `_sqlite_store`.

**Semantic indexer:**
- `mcp_server/utils/semantic_indexer.py` (1200+ LOC). Constructor at L107-121 **already accepts** `repo_identifier`, `branch`, `commit`, `lineage_id` — P3 does not need to change the signature.
- `_resolve_collection_name` at L206-230 already delegates to `namespace_resolver.resolve_collection_name()` when `repo_identifier` is present.
- `mcp_server/artifacts/semantic_namespace.py:45-55` — `resolve_collection_name(repo_identifier, profile_id, lineage_id)` returns `ci__<12-hex-repo-hash>__<profile>__<lineage>`. Already produces per-repo collection names.
- Dispatcher constructs `_semantic_indexer` as a singleton at `dispatcher_enhanced.py:~950` without threading `repo_identifier` — the per-repo wiring is the missing step.
- No existing multi-repo integration test for semantic search.

**Readiness (P2A artifacts, ready to consume):**
- `RepoContext` (`mcp_server/core/repo_context.py`): frozen dataclass with `repo_id`, `sqlite_store`, `workspace_root`, `tracked_branch`, `registry_entry`.
- `StoreRegistry` (`mcp_server/storage/store_registry.py:37-74`): per-key `_build_locks` + double-check pattern — canonical template for P3's new registries.
- `RepoResolver` (`mcp_server/core/repo_resolver.py:38-60`) returns `RepoContext` per path.

### Why an SL-0 preamble

Without freezing `PluginSetRegistry` / `SemanticIndexerRegistry` Protocols + the `IPlugin.bind(ctx)` method and `_profiles_lock` attribute up front, five lanes (SL-1, SL-2, SL-3, SL-4, SL-5) would race to create the same files. The P2B SL-0 model worked — same model here.

## Interface Freeze Gates

- [ ] **IF-0-P3-1** — `PluginSetRegistry` Protocol (new file `mcp_server/plugins/plugin_set_registry.py`). Public surface: `plugins_for(repo_id: str) -> list[IPlugin]`, `plugins_for_file(ctx: RepoContext, path: Path) -> list[tuple[IPlugin, float]]`, `evict(repo_id: str) -> None`. **Unblocks P4** (watcher calls `evict(repo_id)` on repo-removal and `invalidate` on default-branch advancement).
- [ ] **IF-0-P3-2** — `SemanticIndexerRegistry` Protocol (new file `mcp_server/utils/semantic_indexer_registry.py`). Public surface: `get(repo_id: str) -> SemanticIndexer`, `shutdown() -> None`. Per-spec signature (`repo_id`, not `ctx`).
- [ ] **IF-0-P3-3** — `IPlugin.bind(ctx: RepoContext) -> None` — additive method on the existing `IPlugin` ABC at `mcp_server/plugin_base.py:80-101` with a default no-op body. Plugins that need repo state override it; existing plugins inherit the no-op. **No constructor change** — preserves the ~30 fixture sites that pass `Plugin()` with no args.
- [ ] **IF-0-P3-4** — `MemoryAwarePluginManager` public surface: `get_plugin(language: str, ctx: RepoContext | None = None) -> IPlugin | None`, `get_memory_status() -> dict`, `clear_cache() -> None`, `preload_high_priority(ctx: RepoContext) -> None`. Default arg on `ctx` preserves the one non-test caller at `repository_plugin_loader.py:69`.
- [ ] **IF-0-P3-5** — Factory post-construction hook: `PluginFactory.create_plugin(language, ctx: RepoContext | None = None, ...)` calls `plugin.bind(ctx)` before returning iff ctx is provided. Lets SL-3 rewrite factory internals without breaking SL-5's bind expectations.

## Lane Index & Dependencies

```
SL-1 — PluginSetRegistry + MemoryAwarePluginManager fixes
  Depends on: (none)
  Blocks: SL-6
  Parallel-safe: yes

SL-2 — RepositoryPluginLoader concurrency hardening
  Depends on: (none)
  Blocks: (none)
  Parallel-safe: yes

SL-3 — PluginFactory async construction
  Depends on: (none)
  Blocks: SL-6
  Parallel-safe: yes

SL-4 — SemanticIndexerRegistry + narrow multi-repo test
  Depends on: (none)
  Blocks: SL-6
  Parallel-safe: yes

SL-5 — Plugin-level store refactor via bind(ctx)
  Depends on: (none)
  Blocks: (none)
  Parallel-safe: yes

SL-6 — Dispatcher integration (serialized tail)
  Depends on: SL-1, SL-3, SL-4
  Blocks: (none)
  Parallel-safe: no (solo writer of dispatcher_enhanced.py)
```

DAG is acyclic. All five of SL-1/SL-2/SL-3/SL-4/SL-5 branch from the SL-0 preamble commit and dispatch in parallel. SL-6 serializes at the tail — it's the sole writer of `mcp_server/dispatcher/dispatcher_enhanced.py` after P2B and must see the post-SL-1/SL-3/SL-4 state. SL-2 and SL-5 land independently.

## Lanes

### SL-0 — Protocol freeze (preamble commit, orchestrator-authored)

Landed as a single commit on `main` BEFORE `/execute-phase p3` dispatches. Not a swim lane; not emitted as TaskCreate. Produces:

- `mcp_server/plugins/plugin_set_registry.py` (NEW stub, ~50 LOC): `PluginSetRegistry` Protocol + a trivial stub implementation whose methods raise `NotImplementedError`. SL-1 replaces the stub with a real impl.
- `mcp_server/utils/semantic_indexer_registry.py` (NEW stub, ~40 LOC): `SemanticIndexerRegistry` Protocol + stub. SL-4 replaces.
- `mcp_server/plugin_base.py` edit: add `bind(self, ctx: RepoContext) -> None` method to `IPlugin` ABC with `pass` body. Import `RepoContext` under `TYPE_CHECKING` to avoid a top-level cycle.
- `mcp_server/plugins/plugin_factory.py` edit: in `create_plugin()`, accept a new keyword-only `ctx: RepoContext | None = None` arg and, after successful construction, call `plugin.bind(ctx)` iff `ctx is not None`. Existing callers (which pass no ctx) see identical behavior.
- `mcp_server/plugins/repository_plugin_loader.py` edit: add `self._profiles_lock = threading.Lock()` to `__init__` (unused by SL-0; SL-2 starts wrapping reads/writes).
- `mcp_server/plugins/__init__.py` re-exports `PluginSetRegistry`. `mcp_server/utils/__init__.py` re-exports `SemanticIndexerRegistry`.

Scaffolding commit compiles + the existing P2B+P6A test suite still passes.

### SL-1 — PluginSetRegistry + MemoryAwarePluginManager fixes

- **Scope**: Implement `PluginSetRegistry` (swap out SL-0 stub). Fix `MemoryAwarePluginManager` to (a) raise `RuntimeError` at `__init__` if `psutil` is unavailable — no silent no-op, (b) use `psutil.Process().memory_info().rss` (not tracked `PluginMemoryInfo.memory_bytes`) for the eviction trigger at `_ensure_memory_available()`. Keep per-plugin `memory_bytes` for attribution/telemetry. Re-key the manager's plugin cache by `(repo_id, language)` so `get_plugin(language, ctx)` returns per-repo instances. `PluginSetRegistry.plugins_for(repo_id)` composes over `MemoryAwarePluginManager`.
- **Owned files**: `mcp_server/plugins/plugin_set_registry.py`, `mcp_server/plugins/memory_aware_manager.py`, `mcp_server/plugins/__init__.py` (re-export), `tests/test_plugin_set_registry.py` (NEW), `tests/test_memory_aware_manager.py` (extend).
- **Interfaces provided**: IF-0-P3-1 impl, IF-0-P3-4 impl.
- **Interfaces consumed**: `RepoContext` (pre-existing), `IPlugin` (pre-existing), `IPlugin.bind()` (pre-existing from SL-0).
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-1.1 | test | — | `tests/test_plugin_set_registry.py` (NEW), `tests/test_memory_aware_manager.py` (extend) | `PluginSetRegistry.plugins_for(repo_id)` returns a stable list across calls; `evict(repo_id)` clears that repo's cache without affecting other repos; `MemoryAwarePluginManager()` raises `RuntimeError` when psutil is unavailable (stub via monkeypatch); eviction trigger uses `psutil.Process().memory_info().rss` not tracked estimates (verify via a `process.memory_info()` mock that reports above-limit while tracked estimates report below); `get_plugin("python", ctx_a)` and `get_plugin("python", ctx_b)` return distinct instances for different `repo_id`s | `uv run pytest tests/test_plugin_set_registry.py tests/test_memory_aware_manager.py -v` |
| SL-1.2 | impl | SL-1.1 | SL-1 owned files | — | — |
| SL-1.3 | verify | SL-1.2 | SL-1 owned files | all SL-1 tests + existing plugin/memory tests | `uv run pytest tests/test_plugin_set_registry.py tests/test_memory_aware_manager.py -v` |

### SL-2 — RepositoryPluginLoader concurrency hardening

- **Scope**: Replace class-level locking with a per-`repo_id` `threading.Lock` dict (copy the `StoreRegistry._build_locks` double-check pattern from `mcp_server/storage/store_registry.py:37-74`). Wrap `_profiles` reads and writes under the lock. Stress test: 8 threads × 100 iterations of `analyze_repository(repo_id)` for identical repo_ids produces one cached `RepositoryProfile` (verified via `id()` equality).
- **Owned files**: `mcp_server/plugins/repository_plugin_loader.py`, `tests/test_repository_plugin_loader_concurrency.py` (NEW).
- **Interfaces provided**: none new (internal hardening).
- **Interfaces consumed**: `RepositoryProfile` (pre-existing), `_profiles_lock` (pre-existing from SL-0).
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-2.1 | test | — | `tests/test_repository_plugin_loader_concurrency.py` (NEW) | 8 threads × 100 iterations of `analyze_repository` for the same repo_id all return the same `RepositoryProfile` instance (`id()` equality); two different repo_ids analyzed concurrently do not block each other (measure wall-clock: 2× parallel analysis < 1.8× serial) | `uv run pytest tests/test_repository_plugin_loader_concurrency.py -v` |
| SL-2.2 | impl | SL-2.1 | `mcp_server/plugins/repository_plugin_loader.py` | — | — |
| SL-2.3 | verify | SL-2.2 | SL-2 owned files | all SL-2 tests | `uv run pytest tests/test_repository_plugin_loader_concurrency.py -v` |

### SL-3 — PluginFactory async construction

- **Scope**: Add `PluginFactory.create_plugin_async(language, ctx, ...) -> asyncio.Future[IPlugin]` that wraps the existing synchronous path in the existing `ThreadPoolExecutor(4)` at `plugin_system/loader.py:38`. Keep the sync `create_plugin` for backward compat. Post-construction `plugin.bind(ctx)` call (from SL-0) is preserved through the async pathway. Plugin cold-start runs in the thread pool; tool calls that hit a missing plugin either await the future (if already warming) or schedule a warm + return a lightweight "plugin warming up" sentinel. No raw event-loop blocking.
- **Owned files**: `mcp_server/plugins/plugin_factory.py`, `mcp_server/plugin_system/loader.py`, `tests/test_plugin_factory_async.py` (NEW).
- **Interfaces provided**: `create_plugin_async` (method on existing `PluginFactory`).
- **Interfaces consumed**: existing `ThreadPoolExecutor(4)`, `IPlugin.bind()`.
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-3.1 | test | — | `tests/test_plugin_factory_async.py` (NEW) | `await create_plugin_async("python", ctx)` returns a bound `IPlugin` (`plugin.bind` was called with ctx); awaiting the same (language, repo_id) twice returns the same instance without double-building; a dummy slow plugin (0.2s sleep in its ctor) does not block the event loop (measured via `asyncio.wait_for` with a 0.05s poll on an unrelated coroutine that must complete) | `uv run pytest tests/test_plugin_factory_async.py -v` |
| SL-3.2 | impl | SL-3.1 | SL-3 owned files | — | — |
| SL-3.3 | verify | SL-3.2 | SL-3 owned files | all SL-3 tests | `uv run pytest tests/test_plugin_factory_async.py -v` |

### SL-4 — SemanticIndexerRegistry + narrow multi-repo test

- **Scope**: Implement `SemanticIndexerRegistry` (swap out SL-0 stub). `get(repo_id: str) -> SemanticIndexer` constructs a `SemanticIndexer(repo_identifier=repo_id, branch=..., commit=..., ...)` using existing ctor support at L107-121; caches per `repo_id`. Call `_resolve_collection_name` → `namespace_resolver.resolve_collection_name(repo_identifier=repo_id, profile_id=..., lineage_id=...)` → per-repo collection. No edits to `SemanticIndexer` body. Ship narrow integration test: two mocked Qdrant clients, two `repo_id`s, verify two distinct collection names are created. Full end-to-end integration is P5.
- **Owned files**: `mcp_server/utils/semantic_indexer_registry.py`, `mcp_server/utils/__init__.py` (re-export), `tests/test_semantic_indexer_registry.py` (NEW). Dispatcher rewire lives in SL-6.
- **Interfaces provided**: IF-0-P3-2 impl.
- **Interfaces consumed**: `SemanticIndexer` (pre-existing), `namespace_resolver.resolve_collection_name` (pre-existing), `RepositoryRegistry` entries for branch/commit lookup (pre-existing).
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-4.1 | test | — | `tests/test_semantic_indexer_registry.py` (NEW) | `registry.get("repo-a").collection_name != registry.get("repo-b").collection_name`; both match `ci__<hash>__<profile>__<lineage>` format; `registry.get("repo-a")` twice returns the same instance; `shutdown()` closes all cached indexers | `uv run pytest tests/test_semantic_indexer_registry.py -v` |
| SL-4.2 | impl | SL-4.1 | SL-4 owned files | — | — |
| SL-4.3 | verify | SL-4.2 | SL-4 owned files | all SL-4 tests | `uv run pytest tests/test_semantic_indexer_registry.py -v` |

### SL-5 — Plugin-level store refactor via bind(ctx)

- **Scope**: Update the 3 in-scope plugins to consume `ctx.sqlite_store` via the `bind(ctx)` method (overriding IPlugin's no-op default) instead of ctor-captured `sqlite_store`. `bm25_adapter_plugin.py` gets particular attention: its raw `sqlite3.connect(self._db_path)` calls at L50/L127 route through `ctx.sqlite_store.db_path`. Remove the vestigial `self._sqlite_store = sqlite_store` assignments in `js_plugin/plugin.py:49`, `bm25_adapter_plugin.py:33`, `plugin_base_enhanced.py:50`. Patched plugins declare `bind(ctx)` that sets `self._ctx = ctx`; store accesses go through `self._ctx.sqlite_store`. Tests extend to verify bind is called and the plugin uses ctx.sqlite_store.
- **Owned files**: `mcp_server/plugins/js_plugin/plugin.py`, `mcp_server/plugins/js_plugin/plugin_semantic.py` (if present), `mcp_server/plugins/bm25_adapter_plugin.py`, `mcp_server/plugins/plugin_base_enhanced.py`, `tests/test_bm25_adapter_plugin.py` (NEW or extend). If the discovery sweep finds any other plugin meaningfully using `_sqlite_store` (today none do), patch it here.
- **Interfaces provided**: none new (conforms to IF-0-P3-3).
- **Interfaces consumed**: `IPlugin.bind()`, `RepoContext.sqlite_store`.
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-5.1 | test | — | `tests/test_bm25_adapter_plugin.py` (NEW or extend) | After factory constructs `bm25_adapter_plugin` and calls `bind(ctx)`, the plugin's FTS5 query opens `sqlite3.connect(ctx.sqlite_store.db_path)` — verify via a spy/mock on `sqlite3.connect`; `js_plugin` and `plugin_base_enhanced` store no `_sqlite_store` attribute post-bind; `grep -n '_sqlite_store' mcp_server/plugins/{js_plugin,bm25_adapter_plugin,plugin_base_enhanced}*.py` returns zero lines | `uv run pytest tests/test_bm25_adapter_plugin.py -v` |
| SL-5.2 | impl | SL-5.1 | SL-5 owned files | — | — |
| SL-5.3 | verify | SL-5.2 | SL-5 owned files | all SL-5 tests + existing plugin test subset | `uv run pytest tests/test_bm25_adapter_plugin.py tests/root_tests/test_python_plugin.py -v` |

### SL-6 — Dispatcher integration (serialized tail)

- **Scope**: Rewire `EnhancedDispatcher` to consume the new registries. Replace `self._plugins`/`self._by_lang` dispatcher-global plugin state with a `PluginSetRegistry` injected at ctor time; every call site that previously read `self._plugins` or the memory manager now goes through `self._plugin_set_registry.plugins_for(ctx.repo_id)` or `plugins_for_file(ctx, path)`. Replace the singleton `self._semantic_indexer` construction at ~L950 with a `SemanticIndexerRegistry` reference; every search/index method that currently uses `self._semantic_indexer` calls `self._semantic_registry.get(ctx.repo_id)` at method entry. Keep `_reranker`, `_file_cache`, `_graph_*` process-global for this phase (they're P4/P5 territory).
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `tests/test_dispatcher_p3_integration.py` (NEW).
- **Interfaces provided**: none new (consumer).
- **Interfaces consumed**: IF-0-P3-1 (`PluginSetRegistry`), IF-0-P3-2 (`SemanticIndexerRegistry`), `PluginFactory.create_plugin_async` from SL-3.
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-6.1 | test | — | `tests/test_dispatcher_p3_integration.py` (NEW) | `EnhancedDispatcher()` accepts `plugin_set_registry` + `semantic_indexer_registry` kwargs; `dispatcher.search(ctx_a, "x")` and `dispatcher.search(ctx_b, "x")` route through the two registries (verified via mocks); `grep -cE 'self\._(plugins\b\|_by_lang\b\|_semantic_indexer\b)' mcp_server/dispatcher/dispatcher_enhanced.py` returns 0 (no more direct singleton access) | `uv run pytest tests/test_dispatcher_p3_integration.py -v` |
| SL-6.2 | impl | SL-6.1 | `mcp_server/dispatcher/dispatcher_enhanced.py` | — | — |
| SL-6.3 | verify | SL-6.2 | SL-6 owned files | all SL-6 + full dispatcher + gateway test subset | `uv run pytest tests/test_dispatcher.py tests/test_dispatcher_advanced.py tests/test_dispatcher_p3_integration.py tests/test_gateway.py -v` |

## Execution Notes

- **Single-writer files**:
  - `mcp_server/dispatcher/dispatcher_enhanced.py` — SL-6 only.
  - `mcp_server/plugins/plugin_set_registry.py` — SL-1 only (after SL-0 stubs it).
  - `mcp_server/utils/semantic_indexer_registry.py` — SL-4 only.
  - `mcp_server/plugins/plugin_factory.py` — SL-3 only (SL-0 touched it for the bind hook; SL-3 is the sole post-preamble writer). **Coordination**: SL-3's async rewrite MUST preserve the `plugin.bind(ctx)` post-construction call added by SL-0. If SL-3 accidentally drops it, SL-5's tests will fail. Lane brief calls this out explicitly.
  - `mcp_server/plugin_base.py` — SL-0 only (adds `bind()`); no lane edits it.
  - `mcp_server/plugins/repository_plugin_loader.py` — SL-0 adds the lock attr; SL-2 uses it.

- **SL-0 preamble sequencing**: the orchestrator authors SL-0 as a direct commit to main BEFORE invoking `/execute-phase p3`. Scaffolding commit (~250 LOC), no behavior change, existing tests still pass. Only after SL-0 lands does execute-phase dispatch the five parallel lanes.

- **Wave dispatch** (per `MAX_PARALLEL_LANES=2` execute-phase default): first wave SL-1 + SL-2; as those finish, dispatch SL-3 + SL-4 and then SL-5 in the next slots. When all five are merged, dispatch SL-6 (solo).

- **Known destructive changes** (stale-base whitelist — consumed by `pre_merge_destructiveness_check.sh`): **none in this phase**. Every lane is purely additive (new files) or in-place edits. SL-5 removes the vestigial `self._sqlite_store = sqlite_store` lines but the files stay. SL-6 removes `self._semantic_indexer` ctor block but file stays.

- **Stale-base guidance** (copy verbatim): Lane teammates working in isolated worktrees do not see sibling-lane merges automatically. If a lane finds its worktree base is pre-SL-0 preamble (`plugin_set_registry.py` / `semantic_indexer_registry.py` stubs absent, `IPlugin.bind()` method missing, `_profiles_lock` attribute missing) it MUST stop and report rather than committing — the orchestrator will re-spawn or rebase. Silent `git reset --hard` or `git checkout HEAD~N -- ...` in a stale worktree produces commits that destroy peer-lane work on `--no-ff` merge. P6 lost 3 of 10 lanes to exactly this pattern.

- **Harness preflight**: Before dispatch, orchestrator runs `bash ~/.claude/skills/execute-phase/scripts/verify_harness.sh`. All checks must pass.

- **Architectural choices (consensus outcome, `--consensus` round 1)**:
  - **SL-0 preamble, not a lane** (MAJORITY 2/3: arch-clean + arch-parallel): freezes + stubs land as orchestrator-authored commit. arch-minimal preferred no preamble; overruled because P2B's preamble model proved out and 5-way file collision risk is real.
  - **`bind(ctx)` method on `IPlugin` (default no-op), NOT a new `RepoAwarePlugin` subclass** (MAJORITY 2/3: arch-minimal + arch-parallel): simpler plumbing, no new ABC, no cascade into the 7 subclasses that don't need ctx. arch-clean dissented with a `RepoAwarePlugin(IPlugin)` subclass proposal — recorded as design tech debt to revisit if a richer interface becomes necessary.
  - **`SemanticIndexerRegistry.get(repo_id: str)`, NOT `.for_context(ctx: RepoContext)`** (SPEC-LITERAL): exit criterion 2 explicitly names `get(repo_id: str)`. arch-clean argued for `for_context(ctx)` (cleaner, matches P2B's DispatcherProtocol). Spec wins. If P4 wants ctx shape, it can derive `repo_id` from `ctx.repo_id` at the call site.
  - **Dedicated SL-6 serialized dispatcher tail** (arch-parallel alone, accepted by synthesis): P2B's line-range split on `pyproject.toml` was fragile; 5 lanes editing `dispatcher_enhanced.py` simultaneously would be worse. One serialized writer, post the five parallel registry/plugin lanes. arch-minimal folded dispatcher edits into per-lane line-range ownership; arch-clean allowed two lanes (SL-3 semantic + SL-4 plugins) to both touch dispatcher. Both rejected.
  - **Plugin-store refactor as ONE lane (SL-5), not per-file** (UNANIMOUS): `js_plugin`, `bm25_adapter_plugin`, and `plugin_base_enhanced` share the `bind()` pattern and cross-reference each other.
  - **Ship narrow integration test in SL-4** (arch-parallel): spec says "verified by integration test"; non-goals says "full multi-repo integration test is P5". Resolved with a narrow mocked-Qdrant two-collection assertion in SL-4, full end-to-end deferred to P5.
  - **Memory manager kept as singleton, cache re-keyed by `(repo_id, language)`** (UNANIMOUS): 17 call-sites reference `get_memory_aware_manager()`; changing the access pattern is out of scope. Singleton preserved, internal cache keyed differently.

- **Spec inaccuracies flagged for phase-plans v2**:
  1. Spec exit criterion 1 says "returns a stable, memory-managed list of plugins scoped to that repo" — doesn't specify how P4 invalidates on repo-removal. Plan adds `evict(repo_id)` as the invalidation hook. Spec v2 should name it.
  2. Spec exit criterion 2 says `SemanticIndexerRegistry.get(repo_id: str)` but the `SemanticIndexer` ctor also requires `branch` + `commit` to produce a deterministic collection name. The registry must look those up from `RepositoryRegistry`. Spec v2 should surface this dependency.

## Acceptance Criteria

- [ ] `.venv/bin/python -c "from mcp_server.plugins import PluginSetRegistry; r = PluginSetRegistry(); r.plugins_for('fake-repo-id')"` exits 0 (registry + its method importable + callable).
- [ ] `.venv/bin/python -c "from mcp_server.utils import SemanticIndexerRegistry; r = SemanticIndexerRegistry(); r.get('fake-repo-id')"` does not raise `NotImplementedError` after SL-4 (executes against a mocked Qdrant).
- [ ] Two distinct `repo_id` values passed to `SemanticIndexerRegistry.get` produce two `SemanticIndexer` instances whose `collection_name` differs (verified by `tests/test_semantic_indexer_registry.py`).
- [ ] `.venv/bin/python -c "import sys; sys.modules['psutil']=None; from mcp_server.plugins.memory_aware_manager import MemoryAwarePluginManager; MemoryAwarePluginManager()"` exits non-zero with a `RuntimeError` naming psutil.
- [ ] `MemoryAwarePluginManager._ensure_memory_available()` uses real `psutil.Process().memory_info().rss` (verified by mocking `process.memory_info` high while tracked estimates are low — eviction fires based on real RSS).
- [ ] Stress test: 8 threads × 100 iterations of `RepositoryPluginLoader.analyze_repository(repo_id)` for the same `repo_id` all return the same `RepositoryProfile` instance (`id()` equality), verified by `tests/test_repository_plugin_loader_concurrency.py`.
- [ ] `await PluginFactory.create_plugin_async("python", ctx)` returns a bound `IPlugin` without blocking the event loop (verified via an unrelated coroutine completing during the plugin's 0.2s synthetic cold start).
- [ ] `rg -n '_sqlite_store' mcp_server/plugins/js_plugin/plugin.py mcp_server/plugins/bm25_adapter_plugin.py mcp_server/plugins/plugin_base_enhanced.py` produces zero hits after SL-5.
- [ ] `rg -nE 'self\._(plugins\b|_by_lang\b|_semantic_indexer\b)' mcp_server/dispatcher/dispatcher_enhanced.py` produces zero hits after SL-6 (dispatcher no longer holds dispatcher-global plugin/semantic singletons).
- [ ] `uv run pytest tests/test_plugin_set_registry.py tests/test_memory_aware_manager.py tests/test_repository_plugin_loader_concurrency.py tests/test_plugin_factory_async.py tests/test_semantic_indexer_registry.py tests/test_bm25_adapter_plugin.py tests/test_dispatcher_p3_integration.py tests/test_dispatcher.py tests/test_dispatcher_advanced.py tests/test_gateway.py -v` exits 0.

## Verification

```bash
# Pre-flight
bash ~/.claude/skills/execute-phase/scripts/verify_harness.sh

# Sync environment — pick up any P3 dep changes
uv sync --extra dev

# PluginSetRegistry round-trip
.venv/bin/python - <<'PY'
from mcp_server.plugins import PluginSetRegistry
r = PluginSetRegistry()
list_a = r.plugins_for("fake-repo-a")
list_a2 = r.plugins_for("fake-repo-a")
# Same repo_id → same list (stability contract)
assert list_a is list_a2 or list_a == list_a2
r.evict("fake-repo-a")
print("PluginSetRegistry OK")
PY

# SemanticIndexerRegistry produces distinct collections per repo
.venv/bin/python - <<'PY'
from unittest.mock import patch
with patch("qdrant_client.QdrantClient"):
    from mcp_server.utils import SemanticIndexerRegistry
    r = SemanticIndexerRegistry()
    idx_a = r.get("fake-repo-a")
    idx_b = r.get("fake-repo-b")
    assert idx_a.collection_name != idx_b.collection_name, (
        f"Expected distinct collections: {idx_a.collection_name} vs {idx_b.collection_name}"
    )
    assert idx_a.collection_name.startswith("ci__")
    print("SemanticIndexerRegistry OK")
PY

# psutil fail-fast
.venv/bin/python - <<'PY'
import sys
sys.modules["psutil"] = None  # simulate unavailable
try:
    from mcp_server.plugins.memory_aware_manager import MemoryAwarePluginManager
    MemoryAwarePluginManager()
    raise SystemExit("FAIL: manager constructed without psutil")
except RuntimeError as e:
    assert "psutil" in str(e).lower()
    print("psutil fail-fast OK")
PY

# Real-RSS eviction smoke
.venv/bin/python - <<'PY'
from unittest.mock import patch
from mcp_server.plugins.memory_aware_manager import MemoryAwarePluginManager
m = MemoryAwarePluginManager(max_memory_mb=1)
with patch.object(m._process, "memory_info") as mi:
    # Report real RSS well above the limit
    mi.return_value.rss = 10 * 1024 * 1024
    # Tracked estimates report nothing
    m._plugin_info = {}
    # Eviction trigger should still fire (uses real RSS)
    assert m._should_evict() is True, "Real-RSS eviction did not fire"
    print("real-RSS eviction OK")
PY

# Plugin-store cleanup
.venv/bin/rg -n '_sqlite_store' mcp_server/plugins/js_plugin/plugin.py mcp_server/plugins/bm25_adapter_plugin.py mcp_server/plugins/plugin_base_enhanced.py && echo "FAIL: vestigial _sqlite_store remains" || echo "plugin-store cleanup OK"

# Dispatcher no longer holds singletons
.venv/bin/rg -nE 'self\._(plugins\b|_by_lang\b|_semantic_indexer\b)' mcp_server/dispatcher/dispatcher_enhanced.py && echo "FAIL: dispatcher singletons remain" || echo "dispatcher P3 OK"

# Full targeted test suite
.venv/bin/python -m pytest tests/test_plugin_set_registry.py tests/test_memory_aware_manager.py tests/test_repository_plugin_loader_concurrency.py tests/test_plugin_factory_async.py tests/test_semantic_indexer_registry.py tests/test_bm25_adapter_plugin.py tests/test_dispatcher_p3_integration.py tests/test_dispatcher.py tests/test_dispatcher_advanced.py tests/test_gateway.py -v
```

---

### Hand-off

On ExitPlanMode approval, the orchestrator will:

1. Write this doc to `plans/phase-plan-v1-p3.md`.
2. Run `python ~/.claude/skills/plan-phase/scripts/validate_plan_doc.py plans/phase-plan-v1-p3.md` and fix any errors.
3. **Author + commit the SL-0 preamble to main** — ~250 LOC of scaffolding (two new stub registries + `IPlugin.bind()` no-op + factory post-construction hook + `_profiles_lock` attribute). Compiles and passes existing tests.
4. Emit six `TaskCreate` calls (SL-1 through SL-6) with `test / impl / verify` children and DAG metadata.
5. User invokes `/execute-phase p3` when ready.
