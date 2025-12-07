"""Semantic chunker for document processing with context-aware chunking."""

import re
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from .chunk_optimizer import (
    ChunkingConfig,
    ChunkingStrategy,
    ChunkOptimizer,
    HybridChunkingStrategy,
    TokenEstimator,
)
from .document_interfaces import (
    ChunkMetadata,
    ChunkType,
    DocumentChunk,
    DocumentStructure,
    ProcessedDocument,
    Section,
)


class DocumentType(Enum):
    """Types of documentation."""

    TECHNICAL = "technical"
    API = "api"
    TUTORIAL = "tutorial"
    README = "readme"
    GUIDE = "guide"
    REFERENCE = "reference"
    UNKNOWN = "unknown"


@dataclass
class ContextWindow:
    """Manages context windows for chunks."""

    size: int = 512  # tokens
    overlap: int = 128  # tokens for continuity
    preserve_boundaries: bool = True

    def calculate_overlap(self, chunk1_size: int, chunk2_size: int) -> int:
        """Calculate optimal overlap between chunks."""
        # Larger chunks need more overlap
        base_overlap = self.overlap
        size_factor = min(chunk1_size + chunk2_size, self.size * 2) / (self.size * 2)
        return int(base_overlap * (1 + size_factor * 0.5))


@dataclass
class ChunkingContext:
    """Context information for semantic chunking."""

    document_type: DocumentType
    section_depth: int = 0
    parent_sections: List[str] = field(default_factory=list)
    sibling_chunks: List[DocumentChunk] = field(default_factory=list)
    keywords: Set[str] = field(default_factory=set)
    cross_references: List[str] = field(default_factory=list)

    def get_hierarchy_string(self) -> str:
        """Get formatted hierarchy string."""
        if not self.parent_sections:
            return ""
        return " > ".join(self.parent_sections)


class DocumentTypeDetector:
    """Detects the type of documentation from content."""

    def __init__(self):
        self.type_patterns = {
            DocumentType.API: [
                r"(?i)(api|endpoint|request|response|parameter|authentication)",
                r"(?i)(GET|POST|PUT|DELETE|PATCH)\s+/",
                r"(?i)(curl|http|https)://",
                r"(?i)status\s+code|headers?|body",
            ],
            DocumentType.TECHNICAL: [
                r"(?i)(architecture|implementation|design|component|system)",
                r"(?i)(class|method|function|interface|module)",
                r"(?i)(algorithm|data\s+structure|performance|complexity)",
            ],
            DocumentType.TUTORIAL: [
                r"(?i)(step\s+\d+|first|second|third|next|then|finally)",
                r"(?i)(tutorial|guide|walkthrough|getting\s+started)",
                r"(?i)(example|demo|sample|try|follow)",
                r"(?i)(learn|understand|practice)",
            ],
            DocumentType.README: [
                r"(?i)^#\s+[\w\s-]+$",  # Main title
                r"(?i)(installation|usage|features|requirements)",
                r"(?i)(contributing|license|author|credits)",
                r"(?i)(badge|shield|npm|pypi|maven)",
            ],
            DocumentType.GUIDE: [
                r"(?i)(guide|handbook|manual|documentation)",
                r"(?i)(chapter|section|part\s+\d+)",
                r"(?i)(overview|introduction|conclusion|summary)",
            ],
            DocumentType.REFERENCE: [
                r"(?i)(reference|specification|standard|rfc)",
                r"(?i)(syntax|grammar|notation|format)",
                r"(?i)(table\s+of|appendix|glossary|index)",
            ],
        }

    def detect_type(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> DocumentType:
        """Detect document type from content and metadata."""
        # Check metadata hints first
        if metadata:
            if "type" in metadata:
                try:
                    return DocumentType(metadata["type"])
                except ValueError:
                    pass

            # Check filename patterns
            if "path" in metadata:
                path = metadata["path"].lower()
                if "readme" in path:
                    return DocumentType.README
                elif "api" in path:
                    return DocumentType.API
                elif "tutorial" in path or "guide" in path:
                    return DocumentType.TUTORIAL
                elif "reference" in path or "ref" in path:
                    return DocumentType.REFERENCE

        # Analyze content
        scores = {}
        for doc_type, patterns in self.type_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, content[:2000]))  # Check first 2000 chars
                score += matches
            scores[doc_type] = score

        # Return type with highest score
        if scores:
            best_type = max(scores.items(), key=lambda x: x[1])
            if best_type[1] > 0:
                return best_type[0]

        return DocumentType.UNKNOWN


