"""CHUNKERSAFE Lane A - chunker identity-scheme guard + atomic rebuild.

These tests pin the version-agnostic data-integrity contract: a single central
choke point refuses every ``code_chunks`` write/delete and every
scheme-dependent read across an id-scheme boundary, a missing marker over a
non-empty index fails closed, and an atomic rebuild coherently invalidates the
dependent stores (summaries, semantic point mappings, remote vector ids) while
preserving synthetic history/document rows and flipping the marker only after
repopulation.

They fail at base because the guard, marker, typed error, and rebuild entry
points do not exist there (ImportError on the symbols below).
"""

from __future__ import annotations

import sqlite3

import pytest

from mcp_server.health import repository_readiness
from mcp_server.health.repository_readiness import RepositoryReadinessState
from mcp_server.storage import sqlite_store as sqlite_store_module
from mcp_server.storage.sqlite_store import (
    CHUNK_SCHEME_MARKER_KEY,
    ChunkSchemeMismatchError,
    SQLiteStore,
    assert_chunk_scheme_readable,
    current_chunk_id_scheme,
    evaluate_chunk_scheme,
)

FOREIGN_SCHEME = "treesitter_chunk_id_v4_foreign"


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _make_store(tmp_path) -> SQLiteStore:
    return SQLiteStore(str(tmp_path / "code_index.db"))


def _make_file(store: SQLiteStore, name: str = "a.py") -> int:
    repo_id = store.create_repository(str(name) + "-repo-root", f"repo-{name}")
    return store.store_file(
        repository_id=repo_id,
        path=f"/repo/{name}",
        relative_path=name,
        language="python",
    )


def _store_code_chunk(store: SQLiteStore, file_id: int, chunk_id: str, index: int = 0) -> int:
    return store.store_chunk(
        file_id=file_id,
        content=f"def f_{chunk_id}():\n    return 1\n",
        content_start=0,
        content_end=20,
        line_start=1,
        line_end=2,
        chunk_id=chunk_id,
        node_id=f"node-{chunk_id}",
        treesitter_file_id="tsfile",
        language="python",
        chunk_index=index,
    )


def _store_document_chunk(store: SQLiteStore, file_id: int, chunk_id: str) -> int:
    """Synthetic non-chunker row (history/document), must survive a rebuild."""
    return store.store_chunk(
        file_id=file_id,
        content="# history document\n",
        content_start=0,
        content_end=18,
        line_start=1,
        line_end=1,
        chunk_id=chunk_id,
        node_id=chunk_id,
        treesitter_file_id="history",
        chunk_type="document",
        language="history",
    )


def _insert_summary(store: SQLiteStore, chunk_hash: str, file_id: int) -> None:
    with store._get_connection() as conn:
        conn.execute(
            "INSERT INTO chunk_summaries (chunk_hash, file_id, chunk_start, chunk_end, "
            "summary_text) VALUES (?, ?, 0, 1, ?)",
            (chunk_hash, file_id, f"summary of {chunk_hash}"),
        )


def _clear_marker(store: SQLiteStore) -> None:
    """Simulate a legacy / v3-unmarked index: chunker rows present, no marker."""
    with store._get_connection() as conn:
        conn.execute(
            "DELETE FROM index_config WHERE config_key = ?", (CHUNK_SCHEME_MARKER_KEY,)
        )


def _force_scheme(monkeypatch, value: str) -> None:
    monkeypatch.setattr(sqlite_store_module, "current_chunk_id_scheme", lambda: value)


def _count_chunks(store: SQLiteStore) -> int:
    with store._get_connection() as conn:
        return int(conn.execute("SELECT COUNT(*) FROM code_chunks").fetchone()[0])


# --------------------------------------------------------------------------- #
# 1. Empty index stamps the scheme on first build
# --------------------------------------------------------------------------- #
def test_empty_index_stamps_scheme_on_first_build(tmp_path):
    store = _make_store(tmp_path)
    assert store.get_chunk_scheme_marker() is None

    file_id = _make_file(store)
    _store_code_chunk(store, file_id, "c1")

    assert store.get_chunk_scheme_marker() == current_chunk_id_scheme()
    status, marker, target = store.get_chunk_scheme_status()
    assert status == "compatible"
    assert marker == target == current_chunk_id_scheme()


