"""AUTHBOUND documentation contract tests."""

from __future__ import annotations

from pathlib import Path


def test_auth_boundary_docs_cover_contract() -> None:
    auth_boundary = Path("docs/security/auth-boundary.md").read_text()
    checklist = Path("docs/operations/gateway-startup-checklist.md").read_text()
    boundary_validation = Path("docs/validation/mcp-auth-boundary.md").read_text()

    combined = "\n".join([auth_boundary, checklist, boundary_validation])
    for required in (
        "validated JWT",
        "arbitrary bearer",
        "fail closed",
        "public allowlist",
        "MCP_CLIENT_SECRET",
    ):
        assert required in combined

    assert "identity provider" not in combined.lower()