class SemanticBoundaryDetector:
    """Detects semantic boundaries in documentation."""

    def __init__(self):
        self.boundary_patterns = {
            "strong": [
                r"^#{1,6}\s+",  # Markdown headings
                r"^={3,}$",  # Section separators
                r"^-{3,}$",
                r"^\*{3,}$",
                r"^Chapter\s+\d+",
                r"^Section\s+\d+",
                r"^Part\s+\d+",
            ],
            "medium": [
                r"^\d+\.\s+\w+",  # Numbered sections
                r"^[A-Z][^.!?]*:$",  # Capitalized labels
                r"^\s*\n\s*\n",  # Double newlines
                r"^(However|Moreover|Furthermore|Therefore)",
                r"^(In conclusion|To summarize|In summary)",
            ],
            "weak": [
                r"\.\s+[A-Z]",  # Sentence boundaries
                r"[.!?]\s*\n",  # End of paragraph
                r"^\s*[-*+]\s+",  # List items
                r"^\s*\d+\)\s+",  # Numbered lists
            ],
        }

        self.topic_shift_indicators = [
            "however",
            "moreover",
            "furthermore",
            "therefore",
            "consequently",
            "on the other hand",
            "in contrast",
            "alternatively",
            "additionally",
            "next",
            "then",
            "finally",
            "first",
            "second",
            "third",
        ]

    def find_boundaries(self, content: str) -> List[Tuple[int, str]]:
        """Find semantic boundaries with their strength."""
        boundaries = []

        # Find all boundary matches
        for strength, patterns in self.boundary_patterns.items():
            for pattern in patterns:
                for match in re.finditer(pattern, content, re.MULTILINE):
                    boundaries.append((match.start(), strength))

        # Sort by position
        boundaries.sort(key=lambda x: x[0])

        # Remove duplicates within 10 characters
        filtered = []
        last_pos = -100
        for pos, strength in boundaries:
            if pos - last_pos > 10:
                filtered.append((pos, strength))
                last_pos = pos

        return filtered

    def calculate_boundary_score(self, text_before: str, text_after: str) -> float:
        """Calculate semantic boundary score between two text segments."""
        score = 0.0

        # Check for topic shift indicators
        after_lower = text_after[:200].lower()
        for indicator in self.topic_shift_indicators:
            if indicator in after_lower:
                score += 0.2

        # Check for significant whitespace
        whitespace_before = len(text_before) - len(text_before.rstrip())
        whitespace_after = len(text_after) - len(text_after.lstrip())
        if whitespace_before + whitespace_after > 2:
            score += 0.1

        # Check for heading patterns
        if re.match(r"^#{1,6}\s+", text_after):
            score += 0.5

        # Check for different paragraph styles
        if text_before.strip().endswith(":") and text_after.strip():
            score += 0.3

        return min(score, 1.0)


