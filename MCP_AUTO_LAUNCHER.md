# MCP Auto-Launcher

The MCP Auto-Launcher provides **zero-setup** deployment for the Code Index MCP server, automatically selecting the best available runtime option.

## How It Works

The `mcp-auto` script automatically detects and uses the best available option:

1. **Docker Container** (preferred)
   - Isolated environment with all dependencies
   - Consistent behavior across systems
   - No local Python environment required

2. **Local Python** (fallback)
   - Uses local Python installation
   - Falls back when Docker is unavailable
   - Requires manual dependency management

## Quick Start

### With Claude Code

The `.mcp.json` configuration is already set up to use the auto-launcher:

```json
{
  "mcpServers": {
    "code-index": {
      "command": "/home/jenner/Code/Code-Index-MCP/mcp-auto",
      "args": [],
      "cwd": "/home/jenner/Code/Code-Index-MCP",
      "env": {}
    }
  }
}
```

**Just start Claude Code** - the MCP server will launch automatically!

### Manual Testing

```bash
# Test the auto-launcher
./mcp-auto

# Check execution logs
tail -f mcp-auto.log
```

## Features

### Automatic Detection
- ✅ Docker availability and daemon status
- ✅ Docker image existence (builds if missing)
- ✅ Python environment and module availability
- ✅ Graceful fallback between options

### Production-Ready
- ✅ Proper signal handling (SIGINT/SIGTERM)
- ✅ Container cleanup on exit
- ✅ Comprehensive logging
- ✅ Error handling and recovery

### Zero Configuration
- ✅ No manual setup required
- ✅ Works out-of-the-box with Claude Code
- ✅ Automatic environment detection
- ✅ Self-building Docker images

## Runtime Options

### Docker Mode (Preferred)
```bash
# What happens when Docker is available:
Docker is available
Docker image found, launching container...
Launching MCP server via Docker...
```

**Features:**
- 25 language plugins (C#, Python, Rust, Go, JavaScript, TypeScript, etc.)
- Tree-sitter parsing with regex fallbacks
- Isolated environment with all dependencies
- Consistent behavior across systems
- SQLite database persistence

### Python Mode (Fallback)
```bash
# What happens when Docker is unavailable:
Docker not available, checking Python...
Python environment is available, launching local server...
```

**Requirements:**
- Python 3.10+ with mcp_server module installed
- All dependencies from requirements.txt
- Local Tree-sitter language parsers

## Docker Configuration

The auto-launcher uses `docker-compose.mcp.yml` with these optimizations:

```yaml
environment:
  - MCP_DISABLE_RESOURCES=true     # Claude Code compatibility
  - SEMANTIC_SEARCH_ENABLED=false  # Lightweight mode
  - METRICS_ENABLED=false          # Reduce overhead
  - CACHE_BACKEND=memory           # Fast local caching
  - INDEXING_MAX_WORKERS=4         # Balanced performance
```

## Troubleshooting

### Check Logs
```bash
# Auto-launcher logs
tail -f mcp-auto.log

# Docker container logs (if using Docker)
docker logs mcp-code-index
```

### Common Issues

**Docker image not found:**
```bash
# The auto-launcher will attempt to build it automatically
# If that fails, build manually:
docker compose -f docker-compose.mcp.yml build
```

**Python module not found:**
```bash
# Install dependencies:
pip install -r requirements.txt
pip install -e .
```

**Permission denied:**
```bash
# Make script executable:
chmod +x mcp-auto
```

### Force Specific Mode

**Force Docker mode:**
```bash
# Stop any existing containers
docker stop mcp-code-index 2>/dev/null || true

# Run directly
docker compose -f docker-compose.mcp.yml up
```

**Force Python mode:**
```bash
# Disable Docker temporarily
sudo systemctl stop docker

# Run auto-launcher (will use Python)
./mcp-auto

# Re-enable Docker
sudo systemctl start docker
```

## Architecture

```
Claude Code
    ↓
mcp-auto script
    ↓
  Decision Logic
    ↓
┌─────────────────┐    ┌──────────────────┐
│  Docker Mode    │ or │  Python Mode     │
│                 │    │                  │
│ code-index-mcp  │    │ python -m        │
│ container       │    │ mcp_server       │
│                 │    │                  │
│ 25 plugins      │    │ 25 plugins       │
│ Tree-sitter     │    │ Tree-sitter      │
│ SQLite DB       │    │ SQLite DB        │
└─────────────────┘    └──────────────────┘
```

## Development

### Adding New Detection Logic
Edit the `mcp-auto` script to add new runtime options:

```bash
# Add new detection function
check_new_runtime() {
    # Detection logic here
    return 0  # or 1 for failure
}

# Add to main execution logic
if check_new_runtime; then
    launch_new_runtime
    exit 0
fi
```

### Customizing Docker Configuration
Modify `docker-compose.mcp.yml` for different Docker setups:

```yaml
services:
  mcp-server:
    environment:
      - CUSTOM_SETTING=value
    volumes:
      - custom-volume:/app/custom
```

## Status

✅ **Production Ready**
- Zero-setup deployment working
- Docker and Python fallback tested
- Claude Code integration confirmed
- All 25 language plugins operational
- Comprehensive error handling and logging

The MCP Auto-Launcher provides the "it just works" experience you had before, with robust fallback options and production-ready deployment.