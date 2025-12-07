#!/usr/bin/env python3
"""
Comprehensive test suite for measuring reranking performance and quality.
Tests both time and quality differences between non-reranking and reranking approaches.
"""

import asyncio
import json
import logging
import os
import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Import MCP server components
from mcp_server.config.settings import RerankingSettings, Settings
from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.indexer.bm25_indexer import BM25Indexer
from mcp_server.indexer.hybrid_search import HybridSearch, HybridSearchConfig
from mcp_server.indexer.reranker import RerankerFactory
from mcp_server.plugin_system.plugin_registry import PluginRegistry
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.utils.fuzzy_indexer import FuzzyIndexer
from mcp_server.utils.semantic_indexer import SemanticIndexer

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class TestQuery:
    """Represents a test query with expected results."""

    query: str
    query_type: str  # 'symbol', 'pattern', 'semantic', 'natural'
    expected_top_results: List[str] = field(default_factory=list)
    description: str = ""


@dataclass
class TestResult:
    """Stores test execution results."""

    query: TestQuery
    search_time_ms: float
    rerank_time_ms: float
    total_time_ms: float
    results_count: int
    top_10_results: List[Dict[str, Any]]
    relevance_scores: Dict[str, float] = field(default_factory=dict)

    def calculate_metrics(self) -> Dict[str, Any]:
        """Calculate quality metrics for this result."""
        metrics = {
            "search_time_ms": self.search_time_ms,
            "rerank_time_ms": self.rerank_time_ms,
            "total_time_ms": self.total_time_ms,
            "results_count": self.results_count,
        }

        # Calculate precision@k
        if self.query.expected_top_results:
            for k in [1, 3, 5, 10]:
                hits = 0
                for i in range(min(k, len(self.top_10_results))):
                    if (
                        self.top_10_results[i].get("filepath", "")
                        in self.query.expected_top_results
                    ):
                        hits += 1
                metrics[f"precision@{k}"] = hits / k if k <= len(self.top_10_results) else 0

        # Calculate MRR (Mean Reciprocal Rank)
        if self.query.expected_top_results and self.top_10_results:
            for i, result in enumerate(self.top_10_results):
                if result.get("filepath", "") in self.query.expected_top_results:
                    metrics["mrr"] = 1.0 / (i + 1)
                    break
            else:
                metrics["mrr"] = 0.0

        return metrics


