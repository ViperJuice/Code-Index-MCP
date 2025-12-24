"""
Dispatcher Interfaces

All interfaces related to request dispatching, routing, and result aggregation.
The dispatcher coordinates between the API gateway and the plugin system.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from .plugin_interfaces import SearchResult, SymbolDefinition, SymbolReference
from .shared_interfaces import ICache, Result

# ========================================
# Dispatcher Data Types
# ========================================


@dataclass
class DispatchRequest:
    """Request to be dispatched to plugins"""

    operation: str  # index, search, get_definition, get_references, etc.
    file_path: Optional[str]
    content: Optional[str]
    query: Optional[str]
    symbol: Optional[str]
    context: Dict[str, Any]
    options: Dict[str, Any]


@dataclass
class DispatchResult:
    """Result from a dispatched operation"""

    success: bool
    plugin_name: str
    operation: str
    result: Any
    execution_time: float
    error: Optional[str] = None
    metadata: Dict[str, Any] = None


@dataclass
class AggregatedResult:
    """Aggregated result from multiple plugins"""

    operation: str
    total_plugins: int
    successful_plugins: int
    failed_plugins: int
    results: List[DispatchResult]
    merged_result: Any
    total_execution_time: float
    metadata: Dict[str, Any] = None


@dataclass
class RoutingRule:
    """Rule for routing requests to plugins"""

    condition: str  # file_extension, language, pattern, etc.
    value: str
    plugin_names: List[str]
    priority: int
    enabled: bool = True


# ========================================
# Core Dispatcher Interfaces
# ========================================


class IDispatcher(ABC):
    """Main dispatcher interface for coordinating plugin operations"""

    @abstractmethod
    async def dispatch(self, request: DispatchRequest) -> Result[AggregatedResult]:
        """Dispatch a request to appropriate plugins and aggregate results"""

    @abstractmethod
    async def dispatch_to_plugin(
        self, plugin_name: str, request: DispatchRequest
    ) -> Result[DispatchResult]:
        """Dispatch a request to a specific plugin"""

    @abstractmethod
    async def dispatch_to_all(self, request: DispatchRequest) -> Result[AggregatedResult]:
        """Dispatch a request to all available plugins"""

    @abstractmethod
    def get_dispatch_statistics(self) -> Dict[str, Any]:
        """Get statistics about dispatch operations"""


class IRequestRouter(ABC):
    """Interface for routing requests to appropriate plugins"""

    @abstractmethod
    def route_request(self, request: DispatchRequest) -> List[str]:
        """Determine which plugins should handle a request"""

    @abstractmethod
    def add_routing_rule(self, rule: RoutingRule) -> None:
        """Add a routing rule"""

    @abstractmethod
    def remove_routing_rule(self, rule_id: str) -> None:
        """Remove a routing rule"""

    @abstractmethod
    def get_routing_rules(self) -> List[RoutingRule]:
        """Get all routing rules"""

    @abstractmethod
    def get_plugins_for_file(self, file_path: str) -> List[str]:
        """Get plugins that can handle a specific file"""


class IPluginRouter(ABC):
    """Interface for plugin-specific routing logic"""

    @abstractmethod
    def can_route_to_plugin(self, plugin_name: str, request: DispatchRequest) -> bool:
        """Check if a request can be routed to a specific plugin"""

    @abstractmethod
    def get_plugin_priority(self, plugin_name: str, request: DispatchRequest) -> int:
        """Get priority for routing to a plugin"""

    @abstractmethod
    def filter_plugins(self, plugins: List[str], request: DispatchRequest) -> List[str]:
        """Filter plugins based on request characteristics"""


# ========================================
# Result Aggregation Interfaces
# ========================================


class IResultAggregator(ABC):
    """Interface for aggregating results from multiple plugins"""

    @abstractmethod
    def aggregate_search_results(self, results: List[DispatchResult]) -> List[SearchResult]:
        """Aggregate search results from multiple plugins"""

    @abstractmethod
    def aggregate_symbol_definitions(self, results: List[DispatchResult]) -> List[SymbolDefinition]:
        """Aggregate symbol definitions from multiple plugins"""

    @abstractmethod
    def aggregate_symbol_references(self, results: List[DispatchResult]) -> List[SymbolReference]:
        """Aggregate symbol references from multiple plugins"""

    @abstractmethod
    def merge_plugin_results(
        self, operation: str, results: List[DispatchResult]
    ) -> AggregatedResult:
        """Merge results from multiple plugins into a single result"""


class IResultMerger(ABC):
    """Interface for merging specific types of results"""

    @abstractmethod
    def merge_search_results(self, results: List[List[SearchResult]]) -> List[SearchResult]:
        """Merge and deduplicate search results"""

    @abstractmethod
    def rank_results(self, results: List[SearchResult], query: str) -> List[SearchResult]:
        """Rank search results by relevance"""

    @abstractmethod
    def deduplicate_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """Remove duplicate results"""


class IResultFilter(ABC):
    """Interface for filtering aggregated results"""

    @abstractmethod
    def filter_by_score(self, results: List[SearchResult], min_score: float) -> List[SearchResult]:
        """Filter results by minimum score"""

    @abstractmethod
    def filter_by_file_type(
        self, results: List[SearchResult], file_types: List[str]
    ) -> List[SearchResult]:
        """Filter results by file type"""

    @abstractmethod
    def apply_custom_filter(
        self, results: List[SearchResult], filter_func: Callable[[SearchResult], bool]
    ) -> List[SearchResult]:
        """Apply a custom filter function"""


# ========================================
# Execution Control Interfaces
# ========================================


class IExecutionCoordinator(ABC):
    """Interface for coordinating plugin execution"""

    @abstractmethod
    async def execute_parallel(self, operations: List[Callable]) -> List[Result[Any]]:
        """Execute operations in parallel"""

    @abstractmethod
    async def execute_sequential(self, operations: List[Callable]) -> List[Result[Any]]:
        """Execute operations sequentially"""

    @abstractmethod
    async def execute_with_timeout(self, operation: Callable, timeout: float) -> Result[Any]:
        """Execute an operation with a timeout"""

    @abstractmethod
    def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a running execution"""


