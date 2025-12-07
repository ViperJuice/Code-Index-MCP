"""Semantic code indexing using Voyage AI embeddings and Qdrant."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Union

import voyageai
from qdrant_client import QdrantClient, models
from qdrant_client.http.models import FieldCondition, Filter, MatchValue

from ..core.path_resolver import PathResolver
from .treesitter_wrapper import TreeSitterWrapper

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
        "markdown": 1.2,  # Documentation gets higher weight
        "readme": 1.3,  # README files get highest weight
        "docstring": 1.1,  # Inline documentation
        "comment": 1.0,  # Regular comments
        "code": 0.9,  # Code slightly lower for doc searches
        "api": 1.15,  # API documentation
        "tutorial": 1.25,  # Tutorial content
        "guide": 1.2,  # Guide content
    }

    def __init__(
        self,
        collection: str = "code-index",
        qdrant_path: str = "./vector_index.qdrant",
        path_resolver: Optional[PathResolver] = None,
    ) -> None:
        self.collection = collection
        self.qdrant_path = qdrant_path
        self.embedding_model = "voyage-code-3"
        self.metadata_file = ".index_metadata.json"
        self.path_resolver = path_resolver or PathResolver()

        # Initialize Qdrant client with server mode preference
        self._qdrant_available = False
        self._connection_mode = None  # 'server', 'file', or 'memory'
        self.qdrant = self._init_qdrant_client(qdrant_path)
        self.wrapper = TreeSitterWrapper()

        # Initialize Voyage AI client with proper API key handling
        api_key = os.environ.get("VOYAGE_API_KEY") or os.environ.get("VOYAGE_AI_API_KEY")
        if api_key:
            self.voyage = voyageai.Client(api_key=api_key)
        else:
            # Let voyageai.Client() look for VOYAGE_API_KEY environment variable
            try:
                self.voyage = voyageai.Client()
            except Exception:
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

    def _init_qdrant_client(self, qdrant_path: str) -> QdrantClient:
        """Initialize Qdrant client with server mode preference.

        Tries to connect in the following order:
        1. Server mode (if QDRANT_USE_SERVER=true)
        2. Explicit HTTP URL (if qdrant_path starts with http)
        3. Memory mode (if qdrant_path is :memory:)
        4. File-based mode (local storage)

        Sets _qdrant_available and _connection_mode on success.

        Returns:
            Configured QdrantClient instance

        Raises:
            RuntimeError: If all connection methods fail
        """
        # First, try server mode (recommended for concurrent access)
        server_url = os.environ.get("QDRANT_URL", "http://localhost:6333")

        if os.environ.get("QDRANT_USE_SERVER", "true").lower() == "true":
            try:
                # Try connecting to Qdrant server
                logger.info(f"Attempting to connect to Qdrant server at {server_url}")
                client = QdrantClient(url=server_url, timeout=5)
                # Test connection with actual API call
                client.get_collections()
                logger.info(f"Successfully connected to Qdrant server at {server_url}")
                self._qdrant_available = True
                self._connection_mode = "server"
                return client
            except Exception as e:
                logger.warning(
                    f"Qdrant server not available at {server_url}: {type(e).__name__}: {e}. "
                    "Falling back to file-based mode."
                )

        # Support explicit HTTP URLs
        if qdrant_path.startswith("http"):
            try:
                logger.info(f"Connecting to Qdrant at explicit URL: {qdrant_path}")
                client = QdrantClient(url=qdrant_path, timeout=5)
                # Test connection
                client.get_collections()
                logger.info(f"Successfully connected to Qdrant at {qdrant_path}")
                self._qdrant_available = True
                self._connection_mode = "server"
                return client
            except Exception as e:
                logger.error(
                    f"Failed to connect to Qdrant server at {qdrant_path}: {type(e).__name__}: {e}"
                )
                raise RuntimeError(
                    f"Cannot connect to Qdrant server at {qdrant_path}. "
                    f"Error: {e}. Please check the URL and ensure the server is running."
                )

        # Memory mode
        if qdrant_path == ":memory:":
            try:
                logger.info("Initializing Qdrant in memory mode")
                client = QdrantClient(location=":memory:")
                self._qdrant_available = True
                self._connection_mode = "memory"
                logger.info("Qdrant memory mode initialized successfully")
                return client
            except Exception as e:
                logger.error(f"Failed to initialize Qdrant in memory mode: {e}")
                raise RuntimeError(f"Failed to initialize Qdrant in memory mode: {e}")

        # Local file path with lock cleanup
        try:
            logger.info(f"Initializing file-based Qdrant at {qdrant_path}")

            # Clean up any stale locks
            lock_file = Path(qdrant_path) / ".lock"
            if lock_file.exists():
                logger.warning(f"Removing stale Qdrant lock file: {lock_file}")
                try:
                    lock_file.unlink()
                except Exception as lock_error:
                    logger.error(f"Failed to remove lock file: {lock_error}")
                    # Continue anyway - Qdrant might handle it

            client = QdrantClient(path=qdrant_path)
            # Test that client is functional
            try:
                client.get_collections()
            except Exception as test_error:
                logger.warning(f"Initial collection check failed: {test_error}")
                # This is okay - collection might not exist yet

            self._qdrant_available = True
            self._connection_mode = "file"
            logger.info(f"File-based Qdrant initialized successfully at {qdrant_path}")
            return client
        except Exception as e:
            logger.error(
                f"Failed to initialize file-based Qdrant at {qdrant_path}: "
                f"{type(e).__name__}: {e}"
            )
            raise RuntimeError(
                f"Failed to initialize Qdrant vector store. "
                f"Attempted path: {qdrant_path}. Error: {e}. "
                f"Please check file permissions and disk space."
            )

    @property
    def is_available(self) -> bool:
        """Check if Qdrant is available without throwing exceptions.

        This property can be used by other components (like HybridSearch)
        to gracefully degrade functionality when Qdrant is unavailable.

        Returns:
            True if Qdrant is initialized and available, False otherwise
        """
        return self._qdrant_available

    @property
    def connection_mode(self) -> Optional[str]:
        """Get the current connection mode.

        Returns:
            'server', 'file', 'memory', or None if not connected
        """
        return self._connection_mode

    def validate_connection(self) -> bool:
        """Validate that the Qdrant connection is still active.

        This method is useful for long-running processes to ensure
        the connection hasn't been lost or corrupted.

        Returns:
            True if connection is valid and responsive, False otherwise
        """
        if not self._qdrant_available:
            logger.warning("Qdrant is not available - connection was never established")
            return False

        try:
            # Attempt a simple operation to verify connection
            collections = self.qdrant.get_collections()
            # Check if our collection exists
            collection_exists = any(c.name == self.collection for c in collections.collections)
            if collection_exists:
                logger.debug(f"Qdrant connection valid - collection '{self.collection}' exists")
            else:
                logger.warning(
                    f"Qdrant connection active but collection '{self.collection}' not found"
                )
            return True
        except Exception as e:
            logger.error(f"Qdrant connection validation failed: {type(e).__name__}: {e}")
            self._qdrant_available = False
            return False

    def _ensure_collection(self) -> None:
        """Ensure the collection exists in Qdrant.

        Raises:
            RuntimeError: If collection cannot be created or verified
        """
        if not self._qdrant_available:
            raise RuntimeError("Qdrant is not available - cannot ensure collection")

        try:
            collections = self.qdrant.get_collections()
            exists = any(c.name == self.collection for c in collections.collections)

            if not exists:
                logger.info(f"Creating Qdrant collection: {self.collection}")
                self.qdrant.recreate_collection(
                    collection_name=self.collection,
                    vectors_config=models.VectorParams(size=1024, distance=models.Distance.COSINE),
                )
                logger.info(f"Successfully created collection: {self.collection}")
            else:
                logger.debug(f"Collection already exists: {self.collection}")
        except Exception as e:
            logger.error(
                f"Failed to ensure collection '{self.collection}': {type(e).__name__}: {e}"
            )
            self._qdrant_available = False
            raise RuntimeError(
                f"Failed to create or verify Qdrant collection '{self.collection}': {e}"
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
            "git_commit": self._get_git_commit_hash(),
        }

        try:
            with open(self.metadata_file, "w") as f:
                json.dump(metadata, f, indent=2)
        except Exception:
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
                ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd="."
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
            with open(other_metadata_file, "r") as f:
                other_metadata = json.load(f)

            current_hash = self._generate_compatibility_hash()
            other_hash = other_metadata.get("compatibility_hash")

            return current_hash == other_hash
        except Exception:
            return False  # If we can't read metadata, assume incompatible

    # ------------------------------------------------------------------
    def _symbol_id(
        self, file: str, name: str, line: int, content_hash: Optional[str] = None
    ) -> int:
        """Generate ID using relative path and optional content hash."""
        # Normalize file path to relative
        try:
            relative_path = self.path_resolver.normalize_path(file)
        except ValueError:
            # File might already be relative
            relative_path = str(file).replace("\\", "/")

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
                points.append(
                    models.PointStruct(
                        id=self._symbol_id(str(path), sym.symbol, sym.line, content_hash),
                        vector=vec,
                        payload=payload,
                    )
                )

            # Upsert to Qdrant with error handling
            if not self._qdrant_available:
                raise RuntimeError(f"Qdrant is not available - cannot index file {path}")

            try:
                self.qdrant.upsert(collection_name=self.collection, points=points)
            except Exception as e:
                logger.error(
                    f"Failed to upsert {len(points)} points for file {path}: "
                    f"{type(e).__name__}: {e}"
                )
                self._qdrant_available = False
                raise RuntimeError(f"Failed to store embeddings for {path} in Qdrant: {e}")

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
        """Query indexed code snippets using a natural language description.

        Args:
            text: Natural language query
            limit: Maximum number of results

        Yields:
            Search results with metadata and scores

        Raises:
            RuntimeError: If Qdrant is unavailable or query fails
        """
        if not self._qdrant_available:
            raise RuntimeError(
                "Qdrant is not available - cannot perform semantic search. "
                "Check connection status with validate_connection()."
            )

        try:
            embedding = self.voyage.embed(
                [text],
                model="voyage-code-3",
                input_type="document",
                output_dimension=1024,
                output_dtype="float",
            ).embeddings[0]
        except Exception as e:
            raise RuntimeError(f"Failed to generate query embedding: {e}")

        try:
            results = self.qdrant.search(
                collection_name=self.collection,
                query_vector=embedding,
                limit=limit,
            )

            for res in results:
                payload = res.payload or {}
                payload["score"] = res.score
                yield payload
        except Exception as e:
            logger.error(f"Qdrant search failed: {type(e).__name__}: {e}")
            self._qdrant_available = False
            raise RuntimeError(
                f"Semantic search failed - Qdrant error: {e}. " "Connection may have been lost."
            )

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
        metadata: dict[str, Any] | None = None,
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

            point = models.PointStruct(id=point_id, vector=embedding, payload=payload)

            # Upsert to Qdrant with error handling
            if not self._qdrant_available:
                raise RuntimeError("Qdrant is not available - cannot index symbol")

            try:
                self.qdrant.upsert(collection_name=self.collection, points=[point])
            except Exception as upsert_error:
                logger.error(
                    f"Qdrant upsert failed for symbol '{name}': "
                    f"{type(upsert_error).__name__}: {upsert_error}"
                )
                self._qdrant_available = False
                raise RuntimeError(f"Failed to store symbol '{name}' in Qdrant: {upsert_error}")
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

        Raises:
            RuntimeError: If Qdrant is unavailable or search fails
        """
        if not self._qdrant_available:
            raise RuntimeError(
                "Qdrant is not available - semantic search unavailable. "
                "Use is_available property to check before calling."
            )
        return list(self.query(query, limit))

    # ------------------------------------------------------------------
    # Document-specific methods
    # ------------------------------------------------------------------

    def _parse_markdown_sections(self, content: str, file_path: str) -> list[DocumentSection]:
        """Parse markdown content into hierarchical sections."""
        lines = content.split("\n")
        sections = []
        current_section = None
        section_stack = []  # Track parent sections

        for i, line in enumerate(lines):
            # Match markdown headers
            header_match = re.match(r"^(#{1,6})\s+(.+)$", line)
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
                    parent_section=parent_section,
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
            section.content = "\n".join(lines[section.start_line : section.end_line])

        return sections

    def _create_document_embedding(
        self,
        content: str,
        title: Optional[str] = None,
        section_context: Optional[str] = None,
        doc_type: str = "markdown",
        metadata: Optional[dict] = None,
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
        metadata: Optional[dict] = None,
    ) -> dict[str, Any]:
        """Index a document with section-aware embeddings.

        Args:
            path: Path to the document
            doc_type: Type of document (markdown, readme, etc.)
            metadata: Additional metadata for the document

        Returns:
            Information about indexed sections
        """
        content = path.read_text(encoding="utf-8")
        file_name = path.name.lower()

        # Determine document type
        if doc_type is None:
            if file_name == "readme.md":
                doc_type = "readme"
            elif file_name.endswith(".md"):
                doc_type = "markdown"
            else:
                doc_type = "text"

        # Parse sections for markdown documents
        if doc_type in ["markdown", "readme"]:
            sections = self._parse_markdown_sections(content, str(path))
        else:
            # Treat entire document as one section
            sections = [
                DocumentSection(
                    title=path.stem,
                    content=content,
                    level=1,
                    start_line=1,
                    end_line=len(content.split("\n")),
                )
            ]

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
                metadata=metadata,
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
                "language": ("markdown" if doc_type in ["markdown", "readme"] else "text"),
                "is_deleted": False,
            }

            if metadata:
                payload["metadata"] = metadata

            points.append(models.PointStruct(id=section_id, vector=embedding, payload=payload))

            indexed_sections.append(
                {
                    "title": section.title,
                    "level": section.level,
                    "context": context_str,
                    "lines": f"{section.start_line}-{section.end_line}",
                }
            )

        # Upsert all sections with error handling
        if points:
            if not self._qdrant_available:
                raise RuntimeError(f"Qdrant is not available - cannot index document {path}")

            try:
                self.qdrant.upsert(collection_name=self.collection, points=points)
            except Exception as e:
                logger.error(
                    f"Failed to upsert {len(points)} sections for document {path}: "
                    f"{type(e).__name__}: {e}"
                )
                self._qdrant_available = False
                raise RuntimeError(f"Failed to store document sections for {path} in Qdrant: {e}")

        return {
            "file": str(path),
            "doc_type": doc_type,
            "sections": indexed_sections,
            "total_sections": len(indexed_sections),
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
        include_code: bool = True,
    ) -> list[dict[str, Any]]:
        """Query using natural language with document type weighting.

        Args:
            query: Natural language query
            limit: Maximum results
            doc_types: Filter by document types
            include_code: Whether to include code results

        Returns:
            Weighted and filtered search results

        Raises:
            RuntimeError: If Qdrant is unavailable or query fails
        """
        if not self._qdrant_available:
            raise RuntimeError("Qdrant is not available - cannot perform natural language query")

        try:
            # Generate query embedding
            embedding = self.voyage.embed(
                [query],
                model="voyage-code-3",
                input_type="query",  # Use query type for natural language
                output_dimension=1024,
                output_dtype="float",
            ).embeddings[0]
        except Exception as e:
            raise RuntimeError(f"Failed to generate query embedding: {e}")

        try:
            # Search with higher limit to allow filtering
            results = self.qdrant.search(
                collection_name=self.collection,
                query_vector=embedding,
                limit=limit * 2 if doc_types else limit,
            )
        except Exception as e:
            logger.error(f"Qdrant natural language query failed: {type(e).__name__}: {e}")
            self._qdrant_available = False
            raise RuntimeError(f"Natural language query failed - Qdrant error: {e}")

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
                "weight_factor": weight,
            }

            weighted_results.append(result)

        # Sort by weighted score and limit
        weighted_results.sort(key=lambda x: x["weighted_score"], reverse=True)
        return weighted_results[:limit]

    def index_documentation_directory(
        self,
        directory: Path,
        recursive: bool = True,
        file_patterns: Optional[list[str]] = None,
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
            "total_sections": total_sections,
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

        Raises:
            RuntimeError: If Qdrant is unavailable or deletion fails
        """
        if not self._qdrant_available:
            raise RuntimeError(f"Qdrant is not available - cannot remove file {file_path}")

        # Normalize to relative path
        try:
            relative_path = self.path_resolver.normalize_path(file_path)
        except ValueError:
            # Path might already be relative
            relative_path = str(file_path).replace("\\", "/")

        # Search for all points with this file
        filter_condition = Filter(
            must=[FieldCondition(key="relative_path", match=MatchValue(value=relative_path))]
        )

        try:
            # Get count before deletion for logging
            search_result = self.qdrant.search(
                collection_name=self.collection,
                query_vector=[0.0] * 1024,  # Dummy vector
                filter=filter_condition,
                limit=1000,  # Get all matches
                with_payload=False,
                with_vectors=False,
            )

            point_ids = [point.id for point in search_result]

            if point_ids:
                # Delete all points
                self.qdrant.delete(
                    collection_name=self.collection,
                    points_selector=models.PointIdsList(points=point_ids),
                )
                logger.info(f"Removed {len(point_ids)} embeddings for file: {relative_path}")

            return len(point_ids)
        except Exception as e:
            logger.error(f"Failed to remove file {relative_path}: {type(e).__name__}: {e}")
            self._qdrant_available = False
            raise RuntimeError(f"Failed to remove file {relative_path} from Qdrant: {e}")

    def move_file(
        self,
        old_path: Union[str, Path],
        new_path: Union[str, Path],
        content_hash: Optional[str] = None,
    ) -> int:
        """Update all embeddings when a file is moved.

        Args:
            old_path: Old file path
            new_path: New file path
            content_hash: Optional content hash for verification

        Returns:
            Number of points updated

        Raises:
            RuntimeError: If Qdrant is unavailable or update fails
        """
        if not self._qdrant_available:
            raise RuntimeError(
                f"Qdrant is not available - cannot move file {old_path} -> {new_path}"
            )

        # Normalize paths
        old_relative = self.path_resolver.normalize_path(old_path)
        new_relative = self.path_resolver.normalize_path(new_path)

        # Find all points for the old file
        filter_condition = Filter(
            must=[FieldCondition(key="relative_path", match=MatchValue(value=old_relative))]
        )

        try:
            # Search for all points
            search_result = self.qdrant.search(
                collection_name=self.collection,
                query_vector=[0.0] * 1024,  # Dummy vector
                filter=filter_condition,
                limit=1000,
                with_payload=True,
                with_vectors=False,
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
                        vector=[],  # Empty vector, we're only updating payload
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
                    with_vectors=True,
                )

                # Create new points with updated payloads
                new_points = []
                for i, full_point in enumerate(full_points):
                    new_points.append(
                        models.PointStruct(
                            id=full_point.id,
                            vector=full_point.vector,
                            payload=updated_points[i].payload,
                        )
                    )

                # Upsert updated points
                self.qdrant.upsert(collection_name=self.collection, points=new_points)

                logger.info(
                    f"Updated {len(new_points)} embeddings: {old_relative} -> {new_relative}"
                )

            return len(updated_points)
        except Exception as e:
            logger.error(
                f"Failed to move file {old_relative} -> {new_relative}: " f"{type(e).__name__}: {e}"
            )
            self._qdrant_available = False
            raise RuntimeError(
                f"Failed to move file {old_relative} -> {new_relative} in Qdrant: {e}"
            )

    def get_embeddings_by_content_hash(self, content_hash: str) -> List[Dict[str, Any]]:
        """Get all embeddings with a specific content hash.

        Args:
            content_hash: Content hash to search for

        Returns:
            List of embedding metadata

        Raises:
            RuntimeError: If Qdrant is unavailable or query fails
        """
        if not self._qdrant_available:
            raise RuntimeError("Qdrant is not available - cannot query embeddings by content hash")

        filter_condition = Filter(
            must=[FieldCondition(key="content_hash", match=MatchValue(value=content_hash))]
        )

        try:
            results = self.qdrant.search(
                collection_name=self.collection,
                query_vector=[0.0] * 1024,  # Dummy vector
                filter=filter_condition,
                limit=1000,
                with_payload=True,
                with_vectors=False,
            )

            return [{"id": res.id, **res.payload} for res in results]
        except Exception as e:
            logger.error(f"Failed to get embeddings by content hash: {type(e).__name__}: {e}")
            self._qdrant_available = False
            raise RuntimeError(f"Failed to query embeddings by content hash in Qdrant: {e}")

    def mark_file_deleted(self, file_path: Union[str, Path]) -> int:
        """Mark all embeddings for a file as deleted (soft delete).

        Args:
            file_path: File path to mark as deleted

        Returns:
            Number of points marked as deleted

        Raises:
            RuntimeError: If Qdrant is unavailable or update fails
        """
        if not self._qdrant_available:
            raise RuntimeError(f"Qdrant is not available - cannot mark file {file_path} as deleted")

        # This is similar to move_file but only updates is_deleted flag
        relative_path = self.path_resolver.normalize_path(file_path)

        filter_condition = Filter(
            must=[FieldCondition(key="relative_path", match=MatchValue(value=relative_path))]
        )

        try:
            # Search and update
            search_result = self.qdrant.search(
                collection_name=self.collection,
                query_vector=[0.0] * 1024,
                filter=filter_condition,
                limit=1000,
                with_payload=True,
                with_vectors=False,
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
                with_vectors=True,
            )

            updated_points = []
            for i, full_point in enumerate(full_points):
                updated_points.append(
                    models.PointStruct(
                        id=full_point.id,
                        vector=full_point.vector,
                        payload=search_result[i].payload,
                    )
                )

            self.qdrant.upsert(collection_name=self.collection, points=updated_points)

            logger.info(f"Marked {len(updated_points)} embeddings as deleted for: {relative_path}")
            return len(updated_points)
        except Exception as e:
            logger.error(
                f"Failed to mark file {relative_path} as deleted: " f"{type(e).__name__}: {e}"
            )
            self._qdrant_available = False
            raise RuntimeError(f"Failed to mark file {relative_path} as deleted in Qdrant: {e}")
