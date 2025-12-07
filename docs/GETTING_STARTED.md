# Getting Started with Code-Index-MCP

This guide walks you through installing and using Code-Index-MCP to index and search your codebase.

## Prerequisites

- Python 3.8 or higher
- Git (for version control features)
- A code repository to index

## Installation

### Option 1: Install via pip (Recommended)

```bash
# Install core package
pip install code-index-mcp

# Verify installation
mcp-index --version
```

### Option 2: Install from Source

```bash
# Clone the repository
git clone https://github.com/ViperJuice/Code-Index-MCP.git
cd Code-Index-MCP

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in editable mode
pip install -e .
```

## Quick Start

### 1. Index Your Project

Navigate to your project directory and build the index:

```bash
cd /path/to/your/project

# Build the index
mcp-index index rebuild

# Check the index status
mcp-index index status
```

The indexer will:
- Scan all supported source files (48 languages)
- Extract symbols (functions, classes, variables)
- Build a searchable FTS5 index in SQLite

### 2. Start the MCP Server

```bash
# Start the server
uvicorn mcp_server.gateway:app --host 127.0.0.1 --port 8000
```

The server exposes:
- REST API at `http://127.0.0.1:8000`
- MCP protocol for AI assistant integration

### 3. Search Your Code

**Via REST API:**

```bash
# Search for code
curl -X POST http://127.0.0.1:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "parse"}'

# Get symbol definition
curl "http://127.0.0.1:8000/symbol?symbol_name=parse_file"
```

**Via MCP Protocol (Claude Code):**

Add to your `.mcp.json`:

```json
{
  "mcpServers": {
    "code-index": {
      "command": "python",
      "args": ["-m", "mcp_server.cli"],
      "cwd": "/path/to/your/project"
    }
  }
}
```

## Configuration

### Environment Variables

Create a `.env` file in your project root:

```env
# Server settings
MCP_SERVER_HOST=127.0.0.1
MCP_SERVER_PORT=8000
MCP_LOG_LEVEL=INFO

# Index settings
MCP_WORKSPACE_ROOT=.
MCP_MAX_FILE_SIZE=10485760
```

### Ignore Patterns

Create `.mcp-index-ignore` to exclude files from indexing:

```
# Ignore patterns (gitignore syntax)
node_modules/
*.min.js
dist/
build/
.venv/
```

## Optional: Semantic Search

For AI-powered semantic search, install with semantic support:

```bash
pip install code-index-mcp[semantic]
```

Then configure Voyage AI:

```env
# Add to .env
VOYAGE_AI_API_KEY=your_api_key_here
SEMANTIC_SEARCH_ENABLED=true
```

Get a free API key at [voyageai.com](https://www.voyageai.com/).

## CLI Commands Reference

```bash
# Index management
mcp-index index status          # Show index status
mcp-index index rebuild         # Rebuild the index
mcp-index index check-compatibility  # Check index compatibility

# Artifact sync (optional)
mcp-index artifact pull --latest    # Download team index
mcp-index artifact push             # Upload your index
mcp-index artifact sync             # Sync with team

# Repository
mcp-index repository status     # Show repository info
```

## Troubleshooting

### Index not found

```bash
# Rebuild the index
mcp-index index rebuild --force
```

### Server won't start

Check if the port is in use:
```bash
lsof -i :8000
```

### Slow indexing

For large repositories, try:
```bash
# Use SQL-only mode (faster, no semantic search)
mcp-index index rebuild --mode sql
```

## Next Steps

- Read the [full documentation](https://github.com/ViperJuice/Code-Index-MCP#readme)
- Configure [semantic search](https://github.com/ViperJuice/Code-Index-MCP#semantic-search-configuration)
- Set up [team sync](https://github.com/ViperJuice/Code-Index-MCP#github-actions-integration)

## Support

- **Issues**: [GitHub Issues](https://github.com/ViperJuice/Code-Index-MCP/issues)
- **Discussions**: [GitHub Discussions](https://github.com/ViperJuice/Code-Index-MCP/discussions)
