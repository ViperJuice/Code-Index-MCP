# Changelog

All notable changes to Code-Index-MCP will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added (P17 — Durability & Multi-Instance Safety)
- **Registry flock protocol** (IF-0-P17-1): `RepositoryRegistry.save()` acquires
  `fcntl.flock(LOCK_EX)` on a sibling `.lock` file, then performs a read-merge-write
  with an atomic `rename()`.  Two concurrent processes calling `save()` against the same
  file no longer lose each other's writes. (`mcp_server/storage/repository_registry.py`,
  `tests/test_registry_concurrency.py`)
- **Singleton reset wired**: `reset_process_singletons()` (P16 IF-0-P16-4 stub) is now
  called at the top of `initialize_stateless_services()`.  Repeat-init in the same
  Python process yields fresh managers. (`mcp_server/cli/bootstrap.py`,
  `tests/test_singleton_reset.py`)
- **Ref-poller edge-case handling** (SL-2): `RefPoller` detects detached HEAD,
  force-push, and branch-rename; each triggers `enqueue_full_rescan(repo_id)` to prevent
  incremental indexing on a rewritten history. (`mcp_server/watcher/ref_poller.py`,
  `tests/test_ref_poller_edges.py`)
- **Sweeper observability** (SL-2): `WatcherSweeper` exceptions emit `WARNING` log and
  increment `mcp_watcher_sweep_errors_total` Prometheus counter.
  (`mcp_server/watcher/sweeper.py`, `tests/test_sweeper_observability.py`)
- **MCP_MAX_FILE_SIZE_BYTES enforced** (SL-2): Dispatcher walker (`index_directory`)
  now skips files larger than `MCP_MAX_FILE_SIZE_BYTES` (default 10 MiB); oversize
  files are logged and skipped without stalling the indexer.
  (`mcp_server/dispatcher/dispatcher_enhanced.py`)
- **Checkpoint clears on clean exit** (SL-2): `IncrementalIndexer` clears the
  checkpoint file even when `errors` is non-empty on clean exit; a re-run starts fresh
  rather than resuming from a stale error state.
  (`mcp_server/indexing/incremental_indexer.py`)
- **ENOSPC → read-only store** (SL-3): `SQLiteStore` catches `OSError(ENOSPC)` on
  `commit()`, transitions to read-only mode, and increments
  `mcp_storage_readonly_total`.  The server keeps serving reads without crashing.
  (`mcp_server/storage/sqlite_store.py`, `tests/test_disk_full.py`)
- **Schema migration backup** (SL-3): `SchemaMigrator.migrate_artifact()` writes a
  timestamped `.backup` copy of the DB before any migration; rollback-on-failure
  restores from backup. (`mcp_server/storage/schema_migrator.py`,
  `tests/test_schema_migration_backup.py`)
- **UnknownSchemaVersionError in core/errors.py** (SL-3): `UnknownSchemaVersionError`
  promoted from `schema_migrator.py` to `mcp_server/core/errors.py`, extending the P16
  IF-0-P16-1 taxonomy by one class.
- **RerankerFactory.create_default()** (SL-4): `RerankerFactory.create_default()`
  returns a functional reranker; resolves the P14 carry-over.
  (`mcp_server/plugins/reranker_factory.py`)
- **Ruff F401 clean** (SL-4): `ruff F401` count across `mcp_server/dispatcher`,
  `mcp_server/storage`, `mcp_server/watcher` is 0.
- **Multi-instance runbook** (SL-docs): `docs/operations/multi-instance.md` — flock
  protocol, singleton-reset semantics, DR/recovery procedure.
- **Vocabulary freeze** (IF-0-P17-1): Registry flock + read-merge-write pattern is
  frozen as a named interface for cross-phase reference.
- **Test-debt ledger** (SL-docs): `docs/operations/known-test-debt.md` enumerates
  residual failures after P17 close (56 total; 9 cross-repo coordinator carry-over +
  47 pre-existing in other modules).

