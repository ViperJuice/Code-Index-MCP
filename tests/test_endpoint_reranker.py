"""Tests for RERANKEND lane R1 (IF-0-RERANKEND-1).

Covers:
    * ``EndpointReranker`` reorders candidates per a fake transport's scores;
    * stable ``candidate_id`` values survive request -> response reordering;
    * per-candidate partial failure is represented;
    * missing / unknown ids RAISE via ``validate_rerank_response``;
    * the sync/async bridge ``run_coroutine_sync`` runs an async rerank from
      synchronous code both WITH and WITHOUT an already-running event loop;
    * the Cohere ``/v2/rerank`` adapter builds a v2-shaped request;
    * in-process rerankers are selectable ONLY via the explicit standalone flag;
    * the canonical interface consolidation (single source of truth).

No network is performed anywhere: every transport is a fake.
"""

import asyncio

import pytest

from mcp_server.indexer.reranker import (
    COHERE_CURRENT_RERANK_MODEL,
    COHERE_LEGACY_RERANK_MODEL,
    CohereV2RerankAdapter,
    CrossEncoderReranker,
    EndpointReranker,
    FlashRankReranker,
    IReranker,
    RerankerFactory,
    RerankOutcome,
    RerankResult,
    SearchResult,
    SyncRerankerAdapter,
    run_coroutine_sync,
)
from mcp_server.interfaces import indexing_interfaces
from mcp_server.interfaces.rerank_contracts import (
    RerankContractError,
    RerankRequest,
)


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def _results(n: int = 3):
    """Build ``n`` SearchResults with distinct, identifiable snippets."""
    letters = ["alpha", "beta", "gamma", "delta", "epsilon"]
    return [
        SearchResult(
            file_path=f"{letters[i]}.py",
            start_line=i + 1,
            end_line=i + 1,
            column=0,
            snippet=letters[i],
            match_type="exact",
            score=0.5,
        )
        for i in range(n)
    ]


def _fake_transport(scores_by_index, *, reorder=True, latency_ms=5.0):
    """Return a transport that scores candidates by their positional index.

    ``scores_by_index`` maps candidate index -> score (or ``None`` to mark a
    per-candidate FAILED result). Response results are optionally reordered to
    exercise id-stable correlation.
    """

    def transport(request_dict):
        req = RerankRequest.from_dict(request_dict)
        results = []
        scored = 0
        for idx, cand in enumerate(req.candidates):
            score = scores_by_index.get(idx)
            if score is None:
                status = RerankOutcome.FAILED
            else:
                status = RerankOutcome.SUCCEEDED
                scored += 1
            results.append(
                {
                    "candidate_id": cand.candidate_id,
                    "status": status.value,
                    "score": score,
                }
            )
        if reorder:
            results = list(reversed(results))
        return {
            "contract_version": req.contract_version,
            "request_id": req.request_id,
            "provider": "fake",
            "model_id": "fake-rerank-1",
            "model_revision": "2026-07-01",
            "results": results,
            "candidate_count": len(req.candidates),
            "scored_count": scored,
            "latency_ms": latency_ms,
        }

    return transport


# --------------------------------------------------------------------------
# Consolidation: single canonical interface
# --------------------------------------------------------------------------


def test_indexing_interfaces_reexports_canonical():
    """indexing_interfaces re-exports the canonical reranker symbols."""
    assert indexing_interfaces.IReranker is IReranker
    assert indexing_interfaces.RerankResult is RerankResult
    assert issubclass(EndpointReranker, IReranker)


# --------------------------------------------------------------------------
# EndpointReranker: reorder + stable ids
# --------------------------------------------------------------------------


def test_endpoint_reranker_reorders_by_transport_scores():
    # Index 2 (gamma) gets the highest score, index 0 (alpha) the lowest, so the
    # output order genuinely differs from the input order.
    transport = _fake_transport({0: 0.1, 1: 0.5, 2: 0.9}, reorder=True)
    reranker = EndpointReranker(transport, provider="fake")

    result = run_coroutine_sync(reranker.rerank("q", _results(3), top_k=3))
    assert result.is_success
    rr = result.data
    assert isinstance(rr, RerankResult)

    order = [item.original_result.file_path for item in rr.results]
    assert order == ["gamma.py", "beta.py", "alpha.py"]
    assert reranker.last_outcome is RerankOutcome.SUCCEEDED
    assert rr.metadata["cross_provider_comparable"] is False


