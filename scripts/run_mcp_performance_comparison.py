#!/usr/bin/env python3
"""
Run actual performance comparison between MCP and direct retrieval methods.
"""

import time
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Tuple
import os
import sys
from mcp_server.core.path_utils import PathUtils

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class PerformanceComparison:
    """Compare MCP vs direct retrieval performance."""
    
    def __init__(self):
        self.test_queries = {
            'symbol_searches': [
                ('Find IndexManager class definition', 'IndexManager', 'class IndexManager'),
                ('Find BM25Indexer class', 'BM25Indexer', 'class BM25Indexer'),
                ('Find PluginManager class', 'PluginManager', 'class PluginManager'),
                ('Find SQLiteStore class', 'SQLiteStore', 'class SQLiteStore'),
                ('Find TokenCounter class', 'TokenCounter', 'class TokenCounter'),
                ('Find EnhancedDispatcher', 'EnhancedDispatcher', 'class EnhancedDispatcher'),
                ('Find DocumentPlugin interface', 'DocumentPlugin', 'DocumentPlugin'),
                ('Find SearchResult type', 'SearchResult', 'SearchResult'),
                ('Find PathResolver class', 'PathResolver', 'class PathResolver'),
                ('Find MCP server main', 'main', 'def main'),
            ],
            'content_searches': [
                ('Find centralized storage implementation', 'centralized storage', 'centralized.*storage'),
                ('Find semantic search code', 'semantic search', 'semantic.*search'),
                ('Find reranking implementation', 'reranking', 'rerank'),
                ('Find path resolution logic', 'path resolution', 'path.*resolv'),
                ('Find index migration code', 'index migration', 'migration.*index'),
                ('Find BM25 scoring', 'BM25 scoring', 'bm25.*score'),
                ('Find vector embeddings', 'vector embeddings', 'embedding'),
                ('Find cache implementation', 'cache implementation', 'cache'),
                ('Find error handling', 'error handling', 'try.*except|catch'),
                ('Find logging setup', 'logging configuration', 'logging.config'),
            ],
            'navigation_searches': [
                ('Find Python plugin files', 'python plugin files', '*/python_plugin/*.py'),
                ('Find test files', 'test files', 'test_*.py'),
                ('Find configuration files', 'config files', '*.json'),
                ('Find documentation', 'documentation files', '*.md'),
                ('Find example scripts', 'examples', '*/examples/*.py'),
                ('Find TypeScript plugin', 'typescript plugin', '*/typescript_plugin/*'),
                ('Find storage modules', 'storage modules', '*/storage/*.py'),
                ('Find CLI scripts', 'CLI tools', '*/cli/*.py'),
                ('Find benchmark scripts', 'benchmarks', '*/benchmarks/*.py'),
                ('Find Docker files', 'docker config', 'Dockerfile*'),
            ]
        }
        
        self.results = {
            'mcp': [],
            'direct': []
        }
    
    def run_mcp_search(self, query_type: str, symbol_or_query: str) -> Tuple[int, float, int]:
        """Run search using MCP tools and measure performance."""
        start_time = time.time()
        
        try:
            if query_type == 'symbol_searches':
                # Use symbol_lookup
                cmd = [
                    'python', '-c',
                    f'''
import asyncio
import sys
sys.path.insert(0, "PathUtils.get_workspace_root()")
from scripts.test_mcp_direct import test_symbol_lookup

async def run():
    return await test_symbol_lookup("{symbol_or_query}")

result = asyncio.run(run())
print(json.dumps(result))
'''
                ]
            else:
                # Use search_code
                cmd = [
                    'python', '-c',
                    f'''
import asyncio
import sys
sys.path.insert(0, "PathUtils.get_workspace_root()")
from scripts.test_mcp_direct import test_search_code

async def run():
    return await test_search_code("{symbol_or_query}")

result = asyncio.run(run())
print(json.dumps(result))
'''
                ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            elapsed_time = time.time() - start_time
            
            if result.returncode == 0 and result.stdout:
                try:
                    data = json.loads(result.stdout)
                    num_results = len(data.get('results', []))
                    # Estimate tokens (rough approximation)
                    tokens = len(json.dumps(data)) // 4
                    return num_results, elapsed_time, tokens
                except:
                    pass
            
            return 0, elapsed_time, 0
            
        except subprocess.TimeoutExpired:
            return 0, 30.0, 0
        except Exception as e:
            print(f"MCP search error: {e}")
            return 0, time.time() - start_time, 0
    
    def run_direct_search(self, query_type: str, pattern: str) -> Tuple[int, float, int]:
        """Run search using grep/find and measure performance."""
        start_time = time.time()
        total_tokens = 0
        
        try:
            if query_type == 'navigation_searches':
                # Use find command
                cmd = ['find', 'PathUtils.get_workspace_root()', '-name', pattern, '-type', 'f']
            else:
                # Use grep command
                cmd = ['grep', '-r', '-n', '-E', pattern, 'PathUtils.get_workspace_root()', 
                       '--include=*.py', '--include=*.js', '--include=*.ts']
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            elapsed_time = time.time() - start_time
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n') if result.stdout else []
                num_results = len(lines)
                
                # Simulate Read operations for first 5 results
                for i, line in enumerate(lines[:5]):
                    if ':' in line:
                        # Extract file path
                        file_path = line.split(':')[0]
                        # Estimate tokens for reading context (500 tokens per file read)
                        total_tokens += 500
                
                return num_results, elapsed_time, total_tokens
            
            return 0, elapsed_time, 0
            
        except subprocess.TimeoutExpired:
            return 0, 30.0, 0
        except Exception as e:
            print(f"Direct search error: {e}")
            return 0, time.time() - start_time, 0
    
    def run_comparison(self):
        """Run full comparison test."""
        print("Starting MCP vs Direct Retrieval Performance Comparison")
        print("=" * 60)
        
        for query_type, queries in self.test_queries.items():
            print(f"\n{query_type.replace('_', ' ').title()}")
            print("-" * 40)
            
            for description, mcp_query, grep_pattern in queries:
                print(f"\n{description}:")
                
                # Run MCP search
                mcp_results, mcp_time, mcp_tokens = self.run_mcp_search(query_type, mcp_query)
                print(f"  MCP: {mcp_results} results in {mcp_time:.2f}s (~{mcp_tokens} tokens)")
                
                # Run direct search
                direct_results, direct_time, direct_tokens = self.run_direct_search(query_type, grep_pattern)
                print(f"  Direct: {direct_results} results in {direct_time:.2f}s (~{direct_tokens} tokens)")
                
                # Calculate improvements
                if direct_time > 0:
                    speed_improvement = direct_time / mcp_time if mcp_time > 0 else 0
                    print(f"  Speed: {speed_improvement:.1f}x faster with MCP")
                
                if direct_tokens > 0:
                    token_reduction = (1 - mcp_tokens / direct_tokens) * 100 if mcp_tokens < direct_tokens else 0
                    print(f"  Tokens: {token_reduction:.0f}% reduction with MCP")
                
                # Store results
                self.results['mcp'].append({
                    'query': description,
                    'type': query_type,
                    'results': mcp_results,
                    'time': mcp_time,
                    'tokens': mcp_tokens
                })
                
                self.results['direct'].append({
                    'query': description,
                    'type': query_type,
                    'results': direct_results,
                    'time': direct_time,
                    'tokens': direct_tokens
                })
    
    def generate_summary(self):
        """Generate performance summary."""
        print("\n" + "=" * 60)
        print("PERFORMANCE SUMMARY")
        print("=" * 60)
        
        # Calculate averages by query type
        for query_type in self.test_queries.keys():
            mcp_data = [r for r in self.results['mcp'] if r['type'] == query_type]
            direct_data = [r for r in self.results['direct'] if r['type'] == query_type]
            
            if mcp_data and direct_data:
                avg_mcp_time = sum(r['time'] for r in mcp_data) / len(mcp_data)
                avg_direct_time = sum(r['time'] for r in direct_data) / len(direct_data)
                avg_mcp_tokens = sum(r['tokens'] for r in mcp_data) / len(mcp_data)
                avg_direct_tokens = sum(r['tokens'] for r in direct_data) / len(direct_data)
                
                print(f"\n{query_type.replace('_', ' ').title()}:")
                print(f"  Average MCP time: {avg_mcp_time:.2f}s")
                print(f"  Average Direct time: {avg_direct_time:.2f}s")
                print(f"  Speed improvement: {avg_direct_time/avg_mcp_time:.1f}x")
                print(f"  Average MCP tokens: {avg_mcp_tokens:.0f}")
                print(f"  Average Direct tokens: {avg_direct_tokens:.0f}")
                if avg_direct_tokens > 0:
                    print(f"  Token reduction: {(1-avg_mcp_tokens/avg_direct_tokens)*100:.0f}%")
        
        # Save detailed results
        output_file = Path('PathUtils.get_workspace_root()/mcp_performance_comparison.json')
        with open(output_file, 'w') as f:
            json.dump({
                'results': self.results,
                'summary': self._calculate_overall_summary()
            }, f, indent=2)
        
        print(f"\nDetailed results saved to: {output_file}")
    
    def _calculate_overall_summary(self) -> Dict[str, Any]:
        """Calculate overall performance summary."""
        all_mcp = self.results['mcp']
        all_direct = self.results['direct']
        
        return {
            'total_queries': len(all_mcp),
            'avg_mcp_time': sum(r['time'] for r in all_mcp) / len(all_mcp),
            'avg_direct_time': sum(r['time'] for r in all_direct) / len(all_direct),
            'avg_mcp_tokens': sum(r['tokens'] for r in all_mcp) / len(all_mcp),
            'avg_direct_tokens': sum(r['tokens'] for r in all_direct) / len(all_direct),
            'mcp_faster_count': sum(1 for m, d in zip(all_mcp, all_direct) if m['time'] < d['time']),
            'mcp_fewer_tokens_count': sum(1 for m, d in zip(all_mcp, all_direct) if m['tokens'] < d['tokens'])
        }


def main():
    """Main function."""
    # First create the test helper script
    test_helper = '''#!/usr/bin/env python3
import asyncio
import sys
import json
sys.path.insert(0, "PathUtils.get_workspace_root()")

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_symbol_lookup(symbol: str):
    """Test MCP symbol lookup."""
    try:
        server_params = StdioServerParameters(
            command="python",
            args=["-m", "mcp_server"],
            env={"PYTHONPATH": "PathUtils.get_workspace_root()"}
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                result = await session.call_tool(
                    "mcp__code-index-mcp__symbol_lookup",
                    arguments={"symbol": symbol}
                )
                
                return {"results": result.content if hasattr(result, 'content') else []}
    except Exception as e:
        return {"error": str(e), "results": []}

async def test_search_code(query: str):
    """Test MCP code search."""
    try:
        server_params = StdioServerParameters(
            command="python",
            args=["-m", "mcp_server"],
            env={"PYTHONPATH": "PathUtils.get_workspace_root()"}
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                result = await session.call_tool(
                    "mcp__code-index-mcp__search_code",
                    arguments={"query": query, "limit": 10}
                )
                
                return {"results": result.content if hasattr(result, 'content') else []}
    except Exception as e:
        return {"error": str(e), "results": []}
'''
    
    # Write test helper
    with open('PathUtils.get_workspace_root()/scripts/test_mcp_direct.py', 'w') as f:
        f.write(test_helper)
    
    # Run comparison
    comparison = PerformanceComparison()
    comparison.run_comparison()
    comparison.generate_summary()


if __name__ == "__main__":
    main()