def test_document_rows_do_not_stamp_or_trip_the_guard(tmp_path, monkeypatch):
    """Synthetic document rows bypass the chunker guard entirely."""
    store = _make_store(tmp_path)
    file_id = _make_file(store, "hist.md")
    _store_document_chunk(store, file_id, "history:issue")
    # No chunker rows -> still unmarked (document writes never stamp).
    assert store.get_chunk_scheme_marker() is None
    # Even under a foreign scheme, a document write is allowed.
    _force_scheme(monkeypatch, FOREIGN_SCHEME)
    _store_document_chunk(store, file_id, "history:comment")
    assert store.get_chunk_scheme_marker() is None


# --------------------------------------------------------------------------- #
# 2. Scheme mismatch refuses store_chunk AND dispatcher path AND plugin path
# --------------------------------------------------------------------------- #
def test_mismatch_refuses_store_chunk(tmp_path, monkeypatch):
    store = _make_store(tmp_path)
    file_id = _make_file(store)
    _store_code_chunk(store, file_id, "c1")  # stamps current scheme
    before = _count_chunks(store)

    _force_scheme(monkeypatch, FOREIGN_SCHEME)
    with pytest.raises(ChunkSchemeMismatchError) as excinfo:
        _store_code_chunk(store, file_id, "c2")
    assert excinfo.value.state == "mismatch"
    assert excinfo.value.expected == FOREIGN_SCHEME
    assert _count_chunks(store) == before  # no upsert occurred


def test_mismatch_refuses_dispatcher_raw_path(tmp_path, monkeypatch):
    """The dispatcher raw upsert routes through store._assert_chunk_scheme_writable
    before any delete/insert (dispatcher_enhanced.py _persist_index_shard)."""
    store = _make_store(tmp_path)
    file_id = _make_file(store)
    _store_code_chunk(store, file_id, "c1")

    _force_scheme(monkeypatch, FOREIGN_SCHEME)
    with store._get_connection() as conn:
        with pytest.raises(ChunkSchemeMismatchError):
            # Exact call the dispatcher makes before _clear_file_index_rows.
            store._assert_chunk_scheme_writable(conn, chunk_type="code")


def test_mismatch_refuses_plugin_path(tmp_path, monkeypatch):
    """Plugins call delete_chunks_for_file + store_chunk directly; both are
    guarded, so no delete or upsert happens under a scheme mismatch."""
    store = _make_store(tmp_path)
    file_id = _make_file(store)
    _store_code_chunk(store, file_id, "c1")
    before = _count_chunks(store)

    _force_scheme(monkeypatch, FOREIGN_SCHEME)
    # Plugin step 1: delete old chunks -> must refuse (would destroy coherent rows).
    with pytest.raises(ChunkSchemeMismatchError):
        store.delete_chunks_for_file(file_id)
    # Plugin step 2: store new chunk -> must refuse.
    with pytest.raises(ChunkSchemeMismatchError):
        _store_code_chunk(store, file_id, "c2")
    assert _count_chunks(store) == before  # nothing deleted, nothing written


# --------------------------------------------------------------------------- #
# 3. Missing marker over non-empty index fails closed on read AND write
# --------------------------------------------------------------------------- #
def test_missing_marker_over_nonempty_index_fails_closed(tmp_path):
    store = _make_store(tmp_path)
    file_id = _make_file(store)
    _store_code_chunk(store, file_id, "c1")
    _clear_marker(store)  # v3-unmarked legacy fixture

    with store._get_connection() as conn:
        status, marker, _ = evaluate_chunk_scheme(conn)
    assert status == "missing_marker"
    assert marker is None

    before = _count_chunks(store)

    # Write fails closed.
    with pytest.raises(ChunkSchemeMismatchError):
        _store_code_chunk(store, file_id, "c2")
    # Delete fails closed.
    with pytest.raises(ChunkSchemeMismatchError):
        store.delete_chunks_for_file(file_id)
    # Read fails closed.
    with sqlite3.connect(store.db_path) as raw:
        with pytest.raises(ChunkSchemeMismatchError):
            assert_chunk_scheme_readable(raw)

    assert _count_chunks(store) == before  # no read/delete/upsert mutated the index


