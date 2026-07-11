"""
Tests for SL-1: reranker wiring in CrossRepositoryCoordinator.
"""

from typing import List
from unittest.mock import Mock, patch

import pytest

from mcp_server.dispatcher.cross_repo_coordinator import (
    CrossRepositoryCoordinator,
    SearchContext,
)
from mcp_server.indexer.reranker import (
    IReranker,
    RerankItem,
    RerankResult,
    Result,
    SearchResult,
)
from mcp_server.storage.multi_repo_manager import MultiRepositoryManager


class FakeReranker(IReranker):
    """Canonical reranker that reverses order (RERANKEND-migrated contract).

    Post-RERANKEND, the coordinator drives ``IReranker.rerank(query, results,
    top_k)`` and consumes a ``Result[RerankResult]`` — correlating results back
    by each ``RerankItem.original_rank``. (The pre-migration fake returned a bare
    index list, encoding the very ``documents=``/index-return bug this phase
    fixes.)
    """

    async def rerank(self, query: str, results: List[SearchResult], top_k: int):
        n = len(results)
        order = list(reversed(range(n)))[:top_k]
        items = [
            RerankItem(
                original_result=results[original_rank],
                rerank_score=float(n - new_rank),
                original_rank=original_rank,
                new_rank=new_rank,
            )
            for new_rank, original_rank in enumerate(order)
        ]
        return Result.ok(RerankResult(results=items, metadata={"reranker": "fake"}))


@pytest.fixture
def mock_manager():
    manager = Mock(spec=MultiRepositoryManager)
    manager.list_repositories.return_value = []
    return manager


def make_result(score: float, label: str):
    """Create a minimal object that satisfies CrossRepositoryCoordinator's _rerank_results."""
    obj = Mock()
    obj.content = {"symbol": label, "file": f"{label}.py"}
    obj.score = score
    return obj


class TestRerankerWiring:

    @pytest.mark.asyncio
    async def test_rerank_changes_order_with_fake_reranker(self, mock_manager):
        """Injected FakeReranker must reverse result order."""
        fake = FakeReranker()
        coord = CrossRepositoryCoordinator(
            multi_repo_manager=mock_manager,
            enable_reranking=True,
            reranker=fake,
        )

        results = [make_result(1.0, "alpha"), make_result(0.9, "beta"), make_result(0.8, "gamma")]
        context = SearchContext(query="test", search_type="symbol", max_results=10)

        reranked = await coord._rerank_results(results, context)

        labels = [r.content["symbol"] for r in reranked]
        assert labels == ["gamma", "beta", "alpha"]

    def test_no_reranker_when_disabled(self, mock_manager):
        """When enable_reranking=False, reranker must be None."""
        coord = CrossRepositoryCoordinator(
            multi_repo_manager=mock_manager,
            enable_reranking=False,
        )

        assert coord.reranker is None

    def test_injected_reranker_overrides_factory(self, mock_manager):
        """An injected reranker instance is stored, factory is NOT called."""
        fake = FakeReranker()
        with patch(
            "mcp_server.dispatcher.cross_repo_coordinator.RerankerFactory",
        ) as mock_factory_cls:
            coord = CrossRepositoryCoordinator(
                multi_repo_manager=mock_manager,
                enable_reranking=True,
                reranker=fake,
            )

        mock_factory_cls.assert_not_called()
        assert coord.reranker is fake
