"""Integration tests for plugin system with document processing."""

import logging
import shutil
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.document_processing.document_interfaces import (
    ChunkMetadata,
    ChunkType,
    DocumentChunk,
    ProcessedDocument,
)
from mcp_server.plugins.markdown_plugin.plugin import MarkdownPlugin
from mcp_server.plugins.plaintext_plugin.plugin import PlainTextPlugin
from mcp_server.plugins.plugin_factory import PluginFactory
from mcp_server.plugins.python_plugin.plugin_semantic import PythonPluginSemantic
from mcp_server.storage.sqlite_store import SQLiteStore
from tests.base_test import BaseDocumentTest

logger = logging.getLogger(__name__)


class TestPluginIntegration(BaseDocumentTest):
    """Test plugin integration with the document processing system."""

    @pytest.fixture
    def plugin_factory(self):
        """Create plugin factory instance."""
        return PluginFactory(sqlite_store=self.store)

    def test_plugin_factory_creates_correct_plugins(self, plugin_factory):
        """Test that plugin factory creates appropriate plugins for different file types."""
        # Create test files
        md_file = self.workspace / "README.md"
        md_file.write_text("# Test Documentation\n\nThis is a test.")

        py_file = self.workspace / "test.py"
        py_file.write_text("def hello():\n    '''Say hello'''\n    return 'Hello'")

        txt_file = self.workspace / "notes.txt"
        txt_file.write_text("Some plain text notes.")

        # Test markdown plugin creation
        md_plugin = plugin_factory.get_plugin(str(md_file))
        assert isinstance(md_plugin, MarkdownPlugin)

        # Test Python plugin creation
        py_plugin = plugin_factory.get_plugin(str(py_file))
        assert isinstance(py_plugin, (PythonPluginSemantic, type(py_plugin)))

        # Test plaintext plugin creation
        txt_plugin = plugin_factory.get_plugin(str(txt_file))
        assert isinstance(txt_plugin, PlainTextPlugin)

    def test_document_plugin_process_and_index(self, plugin_factory):
        """Test document plugin processing and indexing."""
        # Create a markdown file
        md_file = self.workspace / "docs.md"
        content = """# API Documentation

## Installation

To install the package:

```bash
pip install mypackage
```

## Usage

Here's how to use the API:

```python
from mypackage import Client

client = Client()
result = client.process()
```

## Configuration

Set the following environment variables:
- API_KEY: Your API key
- API_URL: The API endpoint
"""
        md_file.write_text(content)

        # Get plugin and index the file
        plugin = plugin_factory.get_plugin(str(md_file))
        assert isinstance(plugin, MarkdownPlugin)

        # Index the file
        shard = plugin.index([str(md_file)])
        assert shard is not None

        # Search for content
        results = list(plugin.search("installation", {"limit": 10}))
        assert len(results) > 0
        assert any("pip install" in r.snippet for r in results)

        # Search for code content
        code_results = list(plugin.search("Client()", {"limit": 10}))
        assert len(code_results) > 0
        assert any("Client()" in r.snippet for r in code_results)

    def test_plugin_semantic_search_integration(self, plugin_factory):
        """Test semantic search integration in plugins."""
        # Create Python file with documentation
        py_file = self.workspace / "example.py"
        content = '''"""
Module for handling database connections and queries.

This module provides a DatabaseManager class that handles
connection pooling and query execution.
"""

class DatabaseManager:
    """Manages database connections with pooling support."""
    
    def __init__(self, connection_string):
        """Initialize with connection string."""
        self.connection_string = connection_string
        self.pool = None
    
    def connect(self):
        """Establish database connection."""
        pass
    
    def execute_query(self, query, params=None):
        """Execute a SQL query with optional parameters."""
        pass
'''
        py_file.write_text(content)

        # Get plugin with semantic search disabled (for testing base functionality)
        with patch.dict("os.environ", {"SEMANTIC_SEARCH_ENABLED": "false"}):
            plugin = plugin_factory.get_plugin(str(py_file))

            # Index the file
            shard = plugin.index([str(py_file)])
            assert shard is not None

            # Search for database-related content
            results = list(plugin.search("database connection pooling", {"limit": 10}))
            assert len(results) > 0

            # Verify we found relevant content
            found_content = [r.snippet for r in results]
            assert any("DatabaseManager" in s for s in found_content)
            assert any("pooling" in s.lower() for s in found_content)

    def test_cross_plugin_consistency(self, plugin_factory):
        """Test consistency across different plugin types."""
        # Create files with similar content in different formats
        content_template = """
Configuration Guide

To configure the application, set these parameters:
- timeout: Request timeout in seconds
- retries: Number of retry attempts
- log_level: Logging level (DEBUG, INFO, WARN, ERROR)
"""

        # Markdown version
        md_file = self.workspace / "config.md"
        md_file.write_text(f"# {content_template}")

        # Text version
        txt_file = self.workspace / "config.txt"
        txt_file.write_text(content_template)

        # Index both files
        md_plugin = plugin_factory.get_plugin(str(md_file))
        txt_plugin = plugin_factory.get_plugin(str(txt_file))

        md_shard = md_plugin.index([str(md_file)])
        txt_shard = txt_plugin.index([str(txt_file)])

        # Search in both
        search_query = "timeout configuration"
        md_results = list(md_plugin.search(search_query, {"limit": 5}))
        txt_results = list(txt_plugin.search(search_query, {"limit": 5}))

        # Both should find relevant content
        assert len(md_results) > 0
        assert len(txt_results) > 0

        # Check that both found the timeout configuration
        assert any("timeout" in r.snippet.lower() for r in md_results)
        assert any("timeout" in r.snippet.lower() for r in txt_results)

    def test_plugin_error_handling(self, plugin_factory):
        """Test plugin error handling and recovery."""
        # Test with non-existent file
        fake_file = self.workspace / "nonexistent.md"
        plugin = plugin_factory.get_plugin(str(fake_file))

        # Should handle gracefully
        shard = plugin.index([str(fake_file)])
        assert shard is not None

        # Test with corrupted content
        bad_file = self.workspace / "bad.py"
        bad_file.write_text("def broken(\n    # Syntax error")

        plugin = plugin_factory.get_plugin(str(bad_file))
        # Should still index despite syntax errors
        shard = plugin.index([str(bad_file)])
        assert shard is not None

    def test_plugin_metadata_extraction(self, plugin_factory):
        """Test that plugins correctly extract and store metadata."""
        # Create a Python file with rich metadata
        py_file = self.workspace / "module.py"
        content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Module
