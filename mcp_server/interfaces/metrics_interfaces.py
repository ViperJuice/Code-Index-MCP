"""
Metrics and Monitoring Interfaces

All interfaces related to metrics collection, monitoring, and observability.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from .shared_interfaces import IMetrics, Result

# ========================================
# Metrics Data Types
# ========================================


@dataclass
class MetricDefinition:
    """Definition of a metric"""

    name: str
    metric_type: str  # counter, gauge, histogram, summary
    description: str
    unit: str
    labels: List[str]
    namespace: Optional[str] = None


@dataclass
class MetricSample:
    """A single metric sample"""

    metric_name: str
    value: float
    timestamp: datetime
    labels: Dict[str, str]
    metadata: Dict[str, Any] = None


@dataclass
class AlertRule:
    """Alert rule definition"""

    rule_id: str
    name: str
    metric_name: str
    condition: str  # gt, lt, eq, etc.
    threshold: float
    duration: timedelta
    severity: str  # critical, warning, info
    description: str
    is_active: bool = True


@dataclass
class Alert:
    """Alert instance"""

    alert_id: str
    rule_id: str
    metric_name: str
    current_value: float
    threshold: float
    severity: str
    description: str
    triggered_at: datetime
    resolved_at: Optional[datetime] = None
    status: str = "firing"  # firing, resolved


@dataclass
class HealthCheckResult:
    """Health check result"""

    check_name: str
    status: str  # healthy, unhealthy, degraded
    response_time: float
    timestamp: datetime
    details: Dict[str, Any] = None
    error: Optional[str] = None


# ========================================
# Core Metrics Interfaces
# ========================================


class IMetricsCollector(IMetrics):
    """Enhanced metrics collector interface"""

    @abstractmethod
    def define_metric(self, definition: MetricDefinition) -> Result[None]:
        """Define a new metric"""

    @abstractmethod
    def record_metric(self, sample: MetricSample) -> None:
        """Record a metric sample"""

    @abstractmethod
    def get_metric_value(self, metric_name: str, labels: Dict[str, str] = None) -> Optional[float]:
        """Get current value of a metric"""

    @abstractmethod
    def get_metric_history(
        self, metric_name: str, start_time: datetime, end_time: datetime
    ) -> List[MetricSample]:
        """Get metric history"""

    @abstractmethod
    def list_metrics(self) -> List[str]:
        """List all defined metrics"""

    @abstractmethod
    def delete_metric(self, metric_name: str) -> Result[None]:
        """Delete a metric"""


class IMetricsRegistry(ABC):
    """Interface for metrics registry"""

    @abstractmethod
    def register_collector(self, collector: IMetricsCollector) -> None:
        """Register a metrics collector"""

    @abstractmethod
    def unregister_collector(self, collector: IMetricsCollector) -> None:
        """Unregister a metrics collector"""

    @abstractmethod
    def get_all_metrics(self) -> Dict[str, List[MetricSample]]:
        """Get all metrics from all collectors"""

    @abstractmethod
    def get_metrics_by_namespace(self, namespace: str) -> Dict[str, List[MetricSample]]:
        """Get metrics by namespace"""


class IMetricsExporter(ABC):
    """Interface for exporting metrics"""

    @abstractmethod
    async def export_metrics(
        self, metrics: List[MetricSample], format: str = "prometheus"
    ) -> Result[str]:
        """Export metrics in specified format"""

    @abstractmethod
    async def send_to_endpoint(self, endpoint: str, metrics: List[MetricSample]) -> Result[None]:
        """Send metrics to an endpoint"""

    @abstractmethod
    def get_supported_formats(self) -> List[str]:
        """Get supported export formats"""


# ========================================
# Monitoring Interfaces
# ========================================


class IHealthMonitor(ABC):
    """Interface for health monitoring"""

    @abstractmethod
    async def register_health_check(
        self, name: str, check_func: Callable[[], HealthCheckResult]
    ) -> None:
        """Register a health check"""

    @abstractmethod
    async def unregister_health_check(self, name: str) -> None:
        """Unregister a health check"""

    @abstractmethod
    async def run_health_check(self, name: str) -> Result[HealthCheckResult]:
        """Run a specific health check"""

    @abstractmethod
    async def run_all_health_checks(self) -> Result[List[HealthCheckResult]]:
        """Run all health checks"""

    @abstractmethod
    async def get_overall_health(self) -> Result[str]:
        """Get overall system health status"""


class IPerformanceMonitor(ABC):
    """Interface for performance monitoring"""

    @abstractmethod
    def start_timer(self, operation: str, labels: Dict[str, str] = None) -> str:
        """Start a performance timer"""

    @abstractmethod
    def stop_timer(self, timer_id: str) -> float:
        """Stop a timer and return duration"""

    @abstractmethod
    def record_duration(
        self, operation: str, duration: float, labels: Dict[str, str] = None
    ) -> None:
        """Record operation duration"""

    @abstractmethod
    def get_performance_stats(self, operation: str) -> Dict[str, Any]:
        """Get performance statistics"""


class IResourceMonitor(ABC):
    """Interface for resource monitoring"""

    @abstractmethod
    async def get_cpu_usage(self) -> float:
        """Get CPU usage percentage"""

    @abstractmethod
    async def get_memory_usage(self) -> Dict[str, int]:
        """Get memory usage information"""

    @abstractmethod
    async def get_disk_usage(self) -> Dict[str, Any]:
        """Get disk usage information"""

    @abstractmethod
    async def get_network_stats(self) -> Dict[str, Any]:
        """Get network statistics"""

    @abstractmethod
    async def get_process_info(self) -> Dict[str, Any]:
        """Get process information"""


# ========================================
# Alerting Interfaces
# ========================================


class IAlertManager(ABC):
    """Interface for alert management"""

    @abstractmethod
    async def create_alert_rule(self, rule: AlertRule) -> Result[str]:
        """Create an alert rule"""

    @abstractmethod
    async def update_alert_rule(self, rule_id: str, updates: Dict[str, Any]) -> Result[None]:
        """Update an alert rule"""

    @abstractmethod
    async def delete_alert_rule(self, rule_id: str) -> Result[None]:
        """Delete an alert rule"""

    @abstractmethod
    async def evaluate_rules(self) -> Result[List[Alert]]:
        """Evaluate all alert rules"""

    @abstractmethod
    async def get_active_alerts(self) -> Result[List[Alert]]:
        """Get active alerts"""

    @abstractmethod
    async def resolve_alert(self, alert_id: str) -> Result[None]:
        """Resolve an alert"""


class INotificationService(ABC):
    """Interface for sending notifications"""

    @abstractmethod
    async def send_alert(self, alert: Alert, channels: List[str]) -> Result[None]:
        """Send alert notification"""

    @abstractmethod
    async def register_channel(self, channel_name: str, config: Dict[str, Any]) -> Result[None]:
        """Register notification channel"""

    @abstractmethod
    async def test_channel(self, channel_name: str) -> Result[bool]:
        """Test notification channel"""

    @abstractmethod
    def get_supported_channels(self) -> List[str]:
        """Get supported notification channels"""


# ========================================
# Prometheus Integration Interfaces
# ========================================


class IPrometheusExporter(IMetricsExporter):
    """Interface for Prometheus metrics export"""

    @abstractmethod
    def get_prometheus_metrics(self) -> str:
        """Get metrics in Prometheus format"""

    @abstractmethod
    def register_prometheus_metric(
        self,
        metric_name: str,
        metric_type: str,
        description: str,
        labels: List[str] = None,
    ) -> None:
        """Register a Prometheus metric"""

    @abstractmethod
    def update_prometheus_metric(
        self, metric_name: str, value: float, labels: Dict[str, str] = None
    ) -> None:
        """Update a Prometheus metric"""

    @abstractmethod
    def start_http_server(self, port: int = 8000) -> None:
        """Start Prometheus HTTP metrics server"""


class IPrometheusRegistry(ABC):
    """Interface for Prometheus registry"""

    @abstractmethod
    def register_collector(self, collector: Any) -> None:
        """Register a Prometheus collector"""

    @abstractmethod
    def unregister_collector(self, collector: Any) -> None:
        """Unregister a Prometheus collector"""

    @abstractmethod
    def collect(self) -> str:
        """Collect all metrics"""


# ========================================
# Tracing Interfaces
# ========================================


class ITracer(ABC):
    """Interface for distributed tracing"""

    @abstractmethod
    def start_span(self, operation_name: str, parent_span: Optional[Any] = None) -> Any:
        """Start a trace span"""

    @abstractmethod
    def finish_span(self, span: Any) -> None:
        """Finish a trace span"""

    @abstractmethod
    def add_tag(self, span: Any, key: str, value: str) -> None:
        """Add tag to span"""

    @abstractmethod
    def add_log(self, span: Any, fields: Dict[str, Any]) -> None:
        """Add log to span"""

    @abstractmethod
    def inject_context(self, span: Any, headers: Dict[str, str]) -> Dict[str, str]:
        """Inject trace context into headers"""

    @abstractmethod
    def extract_context(self, headers: Dict[str, str]) -> Optional[Any]:
        """Extract trace context from headers"""


class ISpanProcessor(ABC):
    """Interface for processing spans"""

    @abstractmethod
    def on_start(self, span: Any) -> None:
        """Called when span starts"""

    @abstractmethod
    def on_end(self, span: Any) -> None:
        """Called when span ends"""

    @abstractmethod
    def shutdown(self) -> None:
        """Shutdown processor"""


# ========================================
# Logging Integration Interfaces
# ========================================


class IMetricsLogger(ABC):
    """Interface for logging metrics"""

    @abstractmethod
    def log_metric(self, metric_name: str, value: float, labels: Dict[str, str] = None) -> None:
        """Log a metric value"""

    @abstractmethod
    def log_performance(self, operation: str, duration: float, success: bool = True) -> None:
        """Log performance metric"""

    @abstractmethod
    def log_error_metric(self, error_type: str, count: int = 1) -> None:
        """Log error metric"""


class IStructuredLogger(ABC):
    """Interface for structured logging with metrics"""

    @abstractmethod
    def log_with_metrics(
        self,
        level: str,
        message: str,
        metrics: Dict[str, float],
        context: Dict[str, Any] = None,
    ) -> None:
        """Log message with associated metrics"""

    @abstractmethod
    def create_correlation_id(self) -> str:
        """Create correlation ID for request tracking"""

    @abstractmethod
    def log_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration: float,
        correlation_id: str,
    ) -> None:
        """Log HTTP request with metrics"""


# ========================================
# Custom Metrics Interfaces
# ========================================


class IBusinessMetrics(ABC):
    """Interface for business-specific metrics"""

    @abstractmethod
    def track_api_usage(self, endpoint: str, user_id: str, response_time: float) -> None:
        """Track API usage metrics"""

    @abstractmethod
    def track_indexing_performance(self, file_count: int, duration: float, language: str) -> None:
        """Track indexing performance"""

    @abstractmethod
    def track_search_performance(self, query_type: str, result_count: int, duration: float) -> None:
        """Track search performance"""

    @abstractmethod
    def track_plugin_performance(
        self, plugin_name: str, operation: str, duration: float, success: bool
    ) -> None:
        """Track plugin performance"""


class ICustomMetricsCollector(ABC):
    """Interface for custom metrics collection"""

    @abstractmethod
    def collect_custom_metrics(self) -> List[MetricSample]:
        """Collect custom application metrics"""

    @abstractmethod
    def register_custom_metric(self, name: str, collector_func: Callable[[], float]) -> None:
        """Register custom metric collector"""

    @abstractmethod
    def get_metric_metadata(self, metric_name: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a metric"""
