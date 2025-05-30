# HTML/CSS Plugin Agent Configuration

## Implementation Status
❌ **STUB IMPLEMENTATION** - This plugin needs full implementation following the Python plugin pattern

## Overview
The HTML/CSS plugin will provide code intelligence for HTML (.html, .htm) and CSS (.css, .scss, .sass, .less) files using Tree-sitter for parsing. It will track DOM structure, CSS selectors, style definitions, and the relationships between HTML elements and their styles.

## Implementation Requirements

### 1. Tree-sitter Integration
**Grammars**: Use `tree-sitter-html` and `tree-sitter-css` from tree-sitter-languages
```python
from ...utils.treesitter_wrapper import TreeSitterWrapper
from ...utils.fuzzy_indexer import FuzzyIndexer
from ...storage.sqlite_store import SQLiteStore

class Plugin(IPlugin):
    lang = "html_css"
    
    def __init__(self, sqlite_store: Optional[SQLiteStore] = None) -> None:
        self._ts = TreeSitterWrapper()
        self._indexer = FuzzyIndexer(sqlite_store=sqlite_store)
        self._sqlite_store = sqlite_store
        self._repository_id = None
        
        # Separate parsers for HTML and CSS
        self._html_parser = None
        self._css_parser = None
        
        # Track relationships between HTML and CSS
        self._style_index = {}  # selector -> styles mapping
        self._id_index = {}     # id -> elements mapping
        self._class_index = {}  # class -> elements mapping
        
        self._preindex()
```

### 2. File Support Implementation
```python
def supports(self, path: str | Path) -> bool:
    """Support HTML and CSS files including preprocessors"""
    html_suffixes = {'.html', '.htm', '.xhtml'}
    css_suffixes = {'.css', '.scss', '.sass', '.less', '.styl'}
    suffix = Path(path).suffix.lower()
    return suffix in html_suffixes or suffix in css_suffixes

def _get_file_type(self, path: Path) -> str:
    """Determine if file is HTML or CSS"""
    suffix = path.suffix.lower()
    if suffix in {'.html', '.htm', '.xhtml'}:
        return 'html'
    elif suffix in {'.css', '.scss', '.sass', '.less', '.styl'}:
        return 'css'
    return 'unknown'
```

### 3. HTML Symbol Extraction
**Target Node Types** (from Tree-sitter HTML grammar):
- `element` - HTML elements
- `start_tag` - Opening tags
- `end_tag` - Closing tags
- `attribute` - Element attributes
- `attribute_name` - Attribute names
- `attribute_value` - Attribute values
- `text` - Text content
- `script_element` - Script tags
- `style_element` - Style tags

**Implementation Strategy**:
```python
def _index_html_file(self, path: Path, content: str) -> dict:
    """Parse and index HTML file"""
    tree = self._html_parser.parse(content.encode('utf-8'))
    root = tree.root_node
    
    symbols = []
    elements_by_id = {}
    elements_by_class = {}
    inline_styles = []
    
    # Walk the DOM tree
    self._walk_html_tree(root, content, symbols, elements_by_id, elements_by_class, inline_styles)
    
    # Extract embedded CSS from <style> tags
    style_elements = self._find_nodes(root, 'style_element')
    for style_elem in style_elements:
        css_content = self._extract_element_content(style_elem, content)
        if css_content:
            embedded_styles = self._parse_css_content(css_content, path, style_elem.start_point[0] + 1)
            symbols.extend(embedded_styles)
    
    return {
        'symbols': symbols,
        'elements_by_id': elements_by_id,
        'elements_by_class': elements_by_class,
        'inline_styles': inline_styles
    }

def _walk_html_tree(self, node, content, symbols, elements_by_id, elements_by_class, inline_styles, path=[]):
    """Recursively walk HTML tree extracting information"""
    if node.type == 'element':
        # Extract tag name
        start_tag = node.child_by_field_name('start_tag')
        if start_tag:
            tag_name = self._extract_tag_name(start_tag, content)
            
            # Extract attributes
            attributes = self._extract_attributes(start_tag, content)
            
            # Track IDs
            if 'id' in attributes:
                element_id = attributes['id']
                elements_by_id[element_id] = {
                    'tag': tag_name,
                    'line': node.start_point[0] + 1,
                    'path': '/'.join(path + [tag_name]),
                    'attributes': attributes
                }
                
                symbols.append({
                    'symbol': f'#{element_id}',
                    'kind': 'id',
                    'signature': f'<{tag_name} id="{element_id}">',
                    'line': node.start_point[0] + 1
                })
            
            # Track classes
            if 'class' in attributes:
                classes = attributes['class'].split()
                for class_name in classes:
                    if class_name not in elements_by_class:
                        elements_by_class[class_name] = []
                    elements_by_class[class_name].append({
                        'tag': tag_name,
                        'line': node.start_point[0] + 1,
                        'path': '/'.join(path + [tag_name])
                    })
                    
                    symbols.append({
                        'symbol': f'.{class_name}',
                        'kind': 'class',
                        'signature': f'<{tag_name} class="...{class_name}...">',
                        'line': node.start_point[0] + 1
                    })
            
            # Track inline styles
            if 'style' in attributes:
                inline_styles.append({
                    'element': tag_name,
                    'id': attributes.get('id'),
                    'classes': attributes.get('class', '').split(),
                    'styles': attributes['style'],
                    'line': node.start_point[0] + 1
                })
            
            # Track data attributes
            for attr_name, attr_value in attributes.items():
                if attr_name.startswith('data-'):
                    symbols.append({
                        'symbol': f'[{attr_name}]',
                        'kind': 'data_attribute',
                        'signature': f'{attr_name}="{attr_value}"',
                        'line': node.start_point[0] + 1
                    })
    
    # Recurse to children
    for child in node.named_children:
        new_path = path + [tag_name] if node.type == 'element' else path
        self._walk_html_tree(child, content, symbols, elements_by_id, elements_by_class, inline_styles, new_path)
```

