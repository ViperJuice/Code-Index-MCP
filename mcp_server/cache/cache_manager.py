"""
Cache manager implementation with multiple backend support and performance monitoring.
"""

import asyncio
import hashlib
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional, Set

from .backends import (
    CacheBackend,
    HybridCacheBackend,
    MemoryCacheBackend,
    RedisCacheBackend,
)

logger = logging.getLogger(__name__)


class CacheBackendType(Enum):
    """Cache backend types."""

    MEMORY = "memory"
    REDIS = "redis"
    HYBRID = "hybrid"


@dataclass
class CacheConfig:
    """Cache configuration."""

    backend_type: CacheBackendType = CacheBackendType.MEMORY
    default_ttl: int = 3600  # 1 hour
    max_memory_mb: int = 100
    max_entries: int = 1000
    redis_url: str = "redis://localhost:6379"
    redis_db: int = 0
    cache_prefix: str = "mcp_cache:"
    enable_warming: bool = True
    warming_batch_size: int = 50
    cleanup_interval: int = 300  # 5 minutes
    performance_monitoring: bool = True


@dataclass
class CacheMetrics:
    """Cache performance metrics."""

    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    evictions: int = 0
    errors: int = 0
    total_time_ms: float = 0.0
    avg_response_time_ms: float = 0.0
    hit_rate: float = 0.0
    memory_usage_mb: float = 0.0
    entries_count: int = 0


class ICacheManager(ABC):
    """Interface for cache manager implementations."""

    @abstractmethod
    async def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache."""

    @abstractmethod
    async def set(
        self, key: str, value: Any, ttl: Optional[int] = None, tags: Optional[Set[str]] = None
    ) -> bool:
        """Set value in cache."""

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""

    @abstractmethod
    async def clear(self) -> int:
        """Clear all cache entries."""

    @abstractmethod
    async def invalidate_by_tags(self, tags: Set[str]) -> int:
        """Invalidate entries by tags."""

    @abstractmethod
    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Awaitable[Any]],
        ttl: Optional[int] = None,
        tags: Optional[Set[str]] = None,
    ) -> Any:
        """Get value or set if not exists using factory function."""

    @abstractmethod
    async def mget(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values."""

    @abstractmethod
    async def mset(
        self, mapping: Dict[str, Any], ttl: Optional[int] = None, tags: Optional[Set[str]] = None
    ) -> int:
        """Set multiple values."""

    @abstractmethod
    async def get_metrics(self) -> CacheMetrics:
        """Get cache performance metrics."""

    @abstractmethod
    async def warm_cache(self, keys: List[str], factory: Callable[[str], Awaitable[Any]]) -> int:
        """Warm cache with predefined keys."""

    @abstractmethod
    async def cleanup(self) -> int:
        """Clean up expired entries."""


