"""Enhanced TreeSitter wrapper supporting multiple languages.

This wrapper provides a language-agnostic interface to the tree-sitter-languages
package, supporting 49+ programming languages with a simple API and robust
error handling for missing parsers.
"""

from __future__ import annotations

import ctypes
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

from tree_sitter import Language, Parser, Node

# Import tree-sitter-languages with graceful fallback
try:
    import tree_sitter_languages
    HAS_TREE_SITTER_LANGUAGES = True
except ImportError:
    HAS_TREE_SITTER_LANGUAGES = False
    tree_sitter_languages = None

logger = logging.getLogger(__name__)


class TreeSitterWrapper:
    """Enhanced utility class for parsing files with Tree-sitter across multiple languages."""
    
    # Map of language names to their tree_sitter function names
    # Some languages have different names in the library
    LANGUAGE_MAPPINGS = {
        'c++': 'cpp',
        'c#': 'c_sharp',
        'csharp': 'c_sharp',
        'objc': 'objc',
        'objective-c': 'objc',
        'lisp': 'commonlisp',
        'elisp': 'elisp',
        'emacs-lisp': 'elisp',
        'fortran77': 'fixed_form_fortran',
        'f77': 'fixed_form_fortran',
        'fortran90': 'fortran',
        'f90': 'fortran',
        'js': 'javascript',
        'ts': 'typescript',
        'yml': 'yaml',
        'md': 'markdown',
        'restructuredtext': 'rst',
        'makefile': 'make',
    }
    
    # Complete list of supported languages
    SUPPORTED_LANGUAGES = [
        'bash', 'c', 'c_sharp', 'commonlisp', 'cpp', 'css', 'dockerfile',
        'dot', 'elisp', 'elixir', 'elm', 'embedded_template', 'erlang',
        'fixed_form_fortran', 'fortran', 'go', 'gomod', 'hack', 'haskell',
        'hcl', 'html', 'java', 'javascript', 'jsdoc', 'json', 'julia',
        'kotlin', 'lua', 'make', 'markdown', 'objc', 'ocaml', 'perl', 'php',
        'python', 'ql', 'r', 'regex', 'rst', 'ruby', 'rust', 'scala', 'sql',
        'sqlite', 'toml', 'tsq', 'tsx', 'typescript', 'yaml'
    ]

    def __init__(self, language: str = 'python') -> None:
        """Initialize the wrapper for a specific language.
        
        Args:
            language: The programming language to parse (default: 'python').
                     Can be a common name like 'c++' or 'js' which will be
                     automatically mapped to the correct internal name.
                     
        Raises:
            ValueError: If the language is not supported.
            RuntimeError: If tree-sitter-languages is not available.
        """
        # Check if tree-sitter-languages is available
        if not HAS_TREE_SITTER_LANGUAGES:
            raise RuntimeError(
                "tree-sitter-languages package is not available. "
                "Please install it with: pip install tree-sitter-languages"
            )
        
        # Normalize the language name
        self.requested_language = language.lower()
        self.language_name = self._normalize_language_name(self.requested_language)
        
        if self.language_name not in self.SUPPORTED_LANGUAGES:
            raise ValueError(
                f"Language '{language}' is not supported. "
                f"Supported languages: {', '.join(sorted(self.get_supported_languages()))}"
            )
        
        self._lib = None
        self._language = None
        self._parser = None
        
        try:
            # Load the shared library
            lib_path = Path(tree_sitter_languages.__path__[0]) / "languages.so"
            if not lib_path.exists():
                # Try alternative paths for different platforms
                for alt_name in ["languages.dylib", "languages.dll"]:
                    alt_path = Path(tree_sitter_languages.__path__[0]) / alt_name
                    if alt_path.exists():
                        lib_path = alt_path
                        break
            
            if not lib_path.exists():
                raise RuntimeError(
                    f"Could not find tree-sitter-languages shared library. "
                    f"Tried: {tree_sitter_languages.__path__[0]}/languages.*"
                )
            
            self._lib = ctypes.CDLL(str(lib_path))
            
            # Get the language function dynamically
            func_name = f"tree_sitter_{self.language_name}"
            if not hasattr(self._lib, func_name):
                raise ValueError(
                    f"Language function '{func_name}' not found in library. "
                    f"This language may not be supported in your version of tree-sitter-languages."
                )
            
            # Configure the return type
            lang_func = getattr(self._lib, func_name)
            lang_func.restype = ctypes.c_void_p
            
            # Create the Language object
            # The tree-sitter-languages library returns a pointer to TSLanguage
            language_ptr = lang_func()
            if not language_ptr:
                raise RuntimeError(f"Failed to get language pointer for {self.language_name}")
            
            self._language = Language(language_ptr)
            
            # Create and configure the parser
            self._parser = Parser()
            self._parser.language = self._language
            
            logger.debug(f"Successfully initialized TreeSitter wrapper for {self.language_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize TreeSitter wrapper for {language}: {e}")
            # Clean up partial state
            self._lib = None
            self._language = None
            self._parser = None
            raise
    
    def _normalize_language_name(self, language: str) -> str:
        """Normalize a language name to its internal representation.
        
        Args:
            language: The language name to normalize.
            
        Returns:
            The normalized language name.
        """
        # Check if it's already a valid name
        if language in self.SUPPORTED_LANGUAGES:
            return language
        
        # Check if it's in the mapping
        if language in self.LANGUAGE_MAPPINGS:
            return self.LANGUAGE_MAPPINGS[language]
        
        # Try without special characters
        cleaned = language.replace('-', '_').replace(' ', '_')
        if cleaned in self.SUPPORTED_LANGUAGES:
            return cleaned
        
        # Return as-is and let validation handle it
        return language
    
    @classmethod
    def get_supported_languages(cls) -> List[str]:
        """Get a list of all supported language names.
        
        Returns:
            A sorted list of supported language names, including aliases.
        """
        languages = set(cls.SUPPORTED_LANGUAGES)
        # Add common aliases
        languages.update(cls.LANGUAGE_MAPPINGS.keys())
        return sorted(languages)
    
    @classmethod
    def is_language_supported(cls, language: str) -> bool:
        """Check if a language is supported.
        
        Args:
            language: The language name to check.
            
        Returns:
            True if the language is supported, False otherwise.
        """
        if not HAS_TREE_SITTER_LANGUAGES:
            return False
        
        normalized = language.lower()
        return (normalized in cls.SUPPORTED_LANGUAGES or 
                normalized in cls.LANGUAGE_MAPPINGS)
    
    @classmethod
    def check_parser_availability(cls, language: str) -> Dict[str, Any]:
        """Check the availability of a specific parser.
        
        Args:
            language: The language name to check.
            
        Returns:
            Dictionary with availability information.
        """
        result = {
            'language': language,
            'available': False,
            'error': None,
            'tree_sitter_languages_installed': HAS_TREE_SITTER_LANGUAGES,
        }
        
        if not HAS_TREE_SITTER_LANGUAGES:
            result['error'] = "tree-sitter-languages package not installed"
            return result
        
        try:
            # Try to create a wrapper instance
            wrapper = cls(language)
            result['available'] = True
            result['normalized_name'] = wrapper.language_name
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    @classmethod
    def get_available_parsers(cls) -> List[str]:
        """Get a list of actually available parsers (not just theoretically supported).
        
        Returns:
            List of language names that can be successfully loaded.
        """
        if not HAS_TREE_SITTER_LANGUAGES:
            return []
        
        available = []
        for language in cls.SUPPORTED_LANGUAGES:
            try:
                # Quick test - just try to get the function
                lib_path = Path(tree_sitter_languages.__path__[0]) / "languages.so"
                if not lib_path.exists():
                    for alt_name in ["languages.dylib", "languages.dll"]:
                        alt_path = Path(tree_sitter_languages.__path__[0]) / alt_name
                        if alt_path.exists():
                            lib_path = alt_path
                            break
                
                if lib_path.exists():
                    lib = ctypes.CDLL(str(lib_path))
                    func_name = f"tree_sitter_{language}"
                    if hasattr(lib, func_name):
                        available.append(language)
            except Exception:
                # Skip languages that can't be loaded
                continue
        
        return sorted(available)
    
    def get_language_info(self) -> Dict[str, Any]:
        """Get information about the current language.
        
        Returns:
            A dictionary with language information.
        """
        return {
            'requested': self.requested_language,
            'normalized': self.language_name,
            'parser': self._parser is not None,
            'language': self._language is not None,
        }
    
    def parse(self, content: bytes) -> Node:
        """Parse content and return the root Node.
        
        Args:
            content: The source code to parse as bytes.
            
        Returns:
            The root node of the parsed tree.
        """
        tree = self._parser.parse(content)
        return tree.root_node
    
    def parse_file(self, path: Path) -> str:
        """Parse a file and return the AST root as an S-expression.
        
        Args:
            path: Path to the file to parse.
            
        Returns:
            S-expression representation of the AST.
        """
        content = path.read_bytes()
        root = self.parse(content)
        return self._sexp(root)
    
    def parse_path(self, path: Path) -> Node:
        """Parse a file and return the root node.
        
        Args:
            path: Path to the file to parse.
            
        Returns:
            The root node of the parsed tree.
        """
        return self.parse(path.read_bytes())
    
    def _sexp(self, node: Node) -> str:
        """Return an S-expression representation of a node.
        
        Args:
            node: The node to convert.
            
        Returns:
            S-expression string representation.
        """
        if node.child_count == 0:
            return node.type
        
        parts: List[str] = []
        for i in range(node.child_count):
            child = node.child(i)
            if child is None:
                continue
            child_sexp = self._sexp(child)
            field = node.field_name_for_child(i)
            if field:
                parts.append(f"{field}: {child_sexp}")
            else:
                parts.append(child_sexp)
        
        return f"({node.type} {' '.join(parts)})"
    
    def query(self, query_string: str, content: bytes) -> List[Dict[str, Any]]:
        """Execute a tree-sitter query on the content.
        
        Args:
            query_string: The tree-sitter query string.
            content: The source code to query.
            
        Returns:
            List of query matches with capture information.
        """
        from tree_sitter import Query
        
        root = self.parse(content)
        query = self._language.query(query_string)
        
        matches = []
        for match in query.matches(root):
            match_info = {
                'pattern_index': match.pattern_index,
                'captures': {}
            }
            for capture_name, nodes in match.captures.items():
                match_info['captures'][capture_name] = [
                    {
                        'type': node.type,
                        'text': node.text.decode('utf-8') if node.text else '',
                        'start_point': node.start_point,
                        'end_point': node.end_point,
                    }
                    for node in nodes
                ]
            matches.append(match_info)
        
        return matches
    
    def get_symbols(self, content: bytes) -> List[Dict[str, Any]]:
        """Extract common symbol information from the content.
        
        This is a generic implementation that works for most languages.
        For language-specific symbol extraction, use specialized queries.
        
        Args:
            content: The source code to analyze.
            
        Returns:
            List of symbol information dictionaries.
        """
        # Generic queries that work for many languages
        common_queries = {
            'function': [
                '(function_declaration) @function',
                '(function_definition) @function',
                '(method_declaration) @function',
                '(method_definition) @function',
            ],
            'class': [
                '(class_declaration) @class',
                '(class_definition) @class',
            ],
            'variable': [
                '(variable_declaration) @variable',
                '(variable_definition) @variable',
            ]
        }
        
        symbols = []
        root = self.parse(content)
        
        # Try each query type
        for symbol_type, queries in common_queries.items():
            for query_str in queries:
                try:
                    matches = self.query(query_str, content)
                    for match in matches:
                        for nodes in match['captures'].values():
                            for node_info in nodes:
                                symbols.append({
                                    'type': symbol_type,
                                    'name': node_info['text'],
                                    'start': node_info['start_point'],
                                    'end': node_info['end_point'],
                                })
                except Exception:
                    # Query might not be valid for this language
                    continue
        
        return symbols


