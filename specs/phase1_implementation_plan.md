# Phase 1: Foundation & Cleanup - Implementation Plan

## Executive Summary

Phase 1 focuses on ensuring the core indexing and search works reliably for a single user. This plan defines the architecture, interface contracts, and swim lanes for parallel execution.

**Phase Goal**: Verify and stabilize the SQLite persistence layer, validate dispatcher fallback mechanisms, and ensure Docker minimal image builds correctly.

---

## A. Architectural Baseline & Component Catalog

### A.1 Files to be Modified

| File Path | Change Type | Purpose |
|-----------|-------------|---------|
| `mcp_server/__init__.py` | **MODIFY** | Add proper exports, version consistency |
| `mcp_server/storage/sqlite_store.py` | **MODIFY** | Fix schema gaps (file_moves table in init), add missing column checks |
| `mcp_server/dispatcher/dispatcher_enhanced.py` | **MODIFY** | Improve fallback error handling, add timeout for Windows |
| `mcp_server/gateway.py` | **AUDIT** | Verify initialization order, no code changes expected |
| `requirements.txt` | **MODIFY** | Clean up unused deps, separate core vs optional |
| `docker/dockerfiles/Dockerfile.minimal` | **MODIFY** | Verify build, fix any missing dependencies |

### A.2 Files to be Added

| File Path | Purpose |
|-----------|---------|
| `requirements-core.txt` | Core dependencies for minimal build |
| `requirements-dev.txt` | Development and testing dependencies |
| `requirements-semantic.txt` | Optional semantic search dependencies |
| `tests/integration/test_phase1_foundation.py` | Integration tests for Phase 1 |

### A.3 Classes / Types

#### Modified Classes

| Class | File | Changes |
|-------|------|---------|
| `SQLiteStore` | `mcp_server/storage/sqlite_store.py` | Add `_ensure_file_moves_table()`, improve `_init_schema()` |
| `EnhancedDispatcher` | `mcp_server/dispatcher/dispatcher_enhanced.py` | Add Windows timeout support, improve BM25 fallback |

#### No New Classes Required

Phase 1 focuses on stabilization, not new feature development.

### A.4 Functions / Methods

#### SQLiteStore Modifications

```python
# mcp_server/storage/sqlite_store.py

def _ensure_file_moves_table(self, conn: sqlite3.Connection) -> None:
    """
    Ensure file_moves table exists (idempotent).

    Called during _init_database() after schema check.
    Creates table if migration 002 hasn't run yet.

    Args:
        conn: Active database connection

    Returns:
        None

    Raises:
        sqlite3.OperationalError: If table creation fails
    """
    pass

def _check_column_exists(
    self,
    conn: sqlite3.Connection,
    table: str,
    column: str
) -> bool:
    """
    Check if a column exists in a table.

    Args:
        conn: Active database connection
        table: Table name
        column: Column name to check

    Returns:
        True if column exists, False otherwise
    """
    pass

def health_check(self) -> Dict[str, Any]:
    """
    Perform health check on database.

    Returns:
        Dictionary containing:
        - status: "healthy" | "degraded" | "unhealthy"
        - tables_ok: bool
        - fts_ok: bool
        - wal_mode: bool
        - schema_version: int
        - error: Optional[str]
    """
    pass
```

#### EnhancedDispatcher Modifications

```python
# mcp_server/dispatcher/dispatcher_enhanced.py

def _load_all_plugins_with_timeout(self, timeout_seconds: int = 5) -> None:
    """
    Load all plugins with cross-platform timeout support.

    Args:
        timeout_seconds: Maximum time to wait for plugin loading

    Returns:
        None (updates internal state)

    Note:
        Uses threading.Timer on Windows, signal.alarm on Unix
    """
    pass

def _bm25_fallback_search(
    self,
    query: str,
    limit: int = 20
) -> List[SearchResult]:
    """
    Direct BM25 search fallback when plugins unavailable.

    Args:
        query: Search query string
        limit: Maximum results to return

    Returns:
        List of SearchResult dictionaries

    Raises:
        No exceptions - returns empty list on failure
    """
    pass
```

### A.5 Data Structures

#### Database Schema (Verified Complete)

The following tables must exist after Phase 1:

