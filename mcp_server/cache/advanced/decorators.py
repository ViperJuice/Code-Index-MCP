"""Cache decorators for MCP methods with intelligent caching strategies."""
import asyncio
import functools
import hashlib
import json
import logging
import time
from typing import Any, Callable, Optional, Set, Union, Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum

from .tiered_cache import TieredCache, CacheTier
from .cache_warming import CacheWarmingManager, WarmingStrategy

logger = logging.getLogger(__name__)


class CacheKeyStrategy(Enum):
    """Strategies for generating cache keys."""
    ARGS_ONLY = "args_only"          # Use only positional args
    KWARGS_ONLY = "kwargs_only"      # Use only keyword args
    ALL_PARAMS = "all_params"        # Use all parameters
    CUSTOM = "custom"                # Use custom key function


@dataclass
class CacheConfig:
    """Configuration for cache decorators."""
    ttl: int = 3600                  # Time to live in seconds
    tier_hint: Optional[CacheTier] = None  # Preferred cache tier
    key_strategy: CacheKeyStrategy = CacheKeyStrategy.ALL_PARAMS
    key_prefix: str = ""             # Prefix for cache keys
    skip_args: Set[int] = None       # Positional args to skip
    skip_kwargs: Set[str] = None     # Keyword args to skip
    tags: Set[str] = None            # Tags for invalidation
    warming_strategy: WarmingStrategy = WarmingStrategy.LAZY
    compress_large_values: bool = True  # Compress values > 1MB
    max_key_length: int = 250        # Maximum key length


# Global cache instance (set by application)
_global_cache: Optional[TieredCache] = None
_global_warming_manager: Optional[CacheWarmingManager] = None


def set_global_cache(cache: TieredCache, warming_manager: Optional[CacheWarmingManager] = None):
    """Set the global cache instance for decorators."""
    global _global_cache, _global_warming_manager
    _global_cache = cache
    _global_warming_manager = warming_manager


def _get_cache() -> TieredCache:
    """Get the global cache instance."""
    if _global_cache is None:
        raise RuntimeError("Global cache not set. Call set_global_cache() first.")
    return _global_cache


def _get_warming_manager() -> Optional[CacheWarmingManager]:
    """Get the global warming manager instance."""
    return _global_warming_manager


def _generate_cache_key(
    func: Callable,
    config: CacheConfig,
    args: tuple,
    kwargs: dict,
    custom_key_func: Optional[Callable] = None
) -> str:
    """Generate cache key based on function and arguments."""
    
    if custom_key_func:
        base_key = custom_key_func(*args, **kwargs)
    else:
        # Build key components
        key_parts = []
        
        # Add function name
        key_parts.append(f"{func.__module__}.{func.__qualname__}")
        
        # Add arguments based on strategy
        if config.key_strategy in [CacheKeyStrategy.ARGS_ONLY, CacheKeyStrategy.ALL_PARAMS]:
            # Add positional arguments (skip specified indices)
            skip_args = config.skip_args or set()
            for i, arg in enumerate(args):
                if i not in skip_args:
                    key_parts.append(_serialize_arg(arg))
        
        if config.key_strategy in [CacheKeyStrategy.KWARGS_ONLY, CacheKeyStrategy.ALL_PARAMS]:
            # Add keyword arguments (skip specified keys)
            skip_kwargs = config.skip_kwargs or set()
            for key, value in sorted(kwargs.items()):
                if key not in skip_kwargs:
                    key_parts.append(f"{key}={_serialize_arg(value)}")
        
        base_key = "|".join(key_parts)
    
    # Add prefix if specified
    if config.key_prefix:
        base_key = f"{config.key_prefix}:{base_key}"
    
    # Hash if too long
    if len(base_key) > config.max_key_length:
        base_key = hashlib.sha256(base_key.encode()).hexdigest()[:config.max_key_length]
    
    return base_key


def _serialize_arg(arg: Any) -> str:
    """Serialize an argument for use in cache key."""
    try:
        if isinstance(arg, (str, int, float, bool)):
            return str(arg)
        elif isinstance(arg, (list, tuple)):
            return f"[{','.join(_serialize_arg(item) for item in arg)}]"
        elif isinstance(arg, dict):
            items = sorted(arg.items())
            return f"{{{','.join(f'{k}:{_serialize_arg(v)}' for k, v in items)}}}"
        elif hasattr(arg, '__dict__'):
            # For objects, use their dict representation
            return _serialize_arg(arg.__dict__)
        else:
            # Fallback to string representation
            return str(arg)
    except Exception:
        # If serialization fails, use type and id
        return f"{type(arg).__name__}:{id(arg)}"


def _should_compress(value: Any, config: CacheConfig) -> bool:
    """Determine if a value should be compressed."""
    if not config.compress_large_values:
        return False
    
    try:
        # Estimate size
        if isinstance(value, (str, bytes)):
            size = len(value)
        elif isinstance(value, (list, dict)):
            # Rough estimate
            size = len(json.dumps(value, default=str))
        else:
            # Fallback estimate
            size = 1024  # 1KB default
        
        return size > 1024 * 1024  # 1MB threshold
    except Exception:
        return False


