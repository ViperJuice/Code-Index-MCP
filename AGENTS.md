# Code-Index-MCP Agent Configuration

> **Status**: ✅ 100% COMPLETE - Production Ready
> **Last Updated**: 2025-06-03
> **Project Phase**: All 4 phases complete, Phase 5 planned for Q2 2025

## PROJECT_OVERVIEW

Code-Index-MCP is a **production-ready** Model Context Protocol (MCP) server providing AI assistants with deep code understanding through advanced indexing and search capabilities. The project has successfully completed all 4 implementation phases with 100% MCP compliance.

### Implementation Status
- **Phase 1-4**: ✅ Complete (Foundation, Features, Integration, Advanced)
- **Phase 5**: 🔜 Planned Q2-Q3 2025 (Additional languages, GPU acceleration)
- **Test Coverage**: 100% for core features
- **Performance**: Exceeds all targets by 25-60%
- **Production**: Ready for enterprise deployment

## ESSENTIAL_COMMANDS

```bash
# Development Setup
python -m venv venv                    # Create virtual environment
source venv/bin/activate               # Activate (Linux/Mac)
pip install -e .                       # Install in development mode

# Building & Testing
make install                           # Install dependencies
make test                             # Run test suite
make test-coverage                    # Run with coverage report
make lint                             # Run linters
make format                           # Format code

# Running the Server
./mcp                                 # Start MCP server (recommended)
python -m mcp_server                  # Alternative start method
python -m mcp_server --transport stdio # Stdio transport
python -m mcp_server --transport websocket --port 8765  # WebSocket

# Docker Operations
docker-compose up -d                  # Start development environment
docker-compose -f docker-compose.production.yml up -d  # Production
docker-compose logs -f mcp-server     # View logs

# Index Management
python -m mcp_server index build      # Build index
python -m mcp_server index verify     # Verify index integrity
./scripts/mcp-index --force-rebuild   # Force rebuild index
```

## CODE_STYLE_PREFERENCES

### Python Conventions
- **Functions**: snake_case (e.g., `process_file_index()`)
- **Classes**: PascalCase (e.g., `FileWatcher`, `PluginManager`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `MAX_FILE_SIZE`)
- **Private**: Leading underscore (e.g., `_internal_method()`)
- **Type Hints**: Always use for public APIs
- **Docstrings**: Google style for all public functions/classes

### Testing Standards
- **Coverage**: Minimum 80% required
- **Structure**: `tests/` mirrors `mcp_server/` structure
- **Fixtures**: Use pytest fixtures for setup
- **Mocking**: Mock external dependencies
- **Integration**: Separate integration tests in `tests/integration/`

## ARCHITECTURAL_PATTERNS

### Core Patterns
1. **Plugin Architecture**: All language support via plugin system
   - Base class: `PluginBase` in `mcp_server/plugin_base.py`
   - Interface: Standardized methods for parsing and indexing
   - Discovery: Automatic plugin loading from `plugins/` directory

2. **MCP Protocol Implementation**
   - Server: Main implementation in `mcp_server/stdio_server.py`
   - Transport: Stdio and WebSocket support
   - Sessions: Managed via `SessionManager`
   - Tools/Resources: Registry pattern for extensibility

3. **Indexing Pipeline**
   - Tree-sitter: Primary parsing for all languages
   - Fuzzy Search: Powered by SQLite FTS5
   - Semantic Search: Optional vector embeddings
   - Caching: Multi-level cache with Redis support

4. **Error Handling**
   - Result Pattern: `Result[T, Error]` for all operations
   - Custom Exceptions: Hierarchical error types
   - Context: Always include file path and operation
   - Recovery: Graceful degradation on failures

## DEVELOPMENT_ENVIRONMENT

### Requirements
- **Python**: 3.8+ (3.10+ recommended)
- **OS**: Linux, macOS, Windows (WSL recommended)
- **Memory**: 4GB minimum, 8GB recommended
- **Storage**: 20GB for large codebases

### Setup Steps
1. Clone repository
2. Create virtual environment
3. Install dependencies: `pip install -r requirements.txt`
4. Install dev dependencies: `pip install -r requirements-dev.txt`
5. Install pre-commit hooks: `pre-commit install`
6. Run tests: `pytest`

