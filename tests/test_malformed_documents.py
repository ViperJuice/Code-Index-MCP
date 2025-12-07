"""Test cases for handling malformed and corrupted documents."""

import tempfile
from pathlib import Path

import pytest

from mcp_server.plugins.markdown_plugin.plugin import MarkdownPlugin
from mcp_server.plugins.plaintext_plugin.plugin import PlaintextPlugin
from mcp_server.storage.sqlite_store import SQLiteStore
from tests.test_utils import create_malformed_content


class TestMalformedDocuments:
    """Test suite for handling various types of malformed documents."""

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

    def test_invalid_yaml_frontmatter(self, markdown_plugin, tmp_path):
        """Test handling of documents with invalid YAML frontmatter."""
        # Create file with malformed YAML
        content = create_malformed_content("invalid_yaml")
        test_file = tmp_path / "invalid_yaml.md"
        test_file.write_text(content, encoding="utf-8")

        # Index the file - should handle gracefully
        result = markdown_plugin.indexFile(str(test_file))

        # Should still extract content despite invalid frontmatter
        assert result is not None
        assert "chunks" in result
        assert len(result["chunks"]) > 0
        assert result["chunks"][0]["content"].strip() == "# Content"

        # Should have error metadata
        assert "metadata" in result
        assert "parse_errors" in result["metadata"]
        assert "invalid_yaml" in str(result["metadata"]["parse_errors"])

    def test_incomplete_code_blocks(self, markdown_plugin, tmp_path):
        """Test handling of documents with unclosed code blocks."""
        content = create_malformed_content("incomplete_code")
        test_file = tmp_path / "incomplete_code.md"
        test_file.write_text(content, encoding="utf-8")

        result = markdown_plugin.indexFile(str(test_file))

        # Should handle incomplete code blocks
        assert result is not None
        assert "chunks" in result
        # Should capture the content up to the incomplete block
        assert any("# Document" in chunk["content"] for chunk in result["chunks"])

        # Should note the parsing issue
        assert "metadata" in result
        assert result["metadata"].get("has_incomplete_blocks", False)

    def test_binary_content_in_text(self, plaintext_plugin, tmp_path):
        """Test handling of files with embedded binary content."""
        content = create_malformed_content("binary_content")
        test_file = tmp_path / "binary_content.txt"
        test_file.write_bytes(content.encode("utf-8", errors="surrogateescape"))

        result = plaintext_plugin.indexFile(str(test_file))

        # Should handle binary content gracefully
        assert result is not None
        assert "chunks" in result
        # Should skip or sanitize binary portions
        text_content = " ".join(chunk["content"] for chunk in result["chunks"])
        assert "Document" in text_content
        assert "\x00" not in text_content  # Binary should be filtered

    def test_corrupted_file_encoding(self, plaintext_plugin, tmp_path):
        """Test handling of files with encoding issues."""
        # Create file with mixed encodings
        test_file = tmp_path / "corrupted_encoding.txt"

        # Write content with different encodings
        with open(test_file, "wb") as f:
            f.write("UTF-8 content: Hello\n".encode("utf-8"))
            f.write("Latin-1 content: café\n".encode("latin-1"))
            f.write("Invalid UTF-8: \xff\xfe\n".encode("latin-1"))

        result = plaintext_plugin.indexFile(str(test_file))

        # Should handle encoding errors
        assert result is not None
        assert "chunks" in result
        assert len(result["chunks"]) > 0

        # Should have encoding error metadata
        assert "metadata" in result
        assert result["metadata"].get("encoding_errors", 0) > 0

    def test_excessively_nested_structure(self, markdown_plugin, tmp_path):
        """Test handling of documents with excessive nesting."""
        # Create deeply nested markdown
        content = "# Level 1\n"
        for i in range(2, 20):  # Create 19 levels of nesting
            content += f"{'#' * i} Level {i}\n"
            content += f"Content at level {i}\n\n"

        test_file = tmp_path / "deeply_nested.md"
        test_file.write_text(content, encoding="utf-8")

        result = markdown_plugin.indexFile(str(test_file))

        # Should handle deep nesting without crashing
        assert result is not None
        assert "chunks" in result
        assert len(result["chunks"]) > 0

        # Should cap nesting at reasonable level
        assert "metadata" in result
        max_depth = result["metadata"].get("max_heading_depth", 0)
        assert max_depth <= 10  # Should cap at reasonable depth

    def test_invalid_file_permissions(self, plaintext_plugin, tmp_path):
        """Test handling of files with permission issues."""
        test_file = tmp_path / "no_read_permission.txt"
        test_file.write_text("Content that can't be read", encoding="utf-8")

        # Change permissions to write-only
        test_file.chmod(0o200)

        try:
            result = plaintext_plugin.indexFile(str(test_file))

            # Should handle permission errors gracefully
            assert result is not None
            assert result.get("error") is not None
            assert "permission" in result["error"].lower()
        finally:
            # Restore permissions for cleanup
            test_file.chmod(0o644)

    def test_circular_references(self, markdown_plugin, tmp_path):
        """Test handling of documents with circular references."""
        content = create_malformed_content("circular_reference")
        test_file = tmp_path / "circular_refs.md"
        test_file.write_text(content, encoding="utf-8")

        result = markdown_plugin.indexFile(str(test_file))

        # Should handle circular references without infinite loops
        assert result is not None
        assert "chunks" in result

        # Should detect and note circular references
        assert "metadata" in result
        assert result["metadata"].get("has_circular_refs", False)

    def test_truncated_file(self, markdown_plugin, tmp_path):
        """Test handling of truncated/incomplete files."""
        # Create a file that appears truncated
        content = """# Document Title

This is the beginning of a document that gets cut off...

## Section 1

Some content here

## Section 2

This section is incomple"""  # Truncated mid-word

        test_file = tmp_path / "truncated.md"
        test_file.write_text(content, encoding="utf-8")

        result = markdown_plugin.indexFile(str(test_file))

        # Should handle truncated files
        assert result is not None
        assert "chunks" in result
        assert len(result["chunks"]) > 0

        # Should process what's available
        content_joined = " ".join(chunk["content"] for chunk in result["chunks"])
        assert "Document Title" in content_joined
        assert "Section 1" in content_joined
