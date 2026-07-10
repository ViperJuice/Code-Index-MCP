"""REPOCLEAN cleanup evidence contract checks."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
INVENTORY = REPO / "docs" / "status" / "repo-root-cleanup-inventory.md"


def _text() -> str:
    return INVENTORY.read_text(encoding="utf-8")


def test_inventory_records_required_sections_and_commands():
    text = _text()
    for expected in (
        "# Repo Root Cleanup Inventory",
        "Audit date: 2026-07-06",
        "scripts/repo_clean_audit.py --json --max-path 160",
        "scripts/repo_clean_audit.py --json --max-path 160 --wheel-depth",
        "## Generated Path Classes",
        "## Tracked-But-Ignored Classes",
        "## Keep Drop Defer Decisions",
        "## Path-Length Audit",
        "## Wheel Path-Depth Audit",
        "## Windows Fallback",
    ):
        assert expected in text


def test_inventory_preserves_required_public_identity_surfaces_and_source_contract():
    text = _text()
    for expected in (
        "docs/status/public-package-identity.md",
        "code-index-mcp.profiles.yaml",
        "mcp-index-kit/",
        ".mcp.json.example",
        ".mcp.json.templates/",
        "source and test files were preserved unless explicitly listed",
    ):
        assert expected in text


def test_inventory_records_longest_paths_and_fallback_language():
    text = _text()
    assert "Longest tracked path" in text
    assert "Max wheel site-packages member path" in text
    assert "git config --global core.longpaths true" in text
    assert "fallback after the repo tree is clean" in text
