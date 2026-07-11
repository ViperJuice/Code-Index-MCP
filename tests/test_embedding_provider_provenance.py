"""EMBEDPROV lane E1: provider provenance emission (IF-0-EMBEDPROV-1).

Verifies that ``VoyageEmbeddingProvider`` and ``OpenAICompatibleEmbeddingProvider``
emit a valid ``embedding-response.v1`` with the correct per-field provenance
authority, preserve ``input_type``/role end to end, declare their capability
consistently with what they emit, and keep the bare-vector ``embed()`` shim
working.

No live network: the SDK clients are replaced with deterministic fakes and the
providers are built via ``__new__`` so no real ``voyageai.Client`` /
``openai.OpenAI`` is constructed.
"""

from __future__ import annotations

from typing import List

import pytest

from mcp_server.interfaces.inference_contracts import (
    CONTRACT_VERSION,
    EmbeddingItemStatus,
    EmbeddingResponseV1,
    EmbeddingRole,
    ProvenanceAuthority,
)
from mcp_server.utils.embedding_providers import (
    OpenAICompatibleEmbeddingProvider,
    VoyageEmbeddingProvider,
)


# ---------------------------------------------------------------------------
# Deterministic fakes (no network, no SDK import)
# ---------------------------------------------------------------------------


class _FakeVoyageResponse:
    def __init__(self, embeddings: List[List[float]]) -> None:
        self.embeddings = embeddings


class _FakeVoyageClient:
    """Mimics ``voyageai.Client``: ``.embed(...) -> obj.embeddings``."""

    def __init__(self, dimension: int) -> None:
        self.dimension = dimension
        self.last_kwargs = None

    def embed(self, texts, model, input_type, output_dimension, output_dtype):
        self.last_kwargs = {
            "model": model,
            "input_type": input_type,
            "output_dimension": output_dimension,
            "output_dtype": output_dtype,
        }
        embeddings = [[float(i)] * self.dimension for i, _ in enumerate(texts)]
        return _FakeVoyageResponse(embeddings)


class _FakeEmbeddingItem:
    def __init__(self, embedding: List[float]) -> None:
        self.embedding = embedding


class _FakeOpenAIResponse:
    def __init__(self, data, model: str) -> None:
        self.data = data
        self.model = model


class _FakeOpenAIEmbeddings:
    def __init__(self, dimension: int, served_model: str) -> None:
        self.dimension = dimension
        self.served_model = served_model
        self.last_kwargs = None

    def create(self, model, input):
        self.last_kwargs = {"model": model, "input": input}
        data = [_FakeEmbeddingItem([float(i)] * self.dimension) for i, _ in enumerate(input)]
        return _FakeOpenAIResponse(data=data, model=self.served_model)


class _FakeOpenAIClient:
    def __init__(self, dimension: int, served_model: str) -> None:
        self.embeddings = _FakeOpenAIEmbeddings(dimension, served_model)


# ---------------------------------------------------------------------------
# Builders that bypass the SDK-constructing __init__
# ---------------------------------------------------------------------------


def _make_voyage(model_name="voyage-3", dimension=4, normalization=None):
    p = VoyageEmbeddingProvider.__new__(VoyageEmbeddingProvider)
    p.client = _FakeVoyageClient(dimension)
    p.model_name = model_name
    p.vector_dimension = dimension
    p.normalization = normalization
    return p


def _make_openai(model_name="qwen-embed", dimension=4, served_model="srv-qwen-embed", normalization=None):
    p = OpenAICompatibleEmbeddingProvider.__new__(OpenAICompatibleEmbeddingProvider)
    p.client = _FakeOpenAIClient(dimension, served_model)
    p.model_name = model_name
    p.vector_dimension = dimension
    p.normalization = normalization
    p.last_input_type = None
    return p


# ---------------------------------------------------------------------------
# 1. Valid embedding-response.v1 + per-field authority
# ---------------------------------------------------------------------------


def test_voyage_emits_valid_response_with_correct_authority():
    p = _make_voyage(model_name="voyage-3", dimension=4, normalization="l2")
    resp = p.embed_with_provenance(["a", "b"], input_type="document")

    assert isinstance(resp, EmbeddingResponseV1)
    assert resp.contract_version == CONTRACT_VERSION
    assert resp.provider == "voyage"
    assert resp.latency_ms is not None and resp.latency_ms >= 0.0

    # Per-field authority (Voyage mapping).
    assert resp.served_model_id.authority is ProvenanceAuthority.DECLARED
    assert resp.served_model_id.value == "voyage-3"
    assert resp.model_revision.authority is ProvenanceAuthority.UNKNOWN
    assert resp.dimension.authority is ProvenanceAuthority.REPORTED
    assert resp.dimension.value == 4
    assert resp.normalization.authority is ProvenanceAuthority.DECLARED
    assert resp.normalization.value == "l2"
    assert resp.role.authority is ProvenanceAuthority.REPORTED

    # Per-item fields filled.
    assert len(resp.items) == 2
    for idx, item in enumerate(resp.items):
        assert item.index == idx
        assert item.status is EmbeddingItemStatus.OK
        assert item.error is None
        assert len(item.vector) == 4


def test_voyage_normalization_unknown_when_unconfigured():
    p = _make_voyage(normalization=None)
    resp = p.embed_with_provenance(["a"], input_type="document")
    assert resp.normalization.authority is ProvenanceAuthority.UNKNOWN


