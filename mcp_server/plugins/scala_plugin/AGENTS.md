# Scala Plugin Agent Instructions

## Overview
This plugin provides comprehensive support for Scala 2 and Scala 3 codebases, including functional programming patterns, object-oriented designs, and popular frameworks like Akka, Play, and Apache Spark.

## Key Features

### Language Support
- **Scala 2 & 3**: Full support for both major versions
- **File Types**: `.scala`, `.sc` (Scala scripts), `.sbt` (build files)
- **Tree-sitter**: Optional enhanced parsing when available

### Symbol Types
- **Classes**: Regular, case, sealed, abstract, final
- **Traits**: Including self-types and mixins
- **Objects**: Singleton and companion objects
- **Functions**: Methods, vals, vars, lazy vals
- **Types**: Type aliases, opaque types (Scala 3)
- **Implicits**: Implicit vals, defs, classes
- **Givens**: Scala 3 given instances and using clauses
- **Extensions**: Scala 3 extension methods

### Framework Detection
- **Akka**: Actors, FSM, supervision strategies
- **Play Framework**: Controllers, actions, filters
- **Apache Spark**: RDDs, DataFrames, Datasets, jobs
- **SBT**: Dependencies, settings, tasks, plugins

## Usage Patterns

### Basic Indexing
```python
# Index a Scala file
result = plugin.indexFile("MyApp.scala", content)

# The result includes:
# - All symbols with their types and locations
# - Package and import information
# - Framework-specific constructs
```

### Symbol Search
```python
# Find a class definition
definition = plugin.getDefinition("UserService")

# Find all references to a trait
refs = plugin.findReferences("Monad")

# Search for patterns
results = plugin.search("implicit.*Ordering")
```

### Build File Analysis
```python
# Index build.sbt
result = plugin.indexFile("build.sbt", sbt_content)

# Extracts:
# - Project settings (name, version, scala version)
# - Dependencies with versions
# - Custom tasks and commands
# - SBT plugins
```

## Implementation Details

### Parser Strategy
1. **Tree-sitter First**: Uses Tree-sitter when available for accurate parsing
2. **Regex Fallback**: Comprehensive regex patterns for all Scala constructs
3. **Hybrid Approach**: Combines both for maximum coverage

### Scala 3 Support
- Enum classes with pattern matching
- Union and intersection types
- Given/using context parameters
- Extension methods
- Opaque type aliases
- Export clauses
- New control structures (if-then, while-do)

### Performance Optimizations
- Pre-indexes all Scala files on initialization
- Caches parsed results
- Efficient symbol lookup using SQLite when available
- Fuzzy search for quick pattern matching

## Best Practices

### For Maintainers
1. Keep regex patterns in sync with Scala language evolution
2. Test against both Scala 2.13 and Scala 3.x code
3. Update framework patterns as APIs change
4. Maintain backward compatibility

### For Users
1. Ensure proper file extensions for accurate detection
2. Use specific symbol names for better search results
3. Leverage framework-specific searches (e.g., finding all actors)
4. Index build files for dependency management

## Testing
The plugin includes comprehensive test cases covering:
- Functional programming patterns
- Object-oriented designs
- Scala 3 features
- Framework-specific code
- Build file parsing

Run tests with: `pytest tests/test_scala_plugin.py`

## Future Enhancements
- [ ] Semantic analysis using Metals LSP
- [ ] Cross-compilation support detection
- [ ] Macro annotation parsing
- [ ] Improved implicit resolution tracking
- [ ] Integration with Scala.js and Scala Native