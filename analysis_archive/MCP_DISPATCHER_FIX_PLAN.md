# MCP Dispatcher Fix Plan

**Date**: 2025-06-24  
**Issue**: MCP dispatcher returns 0 results despite working SQL/BM25 storage layer  
**Root Cause**: Plugin loading timeout in EnhancedDispatcher

## Executive Summary

The MCP dispatcher has a critical issue where it times out loading plugins, preventing any search results from being returned. This plan outlines a phased approach to fix the dispatcher while maintaining backward compatibility.

## Current State Analysis

### Working Components ✅
- SQLiteStore with BM25 full-text search
- Direct SQL queries return thousands of results
- 25 populated indexes with 152,776 files
- Index structure and data integrity

### Broken Components ❌
- EnhancedDispatcher plugin loading (`_load_all_plugins()` hangs)
- Semantic search (Qdrant conflicts)
- Plugin factory timeout handling
- Fallback to BM25 when plugins fail

## Fix Implementation Plan

### Phase 1: Immediate Dispatcher Fixes (Priority: HIGH)

#### 1.1 Add Timeout to Plugin Loading
```python
# In dispatcher_enhanced.py, modify _load_all_plugins() method (lines 205-254)
def _load_all_plugins(self) -> None:
    """Load all available plugins with timeout protection."""
    if not self._use_factory:
        return
    
    import signal
    from contextlib import contextmanager
    
    @contextmanager
    def timeout(seconds):
        def timeout_handler(signum, frame):
            raise TimeoutError(f"Plugin loading timed out after {seconds}s")
        
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(seconds)
        try:
            yield
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
    
    try:
        with timeout(5):  # 5 second timeout
            self._plugins = PluginFactory.create_all_plugins(
                enable_treesitter=True,
                sqlite_store=self._sqlite_store
            )
            logger.info(f"Loaded {len(self._plugins)} plugins successfully")
    except TimeoutError as e:
        logger.warning(f"Plugin loading timeout: {e}")
        self._plugins = []  # Ensure empty list on failure
    except Exception as e:
        logger.error(f"Plugin loading failed: {e}")
        self._plugins = []
```

#### 1.2 Implement Direct BM25 Bypass
```python
# In search() method (around line 771), add early BM25 return
def search(self, query: str, limit: int = 10, **kwargs) -> Iterable[SearchResult]:
    """Search with direct BM25 fallback."""
    
    # Quick BM25 bypass for non-semantic searches
    if (self._sqlite_store and 
        not kwargs.get('semantic', False) and 
        not self.semantic_search_enabled):
        logger.info(f"Using direct BM25 search for query: {query}")
        return self._search_bm25_direct(query, limit)
    
    # Continue with normal plugin-based search...
```

#### 1.3 Add Direct BM25 Search Method
```python
def _search_bm25_direct(self, query: str, limit: int) -> Iterable[SearchResult]:
    """Direct BM25 search bypassing plugin system."""
    if not self._sqlite_store:
        return []
    
    try:
        # Use SQLiteStore's search_bm25 method directly
        results = self._sqlite_store.search_bm25(query, limit=limit)
        
        # Convert to SearchResult format
        for result in results:
            yield SearchResult(
                file_path=result.get('file_path', ''),
                line=result.get('line', 0),
                column=result.get('column', 0),
                snippet=result.get('snippet', ''),
                score=result.get('score', 0.0),
                metadata=result.get('metadata', {})
            )
    except Exception as e:
        logger.error(f"Direct BM25 search failed: {e}")
        return []
```

### Phase 2: Plugin Loading Optimization (Priority: MEDIUM)

#### 2.1 Lazy Plugin Loading by Language
```python
def _load_plugin_for_file(self, file_path: str) -> Optional[IPlugin]:
    """Load plugin on-demand for specific file type."""
    ext = Path(file_path).suffix.lower()
    language = get_language_by_extension(ext)
    
    if not language:
        return None
    
    # Check cache first
    if language in self._plugin_cache:
        return self._plugin_cache[language]
    
    # Load specific plugin
    try:
        plugin = PluginFactory.create_plugin(language, self._sqlite_store)
        self._plugin_cache[language] = plugin
        return plugin
    except Exception as e:
        logger.warning(f"Failed to load plugin for {language}: {e}")
        return None
```

#### 2.2 Parallel Plugin Loading
```python
def _load_plugins_parallel(self, languages: List[str], max_workers: int = 4):
    """Load multiple plugins in parallel."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_lang = {
            executor.submit(PluginFactory.create_plugin, lang, self._sqlite_store): lang
            for lang in languages
        }
        
        for future in as_completed(future_to_lang, timeout=10):
            language = future_to_lang[future]
            try:
                plugin = future.result()
                if plugin:
                    self._plugins.append(plugin)
                    logger.info(f"Loaded plugin for {language}")
            except Exception as e:
                logger.warning(f"Failed to load {language} plugin: {e}")
```

### Phase 3: Qdrant/Semantic Search Fix (Priority: MEDIUM)

