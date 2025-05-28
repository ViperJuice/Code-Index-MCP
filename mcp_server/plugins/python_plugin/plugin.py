from __future__ import annotations

from pathlib import Path
import jedi
<<<<<<< ours
=======

>>>>>>> theirs
from ...plugin_base import (
    IPlugin,
    IndexShard,
    SymbolDef,
    Reference,
    SearchResult,
    SearchOpts,
)
<<<<<<< ours

from ...utils.treesitter_wrapper import TreeSitterWrapper
=======
from ...utils.treesitter_wrapper import TreeSitterWrapper
from ...utils.fuzzy_indexer import FuzzyIndexer

>>>>>>> theirs

class Plugin(IPlugin):
    lang = "python"

    def __init__(self) -> None:
        self._ts = TreeSitterWrapper()
<<<<<<< ours

    def supports(self, path: str | Path) -> bool:
        """Return True if file extension matches plugin.""
        return Path(path).suffix == ".py"
=======
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
        return str(path).endswith(".py")
>>>>>>> theirs

    # ------------------------------------------------------------------
    def indexFile(self, path: str | Path, content: str) -> IndexShard:
<<<<<<< ours
        """Parse the file and return an index shard."""
        if isinstance(path, str):
            path = Path(path)

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
                    "span": [start_line, end_line],
                }
            )

        return {"file": str(path), "symbols": symbols, "language": self.lang}
=======
        tree = self._ts.parse_file(Path(path))
        shard: IndexShard = {"file": str(path), "symbols": [], "language": self.lang}

        # Very naive extraction of top-level function/class names using AST
        # s-expression. This is not robust but sufficient for the demo.
        for line in tree.splitlines():
            if line.startswith("(function_definition"):
                name = line.split("identifier ")[1].split()[0]
                shard["symbols"].append(
                    {
                        "symbol": name,
                        "kind": "function",
                        "signature": f"def {name}(...):",
                        "line": 0,
                        "span": (0, 0),
                    }
                )
            elif line.startswith("(class_definition"):
                name = line.split("identifier ")[1].split()[0]
                shard["symbols"].append(
                    {
                        "symbol": name,
                        "kind": "class",
                        "signature": f"class {name}:",
                        "line": 0,
                        "span": (0, 0),
                    }
                )
        return shard
>>>>>>> theirs

    # ------------------------------------------------------------------
    def getDefinition(self, symbol: str) -> SymbolDef | None:
<<<<<<< ours
        """Return the definition of a symbol, if known."""
=======
>>>>>>> theirs
        for path in Path(".").rglob("*.py"):
            try:
                source = path.read_text()
                script = jedi.Script(code=source, path=str(path))
<<<<<<< ours
                names = script.get_names(all_scopes=True, definitions=True, references=False)

                for name in names:
                    if name.name == symbol and name.type in ("function", "class"):
=======
                for name in script.get_names(all_scopes=True):
                    if name.name == symbol and name.type in {"function", "class"}:
>>>>>>> theirs
                        defs = name.goto()
                        if defs:
                            d = defs[0]
                            return {
                                "symbol": d.name,
                                "kind": d.type,
<<<<<<< ours
                                "language": "python",
=======
                                "language": self.lang,
>>>>>>> theirs
                                "signature": d.get_line_code().strip(),
                                "doc": d.docstring(raw=True),
                                "defined_in": str(path),
                                "line": d.line,
<<<<<<< ours
                                "span": [d.line, d.line + 3],
                            }
            except Exception:
                continue

=======
                                "span": (d.line, d.line + 3),
                            }
            except Exception:
                continue
>>>>>>> theirs
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
<<<<<<< ours
        """Search for code snippets matching a query."""
        if opts is None:
            opts = {}

        if opts.get("semantic"):
            # Semantic search not implemented yet
            pass

        limit = opts.get("limit", 20)

        results: list[SearchResult] = []
        seen: set[tuple[str, int]] = set()

        for path in Path(".").rglob("*.py"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for lineno, line in enumerate(f, start=1):
                        if query in line:
                            key = (str(path), lineno)
                            if key in seen:
                                continue
                            seen.add(key)
                            results.append({
                                "file": str(path),
                                "line": lineno,
                                "snippet": line.strip()
                            })
                            if len(results) >= limit:
                                return results
            except Exception:
                continue

        return results
=======
        limit = 20
        if opts and "limit" in opts:
            limit = opts["limit"]
        # semantic search is not implemented
        if opts and opts.get("semantic"):
            return []
        return self._indexer.search(query, limit=limit)
>>>>>>> theirs
