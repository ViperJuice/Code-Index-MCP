"""Semantic code indexing using model-agnostic embeddings and Qdrant."""

from __future__ import annotations

from pathlib import Path
import hashlib
import asyncio
from dataclasses import dataclass
from typing import Iterable, Any, Optional

from qdrant_client import QdrantClient, models

from .treesitter_wrapper import TreeSitterWrapper
from mcp_server.semantic.providers import EmbeddingProviderFactory
from mcp_server.interfaces.embedding_interfaces import (
    EmbeddingConfig,
    EmbeddingType,
    IEmbeddingProvider
)


@dataclass
class SymbolEntry:
    symbol: str
    kind: str
    signature: str
    line: int
    span: tuple[int, int]


class SemanticIndexer:
    """Index code using model-agnostic embeddings stored in Qdrant."""

    def __init__(
        self, 
        collection: str = "code-index", 
        qdrant_path: str = ":memory:",
        model_name: str = "voyage-code-3",
        dimension: int = 1024
    ) -> None:
        self.collection = collection
        self.qdrant = QdrantClient(location=qdrant_path)
        self.wrapper = TreeSitterWrapper()
        
        # Initialize embedding provider
        self.model_name = model_name
        self.dimension = dimension
        self.provider: Optional[IEmbeddingProvider] = None
        self._provider_initialized = False
        
        # Create factory and config
        self.factory = EmbeddingProviderFactory()
        self.config = EmbeddingConfig(
            model_name=model_name,
            dimension=dimension,
            batch_size=100,
            normalize=True
        )

        self._ensure_collection()

    # ------------------------------------------------------------------
    def _ensure_collection(self) -> None:
        exists = any(c.name == self.collection for c in self.qdrant.get_collections().collections)
        if not exists:
            self.qdrant.recreate_collection(
                collection_name=self.collection,
                vectors_config=models.VectorParams(size=self.dimension, distance=models.Distance.COSINE),
            )
    
    def _ensure_provider(self) -> None:
        """Ensure embedding provider is initialized."""
        if not self._provider_initialized:
            # Run async initialization in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self._initialize_provider())
            finally:
                loop.close()
    
    async def _initialize_provider(self) -> None:
        """Initialize the embedding provider."""
        self.provider = self.factory.create_provider(self.model_name, self.config)
        result = await self.provider.initialize(self.config)
        if not result.is_ok():
            raise RuntimeError(f"Failed to initialize embedding provider: {result.error}")
        self._provider_initialized = True

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
            # Ensure provider is initialized
            self._ensure_provider()
            
            # Generate embeddings using async provider
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    self.provider.embed_batch(texts, EmbeddingType.CODE)
                )
                if not result.is_ok():
                    raise RuntimeError(f"Failed to generate embeddings: {result.error}")
                embeds = result.value.embeddings
            finally:
                loop.close()

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
        
        # Ensure provider is initialized
        self._ensure_provider()
        
        # Generate query embedding
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                self.provider.embed_batch([text], EmbeddingType.QUERY)
            )
            if not result.is_ok():
                raise RuntimeError(f"Failed to generate query embedding: {result.error}")
            embedding = result.value.embeddings[0]
        finally:
            loop.close()

        results = self.qdrant.search(
            collection_name=self.collection,
            query_vector=embedding,
            limit=limit,
        )

        for res in results:
            payload = res.payload or {}
            payload["score"] = res.score
            yield payload

