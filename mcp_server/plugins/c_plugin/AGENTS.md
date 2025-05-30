# C Plugin Agent Configuration

## Implementation Status
❌ **STUB IMPLEMENTATION** - This plugin needs full implementation following the Python plugin pattern

## Overview
The C plugin will provide code intelligence for C source files (.c, .h) using Tree-sitter for parsing and language-specific analysis for C features like preprocessor directives, header includes, and type definitions.

## Implementation Requirements

### 1. Tree-sitter Integration
**Grammar**: Use `tree-sitter-c` from tree-sitter-languages
```python
from ...utils.treesitter_wrapper import TreeSitterWrapper
from ...utils.fuzzy_indexer import FuzzyIndexer
from ...storage.sqlite_store import SQLiteStore

class Plugin(IPlugin):
    lang = "c"
    
    def __init__(self, sqlite_store: Optional[SQLiteStore] = None) -> None:
        self._ts = TreeSitterWrapper()
        self._indexer = FuzzyIndexer(sqlite_store=sqlite_store)
        self._sqlite_store = sqlite_store
        self._repository_id = None
        self._preindex()
```

### 2. File Support Implementation
```python
def supports(self, path: str | Path) -> bool:
    """Support .c and .h files"""
    suffixes = {'.c', '.h'}
    return Path(path).suffix.lower() in suffixes
```

### 3. Symbol Extraction
**Target Node Types** (from Tree-sitter C grammar):
- `function_definition` - Function definitions
- `declaration` - Variable and type declarations
- `struct_specifier` - Struct definitions
- `enum_specifier` - Enum definitions
- `type_definition` - Typedef declarations
- `preproc_def` - Macro definitions
- `preproc_function_def` - Function-like macros

**Implementation Strategy**:
```python
def indexFile(self, path: str | Path, content: str) -> IndexShard:
    tree = self._ts._parser.parse(content.encode('utf-8'))
    root = tree.root_node
    
    symbols = []
    
    # Extract functions
    for node in self._find_nodes(root, 'function_definition'):
        declarator = node.child_by_field_name('declarator')
        if declarator and declarator.type == 'function_declarator':
            name_node = declarator.child_by_field_name('declarator')
            # Handle pointer declarators
            while name_node and name_node.type == 'pointer_declarator':
                name_node = name_node.child_by_field_name('declarator')
            
            if name_node and name_node.type == 'identifier':
                name = content[name_node.start_byte:name_node.end_byte]
                signature = self._extract_function_signature(node, content)
                symbols.append({
                    'symbol': name,
                    'kind': 'function',
                    'signature': signature,
                    'line': node.start_point[0] + 1,
                    'span': (node.start_point[0] + 1, node.end_point[0] + 1)
                })
    
    # Extract structs, enums, typedefs
    # ... similar pattern for other node types
```

### 4. C-Specific Features

#### Preprocessor Handling
```python
def _extract_includes(self, root, content):
    """Extract #include directives for dependency tracking"""
    includes = []
    for node in self._find_nodes(root, 'preproc_include'):
        path_node = node.child_by_field_name('path')
        if path_node:
            include_path = content[path_node.start_byte:path_node.end_byte]
            includes.append({
                'path': include_path.strip('"<>'),
                'is_system': include_path.startswith('<'),
                'line': node.start_point[0] + 1
            })
    return includes

def _extract_macros(self, root, content):
    """Extract macro definitions"""
    macros = []
    for node in self._find_nodes(root, ['preproc_def', 'preproc_function_def']):
        name_node = node.child_by_field_name('name')
        if name_node:
            name = content[name_node.start_byte:name_node.end_byte]
            # Extract parameters for function-like macros
            params_node = node.child_by_field_name('parameters')
            signature = f"#define {name}"
            if params_node:
                params = content[params_node.start_byte:params_node.end_byte]
                signature += params
            macros.append({
                'symbol': name,
                'kind': 'macro',
                'signature': signature,
                'line': node.start_point[0] + 1
            })
    return macros
```

#### Type Definitions
```python
def _extract_types(self, root, content):
    """Extract structs, enums, and typedefs"""
    types = []
    
    # Structs
    for node in self._find_nodes(root, 'struct_specifier'):
        name_node = node.child_by_field_name('name')
        if name_node:
            name = content[name_node.start_byte:name_node.end_byte]
            types.append({
                'symbol': name,
                'kind': 'struct',
                'signature': f'struct {name}',
                'line': node.start_point[0] + 1
            })
    
    # Similar for enums and typedefs
    return types
```

### 5. Definition and Reference Finding
```python
def getDefinition(self, symbol: str) -> SymbolDef | None:
    """Find symbol definition using parsed data"""
    # Search through indexed files for exact symbol match
    # Consider:
    # - Function definitions
    # - Type definitions (struct, enum, typedef)
    # - Macro definitions
    # - Global variable declarations
    
    # For header files, check corresponding .c files
    # Handle common patterns like foo.h -> foo.c
    pass

def findReferences(self, symbol: str) -> list[Reference]:
    """Find all references to a symbol"""
    # Search for:
    # - Function calls
    # - Type usage
    # - Macro usage
    # - Variable references
    # Use Tree-sitter to parse and find identifier nodes
    pass
```

### 6. Search Implementation
```python
def search(self, query: str, opts: SearchOpts | None = None) -> list[SearchResult]:
    """Search using fuzzy indexer"""
    limit = opts.get('limit', 20) if opts else 20
    if opts and opts.get('semantic'):
        return []  # Semantic search not supported yet
    return self._indexer.search(query, limit=limit)
```

### 7. SQLite Integration
Follow the Python plugin pattern for storing:
- File metadata with language="c"
- Symbols with appropriate kinds (function, struct, enum, typedef, macro, variable)
- Include relationships as imports
- Symbol signatures including return types and parameters

### 8. Testing Requirements

Create `test_c_plugin.py` with:
```python
def test_supports():
    plugin = Plugin()
    assert plugin.supports("main.c")
    assert plugin.supports("header.h")
    assert plugin.supports("MAIN.C")  # Case insensitive
    assert not plugin.supports("main.cpp")

def test_index_functions():
    plugin = Plugin()
    content = '''
    int add(int a, int b) {
        return a + b;
    }
    
    void* malloc_wrapper(size_t size) {
        return malloc(size);
    }
    '''
    shard = plugin.indexFile("test.c", content)
    assert len(shard['symbols']) == 2
    assert shard['symbols'][0]['symbol'] == 'add'
    assert shard['symbols'][0]['kind'] == 'function'

def test_index_types():
    # Test struct, enum, typedef extraction
    pass

def test_macros():
    # Test macro extraction including function-like macros
    pass
```

## Key Differences from Python Plugin

1. **No Built-in Intelligence**: Unlike Jedi for Python, C requires manual parsing for references
2. **Preprocessor Complexity**: Must handle #include, #define, #ifdef etc.
3. **Header Files**: Need to correlate .h and .c files
4. **Type System**: More complex with pointers, structs, unions
5. **Scope Rules**: Different scoping (file-level static, extern declarations)

## Implementation Priority

1. **Phase 1**: Basic parsing and function extraction
2. **Phase 2**: Type definitions (struct, enum, typedef)
3. **Phase 3**: Preprocessor directives and macros
4. **Phase 4**: Reference finding using Tree-sitter
5. **Phase 5**: Header/source file correlation

## Performance Considerations

- Cache parsed ASTs for header files (frequently included)
- Batch process include dependencies
- Consider memory-mapped files for large codebases
- Implement incremental parsing for file changes