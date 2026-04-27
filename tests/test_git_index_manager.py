"""Tests for GitAwareIndexManager branch-change reindex guard (SL-3)."""

import subprocess
from datetime import datetime
from inspect import signature
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcp_server.core.repo_context import RepoContext
from mcp_server.dispatcher.dispatcher_enhanced import IndexResult, IndexResultStatus
from mcp_server.storage.git_index_manager import (
    ChangeSet,
    GitAwareIndexManager,
    IndexSyncResult,
    UpdateResult,
    should_reindex_for_branch,
)
from mcp_server.storage.multi_repo_manager import RepositoryInfo
from mcp_server.storage.sqlite_store import SQLiteStore

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


def test_sync_all_repositories_signature_no_longer_advertises_parallel():
    params = signature(GitAwareIndexManager.sync_all_repositories).parameters
    assert "parallel" not in params


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
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True)
    return repo


def _get_head_commit(repo: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
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


class CtxSignatureDispatcher:
    def __init__(
        self,
        fail_index: set[Path] | None = None,
        index_results: dict[Path, IndexResultStatus] | None = None,
        remove_results: dict[Path, IndexResultStatus] | None = None,
        move_results: dict[tuple[Path, Path], IndexResultStatus] | None = None,
    ) -> None:
        self.calls = []
        self.fail_index = fail_index or set()
        self.index_results = index_results or {}
        self.remove_results = remove_results or {}
        self.move_results = move_results or {}

    def remove_file(self, ctx, path):
        assert isinstance(ctx, RepoContext)
        path = Path(path)
        self.calls.append(("remove", ctx, path))
        status = self.remove_results.get(path, IndexResultStatus.DELETED)
        return IndexResult(status=status, path=path, observed_hash=None, actual_hash=None)

    def move_file(self, ctx, old_path, new_path, content_hash=None):
        assert isinstance(ctx, RepoContext)
        old_path = Path(old_path)
        new_path = Path(new_path)
        self.calls.append(("move", ctx, old_path, new_path, content_hash))
        status = self.move_results.get((old_path, new_path), IndexResultStatus.MOVED)
        return IndexResult(status=status, path=new_path, observed_hash=None, actual_hash=None)

    def index_file(self, ctx, path):
        assert isinstance(ctx, RepoContext)
        path = Path(path)
        if path in self.fail_index:
            return IndexResult(
                status=IndexResultStatus.ERROR,
                path=path,
                observed_hash=None,
                actual_hash=None,
                error="boom",
            )
        self.calls.append(("index", ctx, path))
        status = self.index_results.get(path, IndexResultStatus.INDEXED)
        error = "synthetic status" if status is not IndexResultStatus.INDEXED else None
        return IndexResult(status=status, path=path, observed_hash=None, actual_hash=None, error=error)

    def index_directory(self, ctx, path, recursive=True):
        assert isinstance(ctx, RepoContext)
        self.calls.append(("index_directory", ctx, Path(path), recursive))
        return {"indexed_files": 1, "failed_files": 0, "errors": []}


def _make_ctx(repo_id: str, repo_path: Path, index_path: Path) -> RepoContext:
    store = SQLiteStore(str(index_path))
    return RepoContext(
        repo_id=repo_id,
        sqlite_store=store,
        workspace_root=repo_path,
        tracked_branch="main",
        registry_entry=MagicMock(repository_id=repo_id, path=repo_path),
    )


# ---------------------------------------------------------------------------
# SL-3.1b: Integration — branch-switch yields wrong_branch
# ---------------------------------------------------------------------------


def test_branch_switch_yields_wrong_branch(tmp_path):
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

    manager._has_remote_artifact = MagicMock()
    manager._download_commit_index = MagicMock()
    manager.on_branch_drift = MagicMock()

    result = manager.sync_repository_index("test-repo-id")

    assert result.action == "wrong_branch", f"Expected wrong_branch, got {result.action!r}"
    assert result.code == "wrong_branch"
    assert result.readiness is not None
    assert result.readiness["state"] == "wrong_branch"
    assert manager._full_index.call_count == 0, "_full_index should not be called on branch switch"
    assert (
        manager._incremental_index_update.call_count == 0
    ), "_incremental_index_update should not be called on branch switch"
    manager._has_remote_artifact.assert_not_called()
    manager._download_commit_index.assert_not_called()
    registry.update_indexed_commit.assert_not_called()
    manager.on_branch_drift.assert_not_called()


# ---------------------------------------------------------------------------
# SL-3.1c: Integration — same-branch advance still triggers incremental
# ---------------------------------------------------------------------------


def test_same_branch_advance_triggers_incremental(tmp_path):
    repo = _make_git_repo(tmp_path)
    old_commit = _get_head_commit(repo)

    repo_info = _make_repo_info(repo, old_commit)
    repo_info.index_path.touch()

    # Make a new commit on main
    (repo / "hello.py").write_text("print('updated')\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "update"], cwd=repo, check=True, capture_output=True)
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

    assert (
        incremental_mock.call_count == 1
    ), f"_incremental_index_update should be called once; got {incremental_mock.call_count}"


def test_incremental_update_uses_same_ctx_for_all_dispatcher_mutations(tmp_path):
    repo = _make_git_repo(tmp_path)
    commit = _get_head_commit(repo)
    repo_info = _make_repo_info(repo, commit)
    repo_info.index_path.touch()
    ctx = _make_ctx(repo_info.repository_id, repo, repo_info.index_path)

    (repo / "added.py").write_text("print('added')\n")
    (repo / "renamed.py").write_text("print('renamed')\n")

    registry = MagicMock()
    registry.get_repository.return_value = repo_info
    dispatcher = CtxSignatureDispatcher()
    manager = GitAwareIndexManager(registry, dispatcher)

    result = manager._incremental_index_update(
        repo_info.repository_id,
        ctx,
        ChangeSet(
            added=["added.py"],
            modified=[],
            deleted=["deleted.py"],
            renamed=[("old.py", "renamed.py")],
        ),
    )

    assert result.clean
    assert [call[0] for call in dispatcher.calls] == ["remove", "move", "index"]
    assert all(call[1] is ctx for call in dispatcher.calls)


def test_incremental_update_skipped_required_index_is_not_clean(tmp_path):
    repo = _make_git_repo(tmp_path)
    commit = _get_head_commit(repo)
    repo_info = _make_repo_info(repo, commit)
    repo_info.index_path.touch()
    ctx = _make_ctx(repo_info.repository_id, repo, repo_info.index_path)
    changed_file = repo / "hello.py"

    registry = MagicMock()
    registry.get_repository.return_value = repo_info
    dispatcher = CtxSignatureDispatcher(
        index_results={changed_file: IndexResultStatus.SKIPPED_UNCHANGED}
    )
    manager = GitAwareIndexManager(registry, dispatcher)

    result = manager._incremental_index_update(
        repo_info.repository_id,
        ctx,
        ChangeSet(added=[], modified=["hello.py"], deleted=[], renamed=[]),
    )

    assert not result.clean
    assert result.indexed == 0
    assert result.skipped == 1
    assert any("hello.py" in error for error in result.errors)


def test_sync_repository_index_persists_partial_index_failure(tmp_path):
    repo = _make_git_repo(tmp_path)
    old_commit = _get_head_commit(repo)
    repo_info = _make_repo_info(repo, old_commit)
    repo_info.index_path.touch()

    (repo / "hello.py").write_text("print('updated')\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "update"], cwd=repo, check=True, capture_output=True)
    new_commit = _get_head_commit(repo)

    registry = MagicMock()
    registry.get_repository.return_value = repo_info
    registry.update_git_state.return_value = {"commit": new_commit, "branch": "main"}

    manager = _make_manager(registry)
    manager._should_full_reindex = MagicMock(return_value=False)
    manager._incremental_index_update = MagicMock(
        return_value=UpdateResult(skipped=1, errors=["required mutation skipped"])
    )

    result = manager.sync_repository_index("test-repo-id")

    assert result.action == "failed"
    registry.update_staleness_reason.assert_called_once_with(
        "test-repo-id", "partial_index_failure"
    )


def test_incremental_missing_rename_destination_is_clean_only_after_delete_success(tmp_path):
    repo = _make_git_repo(tmp_path)
    commit = _get_head_commit(repo)
    repo_info = _make_repo_info(repo, commit)
    repo_info.index_path.touch()
    ctx = _make_ctx(repo_info.repository_id, repo, repo_info.index_path)

    registry = MagicMock()
    registry.get_repository.return_value = repo_info
    dispatcher = CtxSignatureDispatcher()
    manager = GitAwareIndexManager(registry, dispatcher)

    result = manager._incremental_index_update(
        repo_info.repository_id,
        ctx,
        ChangeSet(added=[], modified=[], deleted=[], renamed=[("old.py", "new.py")]),
    )

    assert result.clean
    assert result.deleted == 1
    assert result.moved == 0


def test_incremental_missing_rename_destination_not_clean_when_delete_not_found(tmp_path):
    repo = _make_git_repo(tmp_path)
    commit = _get_head_commit(repo)
    repo_info = _make_repo_info(repo, commit)
    repo_info.index_path.touch()
    ctx = _make_ctx(repo_info.repository_id, repo, repo_info.index_path)
    old_full = repo / "old.py"

    registry = MagicMock()
    registry.get_repository.return_value = repo_info
    dispatcher = CtxSignatureDispatcher(
        remove_results={old_full: IndexResultStatus.NOT_FOUND}
    )
    manager = GitAwareIndexManager(registry, dispatcher)

    result = manager._incremental_index_update(
        repo_info.repository_id,
        ctx,
        ChangeSet(added=[], modified=[], deleted=[], renamed=[("old.py", "new.py")]),
    )

    assert not result.clean
    assert result.deleted == 0
    assert result.failed == 1


def test_skipped_required_incremental_result_does_not_advance_commit(tmp_path):
    repo = _make_git_repo(tmp_path)
    old_commit = _get_head_commit(repo)
    repo_info = _make_repo_info(repo, old_commit)
    repo_info.index_path.touch()

    changed_file = repo / "hello.py"
    changed_file.write_text("print('updated')\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "update"], cwd=repo, check=True, capture_output=True)
    new_commit = _get_head_commit(repo)

    registry = MagicMock()
    registry.get_repository.return_value = repo_info
    registry.update_git_state.return_value = {"commit": new_commit, "branch": "main"}

    manager = GitAwareIndexManager(
        registry,
        CtxSignatureDispatcher(
            index_results={changed_file: IndexResultStatus.SKIPPED_UNCHANGED}
        ),
    )
    manager._get_changed_files = MagicMock(
        return_value=ChangeSet(added=[], modified=["hello.py"], deleted=[], renamed=[])
    )
    manager._should_full_reindex = MagicMock(return_value=False)

    result = manager.sync_repository_index(repo_info.repository_id)

    assert result.action == "failed"
    registry.update_indexed_commit.assert_not_called()


def test_missing_index_does_not_incremental_dry_run_or_advance_commit(tmp_path):
    repo = _make_git_repo(tmp_path)
    old_commit = _get_head_commit(repo)
    repo_info = _make_repo_info(repo, old_commit)
    repo_info.index_path.unlink(missing_ok=True)

    (repo / "hello.py").write_text("print('updated')\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "update"], cwd=repo, check=True, capture_output=True)
    new_commit = _get_head_commit(repo)

    registry = MagicMock()
    registry.get_repository.return_value = repo_info
    registry.update_git_state.return_value = {"commit": new_commit, "branch": "main"}
    registry.update_indexed_commit.return_value = True

    manager = GitAwareIndexManager(registry, CtxSignatureDispatcher())
    manager._get_changed_files = MagicMock(
        return_value=ChangeSet(added=[], modified=["hello.py"], deleted=[], renamed=[])
    )
    manager._should_full_reindex = MagicMock(return_value=False)
    manager._incremental_index_update = MagicMock(wraps=manager._incremental_index_update)
    full_result = UpdateResult(indexed=1)
    manager._full_index = MagicMock(return_value=full_result)

    result = manager.sync_repository_index(repo_info.repository_id)

    assert manager._incremental_index_update.call_count == 0
    assert manager._full_index.call_count == 1
    assert result.action in {"full_index", "failed"}
    assert result.action != "incremental_update"


def test_incremental_partial_failure_does_not_advance_commit(tmp_path):
    repo = _make_git_repo(tmp_path)
    old_commit = _get_head_commit(repo)
    repo_info = _make_repo_info(repo, old_commit)
    repo_info.index_path.touch()

    failing_file = repo / "hello.py"
    failing_file.write_text("print('updated')\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "update"], cwd=repo, check=True, capture_output=True)
    new_commit = _get_head_commit(repo)

    registry = MagicMock()
    registry.get_repository.return_value = repo_info
    registry.update_git_state.return_value = {"commit": new_commit, "branch": "main"}

    manager = GitAwareIndexManager(
        registry,
        CtxSignatureDispatcher(fail_index={failing_file}),
    )
    manager._get_changed_files = MagicMock(
        return_value=ChangeSet(added=[], modified=["hello.py"], deleted=[], renamed=[])
    )
    manager._should_full_reindex = MagicMock(return_value=False)

    result = manager.sync_repository_index(repo_info.repository_id)

    assert result.action == "failed"
    registry.update_indexed_commit.assert_not_called()


def test_clean_full_rebuild_advances_commit_only_with_durable_index(tmp_path):
    repo = _make_git_repo(tmp_path)
    old_commit = _get_head_commit(repo)
    repo_info = _make_repo_info(repo, old_commit)
    repo_info.last_indexed_commit = None
    repo_info.index_path.touch()

    registry = MagicMock()
    registry.get_repository.return_value = repo_info
    registry.update_git_state.return_value = {"commit": old_commit, "branch": "main"}
    registry.update_indexed_commit.return_value = True

    manager = GitAwareIndexManager(registry, CtxSignatureDispatcher())

    result = manager.sync_repository_index(repo_info.repository_id, force_full=True)

    assert result.action == "full_index"
    registry.update_indexed_commit.assert_called_once_with(
        repo_info.repository_id, old_commit, branch="main"
    )
