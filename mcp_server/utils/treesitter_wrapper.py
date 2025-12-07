"""Thin wrapper for parsing files with Tree-sitter.

This wrapper only exposes a minimal interface required by the tests.  It
loads the prebuilt Python grammar distributed with ``tree_sitter_languages``
and provides a helper to parse a file and return the root node of the parsed
tree as an S-expression string.
"""

from __future__ import annotations

import ctypes
from pathlib import Path

import tree_sitter_languages
from tree_sitter import Language, Parser


class TreeSitterWrapper:
    """Utility class around :mod:`tree_sitter` for parsing Python files."""

    def __init__(self) -> None:
        # Locate the shared library containing the bundled grammars.  The
        # ``tree_sitter_languages`` package ships a ``languages.so`` file with
        # functions such as ``tree_sitter_python`` which return ``TSLanguage``
        # pointers.  These can be wrapped with :class:`Language`.
        lib_path = Path(tree_sitter_languages.__path__[0]) / "languages.so"
        self._lib = ctypes.CDLL(str(lib_path))
        # Configure the return type for the Python language function so that
        # ``ctypes`` returns a ``void*`` pointer compatible with
        # ``tree_sitter.Language``'s constructor.
        self._lib.tree_sitter_python.restype = ctypes.c_void_p

        self._language = Language(self._lib.tree_sitter_python())

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
