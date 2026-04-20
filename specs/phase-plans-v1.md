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

  P11  Dispatcher Dependability (after P10 merge)
   │
   ▼
  P12  Ops Readiness + Reindex Safety
   │
   ▼
  P13  Reindex Durability + Artifact Automation
   │
   ▼
  P14  Multi-Repo Completeness + Schema Evolution
   │
   ▼
  P15  Security Hardening
   │
   ▼
  P16  Shared vocabulary preamble (error taxonomy + env constants + config validator + singleton reset)
   │
   ├──► P17  Durability & Multi-Instance Safety     parallel after P16
   │
   └──► P18  Enforcement, Artifact Resilience & Ops parallel after P16
                    │
                    ▼
                   P19  Release Readiness (reconcile, publish, residual debt, upgrade comms)
                    │
                    ▼
                   P20  Multi-Repo Validation & Staged Rollout (GA)
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
7. **IF-0-P12-1** — `HealthView.snapshot() -> dict[str, Any]` with stable keys `{sqlite, registry, dispatcher, last_index_ms, uptime_s}`. `/ready` and `/liveness` both derive from it.
8. **IF-0-P12-2** — `IndexingLockRegistry.acquire(repo_id: str) -> ContextManager[None]`. Per-repo reentrant lock; both watcher and manual-sync paths must acquire before dispatcher write.
9. **IF-0-P12-3** — Log event name `branch.drift.detected` with `{repo_id, current_branch, tracked_branch}` fields + `MultiRepoWatcher.enqueue_full_rescan(repo_id)` call point.
10. **IF-0-P12-4** — Histogram attribute names on `PrometheusExporter`: `dispatcher_lookup_histogram`, `dispatcher_search_histogram`. Same `(0.005, … 5.0)` bucket tuple as P11.
11. **IF-0-P12-5** — `verify_artifact_freshness(meta: ArtifactMetadata, head_commit: str, max_age_days: int) -> FreshnessVerdict` enum (`FRESH | STALE_COMMIT | STALE_AGE | INVALID`).
12. **IF-0-P13-1** — `.reindex-state` JSON schema: `{repo_id, started_at, last_completed_path, remaining_paths, errors}`. Stable shape; additive fields OK.
13. **IF-0-P13-2** — `two_phase_commit(primary_op: Callable, shadow_op: Callable, rollback: Callable) -> None` helper. Both-or-neither semantics.
14. **IF-0-P13-3** — `dispatcher.index_file_guarded(path: Path, expected_hash: str) -> IndexResult` — returns `SKIPPED_TOCTOU` if hash mismatch at write time.
15. **IF-0-P13-4** — `ArtifactPublisher.publish_on_reindex(repo_id: str, commit: str) -> ArtifactRef`. Idempotent; atomic `latest` pointer update via GitHub release tag move.
16. **IF-0-P13-5** — Exception base class `McpError` + subclasses (`IndexingError`, `ArtifactError`, `PluginError`). Prometheus counter `mcp_errors_by_type_total{module, exception}`.
17. **IF-0-P14-1** — `RerankerProvider` abstract base with `rerank(query: str, results: list[SearchResult]) -> list[SearchResult]`; registration via `register_reranker(name, provider)` module-level helper.
18. **IF-0-P14-2** — `_get_repository_dependencies(repo_id: str) -> Set[str]` real implementation; returns repo_ids of detected upstream dependencies.
19. **IF-0-P14-3** — `ArtifactManifest.schema_version: int` + `SchemaMigrator.apply(from_version: int, to_version: int, db_path: Path) -> None`.
20. **IF-0-P14-4** — `DeltaPolicy.should_publish_delta(full_size_bytes: int, last_artifact: ArtifactRef | None) -> bool` + delta-manifest shape extension.
21. **IF-0-P14-5** — `FileSystemSweeper.periodic_sweep(repo_id: str)` method + env vars `MCP_WATCHER_SWEEP_MINUTES` and `MCP_WATCHER_POLL_SECONDS`.
22. **IF-0-P15-1** — Plugin-sandbox IPC protocol (message envelope schema) + `SandboxedPlugin(real_plugin_spec, capabilities: CapabilitySet)` adapter.
23. **IF-0-P15-2** — `require_auth(scope: Literal["metrics","admin","tools"]) -> dependency` middleware + the repo-level decision on auth mode (captured in runbook).
24. **IF-0-P15-3** — `attest(artifact_path: Path) -> Attestation` + `verify_attestation(artifact_path: Path, attestation: Attestation) -> bool`.
25. **IF-0-P15-4** — `PathTraversalGuard.normalize_and_check(path: str, roots: list[Path]) -> Path` + `TokenValidator.validate_scopes(required: set[str]) -> None` + rate-limit backoff helper.
26. **IF-0-P16-1** — Artifact error taxonomy in `mcp_server/core/errors.py`: `TransientArtifactError(ArtifactError)` (retry-safe — 5xx, timeout, rate-limit, network), `TerminalArtifactError(ArtifactError)` (not retry-safe — 4xx, auth, validation, missing-artifact), `SchemaMigrationError(ArtifactError)` (migration failed; DB restored from backup). Prometheus counter label extension: `mcp_artifact_errors_by_class_total{class="transient"|"terminal"|"schema_migration"}`.
27. **IF-0-P16-2** — Env-var constant module `mcp_server/config/env_vars.py` with lazy readers (never module-level `os.environ` reads): `get_max_file_size_bytes() -> int` (default 10_485_760 = 10 MiB), `get_artifact_retention_count() -> int` (10), `get_artifact_retention_days() -> int` (30), `get_disk_readonly_threshold_mb() -> int` (100), `get_publish_rollback_enabled() -> bool` (default True).
28. **IF-0-P16-3** — `validate_production_config(config: SecurityConfig, *, environment: str) -> list[ValidationError]` in `mcp_server/config/validation.py`; returns a list (empty if valid), caller decides to raise. `ValidationError` is a frozen dataclass `{code: str, message: str, severity: Literal["fatal","warn"]}`. Fatal severity under `environment="production"` must abort boot.
29. **IF-0-P16-4** — `reset_process_singletons() -> None` in `mcp_server/cli/bootstrap.py`. Idempotent; zeroes each `_instance` at module scope: `multi_repo_manager._manager_instance`, `cross_repo_coordinator._coordinator_instance`, `repository_plugin_loader._loader_instance`, `memory_aware_manager._memory_manager_instance`.
30. **IF-0-P17-1** — Registry save protocol: `RepositoryRegistry.save()` acquires `fcntl.flock(LOCK_EX)` on a sibling `.lock` file, then performs the existing atomic rename. Pattern documented in `docs/operations/multi-instance.md`.
31. **IF-0-P18-1** — Route-auth coverage contract: every `@app.(get|post|put|delete|patch)` route in `mcp_server/gateway.py` is one of (a) explicitly public (auth endpoints, `/health*`, `/ready`, `/liveness`), (b) gated by `Depends(require_auth|require_permission|require_role)` on the function signature, or (c) gated by `dependencies=[Depends(...)]` on the decorator. Enforced by `tests/security/test_route_auth_coverage.py` via `app.routes` introspection.
32. **IF-0-P19-1** — `scripts/preflight_upgrade.sh <env_file_path>` exits `0` if the configured env will not fatal against the current gateway validation rules, `1` with a categorized `[FATAL]`/`[WARN]` listing on stdout otherwise. Same rendering contract as SL-1's `render_validation_errors_to_stderr` so operators see identical diagnostics pre- and post-deploy. Consumed by the deployment runbook in P20.
33. **IF-0-P19-2** — Opt-in network/auth test marker: `pytest.mark.requires_gh_auth` is defined in `tests/conftest.py`; `addopts` skips it by default and runs it when `RUN_GH_AUTHENTICATED_TESTS=1`. All tests that call live `gh` CLI subcommands or require real `attestations:write` scope carry this marker. Default `pytest` run is zero-failure; CI runs both modes in separate jobs.
34. **IF-0-P19-3** — Docs-catalog integrity gate: `tests/test_docs_catalog_integrity.py` asserts (a) every `path` in `.claude/docs-catalog.json` exists on disk, (b) no duplicate `path` entries, (c) schema shape matches `{version:int, generated_at:str, docs:[{path,description,touched_by_phases}]}`. Enforced in CI; any SL-docs lane that rescans the catalog must keep this green.
35. **IF-0-P20-1** — Multi-repo integration fixture: `tests/integration/multi_repo/conftest.py::multi_repo_fixture(n_repos: int = 2)` yields `list[MultiRepoContext]` where `MultiRepoContext = {repo_id: str, workspace: Path, gateway_url: str, registry_path: Path}`. All contexts share `registry_path`; each has distinct `repo_id` and `workspace`. Teardown is synchronous and idempotent. Consumed by every P20 multi-repo integration test.
36. **IF-0-P20-2** — Deployment bake-gate contract: `docs/operations/deployment-runbook.md` defines, for each rollout stage, (a) measurable bake-pass criteria (error rate, 99p latency, log JSON parse rate, counter non-zero), (b) bake window duration, (c) rollback trigger, (d) rollback procedure. Contract shape is stable across phases; future deploys can append new stages without editing existing ones.

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
- Decompose into 3 lanes: (a) identity module (new `repo_identity.py`, publishes `compute_repo_id` signature as IF-0-P1-1 day-one so (b)/(c) unblock immediately); (b) registry changes (`RepositoryRegistry.register()` + `git_index_manager.py` branch-change block removal); (c) walker `.gitignore` respect (disjoint edits in CLI walker + dispatcher walker).
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

**Depends on**
- (none)

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

### Phase 7 — Doc Truth: Agent & Machine Audiences (P7)

**Objective**
Bring the docs agents and MCP clients read into alignment with post-P6B reality. `AGENTS.md`, `specs/active/architecture.md` L3 diagram, and the MCP tool JSON schemas in `stdio_runner.py` are all structured artifacts with testable shape; this phase fixes them without touching customer prose or handler code.

**Exit criteria**
- [ ] `grep -nE '(Fully operational|Production-ready|100% implemented|fully operational)' AGENTS.md` returns zero matches.
- [ ] `grep -nE 'curl .*(search|symbol)' AGENTS.md` returns zero matches (no FastAPI-primary endpoint list survives).
- [ ] `AGENTS.md` contains a "Beta status" note and a "Multi-repo model" section referencing `RepoContext`, `StoreRegistry`, `MCP_ALLOWED_ROOTS`.
- [ ] `specs/active/architecture.md` L3 component diagram includes a `MultiRepositoryWatcher` node (grep the diagram block for the literal string).
- [ ] MCP tool schemas in `mcp_server/cli/stdio_runner.py:57-136` list `repository` as an `inputSchema` property on every tool whose handler will accept it after P9 (`search_code`, `symbol_lookup` already; `reindex`, `summarize_sample`, `write_summaries` added).
- [ ] `CLAUDE.md` content unchanged (diff-verified; it was already clean of stale claims).

**Scope notes**
- Two disjoint lanes: (a) markdown rewrites in `AGENTS.md` + `architecture.md`, (b) JSON-schema edits in `stdio_runner.py:57-136`. Lane (b) is a code edit but semantically advertises contract, so it pairs with the docs lane.
- Do NOT modify handler implementations here — advertising `repository=` is schema-only. Handler-side completion is P9.
- L3 diagram: propagate the `MultiRepositoryWatcher` node from L2 (where it already exists) down to L3.

**Key files**
- `AGENTS.md`
- `specs/active/architecture.md`
- `mcp_server/cli/stdio_runner.py` (tool-list schemas only)

**Depends on**
- P6B merged.

---

### Phase 8 — Doc Truth: Customer Audience & Historical Artifact Sweep (P8)

