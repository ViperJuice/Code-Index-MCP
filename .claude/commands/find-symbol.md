# Find Symbol Definition

Quickly locate any symbol (class, function, method, variable) in the codebase using the MCP index.

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

Never use grep or file searching - the MCP index is 100x faster!