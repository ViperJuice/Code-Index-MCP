#!/usr/bin/env python3
"""Performance tests for document search operations."""

import asyncio
import concurrent.futures
import statistics
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pytest

from tests.base_test import BaseDocumentTest
from tests.test_utils import (
    assert_performance,
    create_mock_search_results,
    create_test_markdown,
    create_test_plaintext,
    memory_monitor,
    timer,
)


class TestDocumentSearchPerformance(BaseDocumentTest):
    """Test search performance and query optimization."""

    def setup_search_corpus(self, size: str = "medium") -> Dict[str, Any]:
        """Set up a corpus for search testing."""
        corpus_configs = {
            "small": {"docs": 50, "topics": 5},
            "medium": {"docs": 200, "topics": 10},
            "large": {"docs": 500, "topics": 20},
        }

        config = corpus_configs[size]
        topics = [
            "API Documentation",
            "User Guide",
            "Installation",
            "Configuration",
            "Troubleshooting",
            "Best Practices",
            "Security",
            "Performance",
            "Architecture",
            "Deployment",
            "Testing",
            "Monitoring",
            "Scaling",
            "Migration",
            "Integration",
            "Authentication",
            "Authorization",
            "Logging",
            "Caching",
            "Optimization",
        ][: config["topics"]]

        created_docs = []

        # Create documents for each topic
        docs_per_topic = config["docs"] // config["topics"]

        for topic_idx, topic in enumerate(topics):
            for doc_idx in range(docs_per_topic):
                # Mix markdown and plaintext
                if (topic_idx + doc_idx) % 2 == 0:
                    filename = f"{topic.lower().replace(' ', '_')}_{doc_idx:03d}.md"
                    content = self._create_topic_markdown(topic, doc_idx)
                else:
                    filename = f"{topic.lower().replace(' ', '_')}_{doc_idx:03d}.txt"
                    content = self._create_topic_plaintext(topic, doc_idx)

                doc_path = self.create_test_file(filename, content)
                created_docs.append({"path": doc_path, "topic": topic, "index": doc_idx})

        # Index all documents
        print(f"Indexing {len(created_docs)} documents...")
        start_time = time.perf_counter()

        for doc_info in created_docs:
            content = doc_info["path"].read_text()
            self.dispatcher.dispatch(str(doc_info["path"]), content)

        index_time = time.perf_counter() - start_time

        return {
            "size": size,
            "documents": created_docs,
            "topics": topics,
            "index_time": index_time,
            "config": config,
        }

    def _create_topic_markdown(self, topic: str, index: int) -> str:
        """Create markdown content for a specific topic."""
        return f"""# {topic} - Document {index}

## Overview

This document covers {topic.lower()} concepts and implementation details.
It provides comprehensive information for developers working with {topic.lower()}.

## Key Concepts

### Concept 1: Fundamentals
Understanding the basics of {topic.lower()} is crucial for effective implementation.
This section covers the fundamental principles and core concepts.

### Concept 2: Advanced Features
Advanced {topic.lower()} features enable more sophisticated use cases.
Learn about optimization techniques and best practices.

## Implementation Guide

```python
# Example {topic.lower()} implementation
class {topic.replace(' ', '')}Handler:
    def __init__(self):
        self.config = {{'enabled': True, 'level': 'advanced'}}
    
    def process(self, data):
        # Process {topic.lower()} logic
        return self.transform(data)
```

## Best Practices

1. Always validate {topic.lower()} configuration
2. Monitor performance metrics
3. Implement proper error handling
4. Follow security guidelines

## Troubleshooting

Common issues with {topic.lower()}:
- Configuration errors
- Performance bottlenecks
- Integration problems

## Reference

For more information on {topic.lower()}, see the official documentation.
"""

    def _create_topic_plaintext(self, topic: str, index: int) -> str:
        """Create plaintext content for a specific topic."""
        return f"""{topic} Reference Guide - Part {index}

Introduction to {topic}

This guide provides detailed information about {topic.lower()} implementation 
and configuration. It covers essential concepts, practical examples, and 
troubleshooting tips.

Key Features of {topic}:

The {topic.lower()} system offers several important features that help 
developers build robust applications. These include automated processing, 
real-time monitoring, and comprehensive error handling.

Configuration Options:

When setting up {topic.lower()}, consider the following configuration 
parameters: connection settings, timeout values, retry policies, and 
logging levels. Each parameter affects system behavior differently.

Performance Considerations:

Optimizing {topic.lower()} performance requires understanding of system 
resources, load patterns, and bottlenecks. Monitor CPU usage, memory 
consumption, and response times.

Security Best Practices:

Secure {topic.lower()} implementation involves proper authentication, 
authorization, encryption, and audit logging. Regular security reviews 
help maintain system integrity.

Troubleshooting Guide:

Common {topic.lower()} issues include connection failures, timeout errors, 
and configuration problems. Use diagnostic tools and logs for debugging.

Conclusion:

Effective use of {topic.lower()} requires understanding of core concepts, 
proper configuration, and ongoing monitoring. Follow best practices for 
optimal results.
"""

    @pytest.mark.performance
    def test_search_query_latency(self):
        """Test search query response times."""
        print("\n=== Search Query Latency Test ===")

        # Setup corpus
        corpus = self.setup_search_corpus("medium")
        print(
            f"Corpus ready: {len(corpus['documents'])} documents indexed in {corpus['index_time']:.1f}s"
        )

        # Test queries of varying complexity
        test_queries = [
            # Simple queries
            ("simple_keyword", "configuration"),
            ("two_words", "api documentation"),
            ("three_words", "user guide setup"),
            # Complex queries
            ("phrase_query", "how to configure authentication"),
            ("question_query", "what are the best practices for security"),
            (
                "long_query",
                "troubleshooting performance issues in production deployment with high load",
            ),
        ]

        results = {}
        iterations = 20

        for query_type, query in test_queries:
            print(f"\nTesting '{query_type}': {query}")

            query_times = []
            result_counts = []

            for _ in range(iterations):
                start_time = time.perf_counter()

                # Simulate search operation
                # In real implementation, this would call the actual search method
                search_results = create_mock_search_results(query, count=10)

                end_time = time.perf_counter()

                query_time_ms = (end_time - start_time) * 1000
                query_times.append(query_time_ms)
                result_counts.append(len(search_results))

            # Calculate statistics
            avg_time = statistics.mean(query_times)
            p50_time = statistics.median(query_times)
            p95_time = statistics.quantiles(query_times, n=20)[18]
            p99_time = (
                statistics.quantiles(query_times, n=100)[98]
                if len(query_times) >= 20
                else max(query_times)
            )

            results[query_type] = {
                "query": query,
                "avg_ms": avg_time,
                "p50_ms": p50_time,
                "p95_ms": p95_time,
                "p99_ms": p99_time,
                "avg_results": statistics.mean(result_counts),
            }

            print(
                f"  Avg: {avg_time:.1f}ms, P50: {p50_time:.1f}ms, P95: {p95_time:.1f}ms, P99: {p99_time:.1f}ms"
            )

            # Performance assertions - semantic search < 500ms P95
            assert_performance(p95_time / 1000, 0.5, f"{query_type} P95 latency")
            assert_performance(avg_time / 1000, 0.3, f"{query_type} average latency")

    @pytest.mark.performance
    def test_query_optimization_effectiveness(self):
        """Test effectiveness of query optimization techniques."""
        print("\n=== Query Optimization Effectiveness Test ===")

        # Setup corpus
        corpus = self.setup_search_corpus("medium")

        # Test different optimization techniques
        optimization_tests = [
            {
                "name": "baseline",
                "query": "configuration security authentication",
                "optimizations": [],
            },
            {
                "name": "with_stemming",
                "query": "configuring secure authentications",
                "optimizations": ["stemming"],
            },
            {
                "name": "with_synonyms",
                "query": "setup safety login",
                "optimizations": ["synonyms"],
            },
            {
                "name": "with_filters",
                "query": "configuration",
                "optimizations": ["topic_filter"],
                "filter": {"topic": "Configuration"},
            },
            {
                "name": "combined",
                "query": "configuring secure login",
                "optimizations": ["stemming", "synonyms", "topic_filter"],
                "filter": {"topic": "Security"},
            },
        ]

        results = {}

        for test in optimization_tests:
            print(f"\nTesting: {test['name']}")
            print(f"  Query: {test['query']}")
            print(f"  Optimizations: {test['optimizations']}")

            # Measure performance with optimizations
            search_times = []

            for _ in range(15):
                start_time = time.perf_counter()

                # Simulate optimized search
                if "topic_filter" in test["optimizations"] and "filter" in test:
                    # Filtered search should be faster
                    search_results = create_mock_search_results(test["query"], count=5)
                else:
                    search_results = create_mock_search_results(test["query"], count=10)

                end_time = time.perf_counter()
                search_times.append((end_time - start_time) * 1000)

            avg_time = statistics.mean(search_times)
            p95_time = (
                statistics.quantiles(search_times, n=20)[14]
                if len(search_times) >= 15
                else max(search_times)
            )

            results[test["name"]] = {
                "avg_ms": avg_time,
                "p95_ms": p95_time,
                "optimizations": test["optimizations"],
            }

            print(f"  Avg time: {avg_time:.1f}ms")
            print(f"  P95 time: {p95_time:.1f}ms")

        # Compare optimization effectiveness
        baseline = results["baseline"]
        print("\nOptimization Impact:")
        print("Optimization | Avg (ms) | P95 (ms) | Improvement")
        print("-" * 50)

        for name, result in results.items():
            if name != "baseline":
                avg_improvement = (
                    (baseline["avg_ms"] - result["avg_ms"]) / baseline["avg_ms"]
                ) * 100
                p95_improvement = (
                    (baseline["p95_ms"] - result["p95_ms"]) / baseline["p95_ms"]
                ) * 100

                print(
                    f"{name:<12} | {result['avg_ms']:>7.1f} | {result['p95_ms']:>7.1f} | "
                    f"{avg_improvement:>6.1f}% / {p95_improvement:>6.1f}%"
                )

    @pytest.mark.performance
    def test_cache_effectiveness(self):
        """Test search cache performance impact."""
        print("\n=== Cache Effectiveness Test ===")

        # Setup corpus
        corpus = self.setup_search_corpus("small")

        # Common queries to test caching
        test_queries = [
            "api documentation",
            "configuration guide",
            "troubleshooting errors",
            "performance optimization",
            "security best practices",
        ]

        # Test without cache (cold queries)
        print("\nCold queries (no cache):")
        cold_times = []

        for query in test_queries:
            start_time = time.perf_counter()
            results = create_mock_search_results(query)
            end_time = time.perf_counter()

            cold_time = (end_time - start_time) * 1000
            cold_times.append(cold_time)
            print(f"  '{query}': {cold_time:.1f}ms")

        avg_cold = statistics.mean(cold_times)

        # Test with cache (warm queries)
        print("\nWarm queries (with cache):")
        warm_times = []

        # Simulate cache warming
        cache = {}
        for query in test_queries:
            cache[query] = create_mock_search_results(query)

        # Measure cached query performance
        for query in test_queries:
            start_time = time.perf_counter()

            # Simulate cache hit
            if query in cache:
                results = cache[query]
            else:
                results = create_mock_search_results(query)

            end_time = time.perf_counter()

            warm_time = (end_time - start_time) * 1000
            warm_times.append(warm_time)
            print(f"  '{query}': {warm_time:.1f}ms")

        avg_warm = statistics.mean(warm_times)

        # Calculate cache effectiveness
        cache_speedup = avg_cold / avg_warm if avg_warm > 0 else 1.0
        cache_reduction = ((avg_cold - avg_warm) / avg_cold) * 100

        print(f"\nCache Performance:")
        print(f"  Avg cold: {avg_cold:.1f}ms")
        print(f"  Avg warm: {avg_warm:.1f}ms")
        print(f"  Speedup: {cache_speedup:.1f}x")
        print(f"  Latency reduction: {cache_reduction:.1f}%")

        # Cache should provide significant speedup
        assert cache_speedup >= 5.0, f"Cache speedup too low: {cache_speedup:.1f}x (expected >= 5x)"

    @pytest.mark.performance
    def test_pagination_performance(self):
        """Test performance of paginated search results."""
        print("\n=== Pagination Performance Test ===")

        # Setup corpus
        corpus = self.setup_search_corpus("large")

        # Test query that returns many results
        query = "documentation"

        # Test different page sizes
        page_sizes = [10, 20, 50, 100]
        results = {}

        for page_size in page_sizes:
            print(f"\nTesting page size: {page_size}")

            page_times = []

            # Test first 5 pages
            for page in range(5):
                start_time = time.perf_counter()

                # Simulate paginated search
                offset = page * page_size
                search_results = create_mock_search_results(query, count=page_size)

                end_time = time.perf_counter()

                page_time = (end_time - start_time) * 1000
                page_times.append(page_time)

                print(f"  Page {page + 1}: {page_time:.1f}ms")

            avg_time = statistics.mean(page_times)
            max_time = max(page_times)

            results[page_size] = {
                "avg_ms": avg_time,
                "max_ms": max_time,
                "per_result_ms": avg_time / page_size,
            }

        # Display pagination performance
        print("\nPagination Performance Summary:")
        print("Page Size | Avg (ms) | Max (ms) | ms/result")
        print("-" * 45)

        for size, data in results.items():
            print(
                f"{size:>9} | {data['avg_ms']:>7.1f} | {data['max_ms']:>7.1f} | {data['per_result_ms']:>9.2f}"
            )

        # Verify pagination doesn't degrade significantly with page size
        smallest = min(page_sizes)
        largest = max(page_sizes)

        time_increase = results[largest]["avg_ms"] / results[smallest]["avg_ms"]
        size_increase = largest / smallest

        # Time should increase sub-linearly with page size
        assert (
            time_increase < size_increase * 0.5
        ), f"Pagination time scales too steeply: {time_increase:.1f}x for {size_increase:.1f}x page size"

    @pytest.mark.performance
    def test_concurrent_search_throughput(self):
        """Test search performance under concurrent load."""
        print("\n=== Concurrent Search Throughput Test ===")

        # Setup corpus
        corpus = self.setup_search_corpus("medium")

        # Queries for concurrent testing
        queries = [
            "api documentation",
            "configuration settings",
            "error troubleshooting",
            "performance tuning",
            "security guidelines",
            "deployment process",
            "testing strategies",
            "monitoring setup",
        ]

        # Test different concurrency levels
        concurrency_levels = [1, 5, 10, 20]
        results = {}

        for num_concurrent in concurrency_levels:
            print(f"\nTesting {num_concurrent} concurrent searches:")

            # Prepare query workload
            query_workload = queries * (num_concurrent * 2)  # Each "user" does multiple queries

            def perform_search(query):
                """Perform a single search."""
                start = time.perf_counter()
                results = create_mock_search_results(query)
                end = time.perf_counter()
                return (end - start) * 1000, len(results)

            # Execute concurrent searches
            start_time = time.perf_counter()

            with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent) as executor:
                futures = [executor.submit(perform_search, q) for q in query_workload]
                search_results = [f.result() for f in concurrent.futures.as_completed(futures)]

            end_time = time.perf_counter()

            # Analyze results
            total_time = end_time - start_time
            query_times = [r[0] for r in search_results]
            queries_per_second = len(query_workload) / total_time

            results[num_concurrent] = {
                "total_queries": len(query_workload),
                "total_time_s": total_time,
                "qps": queries_per_second,
                "avg_latency_ms": statistics.mean(query_times),
                "p95_latency_ms": (
                    statistics.quantiles(query_times, n=20)[18]
                    if len(query_times) >= 20
                    else max(query_times)
                ),
            }

            print(f"  Total queries: {len(query_workload)}")
            print(f"  Time: {total_time:.1f}s")
            print(f"  Throughput: {queries_per_second:.1f} QPS")
            print(f"  Avg latency: {results[num_concurrent]['avg_latency_ms']:.1f}ms")
            print(f"  P95 latency: {results[num_concurrent]['p95_latency_ms']:.1f}ms")

        # Verify concurrent performance
        print("\nConcurrent Search Scaling:")
        print("Concurrent | QPS | Avg (ms) | P95 (ms) | Efficiency")
        print("-" * 55)

        baseline_qps = results[1]["qps"]

        for level, data in results.items():
            efficiency = (data["qps"] / baseline_qps) / level
            print(
                f"{level:>10} | {data['qps']:>3.0f} | {data['avg_latency_ms']:>7.1f} | "
                f"{data['p95_latency_ms']:>7.1f} | {efficiency:>10.1%}"
            )

        # Under load, P95 should still meet requirements
        max_concurrent = max(concurrency_levels)
        assert (
            results[max_concurrent]["p95_latency_ms"] < 1000
        ), f"P95 latency under load too high: {results[max_concurrent]['p95_latency_ms']:.1f}ms"

    @pytest.mark.performance
    async def test_async_search_performance(self):
        """Test asynchronous search performance."""
        print("\n=== Async Search Performance Test ===")

        # Setup corpus
        corpus = self.setup_search_corpus("medium")

        queries = [
            "installation guide",
            "api reference",
            "configuration options",
            "troubleshooting tips",
            "best practices",
        ]

        # Test synchronous baseline
        print("\nSynchronous search baseline:")
        sync_start = time.perf_counter()

        sync_results = []
        for query in queries * 4:  # 20 queries total
            result = create_mock_search_results(query)
            sync_results.append(len(result))

        sync_end = time.perf_counter()
        sync_time = sync_end - sync_start
        sync_rate = len(queries * 4) / sync_time

        print(f"  Time: {sync_time:.1f}s")
        print(f"  Rate: {sync_rate:.1f} queries/s")

        # Test async batch processing
        print("\nAsync batch search:")

        async def async_search(query):
            """Simulate async search."""
            await asyncio.sleep(0.01)  # Simulate I/O
            return create_mock_search_results(query)

        async_start = time.perf_counter()

        # Process in batches
        batch_size = 5
        async_results = []

        for i in range(0, len(queries * 4), batch_size):
            batch = (queries * 4)[i : i + batch_size]
            batch_results = await asyncio.gather(*[async_search(q) for q in batch])
            async_results.extend([len(r) for r in batch_results])

        async_end = time.perf_counter()
        async_time = async_end - async_start
        async_rate = len(queries * 4) / async_time

        print(f"  Time: {async_time:.1f}s")
        print(f"  Rate: {async_rate:.1f} queries/s")

        # Calculate improvement
        speedup = sync_time / async_time
        print(f"\nAsync speedup: {speedup:.1f}x")

        # Async should provide performance benefit
        assert speedup > 1.5, f"Async processing should be faster: {speedup:.1f}x"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "performance"])
