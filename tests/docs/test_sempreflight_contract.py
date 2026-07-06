"""SEMPREFLIGHT docs contract tests."""

from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
SEMANTIC_ONBOARDING = REPO / "docs" / "guides" / "semantic-onboarding.md"
CLI_SETUP_REFERENCE = REPO / "docs" / "tools" / "cli-setup-reference.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8").lower()


def test_docs_name_enrichment_embedding_collection_and_api_key_reporting():
    combined = _read(SEMANTIC_ONBOARDING) + "\n" + _read(CLI_SETUP_REFERENCE)

    assert "chat smoke" in combined
    assert "embedding smoke" in combined
    assert "vector dimension" in combined
    assert "collection" in combined
    assert "api-key" in combined
    assert "metadata-only" in combined


def test_docs_state_fail_closed_write_blocker_and_read_only_boundary():
    combined = _read(SEMANTIC_ONBOARDING) + "\n" + _read(CLI_SETUP_REFERENCE)

    assert "structured blocker" in combined
    assert "semantic vector" in combined
    assert "writes remain fail-closed" in combined
    assert "read-only with respect to summaries and vectors" in combined
