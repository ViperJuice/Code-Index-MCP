"""Path traversal guard stubs."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from mcp_server.core.errors import MCPError


class PathTraversalError(MCPError):
    pass


class PathTraversalGuard:
    def __init__(self, allowed_roots: Sequence[Path]) -> None:
        raise NotImplementedError("filled by SL-4")

    def normalize_and_check(self, p: str | Path) -> Path:
        raise NotImplementedError("filled by SL-4")
