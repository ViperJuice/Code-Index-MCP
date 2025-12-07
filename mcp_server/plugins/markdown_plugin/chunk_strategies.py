"""
Markdown-specific chunking strategies for semantic search optimization.
"""

import hashlib
import logging
import os
import re
from typing import Any, Dict, List, Optional

from mcp_server.document_processing import (
    ChunkMetadata,
    ChunkType,
    DocumentChunk,
)
from mcp_server.document_processing.chunk_optimizer import TokenEstimator

logger = logging.getLogger(__name__)


class MarkdownChunkStrategy:
    """Chunking strategies optimized for Markdown documents."""

    def __init__(
        self,
        max_chunk_size: Optional[int] = None,
        min_chunk_size: Optional[int] = None,
        overlap_size: Optional[int] = None,
        prefer_semantic_boundaries: bool = True,
        adaptive_sizing: bool = True,
    ):
        """
        Initialize the chunking strategy.

        Args:
            max_chunk_size: Maximum size of a chunk in tokens (default from env or 500)
            min_chunk_size: Minimum size of a chunk in tokens (default from env or 100)
            overlap_size: Number of tokens to overlap between chunks (default from env or 50)
            prefer_semantic_boundaries: Whether to prefer semantic boundaries
            adaptive_sizing: Enable adaptive chunk sizing based on document size
        """
        # Get settings from environment variables with defaults
        self.max_chunk_tokens = max_chunk_size or int(os.getenv("MARKDOWN_MAX_CHUNK_TOKENS", "500"))
        self.min_chunk_tokens = min_chunk_size or int(os.getenv("MARKDOWN_MIN_CHUNK_TOKENS", "100"))
        self.overlap_tokens = overlap_size or int(os.getenv("MARKDOWN_OVERLAP_TOKENS", "50"))
        self.prefer_semantic_boundaries = prefer_semantic_boundaries
        self.adaptive_sizing = adaptive_sizing

        # Initialize token estimator
        self.token_estimator = TokenEstimator()

        # Convert token limits to approximate character limits for compatibility
        # These are used as rough guides, actual limits are enforced in tokens
        self.max_chunk_size = int(self.max_chunk_tokens / self.token_estimator.estimation_factor)
        self.min_chunk_size = int(self.min_chunk_tokens / self.token_estimator.estimation_factor)
        self.overlap_size = int(self.overlap_tokens / self.token_estimator.estimation_factor)

    def create_chunks(
        self,
        content: str,
        ast: Dict[str, Any],
        sections: List[Dict[str, Any]],
        file_path: str,
    ) -> List[DocumentChunk]:
        """Create chunks from document content."""
        # Apply adaptive sizing if enabled
        if self.adaptive_sizing:
            self._adjust_chunk_size_for_document(content)

        if self.prefer_semantic_boundaries:
            return self._create_semantic_chunks(content, ast, sections, file_path)
        else:
            return self._create_sliding_window_chunks(content, file_path)

    def _adjust_chunk_size_for_document(self, content: str):
        """Adjust chunk size based on document characteristics."""
        total_tokens = self.token_estimator.estimate_tokens(content)

        # For small documents (< 2000 tokens), use smaller chunks
        if total_tokens < 2000:
            self.max_chunk_tokens = min(self.max_chunk_tokens, 300)
            self.min_chunk_tokens = min(self.min_chunk_tokens, 50)
        # For medium documents (2000-10000 tokens), use default sizes
        elif total_tokens < 10000:
            # Keep defaults
            pass
        # For large documents (> 10000 tokens), use larger chunks
        else:
            self.max_chunk_tokens = min(self.max_chunk_tokens * 2, 1000)
            self.min_chunk_tokens = min(self.min_chunk_tokens * 2, 200)

        # Update character limits
        self.max_chunk_size = int(self.max_chunk_tokens / self.token_estimator.estimation_factor)
        self.min_chunk_size = int(self.min_chunk_tokens / self.token_estimator.estimation_factor)
        self.overlap_size = int(self.overlap_tokens / self.token_estimator.estimation_factor)

        logger.debug(
            f"Adjusted chunk sizes - max_tokens: {self.max_chunk_tokens}, "
            f"min_tokens: {self.min_chunk_tokens}, doc_tokens: {total_tokens}"
        )

    def _create_semantic_chunks(
        self,
        content: str,
        ast: Dict[str, Any],
        sections: List[Dict[str, Any]],
        file_path: str,
    ) -> List[DocumentChunk]:
        """Create chunks based on semantic boundaries."""
        chunks = []
        content_lines = content.split("\n")
        _ = 0  # Will be updated after creating all chunks

        # Flatten sections for processing
        from mcp_server.plugins.markdown_plugin.section_extractor import (
            SectionExtractor,
        )

        extractor = SectionExtractor()
        flat_sections = extractor.get_all_sections_flat(sections)

        # Process each section
        for section in flat_sections:
            section_chunks = self._chunk_section(
                section, content_lines, ast, file_path, len(chunks)
            )
            chunks.extend(section_chunks)

        # Handle content not in any section
        orphan_chunks = self._chunk_orphan_content(
            ast, content_lines, sections, file_path, len(chunks)
        )
        chunks.extend(orphan_chunks)

        # Update total chunks count
        for chunk in chunks:
            chunk.metadata.total_chunks = len(chunks)

        # Add overlap between chunks
        if self.overlap_size > 0:
            chunks = self._add_chunk_overlap(chunks)

        return chunks

    def _chunk_section(
        self,
        section: Dict[str, Any],
        content_lines: List[str],
        ast: Dict[str, Any],
        file_path: str,
        chunk_index_start: int,
    ) -> List[DocumentChunk]:
        """Create chunks from a single section."""
        chunks = []
        section_content = section.get("content", "")

        if not section_content:
            return chunks

        # Extract section hierarchy
        section_hierarchy = [section["title"]]
        if "parent" in section and section["parent"]:
            section_hierarchy.insert(0, section["parent"])

        # Check if section is small enough to be a single chunk (based on tokens)
        section_tokens = self.token_estimator.estimate_tokens(section_content)
        if section_tokens <= self.max_chunk_tokens:
            chunk_id = self._generate_chunk_id(file_path, chunk_index_start + len(chunks))

            metadata = ChunkMetadata(
                document_path=file_path,
                section_hierarchy=section_hierarchy,
                chunk_index=chunk_index_start + len(chunks),
                total_chunks=0,  # Will be updated later
                has_code=section["metadata"]["code_blocks"] > 0,
                language="markdown",
                keywords=self._extract_keywords(section_content),
                word_count=len(section_content.split()),
                line_start=section["start_line"],
                line_end=section.get("end_line", section["start_line"]),
            )

            chunk = DocumentChunk(
                id=chunk_id,
                content=section_content,
                type=(ChunkType.HEADING if section["level"] <= 2 else ChunkType.PARAGRAPH),
                metadata=metadata,
            )
            chunks.append(chunk)
        else:
            # Split large sections
            sub_chunks = self._split_large_section(
                section,
                content_lines,
                file_path,
                section_hierarchy,
                chunk_index_start + len(chunks),
            )
            chunks.extend(sub_chunks)

        # Don't process subsections since we're using flat list
        return chunks

    def _generate_chunk_id(self, file_path: str, chunk_index: int) -> str:
        """Generate a unique ID for a chunk."""
        hash_input = f"{file_path}:{chunk_index}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]

    def _extract_keywords(self, content: str) -> List[str]:
        """Extract keywords from content."""
        # Simple keyword extraction - can be enhanced
        words = re.findall(r"\b\w+\b", content.lower())
        # Filter out common words
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "from",
            "as",
            "is",
            "was",
            "are",
            "been",
        }
        keywords = [w for w in words if len(w) > 3 and w not in stop_words]
        # Get unique keywords
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique_keywords.append(kw)
        return unique_keywords[:10]  # Top 10 keywords

    def _split_large_section(
        self,
        section: Dict[str, Any],
        content_lines: List[str],
        file_path: str,
        section_hierarchy: List[str],
        chunk_index_start: int,
    ) -> List[DocumentChunk]:
        """Split a large section into smaller chunks."""
        chunks = []
        section_content = section.get("content", "")

        # Try to split by paragraphs first
        paragraphs = self._split_by_paragraphs(section_content)

        current_chunk_content = []
        current_chunk_tokens = 0
        chunk_start_line = section["start_line"]

        for paragraph in paragraphs:
            paragraph_tokens = self.token_estimator.estimate_tokens(paragraph)

            # If paragraph itself is too large, split it further
            if paragraph_tokens > self.max_chunk_tokens:
                # Save current chunk first if it has content
                if current_chunk_content and current_chunk_tokens >= self.min_chunk_tokens:
                    chunk_content = "\n\n".join(current_chunk_content)
                    chunk_id = self._generate_chunk_id(file_path, chunk_index_start + len(chunks))

                    metadata = ChunkMetadata(
                        document_path=file_path,
                        section_hierarchy=section_hierarchy,
                        chunk_index=chunk_index_start + len(chunks),
                        total_chunks=0,  # Will be updated later
                        has_code=bool(re.search(r"```[\s\S]*?```", chunk_content)),
                        language="markdown",
                        keywords=self._extract_keywords(chunk_content),
                        word_count=len(chunk_content.split()),
                        line_start=chunk_start_line,
                        line_end=chunk_start_line + len(chunk_content.split("\n")),
                    )

                    chunk = DocumentChunk(
                        id=chunk_id,
                        content=chunk_content,
                        type=ChunkType.PARAGRAPH,
                        metadata=metadata,
                    )
                    chunks.append(chunk)
                    current_chunk_content = []
                    current_chunk_tokens = 0

                # Split the large paragraph by sentences or words
                paragraph_chunks = self._split_paragraph_by_tokens(paragraph, self.max_chunk_tokens)
                for para_chunk in paragraph_chunks:
                    chunk_id = self._generate_chunk_id(file_path, chunk_index_start + len(chunks))

                    metadata = ChunkMetadata(
                        document_path=file_path,
                        section_hierarchy=section_hierarchy,
                        chunk_index=chunk_index_start + len(chunks),
                        total_chunks=0,  # Will be updated later
                        has_code=bool(re.search(r"```[\s\S]*?```", para_chunk)),
                        language="markdown",
                        keywords=self._extract_keywords(para_chunk),
                        word_count=len(para_chunk.split()),
                        line_start=chunk_start_line,
                        line_end=chunk_start_line + len(para_chunk.split("\n")),
                    )

                    chunk = DocumentChunk(
                        id=chunk_id,
                        content=para_chunk,
                        type=ChunkType.PARAGRAPH,
                        metadata=metadata,
                    )
                    chunks.append(chunk)
                    chunk_start_line = metadata.line_end + 1

                continue

            # If adding this paragraph would exceed max size
            if current_chunk_tokens + paragraph_tokens > self.max_chunk_tokens:
                # Save current chunk if it meets minimum size
                if current_chunk_tokens >= self.min_chunk_tokens:
                    chunk_content = "\n\n".join(current_chunk_content)
                    chunk_id = self._generate_chunk_id(file_path, chunk_index_start + len(chunks))

                    metadata = ChunkMetadata(
                        document_path=file_path,
                        section_hierarchy=section_hierarchy,
                        chunk_index=chunk_index_start + len(chunks),
                        total_chunks=0,  # Will be updated later
                        has_code=bool(re.search(r"```[\s\S]*?```", chunk_content)),
                        language="markdown",
                        keywords=self._extract_keywords(chunk_content),
                        word_count=len(chunk_content.split()),
                        line_start=chunk_start_line,
                        line_end=chunk_start_line + len(chunk_content.split("\n")),
                    )

                    chunk = DocumentChunk(
                        id=chunk_id,
                        content=chunk_content,
                        type=ChunkType.PARAGRAPH,
                        metadata=metadata,
                    )
                    chunks.append(chunk)

                    # Start new chunk
                    current_chunk_content = [paragraph]
                    current_chunk_tokens = paragraph_tokens
                    chunk_start_line = metadata.line_end + 1
                else:
                    # Add to current chunk anyway (to meet minimum size)
                    current_chunk_content.append(paragraph)
                    current_chunk_tokens += paragraph_tokens
            else:
                # Add to current chunk
                current_chunk_content.append(paragraph)
                current_chunk_tokens += paragraph_tokens

        # Save final chunk
        if current_chunk_content:
            chunk_content = "\n\n".join(current_chunk_content)
            chunk_id = self._generate_chunk_id(file_path, chunk_index_start + len(chunks))

            metadata = ChunkMetadata(
                document_path=file_path,
                section_hierarchy=section_hierarchy,
                chunk_index=chunk_index_start + len(chunks),
                total_chunks=0,  # Will be updated later
                has_code=bool(re.search(r"```[\s\S]*?```", chunk_content)),
                language="markdown",
                keywords=self._extract_keywords(chunk_content),
                word_count=len(chunk_content.split()),
                line_start=chunk_start_line,
                line_end=section.get("end_line", chunk_start_line + len(chunk_content.split("\n"))),
            )

            chunk = DocumentChunk(
                id=chunk_id,
                content=chunk_content,
                type=ChunkType.PARAGRAPH,
                metadata=metadata,
            )
            chunks.append(chunk)

        return chunks

    def _chunk_orphan_content(
        self,
        ast: Dict[str, Any],
        content_lines: List[str],
        sections: List[Dict[str, Any]],
        file_path: str,
        chunk_index_start: int,
    ) -> List[DocumentChunk]:
        """Create chunks for content not in any section."""
        chunks = []

        # Find lines not covered by sections
        section_lines = set()
        for section in self._flatten_sections(sections):
            start = section["start_line"]
            end = section.get("end_line", len(content_lines))
            section_lines.update(range(start, end))

        # Group orphan content
        orphan_groups = []
        current_group = []

        for i, line in enumerate(content_lines):
            if i not in section_lines:
                current_group.append((i, line))
            elif current_group:
                orphan_groups.append(current_group)
                current_group = []

        if current_group:
            orphan_groups.append(current_group)

        # Create chunks from orphan groups
        for group in orphan_groups:
            if not group:
                continue

            start_line = group[0][0]
            end_line = group[-1][0]
            content = "\n".join(line for _, line in group)

            content_tokens = self.token_estimator.estimate_tokens(content)
            if content_tokens >= self.min_chunk_tokens:
                chunk_id = self._generate_chunk_id(file_path, chunk_index_start + len(chunks))

                metadata = ChunkMetadata(
                    document_path=file_path,
                    section_hierarchy=[],  # No section hierarchy for orphan content
                    chunk_index=chunk_index_start + len(chunks),
                    total_chunks=0,  # Will be updated later
                    has_code=bool(re.search(r"```[\s\S]*?```", content)),
                    language="markdown",
                    keywords=self._extract_keywords(content),
                    word_count=len(content.split()),
                    line_start=start_line,
                    line_end=end_line,
                )

                chunk = DocumentChunk(
                    id=chunk_id,
                    content=content,
                    type=ChunkType.UNKNOWN,
                    metadata=metadata,
                )
                chunks.append(chunk)

        return chunks

    def _create_sliding_window_chunks(self, content: str, file_path: str) -> List[DocumentChunk]:
        """Create chunks using a sliding window approach."""
        chunks = []
        _ = content.split("\n")

        # Token-based sliding window
        start = 0
        chunk_index = 0

        while start < len(content):
            # Find end position based on token count
            # Start with approximate character position
            approx_end = min(start + self.max_chunk_size, len(content))

            # Adjust to actual token boundary
            end = self._find_token_boundary(content, start, approx_end, self.max_chunk_tokens)

            # Try to find a good break point
            if end < len(content):
                # Look for paragraph break
                break_point = content.rfind("\n\n", start, end)
                if break_point > start:
                    end = break_point
                else:
                    # Look for sentence break
                    break_point = content.rfind(". ", start, end)
                    if break_point > start:
                        end = break_point + 1

            chunk_content = content[start:end].strip()

            chunk_tokens = self.token_estimator.estimate_tokens(chunk_content)
            if chunk_tokens >= self.min_chunk_tokens:
                # Calculate line numbers
                start_line = content[:start].count("\n")
                end_line = content[:end].count("\n")

                chunk_id = self._generate_chunk_id(file_path, chunk_index)

                metadata = ChunkMetadata(
                    document_path=file_path,
                    section_hierarchy=[],
                    chunk_index=chunk_index,
                    total_chunks=0,  # Will be updated later
                    has_code=bool(re.search(r"```[\s\S]*?```", chunk_content)),
                    language="markdown",
                    keywords=self._extract_keywords(chunk_content),
                    word_count=len(chunk_content.split()),
                    line_start=start_line,
                    line_end=end_line,
                )

                chunk = DocumentChunk(
                    id=chunk_id,
                    content=chunk_content,
                    type=ChunkType.PARAGRAPH,
                    metadata=metadata,
                )
                chunks.append(chunk)
                chunk_index += 1

            # Move start position with token-based overlap
            if end < len(content):
                # Find overlap position based on tokens
                overlap_start = self._find_overlap_start(content, end, self.overlap_tokens)
                start = overlap_start
            else:
                start = end

        # Update total chunks count
        for chunk in chunks:
            chunk.metadata.total_chunks = len(chunks)

        return chunks

    def _add_chunk_overlap(self, chunks: List[DocumentChunk]) -> List[DocumentChunk]:
        """Add overlap between adjacent chunks."""
        if len(chunks) <= 1:
            return chunks

        for i, chunk in enumerate(chunks):
            # Add overlap from previous chunk
            if i > 0:
                prev_chunk = chunks[i - 1]
                overlap_text = self._extract_overlap(
                    prev_chunk.content, self.overlap_size, from_end=True
                )
                if overlap_text:
                    chunk.context_before = overlap_text

            # Add overlap from next chunk
            if i < len(chunks) - 1:
                next_chunk = chunks[i + 1]
                overlap_text = self._extract_overlap(
                    next_chunk.content, self.overlap_size, from_end=False
                )
                if overlap_text:
                    chunk.context_after = overlap_text

        return chunks

    def _extract_overlap(self, content: str, size: int, from_end: bool) -> str:
        """Extract overlap text from content."""
        if from_end:
            # Extract from end
            if len(content) <= size:
                return content

            # Try to find a good break point
            break_point = content.rfind(". ", -size)
            if break_point > 0:
                return content[break_point + 2 :]
            else:
                return content[-size:]
        else:
            # Extract from start
            if len(content) <= size:
                return content

            # Try to find a good break point
            break_point = content.find(". ", 0, size)
            if break_point > 0:
                return content[: break_point + 1]
            else:
                return content[:size]

    def _split_by_paragraphs(self, content: str) -> List[str]:
        """Split content by paragraphs."""
        # Split by double newlines
        paragraphs = re.split(r"\n\s*\n", content)

        # Clean and filter paragraphs
        cleaned_paragraphs = []
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if paragraph:
                cleaned_paragraphs.append(paragraph)

        return cleaned_paragraphs

    def _split_paragraph_by_tokens(self, paragraph: str, max_tokens: int) -> List[str]:
        """Split a large paragraph into smaller chunks based on token count."""
        chunks = []

        # Try to split by sentences first
        sentences = re.split(r"(?<=[.!?])\s+", paragraph)

        current_chunk = []
        current_tokens = 0

        for sentence in sentences:
            sentence_tokens = self.token_estimator.estimate_tokens(sentence)

            if sentence_tokens > max_tokens:
                # If a single sentence is too large, split by words
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                    current_chunk = []
                    current_tokens = 0

                # Split sentence by words
                words = sentence.split()
                word_chunk = []
                word_tokens = 0

                for word in words:
                    # Estimate tokens for word plus space
                    word_with_space = word + " "
                    word_token_count = self.token_estimator.estimate_tokens(word_with_space)

                    if word_tokens + word_token_count > max_tokens and word_chunk:
                        chunks.append(" ".join(word_chunk))
                        word_chunk = [word]
                        word_tokens = word_token_count
                    else:
                        word_chunk.append(word)
                        word_tokens += word_token_count

                if word_chunk:
                    chunks.append(" ".join(word_chunk))

            elif current_tokens + sentence_tokens > max_tokens:
                # Save current chunk and start new one
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                current_chunk = [sentence]
                current_tokens = sentence_tokens
            else:
                # Add to current chunk
                current_chunk.append(sentence)
                current_tokens += sentence_tokens

        # Add remaining chunk
        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks

    def _flatten_sections(self, sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Flatten hierarchical sections into a flat list."""
        flat_sections = []

        def flatten(section_list: List[Dict[str, Any]]):
            for section in section_list:
                flat_sections.append(section)
                flatten(section.get("subsections", []))

        flatten(sections)
        return flat_sections

    def optimize_chunks_for_search(self, chunks: List[DocumentChunk]) -> List[DocumentChunk]:
        """Optimize chunks for semantic search."""
        for chunk in chunks:
            # Create embedding text optimized for search
            embedding_parts = []

            # Add section context
            if chunk.metadata.section_hierarchy:
                section_path = " > ".join(chunk.metadata.section_hierarchy)
                embedding_parts.append(f"Section: {section_path}")

            # Add content
            embedding_parts.append(chunk.content)

            # Add metadata hints
            if chunk.metadata.has_code:
                embedding_parts.append("[Contains code examples]")

            # Add keywords
            if chunk.metadata.keywords:
                embedding_parts.append(f"Keywords: {', '.join(chunk.metadata.keywords[:5])}")

            # Set embedding on the chunk
            chunk.embedding = None  # Will be generated by the semantic indexer

            # Store optimized text in context (can be used for embedding generation)
            if not chunk.context_before:
                chunk.context_before = "\n\n".join(embedding_parts[:1])  # Just section info
            if not chunk.context_after:
                chunk.context_after = "\n\n".join(embedding_parts[2:])  # Metadata hints

        return chunks

    def merge_small_chunks(self, chunks: List[DocumentChunk]) -> List[DocumentChunk]:
        """Merge adjacent small chunks."""
        if len(chunks) <= 1:
            return chunks

        merged_chunks = []
        current_chunk = chunks[0]

        for next_chunk in chunks[1:]:
            # Check if chunks can be merged (based on tokens)
            current_tokens = self.token_estimator.estimate_tokens(current_chunk.content)
            next_tokens = self.token_estimator.estimate_tokens(next_chunk.content)

            if (
                current_tokens < self.min_chunk_tokens
                and current_tokens + next_tokens <= self.max_chunk_tokens
                and next_chunk.metadata.line_start == current_chunk.metadata.line_end + 1
            ):

                # Merge chunks
                current_chunk.content += "\n\n" + next_chunk.content
                current_chunk.metadata.line_end = next_chunk.metadata.line_end
                current_chunk.metadata.word_count = len(current_chunk.content.split())
                current_chunk.metadata.keywords = self._extract_keywords(current_chunk.content)

                # Merge section hierarchies if compatible
                if (
                    current_chunk.metadata.section_hierarchy
                    == next_chunk.metadata.section_hierarchy
                ):
                    # Same section, just update
                    pass
                else:
                    # Different sections, keep the first one's hierarchy
                    pass
            else:
                # Save current chunk and start new one
                merged_chunks.append(current_chunk)
                current_chunk = next_chunk

        # Add final chunk
        merged_chunks.append(current_chunk)

        return merged_chunks

    def _find_token_boundary(
        self, content: str, start: int, approx_end: int, max_tokens: int
    ) -> int:
        """Find the actual end position based on token count."""
        # Binary search for the right position
        left = start
        right = min(approx_end + self.max_chunk_size // 4, len(content))

        best_end = start
        while left <= right:
            mid = (left + right) // 2
            chunk = content[start:mid]
            tokens = self.token_estimator.estimate_tokens(chunk)

            if tokens <= max_tokens:
                best_end = mid
                left = mid + 1
            else:
                right = mid - 1

        # Try to find a good break point near best_end
        if best_end < len(content):
            # Look for paragraph break
            para_break = content.find(
                "\n\n", max(start, best_end - 50), min(len(content), best_end + 50)
            )
            if para_break != -1:
                return para_break

            # Look for sentence break
            sentence_break = content.find(
                ". ", max(start, best_end - 30), min(len(content), best_end + 30)
            )
            if sentence_break != -1:
                return sentence_break + 1

        return best_end

    def _find_overlap_start(self, content: str, end: int, overlap_tokens: int) -> int:
        """Find the start position for the next chunk with token-based overlap."""
        # Estimate the character position for overlap
        overlap_chars = int(overlap_tokens / self.token_estimator.estimation_factor)
        overlap_start = max(0, end - overlap_chars)

        # Adjust to get exact token count
        while overlap_start < end:
            overlap_content = content[overlap_start:end]
            tokens = self.token_estimator.estimate_tokens(overlap_content)

            if tokens >= overlap_tokens:
                break

            # Move back to include more content
            overlap_start = max(0, overlap_start - 10)

        return overlap_start
