# MCP Server Agent Configuration

This file defines the capabilities and constraints for AI agents working with the MCP server core implementation.

## Current Implementation Status

### What's Actually Working
- **Basic FastAPI Server**: Simple endpoints at `/symbol` and `/search`
- **Basic Dispatcher**: Routes requests to plugins, no caching or optimization
- **Plugin Interface**: Base class defined with required methods
- **Python Plugin**: Partially implemented with Jedi integration

### What's NOT Implemented (TODOs)
- **File Watcher**: Code exists but doesn't trigger indexing (see TODO in watcher.py line 14)
- **Cloud Sync**: Just a stub with empty methods (sync.py)
- **Local Storage**: No database or persistent index
- **Caching**: No caching layer implemented
- **Authentication**: No security measures
- **Metrics/Monitoring**: No health checks or performance metrics
- **Error Recovery**: Basic error handling only
- **Most Language Plugins**: Only Python plugin has any real implementation

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

## Common Operations

```python
# Start server (basic mode only)
uvicorn mcp_server.gateway:app --reload

# Add new plugin (must implement all methods)
class MyPlugin(PluginBase):
    def index(self, path: str) -> Dict:
        # Must implement
        pass
    
    def getDefinition(self, symbol: str) -> SymbolDef | None:
        # Must implement
        pass
    
    def getReferences(self, symbol: str) -> list[Reference]:
        # Must implement
        pass
    
    def search(self, query: str, options: dict) -> list[SearchResult]:
        # Must implement
        pass

# File watcher exists but doesn't do anything useful yet
watcher = FileWatcher(root_path, dispatcher)
watcher.start()  # Watches files but doesn't trigger indexing
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