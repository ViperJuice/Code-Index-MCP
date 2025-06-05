"""
Monitoring and metrics system for MCP server.

Provides comprehensive monitoring, alerting, and performance tracking.
"""

import asyncio
import time
import logging
from typing import Dict, List, Optional, Any, Callable, Union, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict, deque
import statistics
import json

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"
    TIMER = "timer"


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class MetricValue:
    """A metric value with metadata."""
    name: str
    value: Union[int, float]
    type: MetricType
    timestamp: datetime = field(default_factory=datetime.now)
    labels: Dict[str, str] = field(default_factory=dict)
    help_text: str = ""


@dataclass
class Alert:
    """An alert with details."""
    id: str
    name: str
    severity: AlertSeverity
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    labels: Dict[str, str] = field(default_factory=dict)
    resolved: bool = False
    resolved_at: Optional[datetime] = None


@dataclass
class AlertRule:
    """Rule for triggering alerts."""
    name: str
    metric_name: str
    condition: str  # e.g., "> 100", "< 50"
    threshold: float
    severity: AlertSeverity
    duration: timedelta = timedelta(minutes=1)
    labels: Dict[str, str] = field(default_factory=dict)
    description: str = ""


class MetricsCollector:
    """Collector for various types of metrics."""
    
    def __init__(self):
        self._metrics: Dict[str, MetricValue] = {}
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._timers: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._lock = asyncio.Lock()
    
    async def counter(self, name: str, value: float = 1.0, 
                     labels: Optional[Dict[str, str]] = None,
                     help_text: str = "") -> None:
        """Increment a counter metric."""
        async with self._lock:
            key = self._make_key(name, labels)
            self._counters[key] += value
            
            self._metrics[key] = MetricValue(
                name=name,
                value=self._counters[key],
                type=MetricType.COUNTER,
                labels=labels or {},
                help_text=help_text
            )
    
    async def gauge(self, name: str, value: float,
                   labels: Optional[Dict[str, str]] = None,
                   help_text: str = "") -> None:
        """Set a gauge metric."""
        async with self._lock:
            key = self._make_key(name, labels)
            self._gauges[key] = value
            
            self._metrics[key] = MetricValue(
                name=name,
                value=value,
                type=MetricType.GAUGE,
                labels=labels or {},
                help_text=help_text
            )
    
    async def histogram(self, name: str, value: float,
                       labels: Optional[Dict[str, str]] = None,
                       help_text: str = "") -> None:
        """Add value to histogram metric."""
        async with self._lock:
            key = self._make_key(name, labels)
            self._histograms[key].append(value)
            
            # Keep only last 10000 values
            if len(self._histograms[key]) > 10000:
                self._histograms[key] = self._histograms[key][-10000:]
            
            # Calculate statistics
            values = self._histograms[key]
            stats = {
                "count": len(values),
                "sum": sum(values),
                "avg": statistics.mean(values),
                "min": min(values),
                "max": max(values),
                "p50": statistics.median(values),
                "p95": self._percentile(values, 0.95),
                "p99": self._percentile(values, 0.99)
            }
            
            self._metrics[key] = MetricValue(
                name=name,
                value=stats,
                type=MetricType.HISTOGRAM,
                labels=labels or {},
                help_text=help_text
            )
    
    async def timer(self, name: str, duration: float,
                   labels: Optional[Dict[str, str]] = None,
                   help_text: str = "") -> None:
        """Record timer metric."""
        await self.histogram(f"{name}_duration", duration, labels, help_text)
        
        # Also track as timer for rate calculations
        async with self._lock:
            key = self._make_key(name, labels)
            self._timers[key].append((time.time(), duration))
            
            # Calculate rate (operations per second)
            now = time.time()
            recent_ops = [op for op_time, _ in self._timers[key] if now - op_time <= 60]
            rate = len(recent_ops) / 60.0  # ops per second
            
            self._metrics[f"{key}_rate"] = MetricValue(
                name=f"{name}_rate",
                value=rate,
                type=MetricType.GAUGE,
                labels=labels or {},
                help_text=f"Rate of {name} operations per second"
            )
    
    def _make_key(self, name: str, labels: Optional[Dict[str, str]]) -> str:
        """Create a unique key for a metric."""
        if not labels:
            return name
        
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"
    
    def _percentile(self, values: List[float], p: float) -> float:
        """Calculate percentile."""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = int(p * (len(sorted_values) - 1))
        return sorted_values[index]
    
    async def get_metrics(self) -> Dict[str, MetricValue]:
        """Get all current metrics."""
        async with self._lock:
            return dict(self._metrics)
    
    async def get_metric(self, name: str, labels: Optional[Dict[str, str]] = None) -> Optional[MetricValue]:
        """Get a specific metric."""
        key = self._make_key(name, labels)
        async with self._lock:
            return self._metrics.get(key)
    
    async def clear_metrics(self) -> None:
        """Clear all metrics."""
        async with self._lock:
            self._metrics.clear()
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
            self._timers.clear()


