"""Repeatable metadata-only audit for the REPOCLEAN phase."""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Any

GENERATED_PREFIXES = {
    ".metadata/": "runtime_metadata",
    "analysis_archive/": "analysis_archive",
    "comprehensive_real_results/": "generated_results",
    "comprehensive_semantic_results/": "generated_results",
    "fast_test_results/": "generated_results",
    "final_optimized_report_final_report_1750958096/": "generated_results",
    "mcp_test_results/": "generated_results",
    "performance_reports/": "generated_results",
    "quick_test_results/": "generated_results",
    "real_cost_analysis/": "generated_results",
    "real_edit_analysis/": "generated_results",
    "real_session_analysis/": "generated_results",
    "reports/": "generated_results",
    "sample_transcripts/": "generated_results",
    "strategic_recommendations/": "generated_results",
    "test_indexes/": "generated_results",
    "test_results/": "generated_results",
}

GENERATED_EXACT_FILES = {
    "INDEXING_STATUS.json": "root_generated_json",
    "artifact-metadata.json": "root_generated_json",
    "complete_indexing_results.json": "root_generated_json",
    "full_indexing_log.txt": "root_generated_log",
    "indexing_progress_summary.json": "root_generated_json",
    "mcp_direct_test_results.json": "root_generated_json",
    "mcp_indexing_status.json": "root_generated_json",
    "mcp_indexing_summary.json": "root_generated_json",
    "mcp_path_fix_test_results.json": "root_generated_json",
    "mcp_search_code_test_results.json": "root_generated_json",
    "mcp_validation_results.json": "root_generated_json",
    "mcp_verification_results.json": "root_generated_json",
    "missing_repos_to_index.json": "root_generated_json",
    "multi_repo_search_test_results.json": "root_generated_json",
    "proper_repo_mapping.json": "root_generated_json",
    "real_quick_results.json": "root_generated_json",
    "repo_db_mapping.json": "root_generated_json",
    "semantic_indexing_progress.json": "root_generated_json",
    "test_queries.json": "root_generated_json",
    "test_queries_small.json": "root_generated_json",
}

GENERATED_ROOT_SUFFIXES = {
    "_ANALYSIS.md": "root_generated_markdown",
    "_REPORT.md": "root_generated_markdown",
    "_STATUS.md": "root_generated_markdown",
    "_SUMMARY.md": "root_generated_markdown",
}

RETENTION_REQUIRED_PREFIXES = (
    ".mcp.json.templates/",
    "mcp-index-kit/",
)

RETENTION_REQUIRED_EXACT = (
    ".mcp.json.example",
    "code-index-mcp.profiles.yaml",
    "docs/status/public-package-identity.md",
)


def _run_git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def list_tracked_files(root: Path) -> list[str]:
    return [line for line in _run_git(root, "ls-files").splitlines() if line]


def detect_generated_candidates(paths: list[str]) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    for path in sorted(paths):
        matched_category = GENERATED_EXACT_FILES.get(path)
        if matched_category is None:
            for prefix, category in GENERATED_PREFIXES.items():
                if path.startswith(prefix):
                    matched_category = category
                    break
        if matched_category is None and "/" not in path:
            for suffix, category in GENERATED_ROOT_SUFFIXES.items():
                if path.endswith(suffix):
                    matched_category = category
                    break
        if matched_category is not None:
            candidates.append({"path": path, "category": matched_category})
    return candidates


def classify_tracked_ignored_path(path: str, pattern: str) -> str:
    if path.startswith("mcp_server/cache/") and pattern == "cache/":
        return "tracked_source_hidden_by_broad_cache_rule"
    if path.startswith(".cursor/"):
        return "tracked_editor_rules_under_ignored_parent"
    if path == ".mcp.json":
        return "tracked_local_mcp_example_under_private_ignore"
    if path.endswith(".index_metadata.json") or path == ".index_metadata.json":
        return "tracked_generated_metadata_under_runtime_ignore"
    return "tracked_ignored_other"


