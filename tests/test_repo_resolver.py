"""Tests for mcp_server.core.repo_resolver — SL-3."""

import sqlite3
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from mcp_server.storage.multi_repo_manager import RepositoryInfo
from mcp_server.storage.repo_identity import compute_repo_id
from mcp_server.storage.repository_registry import RepositoryRegistry
from mcp_server.storage.sqlite_store import SQLiteStore

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def git(*args, cwd=None):
    subprocess.run(["git"] + list(args), cwd=cwd, check=True, capture_output=True)


def make_git_repo(path: Path) -> Path:
    """Init a git repo with one commit. Returns path."""
    path.mkdir(parents=True, exist_ok=True)
    git("init", "-b", "main", str(path))
    git("config", "user.email", "test@test.com", cwd=path)
    git("config", "user.name", "Test", cwd=path)
    (path / "README.md").write_text("hello")
    git("add", "README.md", cwd=path)
    git("commit", "-m", "init", cwd=path)
    return path


def make_registry_with_repo(tmp_path: Path, repo_path: Path):
    """Register repo_path in a fresh RepositoryRegistry backed by tmp_path."""
    registry_file = tmp_path / "registry.json"
    index_dir = repo_path / ".mcp-index"
    index_dir.mkdir(parents=True, exist_ok=True)
    index_path = index_dir / "current.db"
    conn = sqlite3.connect(str(index_path))
    conn.close()

    registry = RepositoryRegistry(registry_file)
    repo_id = registry.register_repository(str(repo_path))
    return registry, repo_id


def make_store_registry(registry):
    from mcp_server.storage.store_registry import StoreRegistry

    return StoreRegistry.for_registry(registry)


def make_resolver(registry, store_registry):
    from mcp_server.core.repo_resolver import RepoResolver

    return RepoResolver(registry, store_registry)


# ---------------------------------------------------------------------------
# Import guard
# ---------------------------------------------------------------------------

