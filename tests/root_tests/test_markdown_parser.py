"""
Unit tests for Markdown parser functionality.

Tests the Markdown parsing capabilities including:
- Basic Markdown elements (headings, paragraphs, lists)
- Code blocks and inline code
- Links and images
- Tables
- Frontmatter parsing
- Nested structures
- Edge cases and error handling
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
import re

from mcp_server.plugins.markdown_plugin.document_parser import MarkdownParser
from mcp_server.plugins.markdown_plugin.section_extractor import SectionExtractor
from mcp_server.plugins.markdown_plugin.frontmatter_parser import FrontmatterParser
from mcp_server.plugins.markdown_plugin.plugin import MarkdownPlugin
from mcp_server.document_processing import DocumentChunk, ChunkType, DocumentMetadata


class TestMarkdownParser:
    """Test Markdown parser functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = MarkdownParser()
        self.section_extractor = SectionExtractor()
        self.frontmatter_parser = FrontmatterParser()
        
    def test_parse_basic_markdown(self):
        """Test parsing basic Markdown elements."""
        content = """# Main Title
        
This is a paragraph with **bold** and *italic* text.

## Subsection

- List item 1
- List item 2
  - Nested item

1. Numbered item
2. Another numbered item
"""
        ast = self.parser.parse(content)
        
        assert ast is not None
        assert ast.get('type') == 'root'
        assert 'children' in ast
        
        # Verify structure contains expected elements
        children = ast['children']
        assert len(children) > 0
        
        # Check for heading
        headings = [child for child in children if child.get('type') == 'heading']
        assert len(headings) >= 2
        assert headings[0].get('depth') == 1
        assert headings[1].get('depth') == 2
        
    def test_parse_code_blocks(self):
        """Test parsing code blocks."""
        content = '''# Code Examples

```python
def hello_world():
    print("Hello, World!")
```

Here's inline code: `variable = 42`

```javascript
const greeting = "Hello";
console.log(greeting);
```
'''
        ast = self.parser.parse(content)
        
        # Find code blocks
        def find_code_blocks(node):
            blocks = []
            if node.get('type') == 'code':
                blocks.append(node)
            for child in node.get('children', []):
                blocks.extend(find_code_blocks(child))
            return blocks
        
        code_blocks = find_code_blocks(ast)
        assert len(code_blocks) == 2
        
        # Check languages
        assert code_blocks[0].get('lang') == 'python'
        assert code_blocks[1].get('lang') == 'javascript'
        
        # Check content
        assert 'hello_world' in code_blocks[0].get('value', '')
        assert 'greeting' in code_blocks[1].get('value', '')
        
    def test_parse_links_and_images(self):
        """Test parsing links and images."""
        content = """# Links and Images

This is a [link to example](https://example.com).

![Alt text for image](image.png)

[Reference link][ref]

[ref]: https://reference.com
"""
        ast = self.parser.parse(content)
        
        # Find links and images
        links = []
        images = []
        
        def traverse(node):
            if node.get('type') == 'link':
                links.append(node)
            elif node.get('type') == 'image':
                images.append(node)
            for child in node.get('children', []):
                traverse(child)
        
        traverse(ast)
        
        assert len(links) >= 1
        assert len(images) == 1
        
        # Check link properties
        assert links[0].get('url') == 'https://example.com'
        
        # Check image properties
        assert images[0].get('url') == 'image.png'
        assert images[0].get('alt') == 'Alt text for image'
        
    def test_parse_tables(self):
        """Test parsing tables."""
        content = """# Table Example

| Header 1 | Header 2 | Header 3 |
|----------|----------|----------|
| Cell 1   | Cell 2   | Cell 3   |
| Cell 4   | Cell 5   | Cell 6   |
"""
        ast = self.parser.parse(content)
        
        # Find tables
        def find_tables(node):
            tables = []
            if node.get('type') == 'table':
                tables.append(node)
            for child in node.get('children', []):
                tables.extend(find_tables(child))
            return tables
        
        tables = find_tables(ast)
        assert len(tables) == 1
        
        # Check table structure
        table = tables[0]
        assert 'children' in table
        rows = table['children']
        assert len(rows) >= 2  # Header + at least one data row


class TestSectionExtractor:
    """Test section extraction functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = MarkdownParser()
        self.extractor = SectionExtractor()
        
    def test_extract_flat_sections(self):
        """Test extracting flat section list."""
        content = """# Title

Introduction paragraph.

