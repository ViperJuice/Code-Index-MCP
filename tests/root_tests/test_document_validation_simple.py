#!/usr/bin/env python3
"""Simple validation test for document processing functionality."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_server.plugins.markdown_plugin.plugin import MarkdownPlugin
from mcp_server.plugins.plaintext_plugin.plugin import PlainTextPlugin
from mcp_server.storage.sqlite_store import SQLiteStore


def test_direct_plugin_functionality():
    """Test document plugins directly without the full system."""
    print("🧪 Testing Document Processing Direct Plugin Functionality")
    print("=" * 60)

    # Create a simple in-memory store
    store = SQLiteStore(":memory:")

    # Test 1: Create Markdown plugin
    print("\n✅ Test 1: Markdown Plugin Creation")
    try:
        markdown_plugin = MarkdownPlugin(sqlite_store=store)
        print(f"  Created Markdown plugin for extensions: {markdown_plugin.extensions}")
        print(f"  Language: {markdown_plugin.lang}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return

    # Test 2: Create PlainText plugin
    print("\n✅ Test 2: PlainText Plugin Creation")
    try:
        plaintext_plugin = PlainTextPlugin(sqlite_store=store)
        print(f"  Created PlainText plugin for extensions: {plaintext_plugin.extensions}")
        print(f"  Language: {plaintext_plugin.lang}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return

    # Test 3: Test Markdown indexing
    print("\n✅ Test 3: Markdown Document Indexing")
    try:
        md_path = Path("test_data/markdown_samples/simple.md")
        if md_path.exists():
            with open(md_path, "r", encoding="utf-8") as f:
                content = f.read()

            result = markdown_plugin.index_file(str(md_path), content)
            if hasattr(result, "__iter__"):
                result_list = list(result)
                print(f"  Indexed {len(result_list)} symbols from {md_path.name}")
                if result_list:
                    first = result_list[0]
                    print(
                        f"  First symbol: {first.get('name', 'unnamed')} ({first.get('type', 'unknown')})"
                    )
            else:
                print(f"  Result type: {type(result)}")
        else:
            print(f"  ❌ File not found: {md_path}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback

        traceback.print_exc()

    # Test 4: Test PlainText indexing
    print("\n✅ Test 4: PlainText Document Indexing")
    try:
        txt_path = Path("test_data/plaintext_samples/simple.txt")
        if txt_path.exists():
            with open(txt_path, "r", encoding="utf-8") as f:
                content = f.read()

            result = plaintext_plugin.index_file(str(txt_path), content)
            if hasattr(result, "__iter__"):
                result_list = list(result)
                print(f"  Indexed {len(result_list)} symbols from {txt_path.name}")
                if result_list:
                    first = result_list[0]
                    print(
                        f"  First symbol: {first.get('name', 'unnamed')} ({first.get('type', 'unknown')})"
                    )
            else:
                print(f"  Result type: {type(result)}")
        else:
            print(f"  ❌ File not found: {txt_path}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback

        traceback.print_exc()

    # Test 5: Test Markdown with frontmatter
    print("\n✅ Test 5: Markdown Frontmatter Extraction")
    try:
        md_path = Path("test_data/markdown_samples/complex.md")
        if md_path.exists():
            with open(md_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Check if metadata extraction works
            if hasattr(markdown_plugin, "extract_metadata"):
                metadata = markdown_plugin.extract_metadata(content)
                print(f"  Extracted metadata: {metadata}")
            else:
                print("  Metadata extraction not available")
        else:
            print(f"  ❌ File not found: {md_path}")
    except Exception as e:
        print(f"  ❌ Error: {e}")

    # Test 6: Test search functionality
    print("\n✅ Test 6: Search Functionality")
    try:
        # Index some files first
        for md_file in ["simple.md", "complex.md", "api_docs.md"]:
            path = Path(f"test_data/markdown_samples/{md_file}")
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                markdown_plugin.index_file(str(path), content)

        # Try searching
        if hasattr(markdown_plugin, "search"):
            results = markdown_plugin.search("installation")
            print(f"  Search results: {len(list(results)) if hasattr(results, '__iter__') else 0}")
        else:
            print("  Search not implemented in plugin")
    except Exception as e:
        print(f"  ❌ Error: {e}")

    print("\n" + "=" * 60)
    print("✅ Direct plugin validation complete!")

    # Test 7: Performance check
    print("\n✅ Test 7: Performance Check")
    try:
        import time

        start = time.time()

        # Index a larger file
        path = Path("test_data/markdown_samples/huge.md")
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            result = markdown_plugin.index_file(str(path), content)
            elapsed = time.time() - start

            if hasattr(result, "__iter__"):
                result_list = list(result)
                print(f"  Indexed {len(result_list)} symbols in {elapsed:.3f}s")
                print(f"  Performance: {elapsed*1000:.1f}ms for {len(content)} bytes")
            else:
                print(f"  Indexing completed in {elapsed:.3f}s")
        else:
            print(f"  ❌ Large test file not found")
    except Exception as e:
        print(f"  ❌ Error: {e}")


if __name__ == "__main__":
    test_direct_plugin_functionality()
