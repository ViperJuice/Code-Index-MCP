# MCP Server Restart Required

## Issue
The MCP search_code tool is still hanging because Claude is connected to an MCP server instance that was started on June 27th (before our fixes were implemented).

## Current Situation
- Process ID 10248 running since June 27
- This old instance doesn't have our timeout protection fixes
- Our fixes are in the code but not in the running server

## Solution
The MCP server needs to be restarted for the fixes to take effect. This typically happens when:
1. VS Code/Claude Code is restarted
2. The MCP server is manually restarted
3. The .mcp.json configuration is modified

## Verification
After restart, the new server will have:
- Timeout protection on all search operations
- Better async handling to prevent deadlocks
- Enhanced logging for debugging

## Test Command
Once restarted, test with:
```bash
python scripts/verify_mcp_no_hang.py
```

The search_code tool should respond within seconds without hanging.