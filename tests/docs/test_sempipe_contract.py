"""SEMPIPE docs contract tests."""

from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
SEMANTIC_ONBOARDING = REPO / "docs" / "guides" / "semantic-onboarding.md"
CLI_SETUP_REFERENCE = REPO / "docs" / "tools" / "cli-setup-reference.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8").lower()


def test_docs_name_ordered_full_sync_pipeline():
    combined = _read(SEMANTIC_ONBOARDING) + "\n" + _read(CLI_SETUP_REFERENCE)

    assert "lexical/chunk persistence" in combined
    assert "authoritative summary" in combined
    assert "semantic vector writes" in combined


def test_docs_state_lexical_success_can_coexist_with_semantic_blocked():
    combined = _read(SEMANTIC_ONBOARDING) + "\n" + _read(CLI_SETUP_REFERENCE)

    assert "lexical indexing may still complete" in combined
    assert "semantic readiness stays" in combined
    assert "skipped" in combined
    assert "blocked" in combined


def test_docs_keep_manual_summary_tools_distinct_from_full_sync():
    combined = _read(SEMANTIC_ONBOARDING) + "\n" + _read(CLI_SETUP_REFERENCE)

    assert "write_summaries" in combined
    assert "summary-only" in combined
    assert "summarize_sample" in combined
    assert "diagnostic" in combined
