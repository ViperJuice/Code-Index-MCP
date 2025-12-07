#!/usr/bin/env python3
"""Test script for semantic search integration."""

import asyncio
import os
import sys
import time
from pathlib import Path

# Ensure we can import from mcp_server
sys.path.insert(0, str(Path(__file__).parent))

# Set environment variables before imports
os.environ["SEMANTIC_SEARCH_ENABLED"] = "true"
os.environ["QDRANT_HOST"] = "localhost"
os.environ["QDRANT_PORT"] = "6333"

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from mcp_server.config.settings import Settings
from mcp_server.plugins.python_plugin import Plugin as PythonPlugin
from mcp_server.storage.sqlite_store import SQLiteStore


def check_services():
    """Check if required services are running."""
    print("Checking services...")

    # Check Qdrant
    try:
        client = QdrantClient(url="http://localhost:6333")
        collections = client.get_collections()
        print(f"✓ Qdrant is running (collections: {len(collections.collections)})")
    except Exception as e:
        print(f"✗ Qdrant is not accessible: {e}")
        print("  Please run: docker-compose -f docker-compose.development.yml up -d qdrant")
        return False

    # Check Voyage API key
    api_key = os.getenv("VOYAGE_AI_API_KEY")
    if not api_key:
        print("✗ VOYAGE_AI_API_KEY not set")
        return False
    print("✓ Voyage AI API key is configured")

    return True


def create_test_files():
    """Create test Python files with various code patterns."""
    test_dir = Path("test_semantic_files")
    test_dir.mkdir(exist_ok=True)

    # File 1: Math operations
    (test_dir / "math_operations.py").write_text(
        '''
"""Mathematical operations and calculations."""

def fibonacci(n):
    """Calculate the nth Fibonacci number recursively."""
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

def factorial(n):
    """Calculate factorial of a number."""
    if n == 0:
        return 1
    return n * factorial(n - 1)

class Calculator:
    """A simple calculator for basic arithmetic."""
    
    def add(self, a, b):
        """Add two numbers together."""
        return a + b
    
    def multiply(self, a, b):
        """Multiply two numbers."""
        return a * b
    
    def power(self, base, exponent):
        """Calculate base raised to exponent."""
        return base ** exponent
'''
    )

    # File 2: Data processing
    (test_dir / "data_processing.py").write_text(
        '''
"""Data processing and transformation utilities."""

import json
from typing import List, Dict, Any

def parse_json_file(filepath):
    """Read and parse a JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)

def filter_data(data: List[Dict], key: str, value: Any) -> List[Dict]:
    """Filter list of dictionaries by key-value pair."""
    return [item for item in data if item.get(key) == value]

class DataTransformer:
    """Transform and manipulate data structures."""
    
    def __init__(self):
        self.transformations = []
    
    def flatten_dict(self, nested_dict: Dict, parent_key='', sep='_'):
        """Flatten a nested dictionary into a single level."""
        items = []
        for k, v in nested_dict.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self.flatten_dict(v, new_key, sep).items())
            else:
                items.append((new_key, v))
        return dict(items)
    
    def aggregate_by_key(self, data: List[Dict], key: str) -> Dict:
        """Group and aggregate data by a specific key."""
        result = {}
        for item in data:
            k = item.get(key)
            if k not in result:
                result[k] = []
            result[k].append(item)
        return result
'''
    )

    # File 3: Web utilities
    (test_dir / "web_utils.py").write_text(
        '''
"""Web-related utilities and helpers."""

import re
from urllib.parse import urlparse, parse_qs

def extract_urls(text: str) -> List[str]:
    """Extract all URLs from a text string."""
    url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
    return re.findall(url_pattern, text)

def parse_query_params(url: str) -> Dict[str, List[str]]:
    """Parse query parameters from a URL."""
    parsed = urlparse(url)
    return parse_qs(parsed.query)

class APIClient:
    """Simple API client for making HTTP requests."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session = None
    
    def build_url(self, endpoint: str) -> str:
        """Build full URL from base URL and endpoint."""
        endpoint = endpoint.lstrip('/')
        return f"{self.base_url}/{endpoint}"
    
    def authenticate(self, token: str):
        """Set authentication token for requests."""
        if not self.session:
            self.session = {}
        self.session['auth_token'] = token
    
    def make_request(self, method: str, endpoint: str, data=None):
        """Make an HTTP request to the API."""
        url = self.build_url(endpoint)
        # Simulated request
        return {"url": url, "method": method, "data": data}
'''
    )

    print(f"Created test files in {test_dir}")
    return test_dir


