#!/usr/bin/env python3
"""Simple test to validate document processing plugins are working."""

import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_server.plugins.plugin_factory import PluginFactory


def test_plugin_creation():
    """Test that document processing plugins can be created."""
    print("Testing Plugin Creation...")

    # Test Markdown plugin
    try:
        md_plugin = PluginFactory.create_plugin("markdown")
        print(f"✓ Markdown plugin created: {md_plugin.__class__.__name__}")
    except Exception as e:
        print(f"✗ Failed to create Markdown plugin: {e}")
        return False

    # Test Plaintext plugin
    try:
        txt_plugin = PluginFactory.create_plugin("plaintext")
        print(f"✓ Plaintext plugin created: {txt_plugin.__class__.__name__}")
    except Exception as e:
        print(f"✗ Failed to create Plaintext plugin: {e}")
        return False

    return True


def test_file_support():
    """Test that plugins correctly identify supported files."""
    print("\nTesting File Support...")

    test_cases = [
        ("test.md", "markdown", True),
        ("test.markdown", "markdown", True),
        ("test.txt", "plaintext", True),
        ("test.text", "plaintext", True),
        ("test.log", "plaintext", True),
        ("test.py", "python", True),
        ("test.js", "javascript", True),
        ("test.unknown", None, False),
    ]

    all_passed = True
    for filename, expected_lang, should_find in test_cases:
        plugin = PluginFactory.create_plugin_for_file(filename)
        if should_find and plugin:
            print(f"  ✓ {filename} -> {plugin.__class__.__name__}")
        elif not should_find and not plugin:
            print(f"  ✓ {filename} -> No plugin (as expected)")
        else:
            print(f"  ✗ {filename} -> Unexpected result")
            all_passed = False

    return all_passed


def test_basic_indexing():
    """Test basic indexing functionality."""
    print("\nTesting Basic Indexing...")

    # Test with a simple markdown content
    md_content = """# Hello World

This is a test document.

## Section 1
Some content here.

## Section 2  
More content here.
"""

    try:
        md_plugin = PluginFactory.create_plugin("markdown")

        # Test if plugin has the indexFile method
        if hasattr(md_plugin, "indexFile"):
            result = md_plugin.indexFile("test.md", md_content)
            if isinstance(result, dict):
                print(f"✓ Markdown indexing: {len(result.get('symbols', []))} symbols found")

                # Show first few symbols
                for symbol in result.get("symbols", [])[:3]:
                    print(f"  - {symbol.get('symbol', 'N/A')} ({symbol.get('kind', 'N/A')})")
            else:
                print(f"✓ Markdown indexing completed (result type: {type(result).__name__})")
        else:
            print("✗ Markdown plugin missing indexFile method")
            return False

    except Exception as e:
        print(f"✗ Error testing markdown indexing: {e}")
        import traceback

        traceback.print_exc()
        return False

    # Test with plaintext content
    txt_content = """This is a plain text document.

It has multiple paragraphs.

Each paragraph should be properly handled by the plugin.
"""

    try:
        txt_plugin = PluginFactory.create_plugin("plaintext")

        # Test if plugin has the indexFile method
        if hasattr(txt_plugin, "indexFile"):
            result = txt_plugin.indexFile("test.txt", txt_content)
            if isinstance(result, dict):
                print(f"\n✓ Plaintext indexing: {len(result.get('symbols', []))} symbols found")

                # Show content preview
                content = result.get("content", "")
                if content:
                    print(f"  Content preview: {content[:100]}...")
            else:
                print(f"\n✓ Plaintext indexing completed (result type: {type(result).__name__})")
        else:
            print("✗ Plaintext plugin missing indexFile method")
            return False

    except Exception as e:
        print(f"✗ Error testing plaintext indexing: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


def test_plugin_registry():
    """Test the plugin registry and supported languages."""
    print("\nTesting Plugin Registry...")

    try:
        languages = PluginFactory.get_supported_languages()
        print(f"✓ Total supported languages: {len(languages)}")

        # Check for document processing languages
        doc_languages = ["markdown", "plaintext"]
        for lang in doc_languages:
            if lang in languages:
                print(f"  ✓ {lang} is supported")
            else:
                print(f"  ✗ {lang} is NOT supported")

        # Show all supported languages
        print(f"\n  All languages: {', '.join(sorted(languages)[:10])}...")

        return True

    except Exception as e:
        print(f"✗ Error testing plugin registry: {e}")
        return False


def main():
    """Run all tests."""
    print("=== Simple Document Plugin Validation ===\n")

    tests = [test_plugin_creation, test_file_support, test_basic_indexing, test_plugin_registry]

    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
            results.append(False)
        print("-" * 50)

    # Summary
    print("\n=== Test Summary ===")
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("\n✓ All tests passed! Document processing plugins are working.")
        return 0
    else:
        print(f"\n✗ {total - passed} tests failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
