"""Tests for GitAwareIndexManager branch-change reindex guard (SL-3)."""

import subprocess
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcp_server.storage.git_index_manager import (
    GitAwareIndexManager,
    IndexSyncResult,
    should_reindex_for_branch,
)
from mcp_server.storage.multi_repo_manager import RepositoryInfo


# ---------------------------------------------------------------------------
# SL-3.1a: should_reindex_for_branch unit tests
# ---------------------------------------------------------------------------


def test_should_reindex_same_branch():
    assert should_reindex_for_branch("main", "main") is True


def test_should_reindex_different_branch():
    assert should_reindex_for_branch("feature/noise", "main") is False


def test_should_reindex_no_current_branch():
    assert should_reindex_for_branch(None, "main") is False


def test_should_reindex_no_tracked_branch():
    assert should_reindex_for_branch("main", None) is False


# ---------------------------------------------------------------------------
# Helpers for integration tests
# ---------------------------------------------------------------------------


def _make_git_repo(tmp_path: Path) -> Path:
    """Create a git repo with an initial commit and return its path."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"], cwd=repo, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"], cwd=repo, check=True, capture_output=True
    )
    (repo / "hello.py").write_text("print('hello')\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True
    )
    return repo


def _get_head_commit(repo: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo, check=True, capture_output=True, text=True,
    ).stdout.strip()


def _make_repo_info(repo: Path, commit: str) -> RepositoryInfo:
    index_dir = repo.parent / "index"
    index_dir.mkdir(exist_ok=True)
    return RepositoryInfo(
        repository_id="test-repo-id",
        name="test-repo",
        path=repo,
        index_path=index_dir / "current.db",
        language_stats={},
        total_files=1,
        total_symbols=0,
        indexed_at=datetime.now(),
        current_commit=commit,
        last_indexed_commit=commit,
        tracked_branch="main",
        current_branch="main",
    )


def _make_manager(registry_mock) -> GitAwareIndexManager:
    return GitAwareIndexManager(registry=registry_mock, dispatcher=MagicMock())


# ---------------------------------------------------------------------------
# SL-3.1b: Integration — branch-switch yields up_to_date
# ---------------------------------------------------------------------------


def test_branch_switch_yields_up_to_date(tmp_path):
    repo = _make_git_repo(tmp_path)
    commit = _get_head_commit(repo)

    repo_info = _make_repo_info(repo, commit)
    # Simulate switching to feature branch
    subprocess.run(
        ["git", "checkout", "-b", "feature/noise"], cwd=repo, check=True, capture_output=True
    )
    (repo / "hello.py").write_text("print('changed')\n")

    registry = MagicMock()
    registry.get_repository.return_value = repo_info

    feature_commit = _get_head_commit(repo)
    registry.update_git_state.return_value = {
        "commit": feature_commit,
        "branch": "feature/noise",
    }

    manager = _make_manager(registry)
    manager._full_index = MagicMock(return_value=0)
    manager._incremental_index_update = MagicMock()

    result = manager.sync_repository_index("test-repo-id")

    assert result.action == "up_to_date", f"Expected up_to_date, got {result.action!r}"
    assert manager._full_index.call_count == 0, "_full_index should not be called on branch switch"
    assert (
        manager._incremental_index_update.call_count == 0
    ), "_incremental_index_update should not be called on branch switch"


# ---------------------------------------------------------------------------
# SL-3.1c: Integration — same-branch advance still triggers incremental
# ---------------------------------------------------------------------------


def test_same_branch_advance_triggers_incremental(tmp_path):
    repo = _make_git_repo(tmp_path)
    old_commit = _get_head_commit(repo)

    repo_info = _make_repo_info(repo, old_commit)

    # Make a new commit on main
    (repo / "hello.py").write_text("print('updated')\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "update"], cwd=repo, check=True, capture_output=True
    )
    new_commit = _get_head_commit(repo)

    registry = MagicMock()
    registry.get_repository.return_value = repo_info
    registry.update_git_state.return_value = {"commit": new_commit, "branch": "main"}
    registry.update_indexed_commit.return_value = True

    manager = _make_manager(registry)
    manager._full_index = MagicMock(return_value=0)
    manager._should_full_reindex = MagicMock(return_value=False)

    from mcp_server.storage.git_index_manager import UpdateResult
    incremental_mock = MagicMock(return_value=UpdateResult(indexed=1))
    manager._incremental_index_update = incremental_mock

    result = manager.sync_repository_index("test-repo-id")

    assert incremental_mock.call_count == 1, (
        f"_incremental_index_update should be called once; got {incremental_mock.call_count}"
    )