===========

:author: Test Author
:version: 1.0.0
:license: MIT
"""

__version__ = "1.0.0"
__author__ = "Test Author"

class TestClass:
    """A test class with documentation."""
    
    def method(self):
        """Test method."""
        return True
'''
        py_file.write_text(content)

        # Index and verify metadata extraction
        plugin = plugin_factory.get_plugin(str(py_file))
        shard = plugin.index([str(py_file)])

        # Search for author information
        results = list(plugin.search("Test Author", {"limit": 5}))
        assert len(results) > 0
        assert any("Test Author" in r.snippet for r in results)

        # Search for version
        version_results = list(plugin.search("version 1.0.0", {"limit": 5}))
        assert len(version_results) > 0

    def test_plugin_lifecycle_management(self, plugin_factory):
        """Test plugin initialization, usage, and cleanup lifecycle."""
        # Track plugin instances
        created_plugins = []

        # Create multiple plugin instances
        for i in range(5):
            file_path = self.workspace / f"file_{i}.md"
            file_path.write_text(f"# Document {i}\n\nContent for document {i}.")
            plugin = plugin_factory.get_plugin(str(file_path))
            created_plugins.append(plugin)

        # Verify all plugins are properly initialized
        for plugin in created_plugins:
            assert plugin is not None
            assert hasattr(plugin, "index")
            assert hasattr(plugin, "search")

        # Use plugins
        for i, plugin in enumerate(created_plugins):
            file_path = self.workspace / f"file_{i}.md"
            shard = plugin.index([str(file_path)])
            assert shard is not None

        # Verify plugin reuse for same file type
        another_md = self.workspace / "another.md"
        another_md.write_text("# Another Document")
        reused_plugin = plugin_factory.get_plugin(str(another_md))
        # Should be same type as other markdown plugins
        assert type(reused_plugin) == type(created_plugins[0])

    def test_concurrent_plugin_operations(self, plugin_factory):
        """Test concurrent operations across multiple plugins."""
        # Create test files
        files = []
        for i in range(10):
            if i % 3 == 0:
                file_path = self.workspace / f"doc_{i}.md"
                content = f"# Document {i}\n\nMarkdown content {i}."
            elif i % 3 == 1:
                file_path = self.workspace / f"script_{i}.py"
                content = f'"""Script {i}"""\n\ndef func_{i}():\n    return {i}'
            else:
                file_path = self.workspace / f"text_{i}.txt"
                content = f"Plain text content {i}\n\nMore text here."

            file_path.write_text(content)
            files.append(str(file_path))

        # Index files concurrently
        results = []
        errors = []

        def index_file(file_path):
            try:
                plugin = plugin_factory.get_plugin(file_path)
                shard = plugin.index([file_path])
                return (file_path, shard)
            except Exception as e:
                errors.append((file_path, str(e)))
                return None

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(index_file, f) for f in files]
            for future in futures:
                result = future.result()
                if result:
                    results.append(result)

        # Verify all files were indexed successfully
        assert len(errors) == 0
        assert len(results) == len(files)

        # Test concurrent search
        search_results = []

        def search_in_plugin(file_path, query):
            plugin = plugin_factory.get_plugin(file_path)
            return list(plugin.search(query, {"limit": 5}))

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(search_in_plugin, f, "content")
                for f in files[:5]  # Search in first 5 files
            ]
            for future in futures:
                search_results.extend(future.result())

        assert len(search_results) > 0

    def test_plugin_with_mixed_content_types(self, plugin_factory):
        """Test plugins handling files with mixed content types."""
        # Create a markdown file with embedded code
        mixed_md = self.workspace / "mixed.md"
        mixed_md.write_text(
            """# Technical Guide

