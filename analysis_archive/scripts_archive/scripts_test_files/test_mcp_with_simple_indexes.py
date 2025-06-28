#!/usr/bin/env python3
"""
Test MCP search with the simple BM25 indexes we created
"""

import os
import sys
import json
import sqlite3
from pathlib import Path
import time

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_server.utils.token_counter import TokenCounter
from mcp_server.utils.mcp_client_wrapper import MCPClientWrapper


def test_simple_bm25_search(db_path, query):
    """Test direct BM25 search."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT filepath, snippet(bm25_simple, 1, '<<<', '>>>', '...', 20) "
        "FROM bm25_simple WHERE bm25_simple MATCH ? LIMIT 10",
        (query,)
    )
    results = cursor.fetchall()
    conn.close()
    
    return [{'file': f, 'snippet': s} for f, s in results]


def test_mcp_wrapper(repo_name, query):
    """Test MCP client wrapper."""
    try:
        client = MCPClientWrapper()
        results = client.search_code(query, limit=10)
        return results
    except Exception as e:
        return {'error': str(e)}


def main():
    """Run comparison tests."""
    token_counter = TokenCounter()
    
    # Test repos with simple indexes
    test_cases = [
        {
            'repo': 'javascript_react',
            'db_path': '/workspaces/Code-Index-MCP/test_indexes/javascript_react/simple_bm25.db',
            'queries': ['useState', 'render', 'component']
        },
        {
            'repo': 'go_gin', 
            'db_path': '/workspaces/Code-Index-MCP/test_indexes/go_gin/simple_bm25.db',
            'queries': ['func', 'error', 'Handler']
        }
    ]
    
    results = []
    
    for test in test_cases:
        print(f"\n📦 Testing {test['repo']}...")
        
        if not Path(test['db_path']).exists():
            print(f"  ❌ Index not found: {test['db_path']}")
            continue
            
        for query in test['queries']:
            print(f"\n  Query: '{query}'")
            
            # Direct BM25 search
            bm25_results = test_simple_bm25_search(test['db_path'], query)
            bm25_tokens = token_counter.count_tokens(json.dumps(bm25_results))
            
            print(f"    Direct BM25: {len(bm25_results)} results, {bm25_tokens} tokens")
            
            # MCP search (if available)
            mcp_results = test_mcp_wrapper(test['repo'], query)
            if isinstance(mcp_results, dict) and 'error' in mcp_results:
                print(f"    MCP: Error - {mcp_results['error']}")
            else:
                mcp_tokens = token_counter.count_tokens(json.dumps(mcp_results))
                print(f"    MCP: {len(mcp_results)} results, {mcp_tokens} tokens")
            
            results.append({
                'repo': test['repo'],
                'query': query,
                'bm25_count': len(bm25_results),
                'bm25_tokens': bm25_tokens,
                'mcp_status': 'error' if isinstance(mcp_results, dict) and 'error' in mcp_results else 'success'
            })
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    successful_mcp = sum(1 for r in results if r['mcp_status'] == 'success')
    print(f"Total queries: {len(results)}")
    print(f"Direct BM25 working: {len(results)}")
    print(f"MCP working: {successful_mcp}")
    
    # Show example results
    if results and results[0]['bm25_count'] > 0:
        print("\nExample BM25 result:")
        example = test_simple_bm25_search(test_cases[0]['db_path'], test_cases[0]['queries'][0])
        if example:
            print(f"  File: {example[0]['file']}")
            print(f"  Snippet: {example[0]['snippet'][:100]}...")


if __name__ == "__main__":
    main()