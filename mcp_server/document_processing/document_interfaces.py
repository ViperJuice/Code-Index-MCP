"""Interfaces and data structures for document processing."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class ChunkType(Enum):
    """Types of document chunks."""

    HEADING = "heading"
    PARAGRAPH = "paragraph"
    CODE_BLOCK = "code_block"
    LIST = "list"
    TABLE = "table"
    METADATA = "metadata"
    QUOTE = "quote"
    UNKNOWN = "unknown"


@dataclass
class ChunkMetadata:
    """Metadata associated with a document chunk."""

    document_path: str
    section_hierarchy: List[str]  # e.g., ["Installation", "Requirements", "Python"]
    chunk_index: int
    total_chunks: int
    has_code: bool
    language: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    word_count: int = 0
    line_start: int = 0
    line_end: int = 0

    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
        if self.line_end and self.line_start and self.line_end < self.line_start:
            raise ValueError("line_end must be greater than or equal to line_start")


@dataclass
class DocumentChunk:
    """Represents a chunk of a document with metadata."""

    id: str
    content: str
    type: ChunkType
    metadata: ChunkMetadata
    embedding: Optional[List[float]] = None
    context_before: Optional[str] = None
    context_after: Optional[str] = None

    def is_valid(self) -> bool:
        """Validate minimum chunk contract invariants."""
        return (
            bool(self.id)
            and bool(self.content.strip())
            and self.metadata.chunk_index >= 0
            and self.metadata.total_chunks >= self.metadata.chunk_index + 1
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "content": self.content,
            "type": self.type.value,
            "metadata": {
                "document_path": self.metadata.document_path,
                "section_hierarchy": self.metadata.section_hierarchy,
                "chunk_index": self.metadata.chunk_index,
                "total_chunks": self.metadata.total_chunks,
                "has_code": self.metadata.has_code,
                "language": self.metadata.language,
                "keywords": self.metadata.keywords,
                "word_count": self.metadata.word_count,
                "line_start": self.metadata.line_start,
                "line_end": self.metadata.line_end,
            },
            "embedding": self.embedding,
            "context_before": self.context_before,
            "context_after": self.context_after,
        }


@dataclass
class Section:
    """Represents a section in a document."""

    id: str
    heading: str
    level: int  # 1 for #, 2 for ##, etc.
    content: str
    parent: Optional["Section"] = None
    children: List["Section"] = field(default_factory=list)
    start_line: int = 0
    end_line: int = 0

    def get_hierarchy_path(self) -> List[str]:
        """Get the full hierarchy path to this section."""
        path = []
        current = self
        while current:
            path.insert(0, current.heading)
            current = current.parent
        return path


@dataclass
class DocumentStructure:
    """Represents the hierarchical structure of a document."""

    title: Optional[str]
    sections: List[Section]
    metadata: Dict[str, Any]
    outline: Optional[Section] = None  # Root of section tree
    cross_references: List[Dict[str, str]] = field(default_factory=list)

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class IDocumentProcessor(ABC):
    """Interface for document processing."""

    @abstractmethod
    def process_document(
        self, content: str, file_path: Optional[Union[str, Path]] = None
    ) -> "ProcessedDocument":
        """Process a document and extract structured information."""

    @abstractmethod
    def extract_metadata(
        self, content: str, file_path: Optional[Union[str, Path]] = None
    ) -> Dict[str, Any]:
        """Extract metadata from document content."""

    @abstractmethod
    def create_searchable_chunks(
        self, content: str, file_path: Optional[Union[str, Path]] = None
    ) -> List[DocumentChunk]:
        """Create searchable chunks from document content."""


class IChunkStrategy(ABC):
    """Interface for document chunking strategies."""

    @abstractmethod
    def chunk(self, content: str, structure: DocumentStructure) -> List[DocumentChunk]:
        """Chunk document content based on structure.

        Returned chunks must be ordered by ``metadata.chunk_index``.
        """

    @abstractmethod
    def validate_chunk(self, chunk: DocumentChunk) -> bool:
        """Validate that a chunk meets quality criteria."""

    @abstractmethod
    def merge_small_chunks(self, chunks: List[DocumentChunk]) -> List[DocumentChunk]:
        """Merge chunks that are too small."""


class IStructureExtractor(ABC):
    """Interface for document structure extraction."""

    @abstractmethod
    def extract_structure(
        self, content: str, file_path: Optional[Union[str, Path]] = None
    ) -> DocumentStructure:
        """Extract the hierarchical structure of a document."""

    @abstractmethod
    def find_sections(self, content: str) -> List[Section]:
        """Find all sections in the document."""

    @abstractmethod
    def build_hierarchy(self, sections: List[Section]) -> Optional[Section]:
        """Build a hierarchical tree from flat sections."""


@dataclass
class ProcessedDocument:
    """Result of processing a document."""

    path: str
    content: str
    structure: DocumentStructure
    chunks: List[DocumentChunk]
    metadata: Dict[str, Any]
    language: str = "unknown"

    def get_total_chunks(self) -> int:
        """Get total number of chunks."""
        return len(self.chunks)

    def validate_chunk_order(self) -> bool:
        """Check that chunk indices are sequential and total metadata is stable."""
        if not self.chunks:
            return True

        expected_total = len(self.chunks)
        for index, chunk in enumerate(self.chunks):
            if chunk.metadata.chunk_index != index:
                return False
            if chunk.metadata.total_chunks != expected_total:
                return False
            if not chunk.is_valid():
                return False
        return True

    def get_sections_at_level(self, level: int) -> List[Section]:
        """Get all sections at a specific level."""
        sections = []

        def collect_at_level(section: Section, current_level: int):
            if current_level == level:
                sections.append(section)
            for child in section.children:
                collect_at_level(child, current_level + 1)

        if self.structure.outline:
            collect_at_level(self.structure.outline, 0)

        return sections
