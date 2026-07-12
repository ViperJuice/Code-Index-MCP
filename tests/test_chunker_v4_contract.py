"""Real-v4 functional contract test for treesitter-chunker (CHUNKERSAFE Lane B).

Pins the treesitter-chunker v4 surface the Code-Index-MCP callers depend on, so a
future v4.x change that moves an import, renames a ``CodeChunk`` field, or
reshapes chunk metadata fails here instead of silently degrading indexing.

Skips cleanly when the installed chunker is not v4 (e.g. a 3.x dev environment),
so the suite stays green on both sides of the adoption.
"""

from __future__ import annotations

import pytest

chunker = pytest.importorskip("chunker")


def _chunker_major() -> int:
    try:
        from importlib.metadata import version

        return int(version("treesitter-chunker").split(".")[0])
    except Exception:  # pragma: no cover - defensive
        return 0


pytestmark = pytest.mark.skipif(
    _chunker_major() < 4,
    reason="real-v4 contract test requires treesitter-chunker>=4",
)

# The exact call sites the dispatcher/plugins/graph use.
from chunker import CodeChunk, chunk_text  # noqa: E402

_PY_SRC = (
    "def foo(x):\n"
    "    '''Docstring.'''\n"
    "    return x + 1\n"
    "\n"
    "class Bar:\n"
    "    def baz(self):\n"
    "        return 2\n"
)


def test_chunk_text_returns_nonempty_chunks():
    chunks = chunk_text(_PY_SRC, "python")
    assert chunks, "v4 chunk_text produced no chunks"
    assert all(isinstance(c, CodeChunk) for c in chunks)


def test_codechunk_attribute_contract():
    """Every attribute the dispatcher (chunk.__dict__) and plugins read must exist."""
    chunk = chunk_text(_PY_SRC, "python")[0]
    # dispatcher_enhanced.py persists chunk.__dict__
    assert hasattr(chunk, "__dict__")
    for attr in (
        "chunk_id",
        "node_id",
        "definition_id",
        "parent_chunk_id",
        "byte_start",
        "byte_end",
        "start_line",
        "end_line",
        "node_type",
        "metadata",
    ):
        assert hasattr(chunk, attr), f"v4 CodeChunk lost attribute {attr!r}"
    assert isinstance(chunk.chunk_id, str) and chunk.chunk_id
    assert isinstance(chunk.byte_start, int) and isinstance(chunk.byte_end, int)
    assert isinstance(chunk.metadata, dict)


def test_v4_metadata_shape_is_adapter_compatible():
    """v4 nests the symbol name under metadata['signature']['name']; the
    version-tolerant chunker_adapter must still recover a symbol name + signature."""
    from mcp_server.utils.chunker_adapter import ChunkerAdapter

    adapter = ChunkerAdapter()
    func_chunk = next(
        c for c in chunk_text(_PY_SRC, "python") if c.node_type == "function_definition"
    )
    name = adapter._get_symbol_name(func_chunk)
    assert name == "foo", f"adapter failed to recover v4 symbol name (got {name!r})"
    sig = adapter._get_signature(func_chunk)
    assert sig, "adapter recovered no signature from v4 metadata"


def test_graph_imports_resolve_and_are_callable():
    """xref/graph-cut imports (used by the graph features) still resolve under v4."""
    from chunker.core import chunk_file  # noqa: F401
    from chunker.graph.cut import graph_cut
    from chunker.graph.xref import build_xref

    assert callable(build_xref)
    assert callable(graph_cut)


def test_lane_a_guard_derives_v4_scheme():
    """The CHUNKERSAFE identity-scheme guard must recognize v4 as a distinct
    scheme (so a v1/v3-built index trips the guard and rebuilds)."""
    from mcp_server.storage.sqlite_store import current_chunk_id_scheme

    scheme = current_chunk_id_scheme()
    assert scheme == "treesitter_chunk_id_v4", scheme
    assert scheme != "treesitter_chunk_id_v1"
