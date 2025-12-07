#!/usr/bin/env python3
"""Test the enhanced dispatcher's document query functionality."""

import logging
from pathlib import Path

from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.storage.sqlite_store import SQLiteStore

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_document_query_detection():
    """Test document query detection."""
    dispatcher = EnhancedDispatcher(enable_advanced_features=True)

    # Test queries that should be detected as document queries
    doc_queries = [
        "How to install the package",
        "getting started with Python",
        "API documentation for search",
        "configuration options",
        "What is the architecture",
        "troubleshooting errors",
        "best practices for coding",
        "installation guide",
        "where can I find examples",
    ]

    # Test queries that should NOT be document queries
    code_queries = [
        "def search",
        "class EnhancedDispatcher",
        "import logging",
        "search_function",
        "dispatcher.search",
    ]

    print("Testing Document Query Detection:")
    print("=" * 50)

    print("\nDocument Queries (should return True):")
    for query in doc_queries:
        is_doc = dispatcher._is_document_query(query)
        print(f"  '{query}' -> {is_doc}")
        assert is_doc, f"Expected '{query}' to be detected as document query"

    print("\nCode Queries (should return False):")
    for query in code_queries:
        is_doc = dispatcher._is_document_query(query)
        print(f"  '{query}' -> {is_doc}")
        assert not is_doc, f"Expected '{query}' NOT to be detected as document query"

    print("\n✓ Document query detection test passed!")


def test_query_expansion():
    """Test query expansion for document queries."""
    dispatcher = EnhancedDispatcher(enable_advanced_features=True)

    test_cases = [
        ("how to install", ["installation", "setup", "getting started"]),
        ("API documentation", ["api reference", "endpoint", "method"]),
        ("configuration guide", ["configure", "settings", "options"]),
        ("getting started", ["quickstart", "tutorial", "introduction"]),
    ]

    print("\nTesting Query Expansion:")
    print("=" * 50)

    for original, expected_terms in test_cases:
        expanded = dispatcher._expand_document_query(original)
        print(f"\nOriginal: '{original}'")
        print(f"Expanded to {len(expanded)} queries:")
        for i, query in enumerate(expanded[:5]):  # Show first 5
            print(f"  {i+1}. {query}")

        # Check that at least some expected terms appear
        all_expanded_text = " ".join(expanded).lower()
        found_terms = [term for term in expected_terms if term in all_expanded_text]
        print(f"Found expected terms: {found_terms}")
        assert len(found_terms) > 0, f"Expected to find some of {expected_terms} in expansions"

    print("\n✓ Query expansion test passed!")


def test_documentation_file_detection():
    """Test documentation file detection."""
    dispatcher = EnhancedDispatcher(enable_advanced_features=True)

    doc_files = [
        "README.md",
        "docs/installation.md",
        "CONTRIBUTING.rst",
        "documentation/api-guide.md",
        "setup.txt",
        "changelog.md",
        "docs/tutorial.html",
    ]

    code_files = ["main.py", "src/dispatcher.py", "test_something.js", "utils.go", "model.java"]

    print("\nTesting Documentation File Detection:")
    print("=" * 50)

    print("\nDocumentation Files (should return True):")
    for file_path in doc_files:
        is_doc = dispatcher._is_documentation_file(file_path)
        print(f"  '{file_path}' -> {is_doc}")
        assert is_doc, f"Expected '{file_path}' to be detected as documentation file"

    print("\nCode Files (should return False):")
    for file_path in code_files:
        is_doc = dispatcher._is_documentation_file(file_path)
        print(f"  '{file_path}' -> {is_doc}")
        assert not is_doc, f"Expected '{file_path}' NOT to be detected as documentation file"

    print("\n✓ Documentation file detection test passed!")


def test_cross_document_search():
    """Test cross-document search functionality."""
    # Create a test dispatcher
    dispatcher = EnhancedDispatcher(
        enable_advanced_features=True, use_plugin_factory=True, lazy_load=False
    )

    print("\nTesting Cross-Document Search:")
    print("=" * 50)

    # Test searching for installation instructions across docs
    print("\nSearching for 'installation' across documentation...")
    results = list(dispatcher.search_documentation("installation", limit=5))

    print(f"Found {len(results)} results")
    for i, result in enumerate(results):
        print(f"\n{i+1}. {result['file']}:{result['line']}")
        print(f"   Snippet: {result['snippet'][:100]}...")

    # The actual results will depend on what files are indexed
    print("\n✓ Cross-document search test completed!")


def main():
    """Run all tests."""
    print("Enhanced Dispatcher Document Query Tests")
    print("=" * 70)

    test_document_query_detection()
    test_query_expansion()
    test_documentation_file_detection()
    test_cross_document_search()

    print("\n" + "=" * 70)
    print("All tests passed! ✓")


if __name__ == "__main__":
    main()
