#!/usr/bin/env python3
"""Tests for the contextual embeddings service (mock version without anthropic dependency)."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

# Mock the anthropic module before importing our code
sys.modules["anthropic"] = MagicMock()

from mcp_server.document_processing import (
    ChunkMetadata,
    ChunkType,
    ContextCache,
    ContextualEmbeddingService,
    DocumentCategory,
    DocumentChunk,
    PromptTemplateRegistry,
)


class TestDocumentCategoryDetection:
    """Test document category detection."""

    def test_detect_code_by_extension(self):
        """Test detection of code files by extension."""
        service = ContextualEmbeddingService(api_key="test")

        chunk = DocumentChunk(
            id="test",
            content="test content",
            type=ChunkType.PARAGRAPH,
            metadata=ChunkMetadata(
                document_path="/src/main.py",
                section_hierarchy=[],
                chunk_index=0,
                total_chunks=1,
                has_code=True,
            ),
        )

        category = service.detect_document_category(chunk, chunk.metadata.document_path)
        assert category == DocumentCategory.CODE

    def test_detect_documentation_by_extension(self):
        """Test detection of documentation files."""
        service = ContextualEmbeddingService(api_key="test")

        chunk = DocumentChunk(
            id="test",
            content="# Documentation",
            type=ChunkType.HEADING,
            metadata=ChunkMetadata(
                document_path="/docs/guide.md",
                section_hierarchy=[],
                chunk_index=0,
                total_chunks=1,
                has_code=False,
            ),
        )

        category = service.detect_document_category(chunk, chunk.metadata.document_path)
        assert category == DocumentCategory.DOCUMENTATION

    def test_detect_tutorial_by_name(self):
        """Test detection of tutorial files."""
        service = ContextualEmbeddingService(api_key="test")

        chunk = DocumentChunk(
            id="test",
            content="Getting started guide",
            type=ChunkType.PARAGRAPH,
            metadata=ChunkMetadata(
                document_path="/docs/tutorial.md",
                section_hierarchy=[],
                chunk_index=0,
                total_chunks=1,
                has_code=False,
            ),
        )

        category = service.detect_document_category(chunk, chunk.metadata.document_path)
        assert category == DocumentCategory.TUTORIAL

    def test_detect_configuration(self):
        """Test detection of configuration files."""
        service = ContextualEmbeddingService(api_key="test")

        chunk = DocumentChunk(
            id="test",
            content="key: value",
            type=ChunkType.CODE_BLOCK,
            metadata=ChunkMetadata(
                document_path="/config/settings.yaml",
                section_hierarchy=[],
                chunk_index=0,
                total_chunks=1,
                has_code=False,
            ),
        )

        category = service.detect_document_category(chunk, chunk.metadata.document_path)
        assert category == DocumentCategory.CONFIGURATION

    def test_detect_by_content(self):
        """Test detection by content patterns."""
        service = ContextualEmbeddingService(api_key="test")

        # Code block should be detected as code
        chunk = DocumentChunk(
            id="test",
            content="function test() { return true; }",
            type=ChunkType.CODE_BLOCK,
            metadata=ChunkMetadata(
                document_path="/unknown.txt",
                section_hierarchy=[],
                chunk_index=0,
                total_chunks=1,
                has_code=True,
            ),
        )

        category = service.detect_document_category(chunk, chunk.metadata.document_path)
        assert category == DocumentCategory.CODE

        # Tutorial content
        chunk2 = DocumentChunk(
            id="test2",
            content="To install the package, follow these steps",
            type=ChunkType.PARAGRAPH,
            metadata=ChunkMetadata(
                document_path="/unknown.txt",
                section_hierarchy=[],
                chunk_index=0,
                total_chunks=1,
                has_code=False,
            ),
        )

        category2 = service.detect_document_category(chunk2, chunk2.metadata.document_path)
        assert category2 == DocumentCategory.TUTORIAL


class TestContextCache:
    """Test context caching functionality."""

    def test_cache_key_generation(self, tmp_path):
        """Test cache key generation is consistent."""
        cache = ContextCache(cache_dir=tmp_path)

        chunk = DocumentChunk(
            id="test",
            content="test content",
            type=ChunkType.PARAGRAPH,
            metadata=ChunkMetadata(
                document_path="/test.md",
                section_hierarchy=[],
                chunk_index=0,
                total_chunks=1,
                has_code=False,
            ),
        )

        key1 = cache._get_cache_key(chunk, DocumentCategory.GENERAL)
        key2 = cache._get_cache_key(chunk, DocumentCategory.GENERAL)

        assert key1 == key2
        assert len(key1) == 16

    def test_cache_set_and_get(self, tmp_path):
        """Test setting and getting from cache."""
        cache = ContextCache(cache_dir=tmp_path)

        chunk = DocumentChunk(
            id="test",
            content="test content",
            type=ChunkType.PARAGRAPH,
            metadata=ChunkMetadata(
                document_path="/test.md",
                section_hierarchy=[],
                chunk_index=0,
                total_chunks=1,
                has_code=False,
            ),
        )

        # Set context
        context = "This is a test context"
        cache.set(chunk, DocumentCategory.GENERAL, context)

        # Get context
        retrieved = cache.get(chunk, DocumentCategory.GENERAL)
        assert retrieved == context

        # Verify it's in memory cache
        assert len(cache.memory_cache) == 1

        # Verify disk cache
        cache_files = list(tmp_path.glob("*.json"))
        assert len(cache_files) == 1

    def test_cache_different_categories(self, tmp_path):
        """Test that different categories produce different cache keys."""
        cache = ContextCache(cache_dir=tmp_path)

        chunk = DocumentChunk(
            id="test",
            content="test content",
            type=ChunkType.PARAGRAPH,
            metadata=ChunkMetadata(
                document_path="/test.md",
                section_hierarchy=[],
                chunk_index=0,
                total_chunks=1,
                has_code=False,
            ),
        )

        # Set different contexts for different categories
        cache.set(chunk, DocumentCategory.GENERAL, "General context")
        cache.set(chunk, DocumentCategory.DOCUMENTATION, "Documentation context")

        # Retrieve and verify
        general_context = cache.get(chunk, DocumentCategory.GENERAL)
        doc_context = cache.get(chunk, DocumentCategory.DOCUMENTATION)

        assert general_context == "General context"
        assert doc_context == "Documentation context"
        assert general_context != doc_context


class TestPromptTemplates:
    """Test prompt template functionality."""

    def test_template_registry_initialization(self):
        """Test that all categories have templates."""
        registry = PromptTemplateRegistry()

        for category in DocumentCategory:
            template = registry.get_template(category)
            assert template is not None
            assert template.system_prompt
            assert template.user_prompt_template

    def test_template_formatting(self):
        """Test prompt template formatting."""
        registry = PromptTemplateRegistry()
        template = registry.get_template(DocumentCategory.CODE)

        chunk = DocumentChunk(
            id="test",
            content="def hello(): pass",
            type=ChunkType.CODE_BLOCK,
            metadata=ChunkMetadata(
                document_path="/test.py",
                section_hierarchy=["Module", "Functions"],
                chunk_index=0,
                total_chunks=1,
                has_code=True,
            ),
        )

        formatted = template.format_user_prompt(chunk, {"project": "TestProject"})

        assert "/test.py" in formatted
        assert "Module > Functions" in formatted
        assert "def hello(): pass" in formatted
        # TestProject is passed in document_context but the template might not use it

    def test_all_templates_format_correctly(self):
        """Test that all templates can be formatted without errors."""
        registry = PromptTemplateRegistry()

        chunk = DocumentChunk(
            id="test",
            content="Test content",
            type=ChunkType.PARAGRAPH,
            metadata=ChunkMetadata(
                document_path="/test.md",
                section_hierarchy=["Section1", "Section2"],
                chunk_index=0,
                total_chunks=1,
                has_code=False,
            ),
        )

        for category in DocumentCategory:
            template = registry.get_template(category)
            try:
                formatted = template.format_user_prompt(chunk, {})
                assert isinstance(formatted, str)
                assert len(formatted) > 0
            except Exception as e:
                raise AssertionError(f"Failed to format template for {category}: {e}")


class TestContextGenerationMetrics:
    """Test metrics tracking."""

    def test_metrics_initialization(self):
        """Test metrics are initialized correctly."""
        from mcp_server.document_processing.contextual_embeddings import ContextGenerationMetrics

        metrics = ContextGenerationMetrics()
        assert metrics.total_chunks == 0
        assert metrics.processed_chunks == 0
        assert metrics.cached_chunks == 0
        assert metrics.total_tokens_input == 0
        assert metrics.total_tokens_output == 0
        assert metrics.total_cost == 0.0
        assert metrics.processing_time == 0.0
        assert metrics.errors == []

    def test_metrics_add_usage(self):
        """Test adding token usage and cost calculation."""
        from mcp_server.document_processing.contextual_embeddings import ContextGenerationMetrics

        metrics = ContextGenerationMetrics()

        # Add some usage
        metrics.add_usage(1000, 500)

        # Check tokens
        assert metrics.total_tokens_input == 1000
        assert metrics.total_tokens_output == 500

        # Check cost calculation (based on Claude 3.5 Sonnet pricing)
        # Input: $3 per million tokens = 0.003 per 1000
        # Output: $15 per million tokens = 0.015 per 1000
        expected_cost = (1000 * 0.003 + 500 * 0.015) / 1000
        assert abs(metrics.total_cost - expected_cost) < 0.0001

        # Add more usage
        metrics.add_usage(500, 250)
        assert metrics.total_tokens_input == 1500
        assert metrics.total_tokens_output == 750


if __name__ == "__main__":
    # Run all tests
    import tempfile

    print("Running document category detection tests...")
    test_category = TestDocumentCategoryDetection()
    test_category.test_detect_code_by_extension()
    test_category.test_detect_documentation_by_extension()
    test_category.test_detect_tutorial_by_name()
    test_category.test_detect_configuration()
    test_category.test_detect_by_content()
    print("✓ All category detection tests passed")

    print("\nRunning cache tests...")
    with tempfile.TemporaryDirectory() as tmpdir:
        test_cache = TestContextCache()
        test_cache.test_cache_key_generation(Path(tmpdir))
        test_cache.test_cache_set_and_get(Path(tmpdir))
        test_cache.test_cache_different_categories(Path(tmpdir))
    print("✓ All cache tests passed")

    print("\nRunning prompt template tests...")
    test_templates = TestPromptTemplates()
    test_templates.test_template_registry_initialization()
    test_templates.test_template_formatting()
    test_templates.test_all_templates_format_correctly()
    print("✓ All template tests passed")

    print("\nRunning metrics tests...")
    test_metrics = TestContextGenerationMetrics()
    test_metrics.test_metrics_initialization()
    test_metrics.test_metrics_add_usage()
    print("✓ All metrics tests passed")

    print("\n🎉 All tests passed successfully!")
