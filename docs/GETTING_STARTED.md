# Getting Started with Code-Index-MCP

This guide walks you through installing and using Code-Index-MCP to index and search your codebase.

## Prerequisites

- Python 3.12 or higher
- Git (for version control features)
- A code repository to index
- `gh` CLI authenticated with access to the repository artifacts (`gh auth login`)

## Installation

### Option 1: Install via pip (Recommended)

```bash
# Install core package
pip install index-it-mcp

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

### 1. Pull Your Project Baseline Index

Navigate to your project directory and restore the latest published index:

```bash
cd /path/to/your/project

# Check repo/artifact readiness first
mcp-index preflight

# Pull the latest shared artifact baseline
mcp-index artifact pull --latest

# Reconcile only your local changes after restore
mcp-index artifact sync

# Check the index status
mcp-index index status
```

If there is no published artifact yet, fall back to a local rebuild:

```bash
mcp-index index rebuild --force
```

### 2. Start the MCP Server

```bash
# Start the server
mcp-index serve

# Or pick a less crowded port
mcp-index serve --port 9123
```

The server exposes:
- REST API at `http://127.0.0.1:8000`
- MCP protocol for AI assistant integration

### Same-Machine Multi-Repo Setup

If you work across multiple local repositories on one machine, register each
checkout and inspect readiness before starting work:

```bash
mcp-index repository register /path/to/repo-a
mcp-index repository register /path/to/repo-b
mcp-index repository list -v
mcp-index artifact workspace-status
mcp-index artifact reconcile-workspace
```

Newly registered repos usually start with `artifact_health: missing` until you
restore local runtime files with `mcp-index artifact pull --latest` or build a
local index with `mcp-index repository sync`.

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
pip install index-it-mcp[semantic]
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

# Artifact sync (recommended)
mcp-index artifact pull --latest    # Download team index baseline
mcp-index artifact sync             # Reconcile local drift after restore
mcp-index artifact push             # Publish a refreshed index baseline

# Repository
mcp-index repository status     # Show repository info
```

## Troubleshooting

### Index not found

```bash
# Pull the team baseline first, then rebuild only if needed
mcp-index artifact pull --latest
mcp-index artifact sync

# Fallback if no artifact is available or drift is too large
mcp-index index rebuild --force
```

### Artifact pull fails

Check GitHub authentication and repository remote:

```bash
gh auth status
git remote get-url origin
```

### Preflight warns that you are behind remote

```bash
git pull --rebase
mcp-index artifact sync
```

### Preflight warns that local runtime files are missing

```bash
mcp-index artifact pull --latest
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
