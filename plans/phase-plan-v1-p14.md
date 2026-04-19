# P14: Multi-Repo Completeness + Schema Evolution

## Context

P13 merged: checkpointed reindex resume (`mcp_server/indexing/checkpoint.py`), two-phase Qdrant+SQLite commit (`mcp_server/storage/two_phase.py`), TOCTOU-safe dispatch (`index_file_guarded`), direct post-reindex publish (`mcp_server/artifacts/publisher.py::ArtifactPublisher.publish_on_reindex`), and structured errors (`IndexingError`, `ArtifactError` in `mcp_server/core/errors.py`, plus `record_handled_error` and `errors_by_type` Counter). P14 closes five product-reach gaps that currently limit multi-repo usefulness.

What exists today (reconnaissance, verified):

- `mcp_server/dispatcher/cross_repo_coordinator.py`
  - `__init__` L79-110 sets `self.reranker = None` at L99; never assigned elsewhere.
  - `_rerank_results` at L328-353 calls `self.reranker.rerank(...)` but only when `self.reranker` is truthy; it never is — stub.
  - `_create_document_repr` L355-370 already formats results for a reranker.
  - `search_with_dependencies` L459-490 calls `_get_repository_dependencies` at L476.
  - `_get_repository_dependencies(repository_id)` L492-502 returns `set()` (stub).
  - Imports already include `record_handled_error` from `mcp_server.core.errors` and `IReranker as Reranker` from `mcp_server.indexer.reranker` (L18).
  - **No imports from `gateway.py` or `watcher_multi_repo.py`** → worktree-safe.
- `mcp_server/indexer/reranker.py` (806 lines) — **canonical reranker surface**: `IReranker` ABC at L59-64 (`rerank(query, documents, top_k) -> List[int]`), concrete `CohereReranker`, `LocalCrossEncoderReranker`, `TFIDFReranker`, `HybridReranker`, `VoyageReranker`, `FlashRankReranker`, `CrossEncoderReranker`, and `RerankerFactory` at L761-805. **Spec deviation**: P14 spec L742 names `mcp_server/retrieval/reranker.py` as a new module; that directory does not exist, and there is already a full reranker module. P14 reuses the existing one. Recorded in Execution Notes.
- Existing per-ecosystem dep parsing:
  - `mcp_server/plugins/rust_plugin/cargo_integration.py` — `CargoIntegration.parse_cargo_toml` (Cargo.toml).
  - `mcp_server/plugins/go_plugin/module_resolver.py` — `GoModuleResolver` (go.mod).
  - **Missing**: `requirements.txt` and `package.json` parsers. SL-2 adds both.
- `mcp_server/artifacts/manifest_v2.py`
  - `ArtifactManifestV2` dataclass L37-107 **already carries `schema_version: str` at L44** and `chunk_schema_version: str` at L45. Frozen dataclass with `to_dict()`/`from_dict()` JSON round-trip + `validate()`.
  - SL-3 does not add the field; it adds the gate and the migrator.
- `mcp_server/artifacts/artifact_download.py::check_compatibility` L171-199 already reads artifact `schema_version` and compares against local `SELECT MAX(version) FROM schema_version`, raising on mismatch. **This is the SL-3 insertion point** for the migrator call.
- `mcp_server/artifacts/artifact_upload.py`
  - `compress_indexes` L61-90 returns `(tgz_path, sha256, size_bytes)`.
  - `_get_schema_version` L192-212 already sources the version from the DB or env fallback.
  - L330 has a hardcoded 500 MB check that currently only warns. Metadata block L339-341 already has `artifact_type` (`full`/`delta`) and `delta_from` fields — the fields exist, the policy is missing.
- `mcp_server/artifacts/publisher.py::ArtifactPublisher.publish_on_reindex(repo_id, commit) -> ArtifactRef` is the P13 SL-4 orchestrator hook. SL-4 consults a new `DeltaPolicy` here.
- `mcp_server/indexing/incremental_indexer.py::_get_chunk_ids_for_path` L64-107 single-shot query, no pagination. Only known caller: `_cleanup_stale_vectors` L261-345 (internal).
- `mcp_server/storage/sqlite_store.py`
  - `_run_migrations` L168-219 runs numbered SQL files from `migrations/` (001-004 present).
  - `schema_version` table at L294-307; `MAX(version)` read at L191.
  - `files` table L311-327 declares `UNIQUE(repository_id, relative_path)` — rename atomicity has a **constraint-level** guarantee.