class PerformanceMonitor:
    """Monitor for performance metrics."""
    
    def __init__(self, collector: MetricsCollector):
        self.collector = collector
        self._request_times: Dict[str, float] = {}
        self._active_requests: Set[str] = set()
    
    async def start_request(self, request_id: str, method: str,
                           labels: Optional[Dict[str, str]] = None) -> None:
        """Start tracking a request."""
        start_time = time.time()
        self._request_times[request_id] = start_time
        self._active_requests.add(request_id)
        
        # Track active requests
        await self.collector.gauge(
            "active_requests",
            len(self._active_requests),
            labels=labels,
            help_text="Number of active requests"
        )
        
        # Increment request counter
        request_labels = {"method": method}
        if labels:
            request_labels.update(labels)
        
        await self.collector.counter(
            "requests_total",
            labels=request_labels,
            help_text="Total number of requests"
        )
    
    async def end_request(self, request_id: str, method: str, status: str,
                         labels: Optional[Dict[str, str]] = None) -> Optional[float]:
        """End tracking a request and record metrics."""
        if request_id not in self._request_times:
            return None
        
        start_time = self._request_times.pop(request_id)
        self._active_requests.discard(request_id)
        duration = time.time() - start_time
        
        # Update active requests count
        await self.collector.gauge(
            "active_requests",
            len(self._active_requests),
            labels=labels,
            help_text="Number of active requests"
        )
        
        # Record request duration
        request_labels = {"method": method, "status": status}
        if labels:
            request_labels.update(labels)
        
        await self.collector.histogram(
            "request_duration_seconds",
            duration,
            labels=request_labels,
            help_text="Request duration in seconds"
        )
        
        await self.collector.timer(
            "requests",
            duration,
            labels=request_labels,
            help_text="Request processing time"
        )
        
        return duration
    
    async def record_error(self, error_type: str, method: str,
                          labels: Optional[Dict[str, str]] = None) -> None:
        """Record an error metric."""
        error_labels = {"error_type": error_type, "method": method}
        if labels:
            error_labels.update(labels)
        
        await self.collector.counter(
            "errors_total",
            labels=error_labels,
            help_text="Total number of errors"
        )
    
    async def record_cache_hit(self, cache_name: str, hit: bool,
                              labels: Optional[Dict[str, str]] = None) -> None:
        """Record cache hit/miss metrics."""
        cache_labels = {"cache": cache_name, "result": "hit" if hit else "miss"}
        if labels:
            cache_labels.update(labels)
        
        await self.collector.counter(
            "cache_operations_total",
            labels=cache_labels,
            help_text="Total cache operations"
        )
    
    async def record_database_operation(self, operation: str, duration: float,
                                       labels: Optional[Dict[str, str]] = None) -> None:
        """Record database operation metrics."""
        db_labels = {"operation": operation}
        if labels:
            db_labels.update(labels)
        
        await self.collector.timer(
            "database_operations",
            duration,
            labels=db_labels,
            help_text="Database operation time"
        )
        
        await self.collector.counter(
            "database_operations_total",
            labels=db_labels,
            help_text="Total database operations"
        )


