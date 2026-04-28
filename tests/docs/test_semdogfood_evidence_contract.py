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
        "Phase plan: `plans/phase-plan-v7-SEMANALYSIS.md`",
        "## Reset Boundary",
        "## Final-Analysis Lexical Repair",
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
        "SEMCHANGELOG",
        "SEMSTALLFIX",
        "SEMIOWAIT",
        "FINAL_COMPREHENSIVE_MCP_ANALYSIS.md",
        "AGENTS.md",
        "blocked_file_timeout",
        "lexical_stage",
        "last_progress_path",
        "in_flight_path",
        "journal_mode",
        "busy_timeout_ms",
        "Lexical readiness",
        "Semantic readiness",
        "Indexed commit",
        "Current commit",
        "Active-profile preflight",
        "uv run pytest tests/test_dispatcher.py -q --no-cov",
        "uv run pytest tests/test_git_index_manager.py -q --no-cov",
        "uv run pytest tests/test_sqlite_store.py -q --no-cov",
        "uv run mcp-index index check-semantic",
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
        "mcp_server/storage/sqlite_store.py",
        "index_unavailable",
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
    assert "SEMCHANGELOG" in text
    assert "SEMSTALLFIX" in text
    assert "SEMIOWAIT" in text
    assert "SEMROADMAP" in text
    assert "SEMANALYSIS" in text
    assert "SEMAGENTS" in text
    assert "stale_commit" in text
    assert "blocked_file_timeout" in text
    assert "lexical/storage blocker" in text
    assert "storage diagnostics" in text
