"""Thin wrapper for parsing files with Tree-sitter.

This wrapper only exposes a minimal interface required by the tests.  It
loads the prebuilt Python grammar distributed with ``tree_sitter_languages``
and provides a helper to parse a file and return the root node of the parsed
tree as an S-expression string.
"""

from __future__ import annotations

from pathlib import Path

from tree_sitter import Language, Parser
from tree_sitter_language_pack import get_language as _get_ts_language


class TreeSitterWrapper:
    """Utility class around :mod:`tree_sitter` for parsing Python files."""

    def __init__(self) -> None:
        self._language = _get_ts_language("python")

        self._parser = Parser()
        self._parser.language = self._language

    # ------------------------------------------------------------------
    def _sexp(self, node) -> str:
        """Return an S-expression representation of ``node``."""

        if node.child_count == 0:
            return node.type

        parts: list[str] = []
        for i in range(node.child_count):
            child = node.child(i)
            child_sexp = self._sexp(child)
            field = node.field_name_for_child(i)
            if field:
                parts.append(f"{field}: {child_sexp}")
            else:
                parts.append(child_sexp)
        return f"({node.type} {' '.join(parts)})"

    # ------------------------------------------------------------------
    def parse(self, content: bytes):
        """Parse ``content`` and return the root :class:`~tree_sitter.Node`."""

        tree = self._parser.parse(content)
        return tree.root_node

    # ------------------------------------------------------------------
    def parse_file(self, path: Path) -> str:
        """Parse the given file and return the AST root as an S-expression."""

        content = path.read_bytes()
        root = self.parse(content)
        return self._sexp(root)

    # Convenience -------------------------------------------------------
    def parse_path(self, path: Path):
        """Parse ``path`` and return the root node."""

        return self.parse(path.read_bytes())
