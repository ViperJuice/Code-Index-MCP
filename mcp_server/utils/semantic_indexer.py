"""Semantic code indexing using Voyage AI embeddings and Qdrant."""

from __future__ import annotations

from pathlib import Path
import hashlib
from dataclasses import dataclass
from typing import Iterable, Any

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


class SemanticIndexer:
    """Index code using Voyage Code 3 embeddings stored in Qdrant."""

    def __init__(self, collection: str = "code-index", qdrant_path: str = ":memory:") -> None:
        self.collection = collection
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

