# MCP Index Kit

Portable code index management for any repository using MCP (Model Context Protocol).

## Overview

MCP Index Kit enables any repository to have fast, portable code indexing with zero GitHub compute costs. It leverages GitHub Actions Artifacts for free storage and distribution of code indexes.

### Key Features

- 🚀 **Zero-cost indexing**: All indexing happens on developer machines
- 📦 **Portable indexes**: Share indexes via GitHub Artifacts (free for public repos)
- 🔄 **Automatic sync**: Pull indexes on clone, push on changes
- 🎯 **Language agnostic**: Supports 20+ programming languages
- 🔧 **Easy setup**: One command to initialize
- 🎛️ **Configurable**: Enable/disable per repository
- 🌐 **IDE integration**: Works with any MCP-compatible tool

## Installation

### Quick Start (Bash)

```bash
curl -sSL https://raw.githubusercontent.com/yourusername/mcp-index-kit/main/install.sh | bash
```

### NPM

```bash
npm install -g mcp-index-kit
mcp-index init
```

### Python

```bash
pip install mcp-index-kit
mcp-index init
```

### Manual

1. Download the latest release
2. Run the installer:
   ```bash
   ./install.sh
   ```

## Usage

### Initialize in your repository

```bash
cd your-repo
mcp-index init
```

This creates:
- `.mcp-index.json` - Configuration file
- `.mcp-index-ignore` - Patterns to exclude from indexing  
- `.github/workflows/mcp-index.yml` - GitHub Actions workflow
- `.mcp-index/` - Directory for index files

### Build index locally

```bash
mcp-index build
```

### Push index to GitHub

```bash
mcp-index push
```

### Pull latest index

```bash
mcp-index pull
```

### Automatic sync

```bash
mcp-index sync
```

## Configuration

Edit `.mcp-index.json`:

```json
{
  "enabled": true,
  "auto_download": true,
  "artifact_retention_days": 30,
  "languages": "auto",
  "github_artifacts": {
    "enabled": true,
    "compression": true,
    "max_size_mb": 100
  }
}
```

### Disable indexing

```bash
mcp-index toggle --disable
```

Or set in GitHub:
```bash
gh variable set MCP_INDEX_ENABLED --body false
```

## How it works

1. **Local indexing**: Developers build indexes on their machines
2. **Artifact storage**: Indexes are compressed and stored as GitHub artifacts
3. **Automatic download**: When cloning, the latest index is downloaded
4. **Incremental updates**: Only changed files are re-indexed
5. **PR indexes**: Each PR gets its own index for testing

## Cost Analysis

For public repositories:
- **Storage**: FREE (GitHub Actions artifacts)
- **Bandwidth**: FREE (artifact downloads)
- **Compute**: ZERO (all indexing is local)

For private repositories:
- Storage: Free up to 500MB per artifact
- Retention: 90 days (configurable)
- See [GitHub pricing](https://docs.github.com/en/billing/managing-billing-for-github-actions)

## CLI Commands

```bash
# Initialize index management
mcp-index init

# Build index locally  
mcp-index build [--semantic]

# Upload index to GitHub
mcp-index push [--validate]

# Download latest index
mcp-index pull [--latest|--pr NUMBER]

# List available indexes
mcp-index list

# Sync with remote
mcp-index sync

# Show index info
mcp-index info

# Clean up old artifacts  
mcp-index cleanup

# Enable/disable indexing
mcp-index toggle [--enable|--disable]
```

## Ignore Patterns

Edit `.mcp-index-ignore` to exclude files:

```gitignore
# Dependencies
node_modules/
vendor/

# Build outputs
dist/
build/

# Large files
*.zip
*.exe
```

## GitHub Actions Workflow

The workflow automatically:
- Builds indexes on push to main
- Creates PR-specific indexes
- Cleans up old artifacts
- Validates index integrity

### Manual trigger

```bash
gh workflow run mcp-index.yml
```

## Integration

### With MCP Server

MCP automatically detects and uses portable indexes:

```python
from mcp_server.utils.index_discovery import IndexDiscovery

discovery = IndexDiscovery(workspace_path)
if discovery.is_index_enabled():
    index_path = discovery.get_local_index_path()
```

### With IDEs

Any MCP-compatible IDE extension will automatically use the index in `.mcp-index/`.

## Troubleshooting

### Index not found

```bash
# Check if indexing is enabled
mcp-index info

# Try manual download
mcp-index pull --latest
```

### GitHub CLI not installed

Install from: https://cli.github.com/

### Permission denied

```bash
# Make scripts executable
chmod +x .mcp-index/download-index.sh
```

## Security

- Indexes contain only code structure, not source code
- Artifacts are scoped to repository visibility
- No credentials are stored in indexes
- Checksums verify index integrity

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## License

MIT License - see [LICENSE](LICENSE) file

## Support

- Issues: [GitHub Issues](https://github.com/yourusername/mcp-index-kit/issues)
- Discussions: [GitHub Discussions](https://github.com/yourusername/mcp-index-kit/discussions)
- Documentation: [Full Docs](https://mcp-index-kit.readthedocs.io/)

---

Made with ❤️ for the MCP community