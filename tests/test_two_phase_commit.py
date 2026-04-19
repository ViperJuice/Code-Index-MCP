"""Tests for the two_phase_commit primitive and atomic rename/remove operations.

Primary/shadow design rationale:
- For _move_file: primary = SQLite move_file (durable, WAL-backed, rollback via reverse move),
  shadow = Qdrant delete_stale_vectors. SQLite is the preferred primary because it supports
  true rollback (move_file(new, old, ...)); Qdrant has no reliable un-delete primitive.
- For _remove_file: primary = SQLite remove_file, shadow = Qdrant delete_stale_vectors.
  SQLite removal is irreversible (cascades across many tables), so rollback logs a warning
  and re-raises — the invariant is weakened but the failure is surfaced rather than silently
  leaving orphan vectors.  Both operations are irreversible; SQLite is chosen as primary
  because it is the authoritative record of file existence.
"""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, call

import pytest

from mcp_server.core.errors import MCPError
from mcp_server.storage.two_phase import TwoPhaseCommitError, two_phase_commit
from mcp_server.indexing.incremental_indexer import IncrementalIndexer
from mcp_server.core.path_resolver import PathResolver
from mcp_server.storage.sqlite_store import SQLiteStore


# ---------------------------------------------------------------------------
# Primitive tests
# ---------------------------------------------------------------------------


def test_both_ops_succeed_returns_primary_value():
    primary = MagicMock(return_value=42)
    shadow = MagicMock()
    rollback = MagicMock()

    result = two_phase_commit(primary, shadow, rollback)

    assert result == 42
    primary.assert_called_once()
    shadow.assert_called_once_with(42)
    rollback.assert_not_called()


def test_shadow_raises_triggers_rollback_and_wraps_exception():
    primary = MagicMock(return_value="primary-result")
    shadow = MagicMock(side_effect=RuntimeError("qdrant down"))
    rollback = MagicMock()

    with pytest.raises(TwoPhaseCommitError) as exc_info:
        two_phase_commit(primary, shadow, rollback)

    rollback.assert_called_once_with("primary-result")
    assert isinstance(exc_info.value, MCPError)
    assert exc_info.value.__cause__ is not None
    assert isinstance(exc_info.value.__cause__, RuntimeError)


def test_primary_raises_shadow_and_rollback_never_called():
    primary = MagicMock(side_effect=ValueError("disk full"))
    shadow = MagicMock()
    rollback = MagicMock()

    with pytest.raises(ValueError, match="disk full"):
        two_phase_commit(primary, shadow, rollback)

    shadow.assert_not_called()
    rollback.assert_not_called()


def test_shadow_raises_rollback_called_exactly_once():
    primary = MagicMock(return_value="res")
    shadow = MagicMock(side_effect=RuntimeError("fail"))
    rollback = MagicMock()

    with pytest.raises(TwoPhaseCommitError):
        two_phase_commit(primary, shadow, rollback)

    assert rollback.call_count == 1
    rollback.assert_called_once_with("res")


def test_rollback_raises_is_attached_to_two_phase_commit_error():
    """If rollback itself raises, error is attached to TwoPhaseCommitError.details."""
    primary = MagicMock(return_value="res")
    shadow = MagicMock(side_effect=RuntimeError("shadow-fail"))
    rollback = MagicMock(side_effect=Exception("rollback-fail"))

    with pytest.raises(TwoPhaseCommitError) as exc_info:
        two_phase_commit(primary, shadow, rollback)

    err = exc_info.value
    assert err.details is not None
    assert "rollback-fail" in str(err.details)


def test_two_phase_commit_error_is_mcp_error():
    err = TwoPhaseCommitError("test", details={"key": "val"})
    assert isinstance(err, MCPError)


# ---------------------------------------------------------------------------
# Rename fault-injection tests (real SQLiteStore, mocked Qdrant)
# ---------------------------------------------------------------------------


