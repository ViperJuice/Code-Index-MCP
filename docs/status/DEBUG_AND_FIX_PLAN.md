# Debug and Fix Plan for MCP Server Issues

## Issue Analysis

### 1. Python File Count Shows 0

**Root Cause**: Multiple issues identified:
- The `get_indexed_count()` method was checking for wrong attribute (`_file_contents` instead of `index`)
- Fixed this in both basic and semantic Python plugins
- However, still showing 0 because the running MCP server instance may be using different plugin instances

**Additional Finding**: 
- The plugin manager initialization in debug script shows 0 plugins loaded
- SQLite schema issues preventing plugin initialization ("no such table: repositories")
- This suggests the MCP server running through Claude Code uses a different initialization path

### 2. Complex Semantic Queries Return No Results

**Root Cause Analysis**:
- Basic Python plugin returns empty list for semantic queries: `if opts and opts.get("semantic"): return []`
- Semantic plugin exists but may not be loaded when `SEMANTIC_SEARCH_ENABLED=true`
- Environment variable loading happens after plugin imports in some cases

**Key Issues**:
1. Plugin selection happens at import time in `__init__.py`
2. Environment variables from `.env` may not be loaded early enough
3. Voyage AI integration requires API key which may not be available to the MCP server process

### 3. Semantic Search Partially Implemented

**Implementation Status**:
- ✅ SemanticIndexer class fully implemented
- ✅ Voyage AI client integration complete
- ✅ Qdrant vector storage working (tested with in-memory)
- ✅ Enhanced plugin base class created
- ⚠️ Plugin switching logic may not work in production
- ❌ Semantic indexing not called during regular indexing
- ❌ Complex queries fail because embeddings aren't created

## Comprehensive Fix Plan

### Phase 1: Fix Python File Count (Quick Win)

1. **Update Dispatcher Status Collection**
   ```python
   # In mcp_server_cli.py, line 219
   # Current: lang = getattr(plugin, 'language', getattr(plugin, 'lang', 'unknown'))
   # Should be: lang = getattr(plugin, 'lang', getattr(plugin, 'language', 'unknown'))
   ```

2. **Ensure Consistent Plugin Attribute**
   - Add `language` property to base plugin class that returns `lang`
   - Or update all references to use `lang` consistently

### Phase 2: Fix Semantic Search Loading

1. **Early Environment Loading**
   ```python
   # In mcp_server_cli.py - already fixed
   from dotenv import load_dotenv
   load_dotenv()
   ```

2. **Fix Plugin Selection Logic**
   ```python
   # In plugin __init__.py files
   # Move environment check to lazy loading or factory method
   def get_plugin_class():
       if os.getenv("SEMANTIC_SEARCH_ENABLED", "false").lower() == "true":
           return PythonPluginSemantic
       return Plugin
   ```

3. **Ensure API Keys Available**
   - Verify VOYAGE_API_KEY is in environment
   - Add fallback for missing keys
   - Better error messages

### Phase 3: Complete Semantic Integration

1. **Fix Semantic Indexing Call**
   ```python
   # In plugin_semantic.py indexFile method
   # Currently: self.index_with_embeddings() is called
   # Need to verify: _enable_semantic is True
   # Add logging to trace execution
   ```

2. **Debug Embedding Creation**
   ```python
   # Add debug logging
   logger.info(f"Semantic enabled: {self._enable_semantic}")
   logger.info(f"Creating embeddings for {len(symbols)} symbols")
   ```

3. **Fix Search Method**
   ```python
   # Ensure semantic search actually queries embeddings
   # Currently may be falling back to traditional search
   ```

## Implementation Steps

### Step 1: Create Test Harness
Create a test script that mimics MCP server initialization to debug issues in isolation.

### Step 2: Add Comprehensive Logging
Add debug logging at key points:
- Plugin initialization
- Environment variable loading
- Semantic indexer creation
- Embedding generation
- Search query routing

### Step 3: Fix Configuration Loading
Ensure all configuration is loaded before plugin initialization:
- Load .env at startup
- Validate required API keys
- Check Qdrant connectivity

### Step 4: Implement Fixes
1. Fix get_indexed_count() ✅ (already done)
2. Fix language/lang attribute usage
3. Fix plugin selection logic
4. Ensure semantic indexing is called
5. Verify search routing

### Step 5: Test End-to-End
1. Index a repository with semantic enabled
2. Verify embeddings are created
3. Test semantic search queries
4. Confirm file counts are accurate

## Testing Strategy

### Unit Tests
```python
def test_python_plugin_count():
    plugin = PythonPlugin()
    plugin.indexFile("test.py", "def test(): pass")
    assert plugin.get_indexed_count() == 1

def test_semantic_plugin_loading():
    os.environ["SEMANTIC_SEARCH_ENABLED"] = "true"
    from mcp_server.plugins.python_plugin import Plugin
    assert isinstance(Plugin(), PythonPluginSemantic)
```

### Integration Tests
1. Start MCP server with semantic enabled
2. Index sample repository
3. Verify status shows correct counts
4. Test semantic search returns results

## Next Actions

1. **Immediate**: Fix language/lang attribute issue in status collection
2. **Short-term**: Improve plugin loading to respect environment variables
3. **Medium-term**: Add comprehensive debug logging
4. **Long-term**: Refactor plugin system for better configurability

## Success Criteria

- [ ] Python file count shows actual number of indexed files
- [ ] Semantic search returns relevant results for natural language queries
- [ ] All language plugins report accurate counts
- [ ] No errors in logs during indexing or searching
- [ ] Performance remains acceptable with semantic search enabled