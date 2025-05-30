# Code-Index-MCP Development Roadmap

## Overview
This roadmap outlines the development phases for completing the Code-Index-MCP local-first code indexing system. The phases align with the comprehensive architecture defined in the architecture files, including performance requirements, security model, and data model specifications.

## Current Status Summary (~25% Complete)
- ✅ Core architecture established (dual architecture pattern: target + actual)
- ✅ FastAPI gateway with all endpoints working (/symbol, /search, /status, /plugins, /reindex)
- ✅ Python plugin fully functional with Tree-sitter + Jedi
- ✅ Dispatcher routing with caching and auto-initialization
- ✅ File watcher integrated and triggers automatic re-indexing
- ✅ SQLite persistence layer with FTS5 implemented
- ✅ Error handling and logging framework complete
- ⚠️ 5 language plugins have comprehensive implementation guides (not yet implemented)
- ❌ No operational components (cache, metrics, security beyond basic)
- ❌ No automated tests beyond manual test scripts

## Architecture Alignment
This roadmap follows the dual architecture pattern discovered during documentation cleanup:
- **Target Architecture**: Full enterprise system (level1-3 + level4 PlantUML)
- **Actual Architecture**: ~20% implemented (*_actual.dsl and *_actual.puml files)
- **Level 1**: System context with performance SLAs
- **Level 2**: 14 containers (only 3-4 actually implemented)
- **Level 3**: Detailed components (most are stubs or missing)
- **Supporting Docs**: Performance, Security, Data Model (specs only, not implemented)

---

## Phase 1: Foundation Stabilization ✅ COMPLETE

### 1.1 Complete File Watcher Integration ✅ COMPLETE
**Status:** Fully Implemented
- [x] Watchdog integration exists
- [x] File change detection works
- [x] Connected to indexing trigger
- [x] Caching prevents re-indexing unchanged files
- [x] Handles file creation, modification, and moves

### 1.2 Core Infrastructure Enhancement ✅ COMPLETE
**Status:** Fully Implemented
- [x] Gateway API endpoints (`/symbol`, `/search`)
- [x] Dispatcher routing logic with caching
- [x] Plugin base interface (IPlugin abstract base)
- [x] Dispatcher auto-initialization on startup
- [x] Error handling and logging framework
- [x] Basic configuration (more needed for production)
- [x] Added `/status`, `/plugins`, and `/reindex` endpoints
- [x] Request validation with Pydantic and error handling

### 1.3 Testing Framework ❌ NOT STARTED
**Status:** Not Started
- [ ] Set up pytest infrastructure
- [ ] Add unit tests for existing components
- [ ] Create integration test suite
- [ ] Add CI/CD pipeline

---

## Phase 2: Core Components Completion

### 2.1 Complete Stub Language Plugins ⚠️ CRITICAL
**Status:** Only Python plugin works, comprehensive guides created for others
- [x] Python plugin with Tree-sitter + Jedi
- [x] C plugin - comprehensive implementation guide created
- [x] C++ plugin - comprehensive implementation guide created
- [x] JavaScript plugin - comprehensive implementation guide created
- [x] Dart plugin - comprehensive implementation guide created
- [x] HTML/CSS plugin - comprehensive implementation guide created
- [ ] Implement C plugin using guide
- [ ] Implement C++ plugin using guide
- [ ] Implement JavaScript plugin using guide
- [ ] Implement Dart plugin using guide
- [ ] Implement HTML/CSS plugin using guide

### 2.2 Plugin System Enhancement ❌ NOT STARTED
**Status:** Basic system only
- [x] Direct plugin import and registration
- [ ] Dynamic plugin loading
- [ ] Plugin configuration system
- [ ] Plugin isolation (planned: gRPC, current: direct imports)
- [ ] Plugin lifecycle management
- [ ] Plugin discovery mechanism

