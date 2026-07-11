"""Consumer migration tests for RERANKEND lane R2 (IF-0-RERANKEND-1).

Verify that all three rerank consumers drive the canonical async ``IReranker``
correctly and report a truthful structured outcome, using a fake ``rerank.v1``
transport (no network):

* the dispatcher's synchronous path drives an ``EndpointReranker`` end-to-end
  through ``SyncRerankerAdapter`` (via ``EnhancedDispatcher.wrap_endpoint_reranker``);
* ``HybridSearch`` reranks through the canonical interface (and does not assume
  the optional ``initialize`` method the canonical ABC never declared);
* ``CrossRepositoryCoordinator`` reranks through the canonical
  ``rerank(query, results, top_k)`` signature (not the pre-migration
  ``documents=``/index-return shape);
* every consumer's failure path logs no query or document text (egress).
"""

import logging
import types
from typing import Any, Dict

import pytest

from mcp_server.dispatcher.cross_repo_coordinator import (
    CrossRepositoryCoordinator,
    SearchContext,
)
from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.indexer.hybrid_search import HybridSearch
from mcp_server.indexer.hybrid_search import SearchResult as HybridSearchResult
from mcp_server.indexer.reranker import EndpointReranker, RerankOutcome

# Distinctive sentinels that must never reach a log on a failure path.
QUERY_SENTINEL = "zzsecretquery_egress"
DOC_SENTINEL = "zzsecretdoc_egress"


class ReversingTransport:
    """A fake ``rerank.v1`` transport that reverses candidate order.

    It assigns each candidate a score equal to its request index, so the last
    candidate scores highest and ``EndpointReranker`` (descending sort) reverses
    the order. It never touches the network.
    """

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, request_dict: Dict[str, Any]) -> Dict[str, Any]:
        self.calls += 1
        candidates = request_dict["candidates"]
        n = len(candidates)
        results = [
            {
                "candidate_id": c["candidate_id"],
                "status": RerankOutcome.SUCCEEDED.value,
                "score": float(i),
            }
            for i, c in enumerate(candidates)
        ]
        return {
            "contract_version": "rerank.v1",
            "request_id": request_dict["request_id"],
            "provider": "fake-endpoint",
            "model_id": "fake-model",
            "model_revision": "fake-rev",
            "results": results,
            "candidate_count": n,
            "scored_count": n,
            "latency_ms": 1.0,
        }


class RaisingTransport:
    """A fake transport that fails with a text-free constant message."""

    def __call__(self, request_dict: Dict[str, Any]) -> Dict[str, Any]:
        raise RuntimeError("transport boom")


def _dispatcher_with(reranker) -> EnhancedDispatcher:
    d = EnhancedDispatcher.__new__(EnhancedDispatcher)
    d._reranker = reranker
    d._reranker_type = "endpoint"
    d._reranker_skips_semantic = False
    d._last_rerank_diagnostics = None
    return d


def _candidates(doc: str = "doc"):
    return [
        {"file": "a.py", "line": 1, "snippet": "alpha", "score": 0.9, "_rerank_doc": f"alpha {doc}"},
        {"file": "b.py", "line": 2, "snippet": "beta", "score": 0.8, "_rerank_doc": f"beta {doc}"},
        {"file": "c.py", "line": 3, "snippet": "gamma", "score": 0.7, "_rerank_doc": f"gamma {doc}"},
    ]


# --------------------------------------------------------------------------
# 1. Dispatcher drives an EndpointReranker end-to-end via SyncRerankerAdapter.
# --------------------------------------------------------------------------
def test_dispatcher_drives_endpoint_reranker_end_to_end():
    transport = ReversingTransport()
    endpoint = EndpointReranker(transport, provider="fake-endpoint")
    wrapped = EnhancedDispatcher.wrap_endpoint_reranker(endpoint)
    d = _dispatcher_with(wrapped)

    out = d._apply_reranker(None, "find the thing", _candidates(), limit=10)

    # The endpoint reversed the ordering; original dicts are preserved.
    assert [c["file"] for c in out] == ["c.py", "b.py", "a.py"]
    assert transport.calls == 1
    assert out[0]["_rerank_doc"] == "gamma doc"  # original dict object carried through

    diag = d._last_rerank_diagnostics
    assert diag.outcome is RerankOutcome.SUCCEEDED
    assert diag.reordered is True

    # The wrapper mirrors the endpoint's own structured signals.
    assert wrapped.last_outcome is RerankOutcome.SUCCEEDED
    assert wrapped.last_diagnostics is not None
    assert wrapped.last_diagnostics.provider == "fake-endpoint"


