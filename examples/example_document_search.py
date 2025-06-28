#!/usr/bin/env python3
"""Example demonstrating the enhanced dispatcher's document query capabilities."""

import logging
from pathlib import Path
from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def demonstrate_document_queries():
    """Demonstrate various document query capabilities."""
    
    # Create dispatcher with enhanced features
    dispatcher = EnhancedDispatcher(
        enable_advanced_features=True,
        use_plugin_factory=True,
        lazy_load=False,  # Load all plugins for demo
        semantic_search_enabled=True
    )
    
    print("Enhanced Dispatcher Document Query Examples")
    print("=" * 60)
    
    # Example 1: Natural language installation query
    print("\n1. Natural Language Query: 'How to install this package'")
    print("-" * 60)
    results = list(dispatcher.search("How to install this package", limit=5))
    print(f"Found {len(results)} results")
    for i, result in enumerate(results[:3]):
        print(f"\n  Result {i+1}:")
        print(f"  File: {result['file']}")
        print(f"  Line: {result['line']}")
        print(f"  Snippet: {result['snippet'][:100]}...")
    
    # Example 2: Configuration query
    print("\n\n2. Configuration Query: 'configuration options for API'")
    print("-" * 60)
    results = list(dispatcher.search("configuration options for API", limit=5))
    print(f"Found {len(results)} results")
    for i, result in enumerate(results[:3]):
        print(f"\n  Result {i+1}:")
        print(f"  File: {result['file']}")
        print(f"  Line: {result['line']}")
        print(f"  Snippet: {result['snippet'][:100]}...")
    
    # Example 3: Getting started guide
    print("\n\n3. Getting Started Query: 'getting started guide'")
    print("-" * 60)
    results = list(dispatcher.search("getting started guide", limit=5))
    print(f"Found {len(results)} results")
    for i, result in enumerate(results[:3]):
        print(f"\n  Result {i+1}:")
        print(f"  File: {result['file']}")
        print(f"  Line: {result['line']}")
        print(f"  Snippet: {result['snippet'][:100]}...")
    
    # Example 4: Cross-document search
    print("\n\n4. Cross-Document Search: 'installation' across all docs")
    print("-" * 60)
    results = list(dispatcher.search_documentation("installation", limit=5))
    print(f"Found {len(results)} results from documentation files")
    for i, result in enumerate(results[:3]):
        print(f"\n  Result {i+1}:")
        print(f"  File: {result['file']}")
        print(f"  Line: {result['line']}")
        print(f"  Snippet: {result['snippet'][:100]}...")
    
    # Example 5: API documentation search
    print("\n\n5. API Documentation Search")
    print("-" * 60)
    results = list(dispatcher.search_documentation("API", doc_types=["api", "reference"], limit=5))
    print(f"Found {len(results)} results from API documentation")
    for i, result in enumerate(results[:3]):
        print(f"\n  Result {i+1}:")
        print(f"  File: {result['file']}")
        print(f"  Line: {result['line']}")
        print(f"  Snippet: {result['snippet'][:100]}...")
    
    # Example 6: Regular code search (for comparison)
    print("\n\n6. Regular Code Search: 'def search' (non-document query)")
    print("-" * 60)
    results = list(dispatcher.search("def search", limit=5))
    print(f"Found {len(results)} results")
    for i, result in enumerate(results[:3]):
        print(f"\n  Result {i+1}:")
        print(f"  File: {result['file']}")
        print(f"  Line: {result['line']}")
        print(f"  Snippet: {result['snippet'][:100]}...")
    
    print("\n\nDemo complete!")


def demonstrate_query_detection():
    """Show how queries are detected and expanded."""
    dispatcher = EnhancedDispatcher()
    
    print("\n\nQuery Detection and Expansion Demo")
    print("=" * 60)
    
    test_queries = [
        "How to configure the database",
        "API reference for search method",
        "troubleshooting connection errors",
        "def search_documents",  # Code query
        "installation requirements"
    ]
    
    for query in test_queries:
        is_doc = dispatcher._is_document_query(query)
        print(f"\nQuery: '{query}'")
        print(f"Is Document Query: {is_doc}")
        
        if is_doc:
            expansions = dispatcher._expand_document_query(query)
            print(f"Expanded to {len(expansions)} variations:")
            for i, exp in enumerate(expansions[:3]):
                print(f"  {i+1}. {exp}")
            if len(expansions) > 3:
                print(f"  ... and {len(expansions) - 3} more")


if __name__ == "__main__":
    demonstrate_document_queries()
    demonstrate_query_detection()