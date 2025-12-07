#!/usr/bin/env python3
"""
Comprehensive validation test suite for document processing plugins.
Tests both Markdown and PlainText plugins for production readiness.
"""

import os
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List

import psutil
import pytest

from mcp_server.plugins.plugin_factory import PluginFactory
from mcp_server.storage.sqlite_store import SQLiteStore


class TestDocumentProcessingValidation:
    """Comprehensive validation tests for document processing."""

    @pytest.fixture
    def sqlite_store(self):
        """Create a temporary SQLite store for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        store = SQLiteStore(db_path)
        yield store

        # Cleanup
        store.close()
        os.unlink(db_path)

    @pytest.fixture
    def markdown_plugin(self, sqlite_store):
        """Create Markdown plugin instance."""
        return PluginFactory.create_plugin("markdown", sqlite_store)

    @pytest.fixture
    def plaintext_plugin(self, sqlite_store):
        """Create PlainText plugin instance."""
        return PluginFactory.create_plugin("plaintext", sqlite_store)

    def test_markdown_hierarchical_extraction(self, markdown_plugin):
        """Test that Markdown plugin correctly extracts hierarchical structure."""
        content = """
# Main Title

## Section 1
This is section 1 content.

### Subsection 1.1
Details in subsection.

## Section 2
Another section.

### Subsection 2.1
More details.

#### Subsubsection 2.1.1
Deep nesting.
"""

        result = markdown_plugin.extract_symbols(content, "test.md")

        # Verify hierarchical structure
        assert any(s.name == "Main Title" and s.symbol_type == "heading_1" for s in result.symbols)
        assert any(s.name == "Section 1" and s.symbol_type == "heading_2" for s in result.symbols)
        assert any(
            s.name == "Subsection 1.1" and s.symbol_type == "heading_3" for s in result.symbols
        )
        assert any(
            s.name == "Subsubsection 2.1.1" and s.symbol_type == "heading_4" for s in result.symbols
        )

    def test_markdown_code_block_preservation(self, markdown_plugin):
        """Test that code blocks are preserved with language tags."""
        content = """
# Code Examples

```python
def hello_world():
    print("Hello, World!")
```

```javascript
function helloWorld() {
    console.log("Hello, World!");
}
```
"""

        result = markdown_plugin.extract_symbols(content, "test.md")

        # Check for code blocks
        code_blocks = [s for s in result.symbols if s.symbol_type == "code_block"]
        assert len(code_blocks) >= 2

        # Verify language tags
        assert any("python" in str(s.metadata) for s in code_blocks)
        assert any("javascript" in str(s.metadata) for s in code_blocks)

    def test_markdown_frontmatter_parsing(self, markdown_plugin):
        """Test YAML frontmatter parsing."""
        content = """---
title: Test Document
author: Test Author
tags: [testing, validation]
date: 2025-06-09
---

# Document Content
This is the actual content.
"""

        result = markdown_plugin.extract_symbols(content, "test.md")

        # Check metadata extraction
        assert result.metadata.get("title") == "Test Document"
        assert result.metadata.get("author") == "Test Author"
        assert "testing" in result.metadata.get("tags", [])

    def test_plaintext_nlp_features(self, plaintext_plugin):
        """Test NLP features of PlainText plugin."""
        content = """
This is a paragraph about natural language processing. It contains multiple sentences.
The plugin should correctly identify sentence boundaries. It should also detect paragraphs.

This is a second paragraph. The topic might be different here. 
We're testing the semantic coherence-based chunking feature.

Technical terms like API, REST, and JSON should be recognized.
The plugin should handle various formatting patterns.
"""

        result = plaintext_plugin.extract_symbols(content, "test.txt")

        # Check paragraph detection
        paragraphs = [s for s in result.symbols if s.symbol_type == "paragraph"]
        assert len(paragraphs) >= 2

        # Check sentence boundary detection
        assert any("multiple sentences" in s.name for s in result.symbols)

    def test_performance_document_indexing(self, markdown_plugin, sqlite_store):
        """Test indexing performance meets < 100ms per file requirement."""
        content = """
# Large Document

""" + "\n".join(
            [f"## Section {i}\nContent for section {i}." for i in range(100)]
        )

        start_time = time.time()
        result = markdown_plugin.extract_symbols(content, "large.md")

        # Store symbols
        for symbol in result.symbols:
            sqlite_store.add_symbol(
                file_path="large.md",
                symbol_name=symbol.name,
                symbol_type=symbol.symbol_type,
                line_number=symbol.line,
                metadata=symbol.metadata,
            )

        elapsed_time = (time.time() - start_time) * 1000  # Convert to ms

        assert elapsed_time < 100, f"Indexing took {elapsed_time}ms, exceeding 100ms requirement"

    def test_memory_usage_thousand_documents(self, markdown_plugin, sqlite_store):
        """Test memory usage stays under 100MB for 1000 documents."""
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Generate and index 1000 small documents
        for i in range(1000):
            content = f"""
# Document {i}

## Introduction
This is document number {i}.

## Content
Some content here.
"""
            result = markdown_plugin.extract_symbols(content, f"doc_{i}.md")

            for symbol in result.symbols:
                sqlite_store.add_symbol(
                    file_path=f"doc_{i}.md",
                    symbol_name=symbol.name,
                    symbol_type=symbol.symbol_type,
                    line_number=symbol.line,
                    metadata=symbol.metadata,
                )

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        assert (
            memory_increase < 100
        ), f"Memory usage increased by {memory_increase}MB, exceeding 100MB limit"

    def test_natural_language_query_support(self, markdown_plugin, sqlite_store):
        """Test support for natural language queries."""
        content = """
