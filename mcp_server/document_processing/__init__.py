"""Document processing plugins for code-index-mcp."""

from .base_document_plugin import (
    BaseDocumentPlugin,
    DocumentMetadata
)

from .document_interfaces import (
    DocumentChunk,
    DocumentStructure,
    Section,
    ChunkType,
    ChunkMetadata,
    ProcessedDocument,
    IDocumentProcessor,
    IChunkStrategy,
    IStructureExtractor
)

from .chunk_optimizer import (
    ChunkOptimizer,
    ChunkingStrategy,
    ChunkingConfig,
    TokenEstimator,
    SentenceSplitter,
    ParagraphSplitter,
    SemanticAnalyzer,
    FixedSizeChunkingStrategy,
    SentenceBasedChunkingStrategy,
    ParagraphBasedChunkingStrategy,
    SemanticBasedChunkingStrategy,
    HybridChunkingStrategy,
    create_chunk_optimizer
)

from .metadata_extractor import MetadataExtractor

from .semantic_chunker import (
    SemanticChunker,
    DocumentType,
    DocumentTypeDetector,
    ContextWindow,
    ChunkingContext,
    SemanticBoundaryDetector,
    HierarchicalChunker,
    MetadataPreserver,
    create_semantic_chunker
)

__all__ = [
    'BaseDocumentPlugin',
    'DocumentMetadata',
    'DocumentChunk',
    'DocumentStructure',
    'Section',
    'ChunkType',
    'ChunkMetadata',
    'ProcessedDocument',
    'IDocumentProcessor',
    'IChunkStrategy',
    'IStructureExtractor',
    'ChunkOptimizer',
    'ChunkingStrategy',
    'ChunkingConfig',
    'TokenEstimator',
    'SentenceSplitter',
    'ParagraphSplitter',
    'SemanticAnalyzer',
    'FixedSizeChunkingStrategy',
    'SentenceBasedChunkingStrategy',
    'ParagraphBasedChunkingStrategy',
    'SemanticBasedChunkingStrategy',
    'HybridChunkingStrategy',
    'create_chunk_optimizer',
    'MetadataExtractor',
    'SemanticChunker',
    'DocumentType',
    'DocumentTypeDetector',
    'ContextWindow',
    'ChunkingContext',
    'SemanticBoundaryDetector',
    'HierarchicalChunker',
    'MetadataPreserver',
    'create_semantic_chunker'
]