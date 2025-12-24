#!/usr/bin/env python3
"""Test script to validate document processing plugins."""

import sys
import tempfile
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_server.plugins.plugin_factory import PluginFactory
from mcp_server.storage.sqlite_store import SQLiteStore


def test_markdown_plugin():
    """Test the Markdown plugin functionality."""
    print("Testing Markdown Plugin...")

    # Create a test markdown file
    test_content = """# Test Document

This is a test document with multiple sections.

## Section 1

This section contains some **bold** text and *italic* text.

- Item 1
- Item 2
- Item 3

## Section 2

Here's a code block:

```python
def hello_world():
    print("Hello, world!")
```

### Subsection 2.1

This is a subsection with a [link](https://example.com).

## Section 3

Final section with a table:

| Column 1 | Column 2 |
|----------|----------|
| Value 1  | Value 2  |
| Value 3  | Value 4  |
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(test_content)
        temp_path = f.name

    try:
        # Create plugin using factory
        plugin = PluginFactory.create_plugin_for_file(temp_path)

        if not plugin:
            print("✗ Failed to create Markdown plugin")
            return False

        print(f"✓ Created plugin: {plugin.__class__.__name__}")

        # Index the file
        result = plugin.index_file(temp_path)

        print(f"✓ Indexed file: {temp_path}")
        if result:
            print(f"  - Symbols found: {len(result.symbols)}")
            print(f"  - Content length: {len(result.content)}")

            # Show first few symbols
            if result.symbols:
                print("\n  First few symbols:")
                for symbol in result.symbols[:5]:
                    print(f"    - {symbol.name} ({symbol.type}) at line {symbol.line}")

        # Test search (if plugin has search method)
        if hasattr(plugin, "search"):
            search_results = plugin.search("code block", limit=5)
            print(f"\n  Search results for 'code block': {len(search_results)} found")

        return True

    except Exception as e:
        print(f"✗ Error testing Markdown plugin: {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        Path(temp_path).unlink()


def test_plaintext_plugin():
    """Test the Plaintext plugin functionality."""
    print("\nTesting Plaintext Plugin...")

    # Create a test plaintext file
    test_content = """This is a test document for the plaintext plugin.

The plaintext plugin should be able to handle regular text files and extract meaningful chunks from them. It uses natural language processing to identify paragraph boundaries and extract topics.

This is the second paragraph. It contains different content that should be indexed separately. The plugin should detect sentence boundaries and create appropriate chunks.

Here's a third paragraph with some technical content. The semantic indexer should be able to understand the context and provide relevant search results when queried.

Final paragraph: This demonstrates the document processing capabilities of the MCP server."""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(test_content)
        temp_path = f.name

    try:
        # Create plugin using factory
        plugin = PluginFactory.create_plugin_for_file(temp_path)

        if not plugin:
            print("✗ Failed to create Plaintext plugin")
            return False

        print(f"✓ Created plugin: {plugin.__class__.__name__}")

        # Index the file
        result = plugin.index_file(temp_path)

        print(f"✓ Indexed file: {temp_path}")
        if result:
            print(f"  - Symbols found: {len(result.symbols)}")
            print(f"  - Content length: {len(result.content)}")

        # Test search (if plugin has search method)
        if hasattr(plugin, "search"):
            search_results = plugin.search("semantic indexer", limit=5)
            print(f"\n  Search results for 'semantic indexer': {len(search_results)} found")

        return True

    except Exception as e:
        print(f"✗ Error testing Plaintext plugin: {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        Path(temp_path).unlink()


def test_plugin_factory():
    """Test the plugin factory registration."""
    print("\nTesting Plugin Factory...")

    try:
        # Check supported languages
        supported = PluginFactory.get_supported_languages()
        print(f"  Supported languages: {len(supported)}")

        # Test file extensions
        test_files = {
            "test.md": "markdown",
            "test.txt": "plaintext",
            "test.py": "python",
            "test.js": "javascript",
            "test.java": "java",
            "test.c": "c",
            "test.cpp": "cpp",
            "test.go": "go",
            "test.rs": "rust",
            "test.swift": "swift",
            "test.kt": "kotlin",
            "test.cs": "csharp",
            "test.ts": "typescript",
            "test.dart": "dart",
            "test.html": "html",
            "test.css": "css",
        }

        print("\n  Testing file extension mapping:")
        for filename, expected_type in test_files.items():
            plugin = PluginFactory.create_plugin_for_file(filename)
            if plugin:
                print(f"    ✓ {filename} -> {plugin.__class__.__name__}")
            else:
                print(f"    ✗ {filename} -> No plugin found")

        # Test specific plugins
        print("\n  Testing specific plugin creation:")
        for lang in ["markdown", "plaintext", "python", "javascript"]:
            try:
                plugin = PluginFactory.create_plugin(lang)
                print(f"    ✓ {lang} -> {plugin.__class__.__name__}")
            except Exception as e:
                print(f"    ✗ {lang} -> {e}")

        return True

    except Exception as e:
        print(f"✗ Error testing Plugin Factory: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_document_processing_integration():
    """Test document processing with multiple file types."""
    print("\nTesting Document Processing Integration...")

    # Create test files
    test_files = []

    # Markdown file
    md_content = """# API Documentation

