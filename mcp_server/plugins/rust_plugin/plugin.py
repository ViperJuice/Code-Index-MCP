"""Rust language plugin for Code Index MCP."""

from __future__ import annotations

import logging
import re
import time
from pathlib import Path
from typing import Optional, List, Dict, Any, Iterable

from tree_sitter import Parser
from tree_sitter_languages import get_language, get_parser

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
    """Rust language plugin with tree-sitter parsing."""
    
    lang = "rust"
    
    def __init__(self, sqlite_store: Optional[SQLiteStore] = None) -> None:
        """Initialize the Rust plugin."""
        self._sqlite_store = sqlite_store
        self._repository_id = None
        self._indexer = FuzzyIndexer(sqlite_store=sqlite_store)
        
        # Initialize tree-sitter parser
        try:
            self._language = get_language('rust')
            self._parser = get_parser('rust')
        except (ValueError, AttributeError, Exception) as e:
            logger.warning(f"Failed to initialize tree-sitter Rust parser: {e}")
            # Fallback to simple regex-based parsing
            self._language = None
            self._parser = None
        
        # Create or get repository if SQLite is enabled
        if self._sqlite_store:
            self._repository_id = self._sqlite_store.create_repository(
                str(Path.cwd()), 
                Path.cwd().name,
                {"language": "rust"}
            )
        
        # Cache for storing parsed results
        self._file_cache: Dict[str, IndexShard] = {}
        
        logger.info("Rust plugin initialized")
        self._preindex()

    def _preindex(self) -> None:
        """Pre-index all Rust files in the current directory."""
        start_time = time.time()
        indexed_count = 0
        
        for path in Path(".").rglob("*.rs"):
            try:
                if path.is_file():
                    text = path.read_text(encoding='utf-8')
                    self._indexer.add_file(str(path), text)
                    indexed_count += 1
            except Exception as e:
                logger.warning(f"Failed to pre-index {path}: {e}")
                continue
        
        elapsed = time.time() - start_time
        logger.info(f"Pre-indexed {indexed_count} Rust files in {elapsed:.3f}s")

    def supports(self, path: str | Path) -> bool:
        """Check if this plugin supports the given file path."""
        return Path(path).suffix == ".rs"

    def indexFile(self, path: str | Path, content: str) -> IndexShard:
        """Index a Rust file and extract symbols."""
        start_time = time.time()
        
        if isinstance(path, str):
            path = Path(path)
        
        try:
            # Add to fuzzy indexer
            self._indexer.add_file(str(path), content)
            
            # Store file in SQLite if available
            file_id = None
            if self._sqlite_store and self._repository_id:
                import hashlib
                file_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
                
                # Try to get relative path, fallback to absolute path if fails
                try:
                    relative_path = str(path.relative_to(Path.cwd()))
                except (ValueError, OSError):
                    relative_path = str(path)
                
                file_id = self._sqlite_store.store_file(
                    self._repository_id,
                    str(path),
                    relative_path,
                    language="rust",
                    size=len(content),
                    hash=file_hash
                )

            # Parse with tree-sitter or fallback to regex
            if self._parser:
                tree = self._parser.parse(content.encode("utf-8"))
                root = tree.root_node
                symbols = self._extract_symbols(root, content, str(path), file_id)
            else:
                symbols = self._extract_symbols_regex(content, str(path), file_id)
            
            # Create index shard
            shard = IndexShard(
                file=str(path),
                symbols=symbols,
                language=self.lang
            )
            
            # Cache the result
            self._file_cache[str(path)] = shard
            
            elapsed = time.time() - start_time
            logger.debug(f"Indexed {path} in {elapsed*1000:.1f}ms, found {len(symbols)} symbols")
            
            return shard
            
        except Exception as e:
            logger.error(f"Failed to index {path}: {e}")
            return IndexShard(file=str(path), symbols=[], language=self.lang)

    def _extract_symbols(self, root, content: str, file_path: str, file_id: Optional[int]) -> List[Dict[str, Any]]:
        """Extract symbols from the AST."""
        symbols = []
        
        def visit_node(node):
            """Recursively visit AST nodes to extract symbols."""
            
            # Function definitions
            if node.type == "function_item":
                self._extract_function(node, content, symbols, file_path, file_id)
            
            # Struct definitions
            elif node.type == "struct_item":
                self._extract_struct(node, content, symbols, file_path, file_id)
            
            # Enum definitions
            elif node.type == "enum_item":
                self._extract_enum(node, content, symbols, file_path, file_id)
            
            # Trait definitions
            elif node.type == "trait_item":
                self._extract_trait(node, content, symbols, file_path, file_id)
            
            # Implementation blocks
            elif node.type == "impl_item":
                self._extract_impl(node, content, symbols, file_path, file_id)
            
            # Module definitions
            elif node.type == "mod_item":
                self._extract_module(node, content, symbols, file_path, file_id)
            
            # Use statements
            elif node.type == "use_declaration":
                self._extract_use(node, content, symbols, file_path, file_id)
            
            # Constants and static variables
            elif node.type in ["const_item", "static_item"]:
                self._extract_constant(node, content, symbols, file_path, file_id)
            
            # Type aliases
            elif node.type == "type_item":
                self._extract_type_alias(node, content, symbols, file_path, file_id)
            
            # Recursively visit children
            for child in node.children:
                visit_node(child)
        
        visit_node(root)
        return symbols

    def _extract_symbols_regex(self, content: str, file_path: str, file_id: Optional[int]) -> List[Dict[str, Any]]:
        """Fallback symbol extraction using regular expressions."""
        symbols = []
        lines = content.split('\n')
        
        # Extract docstrings for symbols
        def extract_preceding_docs(line_idx: int) -> Optional[str]:
            """Extract documentation comments preceding a symbol."""
            docs = []
            i = line_idx - 1
            while i >= 0 and (lines[i].strip().startswith('///') or lines[i].strip().startswith('//!')):
                docs.insert(0, lines[i].strip()[3:].strip())
                i -= 1
            return ' '.join(docs) if docs else None
        
        # Regex patterns for Rust constructs
        patterns = {
            'function': re.compile(r'^\s*(pub\s+)?fn\s+(\w+)\s*\(([^)]*)\)(\s*->\s*[^{]+)?'),
            'struct': re.compile(r'^\s*(pub\s+)?struct\s+(\w+)(<[^>]+>)?'),
            'enum': re.compile(r'^\s*(pub\s+)?enum\s+(\w+)(<[^>]+>)?'),
            'trait': re.compile(r'^\s*(pub\s+)?trait\s+(\w+)(<[^>]+>)?'),
            'impl': re.compile(r'^\s*impl(<[^>]+>)?\s+([^{]+?)\s*(?:for\s+([^{]+?))?\s*{'),
            'const': re.compile(r'^\s*(pub\s+)?const\s+(\w+):\s*([^=]+)'),
            'static': re.compile(r'^\s*(pub\s+)?static\s+(\w+):\s*([^=]+)'),
            'type_alias': re.compile(r'^\s*(pub\s+)?type\s+(\w+)(<[^>]+>)?\s*='),
            'module': re.compile(r'^\s*(pub\s+)?mod\s+(\w+)'),
            'use': re.compile(r'^\s*use\s+([^;]+);'),
        }
        
        for line_num, line in enumerate(lines, 1):
            for kind, pattern in patterns.items():
                match = pattern.match(line)
                if match:
                    if kind == 'function':
                        visibility = 'pub' if match.group(1) else 'private'
                        name = match.group(2)
                        params = match.group(3) or ''
                        return_type = match.group(4) or ''
                        signature = f"fn {name}({params}){return_type}"
                        docstring = extract_preceding_docs(line_num - 1)
                        
                        symbol_data = {
                            "symbol": name,
                            "kind": "function",
                            "signature": signature,
                            "line": line_num,
                            "span": (line_num, line_num),
                            "visibility": visibility,
                        }
                        if docstring:
                            symbol_data["docstring"] = docstring
                        
                    elif kind in ['struct', 'enum', 'trait']:
                        visibility = 'pub' if match.group(1) else 'private'
                        name = match.group(2)
                        generics = match.group(3) or ''
                        signature = f"{kind} {name}{generics}"
                        docstring = extract_preceding_docs(line_num - 1)
                        
                        symbol_data = {
                            "symbol": name,
                            "kind": kind,
                            "signature": signature,
                            "line": line_num,
                            "span": (line_num, line_num),
                            "visibility": visibility,
                        }
                        if docstring:
                            symbol_data["docstring"] = docstring
                        
                    elif kind == 'impl':
                        generics = match.group(1) or ''
                        type_name = match.group(2).strip()
                        trait_name = match.group(3)
                        
                        if trait_name:
                            signature = f"impl{generics} {trait_name.strip()} for {type_name}"
                            symbol_kind = "trait_impl"
                        else:
                            signature = f"impl{generics} {type_name}"
                            symbol_kind = "impl"
                        
                        symbol_data = {
                            "symbol": f"impl_{type_name.replace(' ', '_')}",
                            "kind": symbol_kind,
                            "signature": signature,
                            "line": line_num,
                            "span": (line_num, line_num),
                            "type_name": type_name,
                        }
                        
                    elif kind in ['const', 'static']:
                        visibility = 'pub' if match.group(1) else 'private'
                        name = match.group(2)
                        type_name = match.group(3).strip()
                        signature = f"{kind} {name}: {type_name}"
                        
                        symbol_data = {
                            "symbol": name,
                            "kind": "constant" if kind == 'const' else "static",
                            "signature": signature,
                            "line": line_num,
                            "span": (line_num, line_num),
                            "visibility": visibility,
                        }
                        
                    elif kind == 'type_alias':
                        visibility = 'pub' if match.group(1) else 'private'
                        name = match.group(2)
                        generics = match.group(3) or ''
                        signature = f"type {name}{generics} = ..."
                        
                        symbol_data = {
                            "symbol": name,
                            "kind": "type_alias",
                            "signature": signature,
                            "line": line_num,
                            "span": (line_num, line_num),
                            "visibility": visibility,
                        }
                        
                    elif kind == 'module':
                        visibility = 'pub' if match.group(1) else 'private'
                        name = match.group(2)
                        signature = f"mod {name}"
                        
                        symbol_data = {
                            "symbol": name,
                            "kind": "module",
                            "signature": signature,
                            "line": line_num,
                            "span": (line_num, line_num),
                            "visibility": visibility,
                        }
                        
                    elif kind == 'use':
                        use_path = match.group(1).strip()
                        imported_items = self._parse_use_statement(f"use {use_path};")
                        
                        for item in imported_items:
                            symbol_data = {
                                "symbol": item.split('::')[-1],  # Get the last part
                                "kind": "import",
                                "signature": f"use {use_path};",
                                "line": line_num,
                                "span": (line_num, line_num),
                            }
                            
                            if self._sqlite_store and file_id:
                                symbol_id = self._sqlite_store.store_symbol(
                                    file_id, symbol_data["symbol"], "import", 
                                    line_num, line_num, signature=symbol_data["signature"]
                                )
                                self._indexer.add_symbol(
                                    symbol_data["symbol"], file_path, line_num,
                                    {"symbol_id": symbol_id, "file_id": file_id}
                                )
                            
                            symbols.append(symbol_data)
                        continue  # Skip the general handling below
                    
                    else:
                        continue  # Unknown pattern
                    
                    # Store in SQLite if available (for non-use statements)
                    if self._sqlite_store and file_id:
                        symbol_id = self._sqlite_store.store_symbol(
                            file_id, symbol_data["symbol"], symbol_data["kind"], 
                            line_num, line_num, signature=symbol_data["signature"]
                        )
                        self._indexer.add_symbol(
                            symbol_data["symbol"], file_path, line_num,
                            {"symbol_id": symbol_id, "file_id": file_id}
                        )
                    
                    symbols.append(symbol_data)
                    break  # Only match the first pattern per line
        
        return symbols

    def _extract_function(self, node, content: str, symbols: List[Dict], file_path: str, file_id: Optional[int]):
        """Extract function definition."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        
        name = content[name_node.start_byte:name_node.end_byte]
        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1
        
        # Extract parameters
        params_node = node.child_by_field_name("parameters")
        params = ""
        if params_node:
            params = content[params_node.start_byte:params_node.end_byte]
        
        # Extract return type
        return_type = ""
        return_type_node = node.child_by_field_name("return_type")
        if return_type_node:
            return_type = content[return_type_node.start_byte:return_type_node.end_byte]
        
        signature = f"fn {name}{params}{return_type}"
        
        # Extract visibility (pub, pub(crate), etc.)
        visibility = self._extract_visibility(node, content)
        
        # Extract docstring
        docstring = self._extract_docstring(node, content)
        
        symbol_data = {
            "symbol": name,
            "kind": "function",
            "signature": signature,
            "line": start_line,
            "span": (start_line, end_line),
            "visibility": visibility,
            "docstring": docstring,
        }
        
        # Store in SQLite if available
        if self._sqlite_store and file_id:
            symbol_id = self._sqlite_store.store_symbol(
                file_id, name, "function", start_line, end_line, signature=signature
            )
            self._indexer.add_symbol(
                name, file_path, start_line,
                {"symbol_id": symbol_id, "file_id": file_id}
            )
        
        symbols.append(symbol_data)

    def _extract_struct(self, node, content: str, symbols: List[Dict], file_path: str, file_id: Optional[int]):
        """Extract struct definition."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        
        name = content[name_node.start_byte:name_node.end_byte]
        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1
        
        # Extract generic parameters
        type_params = ""
        type_params_node = node.child_by_field_name("type_parameters")
        if type_params_node:
            type_params = content[type_params_node.start_byte:type_params_node.end_byte]
        
        signature = f"struct {name}{type_params}"
        visibility = self._extract_visibility(node, content)
        docstring = self._extract_docstring(node, content)
        
        symbol_data = {
            "symbol": name,
            "kind": "struct",
            "signature": signature,
            "line": start_line,
            "span": (start_line, end_line),
            "visibility": visibility,
            "docstring": docstring,
        }
        
        if self._sqlite_store and file_id:
            symbol_id = self._sqlite_store.store_symbol(
                file_id, name, "struct", start_line, end_line, signature=signature
            )
            self._indexer.add_symbol(
                name, file_path, start_line,
                {"symbol_id": symbol_id, "file_id": file_id}
            )
        
        symbols.append(symbol_data)

    def _extract_enum(self, node, content: str, symbols: List[Dict], file_path: str, file_id: Optional[int]):
        """Extract enum definition."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        
        name = content[name_node.start_byte:name_node.end_byte]
        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1
        
        signature = f"enum {name}"
        visibility = self._extract_visibility(node, content)
        docstring = self._extract_docstring(node, content)
        
        symbol_data = {
            "symbol": name,
            "kind": "enum",
            "signature": signature,
            "line": start_line,
            "span": (start_line, end_line),
            "visibility": visibility,
            "docstring": docstring,
        }
        
        if self._sqlite_store and file_id:
            symbol_id = self._sqlite_store.store_symbol(
                file_id, name, "enum", start_line, end_line, signature=signature
            )
            self._indexer.add_symbol(
                name, file_path, start_line,
                {"symbol_id": symbol_id, "file_id": file_id}
            )
        
        symbols.append(symbol_data)

    def _extract_trait(self, node, content: str, symbols: List[Dict], file_path: str, file_id: Optional[int]):
        """Extract trait definition."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        
        name = content[name_node.start_byte:name_node.end_byte]
        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1
        
        signature = f"trait {name}"
        visibility = self._extract_visibility(node, content)
        docstring = self._extract_docstring(node, content)
        
        symbol_data = {
            "symbol": name,
            "kind": "trait",
            "signature": signature,
            "line": start_line,
            "span": (start_line, end_line),
            "visibility": visibility,
            "docstring": docstring,
        }
        
        if self._sqlite_store and file_id:
            symbol_id = self._sqlite_store.store_symbol(
                file_id, name, "trait", start_line, end_line, signature=signature
            )
            self._indexer.add_symbol(
                name, file_path, start_line,
                {"symbol_id": symbol_id, "file_id": file_id}
            )
        
        symbols.append(symbol_data)

    def _extract_impl(self, node, content: str, symbols: List[Dict], file_path: str, file_id: Optional[int]):
        """Extract implementation block."""
        type_node = node.child_by_field_name("type")
        trait_node = node.child_by_field_name("trait")
        
        if not type_node:
            return
        
        type_name = content[type_node.start_byte:type_node.end_byte]
        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1
        
        if trait_node:
            trait_name = content[trait_node.start_byte:trait_node.end_byte]
            signature = f"impl {trait_name} for {type_name}"
            kind = "trait_impl"
        else:
            signature = f"impl {type_name}"
            kind = "impl"
        
        symbol_data = {
            "symbol": f"impl_{type_name}",
            "kind": kind,
            "signature": signature,
            "line": start_line,
            "span": (start_line, end_line),
            "type_name": type_name,
        }
        
        if trait_node:
            symbol_data["trait_name"] = content[trait_node.start_byte:trait_node.end_byte]
        
        if self._sqlite_store and file_id:
            symbol_id = self._sqlite_store.store_symbol(
                file_id, f"impl_{type_name}", kind, start_line, end_line, signature=signature
            )
            self._indexer.add_symbol(
                f"impl_{type_name}", file_path, start_line,
                {"symbol_id": symbol_id, "file_id": file_id}
            )
        
        symbols.append(symbol_data)

    def _extract_module(self, node, content: str, symbols: List[Dict], file_path: str, file_id: Optional[int]):
        """Extract module definition."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        
        name = content[name_node.start_byte:name_node.end_byte]
        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1
        
        signature = f"mod {name}"
        visibility = self._extract_visibility(node, content)
        
        symbol_data = {
            "symbol": name,
            "kind": "module",
            "signature": signature,
            "line": start_line,
            "span": (start_line, end_line),
            "visibility": visibility,
        }
        
        if self._sqlite_store and file_id:
            symbol_id = self._sqlite_store.store_symbol(
                file_id, name, "module", start_line, end_line, signature=signature
            )
            self._indexer.add_symbol(
                name, file_path, start_line,
                {"symbol_id": symbol_id, "file_id": file_id}
            )
        
        symbols.append(symbol_data)

    def _extract_use(self, node, content: str, symbols: List[Dict], file_path: str, file_id: Optional[int]):
        """Extract use statement."""
        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1
        
        use_stmt = content[node.start_byte:node.end_byte]
        
        # Extract the imported items
        imported_items = self._parse_use_statement(use_stmt)
        
        for item in imported_items:
            symbol_data = {
                "symbol": item,
                "kind": "import",
                "signature": use_stmt,
                "line": start_line,
                "span": (start_line, end_line),
            }
            
            if self._sqlite_store and file_id:
                symbol_id = self._sqlite_store.store_symbol(
                    file_id, item, "import", start_line, end_line, signature=use_stmt
                )
                self._indexer.add_symbol(
                    item, file_path, start_line,
                    {"symbol_id": symbol_id, "file_id": file_id}
                )
            
            symbols.append(symbol_data)

    def _extract_constant(self, node, content: str, symbols: List[Dict], file_path: str, file_id: Optional[int]):
        """Extract constant or static variable."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        
        name = content[name_node.start_byte:name_node.end_byte]
        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1
        
        kind = "constant" if node.type == "const_item" else "static"
        signature = content[node.start_byte:node.end_byte]
        visibility = self._extract_visibility(node, content)
        
        symbol_data = {
            "symbol": name,
            "kind": kind,
            "signature": signature,
            "line": start_line,
            "span": (start_line, end_line),
            "visibility": visibility,
        }
        
        if self._sqlite_store and file_id:
            symbol_id = self._sqlite_store.store_symbol(
                file_id, name, kind, start_line, end_line, signature=signature
            )
            self._indexer.add_symbol(
                name, file_path, start_line,
                {"symbol_id": symbol_id, "file_id": file_id}
            )
        
        symbols.append(symbol_data)

    def _extract_type_alias(self, node, content: str, symbols: List[Dict], file_path: str, file_id: Optional[int]):
        """Extract type alias."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        
        name = content[name_node.start_byte:name_node.end_byte]
        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1
        
        signature = content[node.start_byte:node.end_byte]
        visibility = self._extract_visibility(node, content)
        
        symbol_data = {
            "symbol": name,
            "kind": "type_alias",
            "signature": signature,
            "line": start_line,
            "span": (start_line, end_line),
            "visibility": visibility,
        }
        
        if self._sqlite_store and file_id:
            symbol_id = self._sqlite_store.store_symbol(
                file_id, name, "type_alias", start_line, end_line, signature=signature
            )
            self._indexer.add_symbol(
                name, file_path, start_line,
                {"symbol_id": symbol_id, "file_id": file_id}
            )
        
        symbols.append(symbol_data)

    def _extract_visibility(self, node, content: str) -> str:
        """Extract visibility modifier (pub, pub(crate), etc.)."""
        # Look for visibility modifier in the node's children
        for child in node.children:
            if child.type == "visibility_modifier":
                return content[child.start_byte:child.end_byte]
        return "private"

    def _extract_docstring(self, node, content: str) -> Optional[str]:
        """Extract documentation comments preceding the node."""
        # Look for doc comments before the node
        # This is a simplified extraction - could be improved
        lines = content.split('\n')
        node_line = node.start_point[0]
        
        doc_lines = []
        for i in range(node_line - 1, -1, -1):
            line = lines[i].strip()
            if line.startswith('///') or line.startswith('//!'):
                doc_lines.insert(0, line[3:].strip())
            elif line.startswith('/**') or line.startswith('/*!'):
                # Handle block comments (simplified)
                doc_lines.insert(0, line[3:].strip())
                break
            elif not line or line.startswith('//'):
                continue
            else:
                break
        
        return '\n'.join(doc_lines) if doc_lines else None

    def _parse_use_statement(self, use_stmt: str) -> List[str]:
        """Parse a use statement to extract imported items."""
        # Remove 'use' keyword and semicolon
        use_stmt = use_stmt.replace('use ', '').replace(';', '').strip()
        
        # Handle simple cases for now
        # This could be improved to handle complex use patterns
        if '{' in use_stmt and '}' in use_stmt:
            # Handle use crate::{item1, item2}
            base_path = use_stmt.split('{')[0].strip('::').strip()
            items_part = use_stmt.split('{')[1].split('}')[0]
            items = [item.strip() for item in items_part.split(',')]
            return [f"{base_path}::{item}" if base_path else item for item in items]
        else:
            # Handle simple use statements
            return [use_stmt]

    def getDefinition(self, symbol: str) -> SymbolDef | None:
        """Get definition of a symbol."""
        try:
            # Search through cached files first
            for file_path, shard in self._file_cache.items():
                try:
                    # Look for the symbol in this file
                    for sym in shard["symbols"]:
                        if sym["symbol"] == symbol:
                            return SymbolDef(
                                symbol=sym["symbol"],
                                kind=sym["kind"],
                                language=self.lang,
                                signature=sym["signature"],
                                doc=sym.get("docstring"),
                                defined_in=file_path,
                                line=sym["line"],
                                span=sym["span"],
                            )
                
                except Exception as e:
                    logger.warning(f"Error processing cached file {file_path} for definition lookup: {e}")
                    continue
            
            # Search through project files if not found in cache
            for path in Path(".").rglob("*.rs"):
                try:
                    if not path.is_file():
                        continue
                    
                    path_str = str(path)
                    if path_str in self._file_cache:
                        continue  # Already processed above
                    
                    content = path.read_text(encoding='utf-8')
                    shard = self.indexFile(path, content)
                    
                    # Look for the symbol in this file
                    for sym in shard["symbols"]:
                        if sym["symbol"] == symbol:
                            return SymbolDef(
                                symbol=sym["symbol"],
                                kind=sym["kind"],
                                language=self.lang,
                                signature=sym["signature"],
                                doc=sym.get("docstring"),
                                defined_in=path_str,
                                line=sym["line"],
                                span=sym["span"],
                            )
                
                except Exception as e:
                    logger.warning(f"Error processing {path} for definition lookup: {e}")
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting definition for {symbol}: {e}")
            return None

    def findReferences(self, symbol: str) -> Iterable[Reference]:
        """Find all references to a symbol."""
        refs: List[Reference] = []
        seen: set[tuple[str, int]] = set()
        
        try:
            # Search in cached files first
            for file_path, shard in self._file_cache.items():
                try:
                    content = Path(file_path).read_text(encoding='utf-8')
                    
                    # Simple text-based search for references
                    lines = content.split('\n')
                    for line_num, line in enumerate(lines, 1):
                        # Look for symbol usage (simple pattern matching)
                        if re.search(r'\b' + re.escape(symbol) + r'\b', line):
                            key = (file_path, line_num)
                            if key not in seen:
                                refs.append(Reference(file=file_path, line=line_num))
                                seen.add(key)
                
                except Exception as e:
                    logger.warning(f"Error processing {file_path} for reference search: {e}")
                    continue
            
            # Also search in current directory for completeness
            for path in Path(".").rglob("*.rs"):
                try:
                    if not path.is_file():
                        continue
                    
                    path_str = str(path)
                    if path_str in self._file_cache:
                        continue  # Already processed above
                    
                    content = path.read_text(encoding='utf-8')
                    
                    # Simple text-based search for references
                    lines = content.split('\n')
                    for line_num, line in enumerate(lines, 1):
                        # Look for symbol usage (simple pattern matching)
                        if re.search(r'\b' + re.escape(symbol) + r'\b', line):
                            key = (path_str, line_num)
                            if key not in seen:
                                refs.append(Reference(file=path_str, line=line_num))
                                seen.add(key)
                
                except Exception as e:
                    logger.warning(f"Error processing {path} for reference search: {e}")
                    continue
            
            return refs
            
        except Exception as e:
            logger.error(f"Error finding references for {symbol}: {e}")
            return []

    def search(self, query: str, opts: SearchOpts | None = None) -> Iterable[SearchResult]:
        """Search for code patterns."""
        limit = 20
        if opts and "limit" in opts:
            limit = opts["limit"]
        
        if opts and opts.get("semantic"):
            # Semantic search not implemented yet
            return []
        
        try:
            # Use the fuzzy indexer for search
            return self._indexer.search(query, limit=limit)
        except Exception as e:
            logger.error(f"Error during search: {e}")
            return []

    def get_indexed_count(self) -> int:
        """Return the number of indexed files."""
        if hasattr(self._indexer, 'index'):
            return len(self._indexer.index)
        return len(self._file_cache)