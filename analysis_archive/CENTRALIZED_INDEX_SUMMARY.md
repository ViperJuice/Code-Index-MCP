# Centralized Index Storage Implementation

## Summary of Changes

We've successfully simplified the MCP index storage to use a single centralized location at `~/.mcp/indexes/`. This eliminates confusion about which index is being used and prevents indexes from being accidentally committed to git.

### Key Changes Made:

1. **Single Storage Location**
   - All indexes now stored at: `~/.mcp/indexes/{repo_hash}/{branch}_{commit}.db`
   - Removed support for local `.mcp-index/` directories
   - Removed fallback to `code_index.db`

2. **Simplified MCP Server**
   - Now only checks the central location
   - Automatically defaults to `~/.mcp/indexes` if not configured
   - Provides clear error messages if no index found

3. **Migration Completed**
   - Moved main repository index to central location
   - Moved all test repository indexes (10 repositories)
   - Removed `.mcp-index/` directory from repository
   - Total of 21 indexes now in central storage

4. **Updated Configuration**
   - Removed storage strategy options from templates
   - Simplified `.mcp-index.json` configuration
   - No need to set `MCP_INDEX_STORAGE_PATH` explicitly

### Repository Structure

Each repository gets a unique hash-based directory:
```
~/.mcp/indexes/
├── f7b49f5d0ae0/          # Code-Index-MCP main repo
│   ├── main_f48abb0.db     # Index for main branch at commit f48abb0
│   ├── main_f48abb0.metadata.json
│   └── current.db -> main_f48abb0.db
├── 96d34ef1438c/          # go_gin test repo
│   ├── test_main.db
│   ├── test_bm25.db
│   └── current.db -> test_main.db
└── ... (other repositories)
```

### Benefits

1. **No Accidental Commits**: Indexes stored outside repositories
2. **Reusability**: Same index works across multiple clones
3. **Simplicity**: Single location, no confusion
4. **Clean Repos**: No index files in working directories

### Usage

For new repositories:
1. Create index with `mcp-index index`
2. Index automatically stored in central location

For existing repositories with local indexes:
1. Run `python scripts/move_indexes_to_central.py`
2. Index moved to central location
3. MCP server automatically uses central index

The MCP server will show an error if no index exists, with instructions on how to create one.