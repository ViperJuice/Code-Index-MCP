"""Tests for profile-scoped stale vector cleanup and mapping writes."""

from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace

from mcp_server.core.path_resolver import PathResolver
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.utils.semantic_indexer import SemanticIndexer


class _FakeEmbeddingProvider:
    provider_name = "voyage"

    def __init__(self, dimension: int = 8) -> None:
        self.dimension = dimension

    def embed(self, texts, input_type="document"):
        del input_type
        return [[0.0] * self.dimension for _ in texts]


class _FakeQdrantClient:
    def __init__(self) -> None:
        self.deleted = []
        self.upserted = []

    def delete(self, collection_name: str, points_selector) -> None:
        self.deleted.append(
            {
                "collection": collection_name,
                "points": list(points_selector.points),
            }
        )

    def upsert(self, collection_name: str, points) -> None:
        self.upserted.append(
            {
                "collection": collection_name,
                "points": points,
            }
        )


def _build_indexer(repo_path: Path, qdrant: _FakeQdrantClient) -> SemanticIndexer:
    indexer = SemanticIndexer.__new__(SemanticIndexer)
    indexer.embedding_client = _FakeEmbeddingProvider(8)
    indexer.embedding_provider = "voyage"
    indexer.embedding_model = "voyage-code-3"
    indexer.embedding_dimension = 8
    indexer.path_resolver = PathResolver(repo_path)
    indexer.qdrant = qdrant
    indexer.collection = "code-index"
    indexer._qdrant_available = True
    indexer.semantic_profile = SimpleNamespace(profile_id="test-profile")
    return indexer


def test_delete_stale_vectors_deletes_qdrant_points_and_mappings(tmp_path):
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    store = SQLiteStore(
        str(tmp_path / "index.db"), path_resolver=PathResolver(repo_path)
    )
    qdrant = _FakeQdrantClient()
    indexer = _build_indexer(repo_path, qdrant)

    store.upsert_semantic_point("test-profile", "chunk-1", 101, "code-index")
    store.upsert_semantic_point("test-profile", "chunk-2", 202, "code-index")

    deleted = indexer.delete_stale_vectors(
        profile_id="test-profile",
        chunk_ids=["chunk-1", "chunk-2"],
        sqlite_store=store,
    )

    assert deleted == 2
    assert qdrant.deleted[0]["points"] == [101, 202]
    assert store.get_semantic_point_ids("test-profile", ["chunk-1", "chunk-2"]) == []


def test_index_symbol_writes_mapping_for_chunk_metadata(tmp_path):
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    source_file = repo_path / "doc.md"
    source_file.write_text("# title\nhello")

    store = SQLiteStore(
        str(tmp_path / "index.db"), path_resolver=PathResolver(repo_path)
    )
    qdrant = _FakeQdrantClient()
    indexer = _build_indexer(repo_path, qdrant)

    content = "chunk content"
    content_hash = hashlib.sha256(content.encode()).hexdigest()
    expected_point_id = indexer._symbol_id(
        str(source_file),
        "chunk-1",
        1,
        content_hash,
    )

    indexer.index_symbol(
        file=str(source_file),
        name="chunk-1",
        kind="chunk",
        signature="Chunk 1",
        line=1,
        span=(1, 2),
        content=content,
        metadata={"chunk_id": "chunk-1"},
        sqlite_store=store,
    )

    assert qdrant.upserted
    assert store.get_semantic_point_ids("test-profile", ["chunk-1"]) == [
        expected_point_id
    ]
