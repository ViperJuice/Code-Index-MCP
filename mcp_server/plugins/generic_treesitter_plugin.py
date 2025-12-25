"""Generic Tree-Sitter plugin that can handle any supported language."""

from __future__ import annotations

import ctypes
import logging
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import tree_sitter_languages
from tree_sitter import Language, Node, Parser

from ..plugin_base import (
    IndexShard,
    Reference,
    SearchOpts,
    SearchResult,
    SymbolDef,
)
from ..plugin_base_enhanced import PluginWithSemanticSearch
from ..storage.sqlite_store import SQLiteStore
from ..utils.fuzzy_indexer import FuzzyIndexer

logger = logging.getLogger(__name__)


class GenericTreeSitterPlugin(PluginWithSemanticSearch):
    """Generic plugin that can handle any tree-sitter supported language."""

    def __init__(
        self,
        language_config: Dict[str, Any],
        sqlite_store: Optional[SQLiteStore] = None,
        enable_semantic: bool = True,
    ) -> None:
        """Initialize generic plugin with language configuration.

        Args:
            language_config: Dictionary containing:
                - code: Language code for tree-sitter (e.g., 'go', 'rust')
                - name: Display name (e.g., 'Go', 'Rust')
                - extensions: List of file extensions
                - symbols: List of symbol types to extract
                - query: Optional tree-sitter query string
        """
        # Store language configuration first (needed by base class)
        self.lang = language_config["code"]
        self.language_name = language_config["name"]

        # Initialize enhanced base class (after setting lang)
        super().__init__(sqlite_store=sqlite_store, enable_semantic=enable_semantic)
        self.file_extensions = set(language_config["extensions"])
        self.symbol_types = language_config.get("symbols", [])
        self.query_string = language_config.get("query", "")

        # Initialize components
        self._indexer = FuzzyIndexer(sqlite_store=sqlite_store)
        self._repository_id = None

        # Query caching for performance
        self._parsed_query = None
        self._query_cache_key = None

        # Initialize parser using ctypes approach (like working plugins)
        try:
            # Load the shared library
            lib_path = Path(tree_sitter_languages.__path__[0]) / "languages.so"
            self._lib = ctypes.CDLL(str(lib_path))

            # Get the function name for this language
            func_name = f"tree_sitter_{self.lang}"
            if hasattr(self._lib, func_name):
                # Configure return type
                getattr(self._lib, func_name).restype = ctypes.c_void_p

                # Create language and parser
                self.language = Language(getattr(self._lib, func_name)())
                self.parser = Parser()
                self.parser.language = self.language
                logger.info(f"Loaded tree-sitter grammar for {self.language_name}")
            else:
                raise AttributeError(f"No tree-sitter function found for {self.lang}")
        except Exception as e:
            logger.warning(f"Could not load tree-sitter grammar for {self.language_name}: {e}")
            # Fallback - parser will work with basic extraction
            self.parser = None
            self.language = None

        # Create or get repository if SQLite is enabled
        if self._sqlite_store:
            try:
                self._repository_id = self._sqlite_store.create_repository(
                    str(Path.cwd()), Path.cwd().name, {"language": self.lang}
                )
            except Exception as e:
                logger.warning(f"Failed to create repository: {e}")
                self._repository_id = None

        # Pre-index existing files
        self._preindex()

    def _preindex(self) -> None:
        """Pre-index files for this language in the current directory."""
        for ext in self.file_extensions:
            for path in Path(".").rglob(f"*{ext}"):
                try:
                    text = path.read_text(encoding="utf-8")
                    self._indexer.add_file(str(path), text)
                except Exception:
                    continue

    def supports(self, path: str | Path) -> bool:
        """Check if this plugin supports the given file."""
        return Path(path).suffix in self.file_extensions

    def indexFile(self, path: str | Path, content: str) -> IndexShard:
        """Index a file with optional semantic embeddings."""
        if isinstance(path, str):
            path = Path(path)

        # Add to fuzzy indexer
        self._indexer.add_file(str(path), content)

        # Parse with tree-sitter if available
        symbols = []
        if self.parser and self.language:
            try:
                tree = self.parser.parse(content.encode("utf-8"))
                symbols = self._extract_symbols(tree, content)
            except Exception as e:
                logger.error(f"Failed to parse {path}: {e}")
                # Fallback to basic extraction
                symbols = self._extract_symbols_basic(content)
        else:
            # Fallback to basic extraction
            symbols = self._extract_symbols_basic(content)

        # Store file in SQLite if available
        file_id = None
        if self._sqlite_store and self._repository_id:
            import hashlib

            file_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            file_id = self._sqlite_store.store_file(
                self._repository_id,
                str(path),
                str(path.relative_to(Path.cwd()) if path.is_absolute() else path),
                language=self.lang,
                size=len(content),
                hash=file_hash,
            )
            
            # Update FTS content
            if hasattr(self._sqlite_store, "update_file_content_fts"):
                 self._sqlite_store.update_file_content_fts(file_id, content)

            # Store symbols in SQLite
            for symbol in symbols:
                if file_id:
                    try:
                        self._sqlite_store.store_symbol(
                            file_id,
                            symbol["symbol"],
                            symbol["kind"],
                            symbol["line"],
                            symbol.get("end_line", symbol["line"]),
                            signature=symbol.get("signature", ""),
                        )
                    except Exception as e:
                        logger.error(f"Failed to store symbol: {e}")

        # Create semantic embeddings if enabled
        if self._enable_semantic and symbols:
            self.index_with_embeddings(path, content, symbols)

        return IndexShard(file=str(path), symbols=symbols, language=self.lang)

    def _extract_symbols(self, tree, content: str) -> List[Dict]:
        """Extract symbols using tree-sitter queries."""
        symbols = []

        if self.query_string and self.language:
            try:
                # Use cached query for better performance
                query = self._get_cached_query()
                if query is None:
                    # Fallback to traversal if query parsing failed
                    self._traverse_tree(tree.root_node, content, symbols)
                    return symbols

                captures = query.captures(tree.root_node)

                # Handle both dict format (newer) and list of tuples format (older)
                if isinstance(captures, dict):
                    # Dict format: keys are capture names, values are lists of nodes
                    for capture_name, nodes in captures.items():
                        for node in nodes:
                            symbol_text = content[node.start_byte : node.end_byte]
                            symbols.append(
                                {
                                    "symbol": symbol_text,
                                    "kind": capture_name,
                                    "line": node.start_point[0] + 1,
                                    "end_line": node.end_point[0] + 1,
                                    "span": [
                                        node.start_point[0] + 1,
                                        node.end_point[0] + 1,
                                    ],
                                    "signature": self._get_signature(node, content),
                                }
                            )
                elif isinstance(captures, list):
                    # List of tuples format: [(node, capture_name), ...]
                    for node, capture_name in captures:
                        symbol_text = content[node.start_byte : node.end_byte]
                        symbols.append(
                            {
                                "symbol": symbol_text,
                                "kind": capture_name,
                                "line": node.start_point[0] + 1,
                                "end_line": node.end_point[0] + 1,
                                "span": [
                                    node.start_point[0] + 1,
                                    node.end_point[0] + 1,
                                ],
                                "signature": self._get_signature(node, content),
                            }
                        )

                logger.debug(f"Query extracted {len(symbols)} symbols for {self.language_name}")
            except Exception as e:
                logger.warning(f"Query execution failed for {self.language_name}: {e}")
                # Fallback to traversal
                self._traverse_tree(tree.root_node, content, symbols)
        else:
            # No query provided, use traversal
            self._traverse_tree(tree.root_node, content, symbols)

        return symbols

    def _get_cached_query(self):
        """Get cached parsed query for better performance."""
        if self.query_string and self.language:
            # Check if query is already cached
            cache_key = hash(self.query_string + self.lang)
            if self._query_cache_key == cache_key and self._parsed_query is not None:
                return self._parsed_query

            # Parse and cache the query
            try:
                self._parsed_query = self.language.query(self.query_string)
                self._query_cache_key = cache_key
                logger.debug(f"Cached query for {self.language_name}")
                return self._parsed_query
            except Exception as e:
                logger.warning(f"Failed to parse query for {self.language_name}: {e}")
                return None
        return None

    def _traverse_tree(self, node: Node, content: str, symbols: List[Dict]) -> None:
        """Traverse tree and extract symbols based on node types."""
        # Check if this node type is in our symbol types
        if node.type in self.symbol_types:
            # Try to find the name node
            name_node = None
            for child in node.children:
                if "name" in child.type or "identifier" in child.type:
                    name_node = child
                    break

            if name_node:
                symbol_name = content[name_node.start_byte : name_node.end_byte]
                symbols.append(
                    {
                        "symbol": symbol_name,
                        "kind": node.type,
                        "line": node.start_point[0] + 1,
                        "end_line": node.end_point[0] + 1,
                        "span": [node.start_point[0] + 1, node.end_point[0] + 1],
                        "signature": self._get_signature(node, content),
                    }
                )

        # Recurse through children
        for child in node.children:
            self._traverse_tree(child, content, symbols)

    def _get_signature(self, node: Node, content: str) -> str:
        """Get a signature for the symbol."""
        # Get the line containing the symbol
        start_line = node.start_point[0]
        lines = content.split("\n")
        if start_line < len(lines):
            return lines[start_line].strip()
        return content[node.start_byte : node.end_byte]

    def _extract_symbols_basic(self, content: str) -> List[Dict]:
        """Basic symbol extraction without tree-sitter."""
        symbols = []
        lines = content.split("\n")

        # Language-specific patterns
        patterns = self._get_basic_patterns()

        for i, line in enumerate(lines):
            for pattern, kind in patterns:
                if pattern in line:
                    # Extract symbol name (basic approach)
                    parts = line.strip().split()
                    if len(parts) > 1:
                        symbol_name = parts[1].split("(")[0] if "(" in parts[1] else parts[1]
                        symbols.append(
                            {
                                "symbol": symbol_name,
                                "kind": kind,
                                "line": i + 1,
                                "end_line": i + 1,
                                "span": [i + 1, i + 1],
                                "signature": line.strip(),
                            }
                        )
                        break

        return symbols

    def _get_basic_patterns(self) -> List[tuple[str, str]]:
        """Get basic patterns for symbol extraction based on language."""
        # Common patterns for various languages
        pattern_map = {
            "go": [
                ("func ", "function"),
                ("type ", "type"),
                ("interface ", "interface"),
            ],
            "rust": [("fn ", "function"), ("struct ", "struct"), ("enum ", "enum")],
            "java": [
                ("class ", "class"),
                ("interface ", "interface"),
                ("public ", "method"),
            ],
            "kotlin": [
                ("fun ", "function"),
                ("class ", "class"),
                ("interface ", "interface"),
            ],
            "swift": [
                ("func ", "function"),
                ("class ", "class"),
                ("struct ", "struct"),
            ],
            "ruby": [("def ", "method"), ("class ", "class"), ("module ", "module")],
            "php": [
                ("function ", "function"),
                ("class ", "class"),
                ("interface ", "interface"),
            ],
            "scala": [("def ", "method"), ("class ", "class"), ("trait ", "trait")],
            "bash": [("function ", "function"), ("alias ", "alias")],
            "lua": [("function ", "function"), ("local function ", "function")],
        }

        return pattern_map.get(self.lang, [])

    def getDefinition(self, symbol: str) -> SymbolDef | None:
        """Get the definition of a symbol."""
        # Search through indexed files
        for ext in self.file_extensions:
            for path in Path(".").rglob(f"*{ext}"):
                try:
                    content = path.read_text(encoding="utf-8")
                    if symbol in content:
                        # Parse and search for exact definition
                        if self.parser:
                            tree = self.parser.parse(content.encode("utf-8"))
                            symbols = self._extract_symbols(tree, content)
                            for sym in symbols:
                                if sym["symbol"] == symbol:
                                    return SymbolDef(
                                        symbol=symbol,
                                        kind=sym["kind"],
                                        language=self.lang,
                                        signature=sym["signature"],
                                        doc=None,
                                        defined_in=str(path),
                                        line=sym["line"],
                                        span=(
                                            sym["line"],
                                            sym.get("end_line", sym["line"]),
                                        ),
                                    )
                except Exception:
                    continue
        return None

    def findReferences(self, symbol: str) -> list[Reference]:
        """Find all references to a symbol."""
        refs: list[Reference] = []
        seen: set[tuple[str, int]] = set()

        for ext in self.file_extensions:
            for path in Path(".").rglob(f"*{ext}"):
                try:
                    content = path.read_text(encoding="utf-8")
                    lines = content.split("\n")

                    for i, line in enumerate(lines):
                        if symbol in line:
                            key = (str(path), i + 1)
                            if key not in seen:
                                refs.append(Reference(file=str(path), line=i + 1))
                                seen.add(key)
                except Exception:
                    continue

        return refs

    def _traditional_search(
        self, query: str, opts: SearchOpts | None = None
    ) -> Iterable[SearchResult]:
        """Traditional fuzzy search implementation."""
        limit = 20
        if opts and "limit" in opts:
            limit = opts["limit"]
        return self._indexer.search(query, limit=limit)

    def get_indexed_count(self) -> int:
        """Return the number of indexed files."""
        if hasattr(self._indexer, "_file_contents"):
            return len(self._indexer._file_contents)
        return 0
