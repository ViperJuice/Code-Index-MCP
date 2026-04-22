"""Integration tests for dispatcher document routing functionality."""

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict
from unittest.mock import MagicMock

import pytest

from mcp_server.core.repo_context import RepoContext
from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.storage.multi_repo_manager import RepositoryInfo
from tests.base_test import BaseDocumentTest

logger = logging.getLogger(__name__)


def _make_ctx(store, tmp_path=None):
    """Build a minimal RepoContext for document routing tests."""
    registry_entry = MagicMock(spec=RepositoryInfo)
    registry_entry.tracked_branch = "main"
    return RepoContext(
        repo_id="test-doc-routing-repo",
        sqlite_store=store,
        workspace_root=Path(tmp_path or "/tmp"),
        tracked_branch="main",
        registry_entry=registry_entry,
    )


class TestDispatcherDocumentRouting(BaseDocumentTest):
    """Test dispatcher routing for document-related queries."""

    @pytest.fixture
    def dispatcher(self):
        """Create enhanced dispatcher instance (no sqlite_store ctor arg per Protocol)."""
        return EnhancedDispatcher()

    @pytest.fixture
    def ctx(self):
        """RepoContext wrapping the base test's SQLiteStore."""
        return _make_ctx(self.store, self.workspace)

    def create_test_codebase(self, workspace: Path) -> Dict[str, Path]:
        """Create a test codebase with various file types."""
        files = {}

        # Documentation files
        files["readme"] = workspace / "README.md"
        files["readme"].write_text("""# My Project

## Installation

Install using pip:

```bash
pip install myproject
```

## Usage

Import and use:

```python
from myproject import main
main()
```
""")

        files["api_docs"] = workspace / "docs" / "api.md"
        files["api_docs"].parent.mkdir(exist_ok=True)
        files["api_docs"].write_text("""# API Reference

## Classes

### MyClass

A class that does something useful.

Methods:
- process(data): Process the input data
- validate(input): Validate input parameters
""")

        # Code files
        files["main_py"] = workspace / "src" / "main.py"
        files["main_py"].parent.mkdir(exist_ok=True)
        files["main_py"].write_text('''"""Main module for the project."""

def main():
    """Main entry point."""
    print("Hello from main!")

class MyClass:
    """A class that does something useful."""

    def process(self, data):
        """Process the input data."""
        return data

    def validate(self, input):
        """Validate input parameters."""
        return True
''')

        files["config"] = workspace / "config.txt"
        files["config"].write_text("""Configuration Settings

Database URL: postgresql://localhost/mydb
Cache TTL: 3600
Max Connections: 100
""")

        return files

    def test_document_query_detection(self, dispatcher):
        """Test that dispatcher correctly identifies document queries."""
        # Document-related queries
        doc_queries = [
            "how to install",
            "getting started with the project",
            "API documentation",
            "configuration guide",
            "usage examples",
            "troubleshooting errors",
            "best practices for deployment",
        ]

        for query in doc_queries:
            is_doc_query = dispatcher._is_document_query(query)
            assert is_doc_query, f"Query '{query}' should be detected as document query"

        # Non-document queries
        code_queries = [
            "MyClass.process",
            "function definition",
            "import statements",
            "class inheritance",
        ]

        for query in code_queries:
            is_doc_query = dispatcher._is_document_query(query)
            assert not is_doc_query, f"Query '{query}' should not be detected as document query"

    def test_dispatcher_routes_to_document_plugins(self, dispatcher, ctx):
        """Test that dispatcher routes document queries to appropriate plugins."""
        self.create_test_codebase(self.workspace)

        # Index all files
        dispatcher.index_directory(ctx, self.workspace)

        # Test installation query - should prioritize README
        results = list(dispatcher.search(ctx, "how to install pip", limit=10))
        assert len(results) > 0

        # Check that README appears in results
        readme_found = any("README.md" in r["file"] for r in results)
        assert readme_found, "README should be found for installation query"

        # Check ranking - documentation should be prioritized
        if len(results) > 1:
            first_result = results[0]
            assert "README.md" in first_result["file"] or "api.md" in first_result["file"]

    def test_dispatcher_aggregates_cross_file_results(self, dispatcher, ctx, tmp_path):
        """Test that dispatcher aggregates results from multiple files."""
        self.create_test_codebase(tmp_path)
        ctx2 = _make_ctx(self.store, tmp_path)

        # Index files
        dispatcher.index_directory(ctx2, tmp_path)

        # Search for "MyClass" - should find in both code and docs
        results = list(dispatcher.search(ctx2, "MyClass process method", limit=20))
        assert len(results) > 0

        # Should find results from both api.md and main.py
        result_files = {r["file"] for r in results}
        assert any("api.md" in f for f in result_files), "Should find in API docs"
        assert any("main.py" in f for f in result_files), "Should find in Python code"

    def test_dispatcher_prioritizes_relevant_documents(self, dispatcher, ctx, tmp_path):
        """Test that dispatcher prioritizes more relevant documents."""
        # Create multiple documentation files
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir(exist_ok=True)

        (docs_dir / "installation.md").write_text("""# Installation Guide

## Requirements

- Python 3.8+
- pip package manager

## Installation Steps

1. Clone the repository
2. Run pip install -r requirements.txt
3. Configure settings
""")

        (docs_dir / "troubleshooting.md").write_text("""# Troubleshooting

## Common Installation Issues

If pip install fails, try:
- Updating pip: python -m pip install --upgrade pip
- Using virtual environment
""")

        (self.workspace / "notes.txt").write_text("""Random notes about pip and installation.""")

        ctx2 = _make_ctx(self.store, tmp_path)
        dispatcher.index_directory(ctx, self.workspace)
        dispatcher.index_directory(ctx2, tmp_path)

        results = list(dispatcher.search(ctx2, "pip installation guide", limit=10))

        # Installation.md should rank highly
        if len(results) >= 2:
            assert "installation.md" in results[0]["file"].lower()

    def test_dispatcher_handles_mixed_queries(self, dispatcher, ctx, tmp_path):
        """Test dispatcher with queries that span code and documentation."""
        self.create_test_codebase(tmp_path)

        # Add a test file
        test_file = tmp_path / "tests" / "test_main.py"
        test_file.parent.mkdir(exist_ok=True)
        test_file.write_text('''"""Tests for main module."""

def test_myclass_process():
    """Test MyClass.process method as documented in API."""
    from src.main import MyClass
    obj = MyClass()
    assert obj.process("data") == "data"
''')

        ctx2 = _make_ctx(self.store, tmp_path)
        dispatcher.index_directory(ctx2, tmp_path)

        results = list(
            dispatcher.search(ctx2, "MyClass process method implementation test", limit=15)
        )

        # Should find results from multiple file types
        result_files = [r["file"] for r in results]
        file_types = set()
        for f in result_files:
            if f.endswith(".py"):
                file_types.add("python")
            elif f.endswith(".md"):
                file_types.add("markdown")

        # Should have found both code and documentation
        assert len(file_types) >= 2, "Should find results in both code and docs"

    def test_dispatcher_respects_search_options(self, dispatcher, ctx, tmp_path):
        """Test that dispatcher respects search options like limit."""
        self.create_test_codebase(tmp_path)

        # Create many files to test limit
        for i in range(10):
            doc = tmp_path / f"doc_{i}.md"
            doc.write_text(f"# Document {i}\n\nThis document explains feature {i}.")

        ctx2 = _make_ctx(self.store, tmp_path)
        dispatcher.index_directory(ctx2, tmp_path)

        # Test limit
        results_limited = list(dispatcher.search(ctx2, "document explains", limit=3))
        assert len(results_limited) <= 3

        # Test with higher limit
        results_all = list(dispatcher.search(ctx2, "document explains", limit=20))
        assert len(results_all) > len(results_limited)

    def test_dispatcher_error_recovery(self, dispatcher, ctx, tmp_path):
        """Test that dispatcher handles plugin errors gracefully."""
        self.create_test_codebase(tmp_path)

        # Create a file that might cause parsing issues
        bad_file = tmp_path / "bad.md"
        bad_file.write_text("# Broken [link (no closing\n\n```python\n# Unclosed code block")

        ctx2 = _make_ctx(self.store, tmp_path)

        # Should not crash during indexing
        dispatcher.index_directory(ctx2, tmp_path)

        # Should still return results from good files
        results = list(dispatcher.search(ctx2, "installation", limit=10))
        assert len(results) > 0

    def test_dispatcher_fallback_mechanisms(self, dispatcher, ctx):
        """Test dispatcher fallback when primary plugins fail."""
        files = {
            "corrupt.py": "def broken(\n    # Unclosed function",
            "empty.md": "",
            "normal.txt": "This is normal text content.",
        }

        for filename, content in files.items():
            file_path = self.workspace / filename
            file_path.write_text(content)

        # Index all files - should handle gracefully
        dispatcher.index_directory(ctx, self.workspace)

        # Search should still work and find content from valid files
        results = list(dispatcher.search(ctx, "normal text content", limit=10))
        assert len(results) > 0
        assert any("normal" in r["snippet"].lower() for r in results)

    def test_dispatcher_concurrent_processing(self, dispatcher, ctx):
        """Test dispatcher handling concurrent requests."""
        for i in range(20):
            doc = self.workspace / f"concurrent_{i}.md"
            doc.write_text(f"# Document {i}\n\nContent for concurrent testing {i}.")

        dispatcher.index_directory(ctx, self.workspace)

        queries = ["Document 5", "concurrent testing", "content for", "Document 15", "testing 10"]
        results_dict = {}
        errors = []

        def search_query(query):
            try:
                results = list(dispatcher.search(ctx, query, limit=5))
                results_dict[query] = results
            except Exception as e:
                errors.append((query, str(e)))

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(search_query, q) for q in queries]
            for future in futures:
                future.result()

        assert len(errors) == 0
        assert len(results_dict) == len(queries)
        for query, results in results_dict.items():
            assert len(results) > 0

    def test_dispatcher_query_optimization(self, dispatcher, ctx):
        """Test dispatcher query optimization for complex searches."""
        docs = [
            ("intro.md", "# Introduction\n\nThis guide introduces API concepts."),
            ("api_guide.md", "# API Guide\n\nComplete API documentation guide."),
            ("api_reference.md", "# API Reference\n\nDetailed API method reference."),
            ("tutorial.md", "# Tutorial\n\nStep-by-step API tutorial guide."),
            ("concepts.md", "# Concepts\n\nCore API concepts and principles."),
        ]

        for filename, content in docs:
            (self.workspace / filename).write_text(content)

        dispatcher.index_directory(ctx, self.workspace)

        results = list(dispatcher.search(ctx, "API guide documentation", limit=10))
        assert len(results) > 0

        result_files = [r["file"] for r in results[:3]]
        assert any("api_guide.md" in f for f in result_files)

    def test_dispatcher_result_aggregation_strategies(self, dispatcher, ctx):
        """Test different result aggregation strategies."""
        docs = {
            "exact_match.md": "# Exact Match\n\nThis document contains the exact search query.",
            "partial_match.md": "# Partial\n\nThis has only some search terms.",
            "code_match.py": '"""Module with search query in docstring."""\ndef search(): pass',
            "distant_match.txt": "Barely related content with one search word.",
        }

        for filename, content in docs.items():
            (self.workspace / filename).write_text(content)

        dispatcher.index_directory(ctx, self.workspace)

        results = list(dispatcher.search(ctx, "exact search query", limit=10))

        if results:
            top_result = results[0]
            assert (
                "exact_match.md" in top_result["file"] or "exact" in top_result["snippet"].lower()
            )

    def test_dispatcher_handles_special_queries(self, dispatcher, ctx):
        """Test dispatcher with special query patterns."""
        self.create_test_codebase(self.workspace)
        dispatcher.index_directory(ctx, self.workspace)

        special_queries = [
            "MyClass.process()",
            "pip install myproject",
            "import main",
            "__init__",
            "error handling",
        ]

        for query in special_queries:
            results = list(dispatcher.search(ctx, query, limit=5))
            assert isinstance(results, list)

    def test_dispatcher_cache_effectiveness(self, dispatcher, ctx):
        """Test that dispatcher caching improves performance."""
        for i in range(10):
            doc = self.workspace / f"cache_test_{i}.md"
            doc.write_text(f"# Cache Test {i}\n\nContent for caching test {i}.")

        dispatcher.index_directory(ctx, self.workspace)

        start_time = time.time()
        first_results = list(dispatcher.search(ctx, "cache test content", limit=20))
        first_time = time.time() - start_time

        start_time = time.time()
        second_results = list(dispatcher.search(ctx, "cache test content", limit=20))
        second_time = time.time() - start_time

        assert len(first_results) == len(second_results)
        logger.info(f"First search: {first_time:.3f}s, Second search: {second_time:.3f}s")

    def test_dispatcher_graceful_degradation(self, dispatcher, ctx):
        """Test dispatcher graceful degradation with system constraints."""
        large_content = "x" * 10000

        for i in range(20):
            doc = self.workspace / f"stress_{i}.md"
            doc.write_text(f"# Stress Test {i}\n\n{large_content}")

        dispatcher.index_directory(ctx, self.workspace)

        results = list(dispatcher.search(ctx, "stress test", limit=5))
        assert len(results) > 0

        long_query = " ".join([f"word{i}" for i in range(50)])
        long_results = list(dispatcher.search(ctx, long_query, limit=5))
        assert isinstance(long_results, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
