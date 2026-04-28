"""Focused tests for profile-aware semantic indexer behavior."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from mcp_server.artifacts.semantic_profiles import SemanticProfileRegistry
from mcp_server.utils import semantic_indexer as semantic_indexer_module
from mcp_server.utils.semantic_indexer import SemanticIndexer


class _FakeEmbeddingProvider:
    def __init__(self, provider_name: str, dimension: int) -> None:
        self._provider_name = provider_name
        self._dimension = dimension

    @property
    def provider_name(self) -> str:
        return self._provider_name

    def embed(self, texts, input_type="document"):
        del input_type
        return [[0.0] * self._dimension for _ in texts]


class _FakeQdrantClient:
    def __init__(self) -> None:
        self.upserts = []

    def upsert(self, *, collection_name, points):
        self.upserts.append((collection_name, list(points)))


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
            "build_metadata": {"collection_name": "semantic-commercial-high"},
        },
        "oss-high": {
            "provider": "openai_compatible",
            "model_name": "Qwen/Qwen3-Embedding-8B",
            "model_version": "vllm-local",
            "vector_dimension": 4096,
            "distance_metric": "cosine",
            "normalization_policy": "none",
            "chunk_schema_version": "2.1",
            "chunker_version": "treesitter-v3",
            "build_metadata": {"collection_name": "semantic-oss-high"},
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
    monkeypatch.setattr(SemanticIndexer, "_get_git_commit_hash", lambda self: "deadbeef")

    def _fake_provider(
        provider_name: str,
        model_name: str,
        vector_dimension: int,
        api_key=None,
        base_url=None,
    ):
        del model_name, api_key, base_url
        normalized = provider_name.strip().lower()
        if normalized in {"voyage", "voyageai"}:
            return _FakeEmbeddingProvider("voyage", vector_dimension)
        return _FakeEmbeddingProvider("openai_compatible", vector_dimension)

    monkeypatch.setattr(
        semantic_indexer_module,
        "create_embedding_provider",
        _fake_provider,
    )


class _FakeSQLiteStore:
    def __init__(self, summary_text: str | None) -> None:
        self.summary_text = summary_text
        self.semantic_points = []

    def get_chunk_summary(self, _chunk_id: str):
        if self.summary_text is None:
            return None
        return {"summary_text": self.summary_text}

    def upsert_semantic_point(self, **kwargs):
        self.semantic_points.append(kwargs)


def _patch_chunk_file(monkeypatch, chunk_id: str = "chunk-1") -> None:
    def _fake_chunk_file(*_args, **_kwargs):
        return [
            SimpleNamespace(
                content="def alpha(x):\n    return x + 1\n",
                metadata={"symbol": "alpha", "kind": "function", "signature_text": "alpha(x)"},
                start_line=1,
                end_line=2,
                node_type="function_definition",
                chunk_id=chunk_id,
                node_id=chunk_id,
            )
        ]

    monkeypatch.setattr(semantic_indexer_module, "chunk_file", _fake_chunk_file)


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

    assert indexer.embedding_provider == "openai_compatible"
    assert indexer.embedding_model == "Qwen/Qwen3-Embedding-8B"
    assert indexer.embedding_model_version == "vllm-local"
    assert indexer.embedding_dimension == 4096
    assert indexer.distance_metric == "cosine"
    assert indexer.normalization_policy == "none"
    assert indexer.chunk_schema_version == "2.1"
    assert "__oss-high__" in indexer.collection


def test_legacy_fallback_remains_compatible(monkeypatch, tmp_path):
    _patch_indexer_runtime(monkeypatch, tmp_path)

    indexer = SemanticIndexer(collection="legacy-collection", qdrant_path=":memory:")

    assert indexer.collection == "legacy-collection"
    assert indexer.embedding_model == "voyage-code-3"
    assert indexer.embedding_dimension == 1024
    assert indexer.distance_metric == "cosine"

    expected = hashlib.sha256("voyage-code-3:1024:cosine".encode("utf-8")).hexdigest()[:16]
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

    assert commercial_metadata["compatibility_hash"] != oss_metadata["compatibility_hash"]
    assert (
        commercial_metadata["compatibility_fingerprint"]
        != oss_metadata["compatibility_fingerprint"]
    )
    assert commercial.collection == "semantic-commercial-high"
    assert oss.collection == "semantic-oss-high"


def test_metadata_file_accumulates_multiple_semantic_profiles(monkeypatch, tmp_path):
    _patch_indexer_runtime(monkeypatch, tmp_path)
    registry = SemanticProfileRegistry.from_raw(_sample_profiles(), "commercial-high")

    SemanticIndexer(
        collection="code-index",
        qdrant_path=":memory:",
        profile_registry=registry,
        semantic_profile="commercial-high",
    )
    SemanticIndexer(
        collection="code-index",
        qdrant_path=":memory:",
        profile_registry=registry,
        semantic_profile="oss-high",
    )

    metadata = json.loads((tmp_path / ".index_metadata.json").read_text(encoding="utf-8"))

    assert metadata["semantic_profile"] == "oss-high"
    assert sorted(metadata["semantic_profiles"].keys()) == [
        "commercial-high",
        "oss-high",
    ]
    assert (
        metadata["semantic_profiles"]["commercial-high"]["compatibility_fingerprint"]
        == registry.get("commercial-high").compatibility_fingerprint
    )
    assert (
        metadata["semantic_profiles"]["oss-high"]["compatibility_fingerprint"]
        == registry.get("oss-high").compatibility_fingerprint
    )
    assert (
        metadata["semantic_profiles"]["commercial-high"]["collection_name"]
        == "semantic-commercial-high"
    )
    assert metadata["semantic_profiles"]["oss-high"]["collection_name"] == "semantic-oss-high"


def test_strict_batch_indexing_refuses_writes_without_authoritative_summary(monkeypatch, tmp_path):
    _patch_indexer_runtime(monkeypatch, tmp_path)
    _patch_chunk_file(monkeypatch)
    registry = SemanticProfileRegistry.from_raw(_sample_profiles(), "oss-high")
    sqlite_store = _FakeSQLiteStore(summary_text=None)
    source = tmp_path / "sample.py"
    source.write_text("def alpha(x):\n    return x + 1\n", encoding="utf-8")

    indexer = SemanticIndexer(
        collection="code-index",
        qdrant_path=":memory:",
        profile_registry=registry,
        semantic_profile="oss-high",
        sqlite_store=sqlite_store,
    )

    result = indexer.index_files_batch([source], require_summaries=True)

    assert result["files_indexed"] == 0
    assert result["files_blocked"] == 1
    assert result["missing_summary_chunk_ids"] == ["chunk-1"]
    assert indexer.qdrant.upserts == []


def test_strict_preparation_includes_summary_text_in_embedding_input(monkeypatch, tmp_path):
    _patch_indexer_runtime(monkeypatch, tmp_path)
    _patch_chunk_file(monkeypatch)
    registry = SemanticProfileRegistry.from_raw(_sample_profiles(), "oss-high")
    sqlite_store = _FakeSQLiteStore(summary_text="Summarizes alpha and its input")
    source = tmp_path / "sample.py"
    source.write_text("def alpha(x):\n    return x + 1\n", encoding="utf-8")

    indexer = SemanticIndexer(
        collection="code-index",
        qdrant_path=":memory:",
        profile_registry=registry,
        semantic_profile="oss-high",
        sqlite_store=sqlite_store,
    )

    prep = indexer._prepare_file_for_indexing(Path(source))

    assert prep is not None
    assert any("Summarizes alpha and its input" in text for text in prep["embedding_inputs"])
    assert any("return x + 1" in text for text in prep["embedding_inputs"])


def test_successful_strict_batch_indexing_persists_chunk_point_links(monkeypatch, tmp_path):
    _patch_indexer_runtime(monkeypatch, tmp_path)
    _patch_chunk_file(monkeypatch, chunk_id="chunk-link")
    registry = SemanticProfileRegistry.from_raw(_sample_profiles(), "oss-high")
    sqlite_store = _FakeSQLiteStore(summary_text="Summarizes alpha and its input")
    source = tmp_path / "sample.py"
    source.write_text("def alpha(x):\n    return x + 1\n", encoding="utf-8")

    indexer = SemanticIndexer(
        collection="code-index",
        qdrant_path=":memory:",
        profile_registry=registry,
        semantic_profile="oss-high",
        sqlite_store=sqlite_store,
    )

    result = indexer.index_files_batch([source], require_summaries=True)

    assert result["files_indexed"] == 1
    assert len(sqlite_store.semantic_points) == 1
    assert sqlite_store.semantic_points[0]["chunk_id"] == "chunk-link"
    assert sqlite_store.semantic_points[0]["profile_id"] == "oss-high"


def test_preflight_blocker_prevents_any_qdrant_upsert(monkeypatch, tmp_path):
    _patch_indexer_runtime(monkeypatch, tmp_path)
    _patch_chunk_file(monkeypatch)
    registry = SemanticProfileRegistry.from_raw(_sample_profiles(), "oss-high")
    sqlite_store = _FakeSQLiteStore(summary_text="Summarizes alpha and its input")
    source = tmp_path / "sample.py"
    source.write_text("def alpha(x):\n    return x + 1\n", encoding="utf-8")

    indexer = SemanticIndexer(
        collection="code-index",
        qdrant_path=":memory:",
        profile_registry=registry,
        semantic_profile="oss-high",
        sqlite_store=sqlite_store,
    )

    result = indexer.index_files_batch(
        [source],
        require_summaries=True,
        semantic_preflight={
            "can_write_semantic_vectors": False,
            "blocker": {"code": "collection_missing", "message": "Collection missing"},
        },
    )

    assert result["files_blocked"] == 1
    assert indexer.qdrant.upserts == []
