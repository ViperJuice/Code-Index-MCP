# Code-Index-MCP Multi-Repo Refactor — Phase Plan v1

> **How to use this document**: this is the proposed content of `specs/phase-plans-v1.md`. On approval, save it to that path and run `/plan-phase P1` to produce the lane-level plan for Phase 1 (→ `plans/phase-plan-v1-p1.md`), then `/execute-phase p1` to build it. Repeat for each phase. Phase aliases follow the `specs/phase-aliases.json` pattern — use `P1, P2A, P2B, P3, P4, P5, P6A, P6B`.

---

## Context

Code-Index-MCP today is a **single-repo-per-process** MCP server. Everything — the dispatcher's `_sqlite_store`, the plugin map, the watcher root, the semantic collection — is constructed at startup from `Path.cwd()`. Pointing Claude Code at the same server from a different project silently serves the wrong tree. The goal of this refactor is to turn it into **one long-running MCP server that indexes and serves many repos from one machine**, worktree-aware, tracking only each repo's default branch.

The refactor is large but the code already contains most of the raw material:

- `mcp_server/storage/multi_repo_manager.py::MultiRepositoryManager` exists, holds a central registry, and parallel-searches across repos with a `ThreadPoolExecutor`. Its `_connections` cache *is effectively* the store registry we need — it just isn't wired through the dispatcher.
- `mcp_server/utils/semantic_indexer.py::_resolve_collection_name` already supports per-repo Qdrant collections via `namespace_resolver.resolve_collection_name(repo_identifier, profile_id, lineage_id)` — it just falls back to a shared collection when `repo_identifier` is missing.
- `mcp_server/watcher_multi_repo.py::MultiRepoWatcher` exists with per-repo observers but has **zero imports** anywhere in the codebase.
- `mcp_server/storage/repository_registry.py` tracks `current_branch` / `last_indexed_branch` and has `_get_preferred_branch` that prefers `main`/`master`, but it's not wired as a pin — branch switches force a full reindex today.

So the refactor is less "build from scratch" and more **wire up the dormant plumbing, freeze stable interfaces between layers, and delete the single-repo globals**.

