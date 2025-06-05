# MCP Configuration Guide

This project provides multiple MCP configuration options for Claude Code integration.

> **Claude Code Compatibility**: Claude Code only supports Tools and Prompts (not Resources). All configurations automatically set `MCP_DISABLE_RESOURCES=true` for compatibility.

## ✅ **Current Active Config: Smart Fallback**

**File**: `.mcp.json` (uses `./mcp-with-fallback`)

**Behavior**:
1. **Tries Docker first** - Uses local `code-index-mcp:latest` image if available
2. **Falls back to local Python** - If Docker unavailable or image missing
3. **Provides helpful error messages** - Guides you to install missing dependencies

**Benefits**:
- ✅ Works in any environment
- ✅ No manual switching needed
- ✅ Automatic dependency detection
- ✅ Uses fastest available option

## 🔧 **Available Configuration Files**

### 🐳 **Docker-Only Config**
```bash
cp .mcp-docker.json .mcp.json
```
- Uses official Docker image: `ghcr.io/code-index-mcp/mcp-server:latest`
- Requires Docker to be installed and running
- Most consistent environment

### 🐍 **Local Python-Only Config**  
```bash
cp mcp-config.json .mcp.json
```
- Uses local Python installation: `python -m mcp_server.stdio_server`
- Requires local dependencies installed
- Fastest startup time

### 🧠 **Smart Fallback Config** (Current)
```bash
cp .mcp-smart.json .mcp.json
```
- Tries Docker first, falls back to local Python
- Uses `./mcp-with-fallback` script
- Best for mixed environments

## 🛠️ **Setup Requirements**

### For Docker Path
```bash
# Build local image (optional)
docker build -t code-index-mcp:latest .
```

### For Local Python Path
```bash
# Install dependencies
pip install -r requirements.txt
pip install -e .
```

### For Smart Fallback (Recommended)
```bash
# Either Docker OR local Python setup works
# Script automatically detects and uses best option
```

## 🧪 **Testing Your Configuration**

```bash
# Test current config
timeout 5 ./mcp-with-fallback --help

# Test Docker specifically
docker run -i --rm code-index-mcp:latest python -m mcp_server --help

# Test local Python specifically  
python -m mcp_server --help
```

## 📋 **Configuration Examples**

### Example Output: Docker Available
```
Using Docker version...
Usage: python -m mcp_server [OPTIONS] COMMAND [ARGS]...
```

### Example Output: Docker Unavailable
```
Docker not found, falling back to local Python...
Using local Python version...
Usage: python -m mcp_server [OPTIONS] COMMAND [ARGS]...
```

### Example Output: Neither Available
```
Error: Neither Docker nor local MCP server installation found!

Please either:
  1. Install Docker: https://docs.docker.com/get-docker/
  2. Install locally: pip install -r requirements.txt && pip install -e .
```

## 🔄 **After Configuration Changes**

1. **Restart Claude Code** to pick up new `.mcp.json`
2. **Look for "code-index" server** in Claude's MCP servers list
3. **Test with code search** or symbol lookup commands

---

*Current active configuration uses smart fallback for maximum compatibility.*