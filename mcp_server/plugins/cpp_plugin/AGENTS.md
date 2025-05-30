# C++ Plugin Agent Configuration

## Implementation Status
❌ **STUB IMPLEMENTATION** - This plugin needs full implementation following the Python plugin pattern

## Overview
The C++ plugin will provide advanced code intelligence for C++ source files (.cpp, .cc, .cxx, .hpp, .h, .hh) using Tree-sitter for parsing and handling complex C++ features like templates, namespaces, and modern C++ constructs.

## Implementation Requirements

### 1. Tree-sitter Integration
**Grammar**: Use `tree-sitter-cpp` from tree-sitter-languages
```python
from ...utils.treesitter_wrapper import TreeSitterWrapper
from ...utils.fuzzy_indexer import FuzzyIndexer
from ...storage.sqlite_store import SQLiteStore

class Plugin(IPlugin):
    lang = "cpp"
    
    def __init__(self, sqlite_store: Optional[SQLiteStore] = None) -> None:
        self._ts = TreeSitterWrapper()
        self._indexer = FuzzyIndexer(sqlite_store=sqlite_store)
        self._sqlite_store = sqlite_store
        self._repository_id = None
        self._namespace_stack = []  # Track current namespace context
        self._preindex()
```

### 2. File Support Implementation
```python
def supports(self, path: str | Path) -> bool:
    """Support C++ source and header files"""
    suffixes = {'.cpp', '.cc', '.cxx', '.c++', '.hpp', '.h', '.hh', '.h++'}
    return Path(path).suffix.lower() in suffixes
```

### 3. Symbol Extraction
**Target Node Types** (from Tree-sitter C++ grammar):
- `function_definition` - Function definitions
- `class_specifier` - Class definitions
- `struct_specifier` - Struct definitions
- `namespace_definition` - Namespace declarations
- `template_declaration` - Template definitions
- `constructor_or_destructor_definition` - Constructors/destructors
- `field_declaration` - Class member variables
- `enum_specifier` - Enum definitions
- `type_alias_declaration` - Using/typedef declarations
- `lambda_expression` - Lambda functions

**Implementation Strategy**:
```python
def indexFile(self, path: str | Path, content: str) -> IndexShard:
    tree = self._ts._parser.parse(content.encode('utf-8'))
    root = tree.root_node
    
    symbols = []
    self._namespace_stack = []
    
    # Walk tree with namespace context
    self._walk_tree(root, content, symbols)
    
    return {
        'file': str(path),
        'symbols': symbols,
        'language': self.lang
    }

def _walk_tree(self, node, content, symbols, depth=0):
    """Walk tree maintaining namespace context"""
    if node.type == 'namespace_definition':
        name_node = node.child_by_field_name('name')
        if name_node:
            namespace = content[name_node.start_byte:name_node.end_byte]
            self._namespace_stack.append(namespace)
        else:
            self._namespace_stack.append('<anonymous>')
    
    # Process node based on type
    if node.type in self._symbol_types:
        symbol = self._extract_symbol(node, content)
        if symbol:
            symbols.append(symbol)
    
    # Recurse to children
    for child in node.named_children:
        self._walk_tree(child, content, symbols, depth + 1)
    
    # Pop namespace on exit
    if node.type == 'namespace_definition':
        self._namespace_stack.pop()
```

### 4. C++-Specific Features

#### Template Handling
```python
def _extract_template_info(self, node, content):
    """Extract template parameters and constraints"""
    template_params = []
    
    # Find template_parameter_list
    for child in node.children:
        if child.type == 'template_parameter_list':
            for param in child.named_children:
                if param.type in ['type_parameter_declaration', 'parameter_declaration']:
                    param_text = content[param.start_byte:param.end_byte]
                    template_params.append(param_text)
    
    return template_params

def _extract_template_symbol(self, node, content):
    """Extract templated class or function"""
    template_node = node.child_by_field_name('declaration')
    if not template_node:
        return None
    
    template_params = self._extract_template_info(node, content)
    
    if template_node.type == 'class_specifier':
        name_node = template_node.child_by_field_name('name')
        if name_node:
            name = content[name_node.start_byte:name_node.end_byte]
            qualified_name = self._get_qualified_name(name)
            return {
                'symbol': qualified_name,
                'kind': 'template_class',
                'signature': f'template<{', '.join(template_params)}> class {name}',
                'line': node.start_point[0] + 1,
                'span': (node.start_point[0] + 1, node.end_point[0] + 1)
            }
```

#### Class Members and Methods
```python
def _extract_class_members(self, class_node, content):
    """Extract methods, constructors, and member variables"""
    members = []
    class_name = self._get_class_name(class_node, content)
    
    body_node = class_node.child_by_field_name('body')
    if not body_node:
        return members
    
    for member in body_node.named_children:
        if member.type == 'access_specifier':
            # Track public/private/protected
            self._current_access = content[member.start_byte:member.end_byte - 1]
        
        elif member.type == 'function_definition':
            # Method definition
            method = self._extract_method(member, content, class_name)
            if method:
                method['access'] = getattr(self, '_current_access', 'private')
                members.append(method)
        
        elif member.type == 'field_declaration':
            # Member variable
            field = self._extract_field(member, content, class_name)
            if field:
                field['access'] = getattr(self, '_current_access', 'private')
                members.append(field)
    
    return members
```

#### Namespace Resolution
```python
def _get_qualified_name(self, name):
    """Get fully qualified name including namespace"""
    if self._namespace_stack:
        return '::'.join(self._namespace_stack) + '::' + name
    return name

def _resolve_using_declarations(self, root, content):
    """Track using declarations for name resolution"""
    using_decls = {}
    
    for node in self._find_nodes(root, 'using_declaration'):
        # Extract what's being imported
        # Handle 'using namespace std;' and 'using std::vector;'
        pass
    
    return using_decls
```

