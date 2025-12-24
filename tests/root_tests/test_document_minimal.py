#!/usr/bin/env python3
"""Minimal test for document processing functionality."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_server.plugins.language_registry import LANGUAGE_CONFIGS
from mcp_server.plugins.markdown_plugin.plugin import MarkdownPlugin
from mcp_server.plugins.plaintext_plugin.plugin import PlainTextPlugin


def test_minimal():
    """Test document plugins with minimal setup."""
    print("🧪 Testing Document Processing - Minimal Test")
    print("=" * 50)

    # Test 1: Create plugins without store
    print("\n✅ Test 1: Plugin Creation")
    try:
        # Get language configs
        markdown_config = LANGUAGE_CONFIGS.get(
            "markdown",
            {
                "code": "markdown",
                "name": "Markdown",
                "extensions": [".md", ".markdown"],
                "symbols": [],
                "query": "",
            },
        )
        plaintext_config = LANGUAGE_CONFIGS.get(
            "plaintext",
            {
                "code": "plaintext",
                "name": "Plain Text",
                "extensions": [".txt", ".text", ".log"],
                "symbols": [],
                "query": "",
            },
        )

        markdown_plugin = MarkdownPlugin(language_config=markdown_config, sqlite_store=None)
        plaintext_plugin = PlainTextPlugin(language_config=plaintext_config, sqlite_store=None)
        print("  Successfully created both plugins")
        print(f"  Markdown extensions: {markdown_plugin.extensions}")
        print(f"  PlainText extensions: {plaintext_plugin.extensions}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return

    # Test 2: Test file support
    print("\n✅ Test 2: File Support Check")
    test_files = ["README.md", "document.txt", "notes.text", "changelog.log", "script.py"]

    for filename in test_files:
        md_supports = markdown_plugin.supports(Path(filename))
        txt_supports = plaintext_plugin.supports(Path(filename))
        print(f"  {filename}: Markdown={md_supports}, PlainText={txt_supports}")

    # Test 3: Index a simple markdown file
    print("\n✅ Test 3: Basic Markdown Indexing")
    try:
        test_content = """# Test Document

This is a test document for validation.

## Section 1
Some content here.

### Subsection 1.1
More details.

## Section 2
Another section with code:

```python
def hello():
    print("Hello")
```
"""

        result = markdown_plugin.index_file("test.md", test_content)

        # Convert generator to list if needed
        if hasattr(result, "__iter__") and not isinstance(result, (list, tuple)):
            result = list(result)

        print(f"  Indexed {len(result) if result else 0} symbols")

        if result:
            for i, symbol in enumerate(result[:3]):  # Show first 3
                print(
                    f"  Symbol {i+1}: {symbol.get('name', 'unnamed')} ({symbol.get('type', 'unknown')})"
                )
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback

        traceback.print_exc()

    # Test 4: Index a simple text file
    print("\n✅ Test 4: Basic PlainText Indexing")
    try:
        test_content = """Introduction

This document describes the code indexing system. It provides fast symbol search and navigation.

Installation

To install the system, follow these steps:
1. Clone the repository
2. Install dependencies
3. Run the setup script

Configuration

The system can be configured using environment variables or a config file.
"""

        result = plaintext_plugin.index_file("test.txt", test_content)

        # Convert generator to list if needed
        if hasattr(result, "__iter__") and not isinstance(result, (list, tuple)):
            result = list(result)

        print(f"  Indexed {len(result) if result else 0} symbols")

        if result:
            for i, symbol in enumerate(result[:3]):  # Show first 3
                print(
                    f"  Symbol {i+1}: {symbol.get('name', 'unnamed')} ({symbol.get('type', 'unknown')})"
                )
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 50)
    print("✅ Minimal test complete!")


if __name__ == "__main__":
    test_minimal()