### IDE Configuration
- **VS Code**: Settings in `.vscode/`
- **PyCharm**: Use provided `.idea/` configs
- **Formatting**: Black + isort configured
- **Linting**: Ruff as primary linter

## TEAM_SHARED_PRACTICES

### Development Workflow
1. **Branch Strategy**: Feature branches from `main`
2. **Commits**: Conventional commits (feat:, fix:, docs:)
3. **PR Process**: Requires tests, lint pass, review
4. **Documentation**: Update AGENTS.md for new patterns

### Performance Targets
- **Symbol Lookup**: <100ms (p95)
- **Code Search**: <500ms (p95)
- **File Indexing**: >10K files/minute
- **Memory**: <2GB for 100K files

### Security Practices
- **No Secrets**: Never commit API keys or credentials
- **Path Validation**: Always validate file paths
- **Input Sanitization**: Sanitize all user inputs
- **Rate Limiting**: Implement for all endpoints

## RECENT_CHANGES

### Seamless Index Compatibility (2025-06-04)
- Implemented auto-reindexing fallback for incompatible artifacts
- Added smart git hooks for automatic artifact creation/updates
- Created GitHub Actions workflow with standardized embedding model
- Enhanced CLI with seamless compatibility resolution
- Features delivered:
  - ✅ Auto-reindex on compatibility failure (no manual intervention)
  - ✅ Smart git hooks detect embedding model and manage artifacts
  - ✅ GitHub Actions uses voyage-code-3 for team consistency
  - ✅ Comprehensive CLI options for all workflow scenarios

### Phase 2 Enhancement (2025-06-03)
- Embedding provider system refactored to support 7 providers
- Added Google, HuggingFace, Local, and Mock providers
- Implemented auto-dimension detection from HuggingFace Hub
- Enhanced error handling with helpful debug output
- Maintained Voyage AI as default, NV-Embed-v2 as HF default

## DEVELOPMENT_PRIORITIES

### Immediate (This Week)
1. ✅ Enhanced index metadata with embedding model compatibility validation
2. ✅ Updated documentation for index sharing with v2.0 features
3. ✅ Comprehensive CLI commands for import/export with validation
4. Create plugin development guide consolidating all language patterns

### Short Term (This Month)
1. Optimize vector search performance
2. Improve distributed processing
3. Enhance cache warming strategies
4. Add more integration tests

### Long Term (Q2-Q3 2025)
1. **Phase 5 Languages**: Rust, Go, Java/Kotlin, Ruby, PHP
2. **GPU Acceleration**: For semantic search
3. **Advanced Caching**: Predictive cache warming
4. **Distributed Mode**: Multi-node deployment

## AGENT_PREFERENCES

### Code Generation
- Prefer composition over inheritance
- Use type hints for all public APIs
- Include comprehensive docstrings
- Add usage examples in comments

### Testing Strategy
- Unit tests for business logic
- Integration tests for workflows
- Mock external dependencies
- Use fixtures for complex setup

### Documentation Style
- Code examples over theory
- Include common pitfalls
- Reference related files
- Keep it concise and practical

## QUICK_REFERENCE

### Key Files
- `mcp_server/stdio_server.py` - Main MCP server with all features
- `mcp_server/plugin_base.py` - Plugin interface
- `mcp_server/dispatcher/dispatcher.py` - Request routing
- `mcp_server/tools/handlers/` - Tool implementations

### Key Directories
- `plugins/` - Language plugins
- `tests/` - Test suite
- `docs/` - Documentation
- `scripts/` - Utility scripts
- `k8s/` - Kubernetes configs

### Common Tasks
- Add language: Create plugin in `plugins/<language>_plugin/`
- Add tool: Implement in `tools/handlers/`, register in `tools/registry.py`
- Add test: Mirror structure in `tests/`
- Update docs: Edit relevant `.md` files

---

*For human-readable documentation, see [README.md](README.md). For architecture details, see [architecture/AGENTS.md](architecture/AGENTS.md).*