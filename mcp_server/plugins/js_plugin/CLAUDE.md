# JavaScript Plugin

This plugin provides JavaScript code indexing and analysis capabilities for the MCP server.

## Features

- ES6+ syntax support
- Module resolution
- Type inference
- Prototype analysis
- Async/await handling
- Decorator processing

## Implementation Details

### Parser
- Uses Tree-sitter for JS parsing
- Handles ES modules
- Processes decorators
- Manages async code

### Indexer
- Tracks module dependencies
- Maps prototype chains
- Records type information
- Maintains scope hierarchy

### Analysis
- Type inference
- Module resolution
- Prototype analysis
- Async flow tracking

## Common Patterns

1. **Module Analysis**
   ```javascript
   // Track module dependencies
   function analyzeModule(path) {
     const ast = parseModule(path);
     return processImports(ast);
   }
   ```

2. **Prototype Chain**
   ```javascript
   // Analyze prototype inheritance
   function analyzePrototype(obj) {
     return trackPrototypeChain(obj);
   }
   ```

3. **Type Inference**
   ```javascript
   // Infer types from usage
   function inferType(node) {
     return analyzeTypeUsage(node);
   }
   ```

## Edge Cases

- Dynamic imports
- Prototype pollution
- Module cycles
- Async flow
- Decorator chains
- Type coercion 