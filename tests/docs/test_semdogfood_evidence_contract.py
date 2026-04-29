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
        "Phase plan: `plans/phase-plan-v7-SEMCALLTIME.md`",
        "## Reset Boundary",
        "## README Lexical Repair",
        "## SEMCALLTIME Timeout Recovery",
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
        "2026-04-29T06:24:13Z",
        "7ec6351",
        "SEMCALLTIME",
        "SEMCANCEL",
        "timed-out summary-call",
        "three minutes",
        "terminated manually",
        "Files indexed in SQLite: `1046`",
        "Code chunks indexed in SQLite: `29194`",
        "Summary-backed chunks: `0`",
        "Chunks missing summaries: `29194`",
        "Vector-linked chunks: `0`",
        "Chunks missing vectors: `29194`",
        "Current commit: `7ec6351`",
        "Indexed commit: `e2e95198`",
        "Semantic readiness: `summaries_missing`",
        "Query surface: `index_unavailable`",
        "Active-profile preflight: `ready`",
        "Collection bootstrap state: `reused`",
        "roadmap now adds `SEMCANCEL` as the nearest downstream phase",
    ):
        assert expected in text


def test_semdogfood_report_preserves_command_level_verification_and_runtime_paths():
    text = _normalized(EVIDENCE)

    for expected in (
        "env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_summarization.py tests/test_dispatcher.py tests/test_git_index_manager.py tests/docs/test_semdogfood_evidence_contract.py -q --no-cov",
        "env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full",
        "env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status",
        "sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'",
        "mcp_server/indexing/summarization.py",
        "mcp_server/dispatcher/dispatcher_enhanced.py",
        "mcp_server/storage/git_index_manager.py",
        "mcp_server/cli/repository_commands.py",
        "mcp_server/setup/semantic_preflight.py",
        "semantic_source: \"semantic\"",
        "semantic_collection_name: \"code_index__oss_high__v1\"",
        "local multi-repo dogfooding",
    ):
        assert expected in text
