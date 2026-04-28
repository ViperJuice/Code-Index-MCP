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
        "Phase plan: `plans/phase-plan-v7-SEMTIMEOUT.md`",
        "## Reset Boundary",
        "## README Lexical Repair",
        "## SEMTIMEOUT Semantic Recovery",
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
        "Configured enrichment model",
        "Effective enrichment model",
        "Collection bootstrap state",
        "SEMROADMAP",
        "SEMANALYSIS",
        "SEMAGENTS",
        "SEMREADME",
        "SEMCLOSEOUT",
        "SEMTIMEOUT",
        "SEMCHANGELOG",
        "SEMSTALLFIX",
        "SEMIOWAIT",
        "README.md",
        "Summary-backed chunks: `269`",
        "Chunks missing summaries: `33126`",
        "Vector-linked chunks: `0`",
        "Lexical readiness",
        "Semantic readiness",
        "Indexed commit",
        "Current commit",
        "Active-profile preflight",
        "uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_summarization.py tests/test_profile_aware_semantic_indexer.py -q --no-cov",
        "uv run mcp-index index check-semantic",
        "uv run pytest tests/root_tests/test_markdown_production_scenarios.py -q --no-cov -k readme",
        "uv run --extra dev python -m pytest tests/real_world/test_semantic_search.py -q --no-cov -k repo_local_dogfood_queries_stay_on_semantic_path -rs",
    ):
        assert expected in text


def test_semdogfood_report_compares_query_modes_and_states_operator_verdict():
    text = _normalized(EVIDENCE)

    for expected in (
        "symbol",
        "semantic",
        "semantic_source",
        "semantic_collection_name",
        "mcp_server/setup/semantic_preflight.py",
        "mcp_server/cli/repository_commands.py",
        "mcp_server/dispatcher/dispatcher_enhanced.py",
        "mcp_server/storage/git_index_manager.py",
        "mcp_server/utils/semantic_indexer.py",
        ".claude/agents/lane-executer.md",
        "stale_commit",
        "local multi-repo dogfooding",
        "summary timeout",
        "one-batch passes",
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
    assert "SEMCHANGELOG" in text
    assert "SEMSTALLFIX" in text
    assert "SEMIOWAIT" in text
    assert "SEMROADMAP" in text
    assert "SEMANALYSIS" in text
    assert "SEMAGENTS" in text
    assert "SEMREADME" in text
    assert "SEMCLOSEOUT" in text
    assert "SEMTIMEOUT" in text
    assert "stale_commit" in text
    assert "blocked_file_timeout" in text
    assert "lexical/storage blocker" in text
    assert "storage diagnostics" in text
    assert "semantic_points" in text
