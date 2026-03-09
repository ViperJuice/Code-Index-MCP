"""Adapter to convert TreeSitter Chunker CodeChunk to Code-Index-MCP formats."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping

from chunker import CodeChunk

from ..plugin_base import IndexShard, SymbolDef

__all__ = ["ChunkerAdapter", "get_adapter"]


class ChunkerAdapter:
    """Adapter to convert TreeSitter Chunker CodeChunk to internal formats."""

    def _get_symbol_name(self, chunk: CodeChunk) -> str:
        """Extract a stable symbol name across chunker metadata versions."""
        metadata: Mapping[str, Any] = chunk.metadata or {}

        name = metadata.get("name")
        if isinstance(name, str) and name:
            return name

        signature = metadata.get("signature")
        if isinstance(signature, Mapping):
            signature_name = signature.get("name")
            if isinstance(signature_name, str) and signature_name:
                return signature_name

        first_line = chunk.content.split("\n", 1)[0].strip()
        if first_line:
            if first_line.startswith(("def ", "class ")):
                head = first_line.split()[1]
                return head.split("(")[0].split(":")[0]

        return chunk.node_type

    def _get_signature(self, chunk: CodeChunk) -> Any:
        """Extract signature text across chunker metadata versions."""
        metadata: Mapping[str, Any] = chunk.metadata or {}
        signature = metadata.get("signature")
        if isinstance(signature, str) and signature:
            return signature
        if isinstance(signature, Mapping):
            name = signature.get("name")
            parameters = signature.get("parameters") or []
            if isinstance(name, str) and name:
                param_names = []
                if isinstance(parameters, list):
                    for parameter in parameters:
                        if isinstance(parameter, Mapping):
                            param_name = parameter.get("name")
                            if isinstance(param_name, str) and param_name:
                                param_names.append(param_name)
                return f"{name}({', '.join(param_names)})"

        lines = chunk.content.split("\n")
        return lines[0].strip() if lines else ""

    def _get_kind(self, chunk: CodeChunk) -> str:
        """Normalize chunk kinds for internal symbol consumers."""
        metadata: Mapping[str, Any] = chunk.metadata or {}
        raw_kind = metadata.get("kind") or metadata.get("type") or chunk.node_type
        if raw_kind == "function_definition":
            return "function"
        if raw_kind == "class_definition":
            return "class"
        return str(raw_kind)

    def chunk_to_symbol_dict(self, chunk: CodeChunk) -> Dict:
        """Convert a CodeChunk to the symbol dictionary format.

        Args:
            chunk: CodeChunk from treesitter-chunker

        Returns:
            Dict with keys: symbol, kind, line, end_line, span, signature
        """
        # Extract symbol name from metadata or use node_type as fallback
        symbol_name = self._get_symbol_name(chunk)
        signature = self._get_signature(chunk)

        return {
            "symbol": symbol_name,
            "kind": self._get_kind(chunk),
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
        symbol_name = self._get_symbol_name(chunk)
        signature = self._get_signature(chunk)

        # Extract docstring if available
        doc = chunk.metadata.get("docstring", None)

        return SymbolDef(
            symbol=symbol_name,
            kind=self._get_kind(chunk),
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
