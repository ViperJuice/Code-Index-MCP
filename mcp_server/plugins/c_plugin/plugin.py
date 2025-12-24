from __future__ import annotations

import ctypes
import logging
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
        lib_path = Path(tree_sitter_languages.__path__[0]) / "languages.so"
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

        self._preindex()

    def _preindex(self) -> None:
        """Pre-index all C/H files in the current directory."""
        for ext in ["*.c", "*.h"]:
            for path in Path(".").rglob(ext):
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
            file_id = self._sqlite_store.store_file(
                self._repository_id,
                str(path),
                str(path.relative_to(Path.cwd())),
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

        # Extract typedefs
        for node in self._find_nodes(root, "type_definition"):
            symbol_info = self._extract_typedef(node, content)
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
        if self._sqlite_store and file_id and includes:
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

        # Handle function declarators, which may be wrapped in pointer declarators
        while declarator and declarator.type == "pointer_declarator":
            declarator = declarator.child_by_field_name("declarator")

        if not declarator or declarator.type != "function_declarator":
            return None

        # Get the function name
        name_node = declarator.child_by_field_name("declarator")
        while name_node and name_node.type == "pointer_declarator":
            name_node = name_node.child_by_field_name("declarator")

        if not name_node or name_node.type != "identifier":
            return None

        name = content[name_node.start_byte : name_node.end_byte]

        # Extract return type
        type_node = node.child_by_field_name("type")
        return_type = content[type_node.start_byte : type_node.end_byte] if type_node else "void"

        # Extract parameters
        params_node = declarator.child_by_field_name("parameters")
        params = content[params_node.start_byte : params_node.end_byte] if params_node else "()"

        # Build signature
        signature = f"{return_type} {name}{params}"

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

        name = content[name_node.start_byte : name_node.end_byte]

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

        name = content[name_node.start_byte : name_node.end_byte]

        return {
            "symbol": name,
            "kind": "enum",
            "signature": f"enum {name}",
            "line": node.start_point[0] + 1,
            "span": (node.start_point[0] + 1, node.end_point[0] + 1),
        }

    def _extract_typedef(self, node, content):
        """Extract typedef information from a type_definition node."""
        declarator = node.child_by_field_name("declarator")
        if not declarator:
            return None

        # Handle various declarator types
        while declarator and declarator.type in [
            "pointer_declarator",
            "array_declarator",
        ]:
            declarator = declarator.child_by_field_name("declarator")

        if not declarator or declarator.type != "type_identifier":
            return None

        name = content[declarator.start_byte : declarator.end_byte]

        # Get the full typedef statement
        signature = content[node.start_byte : node.end_byte].strip()
        if signature.endswith(";"):
            signature = signature[:-1]

        return {
            "symbol": name,
            "kind": "typedef",
            "signature": signature,
            "line": node.start_point[0] + 1,
            "span": (node.start_point[0] + 1, node.end_point[0] + 1),
        }

    def _extract_macro(self, node, content):
        """Extract macro information from preprocessor definition nodes."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return None

        name = content[name_node.start_byte : name_node.end_byte]

        # Build signature
        signature = f"#define {name}"

        # For function-like macros, add parameters
        if node.type == "preproc_function_def":
            params_node = node.child_by_field_name("parameters")
            if params_node:
                params = content[params_node.start_byte : params_node.end_byte]
                signature += params

        return {
            "symbol": name,
            "kind": "macro",
            "signature": signature,
            "line": node.start_point[0] + 1,
            "span": (node.start_point[0] + 1, node.end_point[0] + 1),
        }

    def _extract_global_variables(self, node, content):
        """Extract global variable declarations."""
        # Skip function declarations and definitions
        if any(child.type == "function_declarator" for child in node.children):
            return []

        # Skip if inside a function body
        parent = node.parent
        while parent:
            if parent.type == "function_definition":
                return []
            parent = parent.parent

        variables = []

        # Find all declarators in this declaration
        declarators = self._find_nodes(node, "init_declarator")
        if not declarators:
            # Try direct declarators
            declarators = [child for child in node.children if child.type == "identifier"]

        type_node = node.child_by_field_name("type")
        if not type_node:
            # Find the type by looking at the first non-declarator child
            for child in node.children:
                if child.type not in ["init_declarator", "identifier", ",", ";"]:
                    type_node = child
                    break

        if not type_node:
            return variables

        var_type = content[type_node.start_byte : type_node.end_byte]

        for declarator in declarators:
            # Handle init_declarator
            if declarator.type == "init_declarator":
                declarator = declarator.child_by_field_name("declarator")

            # Handle pointer declarators
            while declarator and declarator.type == "pointer_declarator":
                declarator = declarator.child_by_field_name("declarator")

            if declarator and declarator.type == "identifier":
                name = content[declarator.start_byte : declarator.end_byte]
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
                include_path = content[path_node.start_byte : path_node.end_byte]
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
                return {
                    "symbol": result["name"],
                    "kind": result["kind"],
                    "language": self.lang,
                    "signature": result.get("signature", ""),
                    "doc": None,  # C doesn't have docstrings like Python
                    "defined_in": result["file_path"],
                    "line": result["line"],
                    "span": (result["line"], result.get("end_line", result["line"])),
                }

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
                    ("type_definition", self._extract_typedef, "typedef"),
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

        # Search all C and H files
        for ext in ["*.c", "*.h"]:
            for path in Path(".").rglob(ext):
                try:
                    content = path.read_text()
                    tree = self._parser.parse(content.encode("utf-8"))
                    root = tree.root_node

                    # Find all identifier nodes that match the symbol
                    for node in self._find_nodes(root, "identifier"):
                        if content[node.start_byte : node.end_byte] == symbol:
                            line = node.start_point[0] + 1
                            key = (str(path), line)
                            if key not in seen:
                                refs.append(Reference(file=str(path), line=line))
                                seen.add(key)

                    # Also check type_identifier nodes (for typedefs)
                    for node in self._find_nodes(root, "type_identifier"):
                        if content[node.start_byte : node.end_byte] == symbol:
                            line = node.start_point[0] + 1
                            key = (str(path), line)
                            if key not in seen:
                                refs.append(Reference(file=str(path), line=line))
                                seen.add(key)

                except Exception as e:
                    logger.error(f"Error finding references in {path}: {e}")
                    continue

        return refs

    def search(self, query: str, opts: SearchOpts | None = None) -> Iterable[SearchResult]:
        """Search for code snippets matching a query."""
        limit = 20
        if opts and "limit" in opts:
            limit = opts["limit"]
        if opts and opts.get("semantic"):
            return []  # Semantic search not supported yet
        return self._indexer.search(query, limit=limit)

    def get_indexed_count(self) -> int:
        """Return the number of indexed files."""
        if hasattr(self._indexer, "_file_contents"):
            return len(self._indexer._file_contents)
        return len(self._parsed_files)