def test_readiness_reports_scheme_mismatch_not_ready(tmp_path):
    store = _make_store(tmp_path)
    file_id = _make_file(store)
    _store_code_chunk(store, file_id, "c1")
    _clear_marker(store)

    state = repository_readiness._inspect_index_uncached(
        __import__("pathlib").Path(store.db_path)
    )
    assert state == RepositoryReadinessState.SCHEME_MISMATCH


# --------------------------------------------------------------------------- #
# 4. Atomic rebuild: cross-store cleanup + preserve synthetic rows + returns ids
# --------------------------------------------------------------------------- #
def _seed_for_rebuild(store: SQLiteStore):
    code_file = _make_file(store, "code.py")
    hist_file = _make_file(store, "hist.md")

    _store_code_chunk(store, code_file, "code-chunk-1", index=0)
    _store_code_chunk(store, code_file, "code-chunk-2", index=1)
    _store_document_chunk(store, hist_file, "history:issue")

    # Summaries for both chunker chunks and the preserved document chunk.
    _insert_summary(store, "code-chunk-1", code_file)
    _insert_summary(store, "code-chunk-2", code_file)
    _insert_summary(store, "history:issue", hist_file)

    # Semantic point mappings (chunker + document).
    store.upsert_semantic_point("profile-a", "code-chunk-1", 101, "col-a")
    store.upsert_semantic_point("profile-a", "code-chunk-2", 102, "col-a")
    store.upsert_semantic_point("profile-a", "history:issue", 900, "col-a")
    return code_file, hist_file


def test_rebuild_invalidates_dependent_stores_and_preserves_synthetic(tmp_path):
    store = _make_store(tmp_path)
    code_file, hist_file = _seed_for_rebuild(store)

    def repopulate(conn):
        conn.execute(
            "INSERT INTO code_chunks (file_id, content, content_start, content_end, "
            "line_start, line_end, chunk_id, node_id, treesitter_file_id, chunk_type) "
            "VALUES (?, 'x', 0, 1, 1, 1, 'new-chunk-1', 'n', 't', 'code')",
            (code_file,),
        )

    result = store.rebuild_chunk_scheme(profile_id="profile-a", repopulate=repopulate)

    with store._get_connection() as conn:
        chunk_ids = {r[0] for r in conn.execute("SELECT chunk_id FROM code_chunks")}
        summary_hashes = {r[0] for r in conn.execute("SELECT chunk_hash FROM chunk_summaries")}
        point_ids = {r[0] for r in conn.execute("SELECT point_id FROM semantic_points")}

    # Old chunker rows gone; repopulated row present; synthetic document preserved.
    assert "code-chunk-1" not in chunk_ids
    assert "code-chunk-2" not in chunk_ids
    assert "new-chunk-1" in chunk_ids
    assert "history:issue" in chunk_ids

    # Chunker summaries removed, document summary preserved (no dangling rows).
    assert summary_hashes == {"history:issue"}

    # Chunker point mappings removed, document mapping preserved.
    assert point_ids == {900}

    # Stale remote-vector ids returned for Qdrant cleanup (chunker only).
    returned_points = {p["point_id"] for p in result["points"]}
    assert returned_points == {101, 102}
    assert set(result["chunk_ids"]) == {"code-chunk-1", "code-chunk-2"}

    # Marker flipped to current scheme after repopulation.
    assert store.get_chunk_scheme_marker() == current_chunk_id_scheme()


