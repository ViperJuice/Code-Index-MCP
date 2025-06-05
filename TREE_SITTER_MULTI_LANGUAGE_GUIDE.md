# Tree-Sitter Python Bindings: Multi-Language Support Guide

## Overview

Tree-sitter Python bindings support multiple programming languages through two main approaches:

1. **Individual Language Packages** - Install and load each language separately
2. **tree-sitter-languages Package** - All-in-one package with pre-compiled language support

## Approach 1: Individual Language Packages

### Installation
```bash
pip install tree-sitter
pip install tree-sitter-python
pip install tree-sitter-javascript
pip install tree-sitter-rust
# etc...
```

### Basic Usage
```python
import tree_sitter_python as tspython
import tree_sitter_javascript as tsjs
import tree_sitter_rust as tsrust
from tree_sitter import Language, Parser

# Load different language grammars
PY_LANGUAGE = Language(tspython.language())
JS_LANGUAGE = Language(tsjs.language())
RUST_LANGUAGE = Language(tsrust.language())

# Create parsers for each language
py_parser = Parser(PY_LANGUAGE)
js_parser = Parser(JS_LANGUAGE)
rust_parser = Parser(RUST_LANGUAGE)

# Parse code
python_code = b"def hello(): pass"
js_code = b"function hello() {}"
rust_code = b"fn hello() {}"

py_tree = py_parser.parse(python_code)
js_tree = js_parser.parse(js_code)
rust_tree = rust_parser.parse(rust_code)
```

### Dynamic Language Switching
```python
# Single parser with switchable language
parser = Parser()

# Switch language based on file extension
def get_parser_for_file(filepath):
    ext = Path(filepath).suffix
    if ext == '.py':
        parser.language = PY_LANGUAGE
    elif ext in ['.js', '.jsx']:
        parser.language = JS_LANGUAGE
    elif ext == '.rs':
        parser.language = RUST_LANGUAGE
    return parser
```

## Approach 2: tree-sitter-languages Package

### Installation
```bash
pip install tree-sitter-languages
```

### Basic Usage
```python
from tree_sitter_languages import get_language, get_parser

# Get language and parser for any supported language
python_lang = get_language('python')
python_parser = get_parser('python')

js_lang = get_language('javascript')
js_parser = get_parser('javascript')

# Parse code
tree = python_parser.parse(b"def hello(): pass")
```

### Dynamic Language Detection
```python
from pathlib import Path
from tree_sitter_languages import get_parser

# Map file extensions to language names
LANGUAGE_MAP = {
    '.py': 'python',
    '.js': 'javascript',
    '.jsx': 'javascript',
    '.ts': 'typescript',
    '.tsx': 'tsx',
    '.rs': 'rust',
    '.go': 'go',
    '.c': 'c',
    '.cpp': 'cpp',
    '.h': 'c',
    '.hpp': 'cpp',
    '.java': 'java',
    '.rb': 'ruby',
    '.php': 'php',
    '.cs': 'c_sharp',
    '.swift': 'swift',
    '.kt': 'kotlin',
    '.scala': 'scala',
    '.r': 'r',
    '.lua': 'lua',
    '.dart': 'dart',
    '.sh': 'bash',
    '.yaml': 'yaml',
    '.yml': 'yaml',
    '.json': 'json',
    '.xml': 'xml',
    '.html': 'html',
    '.css': 'css',
    '.sql': 'sql',
    '.md': 'markdown',
}

def parse_file(filepath):
    """Parse a file with the appropriate language parser."""
    path = Path(filepath)
    ext = path.suffix.lower()
    
    if ext not in LANGUAGE_MAP:
        raise ValueError(f"Unsupported file type: {ext}")
    
    language = LANGUAGE_MAP[ext]
    parser = get_parser(language)
    
    content = path.read_bytes()
    return parser.parse(content)
```

## Advanced Multi-Language Parsing

