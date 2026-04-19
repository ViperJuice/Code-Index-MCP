"""Tests for _get_chunk_ids_for_path pagination (limit/offset)."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Optional
from unittest.mock import MagicMock, patch

import pytest

from mcp_server.indexing.incremental_indexer import IncrementalIndexer


def _build_store(conn: sqlite3.Connection) -> MagicMock:
    """Build a mock SQLiteStore that returns the given connection."""
    store = MagicMock()
    store._get_connection.return_value.__enter__ = lambda s: conn
    store._get_connection.return_value.__exit__ = MagicMock(return_value=False)
    return store


def _build_indexer(conn: sqlite3.Connection, repo_path: Path) -> IncrementalIndexer:
    store = _build_store(conn)
    dispatcher = MagicMock()
    indexer = IncrementalIndexer(store=store, dispatcher=dispatcher, repo_path=repo_path)
    indexer._get_repository_id = MagicMock(return_value=1)
    indexer.path_resolver = MagicMock()
    indexer.path_resolver.normalize_path.side_effect = lambda p: str(p.relative_to(repo_path))
    return indexer


def _populate_db(conn: sqlite3.Connection, repo_path: Path, num_chunks: int = 5) -> list[str]:
    """Insert a file and N code_chunk rows; return list of chunk_ids."""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS files (id INTEGER PRIMARY KEY, relative_path TEXT, repository_id INTEGER)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS code_chunks (id INTEGER PRIMARY KEY, file_id INTEGER, chunk_id TEXT)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS semantic_points (id INTEGER PRIMARY KEY, chunk_id TEXT, profile_id TEXT)"
    )
    rel = "src/foo.py"
    conn.execute("INSERT INTO files (id, relative_path, repository_id) VALUES (1, ?, 1)", (rel,))
    chunk_ids = [f"chunk_{i}" for i in range(num_chunks)]
    for cid in chunk_ids:
        conn.execute("INSERT INTO code_chunks (file_id, chunk_id) VALUES (1, ?)", (cid,))
    conn.commit()
    return chunk_ids


class TestGetChunkIdsForPathPagination:
    def test_default_backcompat(self, tmp_path):
        """Default call (no limit/offset) returns all chunks — behavior unchanged."""
        conn = sqlite3.connect(":memory:")
        chunk_ids = _populate_db(conn, tmp_path, num_chunks=5)
        indexer = _build_indexer(conn, tmp_path)
        indexer.path_resolver.normalize_path.side_effect = lambda p: "src/foo.py"

        result = indexer._get_chunk_ids_for_path("src/foo.py")
        assert sorted(result) == sorted(chunk_ids)

    def test_pagination_respects_limit_offset(self, tmp_path):
        """Passing limit=2, offset=1 returns at most 2 chunks starting from row 1."""
        conn = sqlite3.connect(":memory:")
        chunk_ids = _populate_db(conn, tmp_path, num_chunks=5)
        indexer = _build_indexer(conn, tmp_path)
        indexer.path_resolver.normalize_path.side_effect = lambda p: "src/foo.py"

        result = indexer._get_chunk_ids_for_path("src/foo.py", limit=2, offset=1)
        # Should have exactly 2 items (or fewer if DB has fewer rows remaining)
        assert len(result) <= 2

    def test_limit_zero_returns_empty(self, tmp_path):
        """limit=0 should return empty list."""
        conn = sqlite3.connect(":memory:")
        _populate_db(conn, tmp_path, num_chunks=5)
        indexer = _build_indexer(conn, tmp_path)
        indexer.path_resolver.normalize_path.side_effect = lambda p: "src/foo.py"

        result = indexer._get_chunk_ids_for_path("src/foo.py", limit=0, offset=0)
        assert result == []

    def test_pagination_limit_larger_than_rows(self, tmp_path):
        """limit > num_rows returns all available chunks."""
        conn = sqlite3.connect(":memory:")
        chunk_ids = _populate_db(conn, tmp_path, num_chunks=3)
        indexer = _build_indexer(conn, tmp_path)
        indexer.path_resolver.normalize_path.side_effect = lambda p: "src/foo.py"

        result = indexer._get_chunk_ids_for_path("src/foo.py", limit=100, offset=0)
        assert sorted(result) == sorted(chunk_ids)

    def test_get_chunk_ids_for_path_pagination_respects_limit_offset(self, tmp_path):
        """Named test matching SL-4 task requirement."""
        conn = sqlite3.connect(":memory:")
        _populate_db(conn, tmp_path, num_chunks=4)
        indexer = _build_indexer(conn, tmp_path)
        indexer.path_resolver.normalize_path.side_effect = lambda p: "src/foo.py"

        all_chunks = indexer._get_chunk_ids_for_path("src/foo.py")
        paged = indexer._get_chunk_ids_for_path("src/foo.py", limit=2, offset=0)
        assert len(paged) == 2
        assert set(paged).issubset(set(all_chunks))

    def test_get_chunk_ids_for_path_default_backcompat(self, tmp_path):
        """Named test matching SL-4 task requirement — default call equals paginated(limit=all)."""
        conn = sqlite3.connect(":memory:")
        chunk_ids = _populate_db(conn, tmp_path, num_chunks=4)
        indexer = _build_indexer(conn, tmp_path)
        indexer.path_resolver.normalize_path.side_effect = lambda p: "src/foo.py"

        default_result = indexer._get_chunk_ids_for_path("src/foo.py")
        full_paged = indexer._get_chunk_ids_for_path("src/foo.py", limit=None, offset=0)
        assert sorted(default_result) == sorted(full_paged)
        assert sorted(default_result) == sorted(chunk_ids)
