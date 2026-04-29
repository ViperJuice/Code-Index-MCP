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
        "Phase plan: `plans/phase-plan-v7-SEMVISUALREPORT.md`",
        "## Reset Boundary",
        "## SEMVISUALREPORT Live Lexical Recovery",
        "## Rebuild Command",
        "## Rebuild Evidence",
        "## Repository Status",
        "## Query Comparison",
        "## Dogfood Verdict",
        "## Verification",
    ):
        assert expected in text


def test_semdogfood_report_records_live_visual_report_recovery_and_roadmap_steering():
    text = _normalized(EVIDENCE)

    for expected in (
        "SEMVISUALREPORT",
        "SEMJEDI",
        "2026-04-29T08:13:25Z",
        "6aae3502",
        "scripts/create_multi_repo_visual_report.py",
        "ai_docs/jedi.md",
        "fast_test_results/fast_report_*.md",
        "ai_docs/*_overview.md",
        "stage trace",
        "force_full_exit_trace.json",
        "Trace stage:",
        "Trace stage family:",
        "Trace blocker source:",
        "135",
        "Older downstream assumptions should be treated as stale",
        "roadmap now adds `SEMJEDI` as the nearest downstream phase",
    ):
        assert expected in text


def test_semdogfood_report_preserves_command_level_verification_and_runtime_paths():
    text = _normalized(EVIDENCE)

    for expected in (
        "env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_python_plugin.py tests/test_repository_commands.py tests/docs/test_semdogfood_evidence_contract.py -q --no-cov",
        "env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full",
        "env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status",
        "force_full_exit_trace.json",
        "sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'",
        "mcp_server/plugins/python_plugin/plugin.py",
        "mcp_server/dispatcher/dispatcher_enhanced.py",
        "mcp_server/storage/git_index_manager.py",
        "mcp_server/cli/repository_commands.py",
        "scripts/create_multi_repo_visual_report.py",
        "semantic_source: \"semantic\"",
        "semantic_collection_name: \"code_index__oss_high__v1\"",
        "local multi-repo dogfooding",
    ):
        assert expected in text
