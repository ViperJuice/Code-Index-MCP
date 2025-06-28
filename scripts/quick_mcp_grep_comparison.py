#!/usr/bin/env python3
"""
Quick MCP vs Grep comparison with real indexed data
"""

import os
import sys
import time
import sqlite3
import subprocess
from pathlib import Path
import json
from mcp_server.core.path_utils import PathUtils

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_server.utils.token_counter import TokenCounter


def test_mcp_search(db_path, query):
    """Test MCP-style search using indexed data."""
    start_time = time.time()
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Search with FTS5
    cursor.execute(
        "SELECT filepath, snippet(bm25_simple, 1, '<<<', '>>>', '...', 20) "
        "FROM bm25_simple WHERE bm25_simple MATCH ? LIMIT 20",
        (query,)
    )
    results = cursor.fetchall()
    
    elapsed = time.time() - start_time
    
    # Format as MCP would return
    mcp_output = []
    for filepath, snippet in results:
        mcp_output.append({
            'file': filepath,
            'snippet': snippet[:200]
        })
    
    conn.close()
    
    return {
        'results': mcp_output,
        'count': len(results),
        'time': elapsed
    }


def test_grep_search(repo_path, query):
    """Test traditional grep search."""
    start_time = time.time()
    
    # Run grep
    cmd = ['grep', '-r', '-l', query, repo_path]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0 or not result.stdout:
            return {
                'files': [],
                'count': 0,
                'time': time.time() - start_time,
                'files_to_read': 0
            }
        
        # Get file list
        files = [f.strip() for f in result.stdout.strip().split('\n') if f.strip()]
        
        # Simulate reading files (what Claude Code would do)
        file_contents = []
        for file_path in files[:20]:  # Limit to 20 files
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    file_contents.append({
                        'file': file_path,
                        'content': content
                    })
            except:
                pass
        
        elapsed = time.time() - start_time
        
        return {
            'files': file_contents[:5],  # Sample
            'count': len(files),
            'files_to_read': min(20, len(files)),
            'time': elapsed
        }
        
    except subprocess.TimeoutExpired:
        return {
            'files': [],
            'count': 0,
            'time': 10.0,
            'error': 'timeout'
        }


def main():
    """Run comparison tests."""
    token_counter = TokenCounter()
    
    # Test cases
    test_cases = [
        {
            'repo': 'javascript_react',
            'repo_path': 'PathUtils.get_workspace_root()/test_repos/web/javascript/react',
            'db_path': 'PathUtils.get_workspace_root()/test_indexes/javascript_react/simple_bm25.db',
            'queries': ['useState', 'componentDidMount', 'TODO', 'error handling']
        },
        {
            'repo': 'go_gin',
            'repo_path': 'PathUtils.get_workspace_root()/test_repos/modern/go/gin',
            'db_path': 'PathUtils.get_workspace_root()/test_indexes/go_gin/simple_bm25.db',
            'queries': ['func main', 'error', 'TODO', 'Handler']
        }
    ]
    
    results = []
    
    for test_case in test_cases:
        print(f"\n📦 Testing {test_case['repo']}...")
        
        for query in test_case['queries']:
            print(f"\n  Query: '{query}'")
            
            # MCP search
            mcp_result = test_mcp_search(test_case['db_path'], query)
            mcp_tokens = token_counter.count_tokens(f"search: {query}") + \
                        token_counter.count_tokens(json.dumps(mcp_result['results']))
            
            print(f"    MCP: {mcp_result['count']} results in {mcp_result['time']:.3f}s")
            print(f"         Tokens: {mcp_tokens}")
            
            # Grep search
            grep_result = test_grep_search(test_case['repo_path'], query)
            
            # Calculate grep tokens (command + file contents)
            grep_tokens = token_counter.count_tokens(f"grep -r '{query}' .") 
            for file_data in grep_result['files']:
                grep_tokens += token_counter.count_tokens(file_data['content'])
            
            # Estimate total tokens if all files were read
            if grep_result['files_to_read'] > 0 and grep_result['files']:
                avg_file_tokens = grep_tokens / len(grep_result['files'])
                estimated_total_tokens = int(avg_file_tokens * grep_result['files_to_read'])
            else:
                estimated_total_tokens = grep_tokens
            
            print(f"    Grep: {grep_result['count']} files in {grep_result['time']:.3f}s")
            print(f"          Would read {grep_result['files_to_read']} files")
            print(f"          Estimated tokens: {estimated_total_tokens}")
            
            # Calculate reduction
            if estimated_total_tokens > 0:
                reduction = (1 - mcp_tokens / estimated_total_tokens) * 100
                print(f"    📉 Token reduction: {reduction:.1f}%")
            
            results.append({
                'repo': test_case['repo'],
                'query': query,
                'mcp': {
                    'results': mcp_result['count'],
                    'time': mcp_result['time'],
                    'tokens': mcp_tokens
                },
                'grep': {
                    'files': grep_result['count'],
                    'files_to_read': grep_result['files_to_read'],
                    'time': grep_result['time'],
                    'estimated_tokens': estimated_total_tokens
                },
                'token_reduction': reduction if estimated_total_tokens > 0 else 0
            })
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    total_mcp_tokens = sum(r['mcp']['tokens'] for r in results)
    total_grep_tokens = sum(r['grep']['estimated_tokens'] for r in results)
    avg_reduction = sum(r['token_reduction'] for r in results) / len(results)
    
    print(f"Total queries: {len(results)}")
    print(f"MCP total tokens: {total_mcp_tokens:,}")
    print(f"Grep estimated tokens: {total_grep_tokens:,}")
    print(f"Average token reduction: {avg_reduction:.1f}%")
    
    # Save results
    with open('quick_comparison_results.json', 'w') as f:
        json.dump({
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'summary': {
                'total_queries': len(results),
                'total_mcp_tokens': total_mcp_tokens,
                'total_grep_tokens': total_grep_tokens,
                'average_token_reduction': avg_reduction
            },
            'detailed_results': results
        }, f, indent=2)
    
    print(f"\n💾 Results saved to quick_comparison_results.json")


if __name__ == "__main__":
    main()