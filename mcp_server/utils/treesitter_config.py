"""Multi-language Tree-sitter configuration and management.

This module provides a comprehensive Tree-sitter setup with support for multiple
programming languages, graceful fallback handling, and error recovery when
specific parsers are not available.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Optional, Set, Union
import ctypes

from tree_sitter import Language, Parser, Node

# Language imports with graceful fallback
try:
    import tree_sitter_languages
    HAS_TREE_SITTER_LANGUAGES = True
except ImportError:
    HAS_TREE_SITTER_LANGUAGES = False

# Individual language parser imports
LANGUAGE_IMPORTS = {
    'python': ('tree_sitter_languages', 'tree_sitter_python'),
    'javascript': ('tree_sitter_languages', 'tree_sitter_javascript'),
    'typescript': ('tree_sitter_languages', 'tree_sitter_typescript'),
    'java': ('tree_sitter_languages', 'tree_sitter_java'),
    'c': ('tree_sitter_languages', 'tree_sitter_c'),
    'cpp': ('tree_sitter_languages', 'tree_sitter_cpp'),
    'rust': ('tree_sitter_languages', 'tree_sitter_rust'),
    'go': ('tree_sitter_languages', 'tree_sitter_go'),
    'c_sharp': ('tree_sitter_c_sharp', None),
    'bash': ('tree_sitter_bash', None),
    'haskell': ('tree_sitter_haskell', None),
    'scala': ('tree_sitter_scala', None),
    'lua': ('tree_sitter_lua', None),
    'yaml': ('tree_sitter_yaml', None),
    'toml': ('tree_sitter_toml', None),
    'json': ('tree_sitter_json', None),
    'markdown': ('tree_sitter_markdown', None),
    'csv': ('tree_sitter_csv', None),
}

# File extension to language mapping
EXTENSION_TO_LANGUAGE = {
    '.py': 'python',
    '.js': 'javascript',
    '.mjs': 'javascript',
    '.jsx': 'javascript',
    '.ts': 'typescript',
    '.tsx': 'typescript',
    '.java': 'java',
    '.c': 'c',
    '.h': 'c',
    '.cpp': 'cpp',
    '.cxx': 'cpp',
    '.cc': 'cpp',
    '.hpp': 'cpp',
    '.hxx': 'cpp',
    '.rs': 'rust',
    '.go': 'go',
    '.cs': 'c_sharp',
    '.sh': 'bash',
    '.bash': 'bash',
    '.zsh': 'bash',
    '.hs': 'haskell',
    '.scala': 'scala',
    '.sc': 'scala',
    '.lua': 'lua',
    '.yaml': 'yaml',
    '.yml': 'yaml',
    '.toml': 'toml',
    '.json': 'json',
    '.md': 'markdown',
    '.markdown': 'markdown',
    '.csv': 'csv',
}

logger = logging.getLogger(__name__)


class TreeSitterManager:
    """Manages Tree-sitter parsers for multiple programming languages."""

    def __init__(self):
        """Initialize the Tree-sitter manager with available parsers."""
        self._parsers: Dict[str, Parser] = {}
        self._languages: Dict[str, Language] = {}
        self._available_languages: Set[str] = set()
        self._lib = None
        
        self._initialize_parsers()

    def _initialize_parsers(self) -> None:
        """Initialize all available Tree-sitter parsers."""
        # Try to load tree-sitter-languages first
        if HAS_TREE_SITTER_LANGUAGES:
            self._load_bundled_languages()
        
        # Load individual language parsers
        self._load_individual_languages()
        
        logger.info(f"Initialized Tree-sitter with {len(self._available_languages)} languages: "
                   f"{sorted(self._available_languages)}")

    def _load_bundled_languages(self) -> None:
        """Load languages from tree-sitter-languages bundle."""
        try:
            lib_path = Path(tree_sitter_languages.__path__[0]) / "languages.so"
            if not lib_path.exists():
                # Try alternative locations
                for alt_name in ["languages.so", "languages.dylib", "languages.dll"]:
                    alt_path = Path(tree_sitter_languages.__path__[0]) / alt_name
                    if alt_path.exists():
                        lib_path = alt_path
                        break
                else:
                    logger.warning("Could not find tree-sitter-languages shared library")
                    return
            
            self._lib = ctypes.CDLL(str(lib_path))
            
            # Load bundled languages
            bundled_languages = [
                'python', 'javascript', 'typescript', 'java', 'c', 'cpp', 'rust', 'go'
            ]
            
            for lang in bundled_languages:
                try:
                    func_name = f"tree_sitter_{lang}"
                    if hasattr(self._lib, func_name):
                        func = getattr(self._lib, func_name)
                        func.restype = ctypes.c_void_p
                        language = Language(func())
                        parser = Parser()
                        parser.language = language
                        
                        self._languages[lang] = language
                        self._parsers[lang] = parser
                        self._available_languages.add(lang)
                        
                        logger.debug(f"Loaded bundled parser for {lang}")
                
                except Exception as e:
                    logger.debug(f"Failed to load bundled parser for {lang}: {e}")
                    
        except Exception as e:
            logger.warning(f"Failed to load tree-sitter-languages bundle: {e}")

    def _load_individual_languages(self) -> None:
        """Load individual language parsers."""
        for lang, (module_name, _) in LANGUAGE_IMPORTS.items():
            if lang in self._available_languages:
                continue  # Already loaded from bundle
            
            try:
                module = __import__(module_name)
                
                # Get the language function
                if hasattr(module, 'language'):
                    language = module.language()
                elif hasattr(module, f'tree_sitter_{lang}'):
                    language = getattr(module, f'tree_sitter_{lang}')()
                else:
                    # Try common naming patterns
                    for attr_name in [f'language', f'{lang}_language', f'tree_sitter_{lang}']:
                        if hasattr(module, attr_name):
                            language = getattr(module, attr_name)()
                            break
                    else:
                        logger.debug(f"Could not find language function in {module_name}")
                        continue
                
                parser = Parser()
                parser.language = language
                
                self._languages[lang] = language
                self._parsers[lang] = parser
                self._available_languages.add(lang)
                
                logger.debug(f"Loaded individual parser for {lang}")
                
            except ImportError:
                logger.debug(f"Parser module {module_name} not available for {lang}")
            except Exception as e:
                logger.debug(f"Failed to load parser for {lang}: {e}")

    def get_parser(self, language: str) -> Optional[Parser]:
        """Get a parser for the specified language.
        
        Args:
            language: Language name (e.g., 'python', 'javascript')
            
        Returns:
            Parser instance if available, None otherwise
        """
        return self._parsers.get(language)

    def get_language(self, language: str) -> Optional[Language]:
        """Get a language instance for the specified language.
        
        Args:
            language: Language name (e.g., 'python', 'javascript')
            
        Returns:
            Language instance if available, None otherwise
        """
        return self._languages.get(language)

    def detect_language(self, file_path: Union[str, Path]) -> Optional[str]:
        """Detect the programming language based on file extension.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Language name if detected, None otherwise
        """
        if isinstance(file_path, str):
            file_path = Path(file_path)
        
        extension = file_path.suffix.lower()
        return EXTENSION_TO_LANGUAGE.get(extension)

    def parse_file(self, file_path: Union[str, Path], language: Optional[str] = None) -> Optional[Node]:
        """Parse a file and return the root node.
        
        Args:
            file_path: Path to the file to parse
            language: Language to use (auto-detected if not provided)
            
        Returns:
            Root node of the parsed tree, None if parsing failed
        """
        if isinstance(file_path, str):
            file_path = Path(file_path)
        
        if not file_path.exists():
            logger.error(f"File does not exist: {file_path}")
            return None
        
        # Detect language if not provided
        if language is None:
            language = self.detect_language(file_path)
            if language is None:
                logger.warning(f"Could not detect language for {file_path}")
                return None
        
        # Get parser
        parser = self.get_parser(language)
        if parser is None:
            logger.warning(f"No parser available for language: {language}")
            return None
        
        try:
            content = file_path.read_bytes()
            tree = parser.parse(content)
            return tree.root_node
        except Exception as e:
            logger.error(f"Failed to parse {file_path}: {e}")
            return None

    def parse_content(self, content: Union[str, bytes], language: str) -> Optional[Node]:
        """Parse content and return the root node.
        
        Args:
            content: Content to parse
            language: Language of the content
            
        Returns:
            Root node of the parsed tree, None if parsing failed
        """
        parser = self.get_parser(language)
        if parser is None:
            logger.warning(f"No parser available for language: {language}")
            return None
        
        try:
            if isinstance(content, str):
                content = content.encode('utf-8')
            
            tree = parser.parse(content)
            return tree.root_node
        except Exception as e:
            logger.error(f"Failed to parse content: {e}")
            return None

    def is_language_supported(self, language: str) -> bool:
        """Check if a language is supported.
        
        Args:
            language: Language name to check
            
        Returns:
            True if language is supported, False otherwise
        """
        return language in self._available_languages

    def get_supported_languages(self) -> Set[str]:
        """Get the set of supported languages.
        
        Returns:
            Set of supported language names
        """
        return self._available_languages.copy()

    def get_supported_extensions(self) -> Set[str]:
        """Get the set of supported file extensions.
        
        Returns:
            Set of supported file extensions
        """
        return {ext for ext, lang in EXTENSION_TO_LANGUAGE.items() 
                if lang in self._available_languages}

    def to_sexp(self, node: Node) -> str:
        """Convert a node to S-expression representation.
        
        Args:
            node: Tree-sitter node
            
        Returns:
            S-expression string representation
        """
        if node.child_count == 0:
            return node.type

        parts = []
        for i in range(node.child_count):
            child = node.child(i)
            child_sexp = self.to_sexp(child)
            field = node.field_name_for_child(i)
            if field:
                parts.append(f"{field}: {child_sexp}")
            else:
                parts.append(child_sexp)
        return f"({node.type} {' '.join(parts)})"


# Global instance
_tree_sitter_manager = None


def get_tree_sitter_manager() -> TreeSitterManager:
    """Get the global Tree-sitter manager instance.
    
    Returns:
        TreeSitterManager instance
    """
    global _tree_sitter_manager
    if _tree_sitter_manager is None:
        _tree_sitter_manager = TreeSitterManager()
    return _tree_sitter_manager


def parse_file(file_path: Union[str, Path], language: Optional[str] = None) -> Optional[Node]:
    """Convenience function to parse a file.
    
    Args:
        file_path: Path to the file to parse
        language: Language to use (auto-detected if not provided)
        
    Returns:
        Root node of the parsed tree, None if parsing failed
    """
    manager = get_tree_sitter_manager()
    return manager.parse_file(file_path, language)


def parse_content(content: Union[str, bytes], language: str) -> Optional[Node]:
    """Convenience function to parse content.
    
    Args:
        content: Content to parse
        language: Language of the content
        
    Returns:
        Root node of the parsed tree, None if parsing failed
    """
    manager = get_tree_sitter_manager()
    return manager.parse_content(content, language)


def is_language_supported(language: str) -> bool:
    """Check if a language is supported.
    
    Args:
        language: Language name to check
        
    Returns:
        True if language is supported, False otherwise
    """
    manager = get_tree_sitter_manager()
    return manager.is_language_supported(language)


def get_supported_languages() -> Set[str]:
    """Get the set of supported languages.
    
    Returns:
        Set of supported language names
    """
    manager = get_tree_sitter_manager()
    return manager.get_supported_languages()