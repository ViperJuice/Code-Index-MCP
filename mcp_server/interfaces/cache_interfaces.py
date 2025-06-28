"""
Cache Interfaces

All interfaces related to caching strategies, cache management, and performance optimization.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Callable, Union, Set
from dataclasses import dataclass
from datetime import datetime, timedelta
from .shared_interfaces import Result, ICache

# ========================================
# Cache Data Types
# ========================================


@dataclass
class CacheEntry:
    """Cache entry with metadata"""

    key: str
    value: Any
    created_at: datetime
    expires_at: Optional[datetime]
    access_count: int
    last_accessed: datetime
    size_bytes: int
    metadata: Dict[str, Any] = None


@dataclass
class CacheStats:
    """Cache statistics"""

    total_entries: int
    hit_rate: float
    miss_rate: float
    eviction_count: int
    total_size_bytes: int
    average_entry_size: float
    oldest_entry: Optional[datetime]
    newest_entry: Optional[datetime]


@dataclass
class CacheConfig:
    """Cache configuration"""

    max_size: int  # Maximum number of entries
    max_memory_mb: int  # Maximum memory usage in MB
    default_ttl: Optional[int]  # Default TTL in seconds
    eviction_policy: str  # LRU, LFU, FIFO, etc.
    enable_stats: bool = True
    enable_compression: bool = False
    compression_threshold: int = 1024  # Compress values larger than this


@dataclass
class CacheKey:
    """Structured cache key"""

    namespace: str
    operation: str
    parameters: Dict[str, Any]
    version: str = "v1"

    def to_string(self) -> str:
        """Convert to string representation"""
        param_str = ":".join(f"{k}={v}" for k, v in sorted(self.parameters.items()))
        return f"{self.namespace}:{self.operation}:{param_str}:{self.version}"


# ========================================
# Core Cache Interfaces
# ========================================


class ICacheManager(ABC, ICache):
    """Enhanced cache manager interface"""

    @abstractmethod
    async def initialize(self, config: CacheConfig) -> Result[None]:
        """Initialize the cache manager"""
        pass

    @abstractmethod
    async def shutdown(self) -> Result[None]:
        """Shutdown the cache manager"""
        pass

    @abstractmethod
    async def get_with_metadata(self, key: str) -> Optional[CacheEntry]:
        """Get entry with metadata"""
        pass

    @abstractmethod
    async def set_with_options(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None,
    ) -> None:
        """Set value with options"""
        pass

    @abstractmethod
    async def get_multiple(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values"""
        pass

    @abstractmethod
    async def set_multiple(
        self, items: Dict[str, Any], ttl: Optional[int] = None
    ) -> None:
        """Set multiple values"""
        pass

    @abstractmethod
    async def delete_multiple(self, keys: List[str]) -> int:
        """Delete multiple keys, return count deleted"""
        pass

    @abstractmethod
    async def get_stats(self) -> CacheStats:
        """Get cache statistics"""
        pass


class ICacheBackend(ABC):
    """Interface for cache backends (Redis, Memory, etc.)"""

    @abstractmethod
    async def connect(
        self, connection_string: str, options: Dict[str, Any] = None
    ) -> Result[None]:
        """Connect to cache backend"""
        pass

    @abstractmethod
    async def disconnect(self) -> Result[None]:
        """Disconnect from cache backend"""
        pass

    @abstractmethod
    async def ping(self) -> bool:
        """Check if backend is responsive"""
        pass

    @abstractmethod
    async def get_backend_info(self) -> Dict[str, Any]:
        """Get backend information"""
        pass

    @abstractmethod
    async def flush_all(self) -> Result[None]:
        """Flush all data from backend"""
        pass


class ICacheStrategy(ABC):
    """Interface for cache strategies"""

    @abstractmethod
    def should_cache(
        self, key: str, value: Any, context: Dict[str, Any] = None
    ) -> bool:
        """Determine if value should be cached"""
        pass

    @abstractmethod
    def get_ttl(
        self, key: str, value: Any, context: Dict[str, Any] = None
    ) -> Optional[int]:
        """Get TTL for cache entry"""
        pass

    @abstractmethod
    def get_cache_key(self, operation: str, parameters: Dict[str, Any]) -> str:
        """Generate cache key"""
        pass

    @abstractmethod
    def get_tags(
        self, key: str, value: Any, context: Dict[str, Any] = None
    ) -> List[str]:
        """Get tags for cache entry"""
        pass


# ========================================
# Eviction Policy Interfaces
# ========================================