def test_stable_candidate_ids_survive_reordering():
    # Transport reverses result order; correlation must be by id, so the highest
    # score must still map to the right original SearchResult regardless.
    transport = _fake_transport({0: 0.1, 1: 0.2, 2: 0.99}, reorder=True)
    reranker = EndpointReranker(transport)

    result = run_coroutine_sync(reranker.rerank("q", _results(3), top_k=3))
    rr = result.data
    # gamma (index 2) had the top score -> must be first even though the
    # transport returned results reversed.
    assert rr.results[0].original_result.file_path == "gamma.py"
    assert rr.results[0].original_rank == 2
    assert rr.results[0].new_rank == 0


def test_per_candidate_partial_failure_represented():
    # Index 1 (beta) fails at the provider (score None -> FAILED).
    transport = _fake_transport({0: 0.9, 1: None, 2: 0.4}, reorder=False)
    reranker = EndpointReranker(transport)

    result = run_coroutine_sync(reranker.rerank("q", _results(3), top_k=3))
    rr = result.data

    assert "cand-1" in rr.metadata["partial_failures"]
    assert rr.metadata["candidate_statuses"]["cand-1"] == RerankOutcome.FAILED.value
    # Failed candidate is ordered LAST and carries an explanation.
    last = rr.results[-1]
    assert last.original_result.file_path == "beta.py"
    assert last.explanation and "failed" in last.explanation
    # Scored candidates keep their score-descending order ahead of the failure.
    assert [i.original_result.file_path for i in rr.results[:2]] == [
        "alpha.py",
        "gamma.py",
    ]


def test_missing_candidate_id_raises_contract_error():
    def transport(request_dict):
        req = RerankRequest.from_dict(request_dict)
        # Drop the last candidate from the response -> missing id.
        results = [
            {
                "candidate_id": c.candidate_id,
                "status": RerankOutcome.SUCCEEDED.value,
                "score": 0.5,
            }
            for c in req.candidates[:-1]
        ]
        return {
            "contract_version": req.contract_version,
            "request_id": req.request_id,
            "provider": "fake",
            "model_id": "m",
            "model_revision": "r",
            "results": results,
            "candidate_count": len(req.candidates),
            "scored_count": len(results),
        }

    reranker = EndpointReranker(transport)
    with pytest.raises(RerankContractError):
        run_coroutine_sync(reranker.rerank("q", _results(3), top_k=3))


def test_unknown_candidate_id_raises_contract_error():
    def transport(request_dict):
        req = RerankRequest.from_dict(request_dict)
        results = [
            {
                "candidate_id": c.candidate_id,
                "status": RerankOutcome.SUCCEEDED.value,
                "score": 0.5,
            }
            for c in req.candidates
        ]
        # Inject an id that was never requested.
        results.append(
            {
                "candidate_id": "cand-999",
                "status": RerankOutcome.SUCCEEDED.value,
                "score": 0.9,
            }
        )
        return {
            "contract_version": req.contract_version,
            "request_id": req.request_id,
            "provider": "fake",
            "model_id": "m",
            "model_revision": "r",
            "results": results,
            "candidate_count": len(req.candidates),
            "scored_count": len(results),
        }

    reranker = EndpointReranker(transport)
    with pytest.raises(RerankContractError):
        run_coroutine_sync(reranker.rerank("q", _results(3), top_k=3))


# --------------------------------------------------------------------------
# Sync/async bridge
# --------------------------------------------------------------------------


def test_run_coroutine_sync_without_running_loop():
    async def coro():
        await asyncio.sleep(0)
        return 41 + 1

    # No loop running in this thread -> fast path.
    assert run_coroutine_sync(coro()) == 42


def test_run_coroutine_sync_with_running_loop():
    # Drive the bridge from INSIDE a running event loop; it must not call
    # asyncio.run in the live loop but hand off to a worker thread.
    async def outer():
        async def inner():
            await asyncio.sleep(0)
            return "bridged"

        # We are inside a running loop here.
        return run_coroutine_sync(inner())

    assert asyncio.run(outer()) == "bridged"


