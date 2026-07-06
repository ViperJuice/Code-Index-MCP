"""SEMQUERY docs contract tests."""

from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
SEMANTIC_ONBOARDING = REPO / "docs" / "guides" / "semantic-onboarding.md"
SUPPORT_MATRIX = REPO / "docs" / "SUPPORT_MATRIX.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8").lower()


def test_semantic_onboarding_describes_semantic_only_query_contract():
    text = _read(SEMANTIC_ONBOARDING)
    assert "search_code(semantic=true)" in text
    assert "semantic_source" in text
    assert "semantic_profile_id" in text
    assert "semantic_collection_name" in text
    assert "semantic_search_failed" in text
    assert "instead of silently degrading to lexical or plugin results" in text


def test_support_matrix_describes_explicit_semantic_refusal_and_failure():
    text = _read(SUPPORT_MATRIX)
    assert "semantic: true" in text
    assert "source/profile/collection metadata" in text
    assert "explicit semantic refusal or failure instead of lexical fallback" in text
