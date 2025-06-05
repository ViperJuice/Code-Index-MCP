"""Comprehensive tests for the advanced multi-tier cache system."""
import asyncio
import pytest
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List

from .tiered_cache import TieredCache, CacheTier
from .cache_warming import CacheWarmingManager, WarmingRule, WarmingStrategy, create_symbol_warming_rule
from .decorators import cached, set_global_cache, cache_symbol_lookup, CacheKeyStrategy
from .performance_monitor import PerformanceMonitor, PerformanceThreshold, AlertLevel
from .gpu_acceleration import get_gpu_accelerator


class TestTieredCache:
    """Test the core tiered cache functionality."""
    
    @pytest.fixture
    async def cache(self):
        """Create a test cache instance."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = TieredCache(
                redis_url="redis://localhost:6379",
                l1_max_size=100,
                l1_max_memory_mb=10,
                l3_cache_dir=temp_dir
            )
            yield cache
            await cache.shutdown()
    
    async def test_l1_cache_operations(self, cache):
        """Test L1 (memory) cache operations."""
        # Test set and get
        await cache.set("test_key", "test_value", ttl=60)
        result = await cache.get("test_key")
        assert result == "test_value"
        
        # Test cache hit in L1
        assert "test_key" in cache.l1_cache
        
        # Test eviction when exceeding size limit
        for i in range(150):  # Exceed max_size of 100
            await cache.set(f"key_{i}", f"value_{i}", ttl=60)
        
        # Should have evicted some entries
        assert len(cache.l1_cache) <= cache.l1_max_size
    
    async def test_access_pattern_tracking(self, cache):
        """Test access pattern tracking and promotion."""
        # Access a key multiple times
        key = "frequently_accessed"
        await cache.set(key, "value", ttl=60)
        
        # Access multiple times to build pattern
        for _ in range(5):
            await cache.get(key)
            await asyncio.sleep(0.1)  # Small delay to build frequency
        
        # Check that access pattern is tracked
        assert key in cache.access_patterns
        pattern = cache.access_patterns[key]
        assert pattern.access_count >= 5
        assert pattern.access_frequency > 0
    
    async def test_intelligent_promotion(self, cache):
        """Test intelligent promotion between tiers."""
        # Set a value in L3 (large value)
        large_value = "x" * (1024 * 1024)  # 1MB
        await cache.set("large_key", large_value, ttl=300)
        
        # Should not be in L1 due to size
        assert "large_key" not in cache.l1_cache
        
        # Access multiple times to trigger promotion
        for _ in range(4):
            result = await cache.get("large_key")
            assert result == large_value
            await asyncio.sleep(0.1)
    
    async def test_cache_stats(self, cache):
        """Test cache statistics collection."""
        # Perform some operations
        await cache.set("stat_key1", "value1", ttl=60)
        await cache.set("stat_key2", "value2", ttl=60)
        await cache.get("stat_key1")
        await cache.get("nonexistent_key")
        
        stats = await cache.get_stats()
        
        assert "overall" in stats
        assert "tiers" in stats
        assert "access_patterns" in stats
        
        overall = stats["overall"]
        assert "hit_rate" in overall
        assert "total_requests" in overall
        assert overall["total_requests"] > 0


class TestCacheWarming:
    """Test cache warming and invalidation functionality."""
    
    @pytest.fixture
    async def cache_with_warming(self):
        """Create cache with warming manager."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = TieredCache(l3_cache_dir=temp_dir)
            warming_manager = CacheWarmingManager(cache)
            yield cache, warming_manager
            await warming_manager.shutdown()
            await cache.shutdown()
    
    async def test_warming_rule_creation(self, cache_with_warming):
        """Test warming rule creation and matching."""
        cache, warming_manager = cache_with_warming
        
        async def mock_factory(key: str) -> str:
            return f"generated_value_for_{key}"
        
        # Create a warming rule
        rule = WarmingRule(
            key_pattern="symbol:*",
            factory_func=mock_factory,
            strategy=WarmingStrategy.EAGER,
            priority=3
        )
        
        warming_manager.add_warming_rule("symbol:*", rule)
        
        # Test rule matching
        found_rule = warming_manager._find_warming_rule("symbol:test")
        assert found_rule is not None
        assert found_rule.priority == 3
    
    async def test_eager_warming(self, cache_with_warming):
        """Test eager cache warming."""
        cache, warming_manager = cache_with_warming
        
        async def mock_factory(key: str) -> str:
            await asyncio.sleep(0.01)  # Simulate work
            return f"warm_value_{key}"
        
        rule = WarmingRule(
            key_pattern="test:*",
            factory_func=mock_factory,
            strategy=WarmingStrategy.EAGER
        )
        warming_manager.add_warming_rule("test:*", rule)
        
        # Warm multiple keys
        keys = ["test:key1", "test:key2", "test:key3"]
        results = await warming_manager.warm_cache(keys, WarmingStrategy.EAGER)
        
        # Check that all keys were warmed successfully
        for key in keys:
            assert results.get(key) is True
            cached_value = await cache.get(key)
            assert cached_value == f"warm_value_{key}"
    
    async def test_warming_stats(self, cache_with_warming):
        """Test warming statistics collection."""
        cache, warming_manager = cache_with_warming
        
        async def mock_factory(key: str) -> str:
            return f"stats_value_{key}"
        
        rule = WarmingRule(
            key_pattern="stats:*",
            factory_func=mock_factory
        )
        warming_manager.add_warming_rule("stats:*", rule)
        
        # Perform some warming operations
        await warming_manager.warm_cache(["stats:key1"], WarmingStrategy.EAGER)
        
        # Get stats
        stats = await warming_manager.get_warming_stats()
        
        assert "warming_rules_count" in stats
        assert "stats" in stats
        assert stats["warming_rules_count"] >= 1


