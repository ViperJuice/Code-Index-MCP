#!/usr/bin/env python3
"""
Test script for BM25 hybrid search functionality.

This script tests:
1. BM25 indexer initialization and operations
2. Hybrid search with different configurations
3. Search result ranking and fusion
4. Performance and accuracy
"""

import asyncio
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import pytest

from mcp_server.indexer.bm25_indexer import BM25Indexer
from mcp_server.indexer.hybrid_search import HybridSearch, HybridSearchConfig
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.utils.fuzzy_indexer import FuzzyIndexer


class TestBM25Indexer:
    """Test BM25 indexer functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.db_path = Path(self.test_dir) / "test_bm25.db"
        self.storage = SQLiteStore(str(self.db_path))
        self.bm25_indexer = BM25Indexer(self.storage)

        # Create repository
        self.repo_id = self.storage.create_repository(self.test_dir, "test_repo")

    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)

    def test_initialization(self):
        """Test BM25 indexer initialization."""
        assert self.bm25_indexer is not None
        assert self.bm25_indexer.table_name == "bm25_content"

        # Check that FTS5 tables were created
        with self.storage._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name LIKE 'bm25_%'
            """
            )
            tables = [row[0] for row in cursor]
            assert "bm25_content" in tables
            assert "bm25_symbols" in tables
            assert "bm25_documents" in tables

    def test_add_document(self):
        """Test adding documents to BM25 index."""
        # Create a test file
        test_file = Path(self.test_dir) / "test.py"
        test_content = '''
def hello_world():
    """Print hello world."""
    print("Hello, World!")
    
class Greeter:
    def greet(self, name):
        return f"Hello, {name}!"
'''
        test_file.write_text(test_content)

        # Store file in database
        file_id = self.storage.store_file(
            repository_id=self.repo_id,
            path=str(test_file),
            relative_path="test.py",
            language="python",
        )

        # Index in BM25
        metadata = {"language": "python", "symbols": ["hello_world", "Greeter", "greet"]}
        self.bm25_indexer.add_document(str(test_file), test_content, metadata)

        # Search for content
        results = self.bm25_indexer.search("hello world", limit=10)
        assert len(results) > 0
        assert results[0]["filepath"] == str(test_file)
        assert "hello" in results[0]["snippet"].lower()

    def test_search_methods(self):
        """Test different search methods."""
        # Add test documents
        docs = [
            ("doc1.txt", "The quick brown fox jumps over the lazy dog"),
            ("doc2.txt", "A quick brown fox is a fast animal"),
            ("doc3.txt", "The lazy dog sleeps all day long"),
        ]

        for filename, content in docs:
            filepath = Path(self.test_dir) / filename
            filepath.write_text(content)

            file_id = self.storage.store_file(
                repository_id=self.repo_id,
                path=str(filepath),
                relative_path=filename,
                language="text",
            )

            self.bm25_indexer.add_document(str(filepath), content, {"language": "text"})

        # Test basic search
        results = self.bm25_indexer.search("fox", limit=10)
        assert len(results) == 2
        assert all("fox" in r["snippet"] for r in results)

        # Test phrase search
        results = self.bm25_indexer.search_phrase("brown fox", limit=10)
        assert len(results) == 2

        # Test prefix search
        results = self.bm25_indexer.search_prefix("qui", limit=10)
        assert len(results) == 2

        # Test NEAR search
        results = self.bm25_indexer.search_near(["fox", "dog"], distance=10, limit=10)
        assert len(results) >= 1

    def test_term_statistics(self):
        """Test term statistics functionality."""
        # Add documents
        docs = [
            ("doc1.txt", "Python is a programming language"),
            ("doc2.txt", "Python is popular for data science"),
            ("doc3.txt", "JavaScript is also a programming language"),
            ("doc4.txt", "Data science uses many programming languages"),
        ]

        for filename, content in docs:
            filepath = Path(self.test_dir) / filename
            filepath.write_text(content)

            file_id = self.storage.store_file(
                repository_id=self.repo_id,
                path=str(filepath),
                relative_path=filename,
                language="text",
            )

            self.bm25_indexer.add_document(str(filepath), content, {"language": "text"})

        # Get term statistics
        stats = self.bm25_indexer.get_term_statistics("python")
        assert stats["document_frequency"] == 2
        assert stats["total_documents"] == 4
        assert stats["percentage"] == 50.0
        assert stats["idf"] > 0

        stats = self.bm25_indexer.get_term_statistics("programming")
        assert stats["document_frequency"] == 3
        assert stats["percentage"] == 75.0


