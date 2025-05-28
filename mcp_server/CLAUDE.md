# MCP Server Core Implementation

This directory contains the core implementation of the MCP server, including the FastAPI application, plugin system, and file watching functionality.

## Key Files

- `gateway.py`: FastAPI application and API endpoints
- `plugin_base.py`: Base class for language plugins
- `dispatcher.py`: Plugin management and request routing
- `watcher.py`: File system monitoring
- `sync.py`: Optional cloud synchronization

## Plugin System

The plugin system is designed to be:
1. Language-agnostic
2. Easy to extend
3. Performant for local-first operation
4. Isolated for security

## API Endpoints

The server provides these main endpoints:
- `/index`: Index code in a directory
- `/search`: Search indexed code
- `/status`: Check indexing status
- `/plugins`: List available plugins

## Development Notes

1. All plugins must implement the `PluginBase` interface
2. File watching uses `watchdog` for efficiency
3. Indexing is asynchronous to prevent blocking
4. Cloud sync is optional and disabled by default 