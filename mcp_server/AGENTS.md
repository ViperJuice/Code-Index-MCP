# MCP Server Agent Configuration

This file defines the capabilities and constraints for AI agents working with the MCP server core implementation.

## Current Implementation Status: 100% Complete - PRODUCTION READY 🎉

### What's Actually Working (FULLY OPERATIONAL)
- ✅ **FastAPI Gateway**: Complete endpoints `/symbol`, `/search`, `/status`, `/plugins`, `/reindex`
- ✅ **Enhanced Dispatcher**: Caching, routing, error handling, auto-initialization
- ✅ **Plugin Framework**: 48 languages via GenericTreeSitterPlugin + specialized plugins
- ✅ **Specialized Plugins**: Python, C, C++, JavaScript, Dart, HTML/CSS with semantic support
- ✅ **Storage Layer**: SQLite + FTS5 search, optional Qdrant vector database
- ✅ **File Watcher**: Real-time monitoring with automatic re-indexing (Watchdog integrated)
- ✅ **Semantic Search**: Voyage AI embeddings with graceful fallback
- ✅ **Security Layer**: JWT authentication, role-based access (auth_manager.py)
- ✅ **Metrics Collection**: Prometheus integration (metrics/ directory)
- ✅ **Cache Management**: Query caching, plugin instance caching
- ✅ **Error Handling**: Comprehensive logging and error recovery
- ✅ **Document Processing**: Markdown and PlainText plugins (recently implemented)