class TestCacheDecorators:
    """Test cache decorators functionality."""
    
    @pytest.fixture
    async def setup_global_cache(self):
        """Setup global cache for decorators."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = TieredCache(l3_cache_dir=temp_dir)
            set_global_cache(cache)
            yield cache
            await cache.shutdown()
    
    async def test_basic_cache_decorator(self, setup_global_cache):
        """Test basic cache decorator functionality."""
        call_count = 0
        
        @cached(ttl=60, key_prefix="test_func")
        async def expensive_function(x: int, y: str) -> str:\n            nonlocal call_count\n            call_count += 1\n            await asyncio.sleep(0.01)  # Simulate work\n            return f\"result_{x}_{y}\"\n        \n        # First call - should execute function\n        result1 = await expensive_function(1, \"test\")\n        assert result1 == \"result_1_test\"\n        assert call_count == 1\n        \n        # Second call - should use cache\n        result2 = await expensive_function(1, \"test\")\n        assert result2 == \"result_1_test\"\n        assert call_count == 1  # Function not called again\n        \n        # Different parameters - should execute function\n        result3 = await expensive_function(2, \"test\")\n        assert result3 == \"result_2_test\"\n        assert call_count == 2\n    \n    async def test_specialized_decorators(self, setup_global_cache):\n        \"\"\"Test specialized cache decorators.\"\"\"\n        symbol_call_count = 0\n        search_call_count = 0\n        \n        @cache_symbol_lookup(ttl=120)\n        async def lookup_symbol(symbol_name: str) -> Dict[str, Any]:\n            nonlocal symbol_call_count\n            symbol_call_count += 1\n            return {\"name\": symbol_name, \"type\": \"function\", \"line\": 42}\n        \n        @cached(ttl=300, tier_hint=CacheTier.L2, compress_large_values=True)\n        async def search_code(query: str) -> List[Dict[str, Any]]:\n            nonlocal search_call_count\n            search_call_count += 1\n            # Simulate large search results\n            return [{\"file\": f\"file{i}.py\", \"line\": i} for i in range(100)]\n        \n        # Test symbol lookup caching\n        result1 = await lookup_symbol(\"test_function\")\n        assert result1[\"name\"] == \"test_function\"\n        assert symbol_call_count == 1\n        \n        result2 = await lookup_symbol(\"test_function\")\n        assert result2 == result1\n        assert symbol_call_count == 1  # Cached\n        \n        # Test search caching with large data\n        search_result = await search_code(\"test query\")\n        assert len(search_result) == 100\n        assert search_call_count == 1\n    \n    async def test_custom_key_strategy(self, setup_global_cache):\n        \"\"\"Test custom key generation strategies.\"\"\"\n        call_count = 0\n        \n        @cached(\n            ttl=60,\n            key_strategy=CacheKeyStrategy.ARGS_ONLY,\n            skip_args={1}  # Skip second argument\n        )\n        async def function_with_custom_key(important: str, ignored: str, also_important: int) -> str:\n            nonlocal call_count\n            call_count += 1\n            return f\"{important}_{also_important}\"\n        \n        # These should generate the same cache key (ignoring second arg)\n        result1 = await function_with_custom_key(\"test\", \"ignore1\", 42)\n        result2 = await function_with_custom_key(\"test\", \"ignore2\", 42)\n        \n        assert result1 == result2\n        assert call_count == 1  # Second call used cache


class TestPerformanceMonitoring:
    \"\"\"Test performance monitoring functionality.\"\"\"\n    \n    @pytest.fixture\n    async def monitored_cache(self):\n        \"\"\"Create cache with performance monitoring.\"\"\"\n        with tempfile.TemporaryDirectory() as temp_dir:\n            cache = TieredCache(l3_cache_dir=temp_dir)\n            monitor = PerformanceMonitor(cache, report_interval=1)  # 1 second for testing\n            yield cache, monitor\n            await monitor.shutdown()\n            await cache.shutdown()\n    \n    async def test_metrics_collection(self, monitored_cache):\n        \"\"\"Test that metrics are collected properly.\"\"\"\n        cache, monitor = monitored_cache\n        \n        # Perform some cache operations\n        for i in range(10):\n            await cache.set(f\"key_{i}\", f\"value_{i}\", ttl=60)\n            await cache.get(f\"key_{i}\")\n        \n        # Wait for metrics collection\n        await asyncio.sleep(2)\n        \n        # Check that metrics were collected\n        assert len(monitor.metrics) > 0\n        assert \"hit_rate\" in monitor.metrics\n    \n    async def test_performance_summary(self, monitored_cache):\n        \"\"\"Test performance summary generation.\"\"\"\n        cache, monitor = monitored_cache\n        \n        # Generate some activity\n        for i in range(5):\n            await cache.set(f\"perf_key_{i}\", f\"value_{i}\", ttl=60)\n            await cache.get(f\"perf_key_{i}\")\n        \n        await asyncio.sleep(1.5)  # Wait for monitoring\n        \n        summary = monitor.get_performance_summary(time_window=60)\n        \n        assert \"metrics\" in summary\n        assert \"trends\" in summary\n        assert \"recommendations\" in summary\n        assert \"time_window_seconds\" in summary\n    \n    async def test_custom_thresholds(self, monitored_cache):\n        \"\"\"Test custom performance thresholds.\"\"\"\n        cache, monitor = monitored_cache\n        \n        # Add a custom threshold\n        custom_threshold = PerformanceThreshold(\n            metric_name=\"test_metric\",\n            warning_threshold=50.0,\n            critical_threshold=100.0,\n            comparison=\"greater\"\n        )\n        monitor.add_custom_threshold(custom_threshold)\n        \n        # Simulate exceeding threshold\n        for _ in range(10):\n            monitor._record_metric(\"test_metric\", 75.0, time.time())\n        \n        await monitor._check_thresholds()\n        \n        # Should have generated an alert\n        assert len(monitor.alerts) > 0\n        alert = monitor.alerts[-1]\n        assert alert.level == AlertLevel.WARNING\n        assert alert.metric_name == \"test_metric\"


class TestGPUAcceleration:\n    \"\"\"Test GPU acceleration functionality.\"\"\"\n    \n    async def test_gpu_accelerator_initialization(self):\n        \"\"\"Test GPU accelerator initialization.\"\"\"\n        accelerator = get_gpu_accelerator(use_gpu=True)\n        \n        # Should initialize without errors\n        assert accelerator is not None\n        \n        # Check GPU stats\n        stats = accelerator.get_gpu_stats()\n        assert \"gpu_available\" in stats\n        assert \"backend\" in stats\n    \n    async def test_batch_hashing(self):\n        \"\"\"Test batch hashing operations.\"\"\"\n        accelerator = get_gpu_accelerator(use_gpu=True)\n        \n        keys = [f\"test_key_{i}\" for i in range(100)]\n        hashed_keys = await accelerator.batch_hash_keys(keys)\n        \n        assert len(hashed_keys) == len(keys)\n        assert all(isinstance(hk, str) for hk in hashed_keys)\n        assert len(set(hashed_keys)) == len(keys)  # All unique\n    \n    async def test_batch_compression(self):\n        \"\"\"Test batch compression operations.\"\"\"\n        accelerator = get_gpu_accelerator(use_gpu=True)\n        \n        # Create test data\n        test_data = [f\"test_data_{i}\" * 100 for i in range(50)]  # Make it compressible\n        test_bytes = [data.encode() for data in test_data]\n        \n        compressed = await accelerator.compress_batch(test_bytes)\n        \n        assert len(compressed) == len(test_bytes)\n        assert all(isinstance(cb, bytes) for cb in compressed)\n    \n    async def test_similarity_search(self):\n        \"\"\"Test GPU-accelerated similarity search.\"\"\"\n        import numpy as np\n        \n        accelerator = get_gpu_accelerator(use_gpu=True)\n        \n        # Create test embeddings\n        query_embedding = np.random.rand(128).astype(np.float32)\n        cache_embeddings = {\n            f\"key_{i}\": np.random.rand(128).astype(np.float32)\n            for i in range(100)\n        }\n        \n        # Add one very similar embedding\n        cache_embeddings[\"similar_key\"] = query_embedding + np.random.rand(128) * 0.01\n        \n        results = await accelerator.similarity_search(query_embedding, cache_embeddings, top_k=5)\n        \n        assert len(results) <= 5\n        assert all(isinstance(r, tuple) and len(r) == 2 for r in results)\n        \n        # Check that results are sorted by similarity\n        similarities = [r[1] for r in results]\n        assert similarities == sorted(similarities, reverse=True)


class TestIntegration:\n    \"\"\"Integration tests for the complete cache system.\"\"\"\n    \n    async def test_end_to_end_caching_workflow(self):\n        \"\"\"Test complete caching workflow.\"\"\"\n        with tempfile.TemporaryDirectory() as temp_dir:\n            # Setup complete cache system\n            cache = TieredCache(l3_cache_dir=temp_dir)\n            warming_manager = CacheWarmingManager(cache)\n            monitor = PerformanceMonitor(cache, report_interval=1)\n            set_global_cache(cache, warming_manager)\n            \n            try:\n                # Define a test function with caching\n                call_count = 0\n                \n                @cache_symbol_lookup(ttl=300)\n                async def get_symbol_info(symbol: str) -> Dict[str, Any]:\n                    nonlocal call_count\n                    call_count += 1\n                    await asyncio.sleep(0.01)  # Simulate work\n                    return {\n                        \"symbol\": symbol,\n                        \"type\": \"function\",\n                        \"file\": f\"{symbol}.py\",\n                        \"line\": call_count * 10\n                    }\n                \n                # Setup warming rule\n                async def symbol_factory(key: str) -> Dict[str, Any]:\n                    symbol = key.replace(\"symbol:\", \"\")\n                    return await get_symbol_info(symbol)\n                \n                rule = create_symbol_warming_rule(symbol_factory)\n                warming_manager.add_warming_rule(\"symbol:*\", rule)\n                \n                # Test normal caching\n                result1 = await get_symbol_info(\"test_function\")\n                assert result1[\"symbol\"] == \"test_function\"\n                assert call_count == 1\n                \n                result2 = await get_symbol_info(\"test_function\")\n                assert result2 == result1\n                assert call_count == 1  # Cached\n                \n                # Test cache warming\n                warm_results = await warming_manager.warm_cache(\n                    [\"symbol:warm_func1\", \"symbol:warm_func2\"],\n                    WarmingStrategy.EAGER\n                )\n                assert all(warm_results.values())\n                \n                # Test cache invalidation\n                await warming_manager.invalidate(\"symbol:test_function\")\n                \n                # Wait for monitoring\n                await asyncio.sleep(1.5)\n                \n                # Get performance summary\n                summary = monitor.get_performance_summary(60)\n                assert \"metrics\" in summary\n                assert \"hit_rate\" in summary[\"metrics\"]\n                \n                # Test cache statistics\n                cache_stats = await cache.get_stats()\n                assert cache_stats[\"overall\"][\"total_requests\"] > 0\n                \n            finally:\n                # Cleanup\n                await monitor.shutdown()\n                await warming_manager.shutdown()\n                await cache.shutdown()\n    \n    async def test_performance_under_load(self):\n        \"\"\"Test cache performance under load.\"\"\"\n        with tempfile.TemporaryDirectory() as temp_dir:\n            cache = TieredCache(\n                l1_max_size=500,\n                l1_max_memory_mb=50,\n                l3_cache_dir=temp_dir\n            )\n            \n            try:\n                start_time = time.time()\n                \n                # Perform many cache operations\n                tasks = []\n                for i in range(1000):\n                    tasks.append(cache.set(f\"load_key_{i}\", f\"value_{i}\" * 100, ttl=300))\n                \n                await asyncio.gather(*tasks)\n                \n                # Test retrieval performance\n                tasks = []\n                for i in range(1000):\n                    tasks.append(cache.get(f\"load_key_{i}\"))\n                \n                results = await asyncio.gather(*tasks)\n                \n                end_time = time.time()\n                total_time = end_time - start_time\n                \n                # Check that operations completed in reasonable time\n                assert total_time < 10.0  # Should complete in under 10 seconds\n                \n                # Check that all operations succeeded\n                assert all(r is not None for r in results)\n                \n                # Check cache statistics\n                stats = await cache.get_stats()\n                hit_rate = stats[\"overall\"][\"hit_rate\"]\n                assert hit_rate > 0.9  # Should have high hit rate\n                \n            finally:\n                await cache.shutdown()\n\n\nif __name__ == \"__main__\":\n    # Run basic tests if executed directly\n    async def run_basic_tests():\n        print(\"Running basic cache tests...\")\n        \n        # Test tiered cache\n        with tempfile.TemporaryDirectory() as temp_dir:\n            cache = TieredCache(l3_cache_dir=temp_dir)\n            \n            await cache.set(\"test\", \"value\", ttl=60)\n            result = await cache.get(\"test\")\n            assert result == \"value\"\n            print(\"✓ Basic cache operations work\")\n            \n            stats = await cache.get_stats()\n            assert stats[\"overall\"][\"total_requests\"] > 0\n            print(\"✓ Cache statistics work\")\n            \n            await cache.shutdown()\n        \n        print(\"All basic tests passed!\")\n    \n    asyncio.run(run_basic_tests())