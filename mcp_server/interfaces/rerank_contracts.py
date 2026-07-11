"""Versioned wire contract for reranking: ``rerank.v1``.

This is an **additive** interface module (INFERFREEZE Lane 2 /
IF-0-INFERFREEZE-2). It defines a JSON-serializable request/response schema plus
candidate-ID validation so a reranker can be invoked over a wire boundary while
survivin request -> response reordering.

Nothing here changes any existing reranker behavior or signature. The concrete
``EndpointReranker`` and consumer migration are a later phase (RERANKEND).

Per-candidate status vocabulary intentionally **reuses** the INFERSAFE outcome
enum :class:`mcp_server.indexer.reranker.RerankOutcome` rather than defining a
parallel one, so the wire contract and the in-process dispatcher agree on a
single set of states.

Score comparability
-------------------
Scores in a :class:`RerankResponse` are only meaningful **within a single
provider response**. They are NOT comparable across providers or across separate
responses: different providers (and different models/revisions) use different,
unnormalized score scales. This module deliberately exposes **no** helper that
ranks or merges candidates across providers; cross-provider comparability is not
assumed and must not be built on top of these raw scores.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from mcp_server.indexer.reranker import RerankOutcome

#: The frozen contract version string carried by every request and response.
RERANK_CONTRACT_VERSION = "rerank.v1"


class RerankContractError(ValueError):
    """Raised when a rerank request/response violates the ``rerank.v1`` contract.

    Notably raised by :func:`validate_rerank_response` when the response has
    missing, duplicated, or unknown candidate IDs relative to the request.
    """


@dataclass
class RerankCandidate:
    """A single candidate to be reranked.

    ``candidate_id`` is a STABLE, caller-assigned id. It is the only key used to
    correlate a request candidate with its response result, so it must survive
    request -> response reordering.
    """

    candidate_id: str
    text: str

    def to_dict(self) -> Dict[str, Any]:
        return {"candidate_id": self.candidate_id, "text": self.text}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RerankCandidate":
        return cls(candidate_id=data["candidate_id"], text=data["text"])


@dataclass
class RerankRequest:
    """A ``rerank.v1`` request.

    Attributes:
        contract_version: Always :data:`RERANK_CONTRACT_VERSION`.
        request_id: Caller-assigned id correlating request and response.
        query: The query text candidates are reranked against.
        candidates: The candidates to rerank, each with a stable id.
        top_k: How many top results the caller wants. This is a HINT carried on
            the wire; it does NOT truncate the response ``results`` array, which
            must carry one result per requested candidate (see
            :func:`validate_rerank_response`).
    """

    request_id: str
    query: str
    candidates: List[RerankCandidate] = field(default_factory=list)
    top_k: int = 10
    contract_version: str = RERANK_CONTRACT_VERSION

    @property
    def candidate_ids(self) -> List[str]:
        """The ordered list of requested candidate ids (may contain dups if the
        caller built a malformed request; the contract itself is validated on the
        response side)."""
        return [c.candidate_id for c in self.candidates]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "request_id": self.request_id,
            "query": self.query,
            "candidates": [c.to_dict() for c in self.candidates],
            "top_k": self.top_k,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RerankRequest":
        return cls(
            request_id=data["request_id"],
            query=data["query"],
            candidates=[
                RerankCandidate.from_dict(c) for c in data.get("candidates", [])
            ],
            top_k=data.get("top_k", 10),
            contract_version=data.get("contract_version", RERANK_CONTRACT_VERSION),
        )


@dataclass
class RerankResult:
    """A single per-candidate rerank result.

    Attributes:
        candidate_id: The stable id echoed back from the request candidate.
        status: A :class:`RerankOutcome` describing this candidate's outcome
            (e.g. ``SUCCEEDED`` for a scored candidate, ``FAILED`` for one the
            provider could not score). Reused from the INFERSAFE enum.
        score: The relevance score, or ``None`` when not scored (e.g. ``FAILED``).
            Only comparable within THIS response; see the module docstring.
    """

    candidate_id: str
    status: RerankOutcome
    score: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "status": self.status.value,
            "score": self.score,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RerankResult":
        return cls(
            candidate_id=data["candidate_id"],
            status=RerankOutcome(data["status"]),
            score=data.get("score"),
        )


@dataclass
class RerankResponse:
    """A ``rerank.v1`` response.

    ``results`` carries one :class:`RerankResult` per requested candidate (it is
    NOT truncated by ``top_k``), so per-candidate partial failure is
    representable and set-based id validation is well defined. ``results`` may be
    reordered relative to the request; correlation is by ``candidate_id`` only.

    Scores are only comparable within this single response — see the module
    docstring. There is deliberately no cross-provider ranking helper.
    """

    request_id: str
    provider: str
    model_id: str
    model_revision: str
    results: List[RerankResult] = field(default_factory=list)
    candidate_count: int = 0
    scored_count: int = 0
    latency_ms: Optional[float] = None
    contract_version: str = RERANK_CONTRACT_VERSION

    @property
    def result_ids(self) -> List[str]:
        """The ordered list of result candidate ids (may contain duplicates,
        which :func:`validate_rerank_response` rejects)."""
        return [r.candidate_id for r in self.results]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "request_id": self.request_id,
            "provider": self.provider,
            "model_id": self.model_id,
            "model_revision": self.model_revision,
            "results": [r.to_dict() for r in self.results],
            "candidate_count": self.candidate_count,
            "scored_count": self.scored_count,
            "latency_ms": self.latency_ms,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RerankResponse":
        return cls(
            request_id=data["request_id"],
            provider=data["provider"],
            model_id=data["model_id"],
            model_revision=data["model_revision"],
            results=[RerankResult.from_dict(r) for r in data.get("results", [])],
            candidate_count=data.get("candidate_count", 0),
            scored_count=data.get("scored_count", 0),
            latency_ms=data.get("latency_ms"),
            contract_version=data.get("contract_version", RERANK_CONTRACT_VERSION),
        )


def validate_rerank_response(
    request: RerankRequest, response: RerankResponse
) -> None:
    """Validate a ``rerank.v1`` response against its request.

    The response must carry exactly one result per requested candidate, keyed by
    the stable ``candidate_id``. Validation is **set-based and order-independent**
    so candidate IDs may be freely reordered between request and response.

    Raises:
        RerankContractError: if the response has any of:
            * a **missing** candidate id (a requested id absent from results),
            * a **duplicated** candidate id (a result id appearing more than
              once — even if that id is legitimately requested),
            * an **unknown** candidate id (a result id not present in the
              request).

    Note:
        Score values are intentionally not validated for cross-provider
        comparability; that comparability is not assumed by this contract.
    """
    if response.request_id != request.request_id:
        raise RerankContractError(
            f"request_id mismatch: request={request.request_id!r} "
            f"response={response.request_id!r}"
        )

    request_ids = set(request.candidate_ids)
    result_ids_list = response.result_ids
    result_ids = set(result_ids_list)

    # Duplicated: a result id appears more than once. Checked on the raw list so
    # a duplicate of an otherwise-valid requested id is still rejected (set
    # equality alone would miss this).
    if len(result_ids_list) != len(result_ids):
        seen: set = set()
        dups = sorted({rid for rid in result_ids_list if rid in seen or seen.add(rid)})
        raise RerankContractError(
            f"duplicated candidate_id(s) in response: {dups}"
        )

    # Missing: a requested id has no result.
    missing = request_ids - result_ids
    if missing:
        raise RerankContractError(
            f"missing candidate_id(s) in response: {sorted(missing)}"
        )

    # Unknown: a result id was never requested.
    unknown = result_ids - request_ids
    if unknown:
        raise RerankContractError(
            f"unknown candidate_id(s) in response: {sorted(unknown)}"
        )
