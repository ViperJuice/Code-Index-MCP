"""Contract for the final comprehensive hardening v10 evidence record."""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
STATUS = REPO / "docs" / "status" / "COMPREHENSIVE_HARDENING_V10.md"


def _text() -> str:
    return STATUS.read_text(encoding="utf-8")


def test_status_record_has_complete_evidence_sections() -> None:
    text = _text()

    for heading in (
        "# Comprehensive Hardening V10",
        "## Verdict",
        "## Browser And Admin UI",
        "## MCP And Runtime",
        "## Package, Quality, And Security",
        "## Release Posture",
        "## Residual Risk",
    ):
        assert heading in text


def test_status_record_names_exact_commands_and_artifacts() -> None:
    text = _text()

    for expected in (
        "scripts/admin_browser_smoke.py",
        "scripts/hardening_e2e.py",
        "scripts/check_mypy_baseline.py",
        "make release-smoke",
        "make alpha-release-gates",
        "bandit -r mcp_server",
        "/tmp/code-index-mcp-hardverify/admin.json",
        "/tmp/code-index-mcp-hardverify/runtime.json",
        "/tmp/code-index-mcp-hardverify/bandit.json",
        "/tmp/code-index-mcp-hardverify/admin-docs-desktop.png",
        "/tmp/code-index-mcp-hardverify/admin-docs-mobile.png",
    ):
        assert expected in text

    assert re.search(r"\b\d+ passed\b", text)
    assert "console errors: `0`" in text.lower()
    assert "overlap violations: `0`" in text.lower()


def test_status_record_is_truthful_about_unpublished_version() -> None:
    text = _text()

    assert "1.3.1" in text
    assert "prepared" in text.lower()
    assert "unpublished" in text.lower()
    assert "no broad fleet indexing" in text.lower()
    assert "no external release dispatch" in text.lower()


def test_status_record_contains_no_secret_values() -> None:
    text = _text()

    for forbidden in (
        "JWT_SECRET_KEY=",
        "DEFAULT_ADMIN_PASSWORD=",
        "MCP_CLIENT_SECRET=",
        "Authorization: Bearer",
        "BEGIN PRIVATE KEY",
        "ghp_",
        "op://",
    ):
        assert forbidden not in text
