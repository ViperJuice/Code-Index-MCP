"""Smart parser system that intelligently selects between different parsing backends.

This module provides a unified interface for parsing code across multiple languages,
with the ability to fall back between different parser implementations based on
availability and performance characteristics.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional, Protocol, runtime_checkable
from abc import ABC, abstractmethod

from tree_sitter import Language, Parser, Node
import tree_sitter_languages
from tree_sitter_languages import get_language, get_parser

logger = logging.getLogger(__name__)


@runtime_checkable
class IParserBackend(Protocol):
    """Protocol for parser backends."""
    
    @property
    def name(self) -> str:
        """Return the name of this parser backend."""
        ...
    
    @property
    def supported_languages(self) -> set[str]:
        """Return the set of languages this backend supports."""
        ...
    
    def parse(self, content: bytes, language: str) -> Any:
        """Parse content and return the AST."""
        ...
    
    def is_available(self) -> bool:
        """Check if this parser backend is available."""
        ...


class TreeSitterBackend:
    """Tree-sitter based parser backend."""
    
    def __init__(self):
        self.name = "tree-sitter"
        self._parsers = {}
        self._languages = {}
        self._lib = None
        self._initialize()
    
    def _initialize(self):
        """Initialize tree-sitter languages."""
        try:
            # Languages we want to support
            languages = [
                'python', 'javascript', 'typescript', 'rust', 'go',
                'cpp', 'c', 'java', 'ruby', 'php', 'json'
            ]
            
            for lang in languages:
                try:
                    # Use tree-sitter-languages for better compatibility
                    self._languages[lang] = get_language(lang)
                    self._parsers[lang] = get_parser(lang)
                    logger.debug(f"Initialized tree-sitter parser for {lang}")
                except Exception as e:
                    logger.warning(f"Failed to initialize tree-sitter for {lang}: {e}")
                        
        except Exception as e:
            logger.error(f"Failed to initialize tree-sitter backend: {e}")
    
    @property
    def supported_languages(self) -> set[str]:
        """Return supported languages."""
        return set(self._parsers.keys())
    
    def parse(self, content: bytes, language: str) -> Optional[Node]:
        """Parse content using tree-sitter."""
        if language not in self._parsers:
            raise ValueError(f"Language {language} not supported by tree-sitter backend")
        
        parser = self._parsers[language]
        # Convert string to bytes if needed
        if isinstance(content, str):
            content = content.encode('utf-8')
        tree = parser.parse(content)
        return tree.root_node
    
    def is_available(self) -> bool:
        """Check if tree-sitter is available."""
        return bool(self._parsers)


class ASTBackend:
    """Python AST based parser backend (Python only)."""
    
    def __init__(self):
        self.name = "ast"
        self.supported_languages = {"python"}
    
    def parse(self, content: bytes, language: str):
        """Parse Python code using the ast module."""
        if language != "python":
            raise ValueError(f"AST backend only supports Python, not {language}")
        
        import ast
        try:
            return ast.parse(content.decode('utf-8'))
        except Exception as e:
            logger.error(f"AST parsing failed: {e}")
            raise
    
    def is_available(self) -> bool:
        """AST module is always available for Python."""
        return True


class SmartParser:
    """Smart parser that selects the best available backend for each language."""
    
    def __init__(self, language: str, preferred_backend: Optional[str] = None):
        """Initialize SmartParser for a specific language.
        
        Args:
            language: The programming language to parse
            preferred_backend: Preferred parser backend (optional)
        """
        self.language = language
        self.backends = []
        self._current_backend = None
        self._parser = None  # For compatibility
        
        # Initialize available backends
        self._initialize_backends()
        
        # Select backend
        self._select_backend(preferred_backend)
        
        logger.info(f"SmartParser initialized for {language} using {self._current_backend.name if self._current_backend else 'no'} backend")
    
    def _initialize_backends(self):
        """Initialize all available backends."""
        # Try tree-sitter first (most feature-rich)
        try:
            ts_backend = TreeSitterBackend()
            if ts_backend.is_available() and self.language in ts_backend.supported_languages:
                self.backends.append(ts_backend)
        except Exception as e:
            logger.warning(f"Tree-sitter backend initialization failed: {e}")
        
        # Add AST backend for Python
        if self.language == "python":
            try:
                ast_backend = ASTBackend()
                if ast_backend.is_available():
                    self.backends.append(ast_backend)
            except Exception as e:
                logger.warning(f"AST backend initialization failed: {e}")
    
    def _select_backend(self, preferred_backend: Optional[str] = None):
        """Select the best available backend."""
        if preferred_backend:
            for backend in self.backends:
                if backend.name == preferred_backend:
                    self._current_backend = backend
                    logger.info(f"Using preferred backend: {backend.name}")
                    break
        
        if not self._current_backend and self.backends:
            # Default to first available backend
            self._current_backend = self.backends[0]
            logger.info(f"Using default backend: {self._current_backend.name}")
        
        # Set up compatibility attributes
        if self._current_backend and self._current_backend.name == "tree-sitter":
            # For backward compatibility with code expecting _parser attribute
            if self.language in self._current_backend._parsers:
                self._parser = self._current_backend._parsers[self.language]
    
    def parse(self, content: bytes) -> Any:
        """Parse content using the selected backend.
        
        Args:
            content: The source code to parse as bytes
            
        Returns:
            Parsed AST (format depends on backend)
        """
        if not self._current_backend:
            raise RuntimeError(f"No parser backend available for {self.language}")
        
        result = self._current_backend.parse(content, self.language)
        logger.debug(f"Parsed {len(content)} bytes using {self._current_backend.name}")
        return result
    
    def get_backend_name(self) -> str:
        """Get the name of the current backend."""
        return self._current_backend.name if self._current_backend else "none"
    
    def switch_backend(self, backend_name: str):
        """Switch to a different backend if available."""
        for backend in self.backends:
            if backend.name == backend_name:
                self._current_backend = backend
                logger.info(f"Switched to backend: {backend_name}")
                return
        
        raise ValueError(f"Backend {backend_name} not available for {self.language}")
    
    @property
    def available_backends(self) -> list[str]:
        """List available backend names."""
        return [b.name for b in self.backends]