def test_sync_reranker_adapter_drives_async_endpoint():
    transport = _fake_transport({0: 0.9, 1: 0.5, 2: 0.1}, reorder=True)
    adapter = SyncRerankerAdapter(EndpointReranker(transport))

    result = adapter.rerank("q", _results(3), top_k=3)
    assert result.is_success
    assert [i.original_result.file_path for i in result.data.results] == [
        "alpha.py",
        "beta.py",
        "gamma.py",
    ]


def test_sync_adapter_works_inside_running_loop():
    transport = _fake_transport({0: 0.9, 1: 0.5, 2: 0.1}, reorder=True)
    adapter = SyncRerankerAdapter(EndpointReranker(transport))

    async def outer():
        # Synchronous adapter.rerank invoked from within a running loop.
        return adapter.rerank("q", _results(3), top_k=3)

    result = asyncio.run(outer())
    assert result.is_success
    assert result.data.results[0].original_result.file_path == "alpha.py"


# --------------------------------------------------------------------------
# Cohere /v2/rerank adapter
# --------------------------------------------------------------------------


def test_cohere_adapter_builds_v2_shaped_request():
    captured = {}

    def send(body):
        captured["body"] = body
        # Cohere native response shape. Crucially, HONOR ``top_n`` as real
        # Cohere does (it truncates the response) so a bug that sets
        # top_n=top_k would produce a short response and fail contract
        # validation downstream.
        all_results = [
            {"index": 0, "relevance_score": 0.9},
            {"index": 1, "relevance_score": 0.2},
            {"index": 2, "relevance_score": 0.5},
        ]
        return {
            "results": all_results[: body["top_n"]],
            "model_revision": "2026-06-01",
        }

    adapter = CohereV2RerankAdapter(send)  # default = current model
    assert adapter.model == COHERE_CURRENT_RERANK_MODEL

    reranker = EndpointReranker(adapter, provider="cohere")
    # Request top_k=2 but 3 candidates: the adapter must still ask Cohere to
    # score ALL candidates (top_n=3) so the response carries every candidate_id.
    result = run_coroutine_sync(reranker.rerank("find json", _results(3), top_k=2))
    assert result.is_success

    body = captured["body"]
    assert body["model"] == COHERE_CURRENT_RERANK_MODEL
    assert body["query"] == "find json"
    assert body["documents"] == ["alpha", "beta", "gamma"]
    assert body["top_n"] == 3  # full candidate count, NOT top_k

    # End-to-end through EndpointReranker: index 0 (alpha) scored highest;
    # EndpointReranker applies the top_k=2 truncation on its side.
    assert len(result.data.results) == 2
    assert result.data.results[0].original_result.file_path == "alpha.py"
    assert result.data.metadata["provider"] == "cohere"


def test_cohere_adapter_legacy_model_is_explicit_opt_in():
    def send(body):
        return {"results": []}

    # Default is the current model; legacy must be passed explicitly.
    assert CohereV2RerankAdapter(send).model == COHERE_CURRENT_RERANK_MODEL
    legacy = CohereV2RerankAdapter(send, model=COHERE_LEGACY_RERANK_MODEL)
    assert legacy.model == COHERE_LEGACY_RERANK_MODEL
    assert legacy.build_v2_request({"candidates": [], "query": "x"})["model"] == (
        COHERE_LEGACY_RERANK_MODEL
    )


# --------------------------------------------------------------------------
# In-process rerankers require an explicit standalone flag
# --------------------------------------------------------------------------


def test_in_process_reranker_requires_explicit_standalone_flag():
    factory = RerankerFactory()

    # Not selectable implicitly.
    with pytest.raises(ValueError, match="standalone"):
        factory.create_standalone_reranker("flashrank")

    # Selectable only with the explicit flag.
    fr = factory.create_standalone_reranker("flashrank", standalone_profile=True)
    assert isinstance(fr, FlashRankReranker)

    ce = factory.create_standalone_reranker(
        "cross-encoder", standalone_profile=True
    )
    assert isinstance(ce, CrossEncoderReranker)


def test_in_process_standalone_unknown_name_raises():
    factory = RerankerFactory()
    with pytest.raises(ValueError, match="Unknown in-process"):
        factory.create_standalone_reranker("nope", standalone_profile=True)
