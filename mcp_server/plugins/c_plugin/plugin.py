from __future__ import annotations

import ctypes
import logging
import os
from pathlib import Path
from typing import Iterable, Optional

import tree_sitter_languages
from tree_sitter import Language, Parser

from ...plugin_base import (
    IndexShard,
    IPlugin,
    Reference,
    SearchOpts,
    SearchResult,
    SymbolDef,
)
from ...storage.sqlite_store import SQLiteStore
from ...utils.fuzzy_indexer import FuzzyIndexer

logger = logging.getLogger(__name__)


class Plugin(IPlugin):
    lang = "c"

    def __init__(self, sqlite_store: Optional[SQLiteStore] = None) -> None:
        # Initialize Tree-sitter parser for C
        lib_path = Path(tree_sitter_languages.__path__[0]) / (
            "languages.pyd" if os.name == "nt" else "languages.so"
        )
        self._lib = ctypes.CDLL(str(lib_path))
        self._lib.tree_sitter_c.restype = ctypes.c_void_p

        self._language = Language(self._lib.tree_sitter_c())
        self._parser = Parser()
        self._parser.language = self._language

        # Initialize indexer and storage
        self._indexer = FuzzyIndexer(sqlite_store=sqlite_store)
        self._sqlite_store = sqlite_store
        self._repository_id = None

        # Track parsed files for definition/reference finding
        self._parsed_files = {}  # path -> (content, tree)

        # Create or get repository if SQLite is enabled
        if self._sqlite_store:
            self._repository_id = self._sqlite_store.create_repository(
                str(Path.cwd()), Path.cwd().name, {"language": "c"}
            )

        if os.getenv("MCP_SKIP_PLUGIN_PREINDEX", "false").lower() != "true":
            self._preindex()

    _EXCLUDED_DIRS = {
        "htmlcov",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        ".git",
        "dist",
        "build",
        "test_workspace",
    }

    def _preindex(self) -> None:
        """Pre-index all C/H files in the current directory."""
        for ext in ["*.c", "*.h"]:
            for path in Path(".").rglob(ext):
                if any(part in self._EXCLUDED_DIRS for part in path.parts):
                    continue
                try:
                    text = path.read_text()
                    self._indexer.add_file(str(path), text)
                except Exception as e:
                    logger.error(f"Failed to pre-index {path}: {e}")
                    continue

    def supports(self, path: str | Path) -> bool:
        """Return True if file extension matches C/H files."""
        suffixes = {".c", ".h"}
        return Path(path).suffix.lower() in suffixes

    def indexFile(self, path: str | Path, content: str) -> IndexShard:
        """Parse the file and return an index shard."""
        if isinstance(path, str):
            path = Path(path)

        # Add to fuzzy indexer
        self._indexer.add_file(str(path), content)

        # Parse with Tree-sitter
        tree = self._parser.parse(content.encode("utf-8"))
        root = tree.root_node

        # Cache parsed tree for later use
        self._parsed_files[str(path)] = (content, tree)

        # Store file in SQLite if available
        file_id = None
        if self._sqlite_store and self._repository_id:
            import hashlib

            file_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            rel_path = str(
                path.relative_to(Path.cwd())
                if path.is_absolute() and path.is_relative_to(Path.cwd())
                else path
            )
            file_id = self._sqlite_store.store_file(
                self._repository_id,
                str(path),
                rel_path,
                language="c",
                size=len(content),
                hash=file_hash,
            )

        symbols = []

        # Extract functions
        for node in self._find_nodes(root, "function_definition"):
            symbol_info = self._extract_function(node, content)
            if symbol_info:
                symbols.append(symbol_info)

                # Store in SQLite
                if self._sqlite_store and file_id:
                    symbol_id = self._sqlite_store.store_symbol(
                        file_id,
                        symbol_info["symbol"],
                        symbol_info["kind"],
                        symbol_info["line"],
                        symbol_info["span"][1],
                        signature=symbol_info["signature"],
                    )
                    # Add to fuzzy indexer with metadata
                    self._indexer.add_symbol(
                        symbol_info["symbol"],
                        str(path),
                        symbol_info["line"],
                        {"symbol_id": symbol_id, "file_id": file_id},
                    )

        # Extract struct definitions
        for node in self._find_nodes(root, "struct_specifier"):
            symbol_info = self._extract_struct(node, content)
            if symbol_info:
                symbols.append(symbol_info)

                if self._sqlite_store and file_id:
                    symbol_id = self._sqlite_store.store_symbol(
                        file_id,
                        symbol_info["symbol"],
                        symbol_info["kind"],
                        symbol_info["line"],
                        symbol_info["span"][1],
                        signature=symbol_info["signature"],
                    )
                    self._indexer.add_symbol(
                        symbol_info["symbol"],
                        str(path),
                        symbol_info["line"],
                        {"symbol_id": symbol_id, "file_id": file_id},
                    )

        # Extract enum definitions
        for node in self._find_nodes(root, "enum_specifier"):
            symbol_info = self._extract_enum(node, content)
            if symbol_info:
                symbols.append(symbol_info)

                if self._sqlite_store and file_id:
                    symbol_id = self._sqlite_store.store_symbol(
                        file_id,
                        symbol_info["symbol"],
                        symbol_info["kind"],
                        symbol_info["line"],
                        symbol_info["span"][1],
                        signature=symbol_info["signature"],
                    )
                    self._indexer.add_symbol(
                        symbol_info["symbol"],
                        str(path),
                        symbol_info["line"],
                        {"symbol_id": symbol_id, "file_id": file_id},
                    )

        # Extract typedefs (returns a list per node)
        for node in self._find_nodes(root, "type_definition"):
            for symbol_info in self._extract_typedef(node, content):
                symbols.append(symbol_info)

                if self._sqlite_store and file_id:
                    symbol_id = self._sqlite_store.store_symbol(
                        file_id,
                        symbol_info["symbol"],
                        symbol_info["kind"],
                        symbol_info["line"],
                        symbol_info["span"][1],
                        signature=symbol_info["signature"],
                    )
                    self._indexer.add_symbol(
                        symbol_info["symbol"],
                        str(path),
                        symbol_info["line"],
                        {"symbol_id": symbol_id, "file_id": file_id},
                    )

        # Extract macros
        for node in self._find_nodes(root, ["preproc_def", "preproc_function_def"]):
            symbol_info = self._extract_macro(node, content)
            if symbol_info:
                symbols.append(symbol_info)

                if self._sqlite_store and file_id:
                    symbol_id = self._sqlite_store.store_symbol(
                        file_id,
                        symbol_info["symbol"],
                        symbol_info["kind"],
                        symbol_info["line"],
                        symbol_info["span"][1],
                        signature=symbol_info["signature"],
                    )
                    self._indexer.add_symbol(
                        symbol_info["symbol"],
                        str(path),
                        symbol_info["line"],
                        {"symbol_id": symbol_id, "file_id": file_id},
                    )

        # Extract global variables
        for node in self._find_nodes(root, "declaration"):
            symbol_infos = self._extract_global_variables(node, content)
            for symbol_info in symbol_infos:
                symbols.append(symbol_info)

                if self._sqlite_store and file_id:
                    symbol_id = self._sqlite_store.store_symbol(
                        file_id,
                        symbol_info["symbol"],
                        symbol_info["kind"],
                        symbol_info["line"],
                        symbol_info["span"][1],
                        signature=symbol_info["signature"],
                    )
                    self._indexer.add_symbol(
                        symbol_info["symbol"],
                        str(path),
                        symbol_info["line"],
                        {"symbol_id": symbol_id, "file_id": file_id},
                    )

        # Extract includes
        includes = self._extract_includes(root, content)
        if (
            self._sqlite_store
            and file_id
            and includes
            and hasattr(self._sqlite_store, "store_import")
        ):
            for include in includes:
                # Store includes as imports
                self._sqlite_store.store_import(
                    file_id, include["path"], as_name=None, line=include["line"]
                )

        return {"file": str(path), "symbols": symbols, "language": self.lang}

    def _find_nodes(self, node, node_types):
        """Recursively find all nodes of the given type(s)."""
        if isinstance(node_types, str):
            node_types = [node_types]

        results = []
        if node.type in node_types:
            results.append(node)

        for child in node.children:
            results.extend(self._find_nodes(child, node_types))

        return results

    def _extract_function(self, node, content):
        """Extract function information from a function_definition node."""
        declarator = node.child_by_field_name("declarator")
        if not declarator:
            return None

        # Count pointer levels while unwrapping (e.g. char* get_string(void))
        ptr_stars = ""
        while declarator and declarator.type == "pointer_declarator":
            ptr_stars += "*"
            declarator = declarator.child_by_field_name("declarator")

        if not declarator or declarator.type != "function_declarator":
            return None

        # Get the function name
        name_node = declarator.child_by_field_name("declarator")
        while name_node and name_node.type == "pointer_declarator":
            name_node = name_node.child_by_field_name("declarator")

        if not name_node or name_node.type != "identifier":
            return None

        name = name_node.text.decode("utf-8")

        # Extract return type (include any qualifiers before type node)
        type_node = node.child_by_field_name("type")
        return_type = type_node.text.decode("utf-8") if type_node else "void"

        # Collect any type qualifiers (static, inline, const, etc.) before the type node
        qualifiers = []
        for child in node.children:
            if child == type_node:
                break
            if child.is_named and child.type in (
                "storage_class_specifier",
                "type_qualifier",
                "function_specifier",
            ):
                qualifiers.append(child.text.decode("utf-8"))

        if qualifiers:
            return_type = " ".join(qualifiers) + " " + return_type

        # Extract parameters
        params_node = declarator.child_by_field_name("parameters")
        params = params_node.text.decode("utf-8") if params_node else "()"

        # Build signature: return_type + pointer_stars + space + name + params
        signature = f"{return_type}{ptr_stars} {name}{params}"

        return {
            "symbol": name,
            "kind": "function",
            "signature": signature,
            "line": node.start_point[0] + 1,
            "span": (node.start_point[0] + 1, node.end_point[0] + 1),
        }

    def _extract_struct(self, node, content):
        """Extract struct information from a struct_specifier node."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return None

        name = name_node.text.decode("utf-8")

        return {
            "symbol": name,
            "kind": "struct",
            "signature": f"struct {name}",
            "line": node.start_point[0] + 1,
            "span": (node.start_point[0] + 1, node.end_point[0] + 1),
        }

    def _extract_enum(self, node, content):
        """Extract enum information from an enum_specifier node."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return None

        name = name_node.text.decode("utf-8")

        return {
            "symbol": name,
            "kind": "enum",
            "signature": f"enum {name}",
            "line": node.start_point[0] + 1,
            "span": (node.start_point[0] + 1, node.end_point[0] + 1),
        }

    def _resolve_typedef_name(self, declarator):
        """Walk a typedef declarator chain and return the type_identifier node, or None."""
        while declarator:
            t = declarator.type
            if t == "type_identifier":
                return declarator
            elif t in ("pointer_declarator", "array_declarator"):
                declarator = declarator.child_by_field_name("declarator")
            elif t == "function_declarator":
                # e.g. typedef int (*CompareFunc)(...) — look inside parenthesized_declarator
                inner = declarator.child_by_field_name("declarator")
                if inner and inner.type == "parenthesized_declarator":
                    declarator = inner
                else:
                    return None
            elif t == "parenthesized_declarator":
                # named children: pointer_declarator, etc.
                for child in declarator.named_children:
                    result = self._resolve_typedef_name(child)
                    if result:
                        return result
                return None
            else:
                return None
        return None

    def _extract_typedef(self, node, content):
        """Extract typedef information from a type_definition node. Returns a list."""
        results = []

        # Get the full typedef signature (bytes-safe)
        sig_bytes = node.text
        if sig_bytes:
            signature = sig_bytes.decode("utf-8").strip()
            if signature.endswith(";"):
                signature = signature[:-1]
        else:
            signature = "typedef ..."

        line = node.start_point[0] + 1
        span = (line, node.end_point[0] + 1)

        # Collect all declarator children (typedef may have multiple, e.g. "Node, *NodePtr")
        for i, child in enumerate(node.children):
            field = node.field_name_for_child(i)
            if field != "declarator":
                continue
            ident = self._resolve_typedef_name(child)
            if ident:
                name = ident.text.decode("utf-8")
                results.append(
                    {
                        "symbol": name,
                        "kind": "typedef",
                        "signature": signature,
                        "line": line,
                        "span": span,
                    }
                )

        return results

    def _extract_macro(self, node, content):
        """Extract macro information from preprocessor definition nodes."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return None

        name = name_node.text.decode("utf-8")

        # Build signature
        signature = f"#define {name}"

        # For function-like macros, add parameters
        if node.type == "preproc_function_def":
            params_node = node.child_by_field_name("parameters")
            if params_node:
                params = params_node.text.decode("utf-8")
                signature += params

        return {
            "symbol": name,
            "kind": "macro",
            "signature": signature,
            "line": node.start_point[0] + 1,
            "span": (node.start_point[0] + 1, node.end_point[0] + 1),
        }

    def _unwrap_declarator_name(self, declarator):
        """Walk a variable declarator chain and return the identifier node, or None."""
        while declarator:
            t = declarator.type
            if t == "identifier":
                return declarator
            elif t in ("pointer_declarator", "array_declarator"):
                declarator = declarator.child_by_field_name("declarator")
            elif t == "function_declarator":
                # array/pointer of function pointers: int (*ops[4])(...)
                inner = declarator.child_by_field_name("declarator")
                if inner and inner.type == "parenthesized_declarator":
                    for child in inner.named_children:
                        result = self._unwrap_declarator_name(child)
                        if result:
                            return result
                return None
            elif t == "parenthesized_declarator":
                for child in declarator.named_children:
                    result = self._unwrap_declarator_name(child)
                    if result:
                        return result
                return None
            else:
                return None
        return None

    def _extract_global_variables(self, node, content):
        """Extract global variable declarations."""
        # Skip if inside a function body
        parent = node.parent
        while parent:
            if parent.type == "function_definition":
                return []
            parent = parent.parent

        variables = []

        type_node = node.child_by_field_name("type")
        if not type_node:
            for child in node.children:
                if child.is_named and child.type not in (
                    "init_declarator",
                    "identifier",
                    "pointer_declarator",
                    "array_declarator",
                    "function_declarator",
                    "parenthesized_declarator",
                ):
                    type_node = child
                    break

        if not type_node:
            return variables

        var_type = type_node.text.decode("utf-8")

        # Collect all declarators (direct children that aren't the type or punctuation)
        skip_types = {type_node.type, ",", ";", "typedef"}
        declarator_nodes = []
        for child in node.children:
            if not child.is_named:
                continue
            if child.type in skip_types or child == type_node:
                continue
            declarator_nodes.append(child)

        if not declarator_nodes:
            return variables

        for declarator in declarator_nodes:
            # Unwrap init_declarator
            if declarator.type == "init_declarator":
                declarator = declarator.child_by_field_name("declarator")

            ident = self._unwrap_declarator_name(declarator) if declarator else None
            if ident:
                name = ident.text.decode("utf-8")
                variables.append(
                    {
                        "symbol": name,
                        "kind": "variable",
                        "signature": f"{var_type} {name}",
                        "line": node.start_point[0] + 1,
                        "span": (node.start_point[0] + 1, node.end_point[0] + 1),
                    }
                )

        return variables

    def _extract_includes(self, root, content):
        """Extract #include directives for dependency tracking."""
        includes = []
        for node in self._find_nodes(root, "preproc_include"):
            path_node = node.child_by_field_name("path")
            if path_node:
                include_path = path_node.text.decode("utf-8")
                includes.append(
                    {
                        "path": include_path.strip('"<>'),
                        "is_system": include_path.startswith("<"),
                        "line": node.start_point[0] + 1,
                    }
                )
        return includes

    def getDefinition(self, symbol: str) -> SymbolDef | None:
        """Return the definition of a symbol, if known."""
        # First try SQLite if available
        if self._sqlite_store:
            results = self._sqlite_store.search_symbols_fuzzy(symbol, limit=1)
            if results and results[0]["name"] == symbol:
                result = results[0]
                line = result.get("line_start") or result.get("line", 0)
                end_line = result.get("line_end") or result.get("end_line", line)
                return {
                    "symbol": result["name"],
                    "kind": result["kind"],
                    "language": self.lang,
                    "signature": result.get("signature", ""),
                    "doc": None,  # C doesn't have docstrings like Python
                    "defined_in": result["file_path"],
                    "line": line,
                    "span": (line, end_line),
                }
            # SQLite is authoritative when available — no filesystem fallback
            return None

        # Fall back to searching through parsed files
        for path in Path(".").rglob("*.c"):
            try:
                content = path.read_text()
                tree = self._parser.parse(content.encode("utf-8"))
                root = tree.root_node

                # Search for function definitions
                for node in self._find_nodes(root, "function_definition"):
                    func_info = self._extract_function(node, content)
                    if func_info and func_info["symbol"] == symbol:
                        return {
                            "symbol": symbol,
                            "kind": "function",
                            "language": self.lang,
                            "signature": func_info["signature"],
                            "doc": None,
                            "defined_in": str(path),
                            "line": func_info["line"],
                            "span": func_info["span"],
                        }

                # Search for other symbol types
                for node_type, extractor, kind in [
                    ("struct_specifier", self._extract_struct, "struct"),
                    ("enum_specifier", self._extract_enum, "enum"),
                    (
                        ["preproc_def", "preproc_function_def"],
                        self._extract_macro,
                        "macro",
                    ),
                ]:
                    for node in self._find_nodes(root, node_type):
                        info = extractor(node, content)
                        if info and info["symbol"] == symbol:
                            return {
                                "symbol": symbol,
                                "kind": kind,
                                "language": self.lang,
                                "signature": info["signature"],
                                "doc": None,
                                "defined_in": str(path),
                                "line": info["line"],
                                "span": info["span"],
                            }

                # Typedef extraction returns a list
                for node in self._find_nodes(root, "type_definition"):
                    for info in self._extract_typedef(node, content):
                        if info["symbol"] == symbol:
                            return {
                                "symbol": symbol,
                                "kind": "typedef",
                                "language": self.lang,
                                "signature": info["signature"],
                                "doc": None,
                                "defined_in": str(path),
                                "line": info["line"],
                                "span": info["span"],
                            }

            except Exception as e:
                logger.error(f"Error searching {path}: {e}")
                continue

        # Also check header files
        for path in Path(".").rglob("*.h"):
            try:
                content = path.read_text()
                tree = self._parser.parse(content.encode("utf-8"))
                root = tree.root_node

                # Same search logic as above
                for node in self._find_nodes(root, "function_definition"):
                    func_info = self._extract_function(node, content)
                    if func_info and func_info["symbol"] == symbol:
                        return {
                            "symbol": symbol,
                            "kind": "function",
                            "language": self.lang,
                            "signature": func_info["signature"],
                            "doc": None,
                            "defined_in": str(path),
                            "line": func_info["line"],
                            "span": func_info["span"],
                        }

            except Exception as e:
                logger.error(f"Error searching header {path}: {e}")
                continue

        return None

    def findReferences(self, symbol: str) -> list[Reference]:
        """List all references to a symbol."""
        refs = []
        seen = set()

        def _search_in(path_str: str, content: str, tree) -> None:
            root = tree.root_node
            for node in self._find_nodes(root, "identifier"):
                if node.text.decode("utf-8") == symbol:
                    line = node.start_point[0] + 1
                    key = (path_str, line)
                    if key not in seen:
                        refs.append(Reference(file=path_str, line=line))
                        seen.add(key)
            for node in self._find_nodes(root, "type_identifier"):
                if node.text.decode("utf-8") == symbol:
                    line = node.start_point[0] + 1
                    key = (path_str, line)
                    if key not in seen:
                        refs.append(Reference(file=path_str, line=line))
                        seen.add(key)

        if self._parsed_files:
            # Use already-parsed files (avoids filesystem scan in tests and after indexing)
            for path_str, (content, tree) in self._parsed_files.items():
                try:
                    _search_in(path_str, content, tree)
                except Exception as e:
                    logger.error(f"Error finding references in {path_str}: {e}")
        else:
            # Fall back to filesystem scan
            for ext in ["*.c", "*.h"]:
                for path in Path(".").rglob(ext):
                    try:
                        content = path.read_text()
                        tree = self._parser.parse(content.encode("utf-8"))
                        _search_in(str(path), content, tree)
                    except Exception as e:
                        logger.error(f"Error finding references in {path}: {e}")

        return refs

    def search(self, query: str, opts: SearchOpts | None = None) -> Iterable[SearchResult]:
        """Search for symbols matching a query."""
        limit = 20
        if opts and "limit" in opts:
            limit = opts["limit"]
        if opts and opts.get("semantic"):
            return []  # Semantic search not supported yet

        # When SQLite is available, use symbol search for better precision
        if self._sqlite_store:
            raw = self._indexer.search_symbols(query, limit=limit)
            results = []
            for r in raw:
                results.append(
                    {
                        "symbol": r.get("name") or r.get("symbol", ""),
                        "file": r.get("file_path", ""),
                        "line": r.get("line_start") or r.get("line", 0),
                        "snippet": r.get("signature", ""),
                    }
                )
            return results

        return self._indexer.search(query, limit=limit)

    def get_indexed_count(self) -> int:
        """Return the number of indexed files."""
        if hasattr(self._indexer, "_file_contents"):
            return len(self._indexer._file_contents)
        return len(self._parsed_files)
