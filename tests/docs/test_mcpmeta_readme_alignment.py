"""README alignment tests for MCP metadata and structured tool results."""

from __future__ import annotations

from pathlib import Path


README_PATH = Path(__file__).resolve().parents[2] / "README.md"


def test_readme_describes_richer_tool_metadata_and_structured_call_results():
    readme = README_PATH.read_text(encoding="utf-8")

    assert "tools/list" in readme
    assert "stable `title` values" in readme
    assert "annotations for read-only versus mutating behavior" in readme
    assert "`outputSchema` drafts" in readme
    assert "`CallToolResult` objects" in readme
    assert "preserved JSON" in readme
    assert "structuredContent.results" in readme
