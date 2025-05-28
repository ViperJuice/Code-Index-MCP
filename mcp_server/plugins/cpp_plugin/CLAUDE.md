# C++ Plugin

This plugin provides C++ code indexing and analysis capabilities for the MCP server.

## Features

- Template handling
- Class hierarchy analysis
- Namespace resolution
- Overload resolution
- Template specialization
- Modern C++ features

## Implementation Details

### Parser
- Uses Tree-sitter for C++ parsing
- Handles templates
- Processes namespaces
- Manages class hierarchies

### Indexer
- Tracks class relationships
- Maps template instantiations
- Records namespace scopes
- Maintains overload sets

### Analysis
- Template analysis
- Class hierarchy tracking
- Namespace resolution
- Overload resolution

## Common Patterns

1. **Class Analysis**
   ```cpp
   // Track class hierarchy
   void analyze_class(const ClassDecl* decl) {
       process_base_classes(decl);
       track_methods(decl);
   }
   ```

2. **Template Handling**
   ```cpp
   // Process template definitions
   void process_template(const TemplateDecl* decl) {
       analyze_template_params(decl);
       track_specializations(decl);
   }
   ```

3. **Namespace Resolution**
   ```cpp
   // Resolve namespace scopes
   Namespace* resolve_namespace(const char* name) {
       return find_namespace_in_scope(name);
   }
   ```

## Edge Cases

- Template metaprogramming
- Multiple inheritance
- Virtual inheritance
- ADL resolution
- SFINAE
- CRTP patterns 