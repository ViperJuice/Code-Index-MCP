"""Registry for regex-based language parsers.

This module provides a registry system for managing language-specific regex parsers.
"""

from typing import Dict, Type, Optional
from ..regex_parser import RegexParser


class ParserRegistry:
    """Registry for managing regex parsers by language."""
    
    def __init__(self):
        self._parsers: Dict[str, Type[RegexParser]] = {}
        self._instances: Dict[str, RegexParser] = {}
    
    def register(self, language: str, parser_class: Type[RegexParser]) -> None:
        """Register a parser class for a language.
        
        Args:
            language: Language identifier (e.g., 'python', 'javascript')
            parser_class: Parser class to register
        """
        self._parsers[language.lower()] = parser_class
    
    def get_parser(self, language: str, use_unicode: bool = True) -> Optional[RegexParser]:
        """Get a parser instance for a language.
        
        Args:
            language: Language identifier
            use_unicode: Whether to use Unicode patterns
            
        Returns:
            Parser instance or None if not found
        """
        lang_key = language.lower()
        cache_key = f"{lang_key}_{use_unicode}"
        
        if cache_key not in self._instances:
            parser_class = self._parsers.get(lang_key)
            if parser_class:
                self._instances[cache_key] = parser_class(use_unicode=use_unicode)
            else:
                return None
        
        return self._instances.get(cache_key)
    
    def list_languages(self) -> list[str]:
        """List all registered languages."""
        return list(self._parsers.keys())


# Global registry instance
registry = ParserRegistry()


# Import and register parsers
from .python_parser import PythonRegexParser
from .javascript_parser import JavaScriptRegexParser
from .go_parser import GoRegexParser

registry.register('python', PythonRegexParser)
registry.register('javascript', JavaScriptRegexParser)
registry.register('js', JavaScriptRegexParser)  # Alias
registry.register('typescript', JavaScriptRegexParser)  # TypeScript uses same parser
registry.register('ts', JavaScriptRegexParser)  # Alias
registry.register('go', GoRegexParser)


# Export convenience functions
def get_parser(language: str, use_unicode: bool = True) -> Optional[RegexParser]:
    """Get a parser for the specified language."""
    return registry.get_parser(language, use_unicode)


def parse_file(content: str, language: str, path: Optional[str] = None, 
               use_unicode: bool = True):
    """Parse a file with the appropriate language parser.
    
    Args:
        content: Source code content
        language: Programming language
        path: Optional file path
        use_unicode: Whether to use Unicode patterns
        
    Returns:
        ParseResult or None if parser not found
    """
    parser = get_parser(language, use_unicode)
    if parser:
        from pathlib import Path
        return parser.parse(content, Path(path) if path else None)
    return None


__all__ = ['registry', 'get_parser', 'parse_file']