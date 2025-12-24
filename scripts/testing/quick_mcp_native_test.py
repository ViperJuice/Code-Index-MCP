#!/usr/bin/env python3
"""
Quick MCP vs Native Performance Test
Focuses on SQL/BM25 search and native grep for rapid testing
"""

import json
import time
import subprocess
import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


def test_mcp_sql_search(query: str, db_path: Path, limit: int = 20) -> Dict:
    """Direct SQL search on MCP database"""
    start_time = time.perf_counter()
    results = []
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Try BM25 search
        cursor.execute("""
            SELECT 
                filepath,
                snippet(bm25_content, -1, '<<', '>>', '...', 20) as snippet,
                rank
            FROM bm25_content
            WHERE bm25_content MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (query, limit))
        
        results = cursor.fetchall()
        conn.close()
        
        duration_ms = (time.perf_counter() - start_time) * 1000
        
        return {
            'method': 'mcp_sql_bm25',
            'query': query,
            'duration_ms': duration_ms,
            'result_count': len(results),
            'has_snippets': True,
            'has_file_paths': True,
            'sample_results': results[:3]
        }
    except Exception as e:
        return {
            'method': 'mcp_sql_bm25',
            'query': query,
            'duration_ms': (time.perf_counter() - start_time) * 1000,
            'error': str(e)
        }


def test_native_grep(query: str, workspace: Path) -> Dict:
    """Test native grep performance"""
    start_time = time.perf_counter()
    
    try:
        result = subprocess.run(
            ['grep', '-r', '-n', '--include=*.py', query, '.'],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        duration_ms = (time.perf_counter() - start_time) * 1000
        lines = result.stdout.strip().split('\n') if result.stdout else []
        
        return {
            'method': 'native_grep',
            'query': query,
            'duration_ms': duration_ms,
            'result_count': len(lines) if lines[0] else 0,
            'has_snippets': True,
            'has_file_paths': True,
            'has_line_numbers': True,
            'sample_results': lines[:3]
        }
    except Exception as e:
        return {
            'method': 'native_grep',
            'query': query,
            'duration_ms': (time.perf_counter() - start_time) * 1000,
            'error': str(e)
        }


def test_ripgrep(query: str, workspace: Path) -> Dict:
    """Test ripgrep for comparison"""
    start_time = time.perf_counter()
    
    try:
        result = subprocess.run(
            ['rg', '--line-number', '--with-filename', query],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        duration_ms = (time.perf_counter() - start_time) * 1000
        lines = result.stdout.strip().split('\n') if result.stdout else []
        
        return {
            'method': 'ripgrep',
            'query': query,
            'duration_ms': duration_ms,
            'result_count': len(lines) if lines[0] else 0,
            'has_snippets': True,
            'has_file_paths': True,
            'has_line_numbers': True,
            'sample_results': lines[:3]
        }
    except Exception as e:
        return {
            'method': 'ripgrep',
            'query': query,
            'duration_ms': (time.perf_counter() - start_time) * 1000,
            'error': str(e)
        }


def run_quick_comparison():
    """Run quick comparison tests"""
    workspace = Path('/workspaces/Code-Index-MCP')
    db_path = workspace / '.indexes/f7b49f5d0ae0/code_index.db'
    
    if not db_path.exists():
        # Try to find the database
        indexes_dir = workspace / '.indexes'
        for repo_dir in indexes_dir.iterdir():
            possible_db = repo_dir / 'code_index.db'
            if possible_db.exists():
                db_path = possible_db
                break
    
    # Test queries
    queries = [
        "EnhancedDispatcher",
        "async def",
        "TODO",
        "import",
        "class",
        "error",
        "test_",
        "configuration",
        "authentication",
        "def search"
    ]
    
    results = []
    
    logger.info(f"Running quick comparison tests...")
    logger.info(f"Database: {db_path}")
    logger.info(f"Workspace: {workspace}")
    
    for query in queries:
        logger.info(f"\nTesting query: '{query}'")
        
        # Test MCP SQL
        mcp_result = test_mcp_sql_search(query, db_path)
        logger.info(f"  MCP SQL: {mcp_result['duration_ms']:.2f}ms, {mcp_result.get('result_count', 0)} results")
        
        # Test native grep
        grep_result = test_native_grep(query, workspace)
        logger.info(f"  Grep: {grep_result['duration_ms']:.2f}ms, {grep_result.get('result_count', 0)} results")
        
        # Test ripgrep if available
        rg_result = test_ripgrep(query, workspace)
        if 'error' not in rg_result:
            logger.info(f"  Ripgrep: {rg_result['duration_ms']:.2f}ms, {rg_result.get('result_count', 0)} results")
        
        results.append({
            'query': query,
            'mcp': mcp_result,
            'grep': grep_result,
            'ripgrep': rg_result
        })
    
    # Calculate summary statistics
    summary = analyze_results(results)
    
    # Save results
    output_path = workspace / 'quick_test_results' / f'quick_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    output_path.parent.mkdir(exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump({
            'test_results': results,
            'summary': summary,
            'timestamp': datetime.now().isoformat()
        }, f, indent=2)
    
    # Print summary
    print_summary(summary)
    
    return summary


def analyze_results(results: List[Dict]) -> Dict:
    """Analyze test results"""
    mcp_times = []
    grep_times = []
    rg_times = []
    
    for result in results:
        if 'error' not in result['mcp']:
            mcp_times.append(result['mcp']['duration_ms'])
        if 'error' not in result['grep']:
            grep_times.append(result['grep']['duration_ms'])
        if 'error' not in result['ripgrep']:
            rg_times.append(result['ripgrep']['duration_ms'])
    
    summary = {
        'total_queries': len(results),
        'mcp_avg_ms': sum(mcp_times) / len(mcp_times) if mcp_times else 0,
        'grep_avg_ms': sum(grep_times) / len(grep_times) if grep_times else 0,
        'ripgrep_avg_ms': sum(rg_times) / len(rg_times) if rg_times else 0,
        'mcp_vs_grep_speedup': 0,
        'mcp_vs_ripgrep_speedup': 0
    }
    
    if summary['mcp_avg_ms'] > 0:
        summary['mcp_vs_grep_speedup'] = (summary['grep_avg_ms'] / summary['mcp_avg_ms']) if summary['grep_avg_ms'] > 0 else 0
        summary['mcp_vs_ripgrep_speedup'] = (summary['ripgrep_avg_ms'] / summary['mcp_avg_ms']) if summary['ripgrep_avg_ms'] > 0 else 0
    
    return summary


def print_summary(summary: Dict):
    """Print test summary"""
    print("\n" + "="*60)
    print("QUICK MCP vs NATIVE PERFORMANCE TEST SUMMARY")
    print("="*60)
    print(f"Total queries tested: {summary['total_queries']}")
    print(f"\nAverage response times:")
    print(f"  MCP SQL (BM25):  {summary['mcp_avg_ms']:.2f}ms")
    print(f"  Native grep:     {summary['grep_avg_ms']:.2f}ms")
    print(f"  Ripgrep:         {summary['ripgrep_avg_ms']:.2f}ms")
    print(f"\nPerformance comparison:")
    print(f"  MCP vs grep:     {summary['mcp_vs_grep_speedup']:.1f}x faster")
    print(f"  MCP vs ripgrep:  {summary['mcp_vs_ripgrep_speedup']:.1f}x faster")
    print("="*60)


if __name__ == "__main__":
    run_quick_comparison()