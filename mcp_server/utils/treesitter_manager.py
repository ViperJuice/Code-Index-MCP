"""
Tree-sitter Manager Utility

A comprehensive wrapper for Tree-sitter that provides:
- Parser instance management and caching
- Dynamic loading of language parsers
- Unified interface for multiple languages
- Error handling for missing parsers
- Synchronous and asynchronous parsing
- Performance monitoring and caching
- Query utilities for symbol extraction

This manager abstracts away low-level details like parser compilation,
query management, and error handling, providing a clean interface for plugins.
"""

from __future__ import annotations

import asyncio
import ctypes
import hashlib
import logging
import time
import weakref
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union, Callable
from collections import defaultdict
import threading

from tree_sitter import Language, Parser, Node, Query
import tree_sitter_languages

from ..interfaces.cache_interfaces import CacheEntry, CacheStats
from ..performance.memory_optimizer import memory_optimizer

logger = logging.getLogger(__name__)


@dataclass
class ParseResult:
    """Result of parsing operation."""
    root_node: Node
    parse_time_ms: float
    source_hash: str
    language: str
    cached: bool = False
    error: Optional[str] = None


@dataclass
class ParserStats:
    """Statistics for a parser instance."""
    language: str
    total_parses: int = 0
    total_parse_time_ms: float = 0.0
    average_parse_time_ms: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    last_used: datetime = field(default_factory=datetime.now)
    created_at: datetime = field(default_factory=datetime.now)
    memory_usage_bytes: int = 0


@dataclass
class QueryPattern:
    """Pre-compiled query pattern."""
    name: str
    query_string: str
    query: Query
    language: str
    usage_count: int = 0
    last_used: datetime = field(default_factory=datetime.now)


class ParserCache:
    """Thread-safe cache for parser instances."""
    
    def __init__(self, max_size: int = 50):
        self.max_size = max_size
        self._parsers: Dict[str, Parser] = {}
        self._languages: Dict[str, Language] = {}
        self._stats: Dict[str, ParserStats] = {}
        self._access_order: List[str] = []
        self._lock = threading.RLock()
    
    def get_parser(self, language: str) -> Optional[Parser]:
        """Get parser for language, creating if needed."""
        with self._lock:
            if language in self._parsers:
                # Update access order
                self._access_order.remove(language)
                self._access_order.append(language)
                self._stats[language].last_used = datetime.now()
                return self._parsers[language]
            
            return None
    
    def set_parser(self, language: str, parser: Parser, lang_obj: Language) -> None:
        """Store parser in cache."""
        with self._lock:
            # Evict if necessary
            if len(self._parsers) >= self.max_size and language not in self._parsers:
                self._evict_lru()
            
            self._parsers[language] = parser
            self._languages[language] = lang_obj
            
            if language not in self._stats:
                self._stats[language] = ParserStats(language=language)
            
            # Update access order
            if language in self._access_order:
                self._access_order.remove(language)
            self._access_order.append(language)
    
    def _evict_lru(self) -> None:
        """Evict least recently used parser."""
        if not self._access_order:
            return
        
        lru_language = self._access_order.pop(0)
        if lru_language in self._parsers:
            logger.debug(f"Evicting parser for language: {lru_language}")
            del self._parsers[lru_language]
            del self._languages[lru_language]
            # Keep stats for reporting
    
    def get_stats(self) -> Dict[str, ParserStats]:
        """Get cache statistics."""
        with self._lock:
            return self._stats.copy()
    
    def clear(self) -> None:
        """Clear the cache."""
        with self._lock:
            self._parsers.clear()
            self._languages.clear()
            self._access_order.clear()


