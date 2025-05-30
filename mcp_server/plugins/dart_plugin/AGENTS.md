# Dart Plugin Agent Configuration

## Implementation Status
❌ **STUB IMPLEMENTATION** - This plugin needs full implementation following the Python plugin pattern

## Overview
The Dart plugin will provide code intelligence for Dart source files (.dart) using Tree-sitter for parsing and handling Dart-specific features like null safety, mixins, extension methods, and Flutter widget hierarchies.

## Implementation Requirements

### 1. Tree-sitter Integration
**Grammar**: Use `tree-sitter-dart` from tree-sitter-languages
```python
from ...utils.treesitter_wrapper import TreeSitterWrapper
from ...utils.fuzzy_indexer import FuzzyIndexer
from ...storage.sqlite_store import SQLiteStore

class Plugin(IPlugin):
    lang = "dart"
    
    def __init__(self, sqlite_store: Optional[SQLiteStore] = None) -> None:
        self._ts = TreeSitterWrapper()
        self._indexer = FuzzyIndexer(sqlite_store=sqlite_store)
        self._sqlite_store = sqlite_store
        self._repository_id = None
        self._is_flutter_project = self._detect_flutter()
        self._null_safety_enabled = True  # Default for Dart 2.12+
        self._preindex()
```

### 2. File Support Implementation
```python
def supports(self, path: str | Path) -> bool:
    """Support Dart files"""
    return Path(path).suffix.lower() == '.dart'

def _detect_flutter(self) -> bool:
    """Check if this is a Flutter project"""
    pubspec_path = Path.cwd() / 'pubspec.yaml'
    if pubspec_path.exists():
        content = pubspec_path.read_text()
        return 'flutter:' in content
    return False
```

### 3. Symbol Extraction
**Target Node Types** (from Tree-sitter Dart grammar):
- `class_definition` - Class declarations
- `mixin_declaration` - Mixin declarations
- `function_signature` - Function declarations
- `method_signature` - Method declarations
- `constructor_signature` - Constructor declarations
- `enum_declaration` - Enum declarations
- `extension_declaration` - Extension declarations
- `variable_declaration` - Variable/field declarations
- `import_or_export` - Import/export statements

**Implementation Strategy**:
```python
def indexFile(self, path: str | Path, content: str) -> IndexShard:
    tree = self._ts._parser.parse(content.encode('utf-8'))
    root = tree.root_node
    
    symbols = []
    imports = []
    
    # Extract library/part information
    library_name = self._extract_library_name(root, content)
    
    # Process all top-level declarations
    for child in root.named_children:
        if child.type == 'class_definition':
            self._extract_class(child, content, symbols)
        elif child.type == 'mixin_declaration':
            self._extract_mixin(child, content, symbols)
        elif child.type == 'function_signature':
            self._extract_function(child, content, symbols)
        elif child.type == 'enum_declaration':
            self._extract_enum(child, content, symbols)
        elif child.type == 'extension_declaration':
            self._extract_extension(child, content, symbols)
        elif child.type == 'import_or_export':
            self._extract_import(child, content, imports)
    
    # Store imports in SQLite if available
    if self._sqlite_store and self._repository_id:
        self._store_imports(path, imports)
    
    return {
        'file': str(path),
        'symbols': symbols,
        'language': self.lang,
        'library': library_name,
        'is_flutter': self._is_flutter_project
    }

def _extract_class(self, node, content, symbols):
    """Extract class with constructors, methods, and fields"""
    name_node = node.child_by_field_name('name')
    if not name_node:
        return
    
    class_name = content[name_node.start_byte:name_node.end_byte]
    
    # Check for extends, with, implements
    extends = self._extract_extends(node, content)
    mixins = self._extract_mixins(node, content)
    implements = self._extract_implements(node, content)
    
    # Build signature
    signature_parts = [f'class {class_name}']
    if extends:
        signature_parts.append(f'extends {extends}')
    if mixins:
        signature_parts.append(f'with {', '.join(mixins)}')
    if implements:
        signature_parts.append(f'implements {', '.join(implements)}')
    
    # Check if it's a Flutter widget
    is_widget = self._is_flutter_widget(extends, class_name)
    
    symbols.append({
        'symbol': class_name,
        'kind': 'widget' if is_widget else 'class',
        'signature': ' '.join(signature_parts),
        'line': node.start_point[0] + 1,
        'span': (node.start_point[0] + 1, node.end_point[0] + 1),
        'metadata': {
            'is_abstract': self._is_abstract(node, content),
            'is_widget': is_widget
        }
    })
    
    # Extract class members
    body_node = node.child_by_field_name('body')
    if body_node:
        self._extract_class_members(body_node, content, symbols, class_name)
```

### 4. Dart-Specific Features