### 4. CSS Symbol Extraction
**Target Node Types** (from Tree-sitter CSS grammar):
- `rule_set` - CSS rules
- `selectors` - Selector list
- `declaration` - Property declarations
- `media_statement` - Media queries
- `keyframes_statement` - Animations
- `import_statement` - CSS imports
- `supports_statement` - Feature queries

```python
def _index_css_file(self, path: Path, content: str) -> dict:
    """Parse and index CSS file"""
    # Preprocess if needed (SCSS, LESS)
    if path.suffix in {'.scss', '.sass', '.less'}:
        content = self._preprocess_css(content, path.suffix)
    
    tree = self._css_parser.parse(content.encode('utf-8'))
    root = tree.root_node
    
    symbols = []
    selectors_index = {}
    variables = {}
    mixins = {}
    
    # Process all rules
    for child in root.named_children:
        if child.type == 'rule_set':
            self._extract_rule_set(child, content, symbols, selectors_index)
        elif child.type == 'media_statement':
            self._extract_media_query(child, content, symbols)
        elif child.type == 'keyframes_statement':
            self._extract_keyframes(child, content, symbols)
        elif child.type == 'import_statement':
            self._extract_import(child, content, symbols)
        # SCSS/LESS specific
        elif child.type == 'variable_declaration':
            self._extract_variable(child, content, variables)
        elif child.type == 'mixin_declaration':
            self._extract_mixin(child, content, mixins)
    
    return {
        'symbols': symbols,
        'selectors': selectors_index,
        'variables': variables,
        'mixins': mixins
    }

def _extract_rule_set(self, node, content, symbols, selectors_index):
    """Extract CSS rule set"""
    selectors_node = node.child_by_field_name('selectors')
    block_node = node.child_by_field_name('block')
    
    if not selectors_node or not block_node:
        return
    
    # Extract all selectors
    selectors = self._parse_selectors(selectors_node, content)
    
    # Extract declarations
    declarations = self._extract_declarations(block_node, content)
    
    for selector in selectors:
        # Classify selector type
        selector_type = self._classify_selector(selector)
        
        symbols.append({
            'symbol': selector,
            'kind': f'css_{selector_type}',
            'signature': f"{selector} {{ {len(declarations)} rules }}",
            'line': node.start_point[0] + 1,
            'span': (node.start_point[0] + 1, node.end_point[0] + 1)
        })
        
        # Index for cross-referencing
        selectors_index[selector] = {
            'declarations': declarations,
            'line': node.start_point[0] + 1,
            'specificity': self._calculate_specificity(selector)
        }

def _classify_selector(self, selector: str) -> str:
    """Classify CSS selector type"""
    if selector.startswith('#'):
        return 'id_selector'
    elif selector.startswith('.'):
        return 'class_selector'
    elif selector.startswith('[') and selector.endswith(']'):
        return 'attribute_selector'
    elif ':' in selector:
        return 'pseudo_selector'
    elif selector in ['*', 'html', 'body'] or selector.isalpha():
        return 'element_selector'
    else:
        return 'complex_selector'
```

