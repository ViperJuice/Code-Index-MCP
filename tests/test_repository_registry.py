"""Tests for RepositoryRegistry — SL-2."""

import json
import sqlite3
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from mcp_server.storage.multi_repo_manager import RepositoryInfo
from mcp_server.storage.repo_identity import compute_repo_id


def git(*args, cwd=None):
    subprocess.run(["git"] + list(args), cwd=cwd, check=True, capture_output=True)


def make_git_repo(path: Path, branch: str = "main") -> Path:
    """Create a minimal git repo with one commit."""
    git("init", "-b", branch, str(path))
    git("config", "user.email", "test@test.com", cwd=path)
    git("config", "user.name", "Test", cwd=path)
    (path / "README.md").write_text("hello")
    git("add", "README.md", cwd=path)
    git("commit", "-m", "init", cwd=path)
    return path


def make_clone(origin: Path, clone_path: Path) -> Path:
    """Clone origin to clone_path so remote tracking is set up."""
    git("clone", str(origin), str(clone_path))
    return clone_path


# ---------------------------------------------------------------------------
# RepositoryInfo additive fields
# ---------------------------------------------------------------------------


class TestRepositoryInfoAdditiveFields:
    def test_construct_with_new_fields(self, tmp_path):
        """RepositoryInfo accepts tracked_branch and git_common_dir."""
        info = RepositoryInfo(
            repository_id="x",
            name="n",
            path=tmp_path,
            index_path=tmp_path / "idx.db",
            language_stats={},
            total_files=0,
            total_symbols=0,
            indexed_at=datetime.now(),
            tracked_branch="main",
            git_common_dir=str(tmp_path / ".git"),
        )
        assert info.tracked_branch == "main"
        assert info.git_common_dir == str(tmp_path / ".git")

    def test_git_common_dir_path_coercion(self, tmp_path):
        """If a Path is passed for git_common_dir, __post_init__ coerces to str."""
        git_dir = tmp_path / ".git"
        info = RepositoryInfo(
            repository_id="x",
            name="n",
            path=tmp_path,
            index_path=tmp_path / "idx.db",
            language_stats={},
            total_files=0,
            total_symbols=0,
            indexed_at=datetime.now(),
            git_common_dir=git_dir,
        )
        assert isinstance(info.git_common_dir, str)
        assert info.git_common_dir == str(git_dir)

    def test_legacy_load_defaults_to_none(self, tmp_path):
        """Legacy dict without the new fields loads fine via RepositoryInfo(**d)."""
        legacy = {
            "repository_id": "abc",
            "name": "legacy",
            "path": str(tmp_path),
            "index_path": str(tmp_path / "idx.db"),
            "language_stats": {},
            "total_files": 0,
            "total_symbols": 0,
            "indexed_at": datetime.now(),
        }
        info = RepositoryInfo(**legacy)
        assert info.tracked_branch is None
        assert info.git_common_dir is None


# ---------------------------------------------------------------------------
# RepositoryRegistry load-time re-keying
# ---------------------------------------------------------------------------


class TestRegistryRekey:
    def _write_legacy_registry(
        self, registry_path: Path, old_id: str, repo_path: Path, index_path: Path
    ) -> None:
        data = {
            old_id: {
                "repository_id": old_id,
                "name": "myrepo",
                "path": str(repo_path),
                "index_path": str(index_path),
                "language_stats": {},
                "total_files": 0,
                "total_symbols": 0,
                "indexed_at": datetime.now().isoformat(),
                "current_commit": None,
                "last_indexed_commit": None,
                "last_indexed_branch": None,
                "last_indexed": None,
                "current_branch": None,
                "url": None,
                "auto_sync": True,
                "artifact_enabled": False,
                "active": True,
                "priority": 0,
                "index_location": None,
                "last_published_commit": None,
                "last_recovered_commit": None,
                "available_semantic_profiles": None,
                "artifact_backend": None,
                "artifact_health": None,
            }
        }
        with open(registry_path, "w") as f:
            json.dump(data, f)

    def test_legacy_json_load_rekeys_entry(self, tmp_path):
        """Loading a registry with a legacy SHA1-prefixed id re-keys to new sha256 id."""
        from mcp_server.storage.repository_registry import RepositoryRegistry

        repo_path = make_git_repo(tmp_path / "repo-a")
        index_path = tmp_path / "idx.db"
        index_path.touch()

        registry_path = tmp_path / "registry.json"
        old_id = "myrepo-abcd1234beef"
        self._write_legacy_registry(registry_path, old_id, repo_path, index_path)

        registry = RepositoryRegistry(registry_path=registry_path)

        expected_id = compute_repo_id(repo_path).repo_id
        assert old_id not in registry._registry, "Old key should be gone after re-key"
        assert expected_id in registry._registry, f"New key {expected_id} should be in registry"

    def test_legacy_json_load_populates_tracked_branch(self, tmp_path):
        """After re-keying, tracked_branch is populated."""
        from mcp_server.storage.repository_registry import RepositoryRegistry

        repo_path = make_git_repo(tmp_path / "repo-b")
        index_path = tmp_path / "idx.db"
        index_path.touch()

        registry_path = tmp_path / "registry.json"
        old_id = "myrepo-abcd1234beef"
        self._write_legacy_registry(registry_path, old_id, repo_path, index_path)

        registry = RepositoryRegistry(registry_path=registry_path)

        expected_id = compute_repo_id(repo_path).repo_id
        entry = registry._registry[expected_id]
        assert entry.get("tracked_branch") is not None
        assert isinstance(entry["tracked_branch"], str)
        assert len(entry["tracked_branch"]) > 0

    def test_second_load_is_no_op(self, tmp_path):
        """Loading a registry twice does not change keys (idempotent)."""
        from mcp_server.storage.repository_registry import RepositoryRegistry

        repo_path = make_git_repo(tmp_path / "repo-c")
        index_path = tmp_path / "idx.db"
        index_path.touch()

        registry_path = tmp_path / "registry.json"
        old_id = "myrepo-abcd1234beef"
        self._write_legacy_registry(registry_path, old_id, repo_path, index_path)

        # First load — triggers rekey
        registry1 = RepositoryRegistry(registry_path=registry_path)
        keys_after_first = set(registry1._registry.keys())

        # Second load — should be no-op
        registry2 = RepositoryRegistry(registry_path=registry_path)
        keys_after_second = set(registry2._registry.keys())

        assert keys_after_first == keys_after_second