def test_dispatcher_build_reranker_endpoint_requires_transport():
    d = EnhancedDispatcher.__new__(EnhancedDispatcher)
    # No transport -> fail safe to None (never a broken reranker).
    assert d._build_reranker("endpoint", endpoint_rerank_transport=None) is None
    # With a transport -> a sync-dict wrapper around an EndpointReranker.
    wrapped = d._build_reranker("endpoint", endpoint_rerank_transport=ReversingTransport())
    assert wrapped is not None
    assert hasattr(wrapped, "rerank")
    assert wrapped.skips_semantic_path is False


# --------------------------------------------------------------------------
# 2. HybridSearch reranks through the canonical interface.
# --------------------------------------------------------------------------
def _hybrid_results(doc: str = "doc"):
    return [
        HybridSearchResult(
            doc_id="1", filepath="a.py", score=0.9, snippet=f"alpha {doc}",
            metadata={"line": 1}, source="bm25",
        ),
        HybridSearchResult(
            doc_id="2", filepath="b.py", score=0.8, snippet=f"beta {doc}",
            metadata={"line": 2}, source="bm25",
        ),
        HybridSearchResult(
            doc_id="3", filepath="c.py", score=0.7, snippet=f"gamma {doc}",
            metadata={"line": 3}, source="bm25",
        ),
    ]


async def test_hybrid_search_reranks_through_canonical_interface():
    hs = HybridSearch.__new__(HybridSearch)
    hs.reranker = EndpointReranker(ReversingTransport(), provider="fake-endpoint")
    hs.reranking_settings = types.SimpleNamespace(top_k=10, enabled=True)
    hs.last_rerank_diagnostics = None

    out = await hs._rerank_results("find the thing", _hybrid_results())

    assert [r.filepath for r in out] == ["c.py", "b.py", "a.py"]
    assert hs.last_rerank_diagnostics.outcome is RerankOutcome.SUCCEEDED
    assert hs.last_rerank_diagnostics.reordered is True
    # Original metadata preserved; rerank metadata added.
    assert out[0].metadata["original_rank"] == 2


# --------------------------------------------------------------------------
# 3. CrossRepositoryCoordinator reranks through the canonical signature.
# --------------------------------------------------------------------------
def _agg_results(doc: str = "doc"):
    return [
        types.SimpleNamespace(content={"symbol": f"alpha_{doc}", "file": "a.py"}, score=1.0),
        types.SimpleNamespace(content={"symbol": f"beta_{doc}", "file": "b.py"}, score=0.9),
        types.SimpleNamespace(content={"symbol": f"gamma_{doc}", "file": "c.py"}, score=0.8),
    ]


async def test_cross_repo_coordinator_reranks_through_canonical_signature():
    coord = CrossRepositoryCoordinator.__new__(CrossRepositoryCoordinator)
    coord.reranker = EndpointReranker(ReversingTransport(), provider="fake-endpoint")
    coord.last_rerank_diagnostics = None

    results = _agg_results()
    context = SearchContext(query="find the thing", search_type="symbol", max_results=10)

    out = await coord._rerank_results(results, context)

    assert [r.content["symbol"] for r in out] == ["gamma_doc", "beta_doc", "alpha_doc"]
    assert coord.last_rerank_diagnostics.outcome is RerankOutcome.SUCCEEDED
    assert coord.last_rerank_diagnostics.reordered is True


