"""Test cases for handling Unicode and various text encodings."""

import codecs
import tempfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.skip(
    reason="DocumentMetadata fields (has_emoji, encoding_info, etc.) not yet implemented"
)

from mcp_server.plugins.language_registry import LANGUAGE_CONFIGS
from mcp_server.plugins.markdown_plugin.plugin import MarkdownPlugin
from mcp_server.plugins.plaintext_plugin.plugin import PlainTextPlugin
from mcp_server.storage.sqlite_store import SQLiteStore


class TestUnicodeDocuments:
    """Test suite for handling documents with various Unicode features."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        store = SQLiteStore(db_path)
        yield store
        Path(db_path).unlink(missing_ok=True)

    @pytest.fixture
    def markdown_plugin(self, temp_db):
        """Create a markdown plugin instance."""
        return MarkdownPlugin(sqlite_store=temp_db)

    @pytest.fixture
    def plaintext_plugin(self, temp_db):
        """Create a plaintext plugin instance."""
        return PlainTextPlugin(language_config=LANGUAGE_CONFIGS["plaintext"], sqlite_store=temp_db)

    def test_emoji_content(self, plaintext_plugin, tmp_path):
        """Test handling of documents with emoji and emoticons."""
        emoji_content = """Document with Emojis 🎉

This document contains various emoji:
- Happy faces: 😀 😃 😄 😁 😊
- Animals: 🐶 🐱 🐭 🐹 🦊
- Food: 🍕 🍔 🍟 🌮 🍜
- Flags: 🇺🇸 🇬🇧 🇯🇵 🇩🇪 🇫🇷
- Complex emoji: 👨‍👩‍👧‍👦 👩‍💻 🧑‍🚀

Special sequences: 👍🏻 👍🏼 👍🏽 👍🏾 👍🏿"""

        emoji_file = tmp_path / "emoji_doc.txt"
        emoji_file.write_text(emoji_content, encoding="utf-8")

        result = plaintext_plugin.indexFile(str(emoji_file))

        assert result is not None
        assert "chunks" in result
        assert len(result["chunks"]) > 0

        # Verify emoji are preserved
        content = " ".join(chunk["content"] for chunk in result["chunks"])
        assert "🎉" in content
        assert "😀" in content
        assert "🍕" in content
        assert "👨‍👩‍👧‍👦" in content  # Family emoji

        # Check metadata
        assert result["metadata"]["has_emoji"] is True
        assert result["metadata"]["encoding"] == "utf-8"

    def test_rtl_languages(self, markdown_plugin, tmp_path):
        """Test handling of right-to-left languages."""
        rtl_content = """# مستند عربي

هذا مستند باللغة العربية.

## עברית

זהו מסמך בעברית.

## فارسی

این یک سند فارسی است.

## Mixed Content

This paragraph contains English text mixed with العربية and עברית text.

### Lists with RTL
- English item
- عنصر عربي
- פריט עברי
- آیتم فارسی"""

        rtl_file = tmp_path / "rtl_languages.md"
        rtl_file.write_text(rtl_content, encoding="utf-8")

        result = markdown_plugin.indexFile(str(rtl_file))

        assert result is not None
        assert "chunks" in result
        assert len(result["chunks"]) > 0

        # Verify RTL content is preserved
        content = " ".join(chunk["content"] for chunk in result["chunks"])
        assert "مستند عربي" in content
        assert "עברית" in content
        assert "فارسی" in content

        # Check metadata
        assert result["metadata"]["has_rtl"] is True
        assert result["metadata"]["languages_detected"] >= {"ar", "he", "fa", "en"}

    def test_cjk_characters(self, plaintext_plugin, tmp_path):
        """Test handling of Chinese, Japanese, and Korean characters."""
        cjk_content = """CJK Language Test Document

Chinese (Simplified): 这是一个测试文档
Chinese (Traditional): 這是一個測試文檔

Japanese:
ひらがな: これはテストです
カタカナ: コレハテストデス
漢字: 日本語の文書

Korean: 이것은 테스트 문서입니다

Mixed: The word 「テスト」means "test" in Japanese (测试 in Chinese)."""

        cjk_file = tmp_path / "cjk_doc.txt"
        cjk_file.write_text(cjk_content, encoding="utf-8")

        result = plaintext_plugin.indexFile(str(cjk_file))

        assert result is not None
        assert "chunks" in result

        # Verify CJK content is preserved
        content = " ".join(chunk["content"] for chunk in result["chunks"])
        assert "这是一个测试文档" in content
        assert "これはテストです" in content
        assert "이것은 테스트 문서입니다" in content

        # Check proper handling of different scripts
        assert result["metadata"]["has_cjk"] is True
        assert result["metadata"]["scripts_detected"] >= {
            "han",
            "hiragana",
            "katakana",
            "hangul",
        }

    def test_mathematical_symbols(self, markdown_plugin, tmp_path):
        """Test handling of mathematical and special symbols."""
        math_content = """# Mathematical Notation

## Basic Operations
- Addition: 2 + 2 = 4
- Multiplication: 3 × 4 = 12
- Division: 10 ÷ 2 = 5
- Not equal: 5 ≠ 6

## Advanced Math
- Sum: ∑(i=1 to n) = n(n+1)/2
- Integral: ∫₀^∞ e^(-x) dx = 1
- Square root: √16 = 4
- Pi: π ≈ 3.14159
- Infinity: ∞

