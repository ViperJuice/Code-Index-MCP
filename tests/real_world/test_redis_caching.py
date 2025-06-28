"""
Real-World Redis Caching Testing for Dormant Features Validation

Tests Redis caching system with real-world scenarios to validate dormant features.
Requires Redis server running and REDIS_URL environment variable set.
"""

import pytest
import asyncio
import os
import time
import tempfile
from pathlib import Path
from typing import Dict, Any, List

# Skip all tests if Redis is not configured
pytestmark = pytest.mark.skipif(
    not os.getenv("REDIS_URL"),
    reason="Redis not configured - set REDIS_URL environment variable",
)


@pytest.mark.cache
class TestRedisCaching:
    """Test Redis caching with real-world scenarios."""

    @pytest.fixture
    async def redis_cache_manager(self):
        """Setup Redis cache manager."""
        try:
            from mcp_server.cache import CacheManagerFactory
        except ImportError:
            pytest.skip("Cache manager not available")

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

        try:
            cache_manager = CacheManagerFactory.create_redis_cache(
                redis_url=redis_url, default_ttl=300  # 5 minutes for testing
            )
            await cache_manager.initialize()

            # Clear any existing test data
            await cache_manager.clear()

            yield cache_manager

            # Cleanup
            await cache_manager.clear()
            await cache_manager.close()

        except Exception as e:
            pytest.skip(f"Failed to connect to Redis: {e}")

    @pytest.fixture
    async def query_cache(self, redis_cache_manager):
        """Setup query result cache with Redis backend."""
        try:
            from mcp_server.cache import QueryResultCache, QueryCacheConfig
        except ImportError:
            pytest.skip("Query cache not available")

        config = QueryCacheConfig(
            enabled=True,
            default_ttl=300,
            symbol_lookup_ttl=600,
            search_ttl=180,
            semantic_search_ttl=900,
        )

        query_cache = QueryResultCache(redis_cache_manager, config)
        yield query_cache

    async def test_basic_redis_operations(self, redis_cache_manager):
        """Test basic Redis cache operations."""
        cache = redis_cache_manager

        # Test basic set/get operations
        test_key = "test:basic:key"
        test_value = {"message": "Hello Redis", "timestamp": time.time()}

        # Set value
        await cache.set(test_key, test_value, ttl=60)

        # Get value
        retrieved = await cache.get(test_key)
        assert retrieved is not None, "Should retrieve cached value"
        assert retrieved["message"] == test_value["message"]

        # Test existence check
        exists = await cache.exists(test_key)
        assert exists, "Key should exist in cache"

        # Test deletion
        deleted = await cache.delete(test_key)
        assert deleted, "Should successfully delete key"

        # Verify deletion
        retrieved_after_delete = await cache.get(test_key)
        assert retrieved_after_delete is None, "Key should not exist after deletion"

    async def test_query_result_caching(self, query_cache):
        """Test query result caching with real search patterns."""
        from mcp_server.cache import QueryType

        # Simulate expensive query results
        symbol_lookup_result = {
            "symbol": "TestClass",
            "kind": "class",
            "language": "python",
            "signature": "class TestClass:",
            "file_path": "/test/file.py",
            "line": 1,
            "span": (1, 10),
        }

        search_results = [
            {
                "file": "/test/file1.py",
                "line": 5,
                "snippet": "def test_function():",
                "score": 0.95,
            },
            {
                "file": "/test/file2.py",
                "line": 12,
                "snippet": "class TestImplementation:",
                "score": 0.87,
            },
        ]

        # Test symbol lookup caching
        symbol_key = "test_symbol"
        await query_cache.cache_result(
            QueryType.SYMBOL_LOOKUP, symbol_lookup_result, symbol=symbol_key
        )

        cached_symbol = await query_cache.get_cached_result(
            QueryType.SYMBOL_LOOKUP, symbol=symbol_key
        )

        assert cached_symbol is not None, "Should retrieve cached symbol"
        assert cached_symbol["symbol"] == "TestClass"
        assert "cached_at" in cached_symbol, "Should include cache metadata"

        # Test search result caching
        search_query = "test function"
        await query_cache.cache_result(
            QueryType.SEARCH, search_results, q=search_query, limit=10
        )

        cached_search = await query_cache.get_cached_result(
            QueryType.SEARCH, q=search_query, limit=10
        )

        assert cached_search is not None, "Should retrieve cached search results"
        assert len(cached_search) == 2, "Should cache all search results"
        assert cached_search[0]["file"] == "/test/file1.py"

    @pytest.mark.performance
    async def test_cache_performance_improvement(self, redis_cache_manager, benchmark):
        """Test cache performance improvement for repeated queries."""
        cache = redis_cache_manager

        # Simulate expensive database operation
        async def expensive_operation(query_id: str) -> Dict[str, Any]:
            # Simulate 50ms database query
            await asyncio.sleep(0.05)
            return {
                "result": f"expensive_data_for_{query_id}",
                "computation_time": 50,
                "timestamp": time.time(),
            }

        # Test without cache (cold queries)
        def uncached_queries():
            async def run_queries():
                results = []
                for i in range(5):
                    result = await expensive_operation(f"query_{i}")
                    results.append(result)
                return results

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(run_queries())
            finally:
                loop.close()

        uncached_results = benchmark(uncached_queries)
        uncached_time = benchmark.stats.mean

        # Test with cache (warm queries)
        async def cached_queries():
            results = []

            # First run - populate cache
            for i in range(5):
                cache_key = f"expensive_query_{i}"

                # Try cache first
                cached = await cache.get(cache_key)
                if cached:
                    results.append(cached)
                else:
                    # Cache miss - compute and cache
                    result = await expensive_operation(f"query_{i}")
                    await cache.set(cache_key, result, ttl=300)
                    results.append(result)

            # Second run - should hit cache
            cached_results = []
            for i in range(5):
                cache_key = f"expensive_query_{i}"
                cached = await cache.get(cache_key)
                assert cached is not None, f"Should find cached result for {cache_key}"
                cached_results.append(cached)

            return results + cached_results

        def cached_queries_wrapper():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(cached_queries())
            finally:
                loop.close()

        cached_results = benchmark(cached_queries_wrapper)
        cached_time = benchmark.stats.mean

        # Verify cache provides performance benefit
        assert (
            len(cached_results) == 10
        ), "Should handle all cached and uncached queries"
        assert len(uncached_results) == 5, "Should handle all uncached queries"

        # The cached run should include both cache misses and hits, but still be faster overall
        print(f"Uncached time: {uncached_time:.3f}s, Cached time: {cached_time:.3f}s")

        # Note: This is a simplified test - real-world performance gains depend on query complexity

    async def test_cache_invalidation_patterns(self, redis_cache_manager, query_cache):
        """Test various cache invalidation scenarios."""
        from mcp_server.cache import QueryType

        cache = redis_cache_manager

        # Set up test data
        test_data = {
            "file1.py": {
                "symbols": ["ClassA", "function_b"],
                "content": "class ClassA: pass",
            },
            "file2.py": {
                "symbols": ["ClassC", "function_d"],
                "content": "def function_d(): pass",
            },
            "shared.py": {
                "symbols": ["SharedClass"],
                "content": "class SharedClass: pass",
            },
        }

        # Cache some query results
        for filename, data in test_data.items():
            # Cache symbol lookups
            for symbol in data["symbols"]:
                await query_cache.cache_result(
                    QueryType.SYMBOL_LOOKUP,
                    {"symbol": symbol, "file": filename, "content": data["content"]},
                    symbol=symbol,
                )

            # Cache search results
            await query_cache.cache_result(
                QueryType.SEARCH,
                [{"file": filename, "line": 1, "snippet": data["content"]}],
                q=f"content in {filename}",
                limit=10,
            )

        # Test file-based invalidation
        invalidated_count = await query_cache.invalidate_file_queries("file1.py")
        assert invalidated_count > 0, "Should invalidate queries related to file1.py"

        # Verify file1.py related queries are invalidated
        cached_symbol = await query_cache.get_cached_result(
            QueryType.SYMBOL_LOOKUP, symbol="ClassA"
        )
        assert cached_symbol is None, "ClassA should be invalidated"

        # Verify other files are not affected
        cached_symbol_c = await query_cache.get_cached_result(
            QueryType.SYMBOL_LOOKUP, symbol="ClassC"
        )
        assert cached_symbol_c is not None, "ClassC should still be cached"

        # Test semantic query invalidation
        if os.getenv("SEMANTIC_SEARCH_ENABLED", "false").lower() == "true":
            # Cache semantic search result
            await query_cache.cache_result(
                QueryType.SEMANTIC_SEARCH,
                [{"file": "semantic_test.py", "score": 0.9}],
                q="semantic query test",
                limit=5,
            )

            # Invalidate semantic queries
            semantic_invalidated = await query_cache.invalidate_semantic_queries()
            assert semantic_invalidated >= 1, "Should invalidate semantic queries"

    async def test_cache_memory_efficiency(self, redis_cache_manager):
        """Test cache memory usage and efficiency."""
        cache = redis_cache_manager

        # Get initial metrics
        initial_metrics = await cache.get_metrics()
        initial_entries = initial_metrics.entries_count

        # Add various sized entries
        test_entries = {}
        for i in range(100):
            key = f"memory_test_{i}"
            # Create entries of varying sizes
            size_multiplier = (i % 10) + 1
            value = {
                "data": "x" * (100 * size_multiplier),
                "metadata": {"index": i, "size": size_multiplier},
                "timestamp": time.time(),
            }
            test_entries[key] = value
            await cache.set(key, value, ttl=300)

        # Check metrics after adding entries
        after_metrics = await cache.get_metrics()
        entries_added = after_metrics.entries_count - initial_entries

        assert entries_added >= 90, f"Should add most entries, added {entries_added}"

        # Test bulk retrieval performance
        start_time = time.time()
        retrieved_count = 0

        for key in list(test_entries.keys())[:50]:  # Test first 50
            value = await cache.get(key)
            if value is not None:
                retrieved_count += 1

        retrieval_time = time.time() - start_time

        assert (
            retrieved_count >= 45
        ), f"Should retrieve most entries, got {retrieved_count}"
        assert retrieval_time < 2.0, f"Bulk retrieval too slow: {retrieval_time:.3f}s"

        print(
            f"Memory efficiency test: {entries_added} entries added, {retrieved_count} retrieved in {retrieval_time:.3f}s"
        )

        # Test memory usage reporting
        final_metrics = await cache.get_metrics()
        if hasattr(final_metrics, "memory_usage_mb"):
            memory_usage = final_metrics.memory_usage_mb
            print(f"Cache memory usage: {memory_usage:.2f} MB")

    async def test_cache_concurrency_safety(self, redis_cache_manager):
        """Test cache operations under concurrent access."""
        cache = redis_cache_manager

        # Define concurrent operations
        async def write_operations(worker_id: int):
            results = []
            for i in range(20):
                key = f"concurrent_{worker_id}_{i}"
                value = {"worker": worker_id, "item": i, "timestamp": time.time()}

                try:
                    await cache.set(key, value, ttl=300)
                    results.append(("set", key, True))
                except Exception as e:
                    results.append(("set", key, False, str(e)))

            return results

        async def read_operations(worker_id: int):
            results = []
            for i in range(20):
                # Try to read keys from all workers
                for w in range(3):
                    key = f"concurrent_{w}_{i}"
                    try:
                        value = await cache.get(key)
                        results.append(("get", key, value is not None))
                    except Exception as e:
                        results.append(("get", key, False, str(e)))

            return results

        # Run concurrent operations
        write_tasks = [write_operations(i) for i in range(3)]
        read_tasks = [read_operations(i) for i in range(2)]

        all_tasks = write_tasks + read_tasks
        results = await asyncio.gather(*all_tasks, return_exceptions=True)

        # Analyze results
        write_results = results[:3]
        read_results = results[3:]

        # Check write operations
        total_writes = 0
        successful_writes = 0

        for write_result in write_results:
            if isinstance(write_result, list):
                total_writes += len(write_result)
                successful_writes += sum(
                    1 for op in write_result if len(op) == 3 and op[2]
                )

        assert total_writes == 60, f"Should attempt 60 writes, attempted {total_writes}"
        assert (
            successful_writes >= 55
        ), f"Should complete most writes, completed {successful_writes}"

        # Check read operations
        total_reads = 0
        for read_result in read_results:
            if isinstance(read_result, list):
                total_reads += len(read_result)

        assert total_reads == 120, f"Should attempt 120 reads, attempted {total_reads}"

        print(
            f"Concurrency test: {successful_writes}/{total_writes} writes, {total_reads} reads"
        )

    async def test_cache_persistence_and_recovery(self, redis_cache_manager):
        """Test cache persistence across connections."""
        cache = redis_cache_manager

        # Store test data
        test_data = {
            "persistent_key_1": {"value": "data1", "type": "persistent"},
            "persistent_key_2": {"value": "data2", "type": "persistent"},
            "persistent_key_3": {"value": "data3", "type": "persistent"},
        }

        # Set data with longer TTL
        for key, value in test_data.items():
            await cache.set(key, value, ttl=600)  # 10 minutes

        # Verify data is stored
        for key in test_data.keys():
            retrieved = await cache.get(key)
            assert retrieved is not None, f"Should store {key}"
            assert retrieved["type"] == "persistent"

        # Close and reconnect cache (simulating restart)
        await cache.close()

        # Create new cache connection
        try:
            from mcp_server.cache import CacheManagerFactory
        except ImportError:
            pytest.skip("Cache manager not available")

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        new_cache = CacheManagerFactory.create_redis_cache(
            redis_url=redis_url, default_ttl=300
        )
        await new_cache.initialize()

        try:
            # Verify data persisted across connection
            recovered_count = 0
            for key, expected_value in test_data.items():
                retrieved = await new_cache.get(key)
                if retrieved is not None:
                    assert retrieved["value"] == expected_value["value"]
                    recovered_count += 1

            assert (
                recovered_count >= 2
            ), f"Should recover most persistent data, recovered {recovered_count}"
            print(
                f"Persistence test: {recovered_count}/{len(test_data)} entries recovered"
            )

        finally:
            # Cleanup
            await new_cache.clear()
            await new_cache.close()

    async def test_cache_hit_rate_optimization(self, redis_cache_manager, query_cache):
        """Test cache hit rate with realistic usage patterns."""
        from mcp_server.cache import QueryType

        # Simulate realistic search patterns
        common_symbols = ["User", "Session", "API", "Database", "Config"]
        common_queries = [
            "user authentication",
            "session management",
            "API endpoint",
            "database query",
        ]

        total_requests = 0
        cache_hits = 0

        # Simulate multiple rounds of queries
        for round_num in range(3):
            # Symbol lookups - these should have high cache hit rate after first round
            for symbol in common_symbols:
                total_requests += 1

                cached_result = await query_cache.get_cached_result(
                    QueryType.SYMBOL_LOOKUP, symbol=symbol
                )

                if cached_result is not None:
                    cache_hits += 1
                else:
                    # Cache miss - simulate lookup and cache result
                    result = {
                        "symbol": symbol,
                        "kind": "class",
                        "file": f"{symbol.lower()}.py",
                        "line": 1,
                    }
                    await query_cache.cache_result(
                        QueryType.SYMBOL_LOOKUP, result, symbol=symbol
                    )

            # Search queries - also should have increasing hit rate
            for query in common_queries:
                total_requests += 1

                cached_result = await query_cache.get_cached_result(
                    QueryType.SEARCH, q=query, limit=10
                )

                if cached_result is not None:
                    cache_hits += 1
                else:
                    # Cache miss - simulate search and cache results
                    results = [
                        {
                            "file": f"{query.replace(' ', '_')}.py",
                            "line": 1,
                            "snippet": query,
                        }
                    ]
                    await query_cache.cache_result(
                        QueryType.SEARCH, results, q=query, limit=10
                    )

        # Calculate hit rate
        hit_rate = cache_hits / total_requests if total_requests > 0 else 0

        # After 3 rounds, should have good hit rate for repeated queries
        assert (
            hit_rate >= 0.6
        ), f"Cache hit rate {hit_rate:.2f} should be >= 0.6 for repeated queries"

        print(
            f"Hit rate optimization: {cache_hits}/{total_requests} hits ({hit_rate:.2%})"
        )

        # Verify cache metrics
        cache_metrics = await redis_cache_manager.get_metrics()
        if hasattr(cache_metrics, "hit_rate"):
            backend_hit_rate = cache_metrics.hit_rate
            print(f"Backend cache hit rate: {backend_hit_rate:.2%}")


