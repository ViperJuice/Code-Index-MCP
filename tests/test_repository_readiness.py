"""P27 repository readiness contract tests."""

from __future__ import annotations

import sqlite3
import subprocess
from pathlib import Path

from mcp_server.health.repository_readiness import (
    ReadinessClassifier,
    RepositoryReadinessState,
)
from mcp_server.storage.repository_registry import RepositoryRegistry
from tests.fixtures.health_repo import make_repo_info


def git(*args, cwd=None):
    subprocess.run(["git"] + list(args), cwd=cwd, check=True, capture_output=True)


def make_git_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    git("init", "-b", "main", str(path))
    git("config", "user.email", "test@test.com", cwd=path)
    git("config", "user.name", "Test", cwd=path)
    (path / "README.md").write_text("hello")
    git("add", "README.md", cwd=path)
    git("commit", "-m", "init", cwd=path)
    return path


def test_readiness_state_values_are_exact():
    assert {state.value for state in RepositoryReadinessState} == {
        "ready",
        "unregistered_repository",
        "missing_index",
        "index_empty",
        "stale_commit",
        "wrong_branch",
        "index_building",
        "unsupported_worktree",
    }


def test_serialized_response_keys(tmp_path):
    readiness = ReadinessClassifier.classify_registered(make_repo_info(tmp_path))

    assert set(readiness.to_dict()) == {
        "state",
        "ready",
        "code",
        "repository_id",
        "repository_name",
        "registered_path",
        "requested_path",
        "tracked_branch",
        "current_branch",
        "current_commit",
        "last_indexed_commit",
        "index_path",
        "remediation",
    }
    assert readiness.to_dict()["state"] == "ready"
    assert readiness.to_dict()["code"] is None


def test_classifies_missing_index(tmp_path):
    readiness = ReadinessClassifier.classify_registered(
        make_repo_info(tmp_path, missing_index=True)
    )
    assert readiness.state == RepositoryReadinessState.MISSING_INDEX
    assert readiness.ready is False
    assert readiness.code == "missing_index"


def test_classifies_empty_sqlite_index(tmp_path):
    readiness = ReadinessClassifier.classify_registered(make_repo_info(tmp_path, empty_index=True))
    assert readiness.state == RepositoryReadinessState.INDEX_EMPTY


def test_classifies_stale_commit(tmp_path):
    readiness = ReadinessClassifier.classify_registered(
        make_repo_info(
            tmp_path,
            current_commit="bbbb",
            last_indexed_commit="aaaa",
        )
    )
    assert readiness.state == RepositoryReadinessState.STALE_COMMIT


def test_classifies_wrong_branch(tmp_path):
    readiness = ReadinessClassifier.classify_registered(
        make_repo_info(tmp_path, tracked_branch="main", current_branch="feature")
    )
    assert readiness.state == RepositoryReadinessState.WRONG_BRANCH


def test_classifies_index_building(tmp_path):
    readiness = ReadinessClassifier.classify_registered(
        make_repo_info(tmp_path),
        indexing_active=True,
    )
    assert readiness.state == RepositoryReadinessState.INDEX_BUILDING


def test_classifies_unregistered_path(tmp_path):
    registry = RepositoryRegistry(tmp_path / "registry.json")
    unregistered = make_git_repo(tmp_path / "unregistered")

    readiness = ReadinessClassifier.classify_path(registry, unregistered)

    assert readiness.state == RepositoryReadinessState.UNREGISTERED_REPOSITORY
    assert readiness.requested_path == str(unregistered.resolve())


def test_classifies_unsupported_worktree(tmp_path):
    source = make_git_repo(tmp_path / "source")
    worktree = tmp_path / "wt"
    git("worktree", "add", str(worktree), "-b", "feature", cwd=source)

    registry = RepositoryRegistry(tmp_path / "registry.json")
    repo_id = registry.register_repository(str(source))
    info = registry.get(repo_id)
    info.index_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(info.index_path)
    conn.execute(
        "CREATE TABLE files (id INTEGER PRIMARY KEY, path TEXT, is_deleted BOOLEAN DEFAULT 0)"
    )
    conn.execute("INSERT INTO files (path, is_deleted) VALUES ('README.md', 0)")
    conn.commit()
    conn.close()

    readiness = ReadinessClassifier.classify_path(registry, worktree)

    assert readiness.state == RepositoryReadinessState.UNSUPPORTED_WORKTREE
    assert readiness.registered_path == str(source.resolve())
    assert readiness.requested_path == str(worktree.resolve())
