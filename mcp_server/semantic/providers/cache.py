"""
Embedding cache implementations

Provides caching for embeddings to avoid redundant API calls.
"""

import asyncio
import time
import json
from typing import List, Dict, Optional, Any
from abc import ABC
import logging
from collections import OrderedDict
import aioredis

from mcp_server.interfaces.embedding_interfaces import IEmbeddingCache, EmbeddingType
from .utils import generate_cache_key
from .exceptions import CacheError

logger = logging.getLogger(__name__)


class MemoryEmbeddingCache(IEmbeddingCache):
    """In-memory LRU cache implementation"""
    
    def __init__(self, max_size: int = 10000, default_ttl: int = 3600):
        """
        Initialize memory cache
        
        Args:
            max_size: Maximum number of entries
            default_ttl: Default time to live in seconds
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._lock = asyncio.Lock()
    
    async def get(
        self,
        text: str,
        embedding_type: EmbeddingType,
        model: str
    ) -> Optional[List[float]]:
        """Get cached embedding"""
        key = generate_cache_key(text, model, embedding_type.value)
        
        async with self._lock:
            if key not in self._cache:
                return None
            
            entry = self._cache[key]
            
            # Check expiration
            if entry['expires_at'] < time.time():
                del self._cache[key]
                return None
            
            # Move to end (LRU)
            self._cache.move_to_end(key)
            
            return entry['embedding']
    
    async def put(
        self,
        text: str,
        embedding: List[float],
        embedding_type: EmbeddingType,
        model: str,
        ttl_seconds: Optional[int] = None
    ) -> None:
        """Store embedding in cache"""
        key = generate_cache_key(text, model, embedding_type.value)
        ttl = ttl_seconds or self.default_ttl
        
        async with self._lock:
            # Remove oldest if at capacity
            if len(self._cache) >= self.max_size and key not in self._cache:
                self._cache.popitem(last=False)
            
            self._cache[key] = {
                'embedding': embedding,
                'expires_at': time.time() + ttl,
                'created_at': time.time()
            }
            
            # Move to end
            self._cache.move_to_end(key)
    
    async def get_batch(
        self,
        texts: List[str],
        embedding_type: EmbeddingType,
        model: str
    ) -> Dict[str, List[float]]:
        """Get multiple cached embeddings"""
        results = {}
        
        for text in texts:
            embedding = await self.get(text, embedding_type, model)
            if embedding is not None:
                results[text] = embedding
        
        return results
    
    async def clear(self, model: Optional[str] = None) -> int:
        """Clear cache entries"""
        async with self._lock:
            if model is None:
                count = len(self._cache)
                self._cache.clear()
                return count
            
            # Clear only specific model entries
            to_remove = [
                key for key in self._cache
                if f":{model.replace('/', '-')}:" in key
            ]
            
            for key in to_remove:
                del self._cache[key]
            
            return len(to_remove)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            'size': len(self._cache),
            'max_size': self.max_size,
            'type': 'memory'
        }


class RedisEmbeddingCache(IEmbeddingCache):
    """Redis-based cache implementation"""
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        default_ttl: int = 3600,
        key_prefix: str = "emb"
    ):
        """
        Initialize Redis cache
        
        Args:
            redis_url: Redis connection URL
            default_ttl: Default time to live in seconds
            key_prefix: Prefix for all keys
        """
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self.key_prefix = key_prefix
        self._redis: Optional[aioredis.Redis] = None
    
    async def _ensure_connected(self) -> aioredis.Redis:
        """Ensure Redis connection is established"""
        if self._redis is None:
            self._redis = await aioredis.from_url(
                self.redis_url,
                decode_responses=False  # We'll handle encoding
            )
        return self._redis
    
    async def get(
        self,
        text: str,
        embedding_type: EmbeddingType,
        model: str
    ) -> Optional[List[float]]:
        """Get cached embedding from Redis"""
        try:
            redis = await self._ensure_connected()
            key = f"{self.key_prefix}:{generate_cache_key(text, model, embedding_type.value)}"
            
            value = await redis.get(key)
            if value is None:
                return None
            
            # Decode JSON
            data = json.loads(value)
            return data['embedding']
            
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            raise CacheError(f"Failed to get from Redis: {str(e)}")
    
    async def put(
        self,
        text: str,
        embedding: List[float],
        embedding_type: EmbeddingType,
        model: str,
        ttl_seconds: Optional[int] = None
    ) -> None:
        """Store embedding in Redis"""
        try:
            redis = await self._ensure_connected()
            key = f"{self.key_prefix}:{generate_cache_key(text, model, embedding_type.value)}"
            ttl = ttl_seconds or self.default_ttl
            
            # Encode data
            data = {
                'embedding': embedding,
                'created_at': time.time()
            }
            value = json.dumps(data)
            
            # Set with expiration
            await redis.setex(key, ttl, value)
            
        except Exception as e:
            logger.error(f"Redis put error: {e}")
            raise CacheError(f"Failed to put to Redis: {str(e)}")
    
    async def get_batch(
        self,
        texts: List[str],
        embedding_type: EmbeddingType,
        model: str
    ) -> Dict[str, List[float]]:
        """Get multiple cached embeddings from Redis"""
        try:
            redis = await self._ensure_connected()
            
            # Build keys
            keys = [
                f"{self.key_prefix}:{generate_cache_key(text, model, embedding_type.value)}"
                for text in texts
            ]
            
            # Get all values
            values = await redis.mget(keys)
            
            # Build results
            results = {}
            for text, value in zip(texts, values):
                if value is not None:
                    data = json.loads(value)
                    results[text] = data['embedding']
            
            return results
            
        except Exception as e:
            logger.error(f"Redis batch get error: {e}")
            raise CacheError(f"Failed to batch get from Redis: {str(e)}")
    
    async def clear(self, model: Optional[str] = None) -> int:
        """Clear cache entries from Redis"""
        try:
            redis = await self._ensure_connected()
            
            if model is None:
                # Clear all embeddings
                pattern = f"{self.key_prefix}:*"
            else:
                # Clear specific model
                pattern = f"{self.key_prefix}:*:{model.replace('/', '-')}:*"
            
            # Find all matching keys
            keys = []
            async for key in redis.scan_iter(match=pattern):
                keys.append(key)
            
            # Delete keys
            if keys:
                await redis.delete(*keys)
            
            return len(keys)
            
        except Exception as e:
            logger.error(f"Redis clear error: {e}")
            raise CacheError(f"Failed to clear Redis: {str(e)}")
    
    async def close(self) -> None:
        """Close Redis connection"""
        if self._redis:
            await self._redis.close()
            self._redis = None


class NoOpCache(IEmbeddingCache):
    """No-operation cache for when caching is disabled"""
    
    async def get(
        self,
        text: str,
        embedding_type: EmbeddingType,
        model: str
    ) -> Optional[List[float]]:
        """Always returns None"""
        return None
    
    async def put(
        self,
        text: str,
        embedding: List[float],
        embedding_type: EmbeddingType,
        model: str,
        ttl_seconds: Optional[int] = None
    ) -> None:
        """Does nothing"""
        pass
    
    async def get_batch(
        self,
        texts: List[str],
        embedding_type: EmbeddingType,
        model: str
    ) -> Dict[str, List[float]]:
        """Always returns empty dict"""
        return {}
    
    async def clear(self, model: Optional[str] = None) -> int:
        """Always returns 0"""
        return 0


class CacheFactory:
    """Factory for creating cache instances"""
    
    @staticmethod
    def create_cache(
        cache_type: str = "memory",
        **kwargs
    ) -> IEmbeddingCache:
        """
        Create a cache instance
        
        Args:
            cache_type: Type of cache ('memory', 'redis', 'none')
            **kwargs: Additional arguments for cache constructor
            
        Returns:
            Cache instance
        """
        if cache_type == "memory":
            return MemoryEmbeddingCache(**kwargs)
        elif cache_type == "redis":
            return RedisEmbeddingCache(**kwargs)
        elif cache_type == "none":
            return NoOpCache()
        else:
            raise ValueError(f"Unknown cache type: {cache_type}")