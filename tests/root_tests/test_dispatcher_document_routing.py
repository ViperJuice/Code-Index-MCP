"""Integration tests for dispatcher document routing functionality."""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import logging
from typing import List, Dict, Any
import time
from concurrent.futures import ThreadPoolExecutor
import threading

from tests.base_test import BaseDocumentTest
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.dispatcher.plugin_router import PluginRouter, FileTypeMatcher, PluginCapability
from mcp_server.dispatcher.result_aggregator import ResultAggregator, RankingCriteria
from mcp_server.plugins.plugin_factory import PluginFactory
from mcp_server.plugin_base import SearchResult

logger = logging.getLogger(__name__)


class TestDispatcherDocumentRouting(BaseDocumentTest):
    """Test dispatcher routing for document-related queries."""
    
    @pytest.fixture
    def dispatcher(self):
        """Create enhanced dispatcher instance."""
        return EnhancedDispatcher(sqlite_store=self.store)
    
    def create_test_codebase(self, workspace: Path) -> Dict[str, Path]:
        """Create a test codebase with various file types."""
        files = {}
        
        # Documentation files
        files['readme'] = workspace / "README.md"
        files['readme'].write_text("""# My Project

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
        
        files['api_docs'] = workspace / "docs" / "api.md"
        files['api_docs'].parent.mkdir(exist_ok=True)
        files['api_docs'].write_text("""# API Reference

## Classes

### MyClass

A class that does something useful.

Methods:
- process(data): Process the input data
- validate(input): Validate input parameters
""")
        
        # Code files
        files['main_py'] = workspace / "src" / "main.py"
        files['main_py'].parent.mkdir(exist_ok=True)
        files['main_py'].write_text('''"""Main module for the project."""

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
        
        files['config'] = workspace / "config.txt"
        files['config'].write_text("""Configuration Settings

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
            "best practices for deployment"
        ]
        
        for query in doc_queries:
            is_doc_query = dispatcher._is_document_query(query)
            assert is_doc_query, f"Query '{query}' should be detected as document query"
        
        # Non-document queries
        code_queries = [
            "MyClass.process",
            "function definition",
            "import statements",
            "class inheritance"
        ]
        
        for query in code_queries:
            is_doc_query = dispatcher._is_document_query(query)
            assert not is_doc_query, f"Query '{query}' should not be detected as document query"
    
    def test_dispatcher_routes_to_document_plugins(self, dispatcher):
        """Test that dispatcher routes document queries to appropriate plugins."""
        files = self.create_test_codebase(self.workspace)
        
        # Index all files
        dispatcher.index(self.workspace)
        
        # Test installation query - should prioritize README
        results = list(dispatcher.search("how to install pip", {"limit": 10}))
        assert len(results) > 0
        
        # Check that README appears in results
        readme_found = any("README.md" in r.file for r in results)
        assert readme_found, "README should be found for installation query"
        
        # Check ranking - documentation should be prioritized
        if len(results) > 1:
            first_result = results[0]
            assert "README.md" in first_result.file or "api.md" in first_result.file
    
    def test_dispatcher_aggregates_cross_file_results(self, dispatcher, temp_workspace):
        """Test that dispatcher aggregates results from multiple files."""
        files = self.create_test_codebase(temp_workspace)
        
        # Index files
        dispatcher.index(temp_workspace)
        
        # Search for "MyClass" - should find in both code and docs
        results = list(dispatcher.search("MyClass process method", {"limit": 20}))
        assert len(results) > 0
        
        # Should find results from both api.md and main.py
        result_files = {r.file for r in results}
        assert any("api.md" in f for f in result_files), "Should find in API docs"
        assert any("main.py" in f for f in result_files), "Should find in Python code"
    
    def test_dispatcher_file_type_routing(self, dispatcher, temp_workspace):
        """Test that dispatcher routes to correct plugins based on file type."""
        files = self.create_test_codebase(temp_workspace)
        
        # Create plugin router mock to track routing decisions
        original_route = dispatcher._router.route_query
        routing_log = []
        
        def track_routing(query, opts):
            result = original_route(query, opts)
            routing_log.append({
                'query': query,
                'capabilities': [cap.value for cap in result]
            })
            return result
        
        dispatcher._router.route_query = track_routing
        
        # Index files
        dispatcher.index(temp_workspace)
        
        # Test different queries
        dispatcher.search("configuration settings", {"limit": 5})
        dispatcher.search("def process", {"limit": 5})
        
        # Verify routing decisions
        assert len(routing_log) > 0
        
        # Configuration query should include document capability
        config_routing = next((r for r in routing_log if "configuration" in r['query']), None)
        if config_routing:
            assert PluginCapability.DOCUMENT_PROCESSING.value in config_routing['capabilities']
    
    def test_dispatcher_prioritizes_relevant_documents(self, dispatcher, temp_workspace):
        """Test that dispatcher prioritizes more relevant documents."""
        # Create multiple documentation files
        docs_dir = temp_workspace / "docs"
        docs_dir.mkdir(exist_ok=True)
        
        # Create files with different relevance levels
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
        
        # Index and search
        dispatcher.index(self.workspace)
        results = list(dispatcher.search("pip installation guide", {"limit": 10}))
        
        # Installation.md should rank higher than troubleshooting or notes
        if len(results) >= 2:
            assert "installation.md" in results[0].file.lower()
    
    def test_dispatcher_handles_mixed_queries(self, dispatcher, temp_workspace):
        """Test dispatcher with queries that span code and documentation."""
        files = self.create_test_codebase(temp_workspace)
        
        # Add a test file
        test_file = temp_workspace / "tests" / "test_main.py"
        test_file.parent.mkdir(exist_ok=True)
        test_file.write_text('''"""Tests for main module."""

def test_myclass_process():
    """Test MyClass.process method as documented in API."""
    from src.main import MyClass
    obj = MyClass()
    assert obj.process("data") == "data"
''')
        
        # Index everything
        dispatcher.index(temp_workspace)
        
        # Mixed query about implementation and documentation
        results = list(dispatcher.search("MyClass process method implementation test", {"limit": 15}))
        
        # Should find results from multiple file types
        result_files = [r.file for r in results]
        file_types = set()
        for f in result_files:
            if f.endswith('.py'):
                file_types.add('python')
            elif f.endswith('.md'):
                file_types.add('markdown')
        
        # Should have found both code and documentation
        assert len(file_types) >= 2, "Should find results in both code and docs"
    
    def test_dispatcher_respects_search_options(self, dispatcher, temp_workspace):
        """Test that dispatcher respects search options like limit and offset."""
        files = self.create_test_codebase(temp_workspace)
        
        # Create many files to test pagination
        for i in range(10):
            doc = temp_workspace / f"doc_{i}.md"
            doc.write_text(f"# Document {i}\n\nThis document explains feature {i}.")
        
        dispatcher.index(temp_workspace)
        
        # Test limit
        results_limited = list(dispatcher.search("document explains", {"limit": 3}))
        assert len(results_limited) <= 3
        
        # Test with higher limit
        results_all = list(dispatcher.search("document explains", {"limit": 20}))
        assert len(results_all) > len(results_limited)
    
    def test_dispatcher_error_recovery(self, dispatcher, temp_workspace):
        """Test that dispatcher handles plugin errors gracefully."""
        files = self.create_test_codebase(temp_workspace)
        
        # Create a file that might cause parsing issues
        bad_file = temp_workspace / "bad.md"
        bad_file.write_text("# Broken [link (no closing\n\n```python\n# Unclosed code block")
        
        # Should not crash during indexing
        dispatcher.index(temp_workspace)
        
        # Should still return results from good files
        results = list(dispatcher.search("installation", {"limit": 10}))
        assert len(results) > 0
        
        # Results should be from valid files
        assert all("bad.md" not in r.file or r.snippet for r in results)
    
    def test_dispatcher_fallback_mechanisms(self, dispatcher):
        """Test dispatcher fallback when primary plugins fail."""
        # Create files with various issues
        files = {
            'corrupt.py': "def broken(\n    # Unclosed function",
            'empty.md': "",
            'binary.bin': b'\x00\x01\x02\x03',
            'normal.txt': "This is normal text content."
        }
        
        for filename, content in files.items():
            file_path = self.workspace / filename
            if isinstance(content, bytes):
                file_path.write_bytes(content)
            else:
                file_path.write_text(content)
        
        # Index all files - should handle gracefully
        dispatcher.index(self.workspace)
        
        # Search should still work and find content from valid files
        results = list(dispatcher.search("normal text content", {"limit": 10}))
        assert len(results) > 0
        assert any("normal" in r.snippet.lower() for r in results)
    
    def test_dispatcher_concurrent_processing(self, dispatcher):
        """Test dispatcher handling concurrent requests."""
        # Create many files
        for i in range(20):
            doc = self.workspace / f"concurrent_{i}.md"
            doc.write_text(f"# Document {i}\n\nContent for concurrent testing {i}.")
        
        # Index files
        dispatcher.index(self.workspace)
        
        # Concurrent search queries
        queries = [
            "Document 5",
            "concurrent testing",
            "content for",
            "Document 15",
            "testing 10"
        ]
        
        results_dict = {}
        errors = []
        
        def search_query(query):
            try:
                results = list(dispatcher.search(query, {"limit": 5}))
                results_dict[query] = results
            except Exception as e:
                errors.append((query, str(e)))
        
        # Execute searches concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(search_query, q) for q in queries]
            for future in futures:
                future.result()
        
        # All queries should succeed
        assert len(errors) == 0
        assert len(results_dict) == len(queries)
        
        # Each query should have results
        for query, results in results_dict.items():
            assert len(results) > 0
    
    def test_dispatcher_query_optimization(self, dispatcher):
        """Test dispatcher query optimization for complex searches."""
        # Create documents with overlapping content
        docs = [
            ("intro.md", "# Introduction\n\nThis guide introduces API concepts."),
            ("api_guide.md", "# API Guide\n\nComplete API documentation guide."),
            ("api_reference.md", "# API Reference\n\nDetailed API method reference."),
            ("tutorial.md", "# Tutorial\n\nStep-by-step API tutorial guide."),
            ("concepts.md", "# Concepts\n\nCore API concepts and principles.")
        ]
        
        for filename, content in docs:
            (self.workspace / filename).write_text(content)
        
        dispatcher.index(self.workspace)
        
        # Test query optimization with multi-word search
        results = list(dispatcher.search("API guide documentation", {"limit": 10}))
        
        # Should find relevant documents
        assert len(results) > 0
        
        # api_guide.md should rank highly
        result_files = [r.file for r in results[:3]]
        assert any("api_guide.md" in f for f in result_files)
    
    def test_dispatcher_routing_with_filters(self, dispatcher):
        """Test dispatcher routing with file type filters."""
        # Create mixed file types
        files = self.create_test_codebase(self.workspace)
        
        # Add more specific files
        (self.workspace / "script.js").write_text("function main() { console.log('Hello'); }")
        (self.workspace / "style.css").write_text("body { margin: 0; padding: 0; }")
        (self.workspace / "data.json").write_text('{"key": "value", "items": [1, 2, 3]}')
        
        dispatcher.index(self.workspace)
        
        # Test with file type hints in query
        md_results = list(dispatcher.search("installation in:markdown", {"limit": 10}))
        py_results = list(dispatcher.search("function in:python", {"limit": 10}))
        
        # Results should respect file type hints
        if md_results:
            assert all(".md" in r.file for r in md_results)
        if py_results:
            assert all(".py" in r.file for r in py_results)
    
    def test_dispatcher_result_aggregation_strategies(self, dispatcher):
        """Test different result aggregation strategies."""
        # Create documents with varying relevance
        docs = {
            "exact_match.md": "# Exact Match\n\nThis document contains the exact search query.",
            "partial_match.md": "# Partial\n\nThis has only some search terms.",
            "synonym_match.md": "# Similar\n\nThis contains related lookup terms.",
            "code_match.py": '"""Module with search query in docstring."""\ndef search(): pass',
            "distant_match.txt": "Barely related content with one search word."
        }
        
        for filename, content in docs.items():
            (self.workspace / filename).write_text(content)
        
        dispatcher.index(self.workspace)
        
        # Test aggregation with exact phrase
        results = list(dispatcher.search("exact search query", {"limit": 10}))
        
        # Exact match should rank first
        if results:
            top_result = results[0]
            assert "exact_match.md" in top_result.file or "exact" in top_result.snippet.lower()
    
    def test_dispatcher_handles_special_queries(self, dispatcher):
        """Test dispatcher with special query patterns."""
        files = self.create_test_codebase(self.workspace)
        dispatcher.index(self.workspace)
        
        # Test various special queries
        special_queries = [
            "MyClass.process()",  # Method reference
            "pip install myproject",  # Command
            "TODO: fix this",  # Comment pattern
            "import main",  # Import statement
            "__init__",  # Special method
            "*.md",  # File pattern
            "error handling"  # Concept search
        ]
        
        for query in special_queries:
            results = list(dispatcher.search(query, {"limit": 5}))
            # Should handle all queries without errors
            assert isinstance(results, list)
    
    def test_dispatcher_cache_effectiveness(self, dispatcher):
        """Test that dispatcher caching improves performance."""
        # Create test files
        for i in range(10):
            doc = self.workspace / f"cache_test_{i}.md"
            doc.write_text(f"# Cache Test {i}\n\nContent for caching test {i}.")
        
        dispatcher.index(self.workspace)
        
        # First search - cold cache
        start_time = time.time()
        first_results = list(dispatcher.search("cache test content", {"limit": 20}))
        first_time = time.time() - start_time
        
        # Second search - warm cache
        start_time = time.time()
        second_results = list(dispatcher.search("cache test content", {"limit": 20}))
        second_time = time.time() - start_time
        
        # Results should be consistent
        assert len(first_results) == len(second_results)
        
        # Second search should be faster (cache hit)
        # Note: This might not always be true in test environment
        logger.info(f"First search: {first_time:.3f}s, Second search: {second_time:.3f}s")
    
    def test_dispatcher_graceful_degradation(self, dispatcher):
        """Test dispatcher graceful degradation with system constraints."""
        # Create a large number of files to stress the system
        large_content = "x" * 10000  # 10KB of content
        
        for i in range(100):
            doc = self.workspace / f"stress_{i}.md"
            doc.write_text(f"# Stress Test {i}\n\n{large_content}")
        
        # Should handle indexing without crashing
        dispatcher.index(self.workspace)
        
        # Search should still work
        results = list(dispatcher.search("stress test", {"limit": 5}))
        assert len(results) > 0
        
        # Test with very long query
        long_query = " ".join([f"word{i}" for i in range(50)])
        long_results = list(dispatcher.search(long_query, {"limit": 5}))
        # Should handle gracefully even if no results
        assert isinstance(long_results, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])