### Added (P16 — Shared Vocabulary Preamble)
- **Frozen error taxonomy** (IF-0-P16-1): New error classes `TransientArtifactError`, `TerminalArtifactError`, and `SchemaMigrationError` in `mcp_server/core/errors.py` for structured error handling in artifact operations. Stubs only — no consumer wiring.
- **Lazy env-var getters** (IF-0-P16-2): Five new environment variable getters in `mcp_server/config/env_vars.py` — `get_max_file_size_bytes()`, `get_artifact_retention_count()`, `get_artifact_retention_days()`, `get_disk_readonly_threshold_mb()`, and `get_publish_rollback_enabled()` — with sensible defaults. Stubs only — no consumer wiring.
- **ValidationError dataclass + validate_production_config** (IF-0-P16-3): New `ValidationError` dataclass and keyword-only `validate_production_config(environment: str = "production")` function in `mcp_server/config/validation.py`. Stubs only — no consumer wiring.
- **reset_process_singletons** (IF-0-P16-4): New utility function in `mcp_server/cli/bootstrap.py` for test isolation and graceful restarts. Stubs only — no consumer wiring.

### Added (P15 — Security Hardening)
- **Plugin sandboxing** (IF-0-P15-1): Plugins execute in isolated worker processes with JSON-line IPC, 30s timeout, and capability-based restrictions. New `mcp_server/sandbox/` package with supervisor and adapter; `SandboxedPlugin` wraps instances with `CapabilitySet` (filesystem, network, subprocess, env_read). (`mcp_server/sandbox/supervisor.py`, `mcp_server/plugins/sandboxed_plugin.py`, `tests/security/test_plugin_sandbox.py`)
- **Metrics endpoint auth** (IF-0-P15-2): `/metrics` requires `Authorization: Bearer <token>` (app-level) or NetworkPolicy restriction (k8s-only). Wired via `require_auth("metrics")` middleware. (`mcp_server/security/security_middleware.py`, `mcp_server/api/gateway.py`)
- **Artifact attestation** (IF-0-P15-3): Published artifacts are signed with `gh attestation sign` and verified with `gh attestation verify` (requires `GITHUB_TOKEN` with `attestations:write` scope). Mode controlled by `MCP_ATTESTATION_MODE` (enforce/warn/skip). (`mcp_server/artifacts/attestation.py`, `mcp_server/artifacts/publisher.py`, `mcp_server/artifacts/artifact_download.py`)
- **Path traversal guard + token validator** (IF-0-P15-4): Search results filtered through `PathTraversalGuard.normalize_and_check(path, allowed_roots)` (controlled by `MCP_ALLOWED_ROOTS` env). Startup validates `GITHUB_TOKEN` for all five required scopes via `TokenValidator.validate_scopes()` (soft-fail default; hard-fail with `MCP_REQUIRE_TOKEN_SCOPES=1`). Rate-limit backoff on cross-repo artifact fetches. (`mcp_server/security/path_guard.py`, `mcp_server/security/token_validator.py`)

### Added (P14 — Multi-Repo Completeness + Schema Evolution)
- **Reranker wiring** (IF-0-P14-1): `CrossRepoCoordinator.__init__` now accepts an injected `IReranker` (`mcp_server/indexer/reranker.py`); falls back to `RerankerFactory.create_default()` with graceful degradation to `None`. (`mcp_server/dispatcher/cross_repo_coordinator.py`, `tests/test_cross_repo_reranker.py`)
- **Dependency graph** (IF-0-P14-2): New `mcp_server/dependency_graph/` package with `parsers.py`, `aggregator.py`, and ecosystem parsers (Python/npm/Go/Cargo). `_get_repository_dependencies` returns resolved repo IDs. (`mcp_server/dispatcher/cross_repo_coordinator.py`)
- **Schema migrator** (IF-0-P14-3): New `mcp_server/storage/schema_migrator.py` with `SchemaMigrator`, `UnknownSchemaVersionError`, and `SchemaMigrationError`. Artifact manifests carry `schema_version`; `check_compatibility` gates downloads by version. (`mcp_server/artifacts/artifact_download.py`)
- **Auto-delta artifacts** (IF-0-P14-4): New `mcp_server/artifacts/delta_policy.py` with `DeltaPolicy`/`DeltaDecision`. Publisher switches to delta mode when artifact exceeds `MCP_ARTIFACT_FULL_SIZE_LIMIT` (default 500 MB). `_get_chunk_ids_for_path` accepts `limit`/`offset` pagination. (`mcp_server/artifacts/publisher.py`, `mcp_server/artifacts/artifact_upload.py`)
- **Watcher sweep + rename atomicity** (IF-0-P14-5): New `mcp_server/watcher/sweeper.py::WatcherSweeper` runs full-tree scans every `MCP_WATCHER_SWEEP_MINUTES` (default 60) to recover dropped inotify/FSEvents events. `move_file` wrapped in `two_phase_commit`; raises `IndexingError` on semantic failure. (`mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/watcher_multi_repo.py`)

