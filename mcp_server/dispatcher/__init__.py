"""Advanced dispatcher components for enhanced routing and result aggregation.

This package provides advanced dispatcher capabilities including:
- Enhanced plugin routing by file extension, language, and MIME type
- Plugin capability matching and priority routing
- Result aggregation and ranking across multiple plugins
- Context merging for search results
- Performance optimizations with caching
- Load balancing across plugins
"""

# Legacy import for backwards compatibility
from .dispatcher_enhanced import EnhancedDispatcher
from .dispatcher_enhanced import EnhancedDispatcher as Dispatcher
from .plugin_router import (
    FileTypeInfo,
    FileTypeMatcher,
    IFileTypeMatcher,
    IPluginRouter,
    PluginCapability,
    PluginRouter,
    RouteResult,
)
from .result_aggregator import (
    AggregatedResult,
    AggregationStats,
    IAggregationStrategy,
    IResultAggregator,
    RankingCriteria,
    ResultAggregator,
    SimpleAggregationStrategy,
    SmartAggregationStrategy,
)

__all__ = [
    "Dispatcher",  # Legacy alias
    "EnhancedDispatcher",
    "PluginRouter",
    "FileTypeMatcher",
    "IPluginRouter",
    "IFileTypeMatcher",
    "PluginCapability",
    "FileTypeInfo",
    "RouteResult",
    "ResultAggregator",
    "IResultAggregator",
    "SimpleAggregationStrategy",
    "SmartAggregationStrategy",
    "IAggregationStrategy",
    "AggregatedResult",
    "AggregationStats",
    "RankingCriteria",
]
