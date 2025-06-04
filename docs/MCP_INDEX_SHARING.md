# MCP Index Sharing Guide

This guide explains how the MCP server automatically handles index sharing across developers and environments.

## Overview

The MCP server now features **automatic index management** that:
- **Automatically downloads** pre-built indexes from git remotes
- **Builds locally** when no remote index exists
- **Shares indexes** via git branches with zero configuration
- **Updates incrementally** using git hooks

## How Automatic Indexing Works

When an AI assistant requests to index a codebase, the MCP server automatically:

1. **Checks for existing local index** → Uses it immediately
2. **Checks for remote pre-built index** → Downloads in seconds
3. **Falls back to local building** → One-time indexing
4. **Sets up git hooks** → For automatic future updates

This happens transparently - no manual intervention required!

## For End Users

### Zero Configuration Usage

Just ask your AI assistant to index any codebase:

```
AI: "Please analyze this codebase"
↓
MCP automatically:
- Checks for pre-built index from team
- Downloads it if available (seconds!)
- Builds locally if needed (one time)
- Sets up automatic updates
↓
AI: "Analysis complete!"
```

No setup commands needed - it just works!

### Manual Control (Optional)

```bash
# Force rebuild an index
./scripts/mcp-index --force-rebuild

# Use custom index location
./scripts/mcp-index --index-dir /custom/path

# Check index status
python -m mcp_server index verify
```

## For Repository Maintainers

### Option 1: Local-First Workflow (Recommended)

Uses your local machine to build indexes, shares via git:

```bash
# One-time setup in your repository
./scripts/setup-git-hooks.sh

# How it works:
# - On commit: Indexes changed files locally
# - On push to main: Updates and pushes index to 'mcp-index' branch
# - Zero GitHub compute usage!
```

**Git Hooks Installed:**
- **post-commit**: Indexes changed files in background
- **pre-push**: Updates complete index and pushes to remote

### Option 2: GitHub Actions Workflow

For teams preferring cloud builds:

```yaml
# .github/workflows/mcp-index-release.yml
name: Build and Release MCP Index
on:
  push:
    tags:
      - 'v*'
  release:
    types: [created]

jobs:
  build-index:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - name: Build MCP Index
      run: |
        python -m mcp_server index build \
          --output ./mcp-index-export \
          --include-embeddings \
          --compress
    - name: Upload to Release
      uses: actions/upload-release-asset@v1
      with:
        asset_path: ./mcp-index-export.tar.gz
```

### Option 3: Hybrid Approach

Handles both local commits and web UI edits:

```yaml
# .github/workflows/mcp-index-on-merge.yml
name: Update Index on Merge
on:
  push:
    branches: [main]
    
jobs:
  update-index:
    runs-on: ubuntu-latest
    steps:
    # Only runs for web edits/PR merges
    # Local commits already have index via git hooks
```

## Storage Architecture

### Index Contents

```
~/.mcp/indexes/<project-name>/
├── code_index.db          # SQLite database (symbols, references)
├── cache/                 # Vector embeddings (if enabled)
│   ├── embeddings.qdrant  # Semantic search vectors
│   └── ast_cache/         # Parsed AST cache
├── index_metadata.json    # Index version and settings
└── .last_indexed_commit   # Git commit tracking
```

### Where Indexes Live

1. **Local Development**: `~/.mcp/indexes/<project-name>/`
2. **Git Remote**: `mcp-index` branch (separate from code)
3. **Docker Volumes**: `/var/lib/docker/volumes/mcp-index/`
4. **GitHub Releases**: As compressed artifacts (optional)

## Index Sharing Methods

### 1. Automatic via Git (Default)

```bash
# Team member 1 pushes code
git push origin main
# → Index automatically pushed to mcp-index branch

# Team member 2 uses MCP
# → Index automatically downloaded from mcp-index branch
```

### 2. Manual Sharing

```bash
# Export index
python -m mcp_server index build --output ./export --compress

# Share via any method (S3, shared drive, etc.)
scp export.tar.gz teammate@server:/shared/

# Import index
python -m mcp_server index import /shared/export.tar.gz
```

### 3. Container-Based Sharing

```yaml
# docker-compose.yml
services:
  mcp-server:
    volumes:
      - shared-index:/root/.mcp/indexes
volumes:
  shared-index:
    driver: local
```

## CLI Commands

### Index Management