### 5. CSS Preprocessor Support
```python
def _preprocess_css(self, content: str, file_type: str) -> str:
    """Basic preprocessing for SCSS/LESS (simplified)"""
    # This is a simplified version - real implementation would need proper parsers
    if file_type in {'.scss', '.sass'}:
        # Handle SCSS variables ($var)
        content = self._expand_scss_variables(content)
        # Handle nesting
        content = self._flatten_scss_nesting(content)
    elif file_type == '.less':
        # Handle LESS variables (@var)
        content = self._expand_less_variables(content)
    
    return content

def _extract_scss_features(self, content: str, symbols: list):
    """Extract SCSS-specific features"""
    # Variables
    variable_pattern = r'\$(\w+):\s*([^;]+);'
    for match in re.finditer(variable_pattern, content):
        var_name = match.group(1)
        var_value = match.group(2)
        symbols.append({
            'symbol': f'${var_name}',
            'kind': 'scss_variable',
            'signature': f'${var_name}: {var_value}',
            'line': content[:match.start()].count('\n') + 1
        })
    
    # Mixins
    mixin_pattern = r'@mixin\s+(\w+)\s*\(([^)]*)\)'
    for match in re.finditer(mixin_pattern, content):
        mixin_name = match.group(1)
        mixin_params = match.group(2)
        symbols.append({
            'symbol': f'@mixin {mixin_name}',
            'kind': 'scss_mixin',
            'signature': f'@mixin {mixin_name}({mixin_params})',
            'line': content[:match.start()].count('\n') + 1
        })
```

### 6. Cross-Reference HTML and CSS
```python
def findReferences(self, symbol: str) -> list[Reference]:
    """Find references between HTML and CSS"""
    references = []
    
    # CSS selector looking for HTML elements
    if symbol.startswith('#'):  # ID selector
        # Find HTML elements with this ID
        id_name = symbol[1:]
        references.extend(self._find_html_by_id(id_name))
    
    elif symbol.startswith('.'):  # Class selector
        # Find HTML elements with this class
        class_name = symbol[1:]
        references.extend(self._find_html_by_class(class_name))
    
    # HTML ID/class looking for CSS rules
    elif symbol in self._id_index or symbol in self._class_index:
        # Find CSS rules targeting this element
        references.extend(self._find_css_rules_for_element(symbol))
    
    return references

def _match_selector_to_element(self, selector: str, element: dict) -> bool:
    """Check if CSS selector matches HTML element"""
    # Simple matching - real implementation would need full CSS selector parser
    if selector.startswith('#'):
        return element.get('id') == selector[1:]
    elif selector.startswith('.'):
        return selector[1:] in element.get('classes', [])
    elif selector.isalpha():
        return element.get('tag') == selector
    
    # Complex selectors would need more sophisticated parsing
    return False
```

### 7. Framework Support
```python
def _detect_css_framework(self, content: str, imports: list) -> list[str]:
    """Detect CSS frameworks in use"""
    frameworks = []
    
    # Bootstrap
    if any('bootstrap' in imp for imp in imports) or 'bootstrap' in content:
        frameworks.append('bootstrap')
    
    # Tailwind
    if '@tailwind' in content or any('tailwindcss' in imp for imp in imports):
        frameworks.append('tailwind')
    
    # Bulma
    if 'bulma' in content:
        frameworks.append('bulma')
    
    return frameworks

def _extract_utility_classes(self, content: str, framework: str):
    """Extract framework-specific utility classes"""
    if framework == 'tailwind':
        # Tailwind utility classes
        utilities = {
            'spacing': ['p-', 'm-', 'px-', 'py-', 'mx-', 'my-'],
            'flex': ['flex', 'flex-row', 'flex-col', 'justify-', 'items-'],
            'grid': ['grid', 'grid-cols-', 'gap-'],
            'typography': ['text-', 'font-', 'leading-'],
            'color': ['bg-', 'text-', 'border-']
        }
        # Extract usage patterns
```

### 8. Testing Requirements