#### Null Safety Handling
```python
def _extract_null_safety_info(self, type_node, content):
    """Extract null safety information from types"""
    if not type_node:
        return None, False
    
    type_text = content[type_node.start_byte:type_node.end_byte]
    is_nullable = type_text.endswith('?')
    base_type = type_text.rstrip('?')
    
    return base_type, is_nullable

def _extract_late_variables(self, node, content):
    """Handle late initialization"""
    modifiers = []
    for child in node.children:
        if child.type == 'static' or child.type == 'late' or child.type == 'final':
            modifiers.append(child.type)
    return modifiers
```

#### Mixin and Extension Support
```python
def _extract_mixin(self, node, content, symbols):
    """Extract mixin declaration"""
    name_node = node.child_by_field_name('name')
    if not name_node:
        return
    
    mixin_name = content[name_node.start_byte:name_node.end_byte]
    on_types = self._extract_mixin_on_types(node, content)
    
    signature = f"mixin {mixin_name}"
    if on_types:
        signature += f" on {', '.join(on_types)}"
    
    symbols.append({
        'symbol': mixin_name,
        'kind': 'mixin',
        'signature': signature,
        'line': node.start_point[0] + 1,
        'span': (node.start_point[0] + 1, node.end_point[0] + 1)
    })

def _extract_extension(self, node, content, symbols):
    """Extract extension methods"""
    name_node = node.child_by_field_name('name')
    type_node = node.child_by_field_name('type')
    
    extension_name = content[name_node.start_byte:name_node.end_byte] if name_node else '<unnamed>'
    extended_type = content[type_node.start_byte:type_node.end_byte] if type_node else 'Unknown'
    
    symbols.append({
        'symbol': extension_name,
        'kind': 'extension',
        'signature': f"extension {extension_name} on {extended_type}",
        'line': node.start_point[0] + 1,
        'span': (node.start_point[0] + 1, node.end_point[0] + 1)
    })
    
    # Extract extension methods
    body_node = node.child_by_field_name('body')
    if body_node:
        self._extract_extension_methods(body_node, content, symbols, extension_name, extended_type)
```

#### Async Support (Future/Stream)
```python
def _extract_async_info(self, function_node, content):
    """Extract async/sync*/async* information"""
    for child in function_node.children:
        if child.type == 'function_body':
            for body_child in child.children:
                if body_child.type == 'async':
                    return 'async'
                elif body_child.type == 'sync' and '*' in content[body_child.start_byte:body_child.end_byte + 1]:
                    return 'sync*'
                elif body_child.type == 'async' and '*' in content[body_child.start_byte:body_child.end_byte + 1]:
                    return 'async*'
    return None

def _extract_return_type(self, function_node, content):
    """Extract return type including Future/Stream"""
    type_node = function_node.child_by_field_name('returnType')
    if type_node:
        return_type = content[type_node.start_byte:type_node.end_byte]
        # Check for Future/Stream types
        if 'Future<' in return_type:
            return 'Future', return_type
        elif 'Stream<' in return_type:
            return 'Stream', return_type
        return 'sync', return_type
    return None, 'dynamic'
```

#### Flutter Widget Detection
```python
def _is_flutter_widget(self, extends, class_name):
    """Check if class is a Flutter widget"""
    if not self._is_flutter_project:
        return False
    
    # Check inheritance
    widget_bases = {'StatelessWidget', 'StatefulWidget', 'InheritedWidget', 'RenderObjectWidget'}
    if extends in widget_bases:
        return True
    
    # Check naming convention
    if class_name.endswith('Widget') or class_name.endswith('Page') or class_name.endswith('Screen'):
        return True
    
    return False

def _extract_build_method(self, class_body, content, symbols, class_name):
    """Extract build method for widgets"""
    for member in class_body.named_children:
        if member.type == 'method_signature':
            name_node = member.child_by_field_name('name')
            if name_node and content[name_node.start_byte:name_node.end_byte] == 'build':
                symbols.append({
                    'symbol': f'{class_name}.build',
                    'kind': 'build_method',
                    'signature': 'Widget build(BuildContext context)',
                    'line': member.start_point[0] + 1,
                    'metadata': {'parent_widget': class_name}
                })
```

### 5. Package and Import Resolution
```python
def _extract_import(self, node, content, imports):
    """Extract import/export statements"""
    # Get the URI
    uri_node = node.child_by_field_name('uri')
    if not uri_node:
        return
    
    uri = content[uri_node.start_byte:uri_node.end_byte].strip('"\'')
    
    # Determine import type
    import_type = 'package' if uri.startswith('package:') else 'relative'
    is_dart_core = uri.startswith('dart:')
    
    # Extract show/hide clauses
    show_names = []
    hide_names = []
    for child in node.children:
        if child.type == 'show_clause':
            show_names = self._extract_names_from_clause(child, content)
        elif child.type == 'hide_clause':
            hide_names = self._extract_names_from_clause(child, content)
    
    # Extract as clause
    alias = None
    for child in node.children:
        if child.type == 'as_clause':
            alias_node = child.child_by_field_name('name')
            if alias_node:
                alias = content[alias_node.start_byte:alias_node.end_byte]
    
    imports.append({
        'uri': uri,
        'type': import_type,
        'is_dart_core': is_dart_core,
        'show': show_names,
        'hide': hide_names,
        'alias': alias,
        'line': node.start_point[0] + 1
    })
```