### Language-Agnostic Code Analyzer
```python
from tree_sitter_languages import get_parser, get_language
import ctypes

class MultiLanguageAnalyzer:
    def __init__(self):
        # Cache parsers for performance
        self._parsers = {}
        self._languages = {}
        
    def get_parser_for_language(self, language_name):
        """Get or create parser for a language."""
        if language_name not in self._parsers:
            self._parsers[language_name] = get_parser(language_name)
            self._languages[language_name] = get_language(language_name)
        return self._parsers[language_name]
    
    def analyze_file(self, filepath):
        """Analyze a file and extract language-specific features."""
        path = Path(filepath)
        ext = path.suffix.lower()
        language = LANGUAGE_MAP.get(ext)
        
        if not language:
            return None
            
        parser = self.get_parser_for_language(language)
        content = path.read_bytes()
        tree = parser.parse(content)
        
        # Extract common features across languages
        return {
            'language': language,
            'file': str(path),
            'functions': self.extract_functions(tree, language),
            'classes': self.extract_classes(tree, language),
            'imports': self.extract_imports(tree, language),
        }
    
    def extract_functions(self, tree, language):
        """Extract function definitions based on language."""
        functions = []
        
        # Language-specific queries
        queries = {
            'python': '(function_definition name: (identifier) @name)',
            'javascript': '[(function_declaration name: (identifier) @name) (arrow_function)]',
            'rust': '(function_item name: (identifier) @name)',
            'go': '(function_declaration name: (identifier) @name)',
            'c': '(function_definition declarator: (function_declarator declarator: (identifier) @name))',
        }
        
        # Query the tree (simplified - actual implementation would use tree-sitter queries)
        # This is pseudocode for illustration
        return functions
```

### Using ctypes for Direct Library Access
```python
import ctypes
from tree_sitter import Language, Parser
import tree_sitter_languages

# Direct access to language functions in the shared library
lib_path = Path(tree_sitter_languages.__path__[0]) / "languages.so"
lib = ctypes.CDLL(str(lib_path))

# Configure return types for each language function
language_functions = [
    'tree_sitter_python',
    'tree_sitter_javascript',
    'tree_sitter_typescript',
    'tree_sitter_rust',
    'tree_sitter_go',
    'tree_sitter_c',
    'tree_sitter_cpp',
    'tree_sitter_java',
    'tree_sitter_ruby',
    'tree_sitter_php',
]

# Create language objects
languages = {}
for func_name in language_functions:
    if hasattr(lib, func_name):
        func = getattr(lib, func_name)
        func.restype = ctypes.c_void_p
        lang_name = func_name.replace('tree_sitter_', '')
        languages[lang_name] = Language(func())
```

## Best Practices

### 1. Parser Caching
```python
class ParserCache:
    def __init__(self):
        self._cache = {}
    
    def get_parser(self, language):
        if language not in self._cache:
            self._cache[language] = get_parser(language)
        return self._cache[language]
```

### 2. Error Handling
```python
def safe_parse(filepath, language=None):
    """Safely parse a file with appropriate error handling."""
    try:
        path = Path(filepath)
        
        # Auto-detect language if not provided
        if language is None:
            ext = path.suffix.lower()
            language = LANGUAGE_MAP.get(ext)
            
        if not language:
            raise ValueError(f"Cannot determine language for {filepath}")
        
        parser = get_parser(language)
        content = path.read_bytes()
        tree = parser.parse(content)
        
        if tree.root_node.has_error:
            logger.warning(f"Parse errors in {filepath}")
            
        return tree
        
    except Exception as e:
        logger.error(f"Failed to parse {filepath}: {e}")
        return None
```

### 3. Memory Management
```python
# Tree-sitter trees hold references to the source bytes
# Keep source in memory while using the tree
def parse_with_source(filepath):
    source = Path(filepath).read_bytes()
    parser = get_parser('python')
    tree = parser.parse(source)
    return tree, source  # Return both to keep source alive
```