## [1.1.0] - 2026-04-14

### Security
- **#40** Removed hardcoded `JWT_SECRET_KEY` and `DEFAULT_ADMIN_PASSWORD` defaults from
  `gateway.py`. Server now raises `RuntimeError` at startup if either env var is unset,
  preventing silent production deployments with known-weak credentials.
  `docker-compose.yml` and `.env.example` updated to use env var substitution with no
  insecure literal fallbacks. (`mcp_server/gateway.py`, `docker-compose.yml`, `.env.example`)

### Fixed
- **#41** `get_index_status()` `symbols_count` field now returns the actual number of
  symbols stored for the file (was always `0`). Added `SQLiteStore.count_symbols_for_file()`
  and wired it into `IndexEngine.get_index_status()`.
  (`mcp_server/storage/sqlite_store.py`, `mcp_server/indexer/index_engine.py`)
- **#41** Reference storage in `_store_parse_result()` now calls `get_symbol()` +
  `store_reference()` instead of silently passing; references are persisted in
  `symbol_references` and queryable via `get_references()`.
  (`mcp_server/indexer/index_engine.py`)
- **#42** Removed broken `curl .../install-mcp.sh` line from README (script does not
  exist). Replaced silent TODO in `watcher_multi_repo._create_and_upload_artifact()` with
  an explicit `logger.warning` directing users to the CI workflow for artifact upload.
  (`README.md`, `mcp_server/watcher_multi_repo.py`)
- Windows CI compatibility: forward-slash path normalization in `SQLiteStore.store_file()`,
  `signal.SIGALRM` guard in `mcp_server_cli.py`, double-quoted git commit messages in
  tests, `>= 0` timing assertions for low-resolution Windows clocks.
  (`mcp_server/storage/sqlite_store.py`, `scripts/cli/mcp_server_cli.py`,
  `tests/test_utilities.py`, `tests/test_repository_management.py`,
  `tests/test_multi_repo_search.py`, `tests/test_dispatcher_advanced.py`)
- Benchmark scripts updated to current SQLiteStore/plugin API: replaced removed
  `store.add_symbol()` with `create_repository` + `store_file` + `store_symbol`, and
  replaced obsolete `plugin.extract_symbols()` with `plugin.indexFile()` with
  `IndexShard` dict-style access.
  (`benchmarks/symbol_lookup_benchmark.py`, `benchmarks/semantic_search_benchmark.py`,
  `benchmarks/indexing_speed_benchmark.py`)

### Added
- Backstage catalog registration (`catalog-info.yaml`) and standard repo layout
  (`docs/`, `mkdocs.yml`). (`04ea8ff`)
- Consiliency maintenance worker trigger workflow for scheduled index health checks.
  (`.github/workflows/`, `72f15a5`)

### Added
- Query-intent routing: symbol-pattern queries (`class Foo`, `def bar`, CamelCase,
  `snake_case`) route directly to the symbols table, bypassing BM25. Fixes retrieval for
  class/function lookups that previously returned wrong files.
  (`mcp_server/dispatcher/query_intent.py`, `dispatcher_enhanced.py`)
- `FlashRankReranker` and `CrossEncoderReranker` (OSS, lazy-loaded); all three rerankers
  share a unified sync interface. Configured via `RERANKER_TYPE` env var.
  (`mcp_server/dispatcher/reranker.py`)
