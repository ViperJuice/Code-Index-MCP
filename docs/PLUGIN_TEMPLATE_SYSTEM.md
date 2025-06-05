# Plugin Template System

This document describes the comprehensive plugin template system for creating new language plugins in the MCP Server. The system provides multiple base classes and utilities to support different parsing approaches and common plugin functionality.

## Overview

The plugin template system consists of:

1. **Core Template Classes** - Base classes for different parsing approaches
2. **Utility Classes** - Common functionality and helpers
3. **Plugin Generator** - Automated plugin scaffolding
4. **Testing Infrastructure** - Comprehensive test templates

## Core Template Classes

### LanguagePluginBase

The main base class that all language plugins should inherit from. It provides:

- **Configuration Management** - Plugin-specific settings and behavior
- **Caching Integration** - Automatic caching of parsed results
- **Error Handling** - Graceful error handling and fallback mechanisms
- **Performance Optimization** - Async processing and batching
- **Storage Integration** - SQLite persistence and fuzzy indexing

```python
from mcp_server.plugins import LanguagePluginBase, SymbolType, PluginConfig

class MyLanguagePlugin(LanguagePluginBase):
    def get_language(self) -> str:
        return "mylang"
    
    def get_supported_extensions(self) -> List[str]:
        return [".ml", ".mylang"]
    
    def get_symbol_patterns(self) -> Dict[SymbolType, str]:
        return {
            SymbolType.FUNCTION: r"func\s+(\w+)",
            SymbolType.CLASS: r"class\s+(\w+)"
        }
```

### TreeSitterPluginBase

Specialized base class for plugins that use Tree-sitter for parsing:

- **Tree-sitter Integration** - Optimized Tree-sitter parser management
- **AST Traversal** - Advanced tree traversal and query capabilities
- **Node Analysis** - Extract symbols, scopes, and relationships
- **Language Queries** - Support for Tree-sitter query language

```python
from mcp_server.plugins import TreeSitterPluginBase

class MyTreeSitterPlugin(TreeSitterPluginBase):
    def get_node_types(self) -> Dict[SymbolType, List[str]]:
        return {
            SymbolType.FUNCTION: ["function_definition", "method_definition"],
            SymbolType.CLASS: ["class_definition"]
        }
    
    def get_query_patterns(self) -> Dict[str, str]:
        return {
            "functions": """
                (function_definition
                  name: (identifier) @name) @function
            """
        }
```

### RegexPluginBase

Specialized base class for plugins that use regular expressions:

- **Pattern Management** - Compile and manage regex patterns
- **Multi-line Support** - Handle complex multi-line constructs
- **Context Extraction** - Extract docstrings, comments, and metadata
- **Validation** - Symbol name and pattern validation

```python
from mcp_server.plugins import RegexPluginBase, RegexPattern

class MyRegexPlugin(RegexPluginBase):
    def get_regex_patterns(self) -> List[RegexPattern]:
        return [
            RegexPattern(
                pattern=r"func\s+(\w+)\s*\(",
                symbol_type=SymbolType.FUNCTION,
                name_group=1,
                signature_group=0
            )
        ]
```

### HybridPluginBase

Combines Tree-sitter parsing with regex fallback:

- **Intelligent Fallback** - Automatically switch between parsing methods
- **Performance Tracking** - Monitor parsing success rates
- **Result Combination** - Merge and deduplicate symbols from both approaches
- **Threshold Configuration** - Customize fallback behavior

```python
from mcp_server.plugins import HybridPluginBase

class MyHybridPlugin(HybridPluginBase):
    def get_tree_sitter_node_types(self) -> Dict[SymbolType, List[str]]:
        return {SymbolType.FUNCTION: ["function_definition"]}
    
    def get_regex_patterns(self) -> List[RegexPattern]:
        return [
            RegexPattern(
                pattern=r"func\s+(\w+)",
                symbol_type=SymbolType.FUNCTION,
                name_group=1
            )
        ]
    
    def get_fallback_threshold(self) -> float:
        return 0.3  # Fallback if Tree-sitter finds < 30% expected symbols
```

## Symbol Types and Data Structures

### SymbolType Enum

Standard symbol types across languages:

```python
class SymbolType(Enum):
    FUNCTION = "function"
    CLASS = "class"
    INTERFACE = "interface"
    STRUCT = "struct"
    ENUM = "enum"
    VARIABLE = "variable"
    CONSTANT = "constant"
    MODULE = "module"
    NAMESPACE = "namespace"
    IMPORT = "import"
    TYPE = "type"
    FIELD = "field"
    METHOD = "method"
    PROPERTY = "property"
    DECORATOR = "decorator"
    ANNOTATION = "annotation"
    COMMENT = "comment"
    UNKNOWN = "unknown"
```

### ParsedSymbol

Standardized symbol representation:

