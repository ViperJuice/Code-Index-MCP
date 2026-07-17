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
    """Mimics an OpenAI embeddings response item: ``.embedding`` + server ``.index``.

    ``index`` may be omitted (``_MISSING``) to simulate a server item that does
    not carry an index at all.
    """

    _MISSING = object()

    def __init__(self, embedding: List[float], index=_MISSING) -> None:
        self.embedding = embedding
        if index is not _FakeEmbeddingItem._MISSING:
            self.index = index


class _FakeOpenAIResponse:
    def __init__(self, data, model: str) -> None:
        self.data = data
        self.model = model


class _FakeOpenAIEmbeddings:
    """Fake ``client.embeddings`` whose per-item vectors are position-tagged.

    Each returned vector encodes the request position it belongs to (its first
    component is ``float(position)``), so a test can prove that the vector for
    request position *p* actually lands at output position *p* regardless of the
    order the items are returned in.

    ``index_override`` lets a test scramble/duplicate/omit/blow out the
    server-assigned indices independently of the vectors' true positions.
    """

    def __init__(self, dimension: int, served_model: str, index_override=None) -> None:
        self.dimension = dimension
        self.served_model = served_model
        self.index_override = index_override
        self.last_kwargs = None

    def _vector_for(self, position: int) -> List[float]:
        # First component is the true request position; rest pads to dimension.
        return [float(position)] + [0.0] * (self.dimension - 1)

    def create(self, model, input):
        self.last_kwargs = {"model": model, "input": input}
        n = len(input)
        if self.index_override is not None:
            pairs = self.index_override(n)  # list of (server_index, true_position)
        else:
            pairs = [(pos, pos) for pos in range(n)]
        data = [
            _FakeEmbeddingItem(self._vector_for(true_pos), index=server_index)
            for server_index, true_pos in pairs
        ]
        return _FakeOpenAIResponse(data=data, model=self.served_model)


class _FakeOpenAIClient:
    def __init__(self, dimension: int, served_model: str, index_override=None) -> None:
        self.embeddings = _FakeOpenAIEmbeddings(dimension, served_model, index_override)


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


def _make_openai(
    model_name="qwen-embed",
    dimension=4,
    served_model="srv-qwen-embed",
    normalization=None,
    index_override=None,
):
    p = OpenAICompatibleEmbeddingProvider.__new__(OpenAICompatibleEmbeddingProvider)
    p.client = _FakeOpenAIClient(dimension, served_model, index_override)
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
    # Role is declared (config/local), NOT server-reported: input_type never
    # reaches the /v1/embeddings endpoint. Value is still preserved.
    assert resp.role.authority is ProvenanceAuthority.DECLARED
    assert resp.role.value == "query"

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
    # Role is not server-reported for the OpenAI-compatible provider.
    assert cap.can_report("role") is False
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


# ---------------------------------------------------------------------------
# 5. Server ``index`` is honored, not fabricated (bijection is real)
# ---------------------------------------------------------------------------
#
# Each fake vector's first component is the *true* request position it answers
# (see ``_FakeOpenAIEmbeddings._vector_for``). So ``resp.items[p].vector[0]``
# proves which request the vector at output position ``p`` actually belongs to.
_MISSING_INDEX = _FakeEmbeddingItem._MISSING


def _reversed_but_correctly_indexed(n):
    """response.data returned in reverse order, each item keeping its TRUE server index.

    A provider that trusts enumeration order (the old bug) would misattach every
    vector; a provider that honors the server ``index`` reconstructs request order.
    """
    return [(pos, pos) for pos in reversed(range(n))]


def test_openai_reordered_response_maps_vectors_to_correct_positions():
    p = _make_openai(dimension=4, index_override=_reversed_but_correctly_indexed)
    resp = p.embed_with_provenance(["a", "b", "c"], input_type="document")

    # Output is in request order and each vector lands on its own request.
    assert [item.index for item in resp.items] == [0, 1, 2]
    for pos, item in enumerate(resp.items):
        assert item.vector[0] == float(pos), (
            f"vector at output position {pos} belongs to request "
            f"{item.vector[0]} -- silent misattachment"
        )
    # Downstream _validate_embedding_response contract: item.index == position.
    assert all(item.index == pos for pos, item in enumerate(resp.items))


