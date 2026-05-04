"""README alignment tests for the MCPSTRUCT phase boundary."""

from __future__ import annotations

from pathlib import Path


README_PATH = Path(__file__).resolve().parents[2] / "README.md"


def test_readme_describes_structured_call_results_and_legacy_json_fallback():
    readme = README_PATH.read_text(encoding="utf-8")

    assert "`CallToolResult` objects" in readme
    assert "object-shaped `structuredContent`" in readme
    assert "preserved JSON" in readme
    assert "fallback content in `content`" in readme
    assert "`isError`" in readme
    assert "`safe_fallback: \"native_search\"`" in readme
    assert "remain deferred to `MCPSTRUCT`" not in readme
