#!/usr/bin/env python3
"""Test various edge cases in document processing."""

import tempfile
import pytest
from pathlib import Path
import os
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.plugins.markdown_plugin import MarkdownPlugin
from mcp_server.plugins.plaintext_plugin import PlainTextPlugin
from mcp_server.plugins.python_plugin.plugin import Plugin as PythonPlugin
from mcp_server.document_processing import ChunkType, DocumentChunk


class TestDocumentEdgeCases:
    """Test various edge cases in document processing."""
    
    @pytest.fixture
    def setup_plugins(self):
        """Setup plugins for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SQLiteStore(str(Path(tmpdir) / "test.db"))
            
            markdown_plugin = MarkdownPlugin(enable_semantic=False)
            plaintext_config = {
                'name': 'plaintext',
                'code': 'plaintext',
                'extensions': ['.txt', '.text'],
                'file_pattern': r'.*\.(txt|text)$'
            }
            plaintext_plugin = PlainTextPlugin(plaintext_config, enable_semantic=False)
            python_plugin = PythonPlugin()
            
            yield {
                'markdown': markdown_plugin,
                'plaintext': plaintext_plugin,
                'python': python_plugin,
                'store': store,
                'tmpdir': tmpdir
            }
    
    def test_zero_byte_files(self, setup_plugins):
        """Test handling of zero-byte files."""
        plugins = setup_plugins
        tmpdir = plugins['tmpdir']
        
        # Create zero-byte files
        zero_md = Path(tmpdir) / 'zero.md'
        zero_py = Path(tmpdir) / 'zero.py'
        zero_txt = Path(tmpdir) / 'zero.txt'
        
        zero_md.touch()
        zero_py.touch()
        zero_txt.touch()
        
        # Should handle gracefully
        result1 = plugins['markdown'].indexFile(str(zero_md), '')
        assert result1.symbols == []
        
        result2 = plugins['python'].indexFile(str(zero_py), '')
        assert result2.symbols == []
        
        result3 = plugins['plaintext'].indexFile(str(zero_txt), '')
        assert result3.symbols == []
    
    def test_single_character_files(self, setup_plugins):
        """Test handling of single character files."""
        plugins = setup_plugins
        
        # Single character markdown
        result1 = plugins['markdown'].indexFile('single.md', '#')
        assert result1 is not None
        
        result2 = plugins['markdown'].indexFile('single2.md', 'a')
        assert result2 is not None
        
        # Single character code
        result3 = plugins['python'].indexFile('single.py', '#')
        assert result3 is not None
    
    def test_files_with_only_whitespace(self, setup_plugins):
        """Test handling of files containing only whitespace."""
        plugins = setup_plugins
        
        # Various whitespace combinations
        whitespace_contents = [
            '   ',  # Spaces
            '\t\t\t',  # Tabs
            '\n\n\n',  # Newlines
            ' \t \n \r\n ',  # Mixed
            '\u00A0\u2000\u2001',  # Non-breaking spaces
        ]
        
        for i, content in enumerate(whitespace_contents):
            result = plugins['plaintext'].indexFile(f'white{i}.txt', content)
            assert result is not None
            # Should produce minimal or no chunks
            chunks = plugins['plaintext'].chunk_document(content, Path(f'white{i}.txt'))
            assert len(chunks) <= 1
    
    def test_extreme_nesting_levels(self, setup_plugins):
        """Test handling of extremely nested document structures."""
        plugin = setup_plugins['markdown']
        
        # Generate deeply nested headings
        content = ""
        for i in range(1, 10):
            content += f"{'#' * min(i, 6)} Heading Level {i}\n\nContent at level {i}\n\n"
        
        # Add deeply nested lists
        content += "- Level 1\n"
        indent = "  "
        for i in range(2, 20):
            content += f"{indent * (i-1)}- Level {i}\n"
        
        result = plugin.indexFile('nested.md', content)
        assert result is not None
        
        # Check structure extraction
        structure = plugin.extract_structure(content, Path('nested.md'))
        assert structure is not None
        assert len(structure.sections) > 0
    
    def test_unusual_file_extensions(self, setup_plugins):
        """Test handling of files with unusual extensions."""
        plugins = setup_plugins
        
        # Markdown with unusual extensions
        md_contents = "# Test\n\nContent"
        extensions = ['.markdown', '.mdown', '.mkd', '.mdx']
        
        for ext in extensions:
            result = plugins['markdown'].indexFile(f'test{ext}', md_contents)
            assert result is not None
            assert len(result.symbols) > 0
    
    def test_files_with_no_extension(self, setup_plugins):
        """Test handling of files without extensions."""
        plugins = setup_plugins
        
        # README without extension (common in repos)
        content = "# Project Name\n\nDescription"
        result = plugins['markdown'].indexFile('README', content)
        assert result is not None
        
        # License file without extension
        result2 = plugins['plaintext'].indexFile('LICENSE', 'MIT License...')
        assert result2 is not None
    
    def test_extremely_long_identifiers(self, setup_plugins):
        """Test handling of extremely long identifiers/names."""
        plugin = setup_plugins['python']
        
        # Very long function name
        long_name = 'a' * 1000
        content = f"""def {long_name}():
    pass

