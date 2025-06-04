# Quick Start Guide: Phase 4 Advanced MCP Server

This guide helps you quickly get started with the advanced Phase 4 MCP server features.

## 🎯 NEW: Automatic Indexing

The MCP server now features **automatic index management**:

When you ask the AI to index a codebase, it automatically:
1. **Checks for pre-built indexes** from your team
2. **Downloads them instantly** if available 
3. **Builds locally** if no remote index exists
4. **Sets up automatic updates** for future changes

No manual setup required!

## Prerequisites

- Python 3.8+
- Git
- Optional: Redis for advanced caching
- Optional: PostgreSQL for production database

## Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd Code-Index-MCP
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Install optional production dependencies**
```bash
pip install -r requirements-production.txt
```

4. **Optional: Setup automatic index sharing**
```bash
# For repository maintainers who want to enable team index sharing
./scripts/setup-git-hooks.sh
```

## Quick Start Examples

### 1. Basic Server with STDIO Transport

```bash
# Start with default settings
python -m mcp_server.server

# Or with debug mode
python -m mcp_server.server --debug
```

### 2. WebSocket Server

```bash
# Start WebSocket server on port 8080
python -m mcp_server.server --transport websocket --port 8080

# Custom host and port
python -m mcp_server.server --transport websocket --host 0.0.0.0 --port 9000
```

### 3. Using Configuration File

Create `config.json`:
```json
{
    "transport_type": "websocket",
    "websocket_port": 8080,
    "debug": false,
    "enabled_plugins": ["python_plugin", "js_plugin"],
    "cache_max_entries": 5000,
    "log_file": "logs/server.log"
}
```

Start server:
```bash
python -m mcp_server.server --config config.json
```

## Testing the Server

### 1. Health Check (WebSocket mode)

```bash
# Check server health
curl http://localhost:8080/health

# Check detailed status
curl http://localhost:8080/status
```

### 2. Basic MCP Requests

#### List Available Tools
```json
{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
    "params": {}
}
```

#### List Available Prompts
```json
{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "prompts/list",
    "params": {}
}
```

#### Generate Code Review Prompt
```json
{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "prompts/get",
    "params": {
        "name": "code_review",
        "arguments": {
            "file_path": "example.py",
            "language": "python",
            "code": "def hello():\n    print('Hello, World!')"
        }
    }
}
```

### 3. Indexing a Codebase

#### Index a Project (Automatic)
```json
{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
        "name": "index_file",
        "arguments": {
            "path": "/path/to/project"
        }
    }
}
```

The server automatically:
- Checks for pre-built index from git remote
- Downloads it if available (seconds!)
- Builds locally if needed (one-time)
- Returns immediately if already indexed

### 4. Advanced Features

#### Text Completion
```json
{
    "jsonrpc": "2.0",
    "id": 4,
    "method": "completion/generate",
    "params": {
        "prompt": "def fibonacci(n):",
        "model": "template",
        "sampling": {
            "temperature": 0.7,
            "max_tokens": 100
        }
    }
}
```

#### Start Streaming
```json
{
    "jsonrpc": "2.0",
    "id": 5,
    "method": "stream/start",
    "params": {
        "type": "completion",
        "params": {
            "prompt": "Generate a Python class for file handling",
            "model": "template"
        }
    }
}
```

#### Batch Operations
```json
{
    "jsonrpc": "2.0",
    "id": 6,
    "method": "batch",
    "params": {
        "id": "batch_001",
        "requests": [
            {"id": 1, "method": "tools/list", "params": {}},
            {"id": 2, "method": "resources/list", "params": {}},
            {"id": 3, "method": "prompts/list", "params": {}}
        ],
        "parallel": true
    }
}
```

## Using Built-in Features

### 1. Python Integration

```python
import asyncio
from mcp_server.server import MCPServer

async def main():
    # Create server
    server = MCPServer()
    
    # Configure
    server.settings.transport_type = "websocket"
    server.settings.websocket_port = 8080
    server.settings.debug = True
    
    # Start server
    await server.start()

if __name__ == "__main__":
    asyncio.run(main())
```

### 2. Custom Prompts

```python
from mcp_server.prompts import prompt_registry, PromptTemplate, PromptArgument

# Create custom prompt
custom_prompt = PromptTemplate(
    name="code_explanation",
    description="Explain code functionality",
    prompt="""Explain the following {language} code:

```{language}
{code}
```

Provide:
1. What it does
2. How it works
3. Potential improvements""",
    arguments=[
        PromptArgument("language", "Programming language"),
        PromptArgument("code", "Code to explain")
    ],
    category="education",
    tags=["explanation", "learning"]
)

# Register prompt
prompt_registry.register_prompt(custom_prompt)
```

### 3. Performance Monitoring

```python
from mcp_server.production import monitoring_system

# Record custom metrics
await monitoring_system.metrics.counter("custom_operations_total")
await monitoring_system.metrics.gauge("custom_value", 42)
await monitoring_system.metrics.histogram("custom_duration", 0.5)

# Get dashboard data
dashboard = await monitoring_system.get_dashboard_data()
print(f"Active alerts: {len(dashboard['alerts']['active_alerts'])}")
```

### 4. Health Checks

