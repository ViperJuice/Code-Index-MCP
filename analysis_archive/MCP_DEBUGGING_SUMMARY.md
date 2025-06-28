# MCP Debugging Summary

## Problem Identified

The MCP tools were failing to find symbols that existed in the codebase. Investigation revealed:

1. **Stale Index**: The index contained only files from `/app` (Docker mount point) instead of `/workspaces/Code-Index-MCP`
2. **No Current Files**: 0 files from the current repository were indexed
3. **Path Mismatch**: MCP searched the stale index while native tools searched actual files

## Root Cause

The index was created in a Docker environment and contained paths like `/app/mcp_server/...` instead of the current repository paths. The BM25 content table had only 464 entries, all from the wrong location.

## Solutions Implemented

### 1. Reindexed Repository
- Created `scripts/reindex_current_repo.py` to properly index current files
- Successfully indexed 64,500+ files from `/workspaces/Code-Index-MCP`
- BM25Indexer class now properly indexed and searchable

### 2. Fixed Path Translation
Enhanced `translate_path()` in `mcp_server_cli.py` to handle:
- Docker `/app/` paths → current directory
- Absolute paths that exist → no translation
- Relative paths → full path resolution

### 3. Added Index Validation
Created `validate_index()` function that checks:
- Total file count
- BM25 document count  
- Files from current repository
- Stale Docker paths
- Path accessibility

### 4. Improved Error Reporting
- Shows index validation issues when searches fail
- Provides helpful suggestions to reindex
- Reports index statistics in error messages

## Test Results

After fixes, MCP tools now work correctly:

1. **Symbol Lookup**: Successfully found BM25Indexer class
2. **Code Search**: Found 20 results for "class BM25Indexer"
3. **Performance**: Both searches completed in < 1 second

## Key Learnings

1. **Index Portability**: Indexes created in one environment (Docker) may not work in another
2. **Path Management**: Absolute paths in indexes cause issues across environments
3. **Validation**: Always validate index health before trusting search results
4. **User Feedback**: Clear error messages with actionable suggestions are crucial

## Future Improvements

1. **Relative Path Storage**: Store relative paths in indexes for better portability
2. **Auto-Reindexing**: Detect stale indexes and prompt for reindexing
3. **Index Metadata**: Store environment info with indexes
4. **Incremental Updates**: Only reindex changed files

The MCP system is now fully functional with proper error handling and user guidance.