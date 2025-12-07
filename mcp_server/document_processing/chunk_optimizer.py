"""Chunk optimizer for document processing with various chunking strategies."""

import re
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple

from .document_interfaces import (
    ChunkMetadata,
    ChunkType,
    DocumentChunk,
    DocumentStructure,
    IChunkStrategy,
    Section,
)


class ChunkingStrategy(Enum):
    """Available chunking strategies."""

    FIXED_SIZE = "fixed_size"
    SENTENCE_BASED = "sentence_based"
    PARAGRAPH_BASED = "paragraph_based"
    SEMANTIC_BASED = "semantic_based"
    HYBRID = "hybrid"


@dataclass
class ChunkingConfig:
    """Configuration for chunking operations."""

    strategy: ChunkingStrategy = ChunkingStrategy.HYBRID
    max_chunk_size: int = 1500  # tokens
    min_chunk_size: int = 100  # tokens
    overlap_size: int = 150  # tokens for context overlap
    max_context_window: int = 8192  # maximum embedding context window
    preserve_sentence_boundaries: bool = True
    preserve_paragraph_boundaries: bool = True
    semantic_threshold: float = 0.7  # similarity threshold for semantic chunking
    token_estimation_factor: float = 0.75  # chars to tokens ratio approximation


class TokenEstimator:
    """Estimates token count for text without requiring actual tokenizer."""

    def __init__(self, estimation_factor: float = 0.75):
        self.estimation_factor = estimation_factor
        # Common programming language keywords that might affect token count
        self.code_patterns = re.compile(
            r"\b(def|function|class|import|from|return|if|else|for|while|"
            r"try|except|catch|throw|public|private|protected|static|"
            r"const|let|var|async|await)\b"
        )

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for given text."""
        # Handle empty or whitespace-only text
        if not text or text.isspace():
            return 0

        # Basic estimation: characters * factor
        base_estimate = len(text) * self.estimation_factor

        # Adjust for code content (typically more tokens)
        code_matches = len(self.code_patterns.findall(text))
        if code_matches >= 3:  # Lower threshold for code detection
            base_estimate *= 1.2

        # Adjust for punctuation density
        punctuation_count = sum(1 for c in text if c in ".,;:()[]{}")
        punctuation_ratio = punctuation_count / max(len(text), 1)
        if punctuation_ratio > 0.1:
            base_estimate *= 1.1

        return int(base_estimate)


class SentenceSplitter:
    """Splits text into sentences while preserving structure."""

    def __init__(self):
        # Pattern for sentence boundaries
        self.sentence_pattern = re.compile(
            r"(?<=[.!?])\s+(?=[A-Z])|"  # Standard sentence end
            r"(?<=\n)\n+|"  # Double newlines
            r"(?<=\])\s*\n|"  # After closing bracket
            r"(?<=\))\s*\n"  # After closing parenthesis
        )

        # Pattern for list items
        self.list_pattern = re.compile(r"^[\s]*[-*+•]\s+", re.MULTILINE)

        # Pattern for numbered lists
        self.numbered_list_pattern = re.compile(r"^[\s]*\d+[.)]\s+", re.MULTILINE)

    def split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Handle code blocks separately
        code_blocks = []
        code_pattern = re.compile(r"```[\s\S]*?```|`[^`]+`")

        def replace_code(match):
            code_blocks.append(match.group())
            return f"__CODE_BLOCK_{len(code_blocks)-1}__"

        text_no_code = code_pattern.sub(replace_code, text)

        # Split into sentences
        sentences = self.sentence_pattern.split(text_no_code)

        # Restore code blocks
        result = []
        for sentence in sentences:
            if sentence.strip():
                for i, code in enumerate(code_blocks):
                    sentence = sentence.replace(f"__CODE_BLOCK_{i}__", code)
                result.append(sentence.strip())

        return result

    def is_list_item(self, text: str) -> bool:
        """Check if text is a list item."""
        return bool(self.list_pattern.match(text) or self.numbered_list_pattern.match(text))


class ParagraphSplitter:
    """Splits text into paragraphs."""

    def split_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs."""
        # Split by double newlines
        paragraphs = re.split(r"\n\s*\n", text)

        # Clean and filter
        result = []
        for para in paragraphs:
            cleaned = para.strip()
            if cleaned:
                result.append(cleaned)

        return result

    def merge_short_paragraphs(
        self, paragraphs: List[str], min_size: int, estimator: TokenEstimator
    ) -> List[str]:
        """Merge paragraphs that are too short."""
        if not paragraphs:
            return []

        result = []
        current = paragraphs[0]

        for para in paragraphs[1:]:
            current_tokens = estimator.estimate_tokens(current)
            para_tokens = estimator.estimate_tokens(para)

            if current_tokens < min_size and current_tokens + para_tokens < min_size * 3:
                current = current + "\n\n" + para
            else:
                result.append(current)
                current = para

        if current:
            result.append(current)

        return result


