# Changelog

## [vindex-latest.index-latest.1] - 2026-04-03

## What's Changed

- fix: replace tree_sitter_languages ctypes loading with cross-platform tree_sitter_language_pack (ViperJuice)
- fix: lower flashrank version constraint from >=0.3.0 to >=0.2.0 (ViperJuice)
- feat: cross-repo readiness — profiles fallback, env-var substitution, auto-heal, UX polish (ViperJuice)
- docs: sync documentation with recent feature additions (ViperJuice)
- fix: wire IgnorePatternManager into semantic rebuild to exclude fixtures (ViperJuice)
- fix: correct Qwen vLLM endpoint URL and profile URL priority in settings (ViperJuice)
- feat: wire profile summarization config into ChunkWriter (ViperJuice)
- fix: achieve 17/17 benchmark score with Qwen/Qwen3-Embedding-8B (ViperJuice)
- benchmark: full matrix with working rerankers (flashrank + cross-encoder) (ViperJuice)
- fix: reranker packaging, index pollution, and retrieval quality (ViperJuice)
- fix(hook): resolve mcp-index CLI via .venv/bin when not on PATH (ViperJuice)

## Pull Requests


## Statistics
- Commits: 11
- Contributors: 1
- Files changed: 46


## Feature Highlights
- 🚀 Dynamic plugin loading system
- 📊 Comprehensive monitoring with Prometheus & Grafana
- 🔍 48+ language support via tree-sitter
- 📝 Document processing (Markdown & PlainText)
- 🔐 Security with JWT authentication
- ⚡ High-performance caching system


All notable changes to Code-Index-MCP will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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