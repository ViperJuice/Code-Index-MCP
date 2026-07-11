"""Tests for the ``rerank.v1`` wire contract (IF-0-INFERFREEZE-2).

Covers round-trip serialization, order-independent candidate-ID validation, the
three rejection cases (missing / duplicated / unknown ids), representable
per-candidate partial failure, and confirmation that the INFERSAFE
``RerankOutcome`` enum is reused rather than redefined.
"""

import pytest

from mcp_server.indexer.reranker import RerankOutcome
from mcp_server.interfaces.rerank_contracts import (
    RERANK_CONTRACT_VERSION,
    RerankCandidate,
    RerankContractError,
    RerankRequest,
    RerankResponse,
    RerankResult,
    validate_rerank_response,
)


def _make_request() -> RerankRequest:
    return RerankRequest(
        request_id="req-1",
        query="how to parse json",
        candidates=[
            RerankCandidate(candidate_id="a", text="json.loads parses a string"),
            RerankCandidate(candidate_id="b", text="unrelated text"),
            RerankCandidate(candidate_id="c", text="json.dumps serializes"),
        ],
        top_k=2,
    )


def _make_response(request: RerankRequest, *, reorder=False) -> RerankResponse:
    results = [
        RerankResult(candidate_id="a", status=RerankOutcome.SUCCEEDED, score=0.91),
        RerankResult(candidate_id="b", status=RerankOutcome.SUCCEEDED, score=0.10),
        RerankResult(candidate_id="c", status=RerankOutcome.SUCCEEDED, score=0.77),
    ]
    if reorder:
        results = [results[2], results[0], results[1]]  # c, a, b
    return RerankResponse(
        request_id=request.request_id,
        provider="test-provider",
        model_id="rerank-test",
        model_revision="2026-07-01",
        results=results,
        candidate_count=3,
        scored_count=3,
        latency_ms=12.5,
    )


def test_reused_rerank_outcome_import():
    """The status vocabulary reuses the INFERSAFE enum (not a parallel one)."""
    result = RerankResult(candidate_id="a", status=RerankOutcome.SUCCEEDED, score=1.0)
    assert result.status is RerankOutcome.SUCCEEDED
    # Sanity: the shared enum carries the frozen INFERSAFE states.
    assert RerankOutcome.FAILED.value == "failed"
    assert {m.value for m in RerankOutcome} >= {
        "not_configured",
        "attempted",
        "succeeded",
        "failed",
        "fallback_applied",
        "skipped_policy",
    }


def test_request_round_trip():
    request = _make_request()
    restored = RerankRequest.from_dict(request.to_dict())
    assert restored == request
    assert restored.contract_version == RERANK_CONTRACT_VERSION
    assert restored.top_k == 2
    assert restored.candidate_ids == ["a", "b", "c"]


def test_response_round_trip_preserves_enum_status():
    request = _make_request()
    response = _make_response(request)
    restored = RerankResponse.from_dict(response.to_dict())
    assert restored == response
    assert restored.contract_version == RERANK_CONTRACT_VERSION
    # status must be rebuilt into the enum, not left a bare string.
    assert restored.results[0].status is RerankOutcome.SUCCEEDED
    assert all(isinstance(r.status, RerankOutcome) for r in restored.results)


def test_json_serializable():
    import json

    request = _make_request()
    response = _make_response(request)
    # Must survive an actual JSON encode/decode round-trip over a wire.
    req2 = RerankRequest.from_dict(json.loads(json.dumps(request.to_dict())))
    resp2 = RerankResponse.from_dict(json.loads(json.dumps(response.to_dict())))
    assert req2 == request
    assert resp2 == response


def test_validation_passes_in_order():
    request = _make_request()
    response = _make_response(request)
    # Does not raise.
    validate_rerank_response(request, response)


def test_validation_passes_when_reordered():
    request = _make_request()
    response = _make_response(request, reorder=True)
    assert response.result_ids == ["c", "a", "b"]  # different order than request
    # Set-based, order-independent: does not raise.
    validate_rerank_response(request, response)


def test_validation_fails_on_missing_candidate_id():
    request = _make_request()
    response = _make_response(request)
    response.results = [r for r in response.results if r.candidate_id != "b"]
    with pytest.raises(RerankContractError, match="missing"):
        validate_rerank_response(request, response)


def test_validation_fails_on_duplicated_candidate_id():
    request = _make_request()
    response = _make_response(request)
    # Duplicate a candidate id that IS validly requested -> must still fail.
    response.results.append(
        RerankResult(candidate_id="a", status=RerankOutcome.SUCCEEDED, score=0.5)
    )
    assert set(response.result_ids) == set(request.candidate_ids)  # sets are equal
    with pytest.raises(RerankContractError, match="duplicated"):
        validate_rerank_response(request, response)


def test_validation_fails_on_unknown_candidate_id():
    request = _make_request()
    response = _make_response(request)
    response.results.append(
        RerankResult(candidate_id="z", status=RerankOutcome.SUCCEEDED, score=0.5)
    )
    with pytest.raises(RerankContractError, match="unknown"):
        validate_rerank_response(request, response)


def test_partial_failure_representable():
    request = _make_request()
    response = RerankResponse(
        request_id=request.request_id,
        provider="test-provider",
        model_id="rerank-test",
        model_revision="2026-07-01",
        results=[
            RerankResult(candidate_id="a", status=RerankOutcome.SUCCEEDED, score=0.9),
            RerankResult(candidate_id="b", status=RerankOutcome.FAILED, score=None),
            RerankResult(candidate_id="c", status=RerankOutcome.SUCCEEDED, score=0.6),
        ],
        candidate_count=3,
        scored_count=2,
        latency_ms=9.0,
    )
    # A per-candidate mix of succeeded/failed is valid; ids still cover the set.
    validate_rerank_response(request, response)
    statuses = {r.candidate_id: r.status for r in response.results}
    assert statuses["a"] is RerankOutcome.SUCCEEDED
    assert statuses["b"] is RerankOutcome.FAILED
    assert response.results[1].score is None
    # Partial failure survives serialization.
    restored = RerankResponse.from_dict(response.to_dict())
    assert restored.results[1].status is RerankOutcome.FAILED


def test_validation_fails_on_request_id_mismatch():
    request = _make_request()
    response = _make_response(request)
    response.request_id = "other-req"
    with pytest.raises(RerankContractError, match="request_id"):
        validate_rerank_response(request, response)