#### Modern C++ Features
```python
def _extract_lambda(self, node, content):
    """Extract lambda expressions"""
    captures = self._extract_lambda_captures(node, content)
    params = self._extract_lambda_params(node, content)
    
    return {
        'symbol': f'<lambda@{node.start_point[0] + 1}>',
        'kind': 'lambda',
        'signature': f'[{captures}]({params}) {{ ... }}',
        'line': node.start_point[0] + 1,
        'span': (node.start_point[0] + 1, node.end_point[0] + 1)
    }

def _extract_auto_function(self, node, content):
    """Handle auto return type deduction"""
    # Extract trailing return type if present
    # Handle decltype(auto)
    pass
```

### 5. Advanced Analysis

#### Overload Resolution
```python
def _group_overloads(self, symbols):
    """Group function overloads together"""
    overload_groups = {}
    
    for symbol in symbols:
        if symbol['kind'] == 'function':
            base_name = symbol['symbol'].split('(')[0]
            if base_name not in overload_groups:
                overload_groups[base_name] = []
            overload_groups[base_name].append(symbol)
    
    return overload_groups
```

#### Inheritance Tracking
```python
def _extract_base_classes(self, class_node, content):
    """Extract base class information"""
    bases = []
    
    for child in class_node.children:
        if child.type == 'base_class_clause':
            for base in child.named_children:
                if base.type == 'base_class_specifier':
                    access = 'private'  # default for class
                    base_name = None
                    
                    for base_child in base.children:
                        if base_child.type in ['public', 'private', 'protected']:
                            access = base_child.type
                        elif base_child.type == 'type_identifier':
                            base_name = content[base_child.start_byte:base_child.end_byte]
                    
                    if base_name:
                        bases.append({
                            'name': base_name,
                            'access': access,
                            'virtual': 'virtual' in content[base.start_byte:base.end_byte]
                        })
    
    return bases
```

### 6. SQLite Integration Extensions

```python
# Store additional C++ metadata
if self._sqlite_store and file_id:
    # Store namespace information
    if symbol.get('namespace'):
        self._sqlite_store.execute(
            "INSERT INTO symbol_metadata (symbol_id, key, value) VALUES (?, ?, ?)",
            (symbol_id, 'namespace', symbol['namespace'])
        )
    
    # Store template information
    if symbol.get('template_params'):
        self._sqlite_store.execute(
            "INSERT INTO symbol_metadata (symbol_id, key, value) VALUES (?, ?, ?)",
            (symbol_id, 'template_params', json.dumps(symbol['template_params']))
        )
    
    # Store inheritance relationships
    for base in symbol.get('base_classes', []):
        self._sqlite_store.execute(
            "INSERT INTO inheritance (derived_symbol_id, base_name, access, is_virtual) VALUES (?, ?, ?, ?)",
            (symbol_id, base['name'], base['access'], base['virtual'])
        )
```

### 7. Testing Requirements

Create `test_cpp_plugin.py` with:
```python
def test_supports():
    plugin = Plugin()
    assert plugin.supports("main.cpp")
    assert plugin.supports("header.hpp")
    assert plugin.supports("source.cc")
    assert not plugin.supports("main.c")

def test_namespace_extraction():
    plugin = Plugin()
    content = '''
    namespace outer {
        namespace inner {
            class MyClass {
                void method();
            };
        }
    }
    '''
    shard = plugin.indexFile("test.cpp", content)
    # Should find outer::inner::MyClass
    assert any(s['symbol'] == 'outer::inner::MyClass' for s in shard['symbols'])

def test_template_extraction():
    plugin = Plugin()
    content = '''
    template<typename T, int N>
    class Array {
        T data[N];
    public:
        T& operator[](int i) { return data[i]; }
    };
    '''
    shard = plugin.indexFile("test.cpp", content)
    # Should extract template class with parameters
    assert any(s['kind'] == 'template_class' for s in shard['symbols'])

def test_modern_cpp_features():
    # Test auto, lambdas, range-based for, etc.
    pass
```

## Key Differences from C Plugin

1. **Namespaces**: Must track and resolve namespace contexts
2. **Templates**: Complex template parameter and specialization handling
3. **Classes**: Multiple inheritance, access specifiers, virtual functions
4. **Overloading**: Function and operator overloading
5. **Modern Features**: Lambdas, auto, move semantics, concepts (C++20)
6. **Name Mangling**: Consider demangling for better display

## Implementation Priority

1. **Phase 1**: Basic parsing (functions, classes, namespaces)
2. **Phase 2**: Template support (basic templates, not specializations)
3. **Phase 3**: Class members and inheritance
4. **Phase 4**: Modern C++ features (lambdas, auto)
5. **Phase 5**: Advanced template features (SFINAE, concepts)
6. **Phase 6**: STL awareness and standard library integration

## Performance Considerations

- C++ files can be very large (especially with templates)
- Cache template instantiations
- Consider partial parsing for header files
- Implement incremental parsing for IDE-like responsiveness
- Use parallel processing for large codebases

## STL and Library Awareness

```python
# Common STL containers to recognize
STL_CONTAINERS = {
    'vector', 'list', 'deque', 'set', 'map', 'unordered_set', 'unordered_map',
    'array', 'forward_list', 'stack', 'queue', 'priority_queue'
}

# Recognize smart pointers
SMART_POINTERS = {'unique_ptr', 'shared_ptr', 'weak_ptr'}
```