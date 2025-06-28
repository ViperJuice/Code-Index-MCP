#!/usr/bin/env python3
"""Comprehensive MCP vs Native performance test with BM25 and semantic search."""

import os
import sys
import json
import time
import sqlite3
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Tuple
import statistics
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import token counter
from mcp_server.utils.token_counter import TokenCounter


class PerformanceTest:
    """Test MCP vs native search performance."""
    
    def __init__(self):
        self.token_counter = TokenCounter()
        self.results = {
            'mcp': {'bm25': [], 'semantic': []},
            'native': {'bm25': [], 'semantic': []},
            'summary': {}
        }
        
        # Test queries
        self.bm25_queries = [
            # Keyword searches
            "def __init__",
            "class Test",
            "import os",
            "return None",
            "raise Exception",
            "self.config",
            "async def",
            "from typing",
            "logger.info",
            "pytest.mark",
            # Symbol searches
            "EnhancedDispatcher",
            "SQLiteStore", 
            "SemanticIndexer",
            "PluginFactory",
            "TreeSitterWrapper",
            "DocumentChunk",
            "SearchResult",
            "BM25Indexer",
            "QdrantClient",
            "VoyageClient",
            # Code patterns
            "for item in",
            "if __name__",
            "except Exception",
            "with open",
            "json.dumps",
            "Path(__file__)",
            "os.environ",
            "sys.exit",
            "unittest.TestCase",
            "click.command",
            # File patterns
            "test_*.py",
            "*.md",
            "__init__.py",
            "requirements.txt",
            "Dockerfile"
        ]
        
        self.semantic_queries = [
            # Natural language queries
            "how to initialize a class",
            "error handling in main function",
            "database connection setup",
            "parse JSON data",
            "authentication middleware",
            "logging configuration",
            "unit test setup",
            "command line argument parsing",
            "file reading and writing",
            "async function implementation",
            # Conceptual queries
            "implement caching mechanism",
            "handle concurrent requests",
            "validate user input",
            "optimize database queries",
            "manage configuration settings",
            "create REST API endpoint",
            "implement retry logic",
            "handle file uploads",
            "process streaming data",
            "implement rate limiting",
            # Documentation queries
            "getting started guide",
            "API documentation",
            "troubleshooting errors",
            "installation instructions",
            "configuration options"
        ]
    
    def run_mcp_query(self, query: str, semantic: bool = False) -> Tuple[List[Dict], float, int]:
        """Run a query through MCP server."""
        start_time = time.time()
        
        # Prepare MCP request
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "search_code",
                "arguments": {
                    "query": query,
                    "semantic": semantic,
                    "limit": 10
                }
            }
        }
        
        # Set environment
        env = os.environ.copy()
        env['VOYAGE_AI_API_KEY'] = 'pa-Fdhj97wixjABvuP4oGuOgNTgjoPM3-ovbmg-4VktTnL'
        env['PYTHONPATH'] = str(Path(__file__).parent.parent)
        
        # Run MCP server
        cmd = [
            sys.executable,
            str(Path(__file__).parent / "cli" / "mcp_server_cli.py")
        ]
        
        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                text=True
            )
            
            # Send request and get response
            request_str = json.dumps(request)
            stdout, stderr = proc.communicate(input=request_str, timeout=30)
            
            elapsed_time = time.time() - start_time
            
            # Count tokens
            tokens = self.token_counter.count_tokens(request_str + stdout)
            
            # Parse response
            results = []
            if stdout:
                try:
                    lines = stdout.strip().split('\n')
                    for line in lines:
                        if line.strip().startswith('{'):
                            response = json.loads(line)
                            if 'result' in response:
                                result_data = response['result']
                                if isinstance(result_data, list) and result_data:
                                    content = result_data[0].get('content', {})
                                    if isinstance(content, str):
                                        try:
                                            content = json.loads(content)
                                        except:
                                            pass
                                    
                                    # Extract results
                                    if isinstance(content, list):
                                        results = content[:5]  # Take top 5
                                    elif isinstance(content, dict) and 'results' in content:
                                        results = content['results'][:5]
                                break
                except Exception as e:
                    print(f"Error parsing MCP response: {e}")
            
            return results, elapsed_time, tokens
            
        except subprocess.TimeoutExpired:
            return [], 30.0, 0
        except Exception as e:
            print(f"MCP error: {e}")
            return [], 0.0, 0
    
    def run_native_bm25_query(self, db_path: str, query: str) -> Tuple[List[Dict], float, int]:
        """Run BM25 query directly on database."""
        start_time = time.time()
        results = []
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # BM25 search query
            sql_query = """
                SELECT 
                    filepath,
                    snippet(bm25_content, -1, '<<', '>>', '...', 20) as snippet,
                    rank
                FROM bm25_content
                WHERE bm25_content MATCH ?
                ORDER BY rank
                LIMIT 5
            """
            
            cursor.execute(sql_query, (query,))
            
            for row in cursor.fetchall():
                filepath, snippet, rank = row
                results.append({
                    'file': filepath,
                    'snippet': snippet,
                    'score': abs(rank)
                })
            
            conn.close()
            elapsed_time = time.time() - start_time
            
            # Count tokens (query + results)
            result_str = json.dumps(results)
            tokens = self.token_counter.count_tokens(query + result_str)
            
            return results, elapsed_time, tokens
            
        except Exception as e:
            print(f"Native BM25 error: {e}")
            return [], 0.0, 0
    
    def run_native_semantic_query(self, query: str) -> Tuple[List[Dict], float, int]:
        """Run semantic query using direct Qdrant access."""
        start_time = time.time()
        
        try:
            # Import here to avoid initialization issues
            from mcp_server.utils.semantic_indexer import SemanticIndexer
            
            # Initialize semantic indexer
            qdrant_path = Path(".indexes/qdrant/main.qdrant")
            semantic_indexer = SemanticIndexer(
                qdrant_path=str(qdrant_path),
                collection="code-embeddings"
            )
            
            # Search
            results = semantic_indexer.search(query=query, limit=5)
            
            elapsed_time = time.time() - start_time
            
            # Count tokens
            result_str = json.dumps(results)
            tokens = self.token_counter.count_tokens(query + result_str)
            
            return results, elapsed_time, tokens
            
        except Exception as e:
            print(f"Native semantic error: {e}")
            return [], 0.0, 0
    
    def run_test_suite(self, repo_name: str, db_path: str):
        """Run complete test suite for a repository."""
        print(f"\n{'='*60}")
        print(f"Testing repository: {repo_name}")
        print(f"Database: {db_path}")
        print(f"{'='*60}")
        
        # Test BM25 queries
        print("\n### BM25 Queries (25 queries)")
        for i, query in enumerate(self.bm25_queries[:25], 1):
            print(f"\n[{i}/25] Query: '{query}'")
            
            # MCP test
            mcp_results, mcp_time, mcp_tokens = self.run_mcp_query(query, semantic=False)
            print(f"  MCP: {len(mcp_results)} results, {mcp_time:.3f}s, {mcp_tokens} tokens")
            
            # Native test
            native_results, native_time, native_tokens = self.run_native_bm25_query(db_path, query)
            print(f"  Native: {len(native_results)} results, {native_time:.3f}s, {native_tokens} tokens")
            
            # Store results
            self.results['mcp']['bm25'].append({
                'query': query,
                'results': len(mcp_results),
                'time': mcp_time,
                'tokens': mcp_tokens
            })
            
            self.results['native']['bm25'].append({
                'query': query,
                'results': len(native_results),
                'time': native_time,
                'tokens': native_tokens
            })
        
        # Test semantic queries
        print("\n### Semantic Queries (25 queries)")
        for i, query in enumerate(self.semantic_queries[:25], 1):
            print(f"\n[{i}/25] Query: '{query}'")
            
            # MCP test
            mcp_results, mcp_time, mcp_tokens = self.run_mcp_query(query, semantic=True)
            print(f"  MCP: {len(mcp_results)} results, {mcp_time:.3f}s, {mcp_tokens} tokens")
            
            # Native test
            native_results, native_time, native_tokens = self.run_native_semantic_query(query)
            print(f"  Native: {len(native_results)} results, {native_time:.3f}s, {native_tokens} tokens")
            
            # Store results
            self.results['mcp']['semantic'].append({
                'query': query,
                'results': len(mcp_results),
                'time': mcp_time,
                'tokens': mcp_tokens
            })
            
            self.results['native']['semantic'].append({
                'query': query,
                'results': len(native_results),
                'time': native_time,
                'tokens': native_tokens
            })
    
    def generate_summary(self):
        """Generate performance summary."""
        summary = {}
        
        for method in ['mcp', 'native']:
            for search_type in ['bm25', 'semantic']:
                data = self.results[method][search_type]
                if data:
                    times = [d['time'] for d in data]
                    tokens = [d['tokens'] for d in data]
                    results = [d['results'] for d in data]
                    
                    key = f"{method}_{search_type}"
                    summary[key] = {
                        'total_queries': len(data),
                        'avg_time': statistics.mean(times),
                        'median_time': statistics.median(times),
                        'total_tokens': sum(tokens),
                        'avg_tokens': statistics.mean(tokens),
                        'avg_results': statistics.mean(results),
                        'queries_with_results': sum(1 for r in results if r > 0)
                    }
        
        # Calculate comparisons
        if 'mcp_bm25' in summary and 'native_bm25' in summary:
            summary['bm25_comparison'] = {
                'time_ratio': summary['native_bm25']['avg_time'] / summary['mcp_bm25']['avg_time'] if summary['mcp_bm25']['avg_time'] > 0 else 0,
                'token_ratio': summary['mcp_bm25']['avg_tokens'] / summary['native_bm25']['avg_tokens'] if summary['native_bm25']['avg_tokens'] > 0 else 0,
                'token_overhead': summary['mcp_bm25']['total_tokens'] - summary['native_bm25']['total_tokens']
            }
        
        if 'mcp_semantic' in summary and 'native_semantic' in summary:
            summary['semantic_comparison'] = {
                'time_ratio': summary['native_semantic']['avg_time'] / summary['mcp_semantic']['avg_time'] if summary['mcp_semantic']['avg_time'] > 0 else 0,
                'token_ratio': summary['mcp_semantic']['avg_tokens'] / summary['native_semantic']['avg_tokens'] if summary['native_semantic']['avg_tokens'] > 0 else 0,
                'token_overhead': summary['mcp_semantic']['total_tokens'] - summary['native_semantic']['total_tokens']
            }
        
        self.results['summary'] = summary
        
        # Print summary
        print("\n" + "="*60)
        print("PERFORMANCE SUMMARY")
        print("="*60)
        
        print("\n### BM25 Search Performance")
        if 'mcp_bm25' in summary:
            print(f"MCP:    {summary['mcp_bm25']['avg_time']:.3f}s avg, {summary['mcp_bm25']['total_tokens']:,} tokens total")
        if 'native_bm25' in summary:
            print(f"Native: {summary['native_bm25']['avg_time']:.3f}s avg, {summary['native_bm25']['total_tokens']:,} tokens total")
        if 'bm25_comparison' in summary:
            print(f"Speed:  {summary['bm25_comparison']['time_ratio']:.1f}x faster native")
            print(f"Tokens: {summary['bm25_comparison']['token_overhead']:,} extra tokens for MCP")
        
        print("\n### Semantic Search Performance")
        if 'mcp_semantic' in summary:
            print(f"MCP:    {summary['mcp_semantic']['avg_time']:.3f}s avg, {summary['mcp_semantic']['total_tokens']:,} tokens total")
        if 'native_semantic' in summary:
            print(f"Native: {summary['native_semantic']['avg_time']:.3f}s avg, {summary['native_semantic']['total_tokens']:,} tokens total")
        if 'semantic_comparison' in summary:
            print(f"Speed:  {summary['semantic_comparison']['time_ratio']:.1f}x faster native")
            print(f"Tokens: {summary['semantic_comparison']['token_overhead']:,} extra tokens for MCP")
    
    def save_results(self):
        """Save results to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"mcp_performance_results_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\nResults saved to: {filename}")


def main():
    """Run comprehensive performance test."""
    # Set API key
    os.environ['VOYAGE_AI_API_KEY'] = 'pa-Fdhj97wixjABvuP4oGuOgNTgjoPM3-ovbmg-4VktTnL'
    
    # Initialize test
    test = PerformanceTest()
    
    # Find available indexes
    indexes_dir = Path(".indexes")
    test_repos = []
    
    for item in indexes_dir.iterdir():
        if item.is_dir() and item.name != "qdrant":
            db_path = item / "current.db"
            if db_path.exists():
                # Check if it has content
                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM bm25_content")
                    count = cursor.fetchone()[0]
                    conn.close()
                    
                    if count > 0:
                        test_repos.append((item.name, str(db_path)))
                except:
                    pass
    
    print(f"Found {len(test_repos)} indexed repositories")
    
    # Test first repository with content
    if test_repos:
        repo_name, db_path = test_repos[0]
        test.run_test_suite(repo_name, db_path)
        test.generate_summary()
        test.save_results()
    else:
        print("No indexed repositories found with content!")


if __name__ == "__main__":
    main()