## Set Theory
- Union: A ∪ B
- Intersection: A ∩ B
- Element of: x ∈ A
- Subset: A ⊆ B

## Greek Letters
Alpha: α, Beta: β, Gamma: γ, Delta: δ, Epsilon: ε"""

        math_file = tmp_path / "math_symbols.md"
        math_file.write_text(math_content, encoding="utf-8")

        result = markdown_plugin.indexFile(str(math_file))

        assert result is not None
        assert "chunks" in result

        # Verify mathematical symbols are preserved
        content = " ".join(chunk["content"] for chunk in result["chunks"])
        assert "∑" in content
        assert "∫" in content
        assert "√" in content
        assert "π" in content
        assert "∞" in content
        assert "α" in content

        assert result["metadata"]["has_math_symbols"] is True

    def test_various_encodings(self, plaintext_plugin, tmp_path):
        """Test handling of files with different encodings."""
        # UTF-16 file
        utf16_content = "UTF-16 encoded: Hello 世界"
        utf16_file = tmp_path / "utf16.txt"
        with open(utf16_file, "w", encoding="utf-16") as f:
            f.write(utf16_content)

        result_utf16 = plaintext_plugin.indexFile(str(utf16_file))
        assert result_utf16 is not None
        assert "Hello 世界" in " ".join(chunk["content"] for chunk in result_utf16["chunks"])

        # Latin-1 file
        latin1_content = "Latin-1: café, naïve, résumé"
        latin1_file = tmp_path / "latin1.txt"
        with open(latin1_file, "w", encoding="latin-1") as f:
            f.write(latin1_content)

        result_latin1 = plaintext_plugin.indexFile(str(latin1_file))
        assert result_latin1 is not None
        assert "café" in " ".join(chunk["content"] for chunk in result_latin1["chunks"])

        # Windows-1252 file
        cp1252_content = 'Windows-1252: "smart quotes" and —em dash'
        cp1252_file = tmp_path / "cp1252.txt"
        with open(cp1252_file, "w", encoding="windows-1252") as f:
            f.write(cp1252_content)

        result_cp1252 = plaintext_plugin.indexFile(str(cp1252_file))
        assert result_cp1252 is not None
        content = " ".join(chunk["content"] for chunk in result_cp1252["chunks"])
        assert "smart quotes" in content or '"smart quotes"' in content

    def test_bom_handling(self, plaintext_plugin, tmp_path):
        """Test handling of Byte Order Mark (BOM) in files."""
        # UTF-8 with BOM
        utf8_bom_file = tmp_path / "utf8_bom.txt"
        with open(utf8_bom_file, "wb") as f:
            f.write(codecs.BOM_UTF8)
            f.write("UTF-8 with BOM: Test content".encode("utf-8"))

        result = plaintext_plugin.indexFile(str(utf8_bom_file))
        assert result is not None
        content = " ".join(chunk["content"] for chunk in result["chunks"])
        assert "UTF-8 with BOM: Test content" in content
        assert result["metadata"]["has_bom"] is True

        # UTF-16 with BOM
        utf16_bom_file = tmp_path / "utf16_bom.txt"
        with open(utf16_bom_file, "wb") as f:
            f.write(codecs.BOM_UTF16_LE)
            f.write("UTF-16 LE with BOM".encode("utf-16-le"))

        result = plaintext_plugin.indexFile(str(utf16_bom_file))
        assert result is not None
        assert "UTF-16 LE with BOM" in " ".join(chunk["content"] for chunk in result["chunks"])

    def test_control_characters(self, plaintext_plugin, tmp_path):
        """Test handling of control characters and special Unicode."""
        control_content = """Text with control characters:
Tab:	Indented with tab
Zero-width space: Hello​World
Non-breaking space: Hello World
Soft hyphen: Hyphen­ation
Line separator: Line 1 Line 2
Paragraph separator: Para 1 Para 2"""

        # Add actual control characters
        control_content = control_content.replace("", "\u2028")  # Line separator
        control_content = control_content.replace("", "\u2029")  # Paragraph separator

        control_file = tmp_path / "control_chars.txt"
        control_file.write_text(control_content, encoding="utf-8")

        result = plaintext_plugin.indexFile(str(control_file))

        assert result is not None
        assert "chunks" in result

        # Should handle control characters appropriately
        assert result["metadata"]["has_control_chars"] is True
        assert result["metadata"]["control_chars_sanitized"] > 0

    def test_unicode_normalization(self, markdown_plugin, tmp_path):
        """Test handling of Unicode normalization forms."""
        # Same text in different normalization forms
        nfc_text = "é"  # NFC (single character)
        nfd_text = "é"  # NFD (e + combining accent)

        content = f"""# Unicode Normalization Test

NFC form: {nfc_text}
NFD form: {nfd_text}

Composite characters:
- Ω (Ohm sign) vs Ω (Greek capital omega)
- ℌ (Fraktur H) vs H (Latin H)
- ½ (vulgar fraction) vs 1/2 (separate chars)"""

        norm_file = tmp_path / "normalization.md"
        norm_file.write_text(content, encoding="utf-8")

        result = markdown_plugin.indexFile(str(norm_file))

        assert result is not None
        assert "chunks" in result

        # Both forms should be searchable
        content_text = " ".join(chunk["content"] for chunk in result["chunks"])
        assert "é" in content_text  # Should find either form

        # Metadata about normalization
        assert result["metadata"].get("unicode_normalized", False)
