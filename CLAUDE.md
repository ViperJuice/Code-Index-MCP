# MCP Server Project Context

This is a local-first code indexer designed to enhance Claude Code and other LLMs. The project uses a modular, plugin-based architecture to support multiple languages and indexing strategies.

## Key Components

- **MCP Server**: FastAPI-based server that handles code indexing and querying
- **Plugins**: Language-specific indexers (Python, Dart, JS, C/C++, HTML/CSS)
- **Watcher**: File system monitoring for real-time updates
- **Gateway**: API endpoints for code search and indexing

## Development Guidelines

1. All new plugins should inherit from `plugin_base.PluginBase`
2. Use Tree-sitter for language parsing where possible
3. Follow the local-first principle - cloud sync is optional
4. Maintain C4 architecture diagrams in the `architecture/` directory

## Common Tasks

- Adding a new language plugin
- Implementing new indexing strategies
- Extending the API endpoints
- Updating architecture diagrams

## Project Structure

- `mcp_server/`: Core server implementation
- `architecture/`: C4 model diagrams
- `.devcontainer/`: Development environment setup
- `plugins/`: Language-specific indexers 