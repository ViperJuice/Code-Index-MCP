"""Token scope validator."""

from __future__ import annotations

import logging
import os
import urllib.request
from typing import Iterable, Optional

from mcp_server.core.errors import MCPError

logger = logging.getLogger(__name__)


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
        token = token if token is not None else os.environ.get("GITHUB_TOKEN")
        require_flag = os.environ.get("MCP_REQUIRE_TOKEN_SCOPES") == "1"
        if token is None:
            if require_flag:
                raise InsufficientScopesError("GITHUB_TOKEN unset but MCP_REQUIRE_TOKEN_SCOPES=1")
            logger.warning("GITHUB_TOKEN unset; skipping scope validation")
            return
        req = urllib.request.Request(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            scopes_header = resp.headers.get("X-OAuth-Scopes", "") or ""
        granted = {s.strip() for s in scopes_header.split(",") if s.strip()}
        missing = set(required) - granted
        if missing:
            raise InsufficientScopesError(
                f"GITHUB_TOKEN missing required scopes: {sorted(missing)}; granted={sorted(granted)}"
            )
