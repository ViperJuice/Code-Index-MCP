# SmartParser System Guide

## Overview

The SmartParser system is a flexible parsing framework that intelligently selects between different parser backends based on availability and performance characteristics. This system provides a unified interface for parsing code across multiple languages while allowing fallback between different implementations.

## Key Features

- **Multiple Backend Support**: Supports tree-sitter and Python AST backends
- **Automatic Fallback**: Automatically selects the best available backend
- **Backend Switching**: Runtime switching between different backends
- **Language Support**: Extensible to support multiple programming languages
- **Backward Compatibility**: Maintains compatibility with existing code

## Architecture

### Components

1. **SmartParser**: Main class that manages backend selection and parsing
2. **IParserBackend**: Protocol defining the interface for parser backends
3. **TreeSitterBackend**: Tree-sitter based parser implementation
4. **ASTBackend**: Python AST based parser (Python-only)

### Backend Selection Logic

1. Tree-sitter is preferred for its rich feature set and multi-language support
2. AST backend is available as a fallback for Python
3. Custom backends can be specified via the `preferred_backend` parameter

## Usage

### Basic Usage

```python
from mcp_server.utils.smart_parser import SmartParser

# Initialize parser for Python
parser = SmartParser('python')

# Parse code
code = b"def hello(): print('Hello, world!')"
ast = parser.parse(code)

# Get current backend info
print(f"Using backend: {parser.get_backend_name()}")
print(f"Available backends: {parser.available_backends}")
```

### Plugin Integration

The Python plugin has been updated to use SmartParser:

```python
from mcp_server.plugins.python_plugin.plugin import Plugin

# Initialize plugin (automatically uses SmartParser)
plugin = Plugin()

# Get parser information
info = plugin.get_parser_info()
print(f"Current backend: {info['current_backend']}")

# Switch backends
if 'ast' in info['available_backends']:
    plugin.switch_parser_backend('ast')
```

### Backend Switching

```python
# Initialize with preferred backend
parser = SmartParser('python', preferred_backend='ast')

# Switch backends at runtime
parser.switch_backend('tree-sitter')
```

## Backend Differences

### Tree-sitter Backend
- **Pros**: 
  - Supports multiple languages
  - Provides detailed AST with byte positions
  - Fast and memory-efficient
- **Cons**:
  - May only capture top-level definitions
  - Requires native dependencies

### AST Backend (Python only)
- **Pros**:
  - Built into Python standard library
  - Captures all definitions including nested ones
  - No external dependencies
- **Cons**:
  - Python-only
  - Different AST format than tree-sitter

## Extending SmartParser

### Adding a New Backend

1. Create a class implementing the backend interface:

```python
class MyCustomBackend:
    def __init__(self):
        self.name = "custom"
        self.supported_languages = {"python", "javascript"}
    
    def parse(self, content: bytes, language: str):
        # Your parsing logic here
        pass
    
    def is_available(self) -> bool:
        # Check if backend is available
        return True
```

2. Register the backend in SmartParser's `_initialize_backends` method

### Adding Language Support

To add support for a new language:

1. Update the `language_map` in TreeSitterBackend
2. Ensure the tree-sitter grammar is available
3. Update plugin symbol extraction logic if needed

## Migration Guide

### Updating Existing Plugins

1. Replace TreeSitterWrapper import:
```python
# Old
from ...utils.treesitter_wrapper import TreeSitterWrapper

# New
from ...utils.smart_parser import SmartParser
```

2. Update initialization:
```python
# Old
self._ts = TreeSitterWrapper()

# New
self._parser = SmartParser('python')
```

3. Update parsing calls:
```python
# Old
tree = self._ts._parser.parse(content.encode("utf-8"))
root = tree.root_node

# New
root = self._parser.parse(content.encode("utf-8"))
```

4. Add backend-specific logic if needed:
```python
if self._parser.get_backend_name() == "tree-sitter":
    # Tree-sitter specific logic
elif self._parser.get_backend_name() == "ast":
    # AST specific logic
```

## Best Practices

1. **Error Handling**: Always wrap parse operations in try-except blocks
2. **Logging**: Use logging to track which backend is being used
3. **Testing**: Test with different backends to ensure compatibility
4. **Performance**: Profile different backends for your use case

## Example: Complete Implementation

See `examples/demo_smart_parser.py` for a complete demonstration of SmartParser features including:
- Backend initialization
- Parsing with different backends
- Backend switching
- Symbol extraction comparison

## Future Enhancements

1. **Additional Backends**: Support for other parsers (Babel, regex-based, etc.)
2. **Performance Metrics**: Built-in performance tracking and comparison
3. **Caching**: Backend-specific caching strategies
4. **Parallel Parsing**: Support for parallel parsing with different backends
5. **Language Detection**: Automatic language detection and parser selection