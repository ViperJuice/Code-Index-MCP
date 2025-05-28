# C Plugin

This plugin provides C code indexing and analysis capabilities for the MCP server.

## Features

- Preprocessor handling
- Header file resolution
- Symbol table management
- Type system analysis
- Macro expansion
- Include path resolution

## Implementation Details

### Parser
- Uses Tree-sitter for C parsing
- Handles preprocessor directives
- Processes header files
- Manages include paths

### Indexer
- Tracks symbol definitions
- Maps header dependencies
- Records type information
- Maintains scope hierarchy

### Analysis
- Type checking
- Symbol resolution
- Header dependency analysis
- Macro expansion tracking

## Common Patterns

1. **Header Analysis**
   ```c
   // Track header dependencies
   void analyze_header(const char* path) {
       process_includes(path);
       resolve_symbols();
   }
   ```

2. **Symbol Resolution**
   ```c
   // Resolve symbol references
   Symbol* resolve_symbol(const char* name) {
       return find_symbol_in_scope(name);
   }
   ```

3. **Type Analysis**
   ```c
   // Analyze type information
   TypeInfo* analyze_type(Type* type) {
       return process_type_definition(type);
   }
   ```

## Edge Cases

- Circular includes
- Conditional compilation
- Macro redefinition
- Type redefinition
- Scope conflicts 