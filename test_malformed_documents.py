#!/usr/bin/env python3
"""Test handling of malformed documents."""

import tempfile
import pytest
from pathlib import Path
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.plugins.markdown_plugin import MarkdownPlugin
from mcp_server.plugins.plaintext_plugin import PlainTextPlugin
from mcp_server.plugins.python_plugin.plugin import Plugin as PythonPlugin
from mcp_server.plugins.js_plugin.plugin import Plugin as JsPlugin


class TestMalformedDocuments:
    """Test handling of various malformed document scenarios."""
    
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
            js_plugin = JsPlugin()
            
            yield {
                'markdown': markdown_plugin,
                'plaintext': plaintext_plugin,
                'python': python_plugin,
                'javascript': js_plugin,
                'store': store
            }
    
    def test_empty_document(self, setup_plugins):
        """Test handling of empty documents."""
        plugins = setup_plugins
        
        # Test empty markdown
        result = plugins['markdown'].indexFile('empty.md', '')
        assert result.symbols == []
        assert result.references == []
        
        # Test empty plaintext
        result = plugins['plaintext'].indexFile('empty.txt', '')
        assert result.symbols == []
        
        # Test empty Python
        result = plugins['python'].indexFile('empty.py', '')
        assert result.symbols == []
    
    def test_malformed_markdown_frontmatter(self, setup_plugins):
        """Test handling of malformed YAML frontmatter."""
        plugin = setup_plugins['markdown']
        
        # Unclosed frontmatter
        content1 = """---
title: Test
author: Test Author
# Missing closing ---

# Content
This is content."""
        
        result1 = plugin.indexFile('test1.md', content1)
        assert len(result1.symbols) > 0  # Should still process content
        
        # Invalid YAML
        content2 = """---
title: Test
author: [Invalid: YAML: Structure
---

# Valid Content
This should still be processed."""
        
        result2 = plugin.indexFile('test2.md', content2)
        assert len(result2.symbols) > 0
        
        # Frontmatter with invalid characters
        content3 = """---
title: Test\x00\x01\x02
author: Test\xFF\xFE
---

# Content
Regular content here."""
        
        result3 = plugin.indexFile('test3.md', content3)
        assert len(result3.symbols) > 0
    
    def test_incomplete_markdown_structures(self, setup_plugins):
        """Test handling of incomplete Markdown structures."""
        plugin = setup_plugins['markdown']
        
        # Unclosed code blocks
        content1 = """# Test
        
```python
def test():
    print("unclosed code block")
    # No closing ```
    
# Next section
More content"""
        
        result1 = plugin.indexFile('test1.md', content1)
        assert len(result1.symbols) > 0
        
        # Malformed tables
        content2 = """# Tables

| Header 1 | Header 2 |
|----------|
| Cell 1   | Cell 2 | Extra cell |
| Missing  |

Regular paragraph."""
        
        result2 = plugin.indexFile('test2.md', content2)
        assert len(result2.symbols) > 0
        
        # Broken link references
        content3 = """# Links

This is a [broken link][ref1] and [another][].

[ref1]: 
[]: http://example.com

Also [incomplete]("""
        
        result3 = plugin.indexFile('test3.md', content3)
        assert len(result3.symbols) > 0
    
    def test_malformed_python_syntax(self, setup_plugins):
        """Test handling of Python files with syntax errors."""
        plugin = setup_plugins['python']
        
        # Missing colons
        content1 = """def test_function()
    print("missing colon")
    
class TestClass
    def method(self):
        pass"""
        
        result1 = plugin.indexFile('test1.py', content1)
        # Should still attempt to extract what it can
        assert result1 is not None
        
        # Unmatched brackets
        content2 = """def function():
    data = [1, 2, 3
    print(data))
    
def another():
    return {"key": "value"}}"""
        
        result2 = plugin.indexFile('test2.py', content2)
        assert result2 is not None
        
        # Invalid indentation
        content3 = """def function():
print("bad indent")
    if True:
  print("inconsistent")
        pass"""
        
        result3 = plugin.indexFile('test3.py', content3)
        assert result3 is not None
    
    def test_malformed_javascript_syntax(self, setup_plugins):
        """Test handling of JavaScript files with syntax errors."""
        plugin = setup_plugins['javascript']
        
        # Missing brackets
        content1 = """function test() {
    console.log("missing closing bracket"
    
function another() {
    return {key: "value";
}"""
        
        result1 = plugin.indexFile('test1.js', content1)
        assert result1 is not None
        
        # Invalid JSON in code
        content2 = """const data = {
    "key": "value",
    "invalid": undefined,
    "trailing": "comma",
};

function process() {
    return JSON.parse('{"bad": json"}');
}"""
        
        result2 = plugin.indexFile('test2.js', content2)
        assert result2 is not None
    
    def test_binary_content_in_text_files(self, setup_plugins):
        """Test handling of binary content in text files."""
        plugins = setup_plugins
        
        # Binary content in markdown
        binary_md = b"# Title\n\n\x00\x01\x02\xFF\xFE\xFD\n\nText content"
        result1 = plugins['markdown'].indexFile('binary.md', binary_md.decode('utf-8', errors='replace'))
        assert result1 is not None
        
        # Binary content in plaintext
        binary_txt = b"Some text\x00\x00\x00More text\xFF\xFF\xFF"
        result2 = plugins['plaintext'].indexFile('binary.txt', binary_txt.decode('utf-8', errors='replace'))
        assert result2 is not None
    
    def test_extremely_long_lines(self, setup_plugins):
        """Test handling of files with extremely long lines."""
        plugins = setup_plugins
        
        # Markdown with very long line
        long_line = "This is a very long line " * 1000  # ~25k characters
        content1 = f"""# Title

{long_line}

## Section
Normal content."""
        
        result1 = plugins['markdown'].indexFile('long.md', content1)
        assert result1 is not None
        chunks = plugins['markdown'].chunk_document(content1, Path('long.md'))
        assert len(chunks) > 0
        
        # Python with long string
        content2 = f'''def function():
    long_string = "{long_line}"
    return len(long_string)'''
        
        result2 = plugins['python'].indexFile('long.py', content2)
        assert result2 is not None
    
    def test_circular_references(self, setup_plugins):
        """Test handling of circular references in documents."""
        plugin = setup_plugins['markdown']
        
        # Circular link references
        content = """# Document

See [Section A](#section-a) which links to [Section B](#section-b).

## Section A {#section-a}
This links back to [Section B](#section-b).

## Section B {#section-b}
This links back to [Section A](#section-a).

[ref1]: #ref2
[ref2]: #ref1"""
        
        result = plugin.indexFile('circular.md', content)
        assert result is not None
        assert len(result.symbols) > 0
    
    def test_mixed_encodings(self, setup_plugins):
        """Test handling of mixed character encodings."""
        plugins = setup_plugins
        
        # Mix of valid UTF-8 and Latin-1
        content = "# Title\n\nCafé résumé naïve\n\n## Seção\n\nConteúdo português"
        
        # Should handle without errors
        result1 = plugins['markdown'].indexFile('mixed.md', content)
        assert result1 is not None
        
        result2 = plugins['plaintext'].indexFile('mixed.txt', content)
        assert result2 is not None
    
    def test_malformed_nested_structures(self, setup_plugins):
        """Test handling of deeply nested or malformed structures."""
        plugin = setup_plugins['markdown']
        
        # Deeply nested lists with inconsistent markers
        content1 = """# Lists

- Level 1
  * Level 2
    + Level 3
      - Level 4
        * Level 5
          + Level 6
            Missing marker
              - Level 8
  Back to level 2 without proper outdent
- Another level 1"""
        
        result1 = plugin.indexFile('nested.md', content1)
        assert result1 is not None
        
        # Nested blockquotes with code
        content2 = """# Quotes

> Level 1 quote
> > Level 2 quote
> > > Level 3 quote
> > > ```python
> > > def nested():
> > >     print("in nested quote")
> > > ```
> > Still in level 2?
> Back to level 1"""
        
        result2 = plugin.indexFile('quotes.md', content2)
        assert result2 is not None
    
    def test_search_on_malformed_documents(self, setup_plugins):
        """Test searching across malformed documents."""
        plugins = setup_plugins
        store = plugins['store']
        
        # Index various malformed documents
        plugins['markdown'].indexFile('bad1.md', '# Test\n\n```\nUnclosed code')
        plugins['markdown'].indexFile('bad2.md', '---\nbad: yaml: here\n---\n# Content')
        plugins['python'].indexFile('bad.py', 'def test(\n    print("bad")')
        
        # Search should still work
        results = store.search_symbols_fts('test')
        assert len(results) > 0
        
        results = store.search_symbols_fts('content')
        assert len(results) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])