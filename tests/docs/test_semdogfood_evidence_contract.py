"""SEMDOGFOOD evidence contract checks."""

from __future__ import annotations

from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
EVIDENCE = REPO / "docs" / "status" / "SEMANTIC_DOGFOOD_REBUILD.md"
GUIDE = REPO / "docs" / "guides" / "semantic-onboarding.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def test_semdogfood_report_exists_and_names_required_evidence_sections():
    text = _read(EVIDENCE)

    for expected in (
        "# Semantic Dogfood Rebuild",
        "Phase plan: `plans/phase-plan-v7-SEMCOLLECT.md`",
        "## Reset Boundary",
        "## Collection Bootstrap",
        "## Rebuild Command",
        "## Rebuild Evidence",
        "## Repository Status",
        "## Query Comparison",
        "## Dogfood Verdict",
        "## Verification",
    ):
        assert expected in text


def test_semdogfood_report_records_reset_boundary_counts_collection_and_verification():
    text = _normalized(EVIDENCE)

    for expected in (
        "repo-local reset boundary",
        "qdrant_storage/",
        "code_index__oss_high__v1",
        "chunk_summaries",
        "semantic_points",
        "configured enrichment model",
        "effective enrichment model",
        "collection bootstrap",
        "baml-py",
        "max rss",
        "wall time",
        "lexical readiness",
        "semantic readiness",
        "active-profile preflight",
        "uv run pytest tests/test_semantic_preflight.py tests/test_setup_cli.py tests/test_profile_aware_semantic_indexer.py tests/test_dispatcher.py tests/test_repository_commands.py -q --no-cov",
        "uv run mcp-index index check-semantic",
        "uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov",
    ):
        assert expected in text


def test_semdogfood_report_compares_query_modes_and_states_operator_verdict():
    text = _normalized(EVIDENCE)

    for expected in (
        "lexical",
        "symbol",
        "fuzzy",
        "semantic",
        "semantic_source",
        "semantic_collection_name",
        "mcp_server/setup/semantic_preflight.py",
        "mcp_server/indexing/summarization.py",
        "mcp_server/cli/repository_commands.py",
        "semantic_not_ready",
        "local multi-repo dogfooding",
    ):
        assert expected in text


def test_semantic_onboarding_links_semdogfood_report_and_separate_readiness_surfaces():
    text = _normalized(GUIDE)

    assert "docs/status/semantic_dogfood_rebuild.md" in text
    assert "lexical readiness" in text
    assert "semantic readiness" in text
    assert "active-profile preflight" in text
    assert "configured model" in text
    assert "effective model" in text
    assert "collection bootstrap" in text
    assert "baml" in text
