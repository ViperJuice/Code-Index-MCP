# Local Index Storage Documentation

## Overview

As of January 2025, Code-Index-MCP uses local index storage at `.indexes/` (relative to the MCP server directory) instead of the previous centralized location at `~/.mcp/indexes/`. This change makes the MCP server self-contained and simplifies deployment.

## Storage Structure

```
/workspaces/Code-Index-MCP/
├── .indexes/                    # Local index storage (gitignored)
│   ├── f7b49f5d0ae0/           # Repository hash directory
│   │   ├── main_a1b2c3d.db     # Branch + commit specific index
│   │   ├── main_a1b2c3d.metadata.json
│   │   ├── dev_e4f5g6h.db
│   │   ├── current.db -> main_a1b2c3d.db  # Symlink to active index
│   │   └── vector_index.qdrant/
│   ├── a2c3d4e5f6g7/           # Another repository
│   │   └── ...
│   └── ...                     # More repositories (34 total, ~3.1GB)
```

## Key Features

1. **Self-Contained**: All indexes stored with the MCP server
2. **Repository Isolation**: Each repository gets a unique hash-based directory
3. **Version Management**: Multiple index versions per branch supported
4. **Automatic Discovery**: MCP server finds indexes based on git remote URL
5. **Configurable**: Can override with `MCP_INDEX_STORAGE_PATH` environment variable

## GitHub Artifacts Integration

Despite indexes being gitignored (to prevent committing 3.1GB of data), they can still be shared via GitHub artifacts:

### Uploading Indexes

```bash
# Method 1: Direct upload from .indexes/
python scripts/index-artifact-upload-v2.py

# Method 2: Prepare and upload (recommended)
python scripts/utilities/prepare_index_for_upload.py
cd .mcp-index-staging
python ../scripts/index-artifact-upload-v2.py
```

### Downloading Indexes

```bash
# Download latest compatible index
python scripts/index-artifact-download-v2.py

# List available artifacts
python scripts/index-artifact-download-v2.py --list
```

### How It Works

1. **Upload Script** (`index-artifact-upload-v2.py`):
   - Automatically finds indexes in `.indexes/{repo_hash}/`
   - Follows `current.db` symlink to get the active index
   - Compresses and uploads to GitHub artifacts
   - Supports secure export (filters sensitive files)

2. **Download Script** (`index-artifact-download-v2.py`):
   - Downloads artifacts to `.indexes/{repo_hash}/`
   - Creates proper directory structure
   - Sets up `current.db` symlink
   - Maintains version management

3. **GitHub Workflows**:
   - Automatically upload indexes on push to main
   - Download indexes on pull request
   - Validate index compatibility
   - Clean up old artifacts

## Migration from Centralized Storage

If you have existing indexes in `~/.mcp/indexes/`, they have already been migrated to `.indexes/`. The migration preserved:

- Repository isolation (hash-based directories)
- Version management (branch_commit.db naming)
- Current symlinks
- All metadata files

## Benefits

1. **Portability**: Entire MCP installation can be moved/copied
2. **No Home Directory Dependencies**: Works in containers, CI/CD
3. **Simplified Deployment**: Everything in one place
4. **Easy Backup**: Just backup the MCP directory
5. **GitHub Integration**: Seamless artifact sharing despite gitignore

## Configuration

### Default Behavior
- Indexes stored at `.indexes/` relative to MCP server
- Automatic repository detection via git remote

### Environment Variables
- `MCP_INDEX_STORAGE_PATH`: Override default storage location
- `GITHUB_TOKEN`: Required for artifact upload/download

### Example .mcp.json
```json
{
  "mcpServers": {
    "code-index-mcp": {
      "command": "/usr/local/bin/python",
      "args": ["/workspaces/Code-Index-MCP/scripts/cli/mcp_server_cli.py"],
      "cwd": "/workspaces/Code-Index-MCP",
      "env": {
        "PYTHONPATH": "/workspaces/Code-Index-MCP"
        // MCP_INDEX_STORAGE_PATH not needed for default .indexes/
      }
    }
  }
}
```

## Troubleshooting

### Index Not Found
```bash
# Check if index exists
ls -la .indexes/*/current.db

# Verify repository hash
git remote get-url origin | sha256sum | cut -c1-12

# Create new index if needed
python scripts/cli/mcp_cli.py index build
```

### GitHub Artifacts Issues
```bash
# Ensure GITHUB_TOKEN is set
export GITHUB_TOKEN=your_token_here

# Check artifact compatibility
python scripts/index-artifact-upload-v2.py --dry-run

# Force upload regardless of compatibility
python scripts/index-artifact-upload-v2.py --force
```

### Permission Issues
```bash
# Fix ownership if needed
sudo chown -R $(whoami) .indexes/

# Ensure proper permissions
chmod -R u+rw .indexes/
```