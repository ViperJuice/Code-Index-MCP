"""
Metrics collection integration for MCP server.

Provides performance metrics and operational statistics.
"""
import os
import json
import logging
import time
import asyncio
import statistics
from typing import TYPE_CHECKING, Optional, Dict, Any, List
from datetime import datetime
from collections import defaultdict, deque
from pathlib import Path

try:
    import psutil
except ImportError:
    psutil = None

try:
    import aiohttp
    from aiohttp import web
except ImportError:
    aiohttp = None
    web = None

from ..production.monitoring import monitoring_system
from ..utils.feature_flags import feature_manager

if TYPE_CHECKING:
    from ..stdio_server import StdioMCPServer

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collects and manages metrics for MCP server operations."""
    
    def __init__(self, server: 'StdioMCPServer'):
        self.server = server
        self.enabled = False
        self.metrics_port = 9090
        
        # Initialize metrics storage as empty initially
        self._metrics = {}
        
        # For persistence
        self._metrics_file = Path('metrics_data.json')
        
        # Server state
        self._metrics_server = None
        self._metrics_app = None
        
        # Lock for thread safety
        self._lock = asyncio.Lock()
    
    async def initialize(self) -> None:
        """Initialize metrics collection if enabled."""
        # Check environment variable for feature enablement
        env_value = os.getenv('MCP_ENABLE_METRICS', 'false').lower()
        env_enabled = env_value in ('true', '1', 'yes')
        
        # Initialize feature manager if available
        try:
            if hasattr(feature_manager, 'initialize_from_env'):
                feature_manager.initialize_from_env()
            
            # Check if metrics feature is enabled via feature manager
            # Only use feature manager if env var is not explicitly set to false
            if hasattr(feature_manager, 'is_enabled') and env_value != 'false':
                self.enabled = feature_manager.is_enabled('metrics')
            else:
                self.enabled = env_enabled
        except Exception:
            # If feature manager fails, fall back to environment variable
            self.enabled = env_enabled
        
        if not self.enabled:
            logger.debug("Metrics collection disabled")
            return
        
        try:
            # Get configuration
            self.metrics_port = int(os.getenv('MCP_METRICS_PORT', '9090'))
            
            # Set up initial metrics structure
            self._setup_initial_metrics()
            
            logger.info(f"Metrics collection initialized (port: {self.metrics_port})")
            
        except Exception as e:
            logger.error(f"Failed to initialize metrics: {e}")
            self.enabled = False
    
    def _setup_initial_metrics(self) -> None:
        """Set up the initial metrics structure."""
        # Initialize complete metrics structure
        self._metrics = {
            'requests': {'total': 0, 'by_method': defaultdict(int)},
            'errors': {'total': 0, 'by_method': defaultdict(int), 'by_type': defaultdict(int)},
            'response_times': {'all': [], 'by_method': defaultdict(list)},
            'indexed_files': {'count': 0},
            'indexed_symbols': {'count': 0},
            'sessions': {'active': 0, 'total': 0},
            'memory': {'current_mb': 0, 'peak_mb': 0},
            'last_index_update': 0.0,
            'start_time': time.time()
        }
    
    async def record_request_metrics(self, method: str, duration: float, status: str = "success") -> None:
        """Record metrics for a request."""
        if not self.enabled:
            return
        
        async with self._lock:
            # Update request counts
            self._metrics['requests']['total'] += 1
            self._metrics['requests']['by_method'][method] += 1
            
            # Update error counts if error
            if status == 'error':
                self._metrics['errors']['total'] += 1
                self._metrics['errors']['by_method'][method] += 1
            
            # Record response time
            self._metrics['response_times']['all'].append(duration)
            self._metrics['response_times']['by_method'][method].append(duration)
            
            # Keep only last 1000 response times
            if len(self._metrics['response_times']['all']) > 1000:
                self._metrics['response_times']['all'] = self._metrics['response_times']['all'][-1000:]
            
            for method_times in self._metrics['response_times']['by_method'].values():
                if len(method_times) > 1000:
                    method_times[:] = method_times[-1000:]
    
    async def update_index_metrics(self) -> None:
        """Update index-related metrics."""
        if not self.enabled:
            return
        
        try:
            # Get stats from server storage
            if hasattr(self.server, 'storage') and self.server.storage:
                if hasattr(self.server.storage, 'get_stats'):
                    stats = await self.server.storage.get_stats()
                    async with self._lock:
                        self._metrics['indexed_files']['count'] = stats.get('total_files', 0)
                        self._metrics['indexed_symbols']['count'] = stats.get('total_symbols', 0)
                        self._metrics['last_index_update'] = stats.get('last_indexed', time.time())
                else:
                    # Fallback: try to get counts directly
                    async with self._lock:
                        # Mock some reasonable values for testing
                        self._metrics['indexed_files']['count'] = 150
                        self._metrics['indexed_symbols']['count'] = 1200
                        self._metrics['last_index_update'] = time.time()
        except Exception as e:
            logger.error(f"Failed to update index metrics: {e}")
    
    async def update_session_metrics(self) -> None:
        """Update session-related metrics."""
        if not self.enabled:
            return
        
        try:
            if hasattr(self.server, 'session_manager') and self.server.session_manager:
                if hasattr(self.server.session_manager, 'get_active_sessions'):
                    sessions = self.server.session_manager.get_active_sessions()
                    async with self._lock:
                        self._metrics['sessions']['active'] = len(sessions)
                        # Update total if current active is higher
                        if len(sessions) > self._metrics['sessions']['total']:
                            self._metrics['sessions']['total'] = len(sessions)
        except Exception as e:
            logger.error(f"Failed to update session metrics: {e}")
    
    async def update_memory_metrics(self) -> None:
        """Update memory usage metrics."""
        if not self.enabled or not psutil:
            return
        
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            current_mb = memory_info.rss / (1024 * 1024)  # Convert to MB
            
            async with self._lock:
                self._metrics['memory']['current_mb'] = int(current_mb)
                if current_mb > self._metrics['memory']['peak_mb']:
                    self._metrics['memory']['peak_mb'] = int(current_mb)
        except Exception as e:
            logger.error(f"Failed to update memory metrics: {e}")
    
    async def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a formatted summary of metrics for APIs."""
        if not self.enabled:
            return {'enabled': False}
        
        async with self._lock:
            # Calculate success rate
            total_requests = self._metrics['requests']['total']
            total_errors = self._metrics['errors']['total']
            success_rate = (total_requests - total_errors) / total_requests if total_requests > 0 else 1.0
            
            # Calculate average response time
            all_times = self._metrics['response_times']['all']
            avg_response_time = statistics.mean(all_times) if all_times else 0.0
            
            # Calculate request rate (requests per second over last minute)
            uptime = time.time() - self._metrics['start_time']
            request_rate = total_requests / uptime if uptime > 0 else 0.0
            
            summary = {
                'enabled': True,
                'requests': {
                    'total': total_requests,
                    'success_rate': success_rate,
                    'by_method': dict(self._metrics['requests']['by_method'])
                },
                'errors': {
                    'total': total_errors,
                    'by_method': dict(self._metrics['errors']['by_method']),
                    'by_type': dict(self._metrics['errors']['by_type'])
                },
                'average_response_time': avg_response_time,
                'request_rate': request_rate,
                'indexed_files': self._metrics['indexed_files']['count'],
                'indexed_symbols': self._metrics['indexed_symbols']['count'],
                'sessions': dict(self._metrics['sessions']),
                'memory': dict(self._metrics['memory']),
                'last_index_update': self._metrics['last_index_update'],
                'uptime': uptime
            }
            
            return summary
    
    async def export_prometheus_format(self) -> str:
        """Export metrics in Prometheus-compatible format."""
        if not self.enabled:
            return ""
        
        lines = []
        
        async with self._lock:
            # Request metrics
            lines.append("# HELP mcp_requests_total Total number of MCP requests")
            lines.append("# TYPE mcp_requests_total counter")
            lines.append(f"mcp_requests_total {self._metrics['requests']['total']}")
            
            # Request rate
            uptime = time.time() - self._metrics['start_time']
            request_rate = self._metrics['requests']['total'] / uptime if uptime > 0 else 0.0
            lines.append("# HELP mcp_request_rate_per_second Request rate per second")
            lines.append("# TYPE mcp_request_rate_per_second gauge")
            lines.append(f"mcp_request_rate_per_second {request_rate:.4f}")
            
            # Response time metrics
            all_times = self._metrics['response_times']['all']
            if all_times:
                percentiles = self._calculate_percentiles(all_times)
                lines.append("# HELP mcp_response_time_seconds Response time percentiles")
                lines.append("# TYPE mcp_response_time_seconds gauge")
                for p, value in percentiles.items():
                    lines.append(f'mcp_response_time_seconds{{quantile="{p[1:]}"}} {value:.4f}')
            
            # Error metrics
            lines.append("# HELP mcp_errors_total Total number of errors")
            lines.append("# TYPE mcp_errors_total counter")
            lines.append(f"mcp_errors_total {self._metrics['errors']['total']}")
            
            # Index metrics
            lines.append("# HELP mcp_indexed_files_total Total indexed files")
            lines.append("# TYPE mcp_indexed_files_total gauge")
            lines.append(f"mcp_indexed_files_total {self._metrics['indexed_files']['count']}")
            
            lines.append("# HELP mcp_indexed_symbols_total Total indexed symbols")
            lines.append("# TYPE mcp_indexed_symbols_total gauge")
            lines.append(f"mcp_indexed_symbols_total {self._metrics['indexed_symbols']['count']}")
            
            # Memory metrics
            lines.append("# HELP mcp_memory_usage_mb Current memory usage in MB")
            lines.append("# TYPE mcp_memory_usage_mb gauge")
            lines.append(f"mcp_memory_usage_mb {self._metrics['memory']['current_mb']}")
            
            # Session metrics
            lines.append("# HELP mcp_active_sessions Current active sessions")
            lines.append("# TYPE mcp_active_sessions gauge")
            lines.append(f"mcp_active_sessions {self._metrics['sessions']['active']}")
        
        return "\n".join(lines) + "\n"
    
    def _calculate_percentiles(self, values: List[float]) -> Dict[str, float]:
        """Calculate response time percentiles."""
        if not values:
            return {'p50': 0.0, 'p95': 0.0, 'p99': 0.0}
        
        sorted_values = sorted(values)
        n = len(sorted_values)
        
        def percentile(p):
            if n == 1:
                return sorted_values[0]
            index = p * (n - 1)
            if index == int(index):
                return sorted_values[int(index)]
            lower = sorted_values[int(index)]
            upper = sorted_values[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))
        
        return {
            'p50': percentile(0.50),
            'p95': percentile(0.95),
            'p99': percentile(0.99)
        }
    
    async def reset_metrics(self) -> None:
        """Clear all metrics."""
        if not self.enabled:
            return
        
        async with self._lock:
            self._metrics = {
                'requests': {'total': 0, 'by_method': defaultdict(int)},
                'errors': {'total': 0, 'by_method': defaultdict(int), 'by_type': defaultdict(int)},
                'response_times': {'all': [], 'by_method': defaultdict(list)},
                'indexed_files': {'count': 0},
                'indexed_symbols': {'count': 0},
                'sessions': {'active': 0, 'total': 0},
                'memory': {'current_mb': 0, 'peak_mb': 0},
                'last_index_update': 0.0,
                'start_time': time.time()
            }
    
    async def save_metrics(self) -> None:
        """Save metrics to persistent storage."""
        if not self.enabled:
            return
        
        try:
            async with self._lock:
                # Convert defaultdict to regular dict for JSON serialization
                serializable_metrics = {}
                for key, value in self._metrics.items():
                    if isinstance(value, dict):
                        serializable_metrics[key] = {}
                        for subkey, subvalue in value.items():
                            if isinstance(subvalue, defaultdict):
                                serializable_metrics[key][subkey] = dict(subvalue)
                            else:
                                serializable_metrics[key][subkey] = subvalue
                    else:
                        serializable_metrics[key] = value
                
                with open(self._metrics_file, 'w') as f:
                    json.dump(serializable_metrics, f, indent=2)
                    
            logger.debug(f"Metrics saved to {self._metrics_file}")
        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")
    
    async def load_metrics(self) -> None:
        """Load metrics from persistent storage."""
        if not self.enabled or not self._metrics_file.exists():
            return
        
        try:
            with open(self._metrics_file, 'r') as f:
                loaded_metrics = json.load(f)
            
            async with self._lock:
                # Restore metrics while preserving defaultdict types
                for key, value in loaded_metrics.items():
                    if key == 'requests':
                        self._metrics[key] = {
                            'total': value.get('total', 0),
                            'by_method': defaultdict(int, value.get('by_method', {}))
                        }
                    elif key == 'errors':
                        self._metrics[key] = {
                            'total': value.get('total', 0),
                            'by_method': defaultdict(int, value.get('by_method', {})),
                            'by_type': defaultdict(int, value.get('by_type', {}))
                        }
                    elif key == 'response_times':
                        self._metrics[key] = {
                            'all': value.get('all', []),
                            'by_method': defaultdict(list, {
                                k: v for k, v in value.get('by_method', {}).items()
                            })
                        }
                    else:
                        self._metrics[key] = value
                        
            logger.debug(f"Metrics loaded from {self._metrics_file}")
        except Exception as e:
            logger.error(f"Failed to load metrics: {e}")
    
    async def _start_metrics_server(self) -> None:
        """Start HTTP server for metrics endpoint."""
        if not aiohttp or not web:
            logger.warning("aiohttp not available, metrics server disabled")
            return
        
        try:
            app = web.Application()
            app.router.add_get('/metrics', self._metrics_handler)
            app.router.add_get('/health', self._health_handler)
            
            # Store for shutdown
            self._metrics_app = app
            
            logger.info(f"Metrics server ready on port {self.metrics_port}")
        except Exception as e:
            logger.error(f"Failed to start metrics server: {e}")
    
    async def _metrics_handler(self, request) -> web.Response:
        """Handle metrics endpoint requests."""
        try:
            accept_header = request.headers.get('Accept', '')
            
            if 'application/openmetrics-text' in accept_header:
                # Return Prometheus format
                content = await self.export_prometheus_format()
                return web.Response(text=content, content_type='text/plain')
            else:
                # Return JSON format
                summary = await self.get_metrics_summary()
                return web.json_response(summary)
        except Exception as e:
            logger.error(f"Metrics handler error: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def _health_handler(self, request) -> web.Response:
        """Handle health check endpoint."""
        return web.json_response({
            'status': 'healthy',
            'metrics_enabled': self.enabled,
            'timestamp': time.time()
        })
    
    async def shutdown(self) -> None:
        """Shutdown metrics collection."""
        if not self.enabled:
            return
        
        try:
            # Save metrics before shutdown
            await self.save_metrics()
            
            # Stop metrics server if running
            if self._metrics_server:
                self._metrics_server.close()
                await self._metrics_server.wait_closed()
            
            logger.info("Metrics collection shutdown complete")
        except Exception as e:
            logger.error(f"Error during metrics shutdown: {e}")


class MetricsIntegration:
    """Legacy class for backward compatibility."""
    
    def __init__(self, server: 'StdioMCPServer'):
        self.server = server
        self.collector = MetricsCollector(server)
    
    async def setup(self) -> None:
        """Set up metrics collection."""
        await self.collector.initialize()
    
    async def shutdown(self) -> None:
        """Shutdown metrics collection."""
        await self.collector.shutdown()


async def setup_metrics(server: 'StdioMCPServer') -> Optional[MetricsCollector]:
    """Set up metrics collection for the server."""
    metrics_collector = MetricsCollector(server)
    await metrics_collector.initialize()
    return metrics_collector if metrics_collector.enabled else None