| Table | Status | Notes |
|-------|--------|-------|
| `schema_version` | ✅ Exists | Created in `_init_schema()` |
| `repositories` | ✅ Exists | Created in `_init_schema()` |
| `files` | ✅ Exists | With columns: `content_hash`, `is_deleted`, `deleted_at` |
| `symbols` | ✅ Exists | Created in `_init_schema()` |
| `symbol_references` | ✅ Exists | Created in `_init_schema()` |
| `imports` | ✅ Exists | Created in `_init_schema()` |
| `fts_symbols` | ✅ Exists | FTS5 virtual table |
| `fts_code` | ✅ Exists | FTS5 virtual table |
| `symbol_trigrams` | ✅ Exists | For fuzzy search |
| `embeddings` | ✅ Exists | For semantic search |
| `query_cache` | ✅ Exists | Query result caching |
| `parse_cache` | ✅ Exists | AST parse caching |
| `migrations` | ✅ Exists | Migration tracking |
| `index_config` | ✅ Exists | Index configuration |
| `file_moves` | ⚠️ **MIGRATION ONLY** | Must be created in init if migration not run |

#### Configuration DTOs

```python
@dataclass
class Phase1HealthStatus:
    """Health status for Phase 1 components."""
    sqlite_ok: bool
    fts5_ok: bool
    wal_mode: bool
    schema_version: int
    dispatcher_ok: bool
    plugins_loaded: int
    bm25_fallback_ok: bool
    errors: List[str]

    @property
    def overall_status(self) -> str:
        if not self.sqlite_ok or not self.dispatcher_ok:
            return "unhealthy"
        if self.errors:
            return "degraded"
        return "healthy"
```

---

## B. Code-Level Interface Contracts

### B.1 SQLiteStore Interface Contract

**Owner**: Swim Lane 1 (Core Indexing)
**Consumers**: EnhancedDispatcher, Gateway, BM25Indexer

```python
class SQLiteStore:
    """
    INTERFACE CONTRACT - IF-1-SQLITE

    Invariants:
    - Database file must be writable
    - WAL mode must be enabled
    - FTS5 must be available
    - All tables must exist before any operation

    Thread Safety:
    - Connection creation is thread-safe (new connection per operation)
    - No shared mutable state between operations

    Error Behavior:
    - OperationalError on schema issues → health_check returns degraded
    - IntegrityError on constraint violations → raise to caller
    - All other exceptions → log and re-raise
    """

    def __init__(self, db_path: str, path_resolver: Optional[PathResolver] = None):
        """
        Initialize store with database path.

        Postconditions:
        - Database file exists (created if needed)
        - WAL mode enabled
        - All core tables exist
        - FTS5 tables exist
        """
        pass

    def health_check(self) -> Dict[str, Any]:
        """
        Check database health.

        Returns dict with keys:
        - status: "healthy" | "degraded" | "unhealthy"
        - tables: Dict[str, bool] - table existence
        - fts5: bool - FTS5 availability
        - wal: bool - WAL mode status
        - version: int - schema version
        - error: Optional[str] - error message if unhealthy
        """
        pass

    def search_bm25(
        self,
        query: str,
        table: str = "fts_code",
        limit: int = 20,
        offset: int = 0,
        columns: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        BM25 search with graceful table fallback.

        Behavior:
        - Tries requested table first
        - Falls back to alternative tables if not found
        - Returns empty list on all failures (no exceptions)

        Returns list of dicts with keys:
        - filepath/file_path: str
        - snippet: Optional[str]
        - score: float
        - language: Optional[str]
        """
        pass
```

### B.2 EnhancedDispatcher Interface Contract

**Owner**: Swim Lane 1 (Core Indexing)
**Consumers**: Gateway, MCP Tools