class HierarchicalChunker:
    """Handles hierarchical chunking of documents."""

    def __init__(self, token_estimator: TokenEstimator, max_chunk_size: int):
        self.token_estimator = token_estimator
        self.max_chunk_size = max_chunk_size
        self.min_section_size = 50  # Minimum tokens for a section

    def chunk_hierarchically(
        self, structure: DocumentStructure, content: str
    ) -> List[DocumentChunk]:
        """Create chunks following document hierarchy."""
        chunks = []

        if structure.outline:
            self._process_section_tree(structure.outline, chunks, [], content)
        else:
            # Process flat sections
            for section in structure.sections:
                self._process_section(section, chunks, [], content)

        return chunks

    def _process_section_tree(
        self,
        section: Section,
        chunks: List[DocumentChunk],
        parent_hierarchy: List[str],
        full_content: str,
    ):
        """Process a section and its children recursively."""
        hierarchy = parent_hierarchy + [section.heading]

        # Check if section is small enough to be a single chunk
        section_tokens = self.token_estimator.estimate_tokens(section.content)

        if section_tokens <= self.max_chunk_size:
            # Include all subsections in one chunk if they fit
            full_section_content = self._get_full_section_content(section)
            full_tokens = self.token_estimator.estimate_tokens(full_section_content)

            if full_tokens <= self.max_chunk_size:
                # Create single chunk for entire section
                chunk = self._create_section_chunk(
                    full_section_content, hierarchy, len(chunks), section
                )
                chunks.append(chunk)
                return

        # Section is too large, process content and children separately
        if section.content.strip():
            # Chunk the section's direct content
            if section_tokens > self.max_chunk_size:
                # Split large section content
                sub_chunks = self._split_section_content(section.content, hierarchy, section)
                chunks.extend(sub_chunks)
            else:
                # Create chunk for section content
                chunk = self._create_section_chunk(section.content, hierarchy, len(chunks), section)
                chunks.append(chunk)

        # Process child sections
        for child in section.children:
            self._process_section_tree(child, chunks, hierarchy, full_content)

    def _process_section(
        self,
        section: Section,
        chunks: List[DocumentChunk],
        parent_hierarchy: List[str],
        full_content: str,
    ):
        """Process a single section."""
        hierarchy = parent_hierarchy + [section.heading]

        if section.content.strip():
            section_tokens = self.token_estimator.estimate_tokens(section.content)

            if section_tokens > self.max_chunk_size:
                # Split large section
                sub_chunks = self._split_section_content(section.content, hierarchy, section)
                chunks.extend(sub_chunks)
            else:
                # Create single chunk
                chunk = self._create_section_chunk(section.content, hierarchy, len(chunks), section)
                chunks.append(chunk)

    def _get_full_section_content(self, section: Section) -> str:
        """Get full content including all subsections."""
        content = section.content

        for child in section.children:
            child_content = self._get_full_section_content(child)
            if child_content:
                content += "\n\n" + child_content

        return content

    def _split_section_content(
        self, content: str, hierarchy: List[str], section: Section
    ) -> List[DocumentChunk]:
        """Split large section content into smaller chunks."""
        chunks = []

        # Use paragraph boundaries for splitting
        paragraphs = re.split(r"\n\s*\n", content)
        current_content = ""
        current_tokens = 0

        for para in paragraphs:
            para_tokens = self.token_estimator.estimate_tokens(para)

            if current_tokens + para_tokens > self.max_chunk_size and current_content:
                # Create chunk
                chunk = self._create_section_chunk(
                    current_content.strip(), hierarchy, len(chunks), section
                )
                chunks.append(chunk)
                current_content = para
                current_tokens = para_tokens
            else:
                if current_content:
                    current_content += "\n\n" + para
                else:
                    current_content = para
                current_tokens += para_tokens

        # Last chunk
        if current_content:
            chunk = self._create_section_chunk(
                current_content.strip(), hierarchy, len(chunks), section
            )
            chunks.append(chunk)

        return chunks

    def _create_section_chunk(
        self, content: str, hierarchy: List[str], index: int, section: Section
    ) -> DocumentChunk:
        """Create a chunk from section content."""
        # Detect chunk type
        chunk_type = ChunkType.PARAGRAPH
        if content.strip().startswith("#"):
            chunk_type = ChunkType.HEADING
        elif re.search(r"```[\s\S]*?```", content):
            chunk_type = ChunkType.CODE_BLOCK
        elif re.search(r"^[-*+]\s+", content, re.MULTILINE):
            chunk_type = ChunkType.LIST

        metadata = ChunkMetadata(
            document_path="",  # Will be set by parent
            section_hierarchy=hierarchy,
            chunk_index=index,
            total_chunks=0,  # Will be updated
            has_code=bool(re.search(r"```|`[^`]+`", content)),
            word_count=len(content.split()),
            line_start=section.start_line,
            line_end=section.end_line,
        )

        return DocumentChunk(
            id=str(uuid.uuid4()), content=content, type=chunk_type, metadata=metadata
        )


