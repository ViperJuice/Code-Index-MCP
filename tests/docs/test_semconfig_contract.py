"""SEMCONFIG docs contract tests."""

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SEMANTIC_ONBOARDING = REPO / "docs" / "guides" / "semantic-onboarding.md"
CLI_SETUP_REFERENCE = REPO / "docs" / "tools" / "cli-setup-reference.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_semconfig_docs_name_split_endpoints_and_shims():
    onboarding = _read(SEMANTIC_ONBOARDING)
    cli_ref = _read(CLI_SETUP_REFERENCE)
    combined = onboarding + "\n" + cli_ref

    assert "SEMANTIC_ENRICHMENT_BASE_URL" in combined
    assert "SEMANTIC_ENRICHMENT_MODEL" in combined
    assert "SEMANTIC_EMBEDDING_BASE_URL" in combined
    assert "VLLM_SUMMARIZATION_BASE_URL" in combined
    assert "VLLM_EMBEDDING_BASE_URL" in combined
    assert "ai:8002" in combined
    assert "Qwen/Qwen3-Embedding-8B" in combined


def test_semconfig_docs_avoid_stale_defaults():
    onboarding = _read(SEMANTIC_ONBOARDING)
    cli_ref = _read(CLI_SETUP_REFERENCE)
    combined = onboarding + "\n" + cli_ref

    assert "http://win:8002/v1" not in combined
    assert "Qwen/Qwen2.5-Coder-14B-Instruct-AWQ" not in combined