class AlertManager:
    """Manager for alerts and alerting rules."""
    
    def __init__(self, collector: MetricsCollector):
        self.collector = collector
        self._rules: Dict[str, AlertRule] = {}
        self._active_alerts: Dict[str, Alert] = {}
        self._alert_history: List[Alert] = []
        self._callbacks: List[Callable[[Alert], None]] = []
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._check_interval = 10.0  # 10 seconds
    
    def add_rule(self, rule: AlertRule) -> None:
        """Add an alerting rule."""
        self._rules[rule.name] = rule
        logger.info(f"Added alerting rule: {rule.name}")
    
    def remove_rule(self, name: str) -> bool:
        """Remove an alerting rule."""
        if name in self._rules:
            del self._rules[name]
            logger.info(f"Removed alerting rule: {name}")
            return True
        return False
    
    def register_callback(self, callback: Callable[[Alert], None]) -> None:
        """Register callback for alerts."""
        self._callbacks.append(callback)
    
    def unregister_callback(self, callback: Callable[[Alert], None]) -> None:
        """Unregister callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    async def start_monitoring(self, interval: float = 10.0) -> None:
        """Start alert monitoring."""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._check_interval = interval
        self._monitor_task = asyncio.create_task(self._monitoring_loop())
        logger.info(f"Alert monitoring started (interval: {interval}s)")
    
    async def stop_monitoring(self) -> None:
        """Stop alert monitoring."""
        if not self._monitoring:
            return
        
        self._monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Alert monitoring stopped")
    
    async def _monitoring_loop(self) -> None:
        """Main alerting monitoring loop."""
        while self._monitoring:
            try:
                await self._check_rules()
                await asyncio.sleep(self._check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Alert monitoring error: {e}")
                await asyncio.sleep(self._check_interval)
    
    async def _check_rules(self) -> None:
        """Check all alerting rules."""
        metrics = await self.collector.get_metrics()
        
        for rule in self._rules.values():
            try:
                await self._check_rule(rule, metrics)
            except Exception as e:
                logger.error(f"Error checking rule {rule.name}: {e}")
    
    async def _check_rule(self, rule: AlertRule, metrics: Dict[str, MetricValue]) -> None:
        """Check a specific alerting rule."""
        # Find matching metrics
        matching_metrics = [
            metric for name, metric in metrics.items()
            if metric.name == rule.metric_name
        ]
        
        for metric in matching_metrics:
            if self._evaluate_condition(metric.value, rule.condition, rule.threshold):
                await self._trigger_alert(rule, metric)
            else:
                await self._resolve_alert(rule, metric)
    
    def _evaluate_condition(self, value: Union[int, float, Dict], 
                           condition: str, threshold: float) -> bool:
        """Evaluate alert condition."""
        # Handle complex metric values (like histograms)
        if isinstance(value, dict):
            if "avg" in value:
                check_value = value["avg"]
            elif "p95" in value:
                check_value = value["p95"]
            else:
                check_value = value.get("value", 0)
        else:
            check_value = value
        
        if condition.startswith(">"):
            return check_value > threshold
        elif condition.startswith("<"):
            return check_value < threshold
        elif condition.startswith(">="):
            return check_value >= threshold
        elif condition.startswith("<="):
            return check_value <= threshold
        elif condition.startswith("=="):
            return check_value == threshold
        elif condition.startswith("!="):
            return check_value != threshold
        else:
            logger.warning(f"Unknown condition: {condition}")
            return False
    
    async def _trigger_alert(self, rule: AlertRule, metric: MetricValue) -> None:
        """Trigger an alert."""
        alert_id = f"{rule.name}_{self._make_key(metric.name, metric.labels)}"
        
        # Check if alert already exists
        if alert_id in self._active_alerts:
            return
        
        alert = Alert(
            id=alert_id,
            name=rule.name,
            severity=rule.severity,
            message=f"{rule.description} - {metric.name}={metric.value} {rule.condition} {rule.threshold}",
            labels=dict(rule.labels, **metric.labels)
        )
        
        self._active_alerts[alert_id] = alert
        self._alert_history.append(alert)
        
        # Keep history limited
        if len(self._alert_history) > 1000:
            self._alert_history = self._alert_history[-1000:]
        
        logger.warning(f"Alert triggered: {alert.name} - {alert.message}")
        
        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")
    
    async def _resolve_alert(self, rule: AlertRule, metric: MetricValue) -> None:
        """Resolve an alert."""
        alert_id = f"{rule.name}_{self._make_key(metric.name, metric.labels)}"
        
        if alert_id in self._active_alerts:
            alert = self._active_alerts.pop(alert_id)
            alert.resolved = True
            alert.resolved_at = datetime.now()
            
            logger.info(f"Alert resolved: {alert.name}")
            
            # Notify callbacks
            for callback in self._callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    logger.error(f"Alert callback error: {e}")
    
    def _make_key(self, name: str, labels: Dict[str, str]) -> str:
        """Create key from metric name and labels."""
        if not labels:
            return name
        
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts."""
        return list(self._active_alerts.values())
    
    def get_alert_history(self, limit: Optional[int] = None) -> List[Alert]:
        """Get alert history."""
        if limit:
            return self._alert_history[-limit:]
        return self._alert_history.copy()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alerts to dictionary."""
        return {
            "active_alerts": [
                {
                    "id": alert.id,
                    "name": alert.name,
                    "severity": alert.severity.value,
                    "message": alert.message,
                    "timestamp": alert.timestamp.isoformat(),
                    "labels": alert.labels
                }
                for alert in self._active_alerts.values()
            ],
            "alert_count": len(self._active_alerts),
            "rules_count": len(self._rules)
        }


class MonitoringSystem:
    """Main monitoring system that coordinates all components."""
    
    def __init__(self):
        self.metrics = MetricsCollector()
        self.performance = PerformanceMonitor(self.metrics)
        self.alerts = AlertManager(self.metrics)
        self._setup_default_rules()
    
    def _setup_default_rules(self) -> None:
        """Setup default alerting rules."""
        # High error rate
        self.alerts.add_rule(AlertRule(
            name="high_error_rate",
            metric_name="errors_total",
            condition="> 10",
            threshold=10.0,
            severity=AlertSeverity.WARNING,
            description="High error rate detected"
        ))
        
        # Slow requests
        self.alerts.add_rule(AlertRule(
            name="slow_requests",
            metric_name="request_duration_seconds",
            condition="> 5.0",
            threshold=5.0,
            severity=AlertSeverity.WARNING,
            description="Slow requests detected"
        ))
        
        # High memory usage (handled by health checks, but also alert)
        self.alerts.add_rule(AlertRule(
            name="high_memory_usage",
            metric_name="memory_usage_percent",
            condition="> 90",
            threshold=90.0,
            severity=AlertSeverity.CRITICAL,
            description="Critical memory usage"
        ))
    
    async def start(self) -> None:
        """Start the monitoring system."""
        await self.alerts.start_monitoring()
        logger.info("Monitoring system started")
    
    async def stop(self) -> None:
        """Stop the monitoring system."""
        await self.alerts.stop_monitoring()
        logger.info("Monitoring system stopped")
    
    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for monitoring dashboard."""
        metrics = await self.metrics.get_metrics()
        alerts = self.alerts.to_dict()
        
        return {
            "metrics": {
                name: {
                    "name": metric.name,
                    "value": metric.value,
                    "type": metric.type.value,
                    "timestamp": metric.timestamp.isoformat(),
                    "labels": metric.labels,
                    "help": metric.help_text
                }
                for name, metric in metrics.items()
            },
            "alerts": alerts,
            "timestamp": datetime.now().isoformat()
        }


# Global monitoring system instance
monitoring_system = MonitoringSystem()