Create `test_html_css_plugin.py` with:
```python
def test_supports():
    plugin = Plugin()
    assert plugin.supports("index.html")
    assert plugin.supports("styles.css")
    assert plugin.supports("main.scss")
    assert plugin.supports("theme.less")
    assert not plugin.supports("script.js")

def test_html_extraction():
    plugin = Plugin()
    content = '''
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            .header { color: blue; }
        </style>
    </head>
    <body>
        <div id="main" class="container fluid">
            <h1 class="header">Title</h1>
            <p style="color: red;">Text</p>
            <button data-action="submit">Submit</button>
        </div>
    </body>
    </html>
    '''
    shard = plugin.indexFile("test.html", content)
    
    # Should extract IDs, classes, inline styles, data attributes
    assert any(s['symbol'] == '#main' for s in shard['symbols'])
    assert any(s['symbol'] == '.container' for s in shard['symbols'])
    assert any(s['symbol'] == '.header' for s in shard['symbols'])
    assert any(s['symbol'] == '[data-action]' for s in shard['symbols'])

def test_css_extraction():
    plugin = Plugin()
    content = '''
    /* Variables */
    :root {
        --primary-color: #007bff;
    }
    
    /* ID selector */
    #header {
        background: var(--primary-color);
    }
    
    /* Class selectors */
    .container {
        max-width: 1200px;
        margin: 0 auto;
    }
    
    /* Complex selector */
    .container > .row:nth-child(2) {
        padding: 20px;
    }
    
    /* Media query */
    @media (max-width: 768px) {
        .container {
            padding: 10px;
        }
    }
    
    /* Animation */
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
    '''
    shard = plugin.indexFile("styles.css", content)
    
    # Should extract various selector types
    assert any(s['symbol'] == '#header' and s['kind'] == 'css_id_selector' for s in shard['symbols'])
    assert any(s['symbol'] == '.container' and s['kind'] == 'css_class_selector' for s in shard['symbols'])
    assert any(s['kind'] == 'css_media_query' for s in shard['symbols'])
    assert any(s['kind'] == 'css_keyframes' for s in shard['symbols'])

def test_scss_features():
    plugin = Plugin()
    content = '''
    $primary: #333;
    $secondary: lighten($primary, 20%);
    
    @mixin button-style($bg-color) {
        background: $bg-color;
        padding: 10px 20px;
        
        &:hover {
            background: darken($bg-color, 10%);
        }
    }
    
    .button {
        @include button-style($primary);
        
        &--large {
            font-size: 1.2em;
        }
    }
    '''
    shard = plugin.indexFile("styles.scss", content)
    
    # Should extract SCSS variables and mixins
    assert any(s['symbol'] == '$primary' and s['kind'] == 'scss_variable' for s in shard['symbols'])
    assert any(s['symbol'] == '@mixin button-style' and s['kind'] == 'scss_mixin' for s in shard['symbols'])
```

## Key Differences from Other Plugins

1. **Dual Language**: Must handle both HTML and CSS with different parsers
2. **Cross-References**: Track relationships between HTML elements and CSS rules
3. **Preprocessors**: Support SCSS, SASS, LESS with their specific features
4. **No Traditional Symbols**: IDs, classes, and selectors instead of functions/classes
5. **Cascade and Specificity**: CSS-specific concepts for style application
6. **Framework Awareness**: Recognize Bootstrap, Tailwind, etc.

## Implementation Priority

1. **Phase 1**: Basic HTML element and attribute extraction
2. **Phase 2**: Basic CSS selector and rule extraction
3. **Phase 3**: Cross-referencing between HTML and CSS
4. **Phase 4**: Media queries and responsive design features
5. **Phase 5**: Preprocessor support (SCSS, LESS)
6. **Phase 6**: Framework detection and utility class support

## Performance Considerations

- HTML files can be very large (generated content)
- CSS files may have thousands of rules
- Preprocessor compilation can be expensive
- Cache selector matching results
- Consider incremental parsing for live editing

## Advanced Features (Future)

```python
# CSS property validation
def _validate_css_property(self, property_name: str, value: str) -> bool:
    """Validate CSS property values"""
    # Check against known properties and valid values
    pass

# Accessibility checking
def _check_accessibility(self, element: dict) -> list[str]:
    """Basic accessibility checks"""
    issues = []
    if element['tag'] == 'img' and 'alt' not in element.get('attributes', {}):
        issues.append('Image missing alt attribute')
    return issues
```