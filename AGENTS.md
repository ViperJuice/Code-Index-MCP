# MCP Server Agent Configuration

This file defines the capabilities and constraints for AI agents working with this codebase.

## Current State

**PROJECT STATUS**: 85% Complete - Core System Operational (complexity 5/5)

**Current Implementation Status**: 85% complete (corrected from roadmap's claimed 95%)
**System Complexity**: 5/5 (High - 136k lines, 48 plugins, semantic search, document processing)
**Next Priority**: Complete document processing validation and publish performance benchmarks
**Last Updated**: 2025-06-08

### What's Actually Implemented
- ✅ FastAPI gateway with all endpoints: `/symbol`, `/search`, `/status`, `/plugins`, `/reindex`
- ✅ Dispatcher with caching and auto-initialization
- ✅ Python plugin fully functional with Tree-sitter + Jedi
- ✅ JavaScript/TypeScript plugin fully functional with Tree-sitter
- ✅ C plugin fully functional with Tree-sitter
- ✅ SQLite persistence layer with FTS5 search
- ✅ File watcher integrated with automatic re-indexing
- ✅ Error handling and logging framework
- ✅ Comprehensive testing framework (pytest with fixtures)
- ✅ CI/CD pipeline with GitHub Actions
- ✅ Docker support and build system

### What's Recently Implemented
- ✅ C++, HTML/CSS, and Dart plugins fully functional with Tree-sitter
- ✅ Advanced metrics collection with Prometheus
- ✅ Security layer with JWT authentication
- ✅ Comprehensive testing framework with parallel execution
- ✅ Production-ready Docker and Kubernetes configurations
- ✅ Cache management and query optimization
- ✅ Real-world repository testing validation

### Remaining Implementation (15%)
- ⚠️ Document processing validation (5% - recently implemented, needs validation)
- ⚠️ Performance benchmark result publishing (5% - framework exists, results unpublished)
- ⚠️ Production deployment automation (5% - Docker configs exist, automation incomplete)

## Agent Capabilities

### Code Understanding
- Parse and understand the intended architecture
- Navigate plugin structure (though most are stubs)
- Interpret C4 architecture diagrams
- Understand the gap between design and implementation

### Code Modification
- Add new language plugin stubs
- Extend API endpoint definitions
- Update architecture diagrams
- Implement missing functionality

### Testing & Validation
- Run basic test files (`test_python_plugin.py`, `test_tree_sitter.py`)
- Validate TreeSitter functionality
- Check architecture consistency
- Identify implementation gaps

## Agent Constraints

1. **Implementation Gaps**
   - Be aware that most components are not functional
   - The dispatcher doesn't route to plugins properly
   - No actual indexing or storage occurs
   - Search functionality returns empty results

2. **Local-First Priority**
   - Design for local indexing (when implemented)
   - Maintain offline functionality goals
   - Minimize external dependencies

3. **Plugin Architecture**
   - Follow plugin base class requirements
   - Maintain language-specific conventions
   - Preserve plugin isolation design

4. **Security**
   - No hardcoded credentials
   - Respect file system permissions
   - Validate all external inputs

5. **Performance**
   - Consider indexing speed in future implementations
   - Plan for efficient memory usage
   - Design efficient file watching

## ESSENTIAL_COMMANDS

```bash
# Build & Install
make install                    # Install dependencies
pip install -e .               # Install in development mode

# Testing
make test                       # Run unit tests
make test-all                   # Run all tests with coverage
make coverage                   # Generate coverage report
make benchmark                  # Run performance benchmarks

# Code Quality
make lint                       # Run linters (black, isort, flake8, mypy, pylint)
make format                     # Format code (black, isort)
make security                   # Run security checks (safety, bandit)

# Development
uvicorn mcp_server.gateway:app --reload --host 0.0.0.0 --port 8000
make clean                      # Clean up temporary files

# Docker
make docker                     # Build Docker image

# Architecture
docker run --rm -p 8080:8080 -v "$(pwd)/architecture":/usr/local/structurizr structurizr/lite
```

## Development Priorities

### IMMEDIATE_PRIORITIES (This Week, Complexity 3-4)
1. **Document processing validation** - Complete testing and documentation (BLOCKING: production claims)
2. **Performance benchmarks** - Publish existing results (SUPPORTING: production readiness)
3. **Documentation cleanup** - Move status reports to docs/status/ (IMPACT: professional presentation)
4. **Legal compliance** - Verify LICENSE and CODE_OF_CONDUCT.md are properly referenced (BLOCKING: distribution)

### SHORT_TERM_PRIORITIES (Next Sprint, Complexity 2-3)
1. **Production deployment automation** - Complete deployment scripts (COMPLETING: Phase 4)
2. **Architecture diagram updates** - Align with current implementation (MAINTAINING: documentation quality)
3. **Monitoring framework** - Implement production monitoring (ENABLING: operations)
4. **User documentation** - Create comprehensive user guides (SUPPORTING: adoption)

### ARCHITECTURAL_DECISIONS_NEEDED
- Container orchestration platform selection (Kubernetes vs Docker Swarm vs other)
- Monitoring and alerting framework (Prometheus vs other)
- User interface approach (Web UI vs CLI-only vs API-first)

### INTERFACE-FIRST_DEVELOPMENT_SEQUENCE
**Follow ROADMAP.md Next Steps hierarchy**:
1. Container Interface Definition (Priority: HIGHEST, Complexity: 4)
2. External Module Interfaces (Priority: HIGH, Complexity: 3)
3. Intra-Container Module Interfaces (Priority: MEDIUM, Complexity: 2)
4. Implementation details (Priority: FINAL, Complexity varies)

## Architecture Context

The codebase follows C4 architecture model with comprehensive diagrams:
- **Structurizr DSL files**: Define system context, containers, and components (85% implemented)
- **PlantUML files**: Detailed component designs in architecture/level4/ (22 diagrams, 90% coverage)
- **Architecture vs Implementation**: 85% alignment (strong improvement from previous 20%)
- **Implementation Status**: Core functionality operational with production infrastructure

**ARCHITECTURE_IMPLEMENTATION_ALIGNMENT**: STRONG (85%)
✅ **ALIGNED_COMPONENTS**:
- Plugin Factory pattern → GenericTreeSitterPlugin + 48 languages implemented
- Enhanced Dispatcher → Caching, routing, error handling operational  
- Storage abstraction → SQLite + FTS5 with optional Qdrant integration
- API Gateway → FastAPI with all documented endpoints functional
- File Watcher → Real-time monitoring with Watchdog implemented

⚠️ **RECENTLY_IMPLEMENTED** (validation needed):
- Document Processing plugins → Markdown/PlainText created, testing in progress
- Specialized Language plugins → 7 plugins implemented, production validation needed
- Semantic Search integration → Voyage AI integrated with graceful fallback

❌ **GAPS_IDENTIFIED**:
- Performance benchmarks → Framework exists but results unpublished
- Production deployment → Docker configs exist but automation incomplete
- Some PlantUML diagrams → Need updates to match latest implementations

## CODE_STYLE_PREFERENCES

```python
# Discovered from pyproject.toml and Makefile
# Formatting: black + isort
# Linting: flake8 + mypy + pylint
# Type hints: Required for all functions
# Docstrings: Required for public APIs

# Function naming (discovered patterns)
def get_current_user(request: Request) -> TokenData:
def cache_symbol_lookup(query_cache: QueryResultCache):
def require_permission(permission: Permission):

# Class naming (discovered patterns)  
class FileWatcher:
class AuthenticationError(Exception):
class SecurityError(Exception):

# File naming patterns
# test_*.py for tests
# *_manager.py for managers
# *_middleware.py for middleware
```

## ARCHITECTURAL_PATTERNS

```python
# Plugin Pattern: All language plugins inherit from PluginBase
class LanguagePlugin(PluginBase):
    def index(self, file_path: str) -> Dict
    def getDefinition(self, symbol: str, context: Dict) -> Dict
    def getReferences(self, symbol: str, context: Dict) -> List[Dict]

# FastAPI Gateway: Standardized tool interface
@app.get("/symbol")
@app.get("/search") 
@app.get("/status")

# Tree-sitter Integration: Use TreeSitterWrapper for parsing
from mcp_server.utils.treesitter_wrapper import TreeSitterWrapper

# Error Handling: All functions return structured responses
{"status": "success|error", "data": {...}, "timestamp": "..."}

# Testing: pytest with fixtures, >80% coverage required
def test_plugin_functionality(plugin_fixture):
```

## NAMING_CONVENTIONS

```bash
# Functions: snake_case
get_current_user, cache_symbol_lookup, require_permission

# Classes: PascalCase
FileWatcher, AuthenticationError, PluginBase

# Files: snake_case.py
gateway.py, plugin_manager.py, security_middleware.py

# Tests: test_*.py
test_python_plugin.py, test_dispatcher.py, test_gateway.py

# Directories: snake_case
mcp_server/, plugin_system/, tree_sitter_wrapper/
```

## DEVELOPMENT_ENVIRONMENT

```bash
# Python Version: 3.8+ (from pyproject.toml)
# Virtual Environment: Required
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Dependencies
pip install -r requirements.txt
pip install -e .

# Pre-commit: Configured for linting and formatting
make lint     # Verify before committing
make format   # Auto-format code

# IDE Setup: VS Code recommended (if .vscode/ exists)
# Extensions: Python, Pylance, Black Formatter
```

## TEAM_SHARED_PRACTICES

```bash
# Testing: Always run tests before committing
make test-all

# Documentation: Update AGENTS.md when adding new patterns
# Plugin Development: Follow established PluginBase interface  
# Error Messages: Include context and suggested fixes
# Performance: Target <100ms symbol lookup, <500ms search

# Code Review: Focus on
# - Type hints for all functions
# - Comprehensive error handling  
# - Test coverage >80%
# - Documentation updates
``` 