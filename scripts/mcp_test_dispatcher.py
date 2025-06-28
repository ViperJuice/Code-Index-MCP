#!/usr/bin/env python3
"""
MCP dispatcher for test repositories that checks test_indexes directory.
"""

import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Any, Iterable
import logging
import time
from mcp_server.core.path_utils import PathUtils

logger = logging.getLogger(__name__)


class TestIndexDispatcher:
    """Dispatcher that can use test indexes."""
    
    def __init__(self, test_repo_name: Optional[str] = None):
        """Initialize dispatcher for a specific test repository."""
        self.test_repo_name = test_repo_name
        self.test_indexes_dir = Path("PathUtils.get_workspace_root()/test_indexes")
        self._current_index = None
        self._operation_stats = {
            "searches": 0,
            "lookups": 0,
            "total_time": 0.0
        }
        
        if test_repo_name:
            self._set_test_index(test_repo_name)
    
    def _set_test_index(self, repo_name: str) -> bool:
        """Set the current index to a test repository."""
        repo_dir = self.test_indexes_dir / repo_name
        
        if not repo_dir.exists():
            logger.warning(f"Test repo directory not found: {repo_dir}")
            return False
        
        # Look for BM25 index files
        candidates = [
            repo_dir / "code_index.db",
            repo_dir / "simple_bm25.db",
            repo_dir / "bm25_index.db"
        ]
        
        for db_path in candidates:
            if db_path.exists():
                # Verify it has bm25_content table
                try:
                    conn = sqlite3.connect(str(db_path))
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT name FROM sqlite_master 
                        WHERE type='table' AND name='bm25_content'
                    """)
                    if cursor.fetchone():
                        self._current_index = db_path
                        conn.close()
                        logger.info(f"Using test index: {db_path}")
                        return True
                    conn.close()
                except:
                    pass
        
        logger.warning(f"No valid BM25 index found for {repo_name}")
        return False
    
    def _search_bm25(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search BM25 index directly."""
        if not self._current_index or not self._current_index.exists():
            logger.warning(f"No valid index at {self._current_index}")
            return []
        
        conn = sqlite3.connect(str(self._current_index))
        cursor = conn.cursor()
        
        try:
            # Search using FTS5
            cursor.execute("""
                SELECT 
                    filepath,
                    filename,
                    snippet(bm25_content, -1, '<<', '>>', '...', 20) as snippet,
                    rank
                FROM bm25_content
                WHERE bm25_content MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (query, limit))
            
            results = []
            for row in cursor.fetchall():
                filepath, filename, snippet, rank = row
                
                # Default line number
                line_num = 1
                
                results.append({
                    'file': filepath,
                    'filename': filename,
                    'line': line_num,
                    'snippet': snippet,
                    'score': abs(rank)
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error in BM25 search: {e}")
            return []
        finally:
            conn.close()
    
    def search(self, query: str, semantic: bool = False, limit: int = 20) -> Iterable[Dict[str, Any]]:
        """Search for code and documentation."""
        start_time = time.time()
        
        try:
            results = self._search_bm25(query, limit)
            
            self._operation_stats["searches"] += 1
            self._operation_stats["total_time"] += time.time() - start_time
            
            for result in results:
                yield result
                
        except Exception as e:
            logger.error(f"Error in search for '{query}': {e}")
    
    def lookup(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Look up symbol definition."""
        start_time = time.time()
        
        try:
            # Try different patterns for symbol definitions
            patterns = [
                f'class {symbol}',
                f'def {symbol}',
                f'function {symbol}',
                f'interface {symbol}',
                f'struct {symbol}',
                f'type {symbol}',
                f'const {symbol}',
                f'var {symbol}',
                f'let {symbol}'
            ]
            
            for pattern in patterns:
                results = self._search_bm25(pattern, limit=5)
                if results:
                    best = results[0]
                    
                    # Detect kind from snippet
                    snippet_lower = best['snippet'].lower()
                    kind = 'symbol'
                    
                    if 'class' in snippet_lower:
                        kind = 'class'
                    elif 'def' in snippet_lower or 'function' in snippet_lower:
                        kind = 'function'
                    elif 'interface' in snippet_lower:
                        kind = 'interface'
                    elif any(kw in snippet_lower for kw in ['const', 'var', 'let']):
                        kind = 'variable'
                    
                    # Detect language from file extension
                    ext = Path(best['file']).suffix.lower()
                    lang_map = {
                        '.py': 'python',
                        '.js': 'javascript', 
                        '.ts': 'typescript',
                        '.java': 'java',
                        '.go': 'go',
                        '.rs': 'rust',
                        '.cpp': 'cpp',
                        '.c': 'c',
                        '.cs': 'csharp',
                        '.swift': 'swift',
                        '.dart': 'dart',
                        '.lua': 'lua',
                        '.rb': 'ruby'
                    }
                    
                    result = {
                        'symbol': symbol,
                        'kind': kind,
                        'language': lang_map.get(ext, 'unknown'),
                        'defined_in': best['file'],
                        'line': best['line'],
                        'signature': best['snippet'],
                        'doc': ''
                    }
                    
                    self._operation_stats["lookups"] += 1
                    self._operation_stats["total_time"] += time.time() - start_time
                    
                    return result
            
            self._operation_stats["lookups"] += 1
            self._operation_stats["total_time"] += time.time() - start_time
            
            return None
            
        except Exception as e:
            logger.error(f"Error in symbol lookup for '{symbol}': {e}")
            return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get dispatcher statistics."""
        return {
            'operations': self._operation_stats,
            'total_operations': self._operation_stats['searches'] + self._operation_stats['lookups'],
            'backend': 'bm25_test_index',
            'index_path': str(self._current_index) if self._current_index else None,
            'test_repo': self.test_repo_name
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Check dispatcher health."""
        return {
            'status': 'operational' if self._current_index and self._current_index.exists() else 'degraded',
            'backend': 'bm25_test_index',
            'index': str(self._current_index) if self._current_index else None,
            'test_repo': self.test_repo_name
        }


def test_dispatcher():
    """Test the dispatcher with different repositories."""
    
    print("Testing Test Index Dispatcher")
    print("=" * 80)
    
    test_repos = ["go_gin", "python_django", "typescript_TypeScript"]
    
    for repo_name in test_repos:
        print(f"\n\nTesting {repo_name}")
        print("-" * 40)
        
        dispatcher = TestIndexDispatcher(repo_name)
        health = dispatcher.health_check()
        
        if health['status'] != 'operational':
            print(f"Failed to load index for {repo_name}")
            continue
        
        # Test symbol lookup
        if repo_name == "go_gin":
            symbols = ["Engine", "Context", "RouterGroup"]
        elif repo_name == "python_django":
            symbols = ["Model", "View", "HttpResponse"]
        else:
            symbols = ["Parser", "Scanner", "Compiler"]
        
        print("\nSymbol lookups:")
        for symbol in symbols:
            result = dispatcher.lookup(symbol)
            if result:
                print(f"  {symbol}: Found in {result['defined_in']}")
            else:
                print(f"  {symbol}: Not found")
        
        # Test search
        print("\nSearch tests:")
        queries = ["error", "test", "config"]
        for query in queries:
            results = list(dispatcher.search(query, limit=3))
            print(f"  '{query}': {len(results)} results")
        
        stats = dispatcher.get_statistics()
        print(f"\nStats: {stats['operations']}")


if __name__ == "__main__":
    test_dispatcher()