class ComprehensiveRerankingTester:
    """Main test orchestrator for reranking evaluation."""

    def __init__(self):
        self.storage: Optional[SQLiteStore] = None
        self.dispatcher: Optional[EnhancedDispatcher] = None
        self.hybrid_search: Optional[HybridSearch] = None
        self.test_queries: List[TestQuery] = []
        self.results: Dict[str, List[TestResult]] = {}

    async def setup(self):
        """Initialize all components for testing."""
        logger.info("Setting up test environment...")

        # Initialize storage
        db_path = Path("/app/code_index.db")
        self.storage = SQLiteStore(str(db_path))

        # Initialize dispatcher
        registry = PluginRegistry()
        self.dispatcher = EnhancedDispatcher(
            storage=self.storage,
            plugin_registry=registry,
            enable_semantic=True,
            enable_advanced=True,
        )

        # Load plugins
        await self._load_plugins()

        # Initialize BM25 indexer
        bm25_indexer = BM25Indexer(self.storage)

        # Initialize semantic indexer (if available)
        semantic_indexer = None
        if os.getenv("VOYAGE_AI_API_KEY"):
            try:
                semantic_indexer = SemanticIndexer(
                    api_key=os.getenv("VOYAGE_AI_API_KEY"), model="voyage-code-3"
                )
                logger.info("Semantic indexer initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize semantic indexer: {e}")

        # Initialize fuzzy indexer
        fuzzy_indexer = FuzzyIndexer(self.storage)

        # Create hybrid search configurations for different test scenarios
        self._create_hybrid_search_configs(bm25_indexer, semantic_indexer, fuzzy_indexer)

        # Create test queries
        self._create_test_queries()

        logger.info("Test environment setup complete")

    async def _load_plugins(self):
        """Load necessary plugins for testing."""
        plugin_files = [
            "python_plugin.py",
            "js_plugin.py",
            "go_plugin.py",
            "rust_plugin.py",
            "markdown_plugin.py",
        ]

        for plugin_file in plugin_files:
            plugin_path = Path(
                f"/app/mcp_server/plugins/{plugin_file.replace('.py', '')}/plugin.py"
            )
            if plugin_path.exists():
                try:
                    await self.dispatcher._load_plugin(str(plugin_path))
                except Exception as e:
                    logger.warning(f"Failed to load plugin {plugin_file}: {e}")

    def _create_hybrid_search_configs(self, bm25_indexer, semantic_indexer, fuzzy_indexer):
        """Create different hybrid search configurations for testing."""
        self.search_configs = {}

        # Base configuration without reranking
        base_config = HybridSearchConfig(
            enable_bm25=True,
            enable_semantic=bool(semantic_indexer),
            enable_fuzzy=True,
            bm25_weight=0.5,
            semantic_weight=0.3 if semantic_indexer else 0.0,
            fuzzy_weight=0.2,
            individual_limit=50,
            final_limit=20,
        )

        self.search_configs["no_reranking"] = HybridSearch(
            storage=self.storage,
            bm25_indexer=bm25_indexer,
            semantic_indexer=semantic_indexer,
            fuzzy_indexer=fuzzy_indexer,
            config=base_config,
            reranking_settings=None,
        )

        # Configuration with TF-IDF reranking
        tfidf_settings = RerankingSettings(
            enabled=True, reranker_type="tfidf", top_k=20, cache_ttl=3600
        )

        self.search_configs["tfidf_reranking"] = HybridSearch(
            storage=self.storage,
            bm25_indexer=bm25_indexer,
            semantic_indexer=semantic_indexer,
            fuzzy_indexer=fuzzy_indexer,
            config=base_config,
            reranking_settings=tfidf_settings,
        )

        # Configuration with Cross-Encoder reranking (if available)
        cross_encoder_settings = RerankingSettings(
            enabled=True,
            reranker_type="cross-encoder",
            cross_encoder_model="cross-encoder/ms-marco-MiniLM-L-6-v2",
            cross_encoder_device="cpu",
            top_k=20,
            cache_ttl=3600,
        )

        self.search_configs["cross_encoder_reranking"] = HybridSearch(
            storage=self.storage,
            bm25_indexer=bm25_indexer,
            semantic_indexer=semantic_indexer,
            fuzzy_indexer=fuzzy_indexer,
            config=base_config,
            reranking_settings=cross_encoder_settings,
        )

        # Configuration with Cohere reranking (if API key available)
        if (
            os.getenv("COHERE_API_KEY")
            and os.getenv("COHERE_API_KEY") != "your-cohere-api-key-here"
        ):
            cohere_settings = RerankingSettings(
                enabled=True,
                reranker_type="cohere",
                cohere_api_key=os.getenv("COHERE_API_KEY"),
                cohere_model="rerank-english-v2.0",
                top_k=20,
                cache_ttl=3600,
            )

            self.search_configs["cohere_reranking"] = HybridSearch(
                storage=self.storage,
                bm25_indexer=bm25_indexer,
                semantic_indexer=semantic_indexer,
                fuzzy_indexer=fuzzy_indexer,
                config=base_config,
                reranking_settings=cohere_settings,
            )

        # Configuration with Hybrid reranking
        hybrid_settings = RerankingSettings(
            enabled=True,
            reranker_type="hybrid",
            hybrid_primary_type="cross-encoder" if not os.getenv("COHERE_API_KEY") else "cohere",
            hybrid_fallback_type="tfidf",
            hybrid_primary_weight=0.7,
            hybrid_fallback_weight=0.3,
            top_k=20,
            cache_ttl=3600,
        )

        self.search_configs["hybrid_reranking"] = HybridSearch(
            storage=self.storage,
            bm25_indexer=bm25_indexer,
            semantic_indexer=semantic_indexer,
            fuzzy_indexer=fuzzy_indexer,
            config=base_config,
            reranking_settings=hybrid_settings,
        )

    def _create_test_queries(self):
        """Create diverse test queries for evaluation."""
        self.test_queries = [
            # Symbol lookup queries
            TestQuery(
                query="EnhancedDispatcher",
                query_type="symbol",
                expected_top_results=["/app/mcp_server/dispatcher/dispatcher_enhanced.py"],
                description="Class name lookup",
            ),
            TestQuery(
                query="def search",
                query_type="pattern",
                expected_top_results=[
                    "/app/mcp_server/dispatcher/dispatcher.py",
                    "/app/mcp_server/dispatcher/dispatcher_enhanced.py",
                    "/app/mcp_server/indexer/hybrid_search.py",
                ],
                description="Function definition pattern",
            ),
            # Semantic queries
            TestQuery(
                query="authentication and security",
                query_type="semantic",
                expected_top_results=[
                    "/app/mcp_server/security/auth_manager.py",
                    "/app/mcp_server/security/security_middleware.py",
                    "/app/mcp_server/gateway.py",
                ],
                description="Security-related code",
            ),
            TestQuery(
                query="how does caching work",
                query_type="natural",
                expected_top_results=[
                    "/app/mcp_server/cache",
                    "/app/mcp_server/config/settings.py",
                ],
                description="Natural language query about caching",
            ),
            # Code pattern queries
            TestQuery(
                query="async def.*rerank",
                query_type="pattern",
                expected_top_results=[
                    "/app/mcp_server/indexer/reranker.py",
                    "/app/mcp_server/indexer/hybrid_search.py",
                ],
                description="Async reranking methods",
            ),
            TestQuery(
                query="import.*torch|tensorflow",
                query_type="pattern",
                expected_top_results=[],
                description="ML framework imports (should find few/none)",
            ),
            # Complex semantic queries
            TestQuery(
                query="error handling and exception management",
                query_type="semantic",
                expected_top_results=["/app/mcp_server/core/errors.py"],
                description="Error handling patterns",
            ),
            TestQuery(
                query="plugin system architecture",
                query_type="semantic",
                expected_top_results=[
                    "/app/mcp_server/plugin_system/plugin_manager.py",
                    "/app/mcp_server/plugin_system/plugin_registry.py",
                    "/app/mcp_server/plugin_base.py",
                ],
                description="Plugin architecture components",
            ),
            # Natural language queries
            TestQuery(
                query="what plugins are available",
                query_type="natural",
                expected_top_results=[
                    "/app/mcp_server/plugins/plugin_factory.py",
                    "/app/mcp_server/plugins/language_registry.py",
                ],
                description="Available plugins query",
            ),
            TestQuery(
                query="how to implement a new language plugin",
                query_type="natural",
                expected_top_results=[
                    "/app/mcp_server/plugin_base.py",
                    "/app/mcp_server/plugins/specialized_plugin_base.py",
                ],
                description="Plugin implementation guide",
            ),
        ]

    async def run_tests(self):
        """Execute all test scenarios."""
        logger.info("Starting comprehensive reranking tests...")

        for config_name, hybrid_search in self.search_configs.items():
            logger.info(f"\n{'='*60}")
            logger.info(f"Testing configuration: {config_name}")
            logger.info(f"{'='*60}")

            self.results[config_name] = []

            # Run each test query
            for query in self.test_queries:
                result = await self._execute_test_query(hybrid_search, query, config_name)
                self.results[config_name].append(result)

                # Log immediate results
                metrics = result.calculate_metrics()
                logger.info(f"Query: '{query.query}' ({query.query_type})")
                logger.info(f"  Total time: {metrics['total_time_ms']:.2f}ms")
                logger.info(f"  Search time: {metrics['search_time_ms']:.2f}ms")
                logger.info(f"  Rerank time: {metrics['rerank_time_ms']:.2f}ms")
                logger.info(f"  Results: {metrics['results_count']}")
                if "precision@1" in metrics:
                    logger.info(f"  Precision@1: {metrics['precision@1']:.2f}")
                    logger.info(f"  MRR: {metrics.get('mrr', 0):.2f}")

        # Generate comprehensive report
        await self.generate_report()

    async def _execute_test_query(
        self, hybrid_search: HybridSearch, query: TestQuery, config_name: str
    ) -> TestResult:
        """Execute a single test query and measure performance."""
        # Clear cache for fair comparison
        hybrid_search.clear_cache()

        # Measure search time
        start_time = time.time()

        try:
            results = await hybrid_search.search(query=query.query, limit=20)

            search_end_time = time.time()
            search_time_ms = (search_end_time - start_time) * 1000

            # Calculate reranking time (if applicable)
            rerank_time_ms = 0.0
            if "reranking" in config_name and results:
                # The reranking time is included in the total search time
                # We can estimate it based on the difference from base search
                if "no_reranking" in self.results and self.results["no_reranking"]:
                    # Find corresponding base result
                    base_results = [
                        r for r in self.results["no_reranking"] if r.query.query == query.query
                    ]
                    if base_results:
                        base_time = base_results[0].search_time_ms
                        rerank_time_ms = max(0, search_time_ms - base_time)

            total_time_ms = search_time_ms

            # Extract top 10 results
            top_10_results = results[:10] if results else []

            return TestResult(
                query=query,
                search_time_ms=search_time_ms - rerank_time_ms,
                rerank_time_ms=rerank_time_ms,
                total_time_ms=total_time_ms,
                results_count=len(results),
                top_10_results=top_10_results,
            )

        except Exception as e:
            logger.error(f"Error executing query '{query.query}': {e}")
            return TestResult(
                query=query,
                search_time_ms=0,
                rerank_time_ms=0,
                total_time_ms=0,
                results_count=0,
                top_10_results=[],
            )

    async def generate_report(self):
        """Generate comprehensive performance and quality report."""
        logger.info("\n" + "=" * 80)
        logger.info("COMPREHENSIVE RERANKING TEST REPORT")
        logger.info("=" * 80)
        logger.info(f"Generated at: {datetime.now().isoformat()}")

        # 1. Executive Summary
        logger.info("\n1. EXECUTIVE SUMMARY")
        logger.info("-" * 40)

        # Calculate overall statistics
        for config_name, results in self.results.items():
            if not results:
                continue

            avg_total_time = statistics.mean([r.total_time_ms for r in results])
            avg_search_time = statistics.mean([r.search_time_ms for r in results])
            avg_rerank_time = statistics.mean([r.rerank_time_ms for r in results])

            # Calculate quality metrics
            all_metrics = [r.calculate_metrics() for r in results]
            avg_precision_1 = statistics.mean([m.get("precision@1", 0) for m in all_metrics])
            avg_mrr = statistics.mean([m.get("mrr", 0) for m in all_metrics])

            logger.info(f"\n{config_name}:")
            logger.info(f"  Average total time: {avg_total_time:.2f}ms")
            logger.info(f"  Average search time: {avg_search_time:.2f}ms")
            logger.info(f"  Average rerank time: {avg_rerank_time:.2f}ms")
            logger.info(f"  Average Precision@1: {avg_precision_1:.2%}")
            logger.info(f"  Average MRR: {avg_mrr:.3f}")

        # 2. Performance Comparison
        logger.info("\n2. PERFORMANCE COMPARISON")
        logger.info("-" * 40)

        if "no_reranking" in self.results:
            base_avg_time = statistics.mean([r.total_time_ms for r in self.results["no_reranking"]])

            for config_name, results in self.results.items():
                if config_name == "no_reranking" or not results:
                    continue

                avg_time = statistics.mean([r.total_time_ms for r in results])
                overhead = ((avg_time - base_avg_time) / base_avg_time) * 100

                logger.info(f"\n{config_name}:")
                logger.info(f"  Performance overhead: {overhead:+.1f}%")
                logger.info(f"  Absolute overhead: {avg_time - base_avg_time:.2f}ms")

        # 3. Quality Improvement Analysis
        logger.info("\n3. QUALITY IMPROVEMENT ANALYSIS")
        logger.info("-" * 40)

        if "no_reranking" in self.results:
            base_metrics = [r.calculate_metrics() for r in self.results["no_reranking"]]
            base_precision_1 = statistics.mean([m.get("precision@1", 0) for m in base_metrics])
            base_mrr = statistics.mean([m.get("mrr", 0) for m in base_metrics])

            for config_name, results in self.results.items():
                if config_name == "no_reranking" or not results:
                    continue

                metrics = [r.calculate_metrics() for r in results]
                precision_1 = statistics.mean([m.get("precision@1", 0) for m in metrics])
                mrr = statistics.mean([m.get("mrr", 0) for m in metrics])

                precision_improvement = (
                    ((precision_1 - base_precision_1) / base_precision_1) * 100
                    if base_precision_1 > 0
                    else 0
                )
                mrr_improvement = ((mrr - base_mrr) / base_mrr) * 100 if base_mrr > 0 else 0

                logger.info(f"\n{config_name}:")
                logger.info(f"  Precision@1 improvement: {precision_improvement:+.1f}%")
                logger.info(f"  MRR improvement: {mrr_improvement:+.1f}%")

        # 4. Query Type Analysis
        logger.info("\n4. QUERY TYPE ANALYSIS")
        logger.info("-" * 40)

        query_types = set(q.query_type for q in self.test_queries)

        for query_type in query_types:
            logger.info(f"\nQuery Type: {query_type}")

            for config_name, results in self.results.items():
                type_results = [r for r in results if r.query.query_type == query_type]
                if not type_results:
                    continue

                avg_time = statistics.mean([r.total_time_ms for r in type_results])
                metrics = [r.calculate_metrics() for r in type_results]
                avg_precision = statistics.mean([m.get("precision@1", 0) for m in metrics])

                logger.info(f"  {config_name}: {avg_time:.2f}ms, P@1={avg_precision:.2%}")

        # 5. Recommendations
        logger.info("\n5. RECOMMENDATIONS")
        logger.info("-" * 40)

        # Find best configuration based on quality/performance trade-off
        best_quality_config = None
        best_quality_score = 0
        best_balanced_config = None
        best_balanced_score = 0

        for config_name, results in self.results.items():
            if not results:
                continue

            metrics = [r.calculate_metrics() for r in results]
            avg_mrr = statistics.mean([m.get("mrr", 0) for m in metrics])
            avg_time = statistics.mean([r.total_time_ms for r in results])

            # Quality score (higher is better)
            quality_score = avg_mrr

            # Balanced score (considers both quality and performance)
            # Normalize time (lower is better) and quality (higher is better)
            time_penalty = avg_time / 1000  # Convert to seconds
            balanced_score = avg_mrr / (1 + time_penalty)

            if quality_score > best_quality_score:
                best_quality_config = config_name
                best_quality_score = quality_score

            if balanced_score > best_balanced_score:
                best_balanced_config = config_name
                best_balanced_score = balanced_score

        logger.info(f"\nBest quality configuration: {best_quality_config}")
        logger.info(f"Best balanced configuration: {best_balanced_config}")

        logger.info("\nRecommended configurations by use case:")
        logger.info("- High-speed search (< 100ms): Use TF-IDF reranking or no reranking")
        logger.info("- Best quality (accuracy critical): Use Cross-Encoder or Cohere reranking")
        logger.info("- Balanced (default): Use Hybrid reranking with Cross-Encoder primary")
        logger.info("- API availability issues: Use Hybrid with TF-IDF fallback")

        # Save detailed results to JSON
        await self._save_detailed_results()

    async def _save_detailed_results(self):
        """Save detailed test results to JSON file."""
        output_data = {
            "test_run": datetime.now().isoformat(),
            "configurations": {},
            "queries": [
                {
                    "query": q.query,
                    "type": q.query_type,
                    "description": q.description,
                    "expected_results": q.expected_top_results,
                }
                for q in self.test_queries
            ],
        }

        for config_name, results in self.results.items():
            config_data = {"results": []}

            for result in results:
                metrics = result.calculate_metrics()
                config_data["results"].append(
                    {
                        "query": result.query.query,
                        "metrics": metrics,
                        "top_results": [
                            {
                                "filepath": r.get("filepath", ""),
                                "score": r.get("score", 0),
                                "snippet": (
                                    r.get("snippet", "")[:100] + "..."
                                    if r.get("snippet", "")
                                    else ""
                                ),
                            }
                            for r in result.top_10_results[:5]  # Save top 5 for brevity
                        ],
                    }
                )

            output_data["configurations"][config_name] = config_data

        output_path = Path("/app/test_results/reranking_comprehensive_results.json")
        output_path.parent.mkdir(exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(output_data, f, indent=2)

        logger.info(f"\nDetailed results saved to: {output_path}")


async def main():
    """Main test execution function."""
    tester = ComprehensiveRerankingTester()

    try:
        await tester.setup()
        await tester.run_tests()
    except Exception as e:
        logger.error(f"Test execution failed: {e}", exc_info=True)
    finally:
        # Cleanup
        if tester.storage:
            tester.storage.close()


if __name__ == "__main__":
    asyncio.run(main())
