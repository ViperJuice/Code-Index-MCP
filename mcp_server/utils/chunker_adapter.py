"""Adapter to convert TreeSitter Chunker CodeChunk to Code-Index-MCP formats."""

from __future__ import annotations

from typing import Dict, List

from chunker import CodeChunk

from ..plugin_base import IndexShard, SymbolDef

__all__ = ["ChunkerAdapter", "get_adapter"]


class ChunkerAdapter:
    """Adapter to convert TreeSitter Chunker CodeChunk to internal formats."""

    def chunk_to_symbol_dict(self, chunk: CodeChunk) -> Dict:
        """Convert a CodeChunk to the symbol dictionary format.

        Args:
            chunk: CodeChunk from treesitter-chunker

        Returns:
            Dict with keys: symbol, kind, line, end_line, span, signature
        """
        # Extract symbol name from metadata or use node_type as fallback
        symbol_name = chunk.metadata.get("name", chunk.node_type)

        # Get signature from metadata or construct from content
        signature = chunk.metadata.get("signature", "")
        if not signature:
            # Use first line of content as signature
            lines = chunk.content.split("\n")
            signature = lines[0].strip() if lines else ""

        return {
            "symbol": symbol_name,
            "kind": chunk.node_type,
            "line": chunk.start_line,
            "end_line": chunk.end_line,
            "span": [chunk.start_line, chunk.end_line],
            "signature": signature,
        }

    def chunks_to_index_shard(
        self, path: str, chunks: List[CodeChunk], language: str
    ) -> IndexShard:
        """Convert a list of CodeChunks to an IndexShard.

        Args:
            path: File path
            chunks: List of CodeChunk from treesitter-chunker
            language: Language code (e.g., 'python', 'go')

        Returns:
            IndexShard with file, symbols, and language
        """
        symbols = [self.chunk_to_symbol_dict(chunk) for chunk in chunks]
        return IndexShard(file=path, symbols=symbols, language=language)

    def chunk_to_symbol_def(self, chunk: CodeChunk) -> SymbolDef:
        """Convert a CodeChunk to a SymbolDef.

        Args:
            chunk: CodeChunk from treesitter-chunker

        Returns:
            SymbolDef with complete symbol information
        """
        # Extract symbol name from metadata or use node_type as fallback
        symbol_name = chunk.metadata.get("name", chunk.node_type)

        # Get signature from metadata or construct from content
        signature = chunk.metadata.get("signature", "")
        if not signature:
            # Use first line of content as signature
            lines = chunk.content.split("\n")
            signature = lines[0].strip() if lines else ""

        # Extract docstring if available
        doc = chunk.metadata.get("docstring", None)

        return SymbolDef(
            symbol=symbol_name,
            kind=chunk.node_type,
            language=chunk.language,
            signature=signature,
            doc=doc,
            defined_in=chunk.file_path,
            line=chunk.start_line,
            span=(chunk.start_line, chunk.end_line),
        )


# Singleton instance
_adapter: ChunkerAdapter | None = None


def get_adapter() -> ChunkerAdapter:
    """Get singleton ChunkerAdapter instance.

    Returns:
        ChunkerAdapter instance
    """
    global _adapter
    if _adapter is None:
        _adapter = ChunkerAdapter()
    return _adapter