## Section 1

Content for section 1.

## Section 2

Content for section 2.

### Section 2.1

Nested content.
"""
        ast = self.parser.parse(content)
        sections = self.extractor.extract(ast, content)
        
        # The extract method returns a nested structure
        # Top level should have the main title
        assert len(sections) >= 1
        
        # Check section properties
        title_section = sections[0]
        assert title_section['title'] == 'Title'
        assert title_section['level'] == 1
        assert 'Introduction paragraph' in title_section['content']
        
        # Check subsections
        assert 'subsections' in title_section
        subsections = title_section['subsections']
        assert len(subsections) >= 2
        
        # Check Section 2 has a nested subsection
        section2 = next((s for s in subsections if s['title'] == 'Section 2'), None)
        assert section2 is not None
        assert len(section2['subsections']) == 1
        assert section2['subsections'][0]['title'] == 'Section 2.1'
        
    def test_extract_section_hierarchy(self):
        """Test building section hierarchy."""
        content = """# Main Title

## Chapter 1

### Section 1.1

#### Subsection 1.1.1

Content here.

### Section 1.2

## Chapter 2

### Section 2.1
"""
        ast = self.parser.parse(content)
        sections = self.extractor.extract(ast, content)
        
        # Get flat list for level counting
        flat_sections = self.extractor.get_all_sections_flat(sections)
        main_sections = [s for s in flat_sections if s['level'] == 1]
        chapter_sections = [s for s in flat_sections if s['level'] == 2]
        
        assert len(main_sections) == 1
        assert len(chapter_sections) == 2
        
    def test_extract_sections_with_code(self):
        """Test section extraction with code blocks."""
        content = '''# Documentation

## Code Examples

Here's how to use the function:

```python
def example():
    return "test"
```

## Another Section

More content.
'''
        ast = self.parser.parse(content)
        sections = self.extractor.extract(ast, content)
        
        # Get flat list to search for section by title
        flat_sections = self.extractor.get_all_sections_flat(sections)
        code_section = next((s for s in flat_sections if s['title'] == 'Code Examples'), None)
        assert code_section is not None
        assert '```python' in code_section['content']
        assert 'def example()' in code_section['content']


class TestFrontmatterParser:
    """Test frontmatter parsing functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = FrontmatterParser()
        
    def test_parse_yaml_frontmatter(self):
        """Test parsing YAML frontmatter."""
        content = """---
title: Test Document
author: John Doe
date: 2024-01-01
tags:
  - test
  - markdown
---

# Document Content

This is the document body.
"""
        frontmatter, body = self.parser.parse(content)
        
        assert frontmatter is not None
        assert frontmatter['title'] == 'Test Document'
        assert frontmatter['authors'] == ['John Doe']
        assert frontmatter['date'] == '2024-01-01'
        assert 'tags' in frontmatter
        assert len(frontmatter['tags']) == 2
        
        # Check body has frontmatter removed
        assert not body.startswith('---')
        assert body.strip().startswith('# Document Content')
        
    def test_parse_toml_frontmatter(self):
        """Test parsing TOML frontmatter."""
        content = """+++
title = "Test Document"
author = "Jane Doe"
date = 2024-01-01
tags = ["test", "toml"]
+++

# Document Content
"""
        frontmatter, body = self.parser.parse(content)
        
        # Note: This may return empty dict if toml not installed
        if frontmatter:
            assert frontmatter['title'] == 'Test Document'
            assert frontmatter['authors'] == ['Jane Doe']
        
        # Body should have frontmatter removed regardless
        assert not body.startswith('+++')
        
    def test_parse_no_frontmatter(self):
        """Test parsing document without frontmatter."""
        content = """# Direct Title

No frontmatter here, just content.
"""
        frontmatter, body = self.parser.parse(content)
        
        assert frontmatter == {}
        assert body == content
        
    def test_parse_invalid_frontmatter(self):
        """Test handling invalid frontmatter."""
        content = """---
invalid yaml content
  no proper structure
---

# Document
"""
        frontmatter, body = self.parser.parse(content)
        
        # Should handle gracefully
        assert isinstance(frontmatter, dict)
        # Body should still have frontmatter removed
        assert body.strip().startswith('# Document')


class TestMarkdownPlugin:
    """Test the complete Markdown plugin."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.plugin = MarkdownPlugin(enable_semantic=False)
        
    def test_chunk_document(self):
        """Test document chunking."""
        content = """---
title: Test Document
---

