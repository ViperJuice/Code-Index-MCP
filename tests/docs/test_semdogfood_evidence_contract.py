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
        "Phase plan: `plans/phase-plan-v7-SEMTRACEFRESHNESS.md`",
        "## Reset Boundary",
        "## SEMTRACEFRESHNESS Live Trace Recovery",
        "## Rebuild Command",
        "## Rebuild Evidence",
        "## Repository Status",
        "## Query Comparison",
        "## Dogfood Verdict",
        "## Verification",
    ):
        assert expected in text


def test_semdogfood_report_records_trace_freshness_recovery_and_roadmap_steering():
    text = _normalized(EVIDENCE)

    for expected in (
        "SEMJEDI",
        "SEMTRACEFRESHNESS",
        "SEMDEVCONTAINER",
        "2026-04-29T08:50:29Z",
        "2026-04-29T08:50:44Z",
        "2026-04-29T08:51:28Z",
        "2026-04-29T08:52:53Z",
        "2026-04-29T08:53:23Z",
        "8870a23f",
        "7335cf35",
        "scripts/create_multi_repo_visual_report.py",
        "ai_docs/jedi.md",
        "ai_docs/pytest_overview.md",
        ".devcontainer/post_create.sh",
        ".devcontainer/devcontainer.json",
        "fast_test_results/fast_report_*.md",
        "ai_docs/*_overview.md",
        "stage trace",
        "force_full_exit_trace.json",
        "Trace stage:",
        "Trace stage family:",
        "Trace freshness:",
        "Trace blocker source:",
        "Older downstream assumptions should be treated as stale",
        "roadmap now adds `SEMDEVCONTAINER` as the nearest downstream phase",
    ):
        assert expected in text


def test_semdogfood_report_preserves_command_level_verification_and_runtime_paths():
    text = _normalized(EVIDENCE)

    for expected in (
        "uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov",
        "uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov",
        "env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full",
        "env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status",
        "force_full_exit_trace.json",
        "sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'",
        "mcp_server/dispatcher/dispatcher_enhanced.py",
        "mcp_server/storage/git_index_manager.py",
        "mcp_server/cli/repository_commands.py",
        ".devcontainer/devcontainer.json",
        "semantic_source: \"semantic\"",
        "semantic_collection_name: \"code_index__oss_high__v1\"",
        "local multi-repo dogfooding",
    ):
        assert expected in text
