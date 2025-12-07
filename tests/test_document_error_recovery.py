"""Test cases for document error recovery and graceful degradation."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcp_server.plugins.markdown_plugin.plugin import MarkdownPlugin
from mcp_server.plugins.plaintext_plugin.plugin import PlainTextPlugin
from mcp_server.storage.sqlite_store import SQLiteStore


class TestDocumentErrorRecovery:
    """Test suite for error recovery and graceful degradation in document processing."""

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
        # PlainTextPlugin requires language_config as first parameter
        language_config = {
            "name": "plaintext",
            "code": "plaintext",
            "extensions": [".txt", ".text", ".plain"],
        }
        return PlainTextPlugin(language_config=language_config, sqlite_store=temp_db)

    def test_partial_markdown_recovery(self, markdown_plugin, tmp_path):
        """Test recovery from partially corrupted markdown."""
        content = """# Valid Section 1

This is valid content.

## Valid Subsection

More valid content here.

```python
def valid_function():
    return True
```

# Corrupted Section

```python
def broken_function():
    # Unclosed code block that breaks parsing
    
## This heading is inside the code block!

# But parsing should recover here

This content should still be extracted.

## Final Section

With some concluding text."""

        corrupted_file = tmp_path / "partial_corrupt.md"
        corrupted_file.write_text(content, encoding="utf-8")

        # Read the content first
        file_content = corrupted_file.read_text(encoding="utf-8")
        result = markdown_plugin.indexFile(str(corrupted_file), file_content)

        assert result is not None
        assert "chunks" in result
        assert len(result["chunks"]) > 0

        # Should recover valid sections
        content_text = " ".join(chunk["content"] for chunk in result["chunks"])
        assert "Valid Section 1" in content_text
        assert "Valid Subsection" in content_text
        assert "Final Section" in content_text

        # Should note the recovery
        assert result["metadata"]["had_parse_errors"] is True
        assert result["metadata"]["sections_recovered"] > 0
        assert "recovery_points" in result["metadata"]

    def test_encoding_fallback_chain(self, plaintext_plugin, tmp_path):
        """Test fallback through multiple encodings."""
        # Create a file with mixed encoding that might fail
        mixed_file = tmp_path / "mixed_encoding.txt"

        # Write content that's valid in latin-1 but not utf-8
        with open(mixed_file, "wb") as f:
            f.write(b"Standard ASCII text\n")
            f.write("Special chars: café résumé".encode("latin-1"))
            f.write(b"\nMore ASCII text\n")
            f.write('Windows chars: "quotes"'.encode("windows-1252"))

        # Read content with fallback encoding
        try:
            file_content = mixed_file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            file_content = mixed_file.read_text(encoding="latin-1", errors="replace")
        result = plaintext_plugin.indexFile(str(mixed_file), file_content)

        assert result is not None
        assert "chunks" in result
        assert len(result["chunks"]) > 0

        # Should have tried multiple encodings
        assert result["metadata"]["encoding_attempts"] > 1
        assert result["metadata"]["final_encoding"] in [
            "latin-1",
            "windows-1252",
            "utf-8",
        ]

        # Content should be readable
        content = " ".join(chunk["content"] for chunk in result["chunks"])
        assert "Standard ASCII text" in content
        assert "More ASCII text" in content

    def test_memory_limit_handling(self, plaintext_plugin, tmp_path):
        """Test handling when approaching memory limits."""
        # Create a large file that might cause memory issues
        large_file = tmp_path / "large.txt"

        # Write 50MB of content in chunks
        with open(large_file, "w", encoding="utf-8") as f:
            chunk_text = "This is a test line. " * 100 + "\n"
            for _ in range(50000):  # ~50MB
                f.write(chunk_text)

        # Mock memory check to simulate low memory
        with patch("psutil.virtual_memory") as mock_memory:
            mock_memory.return_value = MagicMock(available=100 * 1024 * 1024)  # 100MB available

            # Read the large file content
            file_content = large_file.read_text(encoding="utf-8")
            result = plaintext_plugin.indexFile(str(large_file), file_content)

        assert result is not None
        assert "chunks" in result

        # Should use streaming/chunked processing
        assert result["metadata"]["processing_mode"] == "memory_constrained"
        assert result["metadata"]["used_streaming"] is True

        # Should complete successfully despite constraints
        assert len(result["chunks"]) > 0
        assert result["metadata"]["completed"] is True

    def test_interrupted_processing_recovery(self, markdown_plugin, tmp_path):
        """Test recovery from interrupted processing."""
        content = """# Document Start

Section 1 content.

## Subsection 1.1

Content here.

# Section 2

Section 2 content.

## Subsection 2.1

More content.

# Section 3

Final section."""

        test_file = tmp_path / "interrupt_test.md"
        test_file.write_text(content, encoding="utf-8")

        # Mock an interruption during processing
        original_method = markdown_plugin._process_section
        call_count = 0

        def interrupted_process(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 3:  # Interrupt on third section
                raise KeyboardInterrupt("Simulated interruption")
            return original_method(*args, **kwargs)

        with patch.object(markdown_plugin, "_process_section", interrupted_process):
            # Read the file content
            file_content = test_file.read_text(encoding="utf-8")
            result = markdown_plugin.indexFile(str(test_file), file_content)

        assert result is not None
        assert "chunks" in result

        # Should have partial results
        assert len(result["chunks"]) > 0
        assert result["metadata"]["processing_interrupted"] is True
        assert result["metadata"]["sections_processed"] == 2
        assert result["metadata"]["partial_results"] is True

    def test_filesystem_error_handling(self, plaintext_plugin, tmp_path):
        """Test handling of filesystem errors during processing."""
        test_file = tmp_path / "fs_error_test.txt"
        test_file.write_text("Initial content for testing.", encoding="utf-8")

        # Mock filesystem errors
        with patch("builtins.open") as mock_open:
            # First call succeeds (for file existence check)
            # Second call fails (simulating disk error during read)
            mock_open.side_effect = [
                open(test_file, "r", encoding="utf-8"),
                IOError("Simulated disk read error"),
            ]

            # Read the file content
            file_content = test_file.read_text(encoding="utf-8")
            result = plaintext_plugin.indexFile(str(test_file), file_content)

        assert result is not None
        assert result.get("error") is not None
        assert "disk read error" in result["error"].lower()
        assert result["metadata"]["error_type"] == "filesystem"
        assert result["metadata"]["recoverable"] is False

    def test_malformed_structure_recovery(self, markdown_plugin, tmp_path):
        """Test recovery from malformed document structure."""
        content = """# Main Title

## Section without closing

### Subsection that's too deep

#### Another level

##### Getting ridiculous

###### Maximum depth

####### This exceeds markdown spec

Regular paragraph here.

### Back to normal depth

## # Malformed heading with extra #

Content continues...

##No space after hashes

### Final valid section"""

        malformed_file = tmp_path / "malformed_structure.md"
        malformed_file.write_text(content, encoding="utf-8")

        # Read the malformed content
        file_content = malformed_file.read_text(encoding="utf-8")
        result = markdown_plugin.indexFile(str(malformed_file), file_content)

        assert result is not None
        assert "chunks" in result
        assert len(result["chunks"]) > 0

        # Should handle structure issues
        assert result["metadata"]["structure_issues"] > 0
        assert result["metadata"]["max_depth_exceeded"] is True
        assert result["metadata"]["malformed_headings_fixed"] > 0

        # Content should still be extracted
        content_text = " ".join(chunk["content"] for chunk in result["chunks"])
        assert "Main Title" in content_text
        assert "Regular paragraph here" in content_text
        assert "Final valid section" in content_text

    def test_plugin_fallback_mechanism(self, tmp_path):
        """Test fallback to generic processing when specific plugin fails."""
        from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher

        # Create a file that might cause plugin issues
        problem_file = tmp_path / "problem.xyz"  # Unknown extension
        problem_file.write_text("Content in unknown format", encoding="utf-8")

        # Create enhanced dispatcher that can use PluginFactory
        dispatcher = EnhancedDispatcher(
            plugins=None, sqlite_store=temp_db, use_plugin_factory=True, lazy_load=False
        )

        # Try to index the file
        result = dispatcher.index_file(str(problem_file))

        assert result is not None
        if "error" not in result:
            # Should fall back to plaintext processing
            assert "chunks" in result
            assert result["metadata"]["plugin_used"] == "plaintext"
            assert result["metadata"]["fallback_reason"] == "unknown_extension"

    def test_error_reporting_detail_levels(self, markdown_plugin, tmp_path):
        """Test different levels of error reporting detail."""
        # Create file with multiple types of errors
        content = """---
invalid yaml: [unclosed bracket
another_error yes
---

# Title

```python
unclosed code block

## Section in code block?

### Deeply nested error

Regular content here.

[Broken link](

![Broken image](

> Unclosed blockquote
that continues..."""

        error_file = tmp_path / "multi_error.md"
        error_file.write_text(content, encoding="utf-8")

        # Test with different error detail levels
        for detail_level in ["minimal", "standard", "verbose"]:
            with patch.object(markdown_plugin, "error_detail_level", detail_level):
                # Read the file content
                file_content = error_file.read_text(encoding="utf-8")
                result = markdown_plugin.indexFile(str(error_file), file_content)

            assert result is not None
            assert "chunks" in result

            errors = result["metadata"]["errors"]

            if detail_level == "minimal":
                assert len(errors) <= 3  # Only major errors
                assert all("line" not in err for err in errors)
            elif detail_level == "standard":
                assert len(errors) > 3  # More errors reported
                assert any("line" in err for err in errors)
            else:  # verbose
                assert len(errors) > 5  # All errors reported
                assert all("line" in err and "context" in err for err in errors)
                assert any("suggestion" in err for err in errors)
