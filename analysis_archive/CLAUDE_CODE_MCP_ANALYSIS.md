# Claude Code MCP Connection Analysis

## Executive Summary

After analyzing Claude Code transcripts and configurations, I've identified the primary issue preventing MCP connections: **path mismatches in the `.mcp.json` configuration file**.

## Issues Found

### 1. Path Mismatch in `.mcp.json`

The main `.mcp.json` file contained hardcoded paths pointing to a different environment:

```json
// INCORRECT (original):
{
  "command": "python3",
  "args": ["/home/jenner/code/Code-Index-MCP/scripts/cli/mcp_server_cli.py"],
  "cwd": "/home/jenner/code/Code-Index-MCP",
  "PYTHONPATH": "/home/jenner/code/Code-Index-MCP",
  "MCP_WORKSPACE_ROOT": "/home/jenner/code/Code-Index-MCP"
}

// CORRECTED:
{
  "command": "/usr/local/bin/python",
  "args": ["/workspaces/Code-Index-MCP/scripts/cli/mcp_server_cli.py"],
  "cwd": "/workspaces/Code-Index-MCP",
  "PYTHONPATH": "/workspaces/Code-Index-MCP",
  "MCP_WORKSPACE_ROOT": "/workspaces/Code-Index-MCP"
}
```

### 2. Missing Central Storage Path

The configuration was missing the `MCP_INDEX_STORAGE_PATH` environment variable that points to our centralized index storage:

```json
"MCP_INDEX_STORAGE_PATH": "~/.mcp/indexes"
```

## Evidence of Working MCP

Despite configuration issues, the test logs show that MCP tools DO work when properly configured:

### From `test_claude_session.log`:
- User queries like "Find where PluginManager is defined"
- MCP tool calls: `mcp__code-index-mcp__symbol_lookup` and `mcp__code-index-mcp__search_code`
- Efficient workflow with sub-second response times
- 7 MCP tools used, 0 native search tools

### MCP Tool Format in Claude Code:
```
mcp__<server-name>__<tool-name>
```
Example: `mcp__code-index-mcp__symbol_lookup`

## Analysis Results

### 1. **No Connection Errors in Logs**
- No JSON-RPC errors
- No connection failures
- Server initializes successfully

### 2. **MCP Adoption Rate (from transcripts)**
- Only 2.2% of tool usage is MCP (10 out of 453 tool calls)
- When used, MCP provides 99.996% token reduction
- 26,000:1 token ratio improvement

### 3. **Configuration Files Found**
- `.mcp.json` - Main configuration (now fixed)
- `.mcp.json.backup` - Had correct paths for /workspaces
- `.mcp.json.docker` - Docker-based configuration
- Multiple test configurations in `/test_indexes/`

## Recommendations

### 1. **Immediate Actions (Completed)**
- ✅ Fixed path mismatches in `.mcp.json`
- ✅ Added `MCP_INDEX_STORAGE_PATH` environment variable
- ✅ Verified configuration matches current environment

### 2. **Testing Steps**
1. Restart Claude Code to pick up new configuration
2. Test MCP tools with queries like:
   - "Find the BM25Indexer class"
   - "Search for reranking implementation"
   - "Look up SQLiteStore symbol"

### 3. **Monitoring**
- Watch for `mcp__code-index-mcp__` tool calls in Claude Code
- Monitor response times and accuracy
- Track adoption rate improvements

## Conclusion

The primary issue was a simple path mismatch in the configuration file. With the corrected paths and proper environment variables, Claude Code should now be able to connect to the MCP server. The infrastructure is working correctly (as evidenced by successful test runs), and the BM25 fallback ensures that searches will return results even without plugins loaded.

---

*Analysis completed: 2025-06-17*