#!/usr/bin/env python3
"""
Demo script for testing BM25 hybrid search functionality.

This script demonstrates:
1. Initializing BM25 indexer
2. Indexing sample files
3. Performing different types of searches
4. Using hybrid search with reciprocal rank fusion
5. Configuring search weights
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any

from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.indexer.bm25_indexer import BM25Indexer
from mcp_server.indexer.hybrid_search import HybridSearch, HybridSearchConfig
from mcp_server.utils.fuzzy_indexer import FuzzyIndexer

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_sample_files():
    """Create some sample files for testing."""
    sample_files = {
        "example_python.py": '''
def calculate_fibonacci(n):
    """Calculate the nth Fibonacci number."""
    if n <= 1:
        return n
    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)

class FibonacciCalculator:
    """A class for calculating Fibonacci numbers with caching."""
    def __init__(self):
        self.cache = {}
    
    def calculate(self, n):
        if n in self.cache:
            return self.cache[n]
        if n <= 1:
            result = n
        else:
            result = self.calculate(n-1) + self.calculate(n-2)
        self.cache[n] = result
        return result
''',
        "example_javascript.js": '''
// Calculate factorial of a number
function factorial(n) {
    if (n <= 1) return 1;
    return n * factorial(n - 1);
}

// Calculate Fibonacci sequence
function fibonacci(n) {
    if (n <= 1) return n;
    let a = 0, b = 1;
    for (let i = 2; i <= n; i++) {
        [a, b] = [b, a + b];
    }
    return b;
}

class MathCalculator {
    constructor() {
        this.results = [];
    }
    
    calculate(operation, n) {
        let result;
        switch(operation) {
            case 'factorial':
                result = factorial(n);
                break;
            case 'fibonacci':
                result = fibonacci(n);
                break;
            default:
                throw new Error('Unknown operation');
        }
        this.results.push({operation, n, result});
        return result;
    }
}
''',
        "example_markdown.md": '''
# Mathematics Functions Documentation

This document describes various mathematical functions and their implementations.

## Fibonacci Sequence

The Fibonacci sequence is a series of numbers where each number is the sum of the two preceding ones.
The sequence starts with 0 and 1.

### Implementation Details

- Recursive approach: Simple but inefficient for large numbers
- Iterative approach: More efficient with O(n) time complexity
- Memoization: Caches results to avoid redundant calculations

## Factorial Function

The factorial of a non-negative integer n is the product of all positive integers less than or equal to n.
It's denoted as n! and defined as:
- 0! = 1
- n! = n × (n-1) × (n-2) × ... × 1

### Use Cases

Factorials are commonly used in:
- Combinatorics and probability
- Taylor series expansions
- Calculating permutations and combinations
'''
    }
    
    # Create sample files
    for filename, content in sample_files.items():
        with open(filename, 'w') as f:
            f.write(content)
    
    return list(sample_files.keys())


async def demo_bm25_search():
    """Demonstrate BM25 search functionality."""
    print("\n=== BM25 Search Demo ===\n")
    
    # Initialize storage and BM25 indexer
    storage = SQLiteStore("demo_bm25.db")
    bm25_indexer = BM25Indexer(storage)
    
    # Create sample files
    files = create_sample_files()
    
    # Index files in BM25
    print("Indexing files...")
    for filepath in files:
        try:
            # First create file record in storage
            repo_id = storage.create_repository(".", "demo_repo")
            file_id = storage.store_file(
                repository_id=repo_id,
                path=filepath,
                relative_path=filepath,
                language=Path(filepath).suffix[1:]  # Simple language detection
            )
            
            # Read content
            with open(filepath, 'r') as f:
                content = f.read()
            
            # Index in BM25
            metadata = {
                'language': Path(filepath).suffix[1:],
                'symbols': ['fibonacci', 'factorial', 'calculate'] if 'python' in filepath or 'javascript' in filepath else []
            }
            bm25_indexer.add_document(filepath, content, metadata)
            print(f"  ✓ Indexed: {filepath}")
        except Exception as e:
            print(f"  ✗ Failed to index {filepath}: {e}")
    
    # Perform various searches
    test_queries = [
        ("fibonacci", "Basic term search"),
        ("calculate fibonacci", "Multi-term search"),
        ('"fibonacci sequence"', "Phrase search"),
        ("fibonacci OR factorial", "Boolean OR search"),
        ("calculate AND fibonacci", "Boolean AND search"),
        ("fib*", "Prefix search"),
        ("NEAR(fibonacci calculate, 10)", "Proximity search")
    ]
    
    print("\nPerforming BM25 searches:")
    for query, description in test_queries:
        print(f"\n{description}: '{query}'")
        results = bm25_indexer.search(query, limit=5)
        for i, result in enumerate(results):
            print(f"  {i+1}. {result['filepath']} (score: {result['score']:.3f})")
            if result.get('snippet'):
                print(f"     {result['snippet']}")
    
    # Get statistics
    stats = bm25_indexer.get_statistics()
    print(f"\nBM25 Index Statistics:")
    print(f"  Total documents: {stats['total_documents']}")
    print(f"  Total symbols: {stats['total_symbols']}")
    print(f"  Languages: {stats['language_distribution']}")
    
    return storage, bm25_indexer


async def demo_hybrid_search(storage: SQLiteStore, bm25_indexer: BM25Indexer):
    """Demonstrate hybrid search functionality."""
    print("\n\n=== Hybrid Search Demo ===\n")
    
    # Initialize fuzzy indexer
    fuzzy_indexer = FuzzyIndexer(storage)
    
    # Add files to fuzzy index
    print("Building fuzzy index...")
    for filepath in ["example_python.py", "example_javascript.js", "example_markdown.md"]:
        try:
            with open(filepath, 'r') as f:
                content = f.read()
            fuzzy_indexer.add_file(filepath, content)
            print(f"  ✓ Added to fuzzy index: {filepath}")
        except Exception as e:
            print(f"  ✗ Failed to add {filepath}: {e}")
    
    # Initialize hybrid search
    config = HybridSearchConfig(
        bm25_weight=0.5,
        semantic_weight=0.0,  # Disabled as we don't have semantic indexer
        fuzzy_weight=0.5,
        enable_bm25=True,
        enable_semantic=False,
        enable_fuzzy=True,
        parallel_execution=True
    )
    
    hybrid_search = HybridSearch(
        storage=storage,
        bm25_indexer=bm25_indexer,
        semantic_indexer=None,
        fuzzy_indexer=fuzzy_indexer,
        config=config
    )
    
    # Test hybrid search
    test_queries = [
        "fibonacci calculation",
        "mathematical functions",
        "calculate factorial",
        "caching results"
    ]
    
    print("\nPerforming hybrid searches (BM25 + Fuzzy):")
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        results = await hybrid_search.search(query, limit=3)
        for result in results:
            print(f"  - {result['filepath']} (score: {result['score']:.3f}, source: {result['source']})")
            print(f"    {result['snippet'][:100]}...")
    
    # Test weight adjustment
    print("\n\nAdjusting weights (BM25: 0.8, Fuzzy: 0.2):")
    hybrid_search.set_weights(bm25=0.8, fuzzy=0.2)
    
    query = "fibonacci sequence"
    results = await hybrid_search.search(query, limit=3)
    print(f"\nQuery: '{query}'")
    for result in results:
        print(f"  - {result['filepath']} (score: {result['score']:.3f}, source: {result['source']})")
    
    # Get hybrid search statistics
    stats = hybrid_search.get_statistics()
    print(f"\nHybrid Search Statistics:")
    print(f"  Total searches: {stats.get('total_searches', 0)}")
    print(f"  Cache hit rate: {stats.get('cache_hit_rate', 0):.2%}")
    print(f"  Current weights: {stats['config']['weights']}")


async def demo_term_statistics(bm25_indexer: BM25Indexer):
    """Demonstrate term statistics functionality."""
    print("\n\n=== Term Statistics Demo ===\n")
    
    terms = ["fibonacci", "calculate", "function", "sequence"]
    
    for term in terms:
        stats = bm25_indexer.get_term_statistics(term)
        print(f"Term: '{term}'")
        print(f"  Document frequency: {stats['document_frequency']}")
        print(f"  IDF score: {stats['idf']:.3f}")
        print(f"  Appears in {stats['percentage']:.1f}% of documents\n")


async def main():
    """Run all demos."""
    print("BM25 Hybrid Search Demo")
    print("=" * 50)
    
    try:
        # Demo BM25 search
        storage, bm25_indexer = await demo_bm25_search()
        
        # Demo hybrid search
        await demo_hybrid_search(storage, bm25_indexer)
        
        # Demo term statistics
        await demo_term_statistics(bm25_indexer)
        
        # Optimize indexes
        print("\n\nOptimizing indexes...")
        bm25_indexer.optimize()
        storage.optimize_fts_tables()
        print("✓ Indexes optimized")
        
    finally:
        # Cleanup
        print("\nCleaning up...")
        for filepath in ["example_python.py", "example_javascript.js", "example_markdown.md"]:
            try:
                Path(filepath).unlink()
            except:
                pass
        print("✓ Demo completed")


if __name__ == "__main__":
    asyncio.run(main())