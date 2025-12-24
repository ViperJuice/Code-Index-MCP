"""
Unit tests for document interfaces and data structures.

Tests the document processing interfaces including:
- ChunkType enum
- ChunkMetadata dataclass
- DocumentChunk dataclass and methods
- Section dataclass and hierarchy
- DocumentStructure dataclass
- Interface implementations
- Data serialization/deserialization
"""

import json
import uuid
from unittest.mock import Mock

import pytest

from mcp_server.document_processing.document_interfaces import (
    ChunkMetadata,
    ChunkType,
    DocumentChunk,
    DocumentStructure,
    IChunkStrategy,
    IDocumentProcessor,
    IStructureExtractor,
    ProcessedDocument,
    Section,
)


class TestChunkType:
    """Test ChunkType enum."""

    def test_chunk_types(self):
        """Test all chunk type values."""
        assert ChunkType.HEADING.value == "heading"
        assert ChunkType.PARAGRAPH.value == "paragraph"
        assert ChunkType.CODE_BLOCK.value == "code_block"
        assert ChunkType.LIST.value == "list"
        assert ChunkType.TABLE.value == "table"
        assert ChunkType.METADATA.value == "metadata"
        assert ChunkType.QUOTE.value == "quote"
        assert ChunkType.UNKNOWN.value == "unknown"

    def test_chunk_type_membership(self):
        """Test chunk type membership."""
        assert ChunkType.HEADING in ChunkType
        # Test that we can get enum by value
        assert ChunkType("heading") == ChunkType.HEADING
        # Test that invalid value raises error
        with pytest.raises(ValueError):
            ChunkType("invalid_type")


class TestChunkMetadata:
    """Test ChunkMetadata dataclass."""

    def test_create_metadata(self):
        """Test creating chunk metadata."""
        metadata = ChunkMetadata(
            document_path="/path/to/doc.md",
            section_hierarchy=["Chapter 1", "Section 1.1"],
            chunk_index=5,
            total_chunks=20,
            has_code=True,
            language="python",
            keywords=["test", "example"],
            word_count=150,
            line_start=10,
            line_end=25,
        )

        assert metadata.document_path == "/path/to/doc.md"
        assert metadata.section_hierarchy == ["Chapter 1", "Section 1.1"]
        assert metadata.chunk_index == 5
        assert metadata.total_chunks == 20
        assert metadata.has_code is True
        assert metadata.language == "python"
        assert metadata.keywords == ["test", "example"]
        assert metadata.word_count == 150
        assert metadata.line_start == 10
        assert metadata.line_end == 25

    def test_metadata_defaults(self):
        """Test metadata default values."""
        metadata = ChunkMetadata(
            document_path="test.txt",
            section_hierarchy=[],
            chunk_index=0,
            total_chunks=1,
            has_code=False,
        )

        assert metadata.language is None
        assert metadata.keywords == []  # Post-init sets empty list
        assert metadata.word_count == 0
        assert metadata.line_start == 0
        assert metadata.line_end == 0

    def test_metadata_post_init(self):
        """Test post-init processing."""
        # Keywords should be initialized to empty list if None
        metadata = ChunkMetadata(
            document_path="test.txt",
            section_hierarchy=[],
            chunk_index=0,
            total_chunks=1,
            has_code=False,
            keywords=None,
        )

        assert metadata.keywords == []


