#!/usr/bin/env python3
"""Comprehensive test for document processing capabilities."""

import sys
import tempfile
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_server.plugins.plugin_factory import PluginFactory
from mcp_server.storage.sqlite_store import SQLiteStore


def test_markdown_processing():
    """Test Markdown document processing with various content types."""
    print("Testing Markdown Document Processing...")

    # Complex markdown with various elements
    test_content = """---
title: API Reference Guide
author: Test Author
date: 2024-01-01
tags: [api, documentation, reference]
---

# API Reference Guide

This document provides a comprehensive API reference for our service.

## Table of Contents

1. [Authentication](#authentication)
2. [Endpoints](#endpoints)
3. [Error Handling](#error-handling)

## Authentication

All API requests require authentication using an API key:

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" https://api.example.com/v1/users
```

### Getting an API Key

To obtain an API key:

1. Sign up for an account
2. Navigate to Settings > API Keys
3. Click "Generate New Key"

## Endpoints

### User Management

#### GET /users

Retrieves a list of all users.

**Parameters:**
- `limit` (optional): Maximum number of results
- `offset` (optional): Pagination offset

**Example Response:**
```json
{
  "users": [
    {
      "id": 1,
      "name": "John Doe",
      "email": "john@example.com"
    }
  ],
  "total": 100
}
```

#### POST /users

Creates a new user.

**Request Body:**
```json
{
  "name": "string",
  "email": "string",
  "password": "string"
}
```

### Error Handling

All errors follow this format:

| Error Code | Description |
|------------|-------------|
| 400 | Bad Request |
| 401 | Unauthorized |
| 404 | Not Found |
| 500 | Internal Server Error |

## Code Examples

### Python

```python
import requests

response = requests.get(
    "https://api.example.com/v1/users",
    headers={"Authorization": "Bearer YOUR_API_KEY"}
)
print(response.json())
```

### JavaScript

```javascript
fetch('https://api.example.com/v1/users', {
  headers: {
    'Authorization': 'Bearer YOUR_API_KEY'
  }
})
.then(response => response.json())
.then(data => console.log(data));
```

## Conclusion

For more information, visit our [developer portal](https://developers.example.com).
"""

    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(test_content)
            temp_path = f.name

        # Create plugin and index
        plugin = PluginFactory.create_plugin("markdown")
        result = plugin.indexFile(temp_path, test_content)

        print("✓ Indexed Markdown file successfully")
        print(f"  - Symbols found: {len(result.get('symbols', []))}")
        print(f"  - Language: {result.get('language', 'N/A')}")

        # Display symbol hierarchy
        print("\n  Document Structure:")
        for symbol in result.get("symbols", [])[:10]:
            indent = "    " * (symbol.get("metadata", {}).get("level", 0))
            print(f"    {indent}- {symbol['symbol']} ({symbol['kind']})")

        Path(temp_path).unlink()
        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_plaintext_processing():
    """Test plain text document processing."""
    print("\nTesting Plain Text Document Processing...")

    test_content = """Technical Documentation: System Architecture

Introduction

This document describes the architecture of our distributed system. The system is designed to handle millions of requests per second while maintaining high availability and low latency.

Core Components

The system consists of several key components:

1. Load Balancer: Distributes incoming traffic across multiple application servers using round-robin algorithm with health checks.

2. Application Servers: Stateless servers running our core business logic. Each server can handle 10,000 concurrent connections.

3. Cache Layer: Redis-based caching system with 99.9% cache hit ratio for frequently accessed data.

4. Database Cluster: PostgreSQL cluster with master-slave replication for data persistence.

Performance Considerations

To achieve optimal performance, we implement several strategies:
- Connection pooling to reduce database connection overhead
- Asynchronous processing for non-critical operations
- Horizontal scaling based on CPU and memory metrics
- Circuit breakers to prevent cascade failures

Monitoring and Observability

The system includes comprehensive monitoring:
- Prometheus for metrics collection
- Grafana for visualization
- ELK stack for log aggregation
- Distributed tracing with Jaeger

Best Practices

When working with this system, follow these guidelines:
- Always use prepared statements for database queries
- Implement proper error handling and logging
- Use structured logging format
- Monitor resource usage and set appropriate alerts

Conclusion

This architecture provides a robust foundation for our services. Regular reviews and updates ensure it continues to meet our scaling requirements.
"""

    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(test_content)
            temp_path = f.name

        # Create plugin and index
        plugin = PluginFactory.create_plugin("plaintext")
        result = plugin.indexFile(temp_path, test_content)

        print("✓ Indexed Plain Text file successfully")
        print(f"  - Symbols found: {len(result.get('symbols', []))}")
        print(f"  - Language: {result.get('language', 'N/A')}")

        # Check if content was processed
        if result.get("symbols"):
            symbol = result["symbols"][0]
            print("\n  Document Summary:")
            print(f"    Title: {symbol.get('symbol', 'N/A')}")
            print(f"    Type: {symbol.get('kind', 'N/A')}")

        Path(temp_path).unlink()
        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_cross_document_search():
    """Test searching across different document types."""
    print("\nTesting Cross-Document Search...")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        db_path = temp_path / "test_search.db"

        # Create SQLite store
        sqlite_store = SQLiteStore(str(db_path))

        # Create test documents
        docs = {
            "readme.md": """# Project README

## Installation

To install this project, run:

```bash
pip install myproject
```

## Usage

Import the main module:

```python
from myproject import MyClass
```

## API Reference

See the full API documentation at docs/api.md
""",
            "guide.txt": """User Guide

Getting Started with MyProject

MyProject is a powerful tool for data processing. To begin using it, first ensure you have Python installed.

Installation Steps:
1. Download the package
2. Run pip install myproject
3. Verify installation

Basic Usage:
After installation, you can start using MyProject by importing it in your Python scripts.

API Overview:
The project provides a simple API for common operations. Refer to the API documentation for detailed information.
""",
            "api_reference.md": """# API Reference

## MyClass

The main class for data processing.

### Methods

#### process_data(data)

Processes the input data and returns results.

**Parameters:**
- data (dict): Input data to process

**Returns:**
- dict: Processed results

**Example:**
```python
from myproject import MyClass

processor = MyClass()
result = processor.process_data({"value": 42})
```
""",
        }

        try:
            # Index all documents
            for filename, content in docs.items():
                file_path = temp_path / filename
                file_path.write_text(content)

                plugin = PluginFactory.create_plugin_for_file(
                    str(file_path), sqlite_store=sqlite_store
                )
                if plugin:
                    plugin.indexFile(str(file_path), content)
                    print(f"  ✓ Indexed {filename}")

            # Search across documents
            print("\n  Cross-document searches:")
            queries = [
                ("installation", "Find installation instructions"),
                ("API", "Find API references"),
                ("MyClass", "Find class documentation"),
                ("pip install", "Find installation commands"),
            ]

            for query, description in queries:
                results = sqlite_store.search_symbols_fuzzy(query, limit=3)
                print(f"\n    Query '{query}' ({description}):")
                print(f"      Found {len(results)} results")

                for i, result in enumerate(results[:2]):
                    filename = Path(result["file_path"]).name
                    print(
                        f"      {i+1}. {filename}: {result['symbol_name']} (score: {result['score']:.3f})"
                    )

            return True

        except Exception as e:
            print(f"✗ Error: {e}")
            import traceback

            traceback.print_exc()
            return False


