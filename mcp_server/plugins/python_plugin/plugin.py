from pathlib import Path
from ...plugin_base import (
    IPlugin,
    IndexShard,
    SymbolDef,
    Reference,
    SearchResult,
    SearchOpts,
)
from ...utils.treesitter_wrapper import TreeSitterWrapper

class Plugin(IPlugin):
    lang = "python"

    def __init__(self) -> None:
        self._ts = TreeSitterWrapper()

    def supports(self, path: str | Path) -> bool:
        """Return True if file extension matches plugin."""
        return Path(path).suffix == ".py"

    def indexFile(self, path: str | Path, content: str) -> IndexShard:
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

    def getDefinition(self, symbol: str) -> SymbolDef | None:
        """Return the definition of a symbol, if known."""
        ...

    def findReferences(self, symbol: str) -> list[Reference]:
        """List all references to a symbol."""
        ...

    def search(self, query: str, opts: SearchOpts | None = None) -> list[SearchResult]:
        """Search for code snippets matching a query."""
        ...