class ParseCache:
    """Cache for parsed ASTs."""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: List[str] = []
        self._lock = threading.RLock()
    
    def _make_key(self, content_hash: str, language: str) -> str:
        """Create cache key."""
        return f"{language}:{content_hash}"
    
    def get(self, content_hash: str, language: str) -> Optional[Node]:
        """Get cached parse result."""
        key = self._make_key(content_hash, language)
        
        with self._lock:
            if key not in self._cache:
                return None
            
            entry = self._cache[key]
            
            # Check expiration
            if entry.expires_at and datetime.now() > entry.expires_at:
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
                return None
            
            # Update access
            entry.access_count += 1
            entry.last_accessed = datetime.now()
            
            # Update access order
            self._access_order.remove(key)
            self._access_order.append(key)
            
            return entry.value
    
    def set(self, content_hash: str, language: str, node: Node) -> None:
        """Cache parse result."""
        key = self._make_key(content_hash, language)
        
        with self._lock:
            # Evict if necessary
            if len(self._cache) >= self.max_size and key not in self._cache:
                self._evict_lru()
            
            expires_at = datetime.now() + timedelta(seconds=self.ttl_seconds)
            
            entry = CacheEntry(
                key=key,
                value=node,
                created_at=datetime.now(),
                expires_at=expires_at,
                access_count=1,
                last_accessed=datetime.now(),
                size_bytes=self._estimate_node_size(node)
            )
            
            self._cache[key] = entry
            
            # Update access order
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)
    
    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if not self._access_order:
            return
        
        lru_key = self._access_order.pop(0)
        if lru_key in self._cache:
            del self._cache[lru_key]
    
    def _estimate_node_size(self, node: Node) -> int:
        """Estimate memory size of a node."""
        # Rough estimation - in practice this would be more sophisticated
        return len(str(node)) * 2  # Approximate character size
    
    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        with self._lock:
            if not self._cache:
                return CacheStats(
                    total_entries=0,
                    hit_rate=0.0,
                    miss_rate=0.0,
                    eviction_count=0,
                    total_size_bytes=0,
                    average_entry_size=0.0,
                    oldest_entry=None,
                    newest_entry=None
                )
            
            total_size = sum(entry.size_bytes for entry in self._cache.values())
            total_accesses = sum(entry.access_count for entry in self._cache.values())
            
            entries = list(self._cache.values())
            oldest = min(entry.created_at for entry in entries)
            newest = max(entry.created_at for entry in entries)
            
            return CacheStats(
                total_entries=len(self._cache),
                hit_rate=0.0,  # Would need separate tracking
                miss_rate=0.0,  # Would need separate tracking
                eviction_count=0,  # Would need separate tracking
                total_size_bytes=total_size,
                average_entry_size=total_size / len(self._cache),
                oldest_entry=oldest,
                newest_entry=newest
            )
    
    def clear(self) -> None:
        """Clear the cache."""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()