### 6. Type System Support
```python
def _extract_generics(self, node, content):
    """Extract generic type parameters"""
    type_params = []
    
    for child in node.children:
        if child.type == 'type_parameters':
            for param in child.named_children:
                if param.type == 'type_parameter':
                    name_node = param.child_by_field_name('name')
                    if name_node:
                        param_name = content[name_node.start_byte:name_node.end_byte]
                        
                        # Check for bounds
                        bound = None
                        for param_child in param.children:
                            if param_child.type == 'type_bound':
                                bound = content[param_child.start_byte:param_child.end_byte]
                        
                        type_params.append({
                            'name': param_name,
                            'bound': bound
                        })
    
    return type_params
```

### 7. Testing Requirements

Create `test_dart_plugin.py` with:
```python
def test_supports():
    plugin = Plugin()
    assert plugin.supports("main.dart")
    assert plugin.supports("widget.dart")
    assert not plugin.supports("script.js")

def test_class_extraction():
    plugin = Plugin()
    content = '''
    class Animal {
        String name;
        Animal(this.name);
        
        void speak() {
            print('$name makes a sound');
        }
    }
    
    class Dog extends Animal with Barker implements Pet {
        Dog(String name) : super(name);
        
        @override
        void speak() {
            bark();
        }
    }
    '''
    shard = plugin.indexFile("test.dart", content)
    assert any(s['symbol'] == 'Animal' and s['kind'] == 'class' for s in shard['symbols'])
    assert any('extends Animal' in s['signature'] for s in shard['symbols'])

def test_null_safety():
    plugin = Plugin()
    content = '''
    String? nullableString;
    late final int lateInt;
    
    String nonNullable = 'hello';
    
    void processData(String? input) {
        final result = input ?? 'default';
        print(result.length);  // Safe after null check
    }
    '''
    shard = plugin.indexFile("test.dart", content)
    # Should handle nullable types and late modifiers
    assert len(shard['symbols']) >= 3

def test_flutter_widgets():
    plugin = Plugin()
    plugin._is_flutter_project = True  # Mock Flutter detection
    
    content = '''
    import 'package:flutter/material.dart';
    
    class MyHomePage extends StatefulWidget {
        @override
        _MyHomePageState createState() => _MyHomePageState();
    }
    
    class _MyHomePageState extends State<MyHomePage> {
        @override
        Widget build(BuildContext context) {
            return Scaffold(
                appBar: AppBar(title: Text('Home')),
                body: Center(child: Text('Hello')),
            );
        }
    }
    '''
    shard = plugin.indexFile("home_page.dart", content)
    assert any(s['kind'] == 'widget' for s in shard['symbols'])
    assert any(s['kind'] == 'build_method' for s in shard['symbols'])

def test_async_features():
    plugin = Plugin()
    content = '''
    Future<String> fetchData() async {
        await Future.delayed(Duration(seconds: 1));
        return 'data';
    }
    
    Stream<int> countStream() async* {
        for (int i = 0; i < 10; i++) {
            yield i;
        }
    }
    
    Iterable<int> syncGenerator() sync* {
        yield* [1, 2, 3];
    }
    '''
    shard = plugin.indexFile("async.dart", content)
    assert any('Future<String>' in s['signature'] for s in shard['symbols'])
    assert any('Stream<int>' in s['signature'] for s in shard['symbols'])
```

## Key Differences from Other Plugins

1. **Strong Typing**: Dart has a sound type system with null safety
2. **Flutter Framework**: Special handling for widget trees and build methods
3. **Mixins**: Multiple inheritance through mixins
4. **Extension Methods**: Add methods to existing types
5. **Async Generators**: sync* and async* functions
6. **Package System**: pub package manager integration

## Implementation Priority

1. **Phase 1**: Basic class and function extraction
2. **Phase 2**: Null safety and type system support
3. **Phase 3**: Import/export and package resolution
4. **Phase 4**: Mixins and extensions
5. **Phase 5**: Flutter widget detection and analysis
6. **Phase 6**: Full async pattern support

## Performance Considerations

- Cache package resolution (pubspec.lock parsing)
- Skip generated files (*.g.dart, *.freezed.dart)
- Handle part files correctly (part/part of)
- Consider analyzer integration for deeper insights
- Watch for hot reload in Flutter development

## Dart Analyzer Integration (Future)

```python
# Future enhancement: integrate with Dart analyzer
def _get_analyzer_info(self, file_path):
    """Use Dart analyzer for advanced features"""
    # Could provide:
    # - Type inference
    # - Error detection
    # - Quick fixes
    # - Refactoring support
    pass
```