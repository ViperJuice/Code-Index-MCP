"""Tests for TokenValidator."""

from __future__ import annotations

import io
import os
from unittest.mock import MagicMock, patch

import pytest

from mcp_server.security.token_validator import InsufficientScopesError, TokenValidator


def _fake_urlopen(scopes: str):
    """Return a context-manager mock whose headers.get returns the given scopes string."""
    resp = MagicMock()
    resp.headers.get = lambda key, default="": scopes if "Scopes" in key else default
    resp.__enter__ = lambda s: resp
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def test_missing_scope_raises():
    with patch("urllib.request.urlopen", return_value=_fake_urlopen("contents:read, metadata:read")):
        with pytest.raises(InsufficientScopesError) as exc_info:
            TokenValidator.validate_scopes(["attestations:write"], token="fake-token")
    assert "attestations:write" in str(exc_info.value)


def test_sufficient_scopes_returns_none():
    with patch("urllib.request.urlopen", return_value=_fake_urlopen("contents:read, metadata:read")):
        result = TokenValidator.validate_scopes(["contents:read"], token="fake-token")
    assert result is None


def test_no_token_no_require_flag_no_raise(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("MCP_REQUIRE_TOKEN_SCOPES", raising=False)
    with patch("urllib.request.urlopen") as mock_open:
        TokenValidator.validate_scopes(["contents:read"])
        mock_open.assert_not_called()


def test_no_token_require_flag_raises(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("MCP_REQUIRE_TOKEN_SCOPES", "1")
    with pytest.raises(InsufficientScopesError, match="GITHUB_TOKEN unset"):
        TokenValidator.validate_scopes(["contents:read"])


def test_multiple_scopes_all_granted():
    scopes_str = "contents:read, metadata:read, actions:read, actions:write, attestations:write"
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(scopes_str)):
        result = TokenValidator.validate_scopes(
            ["contents:read", "metadata:read", "actions:read", "actions:write", "attestations:write"],
            token="fake-token",
        )
    assert result is None


def test_multiple_scopes_partial_missing():
    scopes_str = "contents:read, metadata:read"
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(scopes_str)):
        with pytest.raises(InsufficientScopesError) as exc_info:
            TokenValidator.validate_scopes(
                ["contents:read", "actions:write"],
                token="fake-token",
            )
    assert "actions:write" in str(exc_info.value)