class TreeSitterManager:
    """Comprehensive Tree-sitter manager with caching and performance monitoring."""
    
    # Language mappings for common aliases
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
    
    # Supported languages
    SUPPORTED_LANGUAGES = [
        'bash', 'c', 'c_sharp', 'commonlisp', 'cpp', 'css', 'dockerfile',
        'dot', 'elisp', 'elixir', 'elm', 'embedded_template', 'erlang',
        'fixed_form_fortran', 'fortran', 'go', 'gomod', 'hack', 'haskell',
        'hcl', 'html', 'java', 'javascript', 'jsdoc', 'json', 'julia',
        'kotlin', 'lua', 'make', 'markdown', 'objc', 'ocaml', 'perl', 'php',
        'python', 'ql', 'r', 'regex', 'rst', 'ruby', 'rust', 'scala', 'sql',
        'sqlite', 'toml', 'tsq', 'tsx', 'typescript', 'yaml'
    ]
    
    # Common query patterns for symbol extraction
    SYMBOL_QUERIES = {
        'python': {
            'functions': '(function_definition (identifier) @name) @function',
            'classes': '(class_definition (identifier) @name) @class',
            'methods': '(function_definition (identifier) @name) @method',
            'variables': '(assignment (identifier) @name) @variable',
            'imports': '(import_statement (dotted_name) @name) @import',
            'from_imports': '(import_from_statement (dotted_name) @module (dotted_name) @name) @import',
        },
        'javascript': {
            'functions': '(function_declaration name: (identifier) @name) @function',
            'arrow_functions': '(arrow_function) @function',
            'classes': '(class_declaration name: (identifier) @name) @class',
            'methods': '(method_definition name: (property_identifier) @name) @method',
            'variables': '(variable_declarator name: (identifier) @name) @variable',
            'imports': '(import_statement source: (string) @source) @import',
        },
        'typescript': {
            'functions': '(function_declaration name: (identifier) @name) @function',
            'classes': '(class_declaration name: (type_identifier) @name) @class',
            'interfaces': '(interface_declaration name: (type_identifier) @name) @interface',
            'types': '(type_alias_declaration name: (type_identifier) @name) @type',
            'methods': '(method_definition name: (property_identifier) @name) @method',
            'variables': '(variable_declarator name: (identifier) @name) @variable',
        },
        'java': {
            'classes': '(class_declaration name: (identifier) @name) @class',
            'interfaces': '(interface_declaration name: (identifier) @name) @interface',
            'methods': '(method_declaration name: (identifier) @name) @method',
            'fields': '(field_declaration declarator: (variable_declarator name: (identifier) @name)) @field',
            'enums': '(enum_declaration name: (identifier) @name) @enum',
            'packages': '(package_declaration (scoped_identifier) @name) @package',
            'imports': '(import_declaration (scoped_identifier) @name) @import',
        },
        'go': {
            'functions': '(function_declaration name: (identifier) @name) @function',
            'methods': '(method_declaration name: (field_identifier) @name) @method',
            'types': '(type_declaration (type_spec name: (type_identifier) @name)) @type',
            'variables': '(var_declaration (var_spec name: (identifier) @name)) @variable',
            'constants': '(const_declaration (const_spec name: (identifier) @name)) @constant',
            'packages': '(package_clause (package_identifier) @name) @package',
            'imports': '(import_declaration (import_spec path: (interpreted_string_literal) @path)) @import',
        },
        'rust': {
            'functions': '(function_item name: (identifier) @name) @function',
            'structs': '(struct_item name: (type_identifier) @name) @struct',
            'enums': '(enum_item name: (type_identifier) @name) @enum',
            'traits': '(trait_item name: (type_identifier) @name) @trait',
            'impls': '(impl_item type: (type_identifier) @name) @impl',
            'mods': '(mod_item name: (identifier) @name) @module',
            'use_declarations': '(use_declaration argument: (scoped_identifier) @name) @use',
        },
        'cpp': {
            'functions': '(function_definition declarator: (function_declarator declarator: (identifier) @name)) @function',
            'classes': '(class_specifier name: (type_identifier) @name) @class',
            'structs': '(struct_specifier name: (type_identifier) @name) @struct',
            'namespaces': '(namespace_definition name: (identifier) @name) @namespace',
            'methods': '(function_definition declarator: (function_declarator declarator: (identifier) @name)) @method',
            'includes': '(preproc_include path: (string_literal) @path) @include',
        }
    }
    
    def __init__(self, 
                 parser_cache_size: int = 50,
                 parse_cache_size: int = 1000,
                 parse_cache_ttl: int = 3600,
                 enable_monitoring: bool = True,
                 thread_pool_size: int = 4):
        """Initialize the Tree-sitter manager.
        
        Args:
            parser_cache_size: Maximum number of cached parser instances
            parse_cache_size: Maximum number of cached parse results
            parse_cache_ttl: TTL for cached parse results in seconds
            enable_monitoring: Whether to enable performance monitoring
            thread_pool_size: Size of thread pool for async operations
        """
        self.parser_cache = ParserCache(parser_cache_size)
        self.parse_cache = ParseCache(parse_cache_size, parse_cache_ttl)
        self.query_cache: Dict[str, QueryPattern] = {}
        self.enable_monitoring = enable_monitoring
        
        # Thread pool for async operations
        self.thread_pool = ThreadPoolExecutor(max_workers=thread_pool_size)
        
        # Performance tracking
        self.total_parses = 0
        self.total_parse_time_ms = 0.0
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Library path cache
        self._lib_path: Optional[Path] = None
        self._lib: Optional[ctypes.CDLL] = None
        self._lib_lock = threading.Lock()
        
        logger.info(f"TreeSitterManager initialized with caches: parser={parser_cache_size}, parse={parse_cache_size}")
    
    def _get_library_path(self) -> Path:
        """Get the path to the tree-sitter-languages shared library."""
        if self._lib_path is not None:
            return self._lib_path
        
        with self._lib_lock:
            if self._lib_path is not None:
                return self._lib_path
            
            # Find the shared library
            base_path = Path(tree_sitter_languages.__path__[0])
            for lib_name in ["languages.so", "languages.dylib", "languages.dll"]:
                lib_path = base_path / lib_name
                if lib_path.exists():
                    self._lib_path = lib_path
                    break
            
            if self._lib_path is None:
                raise RuntimeError("Could not find tree-sitter-languages shared library")
            
            return self._lib_path
    
    def _get_library(self) -> ctypes.CDLL:
        """Get the tree-sitter-languages shared library."""
        if self._lib is not None:
            return self._lib
        
        with self._lib_lock:
            if self._lib is not None:
                return self._lib
            
            lib_path = self._get_library_path()
            self._lib = ctypes.CDLL(str(lib_path))
            return self._lib
    
    def _normalize_language(self, language: str) -> str:
        """Normalize language name."""
        language = language.lower().strip()
        
        # Check direct mapping
        if language in self.LANGUAGE_MAPPINGS:
            return self.LANGUAGE_MAPPINGS[language]
        
        # Clean up common variations
        cleaned = language.replace('-', '_').replace(' ', '_')
        if cleaned in self.SUPPORTED_LANGUAGES:
            return cleaned
        
        return language
    
    def is_language_supported(self, language: str) -> bool:
        """Check if a language is supported."""
        normalized = self._normalize_language(language)
        return normalized in self.SUPPORTED_LANGUAGES
    
    def get_supported_languages(self) -> List[str]:
        """Get list of all supported languages including aliases."""
        languages = set(self.SUPPORTED_LANGUAGES)
        languages.update(self.LANGUAGE_MAPPINGS.keys())
        return sorted(languages)
    
    def _create_parser(self, language: str) -> Tuple[Parser, Language]:
        """Create a new parser for the given language."""
        normalized_lang = self._normalize_language(language)
        
        if normalized_lang not in self.SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language: {language}")
        
        # Create language object using the new API
        lang_obj = Language(str(self._get_library_path()), normalized_lang)
        
        parser = Parser()
        parser.set_language(lang_obj)
        
        # Track memory usage (skip if objects don't support weak references)
        if self.enable_monitoring:
            try:
                memory_optimizer.track_object(parser)
            except TypeError:
                pass  # Object doesn't support weak references
            try:
                memory_optimizer.track_object(lang_obj)
            except TypeError:
                pass  # Object doesn't support weak references
        
        return parser, lang_obj
    
    def get_parser(self, language: str) -> Parser:
        """Get a parser for the specified language."""
        normalized_lang = self._normalize_language(language)
        
        # Check cache first
        parser = self.parser_cache.get_parser(normalized_lang)
        if parser is not None:
            return parser
        
        # Create new parser
        parser, lang_obj = self._create_parser(language)
        
        # Cache the parser
        self.parser_cache.set_parser(normalized_lang, parser, lang_obj)
        
        logger.debug(f"Created new parser for language: {normalized_lang}")
        return parser
    
    def _hash_content(self, content: Union[str, bytes]) -> str:
        """Create hash of content for caching."""
        if isinstance(content, str):
            content = content.encode('utf-8')
        return hashlib.sha256(content).hexdigest()[:16]
    
    def parse(self, content: Union[str, bytes], language: str) -> ParseResult:
        """Parse content synchronously."""
        if isinstance(content, str):
            content_bytes = content.encode('utf-8')
        else:
            content_bytes = content
        
        content_hash = self._hash_content(content_bytes)
        normalized_lang = self._normalize_language(language)
        
        start_time = time.time()
        
        # Check parse cache
        cached_node = self.parse_cache.get(content_hash, normalized_lang)
        if cached_node is not None:
            parse_time_ms = (time.time() - start_time) * 1000
            self.cache_hits += 1
            
            return ParseResult(
                root_node=cached_node,
                parse_time_ms=parse_time_ms,
                source_hash=content_hash,
                language=normalized_lang,
                cached=True
            )
        
        self.cache_misses += 1
        
        try:
            # Get parser and parse
            parser = self.get_parser(language)
            tree = parser.parse(content_bytes)
            root_node = tree.root_node
            
            # Cache the result
            self.parse_cache.set(content_hash, normalized_lang, root_node)
            
            parse_time_ms = (time.time() - start_time) * 1000
            
            # Update statistics
            self.total_parses += 1
            self.total_parse_time_ms += parse_time_ms
            
            # Update parser stats
            stats = self.parser_cache.get_stats()
            if normalized_lang in stats:
                parser_stats = stats[normalized_lang]
                parser_stats.total_parses += 1
                parser_stats.total_parse_time_ms += parse_time_ms
                parser_stats.average_parse_time_ms = (
                    parser_stats.total_parse_time_ms / parser_stats.total_parses
                )
            
            return ParseResult(
                root_node=root_node,
                parse_time_ms=parse_time_ms,
                source_hash=content_hash,
                language=normalized_lang,
                cached=False
            )
            
        except Exception as e:
            error_msg = f"Failed to parse {language} content: {str(e)}"
            logger.error(error_msg)
            
            return ParseResult(
                root_node=None,
                parse_time_ms=(time.time() - start_time) * 1000,
                source_hash=content_hash,
                language=normalized_lang,
                error=error_msg
            )
    
    async def parse_async(self, content: Union[str, bytes], language: str) -> ParseResult:
        """Parse content asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.thread_pool, self.parse, content, language)
    
    def parse_file(self, file_path: Union[str, Path], language: Optional[str] = None) -> ParseResult:
        """Parse a file."""
        path = Path(file_path)
        
        if not path.exists():
            return ParseResult(
                root_node=None,
                parse_time_ms=0.0,
                source_hash="",
                language=language or "unknown",
                error=f"File not found: {path}"
            )
        
        # Detect language if not provided
        if language is None:
            language = self._detect_language_from_path(path)
        
        try:
            content = path.read_bytes()
            return self.parse(content, language)
        except Exception as e:
            return ParseResult(
                root_node=None,
                parse_time_ms=0.0,
                source_hash="",
                language=language,
                error=f"Failed to read file: {str(e)}"
            )
    
    async def parse_file_async(self, file_path: Union[str, Path], language: Optional[str] = None) -> ParseResult:
        """Parse a file asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.thread_pool, self.parse_file, file_path, language)
    
    def _detect_language_from_path(self, path: Path) -> str:
        """Detect programming language from file path."""
        suffix = path.suffix.lower()
        
        language_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'tsx',
            '.jsx': 'javascript',
            '.java': 'java',
            '.kt': 'kotlin',
            '.go': 'go',
            '.rs': 'rust',
            '.cpp': 'cpp',
            '.cxx': 'cpp',
            '.cc': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.hpp': 'cpp',
            '.cs': 'c_sharp',
            '.php': 'php',
            '.rb': 'ruby',
            '.swift': 'swift',
            '.scala': 'scala',
            '.clj': 'clojure',
            '.hs': 'haskell',
            '.ml': 'ocaml',
            '.sh': 'bash',
            '.bash': 'bash',
            '.zsh': 'bash',
            '.fish': 'bash',
            '.ps1': 'powershell',
            '.sql': 'sql',
            '.html': 'html',
            '.htm': 'html',
            '.css': 'css',
            '.scss': 'scss',
            '.sass': 'sass',
            '.less': 'less',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.toml': 'toml',
            '.xml': 'xml',
            '.md': 'markdown',
            '.markdown': 'markdown',
            '.rst': 'rst',
            '.tex': 'latex',
            '.r': 'r',
            '.R': 'r',
            '.jl': 'julia',
            '.lua': 'lua',
            '.vim': 'vim',
            '.dockerfile': 'dockerfile',
        }
        
        return language_map.get(suffix, 'text')
    
    def get_query(self, language: str, query_name: str) -> Optional[QueryPattern]:
        """Get a pre-compiled query for a language."""
        cache_key = f"{language}:{query_name}"
        
        if cache_key in self.query_cache:
            pattern = self.query_cache[cache_key]
            pattern.usage_count += 1
            pattern.last_used = datetime.now()
            return pattern
        
        # Check if we have this query pattern
        normalized_lang = self._normalize_language(language)
        if normalized_lang not in self.SYMBOL_QUERIES:
            return None
        
        lang_queries = self.SYMBOL_QUERIES[normalized_lang]
        if query_name not in lang_queries:
            return None
        
        # Create and compile query
        try:
            parser = self.get_parser(language)
            query_string = lang_queries[query_name]
            # Get the language from the parser cache
            if normalized_lang in self.parser_cache._languages:
                lang_obj = self.parser_cache._languages[normalized_lang]
            else:
                parser, lang_obj = self._create_parser(language)
            query = lang_obj.query(query_string)
            
            pattern = QueryPattern(
                name=query_name,
                query_string=query_string,
                query=query,
                language=normalized_lang,
                usage_count=1
            )
            
            self.query_cache[cache_key] = pattern
            return pattern
            
        except Exception as e:
            logger.error(f"Failed to compile query '{query_name}' for {language}: {e}")
            return None
    
    def query(self, content: Union[str, bytes], language: str, query_string: str) -> List[Dict[str, Any]]:
        """Execute a custom query on content."""
        parse_result = self.parse(content, language)
        
        if parse_result.error or parse_result.root_node is None:
            return []
        
        try:
            parser = self.get_parser(language)
            normalized_lang = self._normalize_language(language)
            # Get the language object from cache
            if normalized_lang in self.parser_cache._languages:
                lang_obj = self.parser_cache._languages[normalized_lang]
            else:
                parser, lang_obj = self._create_parser(language)
            query = lang_obj.query(query_string)
            
            matches = []
            for match in query.matches(parse_result.root_node):
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
                            'start_byte': node.start_byte,
                            'end_byte': node.end_byte,
                        }
                        for node in nodes
                    ]
                matches.append(match_info)
            
            return matches
            
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            return []
    
    def extract_symbols(self, content: Union[str, bytes], language: str, 
                       symbol_types: Optional[List[str]] = None) -> Dict[str, List[Dict[str, Any]]]:
        """Extract symbols from content using AST traversal (fallback for query issues)."""
        parse_result = self.parse(content, language)
        
        if parse_result.error or parse_result.root_node is None:
            return {}
        
        symbols = {
            'functions': [],
            'classes': [],
            'methods': [],
            'variables': [],
        }
        
        def traverse_node(node: Node, parent_type: Optional[str] = None):
            """Traverse AST and extract symbols."""
            node_type = node.type
            
            # Extract function definitions
            if node_type == 'function_definition':
                # Get function name (second child is usually the identifier)
                name_node = None
                for child in node.children:
                    if child.type == 'identifier':
                        name_node = child
                        break
                
                if name_node:
                    symbol_info = {
                        'name': self.get_node_text(name_node, content),
                        'type': node_type,
                        'start_point': node.start_point,
                        'end_point': node.end_point,
                        'start_byte': node.start_byte,
                        'end_byte': node.end_byte,
                    }
                    
                    # Distinguish between functions and methods
                    if parent_type == 'class_definition':
                        symbols['methods'].append(symbol_info)
                    else:
                        symbols['functions'].append(symbol_info)
            
            # Extract class definitions
            elif node_type == 'class_definition':
                name_node = None
                for child in node.children:
                    if child.type == 'identifier':
                        name_node = child
                        break
                
                if name_node:
                    symbol_info = {
                        'name': self.get_node_text(name_node, content),
                        'type': node_type,
                        'start_point': node.start_point,
                        'end_point': node.end_point,
                        'start_byte': node.start_byte,
                        'end_byte': node.end_byte,
                    }
                    symbols['classes'].append(symbol_info)
            
            # Extract variable assignments (simplified)
            elif node_type == 'assignment':
                # Find identifier on the left side
                for child in node.children:
                    if child.type == 'identifier':
                        symbol_info = {
                            'name': self.get_node_text(child, content),
                            'type': 'variable',
                            'start_point': child.start_point,
                            'end_point': child.end_point,
                            'start_byte': child.start_byte,
                            'end_byte': child.end_byte,
                        }
                        symbols['variables'].append(symbol_info)
                        break
            
            # Recursively traverse children
            for child in node.children:
                traverse_node(child, node_type)
        
        # Start traversal from root
        traverse_node(parse_result.root_node)
        
        # Filter by requested symbol types
        if symbol_types:
            filtered_symbols = {}
            for symbol_type in symbol_types:
                if symbol_type in symbols:
                    filtered_symbols[symbol_type] = symbols[symbol_type]
            return filtered_symbols
        
        return symbols
    
    async def extract_symbols_async(self, content: Union[str, bytes], language: str,
                                   symbol_types: Optional[List[str]] = None) -> Dict[str, List[Dict[str, Any]]]:
        """Extract symbols asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.thread_pool, 
            self.extract_symbols, 
            content, 
            language, 
            symbol_types
        )
    
    def get_node_text(self, node: Node, content: Union[str, bytes]) -> str:
        """Get text content of a node."""
        if isinstance(content, str):
            content_bytes = content.encode('utf-8')
        else:
            content_bytes = content
        
        if node.text:
            return node.text.decode('utf-8')
        
        # Fallback: extract from source using byte positions
        try:
            return content_bytes[node.start_byte:node.end_byte].decode('utf-8')
        except Exception:
            return ""
    
    def find_node_at_position(self, root: Node, line: int, column: int) -> Optional[Node]:
        """Find the smallest node containing the given position."""
        def search_node(node: Node) -> Optional[Node]:
            # Check if position is within this node
            start_line, start_col = node.start_point
            end_line, end_col = node.end_point
            
            if not (start_line <= line <= end_line):
                return None
            
            if line == start_line and column < start_col:
                return None
            
            if line == end_line and column > end_col:
                return None
            
            # Check children for more specific match
            for child in node.children:
                child_result = search_node(child)
                if child_result:
                    return child_result
            
            # This node contains the position
            return node
        
        return search_node(root)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics."""
        parser_stats = self.parser_cache.get_stats()
        parse_cache_stats = self.parse_cache.get_stats()
        
        avg_parse_time = (
            self.total_parse_time_ms / self.total_parses 
            if self.total_parses > 0 else 0.0
        )
        
        cache_hit_rate = (
            self.cache_hits / (self.cache_hits + self.cache_misses)
            if (self.cache_hits + self.cache_misses) > 0 else 0.0
        )
        
        return {
            'total_parses': self.total_parses,
            'total_parse_time_ms': self.total_parse_time_ms,
            'average_parse_time_ms': avg_parse_time,
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'cache_hit_rate': cache_hit_rate,
            'parser_cache': {
                'size': len(parser_stats),
                'languages': list(parser_stats.keys()),
                'stats': {lang: {
                    'total_parses': stats.total_parses,
                    'average_parse_time_ms': stats.average_parse_time_ms,
                    'cache_hits': stats.cache_hits,
                    'cache_misses': stats.cache_misses,
                    'last_used': stats.last_used.isoformat(),
                } for lang, stats in parser_stats.items()}
            },
            'parse_cache': {
                'total_entries': parse_cache_stats.total_entries,
                'total_size_bytes': parse_cache_stats.total_size_bytes,
                'average_entry_size': parse_cache_stats.average_entry_size,
            },
            'query_cache': {
                'total_queries': len(self.query_cache),
                'queries': {key: {
                    'usage_count': pattern.usage_count,
                    'last_used': pattern.last_used.isoformat(),
                } for key, pattern in self.query_cache.items()}
            }
        }
    
    def clear_caches(self) -> None:
        """Clear all caches."""
        self.parser_cache.clear()
        self.parse_cache.clear()
        self.query_cache.clear()
        logger.info("All caches cleared")
    
    def cleanup(self) -> None:
        """Clean up resources."""
        self.clear_caches()
        self.thread_pool.shutdown(wait=True)
        logger.info("TreeSitterManager cleanup completed")
    
    def __del__(self):
        """Destructor."""
        try:
            self.cleanup()
        except Exception:
            pass