def test_semantic_indexing():
    """Test semantic indexing functionality."""
    print("\n=== Testing Semantic Indexing ===")

    # Create SQLite store
    store = SQLiteStore(":memory:")

    # Create plugin with semantic search enabled
    plugin = PythonPlugin(sqlite_store=store, enable_semantic=True)

    # Check if semantic is actually enabled
    if hasattr(plugin, "_enable_semantic"):
        print(f"Semantic search enabled: {plugin._enable_semantic}")
    else:
        print("Warning: Plugin doesn't have semantic search attribute")

    # Index test files
    test_dir = create_test_files()
    indexed_count = 0

    for py_file in test_dir.glob("*.py"):
        print(f"\nIndexing {py_file.name}...")
        content = py_file.read_text()

        try:
            shard = plugin.indexFile(py_file, content)
            symbols = shard.get("symbols", [])
            print(f"  Found {len(symbols)} symbols")
            for sym in symbols:
                print(f"    - {sym['kind']} {sym['symbol']}")
            indexed_count += 1
        except Exception as e:
            print(f"  Error indexing: {e}")

    print(f"\nIndexed {indexed_count} files successfully")
    return plugin, test_dir


def test_semantic_search(plugin, test_dir):
    """Test semantic search queries."""
    print("\n=== Testing Semantic Search ===")

    test_queries = [
        "function that calculates mathematical series",
        "code that processes JSON data",
        "class for making HTTP API calls",
        "recursive algorithm implementation",
        "data transformation and aggregation",
        "authentication and security",
        "parse and extract information from text",
    ]

    for query in test_queries:
        print(f"\nSearching for: '{query}'")

        # Test semantic search
        try:
            results = list(plugin.search(query, {"semantic": True, "limit": 3}))

            if results:
                print(f"  Found {len(results)} semantic results:")
                for i, result in enumerate(results, 1):
                    print(f"  {i}. {result['file']} (line {result['line']})")
                    print(f"     {result['snippet'][:100]}...")
            else:
                print("  No semantic results found")
        except Exception as e:
            print(f"  Error in semantic search: {e}")

        # Compare with traditional search
        print(f"\n  Traditional search for comparison:")
        try:
            results = list(plugin.search(query, {"semantic": False, "limit": 3}))
            if results:
                print(f"  Found {len(results)} traditional results")
            else:
                print("  No traditional results found")
        except Exception as e:
            print(f"  Error in traditional search: {e}")


def cleanup(test_dir):
    """Clean up test files."""
    import shutil

    if test_dir.exists():
        shutil.rmtree(test_dir)
        print(f"\nCleaned up {test_dir}")


def main():
    """Run semantic search integration tests."""
    print("=== Semantic Search Integration Test ===")

    # Check prerequisites
    if not check_services():
        print("\nPlease ensure all required services are running.")
        return 1

    # Load settings
    settings = Settings.from_environment()
    print(f"\nSemantic search enabled in settings: {settings.semantic_search_enabled}")

    try:
        # Test indexing
        plugin, test_dir = test_semantic_indexing()

        # Wait a moment for indexing to complete
        print("\nWaiting for embeddings to be stored...")
        time.sleep(2)

        # Test searching
        test_semantic_search(plugin, test_dir)

        # Cleanup
        cleanup(test_dir)

        print("\n=== Test completed successfully ===")
        return 0

    except Exception as e:
        print(f"\nError during test: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
