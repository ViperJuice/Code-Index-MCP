from __future__ import annotations

import ctypes
import logging
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

import tree_sitter_languages
from tree_sitter import Language, Node, Parser

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
    """JavaScript/TypeScript plugin for code intelligence."""

    lang = "js"

    def __init__(self, sqlite_store: Optional[SQLiteStore] = None) -> None:
        """Initialize the JavaScript/TypeScript plugin.

        Args:
            sqlite_store: Optional SQLite store for persistence
        """
        # Initialize parsers for both JavaScript and TypeScript
        self._js_parser = Parser()
        self._ts_parser = Parser()

        # Load language grammars
        lib_path = Path(tree_sitter_languages.__path__[0]) / "languages.so"
        self._lib = ctypes.CDLL(str(lib_path))

        # Configure JavaScript
        self._lib.tree_sitter_javascript.restype = ctypes.c_void_p
        self._js_language = Language(self._lib.tree_sitter_javascript())
        self._js_parser.language = self._js_language

        # Configure TypeScript
        self._lib.tree_sitter_typescript.restype = ctypes.c_void_p
        self._ts_language = Language(self._lib.tree_sitter_typescript())
        self._ts_parser.language = self._ts_language

        # Initialize indexer and storage
        self._indexer = FuzzyIndexer(sqlite_store=sqlite_store)
        self._sqlite_store = sqlite_store
        self._repository_id = None

        # State tracking
        self._scope_stack: List[str] = []
        self._module_type: Optional[str] = None
        self._current_file: Optional[Path] = None

        # Symbol cache for faster lookups
        self._symbol_cache: Dict[str, List[SymbolDef]] = {}

        # Create or get repository if SQLite is enabled
        if self._sqlite_store:
            self._repository_id = self._sqlite_store.create_repository(
                str(Path.cwd()), Path.cwd().name, {"language": "javascript/typescript"}
            )

        # Pre-index existing files
        self._preindex()

    def _preindex(self) -> None:
        """Pre-index all supported files in the current directory."""
        for pattern in ["*.js", "*.jsx", "*.ts", "*.tsx", "*.mjs", "*.cjs"]:
            for path in Path(".").rglob(pattern):
                try:
                    # Skip node_modules and common build directories
                    if any(
                        part in path.parts for part in ["node_modules", "dist", "build", ".next"]
                    ):
                        continue

                    # Skip minified files
                    if path.stem.endswith(".min"):
                        continue

                    text = path.read_text(encoding="utf-8")
                    self._indexer.add_file(str(path), text)
                except Exception as e:
                    logger.warning(f"Failed to pre-index {path}: {e}")
                    continue

    def supports(self, path: str | Path) -> bool:
        """Check if this plugin supports the given file."""
        suffixes = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".es6", ".es"}
        return Path(path).suffix.lower() in suffixes

    def _get_parser(self, path: Path) -> Parser:
        """Get the appropriate parser for the file type."""
        if path.suffix in {".ts", ".tsx"}:
            return self._ts_parser
        return self._js_parser

    def indexFile(self, path: str | Path, content: str) -> IndexShard:
        """Parse and index a JavaScript/TypeScript file."""
        if isinstance(path, str):
            path = Path(path)

        self._current_file = path
        self._indexer.add_file(str(path), content)

        # Choose parser based on file extension
        parser = self._get_parser(path)
        tree = parser.parse(content.encode("utf-8"))
        root = tree.root_node

        # Detect module type
        self._module_type = self._detect_module_type(root, content)

        # Store file in SQLite if available
        file_id = None
        if self._sqlite_store and self._repository_id:
            import hashlib

            file_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            file_id = self._sqlite_store.store_file(
                self._repository_id,
                str(path),
                str(path.relative_to(Path.cwd())),
                language=(
                    "javascript" if path.suffix in {".js", ".jsx", ".mjs", ".cjs"} else "typescript"
                ),
                size=len(content),
                hash=file_hash,
            )

        # Extract symbols
        symbols: List[Dict[str, Any]] = []
        imports: List[Dict[str, Any]] = []
        exports: List[Dict[str, Any]] = []

        self._extract_symbols(root, content, symbols, imports, exports, file_id)

        # Store module information if SQLite available
        if self._sqlite_store and self._repository_id and file_id:
            self._store_module_info(path, imports, exports, file_id)

        # Cache symbols for quick lookup
        cache_key = str(path)
        self._symbol_cache[cache_key] = [
            self._symbol_to_def(s, str(path), content) for s in symbols
        ]

        return {
            "file": str(path),
            "symbols": symbols,
            "language": self.lang,
            "module_type": self._module_type,
        }

    def _detect_module_type(self, root: Node, content: str) -> str:
        """Detect whether the file uses CommonJS or ES modules."""
        # Check for ES module syntax
        for node in self._walk_tree(root):
            if node.type in [
                "import_statement",
                "export_statement",
                "import_declaration",
                "export_declaration",
            ]:
                return "esm"

        # Check for CommonJS patterns
        if "require(" in content or "module.exports" in content or "exports." in content:
            return "commonjs"

        return "unknown"

    def _extract_symbols(
        self,
        node: Node,
        content: str,
        symbols: List[Dict],
        imports: List[Dict],
        exports: List[Dict],
        file_id: Optional[int] = None,
        scope_path: List[str] = None,
    ) -> None:
        """Recursively extract symbols from the AST."""
        if scope_path is None:
            scope_path = []

        # Extract imports and exports at the top level
        if not scope_path:
            imports.extend(self._extract_imports(node, content))
            exports.extend(self._extract_exports(node, content))

        # Function declarations
        if node.type in ["function_declaration", "function"]:
            name_node = node.child_by_field_name("name")
            if name_node:
                name = content[name_node.start_byte : name_node.end_byte]
                params = self._extract_parameters(node, content)
                is_async = self._is_async_function(node, content)
                is_generator = self._is_generator_function(node, content)

                kind = "function"
                if is_generator:
                    kind = "generator"

                signature = f"{'async ' if is_async else ''}function{'*' if is_generator else ''} {name}({params})"

                symbol_info = {
                    "symbol": name,
                    "kind": kind,
                    "signature": signature,
                    "line": node.start_point[0] + 1,
                    "span": (node.start_point[0] + 1, node.end_point[0] + 1),
                    "scope": ".".join(scope_path) if scope_path else None,
                }
                symbols.append(symbol_info)

                # Store in SQLite if available
                if self._sqlite_store and file_id:
                    symbol_id = self._sqlite_store.store_symbol(
                        file_id,
                        name,
                        kind,
                        node.start_point[0] + 1,
                        node.end_point[0] + 1,
                        signature=signature,
                    )
                    self._indexer.add_symbol(
                        name,
                        str(self._current_file),
                        node.start_point[0] + 1,
                        {"symbol_id": symbol_id, "file_id": file_id},
                    )

        # Variable declarations (including arrow functions)
        elif node.type in ["variable_declaration", "lexical_declaration"]:
            kind_keyword = self._get_declaration_kind(node, content)

            for child in node.named_children:
                if child.type == "variable_declarator":
                    name_node = child.child_by_field_name("name")
                    value_node = child.child_by_field_name("value") or child.child_by_field_name(
                        "init"
                    )

                    if name_node:
                        name = content[name_node.start_byte : name_node.end_byte]

                        if value_node and value_node.type == "arrow_function":
                            # Arrow function
                            params = self._extract_parameters(value_node, content)
                            is_async = self._is_async_function(value_node, content)

                            signature = f"{'async ' if is_async else ''}{kind_keyword} {name} = ({params}) => {{}}"
                            kind = "arrow_function"
                            span = (
                                node.start_point[0] + 1,
                                value_node.end_point[0] + 1,
                            )
                        elif value_node and value_node.type in [
                            "function_expression",
                            "function",
                        ]:
                            # Function expression
                            params = self._extract_parameters(value_node, content)
                            is_async = self._is_async_function(value_node, content)

                            signature = f"{kind_keyword} {name} = {'async ' if is_async else ''}function({params})"
                            kind = "function"
                            span = (
                                node.start_point[0] + 1,
                                value_node.end_point[0] + 1,
                            )
                        elif value_node and value_node.type in [
                            "class_expression",
                            "class",
                        ]:
                            # Class expression
                            signature = f"{kind_keyword} {name} = class"
                            kind = "class"
                            span = (
                                node.start_point[0] + 1,
                                value_node.end_point[0] + 1,
                            )
                        else:
                            # Regular variable
                            signature = f"{kind_keyword} {name}"
                            kind = "variable"
                            span = (node.start_point[0] + 1, node.end_point[0] + 1)

                        symbol_info = {
                            "symbol": name,
                            "kind": kind,
                            "signature": signature,
                            "line": node.start_point[0] + 1,
                            "span": span,
                            "scope": ".".join(scope_path) if scope_path else None,
                        }
                        symbols.append(symbol_info)

                        # Store in SQLite if available
                        if self._sqlite_store and file_id:
                            symbol_id = self._sqlite_store.store_symbol(
                                file_id,
                                name,
                                kind,
                                span[0],
                                span[1],
                                signature=signature,
                            )
                            self._indexer.add_symbol(
                                name,
                                str(self._current_file),
                                node.start_point[0] + 1,
                                {"symbol_id": symbol_id, "file_id": file_id},
                            )

        # Class declarations
        elif node.type in ["class_declaration", "class"]:
            name_node = node.child_by_field_name("name")
            if name_node:
                name = content[name_node.start_byte : name_node.end_byte]
                superclass = self._extract_superclass(node, content)

                signature = f"class {name}{' extends ' + superclass if superclass else ''}"

                symbol_info = {
                    "symbol": name,
                    "kind": "class",
                    "signature": signature,
                    "line": node.start_point[0] + 1,
                    "span": (node.start_point[0] + 1, node.end_point[0] + 1),
                    "scope": ".".join(scope_path) if scope_path else None,
                }
                symbols.append(symbol_info)

                # Store in SQLite if available
                if self._sqlite_store and file_id:
                    symbol_id = self._sqlite_store.store_symbol(
                        file_id,
                        name,
                        "class",
                        node.start_point[0] + 1,
                        node.end_point[0] + 1,
                        signature=signature,
                    )
                    self._indexer.add_symbol(
                        name,
                        str(self._current_file),
                        node.start_point[0] + 1,
                        {"symbol_id": symbol_id, "file_id": file_id},
                    )

                # Extract class members
                body_node = node.child_by_field_name("body")
                if body_node:
                    new_scope = scope_path + [name]
                    for child in body_node.named_children:
                        self._extract_symbols(
                            child,
                            content,
                            symbols,
                            imports,
                            exports,
                            file_id,
                            new_scope,
                        )

        # Method definitions (class methods)
        elif node.type in ["method_definition", "field_definition"]:
            name_node = node.child_by_field_name("name")
            if name_node:
                name = content[name_node.start_byte : name_node.end_byte]

                if node.type == "method_definition":
                    params = self._extract_parameters(node, content)
                    is_async = self._is_async_function(node, content)
                    is_static = self._has_modifier(node, content, "static")
                    is_getter = self._has_modifier(node, content, "get")
                    is_setter = self._has_modifier(node, content, "set")

                    if is_getter:
                        signature = f"get {name}()"
                        kind = "getter"
                    elif is_setter:
                        signature = f"set {name}({params})"
                        kind = "setter"
                    else:
                        signature = f"{'static ' if is_static else ''}{'async ' if is_async else ''}{name}({params})"
                        kind = "method"
                else:
                    # Field definition
                    is_static = self._has_modifier(node, content, "static")
                    signature = f"{'static ' if is_static else ''}{name}"
                    kind = "property"

                symbol_info = {
                    "symbol": f"{'.'.join(scope_path)}.{name}" if scope_path else name,
                    "kind": kind,
                    "signature": signature,
                    "line": node.start_point[0] + 1,
                    "span": (node.start_point[0] + 1, node.end_point[0] + 1),
                }
                symbols.append(symbol_info)

        # Object methods and properties
        elif node.type == "assignment_expression":
            left = node.child_by_field_name("left")
            right = node.child_by_field_name("right")

            if left and left.type == "member_expression":
                prop_node = left.child_by_field_name("property")
                obj_node = left.child_by_field_name("object")

                if prop_node and obj_node:
                    prop_name = content[prop_node.start_byte : prop_node.end_byte]
                    obj_name = content[obj_node.start_byte : obj_node.end_byte]

                    # Check if it's a method assignment
                    if right and right.type in [
                        "arrow_function",
                        "function_expression",
                        "function",
                    ]:
                        params = self._extract_parameters(right, content)
                        signature = f"{obj_name}.{prop_name} = function({params})"
                        kind = "method"
                    else:
                        signature = f"{obj_name}.{prop_name}"
                        kind = "property"

                    symbol_info = {
                        "symbol": f"{obj_name}.{prop_name}",
                        "kind": kind,
                        "signature": signature,
                        "line": node.start_point[0] + 1,
                    }
                    symbols.append(symbol_info)

        # TypeScript interfaces and type aliases
        elif node.type == "interface_declaration":
            name_node = node.child_by_field_name("name")
            if name_node:
                name = content[name_node.start_byte : name_node.end_byte]
                signature = f"interface {name}"

                symbol_info = {
                    "symbol": name,
                    "kind": "interface",
                    "signature": signature,
                    "line": node.start_point[0] + 1,
                    "span": (node.start_point[0] + 1, node.end_point[0] + 1),
                }
                symbols.append(symbol_info)

        elif node.type == "type_alias_declaration":
            name_node = node.child_by_field_name("name")
            if name_node:
                name = content[name_node.start_byte : name_node.end_byte]
                signature = f"type {name}"

                symbol_info = {
                    "symbol": name,
                    "kind": "type",
                    "signature": signature,
                    "line": node.start_point[0] + 1,
                    "span": (node.start_point[0] + 1, node.end_point[0] + 1),
                }
                symbols.append(symbol_info)

        # Continue recursion for child nodes
        for child in node.named_children:
            # Skip if we already processed this as a special case
            if child.type not in ["class_body"]:
                self._extract_symbols(
                    child, content, symbols, imports, exports, file_id, scope_path
                )

    def _extract_parameters(self, node: Node, content: str) -> str:
        """Extract function parameters as a string."""
        params_node = node.child_by_field_name("parameters")
        if not params_node:
            # For arrow functions, parameters might be direct children
            for child in node.children:
                if child.type in ["formal_parameters", "identifier"]:
                    params_node = child
                    break

        if params_node:
            if params_node.type == "identifier":
                # Single parameter arrow function
                return content[params_node.start_byte : params_node.end_byte]
            else:
                # Extract parameter names
                params = []
                for child in params_node.named_children:
                    if child.type in [
                        "identifier",
                        "required_parameter",
                        "optional_parameter",
                    ]:
                        if child.type == "identifier":
                            params.append(content[child.start_byte : child.end_byte])
                        else:
                            # Handle TypeScript parameters
                            name_node = child.child_by_field_name(
                                "pattern"
                            ) or child.child_by_field_name("name")
                            if name_node:
                                param_text = content[name_node.start_byte : name_node.end_byte]
                                if child.type == "optional_parameter":
                                    param_text += "?"
                                params.append(param_text)
                return ", ".join(params)
        return ""

    def _is_async_function(self, node: Node, content: str) -> bool:
        """Check if a function is async."""
        # Check for async modifier
        for child in node.children:
            if child.type == "async":
                return True
            # Check text content for 'async' keyword before function/arrow
            if not child.is_named and child.end_byte <= node.start_byte + 10:
                text = content[child.start_byte : child.end_byte].strip()
                if text == "async":
                    return True
        return False

    def _is_generator_function(self, node: Node, content: str) -> bool:
        """Check if a function is a generator."""
        # Look for * after function keyword
        found_function = False
        for child in node.children:
            if not child.is_named:
                text = content[child.start_byte : child.end_byte].strip()
                if text == "function":
                    found_function = True
                elif found_function and text == "*":
                    return True
        return False

    def _has_modifier(self, node: Node, content: str, modifier: str) -> bool:
        """Check if a node has a specific modifier."""
        for child in node.children:
            if not child.is_named:
                text = content[child.start_byte : child.end_byte].strip()
                if text == modifier:
                    return True
        return False

    def _get_declaration_kind(self, node: Node, content: str) -> str:
        """Get the declaration keyword (var, let, const)."""
        # Check the first token
        for child in node.children:
            if not child.is_named:
                text = content[child.start_byte : child.end_byte].strip()
                if text in ["var", "let", "const"]:
                    return text
        return "const"  # Default

    def _extract_superclass(self, node: Node, content: str) -> Optional[str]:
        """Extract the superclass name from a class declaration."""
        heritage = node.child_by_field_name("heritage")
        if heritage:
            # Look for extends clause
            for child in heritage.named_children:
                if child.type == "extends_clause":
                    # Get the first identifier after extends
                    for subchild in child.named_children:
                        if subchild.type == "identifier":
                            return content[subchild.start_byte : subchild.end_byte]
        return None

    def _extract_imports(self, root: Node, content: str) -> List[Dict[str, Any]]:
        """Extract import statements from the file."""
        imports = []

        for node in self._walk_tree(root):
            # ES6 imports
            if node.type in ["import_statement", "import_declaration"]:
                source_node = node.child_by_field_name("source")
                if source_node:
                    source = content[source_node.start_byte : source_node.end_byte].strip("\"'`")

                    # Extract imported names
                    imported_names = []
                    default_import = None
                    namespace_import = None

                    for child in node.named_children:
                        if child.type == "identifier" and child != source_node:
                            # Default import
                            default_import = content[child.start_byte : child.end_byte]
                        elif child.type == "import_clause":
                            for clause_child in child.named_children:
                                if clause_child.type == "identifier":
                                    default_import = content[
                                        clause_child.start_byte : clause_child.end_byte
                                    ]
                                elif clause_child.type == "namespace_import":
                                    # import * as name
                                    for ns_child in clause_child.named_children:
                                        if ns_child.type == "identifier":
                                            namespace_import = content[
                                                ns_child.start_byte : ns_child.end_byte
                                            ]
                                elif clause_child.type == "named_imports":
                                    # import { a, b, c }
                                    for spec in clause_child.named_children:
                                        if spec.type == "import_specifier":
                                            name_node = spec.child_by_field_name("name")
                                            alias_node = spec.child_by_field_name("alias")
                                            if name_node:
                                                name = content[
                                                    name_node.start_byte : name_node.end_byte
                                                ]
                                                if alias_node:
                                                    alias = content[
                                                        alias_node.start_byte : alias_node.end_byte
                                                    ]
                                                    imported_names.append(f"{name} as {alias}")
                                                else:
                                                    imported_names.append(name)

                    import_info = {
                        "source": source,
                        "line": node.start_point[0] + 1,
                        "type": "esm",
                    }

                    if default_import:
                        import_info["default"] = default_import
                    if namespace_import:
                        import_info["namespace"] = namespace_import
                    if imported_names:
                        import_info["names"] = imported_names

                    imports.append(import_info)

            # CommonJS requires
            elif node.type == "call_expression":
                func_node = node.child_by_field_name("function")
                args_node = node.child_by_field_name("arguments")

                if func_node and args_node:
                    func_text = content[func_node.start_byte : func_node.end_byte]
                    if func_text == "require" and args_node.named_child_count > 0:
                        arg_node = args_node.named_children[0]
                        if arg_node.type in ["string", "template_string"]:
                            source = content[arg_node.start_byte : arg_node.end_byte].strip("\"'`")
                            imports.append(
                                {
                                    "source": source,
                                    "line": node.start_point[0] + 1,
                                    "type": "commonjs",
                                }
                            )

        return imports

    def _extract_exports(self, root: Node, content: str) -> List[Dict[str, Any]]:
        """Extract export statements from the file."""
        exports = []

        for node in self._walk_tree(root):
            # ES6 exports
            if node.type in ["export_statement", "export_declaration"]:
                declaration = node.child_by_field_name("declaration")

                # export default
                default_export = False
                for child in node.children:
                    if (
                        not child.is_named
                        and content[child.start_byte : child.end_byte].strip() == "default"
                    ):
                        default_export = True
                        break

                if declaration:
                    if declaration.type in ["function_declaration", "function"]:
                        name_node = declaration.child_by_field_name("name")
                        if name_node:
                            name = content[name_node.start_byte : name_node.end_byte]
                            exports.append(
                                {
                                    "name": name,
                                    "kind": "function",
                                    "default": default_export,
                                    "line": node.start_point[0] + 1,
                                }
                            )
                    elif declaration.type in ["class_declaration", "class"]:
                        name_node = declaration.child_by_field_name("name")
                        if name_node:
                            name = content[name_node.start_byte : name_node.end_byte]
                            exports.append(
                                {
                                    "name": name,
                                    "kind": "class",
                                    "default": default_export,
                                    "line": node.start_point[0] + 1,
                                }
                            )
                    elif declaration.type in [
                        "variable_declaration",
                        "lexical_declaration",
                    ]:
                        # export const/let/var
                        for child in declaration.named_children:
                            if child.type == "variable_declarator":
                                name_node = child.child_by_field_name("name")
                                if name_node:
                                    name = content[name_node.start_byte : name_node.end_byte]
                                    exports.append(
                                        {
                                            "name": name,
                                            "kind": "variable",
                                            "default": default_export,
                                            "line": node.start_point[0] + 1,
                                        }
                                    )

                # export { a, b, c }
                for child in node.named_children:
                    if child.type == "export_clause":
                        for spec in child.named_children:
                            if spec.type == "export_specifier":
                                name_node = spec.child_by_field_name("name")
                                alias_node = spec.child_by_field_name("alias")
                                if name_node:
                                    name = content[name_node.start_byte : name_node.end_byte]
                                    export_info = {
                                        "name": name,
                                        "kind": "named",
                                        "line": node.start_point[0] + 1,
                                    }
                                    if alias_node:
                                        export_info["alias"] = content[
                                            alias_node.start_byte : alias_node.end_byte
                                        ]
                                    exports.append(export_info)

            # CommonJS exports
            elif node.type == "assignment_expression":
                left = node.child_by_field_name("left")
                if left and left.type == "member_expression":
                    obj_node = left.child_by_field_name("object")
                    prop_node = left.child_by_field_name("property")

                    if obj_node and prop_node:
                        obj_text = content[obj_node.start_byte : obj_node.end_byte]
                        prop_text = content[prop_node.start_byte : prop_node.end_byte]

                        # module.exports = ...
                        if obj_text == "module" and prop_text == "exports":
                            exports.append(
                                {
                                    "name": "default",
                                    "kind": "commonjs",
                                    "line": node.start_point[0] + 1,
                                }
                            )
                        # exports.name = ...
                        elif obj_text == "exports":
                            exports.append(
                                {
                                    "name": prop_text,
                                    "kind": "commonjs",
                                    "line": node.start_point[0] + 1,
                                }
                            )

        return exports

    def _store_module_info(
        self, path: Path, imports: List[Dict], exports: List[Dict], file_id: int
    ) -> None:
        """Store module dependency information in SQLite."""
        if not self._sqlite_store:
            return

        # Store imports
        for imp in imports:
            # TODO: Implement import storage in SQLiteStore
            pass

        # Store exports
        for exp in exports:
            # TODO: Implement export storage in SQLiteStore
            pass

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
            # Try to extract JSDoc comment above the symbol
            lines = content.splitlines()
            line_idx = symbol["line"] - 1
            if line_idx > 0:
                # Look for JSDoc comment
                for i in range(line_idx - 1, max(0, line_idx - 10), -1):
                    line = lines[i].strip()
                    if line.startswith("*/"):
                        # Found end of JSDoc, extract it
                        doc_lines = []
                        for j in range(i, max(0, i - 20), -1):
                            doc_lines.insert(0, lines[j])
                            if lines[j].strip().startswith("/**"):
                                doc = "\n".join(doc_lines)
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
                if sym_def["symbol"] == symbol or sym_def["symbol"].endswith(f".{symbol}"):
                    return sym_def

        # Search in all supported files
        for pattern in ["*.js", "*.jsx", "*.ts", "*.tsx", "*.mjs", "*.cjs"]:
            for path in Path(".").rglob(pattern):
                try:
                    # Skip node_modules and build directories
                    if any(
                        part in path.parts for part in ["node_modules", "dist", "build", ".next"]
                    ):
                        continue

                    content = path.read_text(encoding="utf-8")
                    shard = self.indexFile(path, content)

                    for sym in shard["symbols"]:
                        if sym["symbol"] == symbol or sym["symbol"].endswith(f".{symbol}"):
                            return self._symbol_to_def(sym, str(path), content)
                except Exception:
                    continue

        return None

    def findReferences(self, symbol: str) -> list[Reference]:
        """Find all references to a symbol."""
        refs: List[Reference] = []
        seen: Set[Tuple[str, int]] = set()

        # Search in all supported files
        for pattern in ["*.js", "*.jsx", "*.ts", "*.tsx", "*.mjs", "*.cjs"]:
            for path in Path(".").rglob(pattern):
                try:
                    # Skip node_modules and build directories
                    if any(
                        part in path.parts for part in ["node_modules", "dist", "build", ".next"]
                    ):
                        continue

                    content = path.read_text(encoding="utf-8")

                    # Simple text search for references
                    lines = content.splitlines()
                    for i, line in enumerate(lines):
                        # Look for whole word matches
                        import re

                        pattern = r"\b" + re.escape(symbol) + r"\b"
                        if re.search(pattern, line):
                            line_no = i + 1
                            key = (str(path), line_no)
                            if key not in seen:
                                refs.append(Reference(file=str(path), line=line_no))
                                seen.add(key)
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