# Global instance for easy access
tree_sitter_manager = TreeSitterManager()


# Convenience functions
def parse_content(content: Union[str, bytes], language: str) -> ParseResult:
    """Parse content with the global manager."""
    return tree_sitter_manager.parse(content, language)


async def parse_content_async(content: Union[str, bytes], language: str) -> ParseResult:
    """Parse content asynchronously with the global manager."""
    return await tree_sitter_manager.parse_async(content, language)


def extract_symbols(content: Union[str, bytes], language: str, 
                   symbol_types: Optional[List[str]] = None) -> Dict[str, List[Dict[str, Any]]]:
    """Extract symbols with the global manager."""
    return tree_sitter_manager.extract_symbols(content, language, symbol_types)


def is_language_supported(language: str) -> bool:
    """Check if language is supported."""
    return tree_sitter_manager.is_language_supported(language)


def get_supported_languages() -> List[str]:
    """Get all supported languages."""
    return tree_sitter_manager.get_supported_languages()


if __name__ == "__main__":
    # Example usage
    import json
    
    # Test Python parsing
    python_code = """
def hello_world(name: str) -> str:
    '''Greet someone.'''
    return f"Hello, {name}!"

class Greeter:
    def __init__(self, default_name: str = "World"):
        self.default_name = default_name
    
    def greet(self, name: Optional[str] = None) -> str:
        return hello_world(name or self.default_name)
"""
    
    print("Testing Tree-sitter Manager...")
    
    # Parse Python code
    result = parse_content(python_code, 'python')
    print(f"Parse successful: {result.error is None}")
    print(f"Parse time: {result.parse_time_ms:.2f}ms")
    print(f"Cached: {result.cached}")
    
    # Extract symbols
    symbols = extract_symbols(python_code, 'python')
    print(f"\nExtracted symbols:")
    for symbol_type, symbol_list in symbols.items():
        print(f"  {symbol_type}: {len(symbol_list)} items")
        for symbol in symbol_list[:3]:  # Show first 3
            print(f"    - {symbol['name']} ({symbol['type']})")
    
    # Test caching (second parse should be faster)
    result2 = parse_content(python_code, 'python')
    print(f"\nSecond parse time: {result2.parse_time_ms:.2f}ms")
    print(f"Second parse cached: {result2.cached}")
    
    # Performance stats
    stats = tree_sitter_manager.get_performance_stats()
    print(f"\nPerformance stats:")
    print(f"  Total parses: {stats['total_parses']}")
    print(f"  Cache hit rate: {stats['cache_hit_rate']:.2%}")
    print(f"  Average parse time: {stats['average_parse_time_ms']:.2f}ms")