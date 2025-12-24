# Fast MCP vs Native Performance Report

**Generated:** 2025-06-28 19:34:25
**Total Tests:** 15
**Total Time:** 22.69 seconds

## Executive Summary

- **MCP Average:** 2066.93ms
- **Native Average:** 695.69ms
- **Speedup Factor:** 0.3x

## Method Performance

| Method | Tests | Avg Duration (ms) | Avg Tokens | Error Rate |
|--------|-------|------------------|------------|------------|
| mcp_semantic | 5 | 4128.37 | 1585 | 0.0% |
| mcp_sql | 5 | 5.50 | 1440 | 0.0% |
| native_grep | 5 | 695.69 | 70034 | 0.0% |

## Sample Results

### Test 1: mcp_sql
- Query: 'error'
- Duration: 4.08ms
- Results: 20

### Test 2: mcp_sql
- Query: 'async'
- Duration: 4.10ms
- Results: 20

### Test 3: mcp_sql
- Query: 'class'
- Duration: 5.86ms
- Results: 20

### Test 4: mcp_sql
- Query: 'function'
- Duration: 6.80ms
- Results: 20

### Test 5: mcp_sql
- Query: 'import'
- Duration: 6.65ms
- Results: 20

## Full Test Extrapolation

Based on these results, for 1,280 tests:
- MCP tests would take: ~1322.8 seconds
- Native tests would take: ~445.2 seconds
- Total time saved: ~-877.6 seconds