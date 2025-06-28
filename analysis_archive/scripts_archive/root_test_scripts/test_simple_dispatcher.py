#!/usr/bin/env python3
"""Test the simple dispatcher that bypasses the plugin system."""

import sys
from pathlib import Path
import time

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from mcp_server.dispatcher.simple_dispatcher import SimpleDispatcher, create_simple_dispatcher
from mcp_server.storage.sqlite_store import SQLiteStore


def test_simple_dispatcher():
    """Test simple dispatcher on multiple indexes."""
    
    print("TESTING SIMPLE DISPATCHER")
    print("=" * 80)
    
    # Test indexes
    test_cases = [
        (".indexes/f7b49f5d0ae0/current.db", "Code-Index-MCP"),
        (".indexes/e3acd2328eea/current.db", "TypeScript project"),
        (".indexes/48f70bd595a6/current.db", "Dart SDK"),
    ]
    
    total_tests = 0
    successful_tests = 0
    
    for db_path, description in test_cases:
        if not Path(db_path).exists():
            print(f"\n❌ {description}: Database not found")
            continue
        
        print(f"\n📁 Testing {description}")
        print("-" * 60)
        
        try:
            # Create dispatcher
            dispatcher = create_simple_dispatcher(db_path)
            
            # Check health
            health = dispatcher.health_check()
            print(f"Health check: {health}")
            
            if health['status'] == 'unhealthy':
                print("❌ Dispatcher unhealthy")
                continue
            
            # Test queries
            test_queries = [
                ("def", "Function definitions"),
                ("class", "Class definitions"),
                ("import", "Import statements"),
                ("TODO", "TODO comments"),
                ("error", "Error handling")
            ]
            
            for query, description in test_queries:
                total_tests += 1
                try:
                    start_time = time.time()
                    results = list(dispatcher.search(query, limit=5))
                    elapsed = time.time() - start_time
                    
                    if results:
                        successful_tests += 1
                        print(f"\n✓ {description} ('{query}'): {len(results)} results in {elapsed:.3f}s")
                        # Show first result
                        first = results[0]
                        print(f"  First match: {first.file_path}")
                        print(f"  Snippet: {first.snippet[:100]}...")
                    else:
                        print(f"\n⚠️ {description} ('{query}'): No results")
                        
                except Exception as e:
                    print(f"\n❌ {description} ('{query}'): Error - {e}")
            
            # Test symbol search
            print("\n🔍 Testing symbol search...")
            symbols = list(dispatcher.search_symbol("Dispatcher", limit=3))
            if symbols:
                print(f"✓ Found {len(symbols)} symbols")
                for sym in symbols[:2]:
                    print(f"  - {sym.get('name', 'Unknown')} in {sym.get('file_path', 'Unknown')}")
            
            # Show stats
            stats = dispatcher.get_stats()
            print(f"\n📊 Statistics: {stats}")
            
        except Exception as e:
            print(f"\n❌ Fatal error: {e}")
            import traceback
            traceback.print_exc()
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total tests: {total_tests}")
    print(f"Successful: {successful_tests}")
    print(f"Success rate: {successful_tests/total_tests*100:.1f}%" if total_tests > 0 else "N/A")
    
    if successful_tests == total_tests:
        print("\n✅ Simple dispatcher is working perfectly!")
        print("   This can be used as a fallback while fixing the enhanced dispatcher.")
    else:
        print("\n⚠️ Some tests failed, but simple dispatcher is partially working.")


def benchmark_simple_dispatcher():
    """Benchmark the simple dispatcher performance."""
    
    print("\n\nBENCHMARKING SIMPLE DISPATCHER")
    print("=" * 80)
    
    db_path = ".indexes/e3acd2328eea/current.db"  # Large TypeScript project
    
    if not Path(db_path).exists():
        print("❌ Benchmark database not found")
        return
    
    dispatcher = create_simple_dispatcher(db_path)
    
    # Benchmark queries
    queries = ["function", "class", "import", "export", "interface", "type", "const", "return"]
    
    print(f"Running {len(queries)} queries on 74K file index...")
    
    total_time = 0
    total_results = 0
    
    for query in queries:
        start = time.time()
        results = list(dispatcher.search(query, limit=100))
        elapsed = time.time() - start
        
        total_time += elapsed
        total_results += len(results)
        
        print(f"  '{query}': {len(results)} results in {elapsed:.3f}s ({len(results)/elapsed:.0f} results/sec)")
    
    print(f"\nTotal: {total_results} results in {total_time:.3f}s")
    print(f"Average: {total_time/len(queries):.3f}s per query")
    print(f"Throughput: {total_results/total_time:.0f} results/sec")


if __name__ == "__main__":
    test_simple_dispatcher()
    benchmark_simple_dispatcher()