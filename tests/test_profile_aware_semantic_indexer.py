"""Focused tests for profile-aware semantic indexer behavior."""

from __future__ import annotations

import hashlib
from types import SimpleNamespace

from mcp_server.artifacts.semantic_profiles import SemanticProfileRegistry
from mcp_server.utils.semantic_indexer import SemanticIndexer


class _FakeVoyageClient:
    def embed(self, texts, **kwargs):
        dimension = int(kwargs.get("output_dimension", 8))
        return SimpleNamespace(embeddings=[[0.0] * dimension for _ in texts])


class _FakeQdrantClient:
    pass


def _sample_profiles() -> dict[str, dict[str, object]]:
    return {
        "commercial-high": {
            "provider": "voyage",
            "model_name": "voyage-code-3",
            "model_version": "2025-01",
            "vector_dimension": 1024,
            "distance_metric": "cosine",
            "normalization_policy": "provider-default",
            "chunk_schema_version": "2.0",
            "chunker_version": "treesitter-v2",
        },
        "oss-high": {
            "provider": "sentence-transformers",
            "model_name": "intfloat/e5-large-v2",
            "model_version": "hf-sha-abc123",
            "vector_dimension": 768,
            "distance_metric": "dot",
            "normalization_policy": "l2",
            "chunk_schema_version": "2.1",
            "chunker_version": "treesitter-v3",
        },
    }


def _patch_indexer_runtime(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)

    def _fake_init_qdrant(self, qdrant_path):
        self._qdrant_available = True
        self._connection_mode = "memory"
        return _FakeQdrantClient()

    monkeypatch.setattr(SemanticIndexer, "_init_qdrant_client", _fake_init_qdrant)
    monkeypatch.setattr(SemanticIndexer, "_ensure_collection", lambda self: None)
    monkeypatch.setattr(
        SemanticIndexer, "_get_git_commit_hash", lambda self: "deadbeef"
    )
    monkeypatch.setattr(
        "mcp_server.utils.semantic_indexer.voyageai.Client",
        lambda *args, **kwargs: _FakeVoyageClient(),
    )


def test_profile_configuration_is_selected_from_registry(monkeypatch, tmp_path):
    _patch_indexer_runtime(monkeypatch, tmp_path)
    registry = SemanticProfileRegistry.from_raw(_sample_profiles(), "commercial-high")

    indexer = SemanticIndexer(
        collection="code-index",
        qdrant_path=":memory:",
        profile_registry=registry,
        semantic_profile="oss-high",
        repo_identifier="https://github.com/acme/repo.git",
        branch="main",
        commit="abcdef123456",
    )

    assert indexer.embedding_model == "intfloat/e5-large-v2"
    assert indexer.embedding_model_version == "hf-sha-abc123"
    assert indexer.embedding_dimension == 768
    assert indexer.distance_metric == "dot"
    assert indexer.normalization_policy == "l2"
    assert indexer.chunk_schema_version == "2.1"
    assert "__oss-high__" in indexer.collection


def test_legacy_fallback_remains_compatible(monkeypatch, tmp_path):
    _patch_indexer_runtime(monkeypatch, tmp_path)

    indexer = SemanticIndexer(collection="legacy-collection", qdrant_path=":memory:")

    assert indexer.collection == "legacy-collection"
    assert indexer.embedding_model == "voyage-code-3"
    assert indexer.embedding_dimension == 1024
    assert indexer.distance_metric == "cosine"

    expected = hashlib.sha256("voyage-code-3:1024:cosine".encode("utf-8")).hexdigest()[
        :16
    ]
    assert indexer._generate_compatibility_hash() == expected

    metadata = indexer._build_metadata()
    assert "semantic_profile" not in metadata
    assert "compatibility_fingerprint" not in metadata


def test_compatibility_metadata_differs_by_profile(monkeypatch, tmp_path):
    _patch_indexer_runtime(monkeypatch, tmp_path)
    registry = SemanticProfileRegistry.from_raw(_sample_profiles(), "commercial-high")

    commercial = SemanticIndexer(
        collection="code-index",
        qdrant_path=":memory:",
        profile_registry=registry,
        semantic_profile="commercial-high",
    )
    oss = SemanticIndexer(
        collection="code-index",
        qdrant_path=":memory:",
        profile_registry=registry,
        semantic_profile="oss-high",
    )

    commercial_metadata = commercial._build_metadata()
    oss_metadata = oss._build_metadata()

    assert (
        commercial_metadata["compatibility_hash"] != oss_metadata["compatibility_hash"]
    )
    assert (
        commercial_metadata["compatibility_fingerprint"]
        != oss_metadata["compatibility_fingerprint"]
    )