#### 3.1 Switch to Qdrant Server Mode
```python
# In semantic_indexer.py
def _init_qdrant_client(self):
    """Initialize Qdrant client with server mode."""
    # First, try server mode (recommended for concurrent access)
    try:
        from qdrant_client import QdrantClient
        
        # Try connecting to local Qdrant server
        self.client = QdrantClient(
            host="localhost",
            port=6333,
            timeout=5
        )
        self.client.get_collections()  # Test connection
        logger.info("Connected to Qdrant server")
        return
    except Exception as e:
        logger.warning(f"Qdrant server not available: {e}")
    
    # Fallback to file-based with lock cleanup
    try:
        # Clean up any stale locks
        lock_file = self.vector_db_path / ".lock"
        if lock_file.exists():
            lock_file.unlink()
        
        self.client = QdrantClient(path=str(self.vector_db_path))
        logger.info("Using file-based Qdrant")
    except Exception as e:
        logger.error(f"Failed to initialize Qdrant: {e}")
        self.client = None
```

#### 3.2 Add Qdrant Health Check
```python
def check_semantic_search_health(self) -> Dict[str, Any]:
    """Check if semantic search is operational."""
    health = {
        "available": False,
        "mode": None,
        "collections": 0,
        "error": None
    }
    
    if not self.semantic_indexer or not self.semantic_indexer.client:
        health["error"] = "Semantic indexer not initialized"
        return health
    
    try:
        collections = self.semantic_indexer.client.get_collections()
        health["available"] = True
        health["mode"] = "server" if hasattr(self.semantic_indexer.client, 'http') else "file"
        health["collections"] = len(collections.collections)
    except Exception as e:
        health["error"] = str(e)
    
    return health
```

### Phase 4: Robust Error Handling (Priority: HIGH)

#### 4.1 Search Method Resilience
```python
def search(self, query: str, limit: int = 10, **kwargs) -> Iterable[SearchResult]:
    """Enhanced search with multiple fallback strategies."""
    results_found = False
    
    # Strategy 1: Try plugin-based search
    if self._plugins:
        try:
            for result in self._search_with_plugins(query, limit, **kwargs):
                results_found = True
                yield result
        except Exception as e:
            logger.warning(f"Plugin search failed: {e}")
    
    # Strategy 2: Try semantic search if enabled
    if not results_found and self.semantic_search_enabled:
        try:
            for result in self._search_semantic(query, limit):
                results_found = True
                yield result
        except Exception as e:
            logger.warning(f"Semantic search failed: {e}")
    
    # Strategy 3: Fallback to direct BM25
    if not results_found and self._sqlite_store:
        logger.info("Falling back to direct BM25 search")
        for result in self._search_bm25_direct(query, limit):
            yield result
```

#### 4.2 Add Search Statistics
```python
def get_search_stats(self) -> Dict[str, Any]:
    """Get search performance statistics."""
    return {
        "plugins_loaded": len(self._plugins),
        "plugin_languages": [p.language for p in self._plugins],
        "semantic_enabled": self.semantic_search_enabled,
        "semantic_health": self.check_semantic_search_health(),
        "sqlite_connected": self._sqlite_store is not None,
        "fallback_available": self._sqlite_store is not None
    }
```

## Implementation Timeline

### Day 1: Critical Fixes
1. Implement timeout protection for plugin loading
2. Add direct BM25 bypass method
3. Update search method with immediate fallback
4. Test with existing indexes

### Day 2: Plugin Optimization
1. Implement lazy plugin loading
2. Add parallel plugin loading
3. Create plugin cache management
4. Performance testing

### Day 3: Semantic Search
1. Switch to Qdrant server mode
2. Implement health checks
3. Add graceful degradation
4. Integration testing

### Day 4: Robustness & Testing
1. Add comprehensive error handling
2. Implement search statistics
3. Create test suite for all scenarios
4. Documentation updates

## Testing Strategy

### Unit Tests
```python
def test_dispatcher_timeout_handling():
    """Test that plugin loading timeout is handled gracefully."""
    dispatcher = EnhancedDispatcher(
        use_plugin_factory=True,
        lazy_load=False
    )
    # Should not hang, should fallback to BM25
    results = list(dispatcher.search("test", limit=5))
    assert len(results) >= 0  # Should not throw

def test_direct_bm25_bypass():
    """Test direct BM25 search bypass."""
    store = SQLiteStore("test.db")
    dispatcher = EnhancedDispatcher(
        sqlite_store=store,
        semantic_search_enabled=False
    )
    results = list(dispatcher.search("function", limit=10))
    assert all(isinstance(r, SearchResult) for r in results)
```

### Integration Tests
1. Test with all 25 populated indexes
2. Verify search results match direct SQL queries
3. Benchmark performance improvements
4. Test concurrent access scenarios

### Regression Tests
1. Ensure backward compatibility
2. Test all search parameter combinations
3. Verify plugin-specific features still work
4. Test multi-repository scenarios

## Success Metrics

1. **Response Time**: All searches complete within 2 seconds
2. **Success Rate**: 100% of queries return results (via plugins or fallback)
3. **Accuracy**: BM25 results match direct SQL query results
4. **Stability**: No timeouts or hangs in 1000 consecutive searches
5. **Concurrency**: Support 10 concurrent search operations

## Rollback Plan

If issues arise during implementation:

1. **Immediate**: Revert to direct SQLiteStore usage
2. **Short-term**: Create simplified dispatcher without plugin system
3. **Long-term**: Redesign plugin architecture with better isolation

## Future Enhancements

1. **Plugin Sandboxing**: Run plugins in separate processes
2. **Caching Layer**: Add Redis for search result caching  
3. **Search Analytics**: Track query patterns and optimize
4. **Plugin Profiling**: Monitor and optimize slow plugins
5. **Distributed Search**: Support searching across multiple index servers