class TestHybridSearch:
    """Test hybrid search functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.db_path = Path(self.test_dir) / "test_hybrid.db"
        self.storage = SQLiteStore(str(self.db_path))
        self.repo_id = self.storage.create_repository(self.test_dir, "test_repo")

        # Initialize indexers
        self.bm25_indexer = BM25Indexer(self.storage)
        self.fuzzy_indexer = FuzzyIndexer(self.storage)

        # Initialize hybrid search
        self.config = HybridSearchConfig(
            bm25_weight=0.5,
            fuzzy_weight=0.5,
            semantic_weight=0.0,
            enable_bm25=True,
            enable_fuzzy=True,
            enable_semantic=False,
        )

        self.hybrid_search = HybridSearch(
            storage=self.storage,
            bm25_indexer=self.bm25_indexer,
            fuzzy_indexer=self.fuzzy_indexer,
            semantic_indexer=None,
            config=self.config,
        )

    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)

    @pytest.mark.asyncio
    async def test_hybrid_search_basic(self):
        """Test basic hybrid search functionality."""
        # Add test documents
        docs = [
            (
                "python_code.py",
                '''
def calculate_sum(numbers):
    """Calculate the sum of a list of numbers."""
    return sum(numbers)

def calculate_average(numbers):
    """Calculate the average of a list of numbers."""
    if not numbers:
        return 0
    return sum(numbers) / len(numbers)
''',
            ),
            (
                "math_utils.py",
                '''
import math

def calculate_mean(values):
    """Calculate arithmetic mean."""
    return sum(values) / len(values)

def calculate_median(values):
    """Calculate median value."""
    sorted_values = sorted(values)
    n = len(sorted_values)
    if n % 2 == 0:
        return (sorted_values[n//2 - 1] + sorted_values[n//2]) / 2
    return sorted_values[n//2]
''',
            ),
        ]

        for filename, content in docs:
            filepath = Path(self.test_dir) / filename
            filepath.write_text(content)

            # Store in database
            file_id = self.storage.store_file(
                repository_id=self.repo_id,
                path=str(filepath),
                relative_path=filename,
                language="python",
            )

            # Index in BM25
            self.bm25_indexer.add_document(str(filepath), content, {"language": "python"})

            # Index in fuzzy
            self.fuzzy_indexer.add_file(str(filepath), content)

        # Test hybrid search
        results = await self.hybrid_search.search("calculate average", limit=5)
        assert len(results) > 0
        assert any("average" in r["snippet"].lower() for r in results)

        # Check that results come from multiple sources
        sources = set(r["source"] for r in results)
        assert len(sources) > 1  # Should have both BM25 and fuzzy results

    @pytest.mark.asyncio
    async def test_weight_configuration(self):
        """Test weight configuration in hybrid search."""
        # Add a simple document
        filepath = Path(self.test_dir) / "test.txt"
        content = "This is a test document for weight configuration"
        filepath.write_text(content)

        file_id = self.storage.store_file(
            repository_id=self.repo_id,
            path=str(filepath),
            relative_path="test.txt",
            language="text",
        )

        self.bm25_indexer.add_document(str(filepath), content, {"language": "text"})
        self.fuzzy_indexer.add_file(str(filepath), content)

        # Test with equal weights
        self.hybrid_search.set_weights(bm25=0.5, fuzzy=0.5)
        results1 = await self.hybrid_search.search("test document", limit=1)
        score1 = results1[0]["score"] if results1 else 0

        # Test with BM25 bias
        self.hybrid_search.set_weights(bm25=0.9, fuzzy=0.1)
        results2 = await self.hybrid_search.search("test document", limit=1)
        score2 = results2[0]["score"] if results2 else 0

        # Scores should be different due to weight changes
        assert score1 != score2

    @pytest.mark.asyncio
    async def test_method_toggling(self):
        """Test enabling/disabling search methods."""
        # Add a test document
        filepath = Path(self.test_dir) / "test.txt"
        content = "Enable disable test document"
        filepath.write_text(content)

        file_id = self.storage.store_file(
            repository_id=self.repo_id,
            path=str(filepath),
            relative_path="test.txt",
            language="text",
        )

        self.bm25_indexer.add_document(str(filepath), content, {"language": "text"})
        self.fuzzy_indexer.add_file(str(filepath), content)

        # Test with both enabled
        self.hybrid_search.enable_methods(bm25=True, fuzzy=True)
        results_both = await self.hybrid_search.search("test", limit=10)

        # Test with only BM25
        self.hybrid_search.enable_methods(bm25=True, fuzzy=False)
        results_bm25 = await self.hybrid_search.search("test", limit=10)

        # Test with only fuzzy
        self.hybrid_search.enable_methods(bm25=False, fuzzy=True)
        results_fuzzy = await self.hybrid_search.search("test", limit=10)

        # All should return results
        assert len(results_both) > 0
        assert len(results_bm25) > 0
        assert len(results_fuzzy) > 0

        # Check sources
        assert all(r["source"] == "bm25" for r in results_bm25)
        assert all(r["source"] == "fuzzy" for r in results_fuzzy)

    @pytest.mark.asyncio
    async def test_cache_functionality(self):
        """Test hybrid search caching."""
        # Add a test document
        filepath = Path(self.test_dir) / "cache_test.txt"
        content = "Cache test document content"
        filepath.write_text(content)

        file_id = self.storage.store_file(
            repository_id=self.repo_id,
            path=str(filepath),
            relative_path="cache_test.txt",
            language="text",
        )

        self.bm25_indexer.add_document(str(filepath), content, {"language": "text"})

        # Enable caching
        self.hybrid_search.config.cache_results = True

        # First search (cache miss)
        results1 = await self.hybrid_search.search("cache test", limit=10)
        stats1 = self.hybrid_search.get_statistics()

        # Second search (cache hit)
        results2 = await self.hybrid_search.search("cache test", limit=10)
        stats2 = self.hybrid_search.get_statistics()

        # Results should be identical
        assert len(results1) == len(results2)
        assert results1[0]["filepath"] == results2[0]["filepath"]

        # Cache hit rate should increase
        assert stats2["cache_hits"] > stats1.get("cache_hits", 0)

        # Clear cache
        self.hybrid_search.clear_cache()
        assert len(self.hybrid_search._result_cache) == 0


def test_bm25_optimization():
    """Test BM25 index optimization."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_optimize.db"
        storage = SQLiteStore(str(db_path))
        bm25_indexer = BM25Indexer(storage)
        repo_id = storage.create_repository(tmpdir, "test_repo")

        # Add many documents
        for i in range(50):
            filepath = Path(tmpdir) / f"doc{i}.txt"
            content = f"Document {i} with some content about topic {i % 10}"
            filepath.write_text(content)

            file_id = storage.store_file(
                repository_id=repo_id,
                path=str(filepath),
                relative_path=f"doc{i}.txt",
                language="text",
            )

            bm25_indexer.add_document(str(filepath), content, {"language": "text"})

        # Get statistics before optimization
        stats_before = bm25_indexer.get_statistics()

        # Optimize
        bm25_indexer.optimize()

        # Get statistics after optimization
        stats_after = bm25_indexer.get_statistics()

        # Document count should remain the same
        assert stats_before["total_documents"] == stats_after["total_documents"]

        # Search should still work
        results = bm25_indexer.search("topic 5", limit=10)
        assert len(results) > 0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
