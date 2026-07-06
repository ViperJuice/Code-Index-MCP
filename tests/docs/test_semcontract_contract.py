"""SEMCONTRACT docs contract tests."""

from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
SEMANTIC_ONBOARDING = REPO / "docs" / "guides" / "semantic-onboarding.md"
SUPPORT_MATRIX = REPO / "docs" / "SUPPORT_MATRIX.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8").lower()


def test_semantic_onboarding_distinguishes_lexical_and_semantic_readiness():
    text = _read(SEMANTIC_ONBOARDING)
    assert "lexical readiness" in text
    assert "semantic readiness" in text
    assert "does not imply semantic readiness" in text
    assert "summaries_missing" in text
    assert "vectors_missing" in text
    assert "semantic_stale" in text


def test_support_matrix_keeps_semantic_search_experimental_and_readiness_gated():
    text = _read(SUPPORT_MATRIX)
    assert "semantic search (`uv sync --locked --extra semantic` plus provider config) | experimental" in text
    assert "requires semantic readiness `ready`" in text
