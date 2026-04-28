"""P27 repository readiness contract tests."""

from __future__ import annotations

import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from mcp_server.health.repository_readiness import (
    ReadinessClassifier,
    RepositoryReadinessState,
    SemanticReadinessState,
)
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.storage.multi_repo_manager import RepositoryInfo
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


def test_semantic_readiness_state_values_are_exact():
    assert {state.value for state in SemanticReadinessState} == {
        "ready",
        "enrichment_unavailable",
        "summaries_missing",
        "vectors_missing",
        "vector_dimension_mismatch",
        "profile_mismatch",
        "semantic_stale",
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


def _seed_semantic_rows(
    index_path: Path,
    *,
    with_summary: bool = False,
    with_vector: bool = False,
    collection: str = "code_index__oss_high__v1",
) -> None:
    SQLiteStore(str(index_path))
    conn = sqlite3.connect(index_path)
    file_id = int(conn.execute("SELECT id FROM files LIMIT 1").fetchone()[0])
    conn.execute(
        """INSERT INTO code_chunks
           (file_id, content, content_start, content_end, line_start, line_end,
            chunk_id, node_id, treesitter_file_id, chunk_type, chunk_index)
           VALUES (?, ?, 0, 10, 1, 1, 'chunk-1', 'node-1', 'ts-file-1', 'code', 0)""",
        (file_id, "def demo():\n    return 1\n"),
    )
    if with_summary:
        conn.execute(
            """INSERT INTO chunk_summaries
               (chunk_hash, file_id, chunk_start, chunk_end, summary_text, is_authoritative, llm_model)
               VALUES ('chunk-1', ?, 0, 10, 'demo summary', 1, 'chat')""",
            (file_id,),
        )
    if with_vector:
        conn.execute(
            """INSERT INTO semantic_points (profile_id, chunk_id, point_id, collection)
               VALUES ('oss_high', 'chunk-1', 1, ?)""",
            (collection,),
        )
    conn.commit()
    conn.close()


def _make_semantic_repo_info(tmp_path: Path) -> tuple[RepositoryInfo, SQLiteStore]:
    repo_root = tmp_path / "semantic-repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    readme = repo_root / "README.md"
    readme.write_text("hello\n", encoding="utf-8")
    index_path = repo_root / ".mcp-index" / "current.db"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    store = SQLiteStore(str(index_path))
    repository_row = store.ensure_repository_row(repo_root, name="semantic-repo")
    store.store_file(
        repository_row,
        path=readme,
        relative_path="README.md",
        language="python",
        size=readme.stat().st_size,
    )
    info = RepositoryInfo(
        repository_id="semantic-repo",
        name="semantic-repo",
        path=repo_root,
        index_path=index_path,
        language_stats={},
        total_files=1,
        total_symbols=0,
        indexed_at=datetime.now(),
        tracked_branch="main",
        current_branch="main",
        git_common_dir=str(repo_root / ".git"),
    )
    return info, store


def _profile() -> SimpleNamespace:
    return SimpleNamespace(
        profile_id="oss_high",
        compatibility_fingerprint="fingerprint-1",
        vector_dimension=4096,
        build_metadata={"collection_name": "code_index__oss_high__v1"},
    )


def test_sqlite_semantic_evidence_counts_chunks_summaries_and_vectors(tmp_path):
    info, store = _make_semantic_repo_info(tmp_path)
    _seed_semantic_rows(info.index_path, with_summary=True, with_vector=False)

    evidence = store.get_semantic_readiness_evidence(
        "oss_high",
        collection="code_index__oss_high__v1",
    )

    assert evidence["total_chunks"] == 1
    assert evidence["summary_count"] == 1
    assert evidence["missing_summaries"] == 0
    assert evidence["vector_link_count"] == 0
    assert evidence["missing_vectors"] == 1


def test_semantic_readiness_reports_summaries_missing_for_lexically_ready_repo(
    tmp_path, monkeypatch
):
    import mcp_server.health.repository_readiness as readiness_module

    info, store = _make_semantic_repo_info(tmp_path)
    _seed_semantic_rows(info.index_path, with_summary=False, with_vector=False)
    monkeypatch.setattr(readiness_module, "_current_semantic_profile", lambda: _profile())
    (Path(info.path) / ".index_metadata.json").write_text(
        '{"semantic_profile":"oss_high","semantic_profiles":{"oss_high":{"compatibility_fingerprint":"fingerprint-1","model_dimension":4096,"collection_name":"code_index__oss_high__v1"}}}',
        encoding="utf-8",
    )

    semantic = ReadinessClassifier.classify_semantic_registered(info, store)

    assert semantic.state == SemanticReadinessState.SUMMARIES_MISSING
    assert semantic.ready is False


def test_semantic_readiness_reports_vectors_missing_when_summaries_exist(tmp_path, monkeypatch):
    import mcp_server.health.repository_readiness as readiness_module

    info, store = _make_semantic_repo_info(tmp_path)
    _seed_semantic_rows(info.index_path, with_summary=True, with_vector=False)
    monkeypatch.setattr(readiness_module, "_current_semantic_profile", lambda: _profile())
    (Path(info.path) / ".index_metadata.json").write_text(
        '{"semantic_profile":"oss_high","semantic_profiles":{"oss_high":{"compatibility_fingerprint":"fingerprint-1","model_dimension":4096,"collection_name":"code_index__oss_high__v1"}}}',
        encoding="utf-8",
    )

    semantic = ReadinessClassifier.classify_semantic_registered(info, store)

    assert semantic.state == SemanticReadinessState.VECTORS_MISSING


def test_semantic_readiness_reports_stale_when_fingerprint_mismatches(tmp_path, monkeypatch):
    import mcp_server.health.repository_readiness as readiness_module

    info, store = _make_semantic_repo_info(tmp_path)
    _seed_semantic_rows(info.index_path, with_summary=True, with_vector=True)
    monkeypatch.setattr(readiness_module, "_current_semantic_profile", lambda: _profile())
    (Path(info.path) / ".index_metadata.json").write_text(
        '{"semantic_profile":"oss_high","semantic_profiles":{"oss_high":{"compatibility_fingerprint":"fingerprint-old","model_dimension":4096,"collection_name":"code_index__oss_high__v1"}}}',
        encoding="utf-8",
    )

    semantic = ReadinessClassifier.classify_semantic_registered(info, store)

    assert semantic.state == SemanticReadinessState.SEMANTIC_STALE


def test_semantic_readiness_reports_dimension_mismatch(tmp_path, monkeypatch):
    import mcp_server.health.repository_readiness as readiness_module

    info, store = _make_semantic_repo_info(tmp_path)
    _seed_semantic_rows(info.index_path, with_summary=True, with_vector=True)
    monkeypatch.setattr(readiness_module, "_current_semantic_profile", lambda: _profile())
    (Path(info.path) / ".index_metadata.json").write_text(
        '{"semantic_profile":"oss_high","semantic_profiles":{"oss_high":{"compatibility_fingerprint":"fingerprint-1","model_dimension":1024,"collection_name":"code_index__oss_high__v1"}}}',
        encoding="utf-8",
    )

    semantic = ReadinessClassifier.classify_semantic_registered(info, store)

    assert semantic.state == SemanticReadinessState.VECTOR_DIMENSION_MISMATCH


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
