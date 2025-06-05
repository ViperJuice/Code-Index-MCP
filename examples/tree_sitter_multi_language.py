#!/usr/bin/env python3
"""
Example demonstrating how to use tree-sitter-languages for multiple programming languages.

The tree-sitter-languages package provides pre-built language grammars for 31+ languages,
eliminating the need to compile or distribute grammar files separately.
"""

import ctypes
from pathlib import Path
from typing import Optional, Dict, Any
import tree_sitter_languages
from tree_sitter import Language, Parser, Node


class MultiLanguageParser:
    """A parser that can handle multiple programming languages using tree-sitter-languages."""
    
    # Mapping of file extensions to language names
    EXTENSION_MAP = {
        '.py': 'python',
        '.js': 'javascript',
        '.jsx': 'javascript',
        '.ts': 'typescript',
        '.tsx': 'tsx',
        '.go': 'go',
        '.rs': 'rust',
        '.c': 'c',
        '.h': 'c',
        '.cpp': 'cpp',
        '.cc': 'cpp',
        '.cxx': 'cpp',
        '.hpp': 'cpp',
        '.java': 'java',
        '.kt': 'kotlin',
        '.scala': 'scala',
        '.rb': 'ruby',
        '.php': 'php',
        '.cs': 'c_sharp',
        '.lua': 'lua',
        '.r': 'r',
        '.R': 'r',
        '.jl': 'julia',
        '.ex': 'elixir',
        '.exs': 'elixir',
        '.elm': 'elm',
        '.hs': 'haskell',
        '.ml': 'ocaml',
        '.mli': 'ocaml',
        '.pl': 'perl',
        '.pm': 'perl',
        '.sh': 'bash',
        '.bash': 'bash',
        '.json': 'json',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.toml': 'toml',
        '.md': 'markdown',
        '.sql': 'sql',
        '.html': 'html',
        '.htm': 'html',
        '.css': 'css',
        '.scss': 'css',
        '.sass': 'css',
    }
    
    # List of all supported languages in tree-sitter-languages
    SUPPORTED_LANGUAGES = [
        'bash', 'c', 'c_sharp', 'cpp', 'css', 'elixir', 'elm', 'go', 
        'haskell', 'html', 'java', 'javascript', 'json', 'julia', 'kotlin', 
        'lua', 'markdown', 'ocaml', 'perl', 'php', 'python', 'r', 'regex', 
        'ruby', 'rust', 'scala', 'sql', 'toml', 'tsx', 'typescript', 'yaml'
    ]
    
    def __init__(self):
        """Initialize the multi-language parser."""
        # Load the shared library containing all language grammars
        lib_path = Path(tree_sitter_languages.__path__[0]) / "languages.so"
        self._lib = ctypes.CDLL(str(lib_path))
        
        # Cache for language objects and parsers
        self._languages: Dict[str, Language] = {}
        self._parsers: Dict[str, Parser] = {}
    
    def get_language(self, language_name: str) -> Optional[Language]:
        """Get a Language object for the specified language.
        
        Args:
            language_name: Name of the language (e.g., 'python', 'javascript')
            
        Returns:
            Language object or None if language is not supported
        """
        if language_name not in self.SUPPORTED_LANGUAGES:
            return None
            
        if language_name not in self._languages:
            try:
                # Get the function from the shared library
                func_name = f"tree_sitter_{language_name}"
                func = getattr(self._lib, func_name)
                func.restype = ctypes.c_void_p
                
                # Create Language object
                self._languages[language_name] = Language(func())
            except (AttributeError, ValueError) as e:
                print(f"Failed to load language {language_name}: {e}")
                return None
                
        return self._languages[language_name]
    
    def get_parser(self, language_name: str) -> Optional[Parser]:
        """Get a Parser for the specified language.
        
        Args:
            language_name: Name of the language (e.g., 'python', 'javascript')
            
        Returns:
            Parser object or None if language is not supported
        """
        if language_name not in self._parsers:
            language = self.get_language(language_name)
            if language is None:
                return None
                
            parser = Parser()
            parser.language = language
            self._parsers[language_name] = parser
            
        return self._parsers[language_name]
    
    def parse_file(self, file_path: Path) -> Optional[Node]:
        """Parse a file based on its extension.
        
        Args:
            file_path: Path to the file to parse
            
        Returns:
            Root node of the parse tree or None if parsing failed
        """
        # Determine language from file extension
        ext = file_path.suffix.lower()
        language_name = self.EXTENSION_MAP.get(ext)
        
        if not language_name:
            print(f"Unknown file extension: {ext}")
            return None
            
        # Get parser for the language
        parser = self.get_parser(language_name)
        if not parser:
            print(f"No parser available for language: {language_name}")
            return None
            
        # Read and parse the file
        try:
            content = file_path.read_bytes()
            tree = parser.parse(content)
            return tree.root_node
        except Exception as e:
            print(f"Failed to parse {file_path}: {e}")
            return None
    
    def parse_code(self, code: str, language_name: str) -> Optional[Node]:
        """Parse code snippet in the specified language.
        
        Args:
            code: Source code to parse
            language_name: Name of the language
            
        Returns:
            Root node of the parse tree or None if parsing failed
        """
        parser = self.get_parser(language_name)
        if not parser:
            return None
            
        try:
            tree = parser.parse(code.encode('utf-8'))
            return tree.root_node
        except Exception as e:
            print(f"Failed to parse code: {e}")
            return None
    
    def extract_symbols(self, node: Node, language_name: str) -> Dict[str, Any]:
        """Extract symbols (functions, classes, etc.) from a parse tree.
        
        Args:
            node: Root node of the parse tree
            language_name: Name of the language
            
        Returns:
            Dictionary containing extracted symbols
        """
        symbols = {
            'functions': [],
            'classes': [],
            'variables': [],
            'imports': [],
        }
        
        # Language-specific symbol extraction
        if language_name == 'python':
            self._extract_python_symbols(node, symbols)
        elif language_name in ['javascript', 'typescript']:
            self._extract_js_symbols(node, symbols)
        elif language_name == 'go':
            self._extract_go_symbols(node, symbols)
        elif language_name == 'rust':
            self._extract_rust_symbols(node, symbols)
        elif language_name in ['c', 'cpp']:
            self._extract_c_symbols(node, symbols)
        elif language_name == 'java':
            self._extract_java_symbols(node, symbols)
        
        return symbols
    
    def _extract_python_symbols(self, node: Node, symbols: Dict[str, Any]):
        """Extract symbols from Python code."""
        if node.type == 'function_definition':
            name_node = node.child_by_field_name('name')
            if name_node:
                symbols['functions'].append(name_node.text.decode('utf-8'))
        elif node.type == 'class_definition':
            name_node = node.child_by_field_name('name')
            if name_node:
                symbols['classes'].append(name_node.text.decode('utf-8'))
        elif node.type == 'import_statement' or node.type == 'import_from_statement':
            symbols['imports'].append(node.text.decode('utf-8'))
        
        # Recurse through children
        for child in node.children:
            self._extract_python_symbols(child, symbols)
    
    def _extract_js_symbols(self, node: Node, symbols: Dict[str, Any]):
        """Extract symbols from JavaScript/TypeScript code."""
        if node.type in ['function_declaration', 'arrow_function', 'function']:
            name_node = node.child_by_field_name('name')
            if name_node:
                symbols['functions'].append(name_node.text.decode('utf-8'))
        elif node.type == 'class_declaration':
            name_node = node.child_by_field_name('name')
            if name_node:
                symbols['classes'].append(name_node.text.decode('utf-8'))
        elif node.type in ['import_statement', 'import_clause']:
            symbols['imports'].append(node.text.decode('utf-8'))
        
        for child in node.children:
            self._extract_js_symbols(child, symbols)
    
    def _extract_go_symbols(self, node: Node, symbols: Dict[str, Any]):
        """Extract symbols from Go code."""
        if node.type == 'function_declaration':
            name_node = node.child_by_field_name('name')
            if name_node:
                symbols['functions'].append(name_node.text.decode('utf-8'))
        elif node.type == 'type_declaration':
            for spec in node.children:
                if spec.type == 'type_spec':
                    name_node = spec.child_by_field_name('name')
                    if name_node:
                        symbols['classes'].append(name_node.text.decode('utf-8'))
        elif node.type == 'import_declaration':
            symbols['imports'].append(node.text.decode('utf-8'))
        
        for child in node.children:
            self._extract_go_symbols(child, symbols)
    
    def _extract_rust_symbols(self, node: Node, symbols: Dict[str, Any]):
        """Extract symbols from Rust code."""
        if node.type == 'function_item':
            name_node = node.child_by_field_name('name')
            if name_node:
                symbols['functions'].append(name_node.text.decode('utf-8'))
        elif node.type in ['struct_item', 'enum_item', 'trait_item']:
            name_node = node.child_by_field_name('name')
            if name_node:
                symbols['classes'].append(name_node.text.decode('utf-8'))
        elif node.type == 'use_declaration':
            symbols['imports'].append(node.text.decode('utf-8'))
        
        for child in node.children:
            self._extract_rust_symbols(child, symbols)
    
    def _extract_c_symbols(self, node: Node, symbols: Dict[str, Any]):
        """Extract symbols from C/C++ code."""
        if node.type == 'function_definition':
            declarator = node.child_by_field_name('declarator')
            if declarator and declarator.type == 'function_declarator':
                name_node = declarator.child_by_field_name('declarator')
                if name_node:
                    symbols['functions'].append(name_node.text.decode('utf-8'))
        elif node.type in ['struct_specifier', 'class_specifier']:
            name_node = node.child_by_field_name('name')
            if name_node:
                symbols['classes'].append(name_node.text.decode('utf-8'))
        elif node.type == 'preproc_include':
            symbols['imports'].append(node.text.decode('utf-8'))
        
        for child in node.children:
            self._extract_c_symbols(child, symbols)
    
    def _extract_java_symbols(self, node: Node, symbols: Dict[str, Any]):
        """Extract symbols from Java code."""
        if node.type == 'method_declaration':
            name_node = node.child_by_field_name('name')
            if name_node:
                symbols['functions'].append(name_node.text.decode('utf-8'))
        elif node.type in ['class_declaration', 'interface_declaration']:
            name_node = node.child_by_field_name('name')
            if name_node:
                symbols['classes'].append(name_node.text.decode('utf-8'))
        elif node.type == 'import_declaration':
            symbols['imports'].append(node.text.decode('utf-8'))
        
        for child in node.children:
            self._extract_java_symbols(child, symbols)


