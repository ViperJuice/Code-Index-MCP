from __future__ import annotations

from pathlib import Path
from typing import Optional, Dict, List, Set, Tuple, Any
import re
import logging

from ...plugin_base import (
    IPlugin,
    IndexShard,
    SymbolDef,
    Reference,
    SearchResult,
    SearchOpts,
)
from ...utils.fuzzy_indexer import FuzzyIndexer
from ...storage.sqlite_store import SQLiteStore

logger = logging.getLogger(__name__)


class Plugin(IPlugin):
    """Dart/Flutter plugin for code intelligence.
    
    Supports:
    - File extensions: .dart
    - Symbol extraction: classes, functions, methods, variables, enums, mixins, extensions
    - Dart-specific features: widgets, state classes, async/await, futures, streams, annotations
    - Flutter-specific features: widget hierarchy, state management, build methods
    - Package imports and pub.dev dependencies
    
    Note: Uses regex-based parsing since tree-sitter-dart is not available in current
    tree-sitter-languages package. Can be easily upgraded to tree-sitter when available.
    """
    
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
        self._symbol_cache: Dict[str, List[SymbolDef]] = {}
        
        # Current file context
        self._current_file: Optional[Path] = None
        
        # Create or get repository if SQLite is enabled
        if self._sqlite_store:
            self._repository_id = self._sqlite_store.create_repository(
                str(Path.cwd()), 
                Path.cwd().name,
                {"language": "dart"}
            )
        
        # Pre-index existing files
        self._preindex()

    def _preindex(self) -> None:
        """Pre-index all Dart files in the current directory."""
        for path in Path(".").rglob("*.dart"):
            try:
                # Skip common build and cache directories
                if any(part in path.parts for part in ["build", ".dart_tool", ".pub-cache", "packages"]):
                    continue
                
                text = path.read_text(encoding="utf-8")
                self._indexer.add_file(str(path), text)
            except Exception as e:
                logger.warning(f"Failed to pre-index {path}: {e}")
                continue

    def supports(self, path: str | Path) -> bool:
        """Check if this plugin supports the given file."""
        return Path(path).suffix == ".dart"

    def indexFile(self, path: str | Path, content: str) -> IndexShard:
        """Parse and index a Dart file."""
        if isinstance(path, str):
            path = Path(path)
        
        self._current_file = path
        self._indexer.add_file(str(path), content)
        
        # Store file in SQLite if available
        file_id = None
        if self._sqlite_store and self._repository_id:
            import hashlib
            file_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
            file_id = self._sqlite_store.store_file(
                self._repository_id,
                str(path),
                str(path.relative_to(Path.cwd())),
                language="dart",
                size=len(content),
                hash=file_hash
            )
        
        # Extract symbols using regex-based parsing
        symbols: List[Dict[str, Any]] = []
        imports: List[Dict[str, Any]] = []
        exports: List[Dict[str, Any]] = []
        
        self._extract_symbols(content, symbols, imports, exports, file_id)
        
        # Cache symbols for quick lookup
        cache_key = str(path)
        self._symbol_cache[cache_key] = [
            self._symbol_to_def(s, str(path), content) 
            for s in symbols
        ]
        
        return {
            'file': str(path),
            'symbols': symbols,
            'language': self.lang,
            'imports': imports,
            'exports': exports
        }

    def _extract_symbols(self, content: str, symbols: List[Dict], 
                        imports: List[Dict], exports: List[Dict],
                        file_id: Optional[int] = None) -> None:
        """Extract symbols from Dart code using regex patterns."""
        lines = content.splitlines()
        
        # Extract imports and exports
        imports.extend(self._extract_imports(content))
        exports.extend(self._extract_exports(content))
        
        # Extract classes (including widgets)
        self._extract_classes(content, symbols, file_id)
        
        # Extract enums
        self._extract_enums(content, symbols, file_id)
        
        # Extract mixins
        self._extract_mixins(content, symbols, file_id)
        
        # Extract extensions
        self._extract_extensions(content, symbols, file_id)
        
        # Extract top-level functions
        self._extract_functions(content, symbols, file_id)
        
        # Extract top-level variables and constants
        self._extract_variables(content, symbols, file_id)
        
        # Extract typedefs
        self._extract_typedefs(content, symbols, file_id)

    def _extract_classes(self, content: str, symbols: List[Dict], file_id: Optional[int]) -> None:
        """Extract class definitions including Flutter widgets."""
        # Class pattern: captures abstract, class name, extends, with, implements
        class_pattern = r'^\s*(abstract\s+)?class\s+(\w+)(?:\s*<[^>]*>)?(?:\s+extends\s+(\w+(?:<[^>]*>)?))?' \
                       r'(?:\s+with\s+([\w\s,<>]+))?(?:\s+implements\s+([\w\s,<>]+))?\s*\{'
        
        for match in re.finditer(class_pattern, content, re.MULTILINE):
            is_abstract = match.group(1) is not None
            class_name = match.group(2)
            extends_class = match.group(3)
            with_mixins = match.group(4)
            implements_interfaces = match.group(5)
            
            # Find the actual position of the "class" keyword within the match
            match_text = match.group(0)
            class_keyword_pos = match.start() + match_text.find('class')
            line_no = content[:class_keyword_pos].count('\n') + 1
            
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
            
            # Determine kind
            if is_widget:
                kind = "widget"
            elif is_state:
                kind = "state"
            elif is_abstract:
                kind = "abstract_class"
            else:
                kind = "class"
            
            symbol_info = {
                'symbol': class_name,
                'kind': kind,
                'signature': signature,
                'line': line_no,
                'span': self._find_closing_brace(content, match.end() - 1),
                'extends': extends_class,
                'mixins': with_mixins.strip() if with_mixins else None,
                'interfaces': implements_interfaces.strip() if implements_interfaces else None
            }
            symbols.append(symbol_info)
            
            # Store in SQLite if available
            if self._sqlite_store and file_id:
                symbol_id = self._sqlite_store.store_symbol(
                    file_id,
                    class_name,
                    kind,
                    line_no,
                    symbol_info['span'][1],
                    signature=signature
                )
                self._indexer.add_symbol(
                    class_name, 
                    str(self._current_file), 
                    line_no,
                    {"symbol_id": symbol_id, "file_id": file_id}
                )
            
            # Extract class members (methods, properties)
            self._extract_class_members(content, class_name, match.start(), symbols, file_id)

    def _extract_class_members(self, content: str, class_name: str, class_start: int, 
                              symbols: List[Dict], file_id: Optional[int]) -> None:
        """Extract methods and properties from a class."""
        # Find the class body
        class_end = self._find_matching_brace(content, class_start)
        if class_end == -1:
            return
        
        class_body = content[class_start:class_end]
        
        # Extract methods
        method_pattern = r'^\s*(static\s+)?(override\s+)?(async\s+)?(\w+)\s*\(([^)]*)\)\s*(?:async\s*)?\s*(?:=>|\{)'
        for match in re.finditer(method_pattern, class_body, re.MULTILINE):
            is_static = match.group(1) is not None
            is_override = match.group(2) is not None
            is_async = match.group(3) is not None or 'async' in (match.group(0) or '')
            method_name = match.group(4)
            parameters = match.group(5) or ''
            
            # Skip if it looks like a constructor (same name as class)
            if method_name == class_name:
                continue
            
            line_no = content[:class_start + match.start()].count('\n') + 1
            
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
            
            # Determine kind
            if method_name == 'build' and not is_static:
                kind = 'build_method'
            elif method_name.startswith('init') or method_name == 'dispose':
                kind = 'lifecycle_method'
            else:
                kind = 'method'
            
            symbol_info = {
                'symbol': f"{class_name}.{method_name}",
                'kind': kind,
                'signature': signature,
                'line': line_no,
                'class': class_name,
                'static': is_static,
                'async': is_async
            }
            symbols.append(symbol_info)
            
            # Store in SQLite if available
            if self._sqlite_store and file_id:
                symbol_id = self._sqlite_store.store_symbol(
                    file_id,
                    f"{class_name}.{method_name}",
                    kind,
                    line_no,
                    line_no + 5,  # Approximate end line
                    signature=signature
                )
                self._indexer.add_symbol(
                    f"{class_name}.{method_name}", 
                    str(self._current_file), 
                    line_no,
                    {"symbol_id": symbol_id, "file_id": file_id}
                )
        
        # Extract properties/fields
        property_pattern = r'^\s*(static\s+)?(final\s+|const\s+)?(\w+(?:<[^>]*>)?)\s+(\w+)\s*(?:=|;)'
        for match in re.finditer(property_pattern, class_body, re.MULTILINE):
            is_static = match.group(1) is not None
            modifier = match.group(2)
            prop_type = match.group(3)
            prop_name = match.group(4)
            
            line_no = content[:class_start + match.start()].count('\n') + 1
            
            # Build signature
            signature_parts = []
            if is_static:
                signature_parts.append("static")
            if modifier:
                signature_parts.append(modifier.strip())
            signature_parts.extend([prop_type, prop_name])
            signature = " ".join(signature_parts)
            
            symbol_info = {
                'symbol': f"{class_name}.{prop_name}",
                'kind': 'property',
                'signature': signature,
                'line': line_no,
                'class': class_name,
                'type': prop_type,
                'static': is_static
            }
            symbols.append(symbol_info)

    def _extract_enums(self, content: str, symbols: List[Dict], file_id: Optional[int]) -> None:
        """Extract enum definitions."""
        enum_pattern = r'^\s*enum\s+(\w+)\s*\{'
        
        for match in re.finditer(enum_pattern, content, re.MULTILINE):
            enum_name = match.group(1)
            line_no = content[:match.start()].count('\n') + 1
            
            symbol_info = {
                'symbol': enum_name,
                'kind': 'enum',
                'signature': f"enum {enum_name}",
                'line': line_no,
                'span': self._find_closing_brace(content, match.end() - 1)
            }
            symbols.append(symbol_info)
            
            # Store in SQLite if available
            if self._sqlite_store and file_id:
                symbol_id = self._sqlite_store.store_symbol(
                    file_id,
                    enum_name,
                    'enum',
                    line_no,
                    symbol_info['span'][1],
                    signature=symbol_info['signature']
                )
                self._indexer.add_symbol(
                    enum_name, 
                    str(self._current_file), 
                    line_no,
                    {"symbol_id": symbol_id, "file_id": file_id}
                )

    def _extract_mixins(self, content: str, symbols: List[Dict], file_id: Optional[int]) -> None:
        """Extract mixin definitions."""
        mixin_pattern = r'^\s*mixin\s+(\w+)(?:\s+on\s+([\w\s,<>]+))?\s*\{'
        
        for match in re.finditer(mixin_pattern, content, re.MULTILINE):
            mixin_name = match.group(1)
            on_types = match.group(2)
            line_no = content[:match.start()].count('\n') + 1
            
            signature = f"mixin {mixin_name}"
            if on_types:
                signature += f" on {on_types.strip()}"
            
            symbol_info = {
                'symbol': mixin_name,
                'kind': 'mixin',
                'signature': signature,
                'line': line_no,
                'span': self._find_closing_brace(content, match.end() - 1),
                'on_types': on_types.strip() if on_types else None
            }
            symbols.append(symbol_info)
            
            # Store in SQLite if available
            if self._sqlite_store and file_id:
                symbol_id = self._sqlite_store.store_symbol(
                    file_id,
                    mixin_name,
                    'mixin',
                    line_no,
                    symbol_info['span'][1],
                    signature=signature
                )
                self._indexer.add_symbol(
                    mixin_name, 
                    str(self._current_file), 
                    line_no,
                    {"symbol_id": symbol_id, "file_id": file_id}
                )

    def _extract_extensions(self, content: str, symbols: List[Dict], file_id: Optional[int]) -> None:
        """Extract extension definitions."""
        extension_pattern = r'^\s*extension\s+(\w+)?\s*on\s+(\w+(?:<[^>]*>)?)\s*\{'
        
        for match in re.finditer(extension_pattern, content, re.MULTILINE):
            extension_name = match.group(1) or f"ExtensionOn{match.group(2)}"
            on_type = match.group(2)
            line_no = content[:match.start()].count('\n') + 1
            
            signature = f"extension {extension_name} on {on_type}"
            
            symbol_info = {
                'symbol': extension_name,
                'kind': 'extension',
                'signature': signature,
                'line': line_no,
                'span': self._find_closing_brace(content, match.end() - 1),
                'on_type': on_type
            }
            symbols.append(symbol_info)
            
            # Store in SQLite if available
            if self._sqlite_store and file_id:
                symbol_id = self._sqlite_store.store_symbol(
                    file_id,
                    extension_name,
                    'extension',
                    line_no,
                    symbol_info['span'][1],
                    signature=signature
                )
                self._indexer.add_symbol(
                    extension_name, 
                    str(self._current_file), 
                    line_no,
                    {"symbol_id": symbol_id, "file_id": file_id}
                )

    def _extract_functions(self, content: str, symbols: List[Dict], file_id: Optional[int]) -> None:
        """Extract top-level function definitions."""
        # Function pattern: captures async, return type, name, parameters
        function_pattern = r'^\s*(async\s+)?(?:(\w+(?:<[^>]*>)?)\s+)?(\w+)\s*\(([^)]*)\)\s*(?:async\s*)?\s*(?:=>|\{)'
        
        for match in re.finditer(function_pattern, content, re.MULTILINE):
            is_async = match.group(1) is not None or 'async' in (match.group(0) or '')
            return_type = match.group(2)
            function_name = match.group(3)
            parameters = match.group(4) or ''
            
            # Skip if this looks like a class method (inside a class)
            if self._is_inside_class(content, match.start()):
                continue
            
            # Skip common keywords that might match
            if function_name in ['class', 'enum', 'mixin', 'extension', 'import', 'export', 'library', 'part']:
                continue
            
            line_no = content[:match.start()].count('\n') + 1
            
            # Build signature
            signature_parts = []
            if is_async:
                signature_parts.append("async")
            if return_type:
                signature_parts.append(return_type)
            signature_parts.append(f"{function_name}({parameters})")
            signature = " ".join(signature_parts)
            
            # Determine kind
            if function_name == 'main':
                kind = 'main_function'
            elif function_name.startswith('_'):
                kind = 'private_function'
            else:
                kind = 'function'
            
            symbol_info = {
                'symbol': function_name,
                'kind': kind,
                'signature': signature,
                'line': line_no,
                'async': is_async,
                'return_type': return_type
            }
            symbols.append(symbol_info)
            
            # Store in SQLite if available
            if self._sqlite_store and file_id:
                symbol_id = self._sqlite_store.store_symbol(
                    file_id,
                    function_name,
                    kind,
                    line_no,
                    line_no + 10,  # Approximate end line
                    signature=signature
                )
                self._indexer.add_symbol(
                    function_name, 
                    str(self._current_file), 
                    line_no,
                    {"symbol_id": symbol_id, "file_id": file_id}
                )

    def _extract_variables(self, content: str, symbols: List[Dict], file_id: Optional[int]) -> None:
        """Extract top-level variables and constants."""
        # Variable pattern: captures const/final, type, name
        var_pattern = r'^\s*(const\s+|final\s+|var\s+)(?:(\w+(?:<[^>]*>)?)\s+)?(\w+)\s*='
        
        for match in re.finditer(var_pattern, content, re.MULTILINE):
            modifier = match.group(1).strip()
            var_type = match.group(2)
            var_name = match.group(3)
            
            # Skip if this is inside a class or function
            if self._is_inside_class(content, match.start()) or self._is_inside_function(content, match.start()):
                continue
            
            line_no = content[:match.start()].count('\n') + 1
            
            # Build signature
            signature_parts = [modifier]
            if var_type:
                signature_parts.append(var_type)
            signature_parts.append(var_name)
            signature = " ".join(signature_parts)
            
            # Determine kind
            if modifier == 'const':
                kind = 'constant'
            elif var_name.isupper():
                kind = 'constant'
            else:
                kind = 'variable'
            
            symbol_info = {
                'symbol': var_name,
                'kind': kind,
                'signature': signature,
                'line': line_no,
                'type': var_type,
                'modifier': modifier
            }
            symbols.append(symbol_info)
            
            # Store in SQLite if available
            if self._sqlite_store and file_id:
                symbol_id = self._sqlite_store.store_symbol(
                    file_id,
                    var_name,
                    kind,
                    line_no,
                    line_no,
                    signature=signature
                )
                self._indexer.add_symbol(
                    var_name, 
                    str(self._current_file), 
                    line_no,
                    {"symbol_id": symbol_id, "file_id": file_id}
                )

    def _extract_typedefs(self, content: str, symbols: List[Dict], file_id: Optional[int]) -> None:
        """Extract typedef definitions."""
        typedef_pattern = r'^\s*typedef\s+(\w+)\s*=\s*([^;]+);'
        
        for match in re.finditer(typedef_pattern, content, re.MULTILINE):
            typedef_name = match.group(1)
            typedef_type = match.group(2).strip()
            line_no = content[:match.start()].count('\n') + 1
            
            signature = f"typedef {typedef_name} = {typedef_type}"
            
            symbol_info = {
                'symbol': typedef_name,
                'kind': 'typedef',
                'signature': signature,
                'line': line_no,
                'aliased_type': typedef_type
            }
            symbols.append(symbol_info)
            
            # Store in SQLite if available
            if self._sqlite_store and file_id:
                symbol_id = self._sqlite_store.store_symbol(
                    file_id,
                    typedef_name,
                    'typedef',
                    line_no,
                    line_no,
                    signature=signature
                )
                self._indexer.add_symbol(
                    typedef_name, 
                    str(self._current_file), 
                    line_no,
                    {"symbol_id": symbol_id, "file_id": file_id}
                )

    def _extract_imports(self, content: str) -> List[Dict[str, Any]]:
        """Extract import statements."""
        imports = []
        
        # Import pattern: import 'package:name/path.dart' as alias show/hide symbols;
        import_pattern = r"import\s+['\"]([^'\"]+)['\"](?:\s+as\s+(\w+))?(?:\s+(show|hide)\s+([^;]+))?\s*;"
        
        for match in re.finditer(import_pattern, content, re.MULTILINE):
            import_path = match.group(1)
            alias = match.group(2)
            show_hide = match.group(3)
            symbols = match.group(4)
            
            line_no = content[:match.start()].count('\n') + 1
            
            import_info = {
                'path': import_path,
                'line': line_no,
                'type': 'import'
            }
            
            if alias:
                import_info['alias'] = alias
            if show_hide and symbols:
                symbol_list = [s.strip() for s in symbols.split(',')]
                import_info[show_hide] = symbol_list
            
            imports.append(import_info)
        
        # Export pattern
        export_pattern = r"export\s+['\"]([^'\"]+)['\"](?:\s+(show|hide)\s+([^;]+))?\s*;"
        
        for match in re.finditer(export_pattern, content, re.MULTILINE):
            export_path = match.group(1)
            show_hide = match.group(2)
            symbols = match.group(3)
            
            line_no = content[:match.start()].count('\n') + 1
            
            import_info = {
                'path': export_path,
                'line': line_no,
                'type': 'export'
            }
            
            if show_hide and symbols:
                symbol_list = [s.strip() for s in symbols.split(',')]
                import_info[show_hide] = symbol_list
            
            imports.append(import_info)
        
        return imports

    def _extract_exports(self, content: str) -> List[Dict[str, Any]]:
        """Extract export statements (already handled in imports)."""
        return []  # Exports are handled in _extract_imports

    def _is_flutter_widget(self, class_name: str, extends_class: Optional[str], 
                          content: str, class_start: int) -> bool:
        """Determine if a class is a Flutter widget."""
        if not extends_class:
            return False
        
        # Common Flutter widget base classes
        widget_bases = {
            'StatelessWidget', 'StatefulWidget', 'InheritedWidget', 'Widget',
            'RenderObjectWidget', 'PreferredSizeWidget', 'ImplicitlyAnimatedWidget'
        }
        
        return extends_class in widget_bases or 'Widget' in extends_class

    def _is_flutter_state(self, class_name: str, extends_class: Optional[str], 
                         content: str, class_start: int) -> bool:
        """Determine if a class is a Flutter State class."""
        if not extends_class:
            return False
        
        return extends_class.startswith('State<') or extends_class == 'State'

    def _is_inside_class(self, content: str, position: int) -> bool:
        """Check if position is inside a class definition."""
        # Count open and close braces before this position
        # and look for 'class' keyword
        before_content = content[:position]
        
        # Find the last class keyword before this position
        class_matches = list(re.finditer(r'\bclass\s+\w+', before_content))
        if not class_matches:
            return False
        
        last_class = class_matches[-1]
        
        # Count braces from the class start to current position
        segment = content[last_class.end():position]
        open_braces = segment.count('{')
        close_braces = segment.count('}')
        
        return open_braces > close_braces

    def _is_inside_function(self, content: str, position: int) -> bool:
        """Check if position is inside a function definition."""
        # Similar logic to _is_inside_class but for functions
        before_content = content[:position]
        
        # Look for function patterns before this position
        func_pattern = r'\w+\s*\([^)]*\)\s*(?:async\s*)?\s*\{'
        func_matches = list(re.finditer(func_pattern, before_content))
        if not func_matches:
            return False
        
        last_func = func_matches[-1]
        
        # Count braces from the function start to current position
        segment = content[last_func.end()-1:position]  # Include the opening brace
        open_braces = segment.count('{')
        close_braces = segment.count('}')
        
        return open_braces > close_braces

    def _find_closing_brace(self, content: str, start: int) -> Tuple[int, int]:
        """Find the closing brace for a block starting at given position."""
        open_count = 1
        start_line = content[:start].count('\n') + 1
        
        for i, char in enumerate(content[start:], start):
            if char == '{':
                open_count += 1
            elif char == '}':
                open_count -= 1
                if open_count == 0:
                    end_line = content[:i].count('\n') + 1
                    return (start_line, end_line)
        
        # If no closing brace found, estimate end
        return (start_line, start_line + 10)

    def _find_matching_brace(self, content: str, start: int) -> int:
        """Find the position of the matching closing brace."""
        open_count = 0
        
        for i, char in enumerate(content[start:], start):
            if char == '{':
                open_count += 1
            elif char == '}':
                open_count -= 1
                if open_count == 0:
                    return i
        
        return -1

    def _symbol_to_def(self, symbol: Dict[str, Any], file_path: str, content: str) -> SymbolDef:
        """Convert internal symbol representation to SymbolDef."""
        # Extract documentation if available
        doc = self._extract_documentation(content, symbol.get('line', 1))
        
        return {
            'symbol': symbol['symbol'],
            'kind': symbol['kind'],
            'language': self.lang,
            'signature': symbol['signature'],
            'doc': doc,
            'defined_in': file_path,
            'line': symbol.get('line', 1),
            'span': symbol.get('span', (symbol.get('line', 1), symbol.get('line', 1) + 1))
        }

    def _extract_documentation(self, content: str, line: int) -> Optional[str]:
        """Extract documentation comment above a symbol."""
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
            if line_content.startswith('///'):
                doc_lines.insert(0, line_content[3:].strip())
            elif line_content.startswith('*') and doc_lines:
                doc_lines.insert(0, line_content[1:].strip())
            elif line_content.startswith('/**'):
                doc_lines.insert(0, line_content[3:].strip())
            elif line_content.endswith('*/'):
                doc_lines.insert(0, line_content[:-2].strip())
                break
            elif not line_content or line_content.startswith('//'):
                continue
            else:
                break
        
        return '\n'.join(doc_lines) if doc_lines else None

    def getDefinition(self, symbol: str) -> SymbolDef | None:
        """Get the definition of a symbol."""
        # First check cache
        for file_path, symbols in self._symbol_cache.items():
            for sym_def in symbols:
                if sym_def['symbol'] == symbol or sym_def['symbol'].endswith(f'.{symbol}'):
                    return sym_def
        
        # Search in all Dart files
        for path in Path(".").rglob("*.dart"):
            try:
                # Skip build and cache directories
                if any(part in path.parts for part in ["build", ".dart_tool", ".pub-cache", "packages"]):
                    continue
                
                content = path.read_text(encoding="utf-8")
                shard = self.indexFile(path, content)
                
                for sym in shard['symbols']:
                    if sym['symbol'] == symbol or sym['symbol'].endswith(f'.{symbol}'):
                        return self._symbol_to_def(sym, str(path), content)
            except Exception:
                continue
        
        return None

    def findReferences(self, symbol: str) -> list[Reference]:
        """Find all references to a symbol."""
        refs: List[Reference] = []
        seen: Set[Tuple[str, int]] = set()
        
        # Search in all Dart files
        for path in Path(".").rglob("*.dart"):
            try:
                # Skip build and cache directories
                if any(part in path.parts for part in ["build", ".dart_tool", ".pub-cache", "packages"]):
                    continue
                
                content = path.read_text(encoding="utf-8")
                
                # Simple text search for references
                lines = content.splitlines()
                for i, line in enumerate(lines):
                    # Look for whole word matches
                    pattern = r'\b' + re.escape(symbol) + r'\b'
                    if re.search(pattern, line):
                        line_no = i + 1
                        key = (str(path), line_no)
                        if key not in seen:
                            refs.append(Reference(file=str(path), line=line_no))
                            seen.add(key)
            except Exception:
                continue
        
        return refs

    def search(self, query: str, opts: SearchOpts | None = None) -> list[SearchResult]:
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
        return len(self._symbol_cache)
