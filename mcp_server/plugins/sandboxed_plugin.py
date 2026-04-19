"""Sandboxed plugin adapter — forwards IPlugin calls over subprocess IPC."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from mcp_server.plugin_base import IPlugin, IndexShard, Reference, SearchOpts, SearchResult, SymbolDef
from mcp_server.sandbox.capabilities import CapabilitySet


class SandboxedPlugin(IPlugin):
    lang: str = ""

    def __init__(
        self,
        plugin_module: str,
        capabilities: CapabilitySet,
        *,
        gh_cmd: str = "python",  # interpreter for worker subprocess, not the gh CLI
    ) -> None:
        raise NotImplementedError("filled by SL-1")

    def supports(self, path: str | Path) -> bool:
        raise NotImplementedError("filled by SL-1")

    def indexFile(self, path: str | Path, content: str) -> IndexShard:
        raise NotImplementedError("filled by SL-1")

    def getDefinition(self, symbol: str) -> SymbolDef | None:
        raise NotImplementedError("filled by SL-1")

    def findReferences(self, symbol: str) -> Iterable[Reference]:
        raise NotImplementedError("filled by SL-1")

    def search(self, query: str, opts: SearchOpts | None = None) -> Iterable[SearchResult]:
        raise NotImplementedError("filled by SL-1")
