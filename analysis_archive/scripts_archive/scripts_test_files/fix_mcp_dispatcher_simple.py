#!/usr/bin/env python3
"""
Simple fix for MCP dispatcher to use BM25 when no plugins are loaded.
This patches the enhanced dispatcher to fall back to BM25 search.
"""

import shutil
from pathlib import Path


def patch_dispatcher():
    """Patch the enhanced dispatcher to use BM25 as fallback."""
    
    dispatcher_file = Path("/workspaces/Code-Index-MCP/mcp_server/dispatcher/dispatcher_enhanced.py")
    backup_file = dispatcher_file.with_suffix('.py.backup')
    
    # Backup original
    if not backup_file.exists():
        shutil.copy2(dispatcher_file, backup_file)
        print(f"Created backup: {backup_file}")
    
    # Read the file
    content = dispatcher_file.read_text()
    
    # Find the search method
    search_start = content.find("def search(self, query: str, semantic=False, limit=20)")
    if search_start == -1:
        print("Could not find search method!")
        return
    
    # Find where to insert BM25 fallback
    no_plugins_check = """
            # For search, we may need to search across all languages
            # Load all plugins if using lazy loading
            if self._lazy_load and self._use_factory and len(self._plugins) == 0:
                self._load_all_plugins()"""
    
    bm25_fallback = """
            # For search, we may need to search across all languages
            # Load all plugins if using lazy loading
            if self._lazy_load and self._use_factory and len(self._plugins) == 0:
                self._load_all_plugins()
            
            # If still no plugins, try BM25 directly
            if len(self._plugins) == 0 and self._sqlite_store:
                logger.info("No plugins loaded, using BM25 search directly")
                try:
                    import sqlite3
                    conn = sqlite3.connect(self._sqlite_store.db_path)
                    cursor = conn.cursor()
                    
                    # Check if this is a BM25 index
                    cursor.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name='bm25_content'"
                    )
                    if cursor.fetchone():
                        # Use BM25 search
                        cursor.execute(\"\"\"
                            SELECT 
                                filepath,
                                filename,
                                snippet(bm25_content, -1, '<<', '>>', '...', 20) as snippet,
                                language,
                                rank
                            FROM bm25_content
                            WHERE bm25_content MATCH ?
                            ORDER BY rank
                            LIMIT ?
                        \"\"\", (query, limit))
                        
                        for row in cursor.fetchall():
                            filepath, filename, snippet, language, rank = row
                            yield {
                                'file': filepath,
                                'line': 1,
                                'snippet': snippet,
                                'score': abs(rank),
                                'language': language or 'unknown'
                            }
                        
                        conn.close()
                        self._operation_stats["searches"] += 1
                        self._operation_stats["total_time"] += time.time() - start_time
                        return
                    
                    conn.close()
                except Exception as e:
                    logger.error(f"Error in direct BM25 search: {e}")"""
    
    # Replace the section
    if no_plugins_check in content:
        content = content.replace(no_plugins_check, bm25_fallback)
        print("Added BM25 fallback to search method")
    else:
        print("Could not find location to insert BM25 fallback")
        return
    
    # Now patch the lookup method
    lookup_start = content.find("def lookup(self, symbol: str) -> SymbolDef | None:")
    if lookup_start != -1:
        # Find where to add BM25 lookup
        lookup_check = """
            # For symbol lookup, we may need to search across all languages
            # Load all plugins if using lazy loading
            if self._lazy_load and self._use_factory and len(self._plugins) == 0:
                self._load_all_plugins()"""
        
        bm25_lookup = """
            # For symbol lookup, we may need to search across all languages
            # Load all plugins if using lazy loading
            if self._lazy_load and self._use_factory and len(self._plugins) == 0:
                self._load_all_plugins()
            
            # If still no plugins, try BM25 directly
            if len(self._plugins) == 0 and self._sqlite_store:
                logger.info("No plugins loaded, using BM25 lookup directly")
                try:
                    import sqlite3
                    conn = sqlite3.connect(self._sqlite_store.db_path)
                    cursor = conn.cursor()
                    
                    # Try different patterns
                    patterns = [
                        f'class {symbol}', f'def {symbol}', f'function {symbol}',
                        f'interface {symbol}', f'type {symbol}'
                    ]
                    
                    for pattern in patterns:
                        cursor.execute(\"\"\"
                            SELECT filepath, snippet(bm25_content, -1, '', '', '...', 20), language
                            FROM bm25_content
                            WHERE bm25_content MATCH ?
                            ORDER BY rank
                            LIMIT 1
                        \"\"\", (pattern,))
                        
                        row = cursor.fetchone()
                        if row:
                            filepath, snippet, language = row
                            
                            # Determine kind from snippet
                            snippet_lower = snippet.lower()
                            kind = 'symbol'
                            if 'class' in snippet_lower:
                                kind = 'class'
                            elif 'def' in snippet_lower or 'function' in snippet_lower:
                                kind = 'function'
                            
                            conn.close()
                            return {
                                'symbol': symbol,
                                'kind': kind,
                                'language': language or 'unknown',
                                'defined_in': filepath,
                                'line': 1,
                                'signature': snippet,
                                'doc': ''
                            }
                    
                    conn.close()
                except Exception as e:
                    logger.error(f"Error in direct BM25 lookup: {e}")"""
        
        if lookup_check in content:
            content = content.replace(lookup_check, bm25_lookup)
            print("Added BM25 fallback to lookup method")
    
    # Write the patched file
    dispatcher_file.write_text(content)
    print(f"\nPatched dispatcher at: {dispatcher_file}")
    print("The MCP server should now use BM25 directly when no plugins are loaded")


if __name__ == "__main__":
    patch_dispatcher()