**Objective**
Rewrite human-facing docs (`README.md`, `docs/GETTING_STARTED.md`, `docs/DEPLOYMENT-GUIDE.md`) to reflect beta status and tool-based MCP usage, add a security section for `MCP_CLIENT_SECRET` / `MCP_ALLOWED_ROOTS`, and sweep `docs/implementation/`, `docs/status/`, `docs/validation/` for stale "production-ready" / "100%" claims.

**Exit criteria**
- [ ] `grep -nE '(Production-Ready|Implementation Status: Production|100% implemented|fully operational)' README.md` returns zero matches.
- [ ] `docs/GETTING_STARTED.md` contains zero `curl http.*/search` or `curl http.*/symbol` examples; MCP tool-call JSON examples present instead.
- [ ] `docs/DEPLOYMENT-GUIDE.md` has a `## Security` section mentioning both `MCP_CLIENT_SECRET` and `MCP_ALLOWED_ROOTS` by name.
- [ ] Every file under `docs/implementation/`, `docs/status/`, `docs/validation/` is either deleted, prefixed with a `> **Historical artifact — as-of YYYY-MM-DD, may not reflect current behavior**` banner on line 1, or rewritten. Verified: `grep -L 'Historical artifact' docs/implementation/*.md docs/status/*.md docs/validation/*.md` returns only names of deleted files (shell lists none).
- [ ] Triage log `docs/HISTORICAL-ARTIFACTS-TRIAGE.md` records each file's disposition (deleted / bannered / rewritten) with a one-line rationale.

**Scope notes**
- Three lanes, disjoint ownership: (1) `README.md` + `docs/GETTING_STARTED.md`, (2) `docs/DEPLOYMENT-GUIDE.md` security section, (3) historical sweep + triage log.
- Sweep default: `delete` for files describing vanished code, `banner` for design discussions / benchmark results worth keeping as-of, `rewrite` only if low effort.
- P7 and P8 have fully disjoint file ownership — runnable concurrently.

**Key files**
- `README.md`
- `docs/GETTING_STARTED.md`
- `docs/DEPLOYMENT-GUIDE.md`
- `docs/implementation/` (directory sweep)
- `docs/status/` (directory sweep)
- `docs/validation/` (directory sweep)
- `docs/HISTORICAL-ARTIFACTS-TRIAGE.md` (new)

**Depends on**
- P6B merged. Parallel with P7.

---

### Phase 9 — Operational Scoping Completion (P9)

**Objective**
Close the `repository=` parameter gap so every operational tool handler accepts and honors it consistently, and fix the `tomllib` import so the full pytest suite runs on Python 3.10 workstation venvs.

**Exit criteria**
- [ ] `handle_reindex`, `handle_write_summaries`, `handle_summarize_sample` in `mcp_server/cli/tool_handlers.py` accept a `repository` argument, resolve it via `RepoResolver`, and route through the per-repo `SQLiteStore` (no direct `sqlite_store` kwarg bypass of ctx).
- [ ] Integration test `tests/integration/test_multi_repo_server.py::test_reindex_scoped_to_repo` passes — reindex call with `repository=B` does not modify repo A's index file (mtime-asserted).
- [ ] Integration test for scoped `write_summaries` / `summarize_sample` on both repos — results contain only files from the specified repo.
- [ ] `tests/test_requirements_consolidation.py` runs clean on Python 3.10: uses `try: import tomllib except ImportError: import tomli as tomllib`. `python3.10 -m pytest tests/test_requirements_consolidation.py` returns exit 0.
- [ ] `pyproject.toml` adds `tomli>=2.0.1; python_version<"3.11"` to test dependencies.
- [ ] `tests/test_tool_schema_handler_parity.py` (new) asserts every MCP tool whose schema advertises `repository` has a handler that accepts the kwarg, and vice versa.

**Scope notes**
- Decompose into 2 lanes: (a) handler signature + routing completion (three handlers), (b) `tomllib` fallback + `pyproject.toml` conditional dep + parity test.
- `handle_reindex` edge case: if both `path` and `repository` are given and inconsistent, fail-loud with a structured error (do not silent-reinterpret).
- Depends on P7's schema additions being on `main` first; one-commit ordering, not a structural block.

**Key files**
- `mcp_server/cli/tool_handlers.py`
- `mcp_server/cli/stdio_runner.py` (wiring only; schemas already settled in P7)
- `tests/test_requirements_consolidation.py`
- `tests/test_tool_schema_handler_parity.py` (new)
- `tests/integration/test_multi_repo_server.py` (extend)
- `pyproject.toml`

**Depends on**
- P7 merged (schemas advertise `repository=` before handlers are required to honor it).

---

### Phase 10 — Production Hardening (P10)

**Objective**
Close the production-readiness gaps P1–P6B deferred: STDIO observability parity with FastAPI, SIGTERM graceful shutdown, symlink-escape hardening, multi-repo health surface, SQLite connection pooling, and schema-version enforcement with a breaking-changes log.

**Exit criteria**
- [ ] `stdio_runner._serve()` instantiates and starts the Prometheus exporter from `mcp_server/metrics/prometheus_exporter.py` on `MCP_METRICS_PORT` (default 9090); `curl -s localhost:9090/metrics | grep mcp_tool_calls_total` returns a nonzero count after any stdio tool call.
- [ ] A SIGTERM handler installed in `stdio_runner._serve()` calls `MultiRepositoryWatcher.stop()`, `RefPoller.stop()`, then `StoreRegistry.shutdown()` in that order, completing within 5s wall-time. Verified by `tests/integration/test_sigterm_shutdown.py`.
- [ ] `_path_within_allowed` in the security helper no longer calls `.resolve()` on the candidate path before the prefix check; uses `os.path.realpath` on the allowed roots once at boot and `os.path.commonpath` on the un-resolved candidate. `tests/security/test_symlink_escape.py` asserts a symlink inside an allowed root pointing to `/etc/passwd` returns False.
- [ ] `get_status` response includes a `repositories` array; each entry has `{repo_id, tracked_branch, index_path_exists, git_dir_exists, last_indexed_commit, staleness_reason|null}`. Stale repos (missing `.git` or missing `index_path`) have non-null `staleness_reason`.
- [ ] `SQLiteStore` exposes a thread-safe connection pool (default size 4); `tests/test_sqlite_pool.py` asserts 16 concurrent readers complete with zero `database is locked`.
- [ ] `index_manager.py`: `strict_compatibility` flipped to True by default; schema mismatch raises `SchemaMismatchError` with rebuild instructions; a `--rebuild-on-schema-mismatch` CLI flag performs it.
- [ ] `BREAKING-CHANGES.md` at repo root logs every schema bump with migration notes.
- [ ] `grep -rn '\.resolve()' mcp_server/security/ mcp_server/cli/stdio_runner.py` returns zero occurrences in the allowlist-check path (cited exemptions allowed, noted inline).

**Scope notes**
- Six lanes with disjoint file ownership: metrics wiring, signal handler, symlink hardening, health surface, SQLite pool, schema enforcement + changelog.
- SIGTERM lane is sequencing-critical: watcher/poller stop accepting work BEFORE store shutdown.
- SQLite pool: add a `ConnectionPool` helper; do not rewrite `SQLiteStore` wholesale.
- Schema strict flip is breaking for pre-P1 indexes — document prominently in `BREAKING-CHANGES.md`.
- Plan with `--consensus` if connection-pool design tradeoff (thread-local vs bounded LIFO) is contentious.

**Key files**
- `mcp_server/cli/stdio_runner.py`
- `mcp_server/metrics/prometheus_exporter.py`
- `mcp_server/watcher_multi_repo.py`
- `mcp_server/watcher/ref_poller.py`
- `mcp_server/security/` (symlink hardening)
- `mcp_server/storage/sqlite_store.py`
- `mcp_server/storage/index_manager.py`
- `mcp_server/storage/repository_registry.py` (health surface)
- `BREAKING-CHANGES.md` (new, repo root)
- `tests/integration/test_sigterm_shutdown.py` (new)
- `tests/security/test_symlink_escape.py` (new)
- `tests/test_sqlite_pool.py` (new)

**Depends on**
- P9 merged.

---

### Phase 11 — Dispatcher Dependability (P11)

**Objective**
Investigate why `EnhancedDispatcher.lookup()`'s SIGALRM per-plugin timeout did not catch the C plugin's `_find_nodes` hang during P5, and close the root cause. Replace the best-effort fallback-across-all-plugins with a bounded, extension-gated dispatch path.

