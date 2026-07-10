"""PUBNAME identity evidence contract checks."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
IDENTITY_NOTE = REPO / "docs" / "status" / "public-package-identity.md"


def test_identity_note_records_check_date_sources_and_versions():
    text = IDENTITY_NOTE.read_text(encoding="utf-8")

    for expected in (
        "Check date: 2026-07-06 UTC",
        "https://pypi.org/pypi/index-it-mcp/json",
        "https://pypi.org/pypi/code-index-mcp/json",
        "`2.14.9`",
        "`2.17.0`",
        "https://github.com/ViperJuice/Code-Index-MCP",
        "https://github.com/johnhuang316/code-index-mcp",
        "uv run --extra dev python scripts/release_smoke.py --wheel --stdio",
    ):
        assert expected in text


def test_identity_note_inventories_required_surfaces():
    text = IDENTITY_NOTE.read_text(encoding="utf-8")

    for expected in (
        "Python distribution name",
        "Canonical CLI entrypoints",
        "Legacy console-script alias",
        "Click program name",
        "MCP client server IDs / labels",
        "Container image name",
        "Profile/config filename",
        "`.mcp.json` example labels",
        "Repository name",
        "npm helper kit",
    ):
        assert expected in text


def test_identity_note_uses_keep_drop_or_defer_decisions_with_rationale():
    text = IDENTITY_NOTE.read_text(encoding="utf-8")

    for expected in ("| keep |", "| drop |", "| defer |"):
        assert expected in text
    assert "collides with an external package name" in text
    assert "outside PUBNAME ownership" in text
