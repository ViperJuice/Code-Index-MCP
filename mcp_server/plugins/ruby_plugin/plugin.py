"""Ruby language plugin for code indexing and analysis.

This plugin provides comprehensive Ruby code parsing including:
- Classes and modules
- Methods (instance, class, private/protected)
- Constants and variables
- Metaprogramming patterns (define_method, etc.)
- Rails framework detection (ActiveRecord, controllers, routes)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional, Dict, List, Set, Tuple
import hashlib

from ...plugin_base import (
    IPlugin,
    IndexShard,
    SymbolDef,
    Reference,
    SearchResult,
    SearchOpts,
)

from ...utils.treesitter_wrapper import TreeSitterWrapper
from ...utils.fuzzy_indexer import FuzzyIndexer
from ...storage.sqlite_store import SQLiteStore


class RubyPlugin(IPlugin):
    """Ruby language plugin with comprehensive parsing and Rails support."""
    
    lang = "ruby"
    
    def __init__(self, sqlite_store: Optional[SQLiteStore] = None) -> None:
        self._ts = TreeSitterWrapper()
        self._indexer = FuzzyIndexer(sqlite_store=sqlite_store)
        self._sqlite_store = sqlite_store
        self._repository_id = None
        
        # Rails patterns for framework detection
        self._rails_patterns = {
            'model': re.compile(r'class\s+(\w+)\s*<\s*(?:ActiveRecord::Base|ApplicationRecord)'),
            'controller': re.compile(r'class\s+(\w+Controller)\s*<\s*(?:ActionController::Base|ApplicationController)'),
            'route': re.compile(r'(?:get|post|put|patch|delete)\s+[\'"]([^\'"]+)[\'"]'),
            'migration': re.compile(r'class\s+(\w+)\s*<\s*ActiveRecord::Migration'),
        }
        
        # Metaprogramming patterns
        self._meta_patterns = {
            'define_method': re.compile(r'define_method\s*[\(\s]*[\'":]*(\w+)'),
            'attr_accessor': re.compile(r'attr_(?:accessor|reader|writer)\s+:(\w+)'),
            'scope': re.compile(r'scope\s+:(\w+)'),
            'validates': re.compile(r'validates\s+:(\w+)'),
            'belongs_to': re.compile(r'belongs_to\s+:(\w+)'),
            'has_many': re.compile(r'has_many\s+:(\w+)'),
            'has_one': re.compile(r'has_one\s+:(\w+)'),
        }
        
        # Create or get repository if SQLite is enabled
        if self._sqlite_store:
            self._repository_id = self._sqlite_store.create_repository(
                str(Path.cwd()), 
                Path.cwd().name,
                {"language": "ruby"}
            )
        
        self._preindex()

    def _preindex(self) -> None:
        """Pre-index all Ruby files in the current directory."""
        ruby_extensions = {'.rb', '.rake', '.gemspec'}
        for path in Path(".").rglob("*"):
            if path.suffix in ruby_extensions:
                try:
                    text = path.read_text(encoding='utf-8')
                    self._indexer.add_file(str(path), text)
                except Exception:
                    continue

    def supports(self, path: str | Path) -> bool:
        """Return True if file extension matches Ruby files."""
        if isinstance(path, str):
            path = Path(path)
        return path.suffix in {'.rb', '.rake', '.gemspec'}

    def indexFile(self, path: str | Path, content: str) -> IndexShard:
        """Index a Ruby file and extract symbols."""
        if isinstance(path, str):
            path = Path(path)
        
        self._indexer.add_file(str(path), content)
        
        # Store file in SQLite if available
        file_id = None
        if self._sqlite_store and self._repository_id:
            file_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
            try:
                # Try to get relative path, fallback to filename only
                if path.is_absolute():
                    try:
                        relative_path = str(path.relative_to(Path.cwd()))
                    except ValueError:
                        relative_path = path.name
                else:
                    relative_path = str(path)
                        
                file_id = self._sqlite_store.store_file(
                    self._repository_id,
                    str(path),
                    relative_path,
                    language="ruby",
                    size=len(content),
                    hash=file_hash
                )
            except Exception:
                # Skip SQLite storage if path handling fails
                pass

        symbols = []
        
        # Use regex-based parsing (Tree-sitter Ruby support would need separate configuration)
        symbols = self._extract_symbols_regex(content)
        
        # Store symbols in SQLite and fuzzy indexer
        for symbol in symbols:
            if self._sqlite_store and file_id:
                symbol_id = self._sqlite_store.store_symbol(
                    file_id,
                    symbol["symbol"],
                    symbol["kind"],
                    symbol["line"],
                    symbol.get("span", (symbol["line"], symbol["line"]))[1],
                    signature=symbol.get("signature", "")
                )
                # Add to fuzzy indexer with metadata
                self._indexer.add_symbol(
                    symbol["symbol"], 
                    str(path), 
                    symbol["line"],
                    {"symbol_id": symbol_id, "file_id": file_id}
                )

        return {"file": str(path), "symbols": symbols, "language": self.lang}

    def _extract_symbols_treesitter(self, content: str, root_node) -> List[Dict]:
        """Extract symbols using Tree-sitter parsing."""
        symbols = []
        
        for child in root_node.named_children:
            symbol_info = self._parse_node(content, child)
            if symbol_info:
                symbols.extend(symbol_info)
                
        return symbols

    def _parse_node(self, content: str, node, parent_class: str = None) -> List[Dict]:
        """Parse a Tree-sitter node and extract symbol information."""
        symbols = []
        
        if node.type == "class":
            symbols.extend(self._parse_class(content, node))
        elif node.type == "module":
            symbols.extend(self._parse_module(content, node))
        elif node.type == "method":
            symbols.extend(self._parse_method(content, node, parent_class))
        elif node.type == "singleton_method":
            symbols.extend(self._parse_singleton_method(content, node, parent_class))
        elif node.type == "constant":
            symbols.extend(self._parse_constant(content, node))
        elif node.type == "call" and self._is_metaprogramming_call(content, node):
            symbols.extend(self._parse_metaprogramming(content, node))
            
        # Recursively parse child nodes
        for child in node.named_children:
            symbols.extend(self._parse_node(content, child, parent_class))
            
        return symbols

    def _parse_class(self, content: str, node) -> List[Dict]:
        """Parse Ruby class definition."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return []
            
        name = content[name_node.start_byte:name_node.end_byte]
        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1
        
        # Check for Rails patterns
        superclass_node = node.child_by_field_name("superclass")
        superclass = ""
        if superclass_node:
            superclass = content[superclass_node.start_byte:superclass_node.end_byte]
            
        kind = "class"
        if "ActiveRecord" in superclass or "ApplicationRecord" in superclass:
            kind = "model"
        elif "Controller" in superclass or "ApplicationController" in superclass:
            kind = "controller"
            
        signature = f"class {name}"
        if superclass:
            signature += f" < {superclass}"
            
        return [{
            "symbol": name,
            "kind": kind,
            "signature": signature,
            "line": start_line,
            "span": (start_line, end_line),
        }]

    def _parse_module(self, content: str, node) -> List[Dict]:
        """Parse Ruby module definition."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return []
            
        name = content[name_node.start_byte:name_node.end_byte]
        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1
        
        return [{
            "symbol": name,
            "kind": "module",
            "signature": f"module {name}",
            "line": start_line,
            "span": (start_line, end_line),
        }]

    def _parse_method(self, content: str, node, parent_class: str = None) -> List[Dict]:
        """Parse Ruby method definition."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return []
            
        name = content[name_node.start_byte:name_node.end_byte]
        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1
        
        # Check method visibility (private, protected, public)
        visibility = self._get_method_visibility(content, start_line)
        
        signature = f"def {name}"
        params_node = node.child_by_field_name("parameters")
        if params_node:
            params = content[params_node.start_byte:params_node.end_byte]
            signature += f"({params})"
            
        kind = f"{visibility}_method" if visibility != "public" else "method"
        
        return [{
            "symbol": name,
            "kind": kind,
            "signature": signature,
            "line": start_line,
            "span": (start_line, end_line),
        }]

    def _parse_singleton_method(self, content: str, node, parent_class: str = None) -> List[Dict]:
        """Parse Ruby class/singleton method definition."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return []
            
        name = content[name_node.start_byte:name_node.end_byte]
        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1
        
        signature = f"def self.{name}"
        params_node = node.child_by_field_name("parameters")
        if params_node:
            params = content[params_node.start_byte:params_node.end_byte]
            signature += f"({params})"
            
        return [{
            "symbol": name,
            "kind": "class_method",
            "signature": signature,
            "line": start_line,
            "span": (start_line, end_line),
        }]

    def _parse_constant(self, content: str, node) -> List[Dict]:
        """Parse Ruby constant definition."""
        name = content[node.start_byte:node.end_byte]
        start_line = node.start_point[0] + 1
        
        return [{
            "symbol": name,
            "kind": "constant",
            "signature": f"{name} = ...",
            "line": start_line,
            "span": (start_line, start_line),
        }]

    def _parse_metaprogramming(self, content: str, node) -> List[Dict]:
        """Parse metaprogramming calls like define_method, attr_accessor, etc."""
        method_name = content[node.start_byte:node.end_byte].split('(')[0].strip()
        start_line = node.start_point[0] + 1
        
        symbols = []
        line_content = content.split('\n')[start_line - 1] if start_line <= len(content.split('\n')) else ""
        
        # Extract method names from metaprogramming calls
        for pattern_name, pattern in self._meta_patterns.items():
            matches = pattern.findall(line_content)
            for match in matches:
                symbols.append({
                    "symbol": match,
                    "kind": f"generated_{pattern_name}",
                    "signature": line_content.strip(),
                    "line": start_line,
                    "span": (start_line, start_line),
                })
                
        return symbols

    def _is_metaprogramming_call(self, content: str, node) -> bool:
        """Check if a call node represents metaprogramming."""
        method_name = content[node.start_byte:node.end_byte].split('(')[0].strip()
        meta_methods = {'define_method', 'attr_accessor', 'attr_reader', 'attr_writer', 
                       'scope', 'validates', 'belongs_to', 'has_many', 'has_one'}
        return method_name in meta_methods

    def _get_method_visibility(self, content: str, method_line: int) -> str:
        """Determine method visibility by looking for private/protected keywords."""
        lines = content.split('\n')
        for i in range(method_line - 2, -1, -1):  # Look backwards from method
            line = lines[i].strip()
            if line == 'private':
                return 'private'
            elif line == 'protected':
                return 'protected'
            elif line.startswith('def ') or line.startswith('class ') or line.startswith('module '):
                break
        return 'public'

    def _extract_symbols_regex(self, content: str) -> List[Dict]:
        """Fallback regex-based symbol extraction."""
        symbols = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            
            # Class definitions
            class_match = re.match(r'class\s+(\w+)(?:\s*<\s*(\w+(?:::\w+)*))?', line)
            if class_match:
                name = class_match.group(1)
                superclass = class_match.group(2) or ""
                
                kind = "class"
                if "ActiveRecord" in superclass or "ApplicationRecord" in superclass:
                    kind = "model"
                elif "Controller" in superclass:
                    kind = "controller"
                    
                signature = f"class {name}"
                if superclass:
                    signature += f" < {superclass}"
                    
                symbols.append({
                    "symbol": name,
                    "kind": kind,
                    "signature": signature,
                    "line": i,
                    "span": (i, i),
                })
            
            # Module definitions
            module_match = re.match(r'module\s+(\w+)', line)
            if module_match:
                name = module_match.group(1)
                symbols.append({
                    "symbol": name,
                    "kind": "module",
                    "signature": f"module {name}",
                    "line": i,
                    "span": (i, i),
                })
            
            # Method definitions (including ? and ! endings)
            method_match = re.match(r'def\s+(?:self\.)?(\w+[?!]?)', line)
            if method_match:
                name = method_match.group(1)
                is_class_method = 'self.' in line
                kind = "class_method" if is_class_method else "method"
                
                # Check visibility
                visibility = self._get_method_visibility(content, i)
                if visibility != "public":
                    kind = f"{visibility}_method"
                
                symbols.append({
                    "symbol": name,
                    "kind": kind,
                    "signature": line,
                    "line": i,
                    "span": (i, i),
                })
            
            # Constants
            const_match = re.match(r'([A-Z][A-Z0-9_]*)\s*=', line)
            if const_match:
                name = const_match.group(1)
                symbols.append({
                    "symbol": name,
                    "kind": "constant",
                    "signature": line,
                    "line": i,
                    "span": (i, i),
                })
            
            # Metaprogramming patterns
            for pattern_name, pattern in self._meta_patterns.items():
                matches = pattern.findall(line)
                for match in matches:
                    symbols.append({
                        "symbol": match,
                        "kind": f"generated_{pattern_name}",
                        "signature": line,
                        "line": i,
                        "span": (i, i),
                    })
                    
        return symbols

    def getDefinition(self, symbol: str) -> SymbolDef | None:
        """Find the definition of a Ruby symbol."""
        for path in Path(".").rglob("*.rb"):
            try:
                content = path.read_text(encoding='utf-8')
                lines = content.split('\n')
                
                for i, line in enumerate(lines, 1):
                    # Check for class, module, or method definitions (handle ? and ! in method names)
                    escaped_symbol = re.escape(symbol)
                    if (re.search(rf'\b(?:class|module|def)\s+(?:self\.)?{escaped_symbol}\b', line) or
                        re.search(rf'\b{escaped_symbol}\s*=', line)):
                        
                        # Extract signature and documentation
                        signature = line.strip()
                        doc = self._extract_documentation(lines, i - 1)
                        
                        # Determine kind
                        kind = "unknown"
                        if line.strip().startswith('class'):
                            kind = "class"
                        elif line.strip().startswith('module'):
                            kind = "module"
                        elif line.strip().startswith('def'):
                            kind = "method"
                        elif '=' in line:
                            if symbol.isupper():
                                kind = "constant"
                            else:
                                kind = "variable"
                        
                        return {
                            "symbol": symbol,
                            "kind": kind,
                            "language": self.lang,
                            "signature": signature,
                            "doc": doc,
                            "defined_in": str(path),
                            "line": i,
                            "span": (i, i + 3),
                        }
            except Exception:
                continue
                
        return None

    def _extract_documentation(self, lines: List[str], start_line: int) -> str | None:
        """Extract documentation comments above a symbol."""
        doc_lines = []
        
        # Look backwards for comments
        for i in range(start_line - 1, -1, -1):
            line = lines[i].strip()
            if line.startswith('#'):
                doc_lines.insert(0, line[1:].strip())
            elif line == '':
                continue
            else:
                break
                
        return '\n'.join(doc_lines) if doc_lines else None

    def findReferences(self, symbol: str) -> List[Reference]:
        """Find references to a Ruby symbol."""
        refs = []
        seen = set()
        
        for path in Path(".").rglob("*.rb"):
            try:
                content = path.read_text(encoding='utf-8')
                lines = content.split('\n')
                
                for i, line in enumerate(lines, 1):
                    if re.search(rf'\b{re.escape(symbol)}\b', line):
                        key = (str(path), i)
                        if key not in seen:
                            refs.append(Reference(file=str(path), line=i))
                            seen.add(key)
            except Exception:
                continue
                
        return refs

    def search(self, query: str, opts: SearchOpts | None = None) -> List[SearchResult]:
        """Search for symbols in Ruby code."""
        limit = 20
        if opts and "limit" in opts:
            limit = opts["limit"]
        if opts and opts.get("semantic"):
            return []
            
        return self._indexer.search(query, limit=limit)

    def get_indexed_count(self) -> int:
        """Return the number of indexed files."""
        if hasattr(self._indexer, '_file_contents'):
            return len(self._indexer._file_contents)
        return 0


# Alias for backwards compatibility
Plugin = RubyPlugin