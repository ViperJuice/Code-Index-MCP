"""Optional client handshake gate (IF-0-P5-2).

Reads MCP_CLIENT_SECRET at construction time.  When a non-empty secret is
configured, every tool call is blocked until the client sends the correct
secret via the 'handshake' tool.  Constant-time comparison prevents timing
attacks.
"""

from __future__ import annotations

import hmac
import os
from typing import Optional


class HandshakeGate:
    def __init__(self, secret: Optional[str] = None):
        if secret is None:
            secret = os.environ.get("MCP_CLIENT_SECRET", "")
        # Treat empty string as "no gate"
        self._secret: str = secret if secret else ""
        self._authenticated: bool = False

    @property
    def enabled(self) -> bool:
        """True iff a non-empty secret is configured."""
        return bool(self._secret)

    def check(self, name: str, arguments: dict) -> Optional[dict]:
        """
        Returns None to allow the call, or an MCP error payload dict when blocked.
        - If not enabled → always None.
        - If enabled and name == "handshake" → always None (let handshake execute).
        - If enabled and authenticated → None.
        - If enabled and not authenticated and name != "handshake" → error with code "handshake_required".
        """
        if not self.enabled:
            return None
        if name == "handshake":
            return None
        if self._authenticated:
            return None
        return {
            "error": "Authentication required: call the 'handshake' tool with the correct secret first.",
            "code": "handshake_required",
        }

    def verify(self, secret: str) -> bool:
        """
        Constant-time compare via hmac.compare_digest.
        Flips authenticated True on match and returns True.
        Returns False on mismatch (does not flip flag).
        """
        if not self.enabled:
            return False
        if not secret:
            return False
        match = hmac.compare_digest(self._secret, secret)
        if match:
            self._authenticated = True
        return match
