"""Comprehensive plugin template system for new language plugins."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum

from ..plugin_base import (
    IPlugin,
    IndexShard,
    SymbolDef,
    Reference,
    SearchResult,
    SearchOpts,
)
from ..core.logging import get_logger
from ..utils.smart_parser import SmartParser
from ..utils.fuzzy_indexer import FuzzyIndexer
from ..storage.sqlite_store import SQLiteStore
from ..cache.cache_manager import CacheManager


class SymbolType(Enum):
    """Standard symbol types across languages."""
    FUNCTION = "function"
    CLASS = "class"
    INTERFACE = "interface"
    STRUCT = "struct"
    ENUM = "enum"
    VARIABLE = "variable"
    CONSTANT = "constant"
    MODULE = "module"
    NAMESPACE = "namespace"
    IMPORT = "import"
    TYPE = "type"
    FIELD = "field"
    METHOD = "method"
    PROPERTY = "property"
    DECORATOR = "decorator"
    ANNOTATION = "annotation"
    COMMENT = "comment"
    UNKNOWN = "unknown"


@dataclass
class ParsedSymbol:
    """Standardized symbol representation."""
    name: str
    symbol_type: SymbolType
    line: int
    column: int = 0
    end_line: int = 0
    end_column: int = 0
    signature: Optional[str] = None
    docstring: Optional[str] = None
    scope: Optional[str] = None
    modifiers: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PluginConfig:
    """Configuration for plugin behavior."""
    # Cache settings
    enable_caching: bool = True
    cache_ttl: int = 3600  # 1 hour
    max_cache_size: int = 1000
    
    # Performance settings
    async_processing: bool = True
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    batch_size: int = 100
    
    # Parser settings
    preferred_backend: Optional[str] = None
    enable_fallback: bool = True
    strict_mode: bool = False
    
    # Feature flags
    enable_semantic_analysis: bool = True
    enable_cross_references: bool = True
    enable_documentation_extraction: bool = True


class PluginError(Exception):
    """Base exception for plugin errors."""
    pass


class ParsingError(PluginError):
    """Error during file parsing."""
    pass


class LanguagePluginBase(IPlugin, ABC):
    """Enhanced base class for all language plugins."""
    
    def __init__(
        self,
        config: Optional[PluginConfig] = None,
        sqlite_store: Optional[SQLiteStore] = None,
        cache_manager: Optional[CacheManager] = None
    ):
        """Initialize the plugin with configuration and optional services."""
        self.config = config or PluginConfig()
        self.logger = get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        
        # Services
        self._sqlite_store = sqlite_store
        self._cache_manager = cache_manager
        self._fuzzy_indexer = FuzzyIndexer(sqlite_store=sqlite_store)
        
        # Plugin metadata (to be set by subclasses)
        self.lang = self.get_language()
        self.supported_extensions = self.get_supported_extensions()
        self.symbol_patterns = self.get_symbol_patterns()
        
        # State
        self._repository_id: Optional[int] = None
        self._initialized = False
        self._parser: Optional[SmartParser] = None
        
        # Initialize plugin
        self._initialize()
    
    def _initialize(self) -> None:
        """Initialize the plugin components."""
        try:
            # Initialize parser if Tree-sitter or language-specific parsing is available
            if self.config.preferred_backend or self.supports_tree_sitter():
                self._parser = SmartParser(
                    self.lang, 
                    preferred_backend=self.config.preferred_backend
                )
                self.logger.info(f"Initialized parser with {self._parser.get_backend_name()} backend")
            
            # Set up repository if SQLite is available
            if self._sqlite_store:
                self._repository_id = self._sqlite_store.create_repository(
                    str(Path.cwd()),
                    Path.cwd().name,
                    {"language": self.lang, "plugin": self.__class__.__name__}
                )
            
            self._initialized = True
            self.logger.info(f"Plugin {self.__class__.__name__} initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize plugin: {e}")
            if self.config.strict_mode:
                raise PluginError(f"Plugin initialization failed: {e}") from e
    
    # Abstract methods that subclasses must implement
    
    @abstractmethod
    def get_language(self) -> str:
        """Return the language this plugin supports."""
        pass
    
    @abstractmethod
    def get_supported_extensions(self) -> List[str]:
        """Return list of file extensions this plugin supports."""
        pass
    
    @abstractmethod
    def get_symbol_patterns(self) -> Dict[SymbolType, str]:
        """Return regex patterns for different symbol types."""
        pass
    
    def supports_tree_sitter(self) -> bool:
        """Return True if this plugin supports Tree-sitter parsing."""
        return True
    
    # IPlugin interface implementation
    
    def supports(self, path: str | Path) -> bool:
        """Check if this plugin supports the given file."""
        path = Path(path) if isinstance(path, str) else path
        return path.suffix.lower() in self.supported_extensions
    
    def indexFile(self, path: str | Path, content: str) -> IndexShard:
        """Index a file and extract symbols."""
        if not self._initialized:
            raise PluginError("Plugin not initialized")
        
        path = Path(path) if isinstance(path, str) else path
        
        # Check file size
        if len(content) > self.config.max_file_size:
            self.logger.warning(f"File {path} exceeds max size, skipping")
            return {"file": str(path), "symbols": [], "language": self.lang}
        
        # Check cache first
        cache_key = self._get_cache_key(str(path), content)
        if self.config.enable_caching and self._cache_manager:
            cached_result = self._cache_manager.get(cache_key)
            if cached_result:
                self.logger.debug(f"Using cached result for {path}")
                return cached_result
        
        try:
            # Parse and extract symbols
            symbols = self._extract_symbols(content, str(path))
            
            # Convert to IndexShard format
            shard = self._create_index_shard(str(path), symbols)
            
            # Store in fuzzy indexer
            self._fuzzy_indexer.add_file(str(path), content)
            
            # Store in SQLite if available
            if self._sqlite_store and self._repository_id:
                self._store_file_and_symbols(path, content, symbols)
            
            # Cache result
            if self.config.enable_caching and self._cache_manager:
                self._cache_manager.set(cache_key, shard, ttl=self.config.cache_ttl)
            
            self.logger.debug(f"Indexed {path} with {len(symbols)} symbols")
            return shard
            
        except Exception as e:
            self.logger.error(f"Failed to index {path}: {e}")
            if self.config.strict_mode:
                raise ParsingError(f"Failed to parse {path}: {e}") from e
            return {"file": str(path), "symbols": [], "language": self.lang}
    
    def getDefinition(self, symbol: str) -> SymbolDef | None:
        """Get the definition of a symbol."""
        if self._sqlite_store:
            # Use database for efficient lookup
            result = self._sqlite_store.find_symbol_definition(symbol, self.lang)
            if result:
                return self._convert_to_symbol_def(result)
        
        # Fallback to manual search
        return self._search_symbol_definition(symbol)
    
    def findReferences(self, symbol: str) -> list[Reference]:
        """Find all references to a symbol."""
        if self._sqlite_store:
            # Use database for efficient lookup
            results = self._sqlite_store.find_symbol_references(symbol, self.lang)
            return [Reference(file=r["file"], line=r["line"]) for r in results]
        
        # Fallback to manual search
        return self._search_symbol_references(symbol)
    
    def search(self, query: str, opts: SearchOpts | None = None) -> list[SearchResult]:
        """Search for code patterns."""
        opts = opts or {}
        limit = opts.get("limit", 20)
        
        if opts.get("semantic") and self.config.enable_semantic_analysis:
            # TODO: Implement semantic search
            self.logger.warning("Semantic search not yet implemented")
            return []
        
        # Use fuzzy indexer for text search
        results = self._fuzzy_indexer.search(query, limit=limit)
        return [
            {"file": r["file"], "line": r["line"], "snippet": r["snippet"]}
            for r in results
        ]
    
    # Protected methods for subclasses to override
    
    def _extract_symbols(self, content: str, file_path: str) -> List[ParsedSymbol]:
        """Extract symbols from file content."""
        symbols = []
        
        # Try Tree-sitter first if available
        if self._parser and self.supports_tree_sitter():
            try:
                symbols = self._extract_symbols_tree_sitter(content, file_path)
                self.logger.debug(f"Extracted {len(symbols)} symbols using Tree-sitter")
            except Exception as e:
                self.logger.warning(f"Tree-sitter parsing failed: {e}")
                if not self.config.enable_fallback:
                    raise
        
        # Fallback to regex-based extraction
        if not symbols and self.config.enable_fallback:
            symbols = self._extract_symbols_regex(content, file_path)
            self.logger.debug(f"Extracted {len(symbols)} symbols using regex")
        
        return symbols
    
    def _extract_symbols_tree_sitter(self, content: str, file_path: str) -> List[ParsedSymbol]:
        """Extract symbols using Tree-sitter (to be implemented by subclasses)."""
        # This should be implemented by Tree-sitter-based plugins
        return []
    
    def _extract_symbols_regex(self, content: str, file_path: str) -> List[ParsedSymbol]:
        """Extract symbols using regex patterns."""
        symbols = []
        lines = content.splitlines()
        
        for symbol_type, pattern in self.symbol_patterns.items():
            for line_no, line in enumerate(lines, 1):
                matches = re.finditer(pattern, line)
                for match in matches:
                    name = match.group(1) if match.groups() else match.group(0)
                    symbol = ParsedSymbol(
                        name=name,
                        symbol_type=symbol_type,
                        line=line_no,
                        column=match.start(),
                        signature=line.strip(),
                        metadata={"pattern_match": True}
                    )
                    symbols.append(symbol)
        
        return symbols
    
    # Helper methods
    
    def _get_cache_key(self, file_path: str, content: str) -> str:
        """Generate cache key for file content."""
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        return f"{self.lang}:{Path(file_path).name}:{content_hash}"
    
    def _create_index_shard(self, file_path: str, symbols: List[ParsedSymbol]) -> IndexShard:
        """Convert parsed symbols to IndexShard format."""
        symbol_dicts = []
        for symbol in symbols:
            symbol_dicts.append({
                "symbol": symbol.name,
                "kind": symbol.symbol_type.value,
                "signature": symbol.signature or "",
                "line": symbol.line,
                "span": (symbol.line, symbol.end_line or symbol.line),
                "docstring": symbol.docstring,
                "scope": symbol.scope,
                "modifiers": list(symbol.modifiers),
                "metadata": symbol.metadata
            })
        
        return {
            "file": file_path,
            "symbols": symbol_dicts,
            "language": self.lang
        }
    
    def _store_file_and_symbols(self, path: Path, content: str, symbols: List[ParsedSymbol]) -> None:
        """Store file and symbols in SQLite database."""
        if not self._sqlite_store or not self._repository_id:
            return
        
        try:
            # Store file
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            relative_path = str(path.relative_to(Path.cwd())) if path.is_relative_to(Path.cwd()) else str(path)
            
            file_id = self._sqlite_store.store_file(
                self._repository_id,
                str(path),
                relative_path,
                language=self.lang,
                size=len(content),
                hash=content_hash
            )
            
            # Store symbols
            for symbol in symbols:
                symbol_id = self._sqlite_store.store_symbol(
                    file_id,
                    symbol.name,
                    symbol.symbol_type.value,
                    symbol.line,
                    symbol.end_line or symbol.line,
                    signature=symbol.signature,
                    docstring=symbol.docstring,
                    scope=symbol.scope
                )
                
                # Add to fuzzy indexer with metadata
                self._fuzzy_indexer.add_symbol(
                    symbol.name,
                    str(path),
                    symbol.line,
                    {"symbol_id": symbol_id, "file_id": file_id}
                )
                
        except Exception as e:
            self.logger.error(f"Failed to store file and symbols: {e}")
    
    def _convert_to_symbol_def(self, db_result: Dict[str, Any]) -> SymbolDef:
        """Convert database result to SymbolDef."""
        return {
            "symbol": db_result["name"],
            "kind": db_result["kind"],
            "language": self.lang,
            "signature": db_result.get("signature", ""),
            "doc": db_result.get("docstring"),
            "defined_in": db_result["file_path"],
            "line": db_result["start_line"],
            "span": (db_result["start_line"], db_result["end_line"])
        }
    
    def _search_symbol_definition(self, symbol: str) -> SymbolDef | None:
        """Manual search for symbol definition (fallback)."""
        # This is a basic implementation - subclasses can override for language-specific logic
        for path in Path(".").rglob(f"*.{self.supported_extensions[0].lstrip('.')}"):
            if not path.is_file():
                continue
            try:
                content = path.read_text(encoding='utf-8')
                symbols = self._extract_symbols(content, str(path))
                for s in symbols:
                    if s.name == symbol:
                        return {
                            "symbol": s.name,
                            "kind": s.symbol_type.value,
                            "language": self.lang,
                            "signature": s.signature or "",
                            "doc": s.docstring,
                            "defined_in": str(path),
                            "line": s.line,
                            "span": (s.line, s.end_line or s.line)
                        }
            except Exception:
                continue
        return None
    
    def _search_symbol_references(self, symbol: str) -> List[Reference]:
        """Manual search for symbol references (fallback)."""
        references = []
        seen = set()
        
        for path in Path(".").rglob(f"*.{self.supported_extensions[0].lstrip('.')}"):
            if not path.is_file():
                continue
            try:
                content = path.read_text(encoding='utf-8')
                lines = content.splitlines()
                for line_no, line in enumerate(lines, 1):
                    if symbol in line:
                        key = (str(path), line_no)
                        if key not in seen:
                            references.append(Reference(file=str(path), line=line_no))
                            seen.add(key)
            except Exception:
                continue
        
        return references
    
    # Utility methods for plugin developers
    
    def get_plugin_info(self) -> Dict[str, Any]:
        """Get information about this plugin."""
        return {
            "name": self.__class__.__name__,
            "language": self.lang,
            "extensions": self.supported_extensions,
            "initialized": self._initialized,
            "parser_backend": self._parser.get_backend_name() if self._parser else None,
            "supports_tree_sitter": self.supports_tree_sitter(),
            "config": {
                "caching_enabled": self.config.enable_caching,
                "async_processing": self.config.async_processing,
                "semantic_analysis": self.config.enable_semantic_analysis
            }
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get plugin statistics."""
        stats = {
            "indexed_files": self._fuzzy_indexer.get_stats().get("files", 0),
            "total_symbols": self._fuzzy_indexer.get_stats().get("symbols", 0)
        }
        
        if self._sqlite_store:
            db_stats = self._sqlite_store.get_statistics()
            stats.update({
                "db_files": db_stats.get("files", 0),
                "db_symbols": db_stats.get("symbols", 0)
            })
        
        return stats
