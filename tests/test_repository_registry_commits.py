"""Tests for commit metadata persistence in the repository registry."""

import subprocess
from datetime import datetime
from pathlib import Path

import pytest

from mcp_server.storage.multi_repo_manager import RepositoryInfo
from mcp_server.storage.repository_registry import RepositoryRegistry


def _init_git_repository(repo_path: Path) -> str:
    """Initialize a git repository and return the initial commit SHA."""
    repo_path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )
    (repo_path / "README.md").write_text("# Test Repo\n")
    subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"], cwd=repo_path, check=True, capture_output=True
    )

    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo_path, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def _create_registry_with_repo(tmp_path: Path, repo_name: str = "repo") -> tuple[RepositoryRegistry, str]:
    """Create a registry and register a single repository for testing."""
    repo_path = tmp_path / repo_name
    initial_commit = _init_git_repository(repo_path)
    registry_path = tmp_path / "registry.json"
    registry = RepositoryRegistry(registry_path)

    repo_info = RepositoryInfo(
        repository_id=f"{repo_name}_id",
        name=repo_name,
        path=repo_path,
        index_path=repo_path / ".mcp-index" / "index.db",
        language_stats={},
        total_files=0,
        total_symbols=0,
        indexed_at=datetime.now(),
    )
    repo_info.index_path.parent.mkdir(parents=True, exist_ok=True)
    registry.register(repo_info)

    # Seed current commit metadata
    registry.update_indexed_commit(repo_info.repository_id, initial_commit)
    registry.update_current_commit(repo_info.repository_id)

    return registry, repo_info.repository_id


def test_indexed_commit_persisted_across_sessions(tmp_path: Path):
    """Ensure last indexed commit is saved and restored when reloading the registry."""
    registry, repo_id = _create_registry_with_repo(tmp_path)

    # Reload registry from disk
    reloaded = RepositoryRegistry(registry.registry_path)
    loaded_info = reloaded.get_repository(repo_id)

    assert loaded_info is not None
    assert loaded_info.last_indexed_commit == loaded_info.current_commit
    assert loaded_info.last_indexed is not None


def test_update_indexed_commit_records_latest(tmp_path: Path):
    """Updating the indexed commit should persist the newest commit SHA."""
    registry, repo_id = _create_registry_with_repo(tmp_path, repo_name="commit_update_repo")
    repo_info = registry.get_repository(repo_id)
    assert repo_info is not None

    # Make a new commit
    repo_path = Path(repo_info.path)
    new_file = repo_path / "feature.py"
    new_file.write_text("def feature():\n    return True\n")
    subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Add feature"], cwd=repo_path, check=True, capture_output=True
    )

    updated_commit = registry.update_current_commit(repo_id)
    assert updated_commit is not None
    registry.update_indexed_commit(repo_id, updated_commit)

    # Reload and verify persistence
    reloaded = RepositoryRegistry(registry.registry_path)
    loaded_info = reloaded.get_repository(repo_id)

    assert loaded_info is not None
    assert loaded_info.last_indexed_commit == updated_commit
    assert loaded_info.current_commit == updated_commit