class IEvictionPolicy(ABC):
    """Interface for cache eviction policies"""

    @abstractmethod
    def select_eviction_candidates(
        self, entries: List[CacheEntry], count: int
    ) -> List[str]:
        """Select entries for eviction"""
        pass

    @abstractmethod
    def on_access(self, key: str) -> None:
        """Called when entry is accessed"""
        pass

    @abstractmethod
    def on_insert(self, key: str, entry: CacheEntry) -> None:
        """Called when entry is inserted"""
        pass

    @abstractmethod
    def on_evict(self, key: str) -> None:
        """Called when entry is evicted"""
        pass


class ILRUPolicy(IEvictionPolicy):
    """Least Recently Used eviction policy"""

    @abstractmethod
    def get_lru_entries(self, count: int) -> List[str]:
        """Get least recently used entries"""
        pass

    @abstractmethod
    def update_access_order(self, key: str) -> None:
        """Update access order for key"""
        pass


class ILFUPolicy(IEvictionPolicy):
    """Least Frequently Used eviction policy"""

    @abstractmethod
    def get_lfu_entries(self, count: int) -> List[str]:
        """Get least frequently used entries"""
        pass

    @abstractmethod
    def increment_frequency(self, key: str) -> None:
        """Increment frequency counter"""
        pass


# ========================================
# Cache Invalidation Interfaces
# ========================================


class ICacheInvalidator(ABC):
    """Interface for cache invalidation"""

    @abstractmethod
    async def invalidate_by_key(self, key: str) -> Result[bool]:
        """Invalidate specific key"""
        pass

    @abstractmethod
    async def invalidate_by_pattern(self, pattern: str) -> Result[int]:
        """Invalidate keys matching pattern"""
        pass

    @abstractmethod
    async def invalidate_by_tags(self, tags: List[str]) -> Result[int]:
        """Invalidate entries with specific tags"""
        pass

    @abstractmethod
    async def invalidate_expired(self) -> Result[int]:
        """Invalidate expired entries"""
        pass

    @abstractmethod
    async def invalidate_by_namespace(self, namespace: str) -> Result[int]:
        """Invalidate entries in namespace"""
        pass


class ICacheNotifier(ABC):
    """Interface for cache invalidation notifications"""

    @abstractmethod
    async def notify_invalidation(self, keys: List[str], reason: str) -> None:
        """Notify about cache invalidations"""
        pass

    @abstractmethod
    async def subscribe_to_invalidations(
        self, callback: Callable[[List[str], str], None]
    ) -> None:
        """Subscribe to invalidation notifications"""
        pass

    @abstractmethod
    async def broadcast_invalidation(self, keys: List[str], reason: str) -> None:
        """Broadcast invalidation to other cache instances"""
        pass


# ========================================
# Distributed Cache Interfaces
# ========================================


class IDistributedCache(ABC, ICacheManager):
    """Interface for distributed caching"""

    @abstractmethod
    async def join_cluster(self, nodes: List[str]) -> Result[None]:
        """Join cache cluster"""
        pass

    @abstractmethod
    async def leave_cluster(self) -> Result[None]:
        """Leave cache cluster"""
        pass

    @abstractmethod
    async def get_cluster_nodes(self) -> Result[List[str]]:
        """Get cluster node list"""
        pass

    @abstractmethod
    async def replicate_to_nodes(
        self, key: str, value: Any, nodes: List[str]
    ) -> Result[None]:
        """Replicate data to specific nodes"""
        pass

    @abstractmethod
    async def get_node_for_key(self, key: str) -> str:
        """Get responsible node for key"""
        pass


class IConsistentHashing(ABC):
    """Interface for consistent hashing"""

    @abstractmethod
    def add_node(self, node: str, weight: int = 1) -> None:
        """Add node to hash ring"""
        pass

    @abstractmethod
    def remove_node(self, node: str) -> None:
        """Remove node from hash ring"""
        pass

    @abstractmethod
    def get_node(self, key: str) -> str:
        """Get node for key"""
        pass

    @abstractmethod
    def get_nodes(self, key: str, count: int) -> List[str]:
        """Get multiple nodes for key"""
        pass


# ========================================
# Cache Warming Interfaces
# ========================================


