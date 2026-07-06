"""MCPAUTH docs alignment tests."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DOC_PATHS = [
    REPO_ROOT / "README.md",
    REPO_ROOT / "docs" / "GETTING_STARTED.md",
    REPO_ROOT / "docs" / "MCP_CONFIGURATION.md",
    REPO_ROOT / "docs" / "validation" / "mcp-auth-boundary.md",
]


def test_mcpauth_docs_freeze_current_auth_boundary() -> None:
    for path in DOC_PATHS:
        text = path.read_text()
        assert "MCP_CLIENT_SECRET" in text, f"{path} must document the STDIO guard"
        assert "local STDIO handshake guard" in text, f"{path} must keep the auth scope local"
        assert "admin/debug bearer token authentication" in text, (
            f"{path} must describe the FastAPI admin/debug auth surface"
        )
        assert "no remote MCP authorization is implemented" in text, (
            f"{path} must state that remote MCP auth is deferred"
        )


def test_transport_decision_still_defers_remote_mcp_auth() -> None:
    text = (REPO_ROOT / "docs" / "validation" / "mcp-transport-decision.md").read_text()
    normalized = " ".join(text.split())
    assert "remote mcp transport is deferred" in normalized.lower()
    assert (
        "no remote MCP authorization is implemented" in normalized
        or "no remote MCP auth is implemented" in normalized
    )
