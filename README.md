# MCP Server (Local-first Code Indexer)

Modular, extensible local-first indexer for enhancing Claude Code and other LLMs with deep code understanding capabilities.

## Architecture

The MCP Server follows a plugin-based architecture with three main layers:

1. **System Context (Level 1)**
   - Developer interacts with Claude
   - Claude uses MCP Server tools
   - MCP Server delegates to language plugins
   - Local-first indexing with cloud sync

2. **Containers (Level 2)**
   - API Gateway (FastAPI)
   - Dispatcher
   - Plugin System
   - Local Index Store
   - Cloud Sync
   - Embedding Service

3. **Components (Level 3)**
   - Gateway Controller
   - Dispatcher Core
   - Plugin Base
   - Plugin Registry
   - Plugin Manager
   - Language-specific Plugins

## Features

- **Local-first Code Indexing**
  - Tree-sitter based parsing
  - LSP integration
  - Symbol resolution
  - Type inference
  - Import/Include tracking

- **Plugin Architecture**
  - Python plugin (AST analysis)
  - C++ plugin (Template handling)
  - JavaScript plugin (ES6+ support)
  - C plugin (Preprocessor handling)
  - HTML/CSS plugin (Selector resolution)
  - Dart plugin (Mixin analysis)

- **Cloud Integration**
  - Optional cloud sync
  - Embedding fallback
  - Shard management
  - Distributed indexing

## Quickstart

1. **Install Dependencies**
```bash
# Install Python dependencies
pip install -r requirements.txt

# Install UV package manager
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. **Start the Server**
```bash
# Start the MCP server
uvicorn mcp_server.gateway:app --reload

# Start Structurizr Lite for architecture diagrams
docker run --rm -p 8080:8080 \
  -v "$(pwd)/architecture":/usr/local/structurizr \
  structurizr/lite
```

3. **Access the Services**
- MCP Server: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- Architecture Diagrams: http://localhost:8080

## Development

### Plugin Development

1. Create a new plugin directory in `mcp_server/plugins/`
2. Implement the plugin interface from `mcp_server.plugin_base`
3. Register the plugin in the plugin registry
4. Add plugin documentation in `CLAUDE.md` and `AGENTS.md`

### Architecture Updates

1. Modify the appropriate DSL file in the `architecture/` directory
2. View changes in Structurizr Lite
3. Update this README if necessary

## Contributing

1. Fork the repository
2. Create a feature branch
3. Implement your changes
4. Add tests and documentation
5. Submit a pull request

## License

MIT License - See LICENSE file for details