```bash
# Build index with options
python -m mcp_server index build \
  --path /path/to/project \
  --output ./export \
  --include-embeddings \
  --compress \
  --incremental

# Import pre-built index
python -m mcp_server index import ./index.tar.gz

# Update index with changed files
python -m mcp_server index update \
  --files changed_files.txt \
  --commit abc123

# Verify index integrity
python -m mcp_server index verify --path ~/.mcp/indexes/myproject
```

### Smart Wrapper Script

```bash
# Automatic setup with all features
./scripts/mcp-index /path/to/project

# Options:
#   --force-rebuild     Force rebuild even if exists
#   --index-dir PATH    Custom index location  
#   --no-hooks          Don't setup git hooks
```

## Configuration

### Environment Variables

```bash
# Custom index location
export MCP_INDEX_PATH="/custom/indexes/myproject"

# Disable automatic indexing
export ENABLE_MCP_AUTO_INDEX=false

# Disable index sharing
export ENABLE_MCP_INDEX_PUSH=false

# Custom branch name for indexes
export MCP_INDEX_BRANCH=index-storage
```

### Git Hooks Configuration

Edit `~/.mcp/config`:
```bash
# Enable/disable features
ENABLE_MCP_AUTO_INDEX=true      # Auto-index on commit
ENABLE_MCP_INDEX_PUSH=true      # Push to remote
MCP_INDEX_DIR=/custom/path      # Custom location
```

## Performance & Costs

### Index Sizes

| Project Size | Index Size | Build Time | Download Time |
|-------------|------------|------------|---------------|
| Small (1K files) | ~100MB | ~30s | ~5s |
| Medium (10K files) | ~1GB | ~5min | ~30s |
| Large (100K files) | ~10GB | ~30min | ~2min |

### Storage Costs

- **GitHub**: FREE (release artifacts for public repos)
- **Git LFS**: ~$5/month for 50GB
- **S3**: ~$0.10/GB/month
- **Local**: Free (your disk space)

### Optimization Tips

1. **Compress indexes**: Reduces size by 60-80%
2. **Exclude embeddings**: If not using semantic search
3. **Incremental updates**: Only reindex changed files
4. **Prune old indexes**: Auto-cleanup after 30 days

## Security Considerations

### What's Indexed

- Source code structure and symbols
- Function/class signatures
- Import relationships
- Optional: Vector embeddings

### What's NOT Indexed

- Actual source code content
- Secrets or credentials
- Binary files
- Git history

### Best Practices

1. **Review index contents** before sharing
2. **Use gitignore** patterns for sensitive files
3. **Separate branches** for index storage
4. **Access control** via repository permissions

## Troubleshooting

### Index Not Downloading

```bash
# Check if mcp-index branch exists
git ls-remote origin mcp-index

# Manually fetch and extract
git fetch origin mcp-index
git checkout origin/mcp-index -- mcp-index-latest.tar.gz
tar -xzf mcp-index-latest.tar.gz -C ~/.mcp/indexes/project
```

### Index Build Failing

```bash
# Check available disk space
df -h ~/.mcp/indexes

# Clear corrupted index
rm -rf ~/.mcp/indexes/project
./scripts/mcp-index --force-rebuild

# Verbose logging
MCP_LOG_LEVEL=DEBUG python -m mcp_server index build
```

### Git Hooks Not Working

```bash
# Verify hooks installed
ls -la .git/hooks/

# Re-run setup
./scripts/setup-git-hooks.sh

# Check hook configuration
cat ~/.mcp/config
```

## Integration Examples

### VS Code Extension

```json
// .vscode/settings.json
{
  "mcp.indexPath": "${workspaceFolder}/.mcp/indexes",
  "mcp.autoIndex": true,
  "mcp.downloadRemoteIndex": true
}
```

### CI/CD Pipeline

```yaml
# Download index before tests
- name: Setup MCP Index
  run: |
    if git fetch origin mcp-index 2>/dev/null; then
      git checkout origin/mcp-index -- mcp-index-latest.tar.gz
      tar -xzf mcp-index-latest.tar.gz -C ~/.mcp/indexes/
    fi
```

### Docker Development

```dockerfile
# Dockerfile
FROM python:3.11

# Install MCP with index
RUN git clone https://github.com/org/repo /app && \
    cd /app && \
    ./scripts/mcp-index --no-hooks

WORKDIR /app
```

## Summary

The MCP index sharing system provides:

✅ **Automatic index management** - No manual setup needed
✅ **Team collaboration** - Shared indexes via git
✅ **Local-first approach** - Your compute, not cloud
✅ **Incremental updates** - Only reindex changes
✅ **Zero configuration** - Works out of the box
✅ **Free hosting** - Via GitHub branches/releases

Just use MCP normally - indexing happens automatically!