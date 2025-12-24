from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

import jedi

from ...plugin_base import (
    IndexShard,
    IPlugin,
    Reference,
    SearchOpts,
    SearchResult,
    SymbolDef,
)
from ...storage.sqlite_store import SQLiteStore
from ...utils.fuzzy_indexer import FuzzyIndexer
from ...utils.treesitter_wrapper import TreeSitterWrapper


class Plugin(IPlugin):
    lang = "python"

    def __init__(self, sqlite_store: Optional[SQLiteStore] = None) -> None:
        self._ts = TreeSitterWrapper()
        self._indexer = FuzzyIndexer(sqlite_store=sqlite_store)
        self._sqlite_store = sqlite_store
        self._repository_id = None

        # Create or get repository if SQLite is enabled
        if self._sqlite_store:
            self._repository_id = self._sqlite_store.create_repository(
                str(Path.cwd()), Path.cwd().name, {"language": "python"}
            )

        self._preindex()

    # ------------------------------------------------------------------
    def _preindex(self) -> None:
        for path in Path(".").rglob("*.py"):
            try:
                text = path.read_text()
                self._indexer.add_file(str(path), text)
            except Exception:
                continue

    # ------------------------------------------------------------------
    def supports(self, path: str | Path) -> bool:
        """Return True if file extension matches plugin."""
        return Path(path).suffix == ".py"

    # ------------------------------------------------------------------
    def indexFile(self, path: str | Path, content: str) -> IndexShard:
        if isinstance(path, str):
            path = Path(path)
        self._indexer.add_file(str(path), content)
        tree = self._ts._parser.parse(content.encode("utf-8"))
        root = tree.root_node

        # Store file in SQLite if available
        file_id = None
        if self._sqlite_store and self._repository_id:
            import hashlib

            file_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            file_id = self._sqlite_store.store_file(
                self._repository_id,
                str(path),
                str(path.relative_to(Path.cwd())),
                language="python",
                size=len(content),
                hash=file_hash,
            )

        symbols: list[dict] = []
        for child in root.named_children:
            if child.type not in {"function_definition", "class_definition"}:
                continue

            name_node = child.child_by_field_name("name")
            if name_node is None:
                continue
            name = content[name_node.start_byte : name_node.end_byte]

            start_line = child.start_point[0] + 1
            end_line = child.end_point[0] + 1

            if child.type == "function_definition":
                kind = "function"
                signature = f"def {name}(...):"
            else:
                kind = "class"
                signature = f"class {name}:"

            # Store symbol in SQLite if available
            if self._sqlite_store and file_id:
                symbol_id = self._sqlite_store.store_symbol(
                    file_id, name, kind, start_line, end_line, signature=signature
                )
                # Add to fuzzy indexer with metadata
                self._indexer.add_symbol(
                    name,
                    str(path),
                    start_line,
                    {"symbol_id": symbol_id, "file_id": file_id},
                )

            symbols.append(
                {
                    "symbol": name,
                    "kind": kind,
                    "signature": signature,
                    "line": start_line,
                    "span": (start_line, end_line),
                }
            )

        return {"file": str(path), "symbols": symbols, "language": self.lang}

    # ------------------------------------------------------------------
    def getDefinition(self, symbol: str) -> SymbolDef | None:
        for path in Path(".").rglob("*.py"):
            try:
                source = path.read_text()
                script = jedi.Script(code=source, path=str(path))
                names = script.get_names(all_scopes=True, definitions=True, references=False)
                for name in names:
                    if name.name == symbol and name.type in ("function", "class"):
                        defs = name.goto()
                        if defs:
                            d = defs[0]
                            return {
                                "symbol": d.name,
                                "kind": d.type,
                                "language": self.lang,
                                "signature": d.get_line_code().strip(),
                                "doc": d.docstring(raw=True),
                                "defined_in": str(path),
                                "line": d.line,
                                "span": (d.line, d.line + 3),
                            }
            except Exception:
                continue
        return None

    # ------------------------------------------------------------------
    def findReferences(self, symbol: str) -> list[Reference]:
        refs: list[Reference] = []
        seen: set[tuple[str, int]] = set()
        for path in Path(".").rglob("*.py"):
            try:
                source = path.read_text()
                script = jedi.Script(code=source, path=str(path))
                for r in script.get_references():
                    if r.name == symbol:
                        key = (str(path), r.line)
                        if key not in seen:
                            refs.append(Reference(file=str(path), line=r.line))
                            seen.add(key)
            except Exception:
                continue
        return refs

    # ------------------------------------------------------------------
    def search(self, query: str, opts: SearchOpts | None = None) -> Iterable[SearchResult]:
        limit = 20
        if opts and "limit" in opts:
            limit = opts["limit"]
        if opts and opts.get("semantic"):
            return []
        return self._indexer.search(query, limit=limit)

    # ------------------------------------------------------------------
    def get_indexed_count(self) -> int:
        """Return the number of indexed files."""
        # The fuzzy indexer tracks files internally
        if hasattr(self._indexer, "index"):
            return len(self._indexer.index)
        return 0
