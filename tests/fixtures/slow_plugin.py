"""Slow plugin fixture for timeout testing."""

import time
from pathlib import Path
from typing import Iterable, Optional

from mcp_server.plugin_base import (
    IndexShard,
    IPlugin,
    Reference,
    SearchOpts,
    SearchResult,
    SymbolDef,
)


class SlowPlugin(IPlugin):
    """Plugin that sleeps before returning, used to test timeout behavior."""

    lang = "slow"

    def __init__(self, sleep_seconds: float, symbol_def: Optional[SymbolDef] = None) -> None:
        self._sleep_seconds = sleep_seconds
        self._symbol_def = symbol_def

    def supports(self, path: str | Path) -> bool:
        return str(path).endswith(".slow")

    def indexFile(self, path: str | Path, content: str) -> IndexShard:
        return {"file": str(path), "symbols": [], "language": "slow"}

    def getDefinition(self, symbol: str) -> Optional[SymbolDef]:
        time.sleep(self._sleep_seconds)
        return self._symbol_def

    def findReferences(self, symbol: str) -> Iterable[Reference]:
        return []

    def search(self, query: str, opts: SearchOpts | None = None) -> Iterable[SearchResult]:
        return []