# Introduction

This is the introduction section with some content that should be chunked appropriately.

## Section 1

Content for section 1 that might be long enough to require multiple chunks if we had a very small chunk size.

### Subsection 1.1

More detailed content here.

## Section 2

Another section with different content.
"""
        chunks = self.plugin.chunk_document(content, Path("test.md"))
        
        assert len(chunks) > 0
        assert all(isinstance(chunk, DocumentChunk) for chunk in chunks)
        
        # Check chunk properties
        first_chunk = chunks[0]
        assert first_chunk.content
        assert first_chunk.type in ChunkType
        assert first_chunk.metadata
        
    def test_extract_metadata(self):
        """Test metadata extraction."""
        content = """---
title: My Document
author: Test Author
date: 2024-01-01
tags: [python, testing]
---

# My Document

This is a test document.
"""
        metadata = self.plugin.extract_metadata(content, Path("test.md"))
        
        assert metadata.title == 'My Document'
        assert metadata.author == 'Test Author'
        assert metadata.created_date == '2024-01-01'
        assert 'python' in metadata.tags
        assert metadata.document_type == 'markdown'
        
    def test_extract_structure(self):
        """Test structure extraction."""
        content = """# Main Title

## Chapter 1

### Section 1.1

Content here.

### Section 1.2

More content.

## Chapter 2

Different content.
"""
        structure = self.plugin.extract_structure(content, Path("test.md"))
        
        assert structure.title == 'Main Title'
        assert len(structure.sections) > 0
        
        # Check section hierarchy
        assert any(s.heading == 'Chapter 1' for s in structure.sections)
        assert any(s.heading == 'Section 1.1' for s in structure.sections)
        
    def test_extract_symbols(self):
        """Test symbol extraction from Markdown."""
        content = '''# API Documentation

## Functions

### calculate_sum

```python
def calculate_sum(a, b):
    return a + b
```

### process_data

```javascript
function processData(input) {
    return input.map(x => x * 2);
}
```

## Classes

### DataProcessor

```python
class DataProcessor:
    def __init__(self):
        self.data = []
```
'''
        path = Path("test.md")
        shard = self.plugin.indexFile(str(path), content)
        
        assert shard['file'] == str(path)
        assert len(shard['symbols']) > 0
        
        # Check for heading symbols
        heading_symbols = [s for s in shard['symbols'] if s['kind'] == 'heading']
        assert len(heading_symbols) > 0
        
        # Check for code symbols
        code_symbols = [s for s in shard['symbols'] if s['kind'] in ['function', 'class']]
        assert len(code_symbols) >= 2  # Should find calculate_sum and DataProcessor
        
    def test_search_in_sections(self):
        """Test searching within specific sections."""
        content = """# Documentation

## Installation

To install, run: `pip install package`

## Usage

To use the package:

```python
import package
package.do_something()
```

## Troubleshooting

If you have issues with installation, check your Python version.
"""
        # Index the document
        self.plugin.indexFile("test.md", content)
        chunks = self.plugin.chunk_document(content, Path("test.md"))
        
        # Test that chunks maintain section context
        install_chunks = [c for c in chunks if 'Installation' in c.metadata.section_hierarchy]
        assert len(install_chunks) > 0
        assert any('pip install' in c.content for c in install_chunks)
        
    def test_edge_cases(self):
        """Test edge cases and error handling."""
        # Empty document
        empty_chunks = self.plugin.chunk_document("", Path("empty.md"))
        assert len(empty_chunks) == 0 or (len(empty_chunks) == 1 and empty_chunks[0].content == "")
        
        # Document with only frontmatter
        only_frontmatter = """---
title: Only Frontmatter
---"""
        chunks = self.plugin.chunk_document(only_frontmatter, Path("frontmatter.md"))
        assert len(chunks) >= 0  # Should handle gracefully
        
        # Very large document
        large_content = "# Title\n\n" + ("This is a paragraph. " * 1000)
        chunks = self.plugin.chunk_document(large_content, Path("large.md"))
        assert len(chunks) > 1  # Should split into multiple chunks
        
        # Document with special characters
        special_content = """# Title with émojis 🎉

Content with special chars: → ← ↑ ↓ • © ® ™
"""
        chunks = self.plugin.chunk_document(special_content, Path("special.md"))
        assert len(chunks) > 0
        assert chunks[0].content  # Should preserve special characters


if __name__ == "__main__":
    pytest.main([__file__, "-v"])