class SemanticAnalyzer:
    """Analyzes semantic boundaries in text."""

    def __init__(self):
        self.topic_indicators = [
            # Transition words
            r"\b(however|moreover|furthermore|therefore|consequently|thus|hence)\b",
            # Section indicators
            r"\b(introduction|conclusion|summary|overview|background)\b",
            # Topic changes
            r"\b(first|second|third|finally|next|then|additionally)\b",
            # Heading patterns
            r"^#+\s+",  # Markdown headings
            r"^\d+\.\s+[A-Z]",  # Numbered sections
        ]
        self.topic_pattern = re.compile(
            "|".join(self.topic_indicators), re.IGNORECASE | re.MULTILINE
        )

    def find_topic_boundaries(self, text: str) -> List[int]:
        """Find potential topic boundaries in text."""
        boundaries = []

        # Find matches
        for match in self.topic_pattern.finditer(text):
            boundaries.append(match.start())

        # Add paragraph boundaries as weak topic boundaries
        para_boundaries = [m.start() for m in re.finditer(r"\n\s*\n", text)]
        boundaries.extend(para_boundaries)

        # Sort and deduplicate
        boundaries = sorted(set(boundaries))

        return boundaries

    def calculate_coherence_score(self, text1: str, text2: str) -> float:
        """Calculate semantic coherence between two text segments."""
        # Simple keyword overlap for now
        words1 = set(re.findall(r"\b\w+\b", text1.lower()))
        words2 = set(re.findall(r"\b\w+\b", text2.lower()))

        if not words1 or not words2:
            return 0.0

        overlap = len(words1 & words2)
        total = len(words1 | words2)

        return overlap / total if total > 0 else 0.0