def _compress_value(value: Any) -> Any:
    """Compress a value for storage."""
    try:
        import gzip
        import pickle
        
        serialized = pickle.dumps(value)
        compressed = gzip.compress(serialized)
        
        # Only use compression if it actually reduces size
        if len(compressed) < len(serialized):
            return {'__compressed__': True, 'data': compressed}
        else:
            return value
    except Exception as e:
        logger.warning(f"Failed to compress value: {e}")
        return value


def _decompress_value(value: Any) -> Any:
    """Decompress a value from storage."""
    try:
        if isinstance(value, dict) and value.get('__compressed__'):
            import gzip
            import pickle
            
            decompressed = gzip.decompress(value['data'])
            return pickle.loads(decompressed)
        else:
            return value
    except Exception as e:
        logger.warning(f"Failed to decompress value: {e}")
        return value


def cached(
    ttl: int = 3600,
    tier_hint: Optional[CacheTier] = None,
    key_strategy: CacheKeyStrategy = CacheKeyStrategy.ALL_PARAMS,
    key_prefix: str = "",
    skip_args: Optional[Set[int]] = None,
    skip_kwargs: Optional[Set[str]] = None,
    tags: Optional[Set[str]] = None,
    warming_strategy: WarmingStrategy = WarmingStrategy.LAZY,
    compress_large_values: bool = True,
    custom_key_func: Optional[Callable] = None,
    invalidate_on_error: bool = False
):
    """Cache decorator for MCP methods.
    
    Args:
        ttl: Time to live in seconds
        tier_hint: Preferred cache tier (L1, L2, or L3)
        key_strategy: How to generate cache keys
        key_prefix: Prefix for cache keys
        skip_args: Positional argument indices to skip in key generation
        skip_kwargs: Keyword argument names to skip in key generation
        tags: Tags for cache invalidation
        warming_strategy: Strategy for cache warming
        compress_large_values: Whether to compress large values
        custom_key_func: Custom function for generating cache keys
        invalidate_on_error: Whether to invalidate cache on function errors
    """
    
    def decorator(func: Callable) -> Callable:
        config = CacheConfig(
            ttl=ttl,
            tier_hint=tier_hint,
            key_strategy=key_strategy,
            key_prefix=key_prefix or func.__name__,
            skip_args=skip_args,
            skip_kwargs=skip_kwargs,
            tags=tags,
            warming_strategy=warming_strategy,
            compress_large_values=compress_large_values
        )
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            cache = _get_cache()
            
            # Generate cache key
            cache_key = _generate_cache_key(func, config, args, kwargs, custom_key_func)
            
            # Try to get from cache
            try:
                cached_value = await cache.get(cache_key)
                if cached_value is not None:
                    # Decompress if needed
                    result = _decompress_value(cached_value)
                    logger.debug(f"Cache hit for {func.__name__}: {cache_key}")
                    return result
            except Exception as e:
                logger.warning(f"Cache get error for {cache_key}: {e}")
            
            # Cache miss - execute function
            try:
                logger.debug(f"Cache miss for {func.__name__}: {cache_key}")
                result = await func(*args, **kwargs)
                
                # Compress if needed
                store_value = result
                if _should_compress(result, config):
                    store_value = _compress_value(result)
                
                # Store in cache
                try:
                    await cache.set(
                        cache_key,
                        store_value,
                        ttl=config.ttl,
                        tier_hint=config.tier_hint,
                        tags=config.tags
                    )
                    logger.debug(f"Cached result for {func.__name__}: {cache_key}")
                except Exception as e:
                    logger.warning(f"Cache set error for {cache_key}: {e}")
                
                return result
                
            except Exception as e:
                # Handle function errors
                if invalidate_on_error:
                    try:
                        await cache.delete(cache_key)
                        logger.debug(f"Invalidated cache for error in {func.__name__}: {cache_key}")
                    except Exception:
                        pass
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For synchronous functions, we need to handle async cache operations
            cache = _get_cache()
            
            # Generate cache key
            cache_key = _generate_cache_key(func, config, args, kwargs, custom_key_func)
            
            # Try to get from cache (synchronously)
            try:
                loop = asyncio.get_event_loop()
                cached_value = loop.run_until_complete(cache.get(cache_key))
                if cached_value is not None:
                    result = _decompress_value(cached_value)
                    logger.debug(f"Cache hit for {func.__name__}: {cache_key}")
                    return result
            except Exception as e:
                logger.warning(f"Cache get error for {cache_key}: {e}")
            
            # Cache miss - execute function
            try:
                logger.debug(f"Cache miss for {func.__name__}: {cache_key}")
                result = func(*args, **kwargs)
                
                # Compress if needed
                store_value = result
                if _should_compress(result, config):
                    store_value = _compress_value(result)
                
                # Store in cache (asynchronously)
                try:
                    loop = asyncio.get_event_loop()
                    loop.run_until_complete(cache.set(
                        cache_key,
                        store_value,
                        ttl=config.ttl,
                        tier_hint=config.tier_hint,
                        tags=config.tags
                    ))
                    logger.debug(f"Cached result for {func.__name__}: {cache_key}")
                except Exception as e:
                    logger.warning(f"Cache set error for {cache_key}: {e}")
                
                return result
                
            except Exception as e:
                if invalidate_on_error:
                    try:
                        loop = asyncio.get_event_loop()
                        loop.run_until_complete(cache.delete(cache_key))
                        logger.debug(f"Invalidated cache for error in {func.__name__}: {cache_key}")
                    except Exception:
                        pass
                raise
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Specialized decorators for common MCP operations