class {long_name}Class:
    def {long_name}_method(self):
        pass"""
        
        result = plugin.indexFile('long_names.py', content)
        assert result is not None
        # Should truncate or handle gracefully
        assert all(len(sym.name) <= 1000 for sym in result.symbols)
    
    def test_rapid_content_changes(self, setup_plugins):
        """Test handling of rapid content changes (simulating real-time editing)."""
        plugin = setup_plugins['markdown']
        
        # Simulate rapid edits
        contents = [
            "# Title",
            "# Title\n\n",
            "# Title\n\nPara",
            "# Title\n\nParagraph",
            "# Title\n\nParagraph\n\n## Section",
            "# Title\n\nParagraph\n\n## Section 2",
        ]
        
        for i, content in enumerate(contents):
            result = plugin.indexFile('rapid.md', content)
            assert result is not None
            chunks = plugin.chunk_document(content, Path('rapid.md'))
            assert chunks is not None
    
    def test_files_with_unusual_line_endings(self, setup_plugins):
        """Test handling of files with various line ending styles."""
        plugins = setup_plugins
        
        # Different line ending styles
        contents = [
            "Line 1\nLine 2\nLine 3",  # Unix (LF)
            "Line 1\r\nLine 2\r\nLine 3",  # Windows (CRLF)
            "Line 1\rLine 2\rLine 3",  # Classic Mac (CR)
            "Line 1\n\rLine 2\r\nLine 3",  # Mixed
        ]
        
        for i, content in enumerate(contents):
            result = plugins['plaintext'].indexFile(f'endings{i}.txt', content)
            assert result is not None
            
            # Should normalize to consistent chunks
            chunks = plugins['plaintext'].chunk_document(content, Path(f'endings{i}.txt'))
            assert len(chunks) > 0
    
    def test_chunk_boundary_edge_cases(self, setup_plugins):
        """Test edge cases in chunk boundary detection."""
        plugin = setup_plugins['markdown']
        
        # Content that might confuse chunk boundaries
        content = """# Title

This is a paragraph that ends with a code fence marker```

```python
# This is actual code
```

This paragraph starts with ``` but it's not code.

> This is a quote
that spans multiple lines
> with inconsistent markers

