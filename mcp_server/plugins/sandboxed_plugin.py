"""Sandboxed plugin adapter — forwards IPlugin calls over subprocess IPC.

``SandboxedPlugin`` wraps a target plugin module and runs it inside a
subprocess governed by a :class:`CapabilitySet`. Every ``IPlugin`` method
call on the adapter becomes a JSON-line envelope over the worker's
stdin/stdout. The adapter surfaces :class:`SandboxCallError` (including
worker-side :class:`SandboxViolation`) for forbidden operations.

Typical use::

    caps = CapabilitySet(fs_read=(Path("/repo"),), fs_write=(), env_allow=frozenset())
    p = SandboxedPlugin("mcp_server.plugins.python_plugin", caps)
    shard = p.indexFile("x.py", "print(1)")
    p.close()
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Iterable, List

from mcp_server.plugin_base import (
    IndexShard,
    IPlugin,
    Reference,
    SearchOpts,
    SearchResult,
    SymbolDef,
)
from mcp_server.sandbox.capabilities import CapabilitySet
from mcp_server.sandbox.supervisor import SandboxSupervisor

logger = logging.getLogger(__name__)


class SandboxedPlugin(IPlugin):
    """IPlugin adapter that forwards every call to a sandboxed subprocess."""

    lang: str = ""

    def __init__(
        self,
        plugin_module: str,
        capabilities: CapabilitySet,
        *,
        gh_cmd: str = "python",  # interpreter for worker subprocess, not the gh CLI
    ) -> None:
        self._plugin_module = plugin_module
        self._capabilities = capabilities
        # Default ``"python"`` resolves via PATH; callers that need byte-for-byte
        # interpreter parity (test harness, mcp_server CLI) pass ``sys.executable``.
        interp = gh_cmd if gh_cmd != "python" else sys.executable or "python"
        worker_cmd: List[str] = [
            interp,
            "-m",
            "mcp_server.sandbox.worker_main",
            plugin_module,
            capabilities.to_json(),
        ]
        self._supervisor = SandboxSupervisor(worker_cmd, capabilities)
        self._closed = False
        self._cached_language: str | None = None

    # ------------------------------------------------------------------ IPlugin

    @property
    def language(self) -> str:
        if self._cached_language is None:
            resp = self._supervisor.call("language", {})
            self._cached_language = str(resp.get("value", ""))
            self.lang = self._cached_language
        return self._cached_language

    def bind(self, ctx) -> None:  # type: ignore[override]
        self._ctx = ctx
        # Forward only JSON-safe scalar fields. SQLiteStore / RepositoryInfo
        # cannot cross process boundaries; sandboxed plugins operate without
        # per-repo SQLite state in this release.
        payload = {
            "repo_id": str(getattr(ctx, "repo_id", "") or ""),
            "workspace_root": str(getattr(ctx, "workspace_root", "") or ""),
            "tracked_branch": str(getattr(ctx, "tracked_branch", "") or ""),
        }
        self._supervisor.call("bind", payload)

    def supports(self, path: str | Path) -> bool:
        resp = self._supervisor.call("supports", {"path": str(path)})
        return bool(resp.get("value", False))

    def indexFile(self, path: str | Path, content: str) -> IndexShard:
        resp = self._supervisor.call("indexFile", {"path": str(path), "content": content})
        # IndexShard is a TypedDict; the raw dict is the shape.
        return resp  # type: ignore[return-value]

    def getDefinition(self, symbol: str) -> SymbolDef | None:
        resp = self._supervisor.call("getDefinition", {"symbol": symbol})
        value = resp.get("value")
        return value  # type: ignore[return-value]

    def findReferences(self, symbol: str) -> Iterable[Reference]:
        resp = self._supervisor.call("findReferences", {"symbol": symbol})
        out: List[Reference] = []
        for item in resp.get("items", []):
            try:
                out.append(
                    Reference(
                        file=item.get("file", ""),
                        start_line=int(item.get("start_line", 0)),
                        end_line=int(item.get("end_line", 0)),
                    )
                )
            except Exception:
                continue
        return out

    def search(self, query: str, opts: SearchOpts | None = None) -> Iterable[SearchResult]:
        resp = self._supervisor.call(
            "search", {"query": query, "opts": dict(opts) if opts else None}
        )
        return list(resp.get("items", []))  # type: ignore[return-value]

    # ------------------------------------------------------------------ lifecycle

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self._supervisor.close()
        except Exception as exc:
            logger.debug("SandboxedPlugin.close swallowed: %s", exc)

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
