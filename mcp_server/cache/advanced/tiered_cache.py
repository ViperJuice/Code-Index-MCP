"""Multi-tier caching system with intelligent promotion/eviction."""
import asyncio
import json
import logging
import os
import pickle
import redis
import hashlib
import time
import weakref
from collections import OrderedDict, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Dict, List, Set, Tuple, Callable, Union
from functools import lru_cache, wraps
from enum import Enum

try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    aioredis = None
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class CacheStats:
    """Cache tier statistics."""
    hits: int = 0
    misses: int = 0
    promotions: int = 0
    evictions: int = 0
    size_bytes: int = 0
    entry_count: int = 0
    avg_access_time_ms: float = 0.0


@dataclass
class AccessPattern:
    """Track access patterns for intelligent promotion."""
    key: str
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    access_frequency: float = 0.0  # accesses per hour
    size_bytes: int = 0
    tier_history: List[str] = field(default_factory=list)
    
    def update_access(self):
        """Update access pattern statistics."""
        now = time.time()
        time_diff = now - self.last_accessed
        self.access_count += 1
        
        if time_diff > 0:
            # Calculate frequency as accesses per hour
            self.access_frequency = self.access_count / max(time_diff / 3600, 0.01)
        
        self.last_accessed = now
    
    def should_promote(self, current_tier: str) -> bool:
        """Determine if entry should be promoted to higher tier."""
        # Promote if frequently accessed (>10 times per hour) and not in L1
        if current_tier != "L1" and self.access_frequency > 10:
            return True
        
        # Promote if accessed multiple times recently
        if current_tier == "L3" and self.access_count >= 3:
            return True
            
        return False


class CacheTier(Enum):
    """Cache tier enumeration."""
    L1 = "L1"  # Memory
    L2 = "L2"  # Redis
    L3 = "L3"  # Disk


