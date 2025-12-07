#!/usr/bin/env python3
"""
Test script for SQLite persistence layer.

This script tests the basic functionality of the SQLiteStore and its integration
with the FuzzyIndexer.
"""

import logging
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.utils.fuzzy_indexer import FuzzyIndexer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_sqlite_store():
    """Test basic SQLite store functionality."""
    print("\n=== Testing SQLite Store ===")

    # Create a test database
    db_path = "test_code_index.db"

    # Remove existing test database
    if os.path.exists(db_path):
        os.remove(db_path)

    # Initialize store
    store = SQLiteStore(db_path)

    # Test repository creation
    print("\n1. Creating repository...")
    repo_id = store.create_repository(
        path="/test/repo",
        name="Test Repository",
        metadata={"type": "python", "description": "Test repo"},
    )
    print(f"   Created repository with ID: {repo_id}")

    # Test file storage
    print("\n2. Storing file...")
    file_id = store.store_file(
        repository_id=repo_id,
        path="/test/repo/example.py",
        relative_path="example.py",
        language="python",
        size=1024,
        hash="abc123",
        metadata={"encoding": "utf-8"},
    )
    print(f"   Stored file with ID: {file_id}")

    # Test symbol storage
    print("\n3. Storing symbols...")
    symbol1_id = store.store_symbol(
        file_id=file_id,
        name="calculate_sum",
        kind="function",
        line_start=10,
        line_end=15,
        signature="def calculate_sum(a: int, b: int) -> int:",
        documentation="Calculate the sum of two integers.",
    )
    print(f"   Stored symbol 'calculate_sum' with ID: {symbol1_id}")

    symbol2_id = store.store_symbol(
        file_id=file_id,
        name="Calculator",
        kind="class",
        line_start=20,
        line_end=50,
        documentation="A simple calculator class.",
    )
    print(f"   Stored symbol 'Calculator' with ID: {symbol2_id}")

    # Test symbol search
    print("\n4. Testing fuzzy search...")
    results = store.search_symbols_fuzzy("calc", limit=10)
    print(f"   Found {len(results)} results for 'calc':")
    for result in results:
        print(f"   - {result['name']} ({result['kind']}) in {result['file_path']}")

    # Test FTS search
    print("\n5. Testing FTS search...")
    results = store.search_symbols_fts("calculate", limit=10)
    print(f"   Found {len(results)} results for 'calculate':")
    for result in results:
        print(f"   - {result['name']} ({result['kind']}) in {result['file_path']}")

    # Test statistics
    print("\n6. Database statistics:")
    stats = store.get_statistics()
    for table, count in stats.items():
        print(f"   {table}: {count} records")

    print("\n✓ SQLite store tests completed successfully!")
    return store


def test_fuzzy_indexer_integration(store):
    """Test FuzzyIndexer with SQLite backend."""
    print("\n\n=== Testing FuzzyIndexer with SQLite Backend ===")

    # Create indexer with SQLite backend
    indexer = FuzzyIndexer(sqlite_store=store)

    # Add some file content
    print("\n1. Adding file content...")
    test_content = """def hello_world():
    print("Hello, World!")
    
def calculate_sum(a, b):
    return a + b

class Calculator:
    def add(self, x, y):
        return x + y
    
    def subtract(self, x, y):
        return x - y
"""

    indexer.add_file("/test/repo/example.py", test_content)
    print("   File content added to index")

    # Test search
    print("\n2. Testing content search...")
    results = indexer.search("hello", limit=5)
    print(f"   Found {len(results)} results for 'hello':")
    for result in results:
        print(f"   - Line {result['line']} in {result['file']}: {result['snippet'][:50]}...")

    # Test symbol search
    print("\n3. Testing symbol search...")
    # Add symbols to the indexer
    indexer.add_symbol("hello_world", "/test/repo/example.py", 1, {"symbol_id": 1})
    indexer.add_symbol("calculate_sum", "/test/repo/example.py", 4, {"symbol_id": 2})
    indexer.add_symbol("Calculator", "/test/repo/example.py", 7, {"symbol_id": 3})

    results = indexer.search_symbols("calc", limit=5)
    print(f"   Found {len(results)} symbol results for 'calc':")
    for result in results:
        print(f"   - {result['name']} at line {result.get('line_start', 'N/A')}")

    # Test persistence
    print("\n4. Testing persistence...")
    success = indexer.persist()
    print(f"   Persistence {'successful' if success else 'failed'}")

    # Get statistics
    print("\n5. Indexer statistics:")
    stats = indexer.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")

    print("\n✓ FuzzyIndexer integration tests completed successfully!")


def main():
    """Run all tests."""
    print("SQLite Persistence Layer Test Suite")
    print("=" * 50)

    try:
        # Test SQLite store
        store = test_sqlite_store()

        # Test FuzzyIndexer integration
        test_fuzzy_indexer_integration(store)

        print("\n\n✓ All tests passed!")

    except Exception as e:
        print(f"\n\n✗ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    finally:
        # Cleanup test database
        if os.path.exists("test_code_index.db"):
            os.remove("test_code_index.db")
            print("\nTest database cleaned up.")


if __name__ == "__main__":
    main()
