#!/usr/bin/env python3
"""
Real MCP vs Native Test Executor
Executes actual MCP and native tool calls to gather real performance data
"""

import json
import time
import sqlite3
import subprocess
import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field, asdict
import logging
import uuid

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server.core.path_utils import PathUtils

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class RealToolCall:
    """Record of an actual tool call"""
    tool_name: str
    arguments: Dict[str, Any]
    start_time: float
    end_time: float
    response_size: int
    success: bool
    error: Optional[str] = None


@dataclass
class RealTestExecution:
    """Real test execution data"""
    test_id: str
    prompt: str
    method: str
    repository: str
    
    # Timing
    start_time: float
    end_time: float
    total_duration_ms: float
    
    # Tool calls
    tool_calls: List[RealToolCall] = field(default_factory=list)
    
    # Results
    results_found: int = 0
    files_accessed: int = 0
    symbols_found: int = 0
    
    # Response characteristics
    has_line_numbers: bool = False
    has_snippets: bool = False
    has_file_paths: bool = False
    
    # Raw data
    raw_responses: List[str] = field(default_factory=list)


class RealMCPExecutor:
    """Execute real MCP tool calls"""
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.mcp_available = self._check_mcp_availability()
        
    def _check_mcp_availability(self) -> bool:
        """Check if MCP tools are available"""
        # In a real implementation, this would check for actual MCP tool availability
        # For now, we'll check if the MCP server is running
        try:
            # Check if MCP index exists
            from mcp_server.utils.index_discovery import IndexDiscovery
            discovery = IndexDiscovery(self.workspace_path, enable_multi_path=True)
            return discovery.get_local_index_path() is not None
        except:
            return False
    
    async def execute_mcp_search(self, query: str, semantic: bool = False, limit: int = 20) -> RealTestExecution:
        """Execute real MCP search_code tool"""
        test_exec = RealTestExecution(
            test_id=str(uuid.uuid4())[:8],
            prompt=query,
            method='mcp_search_code',
            repository=str(self.workspace_path.name),
            start_time=time.perf_counter(),
            end_time=0,
            total_duration_ms=0
        )
        
        # Record tool call
        tool_call = RealToolCall(
            tool_name='search_code',
            arguments={'query': query, 'semantic': semantic, 'limit': limit},
            start_time=time.perf_counter(),
            end_time=0,
            response_size=0,
            success=False
        )
        
        try:
            # Direct MCP database query for real performance measurement
            from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
            from mcp_server.storage.sqlite_store import SQLiteStore
            
            # Get real database
            db_path = self._get_db_path()
            if db_path:
                store = SQLiteStore(str(db_path))
                dispatcher = EnhancedDispatcher(
                    plugins=[],
                    sqlite_store=store,
                    enable_advanced_features=True,
                    semantic_search_enabled=semantic
                )
                
                # Execute search
                results = list(dispatcher.search(query, semantic=semantic, limit=limit))
                
                tool_call.end_time = time.perf_counter()
                tool_call.success = True
                tool_call.response_size = len(str(results))
                
                # Analyze results
                test_exec.results_found = len(results)
                for result in results:
                    if isinstance(result, dict):
                        if result.get('line', 0) > 0:
                            test_exec.has_line_numbers = True
                        if result.get('snippet'):
                            test_exec.has_snippets = True
                        if result.get('file') or result.get('file_path'):
                            test_exec.has_file_paths = True
                            
                test_exec.raw_responses.append(json.dumps(results[:5]))  # Store sample
                
        except Exception as e:
            tool_call.error = str(e)
            tool_call.end_time = time.perf_counter()
            logger.error(f"MCP search failed: {e}")
            
        test_exec.tool_calls.append(tool_call)
        test_exec.end_time = time.perf_counter()
        test_exec.total_duration_ms = (test_exec.end_time - test_exec.start_time) * 1000
        
        return test_exec
    
    async def execute_mcp_symbol_lookup(self, symbol: str) -> RealTestExecution:
        """Execute real MCP symbol_lookup tool"""
        test_exec = RealTestExecution(
            test_id=str(uuid.uuid4())[:8],
            prompt=f"Find symbol: {symbol}",
            method='mcp_symbol_lookup',
            repository=str(self.workspace_path.name),
            start_time=time.perf_counter(),
            end_time=0,
            total_duration_ms=0
        )
        
        tool_call = RealToolCall(
            tool_name='symbol_lookup',
            arguments={'symbol': symbol},
            start_time=time.perf_counter(),
            end_time=0,
            response_size=0,
            success=False
        )
        
        try:
            # Direct database query for symbols
            db_path = self._get_db_path()
            if db_path:
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()
                
                # Query symbols table
                cursor.execute("""
                    SELECT symbol, kind, signature, doc, defined_in, line, language
                    FROM symbols
                    WHERE symbol = ?
                    LIMIT 1
                """, (symbol,))
                
                result = cursor.fetchone()
                tool_call.end_time = time.perf_counter()
                
                if result:
                    tool_call.success = True
                    test_exec.symbols_found = 1
                    test_exec.has_line_numbers = bool(result[5])
                    test_exec.has_file_paths = bool(result[4])
                    
                    response = {
                        'symbol': result[0],
                        'kind': result[1],
                        'signature': result[2],
                        'doc': result[3],
                        'defined_in': result[4],
                        'line': result[5],
                        'language': result[6]
                    }
                    tool_call.response_size = len(str(response))
                    test_exec.raw_responses.append(json.dumps(response))
                    
                conn.close()
                
        except Exception as e:
            tool_call.error = str(e)
            tool_call.end_time = time.perf_counter()
            logger.error(f"Symbol lookup failed: {e}")
            
        test_exec.tool_calls.append(tool_call)
        test_exec.end_time = time.perf_counter()
        test_exec.total_duration_ms = (test_exec.end_time - test_exec.start_time) * 1000
        
        return test_exec
    
    def _get_db_path(self) -> Optional[Path]:
        """Get actual database path"""
        try:
            from mcp_server.utils.index_discovery import IndexDiscovery
            discovery = IndexDiscovery(self.workspace_path, enable_multi_path=True)
            return Path(discovery.get_local_index_path()) if discovery.get_local_index_path() else None
        except:
            return None


