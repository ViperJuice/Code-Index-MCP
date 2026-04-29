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
        "Phase plan: `plans/phase-plan-v7-SEMDEVREBOUND.md`",
        "## Reset Boundary",
        "## SEMTRACEFRESHNESS Live Trace Recovery",
        "## SEMPUBLISHRACE Live Rerun Check",
        "## SEMDEVREBOUND Live Rerun Check",
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
        "SEMPUBLISHRACE",
        "SEMDEVREBOUND",
        "SEMSCRIPTREBOUND",
        "2026-04-29T08:50:29Z",
        "2026-04-29T08:50:44Z",
        "2026-04-29T08:51:28Z",
        "2026-04-29T08:52:53Z",
        "2026-04-29T08:53:23Z",
        "2026-04-29T09:28:24Z",
        "2026-04-29T09:28:50Z",
        "2026-04-29T09:29:02Z",
        "2026-04-29T09:29:17Z",
        "2026-04-29T09:29:38Z",
        "2026-04-29T09:29:40Z",
        "2026-04-29T09:30:32Z",
        "2026-04-29T09:31:19Z",
        "2026-04-29T09:50:53Z",
        "2026-04-29T09:50:55Z",
        "2026-04-29T09:52:03Z",
        "4c28493a",
        "aec99482",
        "8870a23f",
        "7335cf35",
        "scripts/check_index_schema.py",
        "scripts/rerun_failed_native_tests.py",
        "scripts/quick_mcp_vs_native_validation.py",
        "scripts/create_multi_repo_visual_report.py",
        "ai_docs/jedi.md",
        "ai_docs/pytest_overview.md",
        ".devcontainer/post_create.sh",
        ".devcontainer/devcontainer.json",
        "tests/test_benchmarks.py",
        "tests/test_artifact_publish_race.py",
        "tests/root_tests/test_contextual_pipeline.py",
        "tests/security/fixtures/mock_plugin/plugin.py",
        "ai_docs/qdrant.md",
        "fast_test_results/fast_report_*.md",
        "ai_docs/*_overview.md",
        ".devcontainer/devcontainer.json",
        "stage trace",
        "force_full_exit_trace.json",
        "Trace stage:",
        "Trace stage family:",
        "Trace blocker source:",
        "Older downstream assumptions should be treated as stale",
        "roadmap now adds `SEMSCRIPTREBOUND` as the nearest downstream phase",
    ):
        assert expected in text


def test_semdogfood_report_preserves_command_level_verification_and_runtime_paths():
    text = _normalized(EVIDENCE)

    for expected in (
        "env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_repository_commands.py tests/docs/test_semdogfood_evidence_contract.py -q --no-cov",
        "env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full",
        "env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status",
        "force_full_exit_trace.json",
        "sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'",
        "mcp_server/dispatcher/dispatcher_enhanced.py",
        "mcp_server/cli/repository_commands.py",
        ".devcontainer/devcontainer.json",
        "scripts/quick_mcp_vs_native_validation.py",
        "tests/test_artifact_publish_race.py",
        "semantic_source: \"semantic\"",
        "semantic_collection_name: \"code_index__oss_high__v1\"",
        "local multi-repo dogfooding",
    ):
        assert expected in text