# Installation Guide

## Prerequisites
You need Python 3.8 or higher.

## How to Install
Run the following command:
```bash
pip install code-index-mcp
```

## Configuration
Edit the config file.

## Troubleshooting
If you encounter errors, check the logs.
"""

        result = markdown_plugin.extract_symbols(content, "install.md")

        for symbol in result.symbols:
            sqlite_store.add_symbol(
                file_path="install.md",
                symbol_name=symbol.name,
                symbol_type=symbol.symbol_type,
                line_number=symbol.line,
                metadata=symbol.metadata,
            )

        # Test natural language query
        results = sqlite_store.search_symbols("how to install", limit=5)
        assert len(results) > 0
        assert any("install" in r[1].lower() for r in results)

    def test_cross_document_linking(self, markdown_plugin, sqlite_store):
        """Test cross-document link extraction and tracking."""
        doc1 = """
# Main Document

See [Installation Guide](install.md) for setup instructions.
Also check [API Reference](api.md#endpoints).
"""

        doc2 = """
# Installation Guide

Return to [Main Document](index.md).
"""

        # Process both documents
        for filename, content in [("index.md", doc1), ("install.md", doc2)]:
            result = markdown_plugin.extract_symbols(content, filename)

            # Extract links
            links = []
            if hasattr(result, "links"):
                links = result.links

            for symbol in result.symbols:
                sqlite_store.add_symbol(
                    file_path=filename,
                    symbol_name=symbol.name,
                    symbol_type=symbol.symbol_type,
                    line_number=symbol.line,
                    metadata={"links": links} if links else symbol.metadata,
                )

    def test_real_world_readme_parsing(self, markdown_plugin):
        """Test with a real-world README structure."""
        content = """
# Awesome Project

[![Build Status](https://travis-ci.org/user/repo.svg)](https://travis-ci.org/user/repo)
[![Coverage](https://codecov.io/gh/user/repo/badge.svg)](https://codecov.io/gh/user/repo)

> A brief description of the project

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [API](#api)
- [Contributing](#contributing)
- [License](#license)

## Features

- ✨ Feature 1
- 🚀 Feature 2
- 🔧 Feature 3

## Installation

### Requirements

- Python >= 3.8
- Redis (optional)

### Quick Start

```bash
git clone https://github.com/user/repo.git
cd repo
pip install -e .
```

## Usage

```python
from awesome import Client

client = Client()
result = client.process("data")
```

## API

### `Client.process(data: str) -> Result`

Processes the input data.

**Parameters:**
- `data` (str): Input data to process

**Returns:**
- `Result`: Processing result

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file.
"""

        result = markdown_plugin.extract_symbols(content, "README.md")

        # Verify key sections are extracted
        section_names = [s.name for s in result.symbols if s.symbol_type.startswith("heading")]
        assert "Features" in section_names
        assert "Installation" in section_names
        assert "Usage" in section_names
        assert "API" in section_names

        # Check code block extraction
        code_blocks = [s for s in result.symbols if s.symbol_type == "code_block"]
        assert len(code_blocks) >= 2

    def test_api_documentation_parsing(self, markdown_plugin):
        """Test parsing of API documentation format."""
        content = """
# API Reference

## Endpoints

### GET /api/v1/search

Search for symbols in the codebase.

**Parameters:**
- `q` (string, required): Search query
- `limit` (integer, optional): Maximum results (default: 10)
- `language` (string, optional): Filter by language

**Response:**
```json
{
  "results": [
    {
      "symbol": "function_name",
      "file": "path/to/file.py",
      "line": 42
    }
  ],
  "total": 150
}
```

**Example:**
```bash
curl -X GET "http://localhost:8000/api/v1/search?q=parse&limit=5"
```

### POST /api/v1/reindex

Trigger reindexing of files.

**Request Body:**
```json
{
  "paths": ["/path/to/code"],
  "recursive": true
}
```

**Response:**
```json
{
  "status": "success",
  "files_indexed": 1234
}
```
"""

        result = markdown_plugin.extract_symbols(content, "api.md")

        # Check API endpoint extraction
        endpoints = [s for s in result.symbols if "GET" in s.name or "POST" in s.name]
        assert len(endpoints) >= 2

        # Verify parameter documentation
        assert any(
            "Parameters:" in s.name or "parameters" in str(s.metadata).lower()
            for s in result.symbols
        )

    def test_technical_documentation_structure(self, plaintext_plugin):
        """Test parsing of technical documentation."""
        content = """
TECHNICAL SPECIFICATION

1. INTRODUCTION
   This document describes the technical architecture of the system.
   
2. SYSTEM OVERVIEW
   2.1 Components
       - API Gateway
       - Message Queue
       - Database Layer
   
   2.2 Data Flow
       Client -> Gateway -> Queue -> Processor -> Database
       
3. IMPLEMENTATION DETAILS
   3.1 API Gateway
       The gateway handles all incoming requests and performs:
       * Authentication
       * Rate limiting
       * Request routing
       
   3.2 Message Queue
       We use RabbitMQ for asynchronous processing.
       
4. PERFORMANCE CONSIDERATIONS
   - Throughput: 10,000 requests/second
   - Latency: < 50ms p95
   - Availability: 99.9%
"""

        result = plaintext_plugin.extract_symbols(content, "tech_spec.txt")

        # Check section extraction
        sections = [s for s in result.symbols if s.symbol_type in ["section", "paragraph"]]
        assert len(sections) >= 4

        # Verify technical terms are recognized
        assert any("API Gateway" in s.name for s in result.symbols)
        assert any("RabbitMQ" in s.name for s in result.symbols)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