class ILoadBalancer(ABC):
    """Interface for load balancing across plugins"""

    @abstractmethod
    def select_plugin(
        self, available_plugins: List[str], request: DispatchRequest
    ) -> Optional[str]:
        """Select the best plugin for a request"""

    @abstractmethod
    def get_plugin_load(self, plugin_name: str) -> float:
        """Get current load for a plugin"""

    @abstractmethod
    def update_plugin_metrics(self, plugin_name: str, execution_time: float, success: bool) -> None:
        """Update metrics for a plugin"""


# ========================================
# Caching Interfaces
# ========================================


class IDispatchCache(ABC, ICache):
    """Interface for caching dispatch results"""

    @abstractmethod
    def cache_result(self, request: DispatchRequest, result: AggregatedResult) -> None:
        """Cache a dispatch result"""

    @abstractmethod
    def get_cached_result(self, request: DispatchRequest) -> Optional[AggregatedResult]:
        """Get a cached result for a request"""

    @abstractmethod
    def invalidate_cache_for_file(self, file_path: str) -> None:
        """Invalidate cache entries for a specific file"""

    @abstractmethod
    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get cache statistics"""


class ICacheStrategy(ABC):
    """Interface for cache strategies"""

    @abstractmethod
    def should_cache(self, request: DispatchRequest, result: AggregatedResult) -> bool:
        """Determine if a result should be cached"""

    @abstractmethod
    def get_cache_key(self, request: DispatchRequest) -> str:
        """Generate a cache key for a request"""

    @abstractmethod
    def get_cache_ttl(self, request: DispatchRequest) -> Optional[int]:
        """Get TTL for a cached result"""


# ========================================
# Circuit Breaker Interfaces
# ========================================


class ICircuitBreaker(ABC):
    """Interface for circuit breaker pattern"""

    @abstractmethod
    def is_open(self, plugin_name: str) -> bool:
        """Check if circuit breaker is open for a plugin"""

    @abstractmethod
    def record_success(self, plugin_name: str) -> None:
        """Record a successful operation"""

    @abstractmethod
    def record_failure(self, plugin_name: str, error: Exception) -> None:
        """Record a failed operation"""

    @abstractmethod
    def force_open(self, plugin_name: str) -> None:
        """Force circuit breaker open"""

    @abstractmethod
    def force_close(self, plugin_name: str) -> None:
        """Force circuit breaker closed"""


# ========================================
# Monitoring Interfaces
# ========================================


class IDispatchMonitor(ABC):
    """Interface for monitoring dispatch operations"""

    @abstractmethod
    def record_dispatch(self, request: DispatchRequest, result: AggregatedResult) -> None:
        """Record a dispatch operation"""

    @abstractmethod
    def record_plugin_execution(
        self, plugin_name: str, operation: str, execution_time: float, success: bool
    ) -> None:
        """Record plugin execution metrics"""

    @abstractmethod
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""

    @abstractmethod
    def get_error_rates(self) -> Dict[str, float]:
        """Get error rates by plugin"""


class IDispatchTracer(ABC):
    """Interface for tracing dispatch operations"""

    @abstractmethod
    def start_trace(self, request: DispatchRequest) -> str:
        """Start a trace for a dispatch operation"""

    @abstractmethod
    def end_trace(self, trace_id: str, result: AggregatedResult) -> None:
        """End a trace"""

    @abstractmethod
    def add_span(
        self,
        trace_id: str,
        plugin_name: str,
        operation: str,
        start_time: float,
        end_time: float,
    ) -> None:
        """Add a span to a trace"""

    @abstractmethod
    def get_trace(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Get trace information"""
