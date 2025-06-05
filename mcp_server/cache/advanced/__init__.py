"""Advanced multi-tier caching system with intelligent features."""

from .tiered_cache import (
    TieredCache,
    CacheTier,
    CacheStats,
    AccessPattern
)

from .cache_warming import (
    CacheWarmingManager,
    WarmingRule,
    InvalidationRule,
    WarmingStrategy,
    InvalidationStrategy,
    create_symbol_warming_rule,
    create_search_warming_rule,
    create_file_invalidation_rule
)

from .decorators import (
    cached,
    cache_symbol_lookup,
    cache_search_results,
    cache_file_analysis,
    cache_project_metadata,
    cache_semantic_search,
    CacheKeyStrategy,
    CacheConfig,
    set_global_cache,
    invalidate_by_tags,
    warm_cache_for_function,
    get_cache_stats,
    CacheContext
)

from .performance_monitor import (
    PerformanceMonitor,
    PerformanceMetric,
    PerformanceAlert,
    PerformanceThreshold,
    AlertLevel
)

__all__ = [
    # Core cache
    "TieredCache",
    "CacheTier", 
    "CacheStats",
    "AccessPattern",
    
    # Warming and invalidation
    "CacheWarmingManager",
    "WarmingRule",
    "InvalidationRule",
    "WarmingStrategy",
    "InvalidationStrategy",
    "create_symbol_warming_rule",
    "create_search_warming_rule",
    "create_file_invalidation_rule",
    
    # Decorators
    "cached",
    "cache_symbol_lookup",
    "cache_search_results", 
    "cache_file_analysis",
    "cache_project_metadata",
    "cache_semantic_search",
    "CacheKeyStrategy",
    "CacheConfig",
    "set_global_cache",
    "invalidate_by_tags",
    "warm_cache_for_function",
    "get_cache_stats",
    "CacheContext",
    
    # Performance monitoring
    "PerformanceMonitor",
    "PerformanceMetric",
    "PerformanceAlert", 
    "PerformanceThreshold",
    "AlertLevel"
]