# Java Plugin - Claude Instructions

## Overview
This is the Java language plugin for the MCP code indexing system. It provides comprehensive support for Java codebases including advanced type analysis, build system integration, and cross-file reference tracking.

## Key Components

### 1. Main Plugin (`plugin.py`)
- Inherits from `SpecializedPluginBase`
- Coordinates all Java-specific analyzers
- Handles file indexing and symbol extraction
- Uses `javalang` library for AST parsing

### 2. Import Resolver (`import_resolver.py`)
- Resolves Java imports to file paths
- Tracks import dependencies
- Detects circular dependencies
- Handles both regular and static imports

### 3. Type Analyzer (`type_analyzer.py`)
- Analyzes Java type hierarchies
- Supports generic types and type bounds
- Tracks inheritance and interface implementations
- Handles access modifiers and other type attributes

### 4. Build System Integration (`build_system.py`)
- Parses Maven `pom.xml` files
- Parses Gradle `build.gradle` files
- Extracts project dependencies
- Determines project structure

### 5. Cross-File Analyzer (in `plugin.py`)
- Tracks references across files
- Builds call graphs
- Analyzes impact of changes

## Important Implementation Notes

### Initialization Order
The plugin must initialize Java-specific state BEFORE calling the parent class constructor:

```python
def __init__(self, ...):
    # Initialize Java-specific state first
    self._file_symbols = {}
    self._package_structure = {}
    self._import_statements = {}
    
    # Then call parent constructor
    super().__init__(language_config, sqlite_store, enable_semantic)
```

### Lazy Loading
Components are created on-demand to improve performance:
- Import resolver created on first access
- Type analyzer created when needed
- Build system integration loaded when required

### Error Handling
- Uses fallback regex parsing when javalang fails
- Gracefully handles malformed Java code
- Logs warnings for parsing failures

### Caching Strategy
- Import resolutions are cached
- Type information is cached
- Cross-file references are cached
- Cache invalidation on file changes

## Testing
- Basic functionality tested in `test_java_plugin_simple.py`
- Comprehensive tests in `test_java_plugin.py`
- Tests cover all major features

## Performance Considerations
- Pre-indexing skips build output directories
- Efficient symbol lookup using dictionaries
- Minimal parsing for initial indexing

## Integration Points
- Registered in `plugin_factory.py` as a specific plugin
- Uses standard MCP interfaces for compatibility
- Extends base functionality with Java-specific features