### Secondary concerns being folded in
The review that preceded this plan surfaced several issues that aren't strictly multi-repo but block the production quality bar:
- Two duplicate cross-repo coordinator classes (`mcp_server/storage/cross_repo_coordinator.py::CrossRepositorySearchCoordinator` and `mcp_server/dispatcher/cross_repo_coordinator.py::CrossRepositoryCoordinator`) totaling ~1100 lines of overlap.
- Two entry points (`scripts/cli/mcp_server_cli.py` ~1700 lines vs `mcp_server/cli/`) that will drift.
- STDIO MCP server has no authorization layer (only FastAPI's JWT path does).
- `passlib==1.7.4` + `bcrypt<4.0.0` are an old, unmaintained compat pin.
- AGENTS.md claims "100% production-ready" despite broken multi-repo code, no stdio auth, no worktree support.

These get woven into the phases where they overlap with multi-repo work, not separated into their own refactor.

---

## Architecture North Star

```
                   ┌─────────────────────────────────────────┐
                   │         MCP stdio server (one)          │
                   │  entry: mcp_server/cli/server_commands  │
                   │  ─ tool handlers accept RepoContext ─   │
                   └────────┬─────────────────┬──────────────┘
                            │                 │
                   ┌────────▼────────┐ ┌──────▼──────────────┐
                   │  RepoResolver   │ │   StoreRegistry     │
                   │  path→repo_id   │ │  repo_id→SQLiteStore│
                   └────────┬────────┘ └──────┬──────────────┘
                            │                 │
                   ┌────────▼─────────────────▼──────────────┐
                   │     RepositoryRegistry (JSON + lock)    │
                   │  repo_id → {path, index_path,           │
                   │             tracked_branch, …}          │
                   │  Worktree-aware: git-common-dir + url   │
                   └────────┬────────────────────────────────┘
                            │
           ┌────────────────┼────────────────────────┐
           │                │                        │
  ┌────────▼────────┐ ┌─────▼─────────────┐ ┌───────▼────────────┐
  │  MultiRepoWatcher│ │  PluginSetRegistry│ │SemanticIndexerReg. │
  │  per-repo roots │ │  repo_id→plugins  │ │  repo_id→indexer   │
  │  + tracked-ref   │ │  RSS-capped LRU  │ │  per-repo collection│
  │  poller          │ └───────────────────┘ └────────────────────┘
  │  default-branch  │
  │  only            │
  └──────────────────┘
```

Every per-tool-call path — `search_code(query, repo_id)`, `symbol_lookup(symbol, repo_id)`, `reindex(path)` — resolves a `RepoContext` first, then hands it to the dispatcher. The dispatcher holds **no repo-level state**. "Current repo" as a concept is gone.

---

## Assumptions (fail-loud if wrong)

1. **EnhancedDispatcher is the target.** SimpleDispatcher stays as a BM25-only debug fallback, not the production path.
2. **Breaking existing indexes is acceptable.** First server run under the new identity scheme auto-regenerates with the new repo_id. No migration bookkeeping — just fail-open and let the FileWatcher / initial-index path rebuild.
3. **STDIO is the primary surface.** FastAPI gateway secondary (operators' view, not Claude Code's). Auth hardening focuses on stdio.
4. **Worktrees REDIRECT, not REJECT.** All worktrees of the same repo share one index, keyed by `git rev-parse --git-common-dir` + `remote.origin.url` hash.
5. **Default branch is pinned at registration, not tracked live.** An operator explicit action is required to retarget a registered repo to a different branch.

---

## Non-Goals

- No rewrite of the plugin authoring interface (`PluginBase` stays put).
- No change to the MCP tool names or their JSON schemas.
- No move off SQLite. FTS5 + BM25 stays; per-repo stores means per-repo files, not sharded tables.
- No new transport (HTTP, SSE) beyond what exists.
- No rewrite of the semantic embeddings pipeline; just thread `repo_id` through the existing `SemanticIndexer` constructor.

---

## Cross-Cutting Principles

1. **Single-writer-per-SQLite-file.** Each repo's `SQLiteStore` owns its DB; cross-repo search reads multiple stores in parallel via a `ThreadPoolExecutor`. No central-DB fan-in.
2. **Worktree identity = `git-common-dir` + `origin` URL hash.** Five worktrees of one repo resolve to one `repo_id`, one store, one plugin set.
3. **Default-branch-only indexing.** Reindex trigger is "`refs/heads/<tracked_branch>` advanced", never "HEAD moved". Branch switches in the watched repo are no-ops.
4. **RepoContext per tool call, never a global.** Dispatcher is stateless w.r.t. repo identity.
5. **Interface freezes > implementation order.** Downstream lanes consume only what upstream lanes have pinned in a `### Interfaces provided` block.
6. **Fail-closed on unknown repos.** A tool call for a path outside the registry returns a structured error, not best-effort auto-registration.

---

## Phase Dependency DAG

```
  P1  Identity + default-branch pinning
   │
   ▼
  P2A  Data model (RepoContext, StoreRegistry, resolver)
   │
   ▼
  P2B  Dispatcher refactor + entry-point consolidation
   │
   ▼
  P3   Per-repo plugins / stores / memory / semantic-indexer registry
   │         (P4 may start as soon as P3's `plugins_for(repo_id)` freeze is closed)
   ▼
  P4   Default-branch-only indexing + MultiRepoWatcher wiring
   │
   ▼
  P5   STDIO hardening + multi-repo integration tests

  P6A  Dep hygiene          parallel after P1
  P6B  Docs alignment       after P4 merge
```

---

## Top Interface-Freeze Gates

These gates are the narrowest contracts that let downstream phases start once they close. Each will be concretized (exact signature + schema) by `/plan-phase` when its owning phase is planned.

1. **IF-0-P1-1** — `mcp_server/storage/repo_identity.py::compute_repo_id(path: Path) -> str`. Deterministic, worktree-aware (uses `git rev-parse --git-common-dir` + remote URL; falls back to common-dir absolute-path hash when no remote).
2. **IF-0-P1-2** — `RepositoryInfo` field set, including `tracked_branch: str` and `git_common_dir: Path`. Stable field set; adding fields OK, renaming not.
3. **IF-0-P2A-1** — `RepoContext` dataclass: `{repo_id, sqlite_store, tracked_branch, workspace_root, common_dir}`. Frozen before P2B starts.
4. **IF-0-P2A-2** — `StoreRegistry.get(repo_id: str) -> SQLiteStore` — idempotent, thread-safe, owns connection lifetime.
5. **IF-0-P2B-1** — Dispatcher public tool-call signature: every public method takes `ctx: RepoContext` as first positional arg after `self`. Frozen before P3/P4 starts.
6. **IF-0-P3-1** — `plugins_for(repo_id: str) -> list[Plugin]` and `SemanticIndexerRegistry.get(repo_id) -> SemanticIndexer`. These are what unblock P4.

---

## Phases

### Phase 1 — Repo Identity & Default-Branch Pinning (P1)

**Objective**
Establish a single, worktree-aware identity scheme for repositories and pin each registered repo to a specific default branch that never auto-changes. Kill the "force full reindex on branch change" behavior.

**Exit criteria**
- [ ] `compute_repo_id(path)` returns the same id for every worktree of a given repo (verified by fixture with one bare repo + 3 worktrees).
- [ ] New `RepositoryInfo` records include a non-null `tracked_branch` (resolved to `origin/HEAD` → `main` → `master` → current, in that order).
- [ ] Checking out a non-tracked branch in a watched repo produces zero reindex events (integration test: checkout feature branch, modify a file, observe no indexing).
- [ ] `.gitignore` is honored by the auto-index walker at `scripts/cli/mcp_server_cli.py:~370` and the dispatcher walker at `mcp_server/dispatcher/dispatcher_enhanced.py:~1670`.
- [ ] Registry auto-regenerates ids on first run under the new scheme; legacy entries either match (no-op) or get re-registered (no stale bookkeeping).

**Scope notes**
- Create `mcp_server/storage/repo_identity.py` as the single source of truth for id computation. Replace the inline logic in `MultiRepositoryManager._generate_repository_id` (~line 193) and the newly added `MultiRepositoryManager.resolve_repo_id` classmethod added earlier this session (which currently hashes path/URL without worktree awareness).
- Extend `RepositoryRegistry.register()` (`mcp_server/storage/repository_registry.py:~195`) to compute + persist `tracked_branch` and `git_common_dir`.
- Rip out the "branch changed → force full reindex" block at `mcp_server/storage/git_index_manager.py:106–113`.
- Walker `.gitignore` respect: reuse existing `mcp_server/core/ignore_patterns.py` if present; otherwise use `pathspec` (already in requirements).

**Non-goals**
- No dispatcher changes yet — the existing single-repo path must still work after P1.
- No `StoreRegistry` yet — per-repo store wiring happens in P2A.

**Key files**
- `mcp_server/storage/repo_identity.py` (new)
- `mcp_server/storage/repository_registry.py`
- `mcp_server/storage/git_index_manager.py`
- `mcp_server/storage/multi_repo_manager.py` (delegate id computation to `repo_identity`)
- `mcp_server/utils/index_discovery.py`
- `scripts/cli/mcp_server_cli.py` (walker `.gitignore` respect only; no other changes)
- `mcp_server/dispatcher/dispatcher_enhanced.py` (walker `.gitignore` respect only)

**Produces**
- IF-0-P1-1, IF-0-P1-2

---

### Phase 2A — Data Model & Store Registry (P2A)

**Objective**
Introduce the `RepoContext` / `StoreRegistry` / `RepoResolver` types. Consolidate the three duplicate multi-repo classes into this new surface. No behavior change yet — dispatcher still works single-repo — but the new types exist and are tested.

**Exit criteria**
- [ ] `RepoContext` dataclass with frozen field set (IF-0-P2A-1) lives in `mcp_server/core/repo_context.py`.
- [ ] `StoreRegistry.get(repo_id)` returns the same `SQLiteStore` instance for repeated calls, closes gracefully in `shutdown()`, and is safe under concurrent access (tested with threaded fixture).
- [ ] `RepoResolver.resolve(path) -> Optional[RepoContext]`: walks up from `path` to the nearest `.git`, computes repo_id, loads from registry, hydrates `RepoContext`. Returns `None` for paths outside the registry.
- [ ] The three duplicates (`MultiRepositoryManager._connections`, `storage/cross_repo_coordinator.py::CrossRepositorySearchCoordinator`, `dispatcher/cross_repo_coordinator.py::CrossRepositoryCoordinator`) are all refactored to thin wrappers that delegate to `StoreRegistry`; duplicate logic removed.

**Scope notes**
- This phase has **disjoint file ownership** for 3–4 swim lanes (data model / store registry / resolver / consolidation) because none of them edit `dispatcher_enhanced.py` — that's P2B.
- `StoreRegistry` should subsume `MultiRepositoryManager._connections` (~line 326) and `cross_repo_coordinator._get_connection`. The existing `_get_connection` implementations are actually compatible APIs; this is mostly "pick one, delete the others, pass the new one around."
- Consolidation lane should verify that `EnhancedDispatcher._multi_repo_manager` (constructed at `dispatcher_enhanced.py:231`) still works against the new surface before any dispatcher changes.

**Non-goals**
- No changes to `dispatcher_enhanced.py`, `simple_dispatcher.py`, or the entry point. P2B owns those.
- No per-repo plugin map yet. P3 owns that.

**Key files**
- `mcp_server/core/repo_context.py` (new)
- `mcp_server/storage/store_registry.py` (new)
- `mcp_server/core/repo_resolver.py` (new)
- `mcp_server/storage/multi_repo_manager.py` (delegate to StoreRegistry)
- `mcp_server/storage/cross_repo_coordinator.py` (delete or thin-wrapper)
- `mcp_server/dispatcher/cross_repo_coordinator.py` (delete or thin-wrapper)
- `tests/test_repo_context.py`, `tests/test_store_registry.py`, `tests/test_repo_resolver.py` (new)

**Depends on**
- P1 merged (needs `compute_repo_id` and `tracked_branch`).

**Produces**
- IF-0-P2A-1, IF-0-P2A-2

---

### Phase 2B — Dispatcher Refactor & Entry-Point Consolidation (P2B)

**Objective**
Remove the single-`_sqlite_store` coupling from the dispatcher. Every public dispatcher method takes a `RepoContext` as its first arg. Collapse the 1700-line `scripts/cli/mcp_server_cli.py` into `mcp_server/cli/server_commands.py` (the canonical package entry point), deleting the duplicate. Update `.mcp.json`, `.mcp.json.example`, and `.mcp.json.templates/*` accordingly.

**Exit criteria**
- [ ] `EnhancedDispatcher` constructor no longer takes `sqlite_store`; all 15+ `self._sqlite_store` references are gone.
- [ ] Every public dispatcher method signature matches `def method(self, ctx: RepoContext, ...) -> ...`.
- [ ] `scripts/cli/mcp_server_cli.py` deleted. `mcp_server/cli/server_commands.py` is the sole MCP stdio entry point (or a thin `scripts/` wrapper that imports from the package).
- [ ] All `.mcp.json.*` templates updated to point at the new entry (keeping `op run --env-file` shape from earlier session work).
- [ ] Existing single-repo usage still works: launching the server in the repo's cwd, calling `search_code` without `repository=`, still returns results.
- [ ] Cross-repo usage works: `search_code(query, repository=<path or id>)` routes via `RepoResolver` and returns results scoped to that repo.

**Scope notes**
- **Facade-freeze pattern required**: before lanes diverge, write the new `EnhancedDispatcher` public interface as a dataclass of method signatures (or an ABC), with one lane owning the internals and another owning consumers (entry point, CLI). Without the facade freeze, both lanes will collide on `dispatcher_enhanced.py` and the phase can't parallelize.
- The old cwd-at-init capture (`scripts/cli/mcp_server_cli.py:113`) vanishes. First tool call resolves `RepoContext` from the path argument or the `MCP_WORKSPACE_ROOT` default; no implicit cwd binding.
- `initialize_services()` becomes `initialize_stateless_services()` — it builds `StoreRegistry`, `RepoResolver`, `PluginSetRegistry` (from P3 — placeholder stub until P3 lands), but does NOT construct a dispatcher with a repo preloaded.

**Non-goals**
- No per-repo plugin map yet — dispatcher still has a single plugin set during P2B; P3 wraps that in a repo-scoped registry.
- No auth hardening yet (P5).
- No watcher changes (P4).

**Key files**
- `mcp_server/dispatcher/dispatcher_enhanced.py` (biggest delta)
- `mcp_server/dispatcher/simple_dispatcher.py`
- `mcp_server/cli/server_commands.py` (becomes the canonical entry)
- `scripts/cli/mcp_server_cli.py` (deleted or reduced to `from mcp_server.cli.server_commands import main; main()`)
- `.mcp.json`, `.mcp.json.example`, `.mcp.json.template`, `.mcp.json.templates/*.json`

**Depends on**
- P2A merged.

**Produces**
- IF-0-P2B-1

---

### Phase 3 — Per-Repo Plugins, Stores & Memory (P3)

**Objective**
Make plugins, semantic indexers, and memory accounting repo-scoped. Every plugin instance is bound to a `RepoContext` at construction; the dispatcher fetches them via `plugins_for(repo_id)`. Memory limits are enforced against real RSS.

**Exit criteria**
- [ ] `PluginSetRegistry.plugins_for(repo_id: str) -> list[Plugin]` returns a stable, memory-managed list of plugins scoped to that repo. Repeated calls return the same instances; evicted plugins are reconstructed on demand.
- [ ] `SemanticIndexerRegistry.get(repo_id: str) -> SemanticIndexer` threads `repo_id` through the `SemanticIndexer` constructor → `_resolve_collection_name` → `namespace_resolver.resolve_collection_name(repo_identifier=repo_id, ...)`. Two repos → two Qdrant collections, verified by integration test.
- [ ] `MemoryAwarePluginManager` uses actual `psutil.Process().memory_info().rss` for eviction decisions (not tracked-plugin estimates). If `psutil` import fails, the manager refuses to start and the server logs a clear error — no silent no-op.
- [ ] `RepositoryPluginLoader._profiles` access is behind a `threading.Lock`; concurrent `analyze_repository` calls from two threads produce identical cached profiles (tested under stress).
- [ ] Plugin cold-start does not block the asyncio event loop. Plugin construction runs in a thread pool; tool calls for unknown languages return a "plugin warming up" response or await on a future, never synchronously block for 100–500 ms.
- [ ] Plugin-level `_sqlite_store` attributes in `js_plugin`, `plugin_semantic`, `bm25_adapter_plugin` replaced with a `RepoContext`-provided store (no per-plugin store ownership).

**Scope notes**
- **5 lanes plausible**: memory manager rewrite, plugin loader lock, plugin factory async, plugin-level store refactor, semantic indexer registry.
- The plugin-level store wiring is the hardest lane because it touches individual plugins. Scope it to the three plugins the Plan-agent review called out (`js_plugin/plugin.py`, plugins using `plugin_semantic.py`, `bm25_adapter_plugin.py`); other plugins are checked but only patched if found to carry the same coupling.
- Semantic-indexer registry should reuse `namespace_resolver.resolve_collection_name` unchanged; the work is constructor-threading only.

**Non-goals**
- No watcher changes — P4 owns that.
- No test-suite expansion beyond unit coverage for the new registries. Full multi-repo integration test is P5.

**Key files**
- `mcp_server/plugins/memory_aware_manager.py`
- `mcp_server/plugins/repository_plugin_loader.py`
- `mcp_server/plugins/plugin_factory.py`
- `mcp_server/plugins/plugin_set_registry.py` (new)
- `mcp_server/utils/semantic_indexer.py`
- `mcp_server/utils/semantic_indexer_registry.py` (new)
- `mcp_server/plugins/js_plugin/plugin.py`
- `mcp_server/plugins/bm25_adapter_plugin.py`
- `mcp_server/plugins/plugin_semantic.py` (if present)
- `mcp_server/dispatcher/dispatcher_enhanced.py` (consumer-side: replace direct plugin access with `plugins_for(ctx.repo_id)`)

**Depends on**
- P2B merged.

**Produces**
- IF-0-P3-1 (unblocks P4)

---

### Phase 4 — Default-Branch-Only Indexing & Multi-Repo Watcher (P4)

**Objective**
Replace the single-root `FileWatcher` with the `MultiRepoWatcher` (currently dead code) wired to all registered repos, plus a tracked-ref poller that only reindexes when `refs/heads/<tracked_branch>` advances.

**Exit criteria**
- [ ] `MultiRepoWatcher` is imported and instantiated in the entry point; it watches every registered repo's `git_common_dir`-resolved primary worktree, not the current cwd.
- [ ] For each registered repo, a tracked-ref poller checks `refs/heads/<tracked_branch>` every N seconds (default 30). On advance, it computes diff vs `last_indexed_commit` and triggers incremental reindex.
- [ ] Checking out a non-tracked branch in a watched worktree produces zero dispatcher calls (reuses P1's exit criterion but in the wired-up watcher).
- [ ] File events on paths matched by the repo's `.gitignore` are dropped at the handler level (hardens P1's walker-level fix).
- [ ] Watcher startup ordering: `MultiRepoWatcher.start()` runs *after* `StoreRegistry` and `PluginSetRegistry` are ready; tested with a boot-order fixture.

**Scope notes**
- 3 lanes: watcher wiring (use existing `mcp_server/watcher_multi_repo.py`), tracked-ref poller (new `mcp_server/watcher/ref_poller.py`), local-watcher filter (drop events outside tracked branch).
- The existing single-repo `FileWatcher` at `mcp_server/watcher.py` (rewritten earlier this session with debouncing + vendor-dir exclusion + async exception surfacing) stays as the per-repo implementation; `MultiRepoWatcher` composes many of them.
- Consider whether `MultiRepoWatcher` should use one shared `Observer` or per-repo `Observer`s (the existing implementation uses one-per-repo). Keep existing shape unless a reason emerges.

**Non-goals**
- No new watcher features beyond the default-branch-only guarantee. No support for watching GitHub/remote refs, no webhook triggers.

**Key files**
- `mcp_server/watcher_multi_repo.py` (wire into entry point)
- `mcp_server/watcher.py` (minor: take `RepoContext`, drop events outside tracked branch)
- `mcp_server/watcher/ref_poller.py` (new)
- `mcp_server/cli/server_commands.py` (boot ordering)
- `mcp_server/storage/git_index_manager.py` (tracked-ref diff logic)

**Depends on**
- P3's `plugins_for(repo_id)` freeze (IF-0-P3-1) closed. May start as soon as the freeze is closed; does not require P3 merge.

**Produces**
- Last concrete runtime behavior — the system can now run as one server for many repos.

---

### Phase 5 — STDIO Hardening & Multi-Repo Integration Tests (P5)

**Objective**
Enforce the path-prefix allowlist at every tool-handler entry (not just `reindex`), add an optional per-client shared-secret for shared-machine scenarios, and prove the whole stack works end-to-end with an integration test booting the server against two repos.

**Exit criteria**
- [ ] Every public MCP tool handler checks that paths in arguments resolve within `_allowed_roots()` (the helper added earlier this session for `reindex`). `symbol_lookup`, `search_code`, `write_summaries`, `summarize_sample` all go through the same guard.
- [ ] Optional `MCP_CLIENT_SECRET` env gate: if set, the server requires the client to send a matching string in an initial `handshake` tool call; if unset, the server runs unprotected (current behavior) but logs a warning once at startup.
- [ ] Integration test `tests/integration/test_multi_repo_server.py` boots a server against two temp repos (A, B), registers both, runs `search_code(query, repository=A)` and `search_code(query, repository=B)`, asserts isolation (A-results do not contain B-paths and vice versa).
- [ ] Branch-switch test: in repo A, checkout a non-tracked branch, modify a file, wait 2× poll interval, assert zero new index entries.
- [ ] Worktree-equals-main test: create a second worktree of repo A at a new path, run `symbol_lookup` through the worktree path, assert it resolves to the same repo_id and returns the same results.
- [ ] Concurrency test: two threads run `search_code` against A and B simultaneously; no `database is locked` errors, no cross-contamination.

**Scope notes**
- 3 lanes: handler-level sandbox, optional handshake, integration-test scaffolding.
- The integration-test lane is the only one that needs new fixtures: temp-repo builders, fake plugin set, minimal registry.
- Handler-level sandbox lane reuses `_allowed_roots()` / `_path_within_allowed()` from the session's existing work.

**Key files**
- `mcp_server/cli/server_commands.py` (tool-handler guards)
- `tests/integration/test_multi_repo_server.py` (new)
- `tests/fixtures/multi_repo.py` (new)

**Depends on**
- P4 merged.

---

### Phase 6A — Dependency Hygiene (P6A, parallel after P1)

**Objective**
Unblock a secure-by-default password stack and a single source-of-truth for dependencies. Parallel-safe because it doesn't touch the hot dispatcher path.

**Exit criteria**
- [ ] `passlib` removed; `argon2-cffi` + a backward-compat verifier for any legacy `passlib`-format hashes (rehash-on-login pattern).
- [ ] `bcrypt` version pin lifted (no more `<4.0.0` ceiling).
- [ ] Four `requirements-*.txt` files deleted; `pyproject.toml` + `uv.lock` is the sole source of dependencies.
- [ ] `pyproject.toml` `requires-python` and AGENTS.md / README Python version claims agree.
- [ ] `PathUtils.get_workspace_root()` literal-string bug cleanup extended to the 10 script-level hits (the three runtime-code hits were fixed in the pre-refactor cleanup session).

**Scope notes**
- 2–3 lanes: password stack (auth_manager), requirements consolidation, scripts string-bug sweep. All independent.
- Password stack migration needs a compat-verifier: on login, if the stored hash starts with `$2b$` or `$2a$`, verify via bcrypt; if mismatch, fail; if match, rehash with argon2 and update. Otherwise verify via argon2.

**Key files**
- `mcp_server/security/auth_manager.py`
- `pyproject.toml`
- `uv.lock`
- `requirements.txt`, `requirements-core.txt`, `requirements-production.txt`, `requirements-semantic.txt` (deleted)
- `scripts/**/*.py` (literal-string sweep)

**Depends on**
- P1 merged (avoids drift with identity module changes).

---

### Phase 6B — Documentation Alignment (P6B, after P4 merge)

**Objective**
Rewrite AGENTS.md, README.md multi-repo section, CLAUDE.md usage hints, and architecture docs to match the post-refactor reality.

**Exit criteria**
- [ ] AGENTS.md no longer claims "100% production-ready" / "Phase 1 8/8 complete"; new sections describe the multi-repo model, repo identity, default-branch policy, and the `MCP_ALLOWED_ROOTS` / registry-based auth story.
- [ ] README.md "how to use against many repos" section added with concrete setup steps.
- [ ] `specs/active/architecture.md` updated so its C4 diagrams show `RepoContext` + `StoreRegistry` + `MultiRepoWatcher`.
- [ ] MCP tool JSON schemas in `scripts/cli/` or the canonical entry point have accurate descriptions mentioning `repository=` parameter semantics.

**Scope notes**
- Single lane. Documentation-only.

**Key files**
- `AGENTS.md`
- `README.md`
- `CLAUDE.md`
- `specs/active/architecture.md`
- `docs/**` (targeted)

**Depends on**
- P4 merged (documenting behavior before it ships is how docs drift).

---

## Execution Notes

- **Save this file as `specs/phase-plans-v1.md`** and create `specs/phase-aliases.json` mapping `P1, P2A, P2B, P3, P4, P5, P6A, P6B` to the full phase headings above so `/plan-phase` can resolve short aliases. If `specs/phase-aliases.json` isn't used, pass `<phase-name-or-id>` as the full heading when invoking `/plan-phase`.
- Run `/plan-phase P1` first. Review the lane plan at `plans/phase-plan-v1-p1.md`, then run `/execute-phase p1`. Repeat per phase.
- `/plan-phase` defaults `MAX_PARALLEL_LANES=2` for execute-phase — keep that default. Full-parallel dispatch caused stale-base salvage issues in prior phases and the two-wave cadence is proven safer.
- **P2B is the riskiest phase to lane-decompose.** Plan it with `--consensus` (three Plan-agent framings) so the facade freeze is validated before lane split.
- Do not start P6A until P1 is merged, even though it's nominally parallel — the identity refactor may touch `mcp_server/security/` indirectly via the `PathUtils` cleanup.
- The integration test in P5 is the phase-gate quality bar for the whole refactor. If it passes and the FastAPI gateway's existing unit tests still pass, we're done.

## Verification (whole-refactor, after P5 merge)

```bash
# Boot the server against two repos
MCP_ALLOWED_ROOTS=/tmp/repo-a,/tmp/repo-b \
op run --env-file=.mcp.env -- python -m mcp_server.cli.server_commands &

# Register both
curl -X POST localhost:8000/repos -d '{"path": "/tmp/repo-a"}'
curl -X POST localhost:8000/repos -d '{"path": "/tmp/repo-b"}'

# Search scoped to each
curl -X POST localhost:8000/search -d '{"query": "foo", "repository": "/tmp/repo-a"}' | jq '.[] | .file' | grep -v repo-b
curl -X POST localhost:8000/search -d '{"query": "foo", "repository": "/tmp/repo-b"}' | jq '.[] | .file' | grep -v repo-a

# Run the integration test
pytest tests/integration/test_multi_repo_server.py -v

# Prove no-reindex-on-branch-switch
cd /tmp/repo-a && git checkout -b feature/noise && echo "x" > newfile.py && sleep 60 && \
  curl localhost:8000/status | jq '.features.initial_index_running' | grep false
```

All commands above should return success. Any `database is locked`, cross-contaminated results, or reindex-on-branch-switch observation fails the refactor.
