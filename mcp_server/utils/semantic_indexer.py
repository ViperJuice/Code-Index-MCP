"""Semantic code indexing using configurable embedding providers and Qdrant."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Mapping, Optional, Union

from chunker.core import chunk_file
from qdrant_client import QdrantClient, models
from qdrant_client.http.models import FieldCondition, Filter, MatchValue

from ..artifacts.semantic_namespace import SemanticNamespaceResolver
from ..artifacts.semantic_profiles import SemanticProfile, SemanticProfileRegistry
from ..core.path_resolver import PathResolver
from .embedding_providers import create_embedding_provider

if TYPE_CHECKING:
    from ..storage.sqlite_store import SQLiteStore

logger = logging.getLogger(__name__)


@dataclass
class SymbolEntry:
    symbol: str
    kind: str
    signature: str
    line: int
    span: tuple[int, int]
    parent_class: Optional[str] = None
    parent_symbol: Optional[str] = None


@dataclass
class SymbolChunk:
    """Size-bounded chunk derived from a symbol body."""

    symbol: SymbolEntry
    chunk_index: int
    chunk_total: int
    start_line: int
    end_line: int
    content: str


@dataclass
class DocumentSection:
    """Represents a section within a document."""

    title: str
    content: str
    level: int  # Heading level (1-6 for markdown)
    start_line: int
    end_line: int
    parent_section: Optional[str] = None
    subsections: Optional[list[str]] = None

    def __post_init__(self):
        if self.subsections is None:
            self.subsections = []


class SemanticIndexer:
    """Index code using semantic profile embeddings stored in Qdrant."""

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
        profile: Optional[SemanticProfile] = None,
        profile_registry: Optional[SemanticProfileRegistry] = None,
        semantic_profile: Optional[str] = None,
        namespace_resolver: Optional[SemanticNamespaceResolver] = None,
        repo_identifier: Optional[str] = None,
        branch: Optional[str] = None,
        commit: Optional[str] = None,
        lineage_id: Optional[str] = None,
    ) -> None:
        self.profile_registry = profile_registry
        self._profile_active = bool(profile or profile_registry or semantic_profile)
        self.semantic_profile = self._resolve_semantic_profile(
            profile=profile,
            profile_registry=profile_registry,
            semantic_profile_id=semantic_profile,
        )

        self.embedding_model = self.semantic_profile.model_name
        self.embedding_model_version = self.semantic_profile.model_version
        self.embedding_dimension = self.semantic_profile.vector_dimension
        self.distance_metric = self.semantic_profile.distance_metric
        self.normalization_policy = self.semantic_profile.normalization_policy
        self.chunk_schema_version = self.semantic_profile.chunk_schema_version
        self.compatibility_fingerprint = self.semantic_profile.compatibility_fingerprint

        self.namespace_resolver = namespace_resolver or SemanticNamespaceResolver()
        self.collection = self._resolve_collection_name(
            requested_collection=collection,
            repo_identifier=repo_identifier,
            lineage_id=lineage_id,
            branch=branch,
            commit=commit,
        )
        self.qdrant_path = qdrant_path
        self.metadata_file = ".index_metadata.json"
        self.path_resolver = path_resolver or PathResolver()

        # Initialize Qdrant client with server mode preference
        self._qdrant_available = False
        self._connection_mode = None  # 'server', 'file', or 'memory'
        self.qdrant = self._init_qdrant_client(qdrant_path)

        self.embedding_client = create_embedding_provider(
            provider_name=self.semantic_profile.provider,
            model_name=self.embedding_model,
            vector_dimension=self.embedding_dimension,
            api_key=(self.semantic_profile.build_metadata or {}).get("openai_api_key"),
            base_url=(self.semantic_profile.build_metadata or {}).get(
                "openai_api_base"
            ),
        )
        self.embedding_provider = self.embedding_client.provider_name

        self._ensure_collection()
        self._update_metadata()

    def _resolve_semantic_profile(
        self,
        *,
        profile: Optional[SemanticProfile],
        profile_registry: Optional[SemanticProfileRegistry],
        semantic_profile_id: Optional[str],
    ) -> SemanticProfile:
        """Resolve semantic profile with legacy-safe fallback behavior."""
        if profile is not None:
            return profile

        if profile_registry is not None:
            return profile_registry.get(semantic_profile_id)

        if semantic_profile_id:
            logger.warning(
                "Semantic profile '%s' requested without a profile registry; "
                "falling back to legacy defaults",
                semantic_profile_id,
            )

        legacy_payload: Mapping[str, Any] = {
            "provider": "voyage",
            "model_name": "voyage-code-3",
            "model_version": "legacy",
            "vector_dimension": 1024,
            "distance_metric": "cosine",
            "normalization_policy": "provider-default",
            "chunk_schema_version": "legacy",
            "chunker_version": "legacy",
        }
        return SemanticProfile.from_dict("legacy-default", legacy_payload)

    def _resolve_collection_name(
        self,
        *,
        requested_collection: str,
        repo_identifier: Optional[str],
        lineage_id: Optional[str],
        branch: Optional[str],
        commit: Optional[str],
    ) -> str:
        """Resolve collection name, using namespace contract when context exists."""
        if not repo_identifier:
            return requested_collection

        effective_lineage = lineage_id
        if not effective_lineage and (branch or commit):
            effective_lineage = self.namespace_resolver.derive_lineage_id(
                branch, commit
            )

        if not effective_lineage:
            return requested_collection

        return self.namespace_resolver.resolve_collection_name(
            repo_identifier=repo_identifier,
            profile_id=self.semantic_profile.profile_id,
            lineage_id=effective_lineage,
        )

    # ------------------------------------------------------------------
    def _embed_texts(
        self, texts: List[str], input_type: str = "document"
    ) -> List[List[float]]:
        """Generate embeddings using the configured provider."""
        return self.embedding_client.embed(texts, input_type=input_type)

    def _max_chunk_chars(self) -> int:
        """Return max chunk size for embedding payloads."""
        raw = os.environ.get("SEMANTIC_MAX_CHARS", "12000")
        try:
            value = int(raw)
        except ValueError:
            value = 12000
        return max(2000, value)

    def _collect_symbol_entries(self, root: Any, lines: List[str]) -> List[SymbolEntry]:
        """Collect class/function symbols including nested method context."""
        entries: List[SymbolEntry] = []

        def walk(node: Any, stack: List[SymbolEntry]) -> None:
            name_node = (
                node.child_by_field_name("name")
                if hasattr(node, "child_by_field_name")
                else None
            )
            current = None
            if (
                node.type in {"function_definition", "class_definition"}
                and name_node is not None
            ):
                name = name_node.text.decode()
                start_line = node.start_point[0] + 1
                end_line = node.end_point[0] + 1
                signature = (
                    lines[start_line - 1].strip()
                    if 0 <= start_line - 1 < len(lines)
                    else name
                )
                kind = "function" if node.type == "function_definition" else "class"

                parent_class = None
                for parent in reversed(stack):
                    if parent.kind == "class":
                        parent_class = parent.symbol
                        break

                parent_symbol = stack[-1].symbol if stack else None
                current = SymbolEntry(
                    symbol=name,
                    kind=kind,
                    signature=signature,
                    line=start_line,
                    span=(start_line, end_line),
                    parent_class=parent_class,
                    parent_symbol=parent_symbol,
                )
                entries.append(current)

            next_stack = stack + ([current] if current else [])
            for child in getattr(node, "children", []):
                walk(child, next_stack)

        walk(root, [])
        return entries

    def _split_symbol_chunks(
        self, symbol: SymbolEntry, lines: List[str]
    ) -> List[SymbolChunk]:
        """Split a symbol body into size-bounded chunks while preserving context."""
        start = max(1, symbol.span[0])
        end = max(start, symbol.span[1])
        symbol_lines = lines[start - 1 : end]
        if not symbol_lines:
            return []

        max_chars = self._max_chunk_chars()
        chunks: List[SymbolChunk] = []

        # Step 1: paragraph-aware splitting on blank lines.
        blocks: List[tuple[int, int]] = []
        block_start = start
        for idx, text in enumerate(symbol_lines, start=start):
            if text.strip() == "":
                if block_start <= idx - 1:
                    blocks.append((block_start, idx - 1))
                block_start = idx + 1
        if block_start <= end:
            blocks.append((block_start, end))
        if not blocks:
            blocks = [(start, end)]

        pending: List[tuple[int, int]] = []
        acc_start: Optional[int] = None
        acc_end: Optional[int] = None
        acc_chars = 0
        for b_start, b_end in blocks:
            block_text = "\n".join(lines[b_start - 1 : b_end])
            block_chars = len(block_text)
            if block_chars > max_chars:
                # Step 2: line-window split for oversized blocks.
                win_start = b_start
                while win_start <= b_end:
                    win_end = win_start
                    current = 0
                    while win_end <= b_end:
                        line_len = len(lines[win_end - 1]) + 1
                        if current + line_len > max_chars and win_end > win_start:
                            break
                        current += line_len
                        win_end += 1
                    pending.append((win_start, win_end - 1))
                    win_start = win_end
                continue

            if acc_start is None:
                acc_start, acc_end = b_start, b_end
                acc_chars = block_chars
                continue

            if acc_chars + block_chars + 1 <= max_chars:
                acc_end = b_end
                acc_chars += block_chars + 1
            else:
                if acc_start is not None and acc_end is not None:
                    pending.append((acc_start, acc_end))
                acc_start, acc_end = b_start, b_end
                acc_chars = block_chars

        if acc_start is not None:
            final_end = acc_end if acc_end is not None else acc_start
            pending.append((acc_start, final_end))

        for i, (c_start, c_end) in enumerate(pending, start=1):
            content = "\n".join(lines[c_start - 1 : c_end])
            chunks.append(
                SymbolChunk(
                    symbol=symbol,
                    chunk_index=i,
                    chunk_total=len(pending),
                    start_line=c_start,
                    end_line=c_end,
                    content=content,
                )
            )
        return chunks

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
            collection_exists = any(
                c.name == self.collection for c in collections.collections
            )
            if collection_exists:
                logger.debug(
                    f"Qdrant connection valid - collection '{self.collection}' exists"
                )
            else:
                logger.warning(
                    f"Qdrant connection active but collection '{self.collection}' not found"
                )
            return True
        except Exception as e:
            logger.error(
                f"Qdrant connection validation failed: {type(e).__name__}: {e}"
            )
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
                    vectors_config=models.VectorParams(
                        size=self.embedding_dimension,
                        distance=self._resolve_qdrant_distance(self.distance_metric),
                    ),
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
    def _resolve_qdrant_distance(self, metric: str) -> models.Distance:
        """Map profile distance metric to Qdrant enum."""
        metric_value = (metric or "").strip().lower()
        mapping = {
            "cosine": models.Distance.COSINE,
            "dot": models.Distance.DOT,
            "dotproduct": models.Distance.DOT,
            "euclidean": models.Distance.EUCLID,
            "euclid": models.Distance.EUCLID,
            "manhattan": models.Distance.MANHATTAN,
        }
        resolved = mapping.get(metric_value)
        if resolved is None:
            logger.warning("Unknown distance metric '%s', defaulting to cosine", metric)
            return models.Distance.COSINE
        return resolved

    # ------------------------------------------------------------------
    def _build_metadata(self) -> Dict[str, Any]:
        """Build metadata payload for semantic index compatibility checks."""
        metadata = {
            "embedding_provider": self.embedding_provider,
            "embedding_model": self.embedding_model,
            "model_version": self.embedding_model_version,
            "model_dimension": self.embedding_dimension,
            "distance_metric": self.distance_metric,
            "normalization_policy": self.normalization_policy,
            "chunk_schema_version": self.chunk_schema_version,
            "created_at": datetime.now().isoformat(),
            "qdrant_path": self.qdrant_path,
            "collection_name": self.collection,
            "compatibility_hash": self._generate_compatibility_hash(),
            "git_commit": self._get_git_commit_hash(),
        }

        if self._profile_active:
            metadata["semantic_profile"] = self.semantic_profile.profile_id
            metadata["compatibility_fingerprint"] = self.compatibility_fingerprint

        return metadata

    # ------------------------------------------------------------------
    def _update_metadata(self) -> None:
        """Update index metadata with current model and configuration."""
        metadata = self._build_metadata()

        try:
            with open(self.metadata_file, "w") as f:
                json.dump(metadata, f, indent=2)
        except Exception:
            # Don't fail if metadata can't be written
            pass

    # ------------------------------------------------------------------
    def _generate_compatibility_hash(self) -> str:
        """Generate a hash for compatibility checking."""
        if self._profile_active:
            return self.compatibility_fingerprint

        compatibility_string = (
            f"{self.embedding_model}:{self.embedding_dimension}:{self.distance_metric}"
        )
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
    def check_compatibility(
        self, other_metadata_file: str = ".index_metadata.json"
    ) -> bool:
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

    def _looks_like_code_intent(self, query: str) -> bool:
        """Detect when a query is likely asking for implementation code."""
        normalized = query.lower()
        if not normalized.strip():
            return False

        code_patterns = [
            r"\b(class|def|function|method|symbol|symbols|module|file|filepath)\b",
            r"\b(py|python|js|ts|typescript|javascript|treesitter|tree-sitter)\b",
            r"\b(where is|how does|how do|implemented|implementation|extract|validate)\b",
            r"\.[a-z0-9]{1,6}\b",
        ]
        return any(re.search(pattern, normalized) for pattern in code_patterns)

    def _path_score_multiplier(
        self, path: str, doc_type: str, code_intent: bool
    ) -> float:
        """Apply lightweight source-path priors to semantic results."""
        normalized = path.replace("\\", "/").lower().lstrip("./")
        doc_type_normalized = (doc_type or "").lower()
        multiplier = 1.0

        is_impl = normalized.startswith(("mcp_server/", "src/"))
        is_script = normalized.startswith("scripts/")
        is_test = normalized.startswith("tests/") or "/tests/" in normalized
        is_doc = normalized.startswith(
            ("docs/", "ai_docs/", "architecture/")
        ) or normalized.endswith(("readme.md", "readme.rst", "readme.txt"))
        is_benchmark_artifact = "/benchmarks/" in normalized or normalized.startswith(
            "benchmarks/"
        )

        if is_impl:
            multiplier *= 1.15
        elif is_script:
            multiplier *= 1.05
        elif is_test:
            multiplier *= 0.75
        elif is_doc or doc_type_normalized in {
            "markdown",
            "readme",
            "guide",
            "tutorial",
        }:
            multiplier *= 0.7

        if is_benchmark_artifact:
            multiplier *= 0.85

        if code_intent:
            if is_impl:
                multiplier *= 1.25
            elif is_script:
                multiplier *= 1.1
            if is_test:
                multiplier *= 0.55
            if is_doc or doc_type_normalized in {
                "markdown",
                "readme",
                "guide",
                "tutorial",
            }:
                multiplier *= 0.35
            if is_benchmark_artifact:
                multiplier *= 0.7

        return multiplier

    def _looks_like_symbol_precise_query(self, query: str) -> bool:
        """Detect exact symbol or file lookup style queries."""
        normalized = query.strip()
        if not normalized:
            return False

        if re.search(
            r"\b(class|def|function|method|symbol)\s+[A-Za-z_][A-Za-z0-9_]*",
            normalized,
        ):
            return True
        if re.search(r"\b[A-Z][A-Za-z0-9_]{2,}\b", normalized):
            return True
        return bool(re.search(r"\b[a-z]+_[a-z0-9_]+\b", normalized))

    def _query_overlap_bonus(self, query: str, payload: Mapping[str, Any]) -> float:
        """Apply a small lexical bonus using retrieval metadata fields."""
        terms = {
            token
            for token in re.findall(r"[a-z0-9_]+", query.lower())
            if len(token) >= 3
        }
        if not terms:
            return 1.0

        relative_path = str(
            payload.get("relative_path")
            or payload.get("filepath")
            or payload.get("file")
            or payload.get("path")
            or ""
        )
        path_haystack = " ".join(re.split(r"[^a-z0-9]+", relative_path.lower())).strip()

        haystack = " ".join(
            str(payload.get(key, ""))
            for key in (
                "relative_path",
                "symbol",
                "qualified_name",
                "semantic_path",
                "signature",
                "signature_text",
                "semantic_text",
                "embedding_text",
                "content",
            )
        ).lower()
        content_matches = sum(1 for term in terms if term in haystack)
        path_matches = sum(1 for term in terms if term in path_haystack)

        return 1.0 + min(content_matches, 5) * 0.04 + min(path_matches, 4) * 0.08

    def _implementation_responsibility_bonus(
        self, query: str, payload: Mapping[str, Any]
    ) -> float:
        """Boost files whose role matches implementation-intent queries."""
        terms = {
            token
            for token in re.findall(r"[a-z0-9_]+", query.lower())
            if len(token) >= 3
        }
        if not terms:
            return 1.0

        relative_path = str(
            payload.get("relative_path")
            or payload.get("filepath")
            or payload.get("file")
            or payload.get("path")
            or ""
        ).lower()
        semantic_text = str(payload.get("semantic_text") or "").lower()
        embedding_text = str(payload.get("embedding_text") or "").lower()
        haystack = f"{semantic_text} {embedding_text}".strip()

        bonus = 1.0
        if {"extract", "symbols", "treesitter"}.issubset(terms):
            if "semantic_indexer.py" in relative_path:
                bonus *= 1.28
            elif "generic_treesitter_plugin.py" in relative_path:
                bonus *= 0.82

        if {"extract", "symbols", "python", "treesitter"}.issubset(terms):
            if "semantic_indexer.py" in relative_path:
                bonus *= 1.08
            elif "generic_treesitter_plugin.py" in relative_path:
                bonus *= 0.88

        if {"semantic", "setup", "validate"}.issubset(terms):
            if "setup_commands.py" in relative_path:
                bonus *= 1.18
            elif "semantic_preflight.py" in relative_path:
                bonus *= 0.96

        if {"artifact", "delta", "resolution"}.issubset(terms):
            if "delta_resolver.py" in relative_path:
                bonus *= 1.22
            elif "delta_artifacts.py" in relative_path:
                bonus *= 0.97

        if {"artifact", "push", "pull", "delta", "resolution"}.issubset(terms):
            if "delta_resolver.py" in relative_path:
                bonus *= 1.12
            elif "artifact_commands.py" in relative_path:
                bonus *= 0.84

        if "extract" in terms and "symbols" in terms and "index" in haystack:
            bonus *= 1.04
        if "validate" in terms and "command" in haystack:
            bonus *= 1.03
        if "delta" in terms and "resolve" in haystack:
            bonus *= 1.04

        return bonus

    def _prefer_unique_files(
        self, results: List[dict[str, Any]], limit: int
    ) -> List[dict[str, Any]]:
        """Keep only the highest-ranked chunk per file path."""
        unique_results: List[dict[str, Any]] = []
        seen_paths: set[str] = set()

        for result in results:
            path = str(
                result.get("relative_path")
                or result.get("filepath")
                or result.get("file")
                or result.get("path")
                or ""
            )
            normalized_path = path.replace("\\", "/").lower().lstrip("./")
            dedupe_key = normalized_path or path
            if dedupe_key in seen_paths:
                continue
            seen_paths.add(dedupe_key)
            unique_results.append(result)
            if len(unique_results) >= limit:
                break

        return unique_results

    def _rerank_query_results(
        self, query: str, results: List[dict[str, Any]], limit: int
    ) -> List[dict[str, Any]]:
        """Apply lightweight query-aware reranking to semantic results."""
        code_intent = self._looks_like_code_intent(query)
        reranked: List[dict[str, Any]] = []

        for result in results:
            path = str(
                result.get("relative_path")
                or result.get("filepath")
                or result.get("file")
                or result.get("path")
                or ""
            )
            doc_type = str(result.get("doc_type") or result.get("type") or "")
            adjusted = dict(result)
            score = float(result.get("score", 0.0))
            score *= self._path_score_multiplier(path, doc_type, code_intent)
            score *= self._query_overlap_bonus(query, result)
            score *= self._implementation_responsibility_bonus(query, result)

            normalized_path = path.replace("\\", "/").lower().lstrip("./")
            is_test = (
                normalized_path.startswith("tests/") or "/tests/" in normalized_path
            )
            is_impl = normalized_path.startswith(("mcp_server/", "src/"))
            if self._looks_like_symbol_precise_query(query):
                if is_test:
                    score *= 0.45
                elif is_impl:
                    score *= 1.1

            adjusted["score"] = score
            reranked.append(adjusted)

        reranked.sort(key=lambda item: float(item.get("score", 0.0)), reverse=True)
        return self._prefer_unique_files(reranked, limit)

    def _build_chunk_embedding_text(
        self,
        relative_path: str,
        symbol_name: str,
        kind: str,
        signature: str,
        parent_symbol: Any,
        metadata: Mapping[str, Any],
        chunk_content: str,
    ) -> str:
        """Build enriched embedding text for semantic chunk indexing."""
        module_stem = Path(relative_path).stem.replace("_", " ")
        path_tokens = " ".join(re.split(r"[^a-z0-9]+", relative_path.lower())).strip()
        qualified_name = str(metadata.get("qualified_name") or "")
        semantic_path = str(metadata.get("semantic_path") or "")
        semantic_text = str(metadata.get("semantic_text") or "")
        imports = metadata.get("imports") or []
        calls = metadata.get("calls") or []

        parts = [
            f"file {relative_path}",
            f"module {module_stem}",
        ]
        if path_tokens:
            parts.append(f"path tokens {path_tokens}")
        parts.append(f"{kind} {symbol_name}")
        if qualified_name:
            parts.append(f"qualified name {qualified_name}")
        if semantic_path:
            parts.append(f"semantic path {semantic_path}")
        if parent_symbol:
            parts.append(f"parent symbol {parent_symbol}")
        if signature:
            parts.append(f"signature {signature}")
        if semantic_text:
            parts.append(semantic_text)
        if imports:
            parts.append("imports " + " ".join(str(item) for item in imports[:5]))
        if calls:
            parts.append("calls " + " ".join(str(item) for item in calls[:5]))
        parts.append(chunk_content)

        return "\n".join(part for part in parts if part).strip()

    # ------------------------------------------------------------------
    def index_file(self, path: Path) -> dict[str, Any]:
        """Index a single Python file and return the shard info."""

        relative_path = self.path_resolver.normalize_path(path)
        try:
            chunk_results = chunk_file(
                path,
                "python",
                extract_metadata=True,
                include_retrieval_metadata=True,
            )
        except TypeError:
            chunk_results = chunk_file(
                path,
                "python",
                extract_metadata=True,
            )

        chunks = [chunk for chunk in chunk_results if chunk.content.strip()]
        symbols: List[Dict[str, Any]] = []
        seen_symbols: set[tuple[str, int, int]] = set()

        if chunks:
            embedding_inputs: List[str] = []
            normalized_chunks: List[Dict[str, Any]] = []
            for chunk in chunks:
                metadata = dict(chunk.metadata or {})
                signature_data = metadata.get("signature")
                signature = str(metadata.get("signature_text") or signature_data or "")
                symbol_name = str(
                    metadata.get("symbol")
                    or metadata.get("name")
                    or metadata.get("qualified_name")
                    or Path(relative_path).stem
                )
                kind = str(metadata.get("kind") or chunk.node_type)
                parent_symbol = metadata.get("parent_symbol")
                embedding_text = self._build_chunk_embedding_text(
                    relative_path=relative_path,
                    symbol_name=symbol_name,
                    kind=kind,
                    signature=signature,
                    parent_symbol=parent_symbol,
                    metadata=metadata,
                    chunk_content=chunk.content,
                )

                normalized_chunks.append(
                    {
                        "chunk": chunk,
                        "metadata": metadata,
                        "symbol": symbol_name,
                        "kind": kind,
                        "signature": signature,
                        "parent_symbol": parent_symbol,
                        "embedding_text": embedding_text,
                    }
                )
                embedding_inputs.append(embedding_text)

                symbol_key = (symbol_name, chunk.start_line, chunk.end_line)
                if symbol_key not in seen_symbols:
                    seen_symbols.add(symbol_key)
                    symbols.append(
                        {
                            "symbol": symbol_name,
                            "kind": kind,
                            "signature": signature,
                            "line": chunk.start_line,
                            "span": [chunk.start_line, chunk.end_line],
                            "parent_class": parent_symbol,
                            "parent_symbol": parent_symbol,
                        }
                    )

            embeds = self._embed_texts(embedding_inputs, input_type="document")

            points = []
            for chunk_index, (normalized, vec) in enumerate(
                zip(normalized_chunks, embeds), start=1
            ):
                chunk = normalized["chunk"]
                metadata = normalized["metadata"]
                content_hash = hashlib.sha256(chunk.content.encode()).hexdigest()
                chunk_id = str(chunk.chunk_id or chunk.node_id)

                payload = {
                    "file": str(path),
                    "relative_path": relative_path,
                    "content_hash": content_hash,
                    "chunk_id": chunk_id,
                    "chunk_index": chunk_index,
                    "chunk_total": len(normalized_chunks),
                    "symbol": normalized["symbol"],
                    "kind": normalized["kind"],
                    "signature": normalized["signature"],
                    "line": chunk.start_line,
                    "span": [chunk.start_line, chunk.end_line],
                    "parent_class": normalized["parent_symbol"],
                    "parent_symbol": normalized["parent_symbol"],
                    "language": "python",
                    "is_deleted": False,
                    "content": chunk.content,
                    "embedding_text": normalized["embedding_text"],
                }
                for key in [
                    "qualified_name",
                    "semantic_path",
                    "signature_text",
                    "semantic_text",
                    "imports",
                    "calls",
                    "dependencies",
                ]:
                    if key in metadata:
                        payload[key] = metadata[key]
                points.append(
                    models.PointStruct(
                        id=self._symbol_id(
                            str(path),
                            f"{normalized['symbol']}#chunk{chunk_index}",
                            chunk.start_line,
                            content_hash,
                        ),
                        vector=vec,
                        payload=payload,
                    )
                )

            # Upsert to Qdrant with error handling
            if not self._qdrant_available:
                raise RuntimeError(
                    f"Qdrant is not available - cannot index file {path}"
                )

            try:
                self.qdrant.upsert(collection_name=self.collection, points=points)
            except Exception as e:
                logger.error(
                    f"Failed to upsert {len(points)} points for file {path}: "
                    f"{type(e).__name__}: {e}"
                )
                self._qdrant_available = False
                raise RuntimeError(
                    f"Failed to store embeddings for {path} in Qdrant: {e}"
                )

        return {
            "file": str(path),
            "symbols": symbols,
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
            embedding = self._embed_texts([text], input_type="query")[0]
        except Exception as e:
            raise RuntimeError(f"Failed to generate query embedding: {e}")

        query_limit = limit
        if self._looks_like_code_intent(text):
            query_limit = min(max(limit * 4, limit), 50)

        try:
            if hasattr(self.qdrant, "search"):
                results = self.qdrant.search(
                    collection_name=self.collection,
                    query_vector=embedding,
                    limit=query_limit,
                )
            else:
                response = self.qdrant.query_points(
                    collection_name=self.collection,
                    query=embedding,
                    limit=query_limit,
                    with_payload=True,
                )
                results = list(getattr(response, "points", []) or [])

            rerank_input: List[dict[str, Any]] = []
            for res in results:
                payload = res.payload or {}
                payload["score"] = res.score
                rerank_input.append(payload)

            yield from self._rerank_query_results(text, rerank_input, limit)
        except Exception as e:
            logger.error(f"Qdrant search failed: {type(e).__name__}: {e}")
            self._qdrant_available = False
            raise RuntimeError(
                f"Semantic search failed - Qdrant error: {e}. "
                "Connection may have been lost."
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
        sqlite_store: Optional["SQLiteStore"] = None,
        profile_id: Optional[str] = None,
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
            embedding = self._embed_texts([embedding_text], input_type="document")[0]

            # Compute content hash
            content_hash = (
                hashlib.sha256(content.encode()).hexdigest() if content else None
            )

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

                chunk_id = (metadata or {}).get("chunk_id") if metadata else None
                if chunk_id and sqlite_store is not None:
                    effective_profile_id = (
                        profile_id or self.semantic_profile.profile_id
                    )
                    sqlite_store.upsert_semantic_point(
                        profile_id=effective_profile_id,
                        chunk_id=str(chunk_id),
                        point_id=point_id,
                        collection=self.collection,
                    )
            except Exception as upsert_error:
                logger.error(
                    f"Qdrant upsert failed for symbol '{name}': "
                    f"{type(upsert_error).__name__}: {upsert_error}"
                )
                self._qdrant_available = False
                raise RuntimeError(
                    f"Failed to store symbol '{name}' in Qdrant: {upsert_error}"
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

    def delete_stale_vectors(
        self,
        profile_id: str,
        chunk_ids: List[str],
        sqlite_store: Optional["SQLiteStore"] = None,
    ) -> int:
        """Delete stale vectors for profile-scoped chunk ids and clear mappings."""
        if sqlite_store is None or not chunk_ids:
            return 0

        point_ids = sqlite_store.get_semantic_point_ids(profile_id, chunk_ids)

        if point_ids and self._qdrant_available:
            try:
                self.qdrant.delete(
                    collection_name=self.collection,
                    points_selector=models.PointIdsList(points=point_ids),
                )
            except Exception as e:
                logger.error(
                    "Failed deleting stale vectors for profile '%s': %s",
                    profile_id,
                    e,
                )
                self._qdrant_available = False
                raise RuntimeError(f"Failed to delete stale vectors from Qdrant: {e}")

        sqlite_store.delete_semantic_point_mappings(profile_id, chunk_ids)
        return len(point_ids)

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

    def _parse_markdown_sections(
        self, content: str, file_path: str
    ) -> list[DocumentSection]:
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
            embedding = self._embed_texts([embedding_text], input_type=input_type)[0]
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
            section_id = self._document_section_id(
                str(path), section.title, section.start_line
            )

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
                "language": (
                    "markdown" if doc_type in ["markdown", "readme"] else "text"
                ),
                "is_deleted": False,
            }

            if metadata:
                payload["metadata"] = metadata

            points.append(
                models.PointStruct(id=section_id, vector=embedding, payload=payload)
            )

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
                raise RuntimeError(
                    f"Qdrant is not available - cannot index document {path}"
                )

            try:
                self.qdrant.upsert(collection_name=self.collection, points=points)
            except Exception as e:
                logger.error(
                    f"Failed to upsert {len(points)} sections for document {path}: "
                    f"{type(e).__name__}: {e}"
                )
                self._qdrant_available = False
                raise RuntimeError(
                    f"Failed to store document sections for {path} in Qdrant: {e}"
                )

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
            raise RuntimeError(
                "Qdrant is not available - cannot perform natural language query"
            )

        try:
            # Generate query embedding
            embedding = self._embed_texts([query], input_type="query")[0]
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
            logger.error(
                f"Qdrant natural language query failed: {type(e).__name__}: {e}"
            )
            self._qdrant_available = False
            raise RuntimeError(f"Natural language query failed - Qdrant error: {e}")

        weighted_results = []

        for res in results:
            payload = res.payload or {}

            # Filter by document types if specified
            if doc_types:
                doc_type = payload.get("doc_type", "code")
                if doc_type not in doc_types and not (
                    include_code and doc_type == "code"
                ):
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
            raise RuntimeError(
                f"Qdrant is not available - cannot remove file {file_path}"
            )

        # Normalize to relative path
        try:
            relative_path = self.path_resolver.normalize_path(file_path)
        except ValueError:
            # Path might already be relative
            relative_path = str(file_path).replace("\\", "/")

        # Search for all points with this file
        filter_condition = Filter(
            must=[
                FieldCondition(
                    key="relative_path", match=MatchValue(value=relative_path)
                )
            ]
        )

        try:
            # Get count before deletion for logging
            search_result = self.qdrant.search(
                collection_name=self.collection,
                query_vector=[0.0] * self.embedding_dimension,  # Dummy vector
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
                logger.info(
                    f"Removed {len(point_ids)} embeddings for file: {relative_path}"
                )

            return len(point_ids)
        except Exception as e:
            logger.error(
                f"Failed to remove file {relative_path}: {type(e).__name__}: {e}"
            )
            self._qdrant_available = False
            raise RuntimeError(
                f"Failed to remove file {relative_path} from Qdrant: {e}"
            )

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
            must=[
                FieldCondition(
                    key="relative_path", match=MatchValue(value=old_relative)
                )
            ]
        )

        try:
            # Search for all points
            search_result = self.qdrant.search(
                collection_name=self.collection,
                query_vector=[0.0] * self.embedding_dimension,  # Dummy vector
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
                    logger.warning(
                        f"Content hash mismatch for {old_relative} -> {new_relative}"
                    )
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
                f"Failed to move file {old_relative} -> {new_relative}: "
                f"{type(e).__name__}: {e}"
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
            raise RuntimeError(
                "Qdrant is not available - cannot query embeddings by content hash"
            )

        filter_condition = Filter(
            must=[
                FieldCondition(key="content_hash", match=MatchValue(value=content_hash))
            ]
        )

        try:
            results = self.qdrant.search(
                collection_name=self.collection,
                query_vector=[0.0] * self.embedding_dimension,  # Dummy vector
                filter=filter_condition,
                limit=1000,
                with_payload=True,
                with_vectors=False,
            )

            return [{"id": res.id, **res.payload} for res in results]
        except Exception as e:
            logger.error(
                f"Failed to get embeddings by content hash: {type(e).__name__}: {e}"
            )
            self._qdrant_available = False
            raise RuntimeError(
                f"Failed to query embeddings by content hash in Qdrant: {e}"
            )

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
            raise RuntimeError(
                f"Qdrant is not available - cannot mark file {file_path} as deleted"
            )

        # This is similar to move_file but only updates is_deleted flag
        relative_path = self.path_resolver.normalize_path(file_path)

        filter_condition = Filter(
            must=[
                FieldCondition(
                    key="relative_path", match=MatchValue(value=relative_path)
                )
            ]
        )

        try:
            # Search and update
            search_result = self.qdrant.search(
                collection_name=self.collection,
                query_vector=[0.0] * self.embedding_dimension,
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

            logger.info(
                f"Marked {len(updated_points)} embeddings as deleted for: {relative_path}"
            )
            return len(updated_points)
        except Exception as e:
            logger.error(
                f"Failed to mark file {relative_path} as deleted: "
                f"{type(e).__name__}: {e}"
            )
            self._qdrant_available = False
            raise RuntimeError(
                f"Failed to mark file {relative_path} as deleted in Qdrant: {e}"
            )