def test_rebuild_flips_marker_only_after_repopulation(tmp_path):
    store = _make_store(tmp_path)
    _seed_for_rebuild(store)
    marker_before = store.get_chunk_scheme_marker()

    # Phase 1 only: invalidate + enter rebuilding, marker NOT yet flipped.
    store.begin_chunk_scheme_rebuild(FOREIGN_SCHEME, profile_id="profile-a")
    with store._get_connection() as conn:
        status, _marker, _target = evaluate_chunk_scheme(conn, FOREIGN_SCHEME)
    assert status == "rebuilding"
    assert store.get_chunk_scheme_marker() == marker_before  # unchanged

    # Phase 2: finalize flips the marker and clears the rebuilding flag.
    store.finalize_chunk_scheme_rebuild(FOREIGN_SCHEME)
    assert store.get_chunk_scheme_marker() == FOREIGN_SCHEME
    with store._get_connection() as conn:
        status, marker, _ = evaluate_chunk_scheme(conn, FOREIGN_SCHEME)
    assert status == "compatible"


# --------------------------------------------------------------------------- #
# 5. Interrupted rebuild: old-coherent OR blocked/resumable, never ready
# --------------------------------------------------------------------------- #
def test_interrupted_rebuild_rolls_back_to_old_coherent_index(tmp_path):
    store = _make_store(tmp_path)
    _seed_for_rebuild(store)

    class Boom(RuntimeError):
        pass

    def repopulate(conn):
        raise Boom("crash mid-rebuild")

    with pytest.raises(Boom):
        store.rebuild_chunk_scheme(profile_id="profile-a", repopulate=repopulate)

    # Old, coherent index survives untouched (rows + marker), no rebuild flag.
    with store._get_connection() as conn:
        chunk_ids = {r[0] for r in conn.execute("SELECT chunk_id FROM code_chunks")}
        status, _marker, _ = evaluate_chunk_scheme(conn)
    assert {"code-chunk-1", "code-chunk-2", "history:issue"}.issubset(chunk_ids)
    assert status == "compatible"


def test_interrupted_rebuild_leaves_blocked_resumable_non_ready(tmp_path):
    from pathlib import Path

    store = _make_store(tmp_path)
    _seed_for_rebuild(store)

    # Phase 1 commits, then the process "crashes" before finalize.
    store.begin_chunk_scheme_rebuild(profile_id="profile-a")

    # Readiness is non-ready (rebuilding), not table-presence 'ready'.
    state = repository_readiness._inspect_index_uncached(Path(store.db_path))
    assert state == RepositoryReadinessState.INDEX_REBUILDING

    # Reads fail closed while rebuilding.
    with sqlite3.connect(store.db_path) as raw:
        with pytest.raises(ChunkSchemeMismatchError):
            assert_chunk_scheme_readable(raw)

    # Resumable: repopulate then finalize -> ready/compatible.
    file_id = _make_file(store, "resumed.py")
    _store_code_chunk(store, file_id, "resumed-1")  # allowed during rebuilding
    store.finalize_chunk_scheme_rebuild()
    state = repository_readiness._inspect_index_uncached(Path(store.db_path))
    assert state is None  # healthy


# --------------------------------------------------------------------------- #
# 6. update_chunk_token_count is scoped by file_id (no cross-file collision)
# --------------------------------------------------------------------------- #
def test_update_chunk_token_count_scoped_by_file_id(tmp_path):
    store = _make_store(tmp_path)
    file_a = _make_file(store, "a.py")
    file_b = _make_file(store, "b.py")

    shared_chunk_id = "dup-chunk"
    _store_code_chunk(store, file_a, shared_chunk_id)
    _store_code_chunk(store, file_b, shared_chunk_id)

    updated = store.update_chunk_token_count(shared_chunk_id, 42, file_id=file_a)
    assert updated is True

    chunk_a = store.get_chunk_by_chunk_id(shared_chunk_id, file_id=file_a)
    chunk_b = store.get_chunk_by_chunk_id(shared_chunk_id, file_id=file_b)
    assert chunk_a["token_count"] == 42
    assert chunk_b["token_count"] is None  # sibling file untouched
