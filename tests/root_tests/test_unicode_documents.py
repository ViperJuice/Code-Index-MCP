#!/usr/bin/env python3
"""Test Unicode handling in document processing."""

import tempfile
from pathlib import Path

import pytest

from mcp_server.plugins.js_plugin.plugin import Plugin as JsPlugin
from mcp_server.plugins.markdown_plugin import MarkdownPlugin
from mcp_server.plugins.plaintext_plugin import PlainTextPlugin
from mcp_server.plugins.python_plugin.plugin import Plugin as PythonPlugin
from mcp_server.storage.sqlite_store import SQLiteStore


class TestUnicodeDocuments:
    """Test Unicode handling across different document types."""

    @pytest.fixture
    def setup_plugins(self):
        """Setup plugins for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SQLiteStore(str(Path(tmpdir) / "test.db"))

            markdown_plugin = MarkdownPlugin(enable_semantic=False)
            plaintext_config = {
                "name": "plaintext",
                "code": "plaintext",
                "extensions": [".txt", ".text"],
                "file_pattern": r".*\.(txt|text)$",
            }
            plaintext_plugin = PlainTextPlugin(plaintext_config, enable_semantic=False)
            python_plugin = PythonPlugin()
            js_plugin = JsPlugin()

            yield {
                "markdown": markdown_plugin,
                "plaintext": plaintext_plugin,
                "python": python_plugin,
                "javascript": js_plugin,
                "store": store,
            }

    def test_basic_unicode_characters(self, setup_plugins):
        """Test handling of common Unicode characters."""
        plugins = setup_plugins

        # Common Unicode content
        content = """# Unicode Test 🚀

## Mathematics: ∑ ∏ ∫ ∂ ∇ ∆ ∞

### Greek Letters: α β γ δ ε ζ η θ

Content with emojis: 😀 😎 🎉 🔥 💯

Accented characters: café, naïve, résumé, piñata

Asian characters:
- Japanese: こんにちは (Hello)
- Chinese: 你好 (Hello)
- Korean: 안녕하세요 (Hello)

Symbols: ™ © ® € £ ¥ ¢"""

        # Test with each plugin
        result1 = plugins["markdown"].indexFile("unicode.md", content)
        assert result1 is not None
        assert len(result1.symbols) > 0

        result2 = plugins["plaintext"].indexFile("unicode.txt", content)
        assert result2 is not None

        # Verify chunks preserve Unicode
        chunks = plugins["markdown"].chunk_document(content, Path("unicode.md"))
        assert any("🚀" in chunk.content for chunk in chunks)
        assert any("∑" in chunk.content for chunk in chunks)

    def test_unicode_in_code(self, setup_plugins):
        """Test Unicode in code files."""
        plugins = setup_plugins

        # Python with Unicode
        python_content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unicode test module."""

def hello_world():
    """Print hello in multiple languages."""
    print("Hello! 👋")
    print("你好!")  # Chinese
    print("こんにちは!")  # Japanese
    print("안녕하세요!")  # Korean
    print("Привет!")  # Russian
    print("مرحبا!")  # Arabic

class UnicodeTest:
    """Test class with Unicode."""
    
    def __init__(self):
        self.π = 3.14159
        self.café = "coffee"
        
    def calculate_∑(self, values):
        """Calculate sum (∑) of values."""
        return sum(values)
