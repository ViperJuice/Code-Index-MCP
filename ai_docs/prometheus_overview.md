# Prometheus Overview

## Introduction

Prometheus is an open-source monitoring and alerting toolkit designed for reliability and scalability. It excels at collecting time-series metrics from distributed systems and providing powerful querying capabilities through PromQL.

## Architecture Overview

### Core Components

1. **Prometheus Server**
   - Scrapes and stores time-series data
   - Evaluates rules and generates alerts
   - Provides HTTP API for queries

2. **Client Libraries**
   - Python client: `prometheus_client`
   - Instrumenting application code
   - Exposing metrics endpoints

3. **Exporters**
   - Bridge between application metrics and Prometheus
   - Built-in exporters for common services
   - Custom exporters for domain-specific metrics

4. **AlertManager**
   - Handles alerts from Prometheus
   - Routes, groups, and dispatches notifications
   - Integrates with external systems (PagerDuty, Slack, email)

### Data Model

```
metric_name{label1="value1", label2="value2"} value timestamp
```

Example:
```
code_index_files_processed{language="python", status="success"} 1523
```

## Python Setup and Integration

### Installation

```bash
pip install prometheus-client
```

### Basic Metrics Types

```python
from prometheus_client import Counter, Histogram, Gauge, Summary

# Counter: only goes up
files_indexed = Counter('code_index_files_total', 
                       'Total files indexed',
                       ['language', 'status'])

# Gauge: can go up and down  
active_indexing_tasks = Gauge('code_index_active_tasks',
                             'Number of active indexing tasks')

# Histogram: observations in buckets
indexing_duration = Histogram('code_index_duration_seconds',
                            'Time spent indexing files',
                            ['language'])

# Summary: statistical distribution
file_size_bytes = Summary('code_index_file_size_bytes',
                         'Size of indexed files')
```

### FastAPI Integration

```python
from fastapi import FastAPI
from prometheus_client import make_asgi_app, Counter, Histogram
import time

app = FastAPI()

# Metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

# Middleware for automatic metrics
@app.middleware("http")
async def prometheus_middleware(request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    http_requests_total.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    http_request_duration.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)
    
    return response

# Mount metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)
```

## MCP Server Specific Implementations

### Code Indexing Metrics

```python
# mcp_server/metrics.py
from prometheus_client import Counter, Histogram, Gauge, Info
from functools import wraps
import time

# Application info
app_info = Info('code_index_mcp_info', 'MCP server information')
app_info.info({'version': '1.0.0', 'environment': 'production'})

# Indexing metrics
indexing_operations = Counter(
    'code_index_operations_total',
    'Total indexing operations',
    ['operation', 'language', 'status']
)

indexing_duration = Histogram(
    'code_index_operation_duration_seconds',
    'Duration of indexing operations',
    ['operation', 'language'],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0)
)

index_size = Gauge(
    'code_index_size_bytes',
    'Size of code index in bytes',
    ['index_type']
)

active_watchers = Gauge(
    'code_index_active_watchers',
    'Number of active file watchers'
)

# Parser metrics
parse_errors = Counter(
    'code_index_parse_errors_total',
    'Total parsing errors',
    ['language', 'error_type']
)

ast_nodes_processed = Counter(
    'code_index_ast_nodes_total',
    'Total AST nodes processed',
    ['language', 'node_type']
)

# Decorator for timing operations
def measure_duration(operation, language=None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            labels = {'operation': operation}
            if language:
                labels['language'] = language
            
            with indexing_duration.labels(**labels).time():
                try:
                    result = func(*args, **kwargs)
                    indexing_operations.labels(
                        operation=operation,
                        language=language or 'unknown',
                        status='success'
                    ).inc()
                    return result
                except Exception as e:
                    indexing_operations.labels(
                        operation=operation,
                        language=language or 'unknown',
                        status='error'
                    ).inc()
                    raise
        return wrapper
    return decorator
```

### Plugin Metrics Integration

