"""Performance monitoring for the multi-tier cache system."""
import asyncio
import logging
import time
import statistics
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Callable
from enum import Enum
import json
from pathlib import Path

from .tiered_cache import TieredCache, CacheTier

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class PerformanceMetric:
    """Single performance metric measurement."""
    timestamp: float
    metric_name: str
    value: float
    tier: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceAlert:
    """Performance alert."""
    timestamp: float
    level: AlertLevel
    message: str
    metric_name: str
    current_value: float
    threshold: float
    tier: Optional[str] = None


@dataclass
class PerformanceThreshold:
    """Performance threshold configuration."""
    metric_name: str
    warning_threshold: float
    critical_threshold: float
    comparison: str = "greater"  # "greater", "less", "equal"
    window_size: int = 60  # seconds
    min_samples: int = 5


class PerformanceMonitor:
    """Monitors and analyzes cache performance metrics."""
    
    def __init__(self, cache: TieredCache, report_interval: int = 60):
        self.cache = cache
        self.report_interval = report_interval
        
        # Metrics storage
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.alerts: deque = deque(maxlen=100)
        
        # Performance thresholds
        self.thresholds = self._setup_default_thresholds()
        
        # Monitoring state
        self._running = True
        self._monitor_task: Optional[asyncio.Task] = None
        self._last_stats = {}
        
        # Performance history for trending
        self.performance_history = {
            "hit_rates": deque(maxlen=100),
            "response_times": deque(maxlen=100),
            "memory_usage": deque(maxlen=100),
            "tier_distribution": deque(maxlen=100)
        }
        
        self._start_monitoring()
    
    def _setup_default_thresholds(self) -> Dict[str, PerformanceThreshold]:
        """Setup default performance thresholds."""
        return {
            "hit_rate": PerformanceThreshold(
                metric_name="hit_rate",
                warning_threshold=0.8,  # 80%
                critical_threshold=0.7,  # 70%
                comparison="less"
            ),
            "avg_response_time": PerformanceThreshold(
                metric_name="avg_response_time",
                warning_threshold=10.0,  # 10ms
                critical_threshold=50.0,  # 50ms
                comparison="greater"
            ),
            "memory_usage_percent": PerformanceThreshold(
                metric_name="memory_usage_percent",
                warning_threshold=80.0,  # 80%
                critical_threshold=95.0,  # 95%
                comparison="greater"
            ),
            "l1_eviction_rate": PerformanceThreshold(
                metric_name="l1_eviction_rate",
                warning_threshold=10.0,  # 10 evictions/min
                critical_threshold=50.0,  # 50 evictions/min
                comparison="greater"
            )
        }
    
    def _start_monitoring(self):
        """Start the background monitoring task."""
        self._monitor_task = asyncio.create_task(self._monitoring_loop())
    
    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while self._running:
            try:
                await asyncio.sleep(self.report_interval)
                await self._collect_metrics()
                await self._check_thresholds()
                await self._update_trends()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in performance monitoring loop: {e}")
    
    async def _collect_metrics(self):
        """Collect performance metrics from cache."""
        try:
            current_stats = await self.cache.get_stats()
            timestamp = time.time()
            
            # Overall metrics
            overall = current_stats.get("overall", {})
            self._record_metric("hit_rate", overall.get("hit_rate", 0.0), timestamp)
            self._record_metric("total_requests", overall.get("total_requests", 0), timestamp)
            self._record_metric("avg_response_time", overall.get("avg_access_time_ms", 0.0), timestamp)
            
            # Tier-specific metrics
            tiers = current_stats.get("tiers", {})
            for tier_name, tier_stats in tiers.items():
                self._record_metric(f"{tier_name.lower()}_hits", tier_stats.get("hits", 0), timestamp, tier_name)
                self._record_metric(f"{tier_name.lower()}_misses", tier_stats.get("misses", 0), timestamp, tier_name)
                self._record_metric(f"{tier_name.lower()}_size_bytes", tier_stats.get("size_bytes", 0), timestamp, tier_name)
                
                # Calculate derived metrics
                if tier_name == "L1":
                    # Memory usage percentage
                    current_memory = tier_stats.get("size_bytes", 0)
                    max_memory = self.cache.l1_max_memory_bytes
                    memory_percent = (current_memory / max_memory) * 100 if max_memory > 0 else 0
                    self._record_metric("memory_usage_percent", memory_percent, timestamp, tier_name)
                    
                    # Eviction rate (evictions per minute)
                    current_evictions = tier_stats.get("evictions", 0)
                    if self._last_stats.get("l1_evictions") is not None:
                        eviction_rate = (current_evictions - self._last_stats["l1_evictions"]) * (60 / self.report_interval)
                        self._record_metric("l1_eviction_rate", eviction_rate, timestamp, tier_name)
                    self._last_stats["l1_evictions"] = current_evictions
            
            # Access patterns metrics
            patterns = current_stats.get("access_patterns", {})
            self._record_metric("hot_keys_count", patterns.get("hot_keys", 0), timestamp)
            self._record_metric("cold_keys_count", patterns.get("cold_keys", 0), timestamp)
            self._record_metric("total_tracked_patterns", patterns.get("total_tracked", 0), timestamp)
            
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
    
    def _record_metric(self, name: str, value: float, timestamp: float, tier: Optional[str] = None):
        """Record a performance metric."""
        metric = PerformanceMetric(
            timestamp=timestamp,
            metric_name=name,
            value=value,
            tier=tier
        )
        self.metrics[name].append(metric)
    
    async def _check_thresholds(self):
        """Check metrics against performance thresholds."""
        for threshold in self.thresholds.values():
            await self._check_single_threshold(threshold)
    
    async def _check_single_threshold(self, threshold: PerformanceThreshold):
        """Check a single performance threshold."""
        metric_data = self.metrics.get(threshold.metric_name)
        if not metric_data or len(metric_data) < threshold.min_samples:
            return
        
        # Get recent values within the time window
        current_time = time.time()
        window_start = current_time - threshold.window_size
        
        recent_values = [
            m.value for m in metric_data 
            if m.timestamp >= window_start
        ]
        
        if len(recent_values) < threshold.min_samples:
            return
        
        # Calculate average value
        avg_value = statistics.mean(recent_values)
        
        # Check thresholds
        alert_level = None
        threshold_value = None
        
        if threshold.comparison == "greater":
            if avg_value >= threshold.critical_threshold:
                alert_level = AlertLevel.CRITICAL
                threshold_value = threshold.critical_threshold
            elif avg_value >= threshold.warning_threshold:
                alert_level = AlertLevel.WARNING
                threshold_value = threshold.warning_threshold
        
        elif threshold.comparison == "less":
            if avg_value <= threshold.critical_threshold:
                alert_level = AlertLevel.CRITICAL
                threshold_value = threshold.critical_threshold
            elif avg_value <= threshold.warning_threshold:
                alert_level = AlertLevel.WARNING
                threshold_value = threshold.warning_threshold
        
        # Create alert if threshold exceeded
        if alert_level:
            await self._create_alert(
                level=alert_level,
                message=f"{threshold.metric_name} {threshold.comparison} threshold: {avg_value:.2f}",
                metric_name=threshold.metric_name,
                current_value=avg_value,
                threshold=threshold_value
            )
    
    async def _create_alert(self, level: AlertLevel, message: str, 
                           metric_name: str, current_value: float, 
                           threshold: float, tier: Optional[str] = None):
        """Create a performance alert."""
        alert = PerformanceAlert(
            timestamp=time.time(),
            level=level,
            message=message,
            metric_name=metric_name,
            current_value=current_value,
            threshold=threshold,
            tier=tier
        )
        
        self.alerts.append(alert)
        
        # Log the alert
        log_func = logger.info
        if level == AlertLevel.WARNING:
            log_func = logger.warning
        elif level == AlertLevel.CRITICAL:
            log_func = logger.critical
        
        log_func(f"Performance alert: {message}")
    
    async def _update_trends(self):
        """Update performance trend data."""
        try:
            current_stats = await self.cache.get_stats()
            timestamp = time.time()
            
            # Hit rate trend
            overall = current_stats.get("overall", {})
            hit_rate = overall.get("hit_rate", 0.0)
            self.performance_history["hit_rates"].append((timestamp, hit_rate))
            
            # Response time trend
            response_time = overall.get("avg_access_time_ms", 0.0)
            self.performance_history["response_times"].append((timestamp, response_time))
            
            # Memory usage trend (L1)
            tiers = current_stats.get("tiers", {})
            l1_stats = tiers.get("L1", {})
            memory_usage = l1_stats.get("size_bytes", 0)
            self.performance_history["memory_usage"].append((timestamp, memory_usage))
            
            # Tier distribution (percentage of hits per tier)
            total_hits = sum(tier.get("hits", 0) for tier in tiers.values())
            if total_hits > 0:
                tier_dist = {
                    tier: (stats.get("hits", 0) / total_hits) * 100
                    for tier, stats in tiers.items()
                }
                self.performance_history["tier_distribution"].append((timestamp, tier_dist))
                
        except Exception as e:
            logger.error(f"Error updating trends: {e}")
    
    def get_performance_summary(self, time_window: int = 3600) -> Dict[str, Any]:
        """Get performance summary for the specified time window."""
        current_time = time.time()
        window_start = current_time - time_window
        
        summary = {
            "time_window_seconds": time_window,
            "metrics": {},
            "alerts": [],
            "trends": {},
            "recommendations": []
        }
        
        # Aggregate metrics
        for metric_name, metric_data in self.metrics.items():
            recent_values = [
                m.value for m in metric_data 
                if m.timestamp >= window_start
            ]
            
            if recent_values:
                summary["metrics"][metric_name] = {
                    "current": recent_values[-1],
                    "average": statistics.mean(recent_values),
                    "min": min(recent_values),
                    "max": max(recent_values),
                    "std_dev": statistics.stdev(recent_values) if len(recent_values) > 1 else 0.0,
                    "sample_count": len(recent_values)
                }
        
        # Recent alerts
        recent_alerts = [
            {
                "timestamp": alert.timestamp,
                "level": alert.level.value,
                "message": alert.message,
                "metric": alert.metric_name,
                "value": alert.current_value,
                "threshold": alert.threshold
            }
            for alert in self.alerts
            if alert.timestamp >= window_start
        ]
        summary["alerts"] = recent_alerts
        
        # Trends analysis
        summary["trends"] = self._analyze_trends(time_window)
        
        # Performance recommendations
        summary["recommendations"] = self._generate_recommendations(summary["metrics"])
        
        return summary
    
    def _analyze_trends(self, time_window: int) -> Dict[str, Any]:
        """Analyze performance trends."""
        current_time = time.time()
        window_start = current_time - time_window
        
        trends = {}
        
        for trend_name, trend_data in self.performance_history.items():
            recent_data = [
                (ts, value) for ts, value in trend_data
                if ts >= window_start
            ]
            
            if len(recent_data) >= 2:
                # Calculate trend direction
                first_half = recent_data[:len(recent_data)//2]
                second_half = recent_data[len(recent_data)//2:]
                
                if trend_name == "tier_distribution":
                    # Special handling for tier distribution
                    trends[trend_name] = "stable"  # Simplified
                else:
                    first_avg = statistics.mean([v for _, v in first_half])
                    second_avg = statistics.mean([v for _, v in second_half])
                    
                    change_percent = ((second_avg - first_avg) / first_avg) * 100 if first_avg > 0 else 0
                    
                    if abs(change_percent) < 5:
                        trends[trend_name] = "stable"
                    elif change_percent > 0:
                        trends[trend_name] = f"increasing ({change_percent:.1f}%)"
                    else:
                        trends[trend_name] = f"decreasing ({abs(change_percent):.1f}%)"
        
        return trends
    
    def _generate_recommendations(self, metrics: Dict[str, Any]) -> List[str]:
        """Generate performance improvement recommendations."""
        recommendations = []
        
        # Hit rate recommendations
        hit_rate_data = metrics.get("hit_rate", {})
        if hit_rate_data and hit_rate_data.get("average", 0) < 0.8:
            recommendations.append(
                "Hit rate is below 80%. Consider increasing cache TTL or L1 cache size."
            )
        
        # Response time recommendations
        response_time_data = metrics.get("avg_response_time", {})
        if response_time_data and response_time_data.get("average", 0) > 10:
            recommendations.append(
                "Average response time is above 10ms. Consider optimizing cache key generation or increasing L1 capacity."
            )
        
        # Memory usage recommendations
        memory_usage_data = metrics.get("memory_usage_percent", {})
        if memory_usage_data and memory_usage_data.get("average", 0) > 85:
            recommendations.append(
                "L1 memory usage is high. Consider increasing max memory or implementing better eviction strategies."
            )
        
        # Eviction rate recommendations
        eviction_rate_data = metrics.get("l1_eviction_rate", {})
        if eviction_rate_data and eviction_rate_data.get("average", 0) > 20:
            recommendations.append(
                "High L1 eviction rate detected. Consider increasing L1 cache size or adjusting access patterns."
            )
        
        return recommendations
    
    async def export_metrics(self, file_path: Path, format: str = "json") -> bool:
        """Export metrics to file."""
        try:
            metrics_data = {
                "timestamp": time.time(),
                "metrics": {
                    name: [
                        {
                            "timestamp": m.timestamp,
                            "value": m.value,
                            "tier": m.tier
                        }
                        for m in data
                    ]
                    for name, data in self.metrics.items()
                },
                "alerts": [
                    {
                        "timestamp": alert.timestamp,
                        "level": alert.level.value,
                        "message": alert.message,
                        "metric_name": alert.metric_name,
                        "current_value": alert.current_value,
                        "threshold": alert.threshold,
                        "tier": alert.tier
                    }
                    for alert in self.alerts
                ]
            }
            
            if format.lower() == "json":
                with open(file_path, 'w') as f:
                    json.dump(metrics_data, f, indent=2)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to export metrics: {e}")
            return False
    
    def add_custom_threshold(self, threshold: PerformanceThreshold):
        """Add a custom performance threshold."""
        self.thresholds[threshold.metric_name] = threshold
        logger.info(f"Added custom threshold for {threshold.metric_name}")
    
    def get_real_time_metrics(self) -> Dict[str, Any]:
        """Get current real-time metrics."""
        real_time = {}
        
        for metric_name, metric_data in self.metrics.items():
            if metric_data:
                latest = metric_data[-1]
                real_time[metric_name] = {
                    "value": latest.value,
                    "timestamp": latest.timestamp,
                    "tier": latest.tier
                }
        
        return real_time
    
    async def shutdown(self):
        """Shutdown the performance monitor."""
        self._running = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Performance monitor shutdown complete")