class ChunkOptimizer:
    """Main chunk optimizer that coordinates different strategies."""

    def __init__(self, config: Optional[ChunkingConfig] = None):
        self.config = config or ChunkingConfig()
        self.token_estimator = TokenEstimator(self.config.token_estimation_factor)
        self.sentence_splitter = SentenceSplitter()
        self.paragraph_splitter = ParagraphSplitter()
        self.semantic_analyzer = SemanticAnalyzer()

    def calculate_optimal_chunk_size(
        self, content: str, structure: Optional[DocumentStructure] = None
    ) -> int:
        """Calculate optimal chunk size based on content characteristics."""
        total_tokens = self.token_estimator.estimate_tokens(content)

        # Base calculation
        if total_tokens < self.config.max_chunk_size:
            return total_tokens

        # Adjust based on structure
        if structure and structure.sections:
            avg_section_size = total_tokens / len(structure.sections)
            if avg_section_size < self.config.max_chunk_size:
                return int(avg_section_size)

        # Consider semantic boundaries
        boundaries = self.semantic_analyzer.find_topic_boundaries(content)
        if boundaries:
            avg_segment_size = total_tokens / (len(boundaries) + 1)
            if self.config.min_chunk_size <= avg_segment_size <= self.config.max_chunk_size:
                return int(avg_segment_size)

        return self.config.max_chunk_size

    def find_optimal_split_points(self, text: str, target_size: int) -> List[int]:
        """Find optimal points to split text."""
        split_points = []
        current_pos = 0

        while current_pos < len(text):
            # Look for split point around target size
            search_start = max(0, current_pos + int(target_size * 0.8))
            search_end = min(len(text), current_pos + int(target_size * 1.2))

            if search_end >= len(text):
                break

            # Find best split point in range
            best_pos = self._find_best_split_in_range(text, search_start, search_end, current_pos)

            if best_pos > current_pos:
                split_points.append(best_pos)
                current_pos = best_pos
            else:
                # Force split if no good point found
                split_points.append(search_end)
                current_pos = search_end

        return split_points

    def _find_best_split_in_range(self, text: str, start: int, end: int, last_pos: int) -> int:
        """Find the best split point in a given range."""
        # Priority order: paragraph > sentence > word > character

        # Look for paragraph boundary
        para_match = re.search(r"\n\s*\n", text[start:end])
        if para_match:
            # Return position in the middle of the paragraph break
            return start + para_match.start() + 1

        # Look for sentence boundary
        sentence_match = re.search(r"[.!?]\s+", text[start:end])
        if sentence_match:
            return start + sentence_match.end()

        # Look for word boundary
        word_match = re.search(r"\s+", text[start:end])
        if word_match:
            return start + word_match.start()

        # Default to end
        return end

    def balance_chunk_sizes(self, chunks: List[str], min_size: int, max_size: int) -> List[str]:
        """Balance chunk sizes by merging small chunks and splitting large ones."""
        balanced = []
        current = ""

        for chunk in chunks:
            chunk_tokens = self.token_estimator.estimate_tokens(chunk)
            current_tokens = self.token_estimator.estimate_tokens(current)

            if chunk_tokens > max_size:
                # Split large chunk
                if current:
                    balanced.append(current)
                    current = ""

                # Split the large chunk
                sub_chunks = self._split_large_chunk(chunk, max_size)
                balanced.extend(sub_chunks[:-1])
                current = sub_chunks[-1] if sub_chunks else ""

            elif current_tokens + chunk_tokens < max_size:
                # Merge with current
                if current:
                    current = current + "\n\n" + chunk
                else:
                    current = chunk
            else:
                # Current is good size, start new
                if current:
                    balanced.append(current)
                current = chunk

        if current:
            balanced.append(current)

        return balanced

    def _split_large_chunk(self, chunk: str, max_size: int) -> List[str]:
        """Split a large chunk into smaller pieces."""
        result = []
        sentences = self.sentence_splitter.split_sentences(chunk)

        current = ""
        for sentence in sentences:
            if self.token_estimator.estimate_tokens(current + sentence) < max_size:
                if current:
                    current = current + " " + sentence
                else:
                    current = sentence
            else:
                if current:
                    result.append(current)
                current = sentence

        if current:
            result.append(current)

        return result

    def maintain_semantic_coherence(self, chunks: List[str]) -> List[str]:
        """Adjust chunks to maintain semantic coherence."""
        if len(chunks) < 2:
            return chunks

        adjusted = [chunks[0]]

        for i in range(1, len(chunks)):
            prev_chunk = adjusted[-1]
            curr_chunk = chunks[i]

            # Check coherence
            coherence = self.semantic_analyzer.calculate_coherence_score(
                prev_chunk[-200:], curr_chunk[:200]
            )

            if coherence < self.config.semantic_threshold:
                # Try to improve coherence by adjusting boundary
                improved = self._improve_coherence(prev_chunk, curr_chunk)
                if improved:
                    adjusted[-1] = improved[0]
                    adjusted.append(improved[1])
                else:
                    adjusted.append(curr_chunk)
            else:
                adjusted.append(curr_chunk)

        return adjusted

    def _improve_coherence(self, chunk1: str, chunk2: str) -> Optional[Tuple[str, str]]:
        """Try to improve coherence between two chunks by adjusting boundary."""
        # Look for better split point near boundary
        overlap_size = min(200, len(chunk1) // 4, len(chunk2) // 4)

        tail = chunk1[-overlap_size:]
        head = chunk2[:overlap_size]
        combined = tail + head

        # Find better split point
        split_match = re.search(r"[.!?]\s+", combined)
        if split_match:
            split_pos = len(chunk1) - overlap_size + split_match.end()
            new_chunk1 = chunk1[:split_pos]
            new_chunk2 = chunk1[split_pos:] + chunk2
            return (new_chunk1, new_chunk2)

        return None


# Strategy implementations


class FixedSizeChunkingStrategy(IChunkStrategy):
    """Fixed size chunking strategy."""

    def __init__(self, optimizer: ChunkOptimizer):
        self.optimizer = optimizer

    def chunk(self, content: str, structure: DocumentStructure) -> List[DocumentChunk]:
        """Create fixed-size chunks."""
        chunks = []
        chunk_size = self.optimizer.config.max_chunk_size

        # Calculate character positions for chunks
        char_chunk_size = int(chunk_size / self.optimizer.config.token_estimation_factor)

        # Calculate overlap in characters
        char_overlap_size = int(
            self.optimizer.config.overlap_size / self.optimizer.config.token_estimation_factor
        )

        # Use step size instead of subtracting overlap from chunk size
        step_size = max(1, char_chunk_size - char_overlap_size)

        for i in range(0, len(content), step_size):
            end = min(i + char_chunk_size, len(content))
            chunk_content = content[i:end]

            if chunk_content.strip():
                chunk = self._create_chunk(
                    chunk_content, i, structure, len(chunks), ChunkType.UNKNOWN
                )
                chunks.append(chunk)

            # Stop if we've reached the end
            if end >= len(content):
                break

        return chunks

    def validate_chunk(self, chunk: DocumentChunk) -> bool:
        """Validate chunk meets criteria."""
        tokens = self.optimizer.token_estimator.estimate_tokens(chunk.content)
        return (
            self.optimizer.config.min_chunk_size <= tokens <= self.optimizer.config.max_chunk_size
        )

    def merge_small_chunks(self, chunks: List[DocumentChunk]) -> List[DocumentChunk]:
        """Merge chunks that are too small."""
        if len(chunks) < 2:
            return chunks

        merged = []
        current = chunks[0]

        for chunk in chunks[1:]:
            current_tokens = self.optimizer.token_estimator.estimate_tokens(current.content)
            chunk_tokens = self.optimizer.token_estimator.estimate_tokens(chunk.content)

            if (
                current_tokens < self.optimizer.config.min_chunk_size
                and current_tokens + chunk_tokens <= self.optimizer.config.max_chunk_size
            ):
                # Merge chunks
                current.content = current.content + "\n\n" + chunk.content
                current.metadata.line_end = chunk.metadata.line_end
            else:
                merged.append(current)
                current = chunk

        merged.append(current)
        return merged

    def _create_chunk(
        self,
        content: str,
        position: int,
        structure: DocumentStructure,
        index: int,
        chunk_type: ChunkType,
    ) -> DocumentChunk:
        """Create a document chunk."""
        # Find section context
        section_hierarchy = []
        if structure.sections:
            for section in structure.sections:
                if section.start_line <= position <= section.end_line:
                    section_hierarchy = section.get_hierarchy_path()
                    break

        metadata = ChunkMetadata(
            document_path=structure.metadata.get("path", ""),
            section_hierarchy=section_hierarchy,
            chunk_index=index,
            total_chunks=0,  # Will be updated later
            has_code=bool(re.search(r"```|`[^`]+`", content)),
            word_count=len(content.split()),
            line_start=content[:position].count("\n"),
            line_end=content[: position + len(content)].count("\n"),
        )

        return DocumentChunk(
            id=str(uuid.uuid4()), content=content, type=chunk_type, metadata=metadata
        )


class SentenceBasedChunkingStrategy(IChunkStrategy):
    """Sentence-based chunking strategy."""

    def __init__(self, optimizer: ChunkOptimizer):
        self.optimizer = optimizer

    def chunk(self, content: str, structure: DocumentStructure) -> List[DocumentChunk]:
        """Create sentence-based chunks."""
        sentences = self.optimizer.sentence_splitter.split_sentences(content)

        chunks = []
        current_sentences = []
        current_tokens = 0

        for sentence in sentences:
            sentence_tokens = self.optimizer.token_estimator.estimate_tokens(sentence)

            if (
                current_tokens + sentence_tokens > self.optimizer.config.max_chunk_size
                and current_sentences
            ):
                # Create chunk
                chunk_content = " ".join(current_sentences)
                chunk = self._create_chunk(chunk_content, chunks, structure)
                chunks.append(chunk)

                # Start new chunk with overlap
                overlap_sentences = self._get_overlap_sentences(current_sentences)
                current_sentences = overlap_sentences + [sentence]
                current_tokens = sum(
                    self.optimizer.token_estimator.estimate_tokens(s) for s in current_sentences
                )
            else:
                current_sentences.append(sentence)
                current_tokens += sentence_tokens

        # Last chunk
        if current_sentences:
            chunk_content = " ".join(current_sentences)
            chunk = self._create_chunk(chunk_content, chunks, structure)
            chunks.append(chunk)

        return chunks

    def validate_chunk(self, chunk: DocumentChunk) -> bool:
        """Validate chunk meets criteria."""
        tokens = self.optimizer.token_estimator.estimate_tokens(chunk.content)
        # Check if chunk ends with complete sentence
        ends_with_sentence = chunk.content.rstrip().endswith((".", "!", "?"))
        return (
            self.optimizer.config.min_chunk_size <= tokens <= self.optimizer.config.max_chunk_size
            and ends_with_sentence
        )

    def merge_small_chunks(self, chunks: List[DocumentChunk]) -> List[DocumentChunk]:
        """Merge chunks that are too small."""
        merged = []
        i = 0

        while i < len(chunks):
            current = chunks[i]
            tokens = self.optimizer.token_estimator.estimate_tokens(current.content)

            if tokens < self.optimizer.config.min_chunk_size and i + 1 < len(chunks):
                # Try to merge with next chunk
                next_chunk = chunks[i + 1]
                next_tokens = self.optimizer.token_estimator.estimate_tokens(next_chunk.content)

                if tokens + next_tokens <= self.optimizer.config.max_chunk_size:
                    # Merge
                    current.content = current.content + " " + next_chunk.content
                    current.metadata.line_end = next_chunk.metadata.line_end
                    merged.append(current)
                    i += 2
                    continue

            merged.append(current)
            i += 1

        return merged

    def _get_overlap_sentences(self, sentences: List[str]) -> List[str]:
        """Get sentences for overlap context."""
        if not sentences:
            return []

        overlap_tokens = 0
        overlap_sentences = []

        for sentence in reversed(sentences):
            sentence_tokens = self.optimizer.token_estimator.estimate_tokens(sentence)
            if overlap_tokens + sentence_tokens <= self.optimizer.config.overlap_size:
                overlap_sentences.insert(0, sentence)
                overlap_tokens += sentence_tokens
            else:
                break

        return overlap_sentences

    def _create_chunk(
        self,
        content: str,
        existing_chunks: List[DocumentChunk],
        structure: DocumentStructure,
    ) -> DocumentChunk:
        """Create a document chunk."""
        metadata = ChunkMetadata(
            document_path=structure.metadata.get("path", ""),
            section_hierarchy=[],
            chunk_index=len(existing_chunks),
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


class ParagraphBasedChunkingStrategy(IChunkStrategy):
    """Paragraph-based chunking strategy."""

    def __init__(self, optimizer: ChunkOptimizer):
        self.optimizer = optimizer

    def chunk(self, content: str, structure: DocumentStructure) -> List[DocumentChunk]:
        """Create paragraph-based chunks."""
        paragraphs = self.optimizer.paragraph_splitter.split_paragraphs(content)

        # Merge short paragraphs
        paragraphs = self.optimizer.paragraph_splitter.merge_short_paragraphs(
            paragraphs,
            self.optimizer.config.min_chunk_size,
            self.optimizer.token_estimator,
        )

        chunks = []
        for i, para in enumerate(paragraphs):
            chunk = self._create_chunk(para, i, structure)
            chunks.append(chunk)

        return chunks

    def validate_chunk(self, chunk: DocumentChunk) -> bool:
        """Validate chunk meets criteria."""
        tokens = self.optimizer.token_estimator.estimate_tokens(chunk.content)
        return (
            self.optimizer.config.min_chunk_size <= tokens <= self.optimizer.config.max_chunk_size
        )

    def merge_small_chunks(self, chunks: List[DocumentChunk]) -> List[DocumentChunk]:
        """Merge chunks that are too small."""
        return chunks  # Already handled in split phase

    def _create_chunk(
        self, content: str, index: int, structure: DocumentStructure
    ) -> DocumentChunk:
        """Create a document chunk."""
        metadata = ChunkMetadata(
            document_path=structure.metadata.get("path", ""),
            section_hierarchy=[],
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


class SemanticBasedChunkingStrategy(IChunkStrategy):
    """Semantic-based chunking strategy using topic boundaries."""

    def __init__(self, optimizer: ChunkOptimizer):
        self.optimizer = optimizer

    def chunk(self, content: str, structure: DocumentStructure) -> List[DocumentChunk]:
        """Create semantic-based chunks."""
        # Find topic boundaries
        boundaries = self.optimizer.semantic_analyzer.find_topic_boundaries(content)

        if not boundaries:
            # Fall back to paragraph-based
            return ParagraphBasedChunkingStrategy(self.optimizer).chunk(content, structure)

        chunks = []
        start = 0

        for boundary in boundaries:
            if boundary > start:
                segment = content[start:boundary].strip()
                if segment:
                    # Check size and split if needed
                    sub_chunks = self._split_if_needed(segment)
                    for sub_chunk in sub_chunks:
                        chunk = self._create_chunk(sub_chunk, len(chunks), structure)
                        chunks.append(chunk)

                start = boundary

        # Last segment
        if start < len(content):
            segment = content[start:].strip()
            if segment:
                sub_chunks = self._split_if_needed(segment)
                for sub_chunk in sub_chunks:
                    chunk = self._create_chunk(sub_chunk, len(chunks), structure)
                    chunks.append(chunk)

        return chunks

    def validate_chunk(self, chunk: DocumentChunk) -> bool:
        """Validate chunk meets criteria."""
        tokens = self.optimizer.token_estimator.estimate_tokens(chunk.content)
        return tokens >= self.optimizer.config.min_chunk_size

    def merge_small_chunks(self, chunks: List[DocumentChunk]) -> List[DocumentChunk]:
        """Merge chunks that are too small."""
        if len(chunks) < 2:
            return chunks

        merged = []
        i = 0

        while i < len(chunks):
            current = chunks[i]
            tokens = self.optimizer.token_estimator.estimate_tokens(current.content)

            if tokens < self.optimizer.config.min_chunk_size and i + 1 < len(chunks):
                # Check semantic coherence with next chunk
                next_chunk = chunks[i + 1]
                coherence = self.optimizer.semantic_analyzer.calculate_coherence_score(
                    current.content, next_chunk.content
                )

                if coherence > self.optimizer.config.semantic_threshold:
                    # Merge
                    current.content = current.content + "\n\n" + next_chunk.content
                    current.metadata.line_end = next_chunk.metadata.line_end
                    merged.append(current)
                    i += 2
                    continue

            merged.append(current)
            i += 1

        return merged

    def _split_if_needed(self, segment: str) -> List[str]:
        """Split segment if it's too large."""
        tokens = self.optimizer.token_estimator.estimate_tokens(segment)

        if tokens <= self.optimizer.config.max_chunk_size:
            return [segment]

        # Use sentence splitter for large segments
        return self.optimizer._split_large_chunk(segment, self.optimizer.config.max_chunk_size)

    def _create_chunk(
        self, content: str, index: int, structure: DocumentStructure
    ) -> DocumentChunk:
        """Create a document chunk."""
        # Determine chunk type based on content
        chunk_type = ChunkType.UNKNOWN
        if content.strip().startswith("#"):
            chunk_type = ChunkType.HEADING
        elif re.search(r"```[\s\S]*?```", content):
            chunk_type = ChunkType.CODE_BLOCK
        elif re.search(r"^[-*+]\s+", content, re.MULTILINE):
            chunk_type = ChunkType.LIST
        else:
            chunk_type = ChunkType.PARAGRAPH

        metadata = ChunkMetadata(
            document_path=structure.metadata.get("path", ""),
            section_hierarchy=[],
            chunk_index=index,
            total_chunks=0,
            has_code=bool(re.search(r"```|`[^`]+`", content)),
            word_count=len(content.split()),
        )

        return DocumentChunk(
            id=str(uuid.uuid4()), content=content, type=chunk_type, metadata=metadata
        )


class HybridChunkingStrategy(IChunkStrategy):
    """Hybrid chunking strategy that combines multiple approaches."""

    def __init__(self, optimizer: ChunkOptimizer):
        self.optimizer = optimizer
        self.strategies = {
            "semantic": SemanticBasedChunkingStrategy(optimizer),
            "paragraph": ParagraphBasedChunkingStrategy(optimizer),
            "sentence": SentenceBasedChunkingStrategy(optimizer),
        }

    def chunk(self, content: str, structure: DocumentStructure) -> List[DocumentChunk]:
        """Create chunks using hybrid approach."""
        # First try semantic chunking if we have structure
        if structure and structure.sections:
            chunks = self._chunk_by_structure(content, structure)
        else:
            # Use semantic strategy
            chunks = self.strategies["semantic"].chunk(content, structure)

        # Validate and adjust chunks
        chunks = self._validate_and_adjust(chunks)

        # Maintain coherence
        chunk_contents = [c.content for c in chunks]
        adjusted_contents = self.optimizer.maintain_semantic_coherence(chunk_contents)

        # Update chunks with adjusted content
        for i, content in enumerate(adjusted_contents):
            if i < len(chunks):
                chunks[i].content = content

        # Update total chunks count
        for i, chunk in enumerate(chunks):
            chunk.metadata.total_chunks = len(chunks)
            chunk.metadata.chunk_index = i

        return chunks

    def validate_chunk(self, chunk: DocumentChunk) -> bool:
        """Validate chunk meets criteria."""
        tokens = self.optimizer.token_estimator.estimate_tokens(chunk.content)
        return (
            self.optimizer.config.min_chunk_size <= tokens <= self.optimizer.config.max_chunk_size
        )

    def merge_small_chunks(self, chunks: List[DocumentChunk]) -> List[DocumentChunk]:
        """Merge chunks that are too small."""
        # Use semantic strategy's merge
        return self.strategies["semantic"].merge_small_chunks(chunks)

    def _chunk_by_structure(
        self, content: str, structure: DocumentStructure
    ) -> List[DocumentChunk]:
        """Create chunks based on document structure."""
        chunks = []

        def process_section(section: Section, parent_hierarchy: List[str]):
            hierarchy = parent_hierarchy + [section.heading]

            # Create chunk for section content
            if section.content.strip():
                tokens = self.optimizer.token_estimator.estimate_tokens(section.content)

                if tokens > self.optimizer.config.max_chunk_size:
                    # Split large section
                    sub_chunks = self.optimizer._split_large_chunk(
                        section.content, self.optimizer.config.max_chunk_size
                    )

                    for i, sub_content in enumerate(sub_chunks):
                        chunk = self._create_structured_chunk(
                            sub_content, hierarchy, len(chunks), structure
                        )
                        chunks.append(chunk)
                else:
                    chunk = self._create_structured_chunk(
                        section.content, hierarchy, len(chunks), structure
                    )
                    chunks.append(chunk)

            # Process children
            for child in section.children:
                process_section(child, hierarchy)

        # Process all top-level sections
        if structure.outline:
            process_section(structure.outline, [])
        else:
            for section in structure.sections:
                process_section(section, [])

        return chunks

    def _create_structured_chunk(
        self,
        content: str,
        hierarchy: List[str],
        index: int,
        structure: DocumentStructure,
    ) -> DocumentChunk:
        """Create a chunk with structure information."""
        metadata = ChunkMetadata(
            document_path=structure.metadata.get("path", ""),
            section_hierarchy=hierarchy,
            chunk_index=index,
            total_chunks=0,
            has_code=bool(re.search(r"```|`[^`]+`", content)),
            word_count=len(content.split()),
        )

        # Determine type
        chunk_type = ChunkType.PARAGRAPH
        if hierarchy and content.strip().startswith("#"):
            chunk_type = ChunkType.HEADING

        return DocumentChunk(
            id=str(uuid.uuid4()), content=content, type=chunk_type, metadata=metadata
        )

    def _validate_and_adjust(self, chunks: List[DocumentChunk]) -> List[DocumentChunk]:
        """Validate chunks and adjust as needed."""
        validated = []

        for chunk in chunks:
            if self.validate_chunk(chunk):
                validated.append(chunk)
            else:
                tokens = self.optimizer.token_estimator.estimate_tokens(chunk.content)
                if tokens > self.optimizer.config.max_chunk_size:
                    # Split large chunk
                    sub_chunks = self.optimizer._split_large_chunk(
                        chunk.content, self.optimizer.config.max_chunk_size
                    )
                    for sub_content in sub_chunks:
                        new_chunk = DocumentChunk(
                            id=str(uuid.uuid4()),
                            content=sub_content,
                            type=chunk.type,
                            metadata=chunk.metadata,
                        )
                        validated.append(new_chunk)
                else:
                    # Keep small chunk for now, will be merged later
                    validated.append(chunk)

        # Merge small chunks
        return self.merge_small_chunks(validated)


def create_chunk_optimizer(
    strategy: ChunkingStrategy = ChunkingStrategy.HYBRID,
    config: Optional[ChunkingConfig] = None,
) -> Tuple[ChunkOptimizer, IChunkStrategy]:
    """Factory function to create chunk optimizer with specified strategy."""
    if config:
        config.strategy = strategy
    else:
        config = ChunkingConfig(strategy=strategy)

    optimizer = ChunkOptimizer(config)

    strategy_map = {
        ChunkingStrategy.FIXED_SIZE: FixedSizeChunkingStrategy,
        ChunkingStrategy.SENTENCE_BASED: SentenceBasedChunkingStrategy,
        ChunkingStrategy.PARAGRAPH_BASED: ParagraphBasedChunkingStrategy,
        ChunkingStrategy.SEMANTIC_BASED: SemanticBasedChunkingStrategy,
        ChunkingStrategy.HYBRID: HybridChunkingStrategy,
    }

    strategy_class = strategy_map.get(strategy, HybridChunkingStrategy)
    strategy_instance = strategy_class(optimizer)

    return optimizer, strategy_instance