```python
@dataclass
class ParsedSymbol:
    name: str
    symbol_type: SymbolType
    line: int
    column: int = 0
    end_line: int = 0
    end_column: int = 0
    signature: Optional[str] = None
    docstring: Optional[str] = None
    scope: Optional[str] = None
    modifiers: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### PluginConfig

Configuration for plugin behavior:

```python
@dataclass
class PluginConfig:
    # Cache settings
    enable_caching: bool = True
    cache_ttl: int = 3600
    max_cache_size: int = 1000
    
    # Performance settings
    async_processing: bool = True
    max_file_size: int = 10 * 1024 * 1024
    batch_size: int = 100
    
    # Parser settings
    preferred_backend: Optional[str] = None
    enable_fallback: bool = True
    strict_mode: bool = False
    
    # Feature flags
    enable_semantic_analysis: bool = True
    enable_cross_references: bool = True
    enable_documentation_extraction: bool = True
```

## Utility Classes

### SymbolExtractor

Common symbol extraction patterns:

```python
from mcp_server.plugins import SymbolExtractor

# Extract function signatures
signatures = SymbolExtractor.extract_function_signatures(content, "python")

# Extract class names
classes = SymbolExtractor.extract_class_names(content, "java")

# Filter symbols by type
functions = SymbolExtractor.filter_symbols_by_type(symbols, [SymbolType.FUNCTION])

# Deduplicate symbols
unique_symbols = SymbolExtractor.deduplicate_symbols(symbols)
```

### FileAnalyzer

File analysis utilities:

```python
from mcp_server.plugins import FileAnalyzer

# Estimate code complexity
complexity = FileAnalyzer.estimate_complexity(content)

# Detect language from content
language = FileAnalyzer.detect_language_from_content(content)

# Get comprehensive file stats
stats = FileAnalyzer.get_file_stats(file_path)
```

### PluginCache

High-performance caching:

```python
from mcp_server.plugins import PluginCache

cache = PluginCache(max_size=1000, ttl=3600)
cache.set("key", "value")
result = cache.get("key")
```

### AsyncPluginHelper

Async processing utilities:

```python
from mcp_server.plugins import AsyncPluginHelper

# Process files in batches
results = await AsyncPluginHelper.process_files_batch(
    files, processor_func, batch_size=10, max_concurrent=5
)

# Process with timeout
result = await AsyncPluginHelper.process_with_timeout(
    async_operation(), timeout=30.0, default_result=None
)
```

## Plugin Generator

The plugin generator creates complete plugin scaffolding:

### Command Line Usage

```bash
# Generate a hybrid plugin for Swift
python -m mcp_server.plugins.plugin_generator swift swift \
    --extensions .swift .playground \
    --type hybrid \
    --description "Swift language plugin with Tree-sitter and regex support" \
    --author "Your Name"

# Generate a regex-only plugin for a custom language
python -m mcp_server.plugins.plugin_generator mylang mylang \
    --extensions .ml .mylang \
    --type regex \
    --function-pattern "func\s+(\w+)" \
    --class-pattern "class\s+(\w+)" \
    --variable-pattern "var\s+(\w+)"
```

### Programmatic Usage

```python
from mcp_server.plugins import PluginGenerator, PluginSpec, PluginType

spec = PluginSpec(
    name="kotlin",
    language="kotlin",
    extensions=[".kt", ".kts"],
    plugin_type=PluginType.HYBRID,
    description="Kotlin language plugin",
    function_pattern=r"fun\s+(\w+)",
    class_pattern=r"class\s+(\w+)",
    function_nodes=["function_declaration"],
    class_nodes=["class_declaration"]
)

generator = PluginGenerator(output_dir=Path("./plugins"))
plugin_dir = generator.generate_plugin(spec)
```

### Generated Files

The generator creates:

- **plugin.py** - Main plugin implementation
- **__init__.py** - Package initialization
- **test_[name]_plugin.py** - Comprehensive test suite
- **README.md** - Complete documentation
- **plugin_config.json** - Configuration file
- **test_data/** - Sample files for testing

## Performance Features

### Caching

- **Automatic Caching** - Results cached by content hash
- **TTL Support** - Time-based cache expiration
- **Size Limits** - LRU eviction when cache is full
- **Cache Warming** - Pre-populate cache for performance

### Async Processing

- **Batch Processing** - Process multiple files concurrently
- **Timeout Handling** - Prevent hanging operations
- **Resource Limits** - Control memory and CPU usage
- **Progress Tracking** - Monitor processing status

### Error Handling

- **Graceful Degradation** - Fallback mechanisms for parsing failures
- **Error Recovery** - Continue processing after errors
- **Detailed Logging** - Comprehensive error reporting
- **Validation** - Input and output validation

## Testing Infrastructure

### Test Templates

Generated plugins include comprehensive tests:

```python
class TestMyLanguagePlugin:
    def test_supports_files(self):
        """Test file support detection."""
        
    def test_parse_simple_code(self):
        """Test parsing simple code."""
        
    def test_symbol_extraction(self):
        """Test symbol extraction."""
        
    def test_get_definition(self):
        """Test symbol definition lookup."""
        
    def test_search_functionality(self):
        """Test search functionality."""
