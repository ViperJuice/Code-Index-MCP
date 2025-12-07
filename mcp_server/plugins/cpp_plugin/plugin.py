from __future__ import annotations

import ctypes
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

import tree_sitter_languages
from tree_sitter import Language, Node, Parser

from ...interfaces.plugin_interfaces import (
    ICppPlugin,
    ILanguageAnalyzer,
    IndexedFile,
)
from ...interfaces.plugin_interfaces import SearchResult as InterfaceSearchResult
from ...interfaces.plugin_interfaces import (
    SymbolDefinition,
    SymbolReference,
)
from ...interfaces.shared_interfaces import Error, Result
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


class Plugin(IPlugin, ICppPlugin, ILanguageAnalyzer):
    """C++ language plugin for code intelligence."""

    lang = "cpp"

    def __init__(self, sqlite_store: Optional[SQLiteStore] = None) -> None:
        """Initialize the C++ plugin.

        Args:
            sqlite_store: Optional SQLite store for persistence
        """
        # Initialize parser
        self._parser = Parser()

        # Load C++ language grammar
        lib_path = Path(tree_sitter_languages.__path__[0]) / "languages.so"
        self._lib = ctypes.CDLL(str(lib_path))

        # Configure C++
        self._lib.tree_sitter_cpp.restype = ctypes.c_void_p
        self._language = Language(self._lib.tree_sitter_cpp())
        self._parser.language = self._language

        # Initialize indexer and storage
        self._indexer = FuzzyIndexer(sqlite_store=sqlite_store)
        self._sqlite_store = sqlite_store
        self._repository_id = None

        # State tracking
        self._current_file: Optional[Path] = None
        self._namespace_stack: List[str] = []

        # Symbol cache for faster lookups
        self._symbol_cache: Dict[str, List[SymbolDef]] = {}

        # Create or get repository if SQLite is enabled
        if self._sqlite_store:
            self._repository_id = self._sqlite_store.create_repository(
                str(Path.cwd()), Path.cwd().name, {"language": "cpp"}
            )

        # Pre-index existing files
        self._preindex()

    def _preindex(self) -> None:
        """Pre-index all supported files in the current directory."""
        patterns = [
            "*.cpp",
            "*.cc",
            "*.cxx",
            "*.c++",
            "*.hpp",
            "*.h",
            "*.hh",
            "*.h++",
            "*.hxx",
        ]
        for pattern in patterns:
            for path in Path(".").rglob(pattern):
                try:
                    # Skip common build directories
                    if any(
                        part in path.parts
                        for part in [
                            "build",
                            "cmake-build",
                            "out",
                            "bin",
                            "obj",
                            ".vscode",
                            ".idea",
                        ]
                    ):
                        continue

                    text = path.read_text(encoding="utf-8")
                    self._indexer.add_file(str(path), text)
                except Exception as e:
                    logger.warning(f"Failed to pre-index {path}: {e}")
                    continue

    def supports(self, path: str | Path) -> bool:
        """Check if this plugin supports the given file."""
        suffixes = {".cpp", ".cc", ".cxx", ".c++", ".hpp", ".h", ".hh", ".h++", ".hxx"}
        return Path(path).suffix.lower() in suffixes

    def indexFile(self, path: str | Path, content: str) -> IndexShard:
        """Parse and index a C++ file."""
        if isinstance(path, str):
            path = Path(path)

        self._current_file = path
        self._indexer.add_file(str(path), content)

        # Parse the file
        tree = self._parser.parse(content.encode("utf-8"))
        root = tree.root_node

        # Store file in SQLite if available
        file_id = None
        if self._sqlite_store and self._repository_id:
            import hashlib

            file_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            file_id = self._sqlite_store.store_file(
                self._repository_id,
                str(path),
                str(path.relative_to(Path.cwd())),
                language="cpp",
                size=len(content),
                hash=file_hash,
            )

        # Extract symbols
        symbols: List[Dict[str, Any]] = []
        self._namespace_stack = []
        self._extract_symbols(root, content, symbols, file_id)

        # Cache symbols for quick lookup
        cache_key = str(path)
        self._symbol_cache[cache_key] = [
            self._symbol_to_def(s, str(path), content) for s in symbols
        ]

        return {"file": str(path), "symbols": symbols, "language": self.lang}

    def _extract_symbols(
        self,
        node: Node,
        content: str,
        symbols: List[Dict],
        file_id: Optional[int] = None,
    ) -> None:
        """Recursively extract symbols from the AST."""
        # Handle template declarations specially
        if node.type == "template_declaration":
            # Process the declaration inside the template
            # The inner declaration (class/function) will be handled by the regular logic
            # but we need to ensure it detects the template properly
            pass  # Don't return, let it fall through to process children normally

        # Namespace handling
        elif node.type == "namespace_definition":
            name_node = node.child_by_field_name("name")
            if name_node:
                namespace_name = content[name_node.start_byte : name_node.end_byte]
                self._namespace_stack.append(namespace_name)

                # Add namespace as a symbol (use just the name, not qualified)
                symbol_info = {
                    "symbol": namespace_name,  # Don't qualify namespace names
                    "kind": "namespace",
                    "signature": f"namespace {namespace_name}",
                    "line": node.start_point[0] + 1,
                    "span": (node.start_point[0] + 1, node.end_point[0] + 1),
                }
                symbols.append(symbol_info)

                # Store in SQLite if available
                if self._sqlite_store and file_id:
                    symbol_id = self._sqlite_store.store_symbol(
                        file_id,
                        namespace_name,  # Don't qualify namespace names
                        "namespace",
                        node.start_point[0] + 1,
                        node.end_point[0] + 1,
                        signature=f"namespace {namespace_name}",
                    )
                    self._indexer.add_symbol(
                        namespace_name,
                        str(self._current_file),
                        node.start_point[0] + 1,
                        {"symbol_id": symbol_id, "file_id": file_id},
                    )

                # Process namespace body
                body_node = node.child_by_field_name("body")
                if body_node:
                    for child in body_node.named_children:
                        self._extract_symbols(child, content, symbols, file_id)

                self._namespace_stack.pop()
                return

        # Function declarations and definitions
        elif node.type in ["function_declaration", "function_definition"]:
            declarator = node.child_by_field_name("declarator")
            if declarator:
                name = self._extract_function_name(declarator, content)
                if name:
                    params = self._extract_parameters(declarator, content)
                    return_type = self._extract_return_type(node, content)
                    is_template = self._has_template_parameters(node, content)
                    template_params = (
                        self._extract_template_parameters(node, content) if is_template else ""
                    )

                    signature = f"{template_params}{return_type} {name}({params})"

                    symbol_info = {
                        "symbol": self._get_qualified_name(name),
                        "kind": "function",
                        "signature": signature.strip(),
                        "line": node.start_point[0] + 1,
                        "span": (node.start_point[0] + 1, node.end_point[0] + 1),
                        "is_template": is_template,
                    }
                    symbols.append(symbol_info)

                    # Store in SQLite if available
                    if self._sqlite_store and file_id:
                        symbol_id = self._sqlite_store.store_symbol(
                            file_id,
                            self._get_qualified_name(name),
                            "function",
                            node.start_point[0] + 1,
                            node.end_point[0] + 1,
                            signature=signature.strip(),
                        )
                        self._indexer.add_symbol(
                            self._get_qualified_name(name),
                            str(self._current_file),
                            node.start_point[0] + 1,
                            {"symbol_id": symbol_id, "file_id": file_id},
                        )

        # Class/struct/union declarations
        elif node.type in ["class_specifier", "struct_specifier", "union_specifier"]:
            name_node = node.child_by_field_name("name")
            if name_node:
                name = content[name_node.start_byte : name_node.end_byte]
                kind = node.type.replace("_specifier", "")
                # Check for template in parent or current node
                is_template = self._has_template_parameters(node, content) or (
                    node.parent and self._has_template_parameters(node.parent, content)
                )
                template_params = ""
                if is_template:
                    template_params = (
                        self._extract_template_parameters(node, content)
                        or (node.parent and self._extract_template_parameters(node.parent, content))
                        or ""
                    )
                base_classes = self._extract_base_classes(node, content)

                signature = f"{template_params}{kind} {name}"
                if base_classes:
                    signature += f" : {', '.join(base_classes)}"

                symbol_info = {
                    "symbol": self._get_qualified_name(name),
                    "kind": kind,
                    "signature": signature.strip(),
                    "line": node.start_point[0] + 1,
                    "span": (node.start_point[0] + 1, node.end_point[0] + 1),
                    "is_template": is_template,
                }
                symbols.append(symbol_info)

                # Store in SQLite if available
                if self._sqlite_store and file_id:
                    symbol_id = self._sqlite_store.store_symbol(
                        file_id,
                        self._get_qualified_name(name),
                        kind,
                        node.start_point[0] + 1,
                        node.end_point[0] + 1,
                        signature=signature.strip(),
                    )
                    self._indexer.add_symbol(
                        self._get_qualified_name(name),
                        str(self._current_file),
                        node.start_point[0] + 1,
                        {"symbol_id": symbol_id, "file_id": file_id},
                    )

                # Process class/struct/union body
                body_node = node.child_by_field_name("body")
                if body_node:
                    self._namespace_stack.append(name)
                    for child in body_node.named_children:
                        self._extract_class_members(child, content, symbols, file_id)
                    self._namespace_stack.pop()

        # Enum declarations
        elif node.type == "enum_specifier":
            name_node = node.child_by_field_name("name")
            if name_node:
                name = content[name_node.start_byte : name_node.end_byte]
                is_scoped = self._is_enum_class(node, content)

                signature = f"enum{'class' if is_scoped else ''} {name}"

                symbol_info = {
                    "symbol": self._get_qualified_name(name),
                    "kind": "enum",
                    "signature": signature,
                    "line": node.start_point[0] + 1,
                    "span": (node.start_point[0] + 1, node.end_point[0] + 1),
                }
                symbols.append(symbol_info)

                # Store in SQLite if available
                if self._sqlite_store and file_id:
                    symbol_id = self._sqlite_store.store_symbol(
                        file_id,
                        self._get_qualified_name(name),
                        "enum",
                        node.start_point[0] + 1,
                        node.end_point[0] + 1,
                        signature=signature,
                    )
                    self._indexer.add_symbol(
                        self._get_qualified_name(name),
                        str(self._current_file),
                        node.start_point[0] + 1,
                        {"symbol_id": symbol_id, "file_id": file_id},
                    )

                # Extract enum values
                body_node = node.child_by_field_name("body")
                if body_node:
                    for child in body_node.named_children:
                        if child.type == "enumerator":
                            enum_name_node = child.child_by_field_name("name")
                            if enum_name_node:
                                enum_value = content[
                                    enum_name_node.start_byte : enum_name_node.end_byte
                                ]
                                enum_symbol_info = {
                                    "symbol": f"{self._get_qualified_name(name)}::{enum_value}",
                                    "kind": "enumerator",
                                    "signature": enum_value,
                                    "line": child.start_point[0] + 1,
                                }
                                symbols.append(enum_symbol_info)

        # Type aliases (typedef and using)
        elif node.type == "type_definition":
            declarator = node.child_by_field_name("declarator")
            if declarator:
                name = self._extract_typedef_name(declarator, content)
                if name:
                    type_spec = node.child_by_field_name("type")
                    type_str = (
                        content[type_spec.start_byte : type_spec.end_byte] if type_spec else "..."
                    )

                    signature = f"typedef {type_str} {name}"

                    symbol_info = {
                        "symbol": self._get_qualified_name(name),
                        "kind": "typedef",
                        "signature": signature,
                        "line": node.start_point[0] + 1,
                        "span": (node.start_point[0] + 1, node.end_point[0] + 1),
                    }
                    symbols.append(symbol_info)

        elif node.type == "alias_declaration":
            name_node = node.child_by_field_name("name")
            if name_node:
                name = content[name_node.start_byte : name_node.end_byte]
                value_node = node.child_by_field_name("value")
                value_str = (
                    content[value_node.start_byte : value_node.end_byte] if value_node else "..."
                )

                signature = f"using {name} = {value_str}"

                symbol_info = {
                    "symbol": self._get_qualified_name(name),
                    "kind": "type_alias",
                    "signature": signature,
                    "line": node.start_point[0] + 1,
                    "span": (node.start_point[0] + 1, node.end_point[0] + 1),
                }
                symbols.append(symbol_info)

        # Check for declaration nodes (function declarations without body)
        elif node.type == "declaration":
            # Check if this is a function declaration
            declarator = node.child_by_field_name("declarator")
            if declarator and declarator.type == "function_declarator":
                name = self._extract_function_name(declarator, content)
                if name:
                    params = self._extract_parameters(declarator, content)
                    return_type = self._extract_return_type(node, content)
                    is_template = self._has_template_parameters(node, content)
                    template_params = (
                        self._extract_template_parameters(node, content) if is_template else ""
                    )

                    signature = f"{template_params}{return_type} {name}({params})"

                    symbol_info = {
                        "symbol": self._get_qualified_name(name),
                        "kind": "function",
                        "signature": signature.strip(),
                        "line": node.start_point[0] + 1,
                        "span": (node.start_point[0] + 1, node.end_point[0] + 1),
                        "is_template": is_template,
                    }
                    symbols.append(symbol_info)

                    # Store in SQLite if available
                    if self._sqlite_store and file_id:
                        symbol_id = self._sqlite_store.store_symbol(
                            file_id,
                            self._get_qualified_name(name),
                            "function",
                            node.start_point[0] + 1,
                            node.end_point[0] + 1,
                            signature=signature.strip(),
                        )
                        self._indexer.add_symbol(
                            self._get_qualified_name(name),
                            str(self._current_file),
                            node.start_point[0] + 1,
                            {"symbol_id": symbol_id, "file_id": file_id},
                        )

        # Continue recursion for child nodes
        for child in node.named_children:
            # Skip if we already processed this node
            if child.type not in [
                "field_declaration_list",
                "declaration_list",
                "enumerator_list",
                "compound_statement",
            ]:
                self._extract_symbols(child, content, symbols, file_id)

    def _extract_class_members(
        self,
        node: Node,
        content: str,
        symbols: List[Dict],
        file_id: Optional[int] = None,
    ) -> None:
        """Extract members from within a class/struct/union."""
        # Field declarations (member variables)
        if node.type == "field_declaration":
            declarator = node.child_by_field_name("declarator")
            if declarator:
                name = self._extract_field_name(declarator, content)
                if name:
                    type_node = node.child_by_field_name("type")
                    type_str = (
                        content[type_node.start_byte : type_node.end_byte] if type_node else "auto"
                    )
                    is_static = self._has_storage_class(node, content, "static")

                    signature = f"{'static ' if is_static else ''}{type_str} {name}"

                    symbol_info = {
                        "symbol": self._get_qualified_name(name),
                        "kind": "field",
                        "signature": signature,
                        "line": node.start_point[0] + 1,
                        "span": (node.start_point[0] + 1, node.end_point[0] + 1),
                    }
                    symbols.append(symbol_info)

        # Method declarations and definitions
        elif node.type in ["function_declaration", "function_definition"]:
            declarator = node.child_by_field_name("declarator")
            if declarator:
                name = self._extract_function_name(declarator, content)
                if name:
                    params = self._extract_parameters(declarator, content)
                    return_type = self._extract_return_type(node, content)
                    is_const = self._is_const_method(declarator, content)
                    is_virtual = self._has_virtual_specifier(node, content)
                    is_static = self._has_storage_class(node, content, "static")
                    is_override = self._has_storage_class(node, content, "override")
                    is_template = self._has_template_parameters(node, content)
                    template_params = (
                        self._extract_template_parameters(node, content) if is_template else ""
                    )

                    # Check for constructor/destructor
                    class_name = self._namespace_stack[-1] if self._namespace_stack else ""
                    if name == class_name:
                        kind = "constructor"
                        signature = f"{template_params}{name}({params})"
                    elif name == f"~{class_name}":
                        kind = "destructor"
                        signature = f"{name}()"
                    else:
                        kind = "method"
                        modifiers = []
                        if is_virtual:
                            modifiers.append("virtual")
                        if is_static:
                            modifiers.append("static")
                        modifier_str = " ".join(modifiers) + " " if modifiers else ""
                        signature = f"{template_params}{modifier_str}{return_type} {name}({params})"
                        if is_const:
                            signature += " const"
                        if is_override:
                            signature += " override"

                    symbol_info = {
                        "symbol": self._get_qualified_name(name),
                        "kind": kind,
                        "signature": signature.strip(),
                        "line": node.start_point[0] + 1,
                        "span": (node.start_point[0] + 1, node.end_point[0] + 1),
                        "is_template": is_template,
                    }
                    symbols.append(symbol_info)

                    # Store in SQLite if available
                    if self._sqlite_store and file_id:
                        symbol_id = self._sqlite_store.store_symbol(
                            file_id,
                            self._get_qualified_name(name),
                            kind,
                            node.start_point[0] + 1,
                            node.end_point[0] + 1,
                            signature=signature.strip(),
                        )
                        self._indexer.add_symbol(
                            self._get_qualified_name(name),
                            str(self._current_file),
                            node.start_point[0] + 1,
                            {"symbol_id": symbol_id, "file_id": file_id},
                        )

        # Access specifiers (public, private, protected)
        elif node.type == "access_specifier":
            # Just note the access level change, don't add as symbol
            pass

        # Nested classes/structs
        elif node.type in ["class_specifier", "struct_specifier", "union_specifier"]:
            self._extract_symbols(node, content, symbols, file_id)

        # Continue recursion
        else:
            for child in node.named_children:
                self._extract_class_members(child, content, symbols, file_id)

    def _get_qualified_name(self, name: str) -> str:
        """Get the fully qualified name including namespace."""
        if self._namespace_stack:
            return "::".join(self._namespace_stack + [name])
        return name

    def _extract_function_name(self, declarator: Node, content: str) -> Optional[str]:
        """Extract function name from declarator."""
        if declarator.type == "function_declarator":
            # For member functions, look for field_identifier
            for child in declarator.children:
                if child.type == "field_identifier":
                    return content[child.start_byte : child.end_byte]
            # Otherwise, look for the regular declarator
            child_declarator = declarator.child_by_field_name("declarator")
            if child_declarator:
                return self._extract_function_name(child_declarator, content)
        elif declarator.type == "pointer_declarator":
            # Skip pointer and get the actual declarator
            child_declarator = declarator.child_by_field_name("declarator")
            if child_declarator:
                return self._extract_function_name(child_declarator, content)
        elif declarator.type == "reference_declarator":
            # Skip reference and get the actual declarator
            child_declarator = declarator.child_by_field_name("declarator")
            if child_declarator:
                return self._extract_function_name(child_declarator, content)
        elif declarator.type == "identifier":
            return content[declarator.start_byte : declarator.end_byte]
        elif declarator.type == "field_identifier":
            return content[declarator.start_byte : declarator.end_byte]
        elif declarator.type == "qualified_identifier":
            # Handle qualified names like Class::method
            name_node = declarator.child_by_field_name("name")
            if name_node:
                return content[name_node.start_byte : name_node.end_byte]
        elif declarator.type == "destructor_name":
            return content[declarator.start_byte : declarator.end_byte]
        elif declarator.type == "operator_name":
            return content[declarator.start_byte : declarator.end_byte]

        return None

    def _extract_field_name(self, declarator: Node, content: str) -> Optional[str]:
        """Extract field name from declarator."""
        if declarator.type == "pointer_declarator":
            # Skip pointer and get the actual declarator
            child_declarator = declarator.child_by_field_name("declarator")
            if child_declarator:
                return self._extract_field_name(child_declarator, content)
        elif declarator.type == "array_declarator":
            # Skip array and get the actual declarator
            child_declarator = declarator.child_by_field_name("declarator")
            if child_declarator:
                return self._extract_field_name(child_declarator, content)
        elif declarator.type == "identifier":
            return content[declarator.start_byte : declarator.end_byte]
        elif declarator.type == "field_identifier":
            return content[declarator.start_byte : declarator.end_byte]

        return None

    def _extract_typedef_name(self, declarator: Node, content: str) -> Optional[str]:
        """Extract typedef name from declarator."""
        if declarator.type == "type_identifier":
            return content[declarator.start_byte : declarator.end_byte]
        elif declarator.type == "pointer_declarator":
            # Skip pointer and get the actual declarator
            child_declarator = declarator.child_by_field_name("declarator")
            if child_declarator:
                return self._extract_typedef_name(child_declarator, content)
        elif declarator.type == "function_declarator":
            # Function pointer typedef
            child_declarator = declarator.child_by_field_name("declarator")
            if child_declarator:
                return self._extract_typedef_name(child_declarator, content)
        elif declarator.type == "identifier":
            return content[declarator.start_byte : declarator.end_byte]

        return None

    def _extract_parameters(self, declarator: Node, content: str) -> str:
        """Extract function parameters as a string."""
        if declarator.type == "function_declarator":
            params_node = declarator.child_by_field_name("parameters")
            if params_node:
                params = []
                for child in params_node.named_children:
                    if child.type == "parameter_declaration":
                        # Get parameter type
                        type_node = child.child_by_field_name("type")
                        type_str = (
                            content[type_node.start_byte : type_node.end_byte] if type_node else ""
                        )

                        # Get parameter name if present
                        declarator_node = child.child_by_field_name("declarator")
                        if declarator_node:
                            param_name = self._extract_field_name(declarator_node, content)
                            if param_name:
                                params.append(f"{type_str} {param_name}")
                            else:
                                params.append(type_str)
                        else:
                            params.append(type_str)
                    elif child.type == "variadic_parameter":
                        params.append("...")

                return ", ".join(params)
        elif declarator.type == "qualified_identifier" or declarator.type == "identifier":
            # Look for parameters in parent node
            parent = declarator.parent
            if parent and parent.type == "function_declarator":
                return self._extract_parameters(parent, content)

        return ""

    def _extract_return_type(self, node: Node, content: str) -> str:
        """Extract function return type."""
        # Return type is usually before the declarator
        return_type_parts = []

        for child in node.children:
            if child == node.child_by_field_name("declarator"):
                break
            if child.type in [
                "primitive_type",
                "type_identifier",
                "qualified_identifier",
                "sized_type_specifier",
                "struct_specifier",
                "class_specifier",
                "enum_specifier",
                "union_specifier",
            ]:
                return_type_parts.append(content[child.start_byte : child.end_byte])
            elif child.type == "storage_class_specifier":
                # Skip storage class specifiers like static, virtual
                continue
            elif child.type == "virtual":
                # Skip virtual specifier for return type
                continue
            elif not child.is_named and child.type in ["const", "volatile"]:
                return_type_parts.append(content[child.start_byte : child.end_byte])

        return " ".join(return_type_parts) if return_type_parts else "void"

    def _extract_base_classes(self, node: Node, content: str) -> List[str]:
        """Extract base classes from class/struct declaration."""
        base_classes = []

        # Look for base_class_clause (not base_clause)
        for child in node.children:
            if child.type == "base_class_clause":
                # Parse the base classes
                for subchild in child.named_children:
                    if subchild.type in ["type_identifier", "qualified_identifier"]:
                        base_classes.append(content[subchild.start_byte : subchild.end_byte])
                    elif subchild.type == "access_specifier":
                        # Skip access specifiers like public/private/protected
                        continue

        return base_classes

    def _has_template_parameters(self, node: Node, content: str) -> bool:
        """Check if a declaration has template parameters."""
        if not node:
            return False

        # Look for template_declaration as parent
        parent = node.parent
        if parent and parent.type == "template_declaration":
            return True

        # Check if node itself is a template_declaration
        if node.type == "template_declaration":
            return True

        # Look for template parameters in previous siblings
        if node.parent:
            for i, child in enumerate(node.parent.children):
                if child == node:
                    break
                if child.type == "template_parameter_list":
                    return True

        return False

    def _extract_template_parameters(self, node: Node, content: str) -> str:
        """Extract template parameters."""
        if not node:
            return ""

        # If node itself is a template_declaration
        if node.type == "template_declaration":
            params_node = node.child_by_field_name("parameters")
            if params_node:
                return f"template<{content[params_node.start_byte+1:params_node.end_byte-1]}> "

        # Look for template_declaration as parent
        parent = node.parent
        if parent and parent.type == "template_declaration":
            params_node = parent.child_by_field_name("parameters")
            if params_node:
                return f"template<{content[params_node.start_byte+1:params_node.end_byte-1]}> "

        # Look for template parameters in previous siblings
        if node.parent:
            for i, child in enumerate(node.parent.children):
                if child == node:
                    break
                if child.type == "template_parameter_list":
                    return f"template<{content[child.start_byte+1:child.end_byte-1]}> "

        return ""

    def _is_const_method(self, declarator: Node, content: str) -> bool:
        """Check if a method is const."""
        if declarator.type == "function_declarator":
            # Look for type_qualifier child with 'const'
            for child in declarator.children:
                if child.type == "type_qualifier":
                    text = content[child.start_byte : child.end_byte].strip()
                    if text == "const":
                        return True
        return False

    def _has_storage_class(self, node: Node, content: str, storage_class: str) -> bool:
        """Check if a declaration has a specific storage class."""
        for child in node.children:
            if child.type == "storage_class_specifier":
                text = content[child.start_byte : child.end_byte].strip()
                if text == storage_class:
                    return True
            elif not child.is_named:
                text = content[child.start_byte : child.end_byte].strip()
                if text == storage_class:
                    return True
        return False

    def _has_virtual_specifier(self, node: Node, content: str) -> bool:
        """Check if a function has virtual specifier."""
        for child in node.children:
            if child.type == "virtual":
                return True
        return False

    def _is_enum_class(self, node: Node, content: str) -> bool:
        """Check if an enum is a scoped enum (enum class)."""
        # Look for 'class' keyword after 'enum'
        found_enum = False
        for child in node.children:
            if not child.is_named:
                text = content[child.start_byte : child.end_byte].strip()
                if text == "enum":
                    found_enum = True
                elif found_enum and text == "class":
                    return True
        return False

    def _walk_tree(self, node: Node) -> List[Node]:
        """Walk the tree and yield all nodes."""
        nodes = [node]
        for child in node.children:
            nodes.extend(self._walk_tree(child))
        return nodes

    def _symbol_to_def(self, symbol: Dict[str, Any], file_path: str, content: str) -> SymbolDef:
        """Convert internal symbol representation to SymbolDef."""
        # Extract documentation if available
        doc = None
        if "line" in symbol:
            # Try to extract documentation comment above the symbol
            lines = content.splitlines()
            line_idx = symbol["line"] - 1
            if line_idx > 0:
                # Look for C++ style comments
                doc_lines = []

                # Check for /// or //! style comments
                for i in range(line_idx - 1, max(0, line_idx - 10), -1):
                    line = lines[i].strip()
                    if line.startswith("///") or line.startswith("//!"):
                        doc_lines.insert(0, line[3:].strip())
                    elif not line or not line.startswith("//"):
                        break

                if doc_lines:
                    doc = "\n".join(doc_lines)
                else:
                    # Look for /** */ style comments
                    for i in range(line_idx - 1, max(0, line_idx - 20), -1):
                        line = lines[i].strip()
                        if line.endswith("*/"):
                            # Found end of block comment, extract it
                            comment_lines = []
                            for j in range(i, max(0, i - 50), -1):
                                comment_lines.insert(0, lines[j])
                                if lines[j].strip().startswith("/**"):
                                    # Parse the comment
                                    comment = "\n".join(comment_lines)
                                    # Remove comment markers
                                    comment = re.sub(r"^\s*\*/?", "", comment, flags=re.MULTILINE)
                                    doc = comment.strip()
                                    break
                            break

        return {
            "symbol": symbol["symbol"],
            "kind": symbol["kind"],
            "language": self.lang,
            "signature": symbol["signature"],
            "doc": doc,
            "defined_in": file_path,
            "line": symbol.get("line", 1),
            "span": symbol.get("span", (symbol.get("line", 1), symbol.get("line", 1) + 1)),
        }

    def getDefinition(self, symbol: str) -> SymbolDef | None:
        """Get the definition of a symbol."""
        # First check cache
        for file_path, symbols in self._symbol_cache.items():
            for sym_def in symbols:
                if sym_def["symbol"] == symbol or sym_def["symbol"].endswith(f"::{symbol}"):
                    return sym_def

        # Search in all supported files
        patterns = [
            "*.cpp",
            "*.cc",
            "*.cxx",
            "*.c++",
            "*.hpp",
            "*.h",
            "*.hh",
            "*.h++",
            "*.hxx",
        ]
        for pattern in patterns:
            for path in Path(".").rglob(pattern):
                try:
                    # Skip build directories
                    if any(
                        part in path.parts for part in ["build", "cmake-build", "out", "bin", "obj"]
                    ):
                        continue

                    content = path.read_text(encoding="utf-8")
                    shard = self.indexFile(path, content)

                    for sym in shard["symbols"]:
                        if sym["symbol"] == symbol or sym["symbol"].endswith(f"::{symbol}"):
                            return self._symbol_to_def(sym, str(path), content)
                except Exception:
                    continue

        return None

    def findReferences(self, symbol: str) -> list[Reference]:
        """Find all references to a symbol."""
        refs: List[Reference] = []
        seen: Set[Tuple[str, int]] = set()

        # Search in all supported files
        patterns = [
            "*.cpp",
            "*.cc",
            "*.cxx",
            "*.c++",
            "*.hpp",
            "*.h",
            "*.hh",
            "*.h++",
            "*.hxx",
        ]
        for pattern in patterns:
            for path in Path(".").rglob(pattern):
                try:
                    # Skip build directories
                    if any(
                        part in path.parts for part in ["build", "cmake-build", "out", "bin", "obj"]
                    ):
                        continue

                    content = path.read_text(encoding="utf-8")

                    # Simple text search for references
                    lines = content.splitlines()
                    for i, line in enumerate(lines):
                        # Look for whole word matches
                        # Handle qualified names
                        patterns_to_check = [symbol]
                        if "::" in symbol:
                            # Also check for just the last part
                            patterns_to_check.append(symbol.split("::")[-1])

                        for pattern_str in patterns_to_check:
                            pattern = r"\b" + re.escape(pattern_str) + r"\b"
                            if re.search(pattern, line):
                                line_no = i + 1
                                key = (str(path), line_no)
                                if key not in seen:
                                    refs.append(Reference(file=str(path), line=line_no))
                                    seen.add(key)
                                    break
                except Exception:
                    continue

        return refs

    def search(self, query: str, opts: SearchOpts | None = None) -> Iterable[SearchResult]:
        """Search for code snippets matching a query."""
        limit = 20
        if opts and "limit" in opts:
            limit = opts["limit"]

        # Semantic search not implemented yet
        if opts and opts.get("semantic"):
            return []

        # Use fuzzy indexer for search
        return self._indexer.search(query, limit=limit)

    def get_indexed_count(self) -> int:
        """Return the number of indexed files."""
        # Count unique files in the symbol cache
        return len(self._symbol_cache)

    # ========================================
    # ICppPlugin Interface Implementation
    # ========================================

    @property
    def name(self) -> str:
        """Get the plugin name"""
        return "C++ Plugin"

    @property
    def supported_extensions(self) -> List[str]:
        """Get list of file extensions this plugin supports"""
        return [".cpp", ".cc", ".cxx", ".c++", ".hpp", ".h", ".hh", ".h++", ".hxx"]

    @property
    def supported_languages(self) -> List[str]:
        """Get list of programming languages this plugin supports"""
        return ["cpp", "c++"]

    def can_handle(self, file_path: str) -> bool:
        """Check if this plugin can handle the given file"""
        return self.supports(file_path)

    def index(self, file_path: str, content: Optional[str] = None) -> Result[IndexedFile]:
        """Index a file and extract symbols"""
        try:
            if content is None:
                content = Path(file_path).read_text(encoding="utf-8")

            # Use existing indexFile method
            shard = self.indexFile(file_path, content)

            # Convert to IndexedFile format
            symbols = []
            for symbol_data in shard["symbols"]:
                symbol_def = SymbolDefinition(
                    symbol=symbol_data["symbol"],
                    file_path=file_path,
                    line=symbol_data.get("line", 1),
                    column=0,  # Tree-sitter doesn't provide column easily
                    symbol_type=symbol_data["kind"],
                    signature=symbol_data.get("signature"),
                    docstring=None,  # Will be extracted separately
                    scope=self._get_scope_from_symbol(symbol_data["symbol"]),
                )
                symbols.append(symbol_def)

            indexed_file = IndexedFile(
                file_path=file_path,
                last_modified=Path(file_path).stat().st_mtime,
                size=len(content),
                symbols=symbols,
                language=self.lang,
                encoding="utf-8",
            )

            return Result.success_result(indexed_file)

        except Exception as e:
            error = Error(
                code="CPP_INDEX_ERROR",
                message=f"Failed to index C++ file: {str(e)}",
                details={"file_path": file_path, "exception": str(e)},
                timestamp=datetime.now(),
            )
            return Result.error_result(error)

    def get_definition(
        self, symbol: str, context: Dict[str, Any]
    ) -> Result[Optional[SymbolDefinition]]:
        """Get the definition of a symbol"""
        try:
            definition = self.getDefinition(symbol)
            if definition is None:
                return Result.success_result(None)

            symbol_def = SymbolDefinition(
                symbol=definition["symbol"],
                file_path=definition["defined_in"],
                line=definition["line"],
                column=0,
                symbol_type=definition["kind"],
                signature=definition["signature"],
                docstring=definition.get("doc"),
                scope=self._get_scope_from_symbol(definition["symbol"]),
            )

            return Result.success_result(symbol_def)

        except Exception as e:
            error = Error(
                code="CPP_DEFINITION_ERROR",
                message=f"Failed to get definition: {str(e)}",
                details={"symbol": symbol, "exception": str(e)},
                timestamp=datetime.now(),
            )
            return Result.error_result(error)

    def get_references(self, symbol: str, context: Dict[str, Any]) -> Result[List[SymbolReference]]:
        """Get all references to a symbol"""
        try:
            references = self.findReferences(symbol)
            symbol_refs = [
                SymbolReference(
                    symbol=symbol,
                    file_path=ref.file,
                    line=ref.line,
                    column=0,
                    context=None,
                )
                for ref in references
            ]

            return Result.success_result(symbol_refs)

        except Exception as e:
            error = Error(
                code="CPP_REFERENCES_ERROR",
                message=f"Failed to find references: {str(e)}",
                details={"symbol": symbol, "exception": str(e)},
                timestamp=datetime.now(),
            )
            return Result.error_result(error)

    def search_with_result(
        self, query: str, options: Dict[str, Any]
    ) -> Result[List[InterfaceSearchResult]]:
        """Search for code patterns"""
        try:
            # Convert options to SearchOpts format
            opts = SearchOpts()
            if "limit" in options:
                opts["limit"] = options["limit"]
            if "semantic" in options:
                opts["semantic"] = options["semantic"]

            # Use the fuzzy indexer search method to avoid infinite recursion
            results = self._indexer.search(query, limit=options.get("limit", 20))

            search_results = [
                InterfaceSearchResult(
                    file_path=result["file"],
                    line=result["line"],
                    column=0,
                    snippet=result["snippet"],
                    match_type="fuzzy",
                    score=1.0,
                    context=None,
                )
                for result in results
            ]

            return Result.success_result(search_results)

        except Exception as e:
            error = Error(
                code="CPP_SEARCH_ERROR",
                message=f"Failed to search: {str(e)}",
                details={"query": query, "exception": str(e)},
                timestamp=datetime.now(),
            )
            return Result.error_result(error)

    def validate_syntax(self, content: str) -> Result[bool]:
        """Validate syntax of code content"""
        try:
            # Use Tree-sitter to parse and check for errors
            tree = self._parser.parse(content.encode("utf-8"))
            root = tree.root_node

            # Check for parse errors
            def has_errors(node: Node) -> bool:
                if node.has_error:
                    return True
                for child in node.children:
                    if has_errors(child):
                        return True
                return False

            is_valid = not has_errors(root)
            return Result.success_result(is_valid)

        except Exception as e:
            error = Error(
                code="CPP_SYNTAX_ERROR",
                message=f"Failed to validate syntax: {str(e)}",
                details={"exception": str(e)},
                timestamp=datetime.now(),
            )
            return Result.error_result(error)

    def get_completions(self, file_path: str, line: int, column: int) -> Result[List[str]]:
        """Get code completions at a position"""
        # Basic implementation - in a real plugin this would be more sophisticated
        try:
            completions = []

            # Add common C++ keywords
            cpp_keywords = [
                "class",
                "struct",
                "namespace",
                "template",
                "typename",
                "public",
                "private",
                "protected",
                "virtual",
                "override",
                "const",
                "static",
                "inline",
                "constexpr",
                "auto",
                "if",
                "else",
                "for",
                "while",
                "do",
                "switch",
                "case",
                "return",
                "break",
                "continue",
                "try",
                "catch",
                "throw",
            ]

            # Add symbols from the current file context
            if file_path in self._symbol_cache:
                for symbol_def in self._symbol_cache[file_path]:
                    completions.append(symbol_def["symbol"])

            completions.extend(cpp_keywords)
            completions = list(set(completions))  # Remove duplicates

            return Result.success_result(completions)

        except Exception as e:
            error = Error(
                code="CPP_COMPLETION_ERROR",
                message=f"Failed to get completions: {str(e)}",
                details={
                    "file_path": file_path,
                    "line": line,
                    "column": column,
                    "exception": str(e),
                },
                timestamp=datetime.now(),
            )
            return Result.error_result(error)

    def resolve_includes(self, file_path: str) -> Result[List[str]]:
        """Resolve #include directives"""
        try:
            content = Path(file_path).read_text(encoding="utf-8")
            tree = self._parser.parse(content.encode("utf-8"))
            root = tree.root_node

            includes = []

            def extract_includes(node: Node) -> None:
                if node.type == "preproc_include":
                    # Extract the include path
                    for child in node.children:
                        if child.type in ["string_literal", "system_lib_string"]:
                            include_path = content[child.start_byte : child.end_byte]
                            # Remove quotes or angle brackets
                            include_path = include_path.strip('"<>')
                            includes.append(include_path)

                for child in node.children:
                    extract_includes(child)

            extract_includes(root)
            return Result.success_result(includes)

        except Exception as e:
            error = Error(
                code="CPP_INCLUDE_ERROR",
                message=f"Failed to resolve includes: {str(e)}",
                details={"file_path": file_path, "exception": str(e)},
                timestamp=datetime.now(),
            )
            return Result.error_result(error)

    def parse_templates(self, content: str) -> Result[List[SymbolDefinition]]:
        """Parse template definitions"""
        try:
            tree = self._parser.parse(content.encode("utf-8"))
            root = tree.root_node

            templates = []

            def extract_templates(node: Node) -> None:
                if node.type == "template_declaration":
                    # Extract template parameters and declaration
                    params_node = node.child_by_field_name("parameters")
                    decl_node = None

                    # Find the actual declaration (class, function, etc.)
                    for child in node.children:
                        if child.type in [
                            "class_specifier",
                            "struct_specifier",
                            "function_declaration",
                            "function_definition",
                        ]:
                            decl_node = child
                            break

                    if decl_node:
                        name = self._extract_template_name(decl_node, content)
                        if name:
                            template_params = ""
                            if params_node:
                                template_params = content[
                                    params_node.start_byte : params_node.end_byte
                                ]

                            symbol_def = SymbolDefinition(
                                symbol=name,
                                file_path="",  # Will be set by caller
                                line=node.start_point[0] + 1,
                                column=node.start_point[1],
                                symbol_type="template",
                                signature=f"template{template_params} {content[decl_node.start_byte:decl_node.end_byte][:100]}...",
                                docstring=None,
                                scope=None,
                            )
                            templates.append(symbol_def)

                for child in node.children:
                    extract_templates(child)

            extract_templates(root)
            return Result.success_result(templates)

        except Exception as e:
            error = Error(
                code="CPP_TEMPLATE_ERROR",
                message=f"Failed to parse templates: {str(e)}",
                details={"exception": str(e)},
                timestamp=datetime.now(),
            )
            return Result.error_result(error)

    # ========================================
    # ILanguageAnalyzer Interface Implementation
    # ========================================

    def parse_imports(self, content: str) -> Result[List[str]]:
        """Parse import statements from content (C++ includes)"""
        # Reuse the resolve_includes logic
        try:
            tree = self._parser.parse(content.encode("utf-8"))
            root = tree.root_node

            includes = []

            def extract_includes(node: Node) -> None:
                if node.type == "preproc_include":
                    for child in node.children:
                        if child.type in ["string_literal", "system_lib_string"]:
                            include_path = content[child.start_byte : child.end_byte]
                            include_path = include_path.strip('"<>')
                            includes.append(include_path)

                for child in node.children:
                    extract_includes(child)

            extract_includes(root)
            return Result.success_result(includes)

        except Exception as e:
            error = Error(
                code="CPP_IMPORTS_ERROR",
                message=f"Failed to parse imports: {str(e)}",
                details={"exception": str(e)},
                timestamp=datetime.now(),
            )
            return Result.error_result(error)

    def extract_symbols(self, content: str) -> Result[List[SymbolDefinition]]:
        """Extract all symbols from content"""
        try:
            tree = self._parser.parse(content.encode("utf-8"))
            root = tree.root_node

            symbols: List[Dict[str, Any]] = []
            self._namespace_stack = []
            self._extract_symbols(root, content, symbols)

            symbol_defs = [
                SymbolDefinition(
                    symbol=s["symbol"],
                    file_path="",  # Will be set by caller
                    line=s.get("line", 1),
                    column=0,
                    symbol_type=s["kind"],
                    signature=s.get("signature"),
                    docstring=None,
                    scope=self._get_scope_from_symbol(s["symbol"]),
                )
                for s in symbols
            ]

            return Result.success_result(symbol_defs)

        except Exception as e:
            error = Error(
                code="CPP_SYMBOLS_ERROR",
                message=f"Failed to extract symbols: {str(e)}",
                details={"exception": str(e)},
                timestamp=datetime.now(),
            )
            return Result.error_result(error)

    def resolve_type(self, symbol: str, context: Dict[str, Any]) -> Result[Optional[str]]:
        """Resolve the type of a symbol"""
        try:
            # Look up the symbol definition
            definition = self.getDefinition(symbol)
            if definition:
                # Try to extract type from signature
                signature = definition.get("signature", "")
                if definition["kind"] == "function" or definition["kind"] == "method":
                    # For functions, return type is usually at the beginning
                    parts = signature.split()
                    if parts:
                        return Result.success_result(parts[0])
                elif definition["kind"] == "field":
                    # For fields, type is usually before the name
                    parts = signature.split()
                    if len(parts) >= 2:
                        return Result.success_result(parts[0])

            return Result.success_result(None)

        except Exception as e:
            error = Error(
                code="CPP_TYPE_ERROR",
                message=f"Failed to resolve type: {str(e)}",
                details={"symbol": symbol, "exception": str(e)},
                timestamp=datetime.now(),
            )
            return Result.error_result(error)

    def get_call_hierarchy(
        self, symbol: str, context: Dict[str, Any]
    ) -> Result[Dict[str, List[str]]]:
        """Get call hierarchy for a symbol"""
        try:
            # Basic implementation - find who calls this symbol and what it calls
            calls_to = []  # Functions this symbol calls
            called_by = []  # Functions that call this symbol

            # Find references to get called_by
            references = self.findReferences(symbol)
            for ref in references:
                # This is a simplified approach
                called_by.append(f"{ref.file}:{ref.line}")

            # For calls_to, we'd need more sophisticated analysis
            # This would require parsing the function body and finding function calls

            hierarchy = {"calls_to": calls_to, "called_by": called_by}

            return Result.success_result(hierarchy)

        except Exception as e:
            error = Error(
                code="CPP_HIERARCHY_ERROR",
                message=f"Failed to get call hierarchy: {str(e)}",
                details={"symbol": symbol, "exception": str(e)},
                timestamp=datetime.now(),
            )
            return Result.error_result(error)

    # ========================================
    # Helper Methods
    # ========================================

    def _get_scope_from_symbol(self, symbol: str) -> Optional[str]:
        """Extract scope/namespace from a qualified symbol name"""
        if "::" in symbol:
            parts = symbol.split("::")
            if len(parts) > 1:
                return "::".join(parts[:-1])
        return None

    def _extract_template_name(self, node: Node, content: str) -> Optional[str]:
        """Extract name from a template declaration node"""
        if node.type in ["class_specifier", "struct_specifier"]:
            name_node = node.child_by_field_name("name")
            if name_node:
                return content[name_node.start_byte : name_node.end_byte]
        elif node.type in ["function_declaration", "function_definition"]:
            declarator = node.child_by_field_name("declarator")
            if declarator:
                return self._extract_function_name(declarator, content)
        return None
