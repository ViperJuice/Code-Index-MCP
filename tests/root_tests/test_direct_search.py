#!/usr/bin/env python3
"""Direct test of search functionality."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mcp_server.plugins.plugin_factory import PluginFactory
from mcp_server.storage.sqlite_store import SQLiteStore


def test_direct_search():
    """Test search directly with plugins."""
    print("=== Direct Search Test ===\n")

    # Create simple Go test
    go_code = """package main

func hello() string {
    return "world"
}

func main() {
    println(hello())
}"""

    # Create plugin and store
    store = SQLiteStore(":memory:")
    plugin = PluginFactory.create_plugin("go", store, enable_semantic=False)

    print(f"Plugin class: {plugin.__class__.__name__}")
    print(f"Plugin language: {getattr(plugin, 'lang', 'unknown')}")

    # Create test file
    test_file = Path("test.go")
    test_file.write_text(go_code)

    try:
        # Index the file
        print(f"\nIndexing {test_file}...")
        shard = plugin.indexFile(test_file, go_code)

        print(f"Symbols found: {len(shard['symbols'])}")
        for symbol in shard["symbols"]:
            print(f"  - {symbol['kind']}: {symbol['symbol']} (line {symbol['line']})")

        # Test search
        print("\nTesting search for 'hello'...")
        search_results = list(plugin.search("hello", {"limit": 10}))
        print(f"Search results: {len(search_results)}")
        for result in search_results:
            print(
                f"  - {result.get('file', 'N/A')}:{result.get('line', 'N/A')} - {result.get('snippet', 'N/A').strip()}"
            )

        # Test definition lookup
        print("\nTesting definition lookup for 'hello'...")
        definition = plugin.getDefinition("hello")
        if definition:
            print("Found definition:")
            print(f"  - Kind: {definition.get('kind', 'N/A')}")
            print(f"  - File: {definition.get('defined_in', 'N/A')}")
            print(f"  - Line: {definition.get('line', 'N/A')}")
        else:
            print("No definition found")

        return len(search_results) > 0 or definition is not None

    finally:
        test_file.unlink(missing_ok=True)


if __name__ == "__main__":
    success = test_direct_search()
    if success:
        print("\n✅ Direct search test passed!")
    else:
        print("\n❌ Direct search test failed!")
        sys.exit(1)
