# Git Hooks for Automatic Index Synchronization

## Overview

The MCP Index Kit now includes git hooks that automatically manage index uploads and downloads during normal git operations. This eliminates the need for manual index management commands in most workflows.

## Available Hooks

### 1. **pre-push Hook**
- **Triggers**: Before `git push`
- **Action**: Uploads index changes to GitHub Artifacts
- **Conditions**: 
  - Only runs if index files have been modified
  - Only runs if `auto_upload` is enabled in configuration
  - Non-blocking: push continues even if upload fails

### 2. **post-merge Hook**
- **Triggers**: After `git pull` or `git merge`
- **Action**: Downloads latest index from GitHub Artifacts
- **Conditions**:
  - Downloads if no local index exists
  - Downloads if configuration changed
  - Downloads if local index is outdated
  - Only runs if `auto_download` is enabled

### 3. **post-checkout Hook**
- **Triggers**: When switching branches with `git checkout`
- **Action**: Checks index compatibility with new branch
- **Features**:
  - Detects PR branches and suggests PR-specific indexes
  - Warns if index is from different commit
  - Provides commands to update index if needed

## Installation

### During Initial Setup

When running `mcp-index init` or the installer, you'll be prompted:

```bash
Would you like to install git hooks for automatic index sync? [Y/n]
```

### Manual Installation

```bash
# Install hooks
mcp-index hooks install

# Check status
mcp-index hooks status

# Uninstall hooks
mcp-index hooks uninstall
```

### Direct Installation

```bash
# From the repository root
bash mcp-index-kit/hooks/install-hooks.sh

# To uninstall
bash mcp-index-kit/hooks/install-hooks.sh --uninstall
```

## Configuration

The hooks respect settings in `.mcp-index.json`:

```json
{
  "enabled": true,           // Master switch for all index features
  "auto_upload": true,       // Enable automatic uploads on push
  "auto_download": true      // Enable automatic downloads on pull
}
```

### Disabling Auto-sync

To disable automatic synchronization while keeping manual commands:

```json
{
  "enabled": true,
  "auto_upload": false,
  "auto_download": false
}
```

## Workflow Examples

### Developer Workflow with Hooks

1. **Clone repository**:
   ```bash
   git clone <repo>
   cd <repo>
   # post-merge hook downloads index automatically
   ```

2. **Make changes and update index**:
   ```bash
   # Edit code...
   python mcp_cli.py index rebuild  # Update local index
   git add .
   git commit -m "feat: new feature"
   git push  # pre-push hook uploads index automatically
   ```

3. **Pull updates**:
   ```bash
   git pull  # post-merge hook downloads updated index
   ```

4. **Switch branches**:
   ```bash
   git checkout feature-branch  # post-checkout warns if index mismatch
   ```

### CI/CD Integration

The hooks work seamlessly with GitHub Actions:

1. Developer pushes with local index
2. pre-push hook uploads to artifacts
3. GitHub Actions validates the uploaded index
4. No rebuilding needed in CI/CD

## Hook Implementation Details

### Safety Features

1. **Non-blocking**: Hooks never prevent git operations from completing
2. **Error handling**: Failures are logged but don't interrupt workflow
3. **Compatibility checks**: Verify environment before running
4. **Backup preservation**: Existing hooks are backed up during installation

### Performance

- **pre-push**: Only runs if index files changed (< 1 second overhead)
- **post-merge**: Checks are fast, download only when needed
- **post-checkout**: Instant compatibility check

### Requirements

- Git 2.x or higher
- Bash shell
- `jq` for JSON parsing (optional but recommended)
- GitHub CLI (`gh`) for artifact operations

## Troubleshooting

### Hooks not running

1. Check if hooks are installed:
   ```bash
   mcp-index hooks status
   ```

2. Verify hooks are executable:
   ```bash
   ls -la .git/hooks/pre-push
   ```

3. Check configuration:
   ```bash
   cat .mcp-index.json | jq '.auto_upload, .auto_download'
   ```

### Upload failures

- Ensure GitHub CLI is authenticated:
  ```bash
  gh auth status
  ```

- Check network connectivity
- Verify repository permissions

### Download failures

- Install GitHub CLI if missing:
  ```bash
  # macOS
  brew install gh
  
  # Linux
  sudo apt install gh
  ```

### Disable hooks temporarily

```bash
# Disable for one command
git -c core.hooksPath=/dev/null push

# Or use configuration
mcp-index toggle --disable
```

## Best Practices

1. **Review changes**: Hooks show what they're doing but don't require interaction
2. **Keep indexes small**: Use `.mcp-index-ignore` to exclude unnecessary files
3. **Regular cleanup**: Old artifacts are automatically cleaned up after 30 days
4. **PR workflows**: Each PR gets its own index artifact

## Security Considerations

1. **No credentials in indexes**: Hooks use secure export by default
2. **Artifact visibility**: Follows repository visibility settings
3. **Checksum verification**: All downloads are verified
4. **Local-first**: All indexing happens on developer machines

## Future Enhancements

- Incremental index updates (only upload changes)
- Support for other git operations (rebase, cherry-pick)
- Integration with git-lfs for large indexes
- P2P index sharing between developers