class TieredCache:
    """Advanced multi-tier cache with intelligent promotion/eviction."""
    
    def __init__(self, 
                 redis_url: str = "redis://localhost:6379",
                 l1_max_size: int = 1000,
                 l1_max_memory_mb: int = 100,
                 l2_default_ttl: int = 3600,
                 l3_cache_dir: str = "/tmp/mcp_cache",
                 enable_stats: bool = True):
        
        # Configuration
        self.redis_url = redis_url
        self.l1_max_size = l1_max_size
        self.l1_max_memory_mb = l1_max_memory_mb
        self.l1_max_memory_bytes = l1_max_memory_mb * 1024 * 1024
        self.l2_default_ttl = l2_default_ttl
        self.l3_cache_dir = Path(l3_cache_dir)
        self.l3_cache_dir.mkdir(parents=True, exist_ok=True)
        
        # L1 Cache (Memory)
        self.l1_cache: OrderedDict[str, Any] = OrderedDict()
        self.l1_current_memory = 0
        
        # Redis client (L2)
        self._redis_client: Optional[Any] = None
        
        # Access patterns for intelligent promotion
        self.access_patterns: Dict[str, AccessPattern] = {}
        
        # Statistics
        self.enable_stats = enable_stats
        self.stats = {
            CacheTier.L1: CacheStats(),
            CacheTier.L2: CacheStats(),
            CacheTier.L3: CacheStats()
        }
        
        # Performance monitoring
        self._access_times: List[float] = []
        self._max_access_history = 1000
        
        # Background tasks
        self._running = True
        self._cleanup_task: Optional[asyncio.Task] = None
        self._start_background_tasks()
    
    def _start_background_tasks(self):
        """Start background maintenance tasks."""
        async def maintenance_loop():
            while self._running:
                try:
                    await asyncio.sleep(300)  # Run every 5 minutes
                    await self._cleanup_expired()
                    await self._optimize_cache_distribution()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in cache maintenance: {e}")
        
        self._cleanup_task = asyncio.create_task(maintenance_loop())
    
    async def _get_redis_client(self):
        """Get Redis client, creating if necessary."""
        if self._redis_client is None and REDIS_AVAILABLE:
            self._redis_client = aioredis.from_url(self.redis_url, decode_responses=False)
        return self._redis_client
    
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
                return sum(self._estimate_size(k) + self._estimate_size(v) 
                          for k, v in value.items()) + 64
            else:
                return len(pickle.dumps(value))
        except Exception:
            return 1024  # Default estimate
    
    async def get(self, key: str) -> Optional[Any]:
        """Get from cache with intelligent tier fallback and promotion."""
        start_time = time.time()
        result = None
        found_tier = None
        
        try:
            # L1: In-memory cache (fastest)
            if key in self.l1_cache:
                result = self.l1_cache[key]
                found_tier = CacheTier.L1
                # Move to end (most recently used)
                self.l1_cache.move_to_end(key)
                if self.enable_stats:
                    self.stats[CacheTier.L1].hits += 1
            
            # L2: Redis cache (medium speed)
            elif REDIS_AVAILABLE:
                redis_client = await self._get_redis_client()
                if redis_client:
                    try:
                        redis_value = await redis_client.get(key)
                        if redis_value:
                            result = pickle.loads(redis_value)
                            found_tier = CacheTier.L2
                            if self.enable_stats:
                                self.stats[CacheTier.L2].hits += 1
                            
                            # Consider promoting to L1
                            await self._consider_promotion(key, result, CacheTier.L2)
                    except Exception as e:
                        logger.warning(f"Redis error for key {key}: {e}")
            
            # L3: Disk cache (slowest but largest capacity)
            if result is None:
                result = await self._get_from_disk_cache(key)
                if result is not None:
                    found_tier = CacheTier.L3
                    if self.enable_stats:
                        self.stats[CacheTier.L3].hits += 1
                    
                    # Consider promoting to higher tiers
                    await self._consider_promotion(key, result, CacheTier.L3)
            
            # Update access patterns
            if result is not None:
                self._update_access_pattern(key, found_tier)
            else:
                # Record miss in all tiers
                if self.enable_stats:
                    for tier in CacheTier:
                        self.stats[tier].misses += 1
            
            return result
            
        finally:
            # Record access time for performance monitoring
            access_time = (time.time() - start_time) * 1000  # ms
            self._access_times.append(access_time)
            if len(self._access_times) > self._max_access_history:
                self._access_times.pop(0)
            
            # Update average access time in stats
            if self.enable_stats and found_tier:
                current_avg = self.stats[found_tier].avg_access_time_ms
                self.stats[found_tier].avg_access_time_ms = (
                    (current_avg * 0.9) + (access_time * 0.1)  # Exponential moving average
                )
    
    def _update_access_pattern(self, key: str, tier: CacheTier):
        """Update access pattern for intelligent caching decisions."""
        if key not in self.access_patterns:
            self.access_patterns[key] = AccessPattern(key=key)
        
        pattern = self.access_patterns[key]
        pattern.update_access()
        pattern.tier_history.append(tier.value)
        
        # Keep only recent history
        if len(pattern.tier_history) > 10:
            pattern.tier_history.pop(0)
    
    async def _consider_promotion(self, key: str, value: Any, current_tier: CacheTier):
        """Consider promoting value to higher tier based on access patterns."""
        if key not in self.access_patterns:
            return
        
        pattern = self.access_patterns[key]
        
        # Promote from L3 to L2 if frequently accessed
        if current_tier == CacheTier.L3 and pattern.should_promote("L3"):
            await self._promote_to_l2(key, value)
        
        # Promote from L2 to L1 if very frequently accessed
        elif current_tier == CacheTier.L2 and pattern.should_promote("L2"):
            await self._promote_to_l1(key, value)
    
    async def _promote_to_l1(self, key: str, value: Any):
        """Promote value to L1 cache."""
        value_size = self._estimate_size(value)
        
        # Check if we have space
        if (len(self.l1_cache) >= self.l1_max_size or 
            self.l1_current_memory + value_size > self.l1_max_memory_bytes):
            await self._evict_from_l1()
        
        self.l1_cache[key] = value
        self.l1_current_memory += value_size
        
        if self.enable_stats:
            self.stats[CacheTier.L1].promotions += 1
            self.stats[CacheTier.L1].entry_count = len(self.l1_cache)
            self.stats[CacheTier.L1].size_bytes = self.l1_current_memory
    
    async def _promote_to_l2(self, key: str, value: Any):
        """Promote value to L2 cache."""
        redis_client = await self._get_redis_client()
        if redis_client:
            try:
                await redis_client.setex(key, self.l2_default_ttl, pickle.dumps(value))
                if self.enable_stats:
                    self.stats[CacheTier.L2].promotions += 1
            except Exception as e:
                logger.error(f"Failed to promote {key} to L2: {e}")
    
    async def _evict_from_l1(self):
        """Evict entries from L1 using intelligent strategy."""
        if not self.l1_cache:
            return
        
        # Find least valuable entry based on access patterns
        candidates = []
        for cache_key in self.l1_cache:
            pattern = self.access_patterns.get(cache_key)
            if pattern:
                # Score based on frequency, recency, and size
                frequency_score = pattern.access_frequency
                recency_score = 1.0 / max(time.time() - pattern.last_accessed, 1)
                size_penalty = pattern.size_bytes / 1024  # Prefer smaller items
                score = frequency_score * recency_score / max(size_penalty, 1)
                candidates.append((cache_key, score))
            else:
                candidates.append((cache_key, 0))  # No pattern data = low priority
        
        # Sort by score (lowest first) and evict
        candidates.sort(key=lambda x: x[1])
        
        evict_count = max(1, len(self.l1_cache) // 10)  # Evict 10% or at least 1
        for cache_key, _ in candidates[:evict_count]:
            if cache_key in self.l1_cache:
                value = self.l1_cache.pop(cache_key)
                self.l1_current_memory -= self._estimate_size(value)
                if self.enable_stats:
                    self.stats[CacheTier.L1].evictions += 1
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None, 
                  tier_hint: Optional[CacheTier] = None, tags: Optional[Set[str]] = None):
        """Set value in appropriate cache tier with intelligent placement."""
        if ttl is None:
            ttl = self.l2_default_ttl
        
        value_size = self._estimate_size(value)
        
        # Update access pattern
        if key not in self.access_patterns:
            self.access_patterns[key] = AccessPattern(key=key, size_bytes=value_size)
        self.access_patterns[key].size_bytes = value_size
        
        # Determine optimal tier based on size and hint
        if tier_hint:
            target_tiers = [tier_hint]
        else:
            target_tiers = self._determine_optimal_tiers(value_size, key)
        
        success = False
        for tier in target_tiers:
            if tier == CacheTier.L1:
                success = await self._set_l1(key, value)
            elif tier == CacheTier.L2:
                success = await self._set_l2(key, value, ttl)
            elif tier == CacheTier.L3:
                success = await self._set_l3(key, value, ttl)
        
        return success
    
    def _determine_optimal_tiers(self, value_size: int, key: str) -> List[CacheTier]:
        """Determine optimal tiers for storing a value."""
        tiers = []
        
        # Check access patterns for frequency
        pattern = self.access_patterns.get(key)
        is_hot = pattern and pattern.access_frequency > 5  # >5 accesses per hour
        
        if value_size < 1024 * 50:  # < 50KB
            if is_hot:
                tiers = [CacheTier.L1, CacheTier.L2, CacheTier.L3]  # Store in all tiers
            else:
                tiers = [CacheTier.L2, CacheTier.L3]  # Skip L1 for cold data
        elif value_size < 1024 * 1024 * 5:  # < 5MB
            tiers = [CacheTier.L2, CacheTier.L3]  # Redis + Disk
        else:
            tiers = [CacheTier.L3]  # Large values go to disk only
        
        return tiers
    
    async def _set_l1(self, key: str, value: Any) -> bool:
        """Set value in L1 cache."""
        value_size = self._estimate_size(value)
        
        # Check capacity
        if (len(self.l1_cache) >= self.l1_max_size or 
            self.l1_current_memory + value_size > self.l1_max_memory_bytes):
            await self._evict_from_l1()
        
        # Remove existing if present
        if key in self.l1_cache:
            old_value = self.l1_cache[key]
            self.l1_current_memory -= self._estimate_size(old_value)
        
        self.l1_cache[key] = value
        self.l1_current_memory += value_size
        
        if self.enable_stats:
            self.stats[CacheTier.L1].entry_count = len(self.l1_cache)
            self.stats[CacheTier.L1].size_bytes = self.l1_current_memory
        
        return True
    
    async def _set_l2(self, key: str, value: Any, ttl: int) -> bool:
        """Set value in L2 cache (Redis)."""
        if not REDIS_AVAILABLE:
            return False
            
        redis_client = await self._get_redis_client()
        if not redis_client:
            return False
        
        try:
            serialized = pickle.dumps(value)
            await redis_client.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.error(f"Failed to set {key} in L2: {e}")
            return False
    
    async def _set_l3(self, key: str, value: Any, ttl: int) -> bool:
        """Set value in L3 cache (Disk)."""
        try:
            file_path = self._get_cache_file_path(key)
            cache_data = {
                'value': value,
                'created_at': time.time(),
                'expires_at': time.time() + ttl,
                'access_count': 0
            }
            
            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write to temporary file first, then rename (atomic operation)
            temp_path = file_path.with_suffix('.tmp')
            with open(temp_path, 'wb') as f:
                pickle.dump(cache_data, f)
            temp_path.rename(file_path)
            
            return True
        except Exception as e:
            logger.error(f"Failed to set {key} in L3: {e}")
            return False
    
    def _get_cache_file_path(self, key: str) -> Path:
        """Get file path for L3 cache entry."""
        # Create safe filename from key
        safe_key = hashlib.md5(key.encode()).hexdigest()
        # Use subdirectories to avoid too many files in one directory
        subdir = safe_key[:2]
        return self.l3_cache_dir / subdir / f"{safe_key}.cache"
    
    async def _get_from_disk_cache(self, key: str) -> Optional[Any]:
        """Get value from L3 disk cache."""
        try:
            file_path = self._get_cache_file_path(key)
            if not file_path.exists():
                return None
            
            with open(file_path, 'rb') as f:
                cache_data = pickle.load(f)
            
            # Check expiration
            if time.time() > cache_data.get('expires_at', float('inf')):
                # Expired, remove file
                try:
                    file_path.unlink()
                except OSError:
                    pass
                return None
            
            # Update access count
            cache_data['access_count'] = cache_data.get('access_count', 0) + 1
            
            # Write back updated access count
            with open(file_path, 'wb') as f:
                pickle.dump(cache_data, f)
            
            return cache_data['value']
            
        except Exception as e:
            logger.error(f"Failed to get {key} from L3: {e}")
            return None
    
    async def delete(self, key: str) -> bool:
        """Delete key from all cache tiers."""
        success = False
        
        # L1
        if key in self.l1_cache:
            value = self.l1_cache.pop(key)
            self.l1_current_memory -= self._estimate_size(value)
            success = True
        
        # L2
        if REDIS_AVAILABLE:
            redis_client = await self._get_redis_client()
            if redis_client:
                try:
                    result = await redis_client.delete(key)
                    success = success or bool(result)
                except Exception as e:
                    logger.error(f"Failed to delete {key} from L2: {e}")
        
        # L3
        try:
            file_path = self._get_cache_file_path(key)
            if file_path.exists():
                file_path.unlink()
                success = True
        except Exception as e:
            logger.error(f"Failed to delete {key} from L3: {e}")
        
        # Clean up access pattern
        if key in self.access_patterns:
            del self.access_patterns[key]
        
        return success
    
    async def clear(self) -> int:
        """Clear all cache tiers."""
        count = 0
        
        # L1
        count += len(self.l1_cache)
        self.l1_cache.clear()
        self.l1_current_memory = 0
        
        # L2
        if REDIS_AVAILABLE:
            redis_client = await self._get_redis_client()
            if redis_client:
                try:
                    # Get keys matching our pattern
                    keys = await redis_client.keys("*")
                    if keys:
                        await redis_client.delete(*keys)
                        count += len(keys)
                except Exception as e:
                    logger.error(f"Failed to clear L2: {e}")
        
        # L3
        try:
            import shutil
            if self.l3_cache_dir.exists():
                shutil.rmtree(self.l3_cache_dir)
                self.l3_cache_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to clear L3: {e}")
        
        # Clear access patterns
        self.access_patterns.clear()
        
        return count
    
    async def _cleanup_expired(self) -> int:
        """Clean up expired entries from all tiers."""
        cleaned = 0
        
        # L3 cleanup (most important as Redis handles its own expiration)
        try:
            for file_path in self.l3_cache_dir.rglob("*.cache"):
                try:
                    with open(file_path, 'rb') as f:
                        cache_data = pickle.load(f)
                    
                    if time.time() > cache_data.get('expires_at', float('inf')):
                        file_path.unlink()
                        cleaned += 1
                except Exception:
                    # Remove corrupted files
                    try:
                        file_path.unlink()
                        cleaned += 1
                    except OSError:
                        pass
        except Exception as e:
            logger.error(f"Error during L3 cleanup: {e}")
        
        # Clean up stale access patterns
        stale_keys = [
            key for key, pattern in self.access_patterns.items()
            if time.time() - pattern.last_accessed > 86400  # 24 hours
        ]
        for key in stale_keys:
            del self.access_patterns[key]
        
        return cleaned
    
    async def _optimize_cache_distribution(self):
        """Optimize data distribution across cache tiers."""
        # Analyze access patterns and promote/demote accordingly
        current_time = time.time()
        
        for key, pattern in list(self.access_patterns.items()):
            # Demote items that haven't been accessed recently
            if current_time - pattern.last_accessed > 3600:  # 1 hour
                if key in self.l1_cache:
                    # Move from L1 to L2 if it exists there
                    value = self.l1_cache.pop(key)
                    self.l1_current_memory -= self._estimate_size(value)
                    
                    # Ensure it's in L2 or L3
                    redis_client = await self._get_redis_client()
                    if redis_client and REDIS_AVAILABLE:
                        try:
                            exists = await redis_client.exists(key)
                            if not exists:
                                await self._set_l2(key, value, self.l2_default_ttl)
                        except Exception as e:
                            logger.error(f"Error checking Redis for {key}: {e}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        total_hits = sum(stats.hits for stats in self.stats.values())
        total_misses = sum(stats.misses for stats in self.stats.values())
        total_requests = total_hits + total_misses
        hit_rate = total_hits / total_requests if total_requests > 0 else 0.0
        
        # Calculate average access time
        avg_access_time = sum(self._access_times) / len(self._access_times) if self._access_times else 0
        
        return {
            "overall": {
                "hit_rate": hit_rate,
                "total_requests": total_requests,
                "avg_access_time_ms": avg_access_time,
                "target_hit_rate": 0.9,  # 90% target
                "target_response_time_ms": 10  # <10ms target
            },
            "tiers": {
                tier.value: {
                    "hits": stats.hits,
                    "misses": stats.misses,
                    "promotions": stats.promotions,
                    "evictions": stats.evictions,
                    "entries": stats.entry_count,
                    "size_bytes": stats.size_bytes,
                    "avg_access_time_ms": stats.avg_access_time_ms
                }
                for tier, stats in self.stats.items()
            },
            "access_patterns": {
                "total_tracked": len(self.access_patterns),
                "hot_keys": len([p for p in self.access_patterns.values() if p.access_frequency > 10]),
                "cold_keys": len([p for p in self.access_patterns.values() if p.access_frequency < 1])
            }
        }
    
    async def shutdown(self):
        """Shutdown the cache system gracefully."""
        self._running = False
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        if self._redis_client:
            await self._redis_client.close()