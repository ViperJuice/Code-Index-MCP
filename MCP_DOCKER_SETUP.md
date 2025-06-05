# MCP Docker Setup Guide

## Overview

The Code Index MCP server now uses a Docker-first approach for dependency isolation and easy deployment. The system automatically falls back to local Python installation if Docker is not available.

## Configuration Scripts

### 1. `mcp-docker` (Primary - Recommended)
- **Docker Mode**: Uses containerized environment (preferred)
- **Fallback Mode**: Automatically switches to local Python if Docker unavailable
- **Auto-builds**: Docker image on first run if not present

### 2. `mcp-local` (Fallback Only)
- **Local Mode**: Uses local Python installation only
- **Faster**: No Docker overhead
- **Requirements**: Python 3.10+ with dependencies

## Claude Code Configuration

Update your `.claude/settings.json`:

```json
{
  "mcpServers": {
    "code-index": {
      "command": "/home/jenner/Code/Code-Index-MCP/mcp-docker",
      "args": [],
      "env": {
        "MCP_DISABLE_RESOURCES": "true"
      }
    }
  }
}
```

## Docker Requirements

The Dockerfile includes all necessary dependencies:

### System Dependencies
- build-essential, gcc, g++, make
- cmake, clang
- git, curl
- sqlite3, libsqlite3-dev
- python3-dev

### Tree-sitter Language Parsers (26 Languages)
- C#, Bash, Haskell, Scala, Lua
- YAML, TOML, JSON, Markdown, CSV
- ARM, MIPS, AVR Assembly support
- And all other supported languages

### Python Dependencies
- All tree-sitter language parsers
- FastAPI, uvicorn for API mode
- aiofiles, aiosqlite for async operations
- Rich logging and prometheus metrics
- Security and performance libraries

## Fallback Behavior

The `mcp-docker` script automatically detects:

1. **Docker Available**: Uses containerized environment
   ```bash
   Using Docker for MCP server...
   Building MCP Docker image... (if needed)
   ```

2. **Docker Unavailable**: Falls back to local Python
   ```bash
   Docker not available, falling back to local Python installation...
   ```

3. **Dependencies Missing**: Provides helpful error message
   ```bash
   Error: MCP server Python package not found.
   Please install dependencies with: pip install -r requirements.txt
   ```

## Testing the Setup

Test both modes:

```bash
# Test Docker mode (will build image if needed)
timeout 5 ./mcp-docker

# Test local mode directly
timeout 5 ./mcp-local

# Test fallback logic
./test-fallback.sh
```

## Benefits of Docker-first Approach

1. **Dependency Isolation**: No conflicts with system Python
2. **Consistent Environment**: Same environment across machines
3. **Easy Updates**: Just rebuild Docker image
4. **Production Ready**: Same container for dev and production
5. **Automatic Fallback**: Works even without Docker

## File Structure

```
Code-Index-MCP/
├── mcp-docker          # Primary script (Docker + fallback)
├── mcp-local           # Local Python only
├── mcp-simple          # Legacy simple wrapper
├── Dockerfile          # Development Docker image
├── Dockerfile.production # Production optimized image
├── docker-compose.yml  # Full production stack
├── docker-compose.mcp.yml # Simplified MCP-only setup
├── requirements.txt    # Development dependencies
└── requirements-production.txt # Production dependencies
```

This setup ensures maximum compatibility while providing the benefits of containerization where available.