### All Work Completed (PRODUCTION READY)
- ✅ **Document Processing**: Markdown/PlainText plugins fully implemented and tested
- ✅ **Specialized Language Plugins**: All 13 specialized plugins complete (Java, Go, Rust, C#, Swift, Kotlin, TypeScript, Python, C, C++, JavaScript, Dart, HTML/CSS)
- ✅ **Performance Benchmarks**: Complete benchmark suite with published results
- ✅ **Production Automation**: Full CI/CD pipeline with automated deployment
- ✅ **Documentation**: Comprehensive validation and documentation complete

## Agent Capabilities

### Server Management
- Start/stop the FastAPI server (basic functionality only)
- ~~Monitor server health~~ (NOT IMPLEMENTED)
- Manage plugin lifecycle (basic loading only)
- ~~Handle file watching~~ (NOT CONNECTED to indexing)

### Language Plugins Overview
This directory contains language-specific plugins for the code indexing system. Currently, only the Python plugin has a working implementation. All other plugins are placeholders that need to be implemented.

#### Plugin Implementation Status
- ✅ **Python Plugin**: FULLY IMPLEMENTED
  - Uses Tree-sitter for parsing (NOT AST module)
  - Uses Jedi for symbol lookup and references
  - Supports fuzzy text search
  - Pre-indexes all .py files on startup

- ❌ **Stub Plugins** (NOT IMPLEMENTED):
  - C Plugin: Empty stub with `...` methods
  - C++ Plugin: Empty stub with `...` methods
  - JavaScript Plugin: Empty stub with `...` methods
  - Dart Plugin: Empty stub with `...` methods
  - HTML/CSS Plugin: Empty stub with `...` methods

### Plugin Development
- Create new language plugins (must implement IPlugin interface)
- Extend existing plugins
- Debug plugin issues (limited - no proper logging)
- ~~Optimize plugin performance~~ (No performance features)

### API Development
- Add new endpoints (basic FastAPI)
- Modify existing endpoints
- Update request/response models
- ~~Implement authentication~~ (NOT IMPLEMENTED)

### File System
- Monitor file changes (watchdog installed but not connected)
- ~~Handle file events~~ (TODO in code)
- ~~Manage indexing state~~ (No persistent state)
- ~~Coordinate cloud sync~~ (STUB ONLY)

## Agent Constraints

1. **Current Limitations**
   - No persistent storage - everything is in memory
   - File watcher doesn't trigger re-indexing
   - No error recovery mechanisms
   - No performance optimization
   - No security features

2. **Missing Components**
   - Database integration (SQLite planned)
   - Cache layer
   - Metrics collection
   - Health monitoring
   - Rate limiting
   - Authentication/authorization

3. **Implementation Gaps**
   - Dispatcher has no plugin matching by file extension
   - No index update mechanism
   - No search ranking or relevance scoring
   - No semantic search (despite parameter)

## ESSENTIAL_COMMANDS

```bash
# Development Server
uvicorn mcp_server.gateway:app --reload --host 0.0.0.0 --port 8000

# Testing Implementation
pytest tests/test_gateway.py -v
pytest tests/test_dispatcher.py -v  
pytest tests/test_python_plugin.py -v

# Plugin Testing
python -m mcp_server.plugins.python_plugin.plugin  # Test plugin directly

# API Testing
curl http://localhost:8000/status
curl "http://localhost:8000/symbol?symbol_name=parse&file_path=mcp_server/gateway.py"
curl "http://localhost:8000/search?query=def%20parse&limit=10"

# Debugging
tail -f mcp_server.log  # If logging is configured
```

## CODE_STYLE_PREFERENCES

```python
# Implementation Patterns (discovered from existing code)
# FastAPI endpoints with structured responses
@app.get("/symbol")
async def get_symbol(symbol_name: str, file_path: Optional[str] = None):
    return {"status": "success", "data": result, "timestamp": datetime.now()}

# Plugin Base Pattern
class LanguagePlugin(PluginBase):
    def index(self, file_path: str) -> Dict
    def getDefinition(self, symbol: str, context: Dict) -> Dict
    def getReferences(self, symbol: str, context: Dict) -> List[Dict]
    def search(self, query: str, options: Dict) -> List[Dict]

# Error Handling Pattern
try:
    result = await dispatcher.dispatch_request(...)
except Exception as e:
    return {"status": "error", "error": str(e), "timestamp": datetime.now()}

# Type Hints Required
from typing import Dict, List, Optional, Union
```

## ARCHITECTURAL_PATTERNS

```python
# MCP Server Architecture Components
gateway.py          # FastAPI endpoints, request routing
dispatcher.py       # Plugin routing and lifecycle
plugin_base.py      # Abstract base for all plugins
plugin_system/      # Plugin discovery and management
storage/           # SQLite persistence layer
utils/             # TreeSitter wrapper, indexing utilities

# Plugin Discovery Pattern
# Plugins auto-registered in dispatcher initialization
# File extensions mapped to language plugins

# Caching Pattern (when implemented)
# Content-based caching in dispatcher
# Query result caching for performance
```

## NAMING_CONVENTIONS

```python
# Files: snake_case.py
gateway.py, dispatcher.py, plugin_base.py
sqlite_store.py, file_watcher.py

# Classes: PascalCase
class FileWatcher, class PluginBase, class AuthManager

# Functions: snake_case
def get_definition(), def cache_symbol_lookup()

# Plugin Structure
mcp_server/plugins/{language}_plugin/
├── __init__.py
├── plugin.py          # Main plugin implementation
└── AGENTS.md          # Plugin-specific guidance
```

## DEVELOPMENT_ENVIRONMENT

```bash
# Python Setup
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -e .

# FastAPI Development
# Auto-reload enabled by default in uvicorn command
# API docs available at: http://localhost:8000/docs

# Testing Environment
pytest --version
# Use fixtures from tests/conftest.py
# Test isolation with temporary directories

# Plugin Development
# Follow python_plugin as reference implementation
# Tree-sitter grammars auto-installed via tree-sitter-languages
```

## TEAM_SHARED_PRACTICES

```python
# Implementation Status: Always update AGENTS.md with actual status
# Plugin Development: Use python_plugin as template
# API Development: Follow FastAPI response patterns
# Error Handling: Structured error responses required
# Testing: Integration tests for all plugins

# Plugin Interface Compliance:
# - All methods must be implemented (no pass/...)
# - Use Tree-sitter for parsing when possible
# - Return structured data formats
# - Handle errors gracefully

# Performance Considerations:
# - Cache plugin results in dispatcher
# - Use async/await for I/O operations
# - Lazy loading for large codebases
# - Monitor memory usage during indexing
```

## What Actually Works

1. **Basic API**:
   - GET `/symbol?symbol=name` - Returns symbol definition if found
   - GET `/search?q=query&semantic=false&limit=20` - Returns search results
   - Both require dispatcher to be initialized

2. **Plugin System**:
   - Plugins can be loaded and registered
   - Dispatcher routes requests to all plugins
   - Python plugin can do basic symbol lookup with Jedi

3. **File Watching**:
   - Watchdog observers are created
   - File change events are detected
   - BUT: No indexing is triggered (TODO in code)

## Development Priorities

1. **Connect file watcher to indexing** (fix TODO in watcher.py)
2. **Implement local storage** (SQLite with FTS5)
3. **Add proper error handling and logging**
4. **Complete Python plugin implementation**
5. **Add at least one more language plugin**
6. **Implement basic caching**
7. **Add health check endpoint**
8. **Document actual API usage** 