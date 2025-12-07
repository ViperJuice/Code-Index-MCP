from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

# Interfaces from shared interfaces
from ...interfaces.plugin_interfaces import (
    IDartPlugin,
    ILanguageAnalyzer,
    IndexedFile,
)
from ...interfaces.plugin_interfaces import SearchResult as SearchResultInterface
from ...interfaces.plugin_interfaces import (
    SymbolDefinition,
    SymbolReference,
)
from ...interfaces.shared_interfaces import Error, Result

# Base plugin interface from plugin_base.py
from ...plugin_base import (
    IndexShard,
    IPlugin,
    Reference,
    SearchOpts,
    SearchResult,
    SymbolDef,
)
from ...storage.sqlite_store import SQLiteStore

# Utilities
from ...utils.fuzzy_indexer import FuzzyIndexer

logger = logging.getLogger(__name__)


class Plugin(IPlugin, IDartPlugin, ILanguageAnalyzer):
    """Complete Dart/Flutter plugin implementation.

    Implements both the base IPlugin interface and the IDartPlugin interface,
    providing comprehensive Dart language analysis including Flutter framework support.

    Features:
    - File extensions: .dart
    - Symbol extraction: classes, functions, methods, variables, enums, mixins, extensions
    - Dart-specific features: widgets, state classes, async/await, futures, streams, annotations
    - Flutter-specific features: widget hierarchy, state management, build methods
    - Package imports and pub.dev dependencies
    - Tree-sitter integration (fallback to regex-based parsing)
    """

    # Base IPlugin properties
    lang = "dart"

    def __init__(self, sqlite_store: Optional[SQLiteStore] = None) -> None:
        """Initialize the Dart/Flutter plugin.

        Args:
            sqlite_store: Optional SQLite store for persistence
        """
        # Initialize indexer and storage
        self._indexer = FuzzyIndexer(sqlite_store=sqlite_store)
        self._sqlite_store = sqlite_store
        self._repository_id = None

        # Symbol cache for faster lookups
        self._symbol_cache: Dict[str, List[SymbolDefinition]] = {}
        self._file_cache: Dict[str, IndexedFile] = {}

        # Current file context
        self._current_file: Optional[Path] = None

        # Create or get repository if SQLite is enabled
        if self._sqlite_store:
            self._repository_id = self._sqlite_store.create_repository(
                str(Path.cwd()), Path.cwd().name, {"language": "dart"}
            )

        # Pre-index existing files
        self._preindex()

    # ========================================
    # IDartPlugin Interface Implementation
    # ========================================

    @property
    def name(self) -> str:
        """Get the plugin name"""
        return "dart_plugin"

    @property
    def supported_extensions(self) -> List[str]:
        """Get list of file extensions this plugin supports"""
        return [".dart"]

    @property
    def supported_languages(self) -> List[str]:
        """Get list of programming languages this plugin supports"""
        return ["dart", "flutter"]

    def can_handle(self, file_path: str) -> bool:
        """Check if this plugin can handle the given file"""
        return Path(file_path).suffix == ".dart"

    def index(self, file_path: str, content: Optional[str] = None) -> Result[IndexedFile]:
        """Index a file and extract symbols using Result pattern"""
        try:
            if content is None:
                content = Path(file_path).read_text(encoding="utf-8")

            # Get file stats (if file exists) or use defaults
            path = Path(file_path)
            if path.exists():
                file_stats = path.stat()
                last_modified = file_stats.st_mtime
                size = file_stats.st_size
            else:
                # For in-memory content or non-existent files
                last_modified = datetime.now().timestamp()
                size = len(content) if content else 0

            # Extract symbols
            symbols = self._extract_all_symbols(content or "", file_path)

            # Create IndexedFile
            indexed_file = IndexedFile(
                file_path=file_path,
                last_modified=last_modified,
                size=size,
                symbols=symbols,
                language="dart",
                encoding="utf-8",
            )

            # Cache the result
            self._file_cache[file_path] = indexed_file
            self._symbol_cache[file_path] = symbols

            # Also update the legacy indexer
            if content is not None:
                self.indexFile(file_path, content)

            return Result.success_result(indexed_file)

        except Exception as e:
            error = Error(
                code="INDEXING_ERROR",
                message=f"Failed to index file {file_path}: {str(e)}",
                details={"file_path": file_path, "exception": str(e)},
                timestamp=datetime.now(),
            )
            return Result.error_result(error)

    def get_definition(
        self, symbol: str, context: Dict[str, Any]
    ) -> Result[Optional[SymbolDefinition]]:
        """Get the definition of a symbol using Result pattern"""
        try:
            # First check cache
            for file_path, symbols in self._symbol_cache.items():
                for sym_def in symbols:
                    if sym_def.symbol == symbol or sym_def.symbol.endswith(f".{symbol}"):
                        return Result.success_result(sym_def)

            # Search in all Dart files
            definition = self._find_symbol_definition(symbol)
            return Result.success_result(definition)

        except Exception as e:
            error = Error(
                code="DEFINITION_ERROR",
                message=f"Failed to get definition for symbol {symbol}: {str(e)}",
                details={"symbol": symbol, "context": context, "exception": str(e)},
                timestamp=datetime.now(),
            )
            return Result.error_result(error)

    def get_references(self, symbol: str, context: Dict[str, Any]) -> Result[List[SymbolReference]]:
        """Get all references to a symbol using Result pattern"""
        try:
            references = self._find_symbol_references(symbol)
            return Result.success_result(references)

        except Exception as e:
            error = Error(
                code="REFERENCES_ERROR",
                message=f"Failed to get references for symbol {symbol}: {str(e)}",
                details={"symbol": symbol, "context": context, "exception": str(e)},
                timestamp=datetime.now(),
            )
            return Result.error_result(error)

    def search_with_result(
        self, query: str, options: Dict[str, Any]
    ) -> Result[List[SearchResultInterface]]:
        """Search for code patterns using Result pattern (IDartPlugin interface)"""
        try:
            limit = options.get("limit", 20)
            results = self._perform_search(query, limit)
            return Result.success_result(results)

        except Exception as e:
            error = Error(
                code="SEARCH_ERROR",
                message=f"Failed to search for query {query}: {str(e)}",
                details={"query": query, "options": options, "exception": str(e)},
                timestamp=datetime.now(),
            )
            return Result.error_result(error)

    def validate_syntax(self, content: str) -> Result[bool]:
        """Validate syntax of Dart code content"""
        try:
            # Basic syntax validation using regex patterns
            # Check for balanced braces, quotes, and basic Dart syntax
            is_valid = self._validate_dart_syntax(content)
            return Result.success_result(is_valid)

        except Exception as e:
            error = Error(
                code="VALIDATION_ERROR",
                message=f"Failed to validate syntax: {str(e)}",
                details={"exception": str(e)},
                timestamp=datetime.now(),
            )
            return Result.error_result(error)

    def get_completions(self, file_path: str, line: int, column: int) -> Result[List[str]]:
        """Get code completions at a position"""
        try:
            # Basic completion based on symbols in scope
            completions = self._get_dart_completions(file_path, line, column)
            return Result.success_result(completions)

        except Exception as e:
            error = Error(
                code="COMPLETION_ERROR",
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

    # Dart-specific interface methods
    def parse_flutter_widgets(self, content: str) -> Result[List[SymbolDefinition]]:
        """Parse Flutter widget definitions"""
        try:
            widgets = self._extract_flutter_widgets(content)
            return Result.success_result(widgets)

        except Exception as e:
            error = Error(
                code="WIDGET_PARSE_ERROR",
                message=f"Failed to parse Flutter widgets: {str(e)}",
                details={"exception": str(e)},
                timestamp=datetime.now(),
            )
            return Result.error_result(error)

    def resolve_packages(self, file_path: str) -> Result[List[str]]:
        """Resolve package dependencies"""
        try:
            packages = self._resolve_dart_packages(file_path)
            return Result.success_result(packages)

        except Exception as e:
            error = Error(
                code="PACKAGE_RESOLVE_ERROR",
                message=f"Failed to resolve packages for {file_path}: {str(e)}",
                details={"file_path": file_path, "exception": str(e)},
                timestamp=datetime.now(),
            )
            return Result.error_result(error)

    # ILanguageAnalyzer interface methods
    def parse_imports(self, content: str) -> Result[List[str]]:
        """Parse import statements from content"""
        try:
            imports = self._extract_imports_list(content)
            return Result.success_result(imports)

        except Exception as e:
            error = Error(
                code="IMPORT_PARSE_ERROR",
                message=f"Failed to parse imports: {str(e)}",
                details={"exception": str(e)},
                timestamp=datetime.now(),
            )
            return Result.error_result(error)

    def extract_symbols(self, content: str) -> Result[List[SymbolDefinition]]:
        """Extract all symbols from content"""
        try:
            symbols = self._extract_all_symbols(content, "temp_file.dart")
            return Result.success_result(symbols)

        except Exception as e:
            error = Error(
                code="SYMBOL_EXTRACT_ERROR",
                message=f"Failed to extract symbols: {str(e)}",
                details={"exception": str(e)},
                timestamp=datetime.now(),
            )
            return Result.error_result(error)

    def resolve_type(self, symbol: str, context: Dict[str, Any]) -> Result[Optional[str]]:
        """Resolve the type of a symbol"""
        try:
            symbol_type = self._resolve_symbol_type(symbol, context)
            return Result.success_result(symbol_type)

        except Exception as e:
            error = Error(
                code="TYPE_RESOLVE_ERROR",
                message=f"Failed to resolve type for symbol {symbol}: {str(e)}",
                details={"symbol": symbol, "context": context, "exception": str(e)},
                timestamp=datetime.now(),
            )
            return Result.error_result(error)

    def get_call_hierarchy(
        self, symbol: str, context: Dict[str, Any]
    ) -> Result[Dict[str, List[str]]]:
        """Get call hierarchy for a symbol"""
        try:
            hierarchy = self._get_dart_call_hierarchy(symbol, context)
            return Result.success_result(hierarchy)

        except Exception as e:
            error = Error(
                code="CALL_HIERARCHY_ERROR",
                message=f"Failed to get call hierarchy for symbol {symbol}: {str(e)}",
                details={"symbol": symbol, "context": context, "exception": str(e)},
                timestamp=datetime.now(),
            )
            return Result.error_result(error)

    # ========================================
    # Base IPlugin Interface Implementation
    # ========================================

    def supports(self, path: str | Path) -> bool:
        """Check if this plugin supports the given file"""
        return Path(path).suffix == ".dart"

    def indexFile(self, path: str | Path, content: str) -> IndexShard:
        """Parse and index a Dart file (legacy interface)"""
        if isinstance(path, str):
            path = Path(path)

        self._current_file = path
        self._indexer.add_file(str(path), content)

        # Store file in SQLite if available
        file_id = None
        if self._sqlite_store and self._repository_id:
            import hashlib

            file_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            file_id = self._sqlite_store.store_file(
                self._repository_id,
                str(path),
                str(path.relative_to(Path.cwd())),
                language="dart",
                size=len(content),
                hash=file_hash,
            )

        # Extract symbols using legacy format
        symbols: List[Dict[str, Any]] = []
        imports: List[Dict[str, Any]] = []
        exports: List[Dict[str, Any]] = []

        self._extract_symbols_legacy(content, symbols, imports, exports, file_id)

        return {
            "file": str(path),
            "symbols": symbols,
            "language": self.lang,
            "imports": imports,
            "exports": exports,
        }

    def getDefinition(self, symbol: str) -> SymbolDef | None:
        """Get the definition of a symbol (legacy interface)"""
        # Convert from new format to legacy format
        result = self.get_definition(symbol, {})
        if result.success and result.value:
            sym_def = result.value
            return {
                "symbol": sym_def.symbol,
                "kind": sym_def.symbol_type,
                "language": self.lang,
                "signature": sym_def.signature or "",
                "doc": sym_def.docstring,
                "defined_in": sym_def.file_path,
                "line": sym_def.line,
                "span": (sym_def.line, sym_def.line + 5),
            }
        return None

    def findReferences(self, symbol: str) -> list[Reference]:
        """Find all references to a symbol (legacy interface)"""
        result = self.get_references(symbol, {})
        if result.success and result.value:
            return [Reference(file=ref.file_path, line=ref.line) for ref in result.value]
        return []

    def search(self, query: str, opts: SearchOpts | None = None) -> Iterable[SearchResult]:
        """Search for code snippets matching a query (legacy interface)"""
        options = {}
        if opts:
            if "limit" in opts:
                options["limit"] = opts["limit"]
            if opts.get("semantic"):
                options["semantic"] = True

        # Call the internal search method directly to avoid name collision
        fuzzy_results = self._indexer.search(query, limit=options.get("limit", 20))

        # Convert to legacy format
        return [
            SearchResult(file=result["file"], line=result["line"], snippet=result["snippet"])
            for result in fuzzy_results
        ]

    def get_indexed_count(self) -> int:
        """Return the number of indexed files"""
        return len(self._file_cache)

    # ========================================
    # Private Implementation Methods
    # ========================================

    def _preindex(self) -> None:
        """Pre-index all Dart files in the current directory"""
        for path in Path(".").rglob("*.dart"):
            try:
                # Skip common build and cache directories
                if any(
                    part in path.parts for part in ["build", ".dart_tool", ".pub-cache", "packages"]
                ):
                    continue

                text = path.read_text(encoding="utf-8")
                self._indexer.add_file(str(path), text)
            except Exception as e:
                logger.warning(f"Failed to pre-index {path}: {e}")
                continue

    def _extract_all_symbols(self, content: str, file_path: str) -> List[SymbolDefinition]:
        """Extract all symbols and convert to SymbolDefinition format"""
        symbols = []

        # Extract different types of symbols
        symbols.extend(self._extract_dart_classes(content, file_path))
        symbols.extend(self._extract_dart_enums(content, file_path))
        symbols.extend(self._extract_dart_mixins(content, file_path))
        symbols.extend(self._extract_dart_extensions(content, file_path))
        symbols.extend(self._extract_dart_functions(content, file_path))
        symbols.extend(self._extract_dart_variables(content, file_path))
        symbols.extend(self._extract_dart_typedefs(content, file_path))

        return symbols

    def _extract_dart_classes(self, content: str, file_path: str) -> List[SymbolDefinition]:
        """Extract class definitions including Flutter widgets"""
        symbols = []

        # Class pattern: captures abstract, class name, extends, with, implements
        class_pattern = (
            r"^\s*(abstract\s+)?class\s+(\w+)(?:\s*<[^>]*>)?(?:\s+extends\s+(\w+(?:<[^>]*>)?))?"
            r"(?:\s+with\s+([\w\s,<>]+))?(?:\s+implements\s+([\w\s,<>]+))?\s*\{"
        )

        for match in re.finditer(class_pattern, content, re.MULTILINE):
            is_abstract = match.group(1) is not None
            class_name = match.group(2)
            extends_class = match.group(3)
            with_mixins = match.group(4)
            implements_interfaces = match.group(5)

            # Find the actual position of the "class" keyword within the match
            match_text = match.group(0)
            class_keyword_pos = match.start() + match_text.find("class")
            line_no = content[:class_keyword_pos].count("\n") + 1

            # Determine if it's a Flutter widget
            is_widget = self._is_flutter_widget(class_name, extends_class, content, match.start())
            is_state = self._is_flutter_state(class_name, extends_class, content, match.start())

            # Build signature
            signature_parts = []
            if is_abstract:
                signature_parts.append("abstract")
            signature_parts.append("class")
            signature_parts.append(class_name)

            if extends_class:
                signature_parts.extend(["extends", extends_class])
            if with_mixins:
                signature_parts.extend(["with", with_mixins.strip()])
            if implements_interfaces:
                signature_parts.extend(["implements", implements_interfaces.strip()])

            signature = " ".join(signature_parts)

            # Determine symbol type
            if is_widget:
                symbol_type = "widget"
            elif is_state:
                symbol_type = "state"
            elif is_abstract:
                symbol_type = "abstract_class"
            else:
                symbol_type = "class"

            # Extract documentation
            doc = self._extract_documentation(content, line_no)

            symbol = SymbolDefinition(
                symbol=class_name,
                file_path=file_path,
                line=line_no,
                column=match_text.find(class_name),
                symbol_type=symbol_type,
                signature=signature,
                docstring=doc,
                scope=None,
            )
            symbols.append(symbol)

            # Extract class members
            symbols.extend(
                self._extract_class_members(content, class_name, match.start(), file_path)
            )

        return symbols

    def _extract_class_members(
        self, content: str, class_name: str, class_start: int, file_path: str
    ) -> List[SymbolDefinition]:
        """Extract methods and properties from a class"""
        symbols = []

        # Find the class body
        class_end = self._find_matching_brace(content, class_start)
        if class_end == -1:
            return symbols

        class_body = content[class_start:class_end]

        # Extract methods
        method_pattern = r"^\s*(static\s+)?(override\s+)?(async\s+)?(\w+)\s*\(([^)]*)\)\s*(?:async\s*)?\s*(?:=>|\{)"
        for match in re.finditer(method_pattern, class_body, re.MULTILINE):
            is_static = match.group(1) is not None
            is_override = match.group(2) is not None
            is_async = match.group(3) is not None or "async" in (match.group(0) or "")
            method_name = match.group(4)
            parameters = match.group(5) or ""

            # Skip if it looks like a constructor (same name as class)
            if method_name == class_name:
                continue

            line_no = content[: class_start + match.start()].count("\n") + 1

            # Build signature
            signature_parts = []
            if is_static:
                signature_parts.append("static")
            if is_override:
                signature_parts.append("override")
            if is_async:
                signature_parts.append("async")

            signature_parts.append(f"{method_name}({parameters})")
            signature = " ".join(signature_parts)

            # Determine symbol type
            if method_name == "build" and not is_static:
                symbol_type = "build_method"
            elif method_name.startswith("init") or method_name == "dispose":
                symbol_type = "lifecycle_method"
            else:
                symbol_type = "method"

            doc = self._extract_documentation(content, line_no)

            symbol = SymbolDefinition(
                symbol=f"{class_name}.{method_name}",
                file_path=file_path,
                line=line_no,
                column=match.group(0).find(method_name),
                symbol_type=symbol_type,
                signature=signature,
                docstring=doc,
                scope=class_name,
            )
            symbols.append(symbol)

        # Extract properties/fields
        property_pattern = (
            r"^\s*(static\s+)?(final\s+|const\s+)?(\w+(?:<[^>]*>)?)\s+(\w+)\s*(?:=|;)"
        )
        for match in re.finditer(property_pattern, class_body, re.MULTILINE):
            is_static = match.group(1) is not None
            modifier = match.group(2)
            prop_type = match.group(3)
            prop_name = match.group(4)

            line_no = content[: class_start + match.start()].count("\n") + 1

            # Build signature
            signature_parts = []
            if is_static:
                signature_parts.append("static")
            if modifier:
                signature_parts.append(modifier.strip())
            signature_parts.extend([prop_type, prop_name])
            signature = " ".join(signature_parts)

            doc = self._extract_documentation(content, line_no)

            symbol = SymbolDefinition(
                symbol=f"{class_name}.{prop_name}",
                file_path=file_path,
                line=line_no,
                column=match.group(0).find(prop_name),
                symbol_type="property",
                signature=signature,
                docstring=doc,
                scope=class_name,
            )
            symbols.append(symbol)

        return symbols

    def _extract_dart_enums(self, content: str, file_path: str) -> List[SymbolDefinition]:
        """Extract enum definitions"""
        symbols = []
        enum_pattern = r"^\s*enum\s+(\w+)\s*\{"

        for match in re.finditer(enum_pattern, content, re.MULTILINE):
            enum_name = match.group(1)
            line_no = content[: match.start()].count("\n") + 1
            doc = self._extract_documentation(content, line_no)

            symbol = SymbolDefinition(
                symbol=enum_name,
                file_path=file_path,
                line=line_no,
                column=match.group(0).find(enum_name),
                symbol_type="enum",
                signature=f"enum {enum_name}",
                docstring=doc,
                scope=None,
            )
            symbols.append(symbol)

        return symbols

    def _extract_dart_mixins(self, content: str, file_path: str) -> List[SymbolDefinition]:
        """Extract mixin definitions"""
        symbols = []
        mixin_pattern = r"^\s*mixin\s+(\w+)(?:\s+on\s+([\w\s,<>]+))?\s*\{"

        for match in re.finditer(mixin_pattern, content, re.MULTILINE):
            mixin_name = match.group(1)
            on_types = match.group(2)
            line_no = content[: match.start()].count("\n") + 1
            doc = self._extract_documentation(content, line_no)

            signature = f"mixin {mixin_name}"
            if on_types:
                signature += f" on {on_types.strip()}"

            symbol = SymbolDefinition(
                symbol=mixin_name,
                file_path=file_path,
                line=line_no,
                column=match.group(0).find(mixin_name),
                symbol_type="mixin",
                signature=signature,
                docstring=doc,
                scope=None,
            )
            symbols.append(symbol)

        return symbols

    def _extract_dart_extensions(self, content: str, file_path: str) -> List[SymbolDefinition]:
        """Extract extension definitions"""
        symbols = []
        extension_pattern = r"^\s*extension\s+(\w+)?\s*on\s+(\w+(?:<[^>]*>)?)\s*\{"

        for match in re.finditer(extension_pattern, content, re.MULTILINE):
            extension_name = match.group(1) or f"ExtensionOn{match.group(2)}"
            on_type = match.group(2)
            line_no = content[: match.start()].count("\n") + 1
            doc = self._extract_documentation(content, line_no)

            signature = f"extension {extension_name} on {on_type}"

            symbol = SymbolDefinition(
                symbol=extension_name,
                file_path=file_path,
                line=line_no,
                column=match.group(0).find("extension"),
                symbol_type="extension",
                signature=signature,
                docstring=doc,
                scope=None,
            )
            symbols.append(symbol)

        return symbols

    def _extract_dart_functions(self, content: str, file_path: str) -> List[SymbolDefinition]:
        """Extract top-level function definitions"""
        symbols = []

        # Function pattern: captures async, return type, name, parameters
        function_pattern = r"^\s*(async\s+)?(?:(\w+(?:<[^>]*>)?)\s+)?(\w+)\s*\(([^)]*)\)\s*(?:async\s*)?\s*(?:=>|\{)"

        for match in re.finditer(function_pattern, content, re.MULTILINE):
            is_async = match.group(1) is not None or "async" in (match.group(0) or "")
            return_type = match.group(2)
            function_name = match.group(3)
            parameters = match.group(4) or ""

            # Skip if this looks like a class method (inside a class)
            if self._is_inside_class(content, match.start()):
                continue

            # Skip common keywords that might match
            if function_name in [
                "class",
                "enum",
                "mixin",
                "extension",
                "import",
                "export",
                "library",
                "part",
            ]:
                continue

            line_no = content[: match.start()].count("\n") + 1
            doc = self._extract_documentation(content, line_no)

            # Build signature
            signature_parts = []
            if is_async:
                signature_parts.append("async")
            if return_type:
                signature_parts.append(return_type)
            signature_parts.append(f"{function_name}({parameters})")
            signature = " ".join(signature_parts)

            # Determine symbol type
            if function_name == "main":
                symbol_type = "main_function"
            elif function_name.startswith("_"):
                symbol_type = "private_function"
            else:
                symbol_type = "function"

            symbol = SymbolDefinition(
                symbol=function_name,
                file_path=file_path,
                line=line_no,
                column=match.group(0).find(function_name),
                symbol_type=symbol_type,
                signature=signature,
                docstring=doc,
                scope=None,
            )
            symbols.append(symbol)

        return symbols

    def _extract_dart_variables(self, content: str, file_path: str) -> List[SymbolDefinition]:
        """Extract top-level variables and constants"""
        symbols = []

        # Variable pattern: captures const/final, type, name
        var_pattern = r"^\s*(const\s+|final\s+|var\s+)(?:(\w+(?:<[^>]*>)?)\s+)?(\w+)\s*="

        for match in re.finditer(var_pattern, content, re.MULTILINE):
            modifier = match.group(1).strip()
            var_type = match.group(2)
            var_name = match.group(3)

            # Skip if this is inside a class or function
            if self._is_inside_class(content, match.start()) or self._is_inside_function(
                content, match.start()
            ):
                continue

            line_no = content[: match.start()].count("\n") + 1
            doc = self._extract_documentation(content, line_no)

            # Build signature
            signature_parts = [modifier]
            if var_type:
                signature_parts.append(var_type)
            signature_parts.append(var_name)
            signature = " ".join(signature_parts)

            # Determine symbol type
            if modifier == "const":
                symbol_type = "constant"
            elif var_name.isupper():
                symbol_type = "constant"
            else:
                symbol_type = "variable"

            symbol = SymbolDefinition(
                symbol=var_name,
                file_path=file_path,
                line=line_no,
                column=match.group(0).find(var_name),
                symbol_type=symbol_type,
                signature=signature,
                docstring=doc,
                scope=None,
            )
            symbols.append(symbol)

        return symbols

    def _extract_dart_typedefs(self, content: str, file_path: str) -> List[SymbolDefinition]:
        """Extract typedef definitions"""
        symbols = []
        typedef_pattern = r"^\s*typedef\s+(\w+)\s*=\s*([^;]+);"

        for match in re.finditer(typedef_pattern, content, re.MULTILINE):
            typedef_name = match.group(1)
            typedef_type = match.group(2).strip()
            line_no = content[: match.start()].count("\n") + 1
            doc = self._extract_documentation(content, line_no)

            signature = f"typedef {typedef_name} = {typedef_type}"

            symbol = SymbolDefinition(
                symbol=typedef_name,
                file_path=file_path,
                line=line_no,
                column=match.group(0).find(typedef_name),
                symbol_type="typedef",
                signature=signature,
                docstring=doc,
                scope=None,
            )
            symbols.append(symbol)

        return symbols

    def _extract_flutter_widgets(self, content: str) -> List[SymbolDefinition]:
        """Extract Flutter widget definitions specifically"""
        widgets = []

        # Look for classes that extend common Flutter widgets
        widget_bases = {
            "StatelessWidget",
            "StatefulWidget",
            "InheritedWidget",
            "Widget",
            "RenderObjectWidget",
            "PreferredSizeWidget",
            "ImplicitlyAnimatedWidget",
        }

        class_pattern = r"^\s*class\s+(\w+)(?:\s*<[^>]*>)?\s+extends\s+(\w+(?:<[^>]*>)?)"

        for match in re.finditer(class_pattern, content, re.MULTILINE):
            class_name = match.group(1)
            extends_class = match.group(2)

            # Check if it extends a known widget class
            base_class = extends_class.split("<")[0]  # Remove generics
            if base_class in widget_bases or "Widget" in extends_class:
                line_no = content[: match.start()].count("\n") + 1
                doc = self._extract_documentation(content, line_no)

                widget = SymbolDefinition(
                    symbol=class_name,
                    file_path="temp_file.dart",  # Will be overridden by caller
                    line=line_no,
                    column=match.group(0).find(class_name),
                    symbol_type="widget",
                    signature=f"class {class_name} extends {extends_class}",
                    docstring=doc,
                    scope=None,
                )
                widgets.append(widget)

        return widgets

    def _resolve_dart_packages(self, file_path: str) -> List[str]:
        """Resolve package dependencies from imports and pubspec.yaml"""
        packages = set()

        try:
            # Read the file content
            content = Path(file_path).read_text(encoding="utf-8")

            # Extract package imports
            import_pattern = r"import\s+['\"]package:([^/]+)/"
            for match in re.finditer(import_pattern, content):
                packages.add(match.group(1))

            # Also try to read pubspec.yaml if available
            project_root = Path(file_path).parent
            while project_root != project_root.parent:
                pubspec_path = project_root / "pubspec.yaml"
                if pubspec_path.exists():
                    pubspec_content = pubspec_path.read_text(encoding="utf-8")
                    # Simple extraction of dependencies
                    dep_pattern = r"^\s*(\w+):\s*"
                    for match in re.finditer(dep_pattern, pubspec_content, re.MULTILINE):
                        dep_name = match.group(1)
                        if dep_name not in [
                            "dependencies",
                            "dev_dependencies",
                            "flutter",
                        ]:
                            packages.add(dep_name)
                    break
                project_root = project_root.parent

        except Exception as e:
            logger.warning(f"Failed to resolve packages for {file_path}: {e}")

        return list(packages)

    def _extract_imports_list(self, content: str) -> List[str]:
        """Extract import paths from content"""
        imports = []

        # Import pattern: import 'package:name/path.dart' or import 'relative/path.dart'
        import_pattern = r"import\s+['\"]([^'\"]+)['\"]"

        for match in re.finditer(import_pattern, content):
            import_path = match.group(1)
            imports.append(import_path)

        return imports

    def _find_symbol_definition(self, symbol: str) -> Optional[SymbolDefinition]:
        """Find the definition of a symbol across all files"""
        # Search in all Dart files
        for path in Path(".").rglob("*.dart"):
            try:
                # Skip build and cache directories
                if any(
                    part in path.parts for part in ["build", ".dart_tool", ".pub-cache", "packages"]
                ):
                    continue

                content = path.read_text(encoding="utf-8")
                symbols = self._extract_all_symbols(content, str(path))

                for sym_def in symbols:
                    if sym_def.symbol == symbol or sym_def.symbol.endswith(f".{symbol}"):
                        return sym_def
            except Exception:
                continue

        return None

    def _find_symbol_references(self, symbol: str) -> List[SymbolReference]:
        """Find all references to a symbol"""
        references = []
        seen = set()

        # Search in all Dart files
        for path in Path(".").rglob("*.dart"):
            try:
                # Skip build and cache directories
                if any(
                    part in path.parts for part in ["build", ".dart_tool", ".pub-cache", "packages"]
                ):
                    continue

                content = path.read_text(encoding="utf-8")

                # Simple text search for references
                lines = content.splitlines()
                for i, line in enumerate(lines):
                    # Look for whole word matches
                    pattern = r"\b" + re.escape(symbol) + r"\b"
                    for match in re.finditer(pattern, line):
                        line_no = i + 1
                        column = match.start()
                        key = (str(path), line_no, column)
                        if key not in seen:
                            ref = SymbolReference(
                                symbol=symbol,
                                file_path=str(path),
                                line=line_no,
                                column=column,
                                context=line.strip(),
                            )
                            references.append(ref)
                            seen.add(key)
            except Exception:
                continue

        return references

    def _perform_search(self, query: str, limit: int) -> List[SearchResultInterface]:
        """Perform a search and return results in the interface format"""
        # Use fuzzy indexer for basic search
        fuzzy_results = self._indexer.search(query, limit=limit)

        # Convert to interface format
        results = []
        for result in fuzzy_results:
            search_result = SearchResultInterface(
                file_path=result["file"],
                line=result["line"],
                column=0,
                snippet=result["snippet"],
                match_type="fuzzy",
                score=1.0,
                context=None,
            )
            results.append(search_result)

        return results

    def _validate_dart_syntax(self, content: str) -> bool:
        """Basic Dart syntax validation using regex patterns"""
        try:
            # Check for balanced braces
            open_braces = content.count("{")
            close_braces = content.count("}")
            if open_braces != close_braces:
                return False

            # Check for balanced parentheses
            open_parens = content.count("(")
            close_parens = content.count(")")
            if open_parens != close_parens:
                return False

            # Check for balanced square brackets
            open_brackets = content.count("[")
            close_brackets = content.count("]")
            if open_brackets != close_brackets:
                return False

            # Check for unclosed string literals (basic check)
            # Count quotes that are not escaped
            single_quotes = len(re.findall(r"(?<!\\)'", content))
            double_quotes = len(re.findall(r'(?<!\\)"', content))

            if single_quotes % 2 != 0 or double_quotes % 2 != 0:
                return False

            return True

        except Exception:
            return False

    def _get_dart_completions(self, file_path: str, line: int, column: int) -> List[str]:
        """Get basic code completions"""
        completions = []

        try:
            # Basic Dart keywords
            dart_keywords = [
                "abstract",
                "as",
                "assert",
                "async",
                "await",
                "break",
                "case",
                "catch",
                "class",
                "const",
                "continue",
                "default",
                "do",
                "else",
                "enum",
                "extends",
                "false",
                "final",
                "finally",
                "for",
                "if",
                "implements",
                "import",
                "in",
                "is",
                "library",
                "new",
                "null",
                "return",
                "super",
                "switch",
                "this",
                "throw",
                "true",
                "try",
                "var",
                "void",
                "while",
                "with",
                "yield",
            ]

            # Flutter-specific completions
            flutter_widgets = [
                "Widget",
                "StatelessWidget",
                "StatefulWidget",
                "Container",
                "Column",
                "Row",
                "Text",
                "Button",
                "AppBar",
                "Scaffold",
                "MaterialApp",
                "CupertinoApp",
            ]

            # Get symbols from current file and project
            if file_path in self._symbol_cache:
                for symbol in self._symbol_cache[file_path]:
                    completions.append(symbol.symbol)

            completions.extend(dart_keywords)
            completions.extend(flutter_widgets)

        except Exception:
            pass

        return list(set(completions))  # Remove duplicates

    def _resolve_symbol_type(self, symbol: str, context: Dict[str, Any]) -> Optional[str]:
        """Resolve the type of a symbol"""
        # Look for the symbol definition
        definition = self._find_symbol_definition(symbol)
        if definition and definition.signature:
            # Try to extract type from signature
            if definition.symbol_type in ["variable", "property"]:
                # For variables, try to extract type from signature
                parts = definition.signature.split()
                for i, part in enumerate(parts):
                    if part == symbol and i > 0:
                        return parts[i - 1]
            elif definition.symbol_type in ["function", "method"]:
                # For functions, return type might be in signature
                if "async" in definition.signature:
                    return "Future"
                # Could do more sophisticated parsing here

        return None

    def _get_dart_call_hierarchy(
        self, symbol: str, context: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        """Get call hierarchy for a symbol"""
        hierarchy = {"calls": [], "called_by": []}

        try:
            # Find all references to this symbol
            references = self._find_symbol_references(symbol)

            # Categorize references as calls or called_by based on context
            for ref in references:
                # This is a simplified implementation
                # In a real implementation, you'd parse the context to determine
                # if this is a call site or a definition
                hierarchy["called_by"].append(f"{ref.file_path}:{ref.line}")

        except Exception:
            pass

        return hierarchy

    # ========================================
    # Helper Methods (Common with Legacy)
    # ========================================

    def _is_flutter_widget(
        self,
        class_name: str,
        extends_class: Optional[str],
        content: str,
        class_start: int,
    ) -> bool:
        """Determine if a class is a Flutter widget"""
        if not extends_class:
            return False

        # Common Flutter widget base classes
        widget_bases = {
            "StatelessWidget",
            "StatefulWidget",
            "InheritedWidget",
            "Widget",
            "RenderObjectWidget",
            "PreferredSizeWidget",
            "ImplicitlyAnimatedWidget",
        }

        return extends_class in widget_bases or "Widget" in extends_class

    def _is_flutter_state(
        self,
        class_name: str,
        extends_class: Optional[str],
        content: str,
        class_start: int,
    ) -> bool:
        """Determine if a class is a Flutter State class"""
        if not extends_class:
            return False

        return extends_class.startswith("State<") or extends_class == "State"

    def _is_inside_class(self, content: str, position: int) -> bool:
        """Check if position is inside a class definition"""
        # Count open and close braces before this position
        # and look for 'class' keyword
        before_content = content[:position]

        # Find the last class keyword before this position
        class_matches = list(re.finditer(r"\bclass\s+\w+", before_content))
        if not class_matches:
            return False

        last_class = class_matches[-1]

        # Count braces from the class start to current position
        segment = content[last_class.end() : position]
        open_braces = segment.count("{")
        close_braces = segment.count("}")

        return open_braces > close_braces

    def _is_inside_function(self, content: str, position: int) -> bool:
        """Check if position is inside a function definition"""
        # Similar logic to _is_inside_class but for functions
        before_content = content[:position]

        # Look for function patterns before this position
        func_pattern = r"\w+\s*\([^)]*\)\s*(?:async\s*)?\s*\{"
        func_matches = list(re.finditer(func_pattern, before_content))
        if not func_matches:
            return False

        last_func = func_matches[-1]

        # Count braces from the function start to current position
        segment = content[last_func.end() - 1 : position]  # Include the opening brace
        open_braces = segment.count("{")
        close_braces = segment.count("}")

        return open_braces > close_braces

    def _find_matching_brace(self, content: str, start: int) -> int:
        """Find the position of the matching closing brace"""
        open_count = 0

        for i, char in enumerate(content[start:], start):
            if char == "{":
                open_count += 1
            elif char == "}":
                open_count -= 1
                if open_count == 0:
                    return i

        return -1

    def _extract_documentation(self, content: str, line: int) -> Optional[str]:
        """Extract documentation comment above a symbol"""
        lines = content.splitlines()
        if line <= 1 or line > len(lines):
            return None

        # Look for documentation comments above the symbol
        doc_lines = []
        for i in range(line - 2, max(0, line - 20), -1):
            if i >= len(lines):
                continue

            line_content = lines[i].strip()

            # Dart doc comments start with /// or /** */
            if line_content.startswith("///"):
                doc_lines.insert(0, line_content[3:].strip())
            elif line_content.startswith("*") and doc_lines:
                doc_lines.insert(0, line_content[1:].strip())
            elif line_content.startswith("/**"):
                doc_lines.insert(0, line_content[3:].strip())
            elif line_content.endswith("*/"):
                doc_lines.insert(0, line_content[:-2].strip())
                break
            elif not line_content or line_content.startswith("//"):
                continue
            else:
                break

        return "\n".join(doc_lines) if doc_lines else None

    # ========================================
    # Legacy Format Support Methods
    # ========================================

    def _extract_symbols_legacy(
        self,
        content: str,
        symbols: List[Dict],
        imports: List[Dict],
        exports: List[Dict],
        file_id: Optional[int] = None,
    ) -> None:
        """Extract symbols in legacy format for backward compatibility"""
        # Extract imports and exports
        imports.extend(self._extract_imports_legacy(content))
        exports.extend(self._extract_exports_legacy(content))

        # Convert new format symbols to legacy format
        new_symbols = self._extract_all_symbols(content, str(self._current_file))

        for sym in new_symbols:
            legacy_symbol = {
                "symbol": sym.symbol,
                "kind": sym.symbol_type,
                "signature": sym.signature or "",
                "line": sym.line,
                "span": (sym.line, sym.line + 5),  # Approximate span
            }

            # Add any additional fields based on symbol type
            if sym.scope:
                legacy_symbol["class"] = sym.scope

            symbols.append(legacy_symbol)

            # Store in SQLite if available
            if self._sqlite_store and file_id:
                symbol_id = self._sqlite_store.store_symbol(
                    file_id,
                    sym.symbol,
                    sym.symbol_type,
                    sym.line,
                    legacy_symbol["span"][1],
                    signature=sym.signature,
                )
                self._indexer.add_symbol(
                    sym.symbol,
                    str(self._current_file),
                    sym.line,
                    {"symbol_id": symbol_id, "file_id": file_id},
                )

    def _extract_imports_legacy(self, content: str) -> List[Dict[str, Any]]:
        """Extract import statements in legacy format"""
        imports = []

        # Import pattern: import 'package:name/path.dart' as alias show/hide symbols;
        import_pattern = (
            r"import\s+['\"]([^'\"]+)['\"](?:\s+as\s+(\w+))?(?:\s+(show|hide)\s+([^;]+))?\s*;"
        )

        for match in re.finditer(import_pattern, content, re.MULTILINE):
            import_path = match.group(1)
            alias = match.group(2)
            show_hide = match.group(3)
            symbols = match.group(4)

            line_no = content[: match.start()].count("\n") + 1

            import_info = {"path": import_path, "line": line_no, "type": "import"}

            if alias:
                import_info["alias"] = alias
            if show_hide and symbols:
                symbol_list = [s.strip() for s in symbols.split(",")]
                import_info[show_hide] = symbol_list

            imports.append(import_info)

        return imports

    def _extract_exports_legacy(self, content: str) -> List[Dict[str, Any]]:
        """Extract export statements in legacy format"""
        exports = []

        # Export pattern
        export_pattern = r"export\s+['\"]([^'\"]+)['\"](?:\s+(show|hide)\s+([^;]+))?\s*;"

        for match in re.finditer(export_pattern, content, re.MULTILINE):
            export_path = match.group(1)
            show_hide = match.group(2)
            symbols = match.group(3)

            line_no = content[: match.start()].count("\n") + 1

            export_info = {"path": export_path, "line": line_no, "type": "export"}

            if show_hide and symbols:
                symbol_list = [s.strip() for s in symbols.split(",")]
                export_info[show_hide] = symbol_list

            exports.append(export_info)

        return exports