def main():
    """Demonstrate the multi-language parser."""
    parser = MultiLanguageParser()
    
    print("Tree-sitter-languages Multi-Language Parser Example")
    print("=" * 60)
    print(f"\nSupported languages ({len(parser.SUPPORTED_LANGUAGES)}):")
    print(", ".join(sorted(parser.SUPPORTED_LANGUAGES)))
    
    # Example: Parse code snippets in different languages
    examples = {
        'python': '''
def calculate_sum(a, b):
    """Calculate the sum of two numbers."""
    return a + b

class Calculator:
    def multiply(self, x, y):
        return x * y
''',
        'javascript': '''
function greet(name) {
    console.log(`Hello, ${name}!`);
}

class Person {
    constructor(name) {
        this.name = name;
    }
}
''',
        'go': '''
package main

import "fmt"

func main() {
    fmt.Println("Hello, World!")
}

type User struct {
    Name string
    Age  int
}
''',
        'rust': '''
fn main() {
    println!("Hello, World!");
}

struct Point {
    x: f64,
    y: f64,
}

impl Point {
    fn distance(&self) -> f64 {
        (self.x * self.x + self.y * self.y).sqrt()
    }
}
''',
    }
    
    print("\n\nParsing examples:")
    print("-" * 60)
    
    for language, code in examples.items():
        print(f"\n{language.upper()}:")
        root = parser.parse_code(code, language)
        
        if root:
            print(f"  ✓ Parse successful - Root node: {root.type}")
            symbols = parser.extract_symbols(root, language)
            
            if symbols['functions']:
                print(f"  Functions: {', '.join(symbols['functions'])}")
            if symbols['classes']:
                print(f"  Classes/Types: {', '.join(symbols['classes'])}")
            if symbols['imports']:
                print(f"  Imports: {len(symbols['imports'])} found")
        else:
            print(f"  ✗ Parse failed")
    
    # Example: Dynamic language detection
    print("\n\nFile extension mapping:")
    print("-" * 60)
    
    test_files = [
        'main.py', 'app.js', 'server.go', 'lib.rs', 'program.c',
        'Main.java', 'script.rb', 'index.php', 'app.tsx', 'config.yaml'
    ]
    
    for filename in test_files:
        path = Path(filename)
        ext = path.suffix.lower()
        lang = parser.EXTENSION_MAP.get(ext, 'unknown')
        print(f"  {filename:15} -> {lang}")


if __name__ == '__main__':
    main()