def test_openai_missing_server_index_raises():
    def _one_missing(n):
        pairs = [(pos, pos) for pos in range(n)]
        pairs[1] = (_MISSING_INDEX, 1)  # second item carries no ``index`` at all
        return pairs

    p = _make_openai(dimension=4, index_override=_one_missing)
    with pytest.raises(RuntimeError, match="index"):
        p.embed_with_provenance(["a", "b", "c"], input_type="document")


def test_openai_duplicate_server_index_raises():
    def _duplicate(n):
        # indices [0, 0, 2] -> right arity, but 1 is missing and 0 duplicated.
        return [(0, 0), (0, 1), (2, 2)]

    p = _make_openai(dimension=4, index_override=_duplicate)
    with pytest.raises(RuntimeError, match="duplicate"):
        p.embed_with_provenance(["a", "b", "c"], input_type="document")


def test_openai_out_of_range_server_index_raises():
    def _out_of_range(n):
        # index 5 for a 2-input request is out of [0, 2).
        return [(0, 0), (5, 1)]

    p = _make_openai(dimension=4, index_override=_out_of_range)
    with pytest.raises(RuntimeError, match="out of range"):
        p.embed_with_provenance(["a", "b"], input_type="document")


def test_openai_arity_mismatch_raises():
    def _short(n):
        # Return one fewer item than requested.
        return [(pos, pos) for pos in range(n - 1)]

    p = _make_openai(dimension=4, index_override=_short)
    with pytest.raises(RuntimeError, match="arity mismatch"):
        p.embed_with_provenance(["a", "b", "c"], input_type="document")


class _FixedCountVoyageClient:
    """Voyage double returning a FIXED number of embeddings, ignoring input size.

    Simulates a provider that answers with too few / too many vectors than the
    request carried — the only failure Voyage's bare ``embeddings`` list exposes.
    """

    def __init__(self, dimension: int, returned_count: int) -> None:
        self.dimension = dimension
        self.returned_count = returned_count

    def embed(self, texts, model, input_type, output_dimension, output_dtype):
        embeddings = [[float(i)] * self.dimension for i in range(self.returned_count)]
        return _FakeVoyageResponse(embeddings)


def test_voyage_arity_mismatch_too_few_raises():
    p = _make_voyage(dimension=4)
    p.client = _FixedCountVoyageClient(dimension=4, returned_count=2)
    # Requested 3 inputs but the client returns only 2 embeddings.
    with pytest.raises(RuntimeError, match="arity mismatch"):
        p.embed_with_provenance(["a", "b", "c"], input_type="document")


def test_voyage_arity_mismatch_too_many_raises():
    p = _make_voyage(dimension=4)
    p.client = _FixedCountVoyageClient(dimension=4, returned_count=3)
    # Requested 2 inputs but the client returns 3 embeddings.
    with pytest.raises(RuntimeError, match="arity mismatch"):
        p.embed_with_provenance(["a", "b"], input_type="document")


def test_voyage_matching_arity_still_ok():
    """The added arity guard must not reject a correct one-to-one response."""
    p = _make_voyage(dimension=4)
    resp = p.embed_with_provenance(["a", "b", "c"], input_type="document")
    assert [item.index for item in resp.items] == [0, 1, 2]


# ---------------------------------------------------------------------------
# 6. OpenAI role authority is ``declared`` (not ``reported``), value preserved
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("input_type,expected", [("query", "query"), ("document", "document")])
def test_openai_role_authority_is_declared_value_preserved(input_type, expected):
    p = _make_openai()
    resp = p.embed_with_provenance(["x"], input_type=input_type)

    # Authority is declared -- the endpoint never saw the role.
    assert resp.role.authority is ProvenanceAuthority.DECLARED
    # Value is still carried end to end.
    assert resp.role.value == expected
    assert resp.role.value == EmbeddingRole(expected).value
    # input_type was recorded locally, never sent to the endpoint.
    assert p.last_input_type == input_type
    assert "input_type" not in p.client.embeddings.last_kwargs


def test_openai_capability_says_role_not_reported():
    cap = _make_openai().capability()
    assert cap.can_report("role") is False
    assert cap.supports_role(EmbeddingRole.QUERY)
    assert cap.supports_role(EmbeddingRole.DOCUMENT)
