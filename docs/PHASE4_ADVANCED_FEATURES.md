# Phase 4: Advanced MCP Features Guide

This document provides a comprehensive guide to the advanced features implemented in Phase 4 of the MCP server refactoring.

## Overview

Phase 4 introduces production-ready features and advanced capabilities including:

- **Prompts System**: Template-based prompt generation and management
- **Performance Optimization**: Caching, connection pooling, memory optimization
- **Advanced Protocol Features**: Streaming, batch operations, completion/sampling
- **Production Features**: Comprehensive logging, health checks, monitoring, rate limiting
- **Self-contained Architecture**: Consolidated server with minimal external dependencies

## Table of Contents

1. [Prompts System](#prompts-system)
2. [Performance Optimization](#performance-optimization)
3. [Advanced Protocol Features](#advanced-protocol-features)
4. [Production Features](#production-features)
5. [Server Configuration](#server-configuration)
6. [API Reference](#api-reference)
7. [Deployment Guide](#deployment-guide)

## Prompts System

The prompts system provides template-based prompt generation with dynamic parameters.

### Core Components

- **PromptRegistry**: Manages prompt templates
- **PromptTemplate**: Defines reusable prompt templates
- **PromptHandler**: Handles MCP prompt requests

### Built-in Prompts

The system includes several built-in prompts:

- `code_review`: Comprehensive code review analysis
- `refactor_suggestions`: Refactoring recommendations
- `generate_documentation`: Documentation generation
- `bug_analysis`: Bug detection and analysis
- `generate_tests`: Unit test generation
- `performance_analysis`: Performance optimization analysis

### Usage Examples

#### Using Built-in Prompts

```python
from mcp_server.prompts import prompt_registry

# Generate a code review prompt
review_prompt = await prompt_registry.generate_prompt(
    "code_review",
    {
        "file_path": "src/main.py",
        "language": "python",
        "code": "def hello(): print('Hello, World!')"
    }
)
```

#### Creating Custom Prompts

```python
from mcp_server.prompts import PromptTemplate, PromptArgument

# Define a custom prompt
custom_prompt = PromptTemplate(
    name="api_documentation",
    description="Generate API documentation for endpoints",
    prompt="""Generate comprehensive API documentation for the following endpoint:

Endpoint: {endpoint}
Method: {method}
Parameters: {parameters}

Include:
1. Description
2. Request/Response examples
3. Error codes
4. Authentication requirements""",
    arguments=[
        PromptArgument("endpoint", "API endpoint path"),
        PromptArgument("method", "HTTP method"),
        PromptArgument("parameters", "Endpoint parameters")
    ],
    category="documentation",
    tags=["api", "docs", "openapi"]
)

# Register the prompt
prompt_registry.register_prompt(custom_prompt)
```

#### MCP Protocol Usage

```json
{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "prompts/get",
    "params": {
        "name": "code_review",
        "arguments": {
            "file_path": "main.py",
            "language": "python",
            "code": "def hello(): pass"
        }
    }
}
```

## Performance Optimization

### Connection Pooling

Efficient connection management for database and external services.

```python
from mcp_server.performance import ConnectionPool, ConnectionPoolConfig

# Configure connection pool
config = ConnectionPoolConfig(
    min_connections=5,
    max_connections=20,
    connection_timeout=30.0,
    idle_timeout=300.0,
    max_lifetime=3600.0
)

# Use connection pool
async with pool.get_connection() as conn:
    result = await conn.execute("SELECT * FROM data")
```

### Memory Optimization

Automatic memory monitoring and optimization.

```python
from mcp_server.performance import memory_optimizer

# Start memory monitoring
await memory_optimizer.start_monitoring(interval=30.0)

# Manual optimization
result = await memory_optimizer.optimize_memory()
print(f"Freed {result['memory_freed_mb']:.2f} MB")
```

### Rate Limiting

Multiple rate limiting algorithms with distributed support.

```python
from mcp_server.performance import RateLimiter, RateLimiterConfig, RateLimitAlgorithm

# Token bucket rate limiter
config = RateLimiterConfig(
    algorithm=RateLimitAlgorithm.TOKEN_BUCKET,
    max_requests=100,
    window_seconds=60.0,
    burst_limit=120
)

limiter = RateLimiter(config)
await limiter.start()

# Check rate limit
result = await limiter.check_limit("user_123")
if not result.allowed:
    print(f"Rate limited. Retry after {result.retry_after} seconds")
```

### Cache Management

Advanced caching with multiple backends.

```python
from mcp_server.cache import CacheManager, CacheConfig, CacheBackendType

# Configure cache
config = CacheConfig(
    backend_type=CacheBackendType.HYBRID,
    max_entries=10000,
    max_memory_mb=500,
    default_ttl=3600
)

cache = CacheManager(config)
await cache.initialize()

# Cache operations
await cache.set("key", {"data": "value"}, ttl=1800)
value = await cache.get("key")
```

## Advanced Protocol Features

### Completion and Sampling

Text completion with configurable sampling strategies.

```python
from mcp_server.protocol.advanced import CompletionEngine, CompletionRequest, SamplingConfig

engine = CompletionEngine()

request = CompletionRequest(
    prompt="def fibonacci(n):",
    model="template",
    sampling=SamplingConfig(
        temperature=0.7,
        max_tokens=150
    )
)

response = await engine.complete(request)
print(response.choices[0].text)
```

### Streaming Operations

Real-time streaming of responses.

```python
from mcp_server.protocol.advanced import StreamingManager

manager = StreamingManager()

# Start a stream
await manager.start_stream("stream_1", "completion", {
    "prompt": "Generate code",
    "model": "template"
})

# Read stream chunks
while True:
    chunk = await manager.get_stream_chunk("stream_1")
    if chunk is None:
        break
    print(chunk.data)
    if chunk.is_final:
        break
```

### Batch Operations

Process multiple requests efficiently.

```python
from mcp_server.protocol.advanced import BatchProcessor, BatchRequest

# Create batch request
batch = BatchRequest(
    id="batch_1",
    requests=[
        JsonRpcRequest(id=1, method="tools/list", params={}),
        JsonRpcRequest(id=2, method="resources/list", params={}),
        JsonRpcRequest(id=3, method="prompts/list", params={})
    ],
    parallel=True,
    max_concurrent=5
)

processor = BatchProcessor(handler)
response = await processor.process_batch(batch)

print(f"Completed: {response.completed}, Failed: {response.failed}")
```

## Production Features

### Structured Logging

Comprehensive logging with context and performance tracking.

```python
from mcp_server.production import production_logger

# Get structured logger
logger = production_logger.get_logger("my_component")

# Set global context
logger.set_context(user_id="user123", session_id="sess456")

# Log with context
logger.info("Operation completed", operation="data_sync", duration_ms=150.5)

# Log errors with stack traces
try:
    # Some operation
    pass
except Exception as e:
    logger.error("Operation failed", error=e, operation="data_sync")
```

### Health Checks

Comprehensive health monitoring.

```python
from mcp_server.production import health_checker, HealthCheck

# Custom health check
class DatabaseHealthCheck(HealthCheck):
    def __init__(self):
        super().__init__("database", timeout=5.0, critical=True)
    
    async def check(self):
        # Check database connectivity
        await self.db.ping()

# Register check
health_checker.register_check(DatabaseHealthCheck())

# Run checks
report = await health_checker.run_checks()
print(f"Overall status: {report.overall_status}")
```

### Metrics and Monitoring

Detailed metrics collection and alerting.

```python
from mcp_server.production import monitoring_system

# Record metrics
await monitoring_system.metrics.counter("requests_total", labels={"method": "POST"})
await monitoring_system.metrics.histogram("request_duration", 0.15, labels={"endpoint": "/api/data"})
await monitoring_system.metrics.gauge("active_connections", 25)

# Performance monitoring
await monitoring_system.performance.start_request("req_123", "tools/list")
# ... process request ...
await monitoring_system.performance.end_request("req_123", "tools/list", "success")
```

### Middleware Stack

Production middleware for request processing.

```python
from mcp_server.production import middleware_stack, ProductionMiddleware

# Create middleware with rate limiting
middleware = ProductionMiddleware(rate_limiter)
middleware_stack.set_default_middleware(middleware)

# Process request through middleware
response = await middleware_stack.process_request(
    request,
    handler,
    client_info={"user_id": "user123", "client_ip": "192.168.1.1"}
)
```

## Server Configuration

### Basic Configuration

```python
from mcp_server.server import MCPServer

# Create server with custom config
server = MCPServer("config/production.json")

# Override settings
server.settings.transport_type = "websocket"
server.settings.websocket_port = 8080
server.settings.debug = False

await server.start()
```

### Configuration File Format

```json
{
    "transport_type": "websocket",
    "websocket_host": "0.0.0.0",
    "websocket_port": 8080,
    "debug": false,
    "enabled_plugins": [
        "python_plugin",
        "js_plugin",
        "c_plugin"
    ],
    "cache_max_entries": 10000,
    "cache_max_memory_mb": 500,
    "log_file": "/var/log/mcp-server/app.log",
    "advanced_features_enabled": true,
    "streaming_enabled": true,
    "batch_operations_enabled": true,
    "prompts_enabled": true
}
```

### Environment Variables

```bash
# Transport
MCP_TRANSPORT_TYPE=websocket
MCP_WEBSOCKET_HOST=0.0.0.0
MCP_WEBSOCKET_PORT=8080

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/mcp-server/app.log

# Performance
CACHE_MAX_ENTRIES=10000
MEMORY_MONITOR_INTERVAL=30

# Security
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# Features
ADVANCED_FEATURES_ENABLED=true
STREAMING_ENABLED=true
BATCH_OPERATIONS_ENABLED=true
```

## API Reference

### Prompts API

#### List Prompts
```json
{
    "method": "prompts/list",
    "params": {
        "category": "code_analysis",
        "tag": "review"
    }
}
```

#### Get Prompt
```json
{
    "method": "prompts/get",
    "params": {
        "name": "code_review",
        "arguments": {
            "file_path": "src/main.py",
            "language": "python",
            "code": "def hello(): pass"
        }
    }
}
```

#### Search Prompts
```json
{
    "method": "prompts/search",
    "params": {
        "query": "documentation"
    }
}
```

### Advanced Protocol API

#### Text Completion
```json
{
    "method": "completion/generate",
    "params": {
        "prompt": "def calculate_fibonacci(n):",
        "model": "template",
        "sampling": {
            "temperature": 0.7,
            "max_tokens": 100
        }
    }
}
```

#### Start Stream
```json
{
    "method": "stream/start",
    "params": {
        "type": "completion",
        "params": {
            "prompt": "Generate a Python class",
            "model": "template"
        }
    }
}
```

#### Batch Request
```json
{
    "method": "batch",
    "params": {
        "id": "batch_001",
        "requests": [
            {"id": 1, "method": "tools/list", "params": {}},
            {"id": 2, "method": "resources/list", "params": {}}
        ],
        "parallel": true,
        "max_concurrent": 5
    }
}
```

### Health and Monitoring API

#### Health Check
```json
{
    "method": "health/check",
    "params": {}
}
```

#### Server Status
```json
{
    "method": "server/status",
    "params": {}
}
```

#### Metrics
```json
{
    "method": "metrics/get",
    "params": {
        "format": "prometheus"
    }
}
```

## Deployment Guide

### Production Deployment

1. **Environment Setup**
```bash
# Install dependencies
pip install -r requirements-production.txt

# Set environment variables
export MCP_ENVIRONMENT=production
export DATABASE_URL=postgresql://user:pass@db:5432/mcp
export REDIS_URL=redis://redis:6379
export JWT_SECRET_KEY=your-secure-secret-key
```

2. **Configuration**
```bash
# Create production config
cat > config/production.json << EOF
{
    "transport_type": "websocket",
    "websocket_host": "0.0.0.0",
    "websocket_port": 8080,
    "debug": false,
    "log_file": "/var/log/mcp-server/app.log",
    "cache_max_entries": 50000,
    "enabled_plugins": ["python_plugin", "js_plugin", "c_plugin"]
}
EOF
```

3. **Start Server**
```bash
# Start with production config
python -m mcp_server.server --config config/production.json --transport websocket --port 8080
```

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements-production.txt .
RUN pip install -r requirements-production.txt

COPY . .

EXPOSE 8080
CMD ["python", "-m", "mcp_server.server", "--transport", "websocket", "--port", "8080"]
```

### Monitoring Setup

1. **Prometheus Configuration**
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'mcp-server'
    static_configs:
      - targets: ['mcp-server:8001']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

2. **Health Check Endpoint**
```bash
# Health check
curl http://localhost:8080/health

# Metrics
curl http://localhost:8001/metrics
```

### Performance Tuning

1. **Memory Optimization**
```python
# config/production.json
{
    "cache_max_memory_mb": 1000,
    "memory_monitor_interval": 30,
    "gc_frequency": 60
}
```

2. **Connection Pooling**
```python
# Database connections
{
    "database": {
        "pool_size": 20,
        "max_overflow": 40,
        "pool_timeout": 30
    }
}
```

3. **Rate Limiting**
```python
# Rate limiting
{
    "rate_limit_requests": 1000,
    "rate_limit_window": 3600,
    "rate_limit_algorithm": "token_bucket"
}
```

## Best Practices

### Development
- Use structured logging with correlation IDs
- Implement comprehensive health checks
- Monitor memory usage and performance metrics
- Use appropriate caching strategies
- Test with realistic data volumes

### Production
- Enable all monitoring and alerting
- Use Redis for distributed caching
- Configure appropriate rate limits
- Set up log aggregation
- Monitor resource usage
- Implement graceful shutdown

### Security
- Use strong JWT secrets
- Enable rate limiting
- Validate all inputs
- Log security events
- Monitor for anomalies
- Keep dependencies updated

## Troubleshooting

### Common Issues

1. **Memory Issues**
```bash
# Check memory usage
curl http://localhost:8080/health | jq '.system_info.memory_percent'

# Force garbage collection
curl -X POST http://localhost:8080/admin/gc
```

2. **Performance Issues**
```bash
# Check metrics
curl http://localhost:8001/metrics | grep request_duration

# Check active requests
curl http://localhost:8080/admin/requests
```

3. **Rate Limiting**
```bash
# Check rate limit status
curl http://localhost:8080/admin/rate-limits
```

### Debugging

1. **Enable Debug Logging**
```bash
export LOG_LEVEL=DEBUG
export DEBUG=true
```

2. **Check Component Health**
```bash
curl http://localhost:8080/health | jq '.checks[]'
```

3. **Monitor Real-time Metrics**
```bash
# Watch metrics
watch -n 1 'curl -s http://localhost:8001/metrics | grep -E "(requests_total|memory_usage)"'
```

## Conclusion

Phase 4 provides a comprehensive, production-ready MCP server with advanced features for:

- Template-based prompt generation
- High-performance operation with caching and optimization
- Advanced protocol features like streaming and batch processing
- Production monitoring, logging, and health checks
- Scalable architecture with proper resource management

The server is now ready for production deployment with comprehensive monitoring, logging, and performance optimization capabilities.