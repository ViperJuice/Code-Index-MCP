# JavaScript Plugin Agent Configuration

This file defines the capabilities and constraints for AI agents working with the JavaScript plugin.

## Agent Capabilities

### JS Analysis
- Parse JavaScript code
- Handle ES modules
- Resolve imports
- Track prototypes
- Analyze types
- Process async code

### Code Understanding
- Understand JS idioms
- Handle ES6+ features
- Process modules
- Track dependencies
- Analyze scopes

### Testing & Validation
- Test parsing
- Validate module resolution
- Check type inference
- Verify prototype chains
- Test edge cases

### Performance
- Optimize parsing
- Cache results
- Handle large codebases
- Manage memory

## Agent Constraints

1. **JavaScript Support**
   - Support ES6+
   - Handle module systems
   - Maintain compatibility
   - Process new features

2. **Analysis Accuracy**
   - Correct module resolution
   - Accurate type inference
   - Valid prototype tracking
   - Proper scope handling

3. **Performance**
   - Efficient parsing
   - Optimize memory usage
   - Handle large codebases
   - Cache effectively

4. **Edge Cases**
   - Handle dynamic imports
   - Process prototype chains
   - Support async flow
   - Handle decorators

## Common Operations

```javascript
// Parse JS file
function parseFile(path) {
  return treeSitterParse(path);
}

// Analyze modules
function analyzeModules(ast) {
  processImports(ast);
  resolveDependencies();
}

// Track prototypes
function trackPrototypes(ast) {
  buildPrototypeChain(ast);
  resolveInheritance();
}
``` 