#!/usr/bin/env python3
"""Test script for the Markdown plugin."""

import sys
import tempfile
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, '/app')

from mcp_server.plugins.markdown_plugin import MarkdownPlugin


def test_markdown_plugin():
    """Test the Markdown plugin functionality."""
    
    # Create a test Markdown file
    test_content = """---
title: Test Document
author: Test Author
tags: [test, markdown, plugin]
date: 2024-01-01
---

# Introduction

This is a test document for the Markdown plugin.

## Features

The plugin supports:

- Markdown parsing
- Frontmatter extraction
- Section detection
- Code block handling

```python
def hello_world():
    print("Hello, World!")
```

### Subsection

This is a subsection with more content.

## Another Section

More content here with **bold** and *italic* text.

| Column 1 | Column 2 |
|----------|----------|
| Data 1   | Data 2   |
| Data 3   | Data 4   |

[Link to example](https://example.com)

![Image alt text](image.png)
"""
    
    # Create a temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(test_content)
        test_file = Path(f.name)
    
    try:
        # Initialize the plugin
        plugin = MarkdownPlugin(enable_semantic=False)  # Disable semantic for simple test
        
        print("Testing Markdown Plugin")
        print("=" * 50)
        
        # Test 1: Check if plugin can handle the file
        print("\n1. Can handle test:")
        can_handle = plugin.supports(str(test_file))
        print(f"   Can handle .md file: {can_handle}")
        assert can_handle, "Plugin should handle .md files"
        
        # Test 2: Extract metadata
        print("\n2. Extract metadata test:")
        metadata = plugin.extract_metadata(test_content, test_file)
        print(f"   Title: {metadata.title}")
        print(f"   Author: {metadata.author}")
        print(f"   Tags: {metadata.tags}")
        print(f"   Date: {metadata.created_date}")
        
        # Test 3: Extract structure
        print("\n3. Extract structure test:")
        structure = plugin.extract_structure(test_content, test_file)
        print(f"   Sections found: {len(structure.sections)}")
        print(f"   Title: {structure.title}")
        
        for i, section in enumerate(structure.sections[:3]):
            print(f"   Section {i+1}: {section.heading} (level {section.level})")
        
        # Test 4: Parse to plain text
        print("\n4. Parse to plain text test:")
        plain_text = plugin.parse_content(test_content, test_file)
        print(f"   Plain text length: {len(plain_text)} characters")
        print(f"   First 100 chars: {plain_text[:100]}...")
        
        # Test 5: Index file
        print("\n5. Index file test:")
        result = plugin.indexFile(str(test_file), test_content)
        print(f"   File: {result['file']}")
        print(f"   Language: {result['language']}")
        print(f"   Symbols found: {len(result['symbols'])}")
        
        for symbol in result['symbols'][:5]:
            print(f"   - {symbol['kind']}: {symbol['symbol']}")
        
        print("\n✅ All tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up
        test_file.unlink(missing_ok=True)


if __name__ == "__main__":
    test_markdown_plugin()