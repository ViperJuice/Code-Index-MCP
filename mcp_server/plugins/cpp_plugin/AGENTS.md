# C++ Plugin Agent Configuration

This file defines the capabilities and constraints for AI agents working with the C++ plugin.

## Agent Capabilities

### C++ Analysis
- Parse C++ source code
- Handle templates
- Resolve namespaces
- Track classes
- Analyze overloads
- Process modern features

### Code Understanding
- Understand C++ idioms
- Handle template metaprogramming
- Process class hierarchies
- Track dependencies
- Analyze scopes

### Testing & Validation
- Test parsing
- Validate template resolution
- Check class hierarchy
- Verify namespace resolution
- Test edge cases

### Performance
- Optimize parsing
- Cache results
- Handle large codebases
- Manage memory

## Agent Constraints

1. **C++ Standard Support**
   - Support C++11/14/17/20
   - Handle standard differences
   - Maintain compatibility
   - Process extensions

2. **Analysis Accuracy**
   - Correct template resolution
   - Accurate class hierarchy
   - Valid namespace handling
   - Proper overload resolution

3. **Performance**
   - Efficient parsing
   - Optimize memory usage
   - Handle large codebases
   - Cache effectively

4. **Edge Cases**
   - Handle template metaprogramming
   - Process multiple inheritance
   - Support SFINAE
   - Handle CRTP

## Common Operations

```cpp
// Parse C++ file
AST* parse_file(const char* path) {
    return tree_sitter_parse(path);
}

// Analyze templates
void analyze_templates(AST* tree) {
    process_template_declarations(tree);
    resolve_specializations();
}

// Track classes
void track_classes(AST* tree) {
    build_class_hierarchy(tree);
    resolve_inheritance();
}
``` 