def collect_tracked_ignored_paths(root: Path) -> list[dict[str, str]]:
    paths = [line for line in _run_git(root, "ls-files", "-ci", "--exclude-standard").splitlines() if line]
    if not paths:
        paths = list_tracked_files(root)
    if not paths:
        return []
    details = subprocess.run(
        ["git", "check-ignore", "-v", "--no-index", "--stdin"],
        cwd=root,
        input="\n".join(paths) + "\n",
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    by_path: dict[str, dict[str, str]] = {}
    for line in details:
        parts = line.split("\t")
        if len(parts) != 2:
            continue
        source_and_pattern, path = parts
        source_parts = source_and_pattern.split(":", 2)
        if len(source_parts) != 3:
            continue
        source_file, source_line, pattern = source_parts
        by_path[path] = {
            "path": path,
            "pattern_source": f"{Path(source_file).name}:{source_line}",
            "pattern": pattern,
            "classification": classify_tracked_ignored_path(path, pattern),
        }
    return [by_path[path] for path in sorted(by_path)]


def longest_paths(paths: list[str], max_path: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    longest = max(paths, key=len, default="")
    longest_entry = {"path": longest, "length": len(longest)}
    over_limit = [{"path": path, "length": len(path)} for path in sorted(paths) if len(path) > max_path]
    return longest_entry, over_limit


def retention_required_paths(paths: list[str]) -> list[str]:
    retained = set()
    for path in paths:
        if path in RETENTION_REQUIRED_EXACT:
            retained.add(path)
            continue
        for prefix in RETENTION_REQUIRED_PREFIXES:
            if path.startswith(prefix):
                retained.add(path)
                break
    return sorted(retained)


def summarize_wheel_members(member_names: list[str]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    paths = sorted(member_names)
    entries = [{"path": path, "length": len(path)} for path in paths]
    longest = max(entries, key=lambda item: item["length"], default={"path": "", "length": 0})
    return entries, longest


def collect_wheel_site_packages_paths(root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    build_cmd = ["uv", "run", "--extra", "dev", "python", "-m", "build", "--wheel"]
    with tempfile.TemporaryDirectory(prefix="repo-clean-audit-") as tmpdir:
        tmp_path = Path(tmpdir)
        subprocess.run(
            build_cmd + ["--outdir", str(tmp_path)],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
        wheels = sorted(tmp_path.glob("*.whl"))
        if len(wheels) != 1:
            raise RuntimeError(f"expected exactly one wheel, found {len(wheels)}")
        with zipfile.ZipFile(wheels[0]) as wheel:
            members = [name for name in wheel.namelist() if not name.endswith("/")]
    return summarize_wheel_members(members)


def build_report(root: Path, max_path: int, wheel_depth: bool) -> dict[str, Any]:
    tracked_files = list_tracked_files(root)
    longest_tracked_path, over_limit_paths = longest_paths(tracked_files, max_path)
    report: dict[str, Any] = {
        "repo_root": str(root),
        "max_path_limit": max_path,
        "tracked_generated_candidates": detect_generated_candidates(tracked_files),
        "tracked_ignored_paths": collect_tracked_ignored_paths(root),
        "longest_tracked_path": longest_tracked_path,
        "over_limit_paths": over_limit_paths,
        "wheel_site_packages_paths": [],
        "max_wheel_site_packages_path_length": {"path": "", "length": 0},
        "retention_required_paths": retention_required_paths(tracked_files),
    }
    if wheel_depth:
        wheel_paths, wheel_max = collect_wheel_site_packages_paths(root)
        report["wheel_site_packages_paths"] = wheel_paths
        report["max_wheel_site_packages_path_length"] = wheel_max
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", dest="emit_json")
    parser.add_argument("--max-path", type=int, default=160)
    parser.add_argument("--wheel-depth", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    report = build_report(root=root, max_path=args.max_path, wheel_depth=args.wheel_depth)
    if args.emit_json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