# --------------------------------------------------------------------------
# 4. Failure paths log no query/document text (egress).
# --------------------------------------------------------------------------
def test_dispatcher_failure_logs_no_query_or_doc_text(caplog):
    endpoint = EndpointReranker(RaisingTransport(), provider="fake-endpoint")
    d = _dispatcher_with(EnhancedDispatcher.wrap_endpoint_reranker(endpoint))
    candidates = _candidates(doc=DOC_SENTINEL)

    with caplog.at_level(logging.DEBUG):
        out = d._apply_reranker(None, QUERY_SENTINEL, candidates, limit=10)

    # Original ordering preserved on failure.
    assert [c["file"] for c in out] == ["a.py", "b.py", "c.py"]
    assert d._last_rerank_diagnostics.outcome is RerankOutcome.FAILED
    assert QUERY_SENTINEL not in caplog.text
    assert DOC_SENTINEL not in caplog.text


async def test_hybrid_failure_logs_no_query_or_doc_text(caplog):
    hs = HybridSearch.__new__(HybridSearch)
    hs.reranker = EndpointReranker(RaisingTransport(), provider="fake-endpoint")
    hs.reranking_settings = types.SimpleNamespace(top_k=10, enabled=True)
    hs.last_rerank_diagnostics = None

    with caplog.at_level(logging.DEBUG):
        out = await hs._rerank_results(QUERY_SENTINEL, _hybrid_results(doc=DOC_SENTINEL))

    assert [r.filepath for r in out] == ["a.py", "b.py", "c.py"]
    assert hs.last_rerank_diagnostics.outcome is RerankOutcome.FAILED
    assert QUERY_SENTINEL not in caplog.text
    assert DOC_SENTINEL not in caplog.text


async def test_cross_repo_failure_logs_no_query_or_doc_text(caplog):
    coord = CrossRepositoryCoordinator.__new__(CrossRepositoryCoordinator)
    coord.reranker = EndpointReranker(RaisingTransport(), provider="fake-endpoint")
    coord.last_rerank_diagnostics = None

    results = _agg_results(doc=DOC_SENTINEL)
    context = SearchContext(query=QUERY_SENTINEL, search_type="symbol", max_results=10)

    with caplog.at_level(logging.DEBUG):
        out = await coord._rerank_results(results, context)

    # Original order preserved on failure.
    assert [r.content["file"] for r in out] == ["a.py", "b.py", "c.py"]
    assert coord.last_rerank_diagnostics.outcome is RerankOutcome.FAILED
    assert QUERY_SENTINEL not in caplog.text
    assert DOC_SENTINEL not in caplog.text


# --------------------------------------------------------------------------
# 5. Empty candidates with a CONFIGURED reranker are ATTEMPTED, not
#    NOT_CONFIGURED (NOT_CONFIGURED is reserved for the absent-reranker case).
# --------------------------------------------------------------------------
async def test_hybrid_empty_candidates_configured_reranker_is_attempted():
    hs = HybridSearch.__new__(HybridSearch)
    hs.reranker = EndpointReranker(ReversingTransport(), provider="fake-endpoint")
    hs.reranking_settings = types.SimpleNamespace(top_k=10, enabled=True)
    hs.last_rerank_diagnostics = None

    out = await hs._rerank_results("find the thing", [])

    assert out == []
    diag = hs.last_rerank_diagnostics
    assert diag.outcome is not RerankOutcome.NOT_CONFIGURED
    assert diag.outcome is RerankOutcome.ATTEMPTED
    assert diag.candidate_count == 0


async def test_cross_repo_empty_candidates_configured_reranker_is_attempted():
    coord = CrossRepositoryCoordinator.__new__(CrossRepositoryCoordinator)
    coord.reranker = EndpointReranker(ReversingTransport(), provider="fake-endpoint")
    coord.last_rerank_diagnostics = None

    context = SearchContext(query="find the thing", search_type="symbol", max_results=10)
    out = await coord._rerank_results([], context)

    assert out == []
    diag = coord.last_rerank_diagnostics
    assert diag.outcome is not RerankOutcome.NOT_CONFIGURED
    assert diag.outcome is RerankOutcome.ATTEMPTED
    assert diag.candidate_count == 0


# --------------------------------------------------------------------------
# CR2: every hybrid failure path (init / rerank-Result / exception) redacts a
# credential embedded in a provider message before it reaches caplog OR the
# structured RerankDiagnostics.error field.
# --------------------------------------------------------------------------
from mcp_server.indexer.reranker import Result  # noqa: E402

BEARER_SECRET = "sk-SECRET123"
SECRET_MSG = f"boom Bearer {BEARER_SECRET}"


