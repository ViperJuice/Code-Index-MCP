"""Generic Tree-Sitter plugin that can handle any supported language."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from chunker import chunk_text

from ..plugin_base import (
    IndexShard,
    Reference,
    SearchOpts,
    SearchResult,
    SymbolDef,
)
from ..plugin_base_enhanced import PluginWithSemanticSearch
from ..storage.sqlite_store import SQLiteStore
from ..utils.chunker_adapter import get_adapter
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

        # Initialize components
        self._indexer = FuzzyIndexer(sqlite_store=sqlite_store)
        self._repository_id = None
        self._adapter = get_adapter()

        logger.info(f"Initialized generic plugin for {self.language_name}")

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

        # Parse with TreeSitter Chunker
        symbols = []
        try:
            chunks = chunk_text(content, self.lang)
            symbols = [self._adapter.chunk_to_symbol_dict(chunk) for chunk in chunks]
            logger.debug(f"Chunked {path}: extracted {len(symbols)} symbols")
        except Exception as e:
            logger.error(f"Failed to chunk {path}: {e}")
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
                        # Parse with chunker and search for exact definition
                        try:
                            chunks = chunk_text(content, self.lang)
                            for chunk in chunks:
                                # Check if chunk contains this symbol
                                symbol_name = chunk.metadata.get("name", chunk.node_type)
                                if symbol_name == symbol:
                                    return self._adapter.chunk_to_symbol_def(chunk)
                        except Exception as e:
                            logger.debug(f"Failed to chunk {path} for definition: {e}")
                            continue
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
