# MCP Server Guide

## Quick Start

1. **Start the MCP server:**
   ```bash
   python -m mcp_server.stdio_server
   ```
   
   This starts the MCP server with stdio transport for MCP client integration.

2. **Test the server:**
   ```bash
   python test_mcp_server.py
   ```

3. **Connect with Claude:**
   Configure Claude Desktop to use the stdio MCP server:
   ```json
   {
     "mcpServers": {
       "code-index": {
         "command": "python",
         "args": ["-m", "mcp_server.stdio_server"],
         "cwd": "/path/to/Code-Index-MCP"
       }
     }
   }
   ```

## Available MCP Methods

### Initialization
- `initialize` - Initialize a session with the server

### Resources
- `resources/list` - List all available code resources
- `resources/read` - Read content of a specific resource
- `resources/subscribe` - Subscribe to resource changes
- `resources/unsubscribe` - Unsubscribe from resource changes

### Tools
- `tools/list` - List all available tools
- `tools/call` - Execute a tool with arguments

### Available Tools

1. **search_code** - Search for code patterns
   ```json
   {
     "name": "search_code",
     "arguments": {
       "query": "search term",
       "limit": 10,
       "file_pattern": "*.py"
     }
   }
   ```

2. **lookup_symbol** - Find symbol definitions
   ```json
   {
     "name": "lookup_symbol",
     "arguments": {
       "symbol": "function_name",
       "type": "function"
     }
   }
   ```

3. **find_references** - Find all references to a symbol
   ```json
   {
     "name": "find_references",
     "arguments": {
       "symbol": "class_name",
       "include_definitions": false
     }
   }
   ```

4. **index_file** - Index or re-index a specific file
   ```json
   {
     "name": "index_file",
     "arguments": {
       "file_path": "/path/to/file.py"
     }
   }
   ```

5. **get_file_outline** - Get structural outline of a file
   ```json
   {
     "name": "get_file_outline",
     "arguments": {
       "file_path": "/path/to/file.py"
     }
   }
   ```

## Configuration

The MCP server uses the same configuration as the main Code-Index system:

- `CODEX_WORKSPACE_DIR` - Directory to index (default: current directory)
- `CODEX_LOG_LEVEL` - Logging level (default: INFO)
- `MCP_HOST` - WebSocket host (default: localhost)
- `MCP_PORT` - WebSocket port (default: 8765)

## Architecture

The MCP server integrates with the existing Code-Index components:

```
MCP Client (Claude, etc.)
    ↓
MCP Protocol Handler
    ↓
┌─────────────────┬──────────────────┬─────────────────┐
│   Resources     │      Tools       │     Watcher     │
│   (Storage)     │   (Dispatcher)   │  (Notifications)│
└─────────────────┴──────────────────┴─────────────────┘
    ↓                    ↓                    ↓
┌──────────────────────────────────────────────────────┐
│              Code-Index Core System                   │
│  (Indexer, Storage, Plugins, File Monitoring)        │
└──────────────────────────────────────────────────────┘
```

## Troubleshooting

1. **Connection refused:**
   - Ensure the server is running
   - Check if port 8765 is available
   - Verify firewall settings

2. **No resources found:**
   - Check if CODEX_WORKSPACE_DIR is set correctly
   - Ensure files have been indexed
   - Run indexing: `python -m mcp_server.indexer`

3. **Tools not working:**
   - Check server logs for errors
   - Verify the storage database exists
   - Ensure plugins are loaded correctly

## Development

To extend the MCP server:

1. **Add new tools:** Create tool handlers in `mcp_server/tools/handlers.py`
2. **Add new resources:** Extend `mcp_server/resources/registry.py`
3. **Custom plugins:** Implement `get_mcp_tools()` in your plugin

## Testing

Run the integration test suite:
```bash
python test_mcp_integration_final.py
```

This validates all MCP functionality including:
- Protocol handling
- Transport layers
- Session management
- Resource operations
- Tool execution
- Error handling