- List item that contains
  ```
  code in the middle
  ```
  of the item"""
        
        chunks = plugin.chunk_document(content, Path('boundaries.md'))
        assert chunks is not None
        assert len(chunks) > 0
        
        # Verify chunks don't split in weird places
        for chunk in chunks:
            assert chunk.content.strip() != ''
            assert chunk.type in ChunkType
    
    def test_metadata_extraction_edge_cases(self, setup_plugins):
        """Test edge cases in metadata extraction."""
        plugin = setup_plugins['markdown']
        
        # Various metadata edge cases
        test_cases = [
            # Empty frontmatter
            ("---\n---\n# Content", {}),
            # Frontmatter with only comments
            ("---\n# comment\n---\n# Content", {}),
            # Duplicate keys
            ("---\ntitle: First\ntitle: Second\n---\n# Content", {'title': 'Second'}),
            # Numeric values
            ("---\ncount: 42\npi: 3.14\n---\n# Content", {'count': 42, 'pi': 3.14}),
            # Boolean values
            ("---\npublished: true\ndraft: false\n---\n# Content", {'published': True, 'draft': False}),
            # Null values
            ("---\nauthor: null\n---\n# Content", {'author': None}),
        ]
        
        for content, expected_keys in test_cases:
            metadata = plugin.extract_metadata(content, Path('meta.md'))
            assert metadata is not None
    
    def test_concurrent_indexing_same_file(self, setup_plugins):
        """Test handling of concurrent indexing of the same file."""
        plugin = setup_plugins['markdown']
        
        content = "# Test\n\nContent for concurrent test"
        
        # Index same file multiple times rapidly
        results = []
        for i in range(5):
            result = plugin.indexFile('concurrent.md', content + f"\n\nIteration {i}")
            results.append(result)
        
        # All should succeed
        assert all(r is not None for r in results)
        assert all(len(r.symbols) > 0 for r in results)
    
    def test_special_markdown_elements(self, setup_plugins):
        """Test handling of special Markdown elements."""
        plugin = setup_plugins['markdown']
        
        # Special elements that might cause issues
        content = """# Test

<!-- HTML comment -->

<details>
<summary>Collapsible section</summary>

Hidden content here

</details>

---

___

***

~~Strikethrough text~~

==Highlighted text==

^Superscript^ and ~Subscript~

++Inserted++ and --Deleted--

::: warning
Custom container
:::

@[youtube](dQw4w9WgXcQ)

- [ ] Unchecked task
- [x] Checked task
- [X] Also checked

| Emoji | Code |
|:-----:|:----:|
| 😀 | `:smile:` |
| 🚀 | `:rocket:` |"""
        
        result = plugin.indexFile('special.md', content)
        assert result is not None
        
        chunks = plugin.chunk_document(content, Path('special.md'))
        assert len(chunks) > 0
    
    def test_performance_with_many_small_chunks(self, setup_plugins):
        """Test performance with documents that produce many small chunks."""
        plugin = setup_plugins['markdown']
        
        # Generate content with many small sections
        content = ""
        for i in range(100):
            content += f"## Section {i}\n\nSmall content {i}\n\n"
        
        import time
        start = time.time()
        
        result = plugin.indexFile('many_chunks.md', content)
        chunks = plugin.chunk_document(content, Path('many_chunks.md'))
        
        elapsed = time.time() - start
        
        assert result is not None
        assert len(chunks) > 0
        # Should complete in reasonable time (< 5 seconds)
        assert elapsed < 5.0
    
    def test_search_with_special_characters(self, setup_plugins):
        """Test searching for content with special characters."""
        plugins = setup_plugins
        store = plugins['store']
        
        # Index content with special characters
        content = """# Special Characters

Code with symbols: `foo->bar()`, `obj.method()`, `array[0]`

Math: $x^2 + y^2 = z^2$

Regex: `/^[a-zA-Z0-9]+$/`

Path: `C:\\Users\\Test\\file.txt`"""
        
        plugins['markdown'].indexFile('special_chars.md', content)
        
        # Search for special character patterns
        test_queries = [
            'foo->bar',
            'array[0]',
            'C:\\Users',
            '^[a-zA-Z0-9]+$'
        ]
        
        for query in test_queries:
            results = store.search_symbols_fts(query)
            # Should handle special characters in search


if __name__ == '__main__':
    pytest.main([__file__, '-v'])