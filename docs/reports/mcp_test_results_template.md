# MCP Test Results Template

**Test Date**: _______________  
**Claude Code Version**: _______________  
**Repository**: MCP Indexer Own Repo  
**Index Status**: _______________

## Test Results

### 1. Symbol Definition Tests

| Prompt | Expected Tool | Actual Tool Used | Result | Time | Notes |
|--------|--------------|------------------|--------|------|-------|
| Find where the PluginManager class is defined | `symbol_lookup("PluginManager")` | | ⬜ Pass ⬜ Fail | | |
| Show me the FileWatcher class | `symbol_lookup("FileWatcher")` | | ⬜ Pass ⬜ Fail | | |
| Where is EnhancedDispatcher defined? | `symbol_lookup("EnhancedDispatcher")` | | ⬜ Pass ⬜ Fail | | |

### 2. Function and Method Search Tests

| Prompt | Expected Tool | Actual Tool Used | Result | Time | Notes |
|--------|--------------|------------------|--------|------|-------|
| Find all functions that start with process_ | `search_code("def process_")` | | ⬜ Pass ⬜ Fail | | |
| Show me all plugin classes | `search_code("class Plugin")` | | ⬜ Pass ⬜ Fail | | |
| Find all imports of dispatcher | `search_code("from dispatcher")` or `search_code("import dispatcher")` | | ⬜ Pass ⬜ Fail | | |

### 3. Semantic Search Tests

| Prompt | Expected Tool | Actual Tool Used | Result | Time | Notes |
|--------|--------------|------------------|--------|------|-------|
| Where is authentication implemented? | `search_code("authentication", semantic=true)` | | ⬜ Pass ⬜ Fail | | |
| Find error handling patterns | `search_code("error handling", semantic=true)` | | ⬜ Pass ⬜ Fail | | |
| Show me data validation logic | `search_code("validation", semantic=true)` | | ⬜ Pass ⬜ Fail | | |

### 4. Content Search Tests

| Prompt | Expected Tool | Actual Tool Used | Result | Time | Notes |
|--------|--------------|------------------|--------|------|-------|
| Find test files for plugins | `search_code("test_plugin")` | | ⬜ Pass ⬜ Fail | | |
| Find Python files with manager functionality | `search_code("class Manager")` or `search_code("PluginManager")` | | ⬜ Pass ⬜ Fail | | |

### 5. Code Pattern Searches

| Prompt | Expected Tool | Actual Tool Used | Result | Time | Notes |
|--------|--------------|------------------|--------|------|-------|
| Find all TODO comments in the codebase | `search_code("TODO")` | | ⬜ Pass ⬜ Fail | | |
| Show me all async functions | `search_code("async def")` | | ⬜ Pass ⬜ Fail | | |
| Find exception handling in the dispatcher | `search_code("except", limit=20)` | | ⬜ Pass ⬜ Fail | | |

### 6. Configuration and Secret Search Tests

| Prompt | Expected Tool | Actual Tool Used | Result | Time | Notes |
|--------|--------------|------------------|--------|------|-------|
| Find where API_KEY is used | `search_code("API_KEY")` | | ⬜ Pass ⬜ Fail | | |
| Show me database configuration | `search_code("DATABASE_URL")` or `search_code("database", semantic=true)` | | ⬜ Pass ⬜ Fail | | |

### 7. Anti-Pattern Tests

| Prompt | Expected Tool | Actual Tool Used | Result | Time | Notes |
|--------|--------------|------------------|--------|------|-------|
| Search for 'PluginManager' in all Python files | `symbol_lookup("PluginManager")` | | ⬜ Pass ⬜ Fail | | |
| Grep for index_file function | `search_code("def index_file")` | | ⬜ Pass ⬜ Fail | | |
| Use find to locate test files | `search_code("import unittest")` or `search_code("import pytest")` | | ⬜ Pass ⬜ Fail | | |

### 8. Real-World Usage Tests

| Prompt | Expected Tool | Actual Tool Used | Result | Time | Notes |
|--------|--------------|------------------|--------|------|-------|
| How does the index_file method work? | `search_code("def index_file")` | | ⬜ Pass ⬜ Fail | | |
| What plugins support TypeScript? | `search_code("typescript", semantic=true)` or `symbol_lookup("TypeScriptPlugin")` | | ⬜ Pass ⬜ Fail | | |
| Show me the reranking implementation | `search_code("rerank")` or `search_code("class Reranker")` | | ⬜ Pass ⬜ Fail | | |

### Status Commands

| Prompt | Expected Tool | Actual Tool Used | Result | Time | Notes |
|--------|--------------|------------------|--------|------|-------|
| What's the MCP index status? | `get_status()` | | ⬜ Pass ⬜ Fail | | |
| What languages are supported? | `list_plugins()` | | ⬜ Pass ⬜ Fail | | |

## Summary Statistics

- **Total Tests**: 24
- **Passed**: _____ 
- **Failed**: _____
- **Pass Rate**: _____%

## Common Issues Found

1. ________________________________
2. ________________________________
3. ________________________________

## Recommendations

1. ________________________________
2. ________________________________
3. ________________________________