#!/usr/bin/env python3
"""
Comprehensive validation for Code-Index-MCP.

Clones psf/requests, indexes it into SQLite + in-memory Qdrant,
and verifies both FTS and semantic search behavior.
"""

from __future__ import annotations

import contextlib
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Iterable, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from mcp_server.core.path_resolver import PathResolver
from mcp_server.plugins.python_plugin.plugin import Plugin as PythonPlugin
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.utils.semantic_indexer import SemanticIndexer


def _load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


@contextlib.contextmanager
def _chdir(path: Path) -> Iterable[None]:
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def _clone_requests_repo(target_dir: Path) -> None:
    if target_dir.exists():
        return
    subprocess.run(
        ["git", "clone", "--depth", "1", "https://github.com/psf/requests.git", str(target_dir)],
        check=True,
    )


def _should_index(path: Path, include_tests: bool) -> bool:
    if path.suffix != ".py":
        return False
    skip_dirs = {
        ".git",
        ".venv",
        "__pycache__",
        ".pytest_cache",
        "venv",
    }
    if any(part in skip_dirs for part in path.parts):
        return False
    if not include_tests and "tests" in path.parts:
        return False
    return True


def _select_files(
    repo_dir: Path, include_tests: bool, max_files: Optional[int]
) -> List[Path]:
    required = [
        repo_dir / "requests" / "sessions.py",
        repo_dir / "requests" / "models.py",
        repo_dir / "requests" / "adapters.py",
    ]
    selected: List[Path] = [p for p in required if p.exists()]
    others = sorted(
        p for p in repo_dir.rglob("*.py") if _should_index(p, include_tests) and p not in selected
    )
    if max_files is not None:
        remaining = max(max_files - len(selected), 0)
        selected.extend(others[:remaining])
    else:
        selected.extend(others)
    return selected


def _run_keyword_checks(store: SQLiteStore) -> None:
    queries = ["Session", "PreparedRequest", "HTTPAdapter"]
    for query in queries:
        results = store.search_bm25(query, table="fts_code", limit=5)
        if not results:
            raise RuntimeError(f"FTS query '{query}' returned no results")
        top = results[0]
        print(f"  ✓ FTS '{query}' -> {len(results)} results (top: {top.get('filepath')})")


def _run_semantic_checks(indexer: SemanticIndexer) -> None:
    queries = [
        "class that manages HTTP sessions",
        "prepare an HTTP request for sending",
    ]
    for query in queries:
        results = indexer.search(query, limit=5)
        if not results:
            raise RuntimeError(f"Semantic query '{query}' returned no results")
        top = results[0]
        if "symbol" not in top or "file" not in top:
            raise RuntimeError(f"Semantic result missing fields for '{query}': {top}")
        print(
            f"  ✓ Semantic '{query}' -> {len(results)} results "
            f"(top: {top.get('symbol')} in {top.get('relative_path', top.get('file'))})"
        )


def main() -> int:
    _load_env_file(PROJECT_ROOT / ".env")

    api_key = os.environ.get("VOYAGE_AI_API_KEY") or os.environ.get("VOYAGE_API_KEY")
    if not api_key:
        print("ERROR: VOYAGE_AI_API_KEY (or VOYAGE_API_KEY) is not set.")
        print("Set it in .env or export it before running this script.")
        return 1

    include_tests = os.environ.get("COMPREHENSIVE_INCLUDE_TESTS", "false").lower() == "true"
    max_files_raw = os.environ.get("COMPREHENSIVE_MAX_FILES")
    max_files = int(max_files_raw) if max_files_raw else None
    keep_artifacts = os.environ.get("COMPREHENSIVE_KEEP_ARTIFACTS", "false").lower() == "true"

    os.environ.setdefault("QDRANT_USE_SERVER", "false")

    print("COMPREHENSIVE MCP VALIDATION")
    print("=" * 60)
    print(f"Include tests: {include_tests}")
    print(f"Max files: {max_files if max_files is not None else 'all'}")

    with tempfile.TemporaryDirectory(prefix="mcp_comprehensive_") as temp_dir:
        temp_path = Path(temp_dir)
        repo_dir = temp_path / "requests"
        db_path = temp_path / "requests_index.db"

        print("\n1) Cloning requests...")
        _clone_requests_repo(repo_dir)
        print(f"  ✓ Repository at {repo_dir}")

        print("\n2) Initializing indexers...")
        start_time = time.time()

        with _chdir(repo_dir):
            store = SQLiteStore(str(db_path))
            plugin = PythonPlugin(sqlite_store=store)
            path_resolver = PathResolver(repository_root=repo_dir)
            semantic_indexer = SemanticIndexer(
                qdrant_path=":memory:",
                collection="requests-comprehensive",
                path_resolver=path_resolver,
            )

            files = _select_files(repo_dir, include_tests=include_tests, max_files=max_files)
            print(f"  Indexing {len(files)} Python files...")

            indexed = 0
            failures = 0
            for file_path in files:
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    plugin.indexFile(file_path, content)
                    semantic_indexer.index_file(file_path)
                    indexed += 1
                except Exception as exc:
                    failures += 1
                    print(f"  ⚠ Failed to index {file_path}: {exc}")

            elapsed = time.time() - start_time
            print(f"  ✓ Indexed {indexed} files ({failures} failures) in {elapsed:.2f}s")

            if indexed == 0:
                print("ERROR: No files were indexed.")
                return 1

            print("\n3) Running FTS checks...")
            _run_keyword_checks(store)

            print("\n4) Running semantic checks...")
            _run_semantic_checks(semantic_indexer)

        print("\nVALIDATION COMPLETE")
        if keep_artifacts:
            print(f"Artifacts preserved at: {temp_path}")
        else:
            print("Temporary artifacts cleaned up.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
