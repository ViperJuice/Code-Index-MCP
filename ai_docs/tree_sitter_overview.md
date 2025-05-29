# Tree-sitter Overview

## Introduction
Tree-sitter is a parser generator tool and incremental parsing library that builds a concrete syntax tree for source code and efficiently updates it as the code is edited. It's designed for use in text editors and development tools.

## Key Features

### Core Capabilities
- **Incremental Parsing**: Efficiently updates parse tree on edits
- **Error Recovery**: Produces useful trees even for syntax errors
- **Language Agnostic**: Supports 100+ programming languages
- **Fast Performance**: Written in C, with efficient memory usage
- **Thread Safe**: Can be used from multiple threads

### Why Tree-sitter for MCP Server
- Parse multiple languages with consistent API
- Extract accurate symbol information
- Handle malformed/incomplete code
- Real-time parsing for file watchers
- Efficient memory usage for large codebases

## Installation

### Option 1: Direct Tree-sitter
```bash
pip install tree-sitter
```

### Option 2: Pre-compiled Languages (Recommended)
```bash
pip install tree-sitter-languages
```

## Basic Usage

### Using tree-sitter-languages (Simplified)
```python
from tree_sitter_languages import get_language, get_parser

# Get language and parser
language = get_language('python')
parser = get_parser('python')

# Parse code
tree = parser.parse(b"def hello():\n    print('world')")
root_node = tree.root_node
```

### Manual Setup with py-tree-sitter
```python
from tree_sitter import Language, Parser
import tree_sitter_python as tspython

# Build language library
PY_LANGUAGE = Language(tspython.language())

# Create parser
parser = Parser()
parser.set_language(PY_LANGUAGE)

# Parse code
tree = parser.parse(b"def hello():\n    print('world')")
```

## MCP Server Implementation

### TreeSitter Wrapper Class
```python
from pathlib import Path
import tree_sitter_languages

class TreeSitterWrapper:
    """Wrapper for consistent tree-sitter usage across plugins"""
    
    def __init__(self):
        self._parsers = {}
        self._languages = {}
    
    def get_parser(self, language: str):
        """Get or create parser for language"""
        if language not in self._parsers:
            self._parsers[language] = tree_sitter_languages.get_parser(language)
            self._languages[language] = tree_sitter_languages.get_language(language)
        return self._parsers[language], self._languages[language]
    
    def parse(self, content: bytes, language: str):
        """Parse content and return root node"""
        parser, _ = self.get_parser(language)
        tree = parser.parse(content)
        return tree.root_node
    
    def parse_file(self, path: Path, language: str):
        """Parse file and return root node"""
        content = path.read_bytes()
        return self.parse(content, language)
```

## Working with Parse Trees

### Node Properties
```python
# Basic node properties
node.type           # Node type (e.g., 'function_definition')
node.start_point    # (row, column) tuple
node.end_point      # (row, column) tuple
node.start_byte     # Byte offset in source
node.end_byte       # Byte offset in source
node.text           # Node text content (bytes)

# Tree navigation
node.parent         # Parent node
node.children       # List of child nodes
node.child_count    # Number of children
node.named_children # Only named children

# Named fields
node.child_by_field_name('name')  # Get specific field
node.field_name_for_child(0)      # Field name of child
```

### Tree Walking
```python
def walk_tree(node, callback, depth=0):
    """Recursively walk parse tree"""
    callback(node, depth)
    for child in node.children:
        walk_tree(child, callback, depth + 1)

# Example: Find all functions
def find_functions(node):
    functions = []
    
    def visitor(node, depth):
        if node.type == 'function_definition':
            name_node = node.child_by_field_name('name')
            if name_node:
                functions.append({
                    'name': name_node.text.decode('utf-8'),
                    'line': node.start_point[0] + 1,
                    'node': node
                })
    
    walk_tree(node, visitor)
    return functions
```

## Query System

### Pattern Matching with Queries
```python
# Define query for Python functions
FUNCTION_QUERY = """
(function_definition
  name: (identifier) @function.name
  parameters: (parameters) @function.params
  body: (block) @function.body) @function.def

(class_definition
  name: (identifier) @class.name
  body: (block) @class.body) @class.def
"""

# Execute query
language = get_language('python')
query = language.query(FUNCTION_QUERY)

# Get captures
tree = parser.parse(source_code)
captures = query.captures(tree.root_node)

# Process captures
for node, name in captures:
    if name == 'function.name':
        print(f"Function: {node.text.decode('utf-8')}")
    elif name == 'class.name':
        print(f"Class: {node.text.decode('utf-8')}")
```

