"""
Comprehensive tests for the cache system.
"""

import asyncio
import time

import pytest

from mcp_server.cache import (
    CacheBackendType,
    CacheConfig,
    CacheEntry,
    CacheManager,
    CacheManagerFactory,
    MemoryCacheBackend,
    QueryCacheConfig,
    QueryResultCache,
    QueryType,
)
from mcp_server.plugin_base import SearchResult, SymbolDef


class TestCacheEntry:
    """Test CacheEntry functionality."""

    def test_cache_entry_creation(self):
        """Test basic cache entry creation."""
        entry = CacheEntry(
            key="test_key",
            value="test_value",
            created_at=time.time(),
            expires_at=time.time() + 3600,
        )

        assert entry.key == "test_key"
        assert entry.value == "test_value"
        assert entry.access_count == 0
        assert not entry.is_expired()

    def test_cache_entry_expiration(self):
        """Test cache entry expiration."""
        past_time = time.time() - 1000
        entry = CacheEntry(
            key="expired_key",
            value="expired_value",
            created_at=past_time,
            expires_at=past_time + 500,  # Already expired
        )

        assert entry.is_expired()

    def test_cache_entry_touch(self):
        """Test cache entry access tracking."""
        entry = CacheEntry(key="test_key", value="test_value", created_at=time.time())

        initial_access_count = entry.access_count
        initial_last_accessed = entry.last_accessed

        time.sleep(0.01)  # Small delay
        entry.touch()

        assert entry.access_count == initial_access_count + 1
        assert entry.last_accessed > initial_last_accessed

    def test_cache_entry_serialization(self):
        """Test cache entry serialization."""
        entry = CacheEntry(
            key="test_key",
            value={"nested": "data"},
            created_at=time.time(),
            tags={"tag1", "tag2"},
        )

        data = entry.to_dict()
        restored_entry = CacheEntry.from_dict(data)

        assert restored_entry.key == entry.key
        assert restored_entry.value == entry.value
        assert restored_entry.tags == entry.tags


class TestMemoryCacheBackend:
    """Test MemoryCacheBackend functionality."""

    @pytest.fixture
    async def memory_backend(self):
        """Create a memory cache backend for testing."""
        backend = MemoryCacheBackend(max_size=10, max_memory_mb=1)
        yield backend
        await backend.shutdown()

    @pytest.mark.asyncio
    async def test_basic_operations(self, memory_backend):
        """Test basic cache operations."""
        # Test set and get
        assert await memory_backend.set("key1", "value1", ttl=3600)
        entry = await memory_backend.get("key1")
        assert entry is not None
        assert entry.value == "value1"

        # Test exists
        assert await memory_backend.exists("key1")
        assert not await memory_backend.exists("nonexistent")

        # Test delete
        assert await memory_backend.delete("key1")
        assert not await memory_backend.exists("key1")

    @pytest.mark.asyncio
    async def test_ttl_expiration(self, memory_backend):
        """Test TTL-based expiration."""
        # Set with short TTL
        await memory_backend.set("short_lived", "value", ttl=1)

        # Should exist immediately
        entry = await memory_backend.get("short_lived")
        assert entry is not None

        # Wait for expiration
        await asyncio.sleep(1.1)

        # Should be expired
        entry = await memory_backend.get("short_lived")
        assert entry is None

    @pytest.mark.asyncio
    async def test_lru_eviction(self, memory_backend):
        """Test LRU eviction when max size is reached."""
        # Fill cache to capacity
        for i in range(10):
            await memory_backend.set(f"key{i}", f"value{i}")

        # All keys should exist
        for i in range(10):
            assert await memory_backend.exists(f"key{i}")

        # Add one more to trigger eviction
        await memory_backend.set("new_key", "new_value")

        # First key should be evicted (LRU)
        assert not await memory_backend.exists("key0")
        assert await memory_backend.exists("new_key")

    @pytest.mark.asyncio
    async def test_tag_invalidation(self, memory_backend):
        """Test tag-based invalidation."""
        # Set entries with tags
        await memory_backend.set("key1", "value1", tags={"tag1", "tag2"})
        await memory_backend.set("key2", "value2", tags={"tag2", "tag3"})
        await memory_backend.set("key3", "value3", tags={"tag3"})

        # Invalidate by tag2
        count = await memory_backend.invalidate_by_tags({"tag2"})
        assert count == 2  # key1 and key2 should be invalidated

        # Check remaining entries
        assert not await memory_backend.exists("key1")
        assert not await memory_backend.exists("key2")
        assert await memory_backend.exists("key3")

    @pytest.mark.asyncio
    async def test_cleanup_expired(self, memory_backend):
        """Test cleanup of expired entries."""
        # Add some entries with different TTLs
        await memory_backend.set("key1", "value1", ttl=1)
        await memory_backend.set("key2", "value2", ttl=3600)
        await memory_backend.set("key3", "value3", ttl=1)

        # Wait for some to expire
        await asyncio.sleep(1.1)

        # Run cleanup
        count = await memory_backend.cleanup_expired()
        assert count == 2  # key1 and key3 should be cleaned up

        # Check remaining
        assert not await memory_backend.exists("key1")
        assert await memory_backend.exists("key2")
        assert not await memory_backend.exists("key3")

    @pytest.mark.asyncio
    async def test_get_stats(self, memory_backend):
        """Test getting cache statistics."""
        # Add some entries
        await memory_backend.set("key1", "value1")
        await memory_backend.set("key2", "value2")

        # Access one to generate hits/misses
        await memory_backend.get("key1")
        await memory_backend.get("nonexistent")

        stats = await memory_backend.get_stats()

        assert stats["backend_type"] == "memory"
        assert stats["entries"] == 2
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.5


