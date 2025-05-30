# JavaScript Plugin Agent Configuration

## Implementation Status
❌ **STUB IMPLEMENTATION** - This plugin needs full implementation following the Python plugin pattern

## Overview
The JavaScript plugin will provide code intelligence for JavaScript/ECMAScript files (.js, .mjs, .jsx) using Tree-sitter for parsing and handling modern JavaScript features including ES6+ syntax, modules, async/await, and JSX.

## Implementation Requirements

### 1. Tree-sitter Integration
**Grammar**: Use `tree-sitter-javascript` from tree-sitter-languages
```python
from ...utils.treesitter_wrapper import TreeSitterWrapper
from ...utils.fuzzy_indexer import FuzzyIndexer
from ...storage.sqlite_store import SQLiteStore

class Plugin(IPlugin):
    lang = "js"
    
    def __init__(self, sqlite_store: Optional[SQLiteStore] = None) -> None:
        self._ts = TreeSitterWrapper()
        self._indexer = FuzzyIndexer(sqlite_store=sqlite_store)
        self._sqlite_store = sqlite_store
        self._repository_id = None
        self._scope_stack = []  # Track scope for closures
        self._module_type = None  # 'commonjs' or 'esm'
        self._preindex()
```

### 2. File Support Implementation
```python
def supports(self, path: str | Path) -> bool:
    """Support JavaScript and JSX files"""
    suffixes = {'.js', '.mjs', '.jsx', '.es6', '.es'}
    return Path(path).suffix.lower() in suffixes
```

### 3. Symbol Extraction
**Target Node Types** (from Tree-sitter JavaScript grammar):
- `function_declaration` - Named function declarations
- `function_expression` - Function expressions
- `arrow_function` - Arrow functions
- `class_declaration` - Class declarations
- `class_expression` - Class expressions
- `method_definition` - Class methods
- `variable_declaration` - var/let/const declarations
- `assignment_expression` - Property assignments
- `export_statement` - Export declarations
- `import_statement` - Import declarations

**Implementation Strategy**:
```python
def indexFile(self, path: str | Path, content: str) -> IndexShard:
    tree = self._ts._parser.parse(content.encode('utf-8'))
    root = tree.root_node
    
    # Detect module type
    self._module_type = self._detect_module_type(root, content)
    
    symbols = []
    imports = []
    exports = []
    
    # Extract all symbols
    self._extract_symbols(root, content, symbols, imports, exports)
    
    # Store module information if SQLite available
    if self._sqlite_store and self._repository_id:
        self._store_module_info(path, imports, exports)
    
    return {
        'file': str(path),
        'symbols': symbols,
        'language': self.lang,
        'module_type': self._module_type
    }

def _extract_symbols(self, node, content, symbols, imports, exports, scope_path=[]):
    """Recursively extract symbols with scope tracking"""
    
    # Function declarations
    if node.type == 'function_declaration':
        name_node = node.child_by_field_name('name')
        if name_node:
            name = content[name_node.start_byte:name_node.end_byte]
            params = self._extract_parameters(node, content)
            is_async = self._is_async_function(node, content)
            
            symbols.append({
                'symbol': name,
                'kind': 'function',
                'signature': f"{'async ' if is_async else ''}function {name}({params})",
                'line': node.start_point[0] + 1,
                'span': (node.start_point[0] + 1, node.end_point[0] + 1),
                'scope': '.'.join(scope_path)
            })
    
    # Arrow functions assigned to variables
    elif node.type == 'variable_declaration':
        for declarator in self._find_nodes(node, 'variable_declarator'):
            name_node = declarator.child_by_field_name('name')
            value_node = declarator.child_by_field_name('value')
            
            if name_node and value_node:
                name = content[name_node.start_byte:name_node.end_byte]
                
                if value_node.type == 'arrow_function':
                    params = self._extract_parameters(value_node, content)
                    is_async = self._is_async_function(value_node, content)
                    
                    symbols.append({
                        'symbol': name,
                        'kind': 'arrow_function',
                        'signature': f"{'async ' if is_async else ''}const {name} = ({params}) => {{}}",
                        'line': node.start_point[0] + 1,
                        'span': (node.start_point[0] + 1, value_node.end_point[0] + 1)
                    })
                else:
                    # Regular variable
                    kind = self._get_declaration_kind(node, content)
                    symbols.append({
                        'symbol': name,
                        'kind': 'variable',
                        'signature': f"{kind} {name}",
                        'line': node.start_point[0] + 1
                    })
    
    # Classes
    elif node.type == 'class_declaration':
        name_node = node.child_by_field_name('name')
        if name_node:
            name = content[name_node.start_byte:name_node.end_byte]
            superclass = self._extract_superclass(node, content)
            
            symbols.append({
                'symbol': name,
                'kind': 'class',
                'signature': f"class {name}{' extends ' + superclass if superclass else ''}",
                'line': node.start_point[0] + 1,
                'span': (node.start_point[0] + 1, node.end_point[0] + 1)
            })
            
            # Extract class methods
            body_node = node.child_by_field_name('body')
            if body_node:
                new_scope = scope_path + [name]
                for child in body_node.named_children:
                    self._extract_symbols(child, content, symbols, imports, exports, new_scope)
    
    # Continue recursion for other nodes
    for child in node.named_children:
        self._extract_symbols(child, content, symbols, imports, exports, scope_path)
```

