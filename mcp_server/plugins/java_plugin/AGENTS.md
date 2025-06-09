# Java Plugin Agent Instructions

## Overview
This plugin provides comprehensive Java language support for the MCP code indexing system, including advanced features for Java-specific constructs.

## Features

### 1. Import Resolution
- Resolves package imports to actual file paths
- Handles wildcard imports (`import java.util.*`)
- Tracks static imports
- Builds import dependency graphs
- Detects circular dependencies

### 2. Type Analysis
- Full support for Java generics
- Tracks class inheritance hierarchies
- Interface implementation tracking
- Type bounds and constraints
- Access modifier analysis (public, private, protected, package-private)
- Static, final, and abstract modifier tracking

### 3. Build System Integration
- **Maven Support**:
  - Parses `pom.xml` files
  - Extracts dependencies with version management
  - Handles property substitution
  - Supports multi-module projects
- **Gradle Support**:
  - Parses `build.gradle` and `build.gradle.kts`
  - Extracts dependencies from various DSL formats
  - Detects Android projects
  - Handles Kotlin DSL syntax

### 4. Cross-File Reference Tracking
- Tracks method calls across files
- Monitors class inheritance relationships
- Interface implementation tracking
- Import usage analysis
- Call graph generation
- Impact analysis for code changes

## Usage

### Basic Usage
```python
from mcp_server.plugins.java_plugin import Plugin
from mcp_server.storage.sqlite_store import SQLiteStore

# Create plugin
plugin = Plugin(sqlite_store=SQLiteStore("index.db"))

# Index a file
plugin.indexFile("src/main/java/Example.java", content)

# Find definition
definition = plugin.getDefinition("MyClass")

# Find references
references = plugin.findReferences("MyClass")
```

### Advanced Features

#### Import Analysis
```python
# Get import information for a file
imports = plugin.analyze_imports(Path("Example.java"))

# Get import dependency graph
import_graph = plugin.import_resolver.get_import_graph()

# Find circular dependencies
cycles = plugin.import_resolver.find_circular_dependencies()
```

#### Type Analysis
```python
# Get type information
type_info = plugin.type_analyzer.get_type_info("MyClass", "Example.java")

# Find all implementations of an interface
implementations = plugin.type_analyzer.find_implementations("MyInterface")

# Check inheritance
is_subtype = plugin.type_analyzer.is_subtype_of("ArrayList", "List")
```

#### Build System
```python
# Get project dependencies
dependencies = plugin.get_project_dependencies()

# Get project structure
structure = plugin.build_system.get_project_structure()
```

#### Cross-File Analysis
```python
# Get class hierarchy
hierarchy = plugin.get_class_hierarchy("MyClass")

# Get package structure
packages = plugin.get_package_structure()

# Analyze impact of changes
impact = plugin.cross_file_analyzer.analyze_impact("Example.java")
```

## Implementation Details

### File Structure Detection
The plugin automatically detects and indexes Java files in standard project layouts:
- Maven: `src/main/java`, `src/test/java`
- Gradle: `src/main/java`, `src/test/java`
- Generic: `src`, `test`, `tests`

### Symbol Extraction
Extracts the following Java constructs:
- Classes (including nested and inner classes)
- Interfaces
- Enums
- Methods (including constructors)
- Fields
- Annotations

### Type System
- Handles primitive types and their wrappers
- Supports generic types with type parameters
- Tracks type bounds and wildcards
- Resolves fully qualified names

### Performance Considerations
- Lazy loading of analyzers to reduce memory usage
- Caching of parsed results
- Incremental indexing support
- Efficient symbol lookup using SQLite

## Dependencies
- `javalang`: For Java AST parsing
- Standard library: `xml.etree` for Maven POM parsing
- `re`: For Gradle build file parsing

## Limitations
- Gradle parsing uses regex patterns (full Groovy/Kotlin parsing would require additional dependencies)
- External dependency resolution is simplified (full resolution would require Maven/Gradle integration)
- Annotation processing is basic (no compile-time annotation processing)

## Future Enhancements
- Full Gradle build file parsing with Groovy/Kotlin AST
- Maven/Gradle plugin integration for accurate dependency resolution
- JavaDoc parsing and indexing
- Lombok support
- Spring Framework-specific features
- Android-specific constructs