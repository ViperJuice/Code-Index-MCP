# Getting Started with Code Index MCP Server

Welcome to this comprehensive tutorial on setting up and using the Code Index MCP Server. This guide will walk you through everything from installation to advanced usage.

## Table of Contents

1. [Introduction](#introduction)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
4. [Quick Start](#quick-start)
5. [Basic Usage](#basic-usage)
6. [Advanced Features](#advanced-features)
7. [Troubleshooting](#troubleshooting)
8. [Next Steps](#next-steps)

## Introduction

The Code Index MCP Server is a powerful tool for indexing and searching source code repositories. It provides:

- **Fast code search** across multiple programming languages
- **Symbol resolution** for functions, classes, and variables
- **Semantic search** using AI-powered embeddings
- **Real-time file watching** for automatic updates
- **Plugin architecture** for extensibility

### Who This Tutorial Is For

This tutorial is designed for:
- Software developers looking to improve code navigation
- DevOps engineers managing large codebases
- Technical writers documenting APIs
- Anyone working with multi-language projects

## Prerequisites

Before starting, ensure you have:

1. **Python 3.8 or higher**
   ```bash
   python --version
   # Should output: Python 3.8.x or higher
   ```

2. **Git** (for cloning repositories)
   ```bash
   git --version
   ```

3. **Basic command line knowledge**

4. **At least 4GB of RAM** for optimal performance

### Optional Prerequisites

- Docker (for containerized deployment)
- Redis (for caching)
- PostgreSQL (for production storage)

## Installation

### Method 1: Using pip (Recommended)

```bash
# Create a virtual environment
python -m venv mcp-env
source mcp-env/bin/activate  # On Windows: mcp-env\Scripts\activate

# Install the package
pip install code-index-mcp

# Verify installation
mcp-server --version
```

### Method 2: From Source

```bash
# Clone the repository
git clone https://github.com/codeindex/mcp-server.git
cd mcp-server

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

### Method 3: Using Docker

```bash
# Pull the official image
docker pull codeindex/mcp-server:latest

# Run the container
docker run -d \
  --name mcp-server \
  -p 8000:8000 \
  -v $(pwd):/workspace \
  codeindex/mcp-server:latest
```

## Quick Start

Let's index your first repository in under 5 minutes!

### Step 1: Start the Server

```bash
# Start with default settings
mcp-server start

# Or with custom port
mcp-server start --port 8080
```

You should see:
```
INFO: MCP Server starting...
INFO: Loading plugins...
INFO: Server ready at http://localhost:8000
```

### Step 2: Index a Repository

Open a new terminal and index a sample repository:

```bash
# Index a local repository
mcp-cli index /path/to/your/project

# Or index a GitHub repository
mcp-cli index https://github.com/python/cpython --branch main
```

### Step 3: Search Your Code

```bash
# Search for a function
mcp-cli search "def calculate"

# Search in specific language
mcp-cli search "class User" --language python

# Search with regex
mcp-cli search "TODO|FIXME" --regex
```

## Basic Usage

### Understanding the Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   CLI/API   │────▶│  Dispatcher │────▶│   Plugins   │
└─────────────┘     └─────────────┘     └─────────────┘
                            │                    │
                            ▼                    ▼
                    ┌─────────────┐     ┌─────────────┐
                    │   Indexer   │     │   Storage   │
                    └─────────────┘     └─────────────┘
```

### Working with Different File Types

#### Python Files

The Python plugin provides advanced features:

```python
# Example: Finding all async functions
mcp-cli search "async def" --language python

# Finding class definitions
mcp-cli search "class.*\(.*\):" --language python --regex

# Finding imports
mcp-cli search "^import|^from.*import" --language python --regex
```

#### JavaScript/TypeScript

```bash
# Find React components
mcp-cli search "function.*Component|class.*Component" --language javascript --regex

# Find exports
mcp-cli search "export default|export {" --language javascript
```

#### Markdown Documentation

```bash
# Find all headers
mcp-cli search "^#{1,6} " --language markdown --regex

# Find code blocks
mcp-cli search "^```" --language markdown
```

### Configuration

Create a configuration file at `~/.mcp/config.yaml`:

```yaml
server:
  host: localhost
  port: 8000
  workers: 4

storage:
  type: sqlite
  path: ~/.mcp/index.db

plugins:
  python:
    enabled: true
    max_file_size: 1048576
  javascript:
    enabled: true
    include_node_modules: false
  markdown:
    enabled: true
    index_code_blocks: true

indexing:
  ignore_patterns:
    - "*.pyc"
    - "__pycache__"
    - "node_modules"
    - ".git"
  max_file_size: 5242880
  
logging:
  level: INFO
  file: ~/.mcp/server.log
```

### Using the Python API

```python
from mcp_server import CodeIndexClient

# Initialize client
client = CodeIndexClient("http://localhost:8000")

# Index a directory
index_id = client.index_directory("/path/to/project")

# Wait for indexing to complete
client.wait_for_index(index_id)

# Search for code
results = client.search("TODO", language="python")
for result in results:
    print(f"{result.file}:{result.line} - {result.content}")

# Get symbol information
symbols = client.get_symbols("calculate_total")
for symbol in symbols:
    print(f"{symbol.type}: {symbol.name} at {symbol.location}")
```

## Advanced Features

### Semantic Search

Enable AI-powered semantic search for natural language queries:

```bash
# Enable semantic indexing
mcp-cli index /path/to/project --semantic

# Search using natural language
mcp-cli search "function that validates email addresses" --semantic

# Find similar code
mcp-cli similar "def authenticate_user(username, password):" --threshold 0.8
```

### Custom Plugins

Create your own language plugin:

```python
# my_plugin.py
from mcp_server.plugin_base import LanguagePlugin
from typing import List, Dict

class MyLanguagePlugin(LanguagePlugin):
    def __init__(self):
        super().__init__()
        self.supported_extensions = ['.mylang']
        self.language_name = 'mylang'
    
    def extract_symbols(self, content: str, file_path: str) -> List[Dict]:
        symbols = []
        # Your parsing logic here
        for line_num, line in enumerate(content.splitlines(), 1):
            if line.startswith('func '):
                symbols.append({
                    'name': line.split()[1],
                    'type': 'function',
                    'line': line_num,
                    'file': file_path
                })
        return symbols
    
    def extract_structure(self, content: str) -> Dict:
        # Extract file structure
        return {
            'functions': self.extract_symbols(content, ''),
            'classes': [],
            'imports': []
        }
```

Register your plugin:

```yaml
# In config.yaml
plugins:
  custom:
    - path: /path/to/my_plugin.py
      class: MyLanguagePlugin
```

### Performance Tuning

#### For Large Repositories

```yaml
# Optimized configuration for large codebases
indexing:
  batch_size: 1000
  parallel_workers: 8
  memory_limit: 4096  # MB
  
cache:
  enabled: true
  type: redis
  redis_url: redis://localhost:6379
  ttl: 3600

storage:
  type: postgresql
  connection: postgresql://user:pass@localhost/mcp_index
  pool_size: 20
```

#### Monitoring Performance

```bash
# Enable performance metrics
mcp-server start --metrics

# View metrics dashboard
open http://localhost:8000/metrics

# Export metrics to Prometheus
mcp-server start --metrics-export prometheus
```

### Integration Examples

#### VS Code Extension

```javascript
// extension.js
const vscode = require('vscode');
const axios = require('axios');

function activate(context) {
    let disposable = vscode.commands.registerCommand('mcp.search', async () => {
        const query = await vscode.window.showInputBox({
            prompt: 'Enter search query'
        });
        
        if (query) {
            const results = await searchCode(query);
            showResults(results);
        }
    });
    
    context.subscriptions.push(disposable);
}

async function searchCode(query) {
    const response = await axios.post('http://localhost:8000/api/search', {
        query: query,
        workspace: vscode.workspace.rootPath
    });
    return response.data.results;
}
```

#### Git Pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Update index before commit
mcp-cli index . --update-only

# Check for TODOs in staged files
todos=$(mcp-cli search "TODO|FIXME" --staged-only)
if [ ! -z "$todos" ]; then
    echo "Warning: Found TODOs in staged files:"
    echo "$todos"
    read -p "Continue with commit? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi
```

## Troubleshooting

### Common Issues

#### Server Won't Start

```bash
# Check if port is in use
lsof -i :8000

# Check logs
tail -f ~/.mcp/server.log

# Run in debug mode
mcp-server start --debug
```

#### Indexing Fails

```bash
# Check file permissions
ls -la /path/to/project

# Verify plugin support
mcp-cli plugins list

# Test with single file
mcp-cli index /path/to/single/file.py --verbose
```

#### Search Returns No Results

1. Verify index status:
   ```bash
   mcp-cli status
   ```

2. Check indexed files:
   ```bash
   mcp-cli list-files
   ```

3. Rebuild index:
   ```bash
   mcp-cli reindex --force
   ```

### Performance Issues

#### Slow Indexing

- Increase worker threads
- Enable caching
- Exclude unnecessary files
- Use SSD storage

#### High Memory Usage

- Limit batch size
- Reduce parallel workers
- Enable memory profiling:
  ```bash
  mcp-server start --profile-memory
  ```

### Getting Help

- **Documentation**: https://docs.codeindex.dev
- **GitHub Issues**: https://github.com/codeindex/mcp-server/issues
- **Community Forum**: https://forum.codeindex.dev
- **Discord**: https://discord.gg/codeindex

## Next Steps

Congratulations! You've learned the basics of the Code Index MCP Server. Here's what to explore next:

### 1. Advanced Search Techniques

- Learn regex patterns for complex searches
- Master query syntax for precise results
- Explore semantic search capabilities

### 2. Automation

- Set up continuous indexing
- Create custom workflows
- Integrate with CI/CD pipelines

### 3. Scaling

- Deploy to production
- Configure clustering
- Optimize for your workload

### 4. Contributing

- Report bugs and request features
- Contribute plugins
- Improve documentation

### Resources

- [API Reference](https://docs.codeindex.dev/api)
- [Plugin Development Guide](https://docs.codeindex.dev/plugins)
- [Best Practices](https://docs.codeindex.dev/best-practices)
- [Video Tutorials](https://youtube.com/codeindex)

Thank you for following this tutorial! Happy coding! 🚀