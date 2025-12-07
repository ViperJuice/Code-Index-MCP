"""
Cache backends implementation supporting memory, Redis, and hybrid storage.
"""

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

try:
    import redis.asyncio as aioredis
    from redis.asyncio import Redis as AsyncRedis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    AsyncRedis = None

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Represents a cache entry with metadata."""

    key: str
    value: Any
    created_at: float
    expires_at: Optional[float] = None
    access_count: int = 0
    last_accessed: float = 0.0
    tags: Set[str] = None
    size_bytes: int = 0

    def __post_init__(self):
        if self.tags is None:
            self.tags = set()
        if self.last_accessed == 0.0:
            self.last_accessed = self.created_at

    def is_expired(self) -> bool:
        """Check if the entry has expired."""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    def touch(self) -> None:
        """Update access time and increment access count."""
        self.last_accessed = time.time()
        self.access_count += 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "key": self.key,
            "value": self.value,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed,
            "tags": list(self.tags),
            "size_bytes": self.size_bytes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CacheEntry":
        """Create from dictionary."""
        data["tags"] = set(data.get("tags", []))
        return cls(**data)


class CacheBackend(ABC):
    """Abstract base class for cache backends."""

    @abstractmethod
    async def get(self, key: str) -> Optional[CacheEntry]:
        """Get a cache entry by key."""

    @abstractmethod
    async def set(
        self, key: str, value: Any, ttl: Optional[int] = None, tags: Optional[Set[str]] = None
    ) -> bool:
        """Set a cache entry with optional TTL and tags."""

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete a cache entry."""

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if a key exists."""

    @abstractmethod
    async def clear(self) -> int:
        """Clear all cache entries. Returns number of cleared entries."""

    @abstractmethod
    async def keys(self, pattern: str = "*") -> List[str]:
        """Get all keys matching pattern."""

    @abstractmethod
    async def invalidate_by_tags(self, tags: Set[str]) -> int:
        """Invalidate entries by tags. Returns number of invalidated entries."""

    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""

    @abstractmethod
    async def cleanup_expired(self) -> int:
        """Clean up expired entries. Returns number of cleaned entries."""


class MemoryCacheBackend(CacheBackend):
    """In-memory cache backend with LRU eviction."""

    def __init__(self, max_size: int = 1000, max_memory_mb: int = 100):
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._tags_index: Dict[str, Set[str]] = {}
        self._current_memory = 0
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._lock = asyncio.Lock()

        # Start background cleanup task
        self._cleanup_task = None
        self._running = True
        self._start_cleanup_task()

    def _start_cleanup_task(self):
        """Start background cleanup task."""

        async def cleanup_loop():
            while self._running:
                try:
                    await asyncio.sleep(60)  # Run every minute
                    await self.cleanup_expired()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in cleanup task: {e}")

        self._cleanup_task = asyncio.create_task(cleanup_loop())

    async def shutdown(self):
        """Shutdown the cache backend."""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

    def _estimate_size(self, value: Any) -> int:
        """Estimate memory size of a value."""
        try:
            if isinstance(value, (str, bytes)):
                return len(value)
            elif isinstance(value, (int, float, bool)):
                return 8
            elif isinstance(value, (list, tuple)):
                return sum(self._estimate_size(item) for item in value) + 64
            elif isinstance(value, dict):
                return (
                    sum(self._estimate_size(k) + self._estimate_size(v) for k, v in value.items())
                    + 64
                )
            else:
                # Fallback to JSON serialization size
                return len(json.dumps(value, default=str))
        except Exception:
            return 1024  # Default estimate

    def _evict_lru(self) -> None:
        """Evict least recently used entries."""
        while len(self._cache) >= self.max_size or self._current_memory > self.max_memory_bytes:
            if not self._cache:
                break

            # Remove oldest entry
            key, entry = self._cache.popitem(last=False)
            self._current_memory -= entry.size_bytes
            self._evictions += 1

            # Remove from tags index
            for tag in entry.tags:
                if tag in self._tags_index:
                    self._tags_index[tag].discard(key)
                    if not self._tags_index[tag]:
                        del self._tags_index[tag]

    async def get(self, key: str) -> Optional[CacheEntry]:
        async with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._misses += 1
                return None

            if entry.is_expired():
                await self._remove_entry(key, entry)
                self._misses += 1
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            entry.touch()
            self._hits += 1
            return entry

    async def set(
        self, key: str, value: Any, ttl: Optional[int] = None, tags: Optional[Set[str]] = None
    ) -> bool:
        async with self._lock:
            now = time.time()
            expires_at = now + ttl if ttl else None
            size_bytes = self._estimate_size(value)

            # Remove existing entry if present
            if key in self._cache:
                old_entry = self._cache[key]
                self._current_memory -= old_entry.size_bytes
                await self._remove_from_tags_index(key, old_entry.tags)

            # Create new entry
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=now,
                expires_at=expires_at,
                tags=tags or set(),
                size_bytes=size_bytes,
            )

            # Check if we need to evict
            self._evict_lru()

            # Add to cache
            self._cache[key] = entry
            self._current_memory += size_bytes

            # Update tags index
            for tag in entry.tags:
                if tag not in self._tags_index:
                    self._tags_index[tag] = set()
                self._tags_index[tag].add(key)

            return True

    async def _remove_entry(self, key: str, entry: CacheEntry) -> None:
        """Remove entry from cache and update indices."""
        if key in self._cache:
            del self._cache[key]
            self._current_memory -= entry.size_bytes
        await self._remove_from_tags_index(key, entry.tags)

    async def _remove_from_tags_index(self, key: str, tags: Set[str]) -> None:
        """Remove key from tags index."""
        for tag in tags:
            if tag in self._tags_index:
                self._tags_index[tag].discard(key)
                if not self._tags_index[tag]:
                    del self._tags_index[tag]

    async def delete(self, key: str) -> bool:
        async with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return False

            await self._remove_entry(key, entry)
            return True

    async def exists(self, key: str) -> bool:
        entry = await self.get(key)
        return entry is not None

    async def clear(self) -> int:
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._tags_index.clear()
            self._current_memory = 0
            return count

    async def keys(self, pattern: str = "*") -> List[str]:
        async with self._lock:
            if pattern == "*":
                return list(self._cache.keys())

            # Simple pattern matching (only supports *)
            import fnmatch

            return [key for key in self._cache.keys() if fnmatch.fnmatch(key, pattern)]

    async def invalidate_by_tags(self, tags: Set[str]) -> int:
        async with self._lock:
            keys_to_remove = set()
            for tag in tags:
                if tag in self._tags_index:
                    keys_to_remove.update(self._tags_index[tag])

            count = 0
            for key in keys_to_remove:
                if key in self._cache:
                    entry = self._cache[key]
                    await self._remove_entry(key, entry)
                    count += 1

            return count

    async def get_stats(self) -> Dict[str, Any]:
        async with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = self._hits / total_requests if total_requests > 0 else 0.0

            return {
                "backend_type": "memory",
                "entries": len(self._cache),
                "max_entries": self.max_size,
                "memory_usage_bytes": self._current_memory,
                "max_memory_bytes": self.max_memory_bytes,
                "memory_usage_percent": (self._current_memory / self.max_memory_bytes) * 100,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": hit_rate,
                "evictions": self._evictions,
                "tags_count": len(self._tags_index),
            }

    async def cleanup_expired(self) -> int:
        async with self._lock:
            _ = time.time()
            expired_keys = []

            for key, entry in self._cache.items():
                if entry.is_expired():
                    expired_keys.append(key)

            count = 0
            for key in expired_keys:
                if key in self._cache:
                    entry = self._cache[key]
                    await self._remove_entry(key, entry)
                    count += 1

            return count


class RedisCacheBackend(CacheBackend):
    """Redis cache backend."""

    def __init__(
        self, redis_url: str = "redis://localhost:6379", prefix: str = "cache:", db: int = 0
    ):
        if not REDIS_AVAILABLE:
            raise ImportError("redis package is required for RedisCacheBackend")

        self.redis_url = redis_url
        self.prefix = prefix
        self.db = db
        self._redis: Optional[aioredis.Redis] = None
        self._hits = 0
        self._misses = 0
        self._lock = asyncio.Lock()

    async def _get_redis(self) -> AsyncRedis:
        """Get Redis connection, creating if necessary."""
        if self._redis is None:
            self._redis = aioredis.from_url(
                self.redis_url, db=self.db, decode_responses=False, encoding="utf-8"
            )
        return self._redis

    async def shutdown(self):
        """Shutdown the Redis connection."""
        if self._redis:
            await self._redis.close()

    def _make_key(self, key: str) -> str:
        """Add prefix to key."""
        return f"{self.prefix}{key}"

    def _serialize_entry(self, entry: CacheEntry) -> bytes:
        """Serialize cache entry to bytes."""
        data = entry.to_dict()
        return json.dumps(data).encode("utf-8")

    def _deserialize_entry(self, data: bytes) -> CacheEntry:
        """Deserialize cache entry from bytes."""
        json_data = json.loads(data.decode("utf-8"))
        return CacheEntry.from_dict(json_data)

    async def get(self, key: str) -> Optional[CacheEntry]:
        redis = await self._get_redis()
        redis_key = self._make_key(key)

        try:
            data = await redis.get(redis_key)
            if data is None:
                self._misses += 1
                return None

            entry = self._deserialize_entry(data)

            if entry.is_expired():
                await redis.delete(redis_key)
                self._misses += 1
                return None

            entry.touch()
            # Update the entry in Redis with new access info
            await redis.set(
                redis_key,
                self._serialize_entry(entry),
                ex=int(entry.expires_at - time.time()) if entry.expires_at else None,
            )

            self._hits += 1
            return entry

        except Exception as e:
            logger.error(f"Redis get error for key {key}: {e}")
            self._misses += 1
            return None

    async def set(
        self, key: str, value: Any, ttl: Optional[int] = None, tags: Optional[Set[str]] = None
    ) -> bool:
        redis = await self._get_redis()
        redis_key = self._make_key(key)

        try:
            now = time.time()
            expires_at = now + ttl if ttl else None
            size_bytes = len(json.dumps(value, default=str))

            entry = CacheEntry(
                key=key,
                value=value,
                created_at=now,
                expires_at=expires_at,
                tags=tags or set(),
                size_bytes=size_bytes,
            )

            # Store the entry
            success = await redis.set(redis_key, self._serialize_entry(entry), ex=ttl)

            # Update tags index
            if tags:
                pipe = redis.pipeline()
                for tag in tags:
                    tag_key = self._make_key(f"tag:{tag}")
                    pipe.sadd(tag_key, key)
                    if ttl:
                        pipe.expire(tag_key, ttl + 3600)  # Tag index expires later
                await pipe.execute()

            return bool(success)

        except Exception as e:
            logger.error(f"Redis set error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        redis = await self._get_redis()
        redis_key = self._make_key(key)

        try:
            # Get entry to remove from tag indices
            entry = await self.get(key)
            if entry:
                pipe = redis.pipeline()
                pipe.delete(redis_key)

                # Remove from tag indices
                for tag in entry.tags:
                    tag_key = self._make_key(f"tag:{tag}")
                    pipe.srem(tag_key, key)

                results = await pipe.execute()
                return bool(results[0])
            else:
                count = await redis.delete(redis_key)
                return count > 0

        except Exception as e:
            logger.error(f"Redis delete error for key {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        redis = await self._get_redis()
        redis_key = self._make_key(key)

        try:
            return bool(await redis.exists(redis_key))
        except Exception as e:
            logger.error(f"Redis exists error for key {key}: {e}")
            return False

    async def clear(self) -> int:
        redis = await self._get_redis()

        try:
            keys = await redis.keys(f"{self.prefix}*")
            if keys:
                return await redis.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Redis clear error: {e}")
            return 0

    async def keys(self, pattern: str = "*") -> List[str]:
        redis = await self._get_redis()

        try:
            redis_pattern = f"{self.prefix}{pattern}"
            keys = await redis.keys(redis_pattern)
            # Remove prefix from keys
            return [key.decode("utf-8")[len(self.prefix) :] for key in keys]
        except Exception as e:
            logger.error(f"Redis keys error: {e}")
            return []

    async def invalidate_by_tags(self, tags: Set[str]) -> int:
        redis = await self._get_redis()

        try:
            keys_to_remove = set()

            # Get all keys for these tags
            for tag in tags:
                tag_key = self._make_key(f"tag:{tag}")
                tag_keys = await redis.smembers(tag_key)
                keys_to_remove.update(key.decode("utf-8") for key in tag_keys)

            if not keys_to_remove:
                return 0

            # Delete the keys and tag indices
            pipe = redis.pipeline()
            for key in keys_to_remove:
                pipe.delete(self._make_key(key))

            for tag in tags:
                tag_key = self._make_key(f"tag:{tag}")
                pipe.delete(tag_key)

            results = await pipe.execute()
            return sum(1 for result in results[: len(keys_to_remove)] if result)

        except Exception as e:
            logger.error(f"Redis invalidate by tags error: {e}")
            return 0

    async def get_stats(self) -> Dict[str, Any]:
        redis = await self._get_redis()

        try:
            info = await redis.info("memory")
            keys_count = len(await redis.keys(f"{self.prefix}*"))

            total_requests = self._hits + self._misses
            hit_rate = self._hits / total_requests if total_requests > 0 else 0.0

            return {
                "backend_type": "redis",
                "entries": keys_count,
                "memory_usage_bytes": info.get("used_memory", 0),
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": hit_rate,
                "redis_version": info.get("redis_version", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
            }
        except Exception as e:
            logger.error(f"Redis stats error: {e}")
            return {"backend_type": "redis", "entries": 0, "error": str(e)}

    async def cleanup_expired(self) -> int:
        # Redis handles expiration automatically
        return 0


class HybridCacheBackend(CacheBackend):
    """Hybrid cache backend using memory for hot data and Redis for persistence."""

    def __init__(
        self,
        memory_backend: MemoryCacheBackend,
        redis_backend: RedisCacheBackend,
        memory_ratio: float = 0.2,
    ):
        self.memory_backend = memory_backend
        self.redis_backend = redis_backend
        self.memory_ratio = memory_ratio  # Percentage of total cache to keep in memory
        self._access_tracker: Dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def shutdown(self):
        """Shutdown both backends."""
        await self.memory_backend.shutdown()
        await self.redis_backend.shutdown()

    async def _should_cache_in_memory(self, key: str) -> bool:
        """Determine if a key should be cached in memory based on access patterns."""
        # Simple strategy: cache in memory if accessed recently
        last_access = self._access_tracker.get(key, 0)
        return (time.time() - last_access) < 3600  # 1 hour threshold

    async def get(self, key: str) -> Optional[CacheEntry]:
        # Try memory first
        entry = await self.memory_backend.get(key)
        if entry:
            self._access_tracker[key] = time.time()
            return entry

        # Try Redis
        entry = await self.redis_backend.get(key)
        if entry:
            self._access_tracker[key] = time.time()

            # Promote to memory if it's hot
            if await self._should_cache_in_memory(key):
                await self.memory_backend.set(
                    key,
                    entry.value,
                    ttl=int(entry.expires_at - time.time()) if entry.expires_at else None,
                    tags=entry.tags,
                )

            return entry

        return None

    async def set(
        self, key: str, value: Any, ttl: Optional[int] = None, tags: Optional[Set[str]] = None
    ) -> bool:
        # Always store in Redis for persistence
        redis_success = await self.redis_backend.set(key, value, ttl, tags)

        # Store in memory if it's likely to be accessed soon
        memory_success = True
        if await self._should_cache_in_memory(key):
            memory_success = await self.memory_backend.set(key, value, ttl, tags)

        self._access_tracker[key] = time.time()
        return redis_success and memory_success

    async def delete(self, key: str) -> bool:
        memory_result = await self.memory_backend.delete(key)
        redis_result = await self.redis_backend.delete(key)
        self._access_tracker.pop(key, None)
        return memory_result or redis_result

    async def exists(self, key: str) -> bool:
        return await self.memory_backend.exists(key) or await self.redis_backend.exists(key)

    async def clear(self) -> int:
        memory_count = await self.memory_backend.clear()
        redis_count = await self.redis_backend.clear()
        self._access_tracker.clear()
        return max(memory_count, redis_count)

    async def keys(self, pattern: str = "*") -> List[str]:
        memory_keys = set(await self.memory_backend.keys(pattern))
        redis_keys = set(await self.redis_backend.keys(pattern))
        return list(memory_keys.union(redis_keys))

    async def invalidate_by_tags(self, tags: Set[str]) -> int:
        memory_count = await self.memory_backend.invalidate_by_tags(tags)
        redis_count = await self.redis_backend.invalidate_by_tags(tags)
        return max(memory_count, redis_count)

    async def get_stats(self) -> Dict[str, Any]:
        memory_stats = await self.memory_backend.get_stats()
        redis_stats = await self.redis_backend.get_stats()

        return {
            "backend_type": "hybrid",
            "memory": memory_stats,
            "redis": redis_stats,
            "access_tracker_size": len(self._access_tracker),
        }

    async def cleanup_expired(self) -> int:
        memory_count = await self.memory_backend.cleanup_expired()
        redis_count = await self.redis_backend.cleanup_expired()

        # Clean up access tracker
        now = time.time()
        stale_keys = [
            key
            for key, last_access in self._access_tracker.items()
            if now - last_access > 86400  # 24 hours
        ]
        for key in stale_keys:
            del self._access_tracker[key]

        return memory_count + redis_count