# ---------------------------------------------------------------------------
# SQLite FK migration during rekey
# ---------------------------------------------------------------------------


class TestSQLiteMigrationDuringRekey:
    def _build_sqlite_with_text_repo_id(self, db_path: str, old_repo_id: str) -> None:
        """Create a minimal SQLite db with a text repository_id column in files."""
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE files (id INTEGER PRIMARY KEY, repository_id TEXT, path TEXT)")
        conn.execute("CREATE TABLE symbols (id INTEGER PRIMARY KEY, repository_id TEXT, name TEXT)")
        conn.execute("INSERT INTO files (repository_id, path) VALUES (?, ?)", (old_repo_id, "a.py"))
        conn.execute(
            "INSERT INTO symbols (repository_id, name) VALUES (?, ?)", (old_repo_id, "func_a")
        )
        conn.commit()
        conn.close()

    def test_sqlite_files_updated_on_rekey(self, tmp_path):
        """After re-keying, files rows carry the new repository_id."""
        from mcp_server.storage.repository_registry import RepositoryRegistry

        repo_path = make_git_repo(tmp_path / "repo-sqlite")
        index_path = tmp_path / "index.db"
        old_id = "myrepo-deadbeef1234"
        self._build_sqlite_with_text_repo_id(str(index_path), old_id)

        registry_path = tmp_path / "registry.json"
        data = {
            old_id: {
                "repository_id": old_id,
                "name": "myrepo",
                "path": str(repo_path),
                "index_path": str(index_path),
                "language_stats": {},
                "total_files": 0,
                "total_symbols": 0,
                "indexed_at": datetime.now().isoformat(),
                "current_commit": None,
                "last_indexed_commit": None,
                "last_indexed_branch": None,
                "last_indexed": None,
                "current_branch": None,
                "url": None,
                "auto_sync": True,
                "artifact_enabled": False,
                "active": True,
                "priority": 0,
                "index_location": None,
                "last_published_commit": None,
                "last_recovered_commit": None,
                "available_semantic_profiles": None,
                "artifact_backend": None,
                "artifact_health": None,
            }
        }
        with open(registry_path, "w") as f:
            json.dump(data, f)

        RepositoryRegistry(registry_path=registry_path)

        expected_id = compute_repo_id(repo_path).repo_id

        conn = sqlite3.connect(str(index_path))
        rows = conn.execute("SELECT repository_id FROM files").fetchall()
        symbol_rows = conn.execute("SELECT repository_id FROM symbols").fetchall()
        conn.close()

        assert all(
            r[0] == expected_id for r in rows
        ), f"Expected all files.repository_id={expected_id}, got {rows}"
        assert all(
            r[0] == expected_id for r in symbol_rows
        ), f"Expected all symbols.repository_id={expected_id}, got {symbol_rows}"


# ---------------------------------------------------------------------------
# register_repository uses compute_repo_id
# ---------------------------------------------------------------------------


class TestRegisterRepositoryUsesComputeRepoId:
    def test_register_populates_new_fields(self, tmp_path):
        """register_repository returns id matching compute_repo_id and fills new fields."""
        from mcp_server.storage.repository_registry import RepositoryRegistry

        repo_path = make_git_repo(tmp_path / "repo-reg")
        registry_path = tmp_path / "registry.json"

        registry = RepositoryRegistry(registry_path=registry_path)
        returned_id = registry.register_repository(str(repo_path))

        expected_id = compute_repo_id(repo_path).repo_id
        assert returned_id == expected_id, f"Expected {expected_id}, got {returned_id}"

        entry = registry._registry[returned_id]
        assert entry.get("tracked_branch") is not None
        assert isinstance(entry["tracked_branch"], str)
        assert len(entry["tracked_branch"]) > 0
        assert entry.get("git_common_dir") is not None
        assert isinstance(entry["git_common_dir"], str)

    def test_register_twice_returns_same_id(self, tmp_path):
        """Registering the same repo twice returns the same id (idempotent)."""
        from mcp_server.storage.repository_registry import RepositoryRegistry

        repo_path = make_git_repo(tmp_path / "repo-reg2")
        registry_path = tmp_path / "registry.json"

        registry = RepositoryRegistry(registry_path=registry_path)
        id1 = registry.register_repository(str(repo_path))
        id2 = registry.register_repository(str(repo_path))
        assert id1 == id2
