# Python Plugin Agent Configuration

## Implementation Status
✅ **FULLY IMPLEMENTED** - This is the ONLY working plugin in the system

## Overview
The Python plugin is the only fully implemented language plugin. It uses Tree-sitter for parsing (NOT the Python AST module) and Jedi for advanced Python intelligence features.

## Actual Implementation

### What It Does
- **Parsing**: Uses Tree-sitter to parse Python files
- **Indexing**: Extracts top-level functions and classes only
- **Symbol Lookup**: Uses Jedi to find symbol definitions
- **Reference Finding**: Uses Jedi to find all references to symbols
- **Search**: Fuzzy text search across all Python files
- **Pre-indexing**: Automatically indexes all .py files on startup

### What It Does NOT Do
- Does NOT use Python's AST module
- Does NOT index variables or nested definitions
- Does NOT resolve imports
- Does NOT extract detailed type information
- Does NOT support semantic/embedding-based search
- Does NOT cache parsed results
- Does NOT handle decorators, metaclasses, or advanced Python features

## Code Structure

```python
class Plugin(IPlugin):
    lang = "python"
    
    def __init__(self):
        self._ts = TreeSitterWrapper()  # Tree-sitter parser
        self._indexer = FuzzyIndexer()  # Text search
        self._preindex()  # Index all .py files
    
    def indexFile(self, path, content):
        # Parses with Tree-sitter
        # Extracts only function_definition and class_definition nodes
        # Returns simple signatures like "def foo(...):"
    
    def getDefinition(self, symbol):
        # Uses Jedi to find symbol definitions
        # Searches all .py files in the project
    
    def findReferences(self, symbol):
        # Uses Jedi to find references
        # Returns list of file+line locations
    
    def search(self, query, opts):
        # Uses FuzzyIndexer for text search
        # Returns empty list for semantic search
```

## Limitations

1. **Limited Symbol Types**: Only indexes functions and classes at the top level
2. **Simple Signatures**: Extracts basic signatures without parameters
3. **No Caching**: Re-parses files on every operation
4. **No Import Analysis**: Cannot resolve imports or dependencies
5. **Basic Error Handling**: Silently skips files with errors

## Dependencies
- `jedi`: For Python code intelligence
- `TreeSitterWrapper`: Internal utility for Tree-sitter parsing
- `FuzzyIndexer`: Internal utility for text search

## Testing
Test with `test_python_plugin.py` to verify basic functionality.