"""Semantic code indexing using Voyage AI embeddings and Qdrant."""

from __future__ import annotations

from pathlib import Path
import hashlib
from dataclasses import dataclass
from typing import Iterable, Any, Optional, Union
import re

import voyageai
from qdrant_client import QdrantClient, models

from .treesitter_wrapper import TreeSitterWrapper


@dataclass
class SymbolEntry:
    symbol: str
    kind: str
    signature: str
    line: int
    span: tuple[int, int]


@dataclass
class DocumentSection:
    """Represents a section within a document."""
    title: str
    content: str
    level: int  # Heading level (1-6 for markdown)
    start_line: int
    end_line: int
    parent_section: Optional[str] = None
    subsections: list[str] = None
    
    def __post_init__(self):
        if self.subsections is None:
            self.subsections = []


class SemanticIndexer:
    """Index code using Voyage Code 3 embeddings stored in Qdrant."""
    
    # Document type weights for similarity calculations
    DOCUMENT_TYPE_WEIGHTS = {
        "markdown": 1.2,      # Documentation gets higher weight
        "readme": 1.3,        # README files get highest weight
        "docstring": 1.1,     # Inline documentation
        "comment": 1.0,       # Regular comments
        "code": 0.9,          # Code slightly lower for doc searches
        "api": 1.15,          # API documentation
        "tutorial": 1.25,     # Tutorial content
        "guide": 1.2,         # Guide content
    }

    def __init__(self, collection: str = "code-index", qdrant_path: str = ":memory:") -> None:
        self.collection = collection
        # Support both memory and HTTP URLs
        if qdrant_path.startswith("http"):
            self.qdrant = QdrantClient(url=qdrant_path)
        else:
            self.qdrant = QdrantClient(location=qdrant_path)
        self.wrapper = TreeSitterWrapper()
        self.voyage = voyageai.Client()

        self._ensure_collection()

    # ------------------------------------------------------------------
    def _ensure_collection(self) -> None:
        exists = any(c.name == self.collection for c in self.qdrant.get_collections().collections)
        if not exists:
            self.qdrant.recreate_collection(
                collection_name=self.collection,
                vectors_config=models.VectorParams(size=1024, distance=models.Distance.COSINE),
            )

    # ------------------------------------------------------------------
    def _symbol_id(self, file: str, name: str, line: int) -> int:
        h = hashlib.sha1(f"{file}:{name}:{line}".encode("utf-8")).digest()[:8]
        return int.from_bytes(h, "big", signed=False)

    # ------------------------------------------------------------------
    def index_file(self, path: Path) -> dict[str, Any]:
        """Index a single Python file and return the shard info."""

        content = path.read_bytes()
        root = self.wrapper.parse(content)
        lines = content.decode("utf-8", "ignore").splitlines()

        symbols: list[SymbolEntry] = []

        for node in root.children:
            if node.type not in {"function_definition", "class_definition"}:
                continue

            name_node = node.child_by_field_name("name")
            if name_node is None:
                continue
            name = name_node.text.decode()
            start_line = node.start_point[0] + 1
            end_line = node.end_point[0] + 1
            signature = lines[start_line - 1].strip() if start_line - 1 < len(lines) else name
            kind = "function" if node.type == "function_definition" else "class"

            symbols.append(
                SymbolEntry(
                    symbol=name,
                    kind=kind,
                    signature=signature,
                    line=start_line,
                    span=(start_line, end_line),
                )
            )

        # Generate embeddings and upsert into Qdrant
        texts = ["\n".join(lines[s.line - 1 : s.span[1]]) for s in symbols]
        if texts:
            embeds = self.voyage.embed(
                texts,
                model="voyage-code-3",
                input_type="document",
                output_dimension=1024,
                output_dtype="float",
            ).embeddings

            points = []
            for sym, vec in zip(symbols, embeds):
                payload = {
                    "file": str(path),
                    "symbol": sym.symbol,
                    "kind": sym.kind,
                    "signature": sym.signature,
                    "line": sym.line,
                    "span": list(sym.span),
                    "language": "python",
                }
                points.append(models.PointStruct(id=self._symbol_id(str(path), sym.symbol, sym.line), vector=vec, payload=payload))

            self.qdrant.upsert(collection_name=self.collection, points=points)

        return {
            "file": str(path),
            "symbols": [
                {
                    "symbol": s.symbol,
                    "kind": s.kind,
                    "signature": s.signature,
                    "line": s.line,
                    "span": list(s.span),
                }
                for s in symbols
            ],
            "language": "python",
        }

    # ------------------------------------------------------------------
    def query(self, text: str, limit: int = 5) -> Iterable[dict[str, Any]]:
        """Query indexed code snippets using a natural language description."""

        embedding = self.voyage.embed(
            [text],
            model="voyage-code-3",
            input_type="document",
            output_dimension=1024,
            output_dtype="float",
        ).embeddings[0]

        results = self.qdrant.search(
            collection_name=self.collection,
            query_vector=embedding,
            limit=limit,
        )

        for res in results:
            payload = res.payload or {}
            payload["score"] = res.score
            yield payload
    
    # ------------------------------------------------------------------
    def index_symbol(
        self,
        file: str,
        name: str,
        kind: str,
        signature: str,
        line: int,
        span: tuple[int, int],
        doc: str | None = None,
        content: str = ""
    ) -> None:
        """Index a single code symbol with its embedding.
        
        Args:
            file: Source file path
            name: Symbol name
            kind: Symbol type (function, class, etc.)
            signature: Symbol signature
            line: Line number where symbol is defined
            span: Line span of the symbol
            doc: Optional documentation string
            content: Symbol content for embedding generation
        """
        # Create embedding text from available information
        embedding_text = f"{kind} {name}\n{signature}"
        if doc:
            embedding_text += f"\n{doc}"
        if content:
            embedding_text += f"\n{content}"
        
        # Generate embedding
        try:
            embedding = self.voyage.embed(
                [embedding_text],
                model="voyage-code-3",
                input_type="document",
                output_dimension=1024,
                output_dtype="float",
            ).embeddings[0]
            
            # Create point for Qdrant
            point_id = self._symbol_id(file, name, line)
            payload = {
                "file": file,
                "symbol": name,
                "kind": kind,
                "signature": signature,
                "line": line,
                "span": list(span),
                "doc": doc,
                "language": "python",  # This should be parameterized
            }
            
            point = models.PointStruct(
                id=point_id,
                vector=embedding,
                payload=payload
            )
            
            # Upsert to Qdrant
            self.qdrant.upsert(
                collection_name=self.collection,
                points=[point]
            )
        except Exception as e:
            raise RuntimeError(f"Failed to index symbol {name}: {e}")
    
    # ------------------------------------------------------------------
    def search(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """Search for code using semantic similarity.
        
        Args:
            query: Natural language search query
            limit: Maximum number of results
            
        Returns:
            List of search results with metadata and scores
        """
        return list(self.query(query, limit))
    
    # ------------------------------------------------------------------
    # Document-specific methods
    # ------------------------------------------------------------------
    
    def _parse_markdown_sections(self, content: str, file_path: str) -> list[DocumentSection]:
        """Parse markdown content into hierarchical sections."""
        lines = content.split('\n')
        sections = []
        current_section = None
        section_stack = []  # Track parent sections
        
        for i, line in enumerate(lines):
            # Match markdown headers
            header_match = re.match(r'^(#{1,6})\s+(.+)$', line)
            if header_match:
                level = len(header_match.group(1))
                title = header_match.group(2).strip()
                
                # Pop sections from stack that are at same or lower level
                while section_stack and section_stack[-1][1] >= level:
                    section_stack.pop()
                
                parent_section = section_stack[-1][0] if section_stack else None
                
                # Save previous section if exists
                if current_section:
                    current_section.end_line = i - 1
                    sections.append(current_section)
                
                # Create new section
                current_section = DocumentSection(
                    title=title,
                    content="",  # Will be filled later
                    level=level,
                    start_line=i + 1,
                    end_line=len(lines),  # Will be updated
                    parent_section=parent_section
                )
                
                # Update parent's subsections
                if parent_section:
                    for sec in sections:
                        if sec.title == parent_section:
                            sec.subsections.append(title)
                            break
                
                section_stack.append((title, level))
        
        # Save last section
        if current_section:
            sections.append(current_section)
        
        # Fill in content for each section
        for section in sections:
            section.content = '\n'.join(lines[section.start_line:section.end_line])
        
        return sections
    
    def _create_document_embedding(
        self, 
        content: str, 
        title: Optional[str] = None, 
        section_context: Optional[str] = None,
        doc_type: str = "markdown",
        metadata: Optional[dict] = None
    ) -> list[float]:
        """Create embeddings with document-specific context."""
        # Build context-aware embedding text
        embedding_parts = []
        
        if title:
            embedding_parts.append(f"Document: {title}")
        
        if section_context:
            embedding_parts.append(f"Section: {section_context}")
        
        if metadata:
            if "summary" in metadata:
                embedding_parts.append(f"Summary: {metadata['summary']}")
            if "tags" in metadata:
                embedding_parts.append(f"Tags: {', '.join(metadata['tags'])}")
        
        embedding_parts.append(content)
        embedding_text = "\n\n".join(embedding_parts)
        
        # Generate embedding with appropriate input type
        input_type = "document" if doc_type in ["markdown", "readme"] else "query"
        
        try:
            embedding = self.voyage.embed(
                [embedding_text],
                model="voyage-code-3",
                input_type=input_type,
                output_dimension=1024,
                output_dtype="float",
            ).embeddings[0]
            return embedding
        except Exception as e:
            raise RuntimeError(f"Failed to create document embedding: {e}")
    
    def index_document(
        self, 
        path: Path, 
        doc_type: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> dict[str, Any]:
        """Index a document with section-aware embeddings.
        
        Args:
            path: Path to the document
            doc_type: Type of document (markdown, readme, etc.)
            metadata: Additional metadata for the document
            
        Returns:
            Information about indexed sections
        """
        content = path.read_text(encoding='utf-8')
        file_name = path.name.lower()
        
        # Determine document type
        if doc_type is None:
            if file_name == "readme.md":
                doc_type = "readme"
            elif file_name.endswith('.md'):
                doc_type = "markdown"
            else:
                doc_type = "text"
        
        # Parse sections for markdown documents
        if doc_type in ["markdown", "readme"]:
            sections = self._parse_markdown_sections(content, str(path))
        else:
            # Treat entire document as one section
            sections = [DocumentSection(
                title=path.stem,
                content=content,
                level=1,
                start_line=1,
                end_line=len(content.split('\n'))
            )]
        
        indexed_sections = []
        points = []
        
        for section in sections:
            # Build section context (parent sections)
            section_context = []
            if section.parent_section:
                section_context.append(section.parent_section)
            section_context.append(section.title)
            context_str = " > ".join(section_context)
            
            # Create embedding with context
            embedding = self._create_document_embedding(
                content=section.content,
                title=path.stem,
                section_context=context_str,
                doc_type=doc_type,
                metadata=metadata
            )
            
            # Create unique ID for section
            section_id = self._document_section_id(str(path), section.title, section.start_line)
            
            # Prepare payload
            payload = {
                "file": str(path),
                "title": section.title,
                "section_context": context_str,
                "content": section.content[:500],  # Store preview
                "level": section.level,
                "start_line": section.start_line,
                "end_line": section.end_line,
                "parent_section": section.parent_section,
                "subsections": section.subsections,
                "doc_type": doc_type,
                "type": "document_section",
                "language": "markdown" if doc_type in ["markdown", "readme"] else "text",
            }
            
            if metadata:
                payload["metadata"] = metadata
            
            points.append(models.PointStruct(
                id=section_id,
                vector=embedding,
                payload=payload
            ))
            
            indexed_sections.append({
                "title": section.title,
                "level": section.level,
                "context": context_str,
                "lines": f"{section.start_line}-{section.end_line}"
            })
        
        # Upsert all sections
        if points:
            self.qdrant.upsert(collection_name=self.collection, points=points)
        
        return {
            "file": str(path),
            "doc_type": doc_type,
            "sections": indexed_sections,
            "total_sections": len(indexed_sections)
        }
    
    def _document_section_id(self, file: str, section: str, line: int) -> int:
        """Generate unique ID for document section."""
        h = hashlib.sha1(f"doc:{file}:{section}:{line}".encode("utf-8")).digest()[:8]
        return int.from_bytes(h, "big", signed=False)
    
    def query_natural_language(
        self, 
        query: str, 
        limit: int = 10,
        doc_types: Optional[list[str]] = None,
        include_code: bool = True
    ) -> list[dict[str, Any]]:
        """Query using natural language with document type weighting.
        
        Args:
            query: Natural language query
            limit: Maximum results
            doc_types: Filter by document types
            include_code: Whether to include code results
            
        Returns:
            Weighted and filtered search results
        """
        # Generate query embedding
        embedding = self.voyage.embed(
            [query],
            model="voyage-code-3",
            input_type="query",  # Use query type for natural language
            output_dimension=1024,
            output_dtype="float",
        ).embeddings[0]
        
        # Search with higher limit to allow filtering
        results = self.qdrant.search(
            collection_name=self.collection,
            query_vector=embedding,
            limit=limit * 2 if doc_types else limit,
        )
        
        weighted_results = []
        
        for res in results:
            payload = res.payload or {}
            
            # Filter by document types if specified
            if doc_types:
                doc_type = payload.get("doc_type", "code")
                if doc_type not in doc_types and not (include_code and doc_type == "code"):
                    continue
            
            # Apply document type weighting
            doc_type = payload.get("doc_type", "code")
            weight = self.DOCUMENT_TYPE_WEIGHTS.get(doc_type, 1.0)
            
            # Adjust score based on document type
            weighted_score = res.score * weight
            
            result = {
                **payload,
                "score": res.score,
                "weighted_score": weighted_score,
                "weight_factor": weight
            }
            
            weighted_results.append(result)
        
        # Sort by weighted score and limit
        weighted_results.sort(key=lambda x: x["weighted_score"], reverse=True)
        return weighted_results[:limit]
    
    def index_documentation_directory(
        self, 
        directory: Path,
        recursive: bool = True,
        file_patterns: Optional[list[str]] = None
    ) -> dict[str, Any]:
        """Index all documentation files in a directory.
        
        Args:
            directory: Directory to index
            recursive: Whether to search recursively
            file_patterns: File patterns to match (default: ["*.md", "*.rst", "*.txt"])
            
        Returns:
            Summary of indexed documents
        """
        if file_patterns is None:
            file_patterns = ["*.md", "*.rst", "*.txt"]
        
        indexed_files = []
        total_sections = 0
        
        for pattern in file_patterns:
            if recursive:
                files = directory.rglob(pattern)
            else:
                files = directory.glob(pattern)
            
            for file_path in files:
                if file_path.is_file():
                    try:
                        result = self.index_document(file_path)
                        indexed_files.append(result["file"])
                        total_sections += result["total_sections"]
                    except Exception as e:
                        print(f"Failed to index {file_path}: {e}")
        
        return {
            "directory": str(directory),
            "indexed_files": indexed_files,
            "total_files": len(indexed_files),
            "total_sections": total_sections
        }

