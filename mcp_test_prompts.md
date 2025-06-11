# MCP Verification Test Prompts

Use these prompts to test if Claude Code is using MCP tools first for code search and navigation.

## Test Scenarios

### 1. Symbol Definition Tests

**Prompt 1**: "Find where the PluginManager class is defined"
- **Expected**: Should use `mcp__code-index-mcp__symbol_lookup(symbol="PluginManager")`
- **Not**: Should NOT use grep or find commands

**Prompt 2**: "Show me the FileWatcher class"
- **Expected**: Should use `mcp__code-index-mcp__symbol_lookup(symbol="FileWatcher")`
- **Not**: Should NOT search through files manually

**Prompt 3**: "Where is EnhancedDispatcher defined?"
- **Expected**: Should use `mcp__code-index-mcp__symbol_lookup(symbol="EnhancedDispatcher")`
- **Not**: Should NOT use Glob patterns

### 2. Function and Method Search Tests

**Prompt 4**: "Find all functions that start with process_"
- **Expected**: Should use `mcp__code-index-mcp__search_code(query="def process_")`
- **Not**: Should NOT use grep with regex

**Prompt 5**: "Show me all plugin classes"
- **Expected**: Should use `mcp__code-index-mcp__search_code(query="class Plugin")`
- **Then**: May do additional searches for specific plugin types
- **Not**: Should NOT read multiple files manually

**Prompt 6**: "Find all imports of dispatcher"
- **Expected**: Should use `mcp__code-index-mcp__search_code(query="from dispatcher")` 
  AND/OR `mcp__code-index-mcp__search_code(query="import dispatcher")`
- **Not**: Should NOT use find/grep combination

### 3. Semantic Search Tests

**Prompt 7**: "Where is authentication implemented?"
- **Expected**: Should use `mcp__code-index-mcp__search_code(query="authentication", semantic=true)`
- **Not**: Should NOT do basic text grep

**Prompt 8**: "Find error handling patterns"
- **Expected**: Should use `mcp__code-index-mcp__search_code(query="error handling", semantic=true)`
- **Not**: Should NOT search for try/except manually

**Prompt 9**: "Show me data validation logic"
- **Expected**: Should use `mcp__code-index-mcp__search_code(query="validation", semantic=true)`
- **Not**: Should NOT use multiple grep searches

### 4. Content Search Tests

**Prompt 10**: "Find test files for plugins"
- **Expected**: Should use `mcp__code-index-mcp__search_code(query="test_plugin")`
  OR `mcp__code-index-mcp__search_code(query="class Test.*Plugin")`
- **Note**: MCP searches content, not filenames

**Prompt 11**: "Find Python files with manager functionality"
- **Expected**: Should use `mcp__code-index-mcp__search_code(query="class Manager")` 
  OR `mcp__code-index-mcp__search_code(query="PluginManager")`
- **Not**: Should NOT use find command for filenames

### 5. Code Pattern Searches

**Prompt 12**: "Find all TODO comments in the codebase"
- **Expected**: Should use `mcp__code-index-mcp__search_code(query="TODO")`
  AND/OR `mcp__code-index-mcp__search_code(query="FIXME")`
- **Not**: Should NOT grep through all files

**Prompt 13**: "Show me all async functions"
- **Expected**: Should use `mcp__code-index-mcp__search_code(query="async def")`
- **Not**: Should NOT read files sequentially

**Prompt 14**: "Find exception handling in the dispatcher"
- **Expected**: Should use `mcp__code-index-mcp__search_code(query="except", limit=20)`
- **Then**: Filter results for dispatcher-related files
- **Not**: Should NOT manually search dispatcher files

### 6. Configuration and Secret Search Tests

**Prompt 15**: "Find where API_KEY is used"
- **Expected**: Should use `mcp__code-index-mcp__search_code(query="API_KEY")`
- **Good**: Will find in .env files, config files, and code
- **Not**: Should NOT exclude .env files from search

**Prompt 16**: "Show me database configuration"
- **Expected**: Should use `mcp__code-index-mcp__search_code(query="DATABASE_URL")`
  OR `mcp__code-index-mcp__search_code(query="database", semantic=true)`
- **Not**: Should NOT only look in specific config files

