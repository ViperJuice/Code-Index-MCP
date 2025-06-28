# Centralized Index Storage Implementation

## Overview

This document describes the implementation of centralized index storage for the Code-Index-MCP system, completed on January 15, 2025.

## Changes Made

### 1. Core Implementation

#### Storage Location
- All indexes now stored at: `~/.mcp/indexes/{repo_hash}/{branch}_{commit}.db`
- Repository isolation using SHA256 hash of git remote URL (12 chars)
- Version management with branch and commit information
- Current index tracked via `current.db` symlink

#### Key Files Modified
- `scripts/cli/mcp_server_cli.py` - Updated to only check central location
- `mcp_server/storage/sqlite_store.py` - Skip migrations for existing databases
- `mcp_server/utils/index_discovery.py` - Support centralized storage strategy
- `mcp_server/core/path_resolver.py` - Added index storage path management

#### New Scripts
- `scripts/move_indexes_to_central.py` - Migrate existing indexes
- `scripts/migrate_all_test_indexes.py` - Migrate test repository indexes
- `scripts/demo_centralized_indexes.py` - Demonstration of new system
- `scripts/mcp_index_manager.py` - CLI for index management

### 2. Configuration Updates

#### Environment Variables
- `MCP_INDEX_STORAGE_PATH` - Defaults to `~/.mcp/indexes`
- Removed `MCP_INDEX_STRATEGY` - No longer needed
- Removed explicit path from `.mcp.json`

#### Template Updates
- `.mcp-index.json` - Removed storage strategy fields
- `mcp-index-kit/templates/mcp-index.json` - Simplified configuration

### 3. Documentation Updates

#### ROADMAP.md
- Added "Centralized Index Storage" to recently completed section
- Documented benefits and migration process

#### README.md
- Added centralized storage to key features
- New section on centralized index management
- Migration instructions for existing users

#### Architecture Documentation
- `architecture/README.md` - Added centralized storage section
- `architecture/implementation-status.md` - Added index management component
- `architecture/level4/storage_actual.puml` - Updated storage diagram
- `architecture/level4/index_management.puml` - New diagram for index system
- `architecture/workspace.dsl` - Updated storage container description

### 4. Migration Results

#### Indexes Migrated
- Main repository index: 1
- Test repository indexes: 10 repositories
- Total indexes in central storage: 21

#### Cleanup
- Removed `.mcp-index/` directory from repository
- All test indexes moved to central location
- No configuration needed for new clones

## Benefits Achieved

1. **Simplicity**: Single storage location, no confusion
2. **Safety**: Indexes never accidentally committed to git
3. **Reusability**: Same index works across multiple clones
4. **Organization**: Clear structure with repo/branch/commit naming
5. **Zero Configuration**: Works out-of-the-box

## Migration Guide

For users with existing local indexes:

```bash
# One-time migration
python scripts/move_indexes_to_central.py

# Verify migration
ls ~/.mcp/indexes/
```

For new users:
- Indexes automatically created in central location
- No migration needed

## Technical Details

### Repository Hash Generation
```python
def get_repo_identifier(repo_path):
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        capture_output=True,
        text=True
    )
    remote_url = result.stdout.strip()
    return hashlib.sha256(remote_url.encode()).hexdigest()[:12]
```

### Index Naming Convention
- Format: `{branch}_{commit_short}.db`
- Example: `main_f48abb0.db`
- Metadata: `main_f48abb0.metadata.json`
- Current: `current.db` -> symlink to active index

### Error Handling
- Clear error messages when no index found
- Instructions for creating new index
- Fallback to path-based hash if no git remote

## Future Considerations

1. **Cleanup Policy**: Currently keeps 3 indexes per branch
2. **Backup Strategy**: Easy to backup `~/.mcp/indexes/`
3. **Multi-User**: Each user has their own `~/.mcp/indexes/`
4. **Cloud Sync**: Could sync centralized indexes if needed

## Conclusion

The centralized index storage implementation successfully simplifies index management while maintaining all existing functionality. The system is more robust, easier to use, and prevents common issues like accidentally committing indexes to git.