class ICacheWarmer(ABC):
    """Interface for cache warming"""

    @abstractmethod
    async def warm_cache(
        self, keys: List[str], loader: Callable[[str], Any]
    ) -> Result[int]:
        """Warm cache with specific keys"""
        pass

    @abstractmethod
    async def warm_from_source(
        self, source: str, loader: Callable[[str], Any]
    ) -> Result[int]:
        """Warm cache from data source"""
        pass

    @abstractmethod
    async def schedule_warming(
        self, schedule: str, loader: Callable[[str], Any]
    ) -> Result[str]:
        """Schedule cache warming"""
        pass

    @abstractmethod
    async def get_warming_status(self, task_id: str) -> Result[Dict[str, Any]]:
        """Get warming task status"""
        pass


class IPrefetcher(ABC):
    """Interface for cache prefetching"""

    @abstractmethod
    async def prefetch_related(self, key: str, depth: int = 1) -> Result[List[str]]:
        """Prefetch related cache entries"""
        pass

    @abstractmethod
    async def register_prefetch_rule(
        self, pattern: str, related_keys: List[str]
    ) -> None:
        """Register prefetch rule"""
        pass

    @abstractmethod
    async def analyze_access_patterns(self) -> Dict[str, List[str]]:
        """Analyze access patterns for prefetching"""
        pass


# ========================================
# Cache Monitoring Interfaces
# ========================================


class ICacheMonitor(ABC):
    """Interface for cache monitoring"""

    @abstractmethod
    async def record_hit(self, key: str, response_time: float) -> None:
        """Record cache hit"""
        pass

    @abstractmethod
    async def record_miss(self, key: str, load_time: float) -> None:
        """Record cache miss"""
        pass

    @abstractmethod
    async def record_eviction(self, key: str, reason: str) -> None:
        """Record cache eviction"""
        pass

    @abstractmethod
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        pass

    @abstractmethod
    async def get_hit_rate_by_namespace(self) -> Dict[str, float]:
        """Get hit rate by namespace"""
        pass


class ICacheAnalyzer(ABC):
    """Interface for cache analysis"""

    @abstractmethod
    async def analyze_usage_patterns(self) -> Dict[str, Any]:
        """Analyze cache usage patterns"""
        pass

    @abstractmethod
    async def identify_hot_keys(self, limit: int = 10) -> List[str]:
        """Identify frequently accessed keys"""
        pass

    @abstractmethod
    async def identify_cold_keys(self, threshold: datetime) -> List[str]:
        """Identify rarely accessed keys"""
        pass

    @abstractmethod
    async def suggest_optimizations(self) -> List[Dict[str, Any]]:
        """Suggest cache optimizations"""
        pass


# ========================================
# Specialized Cache Interfaces
# ========================================


class IQueryCache(ABC):
    """Interface for query result caching"""

    @abstractmethod
    async def cache_query_result(
        self, query: str, params: Dict[str, Any], result: Any, ttl: Optional[int] = None
    ) -> None:
        """Cache query result"""
        pass

    @abstractmethod
    async def get_cached_query(
        self, query: str, params: Dict[str, Any]
    ) -> Optional[Any]:
        """Get cached query result"""
        pass

    @abstractmethod
    async def invalidate_queries_for_table(self, table: str) -> Result[int]:
        """Invalidate queries related to table"""
        pass

    @abstractmethod
    async def get_query_cache_stats(self) -> Dict[str, Any]:
        """Get query cache statistics"""
        pass


class ISessionCache(ABC):
    """Interface for session caching"""

    @abstractmethod
    async def store_session(
        self, session_id: str, data: Dict[str, Any], ttl: Optional[int] = None
    ) -> None:
        """Store session data"""
        pass

    @abstractmethod
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data"""
        pass

    @abstractmethod
    async def update_session(self, session_id: str, updates: Dict[str, Any]) -> None:
        """Update session data"""
        pass

    @abstractmethod
    async def delete_session(self, session_id: str) -> None:
        """Delete session"""
        pass

    @abstractmethod
    async def extend_session(self, session_id: str, ttl: int) -> None:
        """Extend session TTL"""
        pass


class IImageCache(ABC):
    """Interface for image/file caching"""

    @abstractmethod
    async def cache_file(
        self,
        file_path: str,
        content: bytes,
        content_type: str,
        ttl: Optional[int] = None,
    ) -> None:
        """Cache file content"""
        pass

    @abstractmethod
    async def get_cached_file(self, file_path: str) -> Optional[tuple[bytes, str]]:
        """Get cached file content and type"""
        pass

    @abstractmethod
    async def cache_file_metadata(
        self, file_path: str, metadata: Dict[str, Any]
    ) -> None:
        """Cache file metadata"""
        pass

    @abstractmethod
    async def get_file_metadata(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get cached file metadata"""
        pass