```python
# mcp_server/plugin_base.py
from abc import ABC, abstractmethod
from prometheus_client import Counter, Histogram
from .metrics import measure_duration

class PluginBase(ABC):
    def __init__(self, language: str):
        self.language = language
        
        # Plugin-specific metrics
        self.plugin_calls = Counter(
            f'code_index_{language}_plugin_calls_total',
            f'Total calls to {language} plugin methods',
            ['method']
        )
        
        self.plugin_duration = Histogram(
            f'code_index_{language}_plugin_duration_seconds',
            f'Duration of {language} plugin operations',
            ['method']
        )
    
    @measure_duration('parse_file')
    def parse_file(self, file_path: str):
        """Parse file with metrics"""
        self.plugin_calls.labels(method='parse_file').inc()
        with self.plugin_duration.labels(method='parse_file').time():
            return self._parse_file_impl(file_path)
    
    @abstractmethod
    def _parse_file_impl(self, file_path: str):
        """Actual parsing implementation"""
        pass
```

### Watcher Metrics

```python
# mcp_server/watcher.py
from watchdog.observers import Observer
from prometheus_client import Counter, Gauge
from .metrics import active_watchers

file_system_events = Counter(
    'code_index_fs_events_total',
    'Total file system events',
    ['event_type', 'language']
)

class MetricsFileWatcher:
    def __init__(self):
        self.observer = Observer()
        active_watchers.inc()
    
    def on_created(self, event):
        language = self._detect_language(event.src_path)
        file_system_events.labels(
            event_type='created',
            language=language
        ).inc()
    
    def on_modified(self, event):
        language = self._detect_language(event.src_path)
        file_system_events.labels(
            event_type='modified',
            language=language
        ).inc()
    
    def stop(self):
        self.observer.stop()
        active_watchers.dec()
```

## Alerting Configuration

### Alert Rules (prometheus.yml)

```yaml
groups:
  - name: code_indexing_alerts
    interval: 30s
    rules:
      - alert: HighIndexingErrorRate
        expr: |
          rate(code_index_operations_total{status="error"}[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate in code indexing"
          description: "{{ $labels.language }} indexing error rate is {{ $value }}%"
      
      - alert: SlowIndexingOperations
        expr: |
          histogram_quantile(0.95, 
            rate(code_index_operation_duration_seconds_bucket[5m])
          ) > 30
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Slow indexing operations detected"
          description: "95th percentile indexing time is {{ $value }}s"
      
      - alert: IndexSizeGrowth
        expr: |
          rate(code_index_size_bytes[1h]) > 1073741824  # 1GB/hour
        for: 30m
        labels:
          severity: info
        annotations:
          summary: "Rapid index size growth"
          description: "Index growing at {{ $value | humanize }}B/s"
```

### AlertManager Configuration

```yaml
# alertmanager.yml
global:
  resolve_timeout: 5m

route:
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'team-indexing'
  
  routes:
    - match:
        severity: critical
      receiver: 'pagerduty-indexing'
    
    - match:
        alertname: IndexSizeGrowth
      receiver: 'email-ops'

receivers:
  - name: 'team-indexing'
    slack_configs:
      - api_url: 'YOUR_SLACK_WEBHOOK_URL'
        channel: '#code-indexing-alerts'
        title: 'Code Indexing Alert'
        text: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'

  - name: 'pagerduty-indexing'
    pagerduty_configs:
      - service_key: 'YOUR_PAGERDUTY_KEY'
```

## Performance Monitoring Best Practices

### 1. Cardinality Management

```python
# BAD: High cardinality
file_metrics = Counter('files_processed', 'Files processed', ['file_path'])
# This creates a new time series for EVERY file

# GOOD: Controlled cardinality
file_metrics = Counter('files_processed', 'Files processed', 
                      ['language', 'project', 'status'])
```

### 2. Histogram Buckets

```python
# Custom buckets for code indexing operations
indexing_histogram = Histogram(
    'indexing_duration_seconds',
    'Time to index files',
    buckets=(
        0.01,   # 10ms - cached/small files
        0.05,   # 50ms - typical small file
        0.1,    # 100ms - medium file
        0.5,    # 500ms - large file
        1.0,    # 1s - very large file
        5.0,    # 5s - huge file
        10.0,   # 10s - massive file
        30.0,   # 30s - timeout threshold
        float('inf')
    )
)
```

### 3. Resource Metrics

