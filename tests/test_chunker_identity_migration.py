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
# 3. Unmarked non-empty index: legacy-compatible (B1) vs new-scheme fail-closed
# --------------------------------------------------------------------------- #
def test_unmarked_v1_index_is_compatible_and_autostamps(tmp_path, monkeypatch):
    """B1: an existing (v3-built) index has no marker, but the chunk-id algorithm
    was stable across chunker majors 1-3, so under a v1 runtime it genuinely IS
    v1.  Treat it as compatible, allow read+write, and auto-stamp the marker -
    never brick every legacy index by refusing it as a scheme mismatch.

    Forces the v1 runtime scheme so the behavior is asserted regardless of the
    installed chunker major (under a real v4 runtime this path correctly does not
    fire - see test_unmarked_index_under_new_scheme_fails_closed)."""
    _force_scheme(monkeypatch, "treesitter_chunk_id_v1")  # legacy v1 runtime
    store = _make_store(tmp_path)
    file_id = _make_file(store)
    _store_code_chunk(store, file_id, "c1")
    _clear_marker(store)  # legacy/unmarked fixture

    with store._get_connection() as conn:
        status, marker, target = evaluate_chunk_scheme(conn)
    assert status == "compatible_legacy"
    assert marker is None
    # target reflects the forced v1 runtime (the directly-imported
    # current_chunk_id_scheme() bypasses the module-attr patch under a real v4 env).
    assert target == "treesitter_chunk_id_v1"

    # Read is allowed (a genuinely-compatible legacy index must not fail closed).
    with sqlite3.connect(store.db_path) as raw:
        assert_chunk_scheme_readable(raw)  # does not raise
    assert store.get_chunks_for_file(file_id)  # store-level read allowed

    # Write is allowed AND durably auto-stamps the marker as v1.
    _store_code_chunk(store, file_id, "c2")
    assert store.get_chunk_scheme_marker() == "treesitter_chunk_id_v1"
    status, marker, _ = store.get_chunk_scheme_status()
    assert status == "compatible"


def test_unmarked_index_under_new_scheme_fails_closed(tmp_path, monkeypatch):
    """A real scheme change (>=v4) over an unmarked index IS a genuine mismatch:
    ``missing_marker`` - fail closed on read, write, and delete."""
    store = _make_store(tmp_path)
    file_id = _make_file(store)
    _store_code_chunk(store, file_id, "c1")  # stamps v1
    _clear_marker(store)

    _force_scheme(monkeypatch, "treesitter_chunk_id_v4")
    with store._get_connection() as conn:
        status, marker, _ = evaluate_chunk_scheme(conn)
    assert status == "missing_marker"
    assert marker is None

    before = _count_chunks(store)
    with pytest.raises(ChunkSchemeMismatchError):
        _store_code_chunk(store, file_id, "c2")
    with pytest.raises(ChunkSchemeMismatchError):
        store.delete_chunks_for_file(file_id)
    with sqlite3.connect(store.db_path) as raw:
        with pytest.raises(ChunkSchemeMismatchError):
            assert_chunk_scheme_readable(raw)
    assert _count_chunks(store) == before  # no read/delete/upsert mutated the index


def test_store_level_read_fails_closed_under_mismatch(tmp_path):
    """Fix #2: store-level readers route through the central read guard, so a
    direct get_chunk over a scheme-mismatched DB fails closed - not only at the
    tool-layer perimeter."""
    store = _make_store(tmp_path)
    file_id = _make_file(store)
    _store_code_chunk(store, file_id, "c1")
    _insert_summary(store, "c1", file_id)
    # Simulate a foreign-scheme (v4-built) index read by this (v1) runtime.
    with store._get_connection() as conn:
        conn.execute(
            "UPDATE index_config SET config_value = ? WHERE config_key = ?",
            (FOREIGN_SCHEME, CHUNK_SCHEME_MARKER_KEY),
        )
    with store._get_connection() as conn:
        status, _marker, _ = evaluate_chunk_scheme(conn)
    assert status == "mismatch"

    for reader in (
        lambda: store.get_chunk_by_chunk_id("c1", file_id=file_id),
        lambda: store.get_chunk_by_node_id("node-c1"),
        lambda: store.get_chunk_by_definition_id("def-1"),
        lambda: store.get_chunks_for_file(file_id),
        lambda: store.get_missing_summaries(),
        lambda: store.find_best_chunk_for_file(file_id, ["f"]),
        lambda: store.find_chunk_at_line("/repo/a.py", 1),
    ):
        with pytest.raises(ChunkSchemeMismatchError):
            reader()


