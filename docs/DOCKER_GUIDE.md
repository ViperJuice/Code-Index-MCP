# Docker Guide for MCP Index Server

This guide provides comprehensive documentation for running MCP Index Server using Docker, including installation, configuration, and troubleshooting.

## Table of Contents

1. [Overview](#overview)
2. [Docker Variants](#docker-variants)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Usage](#usage)
6. [API Key Management](#api-key-management)
7. [GitHub Artifact Sync](#github-artifact-sync)
8. [MCP Integration](#mcp-integration)
9. [Troubleshooting](#troubleshooting)
10. [Advanced Topics](#advanced-topics)

## Overview

The MCP Index Server Docker images provide a containerized solution for code indexing without requiring local Python installation. All dependencies, including tree-sitter grammars for 48+ languages, are pre-installed and optimized.

### Why Docker?

- **Zero Setup**: No Python, no dependencies, just Docker
- **Consistency**: Same environment for all users
- **Isolation**: No conflicts with system packages
- **Portability**: Works identically on Linux, macOS, and Windows

## Docker Variants

### 1. `mcp-index:minimal` (Default)

**Best for**: Getting started, basic code search, privacy-conscious users

**Features**:
- ✅ Full 48-language indexing
- ✅ BM25 full-text search
- ✅ Symbol navigation
- ✅ Real-time file watching
- ❌ Semantic search (no API key required)
- ❌ GitHub sync (disabled by default)

**Resource Usage**:
- Memory: 512MB-1GB
- CPU: 1 core
- Storage: ~100MB + index size

### 2. `mcp-index:standard`

**Best for**: Teams wanting AI-powered search

**Features**:
- All minimal features PLUS:
- ✅ Semantic search with Voyage AI
- ✅ Contextual embeddings
- ✅ Advanced reranking
- ✅ GitHub artifact sync
- ⚠️ Requires VOYAGE_AI_API_KEY

**Resource Usage**:
- Memory: 2-4GB
- CPU: 2 cores
- Storage: ~500MB + index size

### 3. `mcp-index:full`

**Best for**: Production deployments

**Features**:
- All standard features PLUS:
- ✅ Redis caching
- ✅ Qdrant vector database
- ✅ Prometheus metrics
- ✅ Grafana dashboards
- ✅ Health monitoring

**Resource Usage**:
- Memory: 4-8GB
- CPU: 4 cores
- Storage: 1GB+ depending on codebase

## Installation

### Quick Install (Linux/macOS)

```bash
curl -sSL https://raw.githubusercontent.com/Code-Index-MCP/main/scripts/install-mcp-docker.sh | bash
```

### Quick Install (Windows PowerShell)

```powershell
iwr -useb https://raw.githubusercontent.com/Code-Index-MCP/main/scripts/install-mcp-docker.ps1 | iex
```

### Manual Installation

1. **Install Docker**:
   - Linux: `curl -fsSL https://get.docker.com | sh`
   - macOS: Download [Docker Desktop](https://www.docker.com/products/docker-desktop/)
   - Windows: Download [Docker Desktop](https://www.docker.com/products/docker-desktop/)

2. **Pull the image**:
   ```bash
   docker pull ghcr.io/code-index-mcp/mcp-index:minimal
   ```

3. **Create launcher script**:
   ```bash
   # Linux/macOS
   echo 'docker run -i --rm -v $(pwd):/workspace ghcr.io/code-index-mcp/mcp-index:minimal "$@"' > /usr/local/bin/mcp-index
   chmod +x /usr/local/bin/mcp-index
   ```

## Configuration

### Environment Variables

Configure the Docker container using environment variables:

```bash
# Basic configuration
docker run -it \
  -e LOG_LEVEL=DEBUG \
  -e MCP_WORKSPACE_ROOT=/workspace \
  ghcr.io/code-index-mcp/mcp-index:minimal
```

### Configuration File (.env)

Create a `.env` file in your project root:

```env
# Semantic Search (Standard/Full only)
VOYAGE_AI_API_KEY=your-api-key-here
SEMANTIC_SEARCH_ENABLED=true

# GitHub Artifact Sync
MCP_ARTIFACT_SYNC=true
AUTO_UPLOAD=true
AUTO_DOWNLOAD=true

# Performance
INDEXING_MAX_WORKERS=8
INDEXING_BATCH_SIZE=50

# Logging
LOG_LEVEL=INFO
```

The Docker container automatically loads `.env` from the workspace.

### MCP Index Configuration (.mcp-index.json)

Control index behavior and sharing:

```json
{
  "version": "1.0",
  "enabled": true,
  "github_artifacts": {
    "enabled": true,
    "auto_upload": false,
    "auto_download": true,
    "compression": true,
    "max_size_mb": 100,
    "exclude_patterns": [
      "internal/*",
      "*.secret"
    ]
  },
  "languages": "auto",
  "exclude_defaults": true
}
```

## Usage

### Basic Commands

```bash
# Index current directory
mcp-index

# Index specific directory
mcp-index /path/to/code

# Show version
mcp-index --version

# Run setup wizard
mcp-index setup

# Upgrade to latest version
mcp-index upgrade
```

### Docker Run Examples

```bash
# Minimal version - basic search
docker run -it -v $(pwd):/workspace ghcr.io/code-index-mcp/mcp-index:minimal

# Standard version - with API key
docker run -it \
  -v $(pwd):/workspace \
  -e VOYAGE_AI_API_KEY=your-key \
  ghcr.io/code-index-mcp/mcp-index:standard

# Full version - with external services
docker run -it \
  -v $(pwd):/workspace \
  -e VOYAGE_AI_API_KEY=your-key \
  -e REDIS_URL=redis://redis:6379 \
  -e QDRANT_URL=http://qdrant:6333 \
  ghcr.io/code-index-mcp/mcp-index:full
```

### Docker Compose

For production deployments, use Docker Compose:

```yaml
version: '3.8'

services:
  mcp-index:
    image: ghcr.io/code-index-mcp/mcp-index:standard
    volumes:
      - ./:/workspace
      - ~/.mcp-index:/app/.mcp-index
    environment:
      - VOYAGE_AI_API_KEY=${VOYAGE_AI_API_KEY}
      - MCP_ARTIFACT_SYNC=true
    stdin_open: true
    tty: true
```

## API Key Management

### Voyage AI Setup

1. **Get an API Key**:
   - Visit https://www.voyageai.com/
   - Sign up for free account
   - Generate API key in dashboard

2. **Pricing**:
   - Free tier: 50M tokens/month (~50K embeddings)
   - Paid: $0.05 per 1M tokens
   - 1 token ≈ 1 character of code

3. **Configure the Key**:
   ```bash
   # Option 1: Environment variable
   export VOYAGE_AI_API_KEY=your-key
   
   # Option 2: Docker run
   docker run -e VOYAGE_AI_API_KEY=your-key ...
   
   # Option 3: .env file
   echo "VOYAGE_AI_API_KEY=your-key" >> .env
   ```

### Cost Estimation

| Codebase Size | Files | Embeddings | Monthly Cost |
|---------------|-------|------------|--------------|
| Small (1MB) | ~100 | ~1,000 | Free tier |
| Medium (10MB) | ~1,000 | ~10,000 | Free tier |
| Large (100MB) | ~10,000 | ~100,000 | ~$5/month |
| Huge (1GB) | ~100,000 | ~1,000,000 | ~$50/month |

## GitHub Artifact Sync

### Privacy Settings

Control index sharing per repository:

```json
// .mcp-index.json
{
  "github_artifacts": {
    "enabled": false,     // Completely disable sync
    "auto_upload": false, // Manual upload only
    "auto_download": true // Still receive team indexes
  }
}
```

### Manual Sync Commands

```bash
# Check sync status
docker run -it -v $(pwd):/workspace ghcr.io/code-index-mcp/mcp-index:standard artifact status

# Download latest index
docker run -it -v $(pwd):/workspace ghcr.io/code-index-mcp/mcp-index:standard artifact pull

# Upload your index
docker run -it -v $(pwd):/workspace ghcr.io/code-index-mcp/mcp-index:standard artifact push
```

### Security Features

- Automatic .gitignore filtering
- Additional patterns via .mcp-index-ignore
- Audit logs of excluded files
- No secrets in shared indexes

## MCP Integration

### Claude Code Configuration

Create `.mcp.json` in your project root:

```json
{
  "mcpServers": {
    "code-index": {
      "command": "docker",
      "args": [
        "run", 
        "-i", 
        "--rm",
        "-v", "${workspace}:/workspace",
        "-v", "${HOME}/.mcp-index:/app/.mcp-index",
        "-e", "VOYAGE_AI_API_KEY=${VOYAGE_AI_API_KEY:-}",
        "-e", "MCP_ARTIFACT_SYNC=${MCP_ARTIFACT_SYNC:-true}",
        "ghcr.io/code-index-mcp/mcp-index:standard"
      ]
    }
  }
}
```

### Environment Variables in MCP

Claude Code passes environment variables to the Docker container:

```json
{
  "mcpServers": {
    "code-index": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "..."],
      "env": {
        "VOYAGE_AI_API_KEY": "your-key",
        "LOG_LEVEL": "DEBUG"
      }
    }
  }
}
```

## Nested Container Scenarios

### Overview

Nested container scenarios occur when you're already running inside a container (like a VS Code dev container) and need to run MCP Docker images. This is common in modern development workflows.

### Common Scenarios

1. **VS Code Dev Containers** in WSL2 with Docker Desktop
2. **GitHub Codespaces** or similar cloud environments
3. **CI/CD pipelines** running in containers
4. **Docker-in-Docker** development environments

### Solutions

#### Option 1: Native Python (Recommended for Dev Containers)

If you're already in a development container with Python:

```json
// .mcp.json
{
  "mcpServers": {
    "code-index-native": {
      "command": "python",
      "args": ["scripts/cli/mcp_server_cli.py"],
      "cwd": "${workspace}"
    }
  }
}
```

**Advantages:**
- No nested Docker complexity
- Direct file access
- Faster startup
- No permission issues

#### Option 2: Docker Sidecar Pattern

Run MCP as a separate service alongside your dev container:

1. **Start the sidecar container:**
   ```bash
   docker-compose -f docker/compose/development/docker-compose.mcp-sidecar.yml up -d
   ```

2. **Configure MCP to use the sidecar:**
   ```json
   // .mcp.json
   {
     "mcpServers": {
       "code-index-sidecar": {
         "command": "docker",
         "args": ["exec", "-i", "mcp-sidecar", "python", "/app/scripts/cli/mcp_server_cli.py"]
       }
     }
   }
   ```

**Advantages:**
- Isolated dependencies
- Consistent environment
- No conflicts with dev container packages

#### Option 3: Docker Socket Mounting

Share the Docker socket with your dev container:

```yaml
# .devcontainer/docker-compose.yml
version: '3.8'
services:
  devcontainer:
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - .:/workspace
```

Then use standard Docker commands inside the container.

**⚠️ Security Warning:** Mounting Docker socket grants root-equivalent access.

#### Option 4: Remote Docker Context

Connect to Docker running on the host:

```bash
# Inside dev container
export DOCKER_HOST=tcp://host.docker.internal:2375
docker run -it -v /mnt/c/path/to/code:/workspace mcp-index:minimal
```

**Note:** Requires Docker Desktop with exposed daemon.

### WSL2 Specific Configuration

For WSL2 with Docker Desktop:

1. **Ensure WSL integration is enabled** in Docker Desktop settings
2. **Use WSL paths** for volume mounts:
   ```bash
   # Convert Windows path to WSL path
   docker run -it -v /mnt/c/Users/name/project:/workspace mcp-index:minimal
   ```

3. **Configure .mcp.json for WSL:**
   ```json
   {
     "mcpServers": {
       "code-index-wsl": {
         "command": "docker",
         "args": [
           "run", "-i", "--rm",
           "-v", "${workspace}:/workspace",
           "-v", "/mnt/c/Users/${USER}/.mcp-index:/app/.mcp-index",
           "mcp-index:minimal"
         ]
       }
     }
   }
   ```

### Automatic Configuration

Use the setup script to auto-detect and configure:

```bash
# Detects nested container environment
./scripts/setup-mcp-json.sh

# Output:
# Detected environment: devcontainer
# Using native Python configuration for optimal performance
# Created .mcp.json for devcontainer environment
```

### Best Practices

1. **Check environment first:**
   ```bash
   # Are we in a container?
   if [ -f /.dockerenv ]; then
     echo "Running in container"
   fi
   ```

2. **Use appropriate configuration:**
   - Dev containers → Native Python
   - Production → Docker sidecar
   - CI/CD → Docker-in-Docker

3. **Avoid recursive containers:**
   - Don't run Docker inside Docker inside Docker
   - Use sidecar pattern instead

4. **Handle permissions carefully:**
   - Match UID/GID between containers
   - Use named volumes for persistent data

### Performance Considerations

| Method | Startup Time | Resource Usage | Complexity |
|--------|-------------|----------------|------------|
| Native Python | Fast (1-2s) | Low | Low |
| Docker Sidecar | Medium (5-10s) | Medium | Medium |
| Docker-in-Docker | Slow (10-20s) | High | High |
| Remote Docker | Fast (2-5s) | Low | Medium |

### Debugging Nested Containers

```bash
# Check Docker availability
docker version

# Test MCP connection
echo '{"jsonrpc":"2.0","method":"initialize","id":1}' | \
  docker run -i --rm mcp-index:minimal

# Verify volume mounts
docker run --rm -v $(pwd):/workspace alpine ls -la /workspace

# Check container logs
docker logs mcp-sidecar
```

## Troubleshooting

### Common Issues

#### 1. Docker not found
```bash
Error: Docker command not found
Solution: Install Docker Desktop or Docker Engine
```

#### 2. Permission denied
```bash
Error: docker: permission denied
Solution: Add user to docker group: sudo usermod -aG docker $USER
```

#### 3. API key not working
```bash
Warning: Semantic search requires VOYAGE_AI_API_KEY
Solution: Verify key is set: echo $VOYAGE_AI_API_KEY
```

#### 4. Out of memory
```bash
Error: Container killed (OOM)
Solution: Increase Docker memory limit in Docker Desktop settings
```

### Debug Mode

Enable detailed logging:

```bash
docker run -it \
  -e LOG_LEVEL=DEBUG \
  -e MCP_LOG_FILE=/workspace/mcp-debug.log \
  -v $(pwd):/workspace \
  ghcr.io/code-index-mcp/mcp-index:minimal
```

### Health Checks

Check container health:

```bash
# Check if MCP server is responsive
docker run --rm ghcr.io/code-index-mcp/mcp-index:minimal --health

# Test database connection
docker run --rm -v $(pwd):/workspace ghcr.io/code-index-mcp/mcp-index:minimal test db

# Verify index status
docker run --rm -v $(pwd):/workspace ghcr.io/code-index-mcp/mcp-index:minimal index status
```

## Advanced Topics

### Custom Dockerfile

Extend the base images for your needs:

```dockerfile
FROM ghcr.io/code-index-mcp/mcp-index:standard

# Add custom dependencies
RUN pip install --no-cache-dir custom-package

# Add custom configuration
COPY my-config.yaml /app/config/

# Custom entrypoint
COPY entrypoint.sh /app/
ENTRYPOINT ["/app/entrypoint.sh"]
```

### Multi-Architecture Builds

The images support multiple architectures:

```bash
# Build for multiple platforms
docker buildx build \
  --platform linux/amd64,linux/arm64,linux/arm/v7 \
  -t my-mcp-index:latest \
  -f docker/dockerfiles/Dockerfile.minimal \
  .
```

### Volume Mounts

Advanced volume configurations:

```bash
# Persistent index across runs
docker run -it \
  -v $(pwd):/workspace \
  -v mcp-index-data:/app/data \
  -v mcp-index-cache:/app/.cache \
  ghcr.io/code-index-mcp/mcp-index:standard

# Read-only workspace
docker run -it \
  -v $(pwd):/workspace:ro \
  ghcr.io/code-index-mcp/mcp-index:minimal
```

### Network Configuration

For production deployments:

```bash
# Create isolated network
docker network create mcp-network

# Run with Redis
docker run -d --name redis --network mcp-network redis:alpine

# Run MCP with Redis
docker run -it \
  --network mcp-network \
  -e REDIS_URL=redis://redis:6379 \
  ghcr.io/code-index-mcp/mcp-index:full
```

### Performance Tuning

Optimize for large codebases:

```bash
docker run -it \
  -e INDEXING_MAX_WORKERS=16 \
  -e INDEXING_BATCH_SIZE=100 \
  -e CACHE_MAX_MEMORY_MB=1000 \
  --cpus="4" \
  --memory="8g" \
  ghcr.io/code-index-mcp/mcp-index:standard
```

## Support

- **Documentation**: https://github.com/Code-Index-MCP/docs
- **Issues**: https://github.com/Code-Index-MCP/issues
- **Discord**: https://discord.gg/code-index-mcp
- **Email**: support@code-index-mcp.io