class MetadataPreserver:
    """Preserves and propagates metadata across chunks."""

    def __init__(self):
        self.key_patterns = {
            "author": r"(?i)author:\s*(.+)",
            "date": r"(?i)date:\s*(.+)",
            "version": r"(?i)version:\s*(.+)",
            "tags": r"(?i)tags:\s*(.+)",
            "category": r"(?i)category:\s*(.+)",
        }

    def extract_document_metadata(self, content: str) -> Dict[str, Any]:
        """Extract metadata from document content."""
        metadata = {}

        # Check for front matter (YAML/TOML style)
        front_matter_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
        if front_matter_match:
            front_matter = front_matter_match.group(1)
            for key, pattern in self.key_patterns.items():
                match = re.search(pattern, front_matter)
                if match:
                    metadata[key] = match.group(1).strip()

        # Extract from content
        first_section = content[:1000]
        for key, pattern in self.key_patterns.items():
            if key not in metadata:
                match = re.search(pattern, first_section)
                if match:
                    metadata[key] = match.group(1).strip()

        return metadata

    def propagate_metadata(
        self, chunks: List[DocumentChunk], document_metadata: Dict[str, Any]
    ) -> List[DocumentChunk]:
        """Propagate document metadata to all chunks."""
        for chunk in chunks:
            # Add document-level metadata
            for key, value in document_metadata.items():
                if key not in ["path", "content"]:  # Skip large fields
                    chunk.metadata.__dict__[f"doc_{key}"] = value

            # Extract chunk-specific keywords
            chunk.metadata.keywords = self._extract_keywords(chunk.content)

        return chunks

    def _extract_keywords(self, content: str) -> List[str]:
        """Extract keywords from chunk content."""
        # Simple keyword extraction - can be enhanced
        words = re.findall(r"\b[A-Z][a-z]+(?:[A-Z][a-z]+)*\b", content)  # CamelCase
        words.extend(re.findall(r"\b[A-Z_]+\b", content))  # CONSTANTS
        words.extend(re.findall(r"\b\w+_\w+\b", content))  # snake_case

        # Deduplicate and limit
        seen = set()
        keywords = []
        for word in words:
            if word not in seen and len(word) > 3:
                seen.add(word)
                keywords.append(word)
                if len(keywords) >= 10:
                    break

        return keywords


