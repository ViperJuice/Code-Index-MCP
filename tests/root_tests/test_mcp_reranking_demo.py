#!/usr/bin/env python3
"""
Test script to demonstrate reranking functionality with MCP index.
This script uses the current MCP index to test various search scenarios
with reranking enabled.
"""

import asyncio
import json

# Add the project root to Python path
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).parent))

from mcp_server.config.settings import Settings
from mcp_server.indexer.hybrid_search import HybridSearchEngine
from mcp_server.indexer.reranker import (
    CohereReranker,
    HybridReranker,
    LocalCrossEncoderReranker,
    RerankConfig,
    TFIDFReranker,
)
from mcp_server.storage.sqlite_store import SQLiteStore


class RerankerDemo:
    """Demonstrate reranking functionality with various test cases."""

    def __init__(self):
        self.settings = Settings()
        self.store = SQLiteStore("code_index.db")
        self.search_engine = HybridSearchEngine(self.store, self.settings)

    async def setup(self):
        """Initialize the search engine."""
        await self.search_engine.initialize()

    async def get_index_stats(self):
        """Get statistics about the current index."""
        stats = {"total_files": 0, "language_breakdown": {}, "total_symbols": 0}

        # Get all indexed files
        results = await self.store.search("*", limit=10000)
        stats["total_files"] = len(results)

        # Analyze language breakdown
        for result in results:
            ext = Path(result["file_path"]).suffix
            stats["language_breakdown"][ext] = stats["language_breakdown"].get(ext, 0) + 1

        return stats

    async def test_reranking(self, query: str, reranker_type: str = "tfidf", top_k: int = 10):
        """Test reranking with a specific query and reranker."""
        print(f"\n{'='*80}")
        print(f"Query: '{query}'")
        print(f"Reranker: {reranker_type}")
        print(f"Top K: {top_k}")
        print("=" * 80)

        # Configure reranker
        if reranker_type == "tfidf":
            reranker = TFIDFReranker()
        elif reranker_type == "cross-encoder":
            reranker = LocalCrossEncoderReranker()
        elif reranker_type == "cohere":
            reranker = CohereReranker()
        elif reranker_type == "hybrid":
            reranker = HybridReranker()
        else:
            reranker = None

        config = RerankConfig(enabled=reranker is not None, reranker=reranker, top_k=top_k)

        # Time the search
        start_time = time.time()

        # Search without reranking first
        print("\n1. Initial Search Results (No Reranking):")
        results_no_rerank = await self.search_engine.search(
            query, limit=top_k, rerank_config=RerankConfig(enabled=False)
        )

        search_time = time.time() - start_time

        # Display initial results
        for i, result in enumerate(results_no_rerank[:5], 1):
            print(f"\n  {i}. {result['file_path']}:{result.get('line_number', 'N/A')}")
            print(f"     Score: {result.get('score', 'N/A'):.4f}")
            if "content" in result:
                preview = result["content"][:100].replace("\n", " ")
                print(f"     Preview: {preview}...")

        # Now search with reranking
        print(f"\n2. Reranked Results ({reranker_type}):")
        start_time = time.time()

        results_reranked = await self.search_engine.search(query, limit=top_k, rerank_config=config)

        rerank_time = time.time() - start_time

        # Display reranked results
        for i, result in enumerate(results_reranked[:5], 1):
            print(f"\n  {i}. {result['file_path']}:{result.get('line_number', 'N/A')}")
            print(f"     Score: {result.get('score', 'N/A'):.4f}")
            if "rerank_score" in result:
                print(f"     Rerank Score: {result['rerank_score']:.4f}")
            if "content" in result:
                preview = result["content"][:100].replace("\n", " ")
                print(f"     Preview: {preview}...")

        # Performance metrics
        print(f"\n3. Performance Metrics:")
        print(f"   - Initial search time: {search_time:.3f}s")
        print(f"   - Reranked search time: {rerank_time:.3f}s")
        print(f"   - Reranking overhead: {rerank_time - search_time:.3f}s")

        # Compare result ordering
        print(f"\n4. Result Order Changes:")
        initial_files = [r["file_path"] for r in results_no_rerank[:5]]
        reranked_files = [r["file_path"] for r in results_reranked[:5]]

        for i, (initial, reranked) in enumerate(zip(initial_files, reranked_files), 1):
            if initial != reranked:
                print(f"   Position {i}: {initial} → {reranked}")

        return results_reranked

    async def run_test_suite(self):
        """Run a comprehensive test suite with various queries."""
        # Test queries covering different scenarios
        test_queries = [
            # Code structure queries
            ("class Plugin", "Find plugin class definitions"),
            ("def index", "Find indexing functions"),
            ("async def search", "Find async search methods"),
            # Natural language queries
            ("how to create a new plugin", "Documentation search"),
            ("reranking implementation", "Feature search"),
            ("error handling in dispatcher", "Error handling patterns"),
            # Complex queries
            ("voyage ai embedding integration", "Integration search"),
            ("sqlite fts5 full text search", "Database features"),
            ("tree-sitter language parsing", "Parser integration"),
            # Cross-language queries
            ("function parseFile", "Cross-language function search"),
            ("import logging", "Import statement search"),
        ]

        # Test with different rerankers
        rerankers = ["tfidf", "cross-encoder", "hybrid"]

        results_comparison = []

        for query, description in test_queries:
            print(f"\n\n{'#'*80}")
            print(f"TEST CASE: {description}")
            print(f"{'#'*80}")

            case_results = {"query": query, "description": description, "results": {}}

            for reranker in rerankers:
                try:
                    results = await self.test_reranking(query, reranker, top_k=20)
                    case_results["results"][reranker] = {
                        "success": True,
                        "top_result": results[0]["file_path"] if results else None,
                        "result_count": len(results),
                    }
                except Exception as e:
                    print(f"\nError with {reranker}: {e}")
                    case_results["results"][reranker] = {"success": False, "error": str(e)}

            results_comparison.append(case_results)

        # Summary report
        print(f"\n\n{'='*80}")
        print("SUMMARY REPORT")
        print("=" * 80)

        for case in results_comparison:
            print(f"\nQuery: '{case['query']}' ({case['description']})")
            for reranker, result in case["results"].items():
                if result["success"]:
                    print(f"  {reranker}: {result['top_result']}")
                else:
                    print(f"  {reranker}: Failed - {result['error']}")

    async def test_metadata_preservation(self):
        """Test that all metadata is preserved through reranking."""
        print(f"\n\n{'='*80}")
        print("METADATA PRESERVATION TEST")
        print("=" * 80)

        query = "def initialize"

        # Search with reranking
        config = RerankConfig(enabled=True, reranker=TFIDFReranker(), top_k=5)

        results = await self.search_engine.search(query, limit=5, rerank_config=config)

        print(f"\nChecking metadata for query: '{query}'")

        required_fields = ["file_path", "line_number", "content", "type", "name"]
        optional_fields = ["score", "rerank_score", "language", "docstring"]

        for i, result in enumerate(results, 1):
            print(f"\nResult {i}: {result['file_path']}")

            # Check required fields
            missing_required = [f for f in required_fields if f not in result]
            if missing_required:
                print(f"  ❌ Missing required fields: {missing_required}")
            else:
                print("  ✅ All required fields present")

            # Check optional fields
            present_optional = [f for f in optional_fields if f in result]
            print(f"  ℹ️  Optional fields: {present_optional}")

            # Display all metadata
            print("  📋 Full metadata:")
            for key, value in result.items():
                if key != "content":  # Skip content for brevity
                    print(f"     - {key}: {value}")


async def main():
    """Main entry point for the demo."""
    demo = RerankerDemo()

    try:
        # Setup
        await demo.setup()

        # Show index statistics
        print("MCP INDEX STATISTICS")
        print("=" * 80)
        stats = await demo.get_index_stats()
        print(f"Total indexed files: {stats['total_files']}")
        print(f"\nLanguage breakdown:")
        for ext, count in sorted(
            stats["language_breakdown"].items(), key=lambda x: x[1], reverse=True
        ):
            print(f"  {ext}: {count} files")

        # Run test suite
        await demo.run_test_suite()

        # Test metadata preservation
        await demo.test_metadata_preservation()

        print("\n\n✅ All tests completed!")

    except Exception as e:
        print(f"\n❌ Error during demo: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # Cleanup
        if hasattr(demo.store, "close"):
            await demo.store.close()


if __name__ == "__main__":
    asyncio.run(main())
