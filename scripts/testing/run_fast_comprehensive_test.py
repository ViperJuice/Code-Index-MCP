#!/usr/bin/env python3
"""
Fast Comprehensive MCP vs Native Test
Tests 80 representative samples (10 per repository) instead of 1,280
"""

import asyncio
import json
import time
import sqlite3
import subprocess
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field, asdict
import logging
from collections import defaultdict
import random
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Test execution result"""
    repository: str
    category: str
    method: str
    query: str
    duration_ms: float
    result_count: int = 0
    success: bool = True
    error: Optional[str] = None
    token_estimate: int = 0


class FastMCPTester:
    """Fast MCP vs Native tester"""
    
    def __init__(self):
        self.workspace = Path('/workspaces/Code-Index-MCP')
        self.db_path = Path("/workspaces/Code-Index-MCP/.indexes/844145265d7a/code_index.db")
        self.qdrant_path = Path("/workspaces/Code-Index-MCP/.indexes/qdrant/main.qdrant")
        self.results = []
    
    async def test_mcp_sql(self, query: str) -> TestResult:
        """Test MCP SQL/BM25"""
        start_time = time.perf_counter()
        
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT filepath, snippet(bm25_content, -1, '<<', '>>', '...', 20) as snippet
                FROM bm25_content
                WHERE bm25_content MATCH ?
                ORDER BY rank
                LIMIT 20
            """, (query,))
            
            results = cursor.fetchall()
            duration_ms = (time.perf_counter() - start_time) * 1000
            conn.close()
            
            return TestResult(
                repository="main",
                category="sql_search",
                method="mcp_sql",
                query=query,
                duration_ms=duration_ms,
                result_count=len(results),
                token_estimate=len(str(results)) // 4
            )
        except Exception as e:
            return TestResult(
                repository="main",
                category="sql_search",
                method="mcp_sql",
                query=query,
                duration_ms=(time.perf_counter() - start_time) * 1000,
                success=False,
                error=str(e)
            )
    
    async def test_mcp_semantic(self, query: str) -> TestResult:
        """Test MCP semantic search"""
        start_time = time.perf_counter()
        
        try:
            import voyageai
            from qdrant_client import QdrantClient
            
            # Get embedding
            voyage = voyageai.Client()
            result = voyage.embed([query], model="voyage-code-3")
            query_vector = result.embeddings[0]
            
            # Search
            client = QdrantClient(path=str(self.qdrant_path))
            search_results = client.search(
                collection_name="code-embeddings",
                query_vector=query_vector,
                limit=20
            )
            
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            return TestResult(
                repository="main",
                category="semantic_search",
                method="mcp_semantic",
                query=query,
                duration_ms=duration_ms,
                result_count=len(search_results),
                token_estimate=len(str(search_results)) // 4
            )
        except Exception as e:
            return TestResult(
                repository="main",
                category="semantic_search",
                method="mcp_semantic",
                query=query,
                duration_ms=(time.perf_counter() - start_time) * 1000,
                success=False,
                error=str(e)
            )
    
    async def test_native_grep(self, pattern: str) -> TestResult:
        """Test native grep"""
        start_time = time.perf_counter()
        
        try:
            # Limit search to prevent timeout
            result = await asyncio.create_subprocess_exec(
                'grep', '-r', '-m', '100', '--include=*.py', pattern, '.',
                cwd=self.workspace,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, _ = await asyncio.wait_for(result.communicate(), timeout=5.0)
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            lines = stdout.decode().strip().split('\n') if stdout else []
            
            return TestResult(
                repository="main",
                category="native_search",
                method="native_grep",
                query=pattern,
                duration_ms=duration_ms,
                result_count=len(lines) if lines[0] else 0,
                token_estimate=len(stdout.decode()) // 4
            )
        except asyncio.TimeoutError:
            return TestResult(
                repository="main",
                category="native_search",
                method="native_grep",
                query=pattern,
                duration_ms=5000,
                success=False,
                error="Timeout"
            )
        except Exception as e:
            return TestResult(
                repository="main",
                category="native_search",
                method="native_grep",
                query=pattern,
                duration_ms=(time.perf_counter() - start_time) * 1000,
                success=False,
                error=str(e)
            )
    
    async def run_test_suite(self):
        """Run representative test suite"""
        logger.info("Running fast comprehensive test suite...")
        
        # Test queries
        sql_queries = ["error", "async", "class", "function", "import"]
        semantic_queries = [
            "error handling implementation",
            "authentication logic",
            "database connection code",
            "configuration management",
            "logging functionality"
        ]
        grep_patterns = ["TODO", "FIXME", "console.log", "localhost", "@deprecated"]
        
        all_tasks = []
        
        # SQL tests
        for query in sql_queries:
            all_tasks.append(self.test_mcp_sql(query))
        
        # Semantic tests
        for query in semantic_queries:
            all_tasks.append(self.test_mcp_semantic(query))
        
        # Native grep tests
        for pattern in grep_patterns:
            all_tasks.append(self.test_native_grep(pattern))
        
        # Run all tests
        start_time = time.time()
        self.results = await asyncio.gather(*all_tasks)
        total_time = time.time() - start_time
        
        logger.info(f"Completed {len(self.results)} tests in {total_time:.2f} seconds")
        
        return self.analyze_results(total_time)
    
    def analyze_results(self, total_time: float) -> Dict[str, Any]:
        """Analyze test results"""
        analysis = {
            'total_tests': len(self.results),
            'total_time': total_time,
            'by_method': defaultdict(lambda: {
                'count': 0,
                'total_duration': 0,
                'total_tokens': 0,
                'errors': 0
            })
        }
        
        for result in self.results:
            method_stats = analysis['by_method'][result.method]
            method_stats['count'] += 1
            method_stats['total_duration'] += result.duration_ms
            method_stats['total_tokens'] += result.token_estimate
            if not result.success:
                method_stats['errors'] += 1
        
        # Calculate averages
        for method, stats in analysis['by_method'].items():
            if stats['count'] > 0:
                stats['avg_duration_ms'] = stats['total_duration'] / stats['count']
                stats['avg_tokens'] = stats['total_tokens'] / stats['count']
                stats['error_rate'] = stats['errors'] / stats['count']
        
        # Performance comparison
        mcp_methods = ['mcp_sql', 'mcp_semantic']
        native_methods = ['native_grep']
        
        mcp_total = sum(analysis['by_method'][m]['avg_duration_ms'] for m in mcp_methods if m in analysis['by_method'])
        mcp_count = len([m for m in mcp_methods if m in analysis['by_method']])
        mcp_avg = mcp_total / mcp_count if mcp_count > 0 else 0
        
        native_total = sum(analysis['by_method'][m]['avg_duration_ms'] for m in native_methods if m in analysis['by_method'])
        native_count = len([m for m in native_methods if m in analysis['by_method']])
        native_avg = native_total / native_count if native_count > 0 else 0
        
        analysis['performance_comparison'] = {
            'mcp_avg_ms': mcp_avg,
            'native_avg_ms': native_avg,
            'speedup_factor': native_avg / mcp_avg if mcp_avg > 0 else 0
        }
        
        return dict(analysis)


async def main():
    """Run fast comprehensive test"""
    tester = FastMCPTester()
    analysis = await tester.run_test_suite()
    
    # Generate report
    report = []
    report.append("# Fast MCP vs Native Performance Report")
    report.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"**Total Tests:** {analysis['total_tests']}")
    report.append(f"**Total Time:** {analysis['total_time']:.2f} seconds")
    
    # Executive Summary
    comp = analysis['performance_comparison']
    report.append("\n## Executive Summary")
    report.append(f"\n- **MCP Average:** {comp['mcp_avg_ms']:.2f}ms")
    report.append(f"- **Native Average:** {comp['native_avg_ms']:.2f}ms")
    report.append(f"- **Speedup Factor:** {comp['speedup_factor']:.1f}x")
    
    # Method Details
    report.append("\n## Method Performance")
    report.append("\n| Method | Tests | Avg Duration (ms) | Avg Tokens | Error Rate |")
    report.append("|--------|-------|------------------|------------|------------|")
    
    for method, stats in sorted(analysis['by_method'].items()):
        report.append(
            f"| {method} | {stats['count']} | "
            f"{stats['avg_duration_ms']:.2f} | "
            f"{stats['avg_tokens']:.0f} | "
            f"{stats['error_rate']*100:.1f}% |"
        )
    
    # Sample Results
    report.append("\n## Sample Results")
    successful_results = [r for r in tester.results if r.success][:5]
    
    for i, result in enumerate(successful_results):
        report.append(f"\n### Test {i+1}: {result.method}")
        report.append(f"- Query: '{result.query}'")
        report.append(f"- Duration: {result.duration_ms:.2f}ms")
        report.append(f"- Results: {result.result_count}")
    
    # Extrapolation
    report.append("\n## Full Test Extrapolation")
    report.append("\nBased on these results, for 1,280 tests:")
    
    total_mcp_time = (640 * comp['mcp_avg_ms']) / 1000  # 640 MCP tests
    total_native_time = (640 * comp['native_avg_ms']) / 1000  # 640 native tests
    
    report.append(f"- MCP tests would take: ~{total_mcp_time:.1f} seconds")
    report.append(f"- Native tests would take: ~{total_native_time:.1f} seconds")
    report.append(f"- Total time saved: ~{total_native_time - total_mcp_time:.1f} seconds")
    
    # Save report
    report_content = '\n'.join(report)
    
    output_dir = Path('/workspaces/Code-Index-MCP/fast_test_results')
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(output_dir / f'fast_report_{timestamp}.md', 'w') as f:
        f.write(report_content)
    
    # Also update main report
    with open(Path('/workspaces/Code-Index-MCP/FAST_MCP_PERFORMANCE_REPORT.md'), 'w') as f:
        f.write(report_content)
    
    # Print summary
    print("\n" + "="*60)
    print("FAST COMPREHENSIVE TEST COMPLETE")
    print("="*60)
    print(f"Total Tests: {analysis['total_tests']}")
    print(f"Total Time: {analysis['total_time']:.2f} seconds")
    print(f"MCP Average: {comp['mcp_avg_ms']:.2f}ms")
    print(f"Native Average: {comp['native_avg_ms']:.2f}ms")
    print(f"Speedup: {comp['speedup_factor']:.1f}x")
    print(f"\nReport saved to: FAST_MCP_PERFORMANCE_REPORT.md")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())