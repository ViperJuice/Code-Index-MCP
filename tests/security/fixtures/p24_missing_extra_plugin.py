from __future__ import annotations

import p24_missing_extra  # noqa: F401

from mcp_server.plugin_base import IPlugin


class Plugin(IPlugin):
    lang = "p24_missing_extra"

    @property
    def language(self) -> str:
        return self.lang

    def supports(self, path):
        return False

    def indexFile(self, path, content):
        return {"file": str(path), "language": self.lang, "symbols": []}

    def getDefinition(self, symbol):
        return None

    def findReferences(self, symbol):
        return []

    def search(self, query, opts=None):
        return []
