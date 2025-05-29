# MCP Server Project Context

This is a local-first code indexer designed to enhance Claude Code and other LLMs. The project uses a modular, plugin-based architecture to support multiple languages and indexing strategies.

## Key Components

### Core Infrastructure
- **MCP Server**: FastAPI-based server that handles code indexing and querying
- **Gateway**: API endpoints for code search and indexing (`/symbol`, `/search`)
- **Dispatcher**: Plugin management and request routing
- **Plugin Base**: Base class for all language plugins

### Language Plugins
- **Python Plugin**: AST analysis, import resolution, type inference using Jedi
- **C Plugin**: Preprocessor handling, header resolution, symbol tracking
- **C++ Plugin**: Template handling, namespace resolution, class hierarchies
- **JavaScript Plugin**: ES6+ support, module resolution, prototype analysis
- **Dart Plugin**: Mixin analysis, extension methods, null safety
- **HTML/CSS Plugin**: Selector resolution, style inheritance, media queries

### Supporting Systems
- **Watcher**: File system monitoring for real-time updates (watchdog-based)
- **Utils**: TreeSitter wrapper, fuzzy indexer, semantic indexer
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

# Start the MCP server
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

- `POST /symbol`: Get symbol definition
  - Parameters: `symbol_name`, `file_path`
  - Returns: Definition location and details

- `POST /search`: Search for code patterns
  - Parameters: `query`, `file_extensions` (optional)
  - Returns: Matching code locations

- `GET /status`: Server health check
- `GET /plugins`: List available plugins

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
├── ai_docs/               # Tool-specific documentation
├── requirements.txt       # Python dependencies
└── test_*.py             # Test files
```

## Current Status

- ✅ Core architecture established
- ✅ Plugin system foundation
- ✅ Python plugin with Jedi integration
- ⚠️ Other plugins need implementation
- ❌ File watcher not fully implemented
- ❌ Local storage not implemented
- ❌ Cloud sync stub only

## Next Steps

1. Complete language plugin implementations
2. Implement file system watcher
3. Add local index storage (SQLite with FTS5)
4. Create comprehensive test suite
5. Add performance optimizations
6. Implement security features 