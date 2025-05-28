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

class Plugin(IPlugin):
    lang = "python"

    def supports(self, path: str | Path) -> bool:
        """Return True if file extension matches plugin."""
        ...

    def indexFile(self, path: str | Path, content: str) -> IndexShard:
        """Parse the file and return an index shard."""
        ...

    def getDefinition(self, symbol: str) -> SymbolDef | None:
        """Return the definition of a symbol, if known."""
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
                                "language": "python",
                                "signature": d.get_line_code().strip(),
                                "doc": d.docstring(raw=True),
                                "defined_in": str(path),
                                "line": d.line,
                                "span": [d.line, d.line + 3],
                            }
            except Exception:
                continue

        return None

    def findReferences(self, symbol: str) -> list[Reference]:
        """List all references to a symbol."""
        ...

    def search(self, query: str, opts: SearchOpts | None = None) -> list[SearchResult]:
        """Search for code snippets matching a query."""
        ...
