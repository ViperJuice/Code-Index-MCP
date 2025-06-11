"""Semantic code indexing using Voyage AI embeddings and Qdrant."""

from __future__ import annotations

from pathlib import Path
import hashlib
import json
import os
from dataclasses import dataclass
from typing import Iterable, Any, Optional, Union, List, Dict
from datetime import datetime
import re
import logging

import voyageai
from qdrant_client import QdrantClient, models
from qdrant_client.http.models import Filter, FieldCondition, MatchValue

from .treesitter_wrapper import TreeSitterWrapper
from ..core.path_resolver import PathResolver

logger = logging.getLogger(__name__)


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

    def __init__(self, collection: str = "code-index", qdrant_path: str = "./vector_index.qdrant", path_resolver: Optional[PathResolver] = None) -> None:
        self.collection = collection
        self.qdrant_path = qdrant_path
        self.embedding_model = "voyage-code-3"
        self.metadata_file = ".index_metadata.json"
        self.path_resolver = path_resolver or PathResolver()
        
        # Support both memory and HTTP URLs
        if qdrant_path.startswith("http"):
            # For HTTP URLs, parse properly
            self.qdrant = QdrantClient(url=qdrant_path)
        elif qdrant_path == ":memory:":
            # Memory mode
            self.qdrant = QdrantClient(location=":memory:")
        else:
            # Local file path - use path parameter to avoid IDNA issues
            self.qdrant = QdrantClient(path=qdrant_path)
        self.wrapper = TreeSitterWrapper()
        
        # Initialize Voyage AI client with proper API key handling
        api_key = os.environ.get('VOYAGE_API_KEY') or os.environ.get('VOYAGE_AI_API_KEY')
        if api_key:
            self.voyage = voyageai.Client(api_key=api_key)
        else:
            # Let voyageai.Client() look for VOYAGE_API_KEY environment variable
            try:
                self.voyage = voyageai.Client()
            except Exception as e:
                raise RuntimeError(
                    "Semantic search requires Voyage AI API key. "
                    "Configure it using one of these methods:\n"
                    "1. Create .mcp.json with env.VOYAGE_AI_API_KEY for Claude Code\n"
                    "2. Set VOYAGE_AI_API_KEY environment variable\n"
                    "3. Add VOYAGE_AI_API_KEY to .env file\n"
                    "Get your API key from: https://www.voyageai.com/"
                )

        self._ensure_collection()
        self._update_metadata()

    # ------------------------------------------------------------------
    def _ensure_collection(self) -> None:
        exists = any(c.name == self.collection for c in self.qdrant.get_collections().collections)
        if not exists:
            self.qdrant.recreate_collection(
                collection_name=self.collection,
                vectors_config=models.VectorParams(size=1024, distance=models.Distance.COSINE),
            )

    # ------------------------------------------------------------------
    def _update_metadata(self) -> None:
        """Update index metadata with current model and configuration."""
        metadata = {
            "embedding_model": self.embedding_model,
            "model_dimension": 1024,
            "distance_metric": "cosine",
            "created_at": datetime.now().isoformat(),
            "qdrant_path": self.qdrant_path,
            "collection_name": self.collection,
            "compatibility_hash": self._generate_compatibility_hash(),
            "git_commit": self._get_git_commit_hash()
        }
        
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            # Don't fail if metadata can't be written
            pass

    # ------------------------------------------------------------------
    def _generate_compatibility_hash(self) -> str:
        """Generate a hash for compatibility checking."""
        compatibility_string = f"{self.embedding_model}:1024:cosine"
        return hashlib.sha256(compatibility_string.encode()).hexdigest()[:16]

    # ------------------------------------------------------------------
    def _get_git_commit_hash(self) -> Optional[str]:
        """Get current git commit hash if available."""
        try:
            import subprocess
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                cwd="."
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None

    # ------------------------------------------------------------------
    def check_compatibility(self, other_metadata_file: str = ".index_metadata.json") -> bool:
        """Check if current configuration is compatible with existing index."""
        if not os.path.exists(other_metadata_file):
            return True  # No existing metadata, assume compatible
        
        try:
            with open(other_metadata_file, 'r') as f:
                other_metadata = json.load(f)
            
            current_hash = self._generate_compatibility_hash()
            other_hash = other_metadata.get("compatibility_hash")
            
            return current_hash == other_hash
        except Exception:
            return False  # If we can't read metadata, assume incompatible

    # ------------------------------------------------------------------
    def _symbol_id(self, file: str, name: str, line: int, content_hash: Optional[str] = None) -> int:
        """Generate ID using relative path and optional content hash."""
        # Normalize file path to relative
        try:
            relative_path = self.path_resolver.normalize_path(file)
        except ValueError:
            # File might already be relative
            relative_path = str(file).replace('\\', '/')
        
        # Include content hash if provided for better deduplication
        if content_hash:
            id_str = f"{relative_path}:{name}:{line}:{content_hash[:8]}"
        else:
            id_str = f"{relative_path}:{name}:{line}"
        
        h = hashlib.sha1(id_str.encode("utf-8")).digest()[:8]
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
                # Compute content hash for this symbol
                symbol_content = "\n".join(lines[sym.line - 1 : sym.span[1]])
                content_hash = hashlib.sha256(symbol_content.encode()).hexdigest()
                
                # Use relative path in payload
                relative_path = self.path_resolver.normalize_path(path)
                
                payload = {
                    "file": str(path),  # Keep absolute for backward compatibility
                    "relative_path": relative_path,
                    "content_hash": content_hash,
                    "symbol": sym.symbol,
                    "kind": sym.kind,
                    "signature": sym.signature,
                    "line": sym.line,
                    "span": list(sym.span),
                    "language": "python",
                    "is_deleted": False,
                }
                points.append(models.PointStruct(
                    id=self._symbol_id(str(path), sym.symbol, sym.line, content_hash), 
                    vector=vec, 
                    payload=payload
                ))

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
        content: str = "",
        metadata: dict[str, Any] | None = None
    ) -> None:
        """Index a single code symbol with its embedding.
        
        Args:
            file: Source file path
            name: Symbol name
            kind: Symbol type (function, class, chunk, etc.)
            signature: Symbol signature
            line: Line number where symbol is defined
            span: Line span of the symbol
            doc: Optional documentation string
            content: Symbol content for embedding generation
            metadata: Additional metadata to store with the symbol
        """
        # For chunks, content already contains contextual embedding text
        if kind == "chunk":
            embedding_text = content
        else:
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
            
            # Compute content hash
            content_hash = hashlib.sha256(content.encode()).hexdigest() if content else None
            
            # Use relative path
            relative_path = self.path_resolver.normalize_path(file)
            
            # Create point for Qdrant
            point_id = self._symbol_id(file, name, line, content_hash)
            payload = {
                "file": file,  # Keep absolute for backward compatibility
                "relative_path": relative_path,
                "content_hash": content_hash,
                "symbol": name,
                "kind": kind,
                "signature": signature,
                "line": line,
                "span": list(span),
                "doc": doc,
                "language": "python",  # This should be parameterized
                "is_deleted": False,
            }
            
            # Add custom metadata if provided
            if metadata:
                payload.update(metadata)
            
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
            if "API key" in str(e) or "authentication" in str(e).lower():
                raise RuntimeError(
                    f"Semantic indexing failed due to API key issue: {e}\n"
                    "Configure Voyage AI API key using:\n"
                    "1. .mcp.json with env.VOYAGE_AI_API_KEY for Claude Code\n"
                    "2. VOYAGE_AI_API_KEY environment variable\n"
                    "3. VOYAGE_AI_API_KEY in .env file"
                )
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
            
            # Use relative path
            relative_path = self.path_resolver.normalize_path(path)
            
            # Compute content hash for section
            section_hash = hashlib.sha256(section.content.encode()).hexdigest()
            
            # Prepare payload
            payload = {
                "file": str(path),  # Keep absolute for backward compatibility
                "relative_path": relative_path,
                "content_hash": section_hash,
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
                "is_deleted": False,
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
    
    # ------------------------------------------------------------------
    # File operation methods for path management
    # ------------------------------------------------------------------
    
    def remove_file(self, file_path: Union[str, Path]) -> int:
        """Remove all embeddings for a file from the index.
        
        Args:
            file_path: File path (absolute or relative)
            
        Returns:
            Number of points removed
        """
        # Normalize to relative path
        try:
            relative_path = self.path_resolver.normalize_path(file_path)
        except ValueError:
            # Path might already be relative
            relative_path = str(file_path).replace('\\', '/')
        
        # Search for all points with this file
        filter_condition = Filter(
            must=[
                FieldCondition(
                    key="relative_path",
                    match=MatchValue(value=relative_path)
                )
            ]
        )
        
        # Get count before deletion for logging
        search_result = self.qdrant.search(
            collection_name=self.collection,
            query_vector=[0.0] * 1024,  # Dummy vector
            filter=filter_condition,
            limit=1000,  # Get all matches
            with_payload=False,
            with_vectors=False
        )
        
        point_ids = [point.id for point in search_result]
        
        if point_ids:
            # Delete all points
            self.qdrant.delete(
                collection_name=self.collection,
                points_selector=models.PointIdsList(points=point_ids)
            )
            logger.info(f"Removed {len(point_ids)} embeddings for file: {relative_path}")
        
        return len(point_ids)
    
    def move_file(self, old_path: Union[str, Path], new_path: Union[str, Path], 
                  content_hash: Optional[str] = None) -> int:
        """Update all embeddings when a file is moved.
        
        Args:
            old_path: Old file path
            new_path: New file path
            content_hash: Optional content hash for verification
            
        Returns:
            Number of points updated
        """
        # Normalize paths
        old_relative = self.path_resolver.normalize_path(old_path)
        new_relative = self.path_resolver.normalize_path(new_path)
        
        # Find all points for the old file
        filter_condition = Filter(
            must=[
                FieldCondition(
                    key="relative_path",
                    match=MatchValue(value=old_relative)
                )
            ]
        )
        
        # Search for all points
        search_result = self.qdrant.search(
            collection_name=self.collection,
            query_vector=[0.0] * 1024,  # Dummy vector
            filter=filter_condition,
            limit=1000,
            with_payload=True,
            with_vectors=False
        )
        
        if not search_result:
            logger.warning(f"No embeddings found for file: {old_relative}")
            return 0
        
        # Update payloads with new path
        updated_points = []
        for point in search_result:
            # Update payload
            new_payload = point.payload.copy()
            new_payload["relative_path"] = new_relative
            new_payload["file"] = str(new_path)  # Update absolute path too
            
            # Verify content hash if provided
            if content_hash and new_payload.get("content_hash") != content_hash:
                logger.warning(f"Content hash mismatch for {old_relative} -> {new_relative}")
                continue
            
            updated_points.append(
                models.PointStruct(
                    id=point.id,
                    payload=new_payload,
                    vector=[]  # Empty vector, we're only updating payload
                )
            )
        
        # Batch update payloads
        if updated_points:
            # Qdrant doesn't support payload-only updates directly,
            # so we need to re-fetch vectors and update
            point_ids = [p.id for p in updated_points]
            
            # Fetch full points with vectors
            full_points = self.qdrant.retrieve(
                collection_name=self.collection,
                ids=point_ids,
                with_payload=True,
                with_vectors=True
            )
            
            # Create new points with updated payloads
            new_points = []
            for i, full_point in enumerate(full_points):
                new_points.append(
                    models.PointStruct(
                        id=full_point.id,
                        vector=full_point.vector,
                        payload=updated_points[i].payload
                    )
                )
            
            # Upsert updated points
            self.qdrant.upsert(
                collection_name=self.collection,
                points=new_points
            )
            
            logger.info(f"Updated {len(new_points)} embeddings: {old_relative} -> {new_relative}")
        
        return len(updated_points)
    
    def get_embeddings_by_content_hash(self, content_hash: str) -> List[Dict[str, Any]]:
        """Get all embeddings with a specific content hash.
        
        Args:
            content_hash: Content hash to search for
            
        Returns:
            List of embedding metadata
        """
        filter_condition = Filter(
            must=[
                FieldCondition(
                    key="content_hash",
                    match=MatchValue(value=content_hash)
                )
            ]
        )
        
        results = self.qdrant.search(
            collection_name=self.collection,
            query_vector=[0.0] * 1024,  # Dummy vector
            filter=filter_condition,
            limit=1000,
            with_payload=True,
            with_vectors=False
        )
        
        return [
            {
                "id": res.id,
                **res.payload
            }
            for res in results
        ]
    
    def mark_file_deleted(self, file_path: Union[str, Path]) -> int:
        """Mark all embeddings for a file as deleted (soft delete).
        
        Args:
            file_path: File path to mark as deleted
            
        Returns:
            Number of points marked as deleted
        """
        # This is similar to move_file but only updates is_deleted flag
        relative_path = self.path_resolver.normalize_path(file_path)
        
        filter_condition = Filter(
            must=[
                FieldCondition(
                    key="relative_path",
                    match=MatchValue(value=relative_path)
                )
            ]
        )
        
        # Search and update
        search_result = self.qdrant.search(
            collection_name=self.collection,
            query_vector=[0.0] * 1024,
            filter=filter_condition,
            limit=1000,
            with_payload=True,
            with_vectors=False
        )
        
        if not search_result:
            return 0
        
        # Update is_deleted flag
        point_ids = []
        for point in search_result:
            point.payload["is_deleted"] = True
            point_ids.append(point.id)
        
        # Re-fetch and update (same process as move_file)
        full_points = self.qdrant.retrieve(
            collection_name=self.collection,
            ids=point_ids,
            with_payload=True,
            with_vectors=True
        )
        
        updated_points = []
        for i, full_point in enumerate(full_points):
            updated_points.append(
                models.PointStruct(
                    id=full_point.id,
                    vector=full_point.vector,
                    payload=search_result[i].payload
                )
            )
        
        self.qdrant.upsert(
            collection_name=self.collection,
            points=updated_points
        )
        
        logger.info(f"Marked {len(updated_points)} embeddings as deleted for: {relative_path}")
        return len(updated_points)

