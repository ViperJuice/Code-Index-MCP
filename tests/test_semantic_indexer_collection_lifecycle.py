"""Fail-closed collection lifecycle tests for the semantic indexer.

These tests mock the qdrant client entirely - no live network or server is
used. They lock in the INFERSAFE Lane A guarantees:

* create-when-absent uses the non-destructive ``create_collection`` (never
  ``recreate_collection``);
* a shape mismatch is refused (``blocked``) unless an operator explicitly
  allows recreation;
* an unreadable/unknown collection config fails closed (``blocked``), never
  silently reused;
* a ``blocked`` result raises an actionable diagnostic at runtime;
* explicit operator-authorized recreation succeeds only with the flag set.
"""

from types import SimpleNamespace

import pytest

from mcp_server.utils.semantic_indexer import (
    SemanticIndexer,
    ensure_qdrant_collection,
)

COSINE = SemanticIndexer.resolve_qdrant_distance("cosine")
DOT = SemanticIndexer.resolve_qdrant_distance("dot")


class FakeQdrantClient:
    """Minimal in-memory qdrant double that records lifecycle calls."""

    def __init__(self) -> None:
        # name -> (size, distance); (None, None) simulates an unreadable config.
        self.collections: dict[str, tuple] = {}
        self.calls: list[tuple[str, str]] = []

    def get_collections(self):
        return SimpleNamespace(
            collections=[SimpleNamespace(name=name) for name in self.collections]
        )

    def get_collection(self, collection_name):
        size, distance = self.collections[collection_name]
        return SimpleNamespace(
            config=SimpleNamespace(
                params=SimpleNamespace(
                    vectors=SimpleNamespace(size=size, distance=distance)
                )
            )
        )

    def create_collection(self, *, collection_name, vectors_config):
        self.calls.append(("create", collection_name))
        self.collections[collection_name] = (vectors_config.size, vectors_config.distance)

    def recreate_collection(self, *, collection_name, vectors_config):
        self.calls.append(("recreate", collection_name))
        self.collections[collection_name] = (vectors_config.size, vectors_config.distance)


def _bare_indexer(client: FakeQdrantClient) -> SemanticIndexer:
    """Build a SemanticIndexer without running the heavy __init__."""
    indexer = SemanticIndexer.__new__(SemanticIndexer)
    indexer._qdrant_available = True
    indexer.qdrant = client
    indexer.collection = "semantic-oss-high"
    indexer.embedding_dimension = 4096
    indexer.distance_metric = "cosine"
    return indexer


def test_create_when_absent_uses_create_not_recreate():
    client = FakeQdrantClient()

    result = ensure_qdrant_collection(
        client,
        collection_name="semantic-oss-high",
        expected_dimension=4096,
        distance_metric="cosine",
    )

    assert result.status == "created"
    assert ("create", "semantic-oss-high") in client.calls
    # The destructive recreate path must never fire when creating from absent.
    assert all(kind != "recreate" for kind, _ in client.calls)


def test_default_is_fail_closed_no_recreate_on_mismatch():
    client = FakeQdrantClient()
    client.collections["semantic-oss-high"] = (1024, COSINE)

    # Default allow_recreate is False (fail-closed).
    result = ensure_qdrant_collection(
        client,
        collection_name="semantic-oss-high",
        expected_dimension=4096,
        distance_metric="cosine",
    )

    assert result.status == "blocked"
    assert result.actual_dimension == 1024
    # Nothing destructive happened.
    assert client.calls == []


def test_refuse_on_unreadable_config_blocks():
    client = FakeQdrantClient()
    # Simulate a collection whose config cannot be read (size/distance unknown).
    client.collections["semantic-oss-high"] = (None, None)

    result = ensure_qdrant_collection(
        client,
        collection_name="semantic-oss-high",
        expected_dimension=4096,
        distance_metric="cosine",
    )

    assert result.status == "blocked"
    assert client.calls == []


def test_matching_collection_is_reused():
    client = FakeQdrantClient()
    client.collections["semantic-oss-high"] = (4096, COSINE)

    result = ensure_qdrant_collection(
        client,
        collection_name="semantic-oss-high",
        expected_dimension=4096,
        distance_metric="cosine",
    )

    assert result.status == "reused"
    assert client.calls == []


def test_explicit_operator_recreate_succeeds_only_with_flag():
    client = FakeQdrantClient()
    client.collections["semantic-oss-high"] = (1024, COSINE)

    # Operator-authorized path explicitly opts in to destructive recreation.
    result = ensure_qdrant_collection(
        client,
        collection_name="semantic-oss-high",
        expected_dimension=4096,
        distance_metric="cosine",
        allow_recreate=True,
    )

    assert result.status == "recreated"
    assert ("recreate", "semantic-oss-high") in client.calls
    assert client.collections["semantic-oss-high"] == (4096, COSINE)


def test_distance_metric_mismatch_blocks_by_default():
    client = FakeQdrantClient()
    client.collections["semantic-oss-high"] = (4096, DOT)

    result = ensure_qdrant_collection(
        client,
        collection_name="semantic-oss-high",
        expected_dimension=4096,
        distance_metric="cosine",
    )

    assert result.status == "blocked"
    assert client.calls == []


def test_ensure_collection_raises_on_blocked_at_runtime():
    client = FakeQdrantClient()
    client.collections["semantic-oss-high"] = (1024, COSINE)
    indexer = _bare_indexer(client)

    with pytest.raises(RuntimeError) as excinfo:
        # Runtime default never recreates and must raise on blocked.
        indexer._ensure_collection()

    assert "blocked" in str(excinfo.value).lower()
    # Runtime must never destructively recreate a mismatched live collection.
    assert all(kind != "recreate" for kind, _ in client.calls)


def test_ensure_collection_operator_flag_allows_recreate():
    client = FakeQdrantClient()
    client.collections["semantic-oss-high"] = (1024, COSINE)
    indexer = _bare_indexer(client)

    # Operator-authorized caller may thread the explicit flag.
    indexer._ensure_collection(allow_recreate=True)

    assert ("recreate", "semantic-oss-high") in client.calls
    assert client.collections["semantic-oss-high"] == (4096, COSINE)


def test_ensure_collection_creates_when_absent_at_runtime():
    client = FakeQdrantClient()
    indexer = _bare_indexer(client)

    indexer._ensure_collection()

    assert ("create", "semantic-oss-high") in client.calls
    assert all(kind != "recreate" for kind, _ in client.calls)
