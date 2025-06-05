# Rust Plugin Agent Instructions

## Overview
This is the Rust language plugin for the Code Index MCP server. It provides comprehensive parsing and indexing capabilities for Rust source code files.

## Plugin Capabilities

### Supported File Types
- `.rs` files (Rust source code)

### Symbol Types Extracted
- **Functions**: `fn` declarations with parameters and return types
- **Structs**: `struct` definitions with generic parameters
- **Enums**: `enum` definitions with variants
- **Traits**: `trait` definitions and implementations
- **Implementation blocks**: `impl` blocks for types and traits
- **Modules**: `mod` declarations
- **Constants**: `const` declarations
- **Static variables**: `static` declarations
- **Type aliases**: `type` declarations
- **Use statements**: `use` imports

### Performance
- Target: Parse Rust files within 100ms
- Current performance: ~1ms for typical files
- Achieves 60-100x better than target performance

### Parsing Strategy
The plugin uses a dual-mode parsing approach:

1. **Primary**: Tree-sitter based parsing (when compatible version available)
2. **Fallback**: Regex-based parsing (when tree-sitter has version conflicts)

Both modes provide comprehensive symbol extraction with similar accuracy.

### Features
- **Visibility Detection**: Extracts `pub`, `pub(crate)`, and private visibility
- **Documentation Extraction**: Parses `///` doc comments
- **Generic Parameters**: Handles generic type parameters
- **Trait Implementations**: Distinguishes trait implementations from inherent implementations
- **Module Structure**: Tracks module organization
- **Import Analysis**: Parses use statements and imported symbols

### Error Handling
- Graceful degradation on invalid Rust syntax
- Robust error handling for file system issues
- Comprehensive logging for debugging

### Storage Integration
- **SQLite Support**: Stores symbols and metadata when SQLite backend is available
- **Fuzzy Search**: Integrates with fuzzy indexer for fast text search
- **Caching**: Maintains in-memory cache for frequently accessed files

## Technical Implementation

### Dependencies
- `tree_sitter_rust`: Primary parsing backend
- `tree_sitter`: AST parsing framework
- `re`: Regex fallback parsing
- `pathlib`: File system operations

### Architecture
```
Plugin
├── Tree-sitter Parser (when available)
├── Regex Fallback Parser
├── Symbol Extractors (per construct type)
├── SQLite Integration
├── Fuzzy Indexer Integration
└── Cache Management
```

### Performance Optimizations
- Pre-indexing of project files during initialization
- In-memory caching of parsed results
- Efficient regex patterns for fallback mode
- Minimal file I/O operations

## Agent Notes

### Development Guidelines
1. **Maintain Performance**: All changes must preserve <100ms parsing target
2. **Error Resilience**: Code must handle malformed Rust gracefully
3. **Comprehensive Coverage**: Support all major Rust language constructs
4. **Documentation**: Keep symbol extraction accurate and complete

### Testing Strategy
- Unit tests for each symbol type
- Performance benchmarks for various file sizes
- Integration tests with SQLite backend
- Error handling verification

### Future Enhancements
- Integration with rust-analyzer for advanced type resolution
- Semantic analysis for better reference finding
- Cross-crate symbol resolution
- Macro expansion support

### Maintenance
- Monitor tree-sitter version compatibility
- Update regex patterns for new Rust syntax
- Performance regression testing
- Documentation accuracy validation

## Usage Examples

```python
from mcp_server.plugins.rust_plugin.plugin import Plugin

# Create plugin instance
plugin = Plugin()

# Index a Rust file
shard = plugin.indexFile("src/main.rs", rust_code)

# Find symbol definition
definition = plugin.getDefinition("MyStruct")

# Find references
references = plugin.findReferences("my_function")

# Search for patterns
results = plugin.search("Calculator")
```

## Integration Points

### MCP Server Integration
- Registered as "rust" language plugin
- Supports all standard IPlugin interface methods
- Compatible with plugin manager lifecycle

### Storage Backends
- SQLite: Full symbol storage with metadata
- Fuzzy Indexer: Fast text-based search
- File Cache: In-memory parsing cache

### Transport Protocols
- Works with all MCP transport mechanisms
- JSON-RPC compatible symbol definitions
- Streaming search results support