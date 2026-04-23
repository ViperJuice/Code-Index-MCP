"""P28 README readiness handoff checks."""

from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
README_MD = REPO_ROOT / "README.md"


def _text() -> str:
    return README_MD.read_text(encoding="utf-8")


def test_readme_primary_surface_is_readiness_gated():
    text = _text()
    assert "repository readiness is `ready`" in text
    assert "always use these first" not in text


def test_readme_documents_unavailable_fallback_and_reindex():
    text = _text()
    for expected in ("index_unavailable", 'safe_fallback: "native_search"', "reindex"):
        assert expected in text


def test_readme_distinguishes_ready_misses_from_unavailable_index():
    text = _text()
    assert "`results: []`" in text
    assert '`result: "not_found"`' in text
    assert "unavailable" in text
