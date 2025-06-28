#!/usr/bin/env python3
"""
Patch to fix MCP dispatcher to use BM25 search directly.
"""

import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Any


class BM25SearchAdapter:
    """Adapter to search BM25 index directly."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
    
    def search(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search BM25 index."""
        if not self.db_path.exists():
            return []
        
        conn = sqlite3.connect(str(self.db_path))
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
                
                # Extract line number from snippet if possible
                line_num = 1  # Default
                
                results.append({
                    'file': filepath,
                    'filename': filename,
                    'line': line_num,
                    'snippet': snippet,
                    'score': abs(rank)
                })
            
            return results
            
        finally:
            conn.close()
    
    def lookup_symbol(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Lookup symbol definition."""
        # Try different patterns
        patterns = [
            f'class {symbol}',
            f'def {symbol}',
            f'function {symbol}',
            f'{symbol} =',
            f'const {symbol}',
            f'var {symbol}',
            f'let {symbol}'
        ]
        
        for pattern in patterns:
            results = self.search(pattern, limit=5)
            if results:
                # Return best match
                best = results[0]
                
                # Try to determine kind from snippet
                snippet = best['snippet'].lower()
                if 'class' in snippet:
                    kind = 'class'
                elif 'def' in snippet or 'function' in snippet:
                    kind = 'function'
                elif 'const' in snippet or 'var' in snippet or 'let' in snippet:
                    kind = 'variable'
                else:
                    kind = 'symbol'
                
                return {
                    'symbol': symbol,
                    'kind': kind,
                    'language': self._detect_language(best['file']),
                    'defined_in': best['file'],
                    'line': best['line'],
                    'signature': best['snippet'],
                    'doc': ''
                }
        
        return None
    
    def _detect_language(self, filepath: str) -> str:
        """Detect language from file extension."""
        ext_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.java': 'java',
            '.go': 'go',
            '.rs': 'rust',
            '.cpp': 'cpp',
            '.c': 'c',
            '.cs': 'csharp',
            '.rb': 'ruby',
            '.php': 'php'
        }
        
        ext = Path(filepath).suffix.lower()
        return ext_map.get(ext, 'unknown')


def patch_dispatcher_class():
    """Create a patched dispatcher class that uses BM25 directly."""
    
    class PatchedDispatcher:
        """Dispatcher that uses BM25 search directly."""
        
        def __init__(self, db_path: Path):
            self.bm25_adapter = BM25SearchAdapter(db_path)
            self._operation_stats = {
                'lookups': 0,
                'searches': 0,
                'total_time': 0
            }
        
        def lookup(self, symbol: str) -> Optional[Dict[str, Any]]:
            """Lookup symbol using BM25."""
            self._operation_stats['lookups'] += 1
            return self.bm25_adapter.lookup_symbol(symbol)
        
        def search(self, query: str, semantic: bool = False, limit: int = 20) -> List[Dict[str, Any]]:
            """Search using BM25."""
            self._operation_stats['searches'] += 1
            return self.bm25_adapter.search(query, limit)
        
        def get_statistics(self) -> Dict[str, Any]:
            """Get dispatcher statistics."""
            return {
                'operations': self._operation_stats,
                'total_operations': sum(self._operation_stats.values()),
                'backend': 'bm25_direct'
            }
        
        def health_check(self) -> Dict[str, Any]:
            """Check dispatcher health."""
            return {
                'status': 'operational',
                'backend': 'bm25_direct',
                'database': str(self.bm25_adapter.db_path)
            }
        
        @property
        def supported_languages(self) -> List[str]:
            """Return supported languages."""
            return ['python', 'javascript', 'typescript', 'java', 'go', 'rust', 'cpp', 'c', 'csharp']
    
    return PatchedDispatcher


def test_patched_dispatcher():
    """Test the patched dispatcher."""
    print("Testing Patched Dispatcher")
    print("=" * 60)
    
    db_path = Path.home() / ".mcp" / "indexes" / "f7b49f5d0ae0" / "main_f48abb0.db"
    
    PatchedDispatcher = patch_dispatcher_class()
    dispatcher = PatchedDispatcher(db_path)
    
    # Test symbol lookup
    print("\nTesting Symbol Lookup:")
    for symbol in ["BM25Indexer", "SQLiteStore", "EnhancedDispatcher"]:
        result = dispatcher.lookup(symbol)
        if result:
            print(f"  {symbol}: Found in {result['defined_in']} as {result['kind']}")
        else:
            print(f"  {symbol}: Not found")
    
    # Test search
    print("\nTesting Search:")
    for query in ["reranking", "centralized storage", "semantic search"]:
        results = dispatcher.search(query, limit=3)
        print(f"  '{query}': {len(results)} results")
        if results:
            print(f"    First: {results[0]['file']}")
    
    # Test statistics
    print("\nStatistics:")
    stats = dispatcher.get_statistics()
    print(f"  {stats}")


if __name__ == "__main__":
    test_patched_dispatcher()