### Query Predicates
```python
# Query with predicates
ASYNC_FUNCTION_QUERY = """
(
  (function_definition
    name: (identifier) @function.name) @function.def
  (#match? @function.def "^async")
)
"""
```

## Language-Specific Parsing

### Python Plugin Example
```python
class PythonPlugin(IPlugin):
    def __init__(self, tree_sitter: TreeSitterWrapper):
        self.tree_sitter = tree_sitter
        self.language = 'python'
    
    def index_file(self, file_path: Path) -> IndexShard:
        root = self.tree_sitter.parse_file(file_path, self.language)
        symbols = []
        
        # Extract symbols
        for node in self._find_definitions(root):
            symbol = self._node_to_symbol(node, file_path)
            symbols.append(symbol)
        
        return IndexShard(
            file_path=str(file_path),
            symbols=symbols,
            language=self.language
        )
    
    def _find_definitions(self, root):
        """Find all symbol definitions"""
        query = self.tree_sitter.get_language(self.language).query("""
            (function_definition) @function
            (class_definition) @class
            (assignment
              left: (identifier) @variable)
        """)
        
        for node, capture in query.captures(root):
            yield node
```

## Incremental Parsing

### Efficient Updates
```python
class IncrementalParser:
    def __init__(self, language: str):
        self.parser = get_parser(language)
        self.trees = {}  # file_path -> tree
    
    def parse_file(self, file_path: Path):
        content = file_path.read_bytes()
        old_tree = self.trees.get(file_path)
        
        if old_tree:
            # Reuse old tree for faster parsing
            new_tree = self.parser.parse(content, old_tree)
        else:
            new_tree = self.parser.parse(content)
        
        self.trees[file_path] = new_tree
        return new_tree
    
    def update_file(self, file_path: Path, edits: List[Edit]):
        """Apply edits and reparse incrementally"""
        tree = self.trees[file_path]
        
        # Apply edits to tree
        for edit in edits:
            tree.edit(
                start_byte=edit.start_byte,
                old_end_byte=edit.old_end_byte,
                new_end_byte=edit.new_end_byte,
                start_point=edit.start_point,
                old_end_point=edit.old_end_point,
                new_end_point=edit.new_end_point
            )
        
        # Reparse with edited tree
        content = file_path.read_bytes()
        new_tree = self.parser.parse(content, tree)
        self.trees[file_path] = new_tree
        return new_tree
```

## Error Handling

### Parsing Errors
```python
def parse_with_errors(content: bytes, language: str):
    """Parse and collect syntax errors"""
    parser = get_parser(language)
    tree = parser.parse(content)
    
    errors = []
    
    def find_errors(node):
        if node.type == 'ERROR' or node.is_missing:
            errors.append({
                'type': 'syntax_error',
                'location': node.start_point,
                'text': node.text.decode('utf-8', errors='ignore')
            })
        for child in node.children:
            find_errors(child)
    
    find_errors(tree.root_node)
    return tree, errors
```

## Performance Optimization

### Caching Parsers
```python
class ParserCache:
    """Thread-safe parser cache"""
    def __init__(self):
        self._cache = {}
        self._lock = threading.Lock()
    
    def get_parser(self, language: str):
        with self._lock:
            if language not in self._cache:
                self._cache[language] = {
                    'parser': get_parser(language),
                    'language': get_language(language)
                }
            return self._cache[language]
```

### Batch Processing
```python
async def batch_parse_files(files: List[Path], language: str):
    """Parse multiple files efficiently"""
    parser = get_parser(language)
    results = []
    
    for file_path in files:
        try:
            content = await aiofiles.read(file_path, 'rb')
            tree = parser.parse(content)
            results.append((file_path, tree))
        except Exception as e:
            logger.error(f"Failed to parse {file_path}: {e}")
    
    return results
```

## Supported Languages for MCP

Tree-sitter-languages includes support for:
- Python
- JavaScript/TypeScript
- C/C++
- Java
- Go
- Rust
- Ruby
- HTML/CSS
- JSON/YAML
- And 100+ more languages

## Best Practices

1. **Use tree-sitter-languages**: Avoids compilation issues
2. **Cache parsers**: Create once, reuse many times
3. **Handle encoding**: Tree-sitter works with bytes, decode carefully
4. **Use queries**: More maintainable than manual traversal
5. **Error recovery**: Tree-sitter continues parsing after errors
6. **Incremental parsing**: Use for real-time updates
7. **Memory management**: Trees are reference counted

## Integration Notes

For MCP Server:
- Central TreeSitterWrapper manages all parsers
- Each plugin uses wrapper for consistent parsing
- File watcher uses incremental parsing
- Query system extracts symbols efficiently
- Error nodes help with incomplete code