#!/usr/bin/env python3
"""
Comprehensive MCP vs Direct retrieval test.
"""

import time
import sqlite3
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Tuple
import hashlib


class ComprehensiveMCPTest:
    def __init__(self):
        self.results = []
        self.index_path = Path.home() / ".mcp" / "indexes" / "f7b49f5d0ae0" / "main_f48abb0.db"
        
        # Test queries - 100 total
        self.test_queries = {
            'symbol': [
                # Classes (20)
                'BM25Indexer', 'SQLiteStore', 'PluginManager', 'EnhancedDispatcher',
                'PathResolver', 'TokenCounter', 'SemanticIndexer', 'IndexDiscovery',
                'DocumentPlugin', 'BasePlugin', 'RerankerFactory', 'HybridSearch',
                'MetricsCollector', 'PluginLoader', 'PluginRegistry', 'ConfigValidator',
                'CacheManager', 'ErrorHandler', 'LogManager', 'SecurityMiddleware',
                
                # Functions (10) 
                'initialize_services', 'index_repository', 'search_code', 'lookup_symbol',
                'get_statistics', 'health_check', 'load_plugins', 'create_dispatcher',
                'validate_config', 'run_benchmarks',
                
                # Other symbols (10)
                'dispatcher', 'plugin_manager', 'sqlite_store', 'logger',
                'DEBUG', 'INFO', 'ERROR', 'server', 'app', 'config'
            ],
            'content': [
                # Implementation patterns (20)
                'centralized storage', 'semantic search', 'reranking algorithm',
                'path resolution', 'index migration', 'BM25 scoring', 'vector embeddings',
                'cache implementation', 'error handling', 'logging setup',
                'plugin discovery', 'dynamic loading', 'lazy initialization',
                'connection pooling', 'rate limiting', 'authentication', 'authorization',
                'data validation', 'schema migration', 'performance optimization',
                
                # Code patterns (10)
                'try except', 'async def', 'with open', 'import from',
                'class.*init', 'def.*self', 'return None', 'raise Exception',
                'if __name__', 'for.*in.*range',
                
                # Configuration (10)
                'DATABASE_URL', 'PYTHONPATH', 'MCP_.*', 'VOYAGE_AI_API_KEY',
                'SEMANTIC_SEARCH_ENABLED', 'log.*level', 'debug.*true',
                'config.*yaml', 'env.*variable', 'settings.*json'
            ],
            'navigation': [
                # File patterns (20)
                'test_*.py', '*_test.py', '*.json', '*.yaml', '*.md',
                'plugin_*.py', '*_plugin.py', 'dispatcher*.py', 'index*.py', 'storage*.py',
                'config/*.py', 'tests/*.py', 'scripts/*.py', 'examples/*.py', 'docs/*.md',
                '__init__.py', 'setup.py', 'requirements.txt', 'Dockerfile', '.gitignore'
            ]
        }
    
    def test_mcp_search(self, query: str, query_type: str) -> Tuple[int, float, int]:
        """Test search using BM25 index (simulating MCP)."""
        start_time = time.time()
        
        try:
            conn = sqlite3.connect(str(self.index_path))
            cursor = conn.cursor()
            
            if query_type == 'navigation':
                # File path search
                pattern = query.replace('*', '%')
                cursor.execute("""
                    SELECT COUNT(*) FROM bm25_content
                    WHERE filepath LIKE ?
                """, (pattern,))
            else:
                # Content search
                cursor.execute("""
                    SELECT COUNT(*) FROM bm25_content
                    WHERE bm25_content MATCH ?
                """, (query,))
            
            count = cursor.fetchone()[0]
            
            # Get sample results for token estimation
            if query_type == 'navigation':
                cursor.execute("""
                    SELECT filepath FROM bm25_content
                    WHERE filepath LIKE ?
                    LIMIT 10
                """, (pattern,))
            else:
                cursor.execute("""
                    SELECT filepath, snippet(bm25_content, -1, '', '', '...', 20)
                    FROM bm25_content
                    WHERE bm25_content MATCH ?
                    LIMIT 10
                """, (query,))
            
            results = cursor.fetchall()
            
            # Estimate tokens (filepath + snippet)
            tokens = sum(len(str(r)) // 4 for r in results) * 2  # Rough estimate
            
            conn.close()
            
            elapsed = time.time() - start_time
            return count, elapsed, tokens
            
        except Exception as e:
            return 0, time.time() - start_time, 0
    
    def test_direct_search(self, query: str, query_type: str) -> Tuple[int, float, int]:
        """Test search using grep/find."""
        start_time = time.time()
        
        try:
            if query_type == 'navigation':
                # Use find
                cmd = ['find', '/workspaces/Code-Index-MCP', '-name', query, '-type', 'f']
            else:
                # Use grep
                cmd = ['grep', '-r', '-n', '-E', query, '/workspaces/Code-Index-MCP',
                       '--include=*.py', '--include=*.js', '--include=*.ts']
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            lines = result.stdout.strip().split('\n') if result.stdout else []
            count = len([l for l in lines if l])
            
            # Estimate tokens (full grep output + read operations)
            tokens = len(result.stdout) // 4
            if count > 0 and query_type != 'navigation':
                # Add tokens for reading context (500 per file, up to 5 files)
                tokens += min(5, count) * 500
            
            elapsed = time.time() - start_time
            return count, elapsed, tokens
            
        except subprocess.TimeoutExpired:
            return 0, 10.0, 0
        except Exception:
            return 0, time.time() - start_time, 0
    
    def run_comprehensive_test(self):
        """Run all test queries."""
        print("Comprehensive MCP vs Direct Retrieval Test")
        print("=" * 60)
        
        total_queries = sum(len(queries) for queries in self.test_queries.values())
        query_num = 0
        
        for query_type, queries in self.test_queries.items():
            print(f"\n{query_type.upper()} QUERIES")
            print("-" * 40)
            
            for query in queries:
                query_num += 1
                print(f"\n[{query_num}/{total_queries}] Query: '{query}'")
                
                # Test MCP (BM25 index)
                mcp_count, mcp_time, mcp_tokens = self.test_mcp_search(query, query_type)
                print(f"  MCP: {mcp_count} results, {mcp_time:.3f}s, ~{mcp_tokens} tokens")
                
                # Test Direct (grep/find)
                direct_count, direct_time, direct_tokens = self.test_direct_search(query, query_type)
                print(f"  Direct: {direct_count} results, {direct_time:.3f}s, ~{direct_tokens} tokens")
                
                # Calculate improvements
                if direct_time > 0:
                    speed_factor = direct_time / mcp_time if mcp_time > 0 else 0
                    print(f"  Speed: {speed_factor:.1f}x faster with MCP")
                
                if direct_tokens > 0 and mcp_tokens < direct_tokens:
                    token_reduction = (1 - mcp_tokens / direct_tokens) * 100
                    print(f"  Tokens: {token_reduction:.0f}% reduction with MCP")
                
                # Store results
                self.results.append({
                    'query': query,
                    'type': query_type,
                    'mcp': {
                        'count': mcp_count,
                        'time': mcp_time,
                        'tokens': mcp_tokens
                    },
                    'direct': {
                        'count': direct_count,
                        'time': direct_time,
                        'tokens': direct_tokens
                    }
                })
    
    def generate_report(self):
        """Generate comprehensive report."""
        print("\n" + "=" * 60)
        print("COMPREHENSIVE ANALYSIS REPORT")
        print("=" * 60)
        
        # Overall statistics
        total_mcp_time = sum(r['mcp']['time'] for r in self.results)
        total_direct_time = sum(r['direct']['time'] for r in self.results)
        total_mcp_tokens = sum(r['mcp']['tokens'] for r in self.results)
        total_direct_tokens = sum(r['direct']['tokens'] for r in self.results)
        
        print(f"\nTotal Queries: {len(self.results)}")
        print(f"Total MCP Time: {total_mcp_time:.2f}s")
        print(f"Total Direct Time: {total_direct_time:.2f}s")
        print(f"Overall Speed Improvement: {total_direct_time/total_mcp_time:.1f}x")
        print(f"Total MCP Tokens: {total_mcp_tokens:,}")
        print(f"Total Direct Tokens: {total_direct_tokens:,}")
        print(f"Overall Token Reduction: {(1-total_mcp_tokens/total_direct_tokens)*100:.0f}%")
        
        # By query type
        for query_type in self.test_queries.keys():
            type_results = [r for r in self.results if r['type'] == query_type]
            
            avg_mcp_time = sum(r['mcp']['time'] for r in type_results) / len(type_results)
            avg_direct_time = sum(r['direct']['time'] for r in type_results) / len(type_results)
            avg_mcp_tokens = sum(r['mcp']['tokens'] for r in type_results) / len(type_results)
            avg_direct_tokens = sum(r['direct']['tokens'] for r in type_results) / len(type_results)
            
            print(f"\n{query_type.upper()} QUERIES ({len(type_results)} queries):")
            print(f"  Avg MCP Time: {avg_mcp_time:.3f}s")
            print(f"  Avg Direct Time: {avg_direct_time:.3f}s")
            print(f"  Avg Speed Improvement: {avg_direct_time/avg_mcp_time:.1f}x")
            print(f"  Avg MCP Tokens: {avg_mcp_tokens:.0f}")
            print(f"  Avg Direct Tokens: {avg_direct_tokens:.0f}")
            if avg_direct_tokens > 0:
                print(f"  Avg Token Reduction: {(1-avg_mcp_tokens/avg_direct_tokens)*100:.0f}%")
        
        # Save detailed results
        report_path = Path('/workspaces/Code-Index-MCP/comprehensive_mcp_analysis.json')
        with open(report_path, 'w') as f:
            json.dump({
                'summary': {
                    'total_queries': len(self.results),
                    'total_mcp_time': total_mcp_time,
                    'total_direct_time': total_direct_time,
                    'speed_improvement': total_direct_time/total_mcp_time,
                    'total_mcp_tokens': total_mcp_tokens,
                    'total_direct_tokens': total_direct_tokens,
                    'token_reduction_percent': (1-total_mcp_tokens/total_direct_tokens)*100
                },
                'results': self.results
            }, f, indent=2)
        
        print(f"\nDetailed results saved to: {report_path}")


def main():
    tester = ComprehensiveMCPTest()
    tester.run_comprehensive_test()
    tester.generate_report()


if __name__ == "__main__":
    main()