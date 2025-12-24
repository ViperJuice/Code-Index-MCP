"""
Cache package for MCP Server.

Provides comprehensive caching functionality with multiple backends,
query result caching, and intelligent invalidation strategies.

Example usage:
    from mcp_server.cache import CacheManagerFactory, QueryResultCache, QueryCacheConfig

    # Create a memory cache
    cache_manager = CacheManagerFactory.create_memory_cache()
    await cache_manager.initialize()

    # Create query cache
    query_config = QueryCacheConfig(enabled=True, default_ttl=600)
    query_cache = QueryResultCache(cache_manager, query_config)

    # Use in application
    result = await query_cache.get_cached_result(QueryType.SEARCH, q="test")
"""

from .backends import (
    CacheBackend,
    CacheEntry,
    HybridCacheBackend,
    MemoryCacheBackend,
    RedisCacheBackend,
)
from .cache_manager import (
    CacheBackendType,
    CacheConfig,
    CacheManager,
    CacheManagerFactory,
    CacheMetrics,
    ICacheManager,
)
from .query_cache import (
    CachedQuery,
    InvalidationStrategy,
    QueryCacheConfig,
    QueryCacheDecorator,
    QueryResultCache,
    QueryType,
    cache_file_symbols,
    cache_project_status,
    cache_search,
    cache_semantic_search,
    cache_symbol_lookup,
)

__all__ = [
    # Backend classes
    "CacheBackend",
    "MemoryCacheBackend",
    "RedisCacheBackend",
    "HybridCacheBackend",
    "CacheEntry",
    # Cache manager
    "ICacheManager",
    "CacheManager",
    "CacheManagerFactory",
    "CacheConfig",
    "CacheBackendType",
    "CacheMetrics",
    # Query cache
    "QueryResultCache",
    "QueryCacheConfig",
    "QueryType",
    "InvalidationStrategy",
    "CachedQuery",
    "QueryCacheDecorator",
    "cache_symbol_lookup",
    "cache_search",
    "cache_semantic_search",
    "cache_file_symbols",
    "cache_project_status",
]

__version__ = "1.0.0"
