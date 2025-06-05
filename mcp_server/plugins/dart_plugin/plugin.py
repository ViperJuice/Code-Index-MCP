from pathlib import Path
from ...plugin_base import IPlugin, IndexShard, SymbolDef, Reference, SearchResult, SearchOpts

class Plugin(IPlugin):
    lang = "dart"

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
        ...

    def search(self, query: str, opts: SearchOpts | None = None) -> list[SearchResult]:
        """Search for code snippets matching a query."""
        ...