def test_readiness_reports_scheme_mismatch_not_ready(tmp_path):
    store = _make_store(tmp_path)
    file_id = _make_file(store)
    _store_code_chunk(store, file_id, "c1")
    # A foreign-scheme marker (v4-built index under a v1 runtime) is a genuine
    # mismatch that readiness must surface as non-ready.
    with store._get_connection() as conn:
        conn.execute(
            "UPDATE index_config SET config_value = ? WHERE config_key = ?",
            (FOREIGN_SCHEME, CHUNK_SCHEME_MARKER_KEY),
        )

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


def _rebuild_write(store: SQLiteStore, file_id: int, chunk_id: str, target: str) -> int:
    """The explicitly-scoped rebuild writer: writes rows tagged with the rebuild's
    target scheme so they are admitted during the ``rebuilding`` window."""
    return store.store_chunk(
        file_id=file_id,
        content="x\n",
        content_start=0,
        content_end=1,
        line_start=1,
        line_end=1,
        chunk_id=chunk_id,
        node_id=f"node-{chunk_id}",
        treesitter_file_id="t",
        scheme_target=target,
    )


def test_rebuild_flips_marker_only_after_repopulation(tmp_path):
    store = _make_store(tmp_path)
    code_file, _hist = _seed_for_rebuild(store)
    marker_before = store.get_chunk_scheme_marker()

    # Phase 1: invalidate + enter rebuilding to a NEW scheme; marker NOT flipped.
    store.begin_chunk_scheme_rebuild(FOREIGN_SCHEME, profile_id="profile-a")
    with store._get_connection() as conn:
        status, _marker, _target = evaluate_chunk_scheme(conn, FOREIGN_SCHEME)
    assert status == "rebuilding"
    assert store.get_chunk_scheme_marker() == marker_before  # unchanged

    # An ordinary (old-scheme) writer must NOT commit rows during the rebuild
    # window - only the explicitly-scoped rebuild writer may (fix #3).
    with pytest.raises(ChunkSchemeMismatchError):
        _store_code_chunk(store, code_file, "wrong-scheme")  # target = v1 runtime

    # Repopulate with the rebuild writer (scheme_target == the rebuild target).
    _rebuild_write(store, code_file, "rebuilt-1", FOREIGN_SCHEME)

    # Phase 2: finalize now flips the marker and clears the rebuilding flag.
    store.finalize_chunk_scheme_rebuild(FOREIGN_SCHEME)
    assert store.get_chunk_scheme_marker() == FOREIGN_SCHEME
    with store._get_connection() as conn:
        status, marker, _ = evaluate_chunk_scheme(conn, FOREIGN_SCHEME)
    assert status == "compatible"


def test_finalize_refuses_empty_or_mismatched_target(tmp_path):
    """Fix #3: finalize is not a rubber stamp - it refuses to flip the marker when
    no repopulation happened or the caller's target != the recorded rebuild
    target."""
    store = _make_store(tmp_path)
    _seed_for_rebuild(store)
    store.begin_chunk_scheme_rebuild(FOREIGN_SCHEME, profile_id="profile-a")

    # No repopulation yet -> finalize must refuse (would stamp an empty index).
    with pytest.raises(ChunkSchemeMismatchError) as empty_exc:
        store.finalize_chunk_scheme_rebuild(FOREIGN_SCHEME)
    assert empty_exc.value.state == "rebuild_not_repopulated"
    assert store.get_chunk_scheme_marker() != FOREIGN_SCHEME  # still not flipped

    # Repopulate, then a finalize whose target != recorded rebuild target refuses.
    resumed = _make_file(store, "resumed.py")
    _rebuild_write(store, resumed, "rebuilt-1", FOREIGN_SCHEME)
    with pytest.raises(ChunkSchemeMismatchError) as mismatch_exc:
        store.finalize_chunk_scheme_rebuild("treesitter_chunk_id_v9_other")
    assert mismatch_exc.value.state == "rebuild_target_mismatch"

    # Correct target with repopulation present -> finalizes.
    store.finalize_chunk_scheme_rebuild(FOREIGN_SCHEME)
    assert store.get_chunk_scheme_marker() == FOREIGN_SCHEME

    # A second finalize (no rebuild in progress) refuses.
    with pytest.raises(ChunkSchemeMismatchError) as done_exc:
        store.finalize_chunk_scheme_rebuild(FOREIGN_SCHEME)
    assert done_exc.value.state == "not_rebuilding"


