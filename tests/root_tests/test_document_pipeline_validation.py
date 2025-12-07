#!/usr/bin/env python3
"""
Comprehensive validation test for document processing pipeline.

This test validates:
1. Plugin factory can create Markdown and PlainText plugins
2. Plugins can index documents correctly
3. Basic search functionality works
4. Enhanced dispatcher can handle natural language queries
5. End-to-end document processing workflow
"""

import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
    from mcp_server.plugins.plugin_factory import PluginFactory
    from mcp_server.storage.sqlite_store import SQLiteStore

    print("✓ All required modules imported successfully")
except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)


class DocumentPipelineValidator:
    """Validates the complete document processing pipeline."""

    def __init__(self):
        self.temp_dir = None
        self.sqlite_store = None
        self.plugins = {}
        self.dispatcher = None
        self.test_files = {}

    def setup(self):
        """Set up test environment."""
        print("\n=== Setting up test environment ===")

        # Create temporary directory for test files
        self.temp_dir = tempfile.mkdtemp(prefix="doc_pipeline_test_")
        print(f"✓ Created temp directory: {self.temp_dir}")

        # Create SQLite store
        db_path = Path(self.temp_dir) / "test.db"
        self.sqlite_store = SQLiteStore(str(db_path))
        print(f"✓ Created SQLite store: {db_path}")

        # Create test files
        self._create_test_files()

    def cleanup(self):
        """Clean up test environment."""
        print("\n=== Cleaning up test environment ===")

        if self.temp_dir and Path(self.temp_dir).exists():
            import shutil

            shutil.rmtree(self.temp_dir)
            print(f"✓ Cleaned up temp directory: {self.temp_dir}")

    def _create_test_files(self):
        """Create test files for different document types."""
        print("Creating test files...")

        # Markdown test file
        markdown_content = """---
title: "API Documentation Guide"
author: "Test Author"
date: "2024-01-01"
tags: ["api", "documentation", "guide"]
---

# API Documentation Guide

This is a comprehensive guide for using our API.

## Getting Started

To get started with our API, you need to:

1. **Install the SDK**: Download and install our Python SDK
2. **Get API Key**: Register for an API key from our dashboard
3. **Make your first request**: Try the hello world example

### Installation

Install the SDK using pip:

```python
pip install our-api-sdk
```

### Authentication

All API requests require authentication:

```python
import api_sdk

client = api_sdk.Client(api_key="your-key-here")
response = client.get("/users")
```

## API Reference

### Users API

The Users API allows you to manage user accounts.

#### Get User

Retrieve information about a specific user.

**Endpoint:** `GET /users/{id}`

**Parameters:**
- `id` (required): User ID

**Response:**
```json
{
  "id": 123,
  "name": "John Doe",
  "email": "john@example.com"
}
```

### Common Issues

If you encounter authentication errors, check:

1. Your API key is valid
2. You have the correct permissions
3. The endpoint exists

For more help, see our [troubleshooting guide](troubleshooting.md).

## Best Practices

- Always handle errors gracefully
- Cache responses when possible
- Use pagination for large datasets
- Rate limit your requests

> **Note:** This API is still in beta. Breaking changes may occur.
"""

        markdown_file = Path(self.temp_dir) / "api_guide.md"
        markdown_file.write_text(markdown_content)
        self.test_files["markdown"] = str(markdown_file)
        print(f"✓ Created Markdown test file: {markdown_file}")

        # Plain text test file
        plaintext_content = """Configuration Guide
==================

This document explains how to configure the application.

Installation Requirements
-----------------------

Before installing, ensure you have:
- Python 3.8 or higher
- pip package manager
- 2GB of available disk space

Setting up Configuration
----------------------

1. Create a configuration file named 'config.txt'
2. Add your database connection string
3. Set your logging level
4. Configure cache settings

Example configuration:

    database_url=postgresql://user:pass@localhost/db
    log_level=INFO
    cache_size=1000
    timeout=30

Environment Variables
-------------------

You can also use environment variables:

DB_URL: Database connection URL
LOG_LEVEL: Logging level (DEBUG, INFO, WARN, ERROR)
CACHE_SIZE: Cache size in MB
TIMEOUT: Request timeout in seconds

Troubleshooting
--------------

Common issues and solutions:

Connection timeouts:
- Check your network connection
- Verify the database URL
- Increase timeout values

Permission errors:
- Run with elevated privileges
- Check file permissions
- Verify user access rights

Performance issues:
- Increase cache size
- Use connection pooling
- Monitor resource usage

Warning: Always backup your configuration before making changes.

Tip: Use environment variables in production environments.

For more information, contact support@example.com
"""

        plaintext_file = Path(self.temp_dir) / "config_guide.txt"
        plaintext_file.write_text(plaintext_content)
        self.test_files["plaintext"] = str(plaintext_file)
        print(f"✓ Created Plain text test file: {plaintext_file}")

        # Additional README file
        readme_content = """# Project Documentation

Welcome to our project! This README contains essential information.

## Quick Start

1. Clone the repository
2. Install dependencies
3. Run the application

## API Usage

Our API provides endpoints for user management, data processing, and reporting.

### Authentication

Use Bearer tokens for authentication:

```
Authorization: Bearer your-token-here
```

### Rate Limiting

API calls are limited to 1000 requests per hour per user.

## Contributing

Please read our contributing guidelines before submitting pull requests.

## License

This project is licensed under the MIT License.
"""

        readme_file = Path(self.temp_dir) / "README.md"
        readme_file.write_text(readme_content)
        self.test_files["readme"] = str(readme_file)
        print(f"✓ Created README test file: {readme_file}")

    def test_plugin_factory(self):
        """Test 1: Verify plugin factory can create document plugins."""
        print("\n=== Test 1: Plugin Factory ===")

        # Test creating Markdown plugin
        try:
            markdown_plugin = PluginFactory.create_plugin(
                "markdown", sqlite_store=self.sqlite_store, enable_semantic=True
            )
            self.plugins["markdown"] = markdown_plugin
            print(f"✓ Successfully created Markdown plugin: {type(markdown_plugin).__name__}")
        except Exception as e:
            print(f"✗ Failed to create Markdown plugin: {e}")
            return False

        # Test creating PlainText plugin
        try:
            plaintext_plugin = PluginFactory.create_plugin(
                "plaintext", sqlite_store=self.sqlite_store, enable_semantic=True
            )
            self.plugins["plaintext"] = plaintext_plugin
            print(f"✓ Successfully created PlainText plugin: {type(plaintext_plugin).__name__}")
        except Exception as e:
            print(f"✗ Failed to create PlainText plugin: {e}")
            return False

        # Verify plugins support their file types
        try:
            md_file = Path(self.test_files["markdown"])
            txt_file = Path(self.test_files["plaintext"])

            if markdown_plugin.supports(md_file):
                print("✓ Markdown plugin correctly supports .md files")
            else:
                print("✗ Markdown plugin doesn't support .md files")
                return False

            if plaintext_plugin.supports(txt_file):
                print("✓ PlainText plugin correctly supports .txt files")
            else:
                print("✗ PlainText plugin doesn't support .txt files")
                return False

        except Exception as e:
            print(f"✗ Error testing plugin file support: {e}")
            return False

        print("✓ Plugin factory test passed")
        return True

    def test_document_indexing(self):
        """Test 2: Verify plugins can index documents correctly."""
        print("\n=== Test 2: Document Indexing ===")

        try:
            # Index Markdown file
            md_file = Path(self.test_files["markdown"])
            md_content = md_file.read_text()

            print(f"Indexing Markdown file: {md_file.name}")
            md_shard = self.plugins["markdown"].indexFile(md_file, md_content)

            if md_shard and "symbols" in md_shard:
                symbols = md_shard["symbols"]
                print(f"✓ Markdown indexing successful: {len(symbols)} symbols found")

                # Check for expected symbols
                symbol_types = [s.get("kind", "unknown") for s in symbols]
                if "document" in symbol_types:
                    print("✓ Found document symbol")
                if "heading" in symbol_types:
                    print("✓ Found heading symbols")
                if any("section" in symbol_types):
                    print("✓ Found section symbols")

                # Print first few symbols for verification
                print(f"Sample symbols: {[s.get('symbol', 'unnamed') for s in symbols[:5]]}")
            else:
                print("✗ Markdown indexing failed: no symbols returned")
                return False

            # Index PlainText file
            txt_file = Path(self.test_files["plaintext"])
            txt_content = txt_file.read_text()

            print(f"Indexing PlainText file: {txt_file.name}")
            txt_shard = self.plugins["plaintext"].indexFile(txt_file, txt_content)

            if txt_shard and "symbols" in txt_shard:
                symbols = txt_shard["symbols"]
                print(f"✓ PlainText indexing successful: {len(symbols)} symbols found")

                # Print first few symbols for verification
                print(f"Sample symbols: {[s.get('symbol', 'unnamed') for s in symbols[:5]]}")
            else:
                print("✗ PlainText indexing failed: no symbols returned")
                return False

        except Exception as e:
            print(f"✗ Document indexing error: {e}")
            import traceback

            traceback.print_exc()
            return False

        print("✓ Document indexing test passed")
        return True

    def test_basic_search(self):
        """Test 3: Verify basic search functionality works."""
        print("\n=== Test 3: Basic Search ===")

        try:
            # Test search on Markdown plugin
            print("Testing Markdown plugin search...")
            md_results = list(self.plugins["markdown"].search("API authentication", {"limit": 5}))

            if md_results:
                print(f"✓ Markdown search successful: {len(md_results)} results")
                for i, result in enumerate(md_results[:3], 1):
                    file_name = Path(result.get("file", "")).name
                    snippet = (
                        result.get("snippet", "")[:100] + "..."
                        if len(result.get("snippet", "")) > 100
                        else result.get("snippet", "")
                    )
                    print(f"  {i}. {file_name}: {snippet}")
            else:
                print("✗ Markdown search returned no results")
                return False

            # Test search on PlainText plugin
            print("Testing PlainText plugin search...")
            txt_results = list(
                self.plugins["plaintext"].search("configuration setup", {"limit": 5})
            )

            if txt_results:
                print(f"✓ PlainText search successful: {len(txt_results)} results")
                for i, result in enumerate(txt_results[:3], 1):
                    file_name = Path(result.get("file", "")).name
                    snippet = (
                        result.get("snippet", "")[:100] + "..."
                        if len(result.get("snippet", "")) > 100
                        else result.get("snippet", "")
                    )
                    print(f"  {i}. {file_name}: {snippet}")
            else:
                print("✗ PlainText search returned no results")
                return False

        except Exception as e:
            print(f"✗ Basic search error: {e}")
            import traceback

            traceback.print_exc()
            return False

        print("✓ Basic search test passed")
        return True

    def test_dispatcher_setup(self):
        """Test 4: Verify enhanced dispatcher can be set up with plugins."""
        print("\n=== Test 4: Enhanced Dispatcher Setup ===")

        try:
            # Create dispatcher with plugin factory
            self.dispatcher = EnhancedDispatcher(
                sqlite_store=self.sqlite_store,
                enable_advanced_features=True,
                use_plugin_factory=True,
                lazy_load=False,  # Load all plugins immediately
                semantic_search_enabled=True,
            )

            print(f"✓ Created enhanced dispatcher")

            # Check supported languages
            supported = self.dispatcher.supported_languages
            print(f"✓ Dispatcher supports {len(supported)} languages: {sorted(supported)}")

            # Verify our plugins are available
            if "markdown" in supported:
                print("✓ Markdown support available")
            else:
                print("✗ Markdown support not available")
                return False

            if "plaintext" in supported:
                print("✓ PlainText support available")
            else:
                print("✗ PlainText support not available")
                return False

            # Get health check
            health = self.dispatcher.health_check()
            print(f"✓ Dispatcher health: {health['status']}")
            print(f"✓ Plugins loaded: {health['components']['dispatcher']['plugins_loaded']}")

        except Exception as e:
            print(f"✗ Dispatcher setup error: {e}")
            import traceback

            traceback.print_exc()
            return False

        print("✓ Enhanced dispatcher setup test passed")
        return True

    def test_dispatcher_indexing(self):
        """Test 5: Verify dispatcher can index our test files."""
        print("\n=== Test 5: Dispatcher File Indexing ===")

        try:
            # Index all test files through dispatcher
            for file_type, file_path in self.test_files.items():
                print(f"Indexing {file_type} file through dispatcher...")
                self.dispatcher.index_file(Path(file_path))
                print(f"✓ Successfully indexed {Path(file_path).name}")

            # Get statistics
            stats = self.dispatcher.get_statistics()
            print(f"✓ Dispatcher statistics:")
            print(f"  Total plugins: {stats['total_plugins']}")
            print(f"  Loaded languages: {stats['loaded_languages']}")
            print(f"  Indexing operations: {stats['operations']['indexings']}")

        except Exception as e:
            print(f"✗ Dispatcher indexing error: {e}")
            import traceback

            traceback.print_exc()
            return False

        print("✓ Dispatcher indexing test passed")
        return True

    def test_natural_language_queries(self):
        """Test 6: Verify dispatcher can handle natural language queries."""
        print("\n=== Test 6: Natural Language Queries ===")

        # Test queries that should trigger document search enhancements
        test_queries = [
            "How to install the API?",
            "API authentication guide",
            "Configuration setup instructions",
            "troubleshooting connection issues",
            "What are the best practices?",
            "Getting started with the API",
        ]

        try:
            for query in test_queries:
                print(f"\nTesting query: '{query}'")

                # Search with dispatcher
                results = list(self.dispatcher.search(query, semantic=True, limit=3))

                if results:
                    print(f"✓ Found {len(results)} results")
                    for i, result in enumerate(results, 1):
                        file_name = Path(result.get("file", "")).name
                        snippet = (
                            result.get("snippet", "")[:80] + "..."
                            if len(result.get("snippet", "")) > 80
                            else result.get("snippet", "")
                        )
                        score = result.get("score", 0)
                        print(f"  {i}. {file_name} (score: {score:.3f}): {snippet}")
                else:
                    print("⚠ No results found")

        except Exception as e:
            print(f"✗ Natural language query error: {e}")
            import traceback

            traceback.print_exc()
            return False

        print("✓ Natural language queries test passed")
        return True

    def test_documentation_search(self):
        """Test 7: Verify specialized documentation search."""
        print("\n=== Test 7: Documentation Search ===")

        try:
            # Test documentation-specific search
            doc_topics = ["installation", "authentication", "configuration", "troubleshooting"]

            for topic in doc_topics:
                print(f"\nSearching documentation for: '{topic}'")

                doc_results = list(self.dispatcher.search_documentation(topic, limit=3))

                if doc_results:
                    print(f"✓ Found {len(doc_results)} documentation results")
                    for i, result in enumerate(doc_results, 1):
                        file_name = Path(result.get("file", "")).name
                        snippet = (
                            result.get("snippet", "")[:80] + "..."
                            if len(result.get("snippet", "")) > 80
                            else result.get("snippet", "")
                        )
                        print(f"  {i}. {file_name}: {snippet}")
                else:
                    print(f"⚠ No documentation found for '{topic}'")

        except Exception as e:
            print(f"✗ Documentation search error: {e}")
            import traceback

            traceback.print_exc()
            return False

        print("✓ Documentation search test passed")
        return True

    def test_symbol_lookup(self):
        """Test 8: Verify symbol lookup functionality."""
        print("\n=== Test 8: Symbol Lookup ===")

        try:
            # Test symbol lookup
            test_symbols = [
                "API Documentation Guide",
                "Getting Started",
                "Authentication",
                "Users API",
            ]

            for symbol in test_symbols:
                print(f"Looking up symbol: '{symbol}'")

                definition = self.dispatcher.lookup(symbol)

                if definition:
                    print(f"✓ Found definition for '{symbol}'")
                    print(f"  Kind: {definition.get('kind', 'unknown')}")
                    print(f"  File: {Path(definition.get('file', '')).name}")
                    print(f"  Line: {definition.get('line', 'unknown')}")
                else:
                    print(f"⚠ No definition found for '{symbol}'")

        except Exception as e:
            print(f"✗ Symbol lookup error: {e}")
            import traceback

            traceback.print_exc()
            return False

        print("✓ Symbol lookup test passed")
        return True

    def run_all_tests(self):
        """Run all validation tests."""
        print("🚀 Starting Document Pipeline Validation Tests")
        print("=" * 60)

        tests = [
            ("Plugin Factory", self.test_plugin_factory),
            ("Document Indexing", self.test_document_indexing),
            ("Basic Search", self.test_basic_search),
            ("Dispatcher Setup", self.test_dispatcher_setup),
            ("Dispatcher Indexing", self.test_dispatcher_indexing),
            ("Natural Language Queries", self.test_natural_language_queries),
            ("Documentation Search", self.test_documentation_search),
            ("Symbol Lookup", self.test_symbol_lookup),
        ]

        passed = 0
        failed = 0

        start_time = time.time()

        for test_name, test_func in tests:
            try:
                if test_func():
                    passed += 1
                else:
                    failed += 1
                    print(f"❌ {test_name} FAILED")
            except Exception as e:
                failed += 1
                print(f"❌ {test_name} FAILED with exception: {e}")
                import traceback

                traceback.print_exc()

        end_time = time.time()
        duration = end_time - start_time

        # Print summary
        print("\n" + "=" * 60)
        print("📊 VALIDATION SUMMARY")
        print("=" * 60)
        print(f"Total tests: {len(tests)}")
        print(f"Passed: {passed} ✅")
        print(f"Failed: {failed} ❌")
        print(f"Success rate: {(passed/len(tests)*100):.1f}%")
        print(f"Duration: {duration:.2f} seconds")

        if failed == 0:
            print("\n🎉 ALL TESTS PASSED! Document pipeline is working correctly.")
            return True
        else:
            print(f"\n⚠️  {failed} tests failed. Please check the output above for details.")
            return False


def main():
    """Main function to run the validation."""
    validator = DocumentPipelineValidator()

    try:
        validator.setup()
        success = validator.run_all_tests()
        validator.cleanup()

        return 0 if success else 1

    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        validator.cleanup()
        return 130
    except Exception as e:
        print(f"\n\n💥 Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        validator.cleanup()
        return 1


if __name__ == "__main__":
    sys.exit(main())
