from __future__ import annotations

import ctypes
import hashlib
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

import tree_sitter_languages
from tree_sitter import Language, Node, Parser

from ...interfaces.plugin_interfaces import (
    IHtmlCssPlugin,
    ILanguageAnalyzer,
    IndexedFile,
)
from ...interfaces.plugin_interfaces import SearchResult as PluginSearchResult
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


class Plugin(IPlugin, IHtmlCssPlugin, ILanguageAnalyzer):
    """HTML/CSS plugin for code intelligence."""

    lang = "html_css"

    def __init__(self, sqlite_store: Optional[SQLiteStore] = None) -> None:
        """Initialize the HTML/CSS plugin.

        Args:
            sqlite_store: Optional SQLite store for persistence
        """
        # Initialize parsers for HTML and CSS
        self._html_parser = Parser()
        self._css_parser = Parser()

        # Load language grammars
        lib_path = Path(tree_sitter_languages.__path__[0]) / "languages.so"
        self._lib = ctypes.CDLL(str(lib_path))

        # Configure HTML
        self._lib.tree_sitter_html.restype = ctypes.c_void_p
        self._html_language = Language(self._lib.tree_sitter_html())
        self._html_parser.language = self._html_language

        # Configure CSS
        self._lib.tree_sitter_css.restype = ctypes.c_void_p
        self._css_language = Language(self._lib.tree_sitter_css())
        self._css_parser.language = self._css_language

        # Initialize indexer and storage
        self._indexer = FuzzyIndexer(sqlite_store=sqlite_store)
        self._sqlite_store = sqlite_store
        self._repository_id = None

        # Cross-reference cache for matching CSS selectors to HTML elements
        self._html_elements: Dict[str, List[Dict[str, Any]]] = {}  # file -> elements
        self._css_selectors: Dict[str, List[Dict[str, Any]]] = {}  # file -> selectors

        # Symbol cache for faster lookups
        self._symbol_cache: Dict[str, List[SymbolDef]] = {}

        # Current file being indexed
        self._current_file: Optional[Path] = None

        # Create or get repository if SQLite is enabled
        if self._sqlite_store:
            self._repository_id = self._sqlite_store.create_repository(
                str(Path.cwd()), Path.cwd().name, {"language": "html/css"}
            )

        # Pre-index existing files
        self._preindex()

    # ========================================
    # IPlugin Interface Implementation
    # ========================================

    @property
    def name(self) -> str:
        """Get the plugin name."""
        return "html_css_plugin"

    @property
    def supported_extensions(self) -> List[str]:
        """Get list of file extensions this plugin supports."""
        return [".html", ".htm", ".css", ".scss", ".sass", ".less"]

    @property
    def supported_languages(self) -> List[str]:
        """Get list of programming languages this plugin supports."""
        return ["html", "css", "scss", "sass", "less"]

    def can_handle(self, file_path: str) -> bool:
        """Check if this plugin can handle the given file."""
        return self.supports(file_path)

    def index(self, file_path: str, content: Optional[str] = None) -> Result[IndexedFile]:
        """Index a file and extract symbols."""
        try:
            path = Path(file_path)

            if content is None:
                if not path.exists():
                    return Result.error_result(
                        Error(
                            code="file_not_found",
                            message=f"File not found: {file_path}",
                            details={"file_path": file_path},
                            timestamp=datetime.now(),
                        )
                    )
                content = path.read_text(encoding="utf-8")

            # Use the existing indexFile method
            index_shard = self.indexFile(file_path, content)

            # Convert to new interface format
            symbols = []
            for symbol_dict in index_shard["symbols"]:
                symbol_def = SymbolDefinition(
                    symbol=symbol_dict["symbol"],
                    file_path=file_path,
                    line=symbol_dict.get("line", 1),
                    column=0,  # HTML/CSS doesn't typically track columns precisely
                    symbol_type=symbol_dict["kind"],
                    signature=symbol_dict.get("signature"),
                    docstring=None,  # HTML/CSS don't have docstrings
                    scope=symbol_dict.get("tag"),  # Use tag as scope for HTML elements
                )
                symbols.append(symbol_def)

            indexed_file = IndexedFile(
                file_path=file_path,
                last_modified=path.stat().st_mtime if path.exists() else 0,
                size=len(content),
                symbols=symbols,
                language="html" if self._is_html_file(path) else "css",
                encoding="utf-8",
            )

            return Result.success_result(indexed_file)

        except Exception as e:
            return Result.error_result(
                Error(
                    code="indexing_error",
                    message=f"Failed to index file: {str(e)}",
                    details={"file_path": file_path, "exception": str(e)},
                    timestamp=datetime.now(),
                )
            )

    def get_definition(
        self, symbol: str, context: Dict[str, Any]
    ) -> Result[Optional[SymbolDefinition]]:
        """Get the definition of a symbol."""
        try:
            symbol_def = self.getDefinition(symbol)
            if symbol_def is None:
                return Result.success_result(None)

            # Convert from old format to new
            definition = SymbolDefinition(
                symbol=symbol_def["symbol"],
                file_path=symbol_def["defined_in"],
                line=symbol_def["line"],
                column=0,
                symbol_type=symbol_def["kind"],
                signature=symbol_def.get("signature"),
                docstring=symbol_def.get("doc"),
                scope=None,
            )

            return Result.success_result(definition)

        except Exception as e:
            return Result.error_result(
                Error(
                    code="definition_error",
                    message=f"Failed to get definition: {str(e)}",
                    details={"symbol": symbol, "exception": str(e)},
                    timestamp=datetime.now(),
                )
            )

    def get_references(self, symbol: str, context: Dict[str, Any]) -> Result[List[SymbolReference]]:
        """Get all references to a symbol."""
        try:
            references = self.findReferences(symbol)
            symbol_refs = []

            for ref in references:
                symbol_ref = SymbolReference(
                    symbol=symbol,
                    file_path=ref.file,
                    line=ref.line,
                    column=0,
                    context=None,
                )
                symbol_refs.append(symbol_ref)

            return Result.success_result(symbol_refs)

        except Exception as e:
            return Result.error_result(
                Error(
                    code="references_error",
                    message=f"Failed to get references: {str(e)}",
                    details={"symbol": symbol, "exception": str(e)},
                    timestamp=datetime.now(),
                )
            )

    def search_with_result(
        self, query: str, options: Dict[str, Any]
    ) -> Result[List[PluginSearchResult]]:
        """Search for code patterns."""
        try:
            # Convert options to old format
            opts: SearchOpts = {}
            if "semantic" in options:
                opts["semantic"] = options["semantic"]
            if "limit" in options:
                opts["limit"] = options["limit"]

            results = self.search(query, opts)
            plugin_results = []

            for result in results:
                if isinstance(result, dict):
                    plugin_result = PluginSearchResult(
                        file_path=result.get("file", ""),
                        line=result.get("line", 1),
                        column=0,
                        snippet=result.get("content", result.get("match", "")),
                        match_type=("fuzzy" if not options.get("semantic") else "semantic"),
                        score=result.get("score", 1.0),
                        context=None,
                    )
                    plugin_results.append(plugin_result)

            return Result.success_result(plugin_results)

        except Exception as e:
            return Result.error_result(
                Error(
                    code="search_error",
                    message=f"Failed to search: {str(e)}",
                    details={"query": query, "exception": str(e)},
                    timestamp=datetime.now(),
                )
            )

    def validate_syntax(self, content: str) -> Result[bool]:
        """Validate syntax of code content."""
        try:
            # For HTML/CSS, we can try parsing with tree-sitter to validate
            # HTML validation
            try:
                tree = self._html_parser.parse(content.encode("utf-8"))
                if tree.root_node.has_error:
                    return Result.success_result(False)
            except Exception:
                # If HTML parsing fails, try CSS
                try:
                    tree = self._css_parser.parse(content.encode("utf-8"))
                    if tree.root_node.has_error:
                        return Result.success_result(False)
                except Exception:
                    return Result.success_result(False)

            return Result.success_result(True)

        except Exception as e:
            return Result.error_result(
                Error(
                    code="validation_error",
                    message=f"Failed to validate syntax: {str(e)}",
                    details={"exception": str(e)},
                    timestamp=datetime.now(),
                )
            )

    def get_completions(self, file_path: str, line: int, column: int) -> Result[List[str]]:
        """Get code completions at a position."""
        # HTML/CSS completions are complex and context-dependent
        # For now, return basic completions based on context
        try:
            path = Path(file_path)
            if not path.exists():
                return Result.success_result([])

            content = path.read_text(encoding="utf-8")
            lines = content.splitlines()

            if line >= len(lines):
                return Result.success_result([])

            current_line = lines[line]
            completions = []

            if self._is_html_file(path):
                # Basic HTML completions
                if "<" in current_line:
                    completions.extend(
                        ["div", "span", "p", "h1", "h2", "h3", "a", "img", "ul", "li"]
                    )
                if 'class="' in current_line or "class='" in current_line:
                    # Suggest existing classes
                    for classes in self._html_elements.values():
                        for element in classes:
                            completions.extend(element.get("classes", []))

            elif self._is_css_file(path):
                # Basic CSS completions
                if "{" not in current_line or current_line.count("{") > current_line.count("}"):
                    # In selector context
                    completions.extend([".class", "#id", "element", ":hover", ":active", ":focus"])
                else:
                    # In property context
                    completions.extend(
                        [
                            "color",
                            "background",
                            "padding",
                            "margin",
                            "border",
                            "font-size",
                            "display",
                            "position",
                            "width",
                            "height",
                            "flex",
                            "grid",
                        ]
                    )

            # Remove duplicates and sort
            completions = sorted(list(set(completions)))

            return Result.success_result(completions)

        except Exception as e:
            return Result.error_result(
                Error(
                    code="completions_error",
                    message=f"Failed to get completions: {str(e)}",
                    details={
                        "file_path": file_path,
                        "line": line,
                        "column": column,
                        "exception": str(e),
                    },
                    timestamp=datetime.now(),
                )
            )

    # ========================================
    # ILanguageAnalyzer Interface Implementation
    # ========================================

    def parse_imports(self, content: str) -> Result[List[str]]:
        """Parse import statements from content."""
        try:
            imports = []

            # CSS @import statements
            import_pattern = r'@import\s+["\']([^"\']+)["\']'
            matches = re.findall(import_pattern, content)
            imports.extend(matches)

            # HTML link tags for CSS
            link_pattern = r'<link[^>]+href=["\']([^"\']+\.css)["\']'
            matches = re.findall(link_pattern, content, re.IGNORECASE)
            imports.extend(matches)

            # HTML script tags for JS (related files)
            script_pattern = r'<script[^>]+src=["\']([^"\']+\.js)["\']'
            matches = re.findall(script_pattern, content, re.IGNORECASE)
            imports.extend(matches)

            return Result.success_result(imports)

        except Exception as e:
            return Result.error_result(
                Error(
                    code="parse_imports_error",
                    message=f"Failed to parse imports: {str(e)}",
                    details={"exception": str(e)},
                    timestamp=datetime.now(),
                )
            )

    def extract_symbols(self, content: str) -> Result[List[SymbolDefinition]]:
        """Extract all symbols from content."""
        try:
            # Use a temporary file path for parsing
            temp_path = "temp.html" if "<" in content else "temp.css"
            index_result = self.index(temp_path, content)

            if not index_result.success:
                return Result.error_result(index_result.error)

            return Result.success_result(index_result.value.symbols)

        except Exception as e:
            return Result.error_result(
                Error(
                    code="extract_symbols_error",
                    message=f"Failed to extract symbols: {str(e)}",
                    details={"exception": str(e)},
                    timestamp=datetime.now(),
                )
            )

    def resolve_type(self, symbol: str, context: Dict[str, Any]) -> Result[Optional[str]]:
        """Resolve the type of a symbol."""
        try:
            # Determine symbol type based on prefix/pattern
            if symbol.startswith("#"):
                return Result.success_result("id")
            elif symbol.startswith("."):
                return Result.success_result("class")
            elif symbol.startswith("@keyframes"):
                return Result.success_result("keyframes")
            elif symbol.startswith("@media"):
                return Result.success_result("media-query")
            elif symbol.startswith("--"):
                return Result.success_result("css-variable")
            elif "-" in symbol and not symbol.startswith(".") and not symbol.startswith("#"):
                return Result.success_result("custom-element")
            elif symbol.startswith("[") and symbol.endswith("]"):
                return Result.success_result("attribute-selector")
            else:
                return Result.success_result("element")

        except Exception as e:
            return Result.error_result(
                Error(
                    code="resolve_type_error",
                    message=f"Failed to resolve type: {str(e)}",
                    details={"symbol": symbol, "exception": str(e)},
                    timestamp=datetime.now(),
                )
            )

    def get_call_hierarchy(
        self, symbol: str, context: Dict[str, Any]
    ) -> Result[Dict[str, List[str]]]:
        """Get call hierarchy for a symbol."""
        try:
            # For HTML/CSS, call hierarchy means CSS selectors that target HTML elements
            hierarchy = {
                "callers": [],  # CSS selectors that use this symbol
                "callees": [],  # HTML elements that this CSS selector targets
            }

            if symbol.startswith(".") or symbol.startswith("#"):
                # CSS selector - find HTML elements it targets
                refs = self.findReferences(symbol)
                for ref in refs:
                    if ref.file.endswith((".html", ".htm")):
                        hierarchy["callees"].append(ref.file)
            else:
                # HTML element - find CSS selectors that target it
                # Convert element to potential selectors
                potential_selectors = [f".{symbol}", f"#{symbol}", symbol]
                for selector in potential_selectors:
                    refs = self.findReferences(selector)
                    for ref in refs:
                        if ref.file.endswith((".css", ".scss", ".sass", ".less")):
                            hierarchy["callers"].append(selector)

            return Result.success_result(hierarchy)

        except Exception as e:
            return Result.error_result(
                Error(
                    code="call_hierarchy_error",
                    message=f"Failed to get call hierarchy: {str(e)}",
                    details={"symbol": symbol, "exception": str(e)},
                    timestamp=datetime.now(),
                )
            )

    # ========================================
    # IHtmlCssPlugin Interface Implementation
    # ========================================

    def extract_selectors(self, css_content: str) -> Result[List[str]]:
        """Extract CSS selectors."""
        try:
            tree = self._css_parser.parse(css_content.encode("utf-8"))
            root = tree.root_node

            selectors = []
            self._collect_css_selectors(root, css_content, selectors)

            return Result.success_result(selectors)

        except Exception as e:
            return Result.error_result(
                Error(
                    code="extract_selectors_error",
                    message=f"Failed to extract selectors: {str(e)}",
                    details={"exception": str(e)},
                    timestamp=datetime.now(),
                )
            )

    def find_css_usage(self, html_content: str) -> Result[List[str]]:
        """Find CSS class/ID usage in HTML."""
        try:
            tree = self._html_parser.parse(html_content.encode("utf-8"))
            root = tree.root_node

            css_usage = []
            self._collect_html_css_usage(root, html_content, css_usage)

            return Result.success_result(css_usage)

        except Exception as e:
            return Result.error_result(
                Error(
                    code="find_css_usage_error",
                    message=f"Failed to find CSS usage: {str(e)}",
                    details={"exception": str(e)},
                    timestamp=datetime.now(),
                )
            )

    def _collect_css_selectors(self, node: Node, content: str, selectors: List[str]) -> None:
        """Recursively collect CSS selectors from AST."""
        if node.type == "rule_set":
            for child in node.children:
                if child.type == "selectors":
                    selector_list = self._extract_css_selectors(child, content)
                    selectors.extend(selector_list)

        for child in node.children:
            self._collect_css_selectors(child, content, selectors)

    def _collect_html_css_usage(self, node: Node, content: str, css_usage: List[str]) -> None:
        """Recursively collect CSS class/ID usage from HTML AST."""
        if node.type == "element":
            attributes = self._extract_html_attributes(node, content)

            if "id" in attributes:
                css_usage.append(f"#{attributes['id']}")

            if "class" in attributes:
                classes = attributes["class"].split()
                for class_name in classes:
                    css_usage.append(f".{class_name}")

        for child in node.children:
            self._collect_html_css_usage(child, content, css_usage)

    # ========================================
    # Legacy IPlugin Interface Implementation
    # ========================================

    def _preindex(self) -> None:
        """Pre-index all supported files in the current directory."""
        for pattern in ["*.html", "*.htm", "*.css", "*.scss", "*.sass", "*.less"]:
            for path in Path(".").rglob(pattern):
                try:
                    # Skip common build directories
                    if any(
                        part in path.parts
                        for part in ["node_modules", "dist", "build", ".next", "vendor"]
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
        suffixes = {".html", ".htm", ".css", ".scss", ".sass", ".less"}
        return Path(path).suffix.lower() in suffixes

    def _is_css_file(self, path: Path) -> bool:
        """Check if the file is a CSS file."""
        return path.suffix.lower() in {".css", ".scss", ".sass", ".less"}

    def _is_html_file(self, path: Path) -> bool:
        """Check if the file is an HTML file."""
        return path.suffix.lower() in {".html", ".htm"}

    def indexFile(self, path: str | Path, content: str) -> IndexShard:
        """Parse and index an HTML or CSS file."""
        if isinstance(path, str):
            path = Path(path)

        self._current_file = path
        self._indexer.add_file(str(path), content)

        # Store file in SQLite if available
        file_id = None
        if self._sqlite_store and self._repository_id:
            file_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            language = "html" if self._is_html_file(path) else "css"
            # Handle relative path calculation safely
            try:
                relative_path = str(path.relative_to(Path.cwd()))
            except ValueError:
                # If path is not under cwd, just use the path as-is
                relative_path = str(path)

            file_id = self._sqlite_store.store_file(
                self._repository_id,
                str(path),
                relative_path,
                language=language,
                size=len(content),
                hash=file_hash,
            )

        symbols: List[Dict[str, Any]] = []

        if self._is_html_file(path):
            symbols = self._index_html_file(path, content, file_id)
        else:
            symbols = self._index_css_file(path, content, file_id)

        # Cache symbols for quick lookup
        cache_key = str(path)
        self._symbol_cache[cache_key] = [
            self._symbol_to_def(s, str(path), content) for s in symbols
        ]

        return {"file": str(path), "symbols": symbols, "language": self.lang}

    def _index_html_file(
        self, path: Path, content: str, file_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Index an HTML file."""
        tree = self._html_parser.parse(content.encode("utf-8"))
        root = tree.root_node

        symbols: List[Dict[str, Any]] = []
        elements: List[Dict[str, Any]] = []

        self._extract_html_symbols(root, content, symbols, elements, file_id)

        # Store elements for cross-reference
        self._html_elements[str(path)] = elements

        return symbols

    def _index_css_file(
        self, path: Path, content: str, file_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Index a CSS file."""
        tree = self._css_parser.parse(content.encode("utf-8"))
        root = tree.root_node

        symbols: List[Dict[str, Any]] = []
        selectors: List[Dict[str, Any]] = []

        self._extract_css_symbols(root, content, symbols, selectors, file_id)

        # Store selectors for cross-reference
        self._css_selectors[str(path)] = selectors

        return symbols

    def _extract_html_symbols(
        self,
        node: Node,
        content: str,
        symbols: List[Dict],
        elements: List[Dict],
        file_id: Optional[int] = None,
    ) -> None:
        """Extract symbols from HTML AST."""
        if node.type == "element":
            # Extract tag name from start_tag
            tag_name = None
            start_tag = None

            for child in node.children:
                if child.type == "start_tag":
                    start_tag = child
                    # Find tag name in start_tag
                    for tag_child in child.children:
                        if tag_child.type == "tag_name":
                            tag_name = content[tag_child.start_byte : tag_child.end_byte]
                            break
                    break

            if tag_name and start_tag:
                # Extract attributes
                attributes = self._extract_html_attributes(node, content)

                # Look for id attribute
                if "id" in attributes:
                    id_value = attributes["id"]
                    symbol_info = {
                        "symbol": f"#{id_value}",
                        "kind": "id",
                        "signature": f'<{tag_name} id="{id_value}">',
                        "line": node.start_point[0] + 1,
                        "span": (node.start_point[0] + 1, node.end_point[0] + 1),
                        "tag": tag_name,
                    }
                    symbols.append(symbol_info)

                    # Store in SQLite if available
                    if self._sqlite_store and file_id:
                        symbol_id = self._sqlite_store.store_symbol(
                            file_id,
                            f"#{id_value}",
                            "id",
                            node.start_point[0] + 1,
                            node.end_point[0] + 1,
                            signature=symbol_info["signature"],
                        )
                        self._indexer.add_symbol(
                            f"#{id_value}",
                            str(self._current_file or "unknown"),
                            node.start_point[0] + 1,
                            {"symbol_id": symbol_id, "file_id": file_id},
                        )

                # Look for class attributes
                if "class" in attributes:
                    classes = attributes["class"].split()
                    for class_name in classes:
                        symbol_info = {
                            "symbol": f".{class_name}",
                            "kind": "class",
                            "signature": f'<{tag_name} class="{class_name}">',
                            "line": node.start_point[0] + 1,
                            "span": (node.start_point[0] + 1, node.end_point[0] + 1),
                            "tag": tag_name,
                        }
                        symbols.append(symbol_info)

                        # Store in SQLite if available
                        if self._sqlite_store and file_id:
                            symbol_id = self._sqlite_store.store_symbol(
                                file_id,
                                f".{class_name}",
                                "class",
                                node.start_point[0] + 1,
                                node.end_point[0] + 1,
                                signature=symbol_info["signature"],
                            )
                            self._indexer.add_symbol(
                                f".{class_name}",
                                str(self._current_file or "unknown"),
                                node.start_point[0] + 1,
                                {"symbol_id": symbol_id, "file_id": file_id},
                            )

                # Look for custom elements (with hyphen)
                if "-" in tag_name:
                    symbol_info = {
                        "symbol": tag_name,
                        "kind": "custom-element",
                        "signature": f"<{tag_name}>",
                        "line": node.start_point[0] + 1,
                        "span": (node.start_point[0] + 1, node.end_point[0] + 1),
                    }
                    symbols.append(symbol_info)

                    # Store in SQLite if available
                    if self._sqlite_store and file_id:
                        symbol_id = self._sqlite_store.store_symbol(
                            file_id,
                            tag_name,
                            "custom-element",
                            node.start_point[0] + 1,
                            node.end_point[0] + 1,
                            signature=symbol_info["signature"],
                        )
                        self._indexer.add_symbol(
                            tag_name,
                            str(self._current_file or "unknown"),
                            node.start_point[0] + 1,
                            {"symbol_id": symbol_id, "file_id": file_id},
                        )

                # Look for data attributes
                for attr_name, attr_value in attributes.items():
                    if attr_name.startswith("data-"):
                        symbol_info = {
                            "symbol": f"[{attr_name}]",
                            "kind": "data-attribute",
                            "signature": f'{attr_name}="{attr_value}"',
                            "line": node.start_point[0] + 1,
                            "tag": tag_name,
                        }
                        symbols.append(symbol_info)

                # Store element info for cross-reference
                elements.append(
                    {
                        "tag": tag_name,
                        "id": attributes.get("id"),
                        "classes": (
                            attributes.get("class", "").split() if "class" in attributes else []
                        ),
                        "attributes": attributes,
                        "line": node.start_point[0] + 1,
                    }
                )

        # Continue recursion
        for child in node.children:
            self._extract_html_symbols(child, content, symbols, elements, file_id)

    def _extract_html_attributes(self, element_node: Node, content: str) -> Dict[str, str]:
        """Extract attributes from an HTML element node."""
        attributes = {}

        # Look for attribute nodes
        for child in element_node.children:
            if child.type == "start_tag":
                for attr_child in child.children:
                    if attr_child.type == "attribute":
                        attr_name = None
                        attr_value = ""

                        # Extract attribute name and value
                        for attr_part in attr_child.children:
                            if attr_part.type == "attribute_name":
                                attr_name = content[attr_part.start_byte : attr_part.end_byte]
                            elif attr_part.type == "quoted_attribute_value":
                                # Get the actual value inside the quotes
                                for value_child in attr_part.children:
                                    if value_child.type == "attribute_value":
                                        attr_value = content[
                                            value_child.start_byte : value_child.end_byte
                                        ]
                                        break

                        if attr_name is not None:
                            attributes[attr_name] = attr_value

        return attributes

    def _extract_css_symbols(
        self,
        node: Node,
        content: str,
        symbols: List[Dict],
        selectors: List[Dict],
        file_id: Optional[int] = None,
        parent_selector: Optional[str] = None,
    ) -> None:
        """Extract symbols from CSS AST."""
        if node.type == "rule_set":
            # Extract selectors
            selector_list = []
            for child in node.children:
                if child.type == "selectors":
                    selector_list = self._extract_css_selectors(child, content)
                    break

            # Process each selector
            for selector in selector_list:
                # Combine with parent selector if in nested context
                if parent_selector:
                    if selector.startswith("&"):
                        selector = parent_selector + selector[1:]
                    else:
                        selector = f"{parent_selector} {selector}"

                # Determine selector type
                if selector.startswith("#"):
                    kind = "id"
                elif ":" in selector:
                    kind = "pseudo-selector"
                elif selector.startswith("."):
                    kind = "class"
                elif selector.startswith("[") and selector.endswith("]"):
                    kind = "attribute-selector"
                else:
                    kind = "element-selector"

                symbol_info = {
                    "symbol": selector,
                    "kind": kind,
                    "signature": f"{selector} {{ }}",
                    "line": node.start_point[0] + 1,
                    "span": (node.start_point[0] + 1, node.end_point[0] + 1),
                }
                symbols.append(symbol_info)

                # Store in SQLite if available
                if self._sqlite_store and file_id:
                    symbol_id = self._sqlite_store.store_symbol(
                        file_id,
                        selector,
                        kind,
                        node.start_point[0] + 1,
                        node.end_point[0] + 1,
                        signature=symbol_info["signature"],
                    )
                    self._indexer.add_symbol(
                        selector,
                        str(self._current_file or "unknown"),
                        node.start_point[0] + 1,
                        {"symbol_id": symbol_id, "file_id": file_id},
                    )

                # Store selector for cross-reference
                selectors.append(
                    {
                        "selector": selector,
                        "kind": kind,
                        "line": node.start_point[0] + 1,
                    }
                )

            # Process nested rules (for SCSS/Sass)
            block_node = None
            for child in node.children:
                if child.type == "block":
                    block_node = child
                    break

            if block_node:
                for child in block_node.children:
                    if child.type == "rule_set":
                        # Nested rule
                        for selector in selector_list:
                            self._extract_css_symbols(
                                child, content, symbols, selectors, file_id, selector
                            )

        elif node.type == "keyframes_statement":
            # Extract @keyframes
            keyframe_name = None
            for child in node.children:
                if child.type == "keyframes_name":
                    keyframe_name = content[child.start_byte : child.end_byte]
                    break

            if keyframe_name:
                symbol_info = {
                    "symbol": f"@keyframes {keyframe_name}",
                    "kind": "keyframes",
                    "signature": f"@keyframes {keyframe_name} {{ }}",
                    "line": node.start_point[0] + 1,
                    "span": (node.start_point[0] + 1, node.end_point[0] + 1),
                }
                symbols.append(symbol_info)

                if self._sqlite_store and file_id:
                    symbol_id = self._sqlite_store.store_symbol(
                        file_id,
                        f"@keyframes {keyframe_name}",
                        "keyframes",
                        node.start_point[0] + 1,
                        node.end_point[0] + 1,
                        signature=symbol_info["signature"],
                    )
                    self._indexer.add_symbol(
                        f"@keyframes {keyframe_name}",
                        str(self._current_file or "unknown"),
                        node.start_point[0] + 1,
                        {"symbol_id": symbol_id, "file_id": file_id},
                    )

        elif node.type in [
            "media_statement",
            "supports_statement",
            "charset_statement",
            "import_statement",
            "namespace_statement",
        ]:
            # Extract other @rules
            rule_type = node.type.replace("_statement", "")
            rule_text = content[node.start_byte : node.end_byte]

            # For rules with blocks, extract just the part before the block
            if "{" in rule_text:
                rule_text = rule_text.split("{")[0].strip()
            else:
                rule_text = rule_text.strip()

            # Special handling for media queries to match test expectations
            if rule_type == "media":
                kind = "media-query"
            else:
                kind = f"{rule_type}-rule"

            symbol_info = {
                "symbol": rule_text,
                "kind": kind,
                "signature": rule_text + " { }",
                "line": node.start_point[0] + 1,
                "span": (node.start_point[0] + 1, node.end_point[0] + 1),
            }
            symbols.append(symbol_info)

            # Store in SQLite if available
            if self._sqlite_store and file_id:
                symbol_id = self._sqlite_store.store_symbol(
                    file_id,
                    rule_text,
                    kind,
                    node.start_point[0] + 1,
                    node.end_point[0] + 1,
                    signature=symbol_info["signature"],
                )
                self._indexer.add_symbol(
                    rule_text,
                    str(self._current_file or "unknown"),
                    node.start_point[0] + 1,
                    {"symbol_id": symbol_id, "file_id": file_id},
                )

        elif node.type == "declaration":
            # Extract CSS variables
            prop_name = None
            prop_value_parts = []

            for child in node.children:
                if child.type == "property_name":
                    prop_name = content[child.start_byte : child.end_byte]
                elif child.type not in [":", ";", " ", "\n"]:
                    # Collect all value parts
                    prop_value_parts.append(content[child.start_byte : child.end_byte])

            if prop_name and prop_name.startswith("--"):
                # CSS variable
                prop_value = " ".join(prop_value_parts)
                symbol_info = {
                    "symbol": prop_name,
                    "kind": "css-variable",
                    "signature": f"{prop_name}: {prop_value}",
                    "line": node.start_point[0] + 1,
                }
                symbols.append(symbol_info)

                if self._sqlite_store and file_id:
                    symbol_id = self._sqlite_store.store_symbol(
                        file_id,
                        prop_name,
                        "css-variable",
                        node.start_point[0] + 1,
                        node.start_point[0] + 1,
                        signature=symbol_info["signature"],
                    )
                    self._indexer.add_symbol(
                        prop_name,
                        str(self._current_file or "unknown"),
                        node.start_point[0] + 1,
                        {"symbol_id": symbol_id, "file_id": file_id},
                    )

        # For preprocessor features (SCSS/Sass)
        elif node.type == "mixin_statement":
            # SCSS mixin
            name_node = None
            for child in node.children:
                if child.type == "identifier":
                    name_node = child
                    break

            if name_node:
                mixin_name = content[name_node.start_byte : name_node.end_byte]
                symbol_info = {
                    "symbol": f"@mixin {mixin_name}",
                    "kind": "mixin",
                    "signature": f"@mixin {mixin_name}()",
                    "line": node.start_point[0] + 1,
                    "span": (node.start_point[0] + 1, node.end_point[0] + 1),
                }
                symbols.append(symbol_info)

        # Continue recursion for all node types
        for child in node.children:
            self._extract_css_symbols(child, content, symbols, selectors, file_id, parent_selector)

    def _extract_css_selectors(self, selectors_node: Node, content: str) -> List[str]:
        """Extract selectors from a selectors node."""
        # For simple cases, just extract the text content
        selector_text = content[selectors_node.start_byte : selectors_node.end_byte]

        # Split by comma for multiple selectors
        if "," in selector_text:
            selectors = [s.strip() for s in selector_text.split(",")]
        else:
            selectors = [selector_text.strip()]

        # Filter out empty selectors
        return [s for s in selectors if s]

    def _symbol_to_def(self, symbol: Dict[str, Any], file_path: str, content: str) -> SymbolDef:
        """Convert internal symbol representation to SymbolDef."""
        return {
            "symbol": symbol["symbol"],
            "kind": symbol["kind"],
            "language": self.lang,
            "signature": symbol["signature"],
            "doc": None,  # HTML/CSS don't typically have inline docs
            "defined_in": file_path,
            "line": symbol.get("line", 1),
            "span": symbol.get("span", (symbol.get("line", 1), symbol.get("line", 1) + 1)),
        }

    def getDefinition(self, symbol: str) -> SymbolDef | None:
        """Get the definition of a symbol."""
        # First check cache
        for file_path, symbols in self._symbol_cache.items():
            for sym_def in symbols:
                if sym_def["symbol"] == symbol:
                    return sym_def

        # Search in all supported files
        for pattern in ["*.html", "*.htm", "*.css", "*.scss", "*.sass", "*.less"]:
            for path in Path(".").rglob(pattern):
                try:
                    # Skip common build directories
                    if any(
                        part in path.parts
                        for part in ["node_modules", "dist", "build", ".next", "vendor"]
                    ):
                        continue

                    content = path.read_text(encoding="utf-8")
                    shard = self.indexFile(path, content)

                    for sym in shard["symbols"]:
                        if sym["symbol"] == symbol:
                            return self._symbol_to_def(sym, str(path), content)
                except Exception:
                    continue

        return None

    def findReferences(self, symbol: str) -> list[Reference]:
        """Find all references to a symbol, including cross-references between HTML and CSS."""
        refs: List[Reference] = []
        seen: Set[Tuple[str, int]] = set()

        # Determine symbol type
        symbol_type = None
        if symbol.startswith("#"):
            symbol_type = "id"
            symbol_value = symbol[1:]  # Remove #
        elif symbol.startswith("."):
            symbol_type = "class"
            symbol_value = symbol[1:]  # Remove .
        else:
            symbol_type = "other"
            symbol_value = symbol

        # Search in HTML files
        for pattern in ["*.html", "*.htm"]:
            for path in Path(".").rglob(pattern):
                try:
                    if any(
                        part in path.parts
                        for part in ["node_modules", "dist", "build", ".next", "vendor"]
                    ):
                        continue

                    content = path.read_text(encoding="utf-8")
                    lines = content.splitlines()

                    for i, line in enumerate(lines):
                        found = False

                        if symbol_type == "id":
                            # Look for id="value" or id='value'
                            if re.search(rf'id\s*=\s*["\']({re.escape(symbol_value)})["\']', line):
                                found = True
                        elif symbol_type == "class":
                            # Look for class="... value ..." or class='... value ...'
                            if re.search(
                                rf'class\s*=\s*["\'][^"\']*\b{re.escape(symbol_value)}\b[^"\']*["\']',
                                line,
                            ):
                                found = True
                        else:
                            # Look for custom elements or data attributes
                            if re.search(rf"<{re.escape(symbol_value)}[\s>]", line) or re.search(
                                rf"{re.escape(symbol_value)}\s*=", line
                            ):
                                found = True

                        if found:
                            line_no = i + 1
                            key = (str(path), line_no)
                            if key not in seen:
                                refs.append(Reference(file=str(path), line=line_no))
                                seen.add(key)

                except Exception:
                    continue

        # Search in CSS files
        for pattern in ["*.css", "*.scss", "*.sass", "*.less"]:
            for path in Path(".").rglob(pattern):
                try:
                    if any(
                        part in path.parts
                        for part in ["node_modules", "dist", "build", ".next", "vendor"]
                    ):
                        continue

                    content = path.read_text(encoding="utf-8")
                    lines = content.splitlines()

                    for i, line in enumerate(lines):
                        # Look for the symbol as a selector or reference
                        # Use a more flexible pattern for CSS selectors
                        escaped_symbol = re.escape(symbol)
                        if re.search(escaped_symbol, line):
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
        results = self._indexer.search(query, limit=limit)

        # Convert to SearchResult objects if they're not already
        search_results = []
        for result in results:
            if isinstance(result, dict):
                # Convert dict result to SearchResult format
                search_results.append(
                    {
                        "file": result.get("file", ""),
                        "line": result.get("line", 1),
                        "snippet": result.get("snippet", result.get("content", "")),
                    }
                )
            else:
                search_results.append(result)

        # If query looks like a CSS selector or HTML element, boost relevant results
        if query.startswith("#") or query.startswith(".") or query.startswith("["):
            # Boost exact matches for selectors
            for result in search_results:
                if result.get("match", "").strip() == query:
                    result["score"] = result.get("score", 1.0) * 2.0

        # Sort by score
        search_results.sort(key=lambda x: x.get("score", 0), reverse=True)

        return search_results[:limit]

    def get_indexed_count(self) -> int:
        """Return the number of indexed files."""
        # Count unique files in the symbol cache
        return len(self._symbol_cache)

    def get_cross_references(self, symbol: str) -> Dict[str, List[Reference]]:
        """Get cross-references between HTML and CSS files for a symbol.

        This is an additional method to help find where CSS selectors are used in HTML
        and vice versa.
        """
        refs = {"html_usage": [], "css_definitions": []}

        # If it's a CSS selector, find HTML usage
        if symbol.startswith("#") or symbol.startswith("."):
            refs["html_usage"] = [
                ref for ref in self.findReferences(symbol) if ref.file.endswith((".html", ".htm"))
            ]
            refs["css_definitions"] = [
                ref
                for ref in self.findReferences(symbol)
                if ref.file.endswith((".css", ".scss", ".sass", ".less"))
            ]

        return refs