### 2.3 Persistence Layer Implementation ✅ COMPLETE
**Status:** SQLite persistence with FTS5 fully implemented
- [x] Implemented SQLite with FTS5 (following schema in data_model.md)
- [x] FuzzyIndexer integrated with SQLite backend
- [x] Database schema initialization and migrations
- [x] Trigram-based fuzzy search implemented
- [ ] Add backup/restore functionality (future enhancement)

---

## Phase 3: Persistence and Storage

### 3.1 Local Index Store ✅ BASIC IMPLEMENTATION
**Status:** Basic SQLite persistence implemented
- [x] Storage schema designed (see data_model.md)
- [x] SQLite-based persistence with FTS5 implemented
- [x] Basic schema versioning implemented
- [x] Initial migration system in place
- [ ] Advanced query optimization needed
- [ ] Performance optimizations (partitioning, compression) for scale

### 3.2 Index Management ❌ NOT STARTED
**Status:** Not Started
- [ ] Index creation and updates
- [ ] Index cleanup and maintenance
- [ ] Memory-mapped file support
- [ ] Compression for large indices

---

## Phase 4: Operational Components

### 4.1 Performance Infrastructure ❌ NOT STARTED
**Status:** Not Started (Required by level2 architecture)
- [ ] Implement cache layer (Redis/in-memory)
- [ ] Add metrics collector (Prometheus/OpenTelemetry)
- [ ] Create query optimizer component
- [ ] Implement performance benchmarks
- [ ] Add monitoring dashboards

### 4.2 Security Implementation ❌ NOT STARTED
**Status:** Not Started (Defined in security_model.md)
- [ ] Implement security manager component
- [ ] Add authentication middleware (JWT)
- [ ] Create request validator (Pydantic)
- [ ] Implement secret detection/redaction
- [ ] Add audit logging

### 4.3 Task Queue System ❌ NOT STARTED
**Status:** Not Started (Required by level2 architecture)
- [ ] Set up Celery + Redis
- [ ] Implement async indexing tasks
- [ ] Add batch processing support
- [ ] Create task monitoring
- [ ] Implement retry logic

## Phase 5: Advanced Features

### 5.1 Semantic Search Integration ✅ FOUNDATION EXISTS
**Status:** Basic Implementation
- [x] Semantic indexer with Voyage AI
- [ ] Integrate with main search pipeline
- [ ] Add embedding caching
- [ ] Implement hybrid search (lexical + semantic)
- [ ] Add relevance tuning

### 5.2 Cloud Sync Implementation ❌ NOT STARTED
**Status:** Stub Only
- [ ] Design sync protocol
- [ ] Implement shard management
- [ ] Add conflict resolution
- [ ] Create authentication system
- [ ] Add bandwidth optimization

### 5.3 Embedding Service ❌ NOT STARTED
**Status:** Not Started
- [ ] Integrate Voyage AI embeddings
- [ ] Add local embedding fallback
- [ ] Implement batch processing
- [ ] Add model selection logic

---

## Phase 6: Production Readiness

### 6.1 Performance Optimization ❌ NOT STARTED
**Status:** Not Started
- [ ] Add caching layers
- [ ] Implement parallel processing
- [ ] Optimize memory usage
- [ ] Add performance benchmarks

### 6.2 Security and Reliability ❌ NOT STARTED
**Status:** Not Started
- [ ] Add input validation
- [ ] Implement rate limiting
- [ ] Add security scanning
- [ ] Create backup/restore functionality

### 6.3 Documentation and Tooling ⚠️ PARTIAL
**Status:** Basic Documentation Exists
- [x] Architecture documentation
- [x] Basic README
- [ ] API documentation
- [ ] Plugin development guide
- [ ] Deployment guide
- [ ] Troubleshooting guide

---

## Phase 7: Ecosystem and Extensions

### 7.1 Additional Language Support ❌ FUTURE
**Status:** Not Started
- [ ] Rust plugin
- [ ] Go plugin
- [ ] Ruby plugin
- [ ] Swift plugin

