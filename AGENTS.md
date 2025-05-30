# MCP Server Agent Configuration

This file defines the capabilities and constraints for AI agents working with this codebase.

## Current State

**PROJECT STATUS**: ~65% Complete - Core functionality implemented with comprehensive testing framework

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

### What's NOT Implemented (Stubs/Placeholders)
- ❌ C++, HTML/CSS, and Dart plugins (stubs with guides)
- ❌ Advanced metrics collection (Prometheus)
- ❌ Security layer (JWT authentication)
- ❌ Task queue system (Celery + Redis)
- ❌ Semantic search features
- ❌ Cloud sync capabilities
- ❌ Dynamic plugin loading (hardcoded in gateway)

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

1. **Performance Benchmarks** - Required to validate against requirements
2. **Dynamic Plugin Loading** - Currently hardcoded in gateway
3. **C++ Plugin** - Implementation guide exists in AGENTS.md
4. **HTML/CSS Plugin** - Implementation guide exists in AGENTS.md
5. **Dart Plugin** - Implementation guide exists in AGENTS.md

## Architecture Context

The codebase follows C4 architecture model with comprehensive diagrams:
- **Structurizr DSL files**: Define system context, containers, and components
- **PlantUML files**: Detailed component designs in architecture/level4/
- **Architecture vs Implementation**: ~20% of planned architecture is implemented
- **Pragmatic approach**: Core functionality works but lacks many architectural components

Key architectural gaps:
- No authentication/security layer
- Missing plugin registry (hardcoded imports)
- No graph store (Memgraph) 
- No cache layer (Redis)
- Missing metrics/monitoring components

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