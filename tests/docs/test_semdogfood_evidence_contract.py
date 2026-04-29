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
        "Phase plan: `plans/phase-plan-v7-SEMQUICKCHARTS.md`",
        "## Reset Boundary",
        "## SEMTRACEFRESHNESS Live Trace Recovery",
        "## SEMPUBLISHRACE Live Rerun Check",
        "## SEMDEVREBOUND Live Rerun Check",
        "## SEMSCRIPTREBOUND Live Rerun Check",
        "## SEMDISKIO Live Rerun Check",
        "## SEMDEVSTALE Live Rerun Check",
        "## SEMTESTSTALE Live Rerun Check",
        "## SEMSCRIPTABORT Live Rerun Check",
        "## SEMDEVRELAPSE Live Rerun Check",
        "## SEMWALKGAP Live Rerun Check",
        "## SEMQUICKCHARTS Live Rerun Check",
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
        "SEMDISKIO",
        "SEMDEVSTALE",
        "SEMTESTSTALE",
        "SEMSCRIPTABORT",
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
        "2026-04-29T10:09:17Z",
        "2026-04-29T10:12:58Z",
        "2026-04-29T10:13:00Z",
        "2026-04-29T10:13:12Z",
        "2026-04-29T10:34:59Z",
        "2026-04-29T10:35:02Z",
        "2026-04-29T10:37:14Z",
        "2026-04-29T10:55:11Z",
        "2026-04-29T10:55:12Z",
        "2026-04-29T11:13:51Z",
        "2026-04-29T11:17:34Z",
        "2026-04-29T11:17:51Z",
        "2026-04-29T11:43:04Z",
        "2026-04-29T11:43:05Z",
        "2026-04-29T11:43:19Z",
        "2026-04-29T12:19:54Z",
        "2026-04-29T12:21:08Z",
        "2026-04-29T12:51:58Z",
        "2026-04-29T12:52:00Z",
        "2026-04-29T12:53:14Z",
        "2026-04-29T12:53:24Z",
        "2026-04-29T13:16:25Z",
        "2026-04-29T13:16:35Z",
        "098c1ad1",
        "c8b2d724",
        "a186b352",
        "1e7a2a10",
        "aec99482",
        "8870a23f",
        "7335cf35",
        "ec443d85",
        "26a163da",
        "scripts/check_index_schema.py",
        "scripts/rerun_failed_native_tests.py",
        "scripts/quick_mcp_vs_native_validation.py",
        "scripts/create_multi_repo_visual_report.py",
        "scripts/run_test_batch.py",
        "scripts/validate_mcp_comprehensive.py",
        "mcp_server/plugin_system/loader.py",
        "mcp_server/plugin_system/interfaces.py",
        "mcp_server/storage/sqlite_store.py",
        "ai_docs/jedi.md",
        "ai_docs/pytest_overview.md",
        "ai_docs/fastapi_overview.md",
        "ai_docs/plantuml_reference.md",
        ".devcontainer/post_create.sh",
        ".devcontainer/devcontainer.json",
        "tests/test_security.py",
        "tests/test_bootstrap.py",
        "tests/test_deployment_runbook_shape.py",
        "tests/test_reindex_resume.py",
        "tests/test_benchmarks.py",
        "tests/test_artifact_publish_race.py",
        "tests/root_tests/test_contextual_pipeline.py",
        "tests/root_tests/test_voyage_api.py",
        "tests/root_tests/run_reranking_tests.py",
        "tests/security/fixtures/mock_plugin/plugin.py",
        "ai_docs/qdrant.md",
        "fast_test_results/fast_report_*.md",
        "test_workspace/real_repos/search_scaling/package.json",
        "mcp_server/visualization/__init__.py",
        "mcp_server/visualization/quick_charts.py",
        "docs/validation/ga-closeout-decision.md",
        "docs/validation/mre2e-evidence.md",
        "ai_docs/*_overview.md",
        ".devcontainer/devcontainer.json",
        "stale-running snapshot",
        "force_full_exit_trace.json",
        "code `135`",
        "disk I/O error",
        "Trace stage:",
        "Trace stage family:",
        "Trace blocker source:",
        "Older downstream assumptions should be treated as stale",
        "roadmap now adds `SEMDEVSTALE` as the nearest downstream phase",
        "roadmap now adds downstream phase `SEMWALKGAP`",
        "roadmap now adds downstream phase `SEMQUICKCHARTS`",
        "roadmap now adds downstream phase `SEMVALIDEVIDENCE`",
    ):
        assert expected in text


def test_semdogfood_report_preserves_command_level_verification_and_runtime_paths():
    text = _normalized(EVIDENCE)

    for expected in (
        "env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_ignore_patterns.py tests/test_repository_commands.py -q --no-cov -k \"devcontainer or fast_report or test_workspace or lexical or force_full or trace or ignore or boundary\"",
        "uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov",
        "timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full",
        "env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status",
        "force_full_exit_trace.json",
        "sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'",
        "mcp_server/dispatcher/dispatcher_enhanced.py",
        "mcp_server/cli/repository_commands.py",
        ".devcontainer/devcontainer.json",
        "tests/test_deployment_runbook_shape.py",
        "tests/test_reindex_resume.py",
        "scripts/run_test_batch.py",
        "scripts/validate_mcp_comprehensive.py",
        "tests/root_tests/test_voyage_api.py",
        "tests/root_tests/run_reranking_tests.py",
        "scripts/quick_mcp_vs_native_validation.py",
        "tests/test_artifact_publish_race.py",
        "Last sync error:",
        "disk I/O error",
        "Trace status: `interrupted`",
        "Trace stage: `lexical_walking`",
        "Trace stage family: `lexical`",
        "Trace blocker source: `lexical_mutation`",
        "semantic_source: \"semantic\"",
        "semantic_collection_name: \"code_index__oss_high__v1\"",
        "local multi-repo dogfooding",
        "Phase plan: `plans/phase-plan-v7-SEMQUICKCHARTS.md`",
        "Lexical boundary: using exact bounded Python indexing for mcp_server/visualization/quick_charts.py",
        "fixture repositories under test_workspace/ are ignored during lexical walking",
    ):
        assert expected in text
