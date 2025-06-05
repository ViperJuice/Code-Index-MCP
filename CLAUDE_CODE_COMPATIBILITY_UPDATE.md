# Claude Code Compatibility Update

## Date: June 4, 2025

### Summary
Implemented Claude Code compatibility by adding support for disabling resource capabilities, as Claude Code only supports Tools and Prompts according to the MCP feature matrix.

### Changes Made

#### 1. Server Implementation
- **Modified**: `mcp_server/session/capabilities.py`
  - Added `MCP_DISABLE_RESOURCES` environment variable check in `ServerCapabilities.get_default()`
  - Sets `provides_resources=False` and `available_resource_types=[]` when enabled

- **Modified**: `mcp_server/stdio_server.py`
  - Updated `handle_initialize()` to check `MCP_DISABLE_RESOURCES` environment variable
  - Added guards in resource method handlers to return proper errors when resources are disabled

#### 2. Documentation Updates
- **Updated**: `README.md`
  - Added Claude Code section with specific configuration instructions
  - Added `MCP_DISABLE_RESOURCES` to environment variables table

- **Updated**: `MCP_CONFIGURATION_GUIDE.md`
  - Added Claude Code compatibility note at the top

- **Updated**: `docs/configuration/ENVIRONMENT-VARIABLES.md`
  - Added Model Context Protocol (MCP) Configuration section
  - Documented `MCP_DISABLE_RESOURCES`, `MCP_DEBUG`, and `MCP_CLIENT_TYPE` variables

#### 3. Configuration Files
- **Cleaned up**: Multiple temporary configuration files created during debugging
- **Standardized**: Claude Code configuration using `claude mcp add` command

### Technical Details

The issue was that Claude Code attempted to connect to the MCP server but failed because:
1. Claude Code doesn't support resource capabilities (only Tools and Prompts)
2. Our server was advertising resource capabilities in its initialization response
3. This caused Claude Code to fail the connection

The fix:
1. Added environment variable `MCP_DISABLE_RESOURCES` that when set to `true`:
   - Removes `resources` from the server's advertised capabilities
   - Returns error responses for any resource-related method calls
2. Updated all Claude Code configurations to include this environment variable

### Usage

For Claude Code users, configure the server with:
```bash
claude mcp add code-index python -m mcp_server
```

Or manually in `~/.claude.json`:
```json
{
  "mcpServers": {
    "code-index": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "mcp_server"],
      "env": {
        "MCP_DISABLE_RESOURCES": "true"
      }
    }
  }
}
```

### Testing
Verified that:
- Server starts successfully with `MCP_DISABLE_RESOURCES=true`
- Only Tools and Prompts capabilities are advertised
- Resource method calls return appropriate error messages
- Server works normally without the environment variable (backward compatible)