class TestCacheManager:
    """Test CacheManager functionality."""

    @pytest.fixture
    async def cache_manager(self):
        """Create a cache manager for testing."""
        config = CacheConfig(
            backend_type=CacheBackendType.MEMORY, max_entries=100, default_ttl=3600
        )
        manager = CacheManager(config)
        await manager.initialize()
        yield manager
        await manager.shutdown()

    @pytest.mark.asyncio
    async def test_basic_operations(self, cache_manager):
        """Test basic cache manager operations."""
        # Test set and get
        assert await cache_manager.set("test_key", "test_value")
        value = await cache_manager.get("test_key")
        assert value == "test_value"

        # Test default value
        default_value = await cache_manager.get("nonexistent", "default")
        assert default_value == "default"

        # Test exists
        assert await cache_manager.exists("test_key")
        assert not await cache_manager.exists("nonexistent")

        # Test delete
        assert await cache_manager.delete("test_key")
        assert not await cache_manager.exists("test_key")

    @pytest.mark.asyncio
    async def test_get_or_set(self, cache_manager):
        """Test get_or_set functionality."""
        call_count = 0

        async def factory():
            nonlocal call_count
            call_count += 1
            return f"generated_value_{call_count}"

        # First call should use factory
        value1 = await cache_manager.get_or_set("computed_key", factory)
        assert value1 == "generated_value_1"
        assert call_count == 1

        # Second call should use cache
        value2 = await cache_manager.get_or_set("computed_key", factory)
        assert value2 == "generated_value_1"  # Same value from cache
        assert call_count == 1  # Factory not called again

    @pytest.mark.asyncio
    async def test_mget_mset(self, cache_manager):
        """Test multiple get/set operations."""
        # Test mset
        data = {"key1": "value1", "key2": "value2", "key3": "value3"}
        count = await cache_manager.mset(data)
        assert count == 3

        # Test mget
        result = await cache_manager.mget(["key1", "key2", "key4"])
        assert result == {"key1": "value1", "key2": "value2"}
        assert "key4" not in result  # Nonexistent key

    @pytest.mark.asyncio
    async def test_tag_invalidation(self, cache_manager):
        """Test tag-based invalidation."""
        # Set entries with tags
        await cache_manager.set("key1", "value1", tags={"user:123", "type:data"})
        await cache_manager.set("key2", "value2", tags={"user:456", "type:data"})
        await cache_manager.set("key3", "value3", tags={"user:123", "type:config"})

        # Invalidate by user tag
        count = await cache_manager.invalidate_by_tags({"user:123"})
        assert count == 2  # key1 and key3

        # Check remaining
        assert not await cache_manager.exists("key1")
        assert await cache_manager.exists("key2")
        assert not await cache_manager.exists("key3")

    @pytest.mark.asyncio
    async def test_cache_warming(self, cache_manager):
        """Test cache warming functionality."""

        async def factory(key: str):
            return f"warmed_value_for_{key}"

        keys_to_warm = ["warm_key1", "warm_key2", "warm_key3"]
        count = await cache_manager.warm_cache(keys_to_warm, factory)
        assert count == 3

        # Check that keys are cached
        for key in keys_to_warm:
            value = await cache_manager.get(key)
            assert value == f"warmed_value_for_{key}"

    @pytest.mark.asyncio
    async def test_metrics(self, cache_manager):
        """Test metrics collection."""
        # Perform some operations
        await cache_manager.set("metric_key", "metric_value")
        await cache_manager.get("metric_key")
        await cache_manager.get("nonexistent")

        metrics = await cache_manager.get_metrics()

        assert metrics.hits >= 1
        assert metrics.misses >= 1
        assert metrics.sets >= 1
        assert metrics.hit_rate > 0