```python
from mcp_server.production import health_checker, HealthCheck

class CustomHealthCheck(HealthCheck):
    def __init__(self):
        super().__init__("custom_service", timeout=5.0, critical=True)
    
    async def check(self):
        # Your custom health check logic
        # Raise exception if unhealthy
        pass

# Register custom health check
health_checker.register_check(CustomHealthCheck())
```

## Environment Configuration

### Development
```bash
export MCP_ENVIRONMENT=development
export DEBUG=true
export LOG_LEVEL=DEBUG
export CACHE_MAX_ENTRIES=1000

# Index management (automatic)
export MCP_INDEX_PATH=~/.mcp/indexes/myproject
export ENABLE_MCP_AUTO_INDEX=true
```

### Production
```bash
export MCP_ENVIRONMENT=production
export DEBUG=false
export LOG_LEVEL=INFO
export LOG_FILE=/var/log/mcp-server/app.log
export CACHE_MAX_ENTRIES=50000
export REDIS_URL=redis://localhost:6379
export DATABASE_URL=postgresql://user:pass@localhost/mcp

# Index management
export MCP_INDEX_PATH=/var/mcp/indexes
export ENABLE_MCP_AUTO_INDEX=true
export MCP_INDEX_BRANCH=mcp-index
```

## Docker Quick Start

### 1. Build Image
```bash
docker build -t mcp-server .
```

### 2. Run Container
```bash
# Basic run
docker run -p 8080:8080 mcp-server

# With environment variables
docker run -p 8080:8080 -e DEBUG=true -e LOG_LEVEL=DEBUG mcp-server

# With volume for logs
docker run -p 8080:8080 -v ./logs:/app/logs mcp-server
```

### 3. Docker Compose
```yaml
version: '3.8'
services:
  mcp-server:
    build: .
    ports:
      - "8080:8080"
    environment:
      - DEBUG=false
      - LOG_LEVEL=INFO
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
    volumes:
      - ./logs:/app/logs

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
```

## Common Use Cases

### 1. Code Analysis Service

```python
# Start server with code analysis focus
python -m mcp_server.server \
    --transport websocket \
    --port 8080 \
    --config config/code-analysis.json
```

`config/code-analysis.json`:
```json
{
    "enabled_plugins": ["python_plugin", "js_plugin", "c_plugin", "cpp_plugin"],
    "prompts_enabled": true,
    "cache_max_entries": 10000,
    "advanced_features_enabled": true
}
```

### 2. Documentation Generation

```json
{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "prompts/get",
    "params": {
        "name": "generate_documentation",
        "arguments": {
            "file_path": "src/utils.py",
            "language": "python",
            "code": "def process_data(data): return data.strip().lower()",
            "doc_style": "google"
        }
    }
}
```

### 3. Batch Code Processing

```json
{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "batch",
    "params": {
        "id": "code_analysis_batch",
        "requests": [
            {
                "id": 1,
                "method": "prompts/get",
                "params": {
                    "name": "bug_analysis",
                    "arguments": {"file_path": "file1.py", "language": "python", "code": "..."}
                }
            },
            {
                "id": 2,
                "method": "prompts/get",
                "params": {
                    "name": "performance_analysis",
                    "arguments": {"file_path": "file2.py", "language": "python", "code": "..."}
                }
            }
        ],
        "parallel": true,
        "max_concurrent": 3
    }
}
```

## Monitoring and Debugging

### 1. Real-time Monitoring

```bash
# Watch server logs
tail -f logs/mcp_server.log

# Monitor metrics (if Prometheus enabled)
curl http://localhost:8001/metrics

# Check health status
watch -n 5 'curl -s http://localhost:8080/health | jq ".overall_status"'
```

### 2. Performance Analysis

```bash
# Check memory usage
curl http://localhost:8080/status | jq '.health.system_info.memory_percent'

# Check active requests
curl http://localhost:8080/status | jq '.middleware.default.requests'

# Check cache performance
curl http://localhost:8080/status | jq '.cache_stats'
```

### 3. Debug Mode

```bash
# Start with full debugging
python -m mcp_server.server --debug --transport websocket --port 8080

# Enable specific debug logging
export LOG_LEVEL=DEBUG
export DEBUG=true
python -m mcp_server.server
```

## Next Steps

1. **Explore Advanced Features**: See [PHASE4_ADVANCED_FEATURES.md](PHASE4_ADVANCED_FEATURES.md) for detailed documentation
2. **Custom Plugin Development**: Learn how to create custom plugins
3. **Production Deployment**: Set up monitoring, logging, and scaling
4. **Integration**: Integrate with your existing development tools and workflows

## Troubleshooting

### Common Issues

1. **Server won't start**
   - Check Python version (3.8+ required)
   - Verify all dependencies installed
   - Check port availability

2. **WebSocket connection fails**
   - Verify firewall settings
   - Check port binding
   - Ensure correct host configuration

3. **Memory issues**
   - Reduce cache settings
   - Enable memory monitoring
   - Check for memory leaks in custom code

4. **Performance problems**
   - Enable performance monitoring
   - Check cache hit rates
   - Monitor resource usage

### Getting Help

- Check logs in `logs/mcp_server.log`
- Use debug mode for detailed information
- Check health endpoint for system status
- Monitor metrics for performance insights

For more detailed information, see the full documentation in [PHASE4_ADVANCED_FEATURES.md](PHASE4_ADVANCED_FEATURES.md).