### 7.2 Tool Integrations ❌ FUTURE
**Status:** Not Started
- [ ] VS Code extension
- [ ] IntelliJ plugin
- [ ] Command-line tools
- [ ] Web UI dashboard

### 7.3 Advanced Analytics ❌ FUTURE
**Status:** Not Started
- [ ] Code quality metrics
- [ ] Dependency analysis
- [ ] Security vulnerability detection
- [ ] Performance profiling

---

## Next Steps - Phase 1 Completion Plan

### IMMEDIATE PRIORITIES (Parallel Execution Recommended)

#### Task Group 1: File Watcher Completion
**Files to modify:**
- `mcp_server/watcher.py`: 
  - Complete TODO at line 14
  - Add method `trigger_reindex(self, file_path)` 
  - Connect to dispatcher for incremental indexing
- `mcp_server/dispatcher.py`:
  - Add method `index_file(self, file_path)` for single file indexing
  - Add caching to avoid re-indexing unchanged files

**Implementation steps:**
```python
# In watcher.py on_any_event():
if event.src_path.endswith(('.py', '.js', '.c', '.cpp', '.dart', '.html', '.css')):
    self.trigger_reindex(event.src_path)

def trigger_reindex(self, file_path):
    # Get dispatcher instance (needs to be passed in __init__)
    self.dispatcher.index_file(file_path)
```

#### Task Group 2: Dispatcher Auto-Initialization  
**Files to modify:**
- `mcp_server/gateway.py`:
  - Add startup event handler
  - Initialize dispatcher with all plugins
  - Remove need for manual initialization

**Implementation:**
```python
@app.on_event("startup")
async def startup_event():
    from mcp_server.dispatcher import Dispatcher
    from mcp_server.plugins.python_plugin.plugin import PythonPlugin
    # Import other plugins when implemented
    
    app.state.dispatcher = Dispatcher()
    app.state.dispatcher.registerPlugin(PythonPlugin())
    # Register other plugins
```

#### Task Group 3: Basic Persistence
**New files to create:**
- `mcp_server/storage/__init__.py`
- `mcp_server/storage/sqlite_store.py`
- `mcp_server/storage/migrations/001_initial_schema.sql`

**Files to modify:**
- `mcp_server/utils/fuzzy_indexer.py`:
  - Add SQLite backend option
  - Implement `persist()` and `load()` methods
  - Use FTS5 for search

**Implementation outline:**
```python
# sqlite_store.py
class SQLiteStore:
    def __init__(self, db_path="code_index.db"):
        self.conn = sqlite3.connect(db_path)
        self._init_schema()
    
    def _init_schema(self):
        # Create tables from data_model.md
        # files, symbols, references tables
        # FTS5 virtual table for search
```

#### Task Group 4: Missing Endpoints
**Files to modify:**
- `mcp_server/gateway.py`:
  - Add `/status` endpoint
  - Add `/plugins` endpoint
  - Add `/reindex` endpoint for manual triggers

**Implementation:**
```python
@app.get("/status")
def get_status():
    return {
        "status": "operational",
        "plugins": len(dispatcher.plugins) if dispatcher else 0,
        "indexed_files": dispatcher.get_stats() if dispatcher else {}
    }

@app.get("/plugins")
def get_plugins():
    if not dispatcher:
        return {"error": "Dispatcher not initialized"}
    return [
        {"name": p.__class__.__name__, "language": p.lang}
        for p in dispatcher.plugins
    ]
```

#### Task Group 5: Error Handling & Logging
**New files:**
- `mcp_server/core/__init__.py`
- `mcp_server/core/logging.py`
- `mcp_server/core/errors.py`

**Implementation:**
```python
# logging.py
import logging
import sys

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('mcp_server.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
```

### TESTING REQUIREMENTS
**New test files needed:**
- `tests/test_watcher.py` - Test file monitoring
- `tests/test_gateway.py` - Test API endpoints
- `tests/test_sqlite_store.py` - Test persistence
- `tests/test_dispatcher.py` - Test routing logic

