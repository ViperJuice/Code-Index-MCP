"""Tests for the additive INFERFREEZE embedding contract + provenance validation.

Covers IF-0-INFERFREEZE-1 (embedding-response.v1) and IF-0-INFERFREEZE-3
(per-field provenance authority, provider capability, fail-closed validation,
and the compat shim that wraps a bare-vector provider without changing it).
"""

from __future__ import annotations

import json
from typing import List

import pytest

from mcp_server.interfaces.inference_contracts import (
    AI_STACK_REPORTED_FIELDS,
    COMPATIBILITY_CRITICAL_FIELDS,
    CONTRACT_VERSION,
    EmbeddingItem,
    EmbeddingItemStatus,
    EmbeddingResponseV1,
    EmbeddingRole,
    ExpectedProfile,
    ProviderCapability,
    ProvenanceAuthority,
    ProvenanceField,
    embed_with_provenance,
    validate_profile,
)


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeBareProvider:
    """Mimics the existing providers: bare vectors, no provenance emission.

    Exposes exactly the attributes the real providers expose today
    (``provider_name``, ``model_name``, ``vector_dimension``, ``embed``) so the
    shim's duck-typing is exercised against a realistic shape.
    """

    def __init__(self, model_name: str = "fake-embed-1", vector_dimension: int = 4) -> None:
        self.model_name = model_name
        self.vector_dimension = vector_dimension
        self.last_input_type = None

    @property
    def provider_name(self) -> str:
        return "fake"

    def embed(self, texts: List[str], input_type: str = "document") -> List[List[float]]:
        self.last_input_type = input_type
        return [[float(i)] * self.vector_dimension for i, _ in enumerate(texts)]


def _reported_response(dimension: int = 4, model_id: str = "srv-model-1") -> EmbeddingResponseV1:
    """A response where every compatibility-critical field is server-reported."""
    return EmbeddingResponseV1(
        provider="ai-stack",
        served_model_id=ProvenanceField.reported(model_id),
        model_revision=ProvenanceField.reported("rev-abc"),
        dimension=ProvenanceField.reported(dimension),
        normalization=ProvenanceField.reported("l2"),
        role=ProvenanceField.reported(EmbeddingRole.QUERY.value),
        processor_id=ProvenanceField.reported("proc-1"),
    )


# ---------------------------------------------------------------------------
# 1. Round-trip / serialization
# ---------------------------------------------------------------------------


def test_embedding_response_v1_json_round_trip():
    resp = _reported_response()
    resp.items.append(
        EmbeddingItem(index=0, status=EmbeddingItemStatus.OK, vector=[0.0, 0.0, 0.0, 0.0])
    )
    resp.latency_ms = 12.5
    resp.route = {"endpoint": "https://ai-stack.local/embed", "attempt": 1}

    d = resp.to_dict()
    # Must be genuinely JSON-serializable, not merely a dict with enum objects.
    text = json.dumps(d)
    reloaded = json.loads(text)

    assert reloaded["contract_version"] == CONTRACT_VERSION == "embedding-response.v1"
    assert reloaded["provider"] == "ai-stack"
    assert reloaded["dimension"] == {"value": 4, "authority": "reported"}
    assert reloaded["role"]["value"] == "query"
    assert reloaded["items"][0]["status"] == "ok"
    assert reloaded["items"][0]["vector"] == [0.0, 0.0, 0.0, 0.0]
    assert reloaded["latency_ms"] == 12.5
    assert reloaded["route"]["endpoint"].endswith("/embed")
    assert reloaded["request_id"]


# ---------------------------------------------------------------------------
# 2. Per-field authority preserved & queryable
# ---------------------------------------------------------------------------


def test_per_field_authority_preserved_and_queryable():
    resp = EmbeddingResponseV1(
        provider="mix",
        served_model_id=ProvenanceField.reported("m1"),
        model_revision=ProvenanceField.declared("r-config"),
        dimension=ProvenanceField.reported(8),
        normalization=ProvenanceField.unknown(),
        role=ProvenanceField.declared(EmbeddingRole.DOCUMENT.value),
        processor_id=ProvenanceField.unknown(),
    )

    assert resp.authority_of("served_model_id") == ProvenanceAuthority.REPORTED
    assert resp.authority_of("model_revision") == ProvenanceAuthority.DECLARED
    assert resp.authority_of("normalization") == ProvenanceAuthority.UNKNOWN
    assert resp.provenance_field("dimension").value == 8

    # Authority survives serialization per field.
    d = resp.to_dict()
    assert d["served_model_id"]["authority"] == "reported"
    assert d["model_revision"]["authority"] == "declared"
    assert d["normalization"]["authority"] == "unknown"

    with pytest.raises(KeyError):
        resp.provenance_field("not_a_field")


# ---------------------------------------------------------------------------
# 3. validate_profile — pass on reported match, fail closed otherwise
# ---------------------------------------------------------------------------


def test_validate_profile_passes_on_matching_reported():
    resp = _reported_response(dimension=4, model_id="srv-model-1")
    expected = ExpectedProfile(
        served_model_id="srv-model-1",
        model_revision="rev-abc",
        dimension=4,
        normalization="l2",
    )
    result = validate_profile(expected, resp)
    assert result.ok is True
    assert result.failures == []
    assert set(result.checked_fields) == set(COMPATIBILITY_CRITICAL_FIELDS)


def test_validate_profile_fails_closed_on_unknown_critical_field():
    resp = _reported_response(dimension=4)
    resp.dimension = ProvenanceField.unknown()  # critical field with unknown authority
    expected = ExpectedProfile(
        served_model_id="srv-model-1",
        model_revision="rev-abc",
        dimension=4,
        normalization="l2",
    )
    result = validate_profile(expected, resp)
    assert result.ok is False
    assert any("dimension" in f and "unknown" in f for f in result.failures)