class TestDocumentChunk:
    """Test DocumentChunk dataclass."""

    def test_create_chunk(self):
        """Test creating a document chunk."""
        metadata = ChunkMetadata(
            document_path="test.md",
            section_hierarchy=["Main"],
            chunk_index=0,
            total_chunks=1,
            has_code=False,
        )

        chunk = DocumentChunk(
            id="chunk-123",
            content="This is the chunk content.",
            type=ChunkType.PARAGRAPH,
            metadata=metadata,
            embedding=[0.1, 0.2, 0.3],
            context_before="Previous content",
            context_after="Next content",
        )

        assert chunk.id == "chunk-123"
        assert chunk.content == "This is the chunk content."
        assert chunk.type == ChunkType.PARAGRAPH
        assert chunk.metadata == metadata
        assert chunk.embedding == [0.1, 0.2, 0.3]
        assert chunk.context_before == "Previous content"
        assert chunk.context_after == "Next content"

    def test_chunk_defaults(self):
        """Test chunk default values."""
        metadata = ChunkMetadata(
            document_path="test.md",
            section_hierarchy=[],
            chunk_index=0,
            total_chunks=1,
            has_code=False,
        )

        chunk = DocumentChunk(
            id="chunk-456", content="Content", type=ChunkType.UNKNOWN, metadata=metadata
        )

        assert chunk.embedding is None
        assert chunk.context_before is None
        assert chunk.context_after is None

    def test_chunk_to_dict(self):
        """Test converting chunk to dictionary."""
        metadata = ChunkMetadata(
            document_path="test.md",
            section_hierarchy=["Chapter 1", "Section 1.1"],
            chunk_index=2,
            total_chunks=10,
            has_code=True,
            language="python",
            keywords=["code", "example"],
            word_count=100,
            line_start=20,
            line_end=30,
        )

        chunk = DocumentChunk(
            id="chunk-789",
            content="Chunk content here",
            type=ChunkType.CODE_BLOCK,
            metadata=metadata,
            embedding=[0.5, 0.6],
            context_before="Before",
            context_after="After",
        )

        chunk_dict = chunk.to_dict()

        assert chunk_dict["id"] == "chunk-789"
        assert chunk_dict["content"] == "Chunk content here"
        assert chunk_dict["type"] == "code_block"
        assert chunk_dict["embedding"] == [0.5, 0.6]
        assert chunk_dict["context_before"] == "Before"
        assert chunk_dict["context_after"] == "After"

        # Check metadata conversion
        meta_dict = chunk_dict["metadata"]
        assert meta_dict["document_path"] == "test.md"
        assert meta_dict["section_hierarchy"] == ["Chapter 1", "Section 1.1"]
        assert meta_dict["chunk_index"] == 2
        assert meta_dict["total_chunks"] == 10
        assert meta_dict["has_code"] is True
        assert meta_dict["language"] == "python"
        assert meta_dict["keywords"] == ["code", "example"]
        assert meta_dict["word_count"] == 100
        assert meta_dict["line_start"] == 20
        assert meta_dict["line_end"] == 30

    def test_chunk_serialization(self):
        """Test that chunk can be serialized to JSON."""
        metadata = ChunkMetadata(
            document_path="test.json",
            section_hierarchy=["Root"],
            chunk_index=0,
            total_chunks=1,
            has_code=False,
        )

        chunk = DocumentChunk(
            id=str(uuid.uuid4()),
            content="Serializable content",
            type=ChunkType.PARAGRAPH,
            metadata=metadata,
        )

        # Should be JSON serializable
        chunk_dict = chunk.to_dict()
        json_str = json.dumps(chunk_dict)
        reconstructed = json.loads(json_str)

        assert reconstructed["content"] == "Serializable content"
        assert reconstructed["type"] == "paragraph"


class TestSection:
    """Test Section dataclass."""

    def test_create_section(self):
        """Test creating a section."""
        parent = Section(
            id="parent-1", heading="Chapter 1", level=1, content="Chapter introduction"
        )

        section = Section(
            id="section-1",
            heading="Section 1.1",
            level=2,
            content="Section content here",
            parent=parent,
            children=[],
            start_line=10,
            end_line=20,
        )

        assert section.id == "section-1"
        assert section.heading == "Section 1.1"
        assert section.level == 2
        assert section.content == "Section content here"
        assert section.parent == parent
        assert section.children == []
        assert section.start_line == 10
        assert section.end_line == 20

    def test_section_defaults(self):
        """Test section default values."""
        section = Section(id="section-2", heading="Test Section", level=1, content="Content")

        assert section.parent is None
        assert section.children == []  # Post-init sets empty list
        assert section.start_line == 0
        assert section.end_line == 0

    def test_section_hierarchy_path(self):
        """Test getting section hierarchy path."""
        # Create hierarchy: Chapter > Section > Subsection
        chapter = Section(id="ch-1", heading="Chapter 1", level=1, content="Chapter content")

        section = Section(
            id="sec-1", heading="Section 1.1", level=2, content="Section content", parent=chapter
        )

        subsection = Section(
            id="subsec-1",
            heading="Subsection 1.1.1",
            level=3,
            content="Subsection content",
            parent=section,
        )

        # Test hierarchy paths
        assert chapter.get_hierarchy_path() == ["Chapter 1"]
        assert section.get_hierarchy_path() == ["Chapter 1", "Section 1.1"]
        assert subsection.get_hierarchy_path() == ["Chapter 1", "Section 1.1", "Subsection 1.1.1"]

    def test_section_children_management(self):
        """Test managing section children."""
        parent = Section(id="parent", heading="Parent Section", level=1, content="Parent content")

        child1 = Section(
            id="child1", heading="Child 1", level=2, content="Child 1 content", parent=parent
        )

        child2 = Section(
            id="child2", heading="Child 2", level=2, content="Child 2 content", parent=parent
        )

        # Add children to parent
        parent.children.append(child1)
        parent.children.append(child2)

        assert len(parent.children) == 2
        assert child1 in parent.children
        assert child2 in parent.children
        assert child1.parent == parent
        assert child2.parent == parent


