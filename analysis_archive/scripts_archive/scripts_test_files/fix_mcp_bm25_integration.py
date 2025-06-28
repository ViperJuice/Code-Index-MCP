#!/usr/bin/env python3
"""
Fix MCP dispatcher to integrate BM25 search directly.
This creates a patched version of the dispatcher that can search BM25 indexes.
"""

import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Any, Iterable
import logging
import time
import os

logger = logging.getLogger(__name__)


class BM25DirectDispatcher:
    """Dispatcher that searches BM25 indexes directly."""
    
    def __init__(self, index_root: Optional[Path] = None):
        """Initialize the BM25 direct dispatcher.
        
        Args:
            index_root: Root directory for centralized indexes
        """
        self.index_root = index_root or (Path.home() / ".mcp" / "indexes")
        self._operation_stats = {
            "searches": 0,
            "lookups": 0,
            "total_time": 0.0
        }
        self._current_index = None
        self._detect_current_index()
    
    def _detect_current_index(self):
        """Detect the current repository's index."""
        # Check for current symlink in working directory
        cwd = Path.cwd()
        current_link = cwd / ".mcp-index" / "current"
        
        if current_link.exists() and current_link.is_symlink():
            self._current_index = current_link.resolve()
            logger.info(f"Using index from symlink: {self._current_index}")
        else:
            # Try to find index based on git remote
            try:
                import subprocess
                import hashlib
                
                result = subprocess.run(
                    ["git", "remote", "get-url", "origin"],
                    capture_output=True,
                    text=True,
                    cwd=cwd
                )
                
                if result.returncode == 0:
                    remote_url = result.stdout.strip()
                    repo_hash = hashlib.sha256(remote_url.encode()).hexdigest()[:12]
                    
                    # Look for index in centralized location
                    repo_index_dir = self.index_root / repo_hash
                    if repo_index_dir.exists():
                        # Find the most recent .db file
                        db_files = list(repo_index_dir.glob("*.db"))
                        if db_files:
                            self._current_index = max(db_files, key=lambda p: p.stat().st_mtime)
                            logger.info(f"Using index from central location: {self._current_index}")
            except Exception as e:
                logger.warning(f"Could not detect git repository: {e}")
    
    def _search_bm25(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search BM25 index directly."""
        if not self._current_index or not self._current_index.exists():
            logger.warning(f"No valid index found at {self._current_index}")
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
                
                # Extract line number from content if possible
                line_num = 1  # Default
                
                # Try to find line number in the actual file
                try:
                    file_path = Path(filepath)
                    if file_path.exists():
                        with open(file_path, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                            # Simple search for the snippet content
                            snippet_text = snippet.replace('<<', '').replace('>>', '').strip()
                            for i, line in enumerate(lines, 1):
                                if snippet_text in line:
                                    line_num = i
                                    break
                except:
                    pass
                
                results.append({
                    'file': filepath,
                    'filename': filename,
                    'line': line_num,
                    'snippet': snippet,
                    'score': abs(rank)  # FTS5 rank is negative
                })
            
            return results
            
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
            logger.error(f"Error in BM25 search for '{query}': {e}")
    
    def lookup(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Look up symbol definition."""
        start_time = time.time()
        
        try:
            # Try different patterns for symbol definitions
            patterns = [
                f'class {symbol}',
                f'def {symbol}',
                f'function {symbol}',
                f'const {symbol}',
                f'var {symbol}',
                f'let {symbol}',
                f'type {symbol}',
                f'interface {symbol}',
                f'struct {symbol}',
                f'enum {symbol}'
            ]
            
            for pattern in patterns:
                results = self._search_bm25(pattern, limit=5)
                if results:
                    # Return the best match
                    best = results[0]
                    
                    # Try to determine symbol kind from snippet
                    snippet_lower = best['snippet'].lower()
                    kind = 'symbol'
                    
                    if 'class' in snippet_lower:
                        kind = 'class'
                    elif 'def' in snippet_lower or 'function' in snippet_lower:
                        kind = 'function'
                    elif 'interface' in snippet_lower:
                        kind = 'interface'
                    elif 'struct' in snippet_lower:
                        kind = 'struct'
                    elif 'enum' in snippet_lower:
                        kind = 'enum'
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
                        '.cs': 'csharp'
                    }
                    language = lang_map.get(ext, 'unknown')
                    
                    result = {
                        'symbol': symbol,
                        'kind': kind,
                        'language': language,
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
            'backend': 'bm25_direct',
            'index_path': str(self._current_index) if self._current_index else None
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Check dispatcher health."""
        return {
            'status': 'operational' if self._current_index and self._current_index.exists() else 'degraded',
            'backend': 'bm25_direct',
            'index': str(self._current_index) if self._current_index else None,
            'index_exists': self._current_index.exists() if self._current_index else False
        }
    
    @property
    def supported_languages(self) -> List[str]:
        """Return supported languages."""
        # BM25 is language agnostic
        return ['python', 'javascript', 'typescript', 'java', 'go', 'rust', 
                'cpp', 'c', 'csharp', 'ruby', 'php', 'swift', 'kotlin', 
                'scala', 'r', 'julia', 'haskell', 'erlang', 'elixir']


def test_bm25_dispatcher():
    """Test the BM25 dispatcher."""
    print("Testing BM25 Direct Dispatcher")
    print("=" * 60)
    
    dispatcher = BM25DirectDispatcher()
    
    # Check health
    health = dispatcher.health_check()
    print(f"\nHealth Check: {health}")
    
    # Test symbol lookup
    print("\nTesting Symbol Lookup:")
    test_symbols = ["BM25Indexer", "SQLiteStore", "IndexManager", "EnhancedDispatcher"]
    
    for symbol in test_symbols:
        result = dispatcher.lookup(symbol)
        if result:
            print(f"  {symbol}: Found in {result['defined_in']}:{result['line']} as {result['kind']}")
            print(f"    Snippet: {result['signature'][:80]}...")
        else:
            print(f"  {symbol}: Not found")
    
    # Test search
    print("\n\nTesting Search:")
    test_queries = ["reranking", "centralized storage", "semantic search", "BM25"]
    
    for query in test_queries:
        results = list(dispatcher.search(query, limit=3))
        print(f"  '{query}': Found {len(results)} results")
        for i, result in enumerate(results):
            print(f"    {i+1}. {result['file']}:{result['line']} (score: {result['score']:.2f})")
            print(f"       {result['snippet'][:80]}...")
    
    # Show statistics
    print("\n\nStatistics:")
    stats = dispatcher.get_statistics()
    print(f"  {stats}")


if __name__ == "__main__":
    test_bm25_dispatcher()