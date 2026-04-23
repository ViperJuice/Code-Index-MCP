# Verify MCP Usage

Check if MCP tools are being used correctly and efficiently.

## Usage
```
/verify-mcp
```

## What It Does

This command performs a self-check to verify:
1. MCP tools are available and working
2. Repository readiness is `ready`
3. Search performance is optimal
4. `index_unavailable` responses are treated as `native_search` fallback signals

## Verification Steps

1. **Check MCP Status**
   - Uses `mcp__code-index-mcp__get_status()`
   - Verifies index health and repository readiness

2. **Test Symbol Lookup**
   - Quick test: `mcp__code-index-mcp__symbol_lookup(symbol="PluginManager")`
   - Should return in <100ms

3. **Test Code Search**
   - Quick test: `mcp__code-index-mcp__search_code(query="def test_", limit=5)`
   - Should return in <500ms

4. **List Available Plugins**
   - Uses `mcp__code-index-mcp__list_plugins()`
   - Should show 48 languages

## Expected Output

```
✅ MCP Verification Results:
- Status: Healthy
- Repository Readiness: ready
- Indexed Files: 312
- Languages: 48
- Symbol Lookup: <100ms
- Code Search: <500ms
- Indexed Search: ready
- Fallback: index_unavailable -> safe_fallback native_search

All systems operational!
```

## Troubleshooting

If verification fails:
- Check if MCP server is running
- Verify index exists in .mcp-index/
- If readiness is non-ready, use native_search and run reindex when remediation asks for it
- Ensure AGENTS.md is loaded
- Review recent tool usage patterns

## Performance Baseline

Compare against these benchmarks:
- Symbol lookup: <100ms (vs grep: 45s)
- Pattern search: <500ms (vs grep: 30s)
- Semantic search: <1s (grep: impossible)