def test_validate_profile_fails_on_mismatched_critical_field():
    resp = _reported_response(dimension=4, model_id="srv-model-1")
    expected = ExpectedProfile(
        served_model_id="DIFFERENT-model",
        model_revision="rev-abc",
        dimension=4,
        normalization="l2",
    )
    result = validate_profile(expected, resp)
    assert result.ok is False
    assert any("served_model_id" in f for f in result.failures)


def test_validate_profile_declared_matching_passes():
    # A declared (not reported) but matching critical field passes; only
    # unknown/mismatch fails closed.
    resp = _reported_response(dimension=4, model_id="srv-model-1")
    resp.normalization = ProvenanceField.declared("l2")
    expected = ExpectedProfile(
        served_model_id="srv-model-1",
        model_revision="rev-abc",
        dimension=4,
        normalization="l2",
    )
    result = validate_profile(expected, resp)
    assert result.ok is True


# ---------------------------------------------------------------------------
# 4. Compat shim wraps a bare provider without signature change
# ---------------------------------------------------------------------------


def test_shim_wraps_bare_provider_with_correct_authority_tags():
    provider = FakeBareProvider(model_name="fake-embed-1", vector_dimension=4)
    capability = ProviderCapability(
        provider="fake",
        supported_roles=frozenset(EmbeddingRole),
        reportable_fields={f: False for f in AI_STACK_REPORTED_FIELDS},
    )

    resp = embed_with_provenance(
        provider,
        ["alpha", "beta", "gamma"],
        input_type="document",
        capability=capability,
    )

    # Valid, well-formed response.
    assert resp.contract_version == "embedding-response.v1"
    assert resp.provider == "fake"
    assert len(resp.items) == 3
    assert resp.items[1].index == 1
    assert resp.items[1].status == EmbeddingItemStatus.OK
    assert resp.items[2].vector == [2.0, 2.0, 2.0, 2.0]

    # Provider cannot report -> config-derived fields are DECLARED, others UNKNOWN.
    assert resp.authority_of("served_model_id") == ProvenanceAuthority.DECLARED
    assert resp.served_model_id.value == "fake-embed-1"
    assert resp.authority_of("dimension") == ProvenanceAuthority.DECLARED
    assert resp.dimension.value == 4
    assert resp.authority_of("model_revision") == ProvenanceAuthority.UNKNOWN
    assert resp.authority_of("normalization") == ProvenanceAuthority.UNKNOWN
    assert resp.authority_of("processor_id") == ProvenanceAuthority.UNKNOWN

    # Fully JSON-serializable.
    json.dumps(resp.to_dict())

    # Provider signature untouched: still returns bare vectors.
    bare = provider.embed(["x"], "document")
    assert bare == [[0.0, 0.0, 0.0, 0.0]]


def test_shim_does_not_require_provider_subclass():
    # A minimal object with only provider_name + embed still works (pure duck
    # typing, no subclassing of EmbeddingProvider).
    class Minimal:
        provider_name = "minimal"

        def embed(self, texts, input_type="document"):
            return [[1.0, 2.0] for _ in texts]

    resp = embed_with_provenance(Minimal(), ["a"], input_type="query")
    assert resp.provider == "minimal"
    assert resp.items[0].vector == [1.0, 2.0]
    # No config attributes -> served_model_id/dimension are unknown.
    assert resp.authority_of("served_model_id") == ProvenanceAuthority.UNKNOWN
    assert resp.authority_of("dimension") == ProvenanceAuthority.UNKNOWN


def test_shim_can_promote_reported_fields_when_capability_allows():
    provider = FakeBareProvider(vector_dimension=4)
    capability = ProviderCapability(
        provider="fake",
        reportable_fields={"served_model_id": True, "dimension": True},
    )
    resp = embed_with_provenance(
        provider,
        ["a"],
        input_type="document",
        capability=capability,
        reported={"served_model_id": "srv-x", "dimension": 4},
    )
    assert resp.authority_of("served_model_id") == ProvenanceAuthority.REPORTED
    assert resp.served_model_id.value == "srv-x"
    assert resp.authority_of("dimension") == ProvenanceAuthority.REPORTED


# ---------------------------------------------------------------------------
# 5. Role preserved end to end
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("input_type,expected_role", [("query", "query"), ("document", "document")])
def test_role_preserved_end_to_end(input_type, expected_role):
    provider = FakeBareProvider()
    resp = embed_with_provenance(provider, ["t"], input_type=input_type)

    assert resp.role.value == expected_role
    assert provider.last_input_type == input_type
    # Survives serialization.
    assert resp.to_dict()["role"]["value"] == expected_role


def test_provider_capability_role_support_and_serialization():
    cap = ProviderCapability(
        provider="fake",
        supported_roles=frozenset({EmbeddingRole.DOCUMENT}),
        reportable_fields={"dimension": True},
    )
    assert cap.supports_role(EmbeddingRole.DOCUMENT) is True
    assert cap.supports_role(EmbeddingRole.QUERY) is False
    assert cap.can_report("dimension") is True
    assert cap.can_report("served_model_id") is False

    d = cap.to_dict()
    assert d["supported_roles"] == ["document"]
    # Every provenance field is represented in the reportable map.
    assert set(d["reportable_fields"]) == set(AI_STACK_REPORTED_FIELDS)


def test_compatibility_critical_excludes_role():
    assert "role" not in COMPATIBILITY_CRITICAL_FIELDS
    assert set(COMPATIBILITY_CRITICAL_FIELDS) == {
        "dimension",
        "served_model_id",
        "model_revision",
        "normalization",
    }
