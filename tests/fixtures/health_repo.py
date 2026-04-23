"""Fixtures for health surface tests (SL-4)."""

from __future__ import annotations

import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path

from mcp_server.storage.multi_repo_manager import RepositoryInfo


def make_repo_info(
    tmp_path: Path,
    *,
    repo_id: str = "test-repo",
    missing_git_dir: bool = False,
    missing_index: bool = False,
    empty_index: bool = False,
    tracked_branch: str = "main",
    current_branch: str = "main",
    current_commit: str | None = None,
    last_indexed_commit: str | None = None,
) -> RepositoryInfo:
    """Create a RepositoryInfo pointing at a tmp_path-based repo.

    By default both git_common_dir and index_path exist. Pass flags to
    simulate failure scenarios.
    """
    repo_dir = tmp_path / repo_id
    repo_dir.mkdir(parents=True, exist_ok=True)

    # Create a minimal git repo so .git exists
    subprocess.run(
        ["git", "init", "-b", "main"],
        cwd=str(repo_dir),
        check=True,
        capture_output=True,
    )

    git_dir = repo_dir / ".git"
    index_dir = repo_dir / ".mcp-index"
    index_dir.mkdir(exist_ok=True)
    index_file = index_dir / "code_index.db"
    if not missing_index:
        conn = sqlite3.connect(index_file)
        conn.execute(
            "CREATE TABLE files (id INTEGER PRIMARY KEY, path TEXT, is_deleted BOOLEAN DEFAULT 0)"
        )
        if not empty_index:
            conn.execute("INSERT INTO files (path, is_deleted) VALUES ('README.md', 0)")
        conn.commit()
        conn.close()

    git_common_dir = None if missing_git_dir else str(git_dir)
    index_path = (
        str(index_file) if not missing_index else str(tmp_path / "nonexistent" / "index.db")
    )

    if missing_git_dir:
        import shutil

        shutil.rmtree(str(git_dir))
        git_common_dir = str(git_dir)  # points to now-deleted path

    return RepositoryInfo(
        repository_id=repo_id,
        name=repo_id,
        path=repo_dir,
        index_path=Path(index_path),
        language_stats={},
        total_files=0,
        total_symbols=0,
        indexed_at=datetime.now(),
        tracked_branch=tracked_branch,
        current_branch=current_branch,
        current_commit=current_commit,
        git_common_dir=git_common_dir,
        last_indexed_commit=last_indexed_commit,
    )
