#!/usr/bin/env python3
"""Quick fix for MCP dispatcher timeout issues."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def create_dispatcher_patch():
    """Create a patch file for the dispatcher timeout fix."""
    
    patch_content = '''--- a/mcp_server/dispatcher/dispatcher_enhanced.py
+++ b/mcp_server/dispatcher/dispatcher_enhanced.py
@@ -205,6 +205,30 @@ class EnhancedDispatcher:
     def _load_all_plugins(self) -> None:
         """Load all available plugins via PluginFactory."""
         if not self._use_factory:
             return
+        
+        import signal
+        from contextlib import contextmanager
+        
+        @contextmanager
+        def timeout(seconds):
+            def timeout_handler(signum, frame):
+                raise TimeoutError(f"Plugin loading timed out after {seconds}s")
+            
+            # Only use alarm on Unix-like systems
+            if hasattr(signal, 'SIGALRM'):
+                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
+                signal.alarm(seconds)
+                try:
+                    yield
+                finally:
+                    signal.alarm(0)
+                    signal.signal(signal.SIGALRM, old_handler)
+            else:
+                # On Windows, just yield without timeout
+                yield
+        
+        try:
+            with timeout(5):  # 5 second timeout
                 # Get plugin manager
                 if self._memory_aware and self._plugin_manager:
                     # Memory-aware loading
@@ -251,6 +275,12 @@ class EnhancedDispatcher:
                         self._plugin_router.register_plugin(plugin)
                 
                 logger.info(f"Loaded {len(self._plugins)} plugins")
+        except TimeoutError as e:
+            logger.warning(f"Plugin loading timeout: {e}")
+            self._plugins = []  # Ensure empty list on failure
+        except Exception as e:
+            logger.error(f"Plugin loading failed: {e}")
+            self._plugins = []
 
     def _get_search_strategy(self, query: str) -> str:
         """Determine the search strategy based on query analysis."""
@@ -768,6 +798,22 @@ class EnhancedDispatcher:
         """
         # Implementation tracking
         logger.debug(f"Search called with query='{query}', limit={limit}, kwargs={kwargs}")
+        
+        # Quick BM25 bypass for non-semantic searches when plugins aren't loaded
+        if (self._sqlite_store and 
+            not kwargs.get('semantic', False) and 
+            not self.semantic_search_enabled and
+            (not self._plugins or len(self._plugins) == 0)):
+            logger.info(f"Using direct BM25 search bypass for query: {query}")
+            try:
+                results = self._sqlite_store.search_bm25(query, limit=limit)
+                for result in results:
+                    yield SearchResult(
+                        file_path=result.get('file_path', ''),
+                        line=result.get('line', 0),
+                        snippet=result.get('snippet', ''),
+                        score=result.get('score', 0.0)
+                    )
+                return
+            except Exception as e:
+                logger.warning(f"Direct BM25 bypass failed: {e}")
         
         # Ensure plugins are loaded if using lazy loading
         if self._lazy_load and self._use_factory and len(self._plugins) == 0:
'''
    
    with open("dispatcher_timeout_fix.patch", "w") as f:
        f.write(patch_content)
    
    print("Created patch file: dispatcher_timeout_fix.patch")
    print("\nTo apply the patch:")
    print("  patch -p1 < dispatcher_timeout_fix.patch")
    print("\nOr manually apply the changes to:")
    print("  mcp_server/dispatcher/dispatcher_enhanced.py")


def test_fixed_dispatcher():
    """Test the dispatcher with timeout fix applied."""
    from mcp_server.storage.sqlite_store import SQLiteStore
    from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
    
    print("\nTesting dispatcher with timeout fix...")
    
    # Use a known working index
    db_path = ".indexes/f7b49f5d0ae0/current.db"
    
    try:
        store = SQLiteStore(db_path)
        
        # Create dispatcher with minimal config to avoid issues
        dispatcher = EnhancedDispatcher(
            sqlite_store=store,
            semantic_search_enabled=False,
            lazy_load=True,  # Will trigger plugin loading
            use_plugin_factory=True
        )
        
        # Test search - should use BM25 bypass
        results = list(dispatcher.search("def", limit=5))
        print(f"✓ Search returned {len(results)} results")
        
        if results:
            print(f"  First result: {results[0].file_path}")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        test_fixed_dispatcher()
    else:
        create_dispatcher_patch()