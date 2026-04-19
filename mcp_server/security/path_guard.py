"""Path traversal guard."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from mcp_server.core.errors import MCPError
from mcp_server.security.path_allowlist import path_within_allowed


class PathTraversalError(MCPError):
    pass


class PathTraversalGuard:
    def __init__(self, allowed_roots: Sequence[Path]) -> None:
        self._roots = tuple(Path(r).resolve() for r in allowed_roots)

    def normalize_and_check(self, p: str | Path) -> Path:
        candidate = Path(p).resolve()
        if not self._roots:
            # No roots configured — deny everything (safe default).
            raise PathTraversalError(f"no allowed roots configured; rejecting {p!r}")
        if not path_within_allowed(candidate, self._roots):
            raise PathTraversalError(f"path {p!r} escapes allowed roots")
        return candidate
