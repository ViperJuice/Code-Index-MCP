# Code-Index-MCP Development Roadmap

> **Note for AI Agents**: This roadmap is designed for autonomous AI agents to understand project status and determine next implementation steps. Focus on completing high-priority items that unblock further progress. Work in parallel when possible.

## Project Overview
Code-Index-MCP is a local-first code indexing system providing fast symbol search and code navigation across multiple programming languages. The architecture includes language-specific plugins, persistence layer, and operational components.

## Current Implementation Status (~25% Complete)

### ✅ Completed Components
- Core architecture established (dual pattern: target + actual)
- FastAPI gateway with endpoints: `/symbol`, `/search`, `/status`, `/plugins`, `/reindex`
- Python plugin fully functional with Tree-sitter + Jedi
- Dispatcher routing with caching and auto-initialization
- File watcher integrated with automatic re-indexing
- SQLite persistence layer with FTS5 search
- Error handling and logging framework
- Basic documentation structure

### ⚠️ Partially Complete
- 5 language plugins have implementation guides but no code
- Basic persistence exists but needs optimization
- Documentation exists but incomplete

### ❌ Not Implemented
- Automated testing framework
- Performance benchmarks
- Operational components (cache, metrics, security)
- Task queue system
- Advanced search features
- Cloud sync capabilities
- Additional language support beyond planned 6

## Architecture Components

### Phase 1: Foundation (✅ COMPLETE)
- File watcher integration
- Core API endpoints
- Basic persistence
- Error handling framework

### Phase 2: Core Components
- **Language Plugins** (5 remaining: JavaScript, C, C++, HTML/CSS, Dart)
- **Testing Framework** (pytest infrastructure)
- **Plugin System Enhancements** (dynamic loading, configuration)

### Phase 3: Persistence & Storage
- Query optimization
- Index management
- Performance optimizations for scale
- Backup/restore functionality

### Phase 4: Operational Components
- Cache layer (Redis/in-memory)
- Metrics collection (Prometheus/OpenTelemetry)
- Security implementation (JWT, validation)
- Task queue system (Celery + Redis)

### Phase 5: Advanced Features
- Semantic search integration with embeddings
- Hybrid search (lexical + semantic)
- Cloud sync implementation
- Embedding service

### Phase 6: Production Readiness
- Performance optimization
- Security hardening
- API documentation
- Deployment guides

### Phase 7: Ecosystem Extensions
- Additional languages (Rust, Go, Ruby, Swift)
- IDE integrations
- Web UI dashboard

## Success Metrics

### Performance Requirements
- Symbol lookup: < 100ms (p95)
- Semantic search: < 500ms (p95)
- Indexing speed: 10K files/minute
- Memory usage: < 2GB for 100K files

### Quality Requirements
- All language plugins functional
- 90%+ test coverage
- Zero critical security issues
- Complete API documentation

## Risk Factors

1. **Stub Plugins**: 5 of 6 language plugins unimplemented (guides exist)
2. **No Tests**: Missing automated testing framework
3. **No Operational Components**: Missing cache, metrics, security systems
4. **Performance Unknown**: No benchmarks against requirements
5. **Documentation Gaps**: Missing API docs, deployment guides

## Next Steps - Priority Implementation Tasks

### Critical Path Items (Blocking Other Work)

1. **Testing Framework** - Blocks all other development
   - Create `tests/conftest.py` with pytest fixtures
   - Set up test structure for components
   - Add GitHub Actions CI/CD pipeline
   - Required before implementing new plugins

2. **JavaScript Plugin** - Most requested language
   - Implement `mcp_server/plugins/js_plugin/plugin.py`
   - Follow guide in `mcp_server/plugins/js_plugin/AGENTS.md`
   - Support ES6+, JSX, TypeScript detection
   - Add tests immediately after implementation

### Parallel Execution Opportunities

The following can be implemented simultaneously without conflicts:

**Group A - Language Plugins** (Independent implementations):
- **C Plugin**: `mcp_server/plugins/c_plugin/plugin.py`
- **C++ Plugin**: `mcp_server/plugins/cpp_plugin/plugin.py`
- **HTML/CSS Plugin**: `mcp_server/plugins/html_css_plugin/plugin.py`
- **Dart Plugin**: `mcp_server/plugins/dart_plugin/plugin.py`

**Group B - Infrastructure** (Non-conflicting systems):
- **Performance Benchmarks**: Create benchmark suite for existing functionality
- **API Documentation**: Generate from existing endpoints
- **Query Optimization**: Enhance SQLite queries in `sqlite_store.py`

**Group C - Operational Components** (After Group A completes):
- **Cache Layer**: Add Redis/in-memory caching to dispatcher
- **Metrics Collection**: Implement Prometheus metrics
- **Dynamic Plugin Loading**: Scan and load plugins at startup

### Implementation Priority Order

1. **Immediate**: Testing Framework (blocks everything)
2. **High Priority**: JavaScript Plugin + Group A plugins
3. **Medium Priority**: Group B infrastructure tasks
4. **Lower Priority**: Group C operational components

### Success Validation

For each implementation:
1. Code follows existing patterns (see Python plugin)
2. Includes comprehensive error handling
3. Has >80% test coverage
4. Updates gateway.py startup handler if needed
5. Documentation updated

### Dependencies to Note

- All plugins depend on Tree-sitter grammars (install first)
- Operational components may require new dependencies (Redis, Prometheus)
- Performance testing requires representative test data

*Last Updated: 2025-01-30*
*Status Key: ✅ Complete | ⚠️ Partial | ❌ Not Started*