# These will import-fail if SL-3 impl doesn't exist yet (expected for SL-3.1).
# We do NOT top-level import RepoResolver so individual tests can fail clearly.


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRepoResolver:

    # 1. Resolve from repo root
    def test_resolve_from_repo_root(self, tmp_path):
        repo_path = make_git_repo(tmp_path / "myrepo")
        registry, repo_id = make_registry_with_repo(tmp_path, repo_path)
        store_registry = make_store_registry(registry)
        resolver = make_resolver(registry, store_registry)

        ctx = resolver.resolve(repo_path)

        assert ctx is not None
        assert ctx.repo_id == compute_repo_id(repo_path).repo_id
        assert ctx.workspace_root == repo_path
        assert ctx.tracked_branch == registry.get(repo_id).tracked_branch or ""
        assert isinstance(ctx.sqlite_store, SQLiteStore)

    # 2. Resolve from nested subdirectory — workspace_root is caller path, not git_root
    def test_resolve_from_nested_subdir(self, tmp_path):
        repo_path = make_git_repo(tmp_path / "myrepo")
        registry, repo_id = make_registry_with_repo(tmp_path, repo_path)
        store_registry = make_store_registry(registry)
        resolver = make_resolver(registry, store_registry)

        nested = repo_path / "src" / "nested"
        nested.mkdir(parents=True, exist_ok=True)

        ctx = resolver.resolve(nested)

        assert ctx is not None
        assert ctx.repo_id == compute_repo_id(repo_path).repo_id
        assert ctx.workspace_root == nested

    # 3. Resolve from .git-as-file worktree
    def test_resolve_from_worktree(self, tmp_path):
        source = tmp_path / "source"
        make_git_repo(source)

        bare = tmp_path / "bare.git"
        git("clone", "--bare", str(source), str(bare))

        wt = tmp_path / "wt1"
        git("worktree", "add", str(wt), "-b", "wt-branch-1", cwd=bare)

        # Register the BARE repo
        registry_file = tmp_path / "registry.json"
        registry = RepositoryRegistry(registry_file)

        # Ensure a .mcp-index db for the bare repo
        index_dir = bare / ".mcp-index"
        index_dir.mkdir(parents=True, exist_ok=True)
        index_path = index_dir / "current.db"
        conn = sqlite3.connect(str(index_path))
        conn.close()

        # register_repository uses find_by_path which checks exact path;
        # register bare by path
        bare_repo_id = registry.register_repository(str(bare))

        store_registry = make_store_registry(registry)
        resolver = make_resolver(registry, store_registry)

        ctx = resolver.resolve(bare)
        worktree_ctx = resolver.resolve(wt)
        readiness = resolver.classify(wt)

        assert ctx is not None
        assert ctx.repo_id == compute_repo_id(bare).repo_id
        assert ctx.repo_id == bare_repo_id
        assert worktree_ctx is None
        assert readiness.state.value == "unsupported_worktree"

    # 4. Path outside any registered repo returns None
    def test_path_outside_registry_returns_none(self, tmp_path):
        registry_file = tmp_path / "registry.json"
        registry = RepositoryRegistry(registry_file)
        from mcp_server.storage.store_registry import StoreRegistry

        store_registry = StoreRegistry.for_registry(registry)
        resolver = make_resolver(registry, store_registry)

        unrelated = tmp_path / "unrelated" / "file.txt"
        unrelated.parent.mkdir(parents=True, exist_ok=True)
        unrelated.write_text("data")

        ctx = resolver.resolve(unrelated)
        assert ctx is None

    # 5. Path has .git but repo_id isn't registered → None (no auto-register)
    def test_unregistered_repo_returns_none(self, tmp_path):
        unregistered = make_git_repo(tmp_path / "unregistered_repo")

        registry_file = tmp_path / "registry.json"
        registry = RepositoryRegistry(registry_file)
        from mcp_server.storage.store_registry import StoreRegistry

        store_registry = StoreRegistry.for_registry(registry)
        resolver = make_resolver(registry, store_registry)

        ctx = resolver.resolve(unregistered)
        assert ctx is None

    # 6. find_by_path fast-path is used when registered
    def test_find_by_path_fast_path_called(self, tmp_path):
        from mcp_server.core.repo_resolver import RepoResolver

        repo_path = make_git_repo(tmp_path / "myrepo")
        registry, repo_id = make_registry_with_repo(tmp_path, repo_path)
        store_registry = make_store_registry(registry)

        mock_registry = MagicMock(wraps=registry)
        mock_registry.find_by_path.return_value = repo_id
        mock_registry.get.return_value = registry.get(repo_id)

        resolver = RepoResolver(mock_registry, store_registry)

        ctx = resolver.resolve(repo_path)

        mock_registry.find_by_path.assert_called_once()
        assert ctx is not None

    # 7. find_by_path miss → classifier fallback still returns correct context for same path
    def test_find_by_path_miss_uses_compute_fallback(self, tmp_path):
        from mcp_server.core.repo_resolver import RepoResolver

        repo_path = make_git_repo(tmp_path / "myrepo")
        registry, repo_id = make_registry_with_repo(tmp_path, repo_path)
        store_registry = make_store_registry(registry)

        mock_registry = MagicMock(wraps=registry)
        mock_registry.find_by_path.return_value = None  # force miss
        mock_registry.get.side_effect = registry.get

        resolver = RepoResolver(mock_registry, store_registry)

        ctx = resolver.resolve(repo_path)

        assert ctx is not None
        assert ctx.repo_id == repo_id

    def test_classify_registered_root_and_nested_path(self, tmp_path):
        repo_path = make_git_repo(tmp_path / "myrepo")
        registry, _repo_id = make_registry_with_repo(tmp_path, repo_path)
        resolver = make_resolver(registry, make_store_registry(registry))
        nested = repo_path / "pkg"
        nested.mkdir()

        assert resolver.classify(repo_path).state.value == "index_empty"
        assert resolver.classify(nested).state.value == "index_empty"

    def test_classify_unregistered_git_repo_and_path_outside_git(self, tmp_path):
        registry = RepositoryRegistry(tmp_path / "registry.json")
        resolver = make_resolver(registry, make_store_registry(registry))
        unregistered = make_git_repo(tmp_path / "unregistered")
        outside = tmp_path / "outside"
        outside.mkdir()

        assert resolver.classify(unregistered).state.value == "unregistered_repository"
        assert resolver.classify(outside).state.value == "unregistered_repository"

    def test_classify_unsupported_sibling_worktree(self, tmp_path):
        source = make_git_repo(tmp_path / "source")
        worktree = tmp_path / "wt"
        git("worktree", "add", str(worktree), "-b", "feature", cwd=source)

        registry, _repo_id = make_registry_with_repo(tmp_path, source)
        resolver = make_resolver(registry, make_store_registry(registry))

        assert resolver.classify(worktree).state.value == "unsupported_worktree"
        assert resolver.resolve(worktree) is None
