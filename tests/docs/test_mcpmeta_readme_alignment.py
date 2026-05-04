"""README alignment tests for the MCPMETA phase boundary."""

from __future__ import annotations

from pathlib import Path


README_PATH = Path(__file__).resolve().parents[2] / "README.md"


def test_readme_describes_richer_tools_list_metadata_without_claiming_structured_results():
    readme = README_PATH.read_text(encoding="utf-8")

    assert "tools/list" in readme
    assert "stable `title` values" in readme
    assert "annotations for read-only versus mutating behavior" in readme
    assert "`outputSchema` drafts" in readme
    assert "structured" in readme
    assert "`call_tool` result payloads remain deferred to `MCPSTRUCT`" in readme