class TestQueryResultCache:
    """Test QueryResultCache functionality."""

    @pytest.fixture
    async def query_cache(self):
        """Create a query result cache for testing."""
        cache_manager = CacheManagerFactory.create_memory_cache()
        await cache_manager.initialize()

        config = QueryCacheConfig(enabled=True, default_ttl=3600, search_ttl=600)

        query_cache = QueryResultCache(cache_manager, config)
        yield query_cache
        await cache_manager.shutdown()

    @pytest.mark.asyncio
    async def test_symbol_lookup_caching(self, query_cache):
        """Test symbol lookup result caching."""
        symbol_def = SymbolDef(
            name="test_function",
            type="function",
            file_path="/test/file.py",
            line_number=10,
            column_number=5,
        )

        # Cache result
        success = await query_cache.cache_result(
            QueryType.SYMBOL_LOOKUP, symbol_def, symbol="test_function"
        )
        assert success

        # Retrieve from cache
        cached_result = await query_cache.get_cached_result(
            QueryType.SYMBOL_LOOKUP, symbol="test_function"
        )
        assert cached_result is not None
        assert cached_result.name == "test_function"
        assert cached_result.file_path == "/test/file.py"

    @pytest.mark.asyncio
    async def test_search_results_caching(self, query_cache):
        """Test search results caching."""
        search_results = [
            SearchResult(
                name="result1",
                type="function",
                file_path="/test/file1.py",
                line_number=5,
                score=0.9,
            ),
            SearchResult(
                name="result2",
                type="class",
                file_path="/test/file2.py",
                line_number=15,
                score=0.8,
            ),
        ]

        # Cache results
        success = await query_cache.cache_result(
            QueryType.SEARCH, search_results, q="test_query", semantic=False, limit=20
        )
        assert success

        # Retrieve from cache
        cached_results = await query_cache.get_cached_result(
            QueryType.SEARCH, q="test_query", semantic=False, limit=20
        )
        assert cached_results is not None
        assert len(cached_results) == 2
        assert cached_results[0].name == "result1"

    @pytest.mark.asyncio
    async def test_file_invalidation(self, query_cache):
        """Test file-based cache invalidation."""
        # Cache a symbol lookup result that depends on a file
        symbol_def = SymbolDef(
            name="file_function",
            type="function",
            file_path="/test/target_file.py",
            line_number=10,
        )

        await query_cache.cache_result(QueryType.SYMBOL_LOOKUP, symbol_def, symbol="file_function")

        # Verify it's cached
        cached_result = await query_cache.get_cached_result(
            QueryType.SYMBOL_LOOKUP, symbol="file_function"
        )
        assert cached_result is not None

        # Invalidate by file
        count = await query_cache.invalidate_file_queries("/test/target_file.py")
        assert count >= 1

        # Verify it's no longer cached
        cached_result = await query_cache.get_cached_result(
            QueryType.SYMBOL_LOOKUP, symbol="file_function"
        )
        assert cached_result is None

    @pytest.mark.asyncio
    async def test_query_type_invalidation(self, query_cache):
        """Test invalidation by query type."""
        # Cache different types of queries
        await query_cache.cache_result(QueryType.SEARCH, ["result1"], q="query1")

        await query_cache.cache_result(
            QueryType.SYMBOL_LOOKUP,
            SymbolDef(name="symbol1", type="function"),
            symbol="symbol1",
        )

        # Invalidate all search queries
        count = await query_cache.invalidate_by_query_type(QueryType.SEARCH)
        assert count >= 1

        # Search should be gone, symbol lookup should remain
        search_result = await query_cache.get_cached_result(QueryType.SEARCH, q="query1")
        assert search_result is None

        symbol_result = await query_cache.get_cached_result(
            QueryType.SYMBOL_LOOKUP, symbol="symbol1"
        )
        assert symbol_result is not None

    @pytest.mark.asyncio
    async def test_semantic_query_invalidation(self, query_cache):
        """Test semantic query invalidation."""
        # Cache semantic and non-semantic search results
        await query_cache.cache_result(
            QueryType.SEARCH, ["semantic_result"], q="test", semantic=True
        )

        await query_cache.cache_result(
            QueryType.SEARCH, ["regular_result"], q="test", semantic=False
        )

        # Invalidate semantic queries
        count = await query_cache.invalidate_semantic_queries()
        assert count >= 1

        # Semantic should be gone, regular should remain
        semantic_result = await query_cache.get_cached_result(
            QueryType.SEARCH, q="test", semantic=True
        )
        assert semantic_result is None

        regular_result = await query_cache.get_cached_result(
            QueryType.SEARCH, q="test", semantic=False
        )
        assert regular_result is not None

    @pytest.mark.asyncio
    async def test_cache_stats(self, query_cache):
        """Test cache statistics."""
        # Perform some operations
        await query_cache.cache_result(QueryType.SEARCH, ["result"], q="stats_test")

        await query_cache.get_cached_result(QueryType.SEARCH, q="stats_test")

        stats = await query_cache.get_cache_stats()

        assert stats["enabled"] is True
        assert "cache_metrics" in stats
        assert "query_frequency" in stats