```python
class EnhancedDispatcher:
    """
    INTERFACE CONTRACT - IF-1-DISPATCHER

    Invariants:
    - Must always provide search results (via plugins or BM25 fallback)
    - Plugin loading must not block indefinitely
    - Semantic search failure must not break BM25 search

    Fallback Chain:
    1. Try loaded plugins
    2. Try lazy-load required plugin
    3. Try semantic search (if enabled)
    4. Fall back to direct BM25
    5. Return empty results (never raise)

    Timeout Behavior:
    - Plugin loading: 5 seconds max
    - Search operations: no timeout (caller's responsibility)
    """

    def __init__(
        self,
        plugins: Optional[List[IPlugin]] = None,
        sqlite_store: Optional[SQLiteStore] = None,
        enable_advanced_features: bool = True,
        use_plugin_factory: bool = True,
        lazy_load: bool = True,
        semantic_search_enabled: bool = True,
        memory_aware: bool = True,
        multi_repo_enabled: bool = None
    ):
        """
        Initialize dispatcher.

        Postconditions:
        - _sqlite_store is set (or None)
        - _semantic_enabled reflects actual availability
        - _plugins may be empty (lazy load)
        - health_check() returns valid status
        """
        pass

    def search(
        self,
        query: str,
        semantic: bool = False,
        limit: int = 20
    ) -> Iterable[SearchResult]:
        """
        Search across all sources with fallback chain.

        Guarantees:
        - Never raises exceptions (logs and returns empty)
        - Results are deduplicated
        - Results are sorted by relevance

        Fallback Priority:
        1. Plugin search (if plugins loaded)
        2. Semantic search (if enabled and semantic=True)
        3. BM25 direct search
        """
        pass

    def lookup(self, symbol: str, limit: int = 20) -> Optional[SymbolDef]:
        """
        Look up symbol definition.

        Guarantees:
        - Never raises (returns None on failure)
        - Tries symbol table first, then BM25
        """
        pass

    def health_check(self) -> Dict[str, Any]:
        """
        Check dispatcher health.

        Returns dict with keys:
        - status: "healthy" | "degraded" | "unhealthy"
        - components: Dict[str, ComponentHealth]
        - plugins: Dict[str, PluginHealth]
        - errors: List[str]
        """
        pass
```

### B.3 Interface Freeze Gate (IF-0-PHASE1)

**Freeze Criteria**:
1. `SQLiteStore.health_check()` returns valid structure
2. `EnhancedDispatcher.search()` returns results without exceptions
3. `EnhancedDispatcher.health_check()` returns valid structure
4. All existing tests pass

**Freeze Date**: Before Swim Lane work begins

---

## C. Exhaustive Change List

### C.1 Files Changed (A = Add, M = Modify, D = Delete)

| Change | File | Reason |
|--------|------|--------|
| **M** | `mcp_server/__init__.py` | Add exports, version check |
| **M** | `mcp_server/storage/sqlite_store.py` | Add health_check, ensure file_moves table |
| **M** | `mcp_server/dispatcher/dispatcher_enhanced.py` | Windows timeout, improved fallback |
| **M** | `requirements.txt` | Split into core/dev/semantic |
| **A** | `requirements-core.txt` | Core dependencies only |
| **A** | `requirements-dev.txt` | Development dependencies |
| **A** | `requirements-semantic.txt` | Optional semantic deps |
| **M** | `docker/dockerfiles/Dockerfile.minimal` | Use requirements-core.txt |
| **A** | `tests/integration/test_phase1_foundation.py` | Phase 1 integration tests |
| **M** | `tests/test_sqlite_store.py` | Add health_check tests |
| **M** | `tests/test_dispatcher.py` | Add fallback chain tests |

### C.2 Schema Changes

| Change | Table/Column | Migration |
|--------|--------------|-----------|
| **VERIFY** | `file_moves` | Created in migration 002 or init |
| **VERIFY** | `files.content_hash` | Added in migration 002 |
| **VERIFY** | `files.is_deleted` | Added in migration 002 |
| **VERIFY** | `files.deleted_at` | Added in migration 002 |

---

## D. Swim Lane Definitions

### Swim Lane 1: Core Indexing Verification

**Goal**: Verify SQLiteStore persistence and schema stability

**Owner**: Agent 1
**Dependencies**: None (can start immediately)
**Estimated Tasks**: 5

#### Tasks

1. **Task 1.1**: Verify `file_moves` table creation
   - Check if table exists in fresh database
   - Ensure migration 002 runs correctly
   - Add fallback creation in `_init_schema()` if needed

2. **Task 1.2**: Add `health_check()` method to SQLiteStore
   - Check all required tables exist
   - Verify FTS5 availability
   - Confirm WAL mode enabled
   - Return structured health status

3. **Task 1.3**: Verify column existence checks
   - Add `_check_column_exists()` helper
   - Check `content_hash`, `is_deleted`, `deleted_at` on startup
   - Log warnings for missing columns

4. **Task 1.4**: Write unit tests for SQLiteStore health
   - Test with fresh database
   - Test with corrupted schema
   - Test with missing tables

5. **Task 1.5**: Verify `mcp_server/__init__.py` exports
   - Add `__all__` with public exports
   - Verify version matches pyproject.toml
   - Document import patterns