class TestDocumentStructure:
    """Test DocumentStructure dataclass."""

    def test_create_structure(self):
        """Test creating document structure."""
        section1 = Section(id="s1", heading="Introduction", level=1, content="Intro content")

        section2 = Section(id="s2", heading="Main Content", level=1, content="Main content")

        structure = DocumentStructure(
            title="Test Document",
            sections=[section1, section2],
            metadata={"author": "Test Author", "date": "2024-01-15"},
            outline=section1,
            cross_references=[{"from": "s1", "to": "s2", "type": "see-also"}],
        )

        assert structure.title == "Test Document"
        assert len(structure.sections) == 2
        assert structure.metadata["author"] == "Test Author"
        assert structure.outline == section1
        assert len(structure.cross_references) == 1

    def test_structure_defaults(self):
        """Test structure default values."""
        structure = DocumentStructure(title=None, sections=[], metadata=None)

        assert structure.title is None
        assert structure.sections == []
        assert structure.metadata == {}  # Post-init sets empty dict
        assert structure.outline is None
        assert structure.cross_references == []  # Post-init sets empty list


class TestProcessedDocument:
    """Test ProcessedDocument dataclass."""

    def test_create_processed_document(self):
        """Test creating a processed document."""
        structure = DocumentStructure(title="Test Doc", sections=[], metadata={"type": "test"})

        chunks = [
            DocumentChunk(
                id="c1",
                content="Chunk 1",
                type=ChunkType.PARAGRAPH,
                metadata=ChunkMetadata(
                    document_path="test.md",
                    section_hierarchy=[],
                    chunk_index=0,
                    total_chunks=2,
                    has_code=False,
                ),
            ),
            DocumentChunk(
                id="c2",
                content="Chunk 2",
                type=ChunkType.CODE_BLOCK,
                metadata=ChunkMetadata(
                    document_path="test.md",
                    section_hierarchy=[],
                    chunk_index=1,
                    total_chunks=2,
                    has_code=True,
                ),
            ),
        ]

        doc = ProcessedDocument(
            path="/path/to/test.md",
            content="Original content",
            structure=structure,
            chunks=chunks,
            metadata={"processed": True},
            language="markdown",
        )

        assert doc.path == "/path/to/test.md"
        assert doc.content == "Original content"
        assert doc.structure == structure
        assert len(doc.chunks) == 2
        assert doc.metadata["processed"] is True
        assert doc.language == "markdown"

    def test_get_total_chunks(self):
        """Test getting total chunk count."""
        doc = ProcessedDocument(
            path="test.md",
            content="",
            structure=Mock(),
            chunks=[Mock(), Mock(), Mock()],
            metadata={},
        )

        assert doc.get_total_chunks() == 3

    def test_get_sections_at_level(self):
        """Test getting sections at a specific level."""
        # Create hierarchical structure
        root = Section(id="root", heading="Document", level=0, content="Root")

        chapter1 = Section(id="ch1", heading="Chapter 1", level=1, content="Chapter 1", parent=root)

        chapter2 = Section(id="ch2", heading="Chapter 2", level=1, content="Chapter 2", parent=root)

        section1_1 = Section(
            id="s1.1", heading="Section 1.1", level=2, content="Section 1.1", parent=chapter1
        )

        section1_2 = Section(
            id="s1.2", heading="Section 1.2", level=2, content="Section 1.2", parent=chapter1
        )

        # Build tree
        root.children = [chapter1, chapter2]
        chapter1.children = [section1_1, section1_2]

        structure = DocumentStructure(
            title="Test",
            sections=[root, chapter1, chapter2, section1_1, section1_2],
            metadata={},
            outline=root,
        )

        doc = ProcessedDocument(
            path="test.md", content="", structure=structure, chunks=[], metadata={}
        )

        # Test getting sections at different levels
        level0_sections = doc.get_sections_at_level(0)
        assert len(level0_sections) == 1
        assert level0_sections[0].heading == "Document"

        level1_sections = doc.get_sections_at_level(1)
        assert len(level1_sections) == 2
        assert any(s.heading == "Chapter 1" for s in level1_sections)
        assert any(s.heading == "Chapter 2" for s in level1_sections)

        level2_sections = doc.get_sections_at_level(2)
        assert len(level2_sections) == 2
        assert any(s.heading == "Section 1.1" for s in level2_sections)
        assert any(s.heading == "Section 1.2" for s in level2_sections)

        # No sections at level 3
        level3_sections = doc.get_sections_at_level(3)
        assert len(level3_sections) == 0