### 4. Language Feature Detection
```python
def supports_language(language_name):
    """Check if a language is supported."""
    try:
        get_language(language_name)
        return True
    except:
        return False

# Get list of all supported languages
SUPPORTED_LANGUAGES = [
    'bash', 'c', 'cpp', 'c_sharp', 'css', 'dart', 'elixir', 'elm',
    'go', 'html', 'java', 'javascript', 'json', 'julia', 'kotlin',
    'lua', 'markdown', 'php', 'python', 'r', 'regex', 'ruby', 'rust',
    'scala', 'sql', 'swift', 'toml', 'tsx', 'typescript', 'yaml'
]
```

## Common Patterns

### 1. Multi-Language Project Indexer
```python
class ProjectIndexer:
    def __init__(self):
        self.analyzer = MultiLanguageAnalyzer()
        self.index = {}
    
    def index_directory(self, directory):
        """Index all supported files in a directory."""
        for filepath in Path(directory).rglob("*"):
            if filepath.is_file() and filepath.suffix in LANGUAGE_MAP:
                try:
                    analysis = self.analyzer.analyze_file(filepath)
                    if analysis:
                        self.index[str(filepath)] = analysis
                except Exception as e:
                    logger.error(f"Failed to index {filepath}: {e}")
```

### 2. Language-Specific Visitor Pattern
```python
class LanguageVisitor:
    """Base class for language-specific visitors."""
    
    def visit(self, node, source):
        method_name = f'visit_{node.type}'
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node, source)
    
    def generic_visit(self, node, source):
        for child in node.children:
            self.visit(child, source)

class PythonVisitor(LanguageVisitor):
    def visit_function_definition(self, node, source):
        # Extract Python function info
        pass

class JavaScriptVisitor(LanguageVisitor):
    def visit_function_declaration(self, node, source):
        # Extract JavaScript function info
        pass
```

### 3. Cross-Language Symbol Extraction
```python
def extract_symbols(filepath):
    """Extract symbols from any supported language file."""
    tree = parse_file(filepath)
    if not tree:
        return []
    
    symbols = []
    language = detect_language(filepath)
    
    # Define symbol patterns for each language
    patterns = {
        'python': {
            'function': '(function_definition)',
            'class': '(class_definition)',
            'method': '(function_definition)',
        },
        'javascript': {
            'function': '[(function_declaration) (arrow_function)]',
            'class': '(class_declaration)',
            'method': '(method_definition)',
        },
        # Add more languages...
    }
    
    # Extract symbols using language-specific patterns
    if language in patterns:
        for symbol_type, pattern in patterns[language].items():
            # Use tree-sitter query to find symbols
            # (Implementation depends on tree-sitter query API)
            pass
    
    return symbols
```

## Performance Considerations

1. **Parser Reuse**: Create parsers once and reuse them
2. **Lazy Loading**: Only load languages when needed
3. **Batch Processing**: Parse multiple files of the same language together
4. **Memory Management**: Be mindful of keeping source bytes in memory
5. **Error Recovery**: Tree-sitter has good error recovery, but check for parse errors

## Limitations

1. **Binary Dependencies**: Requires pre-compiled binaries
2. **Language Updates**: Grammar updates require package updates
3. **Query Language**: Advanced queries require learning tree-sitter's S-expression query syntax
4. **Memory Usage**: Large files can consume significant memory

## Alternative Approaches

1. **Language Server Protocol (LSP)**: For more advanced language features
2. **Pygments**: For syntax highlighting and basic lexing
3. **libclang/jedi**: For language-specific deep analysis
4. **Regular Expressions**: For simple pattern matching

## Resources

- [Tree-sitter Documentation](https://tree-sitter.github.io/tree-sitter/)
- [py-tree-sitter GitHub](https://github.com/tree-sitter/py-tree-sitter)
- [tree-sitter-languages PyPI](https://pypi.org/project/tree-sitter-languages/)
- [Writing Tree-sitter Queries](https://tree-sitter.github.io/tree-sitter/using-parsers#pattern-matching-with-queries)