'''

        result = plugins["python"].indexFile("unicode_test.py", python_content)
        assert result is not None
        assert any("hello_world" in sym.name for sym in result.symbols)
        assert any("UnicodeTest" in sym.name for sym in result.symbols)

        # JavaScript with Unicode
        js_content = """// Unicode test 🎯

const greetings = {
    english: "Hello",
    spanish: "¡Hola!",
    french: "Bonjour",
    german: "Guten Tag",
    japanese: "こんにちは",
    emoji: "👋"
};

function calculate∑(numbers) {
    return numbers.reduce((a, b) => a + b, 0);
}

const café = {
    name: "Café René",
    menu: ["Espresso ☕", "Latte 🥛", "Cappuccino ☕"]
};

// Math symbols
const π = Math.PI;
const ∞ = Infinity;
"""

        result2 = plugins["javascript"].indexFile("unicode.js", js_content)
        assert result2 is not None

    def test_unicode_normalization(self, setup_plugins):
        """Test Unicode normalization forms."""
        plugins = setup_plugins

        # Different normalization forms of café
        # NFC (composed): café
        # NFD (decomposed): café (e + combining acute)

        content_nfc = "# Café Test\n\nThis is a café."
        content_nfd = "# Café Test\n\nThis is a café."

        result1 = plugins["markdown"].indexFile("nfc.md", content_nfc)
        result2 = plugins["markdown"].indexFile("nfd.md", content_nfd)

        assert result1 is not None
        assert result2 is not None

        # Search should find both
        results = plugins["store"].search_symbols_fts("café")
        # Note: Search behavior may vary based on normalization

    def test_unicode_in_identifiers(self, setup_plugins):
        """Test Unicode in identifiers (where supported)."""
        plugin = setup_plugins["python"]

        # Python 3 supports Unicode identifiers
        content = '''# Unicode identifiers

def 计算总和(数字列表):
    """Calculate sum in Chinese."""
    return sum(数字列表)

class ΜαθηματικέςΣυναρτήσεις:
    """Mathematical functions in Greek."""
    
    @staticmethod
    def υπολογισμός_π():
        return 3.14159