- Matrix benchmark: 17-query suite covering all mode × embedding × reranker combinations.
  (`scripts/run_matrix_benchmark.py`)
- LLM chunk summarization: `ChunkWriter` / `LazyChunkWriter` / `ComprehensiveChunkWriter`;
  per-profile config via `summarization:` block in `code-index-mcp.profiles.yaml`.
  (`mcp_server/indexing/summarization.py`)
- Initial project structure with plugin-based architecture
- FastAPI-based MCP server implementation
- Python plugin with Jedi integration for advanced code analysis
- Tree-sitter wrapper for language parsing
- Semantic indexer with Voyage AI integration
- C4 architecture diagrams using Structurizr DSL
- Comprehensive documentation structure
- Plugin base class for language extensions
- File watcher skeleton for real-time updates
- Cloud sync stub implementation

### Changed
- Enhanced Python plugin with proper AST analysis
- Improved error handling in gateway endpoints
- Updated project documentation and README

### Added
- MCP `InitializeResult.instructions` field populated: every connecting client receives
  search-first guidance at handshake time, over any transport (stdio, SSE, HTTP).
  (`scripts/cli/mcp_server_cli.py`)
- `last_indexed` field added to `search_code` results, surfacing the index timestamp so
  agents can assess line-number freshness. (`scripts/cli/mcp_server_cli.py`,
  `mcp_server/storage/sqlite_store.py`)
- `FileWatcher` now auto-starts inside `initialize_services()` after the dispatcher is
  ready, so the index stays current without any manual setup. Stopped automatically in
  `main()` `finally` block on server exit. Only active when using `EnhancedDispatcher`
  (not BM25-only `SimpleDispatcher` mode). (`scripts/cli/mcp_server_cli.py`)
- Auto-index on first run: when no index exists, `initialize_services()` creates
  `.mcp-index/code_index.db` and indexes the repository in a background thread. The MCP
  server is immediately responsive; search results populate as indexing progresses.
  Set `MCP_AUTO_INDEX=false` to disable for large repos and run the `reindex` tool
  manually. (`scripts/cli/mcp_server_cli.py`)
- `search_code` responses now include `"indexing_in_progress": true` when the initial
  background index is still running, preventing agents from concluding "no results"
  prematurely while the index is being built. (`scripts/cli/mcp_server_cli.py`)
- `FileWatcher` start deferred until after background initial index completes, eliminating
  concurrent SQLite write contention between the bulk `index_directory()` pass and the
  watchdog event handler on first-run repos. (`scripts/cli/mcp_server_cli.py`)
- `.gitignore` entries for `.mcp-index/code_index.db-shm` and `.mcp-index/code_index.db-wal`
  (SQLite WAL mode sidecar files) added to `install.sh` and written automatically during
  auto-init so WAL files never appear as untracked. (`mcp-index-kit/install.sh`,
  `scripts/cli/mcp_server_cli.py`)
- `code-index-mcp.profiles.yaml` discovery now searches `MCP_PROFILES_PATH` env var →
  CWD → server package directory in that order. Previously the file was only found at CWD,
  so semantic profiles silently vanished when `cwd` was set to another repo. Fallback to the
  server's own installation means semantic search and summarization work out-of-the-box in
  any repo. (`mcp_server/config/settings.py`)
- `${VAR:default}` env-var substitution supported in all `base_url` fields of
  `code-index-mcp.profiles.yaml`. Set `VLLM_EMBEDDING_BASE_URL` or
  `VLLM_SUMMARIZATION_BASE_URL` to point at any server without editing the YAML.
  (`mcp_server/config/settings.py`, `code-index-mcp.profiles.yaml`)
- File-count guard before auto-index: if the target repo exceeds `MCP_AUTO_INDEX_MAX_FILES`
  (default 100 000), auto-indexing is skipped and a warning is logged. Prevents indefinite
  startup I/O on very large monorepos. (`scripts/cli/mcp_server_cli.py`)
