# Python Plugin Agent Configuration

## Implementation Status
✅ **FULLY IMPLEMENTED** - One of 48 production-ready language plugins

## Overview
The Python plugin is a fully implemented specialized language plugin (one of 13 specialized plugins). It uses Tree-sitter for parsing with Jedi for advanced Python intelligence features and semantic search capabilities.

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

## ESSENTIAL_COMMANDS

```bash
# Test Python Plugin Directly
python -c "from mcp_server.plugins.python_plugin.plugin import Plugin; p = Plugin(); print('Plugin loaded successfully')"

# Test Tree-sitter Python Parsing
python -c "from mcp_server.utils.treesitter_wrapper import TreeSitterWrapper; ts = TreeSitterWrapper(); print(ts.parse_file('test.py', 'def hello(): pass'))"

# Test via Gateway API
curl "http://localhost:8000/symbol?symbol_name=parse&file_path=mcp_server/gateway.py"
curl "http://localhost:8000/search?query=def%20parse&limit=10"

# Test Jedi Integration
python -c "import jedi; script = jedi.Script(code='def test(): pass\ntest()', path='test.py'); print([d.name for d in script.get_names()])"

# Plugin Testing
pytest tests/test_python_plugin.py -v
```

## CODE_STYLE_PREFERENCES

```python
# Python Plugin Implementation Pattern
from mcp_server.plugin_base import PluginBase
from mcp_server.utils.treesitter_wrapper import TreeSitterWrapper
from mcp_server.utils.fuzzy_indexer import FuzzyIndexer
import jedi

class Plugin(PluginBase):
    lang = "python"
    
    # Tree-sitter node types for Python
    TARGET_NODES = ["function_definition", "class_definition"]
    
    # File extensions handled
    EXTENSIONS = [".py", ".pyi"]
    
    # Return structured data
    def getDefinition(self, symbol: str) -> Dict:
        return {
            "symbol": symbol,
            "file": file_path,
            "line": line_number,
            "signature": function_signature
        }
```

## ARCHITECTURAL_PATTERNS

```python
# Python Plugin Architecture
class Plugin(PluginBase):
    lang = "python"                    # Language identifier
    
    def __init__(self):
        self._ts = TreeSitterWrapper()      # Tree-sitter parsing
        self._indexer = FuzzyIndexer()      # Text search capabilities
        self._preindex()                    # Pre-index all Python files
    
    # Core Plugin Interface (PluginBase)
    def index(self, file_path: str) -> Dict
    def getDefinition(self, symbol: str, context: Dict) -> Dict  
    def getReferences(self, symbol: str, context: Dict) -> List[Dict]
    def search(self, query: str, options: Dict) -> List[Dict]

# Integration Pattern
# Tree-sitter: Fast parsing, syntax tree extraction
# Jedi: Advanced Python intelligence (definitions, references)
# FuzzyIndexer: Text-based search across files
```

## CODE_STYLE_PREFERENCES

```python
# Python Plugin follows project standards:
# - Type hints for all function parameters and returns
# - Docstrings for all public methods
# - Error handling with structured responses
# - Tree-sitter node traversal patterns

# Interface Method Implementation
def getDefinition(self, file_path: str, line: int, column: int) -> Dict[str, Any]:
    """Get definition for symbol at position."""
    try:
        # Use Jedi for accurate definition lookup
        script = jedi.Script(source=source, line=line, column=column, path=file_path)
        definitions = script.goto(follow_imports=True)
        return {"status": "success", "definitions": [d.to_dict() for d in definitions]}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Tree-sitter Pattern
def _extract_symbols(self, tree):
    """Extract symbols using Tree-sitter traversal."""
    symbols = []
    for node in tree.root_node.children:
        if node.type in ["function_definition", "class_definition"]:
            symbols.append(self._node_to_symbol(node))
    return symbols
```

## ARCHITECTURAL_PATTERNS

```python
# Plugin Architecture: Inherits from PluginBase
from mcp_server.plugin_base import PluginBase

class Plugin(PluginBase):
    lang = "python"  # Language identifier
    
    def __init__(self, sqlite_store=None):
        self._ts = TreeSitterWrapper()  # Tree-sitter integration
        self._indexer = FuzzyIndexer()  # Search functionality
        self._preindex()  # Auto-index on startup

# Tree-sitter Integration Pattern
def _parse_with_treesitter(self, content: str) -> Tree:
    """Standard Tree-sitter parsing pattern."""
    return self._ts.parse(content.encode('utf-8'))

# Jedi Integration Pattern  
def _get_jedi_definitions(self, source: str, line: int, column: int):
    """Standard Jedi definition lookup pattern."""
    script = jedi.Script(source=source, line=line, column=column)
    return script.goto(follow_imports=True)

# Error Handling Pattern
def safe_operation(self, operation_name: str) -> Dict[str, Any]:
    """Consistent error handling across plugin methods."""
    try:
        result = self._perform_operation()
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"Python plugin {operation_name} failed: {e}")
        return {"status": "error", "message": str(e)}
```

## NAMING_CONVENTIONS

```python
# Plugin Structure
mcp_server/plugins/python_plugin/
├── __init__.py
├── plugin.py              # Main Plugin class
└── AGENTS.md             # This file

# Class and Method Names
class Plugin(PluginBase):    # Main plugin class always named "Plugin"
def getDefinition()          # camelCase for interface methods
def findReferences()         # camelCase for interface methods
def _preindex()             # snake_case for internal methods

# Node Types (Tree-sitter)
"function_definition"        # Tree-sitter grammar names
"class_definition" 
"import_statement"
```

## DEVELOPMENT_ENVIRONMENT

```bash
# Python Dependencies (from requirements.txt)
# tree-sitter>=0.20.0
# tree-sitter-languages>=1.8.0  # Auto-installs Python grammar
# jedi>=0.19.0                   # Python intelligence

# Test Python Environment
python -c "import tree_sitter; print('Tree-sitter available')"
python -c "import jedi; print('Jedi available')"
python -c "from tree_sitter_languages import get_language; print('Python grammar:', get_language('python'))"

# Plugin Development Workflow
# 1. Edit plugin.py
# 2. Test with: python -m mcp_server.plugins.python_plugin.plugin
# 3. Run pytest tests/test_python_plugin.py
# 4. Test via gateway API endpoints
```

## TEAM_SHARED_PRACTICES

```python
# Python Plugin as Reference Implementation
# Use this plugin as template for other language plugins
# Follow established patterns:
# - Tree-sitter for parsing
# - Language-specific intelligence library (like Jedi for Python)
# - FuzzyIndexer for text search
# - Structured return formats

# Performance Considerations:
# - Pre-index files on startup (_preindex method)
# - Cache parsed tree-sitter results
# - Use Jedi Script.get_names() for bulk operations
# - Limit file size during indexing

# Error Handling:
# - Graceful degradation when Jedi fails
# - Handle corrupted or incomplete Python files
# - Return empty results rather than exceptions
```

## Code Structure

```python
class Plugin(PluginBase):
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