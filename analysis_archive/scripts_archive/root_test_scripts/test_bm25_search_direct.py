#!/usr/bin/env python3
"""Direct test of BM25 search with correct table names."""

import sys
from pathlib import Path
import sqlite3

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from mcp_server.storage.sqlite_store import SQLiteStore


def test_bm25_search_with_snippets():
    """Test BM25 search using the correct method."""
    
    print("TESTING BM25 SEARCH WITH SNIPPETS")
    print("=" * 80)
    
    # Test on multiple indexes
    test_cases = [
        (".indexes/f7b49f5d0ae0/current.db", "Code-Index-MCP", "fts_code"),
        (".indexes/e3acd2328eea/current.db", "TypeScript project", "bm25_content"),
        (".indexes/48f70bd595a6/current.db", "Dart SDK", "bm25_content"),
    ]
    
    for db_path, description, expected_table in test_cases:
        if not Path(db_path).exists():
            print(f"\n❌ {description}: Database not found")
            continue
        
        print(f"\n📁 Testing {description}")
        print("-" * 60)
        
        try:
            store = SQLiteStore(db_path)
            
            # First check what tables exist
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            print(f"Available tables: {', '.join(tables)}")
            conn.close()
            
            # Determine which table to use
            if "bm25_content" in tables:
                table = "bm25_content"
            elif "fts_code" in tables:
                table = "fts_code"
            else:
                print("❌ No FTS table found")
                continue
            
            print(f"Using table: {table}")
            
            # Test queries
            queries = ["def", "class", "function", "import", "return"]
            
            for query in queries:
                try:
                    # Use search_bm25_with_snippets for better results
                    results = store.search_bm25_with_snippets(
                        query, 
                        table=table,
                        limit=5
                    )
                    
                    if results:
                        print(f"\n✓ Query '{query}': {len(results)} results")
                        # Show first result
                        first = results[0]
                        print(f"  File: {first.get('filepath', first.get('file_path', 'Unknown'))}")
                        snippet = first.get('snippet', '')
                        if snippet:
                            # Clean up snippet
                            snippet = snippet.replace('\n', ' ').strip()
                            print(f"  Match: {snippet[:150]}...")
                    else:
                        print(f"\n⚠️ Query '{query}': No results")
                        
                except Exception as e:
                    print(f"\n❌ Query '{query}': Error - {e}")
            
        except Exception as e:
            print(f"\n❌ Fatal error: {e}")
            import traceback
            traceback.print_exc()


def test_simple_dispatcher_fixed():
    """Test the fixed simple dispatcher."""
    
    print("\n\nTESTING FIXED SIMPLE DISPATCHER")
    print("=" * 80)
    
    from mcp_server.dispatcher.simple_dispatcher import create_simple_dispatcher
    
    db_path = ".indexes/e3acd2328eea/current.db"
    
    if not Path(db_path).exists():
        print("❌ Test database not found")
        return
    
    dispatcher = create_simple_dispatcher(db_path)
    
    # Test search
    queries = ["class", "function", "import"]
    
    for query in queries:
        results = list(dispatcher.search(query, limit=3))
        if results:
            print(f"\n✓ Query '{query}': {len(results)} results")
            for i, res in enumerate(results):
                print(f"  {i+1}. {res.file_path}")
                if res.snippet:
                    print(f"     {res.snippet[:80]}...")
        else:
            print(f"\n⚠️ Query '{query}': No results")
    
    # Show stats
    stats = dispatcher.get_stats()
    print(f"\n📊 Stats: {stats}")


if __name__ == "__main__":
    test_bm25_search_with_snippets()
    test_simple_dispatcher_fixed()