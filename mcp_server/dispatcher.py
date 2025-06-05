from pathlib import Path
from typing import Iterable
from .plugin_base import IPlugin, SymbolDef, SearchResult

class Dispatcher:
    def __init__(self, plugins: list[IPlugin]):
        self._plugins = plugins
        self._by_lang = {p.lang: p for p in plugins}

    def _match_plugin(self, path: Path) -> IPlugin:
        for p in self._plugins:
            if p.supports(path):
                return p
        raise RuntimeError(f"No plugin for {path}")

    def lookup(self, symbol: str) -> SymbolDef | None:
        for p in self._plugins:
            res = p.getDefinition(symbol)
            if res:
                return res
        return None

    def search(self, query: str, semantic=False, limit=20) -> Iterable[SearchResult]:
        opts = {"semantic": semantic, "limit": limit}
        for p in self._plugins:
            yield from p.search(query, opts)