def test_rebuild_invalidates_all_profiles_semantic_mappings(tmp_path):
    """Fix #4: the scheme marker is DB-wide, so a rebuild must invalidate EVERY
    profile's stale semantic-point mappings, not just the caller's profile."""
    store = _make_store(tmp_path)
    _seed_for_rebuild(store)  # profile-a mappings (101, 102) + document (900)
    # A second profile with its own chunker + preserved-document mappings.
    store.upsert_semantic_point("profile-b", "code-chunk-1", 201, "col-b")
    store.upsert_semantic_point("profile-b", "history:issue", 901, "col-b")

    result = store.rebuild_chunk_scheme(profile_id="profile-a")  # begin (no repopulate)

    with store._get_connection() as conn:
        remaining = {
            (r[0], r[1])
            for r in conn.execute("SELECT profile_id, chunk_id FROM semantic_points")
        }
    # Both profiles' chunker mappings gone; both profiles' document mapping kept.
    assert ("profile-a", "code-chunk-1") not in remaining
    assert ("profile-b", "code-chunk-1") not in remaining
    assert ("profile-a", "history:issue") in remaining
    assert ("profile-b", "history:issue") in remaining

    # Returned stale points span BOTH profiles (with their collections) so remote
    # cleanup can target the right collection for each.
    returned = {(p["profile_id"], p["point_id"], p["collection"]) for p in result["points"]}
    assert ("profile-a", 101, "col-a") in returned
    assert ("profile-a", 102, "col-a") in returned
    assert ("profile-b", 201, "col-b") in returned


def test_rebuild_persists_pending_vector_deletions_ledger(tmp_path):
    """Fix #7 (I4): stale remote-vector ids are persisted to a durable crash-ledger
    inside the invalidation transaction, so a crash before the caller's remote
    cleanup cannot orphan them."""
    store = _make_store(tmp_path)
    _seed_for_rebuild(store)
    store.upsert_semantic_point("profile-b", "code-chunk-2", 202, "col-b")

    assert store.get_pending_vector_deletions() == []

    store.begin_chunk_scheme_rebuild(profile_id="profile-a")

    ledger = store.get_pending_vector_deletions()
    point_ids = {row["point_id"] for row in ledger}
    # Every chunker point (all profiles) recorded; preserved document point kept.
    assert {101, 102, 202}.issubset(point_ids)
    assert 900 not in point_ids

    # Ledger survives the local semantic_points delete (rows gone, ledger stays).
    with store._get_connection() as conn:
        remaining = {r[0] for r in conn.execute("SELECT point_id FROM semantic_points")}
    assert remaining == {900}

    # Clearing after remote cleanup drains the ledger.
    cleared = store.clear_pending_vector_deletions()
    assert cleared == len(ledger)
    assert store.get_pending_vector_deletions() == []


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


# --------------------------------------------------------------------------- #
# 7. Lock-contention must fail loud, not be misread as an empty index (I1)
# --------------------------------------------------------------------------- #
def test_scheme_probe_reraises_non_schema_operational_error():
    """Fix #5 (I1): a lock/contention ``OperationalError`` must propagate, not be
    swallowed as 'absent' - swallowing it would let a marked, locked DB be
    reclassified ``empty`` and silently re-stamped with a new scheme.  Only a
    genuine missing-table/column (schema-not-present) is treated as absent."""

    class _LockedConn:
        def execute(self, *_args, **_kwargs):
            raise sqlite3.OperationalError("database is locked")

    with pytest.raises(sqlite3.OperationalError):
        sqlite_store_module._has_chunker_rows(_LockedConn())
    with pytest.raises(sqlite3.OperationalError):
        sqlite_store_module._scheme_read_config_value(_LockedConn(), "k")

    class _NoTableConn:
        def execute(self, *_args, **_kwargs):
            raise sqlite3.OperationalError("no such table: code_chunks")

    # A genuinely-absent schema is still treated as absent (no raise).
    assert sqlite_store_module._has_chunker_rows(_NoTableConn()) is False

    class _NoColumnConn:
        def execute(self, *_args, **_kwargs):
            raise sqlite3.OperationalError("no such column: chunk_type")

    # An older/minimal schema (table present, column absent) is absent, not corrupt.
    assert sqlite_store_module._has_chunker_rows(_NoColumnConn()) is False