class SemanticChunker:
    """Main semantic chunker that provides document-aware chunking."""

    def __init__(self, config: Optional[ChunkingConfig] = None):
        self.config = config or ChunkingConfig(
            strategy=ChunkingStrategy.HYBRID,
            max_chunk_size=1500,
            min_chunk_size=100,
            overlap_size=150,
            semantic_threshold=0.7,
        )

        # Initialize components
        self.optimizer = ChunkOptimizer(self.config)
        self.context_window = ContextWindow()
        self.type_detector = DocumentTypeDetector()
        self.boundary_detector = SemanticBoundaryDetector()
        self.hierarchical_chunker = HierarchicalChunker(
            self.optimizer.token_estimator, self.config.max_chunk_size
        )
        self.metadata_preserver = MetadataPreserver()

        # Strategy instance
        self.strategy = HybridChunkingStrategy(self.optimizer)

    def chunk_document(
        self,
        content: str,
        structure: DocumentStructure,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ProcessedDocument:
        """Main entry point for semantic chunking."""
        # Detect document type
        doc_type = self.type_detector.detect_type(content, metadata)

        # Extract document metadata
        doc_metadata = self.metadata_preserver.extract_document_metadata(content)
        if metadata:
            doc_metadata.update(metadata)

        # Create chunking context
        context = ChunkingContext(document_type=doc_type)

        # Choose chunking approach based on document type
        if doc_type == DocumentType.API:
            chunks = self._chunk_api_documentation(content, structure, context)
        elif doc_type == DocumentType.TUTORIAL:
            chunks = self._chunk_tutorial(content, structure, context)
        elif doc_type == DocumentType.README:
            chunks = self._chunk_readme(content, structure, context)
        elif structure and structure.sections:
            # Use hierarchical chunking for structured documents
            chunks = self.hierarchical_chunker.chunk_hierarchically(structure, content)
        else:
            # Fall back to optimizer strategy
            chunks = self.strategy.chunk(content, structure)

        # Add context and overlap
        chunks = self._add_context_windows(chunks, content)

        # Preserve metadata
        chunks = self.metadata_preserver.propagate_metadata(chunks, doc_metadata)

        # Update chunk metadata
        for i, chunk in enumerate(chunks):
            chunk.metadata.document_path = doc_metadata.get("path", "")
            chunk.metadata.chunk_index = i
            chunk.metadata.total_chunks = len(chunks)

        # Create processed document
        return ProcessedDocument(
            path=doc_metadata.get("path", ""),
            content=content,
            structure=structure,
            chunks=chunks,
            metadata=doc_metadata,
            language=doc_metadata.get("language", "unknown"),
        )

    def _chunk_api_documentation(
        self, content: str, structure: DocumentStructure, context: ChunkingContext
    ) -> List[DocumentChunk]:
        """Special handling for API documentation."""
        chunks = []

        # Look for API endpoint patterns
        endpoint_pattern = re.compile(
            r"(?:^|\n)((?:GET|POST|PUT|DELETE|PATCH)\s+/[^\n]+)", re.MULTILINE
        )

        endpoints = list(endpoint_pattern.finditer(content))

        if endpoints:
            # Chunk by endpoints
            for i, match in enumerate(endpoints):
                start = match.start()
                end = endpoints[i + 1].start() if i + 1 < len(endpoints) else len(content)

                endpoint_content = content[start:end].strip()
                if endpoint_content:
                    # Check size and split if needed
                    tokens = self.optimizer.token_estimator.estimate_tokens(endpoint_content)

                    if tokens > self.config.max_chunk_size:
                        # Split large endpoint documentation
                        sub_chunks = self._split_api_endpoint(endpoint_content)
                        chunks.extend(sub_chunks)
                    else:
                        chunk = self._create_api_chunk(endpoint_content, i)
                        chunks.append(chunk)
        else:
            # Fall back to standard chunking
            chunks = self.strategy.chunk(content, structure)

        return chunks

    def _chunk_tutorial(
        self, content: str, structure: DocumentStructure, context: ChunkingContext
    ) -> List[DocumentChunk]:
        """Special handling for tutorials."""
        chunks = []

        # Look for step patterns
        step_pattern = re.compile(
            r"(?:^|\n)((?:Step\s+\d+|First|Second|Third|Next|Then|Finally)[:\s][^\n]+)",
            re.MULTILINE | re.IGNORECASE,
        )

        steps = list(step_pattern.finditer(content))

        if steps:
            # Chunk by steps
            for i, match in enumerate(steps):
                start = match.start()
                end = steps[i + 1].start() if i + 1 < len(steps) else len(content)

                step_content = content[start:end].strip()
                if step_content:
                    chunk = self._create_tutorial_chunk(step_content, i)
                    chunks.append(chunk)
        else:
            # Use hierarchical chunking
            chunks = self.hierarchical_chunker.chunk_hierarchically(structure, content)

        return chunks

    def _chunk_readme(
        self, content: str, structure: DocumentStructure, context: ChunkingContext
    ) -> List[DocumentChunk]:
        """Special handling for README files."""
        # README files often have important sections that should be kept together
        important_sections = [
            "installation",
            "quick start",
            "usage",
            "getting started",
            "requirements",
            "features",
            "examples",
        ]

        chunks = []

        if structure and structure.sections:
            for section in structure.sections:
                # Check if this is an important section
                is_important = any(
                    keyword in section.heading.lower() for keyword in important_sections
                )

                if is_important:
                    # Try to keep important sections together
                    full_content = self.hierarchical_chunker._get_full_section_content(section)
                    tokens = self.optimizer.token_estimator.estimate_tokens(full_content)

                    if tokens <= self.config.max_chunk_size * 1.2:  # Allow 20% larger
                        chunk = self._create_readme_chunk(full_content, section)
                        chunks.append(chunk)
                        continue

                # Otherwise, process normally
                self.hierarchical_chunker._process_section(section, chunks, [], content)
        else:
            # Fall back to standard chunking
            chunks = self.strategy.chunk(content, structure)

        return chunks

    def _add_context_windows(
        self, chunks: List[DocumentChunk], full_content: str
    ) -> List[DocumentChunk]:
        """Add context windows to chunks for better continuity."""
        for i, chunk in enumerate(chunks):
            # Add context before
            if i > 0:
                prev_chunk = chunks[i - 1]
                overlap_size = self.context_window.calculate_overlap(
                    len(prev_chunk.content), len(chunk.content)
                )

                # Get last N tokens from previous chunk
                context_before = self._get_context_snippet(
                    prev_chunk.content, overlap_size, from_end=True
                )
                chunk.context_before = context_before

            # Add context after
            if i < len(chunks) - 1:
                next_chunk = chunks[i + 1]
                overlap_size = self.context_window.calculate_overlap(
                    len(chunk.content), len(next_chunk.content)
                )

                # Get first N tokens from next chunk
                context_after = self._get_context_snippet(
                    next_chunk.content, overlap_size, from_end=False
                )
                chunk.context_after = context_after

        return chunks

    def _get_context_snippet(self, content: str, target_tokens: int, from_end: bool) -> str:
        """Get a context snippet of approximately target_tokens size."""
        # Estimate characters needed
        target_chars = int(target_tokens / self.config.token_estimation_factor)

        if from_end:
            snippet = content[-target_chars:]
            # Try to start at sentence boundary
            sentence_start = snippet.find(". ")
            if sentence_start > 0 and sentence_start < len(snippet) / 2:
                snippet = snippet[sentence_start + 2 :]
        else:
            snippet = content[:target_chars]
            # Try to end at sentence boundary
            sentence_end = snippet.rfind(". ")
            if sentence_end > len(snippet) / 2:
                snippet = snippet[: sentence_end + 1]

        return snippet.strip()

    def _split_api_endpoint(self, content: str) -> List[DocumentChunk]:
        """Split large API endpoint documentation."""
        chunks = []

        # Common sections in API docs
        section_markers = [
            "Parameters",
            "Request",
            "Response",
            "Examples",
            "Authentication",
            "Errors",
            "Rate Limiting",
        ]

        # Find sections
        sections = []
        for marker in section_markers:
            pattern = re.compile(rf"(?:^|\n)({marker}[:\s])", re.IGNORECASE | re.MULTILINE)
            for match in pattern.finditer(content):
                sections.append((match.start(), marker))

        sections.sort(key=lambda x: x[0])

        # Create chunks based on sections
        for i, (start, marker) in enumerate(sections):
            end = sections[i + 1][0] if i + 1 < len(sections) else len(content)
            section_content = content[start:end].strip()

            if section_content:
                chunk = self._create_api_chunk(section_content, i)
                chunks.append(chunk)

        # If no sections found, split by paragraphs
        if not chunks:
            paragraphs = self.optimizer.paragraph_splitter.split_paragraphs(content)
            for i, para in enumerate(paragraphs):
                chunk = self._create_api_chunk(para, i)
                chunks.append(chunk)

        return chunks

    def _create_api_chunk(self, content: str, index: int) -> DocumentChunk:
        """Create an API documentation chunk."""
        metadata = ChunkMetadata(
            document_path="",
            section_hierarchy=["API Documentation"],
            chunk_index=index,
            total_chunks=0,
            has_code=bool(re.search(r"```|`[^`]+`|curl|http", content)),
            word_count=len(content.split()),
        )

        return DocumentChunk(
            id=str(uuid.uuid4()),
            content=content,
            type=ChunkType.CODE_BLOCK if "```" in content else ChunkType.PARAGRAPH,
            metadata=metadata,
        )

    def _create_tutorial_chunk(self, content: str, index: int) -> DocumentChunk:
        """Create a tutorial chunk."""
        metadata = ChunkMetadata(
            document_path="",
            section_hierarchy=["Tutorial"],
            chunk_index=index,
            total_chunks=0,
            has_code=bool(re.search(r"```|`[^`]+`", content)),
            word_count=len(content.split()),
        )

        return DocumentChunk(
            id=str(uuid.uuid4()),
            content=content,
            type=ChunkType.PARAGRAPH,
            metadata=metadata,
        )

    def _create_readme_chunk(self, content: str, section: Section) -> DocumentChunk:
        """Create a README chunk."""
        metadata = ChunkMetadata(
            document_path="",
            section_hierarchy=section.get_hierarchy_path(),
            chunk_index=0,
            total_chunks=0,
            has_code=bool(re.search(r"```|`[^`]+`", content)),
            word_count=len(content.split()),
            line_start=section.start_line,
            line_end=section.end_line,
        )

        return DocumentChunk(
            id=str(uuid.uuid4()),
            content=content,
            type=ChunkType.HEADING if section.level == 1 else ChunkType.PARAGRAPH,
            metadata=metadata,
        )

    def optimize_chunks(self, chunks: List[DocumentChunk]) -> List[DocumentChunk]:
        """Optimize chunks for better search and retrieval."""
        # Balance chunk sizes
        chunk_contents = [c.content for c in chunks]
        balanced_contents = self.optimizer.balance_chunk_sizes(
            chunk_contents, self.config.min_chunk_size, self.config.max_chunk_size
        )

        # Update chunks with balanced content
        optimized = []
        for i, content in enumerate(balanced_contents):
            if i < len(chunks):
                chunk = chunks[i]
                chunk.content = content
                optimized.append(chunk)
            else:
                # Create new chunk if needed
                chunk = DocumentChunk(
                    id=str(uuid.uuid4()),
                    content=content,
                    type=ChunkType.PARAGRAPH,
                    metadata=ChunkMetadata(
                        document_path="",
                        section_hierarchy=[],
                        chunk_index=i,
                        total_chunks=len(balanced_contents),
                        has_code=bool(re.search(r"```|`[^`]+`", content)),
                        word_count=len(content.split()),
                    ),
                )
                optimized.append(chunk)

        # Maintain semantic coherence
        coherent_contents = self.optimizer.maintain_semantic_coherence(
            [c.content for c in optimized]
        )

        # Update with coherent content
        for i, content in enumerate(coherent_contents):
            if i < len(optimized):
                optimized[i].content = content

        return optimized

    def merge_related_chunks(
        self, chunks: List[DocumentChunk], similarity_threshold: float = 0.8
    ) -> List[DocumentChunk]:
        """Merge chunks that are highly related."""
        if len(chunks) < 2:
            return chunks

        merged = []
        skip_next = False

        for i in range(len(chunks)):
            if skip_next:
                skip_next = False
                continue

            current = chunks[i]

            if i < len(chunks) - 1:
                next_chunk = chunks[i + 1]

                # Check if chunks are from same section
                same_section = (
                    current.metadata.section_hierarchy == next_chunk.metadata.section_hierarchy
                )

                if same_section:
                    # Calculate similarity
                    coherence = self.optimizer.semantic_analyzer.calculate_coherence_score(
                        current.content, next_chunk.content
                    )

                    # Check combined size
                    combined_tokens = self.optimizer.token_estimator.estimate_tokens(
                        current.content
                    ) + self.optimizer.token_estimator.estimate_tokens(next_chunk.content)

                    if (
                        coherence >= similarity_threshold
                        and combined_tokens <= self.config.max_chunk_size
                    ):
                        # Merge chunks
                        merged_content = current.content + "\n\n" + next_chunk.content
                        current.content = merged_content
                        current.metadata.line_end = next_chunk.metadata.line_end
                        merged.append(current)
                        skip_next = True
                        continue

            merged.append(current)

        # Update indices
        for i, chunk in enumerate(merged):
            chunk.metadata.chunk_index = i
            chunk.metadata.total_chunks = len(merged)

        return merged


def create_semantic_chunker(config: Optional[ChunkingConfig] = None) -> SemanticChunker:
    """Factory function to create a semantic chunker."""
    return SemanticChunker(config)