class RealNativeExecutor:
    """Execute real native tool calls"""
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        
    async def execute_grep(self, pattern: str, file_pattern: Optional[str] = None) -> RealTestExecution:
        """Execute real grep command"""
        test_exec = RealTestExecution(
            test_id=str(uuid.uuid4())[:8],
            prompt=f"grep for: {pattern}",
            method='native_grep',
            repository=str(self.workspace_path.name),
            start_time=time.perf_counter(),
            end_time=0,
            total_duration_ms=0
        )
        
        tool_call = RealToolCall(
            tool_name='grep',
            arguments={'pattern': pattern, 'file_pattern': file_pattern},
            start_time=time.perf_counter(),
            end_time=0,
            response_size=0,
            success=False
        )
        
        try:
            # Build grep command
            cmd = ['grep', '-r', '-n', '--include=' + (file_pattern or '*'), pattern, '.']
            
            # Execute grep
            result = subprocess.run(
                cmd,
                cwd=self.workspace_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            tool_call.end_time = time.perf_counter()
            tool_call.success = result.returncode in [0, 1]  # 0=found, 1=not found
            
            # Parse results
            if result.stdout:
                lines = result.stdout.strip().split('\n')
                test_exec.results_found = len(lines)
                tool_call.response_size = len(result.stdout)
                
                # Check characteristics
                for line in lines[:10]:  # Sample first 10
                    if ':' in line:
                        parts = line.split(':', 2)
                        if len(parts) >= 2:
                            test_exec.has_file_paths = True
                            if parts[1].isdigit():
                                test_exec.has_line_numbers = True
                            if len(parts) > 2:
                                test_exec.has_snippets = True
                                
                test_exec.raw_responses.append(result.stdout[:1000])  # Store sample
                
        except subprocess.TimeoutExpired:
            tool_call.error = "Timeout after 30 seconds"
            tool_call.end_time = time.perf_counter()
        except Exception as e:
            tool_call.error = str(e)
            tool_call.end_time = time.perf_counter()
            
        test_exec.tool_calls.append(tool_call)
        test_exec.end_time = time.perf_counter()
        test_exec.total_duration_ms = (test_exec.end_time - test_exec.start_time) * 1000
        
        return test_exec
    
    async def execute_find(self, pattern: str, type_filter: Optional[str] = None) -> RealTestExecution:
        """Execute real find command"""
        test_exec = RealTestExecution(
            test_id=str(uuid.uuid4())[:8],
            prompt=f"find: {pattern}",
            method='native_find',
            repository=str(self.workspace_path.name),
            start_time=time.perf_counter(),
            end_time=0,
            total_duration_ms=0
        )
        
        tool_call = RealToolCall(
            tool_name='find',
            arguments={'pattern': pattern, 'type': type_filter},
            start_time=time.perf_counter(),
            end_time=0,
            response_size=0,
            success=False
        )
        
        try:
            # Build find command
            cmd = ['find', '.', '-name', pattern]
            if type_filter:
                cmd.extend(['-type', type_filter])
                
            # Execute find
            result = subprocess.run(
                cmd,
                cwd=self.workspace_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            tool_call.end_time = time.perf_counter()
            tool_call.success = result.returncode == 0
            
            # Parse results
            if result.stdout:
                files = result.stdout.strip().split('\n')
                test_exec.results_found = len(files)
                test_exec.files_accessed = len(files)
                tool_call.response_size = len(result.stdout)
                test_exec.has_file_paths = True
                
                test_exec.raw_responses.append(result.stdout[:1000])
                
        except subprocess.TimeoutExpired:
            tool_call.error = "Timeout after 30 seconds"
            tool_call.end_time = time.perf_counter()
        except Exception as e:
            tool_call.error = str(e)
            tool_call.end_time = time.perf_counter()
            
        test_exec.tool_calls.append(tool_call)
        test_exec.end_time = time.perf_counter()
        test_exec.total_duration_ms = (test_exec.end_time - test_exec.start_time) * 1000
        
        return test_exec
    
    async def execute_ripgrep(self, pattern: str, file_pattern: Optional[str] = None) -> RealTestExecution:
        """Execute ripgrep for better performance comparison"""
        test_exec = RealTestExecution(
            test_id=str(uuid.uuid4())[:8],
            prompt=f"rg: {pattern}",
            method='native_ripgrep',
            repository=str(self.workspace_path.name),
            start_time=time.perf_counter(),
            end_time=0,
            total_duration_ms=0
        )
        
        tool_call = RealToolCall(
            tool_name='ripgrep',
            arguments={'pattern': pattern, 'file_pattern': file_pattern},
            start_time=time.perf_counter(),
            end_time=0,
            response_size=0,
            success=False
        )
        
        try:
            # Build ripgrep command
            cmd = ['rg', '--line-number', '--with-filename', pattern]
            if file_pattern:
                cmd.extend(['-g', file_pattern])
                
            # Execute ripgrep
            result = subprocess.run(
                cmd,
                cwd=self.workspace_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            tool_call.end_time = time.perf_counter()
            tool_call.success = result.returncode in [0, 1]
            
            # Parse results
            if result.stdout:
                lines = result.stdout.strip().split('\n')
                test_exec.results_found = len(lines)
                tool_call.response_size = len(result.stdout)
                test_exec.has_file_paths = True
                test_exec.has_line_numbers = True
                test_exec.has_snippets = True
                
                test_exec.raw_responses.append(result.stdout[:1000])
                
        except subprocess.TimeoutExpired:
            tool_call.error = "Timeout after 30 seconds"
            tool_call.end_time = time.perf_counter()
        except Exception as e:
            tool_call.error = str(e)
            tool_call.end_time = time.perf_counter()
            
        test_exec.tool_calls.append(tool_call)
        test_exec.end_time = time.perf_counter()
        test_exec.total_duration_ms = (test_exec.end_time - test_exec.start_time) * 1000
        
        return test_exec


class RealTestRunner:
    """Run real tests and collect performance data"""
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.mcp_executor = RealMCPExecutor(workspace_path)
        self.native_executor = RealNativeExecutor(workspace_path)
        self.results = []
        
    async def run_comparison_test(self, query: str, test_type: str = 'search') -> Dict[str, Any]:
        """Run the same query with both MCP and native methods"""
        results = {}
        
        if test_type == 'search':
            # Test MCP semantic search
            mcp_semantic = await self.mcp_executor.execute_mcp_search(query, semantic=True)
            results['mcp_semantic'] = mcp_semantic
            
            # Test MCP SQL search
            mcp_sql = await self.mcp_executor.execute_mcp_search(query, semantic=False)
            results['mcp_sql'] = mcp_sql
            
            # Test native grep
            native_grep = await self.native_executor.execute_grep(query)
            results['native_grep'] = native_grep
            
            # Test ripgrep for fair comparison
            native_rg = await self.native_executor.execute_ripgrep(query)
            results['native_ripgrep'] = native_rg
            
        elif test_type == 'symbol':
            # Extract symbol from query
            symbol = query.split()[-1] if ' ' in query else query
            
            # Test MCP symbol lookup
            mcp_symbol = await self.mcp_executor.execute_mcp_symbol_lookup(symbol)
            results['mcp_symbol'] = mcp_symbol
            
            # Test native grep for symbol
            native_symbol = await self.native_executor.execute_grep(f'\\b{symbol}\\b')
            results['native_grep_symbol'] = native_symbol
            
        elif test_type == 'find':
            # Test native find
            pattern = query.split()[-1] if ' ' in query else '*'
            native_find = await self.native_executor.execute_find(pattern)
            results['native_find'] = native_find
            
        return results
    
    async def run_test_batch(self, test_queries: List[Tuple[str, str]]) -> List[Dict[str, Any]]:
        """Run a batch of tests"""
        batch_results = []
        
        for query, test_type in test_queries:
            logger.info(f"Running test: {query} (type: {test_type})")
            try:
                result = await self.run_comparison_test(query, test_type)
                batch_results.append({
                    'query': query,
                    'test_type': test_type,
                    'timestamp': datetime.now().isoformat(),
                    'results': {k: asdict(v) for k, v in result.items()}
                })
            except Exception as e:
                logger.error(f"Test failed for query '{query}': {e}")
                batch_results.append({
                    'query': query,
                    'test_type': test_type,
                    'timestamp': datetime.now().isoformat(),
                    'error': str(e)
                })
                
        return batch_results
    
    def analyze_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze test results for performance comparison"""
        analysis = {
            'total_tests': len(results),
            'successful_tests': sum(1 for r in results if 'error' not in r),
            'performance_comparison': {},
            'quality_comparison': {},
            'method_statistics': {}
        }
        
        # Collect statistics by method
        method_stats = {}
        
        for result in results:
            if 'results' in result:
                for method, execution in result['results'].items():
                    if method not in method_stats:
                        method_stats[method] = {
                            'count': 0,
                            'total_time_ms': 0,
                            'total_results': 0,
                            'has_line_numbers': 0,
                            'has_snippets': 0,
                            'has_file_paths': 0,
                            'errors': 0
                        }
                    
                    stats = method_stats[method]
                    stats['count'] += 1
                    stats['total_time_ms'] += execution['total_duration_ms']
                    stats['total_results'] += execution['results_found']
                    
                    if execution['has_line_numbers']:
                        stats['has_line_numbers'] += 1
                    if execution['has_snippets']:
                        stats['has_snippets'] += 1
                    if execution['has_file_paths']:
                        stats['has_file_paths'] += 1
                        
                    if execution['tool_calls'] and execution['tool_calls'][0].get('error'):
                        stats['errors'] += 1
                        
        # Calculate averages
        for method, stats in method_stats.items():
            if stats['count'] > 0:
                analysis['method_statistics'][method] = {
                    'avg_response_time_ms': stats['total_time_ms'] / stats['count'],
                    'avg_results_found': stats['total_results'] / stats['count'],
                    'line_number_rate': stats['has_line_numbers'] / stats['count'],
                    'snippet_rate': stats['has_snippets'] / stats['count'],
                    'file_path_rate': stats['has_file_paths'] / stats['count'],
                    'error_rate': stats['errors'] / stats['count'],
                    'total_tests': stats['count']
                }
                
        # Compare MCP vs Native
        mcp_methods = [m for m in method_stats.keys() if m.startswith('mcp_')]
        native_methods = [m for m in method_stats.keys() if m.startswith('native_')]
        
        if mcp_methods and native_methods:
            mcp_avg_time = sum(analysis['method_statistics'][m]['avg_response_time_ms'] for m in mcp_methods) / len(mcp_methods)
            native_avg_time = sum(analysis['method_statistics'][m]['avg_response_time_ms'] for m in native_methods) / len(native_methods)
            
            analysis['performance_comparison'] = {
                'mcp_avg_response_ms': mcp_avg_time,
                'native_avg_response_ms': native_avg_time,
                'performance_improvement': ((native_avg_time - mcp_avg_time) / native_avg_time * 100) if native_avg_time > 0 else 0
            }
            
            # Quality comparison
            mcp_quality = sum(analysis['method_statistics'][m]['line_number_rate'] + 
                            analysis['method_statistics'][m]['snippet_rate'] for m in mcp_methods) / len(mcp_methods)
            native_quality = sum(analysis['method_statistics'][m]['line_number_rate'] + 
                               analysis['method_statistics'][m]['snippet_rate'] for m in native_methods) / len(native_methods)
            
            analysis['quality_comparison'] = {
                'mcp_quality_score': mcp_quality,
                'native_quality_score': native_quality,
                'quality_improvement': ((mcp_quality - native_quality) / native_quality * 100) if native_quality > 0 else 0
            }
            
        return analysis


async def run_real_tests():
    """Run real performance tests"""
    workspace_path = Path('/workspaces/Code-Index-MCP')
    runner = RealTestRunner(workspace_path)
    
    # Define test queries
    test_queries = [
        # Search tests
        ("authentication", "search"),
        ("error handling", "search"),
        ("async def", "search"),
        ("TODO", "search"),
        ("import", "search"),
        
        # Symbol tests
        ("EnhancedDispatcher", "symbol"),
        ("SQLiteStore", "symbol"),
        ("PathUtils", "symbol"),
        
        # Find tests
        ("*.py", "find"),
        ("*.md", "find"),
        ("test_*", "find")
    ]
    
    # Run tests
    results = await runner.run_test_batch(test_queries)
    
    # Analyze results
    analysis = runner.analyze_results(results)
    
    # Save results
    output_dir = workspace_path / 'real_test_results'
    output_dir.mkdir(exist_ok=True)
    
    with open(output_dir / f'real_test_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w') as f:
        json.dump({
            'test_results': results,
            'analysis': analysis,
            'timestamp': datetime.now().isoformat()
        }, f, indent=2)
        
    # Print summary
    print("\n=== Real Performance Test Summary ===")
    print(f"Total tests: {analysis['total_tests']}")
    print(f"Successful: {analysis['successful_tests']}")
    
    if analysis['performance_comparison']:
        print(f"\nPerformance Comparison:")
        print(f"  MCP Average: {analysis['performance_comparison']['mcp_avg_response_ms']:.2f}ms")
        print(f"  Native Average: {analysis['performance_comparison']['native_avg_response_ms']:.2f}ms")
        print(f"  Improvement: {analysis['performance_comparison']['performance_improvement']:.1f}%")
        
    if analysis['quality_comparison']:
        print(f"\nQuality Comparison:")
        print(f"  MCP Quality Score: {analysis['quality_comparison']['mcp_quality_score']:.2f}")
        print(f"  Native Quality Score: {analysis['quality_comparison']['native_quality_score']:.2f}")
        print(f"  Improvement: {analysis['quality_comparison']['quality_improvement']:.1f}%")
        
    print("\nMethod Statistics:")
    for method, stats in analysis['method_statistics'].items():
        print(f"\n{method}:")
        print(f"  Avg Response Time: {stats['avg_response_time_ms']:.2f}ms")
        print(f"  Avg Results: {stats['avg_results_found']:.1f}")
        print(f"  Line Numbers: {stats['line_number_rate']:.1%}")
        print(f"  Snippets: {stats['snippet_rate']:.1%}")
        print(f"  Error Rate: {stats['error_rate']:.1%}")


if __name__ == "__main__":
    asyncio.run(run_real_tests())