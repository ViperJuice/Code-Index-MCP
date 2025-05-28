# Dart Plugin

This plugin provides Dart code indexing and analysis capabilities for the MCP server.

## Features

- Dart 2.x support
- Mixin analysis
- Extension methods
- Null safety
- Async/await handling
- Code generation

## Implementation Details

### Parser
- Uses Tree-sitter for Dart
- Handles mixins
- Processes extensions
- Manages async code

### Indexer
- Tracks class relationships
- Maps extension methods
- Records type information
- Maintains mixin chains

### Analysis
- Type inference
- Mixin resolution
- Extension analysis
- Async flow tracking

## Common Patterns

1. **Class Analysis**
   ```dart
   // Track class relationships
   class MyClass with MyMixin {
     // Classes and mixins are tracked
   }
   ```

2. **Extension Methods**
   ```dart
   // Process extension methods
   extension MyExtension on String {
     String myMethod() => this.toUpperCase();
   }
   ```

3. **Mixin Resolution**
   ```dart
   // Analyze mixin chains
   mixin MyMixin {
     void myMethod() {
       // Mixin methods are tracked
     }
   }
   ```

## Edge Cases

- Multiple mixins
- Extension conflicts
- Null safety
- Code generation
- Async flow
- Generic types 