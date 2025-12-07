"""Base test class for document processing tests."""

import logging
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, Mock

import pytest

from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.plugins.markdown_plugin.plugin import MarkdownPlugin
from mcp_server.plugins.plaintext_plugin.plugin import PlainTextPlugin
from mcp_server.plugins.plugin_factory import PluginFactory
from mcp_server.storage.sqlite_store import SQLiteStore

logger = logging.getLogger(__name__)


class BaseDocumentTest:
    """Base class for all document processing tests."""

    @pytest.fixture(autouse=True)
    def setup_base(self):
        """Automatic setup for all tests."""
        self.temp_dir = tempfile.mkdtemp()
        self.workspace = Path(self.temp_dir)

        # Initialize SQLite with proper schema
        self.db_path = self.workspace / "test.db"
        self.store = self._init_sqlite_store()

        # Create mock for external services
        self.mock_voyage_client = MagicMock()
        self.mock_qdrant_client = MagicMock()

        # Initialize plugins
        self.markdown_plugin = MarkdownPlugin(sqlite_store=self.store, enable_semantic=False)
        self.plaintext_config = {
            "name": "plaintext",
            "code": "plaintext",
            "extensions": [".txt", ".text", ".plain"],
        }
        self.plaintext_plugin = PlainTextPlugin(
            language_config=self.plaintext_config,
            sqlite_store=self.store,
            enable_semantic=False,
        )

        # Initialize dispatcher
        self.dispatcher = EnhancedDispatcher()

        yield

        # Cleanup
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _init_sqlite_store(self) -> SQLiteStore:
        """Initialize SQLite store with proper schema."""
        store = SQLiteStore(str(self.db_path))

        # Ensure schema is created
        try:
            store.initialize_schema()
        except Exception:
            # Schema might already exist
            pass

        return store

    def create_test_file(self, filename: str, content: str) -> Path:
        """Create a test file in the workspace."""
        file_path = self.workspace / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return file_path

    def create_test_documents(self) -> Dict[str, Path]:
        """Create a set of test documents."""
        documents = {
            "simple.md": self.create_test_file(
                "simple.md",
                """# Simple Document

This is a simple test document with basic content.

## Section 1

Some content in section 1.

## Section 2

Some content in section 2.""",
            ),
            "complex.md": self.create_test_file(
                "complex.md",
                """---
title: Complex Document
author: Test Author
tags: [test, complex, markdown]
---

# Complex Document

## Introduction

This document has multiple features.

### Code Examples

```python
def hello_world():
    print("Hello, World!")
```

### Lists

- Item 1
- Item 2
  - Nested item

### Table

| Header 1 | Header 2 |
|----------|----------|
| Cell 1   | Cell 2   |
""",
            ),
            "plain.txt": self.create_test_file(
                "plain.txt",
                """This is a plain text document.

It has multiple paragraphs with different topics.

The first paragraph talks about introduction.
The second paragraph discusses the main topic.
The third paragraph provides conclusions.""",
            ),
            "unicode.md": self.create_test_file(
                "unicode.md",
                """# Unicode Test 测试 🌍

This document contains:
- Chinese: 你好世界
- Arabic: مرحبا بالعالم
- Emoji: 🚀 🎉 ✨
- Special: → ← ↑ ↓ • © ®""",
            ),
        }
        return documents

    def assert_chunks_valid(self, chunks):
        """Assert that chunks are valid."""
        assert chunks is not None
        assert len(chunks) > 0
        for chunk in chunks:
            assert hasattr(chunk, "content")
            assert hasattr(chunk, "metadata")
            assert chunk.content.strip() != ""

    def assert_symbols_valid(self, symbols):
        """Assert that symbols are valid."""
        assert symbols is not None
        for symbol in symbols:
            assert "name" in symbol
            assert "kind" in symbol
            assert "line" in symbol


class MockVoyageClient:
    """Mock Voyage AI client for testing."""

    def embed(self, texts, model=None, input_type=None):
        """Mock embedding generation."""
        # Return random embeddings of correct dimension
        import numpy as np

        return {"embeddings": [np.random.rand(1024).tolist() for _ in texts]}


class MockQdrantClient:
    """Mock Qdrant client for testing."""

    def __init__(self):
        self.collections = {}

    def create_collection(self, collection_name, vectors_config):
        """Mock collection creation."""
        self.collections[collection_name] = {"vectors": {}, "config": vectors_config}

    def upsert(self, collection_name, points):
        """Mock point insertion."""
        if collection_name not in self.collections:
            self.create_collection(collection_name, {})

        collection = self.collections[collection_name]
        for point in points:
            collection["vectors"][point.id] = point

    def search(self, collection_name, query_vector, limit=10):
        """Mock vector search."""
        # Return mock search results
        return [Mock(id=f"mock-{i}", score=0.9 - i * 0.1) for i in range(min(limit, 3))]