# Variables with Unicode
π = 3.14159
е = 2.71828  # Euler's number
φ = 1.618   # Golden ratio
'''

        result = plugin.indexFile("unicode_ids.py", content)
        assert result is not None
        # Should handle Unicode identifiers
        assert len(result.symbols) > 0

    def test_rtl_text(self, setup_plugins):
        """Test right-to-left text handling."""
        plugins = setup_plugins

        # Mixed LTR and RTL text
        content = """# مقدمة (Introduction)

This document contains both English and Arabic text.

## العنوان الأول (First Heading)

مرحبا بكم في هذا المستند. هذا نص عربي.

Hello and welcome. This is English text.

### خليط من اللغات (Mix of Languages)

Sometimes we have mixed text: Welcome مرحبا to our تطبيق application.

Hebrew example: שלום עולם (Hello World)"""

        result = plugins["markdown"].indexFile("rtl.md", content)
        assert result is not None

        chunks = plugins["markdown"].chunk_document(content, Path("rtl.md"))
        assert len(chunks) > 0
        # Verify RTL text is preserved
        assert any("مرحبا" in chunk.content for chunk in chunks)

    def test_unicode_edge_cases(self, setup_plugins):
        """Test edge cases with Unicode."""
        plugins = setup_plugins

        # Zero-width characters
        content1 = "Hello\u200bWor\u200cld\u200d!"  # Zero-width space, non-joiner, joiner
        result1 = plugins["plaintext"].indexFile("zwj.txt", content1)
        assert result1 is not None

        # Combining characters
        content2 = "e\u0301"  # e + combining acute accent
        result2 = plugins["plaintext"].indexFile("combining.txt", content2)
        assert result2 is not None

        # Surrogate pairs (emoji requiring 2 UTF-16 code units)
        content3 = "Test 🏴󠁧󠁢󠁳󠁣󠁴󠁿 🏴󠁧󠁢󠁷󠁬󠁳󠁿"  # Scottish and Welsh flags
        result3 = plugins["plaintext"].indexFile("surrogate.txt", content3)
        assert result3 is not None

        # Variation selectors
        content4 = "Text ✉︎ vs Emoji ✉️"  # Text vs emoji presentation
        result4 = plugins["plaintext"].indexFile("variation.txt", content4)
        assert result4 is not None

    def test_unicode_in_urls_and_paths(self, setup_plugins):
        """Test Unicode in URLs and file paths."""
        plugin = setup_plugins["markdown"]

        content = """# Unicode URLs and Paths

## Links with Unicode

- [Café](https://example.com/café)
- [日本語](https://example.jp/日本語/ページ)
- [Encoded](https://example.com/caf%C3%A9)

## File paths

- `/home/user/文档/file.txt`
- `C:\\用户\\documents\\файл.doc`
- `./café/menü.md`

## Images

![画像](./images/写真.png)
![Photo](./café/фото.jpg)"""

        result = plugin.indexFile("unicode_urls.md", content)
        assert result is not None

        # Check that links are preserved
        chunks = plugin.chunk_document(content, Path("unicode_urls.md"))
        assert any("café" in chunk.content.lower() for chunk in chunks)

    def test_unicode_search(self, setup_plugins):
        """Test searching for Unicode content."""
        plugins = setup_plugins
        store = plugins["store"]

        # Index documents with various Unicode content
        plugins["markdown"].indexFile("emoji.md", "# Emoji Test 🚀\n\nRocket launch! 🚀🎉")
        plugins["markdown"].indexFile("math.md", "# Math ∑∏∫\n\nSum: ∑, Product: ∏")
        plugins["markdown"].indexFile("langs.md", "# Languages\n\n你好, こんにちは, 안녕하세요")

        # Search for Unicode content
        unicode_queries = [
            "🚀",
            "∑",
            "你好",
            "こんにちは",
            "café",  # Even if not in content, shouldn't crash
        ]

        for query in unicode_queries:
            try:
                results = store.search_symbols_fts(query)
                # Should not raise exceptions
            except Exception as e:
                pytest.fail(f"Unicode search failed for '{query}': {e}")

    def test_unicode_file_names(self, setup_plugins):
        """Test handling of Unicode in file names."""
        plugins = setup_plugins

        # Unicode file names
        unicode_names = ["café.md", "文档.md", "файл.txt", "🚀rocket.md", "naïve.py"]

        content = "# Test\n\nContent"

        for name in unicode_names:
            # Should handle Unicode file names
            result = plugins["markdown"].indexFile(name, content)
            assert result is not None

    def test_bom_handling(self, setup_plugins):
        """Test handling of Byte Order Mark (BOM)."""
        plugins = setup_plugins

        # UTF-8 BOM
        content_with_bom = "\ufeff# Title\n\nContent with BOM"
        result1 = plugins["markdown"].indexFile("bom.md", content_with_bom)
        assert result1 is not None

        # Should strip BOM when processing
        chunks = plugins["markdown"].chunk_document(content_with_bom, Path("bom.md"))
        assert not any(chunk.content.startswith("\ufeff") for chunk in chunks)

        # UTF-16 BOM markers (as they might appear if decoded incorrectly)
        content_utf16_le = "\ufffe# Title"
        result2 = plugins["plaintext"].indexFile("utf16.txt", content_utf16_le)
        assert result2 is not None

    def test_control_characters(self, setup_plugins):
        """Test handling of Unicode control characters."""
        plugins = setup_plugins

        # Various control characters
        content = "Title\u0000with\u0001null\u0002chars\n\nContent\u0008backspace\u007fdelete"

        # Should handle without crashing
        result = plugins["plaintext"].indexFile("control.txt", content)
        assert result is not None

        # Control characters should be handled gracefully
        chunks = plugins["plaintext"].chunk_document(content, Path("control.txt"))
        assert len(chunks) > 0

    def test_unicode_categories(self, setup_plugins):
        """Test various Unicode categories."""
        plugin = setup_plugins["markdown"]

        content = """# Unicode Categories

## Currency Symbols
Dollar: $ Euro: € Pound: £ Yen: ¥ Bitcoin: ₿

## Mathematical Operators
Plus-minus: ± Infinity: ∞ Approximately: ≈ Not equal: ≠

## Arrows
Right: → Left: ← Up: ↑ Down: ↓ Bidirectional: ↔

## Box Drawing
┌─────────┐
│ Box     │
├─────────┤
│ Content │
└─────────┘

## Musical Symbols
♩ ♪ ♫ ♬ ♭ ♮ ♯

## Miscellaneous Symbols
☆ ★ ☀ ☁ ☂ ☃ ☄ ☎ ☏ ☐ ☑ ☒"""

        result = plugin.indexFile("unicode_cats.md", content)
        assert result is not None

        chunks = plugin.chunk_document(content, Path("unicode_cats.md"))
        assert len(chunks) > 0

        # Verify various symbols are preserved
        all_content = " ".join(chunk.content for chunk in chunks)
        assert "€" in all_content
        assert "∞" in all_content
        assert "→" in all_content
        assert "♪" in all_content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