#### Acceptance Criteria

- [ ] `SQLiteStore.health_check()` returns structured status
- [ ] Fresh database has all tables including `file_moves`
- [ ] Missing columns logged as warnings (not errors)
- [ ] All existing SQLite tests pass
- [ ] New health check tests pass

---

### Swim Lane 2: Dispatcher Fallback Validation

**Goal**: Validate EnhancedDispatcher fallback mechanisms

**Owner**: Agent 2
**Dependencies**: IF-1-SQLITE (SQLiteStore interface stable)
**Estimated Tasks**: 5

#### Tasks

1. **Task 2.1**: Add Windows-compatible timeout
   - Use `threading.Timer` instead of `signal.alarm`
   - Detect platform and use appropriate mechanism
   - Test on both Unix and Windows (via mock)

2. **Task 2.2**: Improve BM25 fallback search
   - Extract `_bm25_fallback_search()` method
   - Try multiple table names (`bm25_content`, `fts_code`)
   - Return empty list on all failures

3. **Task 2.3**: Add dispatcher health_check improvements
   - Check plugin loading status
   - Check semantic search availability
   - Check BM25 fallback availability
   - Return structured status

4. **Task 2.4**: Write fallback chain tests
   - Test with no plugins loaded
   - Test with plugin loading timeout
   - Test with BM25-only database
   - Test semantic search failure recovery

5. **Task 2.5**: Verify gateway initialization order
   - Audit `gateway.py` startup_event
   - Document initialization sequence
   - Verify error handling at each step

#### Acceptance Criteria

- [ ] Plugin loading times out after 5s (both platforms)
- [ ] Search always returns results (never raises)
- [ ] BM25 fallback works with multiple table schemas
- [ ] Health check reports accurate status
- [ ] Gateway starts successfully with minimal config

---

### Swim Lane 3: Operations & Docker

**Goal**: Clean up requirements and verify Docker minimal build

**Owner**: Agent 3
**Dependencies**: None (can run in parallel)
**Estimated Tasks**: 4

#### Tasks

1. **Task 3.1**: Split requirements.txt
   - Create `requirements-core.txt` (minimal)
   - Create `requirements-dev.txt` (testing/dev)
   - Create `requirements-semantic.txt` (optional)
   - Update original to reference splits

2. **Task 3.2**: Audit core dependencies
   - Remove unused imports from requirements
   - Verify each dependency is actually used
   - Document optional vs required

3. **Task 3.3**: Update Dockerfile.minimal
   - Use `requirements-core.txt`
   - Verify build completes
   - Test image runs correctly

4. **Task 3.4**: Write Docker integration test
   - Build minimal image
   - Start container
   - Verify health check endpoint
   - Run basic search test

#### Acceptance Criteria

- [ ] `requirements-core.txt` contains only essential deps
- [ ] Dockerfile.minimal builds successfully
- [ ] Container starts and responds to health check
- [ ] Basic search works in container
- [ ] Image size < 500MB

---

## E. Integration Test Specification

### E.1 Phase 1 Foundation Tests

```python
# tests/integration/test_phase1_foundation.py

class TestPhase1Foundation:
    """Integration tests for Phase 1 Foundation work."""

    def test_sqlite_fresh_database_has_all_tables(self, tmp_path):
        """Verify fresh database creates all required tables."""
        db_path = tmp_path / "test.db"
        store = SQLiteStore(str(db_path))

        health = store.health_check()

        assert health["status"] == "healthy"
        assert health["tables"]["file_moves"] == True
        assert health["tables"]["files"] == True
        assert health["tables"]["symbols"] == True
        assert health["fts5"] == True
        assert health["wal"] == True

    def test_dispatcher_search_without_plugins(self, tmp_path):
        """Verify search works with no plugins loaded."""
        db_path = tmp_path / "test.db"
        store = SQLiteStore(str(db_path))

        dispatcher = EnhancedDispatcher(
            sqlite_store=store,
            use_plugin_factory=False,
            lazy_load=False
        )

        # Should not raise, should return empty
        results = list(dispatcher.search("test query"))
        assert isinstance(results, list)

    def test_dispatcher_timeout_handling(self, tmp_path, monkeypatch):
        """Verify plugin loading respects timeout."""
        # Mock slow plugin loading
        def slow_load(*args, **kwargs):
            time.sleep(10)
            return {}

        monkeypatch.setattr(PluginFactory, "create_all_plugins", slow_load)

        db_path = tmp_path / "test.db"
        store = SQLiteStore(str(db_path))

        start = time.time()
        dispatcher = EnhancedDispatcher(
            sqlite_store=store,
            lazy_load=False
        )
        elapsed = time.time() - start

        # Should timeout after ~5 seconds, not 10
        assert elapsed < 7
        assert len(dispatcher._plugins) == 0

    def test_bm25_fallback_multiple_schemas(self, tmp_path):
        """Verify BM25 works with different table schemas."""
        # Test with bm25_content table
        db1 = tmp_path / "bm25.db"
        conn = sqlite3.connect(str(db1))
        conn.execute("""
            CREATE VIRTUAL TABLE bm25_content USING fts5(
                filepath, content, language
            )
        """)
        conn.execute(
            "INSERT INTO bm25_content VALUES (?, ?, ?)",
            ("/test.py", "def hello(): pass", "python")
        )
        conn.commit()
        conn.close()

        store = SQLiteStore(str(db1))
        results = store.search_bm25("hello")

        assert len(results) >= 1
        assert "filepath" in results[0] or "file_path" in results[0]
```

