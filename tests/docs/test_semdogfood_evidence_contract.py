"""SEMDOGFOOD evidence contract checks."""

from __future__ import annotations

from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
EVIDENCE = REPO / "docs" / "status" / "SEMANTIC_DOGFOOD_REBUILD.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def test_semdogfood_report_exists_and_names_required_evidence_sections():
    text = _read(EVIDENCE)

    for expected in (
        "# Semantic Dogfood Rebuild",
        "Phase plan: `plans/phase-plan-v7-SEMFASTREPORT.md`",
        "## Reset Boundary",
        "## SEMFASTREPORT Live Lexical Recovery",
        "## Rebuild Command",
        "## Rebuild Evidence",
        "## Repository Status",
        "## Query Comparison",
        "## Dogfood Verdict",
        "## Verification",
    ):
        assert expected in text


def test_semdogfood_report_records_live_timeout_exit_gap_and_roadmap_steering():
    text = _normalized(EVIDENCE)

    for expected in (
        "SEMFASTREPORT",
        "SEMPYTESTOVERVIEW",
        "2026-04-29T07:28:19Z",
        "2026-04-29T07:27:49Z",
        "feda36fc",
        "fast_test_results/fast_report_20250628_193425.md",
        "ai_docs/pytest_overview.md",
        "Lexical boundary: ignoring generated fast-test reports matching fast_test_results/fast_report_*.md",
        "stage trace",
        "force_full_exit_trace.json",
        "Trace stage:",
        "Trace stage family:",
        "Trace blocker source:",
        "external termination",
        "Older downstream assumptions should be treated as stale",
        "roadmap now adds `SEMPYTESTOVERVIEW` as the nearest downstream phase",
    ):
        assert expected in text


def test_semdogfood_report_preserves_command_level_verification_and_runtime_paths():
    text = _normalized(EVIDENCE)

    for expected in (
        "env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_ignore_patterns.py tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_repository_commands.py tests/docs/test_semdogfood_evidence_contract.py -q --no-cov",
        "env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full",
        "env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status",
        "force_full_exit_trace.json",
        "sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'",
        "mcp_server/core/ignore_patterns.py",
        "mcp_server/dispatcher/dispatcher_enhanced.py",
        "mcp_server/storage/git_index_manager.py",
        "mcp_server/cli/repository_commands.py",
        "semantic_source: \"semantic\"",
        "semantic_collection_name: \"code_index__oss_high__v1\"",
        "local multi-repo dogfooding",
    ):
        assert expected in text
