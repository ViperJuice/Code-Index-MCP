"""Test cases for document processing edge cases."""

import tempfile
from pathlib import Path

import pytest

from mcp_server.plugins.markdown_plugin.plugin import MarkdownPlugin
from mcp_server.plugins.plaintext_plugin.plugin import PlaintextPlugin
from mcp_server.storage.sqlite_store import SQLiteStore
from tests.test_utils import generate_large_content, timer


class TestDocumentEdgeCases:
    """Test suite for various document processing edge cases."""

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
        return PlaintextPlugin(sqlite_store=temp_db)

    def test_empty_document(self, markdown_plugin, plaintext_plugin, tmp_path):
        """Test handling of completely empty documents."""
        # Test empty markdown
        empty_md = tmp_path / "empty.md"
        empty_md.write_text("", encoding="utf-8")

        md_result = markdown_plugin.indexFile(str(empty_md))
        assert md_result is not None
        assert "chunks" in md_result
        assert len(md_result["chunks"]) == 0
        assert md_result["metadata"]["is_empty"] is True

        # Test empty plaintext
        empty_txt = tmp_path / "empty.txt"
        empty_txt.write_text("", encoding="utf-8")

        txt_result = plaintext_plugin.indexFile(str(empty_txt))
        assert txt_result is not None
        assert "chunks" in txt_result
        assert len(txt_result["chunks"]) == 0
        assert txt_result["metadata"]["is_empty"] is True

    def test_whitespace_only_document(self, plaintext_plugin, tmp_path):
        """Test handling of documents containing only whitespace."""
        whitespace_file = tmp_path / "whitespace.txt"
        whitespace_file.write_text("   \n\t\n   \r\n  ", encoding="utf-8")

        result = plaintext_plugin.indexFile(str(whitespace_file))

        assert result is not None
        assert "chunks" in result
        assert len(result["chunks"]) == 0
        assert result["metadata"]["is_empty"] is True

    def test_huge_file_processing(self, plaintext_plugin, tmp_path):
        """Test handling of very large files."""
        # Generate a 10MB file
        large_content = generate_large_content(10)
        large_file = tmp_path / "huge.txt"
        large_file.write_text(large_content, encoding="utf-8")

        with timer("Large file processing"):
            result = plaintext_plugin.indexFile(str(large_file))

        assert result is not None
        assert "chunks" in result
        assert len(result["chunks"]) > 0

        # Check chunking worked properly
        assert result["metadata"]["file_size_mb"] >= 10
        assert result["metadata"]["chunk_count"] > 1

        # Verify memory efficiency
        assert result["metadata"].get("processing_strategy") == "streaming"

    def test_single_line_extreme_length(self, plaintext_plugin, tmp_path):
        """Test handling of files with extremely long single lines."""
        # Create a file with a single 1MB line
        long_line = "a" * (1024 * 1024)
        long_file = tmp_path / "long_line.txt"
        long_file.write_text(long_line, encoding="utf-8")

        result = plaintext_plugin.indexFile(str(long_file))

        assert result is not None
        assert "chunks" in result
        # Should split the long line into multiple chunks
        assert len(result["chunks"]) > 1

        # Each chunk should be reasonable size
        for chunk in result["chunks"]:
            assert len(chunk["content"]) <= 10000  # Max 10KB per chunk

    def test_deeply_nested_sections(self, markdown_plugin, tmp_path):
        """Test handling of documents with deep section nesting."""
        # Create markdown with nested sections
        content = "# Root\n\n"

        # Create a tree structure 10 levels deep
        for i in range(10):
            indent = "  " * i
            content += f"{'#' * (i + 1)} Section Level {i + 1}\n\n"
            content += f"{indent}Content at level {i + 1}\n\n"

            # Add subsections at each level
            for j in range(3):
                content += f"{'#' * (i + 2)} Subsection {i + 1}.{j + 1}\n\n"
                content += f"{indent}  Subsection content\n\n"

        nested_file = tmp_path / "deeply_nested.md"
        nested_file.write_text(content, encoding="utf-8")

        result = markdown_plugin.indexFile(str(nested_file))

        assert result is not None
        assert "chunks" in result
        assert len(result["chunks"]) > 0

        # Should handle nesting appropriately
        assert result["metadata"]["max_heading_depth"] >= 6
        assert result["metadata"]["total_sections"] > 20

    def test_circular_include_references(self, markdown_plugin, tmp_path):
        """Test handling of documents with circular include references."""
        # Create files that reference each other
        file_a = tmp_path / "doc_a.md"
        file_b = tmp_path / "doc_b.md"

        file_a.write_text(
            """# Document A

See [Document B](doc_b.md)

<!-- include: doc_b.md -->

End of Document A""",
            encoding="utf-8",
        )

        file_b.write_text(
            """# Document B

See [Document A](doc_a.md)

<!-- include: doc_a.md -->

End of Document B""",
            encoding="utf-8",
        )

        # Process file A
        result = markdown_plugin.indexFile(str(file_a))

        assert result is not None
        assert "chunks" in result

        # Should detect circular reference
        assert result["metadata"].get("has_circular_includes", False)
        assert "circular_reference_detected" in result["metadata"]

    def test_mixed_line_endings(self, plaintext_plugin, tmp_path):
        """Test handling of files with mixed line endings."""
        # Create content with different line endings
        mixed_content = "Line 1\r\nLine 2\nLine 3\rLine 4\r\nLine 5"
        mixed_file = tmp_path / "mixed_endings.txt"

        with open(mixed_file, "wb") as f:
            f.write(mixed_content.encode("utf-8"))

        result = plaintext_plugin.indexFile(str(mixed_file))

        assert result is not None
        assert "chunks" in result

        # Should normalize line endings
        content = " ".join(chunk["content"] for chunk in result["chunks"])
        assert "Line 1" in content
        assert "Line 2" in content
        assert "Line 3" in content
        assert "Line 4" in content
        assert "Line 5" in content

        # Metadata should note mixed endings
        assert result["metadata"].get("mixed_line_endings", False)

    def test_file_with_no_extension(self, plaintext_plugin, tmp_path):
        """Test handling of files without extensions."""
        no_ext_file = tmp_path / "README"  # No extension
        no_ext_file.write_text(
            """This is a README file without extension.

It contains important information.

## Installation

Follow these steps...""",
            encoding="utf-8",
        )

        result = plaintext_plugin.indexFile(str(no_ext_file))

        assert result is not None
        assert "chunks" in result
        assert len(result["chunks"]) > 0

        # Should process as plaintext by default
        assert result["metadata"]["assumed_type"] == "plaintext"
        assert "README" in result["metadata"]["filename"]
