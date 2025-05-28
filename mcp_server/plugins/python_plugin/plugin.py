from pathlib import Path
import jedi
from ...plugin_base import IPlugin, IndexShard, SymbolDef, Reference, SearchResult, SearchOpts

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
        ...

    def findReferences(self, symbol: str) -> list[Reference]:
        """List all references to a symbol."""
        results: set[tuple[str, int]] = set()

        for path in Path('.').rglob('*.py'):
            try:
                source = path.read_text()
            except Exception:
                continue

            try:
                script = jedi.Script(code=source, path=str(path))
            except Exception:
                continue

            try:
                names = script.get_names(all_scopes=True, definitions=True, references=True)
            except Exception:
                continue

            for name in names:
                if name.name != symbol:
                    continue

                try:
                    refs = script.get_references(line=name.line, column=name.column, scope='file')
                except Exception:
                    continue

                for r in refs:
                    if r.name == symbol:
                        results.add((str(path), r.line))

        return [Reference(file=f, line=l) for f, l in sorted(results)]

    def search(self, query: str, opts: SearchOpts | None = None) -> list[SearchResult]:
        """Search for code snippets matching a query."""
        ...