- BM25 FTS auto-heal: on startup, if an existing index has tracked files but an empty
  `fts_code` table (e.g. after a migration or partial corruption), a background thread
  calls `rebuild_fts_code()` automatically. Previously the empty state persisted until
  a manual `reindex` tool call. (`scripts/cli/mcp_server_cli.py`)

### Fixed
- `scripts/cli/mcp_server_cli.py` was calling undefined `get_settings()` on every tool
  invocation, crashing the server before any tool could execute. Replaced with
  `Settings.from_environment()`. (`scripts/cli/mcp_server_cli.py`)
- `LazyChunkWriter.__init__` was missing the `summarization_config` parameter despite
  the base class `ChunkWriter` accepting it, causing a `TypeError` on every server
  startup. (`mcp_server/indexing/summarization.py`)
- File watcher `trigger_reindex()` now calls `remove_file()` before `index_file()`,
  preventing stale chunks from persisting when a file edit changes chunk boundaries.
  (`mcp_server/watcher.py`)
- `EnhancedDispatcher.remove_file()` now evicts `_file_cache` before SQLite deletion,
  preventing a skip-on-reindex race where an unchanged-hash file would be left absent
  from the index after a forced removal. (`mcp_server/dispatcher/dispatcher_enhanced.py`)
- `SQLiteStore.remove_file()` now deletes `symbol_trigrams` before `symbols`, fixing a
  FK constraint failure that silently left file rows in the DB on removal.
  (`mcp_server/storage/sqlite_store.py`)
- `SQLiteStore.remove_file()` now clears `fts_code` entries regardless of whether
  `file_id` was stored as an integer, absolute path, or relative path string.
  (`mcp_server/storage/sqlite_store.py`)
- `SQLiteStore.search_bm25()` now includes `last_modified` in result rows so the
  `last_indexed` field is non-null in search results. (`mcp_server/storage/sqlite_store.py`)
- Semantic rebuild (`_build_semantic_baseline`) now uses `IgnorePatternManager`, respecting
  `.gitignore` and `.mcp-index-ignore`. Previously indexed `test_workspace/` (20,803 Django
  fixture files), causing 7-hour rebuilds. (`mcp_server/cli/index_management.py`)
- Default ignore patterns expanded: `test_workspace/`, `test_repos/`, `vendor/`,
  `third_party/`, `baml_client/`, `*_pb2.py`, `*_pb2_grpc.py`.
  (`mcp_server/core/ignore_patterns.py`)
- `code-index-mcp.profiles.yaml` `base_url` now takes precedence over `OPENAI_API_BASE`
  env default (was reversed, routing oss_high embeddings to wrong endpoint).
  (`mcp_server/config/settings.py`)
- Corrected `oss_high` vLLM `base_url` from `127.0.0.1:8001` to `ai:8001`.
  (`code-index-mcp.profiles.yaml`)
- Resolved merge conflicts in treesitter_wrapper.py
- Fixed Python plugin implementation issues
- Tree-sitter byte-offset/char-offset mismatch in Python plugin: symbol names were corrupted in files
  containing multi-byte characters (e.g. em-dashes in docstrings) before the first class/function
  definition. Fixed by using `node.text.decode("utf-8")` in `plugin.py` and `plugin_semantic.py`.
- BM25/FTS path was bypassed when `semantic=True` but no Qdrant indexer was initialized. Fixed in
  `dispatcher_enhanced.py` so the FTS path runs whenever the semantic indexer is absent.
- Python plugin `_preindex()` now excludes `htmlcov`, `.venv`, `venv`, `node_modules`, `__pycache__`,
  `.git`, `dist`, `build` directories to prevent junk results from polluting in-memory indexes.

### Security
- Added input validation for file paths
- Implemented basic security checks in API endpoints
- Added secret detection patterns

## [0.1.0] - TBD

### Planned Features
- Complete implementation of C, C++, JavaScript, Dart, and HTML/CSS plugins
- SQLite-based local storage with FTS5
- Full file system watcher implementation
- Performance optimizations and caching
- Authentication and authorization system
- Comprehensive test suite
- Production deployment guide

---

## Version History

### Pre-release Development
- Project inception and architecture design
- Core infrastructure setup
- Initial plugin system implementation