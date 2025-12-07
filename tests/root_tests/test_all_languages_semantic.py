#!/usr/bin/env python3
"""Test semantic search for all language plugins."""

import os
import sys
import tempfile
from pathlib import Path

# Load environment
from dotenv import load_dotenv

load_dotenv()

# Force semantic search
os.environ["SEMANTIC_SEARCH_ENABLED"] = "true"
os.environ["QDRANT_HOST"] = ":memory:"

sys.path.insert(0, str(Path(__file__).parent))

from mcp_server.storage.sqlite_store import SQLiteStore


def test_python_plugin():
    """Test Python plugin semantic search."""
    print("\n=== Testing Python Plugin ===")

    from mcp_server.plugins.python_plugin import Plugin

    store = SQLiteStore(":memory:")
    plugin = Plugin(sqlite_store=store)

    # Check if semantic is enabled
    print(f"Plugin type: {plugin.__class__.__name__}")
    print(f"Has semantic features: {hasattr(plugin, '_enable_semantic')}")

    # Create test file
    test_code = '''
def calculate_prime(n):
    """Check if number is prime."""
    if n < 2:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True

class MathUtils:
    """Utilities for mathematical operations."""
    
    def factorial(self, n):
        """Calculate factorial recursively."""
        if n <= 1:
            return 1
        return n * self.factorial(n - 1)
'''

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(test_code)
        test_file = f.name

    # Index the file
    shard = plugin.indexFile(test_file, test_code)
    print(f"Indexed {len(shard['symbols'])} symbols")

    # Test semantic search
    queries = [
        "function to check if a number is prime",
        "recursive mathematical calculation",
        "class for math utilities",
    ]

    for query in queries:
        print(f"\nQuery: '{query}'")
        results = list(plugin.search(query, {"semantic": True, "limit": 2}))
        print(f"  Results: {len(results)}")
        for r in results:
            print(f"    - Line {r['line']}: {r['snippet'].strip()[:50]}...")

    os.unlink(test_file)
    return True


def test_javascript_plugin():
    """Test JavaScript plugin semantic search."""
    print("\n=== Testing JavaScript Plugin ===")

    try:
        from mcp_server.plugins.js_plugin import Plugin

        store = SQLiteStore(":memory:")
        plugin = Plugin(sqlite_store=store)

        print(f"Plugin type: {plugin.__class__.__name__}")
        print(f"Has semantic features: {hasattr(plugin, '_enable_semantic')}")

        # Create test file
        test_code = """
async function fetchUserData(userId) {
    /**
     * Fetch user data from API
     * @param {string} userId - The user ID
     * @returns {Promise<User>} User object
     */
    const response = await fetch(`/api/users/${userId}`);
    return response.json();
}

class DataProcessor {
    constructor() {
        this.cache = new Map();
    }
    
    processData(data) {
        // Transform and validate data
        return data.map(item => ({
            ...item,
            processed: true,
            timestamp: Date.now()
        }));
    }
}

const calculateSum = (numbers) => {
    return numbers.reduce((acc, num) => acc + num, 0);
};
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
            f.write(test_code)
            test_file = f.name

        # Index the file
        shard = plugin.indexFile(test_file, test_code)
        print(f"Indexed {len(shard['symbols'])} symbols")

        # Test semantic search
        queries = [
            "async function to fetch data from API",
            "class for data transformation",
            "function to calculate sum of array",
        ]

        for query in queries:
            print(f"\nQuery: '{query}'")
            results = list(plugin.search(query, {"semantic": True, "limit": 2}))
            print(f"  Results: {len(results)}")
            for r in results:
                print(f"    - Line {r['line']}: {r['snippet'].strip()[:50]}...")

        os.unlink(test_file)
        return True

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_c_plugin():
    """Test C plugin semantic search."""
    print("\n=== Testing C Plugin ===")

    try:
        from mcp_server.plugins.c_plugin.plugin import Plugin

        # Check if C plugin has semantic support
        print(f"C Plugin base class: {Plugin.__bases__}")
        print("Note: C plugin may need semantic implementation")

        # Would need to implement CPluginSemantic similar to Python/JS
        return False

    except Exception as e:
        print(f"Error: {e}")
        return False


def test_html_css_plugin():
    """Test HTML/CSS plugin semantic search."""
    print("\n=== Testing HTML/CSS Plugin ===")

    try:
        from mcp_server.plugins.html_css_plugin import Plugin

        # Check if HTML/CSS plugin has semantic support
        print(f"HTML/CSS Plugin base class: {Plugin.__bases__}")
        print("Note: HTML/CSS plugin may need semantic implementation")

        # Would need to implement HtmlCssPluginSemantic
        return False

    except Exception as e:
        print(f"Error: {e}")
        return False


def main():
    """Run tests for all language plugins."""
    print("=== Testing Semantic Search for All Language Plugins ===")
    print(f"SEMANTIC_SEARCH_ENABLED: {os.getenv('SEMANTIC_SEARCH_ENABLED')}")
    print(f"VOYAGE_API_KEY present: {'VOYAGE_API_KEY' in os.environ}")

    results = {
        "Python": test_python_plugin(),
        "JavaScript": test_javascript_plugin(),
        "C": test_c_plugin(),
        "HTML/CSS": test_html_css_plugin(),
    }

    print("\n=== Summary ===")
    for lang, success in results.items():
        status = "✓ Working" if success else "✗ Not implemented"
        print(f"{lang}: {status}")

    implemented = sum(1 for s in results.values() if s)
    print(f"\nSemantic search implemented for {implemented}/{len(results)} language plugins")

    if implemented < len(results):
        print("\nNext steps:")
        print("- Create semantic versions for remaining plugins")
        print("- Follow the pattern from PythonPluginSemantic and JsPluginSemantic")
        print("- Each plugin needs to inherit from PluginWithSemanticSearch")


if __name__ == "__main__":
    main()
