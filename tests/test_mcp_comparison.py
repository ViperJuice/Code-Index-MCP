"""
Test suite for MCP vs Direct Search comparison functionality.
"""

import os
import sys

import pytest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_server.utils.direct_searcher import DirectSearcher
from mcp_server.utils.token_counter import TokenCounter
from mcp_server.visualization.quick_charts import QuickCharts
from tests.comparison.base_comparison import ComparisonResult, PerformanceMetrics


class TestTokenCounter:
    """Test token counting functionality."""

    def test_basic_token_counting(self):
        counter = TokenCounter()
        text = "Hello world, this is a test."

        counter.add_input_tokens(text)
        assert counter.input_tokens > 0
        assert counter.output_tokens == 0

    def test_token_estimation(self):
        text = "This is approximately twenty characters."
        tokens = TokenCounter.count_tokens(text)
        # ~40 chars / 4 = ~10 tokens
        assert 8 <= tokens <= 12

    def test_cost_estimation(self):
        counter = TokenCounter()
        cost = counter.estimate_cost(100, 200, model="gpt-4")
        assert cost > 0

    def test_model_comparison(self):
        counter = TokenCounter()
        counter.add_input_tokens("Test input")
        counter.add_output_tokens("Test output response")

        comparison = counter.get_model_comparison()
        assert "gpt-4" in comparison
        assert "claude-3-opus" in comparison


class TestDirectSearcher:
    """Test direct search functionality."""

    def test_searcher_initialization(self):
        searcher = DirectSearcher()
        assert searcher.has_ripgrep or searcher.has_grep

    def test_pattern_search(self):
        searcher = DirectSearcher()
        # Search for Python imports in current file
        result = searcher.search_pattern(r"import\s+\w+", __file__, use_ripgrep=True)

        assert result["success"]
        assert result["match_count"] > 0
        assert "elapsed_time" in result

    def test_string_search(self):
        searcher = DirectSearcher()
        # Search for a specific string
        result = searcher.search_string("pytest", __file__)

        assert result["success"]
        assert result["match_count"] > 0


class TestComparisonBase:
    """Test base comparison functionality."""

    def test_comparison_result_structure(self):
        metrics = PerformanceMetrics(execution_time=1.5, cpu_usage=25.0, memory_usage_mb=100.0)

        result = ComparisonResult(
            success=True, performance_metrics=metrics, quality_scores={"accuracy": 0.95}
        )

        assert result.success
        assert result.performance_metrics.execution_time == 1.5
        assert "accuracy" in result.quality_scores

        # Test serialization
        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)
        assert result_dict["success"] is True


class TestVisualization:
    """Test chart generation."""

    def test_chart_creation(self):
        charts = QuickCharts()

        # Test token usage chart
        token_data = {"Query1": 100, "Query2": 150}
        # Just test that it doesn't raise an error
        charts.token_usage_comparison(token_data, show=False)

    def test_latency_chart(self):
        charts = QuickCharts()

        latency_data = {"Tool1": 50.0, "Tool2": 75.0}
        charts.latency_comparison(latency_data, unit="ms", show=False)


class TestIntegration:
    """Integration tests for the comparison system."""

    def test_end_to_end_comparison(self):
        """Test a simple end-to-end comparison."""
        # Token counting
        counter = TokenCounter()
        counter.add_input_tokens("Find all TODO comments")
        counter.add_output_tokens("Found 5 matches...")

        # Direct search
        searcher = DirectSearcher()
        result = searcher.search_pattern("TODO", ".")

        # Verify we can combine results
        comparison = {
            "mcp_tokens": counter.total_tokens,
            "direct_matches": result.get("match_count", 0),
            "direct_time": result.get("elapsed_time", 0),
        }

        assert comparison["mcp_tokens"] > 0
        assert isinstance(comparison["direct_time"], float)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
