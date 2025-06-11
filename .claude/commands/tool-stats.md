# Tool Usage Statistics

Display statistics about tool usage patterns in the current session.

## Usage
```
/tool-stats
```

## What It Shows

This command analyzes your current session and displays:

1. **Tool Usage Counts**
   - MCP tools used
   - Native search tools used
   - File operations

2. **Performance Metrics**
   - Average response times
   - Total time saved by using MCP
   - Efficiency rating

3. **MCP Compliance**
   - Percentage of searches using MCP
   - Any violations of MCP-first strategy
   - Suggestions for improvement

## Example Output

```
📊 Tool Usage Statistics
========================

Session Duration: 15 minutes
Total Tool Calls: 42

MCP Tools (Recommended):
- symbol_lookup: 8 calls (19%)
- search_code: 12 calls (29%)
- get_status: 2 calls (5%)
Total MCP: 22 calls (52%)

Native Tools:
- Read: 18 calls (43%)
- Grep: 0 calls (0%) ✅
- Find: 0 calls (0%) ✅
- Glob: 2 calls (5%) ⚠️

Performance Impact:
- Time with MCP: 11.5s
- Time without MCP: ~680s
- Efficiency Gain: 59x faster

MCP-First Compliance: 100% ✅
All searches used MCP tools first!

Recommendations:
- Consider using search_code instead of Glob for file discovery
- Excellent MCP adoption rate!
```

## Metrics Explained

- **MCP Usage Rate**: Percentage of search operations using MCP
- **Efficiency Gain**: How much faster than traditional search
- **Compliance Score**: Whether MCP tools are used before native search

## Goal Metrics

Aim for:
- MCP Usage: >80% of searches
- Zero grep/find for content search
- Compliance: 100% MCP-first