```python
import psutil
from prometheus_client import Gauge

# System resource metrics
memory_usage = Gauge('code_index_memory_bytes', 
                    'Memory usage in bytes')
cpu_usage = Gauge('code_index_cpu_percent', 
                 'CPU usage percentage')

def update_resource_metrics():
    process = psutil.Process()
    memory_usage.set(process.memory_info().rss)
    cpu_usage.set(process.cpu_percent(interval=1))

# Update periodically
import threading
def metrics_updater():
    while True:
        update_resource_metrics()
        time.sleep(10)

threading.Thread(target=metrics_updater, daemon=True).start()
```

### 4. Query Examples

```promql
# Average indexing time by language (last 5 minutes)
avg by (language) (
  rate(code_index_operation_duration_seconds_sum[5m]) /
  rate(code_index_operation_duration_seconds_count[5m])
)

# Error rate by operation
sum by (operation) (
  rate(code_index_operations_total{status="error"}[5m])
) / sum by (operation) (
  rate(code_index_operations_total[5m])
) * 100

# Top 5 languages by indexing volume
topk(5, 
  sum by (language) (
    increase(code_index_operations_total[1h])
  )
)

# Memory usage trend
rate(code_index_memory_bytes[5m])
```

## Dashboard Example (Grafana)

```json
{
  "dashboard": {
    "title": "Code Index MCP Monitoring",
    "panels": [
      {
        "title": "Indexing Operations Rate",
        "targets": [{
          "expr": "sum(rate(code_index_operations_total[5m])) by (language)"
        }]
      },
      {
        "title": "Error Rate %",
        "targets": [{
          "expr": "sum(rate(code_index_operations_total{status=\"error\"}[5m])) / sum(rate(code_index_operations_total[5m])) * 100"
        }]
      },
      {
        "title": "95th Percentile Latency",
        "targets": [{
          "expr": "histogram_quantile(0.95, sum(rate(code_index_operation_duration_seconds_bucket[5m])) by (le, language))"
        }]
      },
      {
        "title": "Active Indexing Tasks",
        "targets": [{
          "expr": "code_index_active_tasks"
        }]
      }
    ]
  }
}
```

## Best Practices

### 1. Metric Naming Conventions
- Use lowercase with underscores
- Include unit suffix (_seconds, _bytes, _total)
- Start with service name (code_index_)
- Be descriptive but concise

### 2. Label Guidelines
- Keep cardinality low (<100 unique values per label)
- Use static labels for dimensions
- Avoid user IDs, file paths, timestamps
- Common labels: language, status, operation, error_type

### 3. Performance Tips
- Use batch operations for bulk metrics
- Implement sampling for high-frequency events
- Cache metric objects (don't recreate)
- Use child() for dynamic labels

### 4. Monitoring Strategy
- Monitor the monitors (meta-metrics)
- Set up alerting on key SLIs
- Use recording rules for complex queries
- Regular cleanup of unused metrics

## Integration Example

```python
# Complete MCP server monitoring setup
from fastapi import FastAPI
from prometheus_client import make_asgi_app
from contextlib import asynccontextmanager
import asyncio

from .metrics import (
    indexing_operations,
    indexing_duration,
    active_watchers,
    update_resource_metrics
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    metrics_task = asyncio.create_task(
        periodic_metrics_update()
    )
    yield
    # Shutdown
    metrics_task.cancel()

app = FastAPI(lifespan=lifespan)

async def periodic_metrics_update():
    while True:
        update_resource_metrics()
        await asyncio.sleep(10)

# Mount Prometheus metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Example endpoint with metrics
@app.post("/index/{language}")
async def index_file(language: str, file_path: str):
    with indexing_duration.labels(
        operation='api_index',
        language=language
    ).time():
        try:
            # Indexing logic here
            result = await index_file_async(file_path, language)
            
            indexing_operations.labels(
                operation='api_index',
                language=language,
                status='success'
            ).inc()
            
            return result
            
        except Exception as e:
            indexing_operations.labels(
                operation='api_index',
                language=language,
                status='error'
            ).inc()
            raise
```

This comprehensive Prometheus setup provides complete observability for the Code Index MCP server, enabling proactive monitoring, alerting, and performance optimization.