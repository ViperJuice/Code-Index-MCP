"""Tests for GitAwareIndexManager branch-change reindex guard (SL-3)."""

import json
import subprocess
from datetime import datetime
from inspect import signature
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from mcp_server.core.repo_context import RepoContext
from mcp_server.dispatcher.dispatcher_enhanced import IndexResult, IndexResultStatus
from mcp_server.storage.git_index_manager import (
    ChangeSet,
    GitAwareIndexManager,
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
        return IndexResult(
            status=status, path=path, observed_hash=None, actual_hash=None, error=error
        )

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

    manager.sync_repository_index("test-repo-id")

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


def test_full_index_without_durable_rows_does_not_advance_commit(tmp_path):
    repo = _make_git_repo(tmp_path)
    commit = _get_head_commit(repo)
    repo_info = _make_repo_info(repo, commit)
    repo_info.last_indexed_commit = None
    repo_info.index_path.touch()

    registry = MagicMock()
    registry.get_repository.return_value = repo_info
    registry.update_git_state.return_value = {"commit": commit, "branch": "main"}

    manager = _make_manager(registry)
    manager._resolve_ctx = MagicMock(
        return_value=_make_ctx(repo_info.repository_id, repo, repo_info.index_path)
    )
    manager._full_index = MagicMock(return_value=UpdateResult(indexed=1))

    result = manager.sync_repository_index(repo_info.repository_id, force_full=True)

    assert result.action == "failed"
    assert result.error == "Full index completed without durable SQLite file rows"
    registry.update_staleness_reason.assert_called_once_with(repo_info.repository_id, "index_empty")
    registry.update_indexed_commit.assert_not_called()


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
    dispatcher = CtxSignatureDispatcher(remove_results={old_full: IndexResultStatus.NOT_FOUND})
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
        CtxSignatureDispatcher(index_results={changed_file: IndexResultStatus.SKIPPED_UNCHANGED}),
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

    class DurableFullIndexDispatcher(CtxSignatureDispatcher):
        def index_directory(self, ctx, path, recursive=True):
            row_id = ctx.sqlite_store.ensure_repository_row(path, name="test-repo")
            ctx.sqlite_store.store_file(row_id, path=Path(path) / "hello.py", relative_path="hello.py")
            return super().index_directory(ctx, path, recursive=recursive)

    manager = GitAwareIndexManager(registry, DurableFullIndexDispatcher())

    result = manager.sync_repository_index(repo_info.repository_id, force_full=True)

    assert result.action == "full_index"
    registry.update_indexed_commit.assert_called_once_with(
        repo_info.repository_id, old_commit, branch="main"
    )


def test_full_index_returns_exact_semantic_blocker_when_summaries_still_missing(tmp_path):
    repo = _make_git_repo(tmp_path)
    commit = _get_head_commit(repo)
    repo_info = _make_repo_info(repo, commit)
    ctx = _make_ctx(repo_info.repository_id, repo, repo_info.index_path)

    registry = MagicMock()
    registry.get_repository.return_value = repo_info

    dispatcher = MagicMock()
    dispatcher.index_directory.return_value = {
        "indexed_files": 1,
        "failed_files": 0,
        "errors": [],
        "summaries_written": 1,
        "summary_chunks_attempted": 2,
        "summary_missing_chunks": 1,
        "semantic_indexed": 0,
        "semantic_failed": 0,
        "semantic_skipped": 0,
        "semantic_blocked": 1,
        "semantic_stage": "blocked_missing_summaries",
        "semantic_error": "Missing authoritative summaries blocked strict semantic indexing",
    }

    manager = GitAwareIndexManager(registry=registry, dispatcher=dispatcher)
    result = manager._full_index(repo_info.repository_id, ctx)

    assert result.indexed == 1
    assert result.failed == 0
    assert not result.clean
    assert result.semantic is not None
    assert result.semantic["semantic_blocked"] == 1
    assert result.semantic["semantic_stage"] == "blocked_missing_summaries"
    assert result.errors == ["Missing authoritative summaries blocked strict semantic indexing"]


def test_full_index_returns_exact_semantic_blocker_when_summary_progress_plateaus(tmp_path):
    repo = _make_git_repo(tmp_path)
    commit = _get_head_commit(repo)
    repo_info = _make_repo_info(repo, commit)
    ctx = _make_ctx(repo_info.repository_id, repo, repo_info.index_path)

    registry = MagicMock()
    registry.get_repository.return_value = repo_info

    dispatcher = MagicMock()
    dispatcher.index_directory.return_value = {
        "indexed_files": 1,
        "failed_files": 0,
        "errors": [],
        "summaries_written": 12,
        "summary_chunks_attempted": 12,
        "summary_missing_chunks": 4,
        "summary_passes": 3,
        "semantic_indexed": 0,
        "semantic_failed": 0,
        "semantic_skipped": 0,
        "semantic_blocked": 1,
        "semantic_stage": "blocked_summary_plateau",
        "semantic_error": "Summary generation plateaued before strict semantic indexing could start",
    }

    manager = GitAwareIndexManager(registry=registry, dispatcher=dispatcher)
    result = manager._full_index(repo_info.repository_id, ctx)

    assert result.indexed == 1
    assert not result.clean
    assert result.semantic is not None
    assert result.semantic["summary_passes"] == 3
    assert result.semantic["semantic_stage"] == "blocked_summary_plateau"
    assert (
        result.errors
        == ["Summary generation plateaued before strict semantic indexing could start"]
    )


def test_full_index_preserves_exact_summary_call_timeout_details(tmp_path):
    repo = _make_git_repo(tmp_path)
    commit = _get_head_commit(repo)
    repo_info = _make_repo_info(repo, commit)
    ctx = _make_ctx(repo_info.repository_id, repo, repo_info.index_path)

    registry = MagicMock()
    registry.get_repository.return_value = repo_info

    dispatcher = MagicMock()
    dispatcher.index_directory.return_value = {
        "indexed_files": 1,
        "failed_files": 0,
        "errors": [],
        "summaries_written": 0,
        "summary_chunks_attempted": 1,
        "summary_missing_chunks": 4,
        "summary_passes": 0,
        "summary_remaining_chunks": 4,
        "summary_scope_drained": False,
        "summary_call_timed_out": True,
        "summary_call_file_path": str(repo / "README.md"),
        "summary_call_chunk_ids": ["chunk-1"],
        "summary_call_timeout_seconds": 30.0,
        "semantic_indexed": 0,
        "semantic_failed": 0,
        "semantic_skipped": 0,
        "semantic_blocked": 1,
        "semantic_stage": "blocked_summary_call_timeout",
        "semantic_error": (
            "Authoritative summary call timed out after 30 seconds before any summary was "
            f"written for {repo / 'README.md'}; 4 chunks still require summaries"
        ),
    }

    manager = GitAwareIndexManager(registry=registry, dispatcher=dispatcher)
    result = manager._full_index(repo_info.repository_id, ctx)

    assert not result.clean
    assert result.semantic is not None
    assert result.semantic["summary_call_timed_out"] is True
    assert result.semantic["summary_call_file_path"] == str(repo / "README.md")
    assert result.semantic["summary_call_chunk_ids"] == ["chunk-1"]
    assert result.semantic["summary_call_timeout_seconds"] == 30.0
    assert result.semantic["semantic_stage"] == "blocked_summary_call_timeout"


def test_force_full_timeout_restores_active_runtime_and_preserves_exact_blocker(tmp_path):
    repo = _make_git_repo(tmp_path)
    commit = _get_head_commit(repo)
    repo_info = _make_repo_info(repo, commit)
    index_base = Path(repo_info.index_location)
    index_base.mkdir(parents=True, exist_ok=True)

    active_store = SQLiteStore(str(repo_info.index_path))
    repo_row = active_store.ensure_repository_row(repo, name="test-repo")
    active_store.store_file(repo_row, path=repo / "hello.py", relative_path="hello.py")
    active_store.close()
    semantic_qdrant = index_base / "semantic_qdrant"
    semantic_qdrant.mkdir(parents=True, exist_ok=True)
    (semantic_qdrant / "marker.txt").write_text("original", encoding="utf-8")

    registry = MagicMock()
    registry.get_repository.return_value = repo_info
    registry.update_git_state.return_value = {"commit": commit, "branch": "main"}

    manager = _make_manager(registry)
    ctx = _make_ctx(repo_info.repository_id, repo, repo_info.index_path)
    manager._resolve_ctx = MagicMock(return_value=ctx)

    def _mutating_full_index(_repo_id, active_ctx):
        mutated_store = active_ctx.sqlite_store
        mutated_repo_row = mutated_store.ensure_repository_row(repo, name="test-repo")
        mutated_store.store_file(
            mutated_repo_row,
            path=repo / "extra.py",
            relative_path="extra.py",
        )
        (semantic_qdrant / "marker.txt").write_text("mutated", encoding="utf-8")
        return UpdateResult(
            indexed=2,
            errors=[
                "Authoritative summary call timed out after 30 seconds before any summary was "
                f"written for {repo / 'README.md'}; 4 chunks still require summaries"
            ],
            semantic={
                "summaries_written": 0,
                "summary_chunks_attempted": 1,
                "summary_missing_chunks": 4,
                "summary_passes": 0,
                "summary_remaining_chunks": 4,
                "summary_scope_drained": False,
                "summary_call_timed_out": True,
                "summary_call_file_path": str(repo / "README.md"),
                "summary_call_chunk_ids": ["chunk-1"],
                "summary_call_timeout_seconds": 30.0,
                "semantic_indexed": 0,
                "semantic_failed": 0,
                "semantic_skipped": 0,
                "semantic_blocked": 1,
                "semantic_stage": "blocked_summary_call_timeout",
            },
        )

    manager._full_index = MagicMock(side_effect=_mutating_full_index)

    result = manager.sync_repository_index(repo_info.repository_id, force_full=True)

    assert result.action == "failed"
    assert "Authoritative summary call timed out after 30 seconds" in result.error
    assert "runtime restored via" in result.error
    assert result.semantic is not None
    assert result.semantic["runtime_restore_performed"] is True
    assert result.semantic["runtime_counts_before"]["files"] == 1
    assert result.semantic["runtime_counts_after"]["files"] == 1
    restored_store = SQLiteStore(str(repo_info.index_path))
    with restored_store._get_connection() as conn:
        files_count = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        file_paths = {
            row[0] for row in conn.execute("SELECT relative_path FROM files").fetchall()
        }
        semantic_points = conn.execute("SELECT COUNT(*) FROM semantic_points").fetchone()[0]
    restored_store.close()
    assert files_count == 1
    assert file_paths == {"hello.py"}
    assert semantic_points == 0
    assert (semantic_qdrant / "marker.txt").read_text(encoding="utf-8") == "original"
    registry.update_indexed_commit.assert_not_called()


def test_force_full_storage_closeout_restores_runtime_and_preserves_exact_blocker(tmp_path):
    repo = _make_git_repo(tmp_path)
    commit = _get_head_commit(repo)
    repo_info = _make_repo_info(repo, commit)
    index_base = Path(repo_info.index_location)
    index_base.mkdir(parents=True, exist_ok=True)
    semantic_qdrant = index_base / "semantic_qdrant"
    semantic_qdrant.mkdir(parents=True)
    (semantic_qdrant / "marker.txt").write_text("original", encoding="utf-8")

    base_store = SQLiteStore(str(repo_info.index_path))
    base_repo_row = base_store.ensure_repository_row(repo, name="test-repo")
    base_store.store_file(
        base_repo_row,
        path=repo / "hello.py",
        relative_path="hello.py",
    )
    base_store.close()

    registry = MagicMock()
    registry.get_repository.return_value = repo_info
    registry.update_git_state.return_value = {"commit": commit, "branch": "main"}

    manager = GitAwareIndexManager(registry=registry, dispatcher=MagicMock())
    ctx = _make_ctx(repo_info.repository_id, repo, repo_info.index_path)
    manager._resolve_ctx = MagicMock(return_value=ctx)

    def _mutating_full_index(_repo_id, active_ctx):
        mutated_store = active_ctx.sqlite_store
        mutated_repo_row = mutated_store.ensure_repository_row(repo, name="test-repo")
        mutated_store.store_file(
            mutated_repo_row,
            path=repo / "extra.py",
            relative_path="extra.py",
        )
        (semantic_qdrant / "marker.txt").write_text("mutated", encoding="utf-8")
        return UpdateResult(
            indexed=2,
            failed=1,
            errors=["disk I/O error"],
            semantic={
                "summaries_written": 0,
                "summary_chunks_attempted": 0,
                "summary_missing_chunks": 0,
                "summary_passes": 0,
                "summary_remaining_chunks": 0,
                "summary_scope_drained": True,
                "summary_call_timed_out": False,
                "semantic_indexed": 0,
                "semantic_failed": 0,
                "semantic_skipped": 0,
                "semantic_blocked": 1,
                "semantic_stage": "blocked_storage_error",
                "semantic_error": "disk I/O error",
                "semantic_blocker": {
                    "code": "storage_closeout",
                    "message": "disk I/O error",
                },
                "storage_failure_family": "sqlite_operational",
                "storage_failure_reason": "disk_io_error",
                "storage_failure_message": "disk I/O error",
                "storage_diagnostics": {
                    "status": "degraded",
                    "journal_mode": "WAL",
                    "readonly": True,
                },
            },
        )

    manager._full_index = MagicMock(side_effect=_mutating_full_index)

    result = manager.sync_repository_index(repo_info.repository_id, force_full=True)

    trace_path = Path(repo_info.index_location) / "force_full_exit_trace.json"
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    assert result.action == "failed"
    assert "disk I/O error" in result.error
    assert "runtime restored via" in result.error
    assert result.semantic is not None
    assert result.semantic["runtime_restore_performed"] is True
    assert result.semantic["runtime_restore_mode"].startswith("sqlite_restored")
    assert trace["stage"] == "runtime_restore_completed"
    assert trace["stage_family"] == "final_closeout"
    assert trace["blocker_source"] == "storage_closeout"
    assert trace["storage_failure_family"] == "sqlite_operational"
    assert trace["storage_failure_reason"] == "disk_io_error"
    assert trace["runtime_restore_performed"] is True
    restored_store = SQLiteStore(str(repo_info.index_path))
    with restored_store._get_connection() as conn:
        files_count = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        file_paths = {
            row[0] for row in conn.execute("SELECT relative_path FROM files").fetchall()
        }
        semantic_points = conn.execute("SELECT COUNT(*) FROM semantic_points").fetchone()[0]
    restored_store.close()
    assert files_count == 1
    assert file_paths == {"hello.py"}
    assert semantic_points == 0
    assert (semantic_qdrant / "marker.txt").read_text(encoding="utf-8") == "original"
    registry.update_indexed_commit.assert_not_called()


def test_full_index_preserves_bounded_summary_continuation_details(tmp_path):
    repo = _make_git_repo(tmp_path)
    commit = _get_head_commit(repo)
    repo_info = _make_repo_info(repo, commit)
    ctx = _make_ctx(repo_info.repository_id, repo, repo_info.index_path)

    registry = MagicMock()
    registry.get_repository.return_value = repo_info

    dispatcher = MagicMock()
    dispatcher.index_directory.return_value = {
        "indexed_files": 2,
        "failed_files": 0,
        "errors": [],
        "summaries_written": 8,
        "summary_chunks_attempted": 8,
        "summary_missing_chunks": 17,
        "summary_passes": 8,
        "summary_remaining_chunks": 17,
        "summary_scope_drained": False,
        "summary_continuation_required": True,
        "semantic_indexed": 0,
        "semantic_failed": 0,
        "semantic_skipped": 0,
        "semantic_blocked": 2,
        "semantic_stage": "blocked_missing_summaries",
        "semantic_error": (
            "Missing authoritative summaries blocked strict semantic indexing "
            "after 8 bounded summary passes; 17 chunks still require summaries"
        ),
    }

    manager = GitAwareIndexManager(registry=registry, dispatcher=dispatcher)
    result = manager._full_index(repo_info.repository_id, ctx)

    assert result.indexed == 2
    assert not result.clean
    assert result.semantic is not None
    assert result.semantic["summary_passes"] == 8
    assert result.semantic["summary_remaining_chunks"] == 17
    assert result.semantic["summary_scope_drained"] is False
    assert result.semantic["summary_continuation_required"] is True
    assert (
        result.errors
        == [
            "Missing authoritative summaries blocked strict semantic indexing after "
            "8 bounded summary passes; 17 chunks still require summaries"
        ]
    )


def test_full_index_returns_exact_low_level_blocker_when_lexical_stage_times_out(tmp_path):
    repo = _make_git_repo(tmp_path)
    commit = _get_head_commit(repo)
    repo_info = _make_repo_info(repo, commit)
    ctx = _make_ctx(repo_info.repository_id, repo, repo_info.index_path)

    registry = MagicMock()
    registry.get_repository.return_value = repo_info

    dispatcher = MagicMock()
    dispatcher.index_directory.return_value = {
        "indexed_files": 0,
        "failed_files": 1,
        "errors": [],
        "lexical_stage": "blocked_file_timeout",
        "lexical_files_attempted": 1,
        "lexical_files_completed": 0,
        "last_progress_path": None,
        "in_flight_path": str(repo / "hello.py"),
        "semantic_stage": "not_run",
        "low_level_blocker": {
            "code": "lexical_file_timeout",
            "message": "Lexical indexing timed out while processing hello.py",
        },
        "storage_diagnostics": {
            "journal_mode": "WAL",
            "busy_timeout_ms": 5000,
        },
    }

    manager = GitAwareIndexManager(registry=registry, dispatcher=dispatcher)
    result = manager._full_index(repo_info.repository_id, ctx)

    assert result.indexed == 0
    assert not result.clean
    assert result.low_level is not None
    assert result.low_level["lexical_stage"] == "blocked_file_timeout"
    assert result.low_level["low_level_blocker"]["code"] == "lexical_file_timeout"
    assert result.errors == ["Lexical indexing timed out while processing hello.py"]


def test_full_index_preserves_semantic_ready_stats_when_force_full_rebuild_succeeds(tmp_path):
    repo = _make_git_repo(tmp_path)
    commit = _get_head_commit(repo)
    repo_info = _make_repo_info(repo, commit)
    ctx = _make_ctx(repo_info.repository_id, repo, repo_info.index_path)

    registry = MagicMock()
    registry.get_repository.return_value = repo_info

    dispatcher = MagicMock()
    dispatcher.index_directory.return_value = {
        "indexed_files": 2,
        "failed_files": 0,
        "errors": [],
        "summaries_written": 8,
        "summary_chunks_attempted": 8,
        "summary_missing_chunks": 0,
        "semantic_indexed": 2,
        "semantic_failed": 0,
        "semantic_skipped": 0,
        "semantic_blocked": 0,
        "semantic_stage": "indexed",
        "semantic_error": None,
    }

    manager = GitAwareIndexManager(registry=registry, dispatcher=dispatcher)
    result = manager._full_index(repo_info.repository_id, ctx)

    assert result.indexed == 2
    assert result.failed == 0
    assert result.clean
    assert result.semantic is not None
    assert result.semantic["summaries_written"] == 8
    assert result.semantic["summary_chunks_attempted"] == 8
    assert result.semantic["summary_missing_chunks"] == 0
    assert result.semantic["semantic_indexed"] == 2
    assert result.semantic["semantic_blocked"] == 0
    assert result.semantic["semantic_stage"] == "indexed"


def test_full_index_carries_forward_downstream_blocker_after_changelog_repair(tmp_path):
    repo = _make_git_repo(tmp_path)
    commit = _get_head_commit(repo)
    repo_info = _make_repo_info(repo, commit)
    ctx = _make_ctx(repo_info.repository_id, repo, repo_info.index_path)

    registry = MagicMock()
    registry.get_repository.return_value = repo_info

    dispatcher = MagicMock()
    dispatcher.index_directory.return_value = {
        "indexed_files": 2,
        "failed_files": 0,
        "errors": [],
        "lexical_stage": "completed",
        "lexical_files_attempted": 2,
        "lexical_files_completed": 2,
        "last_progress_path": str(repo / "CHANGELOG.md"),
        "in_flight_path": None,
        "summaries_written": 0,
        "summary_chunks_attempted": 2,
        "summary_missing_chunks": 2,
        "semantic_indexed": 0,
        "semantic_failed": 0,
        "semantic_skipped": 0,
        "semantic_blocked": 1,
        "semantic_stage": "blocked_missing_summaries",
        "semantic_error": "Missing authoritative summaries blocked strict semantic indexing",
    }

    manager = GitAwareIndexManager(registry=registry, dispatcher=dispatcher)
    result = manager._full_index(repo_info.repository_id, ctx)

    assert result.indexed == 2
    assert not result.clean
    assert result.low_level is None
    assert result.semantic is not None
    assert result.semantic["semantic_stage"] == "blocked_missing_summaries"
    assert result.errors == ["Missing authoritative summaries blocked strict semantic indexing"]


def test_full_index_carries_forward_downstream_blocker_after_roadmap_repair(tmp_path):
    repo = _make_git_repo(tmp_path)
    commit = _get_head_commit(repo)
    repo_info = _make_repo_info(repo, commit)
    ctx = _make_ctx(repo_info.repository_id, repo, repo_info.index_path)

    registry = MagicMock()
    registry.get_repository.return_value = repo_info

    dispatcher = MagicMock()
    dispatcher.index_directory.return_value = {
        "indexed_files": 2,
        "failed_files": 0,
        "errors": [],
        "lexical_stage": "completed",
        "lexical_files_attempted": 2,
        "lexical_files_completed": 2,
        "last_progress_path": str(repo / "ROADMAP.md"),
        "in_flight_path": None,
        "summaries_written": 0,
        "summary_chunks_attempted": 2,
        "summary_missing_chunks": 2,
        "semantic_indexed": 0,
        "semantic_failed": 0,
        "semantic_skipped": 0,
        "semantic_blocked": 1,
        "semantic_stage": "blocked_missing_summaries",
        "semantic_error": "Missing authoritative summaries blocked strict semantic indexing",
    }

    manager = GitAwareIndexManager(registry=registry, dispatcher=dispatcher)
    result = manager._full_index(repo_info.repository_id, ctx)

    assert result.indexed == 2
    assert not result.clean
    assert result.low_level is None
    assert result.semantic is not None
    assert result.semantic["semantic_stage"] == "blocked_missing_summaries"
    assert result.errors == ["Missing authoritative summaries blocked strict semantic indexing"]


def test_full_index_carries_forward_downstream_blocker_after_final_analysis_repair(tmp_path):
    repo = _make_git_repo(tmp_path)
    commit = _get_head_commit(repo)
    repo_info = _make_repo_info(repo, commit)
    ctx = _make_ctx(repo_info.repository_id, repo, repo_info.index_path)

    registry = MagicMock()
    registry.get_repository.return_value = repo_info

    dispatcher = MagicMock()
    dispatcher.index_directory.return_value = {
        "indexed_files": 2,
        "failed_files": 0,
        "errors": [],
        "lexical_stage": "completed",
        "lexical_files_attempted": 2,
        "lexical_files_completed": 2,
        "last_progress_path": str(repo / "FINAL_COMPREHENSIVE_MCP_ANALYSIS.md"),
        "in_flight_path": None,
        "summaries_written": 0,
        "summary_chunks_attempted": 2,
        "summary_missing_chunks": 2,
        "semantic_indexed": 0,
        "semantic_failed": 0,
        "semantic_skipped": 0,
        "semantic_blocked": 1,
        "semantic_stage": "blocked_missing_summaries",
        "semantic_error": "Missing authoritative summaries blocked strict semantic indexing",
    }

    manager = GitAwareIndexManager(registry=registry, dispatcher=dispatcher)
    result = manager._full_index(repo_info.repository_id, ctx)

    assert result.indexed == 2
    assert not result.clean
    assert result.low_level is None
    assert result.semantic is not None
    assert result.semantic["semantic_stage"] == "blocked_missing_summaries"
    assert result.errors == ["Missing authoritative summaries blocked strict semantic indexing"]


def test_full_index_carries_forward_downstream_blocker_after_agents_repair(tmp_path):
    repo = _make_git_repo(tmp_path)
    commit = _get_head_commit(repo)
    repo_info = _make_repo_info(repo, commit)
    ctx = _make_ctx(repo_info.repository_id, repo, repo_info.index_path)

    registry = MagicMock()
    registry.get_repository.return_value = repo_info

    dispatcher = MagicMock()
    dispatcher.index_directory.return_value = {
        "indexed_files": 2,
        "failed_files": 0,
        "errors": [],
        "lexical_stage": "completed",
        "lexical_files_attempted": 2,
        "lexical_files_completed": 2,
        "last_progress_path": str(repo / "AGENTS.md"),
        "in_flight_path": None,
        "summaries_written": 0,
        "summary_chunks_attempted": 2,
        "summary_missing_chunks": 2,
        "semantic_indexed": 0,
        "semantic_failed": 0,
        "semantic_skipped": 0,
        "semantic_blocked": 1,
        "semantic_stage": "blocked_missing_summaries",
        "semantic_error": "Missing authoritative summaries blocked strict semantic indexing",
    }

    manager = GitAwareIndexManager(registry=registry, dispatcher=dispatcher)
    result = manager._full_index(repo_info.repository_id, ctx)

    assert result.indexed == 2
    assert not result.clean
    assert result.low_level is None
    assert result.semantic is not None
    assert result.semantic["semantic_stage"] == "blocked_missing_summaries"
    assert result.errors == ["Missing authoritative summaries blocked strict semantic indexing"]


def test_full_index_carries_forward_downstream_blocker_after_readme_repair(tmp_path):
    repo = _make_git_repo(tmp_path)
    commit = _get_head_commit(repo)
    repo_info = _make_repo_info(repo, commit)
    ctx = _make_ctx(repo_info.repository_id, repo, repo_info.index_path)

    registry = MagicMock()
    registry.get_repository.return_value = repo_info

    dispatcher = MagicMock()
    dispatcher.index_directory.return_value = {
        "indexed_files": 3,
        "failed_files": 0,
        "errors": [],
        "lexical_stage": "completed",
        "lexical_files_attempted": 3,
        "lexical_files_completed": 3,
        "last_progress_path": str(repo / "README.md"),
        "in_flight_path": None,
        "summaries_written": 0,
        "summary_chunks_attempted": 3,
        "summary_missing_chunks": 3,
        "semantic_indexed": 0,
        "semantic_failed": 0,
        "semantic_skipped": 0,
        "semantic_blocked": 1,
        "semantic_stage": "blocked_missing_summaries",
        "semantic_error": "Missing authoritative summaries blocked strict semantic indexing",
    }

    manager = GitAwareIndexManager(registry=registry, dispatcher=dispatcher)
    result = manager._full_index(repo_info.repository_id, ctx)

    assert result.indexed == 3
    assert not result.clean
    assert result.low_level is None
    assert result.semantic is not None
    assert result.semantic["semantic_stage"] == "blocked_missing_summaries"
    assert result.errors == ["Missing authoritative summaries blocked strict semantic indexing"]


def test_force_full_sync_does_not_advance_commit_when_semantic_stage_is_blocked(tmp_path):
    repo = _make_git_repo(tmp_path)
    old_commit = _get_head_commit(repo)
    repo_info = _make_repo_info(repo, old_commit)
    ctx = _make_ctx(repo_info.repository_id, repo, repo_info.index_path)

    registry = MagicMock()
    registry.get_repository.return_value = repo_info
    registry.update_git_state.return_value = {"commit": old_commit, "branch": "main"}

    manager = GitAwareIndexManager(registry=registry, dispatcher=MagicMock())
    manager._resolve_ctx = MagicMock(return_value=ctx)
    manager._index_exists = MagicMock(return_value=True)
    manager._index_has_durable_rows = MagicMock(return_value=True)
    manager._full_index = MagicMock(
        return_value=UpdateResult(
            indexed=1,
            failed=0,
            errors=["Summary generation plateaued before strict semantic indexing could start"],
            semantic={
                "summary_passes": 3,
                "summaries_written": 12,
                "summary_chunks_attempted": 12,
                "summary_missing_chunks": 4,
                "semantic_indexed": 0,
                "semantic_failed": 0,
                "semantic_skipped": 0,
                "semantic_blocked": 1,
                "semantic_stage": "blocked_summary_plateau",
                "semantic_error": "Summary generation plateaued before strict semantic indexing could start",
            },
        )
    )

    result = manager.sync_repository_index(repo_info.repository_id, force_full=True)

    assert result.action == "failed"
    assert (
        result.error
        == "Summary generation plateaued before strict semantic indexing could start"
    )
    registry.update_staleness_reason.assert_called_once_with(
        repo_info.repository_id, "partial_index_failure"
    )
    registry.update_indexed_commit.assert_not_called()


def test_force_full_sync_preserves_exact_summary_call_timeout_blocker(tmp_path):
    repo = _make_git_repo(tmp_path)
    old_commit = _get_head_commit(repo)
    repo_info = _make_repo_info(repo, old_commit)
    ctx = _make_ctx(repo_info.repository_id, repo, repo_info.index_path)

    registry = MagicMock()
    registry.get_repository.return_value = repo_info
    registry.update_git_state.return_value = {"commit": old_commit, "branch": "main"}

    manager = GitAwareIndexManager(registry=registry, dispatcher=MagicMock())
    manager._resolve_ctx = MagicMock(return_value=ctx)
    manager._index_exists = MagicMock(return_value=True)
    manager._index_has_durable_rows = MagicMock(return_value=True)
    manager._full_index = MagicMock(
        return_value=UpdateResult(
            indexed=1,
            failed=0,
            errors=[
                "Authoritative summary call timed out after 30 seconds before any summary was "
                f"written for {repo / 'README.md'}; 4 chunks still require summaries"
            ],
            semantic={
                "summary_passes": 0,
                "summaries_written": 0,
                "summary_chunks_attempted": 1,
                "summary_missing_chunks": 4,
                "summary_remaining_chunks": 4,
                "summary_scope_drained": False,
                "summary_call_timed_out": True,
                "summary_call_file_path": str(repo / "README.md"),
                "summary_call_chunk_ids": ["chunk-1"],
                "summary_call_timeout_seconds": 30.0,
                "semantic_indexed": 0,
                "semantic_failed": 0,
                "semantic_skipped": 0,
                "semantic_blocked": 1,
                "semantic_stage": "blocked_summary_call_timeout",
                "semantic_error": (
                    "Authoritative summary call timed out after 30 seconds before any summary "
                    f"was written for {repo / 'README.md'}; 4 chunks still require summaries"
                ),
            },
        )
    )

    result = manager.sync_repository_index(repo_info.repository_id, force_full=True)

    assert result.action == "failed"
    assert result.semantic is not None
    assert result.semantic["summary_call_timed_out"] is True
    assert result.semantic["summary_call_file_path"] == str(repo / "README.md")
    assert result.semantic["summary_call_chunk_ids"] == ["chunk-1"]
    assert result.semantic["summary_call_timeout_seconds"] == 30.0
    registry.update_staleness_reason.assert_called_once_with(
        repo_info.repository_id, "partial_index_failure"
    )


def test_force_full_sync_preserves_durable_exit_trace_on_interrupt(tmp_path):
    repo = _make_git_repo(tmp_path)
    commit = _get_head_commit(repo)
    repo_info = _make_repo_info(repo, commit)
    repo_info.last_indexed_commit = "older-indexed-commit"
    repo_info.index_path.touch()

    registry = MagicMock()
    registry.get_repository.return_value = repo_info
    registry.update_git_state.return_value = {"commit": commit, "branch": "main"}

    manager = _make_manager(registry)
    ctx = _make_ctx(repo_info.repository_id, repo, repo_info.index_path)
    manager._resolve_ctx = MagicMock(return_value=ctx)
    manager._index_exists = MagicMock(return_value=True)
    manager._index_has_durable_rows = MagicMock(return_value=True)

    def _interrupting_full_index(repo_id, _ctx):
        manager._write_force_full_exit_trace(
            repo_info,
            {
                "status": "interrupted",
                "stage": "blocked_summary_call_timeout",
                "stage_family": "semantic_closeout",
                "current_commit": commit,
                "indexed_commit_before": "older-indexed-commit",
                "last_progress_path": str(repo / "README.md"),
                "in_flight_path": str(repo / "README.md"),
                "summary_call_timed_out": True,
                "summary_call_file_path": str(repo / "README.md"),
                "summary_call_chunk_ids": ["chunk-1"],
                "summary_call_timeout_seconds": 30.0,
                "blocker_source": "summary_call_shutdown",
            },
        )
        raise KeyboardInterrupt("synthetic interrupt")

    manager._full_index = MagicMock(side_effect=_interrupting_full_index)

    try:
        manager.sync_repository_index(repo_info.repository_id, force_full=True)
    except KeyboardInterrupt:
        pass
    else:
        raise AssertionError("Expected synthetic KeyboardInterrupt")

    trace_path = Path(repo_info.index_location) / "force_full_exit_trace.json"
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    assert trace["status"] == "interrupted"
    assert trace["stage"] == "blocked_summary_call_timeout"
    assert trace["stage_family"] == "semantic_closeout"
    assert trace["current_commit"] == commit
    assert trace["indexed_commit_before"] == "older-indexed-commit"
    assert trace["summary_call_timed_out"] is True
    assert trace["blocker_source"] == "summary_call_shutdown"
    registry.update_indexed_commit.assert_not_called()


def test_force_full_sync_terminalizes_running_trace_when_later_test_pair_crashes(tmp_path):
    repo = _make_git_repo(tmp_path)
    commit = _get_head_commit(repo)
    repo_info = _make_repo_info(repo, commit)
    repo_info.last_indexed_commit = "older-indexed-commit"
    repo_info.index_path.touch()

    registry = MagicMock()
    registry.get_repository.return_value = repo_info
    registry.update_git_state.return_value = {"commit": commit, "branch": "main"}

    manager = _make_manager(registry)
    ctx = _make_ctx(repo_info.repository_id, repo, repo_info.index_path)
    manager._resolve_ctx = MagicMock(return_value=ctx)
    manager._index_exists = MagicMock(return_value=True)
    manager._index_has_durable_rows = MagicMock(return_value=True)

    prior_file = repo / "tests" / "test_deployment_runbook_shape.py"
    blocked_file = repo / "tests" / "test_reindex_resume.py"

    def _crashing_full_index(repo_id, _ctx, progress_callback=None):
        assert progress_callback is not None
        progress_callback(
            {
                "stage": "lexical_walking",
                "stage_family": "lexical",
                "blocker_source": "lexical_mutation",
                "lexical_stage": "walking",
                "semantic_stage": "not_run",
                "last_progress_path": str(prior_file),
                "in_flight_path": str(blocked_file),
                "summary_call_timed_out": False,
                "summary_call_file_path": None,
                "summary_call_chunk_ids": [],
                "summary_call_timeout_seconds": None,
            }
        )
        raise RuntimeError("synthetic crash after later lexical pair")

    manager._full_index = MagicMock(side_effect=_crashing_full_index)

    with pytest.raises(RuntimeError, match="synthetic crash after later lexical pair"):
        manager.sync_repository_index(repo_info.repository_id, force_full=True)

    trace_path = Path(repo_info.index_location) / "force_full_exit_trace.json"
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    assert trace["status"] == "interrupted"
    assert trace["stage"] == "lexical_walking"
    assert trace["stage_family"] == "lexical"
    assert trace["current_commit"] == commit
    assert trace["indexed_commit_before"] == "older-indexed-commit"
    assert trace["last_progress_path"] == str(prior_file)
    assert trace["in_flight_path"] == str(blocked_file)
    assert trace["blocker_source"] == "lexical_mutation"
    assert ".devcontainer/devcontainer.json" not in (trace.get("last_progress_path") or "")
    assert "scripts/quick_mcp_vs_native_validation.py" not in (trace.get("last_progress_path") or "")
    assert "tests/test_artifact_publish_race.py" not in (trace.get("last_progress_path") or "")
    registry.update_indexed_commit.assert_not_called()


def test_force_full_sync_terminalizes_running_trace_when_later_root_test_pair_crashes(tmp_path):
    repo = _make_git_repo(tmp_path)
    commit = _get_head_commit(repo)
    repo_info = _make_repo_info(repo, commit)
    repo_info.last_indexed_commit = "older-indexed-commit"
    repo_info.index_path.touch()

    registry = MagicMock()
    registry.get_repository.return_value = repo_info
    registry.update_git_state.return_value = {"commit": commit, "branch": "main"}

    manager = _make_manager(registry)
    ctx = _make_ctx(repo_info.repository_id, repo, repo_info.index_path)
    manager._resolve_ctx = MagicMock(return_value=ctx)
    manager._index_exists = MagicMock(return_value=True)
    manager._index_has_durable_rows = MagicMock(return_value=True)

    prior_file = repo / "tests" / "root_tests" / "test_voyage_api.py"
    blocked_file = repo / "tests" / "root_tests" / "run_reranking_tests.py"

    def _crashing_full_index(repo_id, _ctx, progress_callback=None):
        assert progress_callback is not None
        progress_callback(
            {
                "stage": "lexical_walking",
                "stage_family": "lexical",
                "blocker_source": "lexical_mutation",
                "lexical_stage": "walking",
                "semantic_stage": "not_run",
                "last_progress_path": str(prior_file),
                "in_flight_path": str(blocked_file),
                "summary_call_timed_out": False,
                "summary_call_file_path": None,
                "summary_call_chunk_ids": [],
                "summary_call_timeout_seconds": None,
            }
        )
        raise RuntimeError("synthetic crash after later root-test pair")

    manager._full_index = MagicMock(side_effect=_crashing_full_index)

    with pytest.raises(RuntimeError, match="synthetic crash after later root-test pair"):
        manager.sync_repository_index(repo_info.repository_id, force_full=True)

    trace_path = Path(repo_info.index_location) / "force_full_exit_trace.json"
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    assert trace["status"] == "interrupted"
    assert trace["stage"] == "lexical_walking"
    assert trace["stage_family"] == "lexical"
    assert trace["current_commit"] == commit
    assert trace["indexed_commit_before"] == "older-indexed-commit"
    assert trace["last_progress_path"] == str(prior_file)
    assert trace["in_flight_path"] == str(blocked_file)
    assert trace["blocker_source"] == "lexical_mutation"
    assert ".devcontainer/devcontainer.json" not in (trace.get("last_progress_path") or "")
    assert "scripts/validate_mcp_comprehensive.py" not in (trace.get("last_progress_path") or "")
    assert "tests/test_artifact_publish_race.py" not in (trace.get("last_progress_path") or "")
    assert "tests/test_reindex_resume.py" not in (trace.get("last_progress_path") or "")
    registry.update_indexed_commit.assert_not_called()


def test_force_full_sync_marks_durable_exit_trace_completed_on_clean_closeout(tmp_path):
    repo = _make_git_repo(tmp_path)
    commit = _get_head_commit(repo)
    repo_info = _make_repo_info(repo, commit)
    repo_info.last_indexed_commit = None
    repo_info.index_path.touch()

    registry = MagicMock()
    registry.get_repository.return_value = repo_info
    registry.update_git_state.return_value = {"commit": commit, "branch": "main"}
    registry.update_indexed_commit.return_value = True

    manager = _make_manager(registry)
    ctx = _make_ctx(repo_info.repository_id, repo, repo_info.index_path)
    manager._resolve_ctx = MagicMock(return_value=ctx)
    manager._index_exists = MagicMock(return_value=True)
    manager._index_has_durable_rows = MagicMock(return_value=True)
    manager._full_index = MagicMock(
        return_value=UpdateResult(
            indexed=1,
            semantic={
                "semantic_stage": "indexed",
            },
        )
    )

    result = manager.sync_repository_index(repo_info.repository_id, force_full=True)

    trace_path = Path(repo_info.index_location) / "force_full_exit_trace.json"
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    assert result.action == "full_index"
    assert trace["status"] == "completed"
    assert trace["stage"] == "force_full_completed"
    assert trace["stage_family"] == "final_closeout"
    assert trace["current_commit"] == commit
    assert trace["indexed_commit_before"] is None
    registry.update_indexed_commit.assert_called_once_with(
        repo_info.repository_id, commit, branch="main"
    )


def test_force_full_progress_callback_persists_fresh_in_flight_snapshot(tmp_path):
    repo = _make_git_repo(tmp_path)
    commit = _get_head_commit(repo)
    repo_info = _make_repo_info(repo, commit)
    repo_info.last_indexed_commit = "older-indexed-commit"

    manager = GitAwareIndexManager(registry=MagicMock(), dispatcher=MagicMock())
    callback = manager._make_force_full_progress_callback(
        repo_info=repo_info,
        current_commit=commit,
        indexed_commit_before=repo_info.last_indexed_commit,
    )

    callback(
        {
            "stage": "lexical_walking",
            "stage_family": "lexical",
            "blocker_source": "lexical_mutation",
            "lexical_stage": "walking",
            "semantic_stage": "not_run",
            "last_progress_path": str(repo / "ai_docs" / "pytest_overview.md"),
            "in_flight_path": str(repo / "docs" / "status" / "SEMANTIC_DOGFOOD_REBUILD.md"),
            "summary_call_timed_out": False,
            "summary_call_file_path": None,
            "summary_call_chunk_ids": [],
            "summary_call_timeout_seconds": None,
        }
    )

    trace_path = Path(repo_info.index_location) / "force_full_exit_trace.json"
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    assert trace["status"] == "running"
    assert trace["stage"] == "lexical_walking"
    assert trace["stage_family"] == "lexical"
    assert trace["current_commit"] == commit
    assert trace["indexed_commit_before"] == "older-indexed-commit"
    assert trace["last_progress_path"] == str(repo / "ai_docs" / "pytest_overview.md")
    assert trace["in_flight_path"] == str(repo / "docs" / "status" / "SEMANTIC_DOGFOOD_REBUILD.md")
    assert isinstance(trace["process_id"], int)
    assert trace["trace_timestamp"]


def test_force_full_progress_callback_persists_later_test_pair_snapshot(tmp_path):
    repo = _make_git_repo(tmp_path)
    commit = _get_head_commit(repo)
    repo_info = _make_repo_info(repo, commit)
    repo_info.last_indexed_commit = "older-indexed-commit"

    manager = GitAwareIndexManager(registry=MagicMock(), dispatcher=MagicMock())
    callback = manager._make_force_full_progress_callback(
        repo_info=repo_info,
        current_commit=commit,
        indexed_commit_before=repo_info.last_indexed_commit,
    )
    prior_file = repo / "tests" / "test_deployment_runbook_shape.py"
    blocked_file = repo / "tests" / "test_reindex_resume.py"

    callback(
        {
            "stage": "lexical_walking",
            "stage_family": "lexical",
            "blocker_source": "lexical_mutation",
            "lexical_stage": "walking",
            "semantic_stage": "not_run",
            "last_progress_path": str(prior_file),
            "in_flight_path": str(blocked_file),
            "summary_call_timed_out": False,
            "summary_call_file_path": None,
            "summary_call_chunk_ids": [],
            "summary_call_timeout_seconds": None,
        }
    )

    trace_path = Path(repo_info.index_location) / "force_full_exit_trace.json"
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    assert trace["status"] == "running"
    assert trace["stage"] == "lexical_walking"
    assert trace["stage_family"] == "lexical"
    assert trace["current_commit"] == commit
    assert trace["indexed_commit_before"] == "older-indexed-commit"
    assert trace["last_progress_path"] == str(prior_file)
    assert trace["in_flight_path"] == str(blocked_file)
    assert ".devcontainer/devcontainer.json" not in (trace.get("last_progress_path") or "")
    assert "scripts/quick_mcp_vs_native_validation.py" not in (trace.get("last_progress_path") or "")
    assert "tests/test_artifact_publish_race.py" not in (trace.get("last_progress_path") or "")
    assert trace["trace_timestamp"]


def test_force_full_progress_callback_persists_later_script_pair_snapshot(tmp_path):
    repo = _make_git_repo(tmp_path)
    commit = _get_head_commit(repo)
    repo_info = _make_repo_info(repo, commit)
    repo_info.last_indexed_commit = "older-indexed-commit"

    manager = GitAwareIndexManager(registry=MagicMock(), dispatcher=MagicMock())
    callback = manager._make_force_full_progress_callback(
        repo_info=repo_info,
        current_commit=commit,
        indexed_commit_before=repo_info.last_indexed_commit,
    )
    prior_file = repo / "scripts" / "run_test_batch.py"
    blocked_file = repo / "scripts" / "validate_mcp_comprehensive.py"

    callback(
        {
            "stage": "lexical_walking",
            "stage_family": "lexical",
            "blocker_source": "lexical_mutation",
            "lexical_stage": "walking",
            "semantic_stage": "not_run",
            "last_progress_path": str(prior_file),
            "in_flight_path": str(blocked_file),
            "summary_call_timed_out": False,
            "summary_call_file_path": None,
            "summary_call_chunk_ids": [],
            "summary_call_timeout_seconds": None,
        }
    )

    trace_path = Path(repo_info.index_location) / "force_full_exit_trace.json"
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    assert trace["status"] == "running"
    assert trace["stage"] == "lexical_walking"
    assert trace["stage_family"] == "lexical"
    assert trace["current_commit"] == commit
    assert trace["indexed_commit_before"] == "older-indexed-commit"
    assert trace["last_progress_path"] == str(prior_file)
    assert trace["in_flight_path"] == str(blocked_file)
    assert ".devcontainer/devcontainer.json" not in (trace.get("last_progress_path") or "")
    assert "scripts/quick_mcp_vs_native_validation.py" not in (trace.get("last_progress_path") or "")
    assert "tests/test_artifact_publish_race.py" not in (trace.get("last_progress_path") or "")
    assert trace["trace_timestamp"]


def test_force_full_progress_callback_persists_later_root_test_pair_snapshot(tmp_path):
    repo = _make_git_repo(tmp_path)
    commit = _get_head_commit(repo)
    repo_info = _make_repo_info(repo, commit)
    repo_info.last_indexed_commit = "older-indexed-commit"

    manager = GitAwareIndexManager(registry=MagicMock(), dispatcher=MagicMock())
    callback = manager._make_force_full_progress_callback(
        repo_info=repo_info,
        current_commit=commit,
        indexed_commit_before=repo_info.last_indexed_commit,
    )
    prior_file = repo / "tests" / "root_tests" / "test_voyage_api.py"
    blocked_file = repo / "tests" / "root_tests" / "run_reranking_tests.py"

    callback(
        {
            "stage": "lexical_walking",
            "stage_family": "lexical",
            "blocker_source": "lexical_mutation",
            "lexical_stage": "walking",
            "semantic_stage": "not_run",
            "last_progress_path": str(prior_file),
            "in_flight_path": str(blocked_file),
            "summary_call_timed_out": False,
            "summary_call_file_path": None,
            "summary_call_chunk_ids": [],
            "summary_call_timeout_seconds": None,
        }
    )

    trace_path = Path(repo_info.index_location) / "force_full_exit_trace.json"
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    assert trace["status"] == "running"
    assert trace["stage"] == "lexical_walking"
    assert trace["stage_family"] == "lexical"
    assert trace["current_commit"] == commit
    assert trace["indexed_commit_before"] == "older-indexed-commit"
    assert trace["last_progress_path"] == str(prior_file)
    assert trace["in_flight_path"] == str(blocked_file)
    assert ".devcontainer/devcontainer.json" not in (trace.get("last_progress_path") or "")
    assert "scripts/validate_mcp_comprehensive.py" not in (trace.get("last_progress_path") or "")
    assert "tests/test_artifact_publish_race.py" not in (trace.get("last_progress_path") or "")
    assert "tests/test_reindex_resume.py" not in (trace.get("last_progress_path") or "")
    assert trace["trace_timestamp"]


def test_force_full_progress_callback_preserves_last_progress_path_across_semantic_handoff(
    tmp_path,
):
    repo = _make_git_repo(tmp_path)
    commit = _get_head_commit(repo)
    repo_info = _make_repo_info(repo, commit)
    repo_info.last_indexed_commit = "older-indexed-commit"

    manager = GitAwareIndexManager(registry=MagicMock(), dispatcher=MagicMock())
    callback = manager._make_force_full_progress_callback(
        repo_info=repo_info,
        current_commit=commit,
        indexed_commit_before=repo_info.last_indexed_commit,
    )
    devcontainer_path = repo / ".devcontainer" / "devcontainer.json"

    callback(
        {
            "stage": "force_full_closeout_handoff",
            "stage_family": "final_closeout",
            "blocker_source": "final_closeout",
            "lexical_stage": "completed",
            "semantic_stage": "not_run",
            "last_progress_path": str(devcontainer_path),
            "in_flight_path": None,
        }
    )
    callback(
        {
            "stage": "summary_shutdown_started",
            "stage_family": "summary_shutdown",
            "blocker_source": "summary_call_shutdown",
            "lexical_stage": "completed",
            "semantic_stage": "not_run",
            "last_progress_path": None,
            "in_flight_path": None,
        }
    )

    trace_path = Path(repo_info.index_location) / "force_full_exit_trace.json"
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    assert trace["stage"] == "summary_shutdown_started"
    assert trace["stage_family"] == "summary_shutdown"
    assert trace["last_progress_path"] == str(devcontainer_path)
    assert trace["in_flight_path"] is None


def test_force_full_progress_callback_preserves_later_included_path_after_ignored_tail(
    tmp_path,
):
    repo = _make_git_repo(tmp_path)
    commit = _get_head_commit(repo)
    repo_info = _make_repo_info(repo, commit)
    repo_info.last_indexed_commit = "older-indexed-commit"

    manager = GitAwareIndexManager(registry=MagicMock(), dispatcher=MagicMock())
    callback = manager._make_force_full_progress_callback(
        repo_info=repo_info,
        current_commit=commit,
        indexed_commit_before=repo_info.last_indexed_commit,
    )
    later_file = repo / "mcp_server" / "cli" / "repository_commands.py"
    ignored_tail = repo / "test_workspace" / "real_repos" / "search_scaling" / "package.json"

    callback(
        {
            "stage": "lexical_walking",
            "stage_family": "lexical",
            "blocker_source": "lexical_mutation",
            "lexical_stage": "walking",
            "semantic_stage": "not_run",
            "last_progress_path": str(later_file),
            "in_flight_path": None,
        }
    )
    callback(
        {
            "stage": "force_full_closeout_handoff",
            "stage_family": "final_closeout",
            "blocker_source": "final_closeout",
            "lexical_stage": "completed",
            "semantic_stage": "not_run",
            "last_progress_path": None,
            "in_flight_path": None,
        }
    )

    trace_path = Path(repo_info.index_location) / "force_full_exit_trace.json"
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    assert trace["stage"] == "force_full_closeout_handoff"
    assert trace["stage_family"] == "final_closeout"
    assert trace["last_progress_path"] == str(later_file)
    assert trace["in_flight_path"] is None
    assert str(ignored_tail) not in (trace.get("last_progress_path") or "")


def test_force_full_sync_terminalizes_running_trace_when_same_devcontainer_relapse_persists(
    tmp_path,
):
    repo = _make_git_repo(tmp_path)
    commit = _get_head_commit(repo)
    repo_info = _make_repo_info(repo, commit)
    repo_info.last_indexed_commit = "older-indexed-commit"
    repo_info.index_path.touch()

    registry = MagicMock()
    registry.get_repository.return_value = repo_info
    registry.update_git_state.return_value = {"commit": commit, "branch": "main"}

    manager = _make_manager(registry)
    ctx = _make_ctx(repo_info.repository_id, repo, repo_info.index_path)
    manager._resolve_ctx = MagicMock(return_value=ctx)
    manager._index_exists = MagicMock(return_value=True)
    manager._index_has_durable_rows = MagicMock(return_value=True)

    blocked_file = repo / ".devcontainer" / "devcontainer.json"

    def _crashing_full_index(repo_id, _ctx, progress_callback=None):
        assert progress_callback is not None
        progress_callback(
            {
                "stage": "lexical_walking",
                "stage_family": "lexical",
                "blocker_source": "lexical_mutation",
                "lexical_stage": "walking",
                "semantic_stage": "not_run",
                "last_progress_path": str(blocked_file),
                "in_flight_path": None,
                "summary_call_timed_out": False,
                "summary_call_file_path": None,
                "summary_call_chunk_ids": [],
                "summary_call_timeout_seconds": None,
            }
        )
        raise RuntimeError("synthetic crash after renewed devcontainer relapse")

    manager._full_index = MagicMock(side_effect=_crashing_full_index)

    with pytest.raises(RuntimeError, match="synthetic crash after renewed devcontainer relapse"):
        manager.sync_repository_index(repo_info.repository_id, force_full=True)

    trace_path = Path(repo_info.index_location) / "force_full_exit_trace.json"
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    assert trace["status"] == "interrupted"
    assert trace["stage"] == "lexical_walking"
    assert trace["stage_family"] == "lexical"
    assert trace["current_commit"] == commit
    assert trace["indexed_commit_before"] == "older-indexed-commit"
    assert trace["last_progress_path"] == str(blocked_file)
    assert trace["in_flight_path"] is None
    assert trace["blocker_source"] == "lexical_mutation"
    assert ".devcontainer/post_create.sh" not in (trace.get("last_progress_path") or "")
    assert "tests/test_reindex_resume.py" not in (trace.get("last_progress_path") or "")
    assert "scripts/validate_mcp_comprehensive.py" not in (trace.get("last_progress_path") or "")
    assert "tests/root_tests/run_reranking_tests.py" not in (trace.get("last_progress_path") or "")
    registry.update_indexed_commit.assert_not_called()


def test_get_repository_status_includes_force_full_exit_trace(tmp_path):
    repo = _make_git_repo(tmp_path)
    commit = _get_head_commit(repo)
    repo_info = _make_repo_info(repo, commit)
    trace_path = Path(repo_info.index_location) / "force_full_exit_trace.json"
    trace_path.write_text(
        json.dumps(
            {
                "status": "interrupted",
                "stage": "blocked_summary_call_timeout",
                "stage_family": "semantic_closeout",
                "trace_timestamp": "2026-04-29T09:00:00Z",
                "current_commit": commit,
                "indexed_commit_before": "older-indexed-commit",
                "last_progress_path": str(repo / "README.md"),
                "in_flight_path": str(repo / "README.md"),
                "summary_call_timed_out": True,
                "summary_call_file_path": str(repo / "README.md"),
                "summary_call_chunk_ids": ["chunk-1"],
                "summary_call_timeout_seconds": 30.0,
                "blocker_source": "summary_call_shutdown",
            }
        ),
        encoding="utf-8",
    )

    registry = MagicMock()
    registry.get_repository.return_value = repo_info

    manager = GitAwareIndexManager(registry=registry, dispatcher=MagicMock())
    status = manager.get_repository_status(repo_info.repository_id)

    assert status["force_full_exit_trace"]["status"] == "interrupted"
    assert status["force_full_exit_trace"]["stage"] == "blocked_summary_call_timeout"
    assert status["force_full_exit_trace"]["stage_family"] == "semantic_closeout"
    assert status["force_full_exit_trace"]["blocker_source"] == "summary_call_shutdown"


def test_get_repository_status_terminalizes_inactive_running_force_full_trace(tmp_path):
    repo = _make_git_repo(tmp_path)
    commit = _get_head_commit(repo)
    repo_info = _make_repo_info(repo, commit)
    trace_path = Path(repo_info.index_location) / "force_full_exit_trace.json"
    trace_path.write_text(
        json.dumps(
            {
                "status": "running",
                "stage": "lexical_walking",
                "stage_family": "lexical",
                "trace_timestamp": "2026-04-29T11:00:00Z",
                "current_commit": commit,
                "indexed_commit_before": "older-indexed-commit",
                "last_progress_path": str(repo / "tests" / "test_p8_historical_sweep.py"),
                "in_flight_path": str(repo / "tests" / "test_p26_public_alpha_decision.py"),
                "process_id": 999999,
                "blocker_source": "lexical_mutation",
            }
        ),
        encoding="utf-8",
    )

    registry = MagicMock()
    registry.get_repository.return_value = repo_info

    manager = GitAwareIndexManager(registry=registry, dispatcher=MagicMock())
    status = manager.get_repository_status(repo_info.repository_id)

    assert status["force_full_exit_trace"]["status"] == "interrupted"
    assert status["force_full_exit_trace"]["stage"] == "lexical_walking"
    assert status["force_full_exit_trace"]["stage_family"] == "lexical"
    assert status["force_full_exit_trace"]["last_progress_path"] == str(
        repo / "tests" / "test_p8_historical_sweep.py"
    )
    assert status["force_full_exit_trace"]["in_flight_path"] == str(
        repo / "tests" / "test_p26_public_alpha_decision.py"
    )


def test_force_full_sync_does_not_advance_commit_when_low_level_blocker_fires(tmp_path):
    repo = _make_git_repo(tmp_path)
    old_commit = _get_head_commit(repo)
    repo_info = _make_repo_info(repo, old_commit)
    ctx = _make_ctx(repo_info.repository_id, repo, repo_info.index_path)

    registry = MagicMock()
    registry.get_repository.return_value = repo_info
    registry.update_git_state.return_value = {"commit": old_commit, "branch": "main"}

    manager = GitAwareIndexManager(registry=registry, dispatcher=MagicMock())
    manager._resolve_ctx = MagicMock(return_value=ctx)
    manager._index_exists = MagicMock(return_value=True)
    manager._index_has_durable_rows = MagicMock(return_value=True)
    manager._full_index = MagicMock(
        return_value=UpdateResult(
            indexed=0,
            failed=1,
            errors=["Lexical indexing timed out while processing hello.py"],
            low_level={
                "lexical_stage": "blocked_file_timeout",
                "lexical_files_attempted": 1,
                "lexical_files_completed": 0,
                "last_progress_path": None,
                "in_flight_path": str(repo / "hello.py"),
                "low_level_blocker": {
                    "code": "lexical_file_timeout",
                    "message": "Lexical indexing timed out while processing hello.py",
                },
            },
            semantic={"semantic_stage": "not_run"},
        )
    )

    result = manager.sync_repository_index(repo_info.repository_id, force_full=True)

    assert result.action == "failed"
    assert result.error == "Lexical indexing timed out while processing hello.py"


def test_force_full_sync_does_not_advance_commit_when_later_script_pair_blocks(tmp_path):
    repo = _make_git_repo(tmp_path)
    commit = _get_head_commit(repo)
    repo_info = _make_repo_info(repo, commit)
    repo_info.last_indexed_commit = "older-indexed-commit"
    repo_info.index_path.touch()

    registry = MagicMock()
    registry.get_repository.return_value = repo_info
    registry.update_git_state.return_value = {"commit": commit, "branch": "main"}
    registry.update_indexed_commit.return_value = True

    manager = _make_manager(registry)
    ctx = _make_ctx(repo_info.repository_id, repo, repo_info.index_path)
    manager._resolve_ctx = MagicMock(return_value=ctx)
    manager._index_exists = MagicMock(return_value=True)
    manager._index_has_durable_rows = MagicMock(return_value=True)

    prior_file = repo / "scripts" / "run_test_batch.py"
    blocked_file = repo / "scripts" / "validate_mcp_comprehensive.py"

    def _crashing_full_index(repo_id, _ctx, progress_callback=None):
        assert progress_callback is not None
        progress_callback(
            {
                "stage": "lexical_walking",
                "stage_family": "lexical",
                "blocker_source": "lexical_mutation",
                "lexical_stage": "walking",
                "semantic_stage": "not_run",
                "last_progress_path": str(prior_file),
                "in_flight_path": str(blocked_file),
                "summary_call_timed_out": False,
                "summary_call_file_path": None,
                "summary_call_chunk_ids": [],
                "summary_call_timeout_seconds": None,
            }
        )
        raise RuntimeError("synthetic crash after later lexical script pair")

    manager._full_index = MagicMock(side_effect=_crashing_full_index)

    with pytest.raises(RuntimeError, match="synthetic crash after later lexical script pair"):
        manager.sync_repository_index(repo_info.repository_id, force_full=True)

    trace_path = Path(repo_info.index_location) / "force_full_exit_trace.json"
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    assert trace["status"] == "interrupted"
    assert trace["stage"] == "lexical_walking"
    assert trace["stage_family"] == "lexical"
    assert trace["current_commit"] == commit
    assert trace["indexed_commit_before"] == "older-indexed-commit"
    assert trace["last_progress_path"] == str(prior_file)
    assert trace["in_flight_path"] == str(blocked_file)
    assert trace["blocker_source"] == "lexical_mutation"
    assert ".devcontainer/devcontainer.json" not in (trace.get("last_progress_path") or "")
    assert "scripts/quick_mcp_vs_native_validation.py" not in (trace.get("last_progress_path") or "")
    assert "tests/test_artifact_publish_race.py" not in (trace.get("last_progress_path") or "")
    registry.update_indexed_commit.assert_not_called()


def test_force_full_sync_does_not_advance_commit_when_later_root_test_pair_blocks(tmp_path):
    repo = _make_git_repo(tmp_path)
    commit = _get_head_commit(repo)
    repo_info = _make_repo_info(repo, commit)
    repo_info.last_indexed_commit = "older-indexed-commit"
    repo_info.index_path.touch()

    registry = MagicMock()
    registry.get_repository.return_value = repo_info
    registry.update_git_state.return_value = {"commit": commit, "branch": "main"}

    manager = _make_manager(registry)
    ctx = _make_ctx(repo_info.repository_id, repo, repo_info.index_path)
    manager._resolve_ctx = MagicMock(return_value=ctx)
    manager._index_exists = MagicMock(return_value=True)
    manager._index_has_durable_rows = MagicMock(return_value=True)

    prior_file = repo / "tests" / "root_tests" / "test_voyage_api.py"
    blocked_file = repo / "tests" / "root_tests" / "run_reranking_tests.py"

    def _blocked_full_index(repo_id, _ctx, progress_callback=None):
        assert progress_callback is not None
        progress_callback(
            {
                "stage": "lexical_walking",
                "stage_family": "lexical",
                "blocker_source": "lexical_mutation",
                "lexical_stage": "walking",
                "semantic_stage": "not_run",
                "last_progress_path": str(prior_file),
                "in_flight_path": str(blocked_file),
                "summary_call_timed_out": False,
                "summary_call_file_path": None,
                "summary_call_chunk_ids": [],
                "summary_call_timeout_seconds": None,
            }
        )
        return UpdateResult(
            indexed=1,
            failed=1,
            errors=["synthetic root-test blocker"],
            low_level={
                "lexical_stage": "blocked_file_timeout",
                "lexical_files_attempted": 2,
                "lexical_files_completed": 1,
                "last_progress_path": str(prior_file),
                "in_flight_path": str(blocked_file),
                "low_level_blocker": {
                    "code": "lexical_file_timeout",
                    "message": "synthetic root-test blocker",
                },
            },
            semantic={"semantic_stage": "not_run"},
        )

    manager._full_index = MagicMock(side_effect=_blocked_full_index)

    result = manager.sync_repository_index(repo_info.repository_id, force_full=True)

    trace_path = Path(repo_info.index_location) / "force_full_exit_trace.json"
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    assert result.action == "failed"
    assert trace["status"] == "completed"
    assert trace["stage"] == "force_full_failed"
    assert trace["stage_family"] == "final_closeout"
    assert trace["current_commit"] == commit
    assert trace["indexed_commit_before"] == "older-indexed-commit"
    assert trace["last_progress_path"] == str(prior_file)
    assert trace["in_flight_path"] == str(blocked_file)
    assert trace["blocker_source"] == "lexical_mutation"
    assert ".devcontainer/devcontainer.json" not in (trace.get("last_progress_path") or "")
    assert "scripts/validate_mcp_comprehensive.py" not in (trace.get("last_progress_path") or "")
    assert "tests/test_artifact_publish_race.py" not in (trace.get("last_progress_path") or "")
    assert "tests/test_reindex_resume.py" not in (trace.get("last_progress_path") or "")
    registry.update_indexed_commit.assert_not_called()


def test_force_full_sync_trace_moves_past_fast_report_family_after_boundary_repair(tmp_path):
    repo = _make_git_repo(tmp_path)
    commit = _get_head_commit(repo)
    repo_info = _make_repo_info(repo, commit)
    ctx = _make_ctx(repo_info.repository_id, repo, repo_info.index_path)

    registry = MagicMock()
    registry.get_repository.return_value = repo_info
    registry.update_git_state.return_value = {"commit": commit, "branch": "main"}

    manager = GitAwareIndexManager(registry=registry, dispatcher=MagicMock())
    manager._resolve_ctx = MagicMock(return_value=ctx)
    manager._index_exists = MagicMock(return_value=True)
    manager._index_has_durable_rows = MagicMock(return_value=True)
    manager._full_index = MagicMock(
        return_value=UpdateResult(
            indexed=1,
            failed=1,
            errors=["Lexical indexing timed out while processing README.md"],
            low_level={
                "lexical_stage": "blocked_file_timeout",
                "lexical_files_attempted": 2,
                "lexical_files_completed": 1,
                "last_progress_path": str(repo / "src" / "main.py"),
                "in_flight_path": str(repo / "README.md"),
                "low_level_blocker": {
                    "code": "lexical_file_timeout",
                    "message": "Lexical indexing timed out while processing README.md",
                },
            },
            semantic={"semantic_stage": "not_run"},
        )
    )

    result = manager.sync_repository_index(repo_info.repository_id, force_full=True)

    trace_path = Path(repo_info.index_location) / "force_full_exit_trace.json"
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    assert result.action == "failed"
    assert "fast_test_results/fast_report_" not in (trace.get("last_progress_path") or "")
    assert "fast_test_results/fast_report_" not in (trace.get("in_flight_path") or "")
    assert trace["last_progress_path"] == str(repo / "src" / "main.py")
    assert trace["in_flight_path"] == str(repo / "README.md")
    registry.update_indexed_commit.assert_not_called()
    registry.update_indexed_commit.assert_not_called()


def test_force_full_sync_trace_moves_past_pytest_overview_after_bounded_ai_docs_repair(tmp_path):
    repo = _make_git_repo(tmp_path)
    commit = _get_head_commit(repo)
    repo_info = _make_repo_info(repo, commit)
    ctx = _make_ctx(repo_info.repository_id, repo, repo_info.index_path)

    registry = MagicMock()
    registry.get_repository.return_value = repo_info
    registry.update_git_state.return_value = {"commit": commit, "branch": "main"}

    manager = GitAwareIndexManager(registry=registry, dispatcher=MagicMock())
    manager._resolve_ctx = MagicMock(return_value=ctx)
    manager._index_exists = MagicMock(return_value=True)
    manager._index_has_durable_rows = MagicMock(return_value=True)
    manager._full_index = MagicMock(
        return_value=UpdateResult(
            indexed=2,
            failed=1,
            errors=["Lexical indexing timed out while processing docs/status/SEMANTIC_DOGFOOD_REBUILD.md"],
            low_level={
                "lexical_stage": "blocked_file_timeout",
                "lexical_files_attempted": 3,
                "lexical_files_completed": 2,
                "last_progress_path": str(repo / "src" / "semantic_preflight.py"),
                "in_flight_path": str(repo / "docs" / "status" / "SEMANTIC_DOGFOOD_REBUILD.md"),
                "low_level_blocker": {
                    "code": "lexical_file_timeout",
                    "message": (
                        "Lexical indexing timed out while processing "
                        "SEMANTIC_DOGFOOD_REBUILD.md"
                    ),
                },
            },
            semantic={"semantic_stage": "not_run"},
        )
    )

    result = manager.sync_repository_index(repo_info.repository_id, force_full=True)

    trace_path = Path(repo_info.index_location) / "force_full_exit_trace.json"
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    assert result.action == "failed"
    assert "pytest_overview.md" not in (trace.get("last_progress_path") or "")
    assert "pytest_overview.md" not in (trace.get("in_flight_path") or "")
    assert trace["last_progress_path"] == str(repo / "src" / "semantic_preflight.py")
    assert trace["in_flight_path"] == str(repo / "docs" / "status" / "SEMANTIC_DOGFOOD_REBUILD.md")
    assert trace["stage"] == "force_full_failed"
    assert trace["stage_family"] == "final_closeout"
    registry.update_indexed_commit.assert_not_called()


def test_force_full_sync_durable_trace_moves_past_jedi_ai_doc(tmp_path):
    repo = _make_git_repo(tmp_path)
    commit = _get_head_commit(repo)
    repo_info = _make_repo_info(repo, commit)
    repo_info.index_path.touch()
    ctx = _make_ctx(repo_info.repository_id, repo, repo_info.index_path)

    registry = MagicMock()
    registry.get_repository.return_value = repo_info
    registry.update_git_state.return_value = {"commit": commit, "branch": "main"}

    manager = GitAwareIndexManager(registry=registry, dispatcher=MagicMock())
    manager._resolve_ctx = MagicMock(return_value=ctx)
    manager._index_exists = MagicMock(return_value=True)
    manager._index_has_durable_rows = MagicMock(return_value=True)
    manager._full_index = MagicMock(
        return_value=UpdateResult(
            indexed=3,
            failed=1,
            errors=["Lexical indexing timed out while processing ai_docs/tree_sitter_queries.md"],
            low_level={
                "lexical_stage": "blocked_file_timeout",
                "lexical_files_attempted": 4,
                "lexical_files_completed": 3,
                "last_progress_path": str(repo / "docs" / "status" / "SEMANTIC_DOGFOOD_REBUILD.md"),
                "in_flight_path": str(repo / "ai_docs" / "tree_sitter_queries.md"),
                "low_level_blocker": {
                    "code": "lexical_file_timeout",
                    "message": (
                        "Lexical indexing timed out while processing "
                        "tree_sitter_queries.md"
                    ),
                },
            },
            semantic={"semantic_stage": "not_run"},
        )
    )

    result = manager.sync_repository_index(repo_info.repository_id, force_full=True)

    trace_path = Path(repo_info.index_location) / "force_full_exit_trace.json"
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    assert result.action == "failed"
    assert "ai_docs/jedi.md" not in (trace.get("last_progress_path") or "")
    assert "ai_docs/jedi.md" not in (trace.get("in_flight_path") or "")
    assert trace["last_progress_path"] == str(repo / "docs" / "status" / "SEMANTIC_DOGFOOD_REBUILD.md")
    assert trace["in_flight_path"] == str(repo / "ai_docs" / "tree_sitter_queries.md")
    assert trace["stage"] == "force_full_failed"
    assert trace["stage_family"] == "final_closeout"
    registry.update_indexed_commit.assert_not_called()


def test_force_full_sync_trace_moves_past_visual_report_script_after_exact_python_repair(tmp_path):
    repo = _make_git_repo(tmp_path)
    commit = _get_head_commit(repo)
    repo_info = _make_repo_info(repo, commit)
    ctx = _make_ctx(repo_info.repository_id, repo, repo_info.index_path)

    registry = MagicMock()
    registry.get_repository.return_value = repo_info
    registry.update_git_state.return_value = {"commit": commit, "branch": "main"}

    manager = GitAwareIndexManager(registry=registry, dispatcher=MagicMock())
    manager._resolve_ctx = MagicMock(return_value=ctx)
    manager._index_exists = MagicMock(return_value=True)
    manager._index_has_durable_rows = MagicMock(return_value=True)
    manager._full_index = MagicMock(
        return_value=UpdateResult(
            indexed=2,
            failed=1,
            errors=["Lexical indexing timed out while processing docs/status/SEMANTIC_DOGFOOD_REBUILD.md"],
            low_level={
                "lexical_stage": "blocked_file_timeout",
                "lexical_files_attempted": 3,
                "lexical_files_completed": 2,
                "last_progress_path": str(repo / "src" / "semantic_preflight.py"),
                "in_flight_path": str(repo / "docs" / "status" / "SEMANTIC_DOGFOOD_REBUILD.md"),
                "low_level_blocker": {
                    "code": "lexical_file_timeout",
                    "message": (
                        "Lexical indexing timed out while processing "
                        "SEMANTIC_DOGFOOD_REBUILD.md"
                    ),
                },
            },
            semantic={"semantic_stage": "not_run"},
        )
    )

    result = manager.sync_repository_index(repo_info.repository_id, force_full=True)

    trace_path = Path(repo_info.index_location) / "force_full_exit_trace.json"
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    assert result.action == "failed"
    assert "create_multi_repo_visual_report.py" not in (trace.get("last_progress_path") or "")
    assert "create_multi_repo_visual_report.py" not in (trace.get("in_flight_path") or "")
    assert trace["last_progress_path"] == str(repo / "src" / "semantic_preflight.py")
    assert trace["in_flight_path"] == str(repo / "docs" / "status" / "SEMANTIC_DOGFOOD_REBUILD.md")
    assert trace["stage"] == "force_full_failed"
    assert trace["stage_family"] == "final_closeout"
    registry.update_indexed_commit.assert_not_called()


def test_incremental_update_aggregates_semantic_mutation_stats(tmp_path):
    repo = _make_git_repo(tmp_path)
    commit = _get_head_commit(repo)
    repo_info = _make_repo_info(repo, commit)
    ctx = _make_ctx(repo_info.repository_id, repo, repo_info.index_path)

    class SemanticDispatcher(CtxSignatureDispatcher):
        def index_file(self, ctx, path):
            result = super().index_file(ctx, path)
            result.semantic = {
                "summaries_written": 1,
                "summary_chunks_attempted": 1,
                "semantic_indexed": 1,
                "semantic_stage": "indexed",
            }
            return result

        def move_file(self, ctx, old_path, new_path, content_hash=None):
            result = super().move_file(ctx, old_path, new_path, content_hash)
            result.semantic = {
                "vectors_deleted": 2,
                "summaries_preserved": 1,
                "semantic_stage": "indexed",
            }
            return result

    dispatcher = SemanticDispatcher()
    manager = GitAwareIndexManager(registry=MagicMock(get_repository=MagicMock(return_value=repo_info)), dispatcher=dispatcher)
    changes = ChangeSet(
        added=[],
        modified=["hello.py"],
        deleted=[],
        renamed=[("old.py", "hello.py")],
    )

    result = manager._incremental_index_update(repo_info.repository_id, ctx, changes)

    assert result.failed == 0
    assert result.semantic is not None
    assert result.semantic["summaries_written"] == 1
    assert result.semantic["semantic_indexed"] == 1
    assert result.semantic["vectors_deleted"] == 2
    assert result.semantic["summaries_preserved"] == 1
