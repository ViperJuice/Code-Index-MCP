# Generic Tree-Sitter Plugin Design

## Overview

This design enables support for all 48 tree-sitter languages through a single generic plugin, with the ability to override with language-specific implementations when needed.

## Architecture

### 1. Generic Plugin Base Class

```python
# mcp_server/plugins/generic_treesitter_plugin.py

from tree_sitter import Language, Parser
import tree_sitter_languages
from ..plugin_base_enhanced import PluginWithSemanticSearch

class GenericTreeSitterPlugin(PluginWithSemanticSearch):
    """Generic plugin that can handle any tree-sitter supported language."""
    
    def __init__(self, language_config: Dict, sqlite_store=None, enable_semantic=True):
        super().__init__(sqlite_store, enable_semantic)
        
        self.lang = language_config['code']
        self.language_name = language_config['name']
        self.file_extensions = language_config['extensions']
        self.symbol_types = language_config.get('symbols', [])
        
        # Load the tree-sitter parser
        self.parser = Parser()
        self.language = tree_sitter_languages.get_language(self.lang)
        self.parser.set_language(self.language)
        
    def supports(self, path: str | Path) -> bool:
        """Check if this plugin supports the file."""
        return Path(path).suffix in self.file_extensions
        
    def _extract_symbols(self, tree, content: str) -> List[Dict]:
        """Generic symbol extraction using tree-sitter queries."""
        symbols = []
        
        # Use tree-sitter query system for symbol extraction
        query_string = self._build_query_string()
        query = self.language.query(query_string)
        
        captures = query.captures(tree.root_node)
        for node, name in captures:
            symbols.append({
                'symbol': content[node.start_byte:node.end_byte],
                'kind': name,
                'line': node.start_point[0] + 1,
                'end_line': node.end_point[0] + 1,
                # ... other fields
            })
        
        return symbols
```

### 2. Language Registry

```python
# mcp_server/plugins/language_registry.py

LANGUAGE_CONFIGS = {
    "go": {
        "code": "go",
        "name": "Go",
        "extensions": [".go"],
        "symbols": ["function_declaration", "type_declaration", "method_declaration"],
        "query": """
            (function_declaration name: (identifier) @function)
            (type_declaration (type_spec name: (type_identifier) @type))
            (method_declaration name: (field_identifier) @method)
        """
    },
    "rust": {
        "code": "rust",
        "name": "Rust",
        "extensions": [".rs"],
        "symbols": ["function_item", "struct_item", "enum_item", "trait_item"],
        "query": """
            (function_item name: (identifier) @function)
            (struct_item name: (type_identifier) @struct)
            (enum_item name: (type_identifier) @enum)
            (trait_item name: (type_identifier) @trait)
        """
    },
    "bash": {
        "code": "bash",
        "name": "Bash",
        "extensions": [".sh", ".bash", ".zsh"],
        "symbols": ["function_definition", "variable_assignment"],
        "query": """
            (function_definition name: (word) @function)
            (variable_assignment name: (variable_name) @variable)
        """
    },
    # ... continue for all 48 languages
}
```

### 3. Plugin Factory

```python
# mcp_server/plugins/plugin_factory.py

class PluginFactory:
    """Factory for creating language plugins."""
    
    # Language-specific plugin classes
    SPECIFIC_PLUGINS = {
        'python': PythonPluginSemantic,  # Has Jedi integration
        'javascript': JsPluginSemantic,   # Has JSX/TSX support
        'c': CPluginSemantic,            # Has preprocessor handling
        'cpp': CppPluginSemantic,        # Has template support
        # ... other specialized plugins
    }
    
    @classmethod
    def create_plugin(cls, language: str, sqlite_store=None, enable_semantic=True):
        """Create appropriate plugin for the language."""
        
        # Check for language-specific implementation first
        if language in cls.SPECIFIC_PLUGINS:
            return cls.SPECIFIC_PLUGINS[language](sqlite_store, enable_semantic)
        
        # Check if language is supported by generic plugin
        if language in LANGUAGE_CONFIGS:
            config = LANGUAGE_CONFIGS[language]
            return GenericTreeSitterPlugin(config, sqlite_store, enable_semantic)
        
        # Language not supported
        raise ValueError(f"Unsupported language: {language}")
```

### 4. Dynamic Plugin Loading

```python
# mcp_server/dispatcher/dispatcher.py (updated)

class Dispatcher:
    def __init__(self, sqlite_store=None):
        self.sqlite_store = sqlite_store
        self.plugins = {}
        self._load_all_plugins()
    
    def _load_all_plugins(self):
        """Load plugins for all supported languages."""
        # Load specific plugins
        for lang in ['python', 'javascript', 'c', 'cpp', 'dart', 'html_css']:
            try:
                self.plugins[lang] = PluginFactory.create_plugin(lang, self.sqlite_store)
            except Exception as e:
                logger.error(f"Failed to load {lang} plugin: {e}")
        
        # Load generic plugins for remaining languages
        for lang, config in LANGUAGE_CONFIGS.items():
            if lang not in self.plugins:
                try:
                    self.plugins[lang] = PluginFactory.create_plugin(lang, self.sqlite_store)
                except Exception as e:
                    logger.error(f"Failed to load {lang} plugin: {e}")
```

## Benefits

1. **Maintainability**: Single codebase for 40+ languages
2. **Extensibility**: Easy to add new languages
3. **Flexibility**: Can override with specific implementations
4. **Performance**: Lazy loading of parsers
5. **Consistency**: Uniform behavior across languages

## Implementation Priority

### Phase 1: Core Generic Plugin
1. Implement GenericTreeSitterPlugin
2. Create language registry with 10 popular languages
3. Test with Go, Rust, Java

### Phase 2: Query System
1. Implement tree-sitter query builder
2. Add symbol extraction queries for each language
3. Test symbol extraction accuracy

### Phase 3: Full Coverage
1. Add all 48 languages to registry
2. Implement lazy parser loading
3. Add configuration system

### Phase 4: Optimizations
1. Add caching for parsed queries
2. Implement parallel file processing
3. Add language detection from content

## Language-Specific Considerations

Some languages will benefit from custom plugins:

- **Python**: Jedi provides better type inference
- **TypeScript**: Needs tsconfig.json handling
- **Go**: Benefits from go.mod parsing
- **Rust**: Can use cargo metadata
- **Java**: Can leverage build tool configs

## Testing Strategy

1. Create test files for each language
2. Verify symbol extraction accuracy
3. Test cross-language search
4. Benchmark performance
5. Validate semantic search

This approach provides the best balance between maintainability and functionality.