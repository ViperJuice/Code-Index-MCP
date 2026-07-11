"""EMBEDPROV lane E2: provenance-validated embedding lifecycle (IF-0-EMBEDPROV-1).

These tests are fully offline: the embedding provider and the qdrant client are
deterministic in-memory doubles built with no network and no SDK. They lock in:

* provenance round-trip + profile-derived-from-response (server-reported values
  replace assumed ones; provider-unreportable fields are explicitly declared);
* fail-closed on a compatibility-critical field that is neither reported nor
  declarable, and on a reported value that mismatches the profile, at BOTH index
  time and query time;
* one-to-one request↔response index validation that rejects a scrambled/short
  response rather than misattaching a vector to the wrong chunk;
* the lifecycle-ordering invariant: a provider failure or a metadata-write
  failure mutates ZERO collection/metadata state (attest -> persist ->
  ensure_collection ordering);
* the reconciliation path for pre-provenance collections, whose diagnostic names
  the reindex remediation.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from mcp_server.artifacts.semantic_profiles import (
    REINDEX_REMEDIATION,
    SemanticProfile,
    attest_embedding_response,
    build_expected_profile,
)
from mcp_server.interfaces.inference_contracts import (
    EmbeddingItem,
    EmbeddingItemStatus,
    EmbeddingResponseV1,
    EmbeddingRole,
    ProvenanceAuthority,
    ProvenanceField,
)
from mcp_server.utils.semantic_indexer import SemanticIndexer


# ---------------------------------------------------------------------------
# Response builders (no network, no SDK)
# ---------------------------------------------------------------------------


def _items(vectors):
    return [
        EmbeddingItem(index=i, status=EmbeddingItemStatus.OK, error=None, vector=list(v))
        for i, v in enumerate(vectors)
    ]


def _openai_response(
    texts,
    input_type="document",
    *,
    served_model="srv-model",
    dimension=8,
    normalization=None,
    items=None,
):
    """A well-formed OpenAI-compatible-style response (served_model_id REPORTED)."""
    vectors = [[float(i)] * dimension for i, _ in enumerate(texts)]
    role = EmbeddingRole.QUERY if input_type == "query" else EmbeddingRole.DOCUMENT
    norm = (
        ProvenanceField.declared(normalization)
        if normalization is not None
        else ProvenanceField.unknown()
    )
    return EmbeddingResponseV1(
        provider="openai_compatible",
        served_model_id=ProvenanceField.reported(served_model),
        model_revision=ProvenanceField.unknown(),
        dimension=ProvenanceField.reported(dimension),
        normalization=norm,
        role=ProvenanceField.reported(role.value),
        processor_id=ProvenanceField.unknown(),
        items=_items(vectors) if items is None else items,
    )


class _FakeProvenanceProvider:
    """Provider double that emits a configurable ``embedding-response.v1``."""

    def __init__(self, response_factory, *, provider_name="openai_compatible"):
        self._provider_name = provider_name
        self._factory = response_factory
        self.calls = []

    @property
    def provider_name(self):
        return self._provider_name

    def embed_with_provenance(self, texts, input_type="document"):
        self.calls.append((list(texts), input_type))
        return self._factory(list(texts), input_type)

    def embed(self, texts, input_type="document"):
        return [it.vector for it in self.embed_with_provenance(texts, input_type).items]


class _FailingProvider:
    provider_name = "openai_compatible"

    def __init__(self):
        self.calls = 0

    def embed_with_provenance(self, texts, input_type="document"):
        self.calls += 1
        raise RuntimeError("provider endpoint unreachable")

    def embed(self, texts, input_type="document"):  # pragma: no cover - guard
        raise RuntimeError("provider endpoint unreachable")


class _RecordingQdrant:
    """In-memory qdrant double recording every lifecycle mutation."""

    def __init__(self):
        self.collections = {}
        self.calls = []
        self.upserts = []

    def get_collections(self):
        return SimpleNamespace(
            collections=[SimpleNamespace(name=n) for n in self.collections]
        )

    def get_collection(self, collection_name):
        size, distance = self.collections[collection_name]
        return SimpleNamespace(
            config=SimpleNamespace(
                params=SimpleNamespace(vectors=SimpleNamespace(size=size, distance=distance))
            )
        )

    def create_collection(self, *, collection_name, vectors_config):
        self.calls.append(("create", collection_name))
        self.collections[collection_name] = (vectors_config.size, vectors_config.distance)

    def recreate_collection(self, *, collection_name, vectors_config):
        self.calls.append(("recreate", collection_name))
        self.collections[collection_name] = (vectors_config.size, vectors_config.distance)

    def upsert(self, *, collection_name, points):
        self.upserts.append((collection_name, list(points)))


def _profile(dim=8, model="srv-model"):
    return SemanticProfile.from_dict(
        "oss-high",
        {
            "provider": "openai_compatible",
            "model_name": model,
            "model_version": "v1",
            "vector_dimension": dim,
            "distance_metric": "cosine",
            "normalization_policy": "none",
            "chunk_schema_version": "v1",
            "chunker_version": "chunker@1",
            "build_metadata": {"collection_name": "semantic-oss-high"},
        },
    )


def _make_indexer(tmp_path, provider, *, dim=8, profile=None, collection="semantic-oss-high"):
    profile = profile or _profile(dim=dim)
    ix = SemanticIndexer.__new__(SemanticIndexer)
    ix.embedding_client = provider
    ix.embedding_provider = provider.provider_name
    ix.embedding_model = profile.model_name
    ix.embedding_model_version = profile.model_version
    ix.embedding_dimension = profile.vector_dimension
    ix.distance_metric = profile.distance_metric
    ix.normalization_policy = profile.normalization_policy
    ix.chunk_schema_version = profile.chunk_schema_version
    ix.compatibility_fingerprint = profile.compatibility_fingerprint
    ix.semantic_profile = profile
    ix._profile_active = True
    ix.collection = collection
    ix.qdrant = _RecordingQdrant()
    ix.qdrant_path = ":memory:"
    ix._qdrant_available = True
    ix._writes_prepared = False
    ix._attestation = None
    ix.metadata_file = str(tmp_path / ".index_metadata.json")
    ix._get_git_commit_hash = lambda: "deadbeef"  # type: ignore[assignment]
    return ix


# ===========================================================================
# 1. Provenance round-trip + profile-derived-from-response
# ===========================================================================


def test_attestation_round_trip_derives_reported_values():
    profile = _profile(dim=8, model="srv-model")
    response = _openai_response(["a", "b"], "document", served_model="srv-model", dimension=8)

    att = attest_embedding_response(profile, response, role=EmbeddingRole.DOCUMENT)

    assert att.ok
    assert att.remediation is None
    # Server-reported values are carried into the derived profile.
    assert att.derived["dimension"]["source"] == "reported"
    assert att.derived["dimension"]["value"] == 8
    assert att.derived["served_model_id"]["source"] == "reported"
    assert att.derived["served_model_id"]["value"] == "srv-model"
    assert "dimension" in att.reported_fields
    assert att.role == "document"


def test_unreportable_fields_are_declared_from_profile_not_assumed():
    """model_revision/normalization the provider cannot report become DECLARED
    (from profile), never silently REPORTED, and attestation still passes."""
    profile = _profile(dim=8, model="srv-model")
    response = _openai_response(["a"], "document", served_model="srv-model", dimension=8)
    # response.model_revision + normalization are UNKNOWN from the provider.
    att = attest_embedding_response(profile, response)

    assert att.ok
    assert att.derived["model_revision"]["source"] == "declared"
    assert att.derived["model_revision"]["value"] == "v1"
    assert att.derived["normalization"]["source"] == "declared"
    assert att.derived["normalization"]["value"] == "none"


def test_expected_profile_maps_profile_fields():
    profile = _profile(dim=16, model="m")
    exp = build_expected_profile(profile, role=EmbeddingRole.QUERY)
    assert exp.dimension == 16
    assert exp.served_model_id == "m"
    assert exp.model_revision == "v1"
    assert exp.role is EmbeddingRole.QUERY


# ===========================================================================
# 2. Unknown compatibility-critical field fails closed
# ===========================================================================


def test_unknown_critical_field_fails_closed_when_undeclarable():
    """A critical field that is neither reported nor declarable stays unknown and
    fails closed with a remediation-naming diagnostic."""
    # Profile stub that cannot declare model_revision (model_version None).
    stub = SimpleNamespace(
        model_name="srv-model",
        model_version=None,
        vector_dimension=8,
        normalization_policy="none",
    )
    response = _openai_response(["a"], "document", served_model="srv-model", dimension=8)
    # model_revision is UNKNOWN and the profile can't declare it -> fail closed.
    att = attest_embedding_response(stub, response)

    assert not att.ok
    assert any("model_revision" in f for f in att.failures)
    assert att.remediation
    assert "reindex" in att.failure_reason().lower()


def test_reported_value_mismatch_fails_closed():
    profile = _profile(dim=8, model="srv-model")
    # Provider reports a DIFFERENT served model than the profile expects.
    response = _openai_response(["a"], "document", served_model="rogue-model", dimension=8)
    att = attest_embedding_response(profile, response)
    assert not att.ok
    assert any("served_model_id" in f for f in att.failures)


# ===========================================================================
# 3. One-to-one index validation prevents misattachment
# ===========================================================================


def test_bijection_rejects_scrambled_response(tmp_path):
    scrambled = _items([[1.0] * 8, [2.0] * 8])
    scrambled[0].index, scrambled[1].index = 1, 0  # reordered

    def factory(texts, input_type):
        return _openai_response(texts, input_type, dimension=8, items=scrambled)

    ix = _make_indexer(tmp_path, _FakeProvenanceProvider(factory))
    with pytest.raises(RuntimeError, match="one-to-one"):
        ix._embed_texts(["a", "b"], input_type="document")


def test_bijection_rejects_duplicate_index(tmp_path):
    dup = _items([[1.0] * 8, [2.0] * 8])
    dup[1].index = 0  # duplicate index 0

    def factory(texts, input_type):
        return _openai_response(texts, input_type, dimension=8, items=dup)

    ix = _make_indexer(tmp_path, _FakeProvenanceProvider(factory))
    with pytest.raises(RuntimeError, match="one-to-one"):
        ix._embed_texts(["a", "b"], input_type="document")


def test_bijection_rejects_short_response(tmp_path):
    def factory(texts, input_type):
        # Return only ONE item for a two-text request.
        return _openai_response(texts[:1], input_type, dimension=8)

    ix = _make_indexer(tmp_path, _FakeProvenanceProvider(factory))
    with pytest.raises(RuntimeError, match="arity mismatch"):
        ix._embed_texts(["a", "b"], input_type="document")


def test_bijection_rejects_wrong_dimension(tmp_path):
    def factory(texts, input_type):
        return _openai_response(texts, input_type, dimension=16)  # index expects 8

    ix = _make_indexer(tmp_path, _FakeProvenanceProvider(factory), dim=8)
    with pytest.raises(RuntimeError, match="dimension"):
        ix._embed_texts(["a", "b"], input_type="document")


def test_valid_response_returns_ordered_vectors(tmp_path):
    ix = _make_indexer(tmp_path, _FakeProvenanceProvider(_openai_response))
    vectors = ix._embed_texts(["a", "b", "c"], input_type="document")
    assert len(vectors) == 3
    assert all(len(v) == 8 for v in vectors)


# ===========================================================================
# 4. Lifecycle ordering: attest -> persist -> ensure_collection
# ===========================================================================


def test_prepare_for_writes_attests_persists_then_ensures(tmp_path):
    ix = _make_indexer(tmp_path, _FakeProvenanceProvider(_openai_response))
    ix._prepare_for_writes()

    # Collection was created only after a successful attestation + persist.
    assert ("create", "semantic-oss-high") in ix.qdrant.calls
    persisted = json.loads((tmp_path / ".index_metadata.json").read_text())
    assert persisted["semantic_attestation"]["ok"] is True
    profile_record = persisted["semantic_profiles"]["oss-high"]
    assert profile_record["attested"] is True
    assert profile_record["provenance"]["dimension"]["source"] == "reported"
    assert ix._writes_prepared is True


def test_no_mutation_on_provider_failure(tmp_path):
    provider = _FailingProvider()
    ix = _make_indexer(tmp_path, provider)

    with pytest.raises(RuntimeError, match="unreachable"):
        ix._prepare_for_writes()

    # Provider failed FIRST: zero collection state and zero metadata written.
    assert provider.calls == 1
    assert ix.qdrant.calls == []
    assert ix.qdrant.upserts == []
    assert not (tmp_path / ".index_metadata.json").exists()
    assert ix._writes_prepared is False


def test_no_mutation_on_metadata_write_failure(tmp_path):
    ix = _make_indexer(tmp_path, _FakeProvenanceProvider(_openai_response))
    # Point the metadata file at a non-existent directory so the atomic write
    # (temp file open) fails after a successful attestation.
    ix.metadata_file = str(tmp_path / "missing-dir" / ".index_metadata.json")

    with pytest.raises(Exception):
        ix._prepare_for_writes()

    # The metadata write failed BEFORE ensure_collection: no collection mutated.
    assert ix.qdrant.calls == []
    assert not (tmp_path / "missing-dir").exists()
    assert ix._writes_prepared is False


def test_index_time_fails_closed_on_mismatch_without_writes(tmp_path):
    def factory(texts, input_type):
        return _openai_response(texts, input_type, served_model="rogue-model", dimension=8)

    ix = _make_indexer(tmp_path, _FakeProvenanceProvider(factory))
    with pytest.raises(RuntimeError) as excinfo:
        ix._prepare_for_writes()

    assert "reindex" in str(excinfo.value).lower()
    assert ix.qdrant.calls == []  # no collection created under an unverified profile
    assert not (tmp_path / ".index_metadata.json").exists()


def test_prepare_for_writes_is_idempotent(tmp_path):
    provider = _FakeProvenanceProvider(_openai_response)
    ix = _make_indexer(tmp_path, provider)
    ix._prepare_for_writes()
    ix._prepare_for_writes()
    # Attestation probe embed ran once; the second call short-circuits.
    assert len(provider.calls) == 1


# ===========================================================================
# 5. Query-time provenance / fingerprint fails closed on mismatch
# ===========================================================================


def test_query_provenance_fails_closed_on_reported_mismatch(tmp_path):
    ix = _make_indexer(tmp_path, _FakeProvenanceProvider(_openai_response))
    # A query response whose reported served model drifted from the profile.
    drifted = _openai_response(["q"], "query", served_model="rogue-model", dimension=8)
    with pytest.raises(RuntimeError) as excinfo:
        ix._check_query_provenance(drifted)
    assert "reindex" in str(excinfo.value).lower()


def test_query_provenance_fails_closed_on_dimension_drift_vs_index(tmp_path):
    # Index was built (and persisted) at dimension 8.
    ix = _make_indexer(tmp_path, _FakeProvenanceProvider(_openai_response), dim=8)
    ix._prepare_for_writes()

    # Now the query model reports a 16-d vector while sharing the (retagged)
    # profile: reconstruct an indexer whose profile is 16-d but whose PERSISTED
    # index record still says 8-d -> record-drift branch must fail closed.
    ix16 = _make_indexer(
        tmp_path, _FakeProvenanceProvider(lambda t, it: _openai_response(t, it, dimension=16)), dim=16
    )
    ix16.metadata_file = ix.metadata_file  # same persisted 8-d record
    query_resp = _openai_response(["q"], "query", dimension=16)
    with pytest.raises(RuntimeError, match="incompatible"):
        ix16._check_query_provenance(query_resp)


def test_query_provenance_passes_when_compatible(tmp_path):
    ix = _make_indexer(tmp_path, _FakeProvenanceProvider(_openai_response), dim=8)
    ix._prepare_for_writes()
    ok_resp = _openai_response(["q"], "query", dimension=8)
    # Compatible query provenance does not raise.
    ix._check_query_provenance(ok_resp)


# ===========================================================================
# 6. Reconciliation path for pre-provenance collections
# ===========================================================================


def test_reconcile_compatible_marks_attested(tmp_path):
    ix = _make_indexer(tmp_path, _FakeProvenanceProvider(_openai_response), dim=8)
    result = ix.reconcile_existing_collection()
    assert result["status"] == "reconciled"
    persisted = json.loads((tmp_path / ".index_metadata.json").read_text())
    assert persisted["semantic_attestation"]["ok"] is True


def test_reconcile_incompatible_names_remediation_without_mutation(tmp_path):
    def factory(texts, input_type):
        # v9 pilot drift: endpoint now serves a different model.
        return _openai_response(texts, input_type, served_model="rogue-model", dimension=8)

    ix = _make_indexer(tmp_path, _FakeProvenanceProvider(factory))
    result = ix.reconcile_existing_collection()

    assert result["status"] == "reindex_required"
    assert REINDEX_REMEDIATION in result["message"]
    assert "reindex" in result["message"].lower()
    # No destructive recreation without operator authorization.
    assert all(kind != "recreate" for kind, _ in ix.qdrant.calls)


def test_reconcile_allow_reindex_recreates(tmp_path):
    def factory(texts, input_type):
        return _openai_response(texts, input_type, served_model="rogue-model", dimension=8)

    ix = _make_indexer(tmp_path, _FakeProvenanceProvider(factory))
    # Pre-existing mismatched collection so ensure(allow_recreate) must recreate.
    ix.qdrant.collections["semantic-oss-high"] = (
        4096,
        SemanticIndexer.resolve_qdrant_distance("cosine"),
    )
    result = ix.reconcile_existing_collection(allow_reindex=True)
    assert result["status"] == "reindexed"
    assert ("recreate", "semantic-oss-high") in ix.qdrant.calls


def test_reconcile_unattestable_for_legacy_provider(tmp_path):
    class _Legacy:
        provider_name = "voyage"

        def embed(self, texts, input_type="document"):
            return [[0.0] * 8 for _ in texts]

    ix = _make_indexer(tmp_path, _Legacy())
    result = ix.reconcile_existing_collection()
    assert result["status"] == "unattestable"
    assert "reindex" in result["message"].lower()