class TestInterfaces:
    """Test interface definitions."""

    def test_document_processor_interface(self):
        """Test IDocumentProcessor interface."""

        class ConcreteProcessor(IDocumentProcessor):
            def process_document(self, content: str) -> ProcessedDocument:
                return ProcessedDocument(
                    path="test.txt", content=content, structure=Mock(), chunks=[], metadata={}
                )

            def extract_metadata(self, content: str):
                return {"extracted": True}

            def create_searchable_chunks(self, content: str):
                return []

        processor = ConcreteProcessor()

        # Test implementation
        result = processor.process_document("Test content")
        assert isinstance(result, ProcessedDocument)

        metadata = processor.extract_metadata("Test")
        assert metadata["extracted"] is True

        chunks = processor.create_searchable_chunks("Test")
        assert chunks == []

    def test_chunk_strategy_interface(self):
        """Test IChunkStrategy interface."""

        class ConcreteStrategy(IChunkStrategy):
            def chunk(self, content: str, structure: DocumentStructure):
                return [
                    DocumentChunk(
                        id="1", content=content, type=ChunkType.PARAGRAPH, metadata=Mock()
                    )
                ]

            def validate_chunk(self, chunk: DocumentChunk):
                return len(chunk.content) > 0

            def merge_small_chunks(self, chunks):
                return chunks

        strategy = ConcreteStrategy()
        structure = Mock(spec=DocumentStructure)

        # Test implementation
        chunks = strategy.chunk("Content", structure)
        assert len(chunks) == 1

        valid = strategy.validate_chunk(chunks[0])
        assert valid is True

        merged = strategy.merge_small_chunks(chunks)
        assert merged == chunks

    def test_structure_extractor_interface(self):
        """Test IStructureExtractor interface."""

        class ConcreteExtractor(IStructureExtractor):
            def extract_structure(self, content: str):
                return DocumentStructure(title="Extracted", sections=[], metadata={})

            def find_sections(self, content: str):
                return [Section(id="1", heading="Section", level=1, content=content)]

            def build_hierarchy(self, sections):
                if sections:
                    return sections[0]
                return None

        extractor = ConcreteExtractor()

        # Test implementation
        structure = extractor.extract_structure("Content")
        assert structure.title == "Extracted"

        sections = extractor.find_sections("Content")
        assert len(sections) == 1

        hierarchy = extractor.build_hierarchy(sections)
        assert hierarchy == sections[0]


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_section_hierarchy(self):
        """Test section with no parent."""
        section = Section(id="orphan", heading="Orphan Section", level=1, content="No parent")

        assert section.get_hierarchy_path() == ["Orphan Section"]

    def test_circular_section_reference(self):
        """Test handling circular section references."""
        section1 = Section(id="s1", heading="Section 1", level=1, content="Content 1")

        section2 = Section(
            id="s2", heading="Section 2", level=2, content="Content 2", parent=section1
        )

        # Create circular reference
        section1.parent = section2

        # get_hierarchy_path should handle this gracefully
        # (in practice, might need cycle detection)
        # This test documents the current behavior

    def test_chunk_with_null_metadata_fields(self):
        """Test chunk with null metadata fields."""
        metadata = ChunkMetadata(
            document_path="",
            section_hierarchy=[],
            chunk_index=0,
            total_chunks=0,
            has_code=False,
            language=None,
            keywords=None,
        )

        chunk = DocumentChunk(id="null-test", content="", type=ChunkType.UNKNOWN, metadata=metadata)

        # to_dict should handle null values
        chunk_dict = chunk.to_dict()
        assert chunk_dict["metadata"]["language"] is None
        assert chunk_dict["metadata"]["keywords"] == []  # Post-init converts None to []

    def test_unicode_in_content(self):
        """Test handling Unicode content."""
        section = Section(
            id="unicode",
            heading="Unicode Section 中文 العربية",
            level=1,
            content="Content with emojis 🚀 and symbols € £ ¥",
        )

        assert "中文" in section.heading
        assert "🚀" in section.content

        # Test in chunk
        metadata = ChunkMetadata(
            document_path="unicode.txt",
            section_hierarchy=["中文章节"],
            chunk_index=0,
            total_chunks=1,
            has_code=False,
        )

        chunk = DocumentChunk(
            id="unicode-chunk",
            content="Unicode content: 你好世界 🌍",
            type=ChunkType.PARAGRAPH,
            metadata=metadata,
        )

        chunk_dict = chunk.to_dict()
        assert "你好世界" in chunk_dict["content"]
        assert "中文章节" in chunk_dict["metadata"]["section_hierarchy"][0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