class FailingSemanticIndexer:
    """Semantic indexer whose delete_stale_vectors can be made to raise."""

    def __init__(self, fail=False):
        self.semantic_profile = SimpleNamespace(profile_id="test-profile")
        self.fail = fail
        self.delete_calls = []

    def delete_stale_vectors(self, profile_id, chunk_ids, sqlite_store=None):
        self.delete_calls.append(list(chunk_ids))
        if self.fail:
            raise RuntimeError("Qdrant unavailable")
        return len(list(chunk_ids))


@pytest.fixture
def rename_setup(tmp_path: Path):
    """Real SQLiteStore + real file system, mocked Qdrant via FailingSemanticIndexer."""
    repo_path = tmp_path / "repo"
    repo_path.mkdir()

    store = SQLiteStore(str(tmp_path / "code_index.db"), path_resolver=PathResolver(repo_path))
    repo_id = store.create_repository(str(repo_path), "test-repo")

    def make_indexer(fail_qdrant=False):
        semantic = FailingSemanticIndexer(fail=fail_qdrant)
        indexer = IncrementalIndexer(
            store=store,
            dispatcher=None,
            repo_path=repo_path,
            semantic_indexer=semantic,
        )
        indexer._get_repository_id = lambda: repo_id  # type: ignore[method-assign]
        return indexer, semantic

    return repo_path, store, repo_id, make_indexer


def _seed_file(store, repo_id, repo_path, rel_path, content="x = 1\n"):
    """Store a file row + chunk + semantic point. Returns file_id."""
    full_path = repo_path / rel_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content)
    file_id = store.store_file(repo_id, full_path, language="python")
    store.store_chunk(
        file_id=file_id,
        content=content,
        content_start=0,
        content_end=len(content),
        line_start=1,
        line_end=1,
        chunk_id=f"chunk-{rel_path}",
        node_id=f"node-{rel_path}",
        treesitter_file_id=f"ts-{rel_path}",
    )
    store.upsert_semantic_point(
        profile_id="test-profile",
        chunk_id=f"chunk-{rel_path}",
        point_id=abs(hash(rel_path)) % (2**31),
        collection="code-index",
    )
    return file_id


def _get_relative_path(store, repo_id, file_id):
    with store._get_connection() as conn:
        row = conn.execute(
            "SELECT relative_path FROM files WHERE id = ? AND repository_id = ?",
            (file_id, repo_id),
        ).fetchone()
        return row[0] if row else None


def test_rename_qdrant_fail_sqlite_not_updated(rename_setup):
    """If Qdrant delete fails, SQLite relative_path must NOT be updated."""
    repo_path, store, repo_id, make_indexer = rename_setup
    file_id = _seed_file(store, repo_id, repo_path, "old_name.py")

    # Also create the new file on disk
    new_file = repo_path / "new_name.py"
    new_file.write_text("x = 1\n")

    indexer, _ = make_indexer(fail_qdrant=True)
    result = indexer._move_file("old_name.py", "new_name.py")

    assert result is False, "Should report failure when Qdrant fails"
    path_in_db = _get_relative_path(store, repo_id, file_id)
    # SQLite path must be unchanged (still old_name)
    assert path_in_db is not None
    assert "old_name" in path_in_db, (
        f"SQLite path was updated despite Qdrant failure: {path_in_db}"
    )


def test_rename_sqlite_fail_qdrant_not_called(rename_setup):
    """If SQLite move_file fails, Qdrant delete must NOT be called."""
    repo_path, store, repo_id, make_indexer = rename_setup
    _seed_file(store, repo_id, repo_path, "src.py")

    new_file = repo_path / "dst.py"
    new_file.write_text("x = 1\n")

    indexer, semantic = make_indexer(fail_qdrant=False)

    # Patch store.move_file to raise
    original_move = store.move_file
    store.move_file = MagicMock(side_effect=RuntimeError("SQLite move failed"))  # type: ignore[method-assign]

    result = indexer._move_file("src.py", "dst.py")

    store.move_file = original_move  # restore

    assert result is False
    assert semantic.delete_calls == [], (
        f"Qdrant delete was called despite SQLite failure: {semantic.delete_calls}"
    )