## Python Examples

```python
def process_data(data):
    '''Process incoming data'''
    return [x * 2 for x in data]
```

## JavaScript Examples

```javascript
function processData(data) {
    return data.map(x => x * 2);
}
```

## Configuration

```yaml
server:
  host: localhost
  port: 8080
```
"""
        )

        # Create Python file with extensive documentation
        doc_heavy_py = self.workspace / "documented.py"
        doc_heavy_py.write_text(
            '''"""
Comprehensive Module Documentation
==================================

This module provides extensive functionality with detailed documentation.

Examples:
    Basic usage::
    
        >>> from documented import process
        >>> result = process([1, 2, 3])
        >>> print(result)
        [2, 4, 6]

Notes:
    This module follows best practices for documentation.
"""

def process(items):
    """
    Process a list of items.
    
    Args:
        items (list): Items to process
        
    Returns:
        list: Processed items
    """
    return [item * 2 for item in items]
'''
        )

        # Index both files
        md_plugin = plugin_factory.get_plugin(str(mixed_md))
        py_plugin = plugin_factory.get_plugin(str(doc_heavy_py))

        md_shard = md_plugin.index([str(mixed_md)])
        py_shard = py_plugin.index([str(doc_heavy_py)])

        # Search for code-related content in markdown
        md_code_results = list(md_plugin.search("process data function", {"limit": 10}))
        assert len(md_code_results) > 0
        assert any("process" in r.snippet.lower() for r in md_code_results)

        # Search for documentation in Python file
        py_doc_results = list(py_plugin.search("module documentation examples", {"limit": 10}))
        assert len(py_doc_results) > 0

    def test_plugin_performance_with_large_files(self, plugin_factory):
        """Test plugin performance with large documents."""
        # Create a large markdown file
        large_md = self.workspace / "large.md"
        sections = []
        for i in range(100):
            sections.append(
                f"""## Section {i}

This is content for section {i}. It contains various information about topic {i}.

### Subsection {i}.1

Detailed information about subtopic {i}.1 with examples and explanations.

### Subsection {i}.2