### SUCCESS CRITERIA
- [ ] File changes trigger automatic re-indexing
- [ ] Server starts with dispatcher pre-initialized
- [ ] Fuzzy index persists across restarts
- [ ] All endpoints return proper responses
- [ ] Errors are logged to file and console
- [ ] Basic test suite passes

### PARALLEL EXECUTION STRATEGY
Use multiple agents/developers to work on task groups simultaneously:
- Agent 1: File Watcher (Task Group 1)
- Agent 2: Gateway improvements (Task Groups 2 & 4)
- Agent 3: Persistence layer (Task Group 3)
- Agent 4: Core infrastructure (Task Group 5)
- Agent 5: Testing framework and tests

### ESTIMATED TIMELINE
- All task groups can be completed in parallel
- Estimated completion: 2-3 days with parallel execution
- Sequential execution would take 1-2 weeks

## Success Metrics

### Performance (per performance_requirements.md)
- [ ] < 100ms response time for symbol lookup (p95)
- [ ] < 500ms for semantic search (p95)
- [ ] 10K files/minute indexing speed
- [ ] < 2GB memory for 100K files

### Quality
- [ ] All language plugins passing tests
- [ ] 90%+ test coverage
- [ ] Zero critical security issues
- [ ] Complete API documentation

### Operational
- [ ] 99.9% availability
- [ ] < 0.1% error rate
- [ ] Monitoring dashboard operational
- [ ] Security audit passed

## Risk Factors (Updated)

1. **Implementation Gap**: Only ~20% implemented vs architecture design
2. **No Persistence**: All indexing lost on restart (memory-only)
3. **Manual Initialization**: Dispatcher must be manually initialized
4. **Stub Plugins**: 5 of 6 language plugins are empty implementations
5. **File Watcher Incomplete**: Exists but doesn't trigger indexing
6. **No Tests**: Only manual test scripts, no automated testing
7. **No Error Handling**: Errors silently ignored in many places
8. **Documentation Mismatch**: Some docs described features that don't exist (now cleaned up)

## Timeline Estimate (Revised based on actual state)

- Phase 1: 1 week - Complete foundation (file watcher, persistence, auto-init)
- Phase 2: 4-6 weeks - Implement all language plugins + enhance system
- Phase 3: 2-3 weeks - Full persistence layer with migrations
- Phase 4: 4-5 weeks - Operational components (cache, metrics, security)
- Phase 5: 3-4 weeks - Advanced features (semantic search, cloud sync)
- Phase 6: 3-4 weeks - Production readiness (testing, docs, optimization)
- Phase 7: Ongoing - Ecosystem and extensions

**Total estimated time to production-ready: 17-23 weeks**
**Time to usable MVP (Phase 1-2): 5-7 weeks**

## Development Process

### Sprint Cadence
- 2-week sprints
- Sprint planning on Mondays
- Daily standups
- Sprint review/retro on Fridays

### Definition of Done
- [ ] Code complete and reviewed
- [ ] Unit tests written and passing
- [ ] Integration tests passing
- [ ] Documentation updated
- [ ] Security review completed
- [ ] Performance benchmarks met

---

*Last Updated: 2025-01-29 - Post Documentation Cleanup*
*Current Phase: Phase 1 - Foundation Stabilization*
*Implementation Status: ~25% Complete*
*Next Review: After Phase 1 Completion*
*Status Key: ✅ Complete | ⚠️ Partial/In Progress | ❌ Not Started | 🚧 Active Development*

## Appendix: Architecture Files
- `/architecture/level1_context.dsl` - System context with SLAs
- `/architecture/level2_containers.dsl` - 14 containers including operational
- `/architecture/level3_mcp_components.dsl` - Detailed components
- `/architecture/performance_requirements.md` - Performance targets
- `/architecture/security_model.md` - Security implementation
- `/architecture/data_model.md` - Database schema