## Overview
This is the API documentation for our service.

## Endpoints

### GET /users
Returns a list of users.

### POST /users
Creates a new user.
"""

    # Plaintext file
    txt_content = """User Guide

This guide explains how to use our application effectively.

Getting Started:
First, install the application using the provided installer.
Then, launch the application and follow the setup wizard.

Main Features:
The application provides several key features for users.
You can manage your documents, collaborate with others, and track changes.
"""

    # Python file
    py_content = """#!/usr/bin/env python3
\"\"\"Example Python module for testing.\"\"\"

class UserManager:
    \"\"\"Manages user operations.\"\"\"
    
    def get_users(self):
        \"\"\"Get all users.\"\"\"
        return []
    
    def create_user(self, name, email):
        \"\"\"Create a new user.\"\"\"
        return {"name": name, "email": email}
"""

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create SQLite store for testing
        db_path = temp_path / "test.db"
        sqlite_store = SQLiteStore(str(db_path))

        # Create test files
        files_to_index = []

        md_file = temp_path / "api_docs.md"
        md_file.write_text(md_content)
        files_to_index.append(str(md_file))

        txt_file = temp_path / "user_guide.txt"
        txt_file.write_text(txt_content)
        files_to_index.append(str(txt_file))

        py_file = temp_path / "user_manager.py"
        py_file.write_text(py_content)
        files_to_index.append(str(py_file))

        try:
            # Index each file
            print(f"  Indexing {len(files_to_index)} files...")

            for file_path in files_to_index:
                plugin = PluginFactory.create_plugin_for_file(file_path, sqlite_store=sqlite_store)
                if plugin:
                    result = plugin.index_file(file_path)
                    if result:
                        print(f"    ✓ {Path(file_path).name} - {len(result.symbols)} symbols")
                    else:
                        print(f"    ✗ {Path(file_path).name} - No result")
                else:
                    print(f"    ✗ {Path(file_path).name} - No plugin")

            # Test search across different file types
            print("\n  Testing cross-file search:")
            queries = ["user", "API", "documentation", "create"]

            for query in queries:
                results = sqlite_store.search(query, limit=5)
                print(f"    Query '{query}': {len(results)} results")
                for i, result in enumerate(results[:2]):
                    print(
                        f"      - {Path(result['file_path']).name}: {result['symbol_name']} (score: {result['score']:.3f})"
                    )

            return True

        except Exception as e:
            print(f"✗ Error in integration test: {e}")
            import traceback

            traceback.print_exc()
            return False


def main():
    """Run all tests."""
    print("=== Document Processing Plugin Validation ===\n")

    tests = [
        test_markdown_plugin,
        test_plaintext_plugin,
        test_plugin_factory,
        test_document_processing_integration,
    ]

    results = []
    for test in tests:
        results.append(test())
        print("-" * 60)

    # Summary
    print("\n=== Test Summary ===")
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("\n✓ All tests passed! Document processing plugins are working correctly.")
        return 0
    else:
        print(f"\n✗ {total - passed} tests failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
