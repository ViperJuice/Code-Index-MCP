"""
Cache integration for MCP server.

Provides caching functionality for search results, symbol lookups, and file outlines.
"""
import logging
import hashlib
import json
from typing import Any, Optional, Dict, TYPE_CHECKING

from ..cache.cache_manager import CacheManager, CacheConfig, CacheBackendType
from ..utils.feature_flags import feature_manager

if TYPE_CHECKING:
    from ..stdio_server import StdioMCPServer

logger = logging.getLogger(__name__)


class CacheIntegration:
    """Integrates caching functionality into MCP server."""
    
    def __init__(self, server: 'StdioMCPServer'):
        self.server = server
        self.cache_manager: Optional[CacheManager] = None
        self.enabled = False
    
    async def initialize(self) -> None:
        """Initialize caching if enabled."""
        # Initialize feature manager from environment
        feature_manager.initialize_from_env()
        
        if not feature_manager.is_enabled('cache'):
            logger.debug("Cache feature is disabled")
            return
        
        try:
            # Get cache configuration
            cache_config = feature_manager.get_config('cache')
            backend_type = CacheBackendType.MEMORY
            if cache_config and cache_config.get('backend') == 'redis':
                backend_type = CacheBackendType.REDIS
            
            # Create cache configuration
            config = CacheConfig(
                backend_type=backend_type,
                max_entries=cache_config.get('max_entries', 1000) if cache_config else 1000,
                default_ttl=cache_config.get('ttl', 3600) if cache_config else 3600,
                performance_monitoring=True
            )
            
            # Initialize cache manager
            self.cache_manager = CacheManager(config)
            await self.cache_manager.initialize()
            
            self.enabled = True
            backend_name = cache_config.get('backend', 'memory') if cache_config else 'memory'
            logger.info(f"Cache enabled with {backend_name} backend")
            
        except Exception as e:
            logger.error(f"Failed to initialize cache: {e}")
            self.enabled = False
    
    def _apply_cache_to_tools(self) -> None:
        """Apply caching to tool handlers."""
        if not self.enabled or not hasattr(self.server, 'tool_manager'):
            return
        
        # Cache these tools
        cacheable_tools = {
            'search_code': self._cache_search_code,
            'lookup_symbol': self._cache_lookup_symbol,
            'find_references': self._cache_find_references,
        }
        
        for tool_name, cache_wrapper in cacheable_tools.items():
            try:
                # Get original handler
                original_handler = self.server.tool_manager.get_handler(tool_name)
                if original_handler:
                    # Create cached wrapper
                    cached_handler = cache_wrapper(original_handler)
                    # Register the cached handler
                    self.server.tool_manager.register_handler(tool_name, cached_handler)
                    logger.debug(f"Added caching to tool: {tool_name}")
            except Exception as e:
                logger.warning(f"Failed to wrap tool {tool_name} with cache: {e}")
    
    def _generate_cache_key(self, tool_name: str, params: Dict[str, Any]) -> str:
        """Generate a cache key for tool parameters."""
        # Create stable string representation of parameters
        param_str = json.dumps(params, sort_keys=True)
        key_data = f"{tool_name}:{param_str}"
        
        # Generate hash for compact key
        return hashlib.sha256(key_data.encode()).hexdigest()[:16]
    
    def _cache_search_code(self, original_handler):
        """Wrap search_code tool with caching."""
        async def cached_handler(params: Dict[str, Any]) -> Dict[str, Any]:
            if not self.cache_manager:
                return await original_handler(params)
            
            try:
                # Generate cache key
                cache_key = self._generate_cache_key('search_code', params)
                
                # Check cache
                cached_result = await self.cache_manager.get(cache_key)
                if cached_result is not None:
                    logger.debug(f"Cache hit for search_code: {params.get('query', '')}")
                    return cached_result
                
                # Execute and cache
                result = await original_handler(params)
                await self.cache_manager.set(cache_key, result)
                
                return result
            except Exception as e:
                logger.error(f"Cache error in search_code: {e}")
                # Fallback to original handler on cache error
                return await original_handler(params)
        
        return cached_handler
    
    def _cache_lookup_symbol(self, original_handler):
        """Wrap lookup_symbol tool with caching."""
        async def cached_handler(params: Dict[str, Any]) -> Dict[str, Any]:
            if not self.cache_manager:
                return await original_handler(params)
            
            try:
                # Generate cache key
                cache_key = self._generate_cache_key('lookup_symbol', params)
                
                # Check cache
                cached_result = await self.cache_manager.get(cache_key)
                if cached_result is not None:
                    logger.debug(f"Cache hit for lookup_symbol: {params.get('symbol', '')}")
                    return cached_result
                
                # Execute and cache
                result = await original_handler(params)
                await self.cache_manager.set(cache_key, result)
                
                return result
            except Exception as e:
                logger.error(f"Cache error in lookup_symbol: {e}")
                # Fallback to original handler on cache error
                return await original_handler(params)
        
        return cached_handler
    
    def _cache_find_references(self, original_handler):
        """Wrap find_references tool with caching."""
        async def cached_handler(params: Dict[str, Any]) -> Dict[str, Any]:
            if not self.cache_manager:
                return await original_handler(params)
            
            try:
                # Generate cache key
                cache_key = self._generate_cache_key('find_references', params)
                
                # Check cache
                cached_result = await self.cache_manager.get(cache_key)
                if cached_result is not None:
                    logger.debug(f"Cache hit for find_references: {params.get('symbol', '')}")
                    return cached_result
                
                # Execute and cache
                result = await original_handler(params)
                await self.cache_manager.set(cache_key, result)
                
                return result
            except Exception as e:
                logger.error(f"Cache error in find_references: {e}")
                # Fallback to original handler on cache error
                return await original_handler(params)
        
        return cached_handler
    
    async def on_index_complete(self, file_path: str) -> None:
        """Handle index completion event - invalidate cache."""
        if self.enabled and self.cache_manager:
            try:
                await self.cache_manager.clear()
                logger.info(f"Cache invalidated after indexing: {file_path}")
            except Exception as e:
                logger.error(f"Failed to invalidate cache: {e}")
    
    async def clear_cache(self) -> None:
        """Clear all cached data."""
        if self.enabled and self.cache_manager:
            await self.cache_manager.clear()
            logger.info("Cache cleared")
    
    async def get_cache_stats(self) -> Optional[Dict[str, Any]]:
        """Get cache statistics."""
        if self.enabled and self.cache_manager:
            try:
                metrics = await self.cache_manager.get_metrics()
                return {
                    'hits': metrics.hits,
                    'misses': metrics.misses,
                    'size': metrics.entries_count,
                    'hit_rate': metrics.hit_rate
                }
            except Exception as e:
                logger.error(f"Failed to get cache stats: {e}")
                return None
        return None
    
    async def shutdown(self) -> None:
        """Shutdown cache manager."""
        if self.enabled and self.cache_manager:
            try:
                # Clear cache before shutdown
                await self.cache_manager.clear()
                await self.cache_manager.shutdown()
                logger.info("Cache shutdown complete")
            except Exception as e:
                logger.error(f"Error during cache shutdown: {e}")
            finally:
                self.enabled = False
                self.cache_manager = None


async def setup_cache(server: 'StdioMCPServer') -> Optional[CacheIntegration]:
    """Set up cache integration for the server."""
    cache_integration = CacheIntegration(server)
    await cache_integration.initialize()
    return cache_integration if cache_integration.enabled else None