def test_openai_emits_valid_response_with_correct_authority():
    p = _make_openai(model_name="qwen-embed", dimension=4, served_model="srv-qwen-embed", normalization="l2")
    resp = p.embed_with_provenance(["a", "b", "c"], input_type="query")

    assert isinstance(resp, EmbeddingResponseV1)
    assert resp.provider == "openai_compatible"
    assert resp.latency_ms is not None and resp.latency_ms >= 0.0

    # served_model_id is server-reported (from response.model), not the config name.
    assert resp.served_model_id.authority is ProvenanceAuthority.REPORTED
    assert resp.served_model_id.value == "srv-qwen-embed"
    assert resp.model_revision.authority is ProvenanceAuthority.UNKNOWN
    assert resp.dimension.authority is ProvenanceAuthority.REPORTED
    assert resp.dimension.value == 4
    assert resp.normalization.authority is ProvenanceAuthority.DECLARED
    assert resp.normalization.value == "l2"
    assert resp.role.authority is ProvenanceAuthority.REPORTED

    assert len(resp.items) == 3
    for idx, item in enumerate(resp.items):
        assert item.index == idx
        assert item.status is EmbeddingItemStatus.OK
        assert len(item.vector) == 4


def test_openai_normalization_unknown_when_unconfigured():
    p = _make_openai(normalization=None)
    resp = p.embed_with_provenance(["a"], input_type="document")
    assert resp.normalization.authority is ProvenanceAuthority.UNKNOWN


# ---------------------------------------------------------------------------
# 2. Role / input_type preserved end to end (query vs document)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("input_type,expected", [("query", "query"), ("document", "document")])
def test_voyage_preserves_role(input_type, expected):
    p = _make_voyage()
    resp = p.embed_with_provenance(["x"], input_type=input_type)
    assert resp.role.value == expected
    assert resp.role.value == EmbeddingRole(expected).value
    # And the role reached the underlying API call.
    assert p.client.last_kwargs["input_type"] == input_type


@pytest.mark.parametrize("input_type,expected", [("query", "query"), ("document", "document")])
def test_openai_preserves_role(input_type, expected):
    p = _make_openai()
    resp = p.embed_with_provenance(["x"], input_type=input_type)
    assert resp.role.value == expected
    # input_type is used (recorded), not discarded.
    assert p.last_input_type == input_type


def test_unknown_input_type_defaults_to_document():
    p = _make_voyage()
    resp = p.embed_with_provenance(["x"], input_type="something-else")
    assert resp.role.value == EmbeddingRole.DOCUMENT.value


# ---------------------------------------------------------------------------
# 3. capability() declares roles + reportable fields consistently
# ---------------------------------------------------------------------------


def test_voyage_capability():
    cap = _make_voyage().capability()
    assert cap.provider == "voyage"
    assert cap.supports_role(EmbeddingRole.QUERY)
    assert cap.supports_role(EmbeddingRole.DOCUMENT)
    assert cap.can_report("dimension") is True
    assert cap.can_report("role") is True
    assert cap.can_report("served_model_id") is False
    assert cap.can_report("model_revision") is False
    assert cap.can_report("normalization") is False
    assert cap.can_report("processor_id") is False


def test_openai_capability():
    cap = _make_openai().capability()
    assert cap.provider == "openai_compatible"
    assert cap.supports_role(EmbeddingRole.QUERY)
    assert cap.supports_role(EmbeddingRole.DOCUMENT)
    assert cap.can_report("served_model_id") is True
    assert cap.can_report("dimension") is True
    assert cap.can_report("role") is True
    assert cap.can_report("model_revision") is False
    assert cap.can_report("normalization") is False
    assert cap.can_report("processor_id") is False


@pytest.mark.parametrize("make", [_make_voyage, _make_openai])
def test_capability_matches_emitted_reported_fields(make):
    """A field the capability says is reportable must actually come back REPORTED
    (with config that lets it), and a non-reportable field must NOT be REPORTED."""
    p = make(normalization="l2")
    cap = p.capability()
    resp = p.embed_with_provenance(["a"], input_type="query")

    field_to_pf = {
        "served_model_id": resp.served_model_id,
        "model_revision": resp.model_revision,
        "dimension": resp.dimension,
        "normalization": resp.normalization,
        "role": resp.role,
        "processor_id": resp.processor_id,
    }
    for name, pf in field_to_pf.items():
        if cap.can_report(name):
            assert pf.authority is ProvenanceAuthority.REPORTED, name
        else:
            assert pf.authority is not ProvenanceAuthority.REPORTED, name


# ---------------------------------------------------------------------------
# 4. Back-compat: embed() still returns List[List[float]] of the right shape
# ---------------------------------------------------------------------------


def test_voyage_embed_backcompat_shape():
    p = _make_voyage(dimension=4)
    vectors = p.embed(["a", "b"], input_type="document")
    assert isinstance(vectors, list)
    assert len(vectors) == 2
    assert all(isinstance(v, list) and len(v) == 4 for v in vectors)
    assert all(isinstance(x, float) for v in vectors for x in v)


def test_openai_embed_backcompat_shape():
    p = _make_openai(dimension=4)
    vectors = p.embed(["a", "b", "c"], input_type="query")
    assert isinstance(vectors, list)
    assert len(vectors) == 3
    assert all(isinstance(v, list) and len(v) == 4 for v in vectors)


def test_openai_embed_backcompat_raises_on_dimension_mismatch():
    """Existing embed() behavior: dimension mismatch fails closed."""
    p = _make_openai(dimension=4)
    p.vector_dimension = 8  # served vectors are len 4, expectation is 8
    with pytest.raises(RuntimeError, match="dimension mismatch"):
        p.embed(["a"], input_type="document")
