# MCP Integration Guide

This guide explains how the new MCP components integrate with existing reusable code during the migration.

## Architecture Overview

The migration strategy keeps all reusable components in place while adding new MCP-specific directories:

```
mcp_server/
├── NEW MCP COMPONENTS           │  EXISTING REUSABLE COMPONENTS
├── protocol/         🆕         │  ├── plugins/          ✅
├── transport/        🆕         │  ├── storage/          ✅
├── resources/        🆕         │  ├── utils/            ✅
├── tools/           🆕         │  ├── cache/            ✅
├── session/         🆕         │  ├── interfaces/       ✅
├── prompts/         🆕         │  ├── plugin_base.py    ✅
                                │  ├── dispatcher/       ✏️ (modify)
                                │  └── watcher.py        ✏️ (modify)
```

## Integration Patterns

### 1. MCP Resources → Storage Layer

The MCP resource handlers will import and use the existing storage layer:

```python
# mcp_server/resources/handlers/file.py
from mcp_server.storage.sqlite_store import SQLiteStore

class FileResourceHandler:
    def __init__(self):
        self.storage = SQLiteStore()
    
    async def get_file_content(self, uri: str):
        # Parse code://file/path/to/file.py
        file_path = self._parse_uri(uri)
        # Use existing storage to get content
        return self.storage.get_file_content(file_path)
```

### 2. MCP Tools → Dispatcher

The MCP tools will wrap existing dispatcher functionality:

```python
# mcp_server/tools/handlers/search_code.py
from mcp_server.dispatcher.dispatcher import Dispatcher

class SearchCodeTool:
    def __init__(self):
        self.dispatcher = Dispatcher()
    
    async def execute(self, params: dict):
        # Use existing dispatcher search
        results = await self.dispatcher.search(
            query=params['query'],
            options=params.get('options', {})
        )
        return self._format_for_mcp(results)
```

### 3. MCP Tools → Plugin System

The MCP server will use the existing plugin system unchanged:

```python
# mcp_server/tools/handlers/lookup_symbol.py
from mcp_server.plugin_system.plugin_manager import PluginManager

class LookupSymbolTool:
    def __init__(self):
        self.plugin_manager = PluginManager()
    
    async def execute(self, params: dict):
        # Get appropriate plugin for file type
        plugin = self.plugin_manager.get_plugin_for_file(params['file'])
        # Use plugin's existing interface
        return plugin.get_definition(params['symbol'])
```

### 4. MCP Session → File Watcher

The MCP session manager will register for file watcher notifications:

```python
# mcp_server/session/manager.py
from mcp_server.watcher import FileWatcher

class MCPSessionManager:
    def __init__(self):
        self.watcher = FileWatcher()
        self.watcher.on_change(self._handle_file_change)
    
    async def _handle_file_change(self, event):
        # Convert to MCP notification
        await self._notify_clients({
            "method": "notifications/resources/changed",
            "params": {"uri": f"code://file/{event.path}"}
        })
```

## Import Examples

### From New MCP Code → Existing Code

```python
# New MCP components import existing reusable code
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.plugins.python_plugin.plugin import PythonPlugin
from mcp_server.utils.fuzzy_indexer import FuzzyIndexer
from mcp_server.utils.semantic_indexer import SemanticIndexer
from mcp_server.cache.query_cache import QueryCache
from mcp_server.interfaces.plugin_interfaces import IPlugin
```

### No Changes Needed

The following components work as-is without any imports or modifications:

1. **All Language Plugins**
   - They implement the `IPlugin` interface
   - MCP tools will call their existing methods
   - No protocol-specific code

2. **Storage Layer**
   - SQLite operations are protocol-agnostic
   - Same queries work for REST and MCP
   - FTS5 search unchanged

3. **Utility Functions**
   - Fuzzy search algorithms
   - Semantic indexing
   - Tree-sitter parsing

## Modification Strategy

### Components Needing Minor Updates

1. **Dispatcher** (`dispatcher/dispatcher.py`)
   - Remove FastAPI dependencies
   - Add async/await where needed
   - Keep core logic intact

2. **File Watcher** (`watcher.py`)
   - Add MCP notification callbacks
   - Keep watchdog implementation
   - Add subscription management

### Example Dispatcher Modification

```python
# Before (REST-coupled)
from fastapi import HTTPException

class Dispatcher:
    def search(self, query: str):
        if not query:
            raise HTTPException(400, "Query required")
        # ... search logic

# After (Protocol-agnostic)
class Dispatcher:
    async def search(self, query: str):
        if not query:
            raise ValueError("Query required")
        # ... same search logic (now async)
```

## Benefits of This Approach

1. **Minimal Risk**: Existing code continues to work
2. **Gradual Migration**: Can implement MCP features incrementally
3. **Code Reuse**: 40-50% of code used without changes
4. **Clear Boundaries**: New MCP code isolated in its own directories
5. **Easy Testing**: Can test both systems side-by-side

## Implementation Order

1. **Phase 1**: Build MCP protocol layer (uses no existing code)
2. **Phase 2**: Implement resources/tools (wraps existing components)
3. **Phase 3**: Modify dispatcher and watcher (remove REST coupling)
4. **Phase 4**: Remove old REST code (cleanup phase)

This approach ensures a smooth transition while maximizing code reuse and minimizing risk.