class CacheManager(ICacheManager):
    """Cache manager implementation with multiple backend support."""

    def __init__(self, config: CacheConfig):
        self.config = config
        self._backend: Optional[CacheBackend] = None
        self._metrics = CacheMetrics()
        self._running = True
        self._cleanup_task: Optional[asyncio.Task] = None

        # Performance monitoring
        self._operation_times: List[float] = []
        self._max_operation_history = 1000

    async def initialize(self) -> None:
        """Initialize the cache manager and backend."""
        try:
            # Create backend based on configuration
            if self.config.backend_type == CacheBackendType.MEMORY:
                self._backend = MemoryCacheBackend(
                    max_size=self.config.max_entries, max_memory_mb=self.config.max_memory_mb
                )
            elif self.config.backend_type == CacheBackendType.REDIS:
                self._backend = RedisCacheBackend(
                    redis_url=self.config.redis_url,
                    prefix=self.config.cache_prefix,
                    db=self.config.redis_db,
                )
            elif self.config.backend_type == CacheBackendType.HYBRID:
                memory_backend = MemoryCacheBackend(
                    max_size=self.config.max_entries // 4,  # 25% in memory
                    max_memory_mb=self.config.max_memory_mb // 4,
                )
                redis_backend = RedisCacheBackend(
                    redis_url=self.config.redis_url,
                    prefix=self.config.cache_prefix,
                    db=self.config.redis_db,
                )
                self._backend = HybridCacheBackend(memory_backend, redis_backend)
            else:
                raise ValueError(f"Unsupported backend type: {self.config.backend_type}")

            # Start cleanup task
            if self.config.cleanup_interval > 0:
                self._start_cleanup_task()

            logger.info(f"Cache manager initialized with {self.config.backend_type.value} backend")

        except Exception as e:
            logger.error(f"Failed to initialize cache manager: {e}")
            raise

    def _start_cleanup_task(self):
        """Start background cleanup task."""

        async def cleanup_loop():
            while self._running:
                try:
                    await asyncio.sleep(self.config.cleanup_interval)
                    await self.cleanup()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in cache cleanup task: {e}")

        self._cleanup_task = asyncio.create_task(cleanup_loop())

    async def shutdown(self):
        """Shutdown the cache manager."""
        self._running = False

        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        if self._backend:
            await self._backend.shutdown()

    def _record_operation_time(self, operation_time: float):
        """Record operation time for performance monitoring."""
        if not self.config.performance_monitoring:
            return

        self._operation_times.append(operation_time)
        if len(self._operation_times) > self._max_operation_history:
            self._operation_times.pop(0)

        # Update metrics
        self._metrics.total_time_ms += operation_time
        if self._operation_times:
            self._metrics.avg_response_time_ms = sum(self._operation_times) / len(
                self._operation_times
            )

    def _generate_cache_key(self, key: str) -> str:
        """Generate a consistent cache key."""
        if isinstance(key, str) and len(key) < 250:  # Simple key
            return key

        # Hash long or complex keys
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    async def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache."""
        if not self._backend:
            raise RuntimeError("Cache manager not initialized")

        start_time = time.time()
        cache_key = self._generate_cache_key(key)

        try:
            entry = await self._backend.get(cache_key)
            operation_time = (time.time() - start_time) * 1000
            self._record_operation_time(operation_time)

            if entry:
                self._metrics.hits += 1
                self._update_hit_rate()
                return entry.value
            else:
                self._metrics.misses += 1
                self._update_hit_rate()
                return default

        except Exception as e:
            self._metrics.errors += 1
            logger.error(f"Cache get error for key {key}: {e}")
            return default

    async def set(
        self, key: str, value: Any, ttl: Optional[int] = None, tags: Optional[Set[str]] = None
    ) -> bool:
        """Set value in cache."""
        if not self._backend:
            raise RuntimeError("Cache manager not initialized")

        start_time = time.time()
        cache_key = self._generate_cache_key(key)
        effective_ttl = ttl or self.config.default_ttl

        try:
            result = await self._backend.set(cache_key, value, effective_ttl, tags)
            operation_time = (time.time() - start_time) * 1000
            self._record_operation_time(operation_time)

            if result:
                self._metrics.sets += 1
            return result

        except Exception as e:
            self._metrics.errors += 1
            logger.error(f"Cache set error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        if not self._backend:
            raise RuntimeError("Cache manager not initialized")

        cache_key = self._generate_cache_key(key)

        try:
            result = await self._backend.delete(cache_key)
            if result:
                self._metrics.deletes += 1
            return result

        except Exception as e:
            self._metrics.errors += 1
            logger.error(f"Cache delete error for key {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        if not self._backend:
            raise RuntimeError("Cache manager not initialized")

        cache_key = self._generate_cache_key(key)

        try:
            return await self._backend.exists(cache_key)
        except Exception as e:
            self._metrics.errors += 1
            logger.error(f"Cache exists error for key {key}: {e}")
            return False

    async def clear(self) -> int:
        """Clear all cache entries."""
        if not self._backend:
            raise RuntimeError("Cache manager not initialized")

        try:
            count = await self._backend.clear()
            logger.info(f"Cleared {count} cache entries")
            return count
        except Exception as e:
            self._metrics.errors += 1
            logger.error(f"Cache clear error: {e}")
            return 0

    async def invalidate_by_tags(self, tags: Set[str]) -> int:
        """Invalidate entries by tags."""
        if not self._backend:
            raise RuntimeError("Cache manager not initialized")

        try:
            count = await self._backend.invalidate_by_tags(tags)
            logger.info(f"Invalidated {count} cache entries by tags: {tags}")
            return count
        except Exception as e:
            self._metrics.errors += 1
            logger.error(f"Cache invalidate by tags error: {e}")
            return 0

    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Awaitable[Any]],
        ttl: Optional[int] = None,
        tags: Optional[Set[str]] = None,
    ) -> Any:
        """Get value or set if not exists using factory function."""
        value = await self.get(key)
        if value is not None:
            return value

        try:
            # Call factory function to generate value
            value = await factory()
            await self.set(key, value, ttl, tags)
            return value
        except Exception as e:
            logger.error(f"Factory function error for key {key}: {e}")
            raise

    async def mget(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values."""
        if not self._backend:
            raise RuntimeError("Cache manager not initialized")

        result = {}
        for key in keys:
            value = await self.get(key)
            if value is not None:
                result[key] = value

        return result

    async def mset(
        self, mapping: Dict[str, Any], ttl: Optional[int] = None, tags: Optional[Set[str]] = None
    ) -> int:
        """Set multiple values."""
        if not self._backend:
            raise RuntimeError("Cache manager not initialized")

        count = 0
        for key, value in mapping.items():
            if await self.set(key, value, ttl, tags):
                count += 1

        return count

    def _update_hit_rate(self):
        """Update hit rate metric."""
        total_requests = self._metrics.hits + self._metrics.misses
        if total_requests > 0:
            self._metrics.hit_rate = self._metrics.hits / total_requests

    async def get_metrics(self) -> CacheMetrics:
        """Get cache performance metrics."""
        # Update metrics from backend
        if self._backend:
            try:
                backend_stats = await self._backend.get_stats()
                self._metrics.entries_count = backend_stats.get("entries", 0)

                # Convert memory usage to MB
                memory_bytes = backend_stats.get("memory_usage_bytes", 0)
                self._metrics.memory_usage_mb = memory_bytes / (1024 * 1024)

                # Update evictions if available
                if "evictions" in backend_stats:
                    self._metrics.evictions = backend_stats["evictions"]

            except Exception as e:
                logger.error(f"Error getting backend stats: {e}")

        return self._metrics

    async def warm_cache(self, keys: List[str], factory: Callable[[str], Awaitable[Any]]) -> int:
        """Warm cache with predefined keys."""
        if not self.config.enable_warming:
            return 0

        count = 0
        batch_size = self.config.warming_batch_size

        for i in range(0, len(keys), batch_size):
            batch_keys = keys[i : i + batch_size]

            # Process batch concurrently
            tasks = []
            for key in batch_keys:
                if not await self.exists(key):
                    tasks.append(self._warm_single_key(key, factory))

            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                count += sum(1 for result in results if result is True)

        logger.info(f"Warmed {count} cache entries")
        return count

    async def _warm_single_key(self, key: str, factory: Callable[[str], Awaitable[Any]]) -> bool:
        """Warm a single cache key."""
        try:
            value = await factory(key)
            return await self.set(key, value)
        except Exception as e:
            logger.warning(f"Failed to warm cache key {key}: {e}")
            return False

    async def cleanup(self) -> int:
        """Clean up expired entries."""
        if not self._backend:
            return 0

        try:
            count = await self._backend.cleanup_expired()
            if count > 0:
                logger.debug(f"Cleaned up {count} expired cache entries")
            return count
        except Exception as e:
            logger.error(f"Cache cleanup error: {e}")
            return 0

    async def get_backend_stats(self) -> Dict[str, Any]:
        """Get detailed backend statistics."""
        if not self._backend:
            return {}

        try:
            return await self._backend.get_stats()
        except Exception as e:
            logger.error(f"Error getting backend stats: {e}")
            return {"error": str(e)}