### 4. JavaScript-Specific Features

#### Module System Handling
```python
def _detect_module_type(self, root, content):
    """Detect CommonJS vs ES Modules"""
    # Check for ES module syntax
    for node in root.named_children:
        if node.type in ['import_statement', 'export_statement']:
            return 'esm'
    
    # Check for CommonJS
    if 'require(' in content or 'module.exports' in content:
        return 'commonjs'
    
    return 'unknown'

def _extract_imports(self, root, content):
    """Extract import statements"""
    imports = []
    
    # ES6 imports
    for node in self._find_nodes(root, 'import_statement'):
        source_node = node.child_by_field_name('source')
        if source_node:
            source = content[source_node.start_byte:source_node.end_byte].strip('"\'')
            
            # Extract imported names
            imported_names = []
            for child in node.named_children:
                if child.type == 'import_specifier':
                    name_node = child.child_by_field_name('name')
                    if name_node:
                        imported_names.append(content[name_node.start_byte:name_node.end_byte])
            
            imports.append({
                'source': source,
                'names': imported_names,
                'line': node.start_point[0] + 1,
                'type': 'esm'
            })
    
    # CommonJS requires
    for node in self._find_nodes(root, 'call_expression'):
        if self._is_require_call(node, content):
            arg_node = node.child_by_field_name('arguments')
            if arg_node and arg_node.named_child_count > 0:
                source_node = arg_node.named_children[0]
                if source_node.type == 'string':
                    source = content[source_node.start_byte:source_node.end_byte].strip('"\'')
                    imports.append({
                        'source': source,
                        'line': node.start_point[0] + 1,
                        'type': 'commonjs'
                    })
    
    return imports

def _extract_exports(self, root, content):
    """Extract export statements"""
    exports = []
    
    # ES6 exports
    for node in self._find_nodes(root, 'export_statement'):
        declaration = node.child_by_field_name('declaration')
        if declaration:
            if declaration.type == 'function_declaration':
                name_node = declaration.child_by_field_name('name')
                if name_node:
                    exports.append({
                        'name': content[name_node.start_byte:name_node.end_byte],
                        'kind': 'function',
                        'line': node.start_point[0] + 1
                    })
    
    return exports
```

#### Object and Property Extraction
```python
def _extract_object_methods(self, node, content, object_name=None):
    """Extract methods from object literals"""
    methods = []
    
    if node.type == 'object':
        for prop in node.named_children:
            if prop.type == 'pair':
                key_node = prop.child_by_field_name('key')
                value_node = prop.child_by_field_name('value')
                
                if key_node and value_node:
                    key = content[key_node.start_byte:key_node.end_byte].strip('"\'')
                    
                    if value_node.type in ['function_expression', 'arrow_function']:
                        methods.append({
                            'symbol': f"{object_name}.{key}" if object_name else key,
                            'kind': 'method',
                            'signature': f"{key}: function",
                            'line': prop.start_point[0] + 1
                        })
            elif prop.type == 'method_definition':
                # ES6 method shorthand
                name_node = prop.child_by_field_name('name')
                if name_node:
                    name = content[name_node.start_byte:name_node.end_byte]
                    methods.append({
                        'symbol': f"{object_name}.{name}" if object_name else name,
                        'kind': 'method',
                        'signature': f"{name}()",
                        'line': prop.start_point[0] + 1
                    })
    
    return methods
```

#### Async/Promise Handling
```python
def _is_async_function(self, node, content):
    """Check if function is async"""
    # Check for async keyword
    for child in node.children:
        if child.type == 'async' or (child.type == 'identifier' and 
            content[child.start_byte:child.end_byte] == 'async'):
            return True
    return False

def _extract_promise_chains(self, node, content):
    """Extract .then() and .catch() chains"""
    chains = []
    
    if node.type == 'call_expression':
        member = node.child_by_field_name('function')
        if member and member.type == 'member_expression':
            property = member.child_by_field_name('property')
            if property:
                prop_name = content[property.start_byte:property.end_byte]
                if prop_name in ['then', 'catch', 'finally']:
                    chains.append({
                        'type': prop_name,
                        'line': node.start_point[0] + 1
                    })
    
    return chains
```