class SecretRaisingTransport:
    """Fake transport whose exception message embeds a credential."""

    def __call__(self, request_dict: Dict[str, Any]) -> Dict[str, Any]:
        raise RuntimeError(SECRET_MSG)


class _InitFailReranker:
    """Reranker whose optional initialize() returns a secret-bearing error."""

    async def initialize(self, config):
        return Result.error(SECRET_MSG)

    async def rerank(self, query, results, top_k=None):  # pragma: no cover - never reached
        return Result.ok(None)


class _RerankResultFailReranker:
    """Reranker (no initialize) whose rerank() returns a secret-bearing error."""

    async def rerank(self, query, results, top_k=None):
        return Result(False, None, SECRET_MSG)


def _fresh_hybrid(reranker):
    hs = HybridSearch.__new__(HybridSearch)
    hs.reranker = reranker
    hs.reranking_settings = types.SimpleNamespace(top_k=10, enabled=True)
    hs.last_rerank_diagnostics = None
    return hs


async def test_hybrid_init_failure_redacts_secret(caplog):
    hs = _fresh_hybrid(_InitFailReranker())
    with caplog.at_level(logging.DEBUG):
        out = await hs._rerank_results(QUERY_SENTINEL, _hybrid_results(doc=DOC_SENTINEL))

    assert [r.filepath for r in out] == ["a.py", "b.py", "c.py"]
    diag = hs.last_rerank_diagnostics
    assert diag.outcome is RerankOutcome.FAILED
    assert BEARER_SECRET not in caplog.text
    assert BEARER_SECRET not in (diag.error or "")
    assert "[REDACTED]" in (diag.error or "")
    assert QUERY_SENTINEL not in caplog.text
    assert DOC_SENTINEL not in caplog.text


async def test_hybrid_rerank_result_failure_redacts_secret(caplog):
    hs = _fresh_hybrid(_RerankResultFailReranker())
    with caplog.at_level(logging.DEBUG):
        out = await hs._rerank_results(QUERY_SENTINEL, _hybrid_results(doc=DOC_SENTINEL))

    assert [r.filepath for r in out] == ["a.py", "b.py", "c.py"]
    diag = hs.last_rerank_diagnostics
    assert diag.outcome is RerankOutcome.FAILED
    assert BEARER_SECRET not in caplog.text
    assert BEARER_SECRET not in (diag.error or "")
    assert "[REDACTED]" in (diag.error or "")
    assert QUERY_SENTINEL not in caplog.text
    assert DOC_SENTINEL not in caplog.text


async def test_hybrid_exception_failure_redacts_secret(caplog):
    hs = _fresh_hybrid(EndpointReranker(SecretRaisingTransport(), provider="fake-endpoint"))
    with caplog.at_level(logging.DEBUG):
        out = await hs._rerank_results(QUERY_SENTINEL, _hybrid_results(doc=DOC_SENTINEL))

    assert [r.filepath for r in out] == ["a.py", "b.py", "c.py"]
    diag = hs.last_rerank_diagnostics
    assert diag.outcome is RerankOutcome.FAILED
    assert BEARER_SECRET not in caplog.text
    assert BEARER_SECRET not in (diag.error or "")
    assert "[REDACTED]" in (diag.error or "")
    assert QUERY_SENTINEL not in caplog.text
    assert DOC_SENTINEL not in caplog.text


async def test_dispatcher_failure_redacts_secret(caplog):
    endpoint = EndpointReranker(SecretRaisingTransport(), provider="fake-endpoint")
    d = _dispatcher_with(EnhancedDispatcher.wrap_endpoint_reranker(endpoint))
    with caplog.at_level(logging.DEBUG):
        out = d._apply_reranker(None, QUERY_SENTINEL, _candidates(doc=DOC_SENTINEL), limit=10)

    assert [c["file"] for c in out] == ["a.py", "b.py", "c.py"]
    diag = d._last_rerank_diagnostics
    assert diag.outcome is RerankOutcome.FAILED
    assert BEARER_SECRET not in caplog.text
    assert BEARER_SECRET not in (diag.error or "")
    assert QUERY_SENTINEL not in caplog.text
    assert DOC_SENTINEL not in caplog.text