---

## F. Risk Analysis

### F.1 Identified Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Migration 002 not applied | Schema mismatch | Add fallback table creation in init |
| Plugin loading hangs on Windows | Startup blocks | Add threading.Timer timeout |
| FTS5 not available | Search broken | Check on startup, fallback to LIKE |
| Circular imports | Import errors | Lazy imports, audit init |
| Docker build fails | No container | Test in CI, pin versions |

### F.2 Fallback Strategies

1. **Schema Issues**: Auto-migrate on first run
2. **Plugin Timeout**: Use BM25-only mode
3. **FTS5 Missing**: Use LIKE queries (slower but works)
4. **Docker Fails**: Provide local install instructions

---

## G. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Installation Success | > 90% | CI pass rate |
| Fresh DB Setup | < 2s | Integration test |
| Search with BM25 Fallback | < 200ms | Benchmark |
| Docker Build Time | < 5min | CI timing |
| Docker Image Size | < 500MB | `docker images` |

---

## H. Swim Lane Execution Order

```
Timeline:
├── Swim Lane 1 (Core Indexing)  ─────────────────►
│   └── No dependencies, starts immediately
│
├── Swim Lane 3 (Operations)     ─────────────────►
│   └── No dependencies, runs in parallel
│
└── Swim Lane 2 (Dispatcher)     ──────[IF-1]────►
    └── Waits for SQLiteStore interface freeze
```

**Parallel Execution**: Lanes 1 and 3 can run simultaneously.
**Sequential Dependency**: Lane 2 must wait for Lane 1's interface freeze (IF-1-SQLITE).

---

## I. Interface Freeze Checklist

Before Swim Lane 2 can begin:

- [ ] `SQLiteStore.__init__` signature finalized
- [ ] `SQLiteStore.health_check` signature finalized
- [ ] `SQLiteStore.search_bm25` signature finalized
- [ ] All SQLiteStore return types documented
- [ ] Unit tests for SQLiteStore pass

---

## Appendix: File Diffs Preview

### A.1 mcp_server/__init__.py (Expected)

```python
"""MCP Server - Local-first code indexer for LLMs."""

__version__ = "0.1.0"

# Public API exports
__all__ = [
    "__version__",
    "SQLiteStore",
    "EnhancedDispatcher",
    "PluginFactory",
]

# Lazy imports to avoid circular dependencies
def __getattr__(name):
    if name == "SQLiteStore":
        from .storage.sqlite_store import SQLiteStore
        return SQLiteStore
    if name == "EnhancedDispatcher":
        from .dispatcher.dispatcher_enhanced import EnhancedDispatcher
        return EnhancedDispatcher
    if name == "PluginFactory":
        from .plugins.plugin_factory import PluginFactory
        return PluginFactory
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
```

### A.2 requirements-core.txt (New)

```
# Core dependencies for minimal MCP Server
mcp>=1.0.0
fastapi>=0.100.0
uvicorn>=0.23.0
tree-sitter>=0.20.0
tree-sitter-languages>=1.7.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
python-dotenv>=1.0.0
watchdog>=3.0.0
typer>=0.9.0
rich>=13.0.0
```