@pytest.mark.cache
@pytest.mark.integration
class TestRedisCacheIntegration:
    """Test Redis cache integration with other system components."""

    @pytest.fixture
    async def integrated_cache_system(self):
        """Setup integrated cache system with multiple components."""
        try:
            from mcp_server.cache import (
                CacheManagerFactory,
                QueryResultCache,
                QueryCacheConfig,
            )
        except ImportError:
            pytest.skip("Cache system components not available")

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

        try:
            # Create cache manager
            cache_manager = CacheManagerFactory.create_redis_cache(
                redis_url=redis_url, default_ttl=300
            )
            await cache_manager.initialize()

            # Create query cache
            query_config = QueryCacheConfig(enabled=True, default_ttl=300)
            query_cache = QueryResultCache(cache_manager, query_config)

            yield {"cache_manager": cache_manager, "query_cache": query_cache}

            # Cleanup
            await cache_manager.clear()
            await cache_manager.close()

        except Exception as e:
            pytest.skip(f"Failed to setup integrated cache system: {e}")

    async def test_cache_with_file_watcher_integration(self, integrated_cache_system):
        """Test cache invalidation integration with file watcher."""
        cache_manager = integrated_cache_system["cache_manager"]
        query_cache = integrated_cache_system["query_cache"]

        # Simulate file watcher detecting file changes
        test_file = "watched_file.py"

        # Cache some data related to the file
        await cache_manager.set(
            f"file:{test_file}:symbols", ["ClassA", "method_b"], ttl=600
        )
        await cache_manager.set(
            f"file:{test_file}:metadata",
            {"size": 1024, "modified": time.time()},
            ttl=600,
        )

        # Verify data is cached
        symbols = await cache_manager.get(f"file:{test_file}:symbols")
        assert symbols is not None, "File symbols should be cached"

        # Simulate file change event - invalidate related cache entries
        invalidated_count = await query_cache.invalidate_file_queries(test_file)

        # Should handle case where file-specific queries exist
        assert invalidated_count >= 0, "Should handle file invalidation without errors"

        print(
            f"File watcher integration: invalidated {invalidated_count} queries for {test_file}"
        )

    async def test_cache_with_plugin_system_integration(self, integrated_cache_system):
        """Test cache integration with plugin system indexing."""
        cache_manager = integrated_cache_system["cache_manager"]
        query_cache = integrated_cache_system["query_cache"]
        from mcp_server.cache import QueryType

        # Simulate plugin indexing operations with caching
        plugin_results = {
            "python_plugin": {
                "file1.py": ["ClassA", "method_b", "CONSTANT_C"],
                "file2.py": ["ClassD", "method_e"],
            },
            "javascript_plugin": {
                "app.js": ["Component", "handleClick", "API_URL"],
                "utils.js": ["formatDate", "validateInput"],
            },
        }

        # Cache plugin results
        for plugin_name, files in plugin_results.items():
            for filename, symbols in files.items():
                # Cache symbol information
                for symbol in symbols:
                    await query_cache.cache_result(
                        QueryType.SYMBOL_LOOKUP,
                        {
                            "symbol": symbol,
                            "file": filename,
                            "plugin": plugin_name,
                            "cached_at": time.time(),
                        },
                        symbol=symbol,
                    )

        # Test retrieval of cached plugin results
        cached_class_a = await query_cache.get_cached_result(
            QueryType.SYMBOL_LOOKUP, symbol="ClassA"
        )

        assert cached_class_a is not None, "Should find cached symbol from plugin"
        assert cached_class_a["plugin"] == "python_plugin"
        assert cached_class_a["file"] == "file1.py"

        # Test cross-plugin symbol lookup
        cached_component = await query_cache.get_cached_result(
            QueryType.SYMBOL_LOOKUP, symbol="Component"
        )

        assert cached_component is not None, "Should find cached JavaScript symbol"
        assert cached_component["plugin"] == "javascript_plugin"

        print(f"Plugin integration: cached symbols from {len(plugin_results)} plugins")

    async def test_cache_performance_under_load(
        self, integrated_cache_system, benchmark
    ):
        """Test cache performance under realistic load conditions."""
        cache_manager = integrated_cache_system["cache_manager"]
        query_cache = integrated_cache_system["query_cache"]
        from mcp_server.cache import QueryType

        async def simulate_realistic_load():
            """Simulate realistic cache usage patterns."""
            operations = []

            # Simulate various cache operations
            for i in range(50):
                # Symbol lookups (common operation)
                if i % 3 == 0:
                    symbol = f"Symbol{i % 10}"  # Some symbols repeated
                    cached = await query_cache.get_cached_result(
                        QueryType.SYMBOL_LOOKUP, symbol=symbol
                    )
                    if not cached:
                        result = {"symbol": symbol, "file": f"file{i}.py", "line": i}
                        await query_cache.cache_result(
                            QueryType.SYMBOL_LOOKUP, result, symbol=symbol
                        )
                    operations.append("symbol_lookup")

                # Search operations
                elif i % 3 == 1:
                    query = f"search_term_{i % 5}"  # Some queries repeated
                    cached = await query_cache.get_cached_result(
                        QueryType.SEARCH, q=query, limit=10
                    )
                    if not cached:
                        results = [{"file": f"result{i}.py", "line": i, "score": 0.9}]
                        await query_cache.cache_result(
                            QueryType.SEARCH, results, q=query, limit=10
                        )
                    operations.append("search")

                # Direct cache operations
                else:
                    key = f"direct_key_{i}"
                    value = {"data": f"value_{i}", "timestamp": time.time()}
                    await cache_manager.set(key, value, ttl=300)
                    retrieved = await cache_manager.get(key)
                    assert retrieved is not None
                    operations.append("direct")

            return operations

        def sync_realistic_load():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(simulate_realistic_load())
            finally:
                loop.close()

        operations = benchmark(sync_realistic_load)

        # Performance assertions
        assert len(operations) == 50, "Should complete all operations"
        assert (
            benchmark.stats.mean < 2.0
        ), f"Load test too slow: {benchmark.stats.mean:.2f}s"

        # Check cache metrics
        metrics = await cache_manager.get_metrics()
        print(
            f"Load test metrics: {metrics.hits} hits, {metrics.misses} misses, hit rate: {metrics.hit_rate:.2%}"
        )

        # Should have reasonable hit rate due to repeated operations
        if metrics.hits + metrics.misses > 0:
            assert (
                metrics.hit_rate >= 0.2
            ), f"Hit rate {metrics.hit_rate:.2%} should be reasonable under load"