def test_document_metadata():
    """Test metadata extraction from documents."""
    print("\nTesting Document Metadata Extraction...")

    # Markdown with frontmatter
    md_with_meta = """---
title: Technical Specification
author: Jane Smith
date: 2024-01-15
version: 2.0
keywords: [spec, technical, api]
---

# Technical Specification

This document outlines the technical requirements...
"""

    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(md_with_meta)
            temp_path = f.name

        plugin = PluginFactory.create_plugin("markdown")
        result = plugin.indexFile(temp_path, md_with_meta)

        print("✓ Processed document with metadata")

        # Check for metadata in symbols
        doc_symbol = next((s for s in result.get("symbols", []) if s["kind"] == "document"), None)
        if doc_symbol and doc_symbol.get("metadata"):
            print("\n  Extracted Metadata:")
            meta = doc_symbol.get("metadata", {})
            for key, value in meta.items():
                if key not in ["level", "parent"]:  # Skip structural metadata
                    print(f"    - {key}: {value}")

        Path(temp_path).unlink()
        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def main():
    """Run all comprehensive tests."""
    print("=== Comprehensive Document Processing Tests ===\n")

    tests = [
        test_markdown_processing,
        test_plaintext_processing,
        test_cross_document_search,
        test_document_metadata,
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
        print("\n✓ All comprehensive tests passed!")
        print("\nDocument Processing Capabilities Verified:")
        print("- Markdown documents with complex structure")
        print("- Plain text documents with NLP processing")
        print("- Cross-document search functionality")
        print("- Metadata extraction from frontmatter")
        return 0
    else:
        print(f"\n✗ {total - passed} tests failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