### 7. Anti-Pattern Tests (Testing Correct Behavior)

**Prompt 17**: "Search for 'PluginManager' in all Python files"
- **Expected**: Should STILL use `mcp__code-index-mcp__symbol_lookup(symbol="PluginManager")`
- **Not**: Even though prompt mentions "search", should try symbol lookup first

**Prompt 18**: "Grep for index_file function"
- **Expected**: Should STILL use `mcp__code-index-mcp__search_code(query="def index_file")`
- **Not**: Even though prompt says "grep", should use MCP

**Prompt 19**: "Use find to locate test files"
- **Expected**: Should use `mcp__code-index-mcp__search_code(query="import unittest")` 
  OR `mcp__code-index-mcp__search_code(query="import pytest")`
- **Not**: Even though prompt says "find", should use MCP for content

### 8. Real-World Usage Tests

**Prompt 20**: "How does the index_file method work?"
- **Expected**: Should use `mcp__code-index-mcp__search_code(query="def index_file")`
- **Then**: Read the specific file containing the implementation
- **Good Pattern**: Search first, then read specific results

**Prompt 21**: "What plugins support TypeScript?"
- **Expected**: Should use `mcp__code-index-mcp__search_code(query="typescript", semantic=true)`
  OR `mcp__code-index-mcp__symbol_lookup(symbol="TypeScriptPlugin")`
- **Not**: Should NOT browse plugin directories

**Prompt 22**: "Show me the reranking implementation"
- **Expected**: Should use `mcp__code-index-mcp__search_code(query="rerank")`
  OR `mcp__code-index-mcp__search_code(query="class Reranker")`
- **Not**: Should NOT guess file locations

## Verification Checklist

For each prompt, verify:

1. ✅ MCP tool is used FIRST (before any file reading)
2. ✅ Correct MCP tool is chosen (symbol_lookup vs search_code)
3. ✅ No grep/find/glob used for initial content search
4. ✅ Response time is fast (typically <2 seconds for MCP)
5. ✅ Results are accurate and relevant
6. ✅ Follow-up file reads are targeted (not browsing)

## Expected Tool Usage Patterns

### ✅ Good Pattern:
```
1. mcp__code-index-mcp__symbol_lookup or search_code
2. Read (only specific files from results)
3. Optional: Additional targeted MCP searches
```

### ❌ Bad Pattern:
```
1. Glob (to find files)
2. Grep (to search content)
3. Read (multiple files)
4. Manual searching through results
```

### ✅ Good Multi-Step Pattern:
```
1. mcp__code-index-mcp__search_code(query="dispatcher")
2. mcp__code-index-mcp__symbol_lookup(symbol="EnhancedDispatcher")
3. Read (specific file with the definition)
```

## Important Notes

1. **MCP searches content, not filenames**: To find files with specific names, search for content typically found in those files (e.g., search for "test_" or "import pytest" to find test files)

2. **Simple queries work best**: Avoid complex regex patterns. Use simple text patterns and let MCP's search handle the matching

3. **Semantic search is available**: For conceptual searches, use `semantic=true` parameter

4. **All files are indexed**: Including .env, .key, and other sensitive files, so searches will find content in configuration files

5. **Symbol lookup is precise**: Use it for class names, function names, and other defined symbols

6. **Search is broader**: Use it for patterns, content, comments, and when you're not sure of exact symbol names

## Testing Status Commands

Also test the MCP status and info commands:

- Check system status: Ask "What's the MCP index status?"
  - **Expected**: `mcp__code-index-mcp__get_status()`

- List available plugins: Ask "What languages are supported?"
  - **Expected**: `mcp__code-index-mcp__list_plugins()`

- Reindex if needed: Ask "Reindex the Python files"
  - **Expected**: `mcp__code-index-mcp__reindex(path=".", language="python")`

## Quick Test Sequence

For a rapid verification, try these in order:

1. "Find the Dispatcher class" → Should use symbol_lookup
2. "Search for TODO comments" → Should use search_code
3. "Where is authentication handled?" → Should use search_code with semantic=true
4. "Show me the index status" → Should use get_status
5. "Find database configuration" → Should search for DATABASE_URL or similar

Each should complete in seconds using MCP tools without falling back to grep/find.