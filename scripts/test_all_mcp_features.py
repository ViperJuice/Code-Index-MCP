#!/usr/bin/env python3
"""
Test all MCP features individually before comprehensive testing.
Tests SQL, Semantic, Hybrid, and Symbol search capabilities.
"""

import asyncio
import json
import time
import sqlite3
import subprocess
import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MCPFeatureTester:
    """Test all MCP features to ensure they work before comprehensive testing."""
    
    def __init__(self):
        self.workspace = Path('/workspaces/Code-Index-MCP')
        self.db_path = self._find_database()
        self.results = {}
        self.issues = []
        
    def _find_database(self) -> Optional[Path]:
        """Find the MCP database."""
        indexes_dir = self.workspace / '.indexes'
        if indexes_dir.exists():
            for repo_dir in indexes_dir.iterdir():
                db_path = repo_dir / 'code_index.db'
                if db_path.exists():
                    return db_path
        return None
    
    async def test_mcp_sql(self) -> Dict[str, Any]:
        """Test MCP SQL/BM25 search."""
        logger.info("Testing MCP SQL/BM25 search...")
        
        test_queries = [
            "EnhancedDispatcher",
            "async def",
            "error handling",
            "TODO",
            "import json"
        ]
        
        results = []
        for query in test_queries:
            start_time = time.perf_counter()
            
            try:
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT 
                        filepath,
                        snippet(bm25_content, -1, '<<', '>>', '...', 20) as snippet,
                        rank
                    FROM bm25_content
                    WHERE bm25_content MATCH ?
                    ORDER BY rank
                    LIMIT 5
                """, (query,))
                
                query_results = cursor.fetchall()
                duration_ms = (time.perf_counter() - start_time) * 1000
                
                results.append({
                    'query': query,
                    'duration_ms': duration_ms,
                    'result_count': len(query_results),
                    'success': True,
                    'sample': query_results[0] if query_results else None
                })
                
                conn.close()
                
            except Exception as e:
                results.append({
                    'query': query,
                    'duration_ms': (time.perf_counter() - start_time) * 1000,
                    'success': False,
                    'error': str(e)
                })
                self.issues.append(f"SQL Search failed for '{query}': {e}")
        
        return {
            'method': 'mcp_sql',
            'working': all(r['success'] for r in results),
            'avg_duration_ms': sum(r['duration_ms'] for r in results) / len(results),
            'test_results': results
        }
    
    async def test_mcp_semantic(self) -> Dict[str, Any]:
        """Test MCP semantic search using the MCP server."""
        logger.info("Testing MCP semantic search...")
        
        test_queries = [
            "error handling logic",
            "authentication implementation",
            "database connection code",
            "configuration management",
            "logging functionality"
        ]
        
        results = []
        
        # Test if semantic search is available
        try:
            # First check if Voyage AI is configured
            voyage_key = os.getenv("VOYAGE_AI_API_KEY") or os.getenv("VOYAGE_API_KEY")
            if not voyage_key:
                self.issues.append("Semantic search unavailable: No Voyage AI API key")
                return {
                    'method': 'mcp_semantic',
                    'working': False,
                    'error': 'No Voyage AI API key configured',
                    'test_results': []
                }
            
            # Import and test semantic indexer
            from mcp_server.utils.semantic_indexer import SemanticIndexer
            
            # Try to create a test semantic indexer
            try:
                test_indexer = SemanticIndexer(
                    collection="test-semantic",
                    qdrant_path=":memory:"
                )
                logger.info("Semantic indexer created successfully")
            except Exception as e:
                self.issues.append(f"Semantic indexer creation failed: {e}")
                return {
                    'method': 'mcp_semantic',
                    'working': False,
                    'error': f'Semantic indexer initialization failed: {e}',
                    'test_results': []
                }
            
            # Now test semantic search through dispatcher
            from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
            
            dispatcher = EnhancedDispatcher(
                sqlite_store=None,
                semantic_search_enabled=True
            )
            
            for query in test_queries:
                start_time = time.perf_counter()
                
                try:
                    # Use dispatcher search with semantic=True
                    search_results = list(dispatcher.search(query, semantic=True, limit=5))
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    
                    results.append({
                        'query': query,
                        'duration_ms': duration_ms,
                        'result_count': len(search_results),
                        'success': True,
                        'sample': search_results[0] if search_results else None
                    })
                    
                except Exception as e:
                    results.append({
                        'query': query,
                        'duration_ms': (time.perf_counter() - start_time) * 1000,
                        'success': False,
                        'error': str(e)
                    })
                    self.issues.append(f"Semantic search failed for '{query}': {e}")
            
        except ImportError as e:
            self.issues.append(f"Semantic search imports failed: {e}")
            return {
                'method': 'mcp_semantic',
                'working': False,
                'error': f'Import error: {e}',
                'test_results': []
            }
        except Exception as e:
            self.issues.append(f"Semantic search setup failed: {e}")
            return {
                'method': 'mcp_semantic',
                'working': False,
                'error': f'Setup error: {e}',
                'test_results': []
            }
        
        return {
            'method': 'mcp_semantic',
            'working': all(r['success'] for r in results) if results else False,
            'avg_duration_ms': sum(r['duration_ms'] for r in results) / len(results) if results else 0,
            'test_results': results
        }
    
    async def test_mcp_hybrid(self) -> Dict[str, Any]:
        """Test MCP hybrid search combining BM25 and semantic."""
        logger.info("Testing MCP hybrid search...")
        
        test_queries = [
            "async error handling",
            "class authentication",
            "database connection pool",
            "import configuration",
            "test logging"
        ]
        
        results = []
        
        try:
            from mcp_server.indexer.hybrid_search import HybridSearch, HybridSearchConfig
            from mcp_server.indexer.bm25_indexer import BM25Indexer
            from mcp_server.utils.semantic_indexer import SemanticIndexer
            from mcp_server.storage.sqlite_store import SQLiteStore
            
            # Create components for hybrid search
            if self.db_path:
                store = SQLiteStore(str(self.db_path))
                bm25_indexer = BM25Indexer(store)
                
                # Try to create semantic indexer
                semantic_indexer = None
                try:
                    semantic_indexer = SemanticIndexer(
                        collection="test-hybrid",
                        qdrant_path=":memory:"
                    )
                except:
                    logger.warning("Semantic indexer not available for hybrid search")
                
                # Create hybrid search
                config = HybridSearchConfig(
                    bm25_weight=0.5,
                    semantic_weight=0.3 if semantic_indexer else 0.0,
                    fuzzy_weight=0.2,
                    enable_semantic=semantic_indexer is not None
                )
                
                hybrid_search = HybridSearch(
                    storage=store,
                    bm25_indexer=bm25_indexer,
                    semantic_indexer=semantic_indexer,
                    config=config
                )
                
                for query in test_queries:
                    start_time = time.perf_counter()
                    
                    try:
                        # Run hybrid search
                        search_results = await hybrid_search.search(query, limit=5)
                        duration_ms = (time.perf_counter() - start_time) * 1000
                        
                        results.append({
                            'query': query,
                            'duration_ms': duration_ms,
                            'result_count': len(search_results),
                            'success': True,
                            'has_bm25': any(r.source == 'bm25' for r in search_results),
                            'has_semantic': any(r.source == 'semantic' for r in search_results)
                        })
                        
                    except Exception as e:
                        results.append({
                            'query': query,
                            'duration_ms': (time.perf_counter() - start_time) * 1000,
                            'success': False,
                            'error': str(e)
                        })
                        self.issues.append(f"Hybrid search failed for '{query}': {e}")
            
        except ImportError as e:
            self.issues.append(f"Hybrid search imports failed: {e}")
            return {
                'method': 'mcp_hybrid',
                'working': False,
                'error': f'Import error: {e}',
                'test_results': []
            }
        except Exception as e:
            self.issues.append(f"Hybrid search setup failed: {e}")
            return {
                'method': 'mcp_hybrid',
                'working': False,
                'error': f'Setup error: {e}',
                'test_results': []
            }
        
        return {
            'method': 'mcp_hybrid',
            'working': all(r['success'] for r in results) if results else False,
            'avg_duration_ms': sum(r['duration_ms'] for r in results) / len(results) if results else 0,
            'test_results': results
        }
    
    async def test_mcp_symbol(self) -> Dict[str, Any]:
        """Test MCP symbol lookup."""
        logger.info("Testing MCP symbol lookup...")
        
        test_symbols = [
            "EnhancedDispatcher",
            "SQLiteStore",
            "BM25Indexer",
            "PathUtils",
            "search"
        ]
        
        results = []
        
        # First check if symbols table exists
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Check if symbols table exists
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='symbols'
            """)
            
            if not cursor.fetchone():
                conn.close()
                self.issues.append("Symbol lookup unavailable: 'symbols' table does not exist")
                return {
                    'method': 'mcp_symbol',
                    'working': False,
                    'error': "Symbols table does not exist in database",
                    'test_results': []
                }
            
            # Test symbol lookups
            for symbol in test_symbols:
                start_time = time.perf_counter()
                
                try:
                    cursor.execute("""
                        SELECT name, type, file_path, line_number, signature
                        FROM symbols
                        WHERE name = ?
                        LIMIT 5
                    """, (symbol,))
                    
                    symbol_results = cursor.fetchall()
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    
                    results.append({
                        'symbol': symbol,
                        'duration_ms': duration_ms,
                        'result_count': len(symbol_results),
                        'success': True,
                        'sample': symbol_results[0] if symbol_results else None
                    })
                    
                except Exception as e:
                    results.append({
                        'symbol': symbol,
                        'duration_ms': (time.perf_counter() - start_time) * 1000,
                        'success': False,
                        'error': str(e)
                    })
                    self.issues.append(f"Symbol lookup failed for '{symbol}': {e}")
            
            conn.close()
            
        except Exception as e:
            self.issues.append(f"Symbol lookup setup failed: {e}")
            return {
                'method': 'mcp_symbol',
                'working': False,
                'error': f'Database error: {e}',
                'test_results': []
            }
        
        return {
            'method': 'mcp_symbol',
            'working': all(r['success'] for r in results) if results else False,
            'avg_duration_ms': sum(r['duration_ms'] for r in results) / len(results) if results else 0,
            'test_results': results
        }
    
    async def test_multi_repo(self) -> Dict[str, Any]:
        """Test multi-repository support."""
        logger.info("Testing multi-repository support...")
        
        results = []
        
        try:
            from mcp_server.storage.multi_repo_manager import MultiRepositoryManager
            
            # Check if test repos exist
            test_repo_base = self.workspace / 'test_repos'
            if not test_repo_base.exists():
                self.issues.append("Multi-repo testing unavailable: test_repos directory not found")
                return {
                    'method': 'multi_repo',
                    'working': False,
                    'error': 'test_repos directory not found',
                    'test_results': []
                }
            
            # Find available test repos
            test_repos = []
            for category in test_repo_base.iterdir():
                if category.is_dir():
                    for lang in category.iterdir():
                        if lang.is_dir():
                            for repo in lang.iterdir():
                                if repo.is_dir() and len(test_repos) < 3:
                                    test_repos.append(repo)
            
            if not test_repos:
                self.issues.append("No test repositories found")
                return {
                    'method': 'multi_repo',
                    'working': False,
                    'error': 'No test repositories found',
                    'test_results': []
                }
            
            logger.info(f"Found {len(test_repos)} test repositories")
            
            # Test each repo
            for repo in test_repos:
                start_time = time.perf_counter()
                
                try:
                    # Check if repo has index
                    repo_name = f"{repo.parent.name}/{repo.name}"
                    results.append({
                        'repository': repo_name,
                        'duration_ms': (time.perf_counter() - start_time) * 1000,
                        'success': True,
                        'path': str(repo)
                    })
                    
                except Exception as e:
                    results.append({
                        'repository': str(repo),
                        'duration_ms': (time.perf_counter() - start_time) * 1000,
                        'success': False,
                        'error': str(e)
                    })
            
        except ImportError as e:
            self.issues.append(f"Multi-repo imports failed: {e}")
            return {
                'method': 'multi_repo',
                'working': False,
                'error': f'Import error: {e}',
                'test_results': []
            }
        
        return {
            'method': 'multi_repo',
            'working': all(r['success'] for r in results) if results else False,
            'repositories_found': len(results),
            'test_results': results
        }
    
    async def run_all_tests(self):
        """Run all tests in parallel."""
        logger.info("Starting parallel MCP feature tests...")
        
        # Create tasks for all test methods
        tasks = [
            self.test_mcp_sql(),
            self.test_mcp_semantic(),
            self.test_mcp_hybrid(),
            self.test_mcp_symbol(),
            self.test_multi_repo()
        ]
        
        # Run all tests in parallel
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Process results
        all_results = {}
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                method_name = ['sql', 'semantic', 'hybrid', 'symbol', 'multi_repo'][i]
                all_results[f'mcp_{method_name}'] = {
                    'method': f'mcp_{method_name}',
                    'working': False,
                    'error': str(result)
                }
                self.issues.append(f"{method_name} test failed with exception: {result}")
            else:
                all_results[result['method']] = result
        
        # Generate summary
        summary = {
            'timestamp': datetime.now().isoformat(),
            'total_time_seconds': total_time,
            'database_path': str(self.db_path) if self.db_path else None,
            'all_tests_passed': all(r.get('working', False) for r in all_results.values()),
            'working_features': [m for m, r in all_results.items() if r.get('working', False)],
            'broken_features': [m for m, r in all_results.items() if not r.get('working', False)],
            'issues_found': self.issues,
            'detailed_results': all_results
        }
        
        # Save results
        output_dir = self.workspace / 'mcp_test_results'
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        with open(output_dir / f'feature_test_{timestamp}.json', 'w') as f:
            json.dump(summary, f, indent=2)
        
        # Print summary
        print("\n" + "="*60)
        print("MCP FEATURE TEST SUMMARY")
        print("="*60)
        print(f"Total Time: {total_time:.2f} seconds")
        print(f"Database: {self.db_path}")
        print(f"\nWorking Features: {', '.join(summary['working_features']) or 'None'}")
        print(f"Broken Features: {', '.join(summary['broken_features']) or 'None'}")
        
        if self.issues:
            print(f"\nIssues Found ({len(self.issues)}):")
            for issue in self.issues[:5]:  # Show first 5 issues
                print(f"  - {issue}")
            if len(self.issues) > 5:
                print(f"  ... and {len(self.issues) - 5} more")
        
        print(f"\nDetailed results saved to: mcp_test_results/feature_test_{timestamp}.json")
        print("="*60)
        
        return summary


async def main():
    """Main entry point."""
    tester = MCPFeatureTester()
    
    if not tester.db_path:
        logger.error("No MCP database found. Please run indexing first.")
        return
    
    summary = await tester.run_all_tests()
    
    # Return exit code based on test results
    if summary['all_tests_passed']:
        logger.info("All MCP features are working correctly!")
        sys.exit(0)
    else:
        logger.warning(f"Some features need fixing: {', '.join(summary['broken_features'])}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())