# Convenience functions for error handling and availability checks
def list_supported_languages() -> List[str]:
    """Get a list of all supported languages.
    
    Returns:
        Sorted list of supported language names.
    """
    return TreeSitterWrapper.get_supported_languages()


def list_available_parsers() -> List[str]:
    """Get a list of actually available parsers.
    
    Returns:
        Sorted list of available parser names.
    """
    return TreeSitterWrapper.get_available_parsers()


def check_tree_sitter_availability() -> Dict[str, Any]:
    """Check the overall Tree-sitter setup availability.
    
    Returns:
        Dictionary with availability information.
    """
    result = {
        'tree_sitter_installed': True,  # If we can import this module, tree-sitter is installed
        'tree_sitter_languages_installed': HAS_TREE_SITTER_LANGUAGES,
        'available_parsers': [],
        'total_parsers': len(TreeSitterWrapper.SUPPORTED_LANGUAGES),
    }
    
    try:
        from tree_sitter import __version__ as ts_version
        result['tree_sitter_version'] = ts_version
    except ImportError:
        result['tree_sitter_installed'] = False
        result['tree_sitter_version'] = None
    
    if HAS_TREE_SITTER_LANGUAGES:
        result['available_parsers'] = list_available_parsers()
        try:
            result['tree_sitter_languages_version'] = tree_sitter_languages.__version__
        except AttributeError:
            result['tree_sitter_languages_version'] = 'unknown'
    
    return result


def safe_create_parser(language: str) -> Optional[TreeSitterWrapper]:
    """Safely create a TreeSitter parser with error handling.
    
    Args:
        language: The language to create a parser for.
        
    Returns:
        TreeSitterWrapper instance if successful, None otherwise.
    """
    try:
        return TreeSitterWrapper(language)
    except Exception as e:
        logger.warning(f"Failed to create parser for {language}: {e}")
        return None


# Example usage
if __name__ == "__main__":
    # List all supported languages
    print("Supported languages:")
    for lang in list_supported_languages():
        print(f"  - {lang}")
    
    # Example: Parse a Python file
    try:
        wrapper = TreeSitterWrapper(language='python')
        test_code = b"def hello(name):\n    print(f'Hello, {name}!')"
        root = wrapper.parse(test_code)
        print(f"\nParsed Python code: {wrapper._sexp(root)}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Example: Parse JavaScript with alias
    try:
        js_wrapper = TreeSitterWrapper(language='js')
        js_code = b"function greet(name) { console.log(`Hello, ${name}!`); }"
        root = js_wrapper.parse(js_code)
        print(f"\nParsed JavaScript code: {js_wrapper._sexp(root)}")
    except Exception as e:
        print(f"Error: {e}")