#### JSX Support
```python
def _extract_jsx_components(self, node, content):
    """Extract React/JSX components"""
    components = []
    
    # Function components
    if node.type == 'function_declaration':
        name_node = node.child_by_field_name('name')
        if name_node:
            name = content[name_node.start_byte:name_node.end_byte]
            # Check if it returns JSX
            if self._returns_jsx(node, content) and name[0].isupper():
                components.append({
                    'symbol': name,
                    'kind': 'react_component',
                    'signature': f"function {name}(props)",
                    'line': node.start_point[0] + 1
                })
    
    return components

def _returns_jsx(self, function_node, content):
    """Check if function returns JSX"""
    # Look for JSX elements in return statements
    for node in self._walk_tree(function_node):
        if node.type == 'return_statement':
            for child in node.named_children:
                if child.type in ['jsx_element', 'jsx_fragment']:
                    return True
    return False
```

### 5. Scope and Closure Analysis
```python
def _analyze_scope(self, node, content, parent_scope=None):
    """Analyze variable scope and closures"""
    scope = {
        'type': node.type,
        'variables': [],
        'parent': parent_scope,
        'line': node.start_point[0] + 1
    }
    
    # Track variable declarations in this scope
    for child in node.named_children:
        if child.type == 'variable_declaration':
            for declarator in self._find_nodes(child, 'variable_declarator'):
                name_node = declarator.child_by_field_name('name')
                if name_node:
                    var_name = content[name_node.start_byte:name_node.end_byte]
                    scope['variables'].append({
                        'name': var_name,
                        'kind': self._get_declaration_kind(child, content),
                        'line': child.start_point[0] + 1
                    })
    
    return scope
```

### 6. Testing Requirements

Create `test_js_plugin.py` with:
```python
def test_supports():
    plugin = Plugin()
    assert plugin.supports("app.js")
    assert plugin.supports("component.jsx")
    assert plugin.supports("module.mjs")
    assert not plugin.supports("script.ts")

def test_function_extraction():
    plugin = Plugin()
    content = '''
    function regularFunction(a, b) {
        return a + b;
    }
    
    const arrowFunction = (x, y) => x * y;
    
    async function asyncFunction() {
        await something();
    }
    
    const asyncArrow = async () => {
        return await fetch('/api');
    };
    '''
    shard = plugin.indexFile("test.js", content)
    assert len(shard['symbols']) == 4
    assert any(s['kind'] == 'arrow_function' for s in shard['symbols'])
    assert any('async' in s['signature'] for s in shard['symbols'])

def test_class_extraction():
    plugin = Plugin()
    content = '''
    class Animal {
        constructor(name) {
            this.name = name;
        }
        
        speak() {
            console.log(`${this.name} makes a sound`);
        }
    }
    
    class Dog extends Animal {
        bark() {
            console.log('Woof!');
        }
    }
    '''
    shard = plugin.indexFile("test.js", content)
    assert any(s['symbol'] == 'Animal' and s['kind'] == 'class' for s in shard['symbols'])
    assert any('extends Animal' in s['signature'] for s in shard['symbols'])

def test_module_detection():
    plugin = Plugin()
    
    # ES Modules
    esm_content = '''
    import { useState } from 'react';
    export default function App() {}
    '''
    shard = plugin.indexFile("app.js", esm_content)
    assert shard['module_type'] == 'esm'
    
    # CommonJS
    cjs_content = '''
    const express = require('express');
    module.exports = { startServer };
    '''
    shard = plugin.indexFile("server.js", cjs_content)
    assert shard['module_type'] == 'commonjs'

def test_jsx_components():
    plugin = Plugin()
    content = '''
    function Button({ onClick, children }) {
        return <button onClick={onClick}>{children}</button>;
    }
    
    const Card = (props) => (
        <div className="card">
            {props.children}
        </div>
    );
    '''
    shard = plugin.indexFile("components.jsx", content)
    # Should detect React components
    assert any(s['kind'] == 'react_component' for s in shard['symbols'])
```

## Key Differences from Python Plugin

1. **Dynamic Typing**: No static type information, rely on naming conventions
2. **Multiple Module Systems**: Handle both CommonJS and ES Modules
3. **Prototype-based OOP**: Different from class-based inheritance
4. **Scope Complexity**: var/let/const have different scoping rules
5. **Async Patterns**: Callbacks, promises, async/await
6. **JSX**: Special syntax for React components

## Implementation Priority

1. **Phase 1**: Basic function and variable extraction
2. **Phase 2**: ES6 classes and arrow functions
3. **Phase 3**: Module import/export handling
4. **Phase 4**: Object methods and properties
5. **Phase 5**: JSX and React component detection
6. **Phase 6**: Async/await and promise chains

## Performance Considerations

- JavaScript files can be very large (bundled files)
- Consider skipping minified files (detect by line length)
- Cache module resolution results
- Handle dynamic imports and code splitting
- Watch for circular dependencies

## Framework Detection

```python
def _detect_framework(self, content, imports):
    """Detect common JavaScript frameworks"""
    frameworks = []
    
    # React
    if any('react' in imp['source'] for imp in imports):
        frameworks.append('react')
    
    # Vue
    if 'vue' in content or '.vue' in str(self.current_file):
        frameworks.append('vue')
    
    # Angular
    if '@angular' in content:
        frameworks.append('angular')
    
    return frameworks
```