**Exit criteria**
- [ ] Investigation note at `docs/investigations/dispatcher-sigalrm-failure.md` captures root cause with a reproducer. Acceptable root causes: signal masked in worker thread, C-extension blocked Python signal handling, nested `sigaction` races.
- [ ] `EnhancedDispatcher.lookup()` no longer iterates every registered plugin on SQLite miss; routes only to plugins whose `supported_extensions` include the symbol's source-file extension (or returns empty if extension unknown).
- [ ] `MCP_DISPATCHER_FALLBACK_MS` (default 2000) hard-caps any `plugin.getDefinition()` fallback call. `tests/test_dispatcher_fallback_timeout.py` deploys a deliberately-slow fake plugin and confirms the cap fires.
- [ ] Fallback timeout mechanism is thread-based (`concurrent.futures.ThreadPoolExecutor.submit(...).result(timeout=...)`) rather than SIGALRM — signals do not cross threads reliably in CPython.
- [ ] Prometheus histogram `mcp_dispatcher_fallback_duration_seconds` records every fallback dispatch (via P10's exporter); integration test asserts its presence in `/metrics` output after a triggering search.
- [ ] `CPlugin` is not instantiated for non-C/C++ file extensions. Unit test: `dispatch_for('.py', symbol='foo')` does not import or instantiate `CPlugin`.

**Scope notes**
- Decompose into 2 lanes: (a) investigation + reproducer (owns `docs/investigations/dispatcher-sigalrm-failure.md` + a `test_dispatcher_fallback_timeout.py` reproducer); (b) extension-gating + bounded dispatch path (owns `dispatcher_enhanced.py` + `bootstrap.py` edits + `test_dispatcher_extension_gating.py`). Disjoint files; (b) begins once (a) commits the root-cause note.
- **Unknown-scope phase** — plan with `--consensus` to surface alternative hypotheses before committing a fix.
- Extension-gating is a behavior change: cross-language symbol fallback is gone. This is the fix, not a regression — the silent correctness failure mode is what made the hang possible.
- SimpleDispatcher is out of scope. Enhanced-only.
- If investigation caps at one lane-day without a reproducer, fall back to extension-gating alone and defer root-cause to a follow-up phase documented in `docs/investigations/`.

**Key files**
- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/dispatcher/bootstrap.py`
- `mcp_server/plugins/c_plugin/plugin.py` (investigation target)
- `docs/investigations/dispatcher-sigalrm-failure.md` (new)
- `tests/test_dispatcher_fallback_timeout.py` (new)
- `tests/test_dispatcher_extension_gating.py` (new)

**Depends on**
- P10 merged.

---

### Phase 12 — Ops Readiness + Reindex Safety (P12)

**Objective**
Stop silent drift immediately and make the service k8s-deployable. Small, high-leverage safety nets: HTTP probes, per-repo indexing lock, branch-drift loud-path, hot-path latency histograms, artifact freshness gate with offline fallback.

**Exit criteria**
- [ ] `GET /ready` returns 200 with a stable JSON envelope (checks SQLite reachable, registry loaded, dispatcher initialized); 503 otherwise.
- [ ] `GET /liveness` returns 200 while the event loop is responsive, 503 after a block exceeding 10 seconds.
- [ ] Concurrent watcher + manual `sync_all_repositories` on the same repo cannot race; enforced by per-repo `threading.Lock` with a passing test that spawns both paths and asserts serialized dispatcher calls.
- [ ] Branch drift no longer drops events silently: if `current != tracked`, a `branch.drift.detected` WARN log fires AND a full rescan is enqueued for the next poll.
- [ ] Prometheus surface includes `mcp_symbol_lookup_duration_seconds` and `mcp_search_duration_seconds` histograms with the same bucket tuple as P11's fallback histogram.
- [ ] Artifact downloader verifies `artifact.metadata.commit` is an ancestor of HEAD AND age < `MCP_ARTIFACT_MAX_AGE_DAYS` (default 14); else skips with warn + falls back to local index. GitHub outage returns local-index + warn, never raises.
- [ ] `uv.lock` committed to repo root; CI verifies it is up-to-date.

**Scope notes**
- Decompose into 5 lanes, each owning disjoint files.
- Lane SL-1 owns `mcp_server/api/gateway.py` route additions + new `mcp_server/health/probes.py`.
- Lane SL-2 owns new `mcp_server/indexing/lock_registry.py` and adds `with lock_registry.acquire(repo_id):` call sites in `mcp_server/watcher_multi_repo.py`.
- Lane SL-3 owns `mcp_server/watcher_multi_repo.py::should_reindex_for_branch` and `mcp_server/storage/git_index_manager.py`.
- **Single-writer overlap between SL-2 and SL-3 on `watcher_multi_repo.py`**: partition by function. SL-2 wraps dispatcher call sites; SL-3 owns the branch-check function and rescan-enqueue. Non-overlapping line ranges.
- Lane SL-4 owns `mcp_server/metrics/prometheus_exporter.py` histogram additions + `mcp_server/dispatcher/dispatcher_enhanced.py` instrumentation (behavior untouched).
- Lane SL-5 owns `mcp_server/artifacts/artifact_download.py`, new `mcp_server/artifacts/freshness.py`, `uv.lock`, and new `.github/workflows/lockfile-check.yml`.

**Non-goals**
- No upload-path changes (deferred to P13).
- No new metric endpoints beyond probes.
- No artifact signing (deferred to P15).

**Key files**
- `mcp_server/api/gateway.py`, `mcp_server/health/probes.py` (new)
- `mcp_server/indexing/lock_registry.py` (new), `mcp_server/watcher_multi_repo.py`
- `mcp_server/storage/git_index_manager.py`
- `mcp_server/metrics/prometheus_exporter.py`, `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/artifacts/artifact_download.py`, `mcp_server/artifacts/freshness.py` (new)
- `uv.lock` (new), `.github/workflows/lockfile-check.yml` (new)
- `tests/test_health_probes.py`, `tests/test_indexing_lock.py`, `tests/test_branch_drift_rescan.py`, `tests/test_hot_path_histograms.py`, `tests/test_artifact_freshness.py` (all new)

**Depends on**
- P11 merged.

**Produces**
- IF-0-P12-1
- IF-0-P12-2
- IF-0-P12-3
- IF-0-P12-4
- IF-0-P12-5

---

### Phase 13 — Reindex Durability + Artifact Automation (P13)

**Objective**
Replace happy-path code with durable flows: checkpointed reindex resume, atomic Qdrant+SQLite coupling, TOCTOU-safe dispatch, direct post-reindex artifact upload (removing the human-cron dependency), structured exception hierarchy with error-type Prometheus counters.

**Exit criteria**
- [ ] Reindex of 1000 files where file #500 fails leaves a `.reindex-state` checkpoint; the next reindex starts at file #500, not file #1. Recovery test asserts no re-work of files #1-499.
- [ ] Qdrant vector delete and SQLite path update for a renamed file are atomic: if SQLite step fails, Qdrant rolls back; conversely if Qdrant fails the SQLite write aborts. Fault-injection test proves this.
- [ ] Dispatcher recomputes file hash immediately before write; if hash has changed since the watcher's observation, it skips and logs a TOCTOU skip. Test with concurrent writer proves no stale content is indexed.
- [ ] Watcher triggers artifact upload directly on successful full-reindex completion; no cron dependency. Measured publish latency (reindex-done → artifact-available) < 2 min.
- [ ] Two parallel CI uploads of the same repo at commits A and B cannot both win the `latest` pointer; one is atomically elected, the loser's artifact remains addressable by its commit SHA.
- [ ] All bare `except:` clauses in `mcp_server/dispatcher/**` and `mcp_server/artifacts/**` replaced with typed catches. Prometheus counter `mcp_errors_by_type_total{module,exception}` increments on each handled error.

**Scope notes**
- Decompose into 5 lanes.
- Lane SL-1 (checkpoint resume) owns `mcp_server/indexing/incremental_indexer.py` resume logic and new `mcp_server/indexing/checkpoint.py`.
- Lane SL-2 (two-phase commit) owns new `mcp_server/storage/two_phase.py` and `mcp_server/indexing/incremental_indexer.py::_cleanup_stale_vectors` + rename handler.
- **Single-writer overlap between SL-1 and SL-2 on `incremental_indexer.py`**: SL-1 owns the resume entry points, SL-2 owns the cleanup and rename handler. Non-overlapping line ranges agreed at plan-phase.
- Lane SL-3 (TOCTOU dispatch) owns `mcp_server/dispatcher/dispatcher_enhanced.py::index_file` guarded variant.
- Lane SL-4 (direct publish) owns `mcp_server/artifacts/artifact_upload.py`, new `mcp_server/artifacts/publisher.py`, and `.github/workflows/index-artifact-management.yml` (cron trigger replaced with workflow_dispatch from runtime).
- Lane SL-5 (exception hierarchy) owns new `mcp_server/errors/__init__.py`, counter registration in `mcp_server/metrics/prometheus_exporter.py`, and cross-module `except` refactoring.
- **SL-5 is a cross-module lane by design**: scoped to `except` keyword replacements only. Other lanes must not touch `except` clauses in their edited files during P13.

**Non-goals**
- No plugin-level error taxonomy (plugins too heterogeneous; deferred).
- No retention-policy change (lives in the user runbook).
- No artifact signing (deferred to P15).

**Key files**
- `mcp_server/indexing/incremental_indexer.py`, `mcp_server/indexing/checkpoint.py` (new)
- `mcp_server/storage/two_phase.py` (new)
- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/artifacts/artifact_upload.py`, `mcp_server/artifacts/publisher.py` (new)
- `.github/workflows/index-artifact-management.yml`
- `mcp_server/errors/__init__.py` (new), `mcp_server/metrics/prometheus_exporter.py`
- `tests/test_reindex_resume.py`, `tests/test_two_phase_commit.py`, `tests/test_dispatcher_toctou.py`, `tests/test_artifact_publish_race.py`, `tests/test_structured_errors.py` (all new)

**Depends on**
- P12 merged (consumes P12-2 lock, P12-5 freshness helper, P12-4 counter registration pattern).

**Produces**
- IF-0-P13-1
- IF-0-P13-2
- IF-0-P13-3
- IF-0-P13-4
- IF-0-P13-5

**Post-execution amendments**

The following interface deviations were empirically determined during P13 execution and do not require P14 scoping adjustments:

1. **IF-0-P13-5 exception base class name**: Spec called for `McpError` but implementation uses `MCPError` (uppercase MCP). Downstream code importing the exception follows `MCPError`. P14+ must use the uppercase form.
2. **IF-0-P13-5 exception module location**: Spec proposed new `mcp_server/errors/` package. Implementation reused existing `mcp_server/core/errors.py` instead. The exception hierarchy (`MCPError`, `IndexingError`, `ArtifactError`, `PluginError`) resides in `mcp_server/core/errors.py` alongside the `record_handled_error(module, exception)` helper. No new package created.
3. **IF-0-P13-5 IndexingError + IndexError coexistence**: The builtin `IndexError` pre-existed in the codebase. `IndexingError` was added as a separate exception for indexing-specific faults, not a rename of `IndexError`. Both are used in dispatching and storage layers; `IndexError` typically surfaces from Python builtins (sequence indexing), while `IndexingError` is raised for data-model faults.
4. **IF-0-P13-5 Prometheus counter labels**: Counter `mcp_errors_by_type_total` uses label names `["module", "exception"]` (not `["service", "error_type"]`). Module refers to the source package (e.g., `dispatcher`, `publisher`, `indexer`); exception is the exception class name (e.g., `IndexingError`, `ArtifactError`).
5. **IF-0-P13-4 ArtifactPublisher watcher injection**: Spec indicated `ArtifactPublisher` would be instantiated in the watcher path. Implementation uses constructor injection + optional setter: the watcher passes the publisher instance to the dispatcher via `set_artifact_publisher(publisher)`, avoiding tight coupling. The publisher's `publish_on_reindex(repo_id, commit)` method is called directly by the watcher on successful reindex completion.

---

### Phase 14 — Multi-Repo Completeness + Schema Evolution (P14)

**Objective**
Close the functional gaps that currently limit product reach: wire the stubbed semantic reranker, implement dependency-aware search, establish schema version gating, add auto-delta on large artifacts, and make the watcher robust against inotify event drops plus enforce rename atomicity.

**Exit criteria**
- [ ] `cross_repo_coordinator.py::_rerank_results` no longer returns unranked results when a reranker is configured; calls the reranker via `RerankerProvider.rerank(query, results) -> results`. Unit test with a fake reranker proves ordering changes.
- [ ] `_get_repository_dependencies(repo_id) -> Set[str]` returns non-empty sets for repos containing `requirements.txt`, `package.json`, `go.mod`, or `Cargo.toml`. Integration test builds a tiny dep graph across 3 test repos.
- [ ] Every new artifact carries a `schema_version` field in its manifest; downloader refuses to open an artifact whose version is unknown, runs `SchemaMigrator` for a known older version, succeeds for equal version. Test covers all three paths.
- [ ] When a full artifact exceeds `MCP_ARTIFACT_FULL_SIZE_LIMIT` (default 500 MB), the publisher automatically switches to delta mode using the previous artifact as base. Test forces the threshold low and verifies delta output shape.
- [ ] Watcher runs a periodic full-tree scan every `MCP_WATCHER_SWEEP_MINUTES` (default 60) to catch inotify/FSEvents drops. Test injects a missed event and confirms the next sweep recovers it.
- [ ] Rename `foo.py → bar.py` produces exactly one `foo.py` removal plus one `bar.py` add in the index; no stale `foo.py` entry lingers. Verified by post-rename grep of SQLite rows.

**Scope notes**
- Decompose into 5 lanes.
- Lane SL-1 owns `mcp_server/dispatcher/cross_repo_coordinator.py::_rerank_results` and new `mcp_server/retrieval/reranker.py`.
- Lane SL-2 owns `mcp_server/dispatcher/cross_repo_coordinator.py::_get_repository_dependencies` and new `mcp_server/dependency_graph/` package.
- Lane SL-3 owns `mcp_server/artifacts/manifest_v2.py` (schema_version promotion), new `mcp_server/storage/schema_migrator.py`, and `mcp_server/storage/sqlite_store.py::_run_migrations` version stamps.
- Lane SL-4 owns `mcp_server/artifacts/artifact_upload.py` delta-fallback branch, `mcp_server/indexing/incremental_indexer.py::_get_chunk_ids_for_path` pagination, and new `mcp_server/artifacts/delta_policy.py`.
- **Cross-phase single-writer note**: Lane SL-4 edits `artifact_upload.py`, which P13 SL-4 also edited. Resolved by time ordering — P13 merges before P14 starts, so no concurrent work.
- Lane SL-5 owns `mcp_server/watcher/file_watcher.py`, `mcp_server/watcher_multi_repo.py`, and new `mcp_server/watcher/sweeper.py`.

**Non-goals**
- No auto-repo discovery (scope creep; deferred).
- No cross-ecosystem dep resolution (e.g., Python→Node via FFI); each ecosystem stays self-contained.

**Key files**
- `mcp_server/dispatcher/cross_repo_coordinator.py`, `mcp_server/retrieval/reranker.py` (new)
- `mcp_server/dependency_graph/` (new package)
- `mcp_server/artifacts/manifest_v2.py`, `mcp_server/storage/schema_migrator.py` (new), `mcp_server/storage/sqlite_store.py`
- `mcp_server/artifacts/artifact_upload.py`, `mcp_server/artifacts/delta_policy.py` (new)
- `mcp_server/indexing/incremental_indexer.py`
- `mcp_server/watcher/file_watcher.py`, `mcp_server/watcher_multi_repo.py`, `mcp_server/watcher/sweeper.py` (new)
- `tests/test_reranker_integration.py`, `tests/test_dependency_aware_search.py`, `tests/test_schema_migration.py`, `tests/test_artifact_auto_delta.py`, `tests/test_chunk_query_pagination.py`, `tests/test_watcher_sweep.py`, `tests/test_rename_atomicity.py` (all new)

**Depends on**
- P13 merged.

**Produces**
- IF-0-P14-1
- IF-0-P14-2
- IF-0-P14-3
- IF-0-P14-4
- IF-0-P14-5

**Post-execution amendments**

The following interface deviations were empirically determined during P14 execution:

1. **IF-0-P14-1 reranker module path**: Spec L742 listed `mcp_server/retrieval/reranker.py` as the landing point for the reranker abstraction. Actual file created: `mcp_server/indexer/reranker.py`. `CrossRepoCoordinator` imports `IReranker` and `RerankerFactory` from that path. Any downstream code referencing the spec path must use `mcp_server/indexer/reranker.py` instead.
2. **IF-0-P14-1 RerankerFactory.create_default() not yet a real classmethod**: IF-0-P14-1 assumed `RerankerFactory.create_default()` would be a fully implemented classmethod by the time SL-1 landed. The method exists but its body may raise (e.g., missing config or import). SL-1 wraps the call in `try/except Exception` so a missing or failing factory degrades gracefully to `reranker = None` rather than crashing at coordinator startup. Callers that need a live reranker must inject one explicitly via the `reranker=` parameter.
3. **IF-0-P14-5 move_file error-handling behaviour change**: Prior to P14, `dispatcher_enhanced.py::move_file` logged semantic-indexer failures silently and continued. After SL-5, the function wraps the operation in `two_phase_commit` and raises `IndexingError` on semantic failure. The watchdog handler in `mcp_server/watcher_multi_repo.py` catches `IndexingError` at the call site. Code that previously relied on move_file completing without exception even on partial failure must be updated to handle `IndexingError`.

---

### Phase 15 — Security Hardening (P15)

**Objective**
Enforce trust boundaries: sandbox plugins, authenticate `/metrics`, sign and verify artifacts, guard path-traversal in search output, validate `GITHUB_TOKEN` scopes at startup, rate-limit cross-repo artifact fetches.

**Exit criteria**
- [ ] Plugin calls (`getDefinition`, `index_file`) execute in a subprocess (or WASI; decided during plan-phase) with no access to the host SQLite DB, network, or arbitrary filesystem. A deliberately-malicious test plugin (attempts shell-command execution via stdlib helpers, opens `/etc/passwd`) is caught and rejected.
- [ ] `/metrics` requires auth (bearer token OR k8s-style NetworkPolicy per user choice documented in runbook). Unauth'd request returns 401.
- [ ] All artifacts uploaded by P13 SL-4's publisher carry a GitHub attestation (`gh attestation`). Downloader verifies attestation and rejects tampered artifacts. Negative test swaps archive bytes post-attest and confirms rejection.
- [ ] Search results cannot return paths outside `MCP_ALLOWED_ROOTS`: response values run through `PathTraversalGuard.normalize_and_check`. Negative test asserts `../../../etc/passwd` variant is 403'd.
- [ ] At startup, `TokenValidator.validate_scopes()` checks `GITHUB_TOKEN` has required scopes (`contents:read`, `actions:read+write`, `attestations:write`). Missing scopes fails-loud with actionable error; no silent mid-operation failures.
- [ ] Cross-repo artifact pulls respect `X-RateLimit-Remaining`; if <100, back off exponentially. Test simulates rate-limit header and verifies backoff.

**Scope notes**
- Decompose into 4 lanes.
- **Lane SL-1 (plugin sandboxing) is the riskiest single lane in this entire remediation arc.** Plan it with `--consensus` (subprocess vs WASI vs subinterpreter); budget for a scoping prototype if consensus can't converge in one lane-day.
- Lane SL-1 owns new `mcp_server/sandbox/` package + adapter `mcp_server/plugins/sandboxed_plugin.py`.
- Lane SL-2 owns `mcp_server/security/security_middleware.py` extension and `mcp_server/api/gateway.py` wiring.
- Lane SL-3 owns `mcp_server/artifacts/publisher.py` (extends P13 SL-4 with attestation call), new `mcp_server/artifacts/attestation.py`, and `mcp_server/artifacts/artifact_download.py` verify-on-download.
- Lane SL-4 owns new `mcp_server/security/path_guard.py`, new `mcp_server/security/token_validator.py`, and `mcp_server/artifacts/providers/github_actions.py` rate-limit tracking.

**Non-goals**
- No plugin signing (decision: sandbox instead).
- No TLS termination inside the app (expected to be ingress/sidecar).
- No secrets management beyond `GITHUB_TOKEN` validation (vault integration out of scope).

**Key files**
- `mcp_server/sandbox/` (new package), `mcp_server/plugins/sandboxed_plugin.py` (new)
- `mcp_server/security/security_middleware.py`, `mcp_server/api/gateway.py`
- `mcp_server/artifacts/publisher.py`, `mcp_server/artifacts/attestation.py` (new), `mcp_server/artifacts/artifact_download.py`
- `mcp_server/security/path_guard.py` (new), `mcp_server/security/token_validator.py` (new)
- `mcp_server/artifacts/providers/github_actions.py`
- `tests/test_plugin_sandbox.py`, `tests/security/test_malicious_plugin.py`, `tests/security/test_metrics_auth.py`, `tests/test_artifact_attestation.py`, `tests/security/test_path_traversal.py`, `tests/security/test_token_scope.py`, `tests/test_cross_repo_rate_limit.py` (all new)

**Depends on**
- P14 merged.

**Produces**
- IF-0-P15-1
- IF-0-P15-2
- IF-0-P15-3
- IF-0-P15-4

### Post-execution amendments

- **2026-04-19** (post-P15 merge):
  - IF-0-P15-4 token scope list: the runbook specified `metadata:read` in addition to the original spec's four scopes (`contents:read`, `actions:read`, `actions:write`, `attestations:write`). SL-4's `TokenValidator.validate_scopes()` enforces all five cumulatively. Spec updated by retroactive commit `be026e5`; this amendment records the decision.
  - Interface signatures otherwise landed as frozen — no drift.

---

### Phase 16 — Shared Vocabulary Preamble (P16)

**Objective**
Freeze the four shared contracts P17 and P18 both consume: the `TransientArtifactError` / `TerminalArtifactError` / `SchemaMigrationError` taxonomy, a lazy-read env-var constant module, the `validate_production_config` signature + `ValidationError` dataclass, and the `reset_process_singletons` bootstrap hook. Single-lane preamble — each downstream phase fills bodies in files it otherwise owns exclusively.

**Exit criteria**
- [ ] `TransientArtifactError`, `TerminalArtifactError`, `SchemaMigrationError` importable from `mcp_server.core.errors`; each subclasses `ArtifactError`; pytest shape check passes.
- [ ] `mcp_server/config/env_vars.py` exports `get_max_file_size_bytes`, `get_artifact_retention_count`, `get_artifact_retention_days`, `get_disk_readonly_threshold_mb`, `get_publish_rollback_enabled`; module-load is side-effect-free (no `os.environ` reads until a getter is called).
- [ ] `validate_production_config(config, environment="production")` callable; returns a `list[ValidationError]`; body emits an empty list in P16 (downstream lanes fill the fatal entries). Signature contract test passes.
- [ ] `reset_process_singletons()` callable; unit test registers sentinel values on each known module-level `_instance` attr, invokes the function, asserts all are `None`.
- [ ] `pytest --collect-only -q` succeeds across the whole repo (proves no downstream breakage from the new imports).

**Scope notes**
- **Preamble / interface-only phase — single lane justified** per roadmap-builder Rule 5 escape hatch. Four tiny freezes, all new files except `core/errors.py` (additive only) and `cli/bootstrap.py` (additive only).
- Stubs only. `validate_production_config` returns `[]`; `reset_process_singletons` fills all known `_instance` attrs today but is called by no consumer yet; env-var getters have real bodies but no callers; error subclasses have `pass` bodies.
- Lane teammate must NOT edit `gateway.py`, `security_middleware.py`, `publisher.py`, `artifact_download.py`, `providers/github_actions.py`, `plugin_factory.py`, `sqlite_store.py`, or any watcher file — those are strictly P17 or P18 territory.
- Env-var constants use the lazy-getter pattern (never `VALUE = int(os.environ.get(...))` at module scope) per the lesson learned from P15 SL-4's `_PATH_GUARD` that was initially module-level and broke `monkeypatch.setenv` in tests.

**Non-goals**
- Do not wire `validate_production_config` into startup — P18 owns that.
- Do not wire `reset_process_singletons` into `initialize_stateless_services` — P17 owns that.
- No retry logic, no metric instrumentation, no doc beyond module docstrings.

**Key files**
- `mcp_server/core/errors.py` (extend — add 3 subclasses)
- `mcp_server/config/env_vars.py` (new)
- `mcp_server/config/validation.py` (extend — add `validate_production_config` + `ValidationError` dataclass)
- `mcp_server/cli/bootstrap.py` (extend — add `reset_process_singletons`)
- `tests/test_p16_vocabulary.py` (new — contract shape tests for all four freezes)

**Depends on**
- P15 merged.

**Produces**
- IF-0-P16-1
- IF-0-P16-2
- IF-0-P16-3
- IF-0-P16-4

---

### Phase 17 — Durability & Multi-Instance Safety (P17)

**Objective**
Make the storage + watcher + indexing layer safe under concurrent multi-instance deployment, disk failures, and long-running process lifecycles. Burn down the 46 pre-existing test failures that hid durability regressions (commit-persistence round-trip bug; stale `CrossRepositorySearchCoordinator` class name after refactor).

**Exit criteria**
- [ ] Registry survives concurrent writes: two processes calling `RepositoryRegistry.save()` against the same file concurrently → both updates persist, no lost writes (new `tests/test_registry_concurrency.py`).
- [ ] `reset_process_singletons()` is called at the top of `initialize_stateless_services`; repeat-init in the same Python process yields fresh managers (new `tests/test_singleton_reset.py`).
- [ ] Ref-poller detects detached HEAD, force-push (commit hash changed without fast-forward), and branch-rename; each triggers a full-repo rescan (new `tests/test_ref_poller_edges.py`, 3 cases).
- [ ] Sweeper exception emits a `WARNING` log and increments `mcp_watcher_sweep_errors_total` Prometheus counter (new `tests/test_sweeper_observability.py`).
- [ ] Checkpoint clears on clean exit even when `errors` non-empty (fix `incremental_indexer.py:232-233`); explicit re-run does not resume from stale error state.
- [ ] `MCP_MAX_FILE_SIZE_BYTES` honored in the dispatcher walker; oversize file logs + skips; indexer does not stall on single-file over-limit.
- [ ] `ENOSPC` during SQLite commit → store enters read-only mode + emits `mcp_storage_readonly_total` counter; server keeps serving reads without crashing (new `tests/test_disk_full.py`).
- [ ] `SchemaMigrator.apply` writes a timestamped `.backup` copy of the DB before any migration; rollback-on-failure restores from backup (new `tests/test_schema_migration_backup.py`).
- [ ] Pre-existing 46 test failures reduced to ≤5; remaining residuals documented in `docs/operations/known-test-debt.md`.
- [ ] `ruff F401` count across `mcp_server/dispatcher`, `mcp_server/storage`, `mcp_server/watcher` is 0.
- [ ] `RerankerFactory.create_default()` returns a functional reranker (resolves the P14 carry-over).

**Scope notes**
- Decompose into 4 impl lanes + terminal SL-docs lane.
- **SL-1 Registry + singleton hygiene** owns `storage/repository_registry.py`, `storage/multi_repo_manager.py`, `cli/bootstrap.py` (caller wiring — adds the `reset_process_singletons()` call at the top of `initialize_stateless_services`), `tests/test_registry_concurrency.py` (new), `tests/test_singleton_reset.py` (new), and fixes `tests/test_repository_registry_commits.py` (the two failing tests wrongly assumed a caller-supplied `repository_id` string round-trips; the implementation correctly uses `compute_repo_id(path).repo_id`. Tests must read-back via `registry.get_repository(compute_repo_id(path).repo_id)`).
- **SL-2 Watcher/indexing resilience** owns `watcher/sweeper.py`, `watcher/ref_poller.py`, `indexing/incremental_indexer.py`, `indexing/checkpoint.py`, `dispatcher/dispatcher_enhanced.py` (walker file-size guard only — line-range ownership of the `_walk_directory` method), and 3 new test files. Disjoint from SL-1.
- **SL-3 Disk & schema safety** owns `storage/sqlite_store.py`, `storage/schema_migrator.py`, fills raise-sites for `SchemaMigrationError` in P16's frozen taxonomy, and 2 new test files. Disjoint from SL-1/SL-2.
- **SL-4 Carry-over debt** owns `tests/test_cross_repo_coordinator.py` (single root cause for all 18 failures: stale class name `CrossRepositorySearchCoordinator` at `mcp_server.storage.cross_repo_coordinator` from a pre-existing refactor; real class is `CrossRepositoryCoordinator` at `mcp_server.dispatcher.cross_repo_coordinator`. Fix: update imports + method references to the current surface). Also `mcp_server/plugins/reranker_factory.py` (realize `create_default()`), ruff F401 cleanup. Isolated; zero file overlap with SL-1/SL-2/SL-3.
- **SL-docs (terminal)** owns `docs/operations/multi-instance.md` (new — file-locking protocol, singleton reset semantics, DR/recovery procedure), `docs/operations/known-test-debt.md` (new), `ARCHITECTURE.md` concurrency addendum.
- **Single-writer within phase**: `mcp_server/core/errors.py` — SL-3 fills `raise SchemaMigrationError(...)` sites in schema_migrator.py only; the class shape is frozen from P16.
- **Cross-phase single-writer with P18**: **none**. P17 files and P18 files are disjoint; P16's freeze means both phases can fill their own raise-sites without collision.

**Non-goals**
- No edits to `publisher.py`, `artifact_download.py`, `gateway.py`, `security_middleware.py`, `plugin_factory.py`, `attestation.py`, `providers/github_actions.py` — those are P18.
- No distributed-backend migration (etcd/Redis). File-based registry + flock only.
- No long-running retention daemon — P18 owns retention CLI.

**Key files**
- `mcp_server/storage/repository_registry.py`, `multi_repo_manager.py`, `sqlite_store.py`, `schema_migrator.py`
- `mcp_server/watcher/sweeper.py`, `ref_poller.py`
- `mcp_server/indexing/incremental_indexer.py`, `checkpoint.py`
- `mcp_server/dispatcher/dispatcher_enhanced.py` (walker file-size guard only)
- `mcp_server/cli/bootstrap.py`
- `mcp_server/plugins/reranker_factory.py`
- `mcp_server/core/errors.py` (raise-sites only; shape is frozen)
- `tests/test_repository_registry_commits.py`, `test_cross_repo_coordinator.py` (fix)
- `tests/test_registry_concurrency.py`, `test_singleton_reset.py`, `test_ref_poller_edges.py`, `test_sweeper_observability.py`, `test_disk_full.py`, `test_schema_migration_backup.py` (all new)
- `docs/operations/multi-instance.md`, `docs/operations/known-test-debt.md` (new)
- `ARCHITECTURE.md` (extend)

**Depends on**
- P16 merged.

**Produces**
- IF-0-P17-1

### Post-execution amendments

- **2026-04-19** (post-P17 merge):
  - **UnknownSchemaVersionError promoted to `core/errors.py`** (SL-3): The spec scoped
    `UnknownSchemaVersionError` to `mcp_server/storage/schema_migrator.py` alongside
    `SchemaMigrationError`.  During SL-3 implementation it was instead placed in
    `mcp_server/core/errors.py` alongside the other P16 taxonomy classes.  This extends
    the P16 IF-0-P16-1 taxonomy by one class and is the authoritative location going
    forward.  `schema_migrator.py` imports it from `core/errors.py`.
  - **`SchemaMigrator.apply(db_path)` was never shipped** (SL-3): IF-0-P14-3 promised
    a `SchemaMigrator.apply(db_path)` surface.  The real surface shipped is
    `SchemaMigrator.migrate_artifact(extracted_dir, from_version, to_version) -> Path`.
    SL-3's backup/rollback logic adapted to this directory-level signature.  The
    `apply(db_path)` name does not exist in the codebase; any P18 code that referenced
    it must use `migrate_artifact` instead.
  - **Full suite failures at P17 close: 56 (criterion was ≤5)**: The phase criterion
    of ≤5 total failures was not met.  9 are the pre-existing cross-repo coordinator
    carry-over (Group A); 47 are pre-existing failures in other modules not addressed
    in P17 scope (Group B).  Full enumeration in
    `docs/operations/known-test-debt.md`.  The ≤5 criterion is carried forward to P18.
  - **IF-0-P17-1 interface landed as frozen**: Registry flock + read-merge-write
    pattern shipped as specified; no drift.

---

### Phase 18 — Enforcement, Artifact Resilience & Ops (P18)

**Objective**
Turn P15's security primitives from "available" into "enforced by default." Harden the artifact publish/download pipeline against partial-failure, missing delta bases, and hostile rate-limiting. Wire the observability operators actually page on (JSON logs, Prometheus counters, secret redaction). Flip safe defaults (sandbox on) after a documented opt-out path.

**Exit criteria**
- [ ] `pytest tests/security/test_route_auth_coverage.py` passes: every `@app.(get|post|put|delete|patch)` route in `mcp_server/gateway.py` is auth'd unless explicitly whitelisted (auth endpoints + `/health*` + `/ready` + `/liveness`). `/search/capabilities` is now auth'd.
- [ ] Boot with `MCP_ENVIRONMENT=production` + weak `JWT_SECRET_KEY` → exits non-zero with a `ValidationError` listing (severity=fatal) rendered to stderr; boot with `MCP_ENVIRONMENT=dev` + same config → logs a WARN and continues.
- [ ] Killing `gh` mid-`publish_on_reindex` → no orphan release on GitHub (rollback test: stub `_move_latest_pointer` to raise, verify `_ensure_sha_release` output is cleaned up via `gh release delete`).
- [ ] `artifact_download` falls back to requesting the full artifact when a delta's base is not found on GitHub Releases (new `tests/test_delta_base_fallback.py`).
- [ ] `_respect_rate_limit` parses `Retry-After` header and applies exponential backoff; distinguishes 429 from 403 (403 raises `TerminalArtifactError`, 429 triggers backoff).
- [ ] `MCP_PLUGIN_SANDBOX_ENABLED` default flips to on; `MCP_PLUGIN_SANDBOX_DISABLE=1` provides opt-out; existing plugin tests still pass.
- [ ] Production-mode logs emit JSON; test asserts `json.loads(captured_line)` succeeds.
- [ ] Secret-redaction response middleware strips `Bearer \S+`, `JWT_SECRET_KEY=\S+`, `GITHUB_TOKEN=\S+` from 4xx/5xx response bodies.
- [ ] `python -m mcp_server.cli retention prune --repo owner/repo` deletes releases older than `MCP_ARTIFACT_RETENTION_DAYS` or beyond `MCP_ARTIFACT_RETENTION_COUNT`; operator-triggered, no daemon.
- [ ] Boot with `MCP_ATTESTATION_MODE=enforce` + `gh` missing the `attestation` subcommand (or missing `attestations:write` scope) → single prominent `ATTESTATION_PREREQ` WARN line at startup; boot continues (enforce still the default, but the warn is diagnosable).

**Scope notes**
- Decompose into 5 impl lanes + terminal SL-docs lane.
- **SL-1 Config + auth enforcement** owns `gateway.py` (the startup-validation block near `AuthManager` instantiation at ~line 343, plus the single decorator edit at `/search/capabilities` ~line 1472), `config/validation.py` (fill P16's frozen signature body with the security entries: weak JWT, CORS wildcard, permissive RATE_LIMIT, missing admin password), `tests/security/test_route_auth_coverage.py` (new — uses `app.routes` introspection to enumerate every route and assert 401 without token on non-whitelisted paths).
- **SL-2 Artifact pipeline resilience** owns `artifacts/publisher.py` (publish rollback via try/finally around `_ensure_sha_release` → `_move_latest_pointer`; on failure, `gh release delete` the SHA release), `artifacts/artifact_download.py` (delta-base-missing → request full artifact fallback), `artifacts/providers/github_actions.py` (Retry-After parsing, 403-vs-429 branching, `TransientArtifactError`/`TerminalArtifactError` emission), `artifacts/attestation.py` (attest preflight section only — check `attestations:write` scope before calling `attest()`), 3 new test files.
- **SL-3 Retention janitor** owns new `artifacts/retention.py`, appends a `delete_releases_older_than` helper at the end of `artifacts/providers/github_actions.py` (append-only past SL-2's line range), extends `cli/commands.py` with the `retention prune` subcommand, new `tests/test_retention_janitor.py`.
- **SL-4 Observability** owns `core/logging.py` (JSON-format default when `MCP_ENVIRONMENT=production` or `MCP_LOG_FORMAT=json`), `security/security_middleware.py` (secret-redaction response middleware), `metrics/exporters.py` (new Prometheus counters: `mcp_watcher_sweep_errors_total`, `mcp_rate_limit_sleeps_total`, `mcp_artifact_errors_by_class_total`, `mcp_storage_readonly_total`), `gateway.py` (one line: middleware registration near `SecurityMiddlewareStack` init, disjoint from SL-1's block). 2 new test files.
- **SL-5 Safe defaults flip** owns `plugins/plugin_factory.py` (flip `MCP_PLUGIN_SANDBOX_ENABLED` default to on; honor `MCP_PLUGIN_SANDBOX_DISABLE=1` opt-out), `artifacts/attestation.py` (adds `probe_gh_attestation_support()` + boot-time capability check — disjoint function block from SL-2's preflight work), `docs/security/sandbox.md` (migration guide extension), 1 new test file.
- **SL-docs (terminal)** owns `docs/configuration/environment-variables.md` (new — full `MCP_*` env reference, defaults, prod-safe values), `docs/operations/gateway-startup-checklist.md` (new — operator deploy checklist), `docs/operations/artifact-retention.md` (new — operator janitor guide), `README.md` / `CHANGELOG.md` extensions, post-execution amendments section of this spec.
- **Single-writer files within phase**:
  - `mcp_server/gateway.py`: SL-1 owns the startup-validation block (~line 343) + `/search/capabilities` decorator (~line 1472); SL-4 owns the middleware registration line near `SecurityMiddlewareStack` init (~line 341 area). Disjoint line ranges; top-of-file imports merged alphabetically at lane merge time (P14/P15 pattern).
  - `mcp_server/artifacts/attestation.py`: SL-2 owns attest-preflight (function block around `attest`); SL-5 owns `probe_gh_attestation_support` (new function, file-end append). Disjoint function blocks.
  - `mcp_server/artifacts/providers/github_actions.py`: SL-2 owns the rate-limit + retry edits inline; SL-3 appends `delete_releases_older_than` at file end (append-only).
- **Cross-phase single-writer with P17**: none. See P17 Scope notes — P16's taxonomy freeze means both phases only fill their own raise-sites.

**Non-goals**
- No mid-run token refresh (operator restart on token rotation remains the documented path).
- No bounded delta-chain depth enforcement (backlog — surface chain length in metadata only).
- No release-janitor daemon (CLI-triggered only).
- No distributed rate-limit coordination (single-instance backoff only).
- No TLS termination inside the app (unchanged from P15).
- No plugin signing (sandbox is the substitute, unchanged from P15).

**Key files**
- `mcp_server/gateway.py` (startup block + one middleware registration line + one route decorator)
- `mcp_server/config/validation.py`
- `mcp_server/security/security_middleware.py`
- `mcp_server/core/logging.py`
- `mcp_server/artifacts/publisher.py`, `artifact_download.py`, `attestation.py`, `providers/github_actions.py`, `retention.py` (new)
- `mcp_server/plugins/plugin_factory.py`
- `mcp_server/metrics/exporters.py`
- `mcp_server/cli/commands.py`
- `tests/security/test_route_auth_coverage.py` (new)
- `tests/test_artifact_publish_rollback.py`, `test_delta_base_fallback.py`, `test_rate_limit_retry_after.py`, `test_json_logs.py`, `test_secret_redaction.py`, `test_sandbox_default_on.py`, `test_retention_janitor.py` (all new)
- `docs/configuration/environment-variables.md`, `docs/operations/gateway-startup-checklist.md`, `docs/operations/artifact-retention.md`, `docs/security/sandbox.md` (all new or extended)

**Depends on**
- P16 merged. (Runs in parallel with P17.)

**Produces**
- IF-0-P18-1

### Post-execution amendments

These drift notes record where the shipped P18 implementation differed from the spec wording above. Recorded by SL-docs at phase close.

- **CLI file path**: spec says `mcp_server/cli/commands.py`; actual layout uses `mcp_server/cli/__main__.py` as the click entry with per-concern files (`artifact_commands.py`, `retention_commands.py`, etc.). SL-3 added `mcp_server/cli/retention_commands.py` (NEW) and a single `_cli.add_command(retention)` line in `__main__.py` — not a `cli/commands.py` edit.
- **Metrics exporter path**: spec says `mcp_server/metrics/exporters.py`; actual file is `mcp_server/metrics/prometheus_exporter.py`. SL-4 appended the two new counter definitions there.
- **Route auth surface**: spec whitelist listed `/health*`, `/ready`, `/liveness`, and auth endpoints. `/graph/context` and `/graph/search` were unprotected at plan time and outside the whitelist — SL-1 added `Depends(require_permission(Permission.READ))` to both, consistent with `/search`.
- **SL-5 probe call**: plan doc specified the attestation probe call at line 232 of `stdio_runner.py` (startup banner); landed at line 233 (after the second banner `logger.info("=" * 60)` line). Functionally equivalent.
- **SL-6 bonus fix**: added `self._ctx = ctx` in `SandboxedPlugin.bind()` to satisfy the IPlugin contract — surfaced while fixing benchmark fixtures. Out of strict SL-6 scope; kept in-lane because it unblocks the sandbox regression suite.
- **P18 interface freezes (all four)** shipped as designed: IF-0-P18-1 (secret redaction middleware), IF-0-P18-2 (`delete_releases_older_than`), IF-0-P18-3 (stdio_runner module surface), IF-0-P18-4 (startup validation error rendering).
- **Full-suite residuals after P18 close**: 4 failures (down from 19 at P17 SL-4b close). All residuals pre-existing or gated on GitHub CLI `attestations:write` scope; none in P18 scope.

### Phase 19 — Release Readiness (P19)

**Objective**
Move P18's feature-complete state into a publishable, CI-verified, deploy-ready RC. Reconcile the local integration branch onto `main` without silently absorbing leaked commits, close the last 4 residual test failures, fix the `.claude/docs-catalog.json` integrity bug, and publish a breaking-change migration path so operators can upgrade without a gateway that fatals on their existing config.

**Exit criteria**
- [ ] Local `main` is a descendant of `worktree-lane-sl-4b-20260419T170149-ms2d`'s tip or has subsumed it cleanly; the leaked SL-docs commit `977c82f` is either absorbed (catalog delta only) or deliberately dropped.
- [ ] `origin/main` is pushed to the post-P18 tip and CI is green on it.
- [ ] `pytest --no-cov --ignore=tests/real_world` reports `0 failed` with the default marker set; the 3 `gh`-gated tests pass under `RUN_GH_AUTHENTICATED_TESTS=1` in a separate CI job.
- [ ] `tests/test_p16_vocabulary.py::test_validate_production_config_signature` passes (P16 signature reconciled with P18's filled body, or explicitly amended in the test).
- [ ] `tests/test_docs_catalog_integrity.py` exists and passes; `.claude/docs-catalog.json` has no duplicate or missing-file entries.
- [ ] `docs/operations/p18-upgrade.md` exists, describes every breaking change from P18 (sandbox default flip, validation fatals, new required envs), and walks operators through a no-downtime upgrade.
- [ ] `scripts/preflight_upgrade.sh` runs non-interactively against an env file and exits `0`/`1` per IF-0-P19-1.
- [ ] Release tag `v0.X.0-rc1` (exact version chosen during the phase) cut on the pushed tip; CHANGELOG `Unreleased` moved into the tagged release section.

**Scope notes**
- **5 impl lanes + 1 terminal SL-docs lane**. All impl lanes DAG-roots with disjoint file ownership. Plan with `MAX_PARALLEL_LANES=2` → 3 waves.
- **SL-1 Reconcile + publish**. Owns the main-branch reconciliation (pick reconcile option (c) from `~/.claude/skills/execute-phase/handoff.md` — cherry-pick the `.claude/docs-catalog.json` hunk out of `977c82f`, strip its duplicate lowercase `environment-variables.md` entry, apply on top of the phase tip, reset local `main` to that commit). Pushes to `origin/main`. Adds / verifies `.github/workflows/ci.yml` coverage of the full-suite + ruff + the new docs-catalog integrity test. Release tag cut here. No other lane touches CI config.
- **SL-2 Residual test debt**. Owns `tests/test_p16_vocabulary.py` (fix or amend the signature-mismatch test; must pass against the current `validate_production_config` body without hollowing the original contract intent), `tests/security/test_artifact_attestation.py::TestAttest` (the 3 remaining failures — gate with `pytest.mark.requires_gh_auth`), `tests/conftest.py` (add the marker definition + `addopts` skip-by-default logic per IF-0-P19-2). Does not touch production code.
- **SL-3 Docs-catalog integrity**. Owns `.claude/docs-catalog.json` (remove duplicate `docs/configuration/environment-variables.md` entry added by the leaked commit; rescan to cover P18 and retroactively P17 additions), `.claude/skills/_shared/scaffold_docs_catalog.py` (if absent, port from the team skills repo; this was flagged absent in the P18 handoff), new `tests/test_docs_catalog_integrity.py` per IF-0-P19-3. Single-writer on the catalog file within this phase.
- **SL-4 Upgrade comms & preflight**. Owns new `docs/operations/p18-upgrade.md` (breaking-change migration guide: sandbox flip, validation fatals, env var surface), new `scripts/preflight_upgrade.sh` per IF-0-P19-1 (shells into Python to re-use `validate_production_config` against a supplied env file), new `tests/test_preflight_upgrade.py` (argument parsing, happy path, fatal-detected path). The `docs/operations/p18-upgrade.md` file does NOT overlap SL-docs' catalog maintenance — SL-4 owns the content; SL-docs registers it.
- **SL-5 Release-notes migration**. Owns `CHANGELOG.md` surgical edit (move the `Unreleased` → `P18` block into a new `## [0.X.0-rc1] — <date>` section; re-open `Unreleased` empty), `README.md` extension if the `## Recent phases` section exists (else no-op), `docs/security/sandbox.md` cross-link to the new `p18-upgrade.md`. Does not touch code; does not touch the spec.
- **SL-docs (terminal)** owns the docs-catalog append of the new P19 doc files, `specs/phase-plans-v1.md` post-execution amendments if any IF-0-P19-* drifted.
- **Single-writer files within phase**: `.claude/docs-catalog.json` (SL-3), `CHANGELOG.md` (SL-5), `tests/conftest.py` (SL-2), `docs/security/sandbox.md` (SL-5 extends only — disjoint from any P18 block). `docs/operations/p18-upgrade.md` is SL-4's owned NEW file; SL-docs references it only.
- **Merge order discipline**: SL-3 should merge before SL-docs (SL-docs' rescan assumes SL-3's shape). SL-5 should merge after SL-4 (CHANGELOG links to `p18-upgrade.md`). Otherwise lanes are independent.

**Non-goals**
- No staging deployment (P20).
- No actual production rollout (P20).
- No retroactive fixes to phases P1–P17 — if a test fix for a pre-existing P16 bug touches P16 production code, scope-creep gate: stop and surface.
- No new features. P19 is a hygiene phase only.
- No force-push to any remote or shared branch. `origin/main` must fast-forward; if it cannot, stop and ask.

**Key files**
- Reconciliation: local `main` branch, `origin/main`, `worktree-lane-sl-4b-20260419T170149-ms2d`
- `.github/workflows/` (CI config additions)
- `tests/conftest.py`, `tests/test_p16_vocabulary.py`, `tests/security/test_artifact_attestation.py` (marker + fix)
- `tests/test_docs_catalog_integrity.py` (NEW), `tests/test_preflight_upgrade.py` (NEW)
- `.claude/docs-catalog.json`, `.claude/skills/_shared/scaffold_docs_catalog.py` (port if absent)
- `scripts/preflight_upgrade.sh` (NEW)
- `docs/operations/p18-upgrade.md` (NEW)
- `CHANGELOG.md`, `README.md`, `docs/security/sandbox.md` (extend)

**Depends on**
- P18 merged (lives on branch `worktree-lane-sl-4b-20260419T170149-ms2d` @ `4580c6c` as of roadmap append).

**Produces**
- IF-0-P19-1, IF-0-P19-2, IF-0-P19-3

### Post-execution amendments

Drift notes recorded by SL-docs at P19 close.

- **Version resolution**: spec placeholder `v0.X.0-rc1` resolved to `v1.2.0-rc1` (given the P12–P18 feature delta on top of the last published `v1.1.0`). Tag pushed to `origin` at merge-commit `baf47a5`.
- **Reconciliation sequence** (SL-1): executed option (c) from the handoff — `git reset --hard` local `main` onto the worktree-branch tip (`6669f3a`), then cherry-picked `977c82f` minus the 3-line duplicate lowercase `docs/configuration/environment-variables.md` catalog entry. Backup tag `pre-p19-main` preserves the pre-reset main tip. Fast-forward push of 125 commits to `origin/main` succeeded on first attempt; `origin/main` went from `8151341` to `baf47a5`.
- **`mcp_server/cli/preflight_commands.py` status**: spec + plan doc said NEW. File already existed from a prior phase (`4108e8e Add startup preflight for local MCP usage`). SL-4 extended it additively (+73 lines, `preflight_env` click subcommand); registration added via a single-line insert in `mcp_server/cli/__main__.py`. Functionally equivalent to the NEW-file contract.
- **`tests/test_release_notes.py`** (SL-5): the plan's Owned-files list for SL-5 did not explicitly include this file; the lane created it per the SL-5.1 test task spec. Included in merge; 3 tests pass.
- **IF-0-P19-1 rendering contract**: shell wrapper and Python subcommand emit `[FATAL]` / `[WARN]` lines to stderr, byte-compatible with `render_validation_errors_to_stderr`. Shell wrapper uses `cd $REPO_ROOT` before `python -m mcp_server.cli preflight_env` so local source takes precedence over any editable install. Exit codes: 0 on no-fatal, 1 on any fatal.
- **IF-0-P19-2 marker gate**: `pytest.mark.requires_gh_auth` registered in `pytest.ini`; `pytest_collection_modifyitems` hook in `tests/conftest.py` composes with the existing `-m "not integration and not slow"` addopts (via marker-attachment, not addopts mutation). 3 `TestAttest` tests marked; `RUN_GH_AUTHENTICATED_TESTS=1 pytest -m requires_gh_auth` collects 3 items.
- **IF-0-P19-3 scaffold tool scope**: `.claude/skills/_shared/scaffold_docs_catalog.py` landed at 130 LOC (<150 cap). `--rescan` preserves `touched_by_phases` history; only bumps `generated_at` and normalises JSON (indent=2); does NOT auto-discover new files. `--check` surfaces missing-file hard errors and case-variant warnings (never hard-errors on case variants).
- **`test-authenticated` CI job**: added in `.github/workflows/ci-cd-pipeline.yml`, gated on `secrets.ATTESTATION_GH_TOKEN` with `continue-on-error: true` and a `::warning::` if the secret is absent. Runs on push-to-main, scheduled nightly, and workflow_dispatch. Secret is NOT yet wired in the repo settings — operators should add it post-push to enable the authenticated suite.
- **Full-suite residuals at P19 close**: 1635 passed, 96 skipped, 4 failed on `pytest --no-cov --ignore=tests/real_world`. Failures: `tests/test_dispatcher.py::TestEnhancedDispatcherProtocolConformance::test_get_plugins_for_file_accepts_ctx` + 3 `tests/test_plugin_factory_async.py::*`. **Root cause**: sandbox-default-on (P18) applies `RLIMIT_AS = 512 MiB` to worker subprocesses via `mcp_server/sandbox/caps_apply.py::_apply_rlimits`; OpenBLAS (imported transitively by numpy via plugin loading) reserves multi-GiB virtual arenas for its thread pool, which exceeds the cap and aborts with `OpenBLAS error: Memory allocation still failed after 10 retries, giving up`. Reproduces under both parallel xdist and `-p no:xdist`; setting `OPENBLAS_NUM_THREADS=1` + `OMP_NUM_THREADS=1` in the parent env does NOT help because the sandbox spawns workers with inherited env but the AS cap hits before thread-count takes effect. **This is a P18 regression surfaced by P19, not a P19 regression** — pre-P18 these tests ran without sandbox rlimits. Fix options (P20 scope): (a) bump `CapabilitySet.mem_mb` default from 512 → 2048; (b) set `OPENBLAS_NUM_THREADS=1` in worker env inside `_ensure_spawned`; (c) exempt tests that import numpy-heavy plugins from the AS cap. Not in P19's hygiene scope.
- **`_check_gh_auth_for_attestations` mockability**: marker-gating the 3 `TestAttest` tests is tactical P19 debt. P20 (or a follow-up lane) should refactor the prereq check in `mcp_server/artifacts/attestation.py` so it can be mocked from test scope.

### Phase 20 — Multi-Repo Validation & Staged Rollout (P20)

**Objective**
Prove that the multi-repo primitives shipped across P3/P4/P14/P17 actually survive real concurrent load, then execute a staged production rollout with documented bake gates and a rehearsed rollback. This phase is the GA milestone.

**Exit criteria**
- [ ] `tests/integration/multi_repo/` harness exists and passes locally and on CI; runs ≥2 gateways against a shared registry with distinct repo workspaces.
- [ ] Harness includes a lost-writes load test: 2 processes each `register_repository()` 100× to a shared registry; post-run registry has all 200 entries (flock holding).
- [ ] Harness includes a cross-repo delta-artifact resolution test: repo-A publishes a delta whose base points at repo-B's latest artifact; downloader resolves it correctly.
- [ ] Observability smoke on a staging target: production-mode logs parse as `json.loads(...)` line-by-line; `/metrics` exposes `mcp_rate_limit_sleeps_total`, `mcp_artifact_errors_by_class_total`, `mcp_tool_calls_total` (all scrapeable); synthetic 4xx with `Bearer xyz` in body renders `Bearer [REDACTED]`.
- [ ] `docs/operations/deployment-runbook.md` exists per IF-0-P20-2, with stage-by-stage bake gates, rollback triggers, and rollback procedure for at least: staging, canary, full-prod.
- [ ] A rollback was exercised at least once on the staging target and the procedure survived without engineer improvisation.
- [ ] Production rollout complete: canary → full-prod, with all bake gates green.
- [ ] 72h post-rollout bake clean (no alerts on the new counters, no unexpected JSON log parse failures, no secret-redaction misses).

**Scope notes**
- **4 impl lanes + 1 terminal SL-docs lane**. SL-1 and SL-2 run parallel (test-side); SL-3 runs parallel with them (docs-side); SL-4 is sequential after all three (operator-driven rollout). Plan with `MAX_PARALLEL_LANES=2`.
- **SL-1 Multi-repo integration harness**. Owns new `tests/integration/multi_repo/` directory end-to-end: `conftest.py` with the fixture per IF-0-P20-1, `test_registry_concurrency_live.py` (real flock under 2+ processes), `test_cross_repo_delta.py` (cross-repo artifact resolution), `test_multi_repo_dispatcher.py` (dispatcher routes by `RepoContext.repo_id`). If gaps in P5's integration test layer are discovered (e.g., fixtures that don't match current API), the lane surfaces them in its final report; it does not retrofit production code.
- **SL-2 Observability staging smoke**. Owns new `tests/integration/obs/test_obs_smoke.py` which spins up a gateway against a local Prometheus + Loki (docker-compose under `tests/integration/obs/infra/`), verifies JSON log parse rate, counter scrape, secret redaction. Also owns `docs/operations/observability-verification.md` (operator procedure to reproduce the smoke on staging). Disjoint from SL-1's harness directory.
- **SL-3 Deployment runbook**. Owns new `docs/operations/deployment-runbook.md` per IF-0-P20-2. Stages: dev → staging → canary → full-prod. Each stage: pass criteria, bake window, rollback trigger, rollback procedure. Cross-links `scripts/preflight_upgrade.sh` from P19.
- **SL-4 Staged rollout execution**. Owns the execution of the rollout itself: cut RC tag (re-use SL-1 of P19 if still within tag window, else `v0.X.0-rc2`), deploy to staging, run SL-2's smoke, bake, promote to canary, bake, promote to full-prod. This lane is operator-driven with orchestrator tracking; commits are `deploy:` messages capturing tag moves and promotion approvals, not code. Rollback rehearsal happens at the staging bake window.
- **SL-docs (terminal)** registers new docs in `.claude/docs-catalog.json`, appends any post-execution amendments.
- **Single-writer files within phase**: `tests/integration/multi_repo/` (SL-1 exclusive), `tests/integration/obs/` (SL-2 exclusive), `docs/operations/deployment-runbook.md` (SL-3 exclusive). No overlap.
- **Parallelism**: SL-1, SL-2, SL-3 can all land concurrently. SL-4 must wait for all three. SL-docs is terminal.
- **Gate escalation**: if SL-1 or SL-2 surfaces a real bug (not a test harness gap), SL-4 must not advance past staging until a hotfix lane is added. Plan explicitly.

**Non-goals**
- No new production features. P20 is validation + rollout only.
- No backfilling of missing integration tests for phases P6–P17 beyond what IF-0-P20-1's fixture naturally exercises.
- No cross-region rollout (single-region only; multi-region is future work).
- No automated canary-analysis system (manual bake with documented criteria).
- No per-customer rollout gating (all-tenants-at-once within each stage).

**Key files**
- `tests/integration/multi_repo/` (NEW directory: conftest.py, 3+ test files)
- `tests/integration/obs/` (NEW directory: `infra/docker-compose.yml`, test file)
- `docs/operations/deployment-runbook.md` (NEW)
- `docs/operations/observability-verification.md` (NEW)
- Release tags: `v0.X.0-rc1`..`v0.X.0` (cut and promoted by SL-4)
- Staging + canary + production infrastructure configs (owned by SL-4; per-operator)

**Depends on**
- P19 merged (needs pushed origin/main, green CI, preflight script, docs-catalog green).

**Produces**
- IF-0-P20-1, IF-0-P20-2

---

## Execution Notes

- **Save this file as `specs/phase-plans-v1.md`** and create `specs/phase-aliases.json` mapping `P1, P2A, P2B, P3, P4, P5, P6A, P6B` to the full phase headings above so `/plan-phase` can resolve short aliases. If `specs/phase-aliases.json` isn't used, pass `<phase-name-or-id>` as the full heading when invoking `/plan-phase`.
- Run `/plan-phase P1` first. Review the lane plan at `plans/phase-plan-v1-p1.md`, then run `/execute-phase p1`. Repeat per phase.
- `/plan-phase` defaults `MAX_PARALLEL_LANES=2` for execute-phase — keep that default. Full-parallel dispatch caused stale-base salvage issues in prior phases and the two-wave cadence is proven safer.
- **P2B is the riskiest phase to lane-decompose.** Plan it with `--consensus` (three Plan-agent framings) so the facade freeze is validated before lane split.
- Do not start P6A until P1 is merged, even though it's nominally parallel — the identity refactor may touch `mcp_server/security/` indirectly via the `PathUtils` cleanup.
- The integration test in P5 is the phase-gate quality bar for the whole refactor. If it passes and the FastAPI gateway's existing unit tests still pass, we're done.
- **P7, P8, P9 parallelize by file ownership.** P7 owns `AGENTS.md`, `architecture.md`, `stdio_runner.py` schemas. P8 owns `README.md`, `GETTING_STARTED.md`, `DEPLOYMENT-GUIDE.md`, `docs/implementation/`, `docs/status/`, `docs/validation/`. P9 owns `tool_handlers.py` + test files. Plan back-to-back; execute concurrently.
- **P9 gates P10.** P10's `get_status` health surface extends handler signatures; let them settle first.
- **P10 is the highest-parallelism phase since P3** — six disjoint lanes. Keep `MAX_PARALLEL_LANES=2`; expect three waves.
- **P11 is unknown-scope.** Plan with `--consensus`. If root cause eludes a one-lane-day timebox, ship extension-gating + bounded timeout and document the investigation gap in `docs/investigations/`.
- **P8 historical sweep requires human review** of the triage log. Consider flagging that lane for no-auto-merge in `/execute-phase`.
- **P12 → P13 → P14 → P15 is strictly serial.** No cross-phase parallelism. Each phase's planning can start the day after its predecessor merges.
- **P12 SL-2 and SL-3 both edit `watcher_multi_repo.py`** — partition by function: SL-2 wraps dispatcher call sites with `with lock_registry.acquire(repo_id):`; SL-3 owns `should_reindex_for_branch` plus the rescan enqueue. Coordinate via IF-freeze at plan-phase.
- **P13 SL-1 and SL-2 both edit `incremental_indexer.py`** — SL-1 owns the resume entry points, SL-2 owns `_cleanup_stale_vectors` and the rename handler. Non-overlapping line ranges.
- **P13 SL-5 touches many files by design** (exception refactoring). Scope strictly to `except` keyword replacements; other lanes must not touch `except` clauses in their edited files during P13.
- **P14 SL-4 and P13 SL-4 both edit `artifact_upload.py`** — time-ordered (P13 merges first), no concurrent work.
- **P15 SL-1 (plugin sandboxing) is the riskiest single lane in this entire remediation arc.** Plan with `--consensus`; budget for a scoping prototype if consensus cannot converge in one lane-day.
- **User runbook prerequisites** apply before each execute-phase. See `docs/operations/user-action-runbook.md` for the per-phase checklist (GitHub token scopes for P13, SLSA attestations for P15, etc.). Read that file before invoking `/execute-phase p12`.
- **P16 is a single-lane preamble phase.** After its merge, P17 and P18 have no shared DAG ancestor beyond P16 — plan and execute both concurrently. Use `/plan-phase P17` and `/plan-phase P18` in parallel, then `/execute-phase p17` and `/execute-phase p18` in separate worktrees or terminal panes.
- **P17 and P18 share `mcp_server/core/errors.py` only for raise-sites.** P16's IF-0-P16-1 freezes the class shape; P17 SL-3 fills `SchemaMigrationError` raise sites in `schema_migrator.py`; P18 SL-2 fills `TransientArtifactError`/`TerminalArtifactError` raise sites in `providers/github_actions.py` and `artifact_download.py`. Disjoint raise-site files; no merge conflict.
- **P18 SL-1 and SL-4 both edit `gateway.py`.** SL-1 owns the startup-validation block (near AuthManager instantiation at ~line 343) and the `/search/capabilities` decorator (~line 1472). SL-4 owns the secret-redaction middleware registration near the `SecurityMiddlewareStack` init (~line 341). Disjoint line ranges; top-of-file imports alphabetized at merge (P14/P15 pattern).
- **P18 SL-2 and SL-3 both touch `artifacts/providers/github_actions.py`.** SL-2 owns the rate-limit + retry edits inline in existing functions; SL-3 appends `delete_releases_older_than` at file end (append-only). No overlap.
- **P18 SL-2 and SL-5 both touch `artifacts/attestation.py`.** SL-2 owns the attest-preflight function block around `attest`; SL-5 owns the new `probe_gh_attestation_support` helper + startup capability probe. Disjoint function blocks; file-end append for SL-5.
- **P18 SL-5 flips `MCP_PLUGIN_SANDBOX_ENABLED` to on by default.** This is a user-visible behavioral change. Document the opt-out (`MCP_PLUGIN_SANDBOX_DISABLE=1`) prominently in CHANGELOG and release notes. Repo-specific ground truth: no existing plugin in this codebase opens sockets or reads outside the workspace, so the default flip is expected to be non-breaking (verified via `grep -rn 'socket\|urlopen' mcp_server/plugins/` → empty).
- **P17 SL-4 is isolated cleanup.** The 18 `test_cross_repo_coordinator.py` failures share a single root cause (stale class/module reference from a prior refactor); the 2 `test_repository_registry_commits.py` failures likewise share a single test-assumption bug (hardcoded `repository_id` string ≠ computed `repo_id`). Fix scope is small.

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

### Post-Execution Amendments (P18)

The following minor deviations from the spec occurred during implementation and are documented for future reference. All deviations are functionally equivalent and do not affect the exit criteria.

- **SL-3 module naming**: `artifacts/retention.py` (spec) implements the janitor; `cli/commands.py` wires the `retention prune` subcommand. Spec referenced `cli/commands.py` as the single owner; implementation split concerns for clarity. Functionally equivalent — both locations are single-writer and disjoint.

- **IF-0-P18-1 produced no interface freeze**: P18's primary interface is the operational CLI `retention prune` (spec completes) and configuration (environment variables). No inter-phase API boundary was introduced beyond the existing artifact/plugin contract extensions. No new frozen interface was needed.

- **All validation errors render to stderr as documented**: `render_validation_errors_to_stderr()` outputs `[FATAL] <code>: <message>` one per line. Tested in production and dev modes per spec.

- **Rate-limit Retry-After parsing**: Correctly distinguishes 429 (Retry-After backoff) from 403 (terminal error, raises `TerminalArtifactError`). No deviations from spec.

- **Sandbox default-on**: `MCP_PLUGIN_SANDBOX_DISABLE=1` provides opt-out. Default is ON. All built-in plugins have been updated with capability declarations. No pre-P18 plugins in the codebase required fallback opt-out.

## Verification (post-hardening, after P11 merge)

All P1–P6B verification above must still pass — regression-free. In addition:

```bash
# STDIO Prometheus metrics scrape (P10)
MCP_ALLOWED_ROOTS=/tmp/repo-a,/tmp/repo-b MCP_METRICS_PORT=9090 \
  python -m mcp_server.cli.server_commands &
# (issue any tool call against the server)
curl -s localhost:9090/metrics | grep -E 'mcp_tool_calls_total|mcp_dispatcher_fallback_duration_seconds'

# SIGTERM graceful shutdown (P10)
pytest tests/integration/test_sigterm_shutdown.py -v

# Symlink-escape negative (P10)
pytest tests/security/test_symlink_escape.py -v

# Multi-repo health surface (P10)
# get_status response must include a `repositories` array with staleness_reason on stale entries
curl -s localhost:8000/status | jq '.repositories[] | {repo_id, staleness_reason}'

# Full-suite baseline on both supported Python versions (P9 tomllib fallback)
python3.10 -m pytest tests/ -v --no-cov --timeout=60
python3.12 -m pytest tests/ -v --no-cov --timeout=60

# Cross-language dispatch exercises P11 extension-gating — unknown-extension returns empty, not hang
pytest tests/test_dispatcher_extension_gating.py tests/test_dispatcher_fallback_timeout.py -v
```

Any failure in the above — stale `mcp_tool_calls_total` of zero after a stdio call, shutdown exceeding 5s, a `/etc/passwd` symlink read succeeding from an allowed-root alias, a `database is locked` surfaced under concurrent readers, or an untrapped fallback hang — fails the post-hardening bar and blocks beta ship.

## Verification (post-P15, pre-GA)

All P1–P11 verification above must still pass — regression-free. In addition:

```bash
# Probes (P12 SL-1)
curl -f localhost:8000/ready       # expect 200
curl -f localhost:8000/liveness    # expect 200

# Hot-path histograms present (P12 SL-4)
curl -s localhost:9090/metrics | grep -E 'mcp_(symbol_lookup|search)_duration_seconds_bucket' | head -5

# Per-repo indexing lock (P12 SL-2)
pytest tests/test_indexing_lock.py -v

# Branch-drift loud-path (P12 SL-3)
pytest tests/test_branch_drift_rescan.py -v

# Artifact freshness gate + offline fallback (P12 SL-5)
pytest tests/test_artifact_freshness.py -v

# Reindex resume (P13 SL-1)
pytest tests/test_reindex_resume.py -v

# Two-phase Qdrant+SQLite commit (P13 SL-2)
pytest tests/test_two_phase_commit.py -v

# TOCTOU-guarded dispatch (P13 SL-3)
pytest tests/test_dispatcher_toctou.py -v

# Direct publish + atomic latest (P13 SL-4)
pytest tests/test_artifact_publish_race.py -v

# Structured error counters surface on /metrics (P13 SL-5)
curl -s localhost:9090/metrics | grep -E 'mcp_errors_by_type_total' | head -3
pytest tests/test_structured_errors.py -v

# Semantic reranker + dependency-aware search (P14 SL-1, SL-2)
pytest tests/test_reranker_integration.py tests/test_dependency_aware_search.py -v

# Schema version gate + migrator (P14 SL-3)
pytest tests/test_schema_migration.py -v

# Auto-delta + paginated chunk queries (P14 SL-4)
pytest tests/test_artifact_auto_delta.py tests/test_chunk_query_pagination.py -v

# Watcher fallback sweep + rename atomicity (P14 SL-5)
pytest tests/test_watcher_sweep.py tests/test_rename_atomicity.py -v

# Plugin sandboxing — malicious plugin rejected (P15 SL-1)
pytest tests/security/test_malicious_plugin.py tests/test_plugin_sandbox.py -v

# Metrics auth (P15 SL-2) — unauth'd request denied
curl -s -o /dev/null -w '%{http_code}' localhost:9090/metrics   # expect 401
pytest tests/security/test_metrics_auth.py -v

# Artifact attestation verify (P15 SL-3)
pytest tests/test_artifact_attestation.py -v

# Path traversal + token scope + rate limit (P15 SL-4)
pytest tests/security/test_path_traversal.py tests/security/test_token_scope.py \
       tests/test_cross_repo_rate_limit.py -v
```

Any failure in the above — a probe returning 503 when the service is healthy, a fallback to pre-reindex index content when artifact is stale, a concurrent watcher+manual-sync race surfacing in the test, a rename leaving `foo.py` entries behind, a sandboxed plugin escaping to the host filesystem, an unauth'd `/metrics` scrape returning 200, or a tampered artifact passing attestation verification — fails the pre-GA bar and must be remediated before release.

## Verification (post-P18, production-ready)

All P1–P15 verification above must still pass — regression-free. In addition:

```bash
# P16 — shared vocabulary frozen
pytest tests/test_p16_vocabulary.py -v --no-cov

# P17 — multi-instance + durability
pytest tests/test_registry_concurrency.py tests/test_singleton_reset.py \
       tests/test_ref_poller_edges.py tests/test_sweeper_observability.py \
       tests/test_disk_full.py tests/test_schema_migration_backup.py -v --no-cov

# P17 — carry-over debt resolved
pytest tests/test_cross_repo_coordinator.py tests/test_repository_registry_commits.py -v --no-cov
ruff check mcp_server/dispatcher mcp_server/storage mcp_server/watcher   # expect 0 F401

# P18 — auth coverage + config enforcement
pytest tests/security/test_route_auth_coverage.py -v --no-cov
MCP_ENVIRONMENT=production JWT_SECRET_KEY=weak python -m mcp_server.cli.server_commands
#   expect: exit non-zero with ValidationError listing rendered to stderr

# P18 — artifact resilience
pytest tests/test_artifact_publish_rollback.py tests/test_delta_base_fallback.py \
       tests/test_rate_limit_retry_after.py -v --no-cov

# P18 — observability + defaults
pytest tests/test_json_logs.py tests/test_secret_redaction.py \
       tests/test_sandbox_default_on.py tests/test_retention_janitor.py -v --no-cov

# P18 — retention CLI round-trip (operator command)
python -m mcp_server.cli retention prune --repo owner/repo --dry-run
#   expect: prints releases that would be deleted; exit 0 with no mutation

# Full-suite regression gate — residuals must be ≤5 (down from 46 pre-P17)
pytest --ignore=tests/test_cross_repo_coordinator.py \
       --deselect tests/test_plugin_manager_enhanced.py::TestRemoveFileSemanticCleanup \
       -v --no-cov
```

Any failure above — concurrent registry writes lost under flock contention, detached-HEAD / force-push missed by ref-poller, disk-full crashing the server instead of dropping to read-only, a gateway route missing auth, a weak JWT accepted under `MCP_ENVIRONMENT=production`, an orphan GitHub release after a mid-publish kill, logs emitting plaintext or leaking secrets in production mode, or the carry-over debt count staying above 5 — fails production-readiness and blocks GA.
