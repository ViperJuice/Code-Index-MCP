"""REPOCLEAN public-doc contract checks."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    return (REPO / relative_path).read_text(encoding="utf-8")


def _normalized(relative_path: str) -> str:
    return " ".join(_read(relative_path).split())


def test_readme_and_project_structure_do_not_present_generated_directories_as_layout():
    for relative_path in ("README.md", "docs/PROJECT_STRUCTURE.md"):
        text = _read(relative_path)
        for forbidden in ("analysis_archive/", "test_results/", "performance_reports/"):
            assert forbidden not in text, f"{relative_path} still advertises {forbidden}"


def test_windows_docs_use_longpaths_as_fallback_after_clean_tree():
    expected = "git config --global core.longpaths true"

    for relative_path in (
        "TROUBLESHOOTING.md",
        "docs/TROUBLESHOOTING.md",
        "docs/GETTING_STARTED.md",
    ):
        text = _normalized(relative_path)
        assert expected in text, relative_path
        assert "160-character tracked-path limit" in text, relative_path
        assert "fallback" in text.lower(), relative_path