class CacheManagerFactory:
    """Factory for creating cache manager instances."""

    @staticmethod
    def create_memory_cache(
        max_entries: int = 1000, max_memory_mb: int = 100, default_ttl: int = 3600
    ) -> CacheManager:
        """Create memory-based cache manager."""
        config = CacheConfig(
            backend_type=CacheBackendType.MEMORY,
            max_entries=max_entries,
            max_memory_mb=max_memory_mb,
            default_ttl=default_ttl,
        )
        return CacheManager(config)

    @staticmethod
    def create_redis_cache(
        redis_url: str = "redis://localhost:6379", redis_db: int = 0, default_ttl: int = 3600
    ) -> CacheManager:
        """Create Redis-based cache manager."""
        config = CacheConfig(
            backend_type=CacheBackendType.REDIS,
            redis_url=redis_url,
            redis_db=redis_db,
            default_ttl=default_ttl,
        )
        return CacheManager(config)

    @staticmethod
    def create_hybrid_cache(
        redis_url: str = "redis://localhost:6379",
        max_entries: int = 1000,
        max_memory_mb: int = 100,
        default_ttl: int = 3600,
    ) -> CacheManager:
        """Create hybrid cache manager."""
        config = CacheConfig(
            backend_type=CacheBackendType.HYBRID,
            redis_url=redis_url,
            max_entries=max_entries,
            max_memory_mb=max_memory_mb,
            default_ttl=default_ttl,
        )
        return CacheManager(config)

    @staticmethod
    def from_config(config: CacheConfig) -> CacheManager:
        """Create cache manager from configuration."""
        return CacheManager(config)
