from __future__ import annotations

from pathlib import Path
import jedi

from ...plugin_base import (
    IPlugin,
    IndexShard,
    SymbolDef,
    Reference,
    SearchResult,
    SearchOpts,
)

from ...utils.treesitter_wrapper import TreeSitterWrapper
from ...utils.fuzzy_indexer import FuzzyIndexer


class Plugin(IPlugin):
    lang = "python"

    def __init__(self) -> None:
        self._ts = TreeSitterWrapper()
        self._indexer = FuzzyIndexer()
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
    def search(self, query: str, opts: SearchOpts | None = None) -> list[SearchResult]:
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
        if hasattr(self._indexer, '_file_contents'):
            return len(self._indexer._file_contents)
        return 0
