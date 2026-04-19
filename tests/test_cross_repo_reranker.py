"""
Tests for SL-1: reranker wiring in CrossRepositoryCoordinator.
"""

import asyncio
from typing import List
from unittest.mock import Mock, patch

import pytest

from mcp_server.dispatcher.cross_repo_coordinator import (
    AggregatedResult,
    CrossRepositoryCoordinator,
    SearchContext,
)
from mcp_server.indexer.reranker import IReranker
from mcp_server.storage.multi_repo_manager import MultiRepositoryManager


class FakeReranker(IReranker):
    """Reranker that reverses the order of documents."""

    async def rerank(self, query: str, documents: List[str], top_k: int):
        n = len(documents)
        return list(reversed(range(n)))[:top_k]


@pytest.fixture
def mock_manager():
    manager = Mock(spec=MultiRepositoryManager)
    manager.list_repositories.return_value = []
    return manager


def make_result(score: float, label: str) -> AggregatedResult:
    return AggregatedResult(
        content={"symbol": label, "file": f"{label}.py"},
        score=score,
        repositories=["repo1"],
        primary_repository="repo1",
        occurrences=1,
    )


class TestRerankerWiring:

    @pytest.mark.asyncio
    async def test_rerank_changes_order_with_fake_reranker(self, mock_manager):
        """Injected FakeReranker must reverse result order."""
        fake = FakeReranker()
        with patch(
            "mcp_server.dispatcher.cross_repo_coordinator.get_multi_repo_manager",
            return_value=mock_manager,
        ):
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
        with patch(
            "mcp_server.dispatcher.cross_repo_coordinator.get_multi_repo_manager",
            return_value=mock_manager,
        ), patch(
            "mcp_server.dispatcher.cross_repo_coordinator.get_repository_plugin_loader",
        ):
            coord = CrossRepositoryCoordinator(
                multi_repo_manager=mock_manager,
                enable_reranking=False,
            )

        assert coord.reranker is None

    def test_injected_reranker_overrides_factory(self, mock_manager):
        """An injected reranker instance is stored, factory is NOT called."""
        fake = FakeReranker()
        with patch(
            "mcp_server.dispatcher.cross_repo_coordinator.get_multi_repo_manager",
            return_value=mock_manager,
        ), patch(
            "mcp_server.dispatcher.cross_repo_coordinator.RerankerFactory",
        ) as mock_factory_cls:
            coord = CrossRepositoryCoordinator(
                multi_repo_manager=mock_manager,
                enable_reranking=True,
                reranker=fake,
            )

        mock_factory_cls.assert_not_called()
        assert coord.reranker is fake
