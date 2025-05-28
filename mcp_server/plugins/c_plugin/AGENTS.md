# C Plugin Agent Configuration

This file defines the capabilities and constraints for AI agents working with the C plugin.

## Agent Capabilities

### C Analysis
- Parse C source code
- Handle preprocessor
- Resolve includes
- Track symbols
- Analyze types
- Process macros

### Code Understanding
- Understand C idioms
- Handle preprocessor directives
- Process header files
- Track dependencies
- Analyze scopes

### Testing & Validation
- Test parsing
- Validate symbol resolution
- Check type analysis
- Verify header resolution
- Test edge cases

### Performance
- Optimize parsing
- Cache results
- Handle large codebases
- Manage memory

## Agent Constraints

1. **C Standard Support**
   - Support C89/C99/C11
   - Handle standard differences
   - Maintain compatibility
   - Process extensions

2. **Analysis Accuracy**
   - Correct symbol resolution
   - Accurate type analysis
   - Valid preprocessor handling
   - Proper scope tracking

3. **Performance**
   - Efficient parsing
   - Optimize memory usage
   - Handle large codebases
   - Cache effectively

4. **Edge Cases**
   - Handle circular includes
   - Process conditional compilation
   - Support macro redefinition
   - Handle scope conflicts

## Common Operations

```c
// Parse C file
AST* parse_file(const char* path) {
    return tree_sitter_parse(path);
}

// Analyze includes
void analyze_includes(AST* tree) {
    process_preprocessor_directives(tree);
    resolve_includes();
}

// Track symbols
void track_symbols(AST* tree) {
    build_symbol_table(tree);
    resolve_references();
}
``` 