- `mcp_server/watcher_multi_repo.py` (note: at package root, not under `mcp_server/watcher/`)
  - `MultiRepositoryHandler._move_with_ctx` L192-207 wraps `dispatcher.move_file(ctx, old, new)` under `lock_registry.acquire(repo_id)` (P12 SL-2) but **not under `two_phase_commit`** — the atomicity gap.
  - `MultiRepositoryWatcher.enqueue_full_rescan` L268-273 — existing "enqueue a re-scan" entry point the sweeper reuses.
  - `GitMonitor._monitor_loop` L59-71 — template for the sweeper's daemon-thread polling loop (Event().wait for graceful stop).
- `mcp_server/watcher/file_watcher.py`
  - `_Handler._handle_file_move` L220-232 calls `dispatcher.move_file(old, new, content_hash)` — watchdog delivers a single `MovedEvent`, handler emits a single move action. No reassembly needed.
- `mcp_server/dispatcher/dispatcher_enhanced.py::move_file` at **L2146** is the single dispatcher move surface (no `dispatcher.py`; the package's single implementation is `dispatcher_enhanced.py`). Currently: SQLite update + semantic indexer move with no rollback.

What constrains the design:

- **`cross_repo_coordinator.py` is a single-writer file touched by SL-1 and SL-2.** Line-range ownership is disjoint: SL-1 owns L79-110 (`__init__`) and L328-370 (`_rerank_results` + `_create_document_repr`); SL-2 owns L459-502 (`search_with_dependencies` + `_get_repository_dependencies`). Top-of-file imports are a known add/add conflict surface — resolution noted in Execution Notes.
- **`artifact_upload.py` is touched by SL-3 (L192-212) and SL-4 (L330 + metadata block L339-341).** Disjoint line ranges; imports section is the add/add conflict surface.
- **Two-phase-commit placement for rename**: wrap `dispatcher_enhanced.move_file` (L2146) rather than threading atomicity through every watcher caller. Catches both `watcher_multi_repo._move_with_ctx` (L206-207) and any direct programmatic callers.
- **Lock re-entry risk**: `watcher_multi_repo._move_with_ctx` already holds `lock_registry.acquire(repo_id)` when it calls `dispatcher.move_file`. The `two_phase_commit` wrapper must NOT acquire the same lock — `IndexingLockRegistry` is reentrant (P12), so a no-op if already held, but SL-5 must state this explicitly in the wrapper.
- **`bypass_branch_guard` on `enqueue_full_rescan` (P12 handoff)**: P14 SL-5's sweeper does NOT consume this parameter. Recorded in Execution Notes.

What this phase does NOT change:

- No auto-repo discovery (spec Non-goals).
- No cross-ecosystem dep resolution (Python→Node via FFI): each ecosystem stays self-contained.
- No artifact signing (deferred to P15).
- No changes to the existing `IReranker` ABC at `mcp_server/indexer/reranker.py:59-64`.
- No schema changes to the `files` or `schema_version` SQLite tables.

## Interface Freeze Gates

- [ ] **IF-0-P14-1** — Reranker wiring in `CrossRepoCoordinator` (reuses existing ABC in `mcp_server/indexer/reranker.py`; no new module).

  ```python
  # mcp_server/indexer/reranker.py (UNCHANGED, referenced only)
  class IReranker(ABC):
      @abstractmethod
      async def rerank(
          self, query: str, documents: List[str], top_k: int
      ) -> List[int]: ...

  # mcp_server/dispatcher/cross_repo_coordinator.py
  from mcp_server.indexer.reranker import IReranker, RerankerFactory

  class CrossRepoCoordinator:
      def __init__(
          self,
          multi_repo_manager,
          enable_semantic: bool = True,
          enable_reranking: bool = True,
          reranker: Optional[IReranker] = None,
      ):
          ...
          # SL-1 replaces `self.reranker = None` at L99:
          self.reranker: Optional[IReranker] = (
              reranker if reranker is not None
              else (RerankerFactory.create_default() if enable_reranking else None)
          )
  ```

  Frozen at end of task `SL-1.1`.

- [ ] **IF-0-P14-2** — Dependency graph (new package `mcp_server/dependency_graph/`).

  ```python
  # mcp_server/dependency_graph/parsers.py (NEW)
  class EcosystemParser(Protocol):
      manifest_filename: str
      def parse(self, path: Path) -> Set[str]: ...  # returns package names

  # Concrete: PythonRequirementsParser, NpmPackageJsonParser, GoModParser, CargoTomlParser
  # CargoTomlParser/GoModParser delegate to existing plugins where possible.

  # mcp_server/dependency_graph/aggregator.py (NEW)
  class DependencyGraphAnalyzer:
      def __init__(self, multi_repo_manager: MultiRepositoryManager): ...
      async def analyze(self, repo_id: str) -> Set[str]:
          """Return set of repo_ids that `repo_id` depends on (resolved via manager);
             silently drops package names not owned by any registered repo."""

  # mcp_server/dispatcher/cross_repo_coordinator.py (L492-502 body replaced)
  async def _get_repository_dependencies(self, repository_id: str) -> Set[str]: ...
  ```

  Frozen at end of task `SL-2.1`.

- [ ] **IF-0-P14-3** — Schema migrator (new `mcp_server/storage/schema_migrator.py`).

  ```python
  # mcp_server/storage/schema_migrator.py (NEW)
  class UnknownSchemaVersionError(ArtifactError): ...
  class SchemaMigrationError(ArtifactError): ...

  class SchemaMigrator:
      SUPPORTED_VERSIONS: tuple[str, ...] = ("1", "2")
      CURRENT_VERSION: str = "2"

      def __init__(self, store: SQLiteStore): ...
      def is_known(self, version: str) -> bool: ...
      def migrate_artifact(
          self, extracted_dir: Path, from_version: str, to_version: str,
      ) -> Path:
          """Equal versions → no-op. Older known → run ordered migrations.
             Unknown → raise UnknownSchemaVersionError."""
  ```

  Both exceptions extend `ArtifactError` from `mcp_server/core/errors.py` so they flow into `record_handled_error` + `errors_by_type{module,exception}` (P13 SL-5).
  Frozen at end of task `SL-3.1`.

- [ ] **IF-0-P14-4** — Delta policy (new `mcp_server/artifacts/delta_policy.py`).

  ```python
  # mcp_server/artifacts/delta_policy.py (NEW)
  ENV_FULL_SIZE_LIMIT: str = "MCP_ARTIFACT_FULL_SIZE_LIMIT"
  DEFAULT_FULL_SIZE_LIMIT_BYTES: int = 500 * 1024 * 1024   # 500 MB

  @dataclass(frozen=True)
  class DeltaDecision:
      strategy: Literal["full", "delta"]
      base_artifact_id: Optional[str]
      reason: str          # short audit-friendly token: "below_limit" | "above_limit_with_base" | "above_limit_no_base"

  class DeltaPolicy:
      def __init__(self, limit_bytes: Optional[int] = None): ...
      def decide(
          self,
          compressed_size_bytes: int,
          previous_artifact_id: Optional[str],
      ) -> DeltaDecision: ...
  ```

  Frozen at end of task `SL-4.1`. Integrates into `ArtifactPublisher.publish_on_reindex` and into `IndexArtifactUploader` metadata construction (L339-341 populates `artifact_type` and `delta_from` from `DeltaDecision`).

- [ ] **IF-0-P14-5** — Watcher sweeper + atomic rename.

  ```python
  # mcp_server/watcher/sweeper.py (NEW)
  ENV_SWEEP_MINUTES: str = "MCP_WATCHER_SWEEP_MINUTES"
  DEFAULT_SWEEP_MINUTES: int = 60

  class WatcherSweeper:
      def __init__(
          self,
          on_missed_path: Callable[[str, str], None],   # (repo_id, relative_path)
          repo_roots_provider: Callable[[], Dict[str, Path]],
          store: SQLiteStore,
          interval_minutes: int = DEFAULT_SWEEP_MINUTES,
          clock: Callable[[], float] = time.monotonic,
      ): ...
      def start(self) -> None: ...
      def stop(self) -> None: ...
      def sweep_once(self) -> List[str]:
          """Diff filesystem ↔ SQLite known paths; for each mismatch call
             on_missed_path(repo_id, relative_path). Return list of repo_ids with drift."""

  # mcp_server/dispatcher/dispatcher_enhanced.py::move_file (L2146) wrapper
  def move_file(self, ctx, old_path: str, new_path: str, content_hash: str) -> None:
      """SQLite path-update + semantic re-embed, wrapped in two_phase_commit so a
         semantic-indexer failure rolls SQLite back. Lock re-entry: relies on
         IndexingLockRegistry's reentrant RLock (P12)."""
  ```

  Frozen at end of task `SL-5.1`.

## Lane Index & Dependencies

```
SL-1 — reranker-wiring
  Depends on: (none)
  Blocks: SL-docs
  Parallel-safe: yes (disjoint line ranges in cross_repo_coordinator.py with SL-2)

SL-2 — dependency-graph
  Depends on: (none)
  Blocks: SL-docs
  Parallel-safe: yes (disjoint line ranges in cross_repo_coordinator.py with SL-1)

SL-3 — schema-migrator
  Depends on: (none)
  Blocks: SL-4, SL-docs
  Parallel-safe: yes

SL-4 — auto-delta
  Depends on: SL-3 (reads manifest schema_version stamped by SL-3)
  Blocks: SL-docs
  Parallel-safe: mixed (shares artifact_upload.py with SL-3 at disjoint line ranges; serialize after SL-3 merges to avoid import add/add)

SL-5 — sweeper-rename-atomicity
  Depends on: (none)
  Blocks: SL-docs
  Parallel-safe: yes

SL-docs — documentation & spec reconciliation
  Depends on: SL-1, SL-2, SL-3, SL-4, SL-5
  Parallel-safe: no (terminal)
```

Wave plan:
- **Wave 1 (parallel)**: SL-1, SL-2, SL-3, SL-5.
- **Wave 2**: SL-4 (after SL-3 merges).
- **Wave 3 (terminal)**: SL-docs.

## Lanes

### SL-1 — reranker-wiring

- **Scope**: Wire a real `IReranker` instance into `CrossRepoCoordinator` so that `_rerank_results` reorders results when reranking is enabled.
- **Owned files**:
  - `mcp_server/dispatcher/cross_repo_coordinator.py` — **L79-110 (`__init__`) and L328-370 (`_rerank_results` + `_create_document_repr`) ONLY**. May also add ONE import line in the top-of-file import block (see Execution Notes for add/add conflict handling).
  - `tests/test_cross_repo_reranker.py` (NEW).
- **Interfaces provided**: `IF-0-P14-1`.
- **Interfaces consumed**: existing `mcp_server.indexer.reranker.IReranker`, `RerankerFactory`.
- **Parallel-safe**: yes.
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-1.1 | test | — | `tests/test_cross_repo_reranker.py` | `test_rerank_changes_order_with_fake_reranker`, `test_no_reranker_when_disabled`, `test_injected_reranker_overrides_factory` | `pytest tests/test_cross_repo_reranker.py -v` |
| SL-1.2 | impl | SL-1.1 | `mcp_server/dispatcher/cross_repo_coordinator.py` L79-110, L328-370 | — | `pytest tests/test_cross_repo_reranker.py -v` |
| SL-1.3 | verify | SL-1.2 | above | all SL-1 tests + pre-existing `tests/test_cross_repo_coordinator.py` must still pass | `pytest tests/test_cross_repo_reranker.py tests/test_cross_repo_coordinator.py -v && ruff check mcp_server/dispatcher/cross_repo_coordinator.py` |

`tests/test_cross_repo_reranker.py` uses a fake `IReranker` that returns `list(reversed(range(len(documents))))` and asserts the aggregated result order flips. Reuses `AggregatedResult` and mock-manager fixtures from `tests/test_cross_repo_coordinator.py`. Does **not** touch `RerankerFactory.create_default()` (no network/model downloads in CI).

### SL-2 — dependency-graph

- **Scope**: Implement real dependency detection for Python/Node/Go/Rust manifests and return resolved repo_ids from `_get_repository_dependencies`.
- **Owned files**:
  - `mcp_server/dependency_graph/__init__.py` (NEW)
  - `mcp_server/dependency_graph/aggregator.py` (NEW)
  - `mcp_server/dependency_graph/parsers.py` (NEW)
  - `mcp_server/dependency_graph/ecosystems/python.py` (NEW — `requirements.txt`)
  - `mcp_server/dependency_graph/ecosystems/npm.py` (NEW — `package.json`)
  - `mcp_server/dependency_graph/ecosystems/go.py` (NEW — delegates to existing `mcp_server/plugins/go_plugin/module_resolver.py`)
  - `mcp_server/dependency_graph/ecosystems/cargo.py` (NEW — delegates to existing `mcp_server/plugins/rust_plugin/cargo_integration.py`)
  - `mcp_server/dispatcher/cross_repo_coordinator.py` — **L459-502 ONLY** (replace `_get_repository_dependencies` body; `search_with_dependencies` stays unchanged in body but may add a single import).
  - `tests/test_dependency_graph_parsers.py` (NEW)
  - `tests/test_dependency_aware_search.py` (NEW)
- **Interfaces provided**: `IF-0-P14-2`.
- **Interfaces consumed**: `MultiRepositoryManager` (read-only).
- **Parallel-safe**: yes.
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-2.1 | test | — | both NEW test files | `test_python_requirements_parser`, `test_npm_package_json_parser`, `test_go_mod_parser`, `test_cargo_toml_parser`, `test_three_repo_dep_graph_nonempty`, `test_unresolved_package_dropped` | `pytest tests/test_dependency_graph_parsers.py tests/test_dependency_aware_search.py -v` |
| SL-2.2 | impl | SL-2.1 | all `mcp_server/dependency_graph/**` files + `cross_repo_coordinator.py` L459-502 | — | same |
| SL-2.3 | verify | SL-2.2 | above | — | `pytest tests/test_dependency_graph_parsers.py tests/test_dependency_aware_search.py tests/test_cross_repo_coordinator.py -v` |

`test_three_repo_dep_graph_nonempty` builds three `tmp_path` repos each containing a manifest file (`requirements.txt`, `package.json`, `go.mod`, `Cargo.toml` across them) that references the other repos' package names. Asserts `_get_repository_dependencies` returns a non-empty `Set[str]` for each — maps directly to acceptance #2.

### SL-3 — schema-migrator

- **Scope**: Add `SchemaMigrator`, wire it into `artifact_download.check_compatibility`, and ensure uploaded manifests carry a populated `schema_version`.
- **Owned files**:
  - `mcp_server/storage/schema_migrator.py` (NEW)
  - `mcp_server/artifacts/artifact_download.py` — L171-199 only (migrator call inserted between read and raise).
  - `mcp_server/artifacts/artifact_upload.py` — **L192-212 only** (`_get_schema_version` feeds into manifest stamping; no edits outside this method).
  - `tests/test_schema_migrator.py` (NEW)
  - `tests/test_schema_migration.py` (NEW, end-to-end download gate)
- **Interfaces provided**: `IF-0-P14-3`.
- **Interfaces consumed**: `SQLiteStore` (read-only), `ArtifactManifestV2.from_dict`, `ArtifactError`.
- **Parallel-safe**: yes in Wave 1 (SL-4 begins after SL-3 merges).
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-3.1 | test | — | both NEW test files | `test_equal_version_passthrough`, `test_older_known_runs_migrator`, `test_unknown_version_refuses`, `test_migration_failure_raises_SchemaMigrationError` | `pytest tests/test_schema_migrator.py tests/test_schema_migration.py -v` |
| SL-3.2 | impl | SL-3.1 | `mcp_server/storage/schema_migrator.py`, `artifact_download.py` L171-199, `artifact_upload.py` L192-212 | — | same |
| SL-3.3 | verify | SL-3.2 | above | — | `pytest tests/test_schema_migrator.py tests/test_schema_migration.py tests/test_artifact_manifest_v2.py tests/test_artifact_lifecycle.py -v` |

Each of the three tests covers one acceptance #3 path (unknown → refuse, older known → migrate, equal → pass). Reuses `ArtifactManifestV2.to_dict()` fixture pattern from `tests/test_artifact_manifest_v2.py`.

### SL-4 — auto-delta

- **Scope**: Implement `DeltaPolicy` + integrate into publisher/uploader so compressed artifacts above `MCP_ARTIFACT_FULL_SIZE_LIMIT` publish as delta-from-previous. Add pagination to `_get_chunk_ids_for_path`.
- **Owned files**:
  - `mcp_server/artifacts/delta_policy.py` (NEW)
  - `mcp_server/artifacts/artifact_upload.py` — **L330 + metadata block L339-341 ONLY** (consume `DeltaDecision` to populate `artifact_type` / `delta_from`).
  - `mcp_server/artifacts/publisher.py` — consume `DeltaPolicy` in `publish_on_reindex` only.
  - `mcp_server/indexing/incremental_indexer.py::_get_chunk_ids_for_path` L64-107 — add `limit: Optional[int] = None`, `offset: int = 0` parameters; default behavior unchanged.
  - `tests/test_delta_policy.py` (NEW)
  - `tests/test_artifact_auto_delta.py` (NEW)
  - `tests/test_chunk_query_pagination.py` (NEW)
- **Interfaces provided**: `IF-0-P14-4`.
- **Interfaces consumed**: `IF-0-P14-3` (manifest `schema_version` read path), `ArtifactPublisher`.
- **Parallel-safe**: mixed (same file as SL-3 in `artifact_upload.py` at disjoint line ranges — merge after SL-3).
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-4.1 | test | SL-3.3 (merged) | all three NEW test files | `test_decide_below_limit_full`, `test_decide_above_limit_delta_when_prev`, `test_decide_above_limit_full_when_no_prev`, `test_publisher_switches_to_delta_when_env_low`, `test_get_chunk_ids_for_path_pagination_respects_limit_offset`, `test_get_chunk_ids_for_path_default_backcompat` | `pytest tests/test_delta_policy.py tests/test_artifact_auto_delta.py tests/test_chunk_query_pagination.py -v` |
| SL-4.2 | impl | SL-4.1 | `delta_policy.py`, `artifact_upload.py` L330-341, `publisher.py`, `incremental_indexer.py` L64-107 | — | same |
| SL-4.3 | verify | SL-4.2 | above | — | `pytest tests/test_delta_policy.py tests/test_artifact_auto_delta.py tests/test_chunk_query_pagination.py tests/test_artifact_publish_race.py tests/test_delta_artifacts.py -v` |

`test_publisher_switches_to_delta_when_env_low` sets `monkeypatch.setenv("MCP_ARTIFACT_FULL_SIZE_LIMIT", "1")` and a recorded previous artifact ID, then asserts metadata `artifact_type == "delta"` and `delta_from == <prev_id>` — maps to acceptance #4.

### SL-5 — sweeper-rename-atomicity

- **Scope**: Add periodic full-tree sweep that recovers inotify/FSEvents drops, and wrap `dispatcher.move_file` in `two_phase_commit` so renames are atomic.
- **Owned files**:
  - `mcp_server/watcher/sweeper.py` (NEW)
  - `mcp_server/dispatcher/dispatcher_enhanced.py::move_file` — L2146 only (method body wrapped in `two_phase_commit`).
  - `mcp_server/watcher_multi_repo.py` — start/stop hook for sweeper only (within `MultiRepositoryWatcher.__init__`/`start`/`stop`); **does not** touch L192-207 `_move_with_ctx` body.
  - `mcp_server/watcher/file_watcher.py` — pass-through only (no behavior change); may be untouched.
  - `tests/test_watcher_sweep.py` (NEW)
  - `tests/test_rename_atomicity.py` (NEW)
- **Interfaces provided**: `IF-0-P14-5`.
- **Interfaces consumed**: `mcp_server.storage.two_phase.two_phase_commit` (P13 SL-2), `IndexingLockRegistry` (P12 SL-2), `MultiRepositoryWatcher.enqueue_full_rescan` (P12).
- **Parallel-safe**: yes.
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Tests owned | Test command |
|---|---|---|---|---|---|
| SL-5.1 | test | — | both NEW test files | `test_sweeper_recovers_missed_event`, `test_sweeper_interval_env_override`, `test_sweeper_noop_when_no_drift`, `test_rename_single_remove_single_add`, `test_rename_rollback_on_semantic_failure` | `pytest tests/test_watcher_sweep.py tests/test_rename_atomicity.py -v` |
| SL-5.2 | impl | SL-5.1 | `watcher/sweeper.py`, `dispatcher_enhanced.py` L2146, `watcher_multi_repo.py` (start/stop hook only) | — | same |
| SL-5.3 | verify | SL-5.2 | above | — | `pytest tests/test_watcher_sweep.py tests/test_rename_atomicity.py tests/test_watcher.py tests/test_watcher_multi_repo.py tests/test_incremental_indexer.py -v` |

`test_sweeper_recovers_missed_event`: create a file under `tmp_repo` without firing the watchdog (bypass the observer), invoke `sweeper.sweep_once()`, assert `on_missed_path` was called with `(repo_id, rel_path)` → acceptance #5.

`test_rename_single_remove_single_add`: rename `foo.py → bar.py`, then execute `SELECT relative_path FROM files WHERE repository_id=? AND relative_path IN ('foo.py','bar.py')` and assert exactly `[('bar.py',)]` → acceptance #6.

`test_rename_rollback_on_semantic_failure`: inject a `SemanticIndexer` that raises on `move_file`; assert post-failure SQLite still shows the OLD path (rollback succeeded) and `mcp_errors_by_type_total{module="mcp_server.dispatcher.dispatcher_enhanced", exception="IndexingError"}` increments by 1.

### SL-docs — Documentation & spec reconciliation

- **Scope**: Refresh docs catalog, update cross-cutting documentation touched by SL-1..5, and append post-execution amendments to P14's spec section if any IF-freeze turned out wrong.
- **Owned files** (`.claude/docs-catalog.json` is canonical if present; at time of planning it does not exist — this lane scaffolds it if missing):
  - Root: `README.md`, `CHANGELOG.md`, `AGENTS.md`, `CLAUDE.md`
  - `docs/**` (architecture section for cross-repo search + reranking; env-var reference for `MCP_ARTIFACT_FULL_SIZE_LIMIT`, `MCP_WATCHER_SWEEP_MINUTES`; schema-versioning note)
  - `.claude/docs-catalog.json` (scaffold if missing)
  - `specs/phase-plans-v1.md` — append `### Post-execution amendments` subsection under the P14 heading if any IF signature changed during execution (e.g., rename of `retrieval/reranker.py` → `indexer/reranker.py` reuse is an expected amendment).
- **Interfaces provided**: (none)
- **Interfaces consumed**: (none)
- **Parallel-safe**: no (terminal)
- **Depends on**: SL-1, SL-2, SL-3, SL-4, SL-5
- **Tasks**:

| Task ID | Type | Depends on | Files in scope | Action |
|---|---|---|---|---|
| SL-docs.1 | docs | — | `.claude/docs-catalog.json` | If present, rescan via `python3 "$(git rev-parse --show-toplevel)/.claude/skills/_shared/scaffold_docs_catalog.py" --rescan`. If not present, create with the baseline doc list. |
| SL-docs.2 | docs | SL-docs.1 | per catalog + `docs/**` | Update cross-repo architecture notes (reranker wiring, dep-graph), env-var reference (`MCP_ARTIFACT_FULL_SIZE_LIMIT`, `MCP_WATCHER_SWEEP_MINUTES`), schema-migration note. Append P14 alias to each touched file's `touched_by_phases`. Cite constants by name, not literal. |
| SL-docs.3 | docs | SL-docs.2 | `specs/phase-plans-v1.md` | Append `### Post-execution amendments` under P14 heading recording: (a) spec said `mcp_server/retrieval/reranker.py`, actual landing point is `mcp_server/indexer/reranker.py`; (b) any other IF deviations observed at execute-phase time. |
| SL-docs.4 | verify | SL-docs.3 | — | Run `markdownlint` if configured (`package.json`/repo script); otherwise no-op. |

## Execution Notes

- **Single-writer files with disjoint line-range ownership**:
  - `mcp_server/dispatcher/cross_repo_coordinator.py` — SL-1 owns L79-110 + L328-370; SL-2 owns L459-502. Imports at top-of-file are the add/add conflict surface: SL-1 adds `from mcp_server.indexer.reranker import RerankerFactory` on a new line (the `IReranker as Reranker` import already exists at L18); SL-2 adds `from mcp_server.dependency_graph.aggregator import DependencyGraphAnalyzer` on a new line. Place imports alphabetically in the `mcp_server.*` block; resolution is trivial.
  - `mcp_server/artifacts/artifact_upload.py` — SL-3 owns L192-212; SL-4 owns L330 + L339-341. Imports: SL-3 adds `from mcp_server.storage.schema_migrator import SchemaMigrator`; SL-4 adds `from mcp_server.artifacts.delta_policy import DeltaPolicy, DeltaDecision`. Alphabetical placement.
- **Known destructive changes**: none — every lane is purely additive or in-place wiring of previously-stubbed methods. No file deletions; no public-symbol renames.
- **Expected add/add conflicts**: only the two import-block cases above. Pre-authorize `git checkout --theirs` for `cross_repo_coordinator.py` and `artifact_upload.py` import sections at merge time.
- **SL-0 preamble**: not required — no cross-lane shared module stubs.
- **SL-0 re-exports**: n/a.
- **Worktree naming**: execute-phase allocates names via `scripts/allocate_worktree_name.sh`.
- **Stale-base guidance (verbatim)**: Lane teammates working in isolated worktrees do not see sibling-lane merges automatically. If a lane finds its worktree base is pre-<first upstream dependency's merge>, it MUST stop and report rather than committing — the orchestrator will re-spawn or rebase. Silent `git reset --hard` or `git checkout HEAD~N -- …` in a stale worktree produces commits that destroy peer-lane work on `--no-ff` merge. Specifically: **SL-4 must rebase onto `main` AFTER SL-3 merges** before beginning IMPL; if `git log --oneline main ^HEAD -- mcp_server/artifacts/artifact_upload.py` shows SL-3's merge commit absent, stop.
- **Lock re-entry note for SL-5**: `IndexingLockRegistry` (P12 SL-2) uses a reentrant RLock. The `two_phase_commit` wrapper on `dispatcher_enhanced.move_file` must NOT acquire `lock_registry.acquire(repo_id)` itself — the caller (`watcher_multi_repo._move_with_ctx` L192-207) already holds it. Direct-programmatic callers outside the watcher loop must acquire the lock explicitly; SL-5 documents this in a module docstring on `dispatcher_enhanced.move_file`.
- **`bypass_branch_guard` on `enqueue_full_rescan`**: P14 SL-5's sweeper does NOT pass this parameter. Do not propagate it.
- **Spec deviations to record (in SL-docs.3 + commit messages)**:
  1. **Reranker module path** — spec L742 names `mcp_server/retrieval/reranker.py`; P14 reuses existing `mcp_server/indexer/reranker.py` (has full `IReranker` ABC + `RerankerFactory`). Rationale: avoid parallel abstractions; existing module is the canonical reranker surface.
  2. **`watcher_multi_repo.py` location** — spec L735 lists `mcp_server/watcher_multi_repo.py` (correct); some plans may have assumed `mcp_server/watcher/watcher_multi_repo.py` — the file is at the package root.
  3. **Dispatcher implementation** — spec implies a `dispatcher.py`; actual implementation is `mcp_server/dispatcher/dispatcher_enhanced.py`. SL-5 wraps `move_file` at L2146 of that file.
- **Existing failing tests (from P13 handoff)**: `TestRemoveFileSemanticCleanup` in `mcp_server` tests is known-failing pre-P13 and unrelated to P14 — do not block SL-5.VERIFY on it. Filter or xfail at SL-5 VERIFY time if encountered.

## Acceptance Criteria

- [ ] `tests/test_cross_repo_reranker.py::test_rerank_changes_order_with_fake_reranker` passes: a fake `IReranker` that reverses input induces the reversed order on aggregated results. (Acceptance #1)
- [ ] `tests/test_dependency_aware_search.py::test_three_repo_dep_graph_nonempty` passes: `_get_repository_dependencies` returns a non-empty `Set[str]` for each of three test repos with `requirements.txt` / `package.json` / `go.mod` / `Cargo.toml`. (Acceptance #2)
- [ ] `tests/test_schema_migration.py` has three passing tests covering unknown → refuse, older known → migrate, equal → pass; each asserts the exact `ArtifactError` subclass raised or returned artifact shape. (Acceptance #3)
- [ ] `tests/test_artifact_auto_delta.py::test_publisher_switches_to_delta_when_env_low` passes: with `MCP_ARTIFACT_FULL_SIZE_LIMIT=1` and a recorded previous artifact, metadata emits `artifact_type="delta"` and `delta_from=<prev_id>`. (Acceptance #4)
- [ ] `tests/test_watcher_sweep.py::test_sweeper_recovers_missed_event` passes: a file created while watchdog is muted is picked up by `sweeper.sweep_once()` and produces an `on_missed_path` call. (Acceptance #5)
- [ ] `tests/test_rename_atomicity.py::test_rename_single_remove_single_add` passes: post-rename SQLite query `SELECT relative_path FROM files WHERE repository_id=? AND relative_path IN ('foo.py','bar.py')` returns exactly `[('bar.py',)]`. (Acceptance #6)
- [ ] `tests/test_rename_atomicity.py::test_rename_rollback_on_semantic_failure` passes: semantic-indexer failure during `dispatcher_enhanced.move_file` rolls SQLite back to the OLD path and increments `mcp_errors_by_type_total{exception="IndexingError"}` by 1.
- [ ] `uv lock --locked` is clean after all lanes merge.
- [ ] `ruff check mcp_server/` is clean for files touched by P14.

## Verification

Commands to run after all lanes merge:

```bash
# Full P14 suite
uv run pytest \
  tests/test_cross_repo_reranker.py \
  tests/test_dependency_graph_parsers.py \
  tests/test_dependency_aware_search.py \
  tests/test_schema_migrator.py \
  tests/test_schema_migration.py \
  tests/test_delta_policy.py \
  tests/test_artifact_auto_delta.py \
  tests/test_chunk_query_pagination.py \
  tests/test_watcher_sweep.py \
  tests/test_rename_atomicity.py \
  -v

# P12/P13 regression suite (must still pass)
uv run pytest \
  tests/test_cross_repo_coordinator.py \
  tests/test_artifact_manifest_v2.py \
  tests/test_artifact_lifecycle.py \
  tests/test_artifact_publish_race.py \
  tests/test_delta_artifacts.py \
  tests/test_watcher.py \
  tests/test_watcher_multi_repo.py \
  tests/test_incremental_indexer.py \
  -v

# Lockfile + lint
uv lock --locked
ruff check mcp_server/dispatcher/cross_repo_coordinator.py \
           mcp_server/dependency_graph/ \
           mcp_server/storage/schema_migrator.py \
           mcp_server/artifacts/delta_policy.py \
           mcp_server/artifacts/artifact_upload.py \
           mcp_server/artifacts/artifact_download.py \
           mcp_server/artifacts/publisher.py \
           mcp_server/indexing/incremental_indexer.py \
           mcp_server/watcher/sweeper.py \
           mcp_server/dispatcher/dispatcher_enhanced.py \
           mcp_server/watcher_multi_repo.py

# Metrics smoke check (P13 errors_by_type counter still surfacing)
uv run python -c "
from mcp_server.metrics.prometheus_exporter import PrometheusExporter
exp = PrometheusExporter()
assert hasattr(exp, 'errors_by_type'), 'P13 SL-5 counter missing'
print('ok: errors_by_type present')
"
```