```

### Test Data

- **Sample Files** - Representative code examples
- **Complex Examples** - Multi-file, nested structures
- **Edge Cases** - Malformed code, edge conditions
- **Performance Tests** - Large file handling

## Integration Guide

### Adding to MCP Server

1. **Generate Plugin**:
   ```bash
   python -m mcp_server.plugins.plugin_generator mylang mylang \
       --extensions .ml --type hybrid
   ```

2. **Customize Implementation**:
   - Add language-specific patterns
   - Implement Tree-sitter queries
   - Add custom symbol extraction logic

3. **Test Plugin**:
   ```bash
   pytest mylang_plugin/test_mylang_plugin.py
   ```

4. **Register Plugin**:
   ```python
   # In plugin registry
   from mylang_plugin import Plugin as MyLangPlugin
   
   registry.register(MyLangPlugin(), metadata)
   ```

### Configuration

Each plugin can be configured via JSON:

```json
{
  "plugin": {
    "name": "mylang",
    "enabled": true,
    "priority": 1
  },
  "features": {
    "caching": true,
    "async_processing": true,
    "semantic_analysis": true
  },
  "performance": {
    "max_file_size": 10485760,
    "cache_ttl": 3600,
    "batch_size": 100
  }
}
```

## Best Practices

### Plugin Development

1. **Start with Hybrid** - Use HybridPluginBase for maximum reliability
2. **Test Thoroughly** - Use generated test templates as starting point
3. **Handle Errors** - Implement proper error handling and fallbacks
4. **Optimize Performance** - Use caching and async processing
5. **Document Patterns** - Clearly document regex patterns and node types

### Pattern Design

1. **Specific Patterns** - Make regex patterns as specific as possible
2. **Named Groups** - Use named groups for clarity
3. **Multi-line Support** - Handle multi-line constructs properly
4. **Context Aware** - Extract surrounding context when possible

### Testing Strategy

1. **Unit Tests** - Test individual methods and patterns
2. **Integration Tests** - Test full parsing pipeline
3. **Performance Tests** - Test with large files
4. **Edge Cases** - Test malformed and unusual code

## Advanced Features

### Custom Symbol Types

Define language-specific symbol types:

```python
class MyLanguageSymbolType(SymbolType):
    PROTOCOL = "protocol"
    EXTENSION = "extension"
    OPERATOR = "operator"
```

### Cross-Reference Analysis

Extract symbol relationships:

```python
def extract_cross_references(self, content: str, file_path: str) -> List[Dict[str, Any]]:
    """Extract cross-references between symbols."""
    # Implementation for finding symbol usage
```

### Semantic Analysis

Add semantic understanding:

```python
def resolve_type(self, symbol: str, context: Dict[str, Any]) -> Optional[str]:
    """Resolve the type of a symbol."""
    # Implementation for type resolution
```

### Custom Metrics

Track plugin-specific metrics:

```python
def get_plugin_metrics(self) -> Dict[str, Any]:
    """Get plugin-specific metrics."""
    return {
        "parsing_accuracy": self._calculate_accuracy(),
        "symbol_coverage": self._calculate_coverage(),
        "performance_score": self._calculate_performance()
    }
```

## Migration Guide

### From Simple Plugins

1. Inherit from appropriate base class
2. Implement required abstract methods
3. Add configuration support
4. Enable caching and async processing
5. Add comprehensive error handling

### From Manual Implementation

1. Replace custom parsing with base classes
2. Use standardized symbol representation
3. Integrate with caching system
4. Add proper test coverage
5. Use utility functions for common operations

## Troubleshooting

### Common Issues

1. **Import Errors** - Ensure all dependencies are available
2. **Pattern Failures** - Test regex patterns with various inputs
3. **Performance Issues** - Enable caching and optimize patterns
4. **Memory Usage** - Monitor file size limits and batch processing

### Debugging

1. **Enable Logging** - Use debug logging for troubleshooting
2. **Test Individual Methods** - Test parsing methods in isolation
3. **Profile Performance** - Use timing decorators and metrics
4. **Validate Symbols** - Use PluginValidator for symbol validation

## Future Enhancements

### Planned Features

1. **Language Server Protocol** - LSP integration for advanced features
2. **Incremental Parsing** - Update only changed portions
3. **Machine Learning** - ML-based symbol classification
4. **Distributed Processing** - Scale across multiple workers
5. **Visual Debugging** - GUI tools for pattern development

### Extension Points

1. **Custom Backends** - Add new parsing backends
2. **Analysis Plugins** - Extend with analysis capabilities
3. **Export Formats** - Support additional output formats
4. **Integration Hooks** - Connect with external tools

This plugin template system provides a comprehensive foundation for creating robust, performant, and maintainable language plugins for the MCP Server.