class TestCacheManagerFactory:
    """Test CacheManagerFactory functionality."""

    @pytest.mark.asyncio
    async def test_create_memory_cache(self):
        """Test creating memory cache."""
        cache_manager = CacheManagerFactory.create_memory_cache(max_entries=50, max_memory_mb=10)

        await cache_manager.initialize()

        assert cache_manager.config.backend_type == CacheBackendType.MEMORY
        assert cache_manager.config.max_entries == 50
        assert cache_manager.config.max_memory_mb == 10

        await cache_manager.shutdown()

    def test_create_redis_cache(self):
        """Test creating Redis cache configuration."""
        cache_manager = CacheManagerFactory.create_redis_cache(
            redis_url="redis://test:6379", redis_db=1
        )

        assert cache_manager.config.backend_type == CacheBackendType.REDIS
        assert cache_manager.config.redis_url == "redis://test:6379"
        assert cache_manager.config.redis_db == 1

    def test_create_hybrid_cache(self):
        """Test creating hybrid cache configuration."""
        cache_manager = CacheManagerFactory.create_hybrid_cache(max_entries=200, max_memory_mb=20)

        assert cache_manager.config.backend_type == CacheBackendType.HYBRID
        assert cache_manager.config.max_entries == 200
        assert cache_manager.config.max_memory_mb == 20


class TestCacheDecorators:
    """Test cache decorator functionality."""

    @pytest.fixture
    async def decorated_query_cache(self):
        """Create query cache with decorators for testing."""
        cache_manager = CacheManagerFactory.create_memory_cache()
        await cache_manager.initialize()

        config = QueryCacheConfig(enabled=True)
        query_cache = QueryResultCache(cache_manager, config)

        yield query_cache
        await cache_manager.shutdown()

    @pytest.mark.asyncio
    async def test_symbol_lookup_decorator(self, decorated_query_cache):
        """Test symbol lookup caching decorator."""
        from mcp_server.cache import cache_symbol_lookup

        call_count = 0

        @cache_symbol_lookup(decorated_query_cache)
        async def lookup_symbol(symbol: str):
            nonlocal call_count
            call_count += 1
            return SymbolDef(name=symbol, type="function", file_path=f"/test/{symbol}.py")

        # First call should execute function
        result1 = await lookup_symbol(symbol="test_func")
        assert call_count == 1
        assert result1.name == "test_func"

        # Second call should use cache
        result2 = await lookup_symbol(symbol="test_func")
        assert call_count == 1  # No additional call
        assert result2.name == "test_func"

    @pytest.mark.asyncio
    async def test_search_decorator(self, decorated_query_cache):
        """Test search caching decorator."""
        from mcp_server.cache import cache_search

        call_count = 0

        @cache_search(decorated_query_cache)
        async def search_symbols(q: str, limit: int = 10):
            nonlocal call_count
            call_count += 1
            return [
                SearchResult(
                    name=f"result_{i}",
                    type="function",
                    file_path=f"/test/file_{i}.py",
                    score=0.9 - i * 0.1,
                )
                for i in range(min(limit, 3))
            ]

        # First call should execute function
        results1 = await search_symbols(q="test", limit=5)
        assert call_count == 1
        assert len(results1) == 3

        # Second call should use cache
        results2 = await search_symbols(q="test", limit=5)
        assert call_count == 1  # No additional call
        assert len(results2) == 3
        assert results2[0].name == "result_0"


if __name__ == "__main__":
    pytest.main([__file__])
