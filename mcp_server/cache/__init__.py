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
    MemoryCacheBackend,
    RedisCacheBackend,
    HybridCacheBackend,
    CacheEntry
)

from .cache_manager import (
    ICacheManager,
    CacheManager,
    CacheManagerFactory,
    CacheConfig,
    CacheBackendType,
    CacheMetrics
)

from .query_cache import (
    QueryResultCache,
    QueryCacheConfig,
    QueryType,
    InvalidationStrategy,
    CachedQuery,
    QueryCacheDecorator,
    cache_symbol_lookup,
    cache_search,
    cache_semantic_search,
    cache_file_symbols,
    cache_project_status
)

# Advanced cache features
try:
    from .advanced import (
        TieredCache,
        CacheTier,
        CacheWarmingManager,
        WarmingStrategy,
        PerformanceMonitor,
        cached as advanced_cached,
        cache_symbol_lookup as advanced_cache_symbol_lookup,
        cache_search_results,
        cache_file_analysis,
        set_global_cache,
        get_gpu_accelerator
    )
    ADVANCED_CACHE_AVAILABLE = True
except ImportError:
    ADVANCED_CACHE_AVAILABLE = False

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
    "cache_project_status"
]

# Add advanced cache exports if available
if ADVANCED_CACHE_AVAILABLE:
    __all__.extend([
        "TieredCache",
        "CacheTier", 
        "CacheWarmingManager",
        "WarmingStrategy",
        "PerformanceMonitor",
        "advanced_cached",
        "advanced_cache_symbol_lookup",
        "cache_search_results",
        "cache_file_analysis",
        "set_global_cache",
        "get_gpu_accelerator",
        "ADVANCED_CACHE_AVAILABLE"
    ])

__all__.append("ADVANCED_CACHE_AVAILABLE")

__version__ = "1.0.0"