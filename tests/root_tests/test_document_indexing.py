#!/usr/bin/env python3
"""Test document-specific indexing functionality."""

import shutil
import tempfile
from pathlib import Path

from mcp_server.utils.semantic_indexer import SemanticIndexer


def create_test_documents(temp_dir: Path) -> None:
    """Create test documentation files."""

    # Create README.md
    readme_content = """# MCP Server Documentation

This is the main documentation for the MCP Server project.

## Installation

Follow these steps to install:

### Prerequisites

- Python 3.9+
- Docker (optional)

### Basic Installation

```bash
pip install mcp-server
```

## Configuration

The server can be configured using environment variables.

### Environment Variables

- `MCP_PORT`: Server port (default: 8080)
- `MCP_HOST`: Server host (default: localhost)

## API Reference

### Search Endpoint

```
GET /api/search?q=<query>
```

Returns search results.

### Index Endpoint

```
POST /api/index
```

Indexes new content.
"""

    readme_path = temp_dir / "README.md"
    readme_path.write_text(readme_content)

    # Create API documentation
    api_doc_content = """# API Documentation

## Overview

The MCP Server provides a REST API for code indexing and search.

## Authentication

All API requests require authentication using JWT tokens.

### Getting a Token

```
POST /auth/token
{
    "username": "user",
    "password": "pass"
}
```

## Endpoints

### Search API

#### Basic Search

```
GET /api/search?q=<query>&limit=10
```

#### Advanced Search

```
POST /api/search
{
    "query": "search terms",
    "filters": {
        "language": "python",
        "type": "function"
    }
}
```

### Indexing API

#### Index File

```
POST /api/index/file
{
    "path": "/path/to/file.py"
}
```

#### Index Directory

```
POST /api/index/directory
{
    "path": "/path/to/dir",
    "recursive": true
}
```
"""

    api_path = temp_dir / "docs" / "api.md"
    api_path.parent.mkdir(exist_ok=True)
    api_path.write_text(api_doc_content)

    # Create tutorial
    tutorial_content = """# Getting Started Tutorial

## Introduction

This tutorial will guide you through using the MCP Server.

## Step 1: Installation

First, install the server:

```bash
pip install mcp-server
```

## Step 2: Basic Configuration

Create a configuration file:

```yaml
server:
  host: localhost
  port: 8080
  
indexing:
  languages:
    - python
    - javascript
    - go
```

## Step 3: Running the Server

Start the server:

```bash
mcp-server start
```

## Step 4: Your First Search

Try searching for a function:

```bash
curl "http://localhost:8080/api/search?q=parse_function"
```

## Next Steps

- Explore the [API Documentation](./api.md)
- Learn about [Advanced Features](./advanced.md)
"""

    tutorial_path = temp_dir / "docs" / "tutorial.md"
    tutorial_path.write_text(tutorial_content)


def test_document_indexing():
    """Test the document indexing functionality."""

    # Create temporary directory with test documents
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        create_test_documents(temp_path)

        # Initialize indexer
        indexer = SemanticIndexer(collection="test-docs")

        print("Testing document indexing...")
        print("-" * 50)

        # Test 1: Index README
        print("\n1. Indexing README.md:")
        result = indexer.index_document(
            temp_path / "README.md",
            metadata={
                "tags": ["documentation", "readme", "main"],
                "summary": "Main project documentation",
            },
        )
        print(f"   - Indexed {result['total_sections']} sections")
        for section in result["sections"]:
            print(f"     - {section['context']} (lines {section['lines']})")

        # Test 2: Index API documentation
        print("\n2. Indexing API documentation:")
        result = indexer.index_document(temp_path / "docs" / "api.md", doc_type="api")
        print(f"   - Indexed {result['total_sections']} sections")

        # Test 3: Index documentation directory
        print("\n3. Indexing documentation directory:")
        result = indexer.index_documentation_directory(temp_path)
        print(f"   - Indexed {result['total_files']} files")
        print(f"   - Total sections: {result['total_sections']}")

        # Test 4: Natural language queries
        print("\n4. Testing natural language queries:")

        queries = [
            ("How do I install the server?", ["readme", "tutorial"]),
            ("What authentication methods are supported?", ["api"]),
            ("Show me the search API endpoints", ["api"]),
            ("Getting started guide", ["tutorial", "readme"]),
        ]

        for query, doc_types in queries:
            print(f"\n   Query: '{query}'")
            print(f"   Document types: {doc_types}")

            results = indexer.query_natural_language(query, limit=3, doc_types=doc_types)

            for i, result in enumerate(results, 1):
                print(f"\n   Result {i}:")
                print(f"     - File: {Path(result['file']).name}")
                print(f"     - Section: {result.get('section_context', 'N/A')}")
                print(f"     - Score: {result['score']:.3f}")
                print(f"     - Weighted Score: {result['weighted_score']:.3f}")
                print(f"     - Type: {result.get('doc_type', 'unknown')}")
                if "content" in result:
                    preview = result["content"][:100].replace("\n", " ")
                    print(f"     - Preview: {preview}...")


if __name__ == "__main__":
    test_document_indexing()
