"""Tiny IPlugin impl used by sandbox tests — no dependencies, no IO."""

from __future__ import annotations

from typing import Iterable

from mcp_server.plugin_base import (
    IndexShard,
    IPlugin,
    Reference,
    SearchOpts,
    SearchResult,
)


class Plugin(IPlugin):
    lang = "mock"

    def __init__(self, sqlite_store=None, enable_semantic=False):
        self._ctx = None

    def bind(self, ctx) -> None:
        self._ctx = ctx

    def supports(self, path) -> bool:
        return True

    def indexFile(self, path, content: str) -> IndexShard:
        return {
            "file": str(path),
            "symbols": [{"name": "echo", "len": len(content)}],
            "language": self.lang,
        }

    def getDefinition(self, symbol: str):
        return {
            "symbol": symbol,
            "kind": "function",
            "language": self.lang,
            "signature": f"def {symbol}()",
            "doc": None,
            "defined_in": "mock.py",
            "start_line": 1,
            "end_line": 1,
            "span": [1, 1],
        }

    def findReferences(self, symbol: str) -> Iterable[Reference]:
        return [Reference(file="mock.py", start_line=1, end_line=1)]

    def search(self, query: str, opts: SearchOpts | None = None) -> Iterable[SearchResult]:
        return [{"file": "mock.py", "start_line": 1, "end_line": 1, "snippet": query}]
