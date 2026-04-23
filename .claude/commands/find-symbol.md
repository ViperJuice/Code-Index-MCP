# Find Symbol Definition

Quickly locate any symbol (class, function, method, variable) in the codebase using the MCP index.
Use indexed results as authoritative only when repository readiness is `ready`.
If `symbol_lookup` returns `index_unavailable` with
`safe_fallback: "native_search"`, use native `rg`/file search and follow the
readiness remediation, such as `reindex`.

## Usage
```
/find-symbol <symbol_name>
```

## Examples
- `/find-symbol PluginManager` - Find the PluginManager class
- `/find-symbol process_file` - Find the process_file function
- `/find-symbol IndexDiscovery` - Find the IndexDiscovery class

## Implementation
This command uses `mcp__code-index-mcp__symbol_lookup` to instantly locate symbol definitions.

Benefits:
- **Speed**: <100ms lookup time
- **Accuracy**: Exact definition location with line numbers
- **Context**: Returns signature and documentation

Ready indexes return ordinary `result: "not_found"` for misses. Non-ready
indexes return `index_unavailable`, where `native_search` is expected until
remediation is complete.
