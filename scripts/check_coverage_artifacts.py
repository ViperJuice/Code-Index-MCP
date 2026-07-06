#!/usr/bin/env python3
"""Fail closed when generated coverage artifacts are tracked or staged."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Iterable


def _normalize(path: str) -> str:
    return path.replace("\\", "/").strip()


def is_coverage_artifact(path: str) -> bool:
    """Return True when a repo-relative path is a generated coverage artifact."""
    normalized = _normalize(path)
    return normalized in {"coverage.xml", "coverage.json", ".coverage"} or (
        normalized.startswith(".coverage.")
        or normalized == "htmlcov"
        or normalized.startswith("htmlcov/")
    )


def _git_lines(repo_root: Path, *args: str) -> list[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )
    return [_normalize(line) for line in result.stdout.splitlines() if line.strip()]


def find_tracked_artifacts(repo_root: Path) -> list[str]:
    """Return tracked generated coverage artifact paths."""
    return sorted(path for path in _git_lines(repo_root, "ls-files") if is_coverage_artifact(path))


def find_staged_artifacts(repo_root: Path) -> list[str]:
    """Return staged generated coverage artifact paths."""
    return sorted(
        path
        for path in _git_lines(repo_root, "diff", "--cached", "--name-only", "--diff-filter=ACMR")
        if is_coverage_artifact(path)
    )


def build_report(repo_root: Path) -> dict[str, list[str]]:
    """Collect tracked and staged generated coverage artifact violations."""
    tracked = find_tracked_artifacts(repo_root)
    staged = find_staged_artifacts(repo_root)
    return {"tracked": tracked, "staged": staged}


def _print_paths(label: str, paths: Iterable[str]) -> None:
    for path in paths:
        print(f"{label}: {path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".", help="Repository root to inspect.")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo).resolve()
    report = build_report(repo_root)
    if not report["tracked"] and not report["staged"]:
        print("coverage artifact guard passed")
        return 0

    print("coverage artifact guard failed")
    _print_paths("tracked", report["tracked"])
    _print_paths("staged", report["staged"])
    return 1


if __name__ == "__main__":
    sys.exit(main())
