"""
Markdown-specific chunking strategies for semantic search optimization.
"""

import re
from typing import List, Dict, Any, Optional, Tuple
import logging
import hashlib

from mcp_server.document_processing import (
    DocumentChunk,
    ChunkType,
    ChunkMetadata,
    Section
)

logger = logging.getLogger(__name__)


class MarkdownChunkStrategy:
    """Chunking strategies optimized for Markdown documents."""
    
    def __init__(self, 
                 max_chunk_size: int = 1000,
                 min_chunk_size: int = 100,
                 overlap_size: int = 50,
                 prefer_semantic_boundaries: bool = True):
        """
        Initialize the chunking strategy.
        
        Args:
            max_chunk_size: Maximum size of a chunk in characters
            min_chunk_size: Minimum size of a chunk in characters
            overlap_size: Number of characters to overlap between chunks
            prefer_semantic_boundaries: Whether to prefer semantic boundaries
        """
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        self.overlap_size = overlap_size
        self.prefer_semantic_boundaries = prefer_semantic_boundaries
        
    def create_chunks(self, 
                     content: str, 
                     ast: Dict[str, Any],
                     sections: List[Dict[str, Any]],
                     file_path: str) -> List[DocumentChunk]:
        """Create chunks from document content."""
        if self.prefer_semantic_boundaries:
            return self._create_semantic_chunks(content, ast, sections, file_path)
        else:
            return self._create_sliding_window_chunks(content, file_path)
            
    def _create_semantic_chunks(self, 
                               content: str,
                               ast: Dict[str, Any],
                               sections: List[Dict[str, Any]],
                               file_path: str) -> List[DocumentChunk]:
        """Create chunks based on semantic boundaries."""
        chunks = []
        content_lines = content.split('\n')
        total_chunks = 0  # Will be updated after creating all chunks
        
        # Flatten sections for processing
        from mcp_server.plugins.markdown_plugin.section_extractor import SectionExtractor
        extractor = SectionExtractor()
        flat_sections = extractor.get_all_sections_flat(sections)
        
        # Process each section
        for section in flat_sections:
            section_chunks = self._chunk_section(section, content_lines, ast, file_path, len(chunks))
            chunks.extend(section_chunks)
            
        # Handle content not in any section
        orphan_chunks = self._chunk_orphan_content(ast, content_lines, sections, file_path, len(chunks))
        chunks.extend(orphan_chunks)
        
        # Update total chunks count
        for chunk in chunks:
            chunk.metadata.total_chunks = len(chunks)
        
        # Add overlap between chunks
        if self.overlap_size > 0:
            chunks = self._add_chunk_overlap(chunks)
            
        return chunks
        
    def _chunk_section(self, 
                      section: Dict[str, Any],
                      content_lines: List[str],
                      ast: Dict[str, Any],
                      file_path: str,
                      chunk_index_start: int) -> List[DocumentChunk]:
        """Create chunks from a single section."""
        chunks = []
        section_content = section.get("content", "")
        
        if not section_content:
            return chunks
        
        # Extract section hierarchy
        section_hierarchy = [section["title"]]
        if "parent" in section and section["parent"]:
            section_hierarchy.insert(0, section["parent"])
            
        # Check if section is small enough to be a single chunk
        if len(section_content) <= self.max_chunk_size:
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
                line_end=section.get("end_line", section["start_line"])
            )
            
            chunk = DocumentChunk(
                id=chunk_id,
                content=section_content,
                type=ChunkType.HEADING if section["level"] <= 2 else ChunkType.PARAGRAPH,
                metadata=metadata
            )
            chunks.append(chunk)
        else:
            # Split large sections
            sub_chunks = self._split_large_section(
                section, content_lines, file_path, 
                section_hierarchy, chunk_index_start + len(chunks)
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
        words = re.findall(r'\b\w+\b', content.lower())
        # Filter out common words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'been'}
        keywords = [w for w in words if len(w) > 3 and w not in stop_words]
        # Get unique keywords
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique_keywords.append(kw)
        return unique_keywords[:10]  # Top 10 keywords
    
    def _split_large_section(self,
                           section: Dict[str, Any],
                           content_lines: List[str],
                           file_path: str,
                           section_hierarchy: List[str],
                           chunk_index_start: int) -> List[DocumentChunk]:
        """Split a large section into smaller chunks."""
        chunks = []
        section_content = section.get("content", "")
        
        # Try to split by paragraphs first
        paragraphs = self._split_by_paragraphs(section_content)
        
        current_chunk_content = []
        current_chunk_size = 0
        chunk_start_line = section["start_line"]
        
        for paragraph in paragraphs:
            paragraph_size = len(paragraph)
            
            # If paragraph itself is too large, split it further
            if paragraph_size > self.max_chunk_size:
                # Save current chunk first if it has content
                if current_chunk_content and current_chunk_size >= self.min_chunk_size:
                    chunk_content = '\n\n'.join(current_chunk_content)
                    chunk_id = self._generate_chunk_id(file_path, chunk_index_start + len(chunks))
                    
                    metadata = ChunkMetadata(
                        document_path=file_path,
                        section_hierarchy=section_hierarchy,
                        chunk_index=chunk_index_start + len(chunks),
                        total_chunks=0,  # Will be updated later
                        has_code=bool(re.search(r'```[\s\S]*?```', chunk_content)),
                        language="markdown",
                        keywords=self._extract_keywords(chunk_content),
                        word_count=len(chunk_content.split()),
                        line_start=chunk_start_line,
                        line_end=chunk_start_line + len(chunk_content.split('\n'))
                    )
                    
                    chunk = DocumentChunk(
                        id=chunk_id,
                        content=chunk_content,
                        type=ChunkType.PARAGRAPH,
                        metadata=metadata
                    )
                    chunks.append(chunk)
                    current_chunk_content = []
                    current_chunk_size = 0
                
                # Split the large paragraph by sentences or words
                paragraph_chunks = self._split_paragraph_by_size(paragraph, self.max_chunk_size)
                for para_chunk in paragraph_chunks:
                    chunk_id = self._generate_chunk_id(file_path, chunk_index_start + len(chunks))
                    
                    metadata = ChunkMetadata(
                        document_path=file_path,
                        section_hierarchy=section_hierarchy,
                        chunk_index=chunk_index_start + len(chunks),
                        total_chunks=0,  # Will be updated later
                        has_code=bool(re.search(r'```[\s\S]*?```', para_chunk)),
                        language="markdown",
                        keywords=self._extract_keywords(para_chunk),
                        word_count=len(para_chunk.split()),
                        line_start=chunk_start_line,
                        line_end=chunk_start_line + len(para_chunk.split('\n'))
                    )
                    
                    chunk = DocumentChunk(
                        id=chunk_id,
                        content=para_chunk,
                        type=ChunkType.PARAGRAPH,
                        metadata=metadata
                    )
                    chunks.append(chunk)
                    chunk_start_line = metadata.line_end + 1
                
                continue
            
            # If adding this paragraph would exceed max size
            if current_chunk_size + paragraph_size > self.max_chunk_size:
                # Save current chunk if it meets minimum size
                if current_chunk_size >= self.min_chunk_size:
                    chunk_content = '\n\n'.join(current_chunk_content)
                    chunk_id = self._generate_chunk_id(file_path, chunk_index_start + len(chunks))
                    
                    metadata = ChunkMetadata(
                        document_path=file_path,
                        section_hierarchy=section_hierarchy,
                        chunk_index=chunk_index_start + len(chunks),
                        total_chunks=0,  # Will be updated later
                        has_code=bool(re.search(r'```[\s\S]*?```', chunk_content)),
                        language="markdown",
                        keywords=self._extract_keywords(chunk_content),
                        word_count=len(chunk_content.split()),
                        line_start=chunk_start_line,
                        line_end=chunk_start_line + len(chunk_content.split('\n'))
                    )
                    
                    chunk = DocumentChunk(
                        id=chunk_id,
                        content=chunk_content,
                        type=ChunkType.PARAGRAPH,
                        metadata=metadata
                    )
                    chunks.append(chunk)
                    
                    # Start new chunk
                    current_chunk_content = [paragraph]
                    current_chunk_size = paragraph_size
                    chunk_start_line = metadata.line_end + 1
                else:
                    # Add to current chunk anyway (to meet minimum size)
                    current_chunk_content.append(paragraph)
                    current_chunk_size += paragraph_size
            else:
                # Add to current chunk
                current_chunk_content.append(paragraph)
                current_chunk_size += paragraph_size
                
        # Save final chunk
        if current_chunk_content:
            chunk_content = '\n\n'.join(current_chunk_content)
            chunk_id = self._generate_chunk_id(file_path, chunk_index_start + len(chunks))
            
            metadata = ChunkMetadata(
                document_path=file_path,
                section_hierarchy=section_hierarchy,
                chunk_index=chunk_index_start + len(chunks),
                total_chunks=0,  # Will be updated later
                has_code=bool(re.search(r'```[\s\S]*?```', chunk_content)),
                language="markdown",
                keywords=self._extract_keywords(chunk_content),
                word_count=len(chunk_content.split()),
                line_start=chunk_start_line,
                line_end=section.get("end_line", chunk_start_line + len(chunk_content.split('\n')))
            )
            
            chunk = DocumentChunk(
                id=chunk_id,
                content=chunk_content,
                type=ChunkType.PARAGRAPH,
                metadata=metadata
            )
            chunks.append(chunk)
            
        return chunks
        
    def _chunk_orphan_content(self,
                            ast: Dict[str, Any],
                            content_lines: List[str],
                            sections: List[Dict[str, Any]],
                            file_path: str,
                            chunk_index_start: int) -> List[DocumentChunk]:
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
            content = '\n'.join(line for _, line in group)
            
            if len(content) >= self.min_chunk_size:
                chunk_id = self._generate_chunk_id(file_path, chunk_index_start + len(chunks))
                
                metadata = ChunkMetadata(
                    document_path=file_path,
                    section_hierarchy=[],  # No section hierarchy for orphan content
                    chunk_index=chunk_index_start + len(chunks),
                    total_chunks=0,  # Will be updated later
                    has_code=bool(re.search(r'```[\s\S]*?```', content)),
                    language="markdown",
                    keywords=self._extract_keywords(content),
                    word_count=len(content.split()),
                    line_start=start_line,
                    line_end=end_line
                )
                
                chunk = DocumentChunk(
                    id=chunk_id,
                    content=content,
                    type=ChunkType.UNKNOWN,
                    metadata=metadata
                )
                chunks.append(chunk)
                
        return chunks
        
    def _create_sliding_window_chunks(self, content: str, file_path: str) -> List[DocumentChunk]:
        """Create chunks using a sliding window approach."""
        chunks = []
        content_lines = content.split('\n')
        
        # Simple character-based sliding window
        start = 0
        chunk_index = 0
        
        while start < len(content):
            # Find end position
            end = min(start + self.max_chunk_size, len(content))
            
            # Try to find a good break point
            if end < len(content):
                # Look for paragraph break
                break_point = content.rfind('\n\n', start, end)
                if break_point > start:
                    end = break_point
                else:
                    # Look for sentence break
                    break_point = content.rfind('. ', start, end)
                    if break_point > start:
                        end = break_point + 1
                        
            chunk_content = content[start:end].strip()
            
            if len(chunk_content) >= self.min_chunk_size:
                # Calculate line numbers
                start_line = content[:start].count('\n')
                end_line = content[:end].count('\n')
                
                chunk_id = self._generate_chunk_id(file_path, chunk_index)
                
                metadata = ChunkMetadata(
                    document_path=file_path,
                    section_hierarchy=[],
                    chunk_index=chunk_index,
                    total_chunks=0,  # Will be updated later
                    has_code=bool(re.search(r'```[\s\S]*?```', chunk_content)),
                    language="markdown",
                    keywords=self._extract_keywords(chunk_content),
                    word_count=len(chunk_content.split()),
                    line_start=start_line,
                    line_end=end_line
                )
                
                chunk = DocumentChunk(
                    id=chunk_id,
                    content=chunk_content,
                    type=ChunkType.PARAGRAPH,
                    metadata=metadata
                )
                chunks.append(chunk)
                chunk_index += 1
                
            # Move start position
            start = end - self.overlap_size if end < len(content) else end
            
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
                overlap_text = self._extract_overlap(prev_chunk.content, self.overlap_size, from_end=True)
                if overlap_text:
                    chunk.context_before = overlap_text
                    
            # Add overlap from next chunk
            if i < len(chunks) - 1:
                next_chunk = chunks[i + 1]
                overlap_text = self._extract_overlap(next_chunk.content, self.overlap_size, from_end=False)
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
            break_point = content.rfind('. ', -size)
            if break_point > 0:
                return content[break_point + 2:]
            else:
                return content[-size:]
        else:
            # Extract from start
            if len(content) <= size:
                return content
                
            # Try to find a good break point
            break_point = content.find('. ', 0, size)
            if break_point > 0:
                return content[:break_point + 1]
            else:
                return content[:size]
                
    def _split_by_paragraphs(self, content: str) -> List[str]:
        """Split content by paragraphs."""
        # Split by double newlines
        paragraphs = re.split(r'\n\s*\n', content)
        
        # Clean and filter paragraphs
        cleaned_paragraphs = []
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if paragraph:
                cleaned_paragraphs.append(paragraph)
        
        return cleaned_paragraphs
    
    def _split_paragraph_by_size(self, paragraph: str, max_size: int) -> List[str]:
        """Split a large paragraph into smaller chunks."""
        chunks = []
        
        # Try to split by sentences first
        sentences = re.split(r'(?<=[.!?])\s+', paragraph)
        
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            sentence_size = len(sentence)
            
            if sentence_size > max_size:
                # If a single sentence is too large, split by words
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                    current_chunk = []
                    current_size = 0
                
                # Split sentence by words
                words = sentence.split()
                word_chunk = []
                word_size = 0
                
                for word in words:
                    word_len = len(word) + 1  # +1 for space
                    if word_size + word_len > max_size and word_chunk:
                        chunks.append(' '.join(word_chunk))
                        word_chunk = [word]
                        word_size = word_len
                    else:
                        word_chunk.append(word)
                        word_size += word_len
                
                if word_chunk:
                    chunks.append(' '.join(word_chunk))
            
            elif current_size + sentence_size + 1 > max_size:
                # Save current chunk and start new one
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                current_chunk = [sentence]
                current_size = sentence_size
            else:
                # Add to current chunk
                current_chunk.append(sentence)
                current_size += sentence_size + 1
        
        # Add remaining chunk
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
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
            # Check if chunks can be merged
            if (len(current_chunk.content) < self.min_chunk_size and
                len(current_chunk.content) + len(next_chunk.content) <= self.max_chunk_size and
                next_chunk.metadata.line_start == current_chunk.metadata.line_end + 1):
                
                # Merge chunks
                current_chunk.content += "\n\n" + next_chunk.content
                current_chunk.metadata.line_end = next_chunk.metadata.line_end
                current_chunk.metadata.word_count = len(current_chunk.content.split())
                current_chunk.metadata.keywords = self._extract_keywords(current_chunk.content)
                
                # Merge section hierarchies if compatible
                if current_chunk.metadata.section_hierarchy == next_chunk.metadata.section_hierarchy:
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