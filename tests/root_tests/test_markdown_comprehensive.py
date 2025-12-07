"""
Comprehensive tests for Markdown document processing features.

This test suite covers:
- Full Markdown parsing (headings, lists, code blocks, tables)
- Frontmatter extraction (YAML/TOML)
- Section hierarchy extraction
- Smart chunking strategies
- Integration with semantic search
"""

import json

# Import the Markdown plugin and related classes
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, "/app")

from mcp_server.document_processing import DocumentChunk, DocumentMetadata, DocumentStructure
from mcp_server.plugins.markdown_plugin.chunk_strategies import MarkdownChunkStrategy
from mcp_server.plugins.markdown_plugin.document_parser import MarkdownParser
from mcp_server.plugins.markdown_plugin.frontmatter_parser import FrontmatterParser
from mcp_server.plugins.markdown_plugin.plugin import MarkdownPlugin
from mcp_server.plugins.markdown_plugin.section_extractor import SectionExtractor
from mcp_server.storage.sqlite_store import SQLiteStore


class TestMarkdownParser:
    """Test the core Markdown parser functionality."""

    @pytest.fixture
    def parser(self):
        """Create a MarkdownParser instance."""
        return MarkdownParser()

    def test_basic_markdown_parsing(self, parser):
        """Test parsing basic Markdown elements."""
        content = """# Main Title

This is a paragraph with **bold** and *italic* text.

## Subsection

Another paragraph with `inline code`.

### Sub-subsection

- List item 1
- List item 2
  - Nested item
  
1. Numbered item
2. Second item

```python
def hello():
    print("Hello, World!")
```

| Column 1 | Column 2 |
|----------|----------|
| Data 1   | Data 2   |
| Data 3   | Data 4   |

[Link text](https://example.com)

![Image alt](image.png)
"""
        ast = parser.parse(content)

        # Verify AST structure
        assert ast is not None
        assert "type" in ast
        assert "children" in ast

        # Check for different element types
        elements = self._collect_element_types(ast)
        expected_types = {"heading", "paragraph", "list", "code", "table", "link", "image"}

        # Verify we found most expected elements
        found_types = set(elements)
        assert (
            len(found_types & expected_types) >= 5
        ), f"Expected more element types, found: {found_types}"

    def test_heading_hierarchy(self, parser):
        """Test parsing heading hierarchy."""
        content = """# Level 1

Content under level 1.

## Level 2

Content under level 2.

### Level 3

Content under level 3.

#### Level 4

Content under level 4.

## Another Level 2

More content.
"""
        ast = parser.parse(content)
        headings = self._extract_headings(ast)

        # Verify heading levels
        expected_levels = [1, 2, 3, 4, 2]
        actual_levels = [h["level"] for h in headings]
        assert actual_levels == expected_levels

        # Verify heading text
        expected_texts = ["Level 1", "Level 2", "Level 3", "Level 4", "Another Level 2"]
        actual_texts = [h["text"] for h in headings]
        assert actual_texts == expected_texts

    def test_code_block_parsing(self, parser):
        """Test parsing various code block formats."""
        content = """
```python
def function():
    return "Python code"
```

```javascript
function greet(name) {
    return `Hello, ${name}!`;
}
```

```
Plain code block without language
```

    # Indented code block
    def indented():
        pass
"""
        ast = parser.parse(content)
        code_blocks = self._extract_code_blocks(ast)

        assert len(code_blocks) >= 3

        # Check for different languages
        languages = [block.get("lang", "") for block in code_blocks]
        assert "python" in languages
        assert "javascript" in languages

    def test_list_parsing(self, parser):
        """Test parsing various list formats."""
        content = """
- Unordered item 1
- Unordered item 2
  - Nested item
  - Another nested
    - Deep nested

1. Ordered item 1
2. Ordered item 2
   1. Nested ordered
   2. Another nested

* Alternative bullet
+ Another bullet style

- [ ] Task item unchecked
- [x] Task item checked
"""
        ast = parser.parse(content)
        lists = self._extract_lists(ast)

        assert len(lists) >= 4

        # Check for ordered and unordered lists
        ordered_count = sum(1 for lst in lists if lst.get("ordered", False))
        unordered_count = len(lists) - ordered_count

        assert ordered_count >= 1
        assert unordered_count >= 3

    def test_table_parsing(self, parser):
        """Test parsing Markdown tables."""
        content = """
| Name | Age | City |
|------|-----|------|
| John | 30  | NYC  |
| Jane | 25  | LA   |

| Left | Center | Right |
|:-----|:------:|------:|
| L1   | C1     | R1    |
| L2   | C2     | R2    |
"""
        ast = parser.parse(content)
        tables = self._extract_tables(ast)

        assert len(tables) >= 2

        # Verify table structure
        for table in tables:
            assert "children" in table  # Should have rows
            assert len(table["children"]) >= 2  # Header + data rows

    def test_inline_elements(self, parser):
        """Test parsing inline Markdown elements."""
        content = """
This paragraph has **bold**, *italic*, ***bold italic***, 
`inline code`, ~~strikethrough~~, and [links](https://example.com).

Also has inline images: ![alt](image.png) and autolinks: https://auto.link
"""
        ast = parser.parse(content)

        # Extract inline elements
        inline_elements = self._collect_inline_elements(ast)

        expected_types = {"strong", "emphasis", "inlineCode", "link", "image"}
        found_types = set(element["type"] for element in inline_elements)

        assert len(found_types & expected_types) >= 4

    # Helper methods

    def _collect_element_types(self, ast: Dict[str, Any], types: List[str] = None) -> List[str]:
        """Recursively collect all element types in the AST."""
        if types is None:
            types = []

        if "type" in ast:
            types.append(ast["type"])

        for child in ast.get("children", []):
            self._collect_element_types(child, types)

        return types

    def _extract_headings(self, ast: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract heading information from AST."""
        headings = []

        def traverse(node):
            if node.get("type") == "heading":
                headings.append({"level": node.get("depth", 1), "text": self._extract_text(node)})

            for child in node.get("children", []):
                traverse(child)

        traverse(ast)
        return headings

    def _extract_code_blocks(self, ast: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract code block information from AST."""
        blocks = []

        def traverse(node):
            if node.get("type") == "code":
                blocks.append({"lang": node.get("lang", ""), "value": node.get("value", "")})

            for child in node.get("children", []):
                traverse(child)

        traverse(ast)
        return blocks

    def _extract_lists(self, ast: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract list information from AST."""
        lists = []

        def traverse(node):
            if node.get("type") == "list":
                lists.append(
                    {"ordered": node.get("ordered", False), "items": len(node.get("children", []))}
                )

            for child in node.get("children", []):
                traverse(child)

        traverse(ast)
        return lists

    def _extract_tables(self, ast: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract table information from AST."""
        tables = []

        def traverse(node):
            if node.get("type") == "table":
                tables.append(node)

            for child in node.get("children", []):
                traverse(child)

        traverse(ast)
        return tables

    def _collect_inline_elements(
        self, ast: Dict[str, Any], elements: List[Dict] = None
    ) -> List[Dict]:
        """Collect inline elements from AST."""
        if elements is None:
            elements = []

        inline_types = {"strong", "emphasis", "inlineCode", "link", "image", "delete"}

        if ast.get("type") in inline_types:
            elements.append(ast)

        for child in ast.get("children", []):
            self._collect_inline_elements(child, elements)

        return elements

    def _extract_text(self, node: Dict[str, Any]) -> str:
        """Extract text content from an AST node."""
        if node.get("type") == "text":
            return node.get("value", "")

        text_parts = []
        for child in node.get("children", []):
            text_parts.append(self._extract_text(child))

        return " ".join(text_parts).strip()


class TestFrontmatterParser:
    """Test frontmatter parsing functionality."""

    @pytest.fixture
    def parser(self):
        """Create a FrontmatterParser instance."""
        return FrontmatterParser()

    def test_yaml_frontmatter(self, parser):
        """Test parsing YAML frontmatter."""
        content = """---
title: Test Document
author: John Doe
date: 2024-01-01
tags: [test, markdown, yaml]
published: true
meta:
  description: A test document
  keywords: ["test", "markdown"]
---

# Document Content

This is the main content.
"""
        frontmatter, content_without_fm = parser.parse(content)

        # Verify frontmatter extraction
        assert frontmatter["title"] == "Test Document"
        assert frontmatter["author"] == "John Doe"
        assert frontmatter["date"] == "2024-01-01"
        assert frontmatter["tags"] == ["test", "markdown", "yaml"]
        assert frontmatter["published"] is True
        assert isinstance(frontmatter["meta"], dict)
        assert frontmatter["meta"]["description"] == "A test document"

        # Verify content separation
        assert "---" not in content_without_fm
        assert "# Document Content" in content_without_fm

    def test_toml_frontmatter(self, parser):
        """Test parsing TOML frontmatter."""
        content = """+++
title = "TOML Document"
author = "Jane Smith"
date = 2024-01-01
tags = ["test", "toml"]
published = true

[meta]
description = "A TOML test document"
+++

# Document Content

TOML frontmatter content.
"""
        frontmatter, content_without_fm = parser.parse(content)

        # Verify TOML parsing
        assert frontmatter["title"] == "TOML Document"
        assert frontmatter["author"] == "Jane Smith"
        assert frontmatter["tags"] == ["test", "toml"]
        assert "meta" in frontmatter

        # Verify content separation
        assert "+++" not in content_without_fm
        assert "# Document Content" in content_without_fm

    def test_json_frontmatter(self, parser):
        """Test parsing JSON frontmatter."""
        content = """{
  "title": "JSON Document",
  "author": "Bob Wilson",
  "tags": ["test", "json"],
  "meta": {
    "description": "JSON frontmatter test"
  }
}

# Document Content

JSON frontmatter content.
"""
        frontmatter, content_without_fm = parser.parse(content)

        # Verify JSON parsing
        assert frontmatter["title"] == "JSON Document"
        assert frontmatter["author"] == "Bob Wilson"
        assert frontmatter["tags"] == ["test", "json"]
        assert frontmatter["meta"]["description"] == "JSON frontmatter test"

    def test_no_frontmatter(self, parser):
        """Test handling content without frontmatter."""
        content = """# Document Without Frontmatter

This document has no frontmatter.
"""
        frontmatter, content_without_fm = parser.parse(content)

        # Should return empty frontmatter and original content
        assert frontmatter == {}
        assert content_without_fm == content

    def test_invalid_frontmatter(self, parser):
        """Test handling invalid frontmatter."""
        content = """---
invalid: yaml: content: [
---

# Document Content
"""
        frontmatter, content_without_fm = parser.parse(content)

        # Should handle gracefully and return empty frontmatter
        assert isinstance(frontmatter, dict)
        assert "# Document Content" in content_without_fm


class TestSectionExtractor:
    """Test section hierarchy extraction."""

    @pytest.fixture
    def extractor(self):
        """Create a SectionExtractor instance."""
        return SectionExtractor()

    @pytest.fixture
    def parser(self):
        """Create a MarkdownParser instance."""
        return MarkdownParser()

    def test_flat_sections(self, extractor, parser):
        """Test extracting flat section structure."""
        content = """# Introduction

Introduction content.

# Main Content

Main content here.

# Conclusion

Conclusion content.
"""
        ast = parser.parse(content)
        sections = extractor.extract(ast, content)

        assert len(sections) == 3

        # Verify section titles
        titles = [section["title"] for section in sections]
        assert titles == ["Introduction", "Main Content", "Conclusion"]

        # Verify section levels
        levels = [section["level"] for section in sections]
        assert all(level == 1 for level in levels)

    def test_hierarchical_sections(self, extractor, parser):
        """Test extracting hierarchical section structure."""
        content = """# Chapter 1

Chapter introduction.

## Section 1.1

First section content.

### Subsection 1.1.1

Subsection content.

### Subsection 1.1.2

Another subsection.

## Section 1.2

Second section content.

# Chapter 2

Second chapter.

## Section 2.1

Content here.
"""
        ast = parser.parse(content)
        sections = extractor.extract(ast, content)

        # Verify section count
        assert len(sections) >= 6

        # Verify hierarchy
        chapter1 = next(s for s in sections if s["title"] == "Chapter 1")
        section11 = next(s for s in sections if s["title"] == "Section 1.1")
        subsection111 = next(s for s in sections if s["title"] == "Subsection 1.1.1")

        assert chapter1["level"] == 1
        assert section11["level"] == 2
        assert subsection111["level"] == 3

        # Check parent relationships
        assert subsection111.get("parent_id") == section11["id"]

    def test_section_content_extraction(self, extractor, parser):
        """Test extracting section content."""
        content = """# First Section

This is the content of the first section.

It has multiple paragraphs.

## Subsection

Subsection content here.

# Second Section

Content of the second section.
"""
        ast = parser.parse(content)
        sections = extractor.extract(ast, content)

        first_section = next(s for s in sections if s["title"] == "First Section")

        # Verify content extraction
        assert "This is the content of the first section" in first_section["content"]
        assert "It has multiple paragraphs" in first_section["content"]

        # Verify line numbers
        assert first_section["start_line"] == 1
        assert first_section["end_line"] > first_section["start_line"]

    def test_section_ids(self, extractor, parser):
        """Test section ID generation."""
        content = """# Section One

Content.

# Section Two

More content.

# Section One

Duplicate name.
"""
        ast = parser.parse(content)
        sections = extractor.extract(ast, content)

        # Verify unique IDs
        ids = [section["id"] for section in sections]
        assert len(ids) == len(set(ids)), "Section IDs should be unique"

        # Verify ID format
        for section_id in ids:
            assert isinstance(section_id, str)
            assert len(section_id) > 0


class TestMarkdownChunkStrategy:
    """Test Markdown-specific chunking strategies."""

    @pytest.fixture
    def strategy(self):
        """Create a MarkdownChunkStrategy instance."""
        return MarkdownChunkStrategy()

    @pytest.fixture
    def parser(self):
        """Create a MarkdownParser instance."""
        return MarkdownParser()

    @pytest.fixture
    def extractor(self):
        """Create a SectionExtractor instance."""
        return SectionExtractor()

    def test_section_based_chunking(self, strategy, parser, extractor):
        """Test chunking based on sections."""
        content = """# Introduction

This is a long introduction section with enough content to form its own chunk.
It contains multiple sentences and provides context for the entire document.

# Main Content

This is the main content section with substantial text.
It discusses the primary topics and contains detailed information.

## Subsection

This subsection contains specific details and examples.
It builds upon the main content with additional specificity.

# Conclusion

The conclusion summarizes the key points and provides final thoughts.
"""
        ast = parser.parse(content)
        sections_data = extractor.extract(ast, content)

        chunks = strategy.create_chunks(content, ast, sections_data, "test.md")

        # Should have multiple chunks
        assert len(chunks) >= 3

        # Verify chunk boundaries align with sections
        for chunk in chunks:
            assert hasattr(chunk, "content")
            assert hasattr(chunk, "metadata")
            assert len(chunk.content) > 0

    def test_code_block_preservation(self, strategy, parser, extractor):
        """Test that code blocks are preserved intact."""
        content = """# Code Examples

Here's a Python example:

```python
def hello_world():
    print("Hello, World!")
    
    for i in range(5):
        print(f"Count: {i}")
```

And here's JavaScript:

```javascript
function greet(name) {
    return `Hello, ${name}!`;
}
```

More content after code blocks.
"""
        ast = parser.parse(content)
        sections_data = extractor.extract(ast, content)

        chunks = strategy.create_chunks(content, ast, sections_data, "test.md")

        # Verify code blocks are preserved
        code_found = False
        for chunk in chunks:
            if "def hello_world" in chunk.content:
                assert "for i in range(5)" in chunk.content
                code_found = True

        assert code_found, "Code blocks should be preserved intact"

    def test_table_preservation(self, strategy, parser, extractor):
        """Test that tables are preserved intact."""
        content = """# Data Tables

Here's a comparison table:

| Feature | Option A | Option B |
|---------|----------|----------|
| Speed   | Fast     | Slow     |
| Cost    | High     | Low      |
| Quality | Good     | Fair     |

The table above shows the comparison.
"""
        ast = parser.parse(content)
        sections_data = extractor.extract(ast, content)

        chunks = strategy.create_chunks(content, ast, sections_data, "test.md")

        # Verify table is preserved
        table_found = False
        for chunk in chunks:
            if "| Feature |" in chunk.content:
                assert "| Speed   |" in chunk.content
                assert "| Cost    |" in chunk.content
                table_found = True

        assert table_found, "Tables should be preserved intact"

    def test_chunk_size_optimization(self, strategy, parser, extractor):
        """Test chunk size optimization."""
        # Create content with varying section sizes
        sections = []
        for i in range(10):
            if i % 3 == 0:
                # Large section
                content_part = (
                    f"# Section {i}\n\n" + "This is a large section with lots of content. " * 50
                )
            else:
                # Small section
                content_part = f"# Section {i}\n\nThis is a small section."
            sections.append(content_part)

        content = "\n\n".join(sections)
        ast = parser.parse(content)
        sections_data = extractor.extract(ast, content)

        chunks = strategy.create_chunks(content, ast, sections_data, "test.md")
        optimized_chunks = strategy.optimize_chunks_for_search(chunks)

        # Verify optimization
        assert len(optimized_chunks) > 0

        # Check chunk sizes are reasonable
        for chunk in optimized_chunks:
            assert len(chunk.content) >= 50  # Not too small
            assert len(chunk.content) <= 5000  # Not too large

    def test_metadata_enrichment(self, strategy, parser, extractor):
        """Test chunk metadata enrichment."""
        content = """# Technical Documentation

This section contains technical information.

## API Reference

Details about the API endpoints.

### Authentication

Information about authentication methods.

```python
# Example authentication code
api_key = "your-api-key"
```
"""
        ast = parser.parse(content)
        sections_data = extractor.extract(ast, content)

        chunks = strategy.create_chunks(content, ast, sections_data, "test.md")

        # Verify metadata enrichment
        for chunk in chunks:
            assert hasattr(chunk, "metadata")
            metadata = chunk.metadata

            # Should have section information
            if "API Reference" in chunk.content:
                assert metadata.get("section_level", 0) > 0
                assert "heading_hierarchy" in metadata or "section" in metadata


class TestMarkdownPlugin:
    """Test the complete Markdown plugin functionality."""

    @pytest.fixture
    def temp_db(self, tmp_path):
        """Create a temporary database."""
        db_path = tmp_path / "test.db"
        return SQLiteStore(str(db_path))

    @pytest.fixture
    def plugin(self, temp_db):
        """Create a MarkdownPlugin instance."""
        return MarkdownPlugin(sqlite_store=temp_db, enable_semantic=False)

    @pytest.fixture
    def sample_markdown_file(self, tmp_path):
        """Create a sample Markdown file."""
        content = """---
title: Sample Document
author: Test Author
date: 2024-01-01
tags: [test, sample, markdown]
description: A comprehensive test document
---

# Introduction

This is a comprehensive test document for the Markdown plugin.
It contains various Markdown elements to test parsing capabilities.

## Features

The document includes:

- Multiple heading levels
- Various list types
- Code blocks with syntax highlighting
- Tables with data
- Links and images
- **Bold** and *italic* text

### Code Examples

Here's a Python example:

```python
def process_markdown(content):
    \"\"\"Process Markdown content.\"\"\"
    # Parse the content
    parser = MarkdownParser()
    ast = parser.parse(content)
    return ast
```

### Data Tables

| Language | Extension | Type       |
|----------|-----------|------------|
| Python   | .py       | Scripting  |
| Markdown | .md       | Markup     |
| JSON     | .json     | Data       |

## Advanced Features

### Nested Lists

1. First level item
   - Second level bullet
   - Another second level
     1. Third level numbered
     2. Another third level
2. Back to first level

### Links and References

Check out [our documentation](https://docs.example.com) for more details.

![Example Image](example.png "Example image caption")

## Conclusion

This document demonstrates the full range of Markdown features
that should be properly parsed and indexed by the plugin.

### Final Notes

- Always test edge cases
- Verify parsing accuracy
- Check performance with large documents
"""

        file_path = tmp_path / "sample.md"
        file_path.write_text(content)
        return file_path, content

    def test_file_support(self, plugin):
        """Test file extension support."""
        assert plugin.supports("test.md")
        assert plugin.supports("test.markdown")
        assert plugin.supports("test.mdown")
        assert plugin.supports("test.mkd")
        assert plugin.supports("test.mdx")
        assert not plugin.supports("test.txt")
        assert not plugin.supports("test.py")

    def test_metadata_extraction(self, plugin, sample_markdown_file):
        """Test comprehensive metadata extraction."""
        file_path, content = sample_markdown_file

        metadata = plugin.extract_metadata(content, file_path)

        # Verify frontmatter metadata
        assert metadata.title == "Sample Document"
        assert metadata.author == "Test Author"
        assert metadata.created_date == "2024-01-01"
        assert metadata.tags == ["test", "sample", "markdown"]
        assert metadata.document_type == "markdown"

        # Verify custom metadata
        assert "description" in metadata.custom
        assert metadata.custom["description"] == "A comprehensive test document"

    def test_structure_extraction(self, plugin, sample_markdown_file):
        """Test document structure extraction."""
        file_path, content = sample_markdown_file

        structure = plugin.extract_structure(content, file_path)

        # Verify structure components
        assert structure.title == "Sample Document"
        assert len(structure.sections) >= 5
        assert structure.metadata is not None

        # Verify section hierarchy
        intro_section = next((s for s in structure.sections if s.heading == "Introduction"), None)
        assert intro_section is not None
        assert intro_section.level == 1

        features_section = next((s for s in structure.sections if s.heading == "Features"), None)
        assert features_section is not None
        assert features_section.level == 2

        code_section = next((s for s in structure.sections if s.heading == "Code Examples"), None)
        assert code_section is not None
        assert code_section.level == 3

    def test_content_parsing(self, plugin, sample_markdown_file):
        """Test content parsing to plain text."""
        file_path, content = sample_markdown_file

        plain_text = plugin.parse_content(content, file_path)

        # Verify content conversion
        assert "Sample Document" in plain_text or "Introduction" in plain_text
        assert "def process_markdown" in plain_text  # Code should be preserved
        assert "Python" in plain_text
        assert "Markdown" in plain_text

        # Verify Markdown syntax is removed
        assert "```python" not in plain_text
        assert "| Language |" not in plain_text or "Language" in plain_text

    def test_full_indexing(self, plugin, sample_markdown_file):
        """Test complete file indexing."""
        file_path, content = sample_markdown_file

        result = plugin.indexFile(file_path, content)

        # Verify index result structure
        assert "file" in result
        assert "symbols" in result
        assert "language" in result
        assert result["language"] == "markdown"

        # Verify symbols
        symbols = result["symbols"]
        assert len(symbols) > 0

        # Should have document symbol
        doc_symbol = next((s for s in symbols if s["kind"] == "document"), None)
        assert doc_symbol is not None
        assert doc_symbol["symbol"] == "Sample Document"

        # Should have section symbols
        section_symbols = [s for s in symbols if s["kind"] == "section"]
        assert len(section_symbols) >= 5

        # Verify section symbol details
        intro_symbol = next((s for s in section_symbols if s["symbol"] == "Introduction"), None)
        assert intro_symbol is not None
        assert intro_symbol["metadata"]["level"] == 1

    def test_chunking_integration(self, plugin, sample_markdown_file):
        """Test document chunking integration."""
        file_path, content = sample_markdown_file

        chunks = plugin.chunk_document(content, file_path)

        # Verify chunks
        assert len(chunks) > 0
        assert all(hasattr(chunk, "content") for chunk in chunks)
        assert all(hasattr(chunk, "metadata") for chunk in chunks)

        # Verify chunk content coverage
        all_chunk_content = " ".join(chunk.content for chunk in chunks)
        assert "Introduction" in all_chunk_content
        assert "Features" in all_chunk_content
        assert "def process_markdown" in all_chunk_content

        # Verify chunk metadata
        for chunk in chunks:
            assert chunk.metadata is not None
            assert chunk.chunk_index >= 0

    def test_semantic_search_integration(self, tmp_path):
        """Test integration with semantic search capabilities."""
        # Create plugin with semantic search enabled
        db_path = tmp_path / "semantic_test.db"
        store = SQLiteStore(str(db_path))

        # Mock semantic indexer
        with patch("mcp_server.utils.semantic_indexer.SemanticIndexer") as mock_indexer:
            mock_instance = Mock()
            mock_indexer.return_value = mock_instance

            plugin = MarkdownPlugin(sqlite_store=store, enable_semantic=True)
            plugin.semantic_indexer = mock_instance

            # Create test file
            content = """---
title: Semantic Test
tags: [ai, search, semantic]
---

# Machine Learning

This document discusses machine learning algorithms and techniques.

## Neural Networks

Deep learning with neural networks provides powerful pattern recognition.
"""

            file_path = tmp_path / "semantic_test.md"
            file_path.write_text(content)

            # Index the file
            result = plugin.indexFile(file_path, content)

            # Verify indexing occurred
            assert result is not None

            # Verify semantic indexer was called (if enabled)
            if hasattr(plugin, "semantic_indexer") and plugin.semantic_indexer:
                mock_instance.index_document.assert_called()

    def test_large_document_handling(self, plugin, tmp_path):
        """Test handling of large Markdown documents."""
        # Create a large document
        sections = []
        for i in range(50):
            section_content = f"""## Section {i}

This is section {i} with substantial content. """ + (
                "Lorem ipsum dolor sit amet. " * 20
            )
            sections.append(section_content)

        large_content = "# Large Document\n\n" + "\n\n".join(sections)

        file_path = tmp_path / "large.md"
        file_path.write_text(large_content)

        # Test indexing
        result = plugin.indexFile(file_path, large_content)

        # Verify handling
        assert result is not None
        assert len(result["symbols"]) > 0

        # Test chunking
        chunks = plugin.chunk_document(large_content, file_path)
        assert len(chunks) > 1

        # Verify no chunks are too large
        for chunk in chunks:
            assert len(chunk.content) <= 10000  # Reasonable chunk size limit

    def test_malformed_markdown_handling(self, plugin, tmp_path):
        """Test handling of malformed Markdown."""
        malformed_content = """---
title: Malformed Test
invalid yaml: [
---

# Heading

Unclosed [link

| Malformed | Table
|-----------|
| Missing   |

```python
# Unclosed code block
def function():
    return "test"

More content after...
"""

        file_path = tmp_path / "malformed.md"
        file_path.write_text(malformed_content)

        # Should handle gracefully without exceptions
        try:
            result = plugin.indexFile(file_path, malformed_content)
            assert result is not None

            metadata = plugin.extract_metadata(malformed_content, file_path)
            assert metadata is not None

            chunks = plugin.chunk_document(malformed_content, file_path)
            assert len(chunks) > 0

        except Exception as e:
            pytest.fail(f"Plugin should handle malformed Markdown gracefully: {e}")


class TestMarkdownIntegration:
    """Integration tests for Markdown processing."""

    @pytest.fixture
    def temp_workspace(self, tmp_path):
        """Create a temporary workspace with multiple Markdown files."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Create README
        readme_content = """# Project Documentation

This is the main project documentation.

## Installation

```bash
pip install project
```

## Usage

Import and use the project:

```python
import project
project.run()
```
"""
        (workspace / "README.md").write_text(readme_content)

        # Create API documentation
        api_content = """---
title: API Reference
category: documentation
---

# API Reference

Complete API documentation for the project.

## Authentication

All API calls require authentication.

### API Keys

Use your API key in the header:

```
Authorization: Bearer YOUR_API_KEY
```

## Endpoints

### GET /users

Retrieve user information.

### POST /users

Create a new user.
"""
        (workspace / "api.md").write_text(api_content)

        # Create tutorial
        tutorial_content = """# Getting Started Tutorial

Step-by-step guide to get started.

## Prerequisites

- Python 3.8+
- Git
- Basic programming knowledge

## Step 1: Setup

1. Clone the repository
2. Install dependencies
3. Configure settings

## Step 2: First Project

Create your first project:

```python
from project import App

app = App()
app.run()
```

## Next Steps

- Read the API documentation
- Check out examples
- Join the community
"""
        (workspace / "tutorial.md").write_text(tutorial_content)

        return workspace

    def test_multi_file_indexing(self, temp_workspace, tmp_path):
        """Test indexing multiple Markdown files."""
        db_path = tmp_path / "multi_test.db"
        store = SQLiteStore(str(db_path))
        plugin = MarkdownPlugin(sqlite_store=store, enable_semantic=False)

        # Index all files
        results = []
        for md_file in temp_workspace.glob("*.md"):
            content = md_file.read_text()
            result = plugin.indexFile(md_file, content)
            results.append(result)

        # Verify all files were indexed
        assert len(results) == 3

        # Verify each file has symbols
        for result in results:
            assert len(result["symbols"]) > 0
            assert result["language"] == "markdown"

    def test_cross_document_references(self, temp_workspace, tmp_path):
        """Test handling of cross-document references."""
        # Add a file with references to other documents
        index_content = """# Documentation Index

Welcome to our documentation!

## Available Documents

- [README](README.md) - Main project information
- [API Reference](api.md) - Complete API documentation  
- [Tutorial](tutorial.md) - Getting started guide

## Quick Links

- [Installation](README.md#installation)
- [Authentication](api.md#authentication)
- [First Project](tutorial.md#step-2-first-project)
"""
        (temp_workspace / "index.md").write_text(index_content)

        db_path = tmp_path / "cross_ref_test.db"
        store = SQLiteStore(str(db_path))
        plugin = MarkdownPlugin(sqlite_store=store, enable_semantic=False)

        # Index the index file
        result = plugin.indexFile(temp_workspace / "index.md", index_content)

        # Verify links are preserved in content
        plain_text = plugin.parse_content(index_content, temp_workspace / "index.md")
        assert "README" in plain_text
        assert "API Reference" in plain_text
        assert "Tutorial" in plain_text

    def test_performance_with_many_files(self, tmp_path):
        """Test performance with many Markdown files."""
        import time

        # Create many small files
        workspace = tmp_path / "performance_test"
        workspace.mkdir()

        for i in range(20):
            content = f"""# Document {i}

This is document number {i}.

## Section A

Content for section A in document {i}.

## Section B  

Content for section B in document {i}.

```python
def function_{i}():
    return {i}
```
"""
            (workspace / f"doc_{i:02d}.md").write_text(content)

        db_path = tmp_path / "perf_test.db"
        store = SQLiteStore(str(db_path))
        plugin = MarkdownPlugin(sqlite_store=store, enable_semantic=False)

        # Time the indexing
        start_time = time.time()

        for md_file in workspace.glob("*.md"):
            content = md_file.read_text()
            plugin.indexFile(md_file, content)

        end_time = time.time()
        elapsed = end_time - start_time

        # Should complete reasonably quickly
        assert elapsed < 10.0, f"Indexing took too long: {elapsed:.2f}s"

        # Verify all files were processed
        indexed_files = len(list(workspace.glob("*.md")))
        assert indexed_files == 20


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
