# MCP Verification Report

Generated: 2025-06-09T20:15:04.494377

## Summary
- Total Tests: 5
- Passed: 4
- Failed: 1
- Success Rate: 80.0%

## Test Results

### Find class definition
- Status: ✅ PASS
- MCP First: True
- Expected Tool Used: True
- Message: MCP tools used first
- Tools Used: mcp__code-index-mcp__symbol_lookup, Read

### Search function pattern
- Status: ✅ PASS
- MCP First: True
- Expected Tool Used: True
- Message: MCP tools used first
- Tools Used: mcp__code-index-mcp__search_code, Read

### Find imports of module
- Status: ✅ PASS
- MCP First: True
- Expected Tool Used: True
- Message: MCP tools used first
- Tools Used: mcp__code-index-mcp__search_code

### Semantic concept search
- Status: ✅ PASS
- MCP First: True
- Expected Tool Used: True
- Message: MCP tools used first
- Tools Used: mcp__code-index-mcp__search_code

### Bad pattern - Grep first
- Status: ❌ FAIL
- MCP First: False
- Expected Tool Used: True
- Message: Native tool used before MCP at position 0
- Tools Used: Grep, mcp__code-index-mcp__search_code


## Performance Impact
- Estimated time with MCP: 0.5s
- Estimated time without MCP: 0.0s
- Speedup: 0x faster