"""Token scope validator stubs."""

from __future__ import annotations

from typing import Iterable, Optional

from mcp_server.core.errors import MCPError


class InsufficientScopesError(MCPError):
    pass


class TokenValidator:
    @classmethod
    def validate_scopes(
        cls,
        required: Iterable[str],
        *,
        token: Optional[str] = None,
    ) -> None:
        raise NotImplementedError("filled by SL-4")