def cache_symbol_lookup(
    ttl: int = 1800,  # 30 minutes
    tier_hint: CacheTier = CacheTier.L1  # Fast access for symbols
):
    """Cache decorator optimized for symbol lookups."""
    return cached(
        ttl=ttl,
        tier_hint=tier_hint,
        key_prefix="symbol",
        tags={"symbols"},
        warming_strategy=WarmingStrategy.PREDICTIVE
    )


def cache_search_results(
    ttl: int = 600,  # 10 minutes
    tier_hint: CacheTier = CacheTier.L2  # Medium-term storage
):
    """Cache decorator optimized for search results."""
    return cached(
        ttl=ttl,
        tier_hint=tier_hint,
        key_prefix="search",
        tags={"search"},
        compress_large_values=True
    )


def cache_file_analysis(
    ttl: int = 3600,  # 1 hour
    tier_hint: CacheTier = CacheTier.L3  # Long-term storage for large data
):
    """Cache decorator optimized for file analysis results."""
    return cached(
        ttl=ttl,
        tier_hint=tier_hint,
        key_prefix="file_analysis",
        tags={"files", "analysis"},
        compress_large_values=True,
        invalidate_on_error=True
    )


def cache_project_metadata(
    ttl: int = 7200,  # 2 hours
    tier_hint: CacheTier = CacheTier.L2
):
    """Cache decorator optimized for project metadata."""
    return cached(
        ttl=ttl,
        tier_hint=tier_hint,
        key_prefix="project",
        tags={"project", "metadata"},
        skip_kwargs={"_internal", "_debug"}  # Skip internal parameters
    )


def cache_semantic_search(
    ttl: int = 1800,  # 30 minutes
    tier_hint: CacheTier = CacheTier.L2
):
    """Cache decorator optimized for semantic search results."""
    return cached(
        ttl=ttl,
        tier_hint=tier_hint,
        key_prefix="semantic",
        tags={"semantic", "search"},
        compress_large_values=True,
        warming_strategy=WarmingStrategy.PREDICTIVE
    )


# Cache management utilities

async def invalidate_by_tags(tags: Set[str]) -> int:
    """Invalidate cache entries by tags."""
    cache = _get_cache()
    warming_manager = _get_warming_manager()
    
    count = 0
    if hasattr(cache, 'invalidate_by_tags'):
        count = await cache.invalidate_by_tags(tags)
    
    # Also trigger warming manager invalidation if available
    if warming_manager:
        for tag in tags:
            await warming_manager.invalidate(f"tag:{tag}")
    
    return count


async def warm_cache_for_function(
    func: Callable,
    args_list: List[Tuple[tuple, dict]],
    strategy: WarmingStrategy = WarmingStrategy.EAGER
) -> Dict[str, bool]:
    """Warm cache for a function with multiple argument sets."""
    cache = _get_cache()
    results = {}
    
    for args, kwargs in args_list:
        try:
            # Execute function to warm cache
            if asyncio.iscoroutinefunction(func):
                await func(*args, **kwargs)
            else:
                func(*args, **kwargs)
            
            # Generate key for tracking
            key = f"{func.__name__}:{len(args)}:{len(kwargs)}"
            results[key] = True
            
        except Exception as e:
            logger.error(f"Failed to warm cache for {func.__name__}: {e}")
            key = f"{func.__name__}:{len(args)}:{len(kwargs)}"
            results[key] = False
    
    return results


async def get_cache_stats() -> Dict[str, Any]:
    """Get comprehensive cache statistics."""
    cache = _get_cache()
    warming_manager = _get_warming_manager()
    
    stats = await cache.get_stats()
    
    if warming_manager:
        warming_stats = await warming_manager.get_warming_stats()
        stats["warming"] = warming_stats
    
    return stats


# Context manager for cache operations

class CacheContext:
    """Context manager for cache operations with automatic cleanup."""
    
    def __init__(self, tags: Optional[Set[str]] = None):
        self.tags = tags or set()
        self.created_keys: List[str] = []
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # Clean up on error
            cache = _get_cache()
            for key in self.created_keys:
                try:
                    await cache.delete(key)
                except Exception:
                    pass
    
    def track_key(self, key: str):
        """Track a cache key for potential cleanup."""
        self.created_keys.append(key)