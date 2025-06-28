#!/usr/bin/env python3
"""
Test MCP functionality to ensure it's working correctly before analysis.
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, "/workspaces/Code-Index-MCP/scripts")
from fix_mcp_bm25_integration import BM25DirectDispatcher


def test_mcp_functionality():
    """Test that MCP is returning valid results."""
    
    print("Testing MCP Functionality")
    print("=" * 80)
    
    # Initialize dispatcher
    dispatcher = BM25DirectDispatcher()
    
    # Check health
    health = dispatcher.health_check()
    print(f"\n1. Health Check:")
    print(f"   Status: {health['status']}")
    print(f"   Index: {health.get('index', 'None')}")
    
    if health['status'] != 'operational':
        print("   ERROR: MCP is not operational!")
        return False
    
    # Test symbol lookup
    print(f"\n2. Symbol Lookup Tests:")
    test_symbols = ["BM25Indexer", "SQLiteStore", "IndexManager", "EnhancedDispatcher"]
    
    symbol_results = []
    for symbol in test_symbols:
        result = dispatcher.lookup(symbol)
        if result:
            symbol_results.append(result)
            print(f"   ✓ {symbol}: Found in {result['defined_in']}:{result['line']}")
            print(f"     Kind: {result['kind']}, Language: {result['language']}")
        else:
            print(f"   ✗ {symbol}: Not found")
    
    # Test search
    print(f"\n3. Search Tests:")
    test_queries = ["reranking", "centralized storage", "semantic search", "BM25"]
    
    search_results = []
    for query in test_queries:
        results = list(dispatcher.search(query, limit=5))
        search_results.append((query, results))
        print(f"   Query '{query}': {len(results)} results")
        if results:
            print(f"     First: {results[0]['file']}:{results[0]['line']}")
            print(f"     Snippet: {results[0]['snippet'][:60]}...")
    
    # Test response format
    print(f"\n4. Response Format Test:")
    if symbol_results:
        print("   Symbol response structure:")
        print(f"   {json.dumps(symbol_results[0], indent=2)}")
    
    if search_results and search_results[0][1]:
        print("\n   Search response structure:")
        print(f"   {json.dumps(search_results[0][1][0], indent=2)}")
    
    # Performance stats
    stats = dispatcher.get_statistics()
    print(f"\n5. Performance Statistics:")
    print(f"   {json.dumps(stats, indent=2)}")
    
    return True


def test_line_number_accuracy():
    """Test if line numbers returned are accurate."""
    
    print("\n\nTesting Line Number Accuracy")
    print("=" * 80)
    
    dispatcher = BM25DirectDispatcher()
    
    # Search for a known symbol
    result = dispatcher.lookup("BM25Indexer")
    if result:
        file_path = Path(result['defined_in'])
        line_num = result['line']
        
        print(f"Found BM25Indexer at {file_path}:{line_num}")
        
        # Verify by reading the file
        if file_path.exists():
            with open(file_path, 'r') as f:
                lines = f.readlines()
                
                # Check around the reported line
                start = max(0, line_num - 3)
                end = min(len(lines), line_num + 3)
                
                print(f"\nFile content around line {line_num}:")
                for i in range(start, end):
                    prefix = ">>> " if i == line_num - 1 else "    "
                    print(f"{prefix}{i+1}: {lines[i].rstrip()}")
                
                # Check if the line contains the symbol
                if line_num <= len(lines):
                    line_content = lines[line_num - 1]
                    if "BM25Indexer" in line_content:
                        print(f"\n✓ Line number is accurate!")
                    else:
                        print(f"\n✗ Line number may be inaccurate")
        else:
            print(f"File {file_path} not found")


def test_query_variations():
    """Test different query patterns."""
    
    print("\n\nTesting Query Variations")
    print("=" * 80)
    
    dispatcher = BM25DirectDispatcher()
    
    query_patterns = {
        "Class definition": "class SQLiteStore",
        "Function definition": "def index_repository",
        "Import statement": "from pathlib import",
        "Error handling": "try except",
        "Natural language": "how to index files",
        "Code pattern": "async def.*await",
        "TODO/FIXME": "TODO",
        "Configuration": "config"
    }
    
    for pattern_type, query in query_patterns.items():
        results = list(dispatcher.search(query, limit=3))
        print(f"\n{pattern_type}: '{query}'")
        print(f"  Found {len(results)} results")
        if results:
            for i, r in enumerate(results[:2]):
                print(f"  {i+1}. {r['file']}:{r['line']}")
                print(f"     {r['snippet'][:80]}...")


if __name__ == "__main__":
    success = test_mcp_functionality()
    if success:
        test_line_number_accuracy()
        test_query_variations()
    else:
        print("\nMCP is not functioning correctly. Fix required before analysis.")