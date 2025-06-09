# Go Plugin for MCP Server

The Go plugin provides comprehensive code analysis and indexing capabilities for Go programming language projects. It extends the base plugin functionality with Go-specific features like module resolution, package analysis, and interface satisfaction checking.

## Features

### 1. Module Resolution
- Parses `go.mod` files to understand module dependencies
- Resolves import paths to their actual locations
- Handles module replacements and local modules
- Distinguishes between standard library, external, and internal imports

### 2. Package Analysis
- Analyzes Go packages to extract type information
- Tracks package imports and dependencies
- Identifies exported symbols (types, functions, constants, variables)
- Maintains relationships between packages

### 3. Interface Satisfaction Checking
- Checks if types implement specific interfaces
- Tracks method implementations
- Identifies missing methods for interface compliance
- Supports embedded types and interfaces

### 4. Go Tools Integration
- Integrates with `go doc` for enhanced symbol information
- Can leverage `guru` or `gopls` for advanced analysis (when available)

### 5. Cross-File Reference Tracking
- Tracks symbol usage across multiple files
- Handles qualified references (e.g., `package.Symbol`)
- Supports method references and type assertions

## Architecture

### Core Components

1. **GoModuleResolver** (`module_resolver.py`)
   - Parses and manages go.mod files
   - Resolves import paths
   - Tracks module dependencies and replacements

2. **GoPackageAnalyzer** (`package_analyzer.py`)
   - Analyzes package structure
   - Extracts type definitions, interfaces, and functions
   - Tracks package-level exports

3. **GoInterfaceChecker** (`interface_checker.py`)
   - Verifies interface implementations
   - Handles embedded types and method promotion
   - Generates interface implementation reports

4. **Plugin** (`plugin.py`)
   - Main plugin class inheriting from `PluginWithSemanticSearch`
   - Coordinates all Go-specific analysis
   - Provides API for code indexing and searching

## Usage

### Basic Initialization

```python
from mcp_server.plugins.go_plugin import Plugin as GoPlugin
from mcp_server.storage.sqlite_store import SQLiteStore

# Create plugin instance
sqlite_store = SQLiteStore("code_index.db")
go_plugin = GoPlugin(sqlite_store=sqlite_store, enable_semantic=True)
```

### Indexing Go Files

```python
# Index a single file
with open("main.go", "r") as f:
    content = f.read()
    shard = go_plugin.indexFile("main.go", content)
    
# The shard contains extracted symbols
for symbol in shard['symbols']:
    print(f"{symbol['kind']}: {symbol['symbol']} at line {symbol['line']}")
```

### Module Information

```python
# Get current module information
module_info = go_plugin.get_module_info()
if module_info:
    print(f"Module: {module_info['name']}")
    print(f"Go version: {module_info['version']}")
    for dep in module_info['dependencies']:
        print(f"Dependency: {dep['module']} {dep['version']}")
```

### Package Analysis

```python
# Analyze a package
package_info = go_plugin.get_package_info("internal/handlers")
if package_info:
    print(f"Package: {package_info['name']}")
    print(f"Exports: {package_info['exports']}")
    print(f"Interfaces: {package_info['interfaces']}")
```

### Interface Checking

```python
# Check if a type implements an interface
result = go_plugin.check_interface_implementation("MyHandler", "http.Handler")
if result:
    print(f"Implements interface: {result['satisfied']}")
    if result['missing_methods']:
        print(f"Missing methods: {result['missing_methods']}")
```

### Symbol Search

```python
# Find symbol definition
definition = go_plugin.getDefinition("MyFunction")
if definition:
    print(f"Found at {definition['defined_in']}:{definition['line']}")
    print(f"Signature: {definition['signature']}")

# Find references
refs = go_plugin.findReferences("MyType")
for ref in refs:
    print(f"Referenced at {ref.file}:{ref.line}")

# Fuzzy search
results = go_plugin.search("Handler", {"limit": 10})
for result in results:
    print(f"{result['file']}:{result['line']} - {result['snippet']}")
```

## Go-Specific Symbol Types

The plugin recognizes and indexes the following Go constructs:

- **Types**: struct, interface, type aliases
- **Functions**: standalone functions, methods
- **Variables**: package-level variables, constants
- **Interfaces**: method signatures, embedded interfaces
- **Imports**: standard library, external packages, internal modules

## Integration with Tree-Sitter

The plugin uses tree-sitter for accurate Go parsing with the following query:

```scheme
(function_declaration name: (identifier) @function)
(method_declaration name: (field_identifier) @method)
(type_declaration (type_spec name: (type_identifier) @type))
(const_declaration (const_spec name: (identifier) @constant))
(var_declaration (var_spec name: (identifier) @variable))
(interface_type (method_spec name: (field_identifier) @interface_method))
```

## Performance Considerations

- **Pre-indexing**: The plugin pre-indexes all Go files on initialization
- **Caching**: Package analysis results are cached to avoid re-parsing
- **Incremental Updates**: Only modified files are re-indexed
- **Parallel Processing**: Large projects can benefit from parallel indexing

## Limitations

1. **Build Tags**: Currently doesn't handle build tags comprehensively
2. **Generated Code**: May not distinguish between generated and hand-written code
3. **Vendored Dependencies**: Limited support for vendor directories
4. **CGO**: C code in CGO files is not analyzed

## Future Enhancements

- Integration with `gopls` language server for richer analysis
- Support for Go workspaces (go.work files)
- Advanced type inference and flow analysis
- Build tag awareness
- Test coverage integration