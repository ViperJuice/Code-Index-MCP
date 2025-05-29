# MCP Server Project Context

This is a local-first code indexer designed to enhance Claude Code and other LLMs. The project uses a modular, plugin-based architecture to support multiple languages and indexing strategies.

## Key Components

### Core Infrastructure
- **MCP Server**: FastAPI-based server that handles code indexing and querying
- **Gateway**: API endpoints for code search and indexing (`/symbol`, `/search`)
- **Dispatcher**: Plugin management and request routing
- **Plugin Base**: Base class for all language plugins

### Language Plugins

This directory contains language-specific plugins for code indexing and analysis. Each plugin implements the `PluginBase` interface and provides language-specific functionality.

#### Available Plugins
- **Python Plugin**: AST analysis, import resolution, type inference using Jedi (✅ Implemented)
  - Uses Tree-sitter for parsing (NOT AST module despite what's stated above)
  - Uses Jedi for symbol lookup and references
  - Supports fuzzy text search
  - Pre-indexes all .py files on startup
- **C Plugin**: Preprocessor handling, header resolution, symbol tracking (❌ Stub only)
- **C++ Plugin**: Template handling, namespace resolution, class hierarchies (❌ Stub only)
- **JavaScript Plugin**: ES6+ support, module resolution, prototype analysis (❌ Stub only)
- **Dart Plugin**: Mixin analysis, extension methods, null safety (❌ Stub only)
- **HTML/CSS Plugin**: Selector resolution, style inheritance, media queries (❌ Stub only)

#### Plugin Structure
Each plugin directory should contain:
1. `__init__.py`: Plugin registration
2. `indexer.py`: Main indexing logic
3. `parser.py`: Language-specific parsing
4. `utils.py`: Helper functions
5. `tests/`: Plugin-specific tests

#### Plugin Development
When creating a new plugin:
1. Inherit from `PluginBase`
2. Implement required methods: `supports()`, `indexFile()`, `getDefinition()`, `findReferences()`, `search()`
3. Add language-specific tests
4. Document language quirks
5. Handle edge cases

#### Common Patterns
- Use Tree-sitter for parsing
- Implement incremental updates
- Cache parsed results
- Handle language-specific features

### Supporting Systems
- **Watcher**: File system monitoring skeleton (watchdog-based, TODO: doesn't trigger indexing)
- **Utils**: TreeSitter wrapper (prototype), fuzzy indexer (prototype), semantic indexer (stub)
- **Sync**: Optional cloud synchronization (stub implementation)

## Technology Stack

- **Backend**: Python 3.x with FastAPI
- **Parsing**: Tree-sitter for language parsing
- **Language Analysis**: 
  - Python: AST module + Jedi
  - Other languages: Tree-sitter grammars
- **File Monitoring**: Watchdog
- **Embeddings**: Voyage AI (optional)
- **Architecture**: C4 model with Structurizr Lite

## Development Guidelines

1. **Plugin Development**
   - All plugins must inherit from `plugin_base.PluginBase`
   - Implement required methods: `index()`, `getDefinition()`, `getReferences()`
   - Use Tree-sitter for parsing where possible
   - Handle language-specific edge cases

2. **Architecture Principles**
   - Local-first design (offline functionality is primary)
   - Plugin isolation for security
   - Minimal external dependencies
   - Efficient memory usage

3. **Code Standards**
   - Type hints for all Python code
   - Comprehensive error handling
   - Logging for debugging
   - Unit tests for all components

4. **Documentation**
   - Update C4 diagrams for architectural changes
   - Maintain AGENTS.md files for AI guidance
   - Document API changes
   - Keep plugin documentation current

## Common Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Start the MCP server (Note: dispatcher initialization required)
uvicorn mcp_server.gateway:app --reload

# View architecture diagrams
docker run --rm -p 8080:8080 \
  -v "$(pwd)/architecture":/usr/local/structurizr \
  structurizr/lite

# Run tests
pytest

# Test specific plugin
python test_python_plugin.py
```

## API Endpoints

**Note**: The server starts with `dispatcher = None` and requires manual initialization. Without this, all endpoints return 503 errors.

- `GET /symbol`: Get symbol definition
  - Query parameter: `symbol` (string)
  - Returns: SymbolDef or null
  - Status: 503 if dispatcher not initialized

- `GET /search`: Search for code patterns
  - Query parameters: 
    - `q` (string): search query
    - `semantic` (bool, optional): enable semantic search (default: false)
    - `limit` (int, optional): max results (default: 20)
  - Returns: Array of SearchResult objects
  - Status: 503 if dispatcher not initialized

- `GET /status`: Server health check (❌ Not implemented)
- `GET /plugins`: List available plugins (❌ Not implemented)

## Project Structure

```
/workspaces/Code-Index-MCP/
├── mcp_server/              # Core server implementation
│   ├── gateway.py          # FastAPI application
│   ├── dispatcher.py       # Plugin routing
│   ├── plugin_base.py      # Plugin interface
│   ├── watcher.py          # File monitoring
│   ├── sync.py             # Cloud sync (stub)
│   ├── utils/              # Utility modules
│   └── plugins/            # Language plugins
├── architecture/           # C4 model diagrams
│   ├── level1_context.dsl  # System context
│   ├── level2_containers.dsl # Container architecture
│   ├── level3_mcp_components.dsl # Components with interfaces
│   └── level4/             # PlantUML code design
│       ├── shared_interfaces.puml
│       ├── api_gateway.puml
│       ├── dispatcher.puml
│       └── ... (component-specific UML)
├── ai_docs/               # Tool-specific documentation
├── docs/                  # Project documentation
├── requirements.txt       # Python dependencies
└── test_*.py             # Test files
```

## Architecture Documentation

The project follows the C4 model with four levels of detail:
1. **Context (Level 1)**: System boundaries and external interactions
2. **Containers (Level 2)**: High-level technical building blocks
3. **Components (Level 3)**: Internal structure with interface definitions
4. **Code (Level 4)**: Detailed PlantUML class diagrams showing implementation

Each component in Level 3 references its corresponding PlantUML file in Level 4, providing a complete view from architecture to code design.

## Current Status (~20% Implementation)

### Implemented Components
- ✅ Core FastAPI gateway structure
- ✅ Basic dispatcher framework
- ✅ Plugin base interface (IPlugin)
- ✅ Python plugin with:
  - Tree-sitter parsing for functions/classes
  - Jedi integration for definitions
  - Fuzzy search indexing
  - Pre-indexing of *.py files on init
- ✅ TreeSitterWrapper (prototype)
- ✅ FuzzyIndexer (prototype)

### Partially Implemented
- ⚠️ File watcher skeleton (doesn't trigger indexing)
- ⚠️ API endpoints (require manual dispatcher init)
- ⚠️ SearchResult model (basic implementation)

### Not Implemented
- ❌ Other language plugins (all are stubs)
- ❌ Semantic indexer (stub only)
- ❌ Local storage persistence
- ❌ Cloud sync (stub only)
- ❌ Server initialization/startup
- ❌ /status and /plugins endpoints
- ❌ Security features
- ❌ Error recovery
- ❌ Configuration system
- ❌ Logging infrastructure

## Important Notes

1. **Server Initialization**: The dispatcher is not automatically initialized. Without manual setup, all API calls return 503 errors.
   
   To properly initialize the dispatcher:
   ```python
   # In gateway.py or during startup:
   from mcp_server.dispatcher import Dispatcher
   from mcp_server.plugins.python_plugin.plugin import PythonPlugin
   
   # Create and configure dispatcher
   dispatcher = Dispatcher()
   dispatcher.registerPlugin(PythonPlugin())
   
   # Assign to gateway
   app.state.dispatcher = dispatcher
   ```

2. **Python Plugin Limitations**:
   - Only indexes functions and classes (no variables, imports, etc.)
   - Pre-indexes all .py files on construction (not scalable)
   - No incremental updates
   - No caching or persistence

3. **File Watcher**: Currently just a skeleton that doesn't trigger re-indexing when files change.

4. **Production Readiness**: This is a prototype/proof-of-concept. Not suitable for production use.

## Next Steps

1. Implement proper server initialization and plugin loading
2. Complete file watcher integration with indexing
3. Add persistence layer (SQLite with FTS5)
4. Implement remaining language plugins
5. Add configuration and logging
6. Create comprehensive test suite
7. Add error handling and recovery
8. Implement security features
9. Add performance optimizations
10. Create deployment documentation 