# Dart Plugin Agent Configuration

This file defines the capabilities and constraints for AI agents working with the Dart plugin.

## Agent Capabilities

### Dart Analysis
- Parse Dart code
- Handle mixins
- Resolve extensions
- Track types
- Analyze async code
- Process null safety

### Code Understanding
- Understand Dart idioms
- Handle mixin chains
- Process extensions
- Track dependencies
- Analyze scopes

### Testing & Validation
- Test parsing
- Validate mixin resolution
- Check type inference
- Verify extensions
- Test edge cases

### Performance
- Optimize parsing
- Cache results
- Handle large codebases
- Manage memory

## Agent Constraints

1. **Dart Support**
   - Support Dart 2.x
   - Handle null safety
   - Maintain compatibility
   - Process new features

2. **Analysis Accuracy**
   - Correct mixin resolution
   - Accurate type inference
   - Valid extension handling
   - Proper null safety

3. **Performance**
   - Efficient parsing
   - Optimize memory usage
   - Handle large codebases
   - Cache effectively

4. **Edge Cases**
   - Handle multiple mixins
   - Process extension conflicts
   - Support code generation
   - Handle async flow

## Common Operations

```dart
// Parse Dart file
AST parseFile(String path) {
  return treeSitterParse(path);
}

// Analyze mixins
void analyzeMixins(AST ast) {
  processMixinDeclarations(ast);
  resolveMixinChains();
}

// Track extensions
void trackExtensions(AST ast) {
  buildExtensionMap(ast);
  resolveConflicts();
}
``` 