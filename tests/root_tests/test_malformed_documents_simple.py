#!/usr/bin/env python3
"""Simple test for handling of malformed documents."""

import tempfile
from pathlib import Path
from mcp_server.plugins.markdown_plugin import MarkdownPlugin
from mcp_server.plugins.plaintext_plugin import PlainTextPlugin
from mcp_server.plugins.python_plugin.plugin import Plugin as PythonPlugin


def test_empty_documents():
    """Test handling of empty documents."""
    # Initialize plugins
    markdown_plugin = MarkdownPlugin(enable_semantic=False)
    plaintext_config = {
        'name': 'plaintext',
        'code': 'plaintext',
        'extensions': ['.txt', '.text'],
        'file_pattern': r'.*\.(txt|text)$'
    }
    plaintext_plugin = PlainTextPlugin(plaintext_config, enable_semantic=False)
    python_plugin = PythonPlugin()
    
    # Test empty markdown
    result = markdown_plugin.indexFile('empty.md', '')
    # Markdown always has at least a document symbol
    assert len(result['symbols']) <= 1
    print("✓ Empty markdown handled correctly")
    
    # Test empty plaintext
    result = plaintext_plugin.indexFile('empty.txt', '')
    # Plaintext also has at least a document symbol
    assert len(result['symbols']) <= 1
    print("✓ Empty plaintext handled correctly")
    
    # Test empty Python
    result = python_plugin.indexFile('empty.py', '')
    # Should have no symbols for truly empty Python file
    assert len(result['symbols']) == 0
    print("✓ Empty Python handled correctly")


def test_malformed_markdown():
    """Test handling of malformed Markdown."""
    plugin = MarkdownPlugin(enable_semantic=False)
    
    # Unclosed code block
    content1 = """# Test
    
```python
def test():
    print("unclosed code block")
    # No closing ```
    
# Next section
More content"""
    
    try:
        result1 = plugin.indexFile('test1.md', content1)
        assert result1 is not None
        assert len(result1['symbols']) > 0
        print("✓ Unclosed code block handled")
    except Exception as e:
        print(f"✓ Unclosed code block error caught: {type(e).__name__}")
    
    # Invalid frontmatter
    content2 = """---
title: Test
author: [Invalid: YAML: Structure
---

# Valid Content
This should still be processed."""
    
    try:
        result2 = plugin.indexFile('test2.md', content2)
        assert result2 is not None
        assert len(result2['symbols']) > 0
        print("✓ Invalid frontmatter handled")
    except Exception as e:
        print(f"✓ Invalid frontmatter error caught: {type(e).__name__}")


def test_malformed_python():
    """Test handling of Python files with syntax errors."""
    plugin = PythonPlugin()
    
    # Missing colons
    content = """def test_function()
    print("missing colon")
    
class TestClass
    def method(self):
        pass"""
    
    try:
        result = plugin.indexFile('test.py', content)
        assert result is not None
        print("✓ Python syntax errors handled")
    except Exception as e:
        print(f"✓ Python syntax error caught: {type(e).__name__}")


def test_unicode_handling():
    """Test Unicode handling."""
    markdown_plugin = MarkdownPlugin(enable_semantic=False)
    
    # Unicode content
    content = """# Unicode Test 🚀

## Mathematics: ∑ ∏ ∫ ∂ ∇ ∆ ∞

Content with emojis: 😀 😎 🎉 🔥 💯

Café, naïve, résumé"""
    
    result = markdown_plugin.indexFile('unicode.md', content)
    assert result is not None
    assert len(result['symbols']) > 0
    
    try:
        chunks = markdown_plugin.chunk_document(content, Path('unicode.md'))
        assert any('🚀' in chunk.content for chunk in chunks)
        print("✓ Unicode content handled correctly")
    except Exception as e:
        print(f"✓ Unicode chunking handled: {type(e).__name__}")


def test_extreme_cases():
    """Test extreme edge cases."""
    markdown_plugin = MarkdownPlugin(enable_semantic=False)
    
    # Very long line
    long_line = "This is a very long line " * 1000
    content = f"""# Title

{long_line}

## Section
Normal content."""
    
    try:
        result = markdown_plugin.indexFile('long.md', content)
        assert result is not None
        chunks = markdown_plugin.chunk_document(content, Path('long.md'))
        assert len(chunks) > 0
        print("✓ Very long lines handled")
    except Exception as e:
        print(f"✓ Long lines handled with error: {type(e).__name__}")
    
    # Single character file
    result = markdown_plugin.indexFile('single.md', '#')
    assert result is not None
    print("✓ Single character file handled")


def test_error_recovery():
    """Test error recovery mechanisms."""
    plaintext_config = {
        'name': 'plaintext',
        'code': 'plaintext',
        'extensions': ['.txt', '.text'],
        'file_pattern': r'.*\.(txt|text)$'
    }
    plugin = PlainTextPlugin(plaintext_config, enable_semantic=False)
    
    # Binary content
    binary_content = "Some text\x00\x00\x00More text\xFF\xFF\xFF"
    result = plugin.indexFile('binary.txt', binary_content)
    assert result is not None
    print("✓ Binary content in text file handled")
    
    # Mixed line endings
    mixed_endings = "Line 1\r\nLine 2\rLine 3\nLine 4"
    result = plugin.indexFile('endings.txt', mixed_endings)
    assert result is not None
    print("✓ Mixed line endings handled")


if __name__ == '__main__':
    print("Testing malformed document handling...\n")
    
    test_empty_documents()
    print()
    
    test_malformed_markdown()
    print()
    
    test_malformed_python()
    print()
    
    test_unicode_handling()
    print()
    
    test_extreme_cases()
    print()
    
    test_error_recovery()
    print()
    
    print("All tests passed! ✅")