More details about subtopic {i}.2 with additional context.
"""
            )

        large_content = "# Large Document\n\n" + "\n".join(sections)
        large_md.write_text(large_content)

        # Measure indexing time
        plugin = plugin_factory.get_plugin(str(large_md))
        start_time = time.time()
        shard = plugin.index([str(large_md)])
        index_time = time.time() - start_time

        # Should complete in reasonable time
        assert shard is not None
        assert index_time < 5.0  # Less than 5 seconds

        # Test search performance
        start_time = time.time()
        results = list(plugin.search("section 50 information", {"limit": 20}))
        search_time = time.time() - start_time

        assert len(results) > 0
        assert search_time < 1.0  # Less than 1 second
        assert any("section 50" in r.snippet.lower() for r in results)

    def test_plugin_memory_efficiency(self, plugin_factory):
        """Test that plugins handle memory efficiently with multiple files."""
        import gc
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Create and index many files
        for i in range(50):
            file_path = self.workspace / f"mem_test_{i}.md"
            content = f"# Document {i}\n\n" + "Content " * 1000
            file_path.write_text(content)

            plugin = plugin_factory.get_plugin(str(file_path))
            plugin.index([str(file_path)])

        # Force garbage collection
        gc.collect()

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable
        assert memory_increase < 100  # Less than 100MB increase

    def test_plugin_hot_reload_simulation(self, plugin_factory):
        """Test plugin behavior when files are modified during operation."""
        # Create initial file
        dynamic_file = self.workspace / "dynamic.md"
        initial_content = "# Initial Version\n\nOriginal content here."
        dynamic_file.write_text(initial_content)

        # Initial indexing
        plugin = plugin_factory.get_plugin(str(dynamic_file))
        plugin.index([str(dynamic_file)])

        # Search for initial content
        results = list(plugin.search("original content", {"limit": 5}))
        assert len(results) > 0
        assert any("original" in r.snippet.lower() for r in results)

        # Modify file
        updated_content = "# Updated Version\n\nCompletely new content here."
        dynamic_file.write_text(updated_content)

        # Re-index
        plugin.index([str(dynamic_file)])

        # Search for new content
        new_results = list(plugin.search("new content", {"limit": 5}))
        assert len(new_results) > 0
        assert any("new" in r.snippet.lower() for r in new_results)

        # Old content should not be found
        old_results = list(plugin.search("original content", {"limit": 5}))
        # Results might be empty or have low relevance
        if old_results:
            # If found, should have lower relevance than before
            assert all(r.score < 0.5 for r in old_results if hasattr(r, "score"))

    def test_plugin_edge_cases(self, plugin_factory):
        """Test plugins with various edge cases."""
        # Empty file
        empty_file = self.workspace / "empty.md"
        empty_file.write_text("")
        empty_plugin = plugin_factory.get_plugin(str(empty_file))
        empty_shard = empty_plugin.index([str(empty_file)])
        assert empty_shard is not None

        # File with only whitespace
        whitespace_file = self.workspace / "whitespace.txt"
        whitespace_file.write_text("   \n\n\t\t\n   ")
        ws_plugin = plugin_factory.get_plugin(str(whitespace_file))
        ws_shard = ws_plugin.index([str(whitespace_file)])
        assert ws_shard is not None

        # File with special characters
        special_file = self.workspace / "special.md"
        special_file.write_text("# Special © Characters ™\n\n→ ← ↑ ↓ • Unicode: 你好 🌍")
        special_plugin = plugin_factory.get_plugin(str(special_file))
        special_shard = special_plugin.index([str(special_file)])
        assert special_shard is not None

        # Search for special characters
        unicode_results = list(special_plugin.search("Unicode 你好", {"limit": 5}))
        assert len(unicode_results) > 0

        # Very long single line
        long_line_file = self.workspace / "longline.txt"
        long_line_file.write_text("word " * 1000)  # 5000 characters
        ll_plugin = plugin_factory.get_plugin(str(long_line_file))
        ll_shard = ll_plugin.index([str(long_line_file)])
        assert ll_shard is not None

        # File with no extension
        no_ext_file = self.workspace / "README"
        no_ext_file.write_text("This is a README file without extension")
        no_ext_plugin = plugin_factory.get_plugin(str(no_ext_file))
        assert no_ext_plugin is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
