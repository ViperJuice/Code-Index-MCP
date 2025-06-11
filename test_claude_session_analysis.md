# Tool Usage Analysis Report

Generated: 2025-06-09T21:11:45.012336

## Summary
- Total Tools Used: 9
- MCP Tools: 7
- Native Search Tools: 0
- MCP-First Compliance: ✅ YES

## Performance Metrics
- Estimated Total Time: 3.7s
- MCP Time: 2.7s
- Native Search Time: 0.0s
- File Reads: 2

## Tool Usage Sequence
```
1. ✅ mcp__code-index-mcp__symbol_lookup
   Params: symbol="PluginManager"...
2. ✅ mcp__code-index-mcp__search_code
   Params: query="class PluginManager", limit=10...
3. ⚠️ Read
   Params: file_path="/app/mcp_server/plugin_system/plugin_ma...
4. ✅ mcp__code-index-mcp__search_code
   Params: query="def process_.*", limit=20...
5. ✅ mcp__code-index-mcp__search_code
   Params: query="TODO|FIXME", limit=30...
6. ✅ mcp__code-index-mcp__search_code
   Params: query="authentication", semantic=true...
7. ✅ mcp__code-index-mcp__search_code
   Params: query="file watch", semantic=true...
8. ✅ mcp__code-index-mcp__symbol_lookup
   Params: symbol="FileWatcher"...
9. ⚠️ Read
   Params: file_path="/app/mcp_server/watcher.py"...
```