"""Tests for scripts/repo_clean_audit.py."""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "repo_clean_audit.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("repo_clean_audit", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_detect_generated_candidates_only_flags_owned_cleanup_targets():
    mod = _load_script()

    candidates = mod.detect_generated_candidates(
        [
            "INDEXING_STATUS.json",
            "analysis_archive/README.md",
            "reports/performance_charts/performance_report.html",
            "AUTHENTIC_MCP_VS_NATIVE_ANALYSIS.md",
            "mcp_server/cache/query_cache.py",
            "docs/status/public-package-identity.md",
        ]
    )

    assert candidates == [
        {"path": "AUTHENTIC_MCP_VS_NATIVE_ANALYSIS.md", "category": "root_generated_markdown"},
        {"path": "INDEXING_STATUS.json", "category": "root_generated_json"},
        {"path": "analysis_archive/README.md", "category": "analysis_archive"},
        {"path": "reports/performance_charts/performance_report.html", "category": "generated_results"},
    ]


def test_collect_tracked_ignored_paths_records_pattern_and_source_classification(tmp_path):
    mod = _load_script()
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".gitignore").write_text("cache/\n.cursor/\n.mcp.json\n.index_metadata.json\n", encoding="utf-8")
    (repo / "mcp_server" / "cache").mkdir(parents=True)
    (repo / "mcp_server" / "cache" / "query_cache.py").write_text("VALUE = 1\n", encoding="utf-8")
    (repo / ".cursor" / "rules").mkdir(parents=True)
    (repo / ".cursor" / "rules" / "react.mdc").write_text("rule\n", encoding="utf-8")
    (repo / ".mcp.json").write_text("{}\n", encoding="utf-8")
    (repo / ".index_metadata.json").write_text("{}\n", encoding="utf-8")

    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "add", ".gitignore"], cwd=repo, check=True)
    subprocess.run(
        [
            "git",
            "add",
            "-f",
            ".cursor/rules/react.mdc",
            ".index_metadata.json",
            ".mcp.json",
            "mcp_server/cache/query_cache.py",
        ],
        cwd=repo,
        check=True,
    )
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True, text=True)

    tracked_ignored = mod.collect_tracked_ignored_paths(repo)

    assert tracked_ignored == [
        {
            "path": ".cursor/rules/react.mdc",
            "pattern_source": ".gitignore:2",
            "pattern": ".cursor/",
            "classification": "tracked_editor_rules_under_ignored_parent",
        },
        {
            "path": ".index_metadata.json",
            "pattern_source": ".gitignore:4",
            "pattern": ".index_metadata.json",
            "classification": "tracked_generated_metadata_under_runtime_ignore",
        },
        {
            "path": ".mcp.json",
            "pattern_source": ".gitignore:3",
            "pattern": ".mcp.json",
            "classification": "tracked_local_mcp_example_under_private_ignore",
        },
        {
            "path": "mcp_server/cache/query_cache.py",
            "pattern_source": ".gitignore:1",
            "pattern": "cache/",
            "classification": "tracked_source_hidden_by_broad_cache_rule",
        },
    ]


def test_longest_paths_and_retention_requirements_are_deterministic():
    mod = _load_script()
    tracked_files = [
        "mcp-index-kit/README.md",
        "docs/status/public-package-identity.md",
        "code-index-mcp.profiles.yaml",
        ".mcp.json.example",
        "src/main.py",
    ]

    longest, over_limit = mod.longest_paths(tracked_files, max_path=20)
    retained = mod.retention_required_paths(tracked_files)

    assert longest == {"path": "docs/status/public-package-identity.md", "length": 38}
    assert over_limit == [
        {"path": "code-index-mcp.profiles.yaml", "length": 28},
        {"path": "docs/status/public-package-identity.md", "length": 38},
        {"path": "mcp-index-kit/README.md", "length": 23},
    ]
    assert retained == [
        ".mcp.json.example",
        "code-index-mcp.profiles.yaml",
        "docs/status/public-package-identity.md",
        "mcp-index-kit/README.md",
    ]


def test_summarize_wheel_members_extracts_max_path_from_fixture_names():
    mod = _load_script()

    members, longest = mod.summarize_wheel_members(
        [
            "index_it_mcp-1.2.0.dist-info/METADATA",
            "mcp_server/core/repo_context.py",
            "mcp_server/plugins/python_plugin/plugin.py",
        ]
    )

    assert members == [
        {"path": "index_it_mcp-1.2.0.dist-info/METADATA", "length": 37},
        {"path": "mcp_server/core/repo_context.py", "length": 31},
        {"path": "mcp_server/plugins/python_plugin/plugin.py", "length": 42},
    ]
    assert longest == {"path": "mcp_server/plugins/python_plugin/plugin.py", "length": 42}
