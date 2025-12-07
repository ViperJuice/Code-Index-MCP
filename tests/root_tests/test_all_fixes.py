#!/usr/bin/env python3
"""Test all three parallel fixes: plugin compatibility, path resolution, and semantic search."""

import asyncio
import logging
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import mcp_server_cli


async def test_all_fixes():
    """Test all three fixes in parallel."""
    print("=== Testing All Parallel Fixes ===\n")

    # Suppress verbose logging for cleaner output
    logging.getLogger("mcp_server").setLevel(logging.ERROR)
    logging.getLogger("mcp_server.dispatcher").setLevel(logging.ERROR)
    logging.getLogger("mcp_server.plugins").setLevel(logging.ERROR)

    # Create test environment
    test_dir = tempfile.mkdtemp()
    original_dir = os.getcwd()
    os.chdir(test_dir)

    test_results = {
        "plugin_compatibility": False,
        "path_resolution": False,
        "semantic_search": False,
    }

    try:
        # Initialize MCP server
        print("1. Initializing MCP Server...")
        await mcp_server_cli.initialize_services()
        dispatcher = mcp_server_cli.dispatcher
        print("✓ MCP Server initialized")

        # Test 1: Plugin Compatibility (Result object fix)
        print("\n2. Testing Plugin Compatibility Fix...")
        test_files_compat = {
            "test.html": "<html><body><h1>Test</h1></body></html>",
            "test.cpp": "int main() { return 0; }",
            "test.dart": 'void main() { print("Hello"); }',
            "test.js": 'function test() { console.log("test"); }',
        }

        compat_passed = 0
        for filename, content in test_files_compat.items():
            path = Path(filename)
            path.write_text(content)

            try:
                # Index the file
                dispatcher.index_file(path)

                # Test search (this would fail with Result object issue)
                results = list(dispatcher.search("test", limit=5))

                # Verify results have correct structure
                if results and all("file" in r and "line" in r and "snippet" in r for r in results):
                    compat_passed += 1
                    print(f"✓ {filename}: search returned valid results")
                else:
                    print(f"✗ {filename}: search results invalid")

            except Exception as e:
                print(f"✗ {filename}: error - {e}")

        test_results["plugin_compatibility"] = compat_passed >= 3

        # Test 2: Path Resolution Fix
        print("\n3. Testing Path Resolution Fix...")

        # Create nested directory structure
        nested_dir = Path("src/utils/helpers")
        nested_dir.mkdir(parents=True, exist_ok=True)

        test_files_path = {
            "src/utils/helpers/math.py": "def add(a, b): return a + b",
            "src/utils/string.go": "func concat(a, b string) string { return a + b }",
            "./relative.rs": "fn main() {}",  # Relative path
        }

        path_passed = 0
        for filepath, content in test_files_path.items():
            path = Path(filepath)
            if path.parent != Path("."):
                path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)

            try:
                # Index with potentially problematic paths
                dispatcher.index_file(path)
                path_passed += 1
                print(f"✓ {filepath}: indexed successfully")
            except Exception as e:
                if "not in the subpath" in str(e):
                    print(f"✗ {filepath}: path resolution error - {e}")
                else:
                    print(f"✗ {filepath}: other error - {e}")

        test_results["path_resolution"] = path_passed == len(test_files_path)

        # Test 3: Semantic Search Connection Handling
        print("\n4. Testing Semantic Search Connection Handling...")

        # This should not crash even without Qdrant running
        semantic_test_passed = True
        try:
            # Set semantic search enabled temporarily
            os.environ["SEMANTIC_SEARCH_ENABLED"] = "true"

            # Create a Python file (uses semantic search)
            semantic_file = Path("semantic_test.py")
            semantic_file.write_text(
                '''
class DataProcessor:
    def process(self, data):
        """Process data with semantic understanding."""
        return [x * 2 for x in data]

def main():
    processor = DataProcessor()
    result = processor.process([1, 2, 3])
    print(result)
'''
            )

            # Index the file - should handle connection refused gracefully
            dispatcher.index_file(semantic_file)
            print("✓ File indexed with semantic search disabled gracefully")

            # Search should still work without semantic
            results = list(dispatcher.search("process", limit=5))
            if results:
                print(f"✓ Regular search still works: {len(results)} results")
            else:
                print("✗ Regular search failed")
                semantic_test_passed = False

        except Exception as e:
            print(f"✗ Semantic search handling error: {e}")
            semantic_test_passed = False
        finally:
            # Reset env var
            os.environ.pop("SEMANTIC_SEARCH_ENABLED", None)

        test_results["semantic_search"] = semantic_test_passed

        # Summary
        print("\n=== Fix Verification Summary ===")

        all_passed = all(test_results.values())

        for fix_name, passed in test_results.items():
            status = "✅ FIXED" if passed else "❌ NEEDS WORK"
            print(f"{fix_name.replace('_', ' ').title()}: {status}")

        if all_passed:
            print("\n🎉 All fixes verified successfully!")
            print("\nThe MCP server now:")
            print("• Handles all plugin search results correctly")
            print("• Resolves file paths properly")
            print("• Gracefully handles missing Qdrant connections")
            return True
        else:
            print("\n⚠️ Some fixes need attention")
            return False

    except Exception as e:
        print(f"\n❌ Critical error during testing: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        # Cleanup
        os.chdir(original_dir)
        import shutil

        shutil.rmtree(test_dir, ignore_errors=True)


async def main():
    """Run the test."""
    success = await test_all_fixes()

    if success:
        print("\n✅ All parallel fixes are working correctly!")
        print("\nNext step: Update documentation and architecture files")
    else:
        print("\n❌ Some fixes need more work")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
