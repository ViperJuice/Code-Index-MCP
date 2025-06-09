# Monitoring Framework Documentation

## Overview

The MCP Server includes a comprehensive monitoring framework built on Prometheus and Grafana, providing real-time metrics, alerting, and visualization capabilities.

## Components

### 1. Prometheus Exporter
The server exposes metrics in Prometheus format at `/metrics` endpoint.

#### Key Metrics

**Request Metrics:**
- `mcp_requests_total` - Total requests by method, endpoint, and status
- `mcp_request_duration_seconds` - Request duration histogram

**Plugin Metrics:**
- `mcp_plugin_load_duration_seconds` - Plugin loading time
- `mcp_plugin_status` - Plugin active/inactive status
- `mcp_plugin_errors_total` - Plugin error counts

**Indexing Metrics:**
- `mcp_symbols_indexed_total` - Total symbols indexed by language and type
- `mcp_files_indexed_total` - Total files indexed by language
- `mcp_indexing_duration_seconds` - File indexing duration

**Search Metrics:**
- `mcp_search_requests_total` - Search requests by type and language
- `mcp_search_duration_seconds` - Search query duration
- `mcp_search_results_count` - Number of search results

**Cache Metrics:**
- `mcp_cache_hits_total` - Cache hit count
- `mcp_cache_misses_total` - Cache miss count
- `mcp_cache_evictions_total` - Cache evictions by reason

**System Metrics:**
- `mcp_memory_usage_bytes` - Memory usage (RSS/VMS)
- `mcp_cpu_usage_percent` - CPU usage percentage
- `mcp_active_threads` - Active thread count

### 2. Grafana Dashboards

Pre-configured dashboards provide visualization for:
- Request rate and latency
- Plugin status and performance
- Cache hit rates
- Memory and CPU usage
- Error rates and alerts

### 3. Alerting Rules

Prometheus alerting rules monitor:
- High error rates (> 0.1 errors/sec)
- Plugin load failures
- High memory usage (> 2GB)
- Slow request latency (p95 > 1s)
- Low cache hit rate (< 50%)
- Database connection pool exhaustion
- Service availability

## Deployment

### Using Docker Compose

```bash
# Start monitoring stack
docker-compose -f docker-compose.monitoring.yml up -d

# Access services
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3000 (admin/admin)
# Alertmanager: http://localhost:9093
```

### Manual Configuration

1. **Configure Prometheus:**
```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'mcp_server'
    static_configs:
      - targets: ['mcp-server:8000']
```

2. **Import Grafana Dashboard:**
- Login to Grafana
- Go to Dashboards → Import
- Upload `/monitoring/grafana/dashboards/mcp-server-dashboard.json`

3. **Configure Alerts:**
- Copy alert rules to Prometheus config
- Configure Alertmanager for notifications

## Usage

### Accessing Metrics

```bash
# Raw Prometheus metrics
curl http://localhost:8000/metrics

# JSON metrics (requires auth)
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/metrics/json
```

### Custom Metrics

Add custom metrics in your code:

```python
from mcp_server.metrics.prometheus_exporter import get_prometheus_exporter

exporter = get_prometheus_exporter()

# Record custom metric
exporter.record_plugin_load("my_plugin", "python", 0.5, success=True)

# Increment counter
exporter.plugin_errors.labels(
    plugin="my_plugin",
    language="python",
    error_type="parse_error"
).inc()
```

### Dashboard Customization

Edit dashboard JSON or use Grafana UI to:
- Add new panels
- Create custom queries
- Set up annotations
- Configure variables

## Performance Impact

The monitoring framework has minimal performance impact:
- Metrics collection: < 1ms overhead
- Memory usage: ~10MB for metric storage
- CPU usage: < 1% for metric calculation

## Best Practices

1. **Metric Naming:**
   - Use consistent prefixes (`mcp_`)
   - Include units in metric names (`_seconds`, `_bytes`)
   - Use labels for dimensions

2. **Cardinality:**
   - Avoid high-cardinality labels
   - Use bounded label values
   - Monitor metric count

3. **Alerting:**
   - Set appropriate thresholds
   - Use multi-window alerts
   - Configure notification channels

4. **Dashboard Design:**
   - Group related metrics
   - Use appropriate visualizations
   - Include helpful annotations

## Troubleshooting

### Missing Metrics
- Check if MCP server is running
- Verify Prometheus can reach the server
- Check for authentication issues

### High Memory Usage
- Reduce metric retention
- Decrease scrape frequency
- Limit label cardinality

### Alert Fatigue
- Tune alert thresholds
- Add alert dependencies
- Use alert inhibition rules

## Integration Examples

### With Kubernetes
```yaml
apiVersion: v1
kind: Service
metadata:
  name: mcp-server
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "8000"
    prometheus.io/path: "/metrics"
```

### With CloudWatch
```python
# Export to CloudWatch
import boto3
cloudwatch = boto3.client('cloudwatch')

# Send custom metric
cloudwatch.put_metric_data(
    Namespace='MCP',
    MetricData=[{
        'MetricName': 'RequestCount',
        'Value': request_count,
        'Unit': 'Count'
    }]
)
```

## Security Considerations

1. **Metric Endpoint Access:**
   - `/metrics` is public by default
   - `/metrics/json` requires authentication
   - Consider reverse proxy for production

2. **Sensitive Data:**
   - Don't expose secrets in labels
   - Sanitize user-provided values
   - Use aggregated metrics

3. **Resource Limits:**
   - Set metric count limits
   - Configure retention policies
   - Monitor storage usage