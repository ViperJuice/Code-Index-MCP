from __future__ import annotations

import re
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
import hashlib

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


class GoTreeSitterWrapper:
    """Simplified Go parser using regular expressions until tree-sitter is properly configured."""
    
    def __init__(self):
        # Go syntax patterns - handles generics with [T any] syntax
        self.function_pattern = re.compile(
            r'^\s*func\s+(?:\([^)]*\)\s+)?(\w+)(?:\[[^\]]*\])?\s*\([^)]*\)(?:\s*[^{]*)?(?:\s*\{|\s*$)',
            re.MULTILINE
        )
        self.interface_pattern = re.compile(
            r'^\s*type\s+(\w+)\s+interface\s*\{',
            re.MULTILINE
        )
        self.struct_pattern = re.compile(
            r'^\s*type\s+(\w+)\s+struct\s*\{',
            re.MULTILINE
        )
        self.type_pattern = re.compile(
            r'^\s*type\s+(\w+)\s+(?!interface|struct)([^{]+?)(?:\s*$|\s*//)',
            re.MULTILINE
        )
        self.const_pattern = re.compile(
            r'^\s*const\s+(\w+)',
            re.MULTILINE
        )
        self.var_pattern = re.compile(
            r'^\s*var\s+(\w+)',
            re.MULTILINE
        )
        self.package_pattern = re.compile(r'^\s*package\s+(\w+)', re.MULTILINE)
        self.import_pattern = re.compile(r'^\s*import\s+(?:\(\s*([^)]+)\s*\)|"([^"]+)")', re.MULTILINE | re.DOTALL)
    
    def parse_go_file(self, content: str) -> Dict[str, List[Dict[str, Any]]]:
        """Parse Go file content and extract symbols."""
        symbols = {
            'functions': [],
            'interfaces': [],
            'structs': [],
            'types': [],
            'constants': [],
            'variables': [],
            'package': None,
            'imports': []
        }
        
        lines = content.split('\n')
        
        # Parse package
        package_match = self.package_pattern.search(content)
        if package_match:
            symbols['package'] = package_match.group(1)
        
        # Parse imports
        import_matches = self.import_pattern.finditer(content)
        for match in import_matches:
            if match.group(1):  # Multi-line import
                import_block = match.group(1)
                for line in import_block.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('//'):
                        # Extract import path
                        import_match = re.search(r'"([^"]+)"', line)
                        if import_match:
                            symbols['imports'].append(import_match.group(1))
            elif match.group(2):  # Single import
                symbols['imports'].append(match.group(2))
        
        # Parse functions
        for match in self.function_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            symbols['functions'].append({
                'name': match.group(1),
                'line': line_num,
                'signature': match.group(0).strip()
            })
        
        # Parse interfaces
        for match in self.interface_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            symbols['interfaces'].append({
                'name': match.group(1),
                'line': line_num,
                'signature': f"type {match.group(1)} interface"
            })
        
        # Parse structs
        for match in self.struct_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            symbols['structs'].append({
                'name': match.group(1),
                'line': line_num,
                'signature': f"type {match.group(1)} struct"
            })
        
        # Parse type declarations
        for match in self.type_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            symbols['types'].append({
                'name': match.group(1),
                'line': line_num,
                'signature': f"type {match.group(1)} {match.group(2).strip()}"
            })
        
        # Parse constants
        for match in self.const_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            const_name = match.group(1) or match.group(2)
            if const_name:
                symbols['constants'].append({
                    'name': const_name,
                    'line': line_num,
                    'signature': f"const {const_name}"
                })
        
        # Parse variables
        for match in self.var_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            symbols['variables'].append({
                'name': match.group(1),
                'line': line_num,
                'signature': f"var {match.group(1)}"
            })
        
        return symbols


class Plugin(IPlugin):
    lang = "go"

    def __init__(self, sqlite_store: Optional[SQLiteStore] = None) -> None:
        self._parser = GoTreeSitterWrapper()
        self._indexer = FuzzyIndexer(sqlite_store=sqlite_store)
        self._sqlite_store = sqlite_store
        self._repository_id = None
        
        # Create or get repository if SQLite is enabled
        if self._sqlite_store:
            self._repository_id = self._sqlite_store.create_repository(
                str(Path.cwd()), 
                Path.cwd().name,
                {"language": "go"}
            )
        
        self._preindex()

    def _preindex(self) -> None:
        """Pre-index all Go files in the current directory."""
        for path in Path(".").rglob("*.go"):
            try:
                text = path.read_text()
                self._indexer.add_file(str(path), text)
            except Exception:
                continue

    def supports(self, path: str | Path) -> bool:
        """Return True if file extension matches Go files."""
        path_obj = Path(path) if isinstance(path, str) else path
        return path_obj.suffix == ".go" or path_obj.name == "go.mod"

    def indexFile(self, path: str | Path, content: str) -> IndexShard:
        """Index a Go file and extract symbols."""
        if isinstance(path, str):
            path = Path(path)
        
        self._indexer.add_file(str(path), content)
        
        # Store file in SQLite if available
        file_id = None
        if self._sqlite_store and self._repository_id:
            file_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
            # Handle relative path calculation safely
            try:
                if path.is_absolute():
                    relative_path = str(path.relative_to(Path.cwd()))
                else:
                    relative_path = str(path)
            except ValueError:
                # If path is not under current directory, use the filename
                relative_path = path.name
            
            file_id = self._sqlite_store.store_file(
                self._repository_id,
                str(path),
                relative_path,
                language="go",
                size=len(content),
                hash=file_hash
            )

        symbols: List[Dict[str, Any]] = []
        
        # Handle go.mod files
        if path.name == "go.mod":
            return self._parse_go_mod(path, content, file_id)
        
        # Parse Go source files
        parsed_symbols = self._parser.parse_go_file(content)
        
        # Process all symbol types
        for symbol_type, symbol_list in parsed_symbols.items():
            if symbol_type in ['package', 'imports'] or not symbol_list:
                continue
                
            for symbol_data in symbol_list:
                name = symbol_data['name']
                line = symbol_data['line']
                signature = symbol_data['signature']
                
                # Determine symbol kind
                if symbol_type == 'functions':
                    kind = "function"
                elif symbol_type == 'interfaces':
                    kind = "interface"
                elif symbol_type == 'structs':
                    kind = "struct"
                elif symbol_type == 'types':
                    kind = "type"
                elif symbol_type == 'constants':
                    kind = "constant"
                elif symbol_type == 'variables':
                    kind = "variable"
                else:
                    kind = "unknown"
                
                # Store symbol in SQLite if available
                if self._sqlite_store and file_id:
                    symbol_id = self._sqlite_store.store_symbol(
                        file_id,
                        name,
                        kind,
                        line,
                        line + 1,  # End line approximation
                        signature=signature
                    )
                    # Add to fuzzy indexer with metadata
                    self._indexer.add_symbol(
                        name, 
                        str(path), 
                        line,
                        {"symbol_id": symbol_id, "file_id": file_id}
                    )

                symbols.append({
                    "symbol": name,
                    "kind": kind,
                    "signature": signature,
                    "line": line,
                    "span": (line, line + 1),
                })
        
        return {
            "file": str(path), 
            "symbols": symbols, 
            "language": self.lang,
            "package": parsed_symbols.get('package'),
            "imports": parsed_symbols.get('imports', [])
        }

    def _parse_go_mod(self, path: Path, content: str, file_id: Optional[int]) -> IndexShard:
        """Parse go.mod file for module and dependency information."""
        symbols = []
        lines = content.split('\n')
        
        # Parse module declaration
        module_pattern = re.compile(r'^module\s+(.+)$')
        require_pattern = re.compile(r'^\s*([^\s]+)\s+(.+)$')
        
        in_require_block = False
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            # Module declaration
            module_match = module_pattern.match(line)
            if module_match:
                module_name = module_match.group(1)
                symbols.append({
                    "symbol": module_name,
                    "kind": "module",
                    "signature": f"module {module_name}",
                    "line": line_num,
                    "span": (line_num, line_num),
                })
                
                if self._sqlite_store and file_id:
                    symbol_id = self._sqlite_store.store_symbol(
                        file_id,
                        module_name,
                        "module",
                        line_num,
                        line_num,
                        signature=f"module {module_name}"
                    )
                    self._indexer.add_symbol(
                        module_name, 
                        str(path), 
                        line_num,
                        {"symbol_id": symbol_id, "file_id": file_id}
                    )
            
            # Require block
            if line.startswith('require'):
                in_require_block = True
                continue
            elif line == ')':
                in_require_block = False
                continue
            elif in_require_block or line.startswith('require '):
                # Parse dependency
                clean_line = line.replace('require ', '').strip()
                require_match = require_pattern.match(clean_line)
                if require_match:
                    dep_name = require_match.group(1)
                    dep_version = require_match.group(2)
                    symbols.append({
                        "symbol": dep_name,
                        "kind": "dependency",
                        "signature": f"require {dep_name} {dep_version}",
                        "line": line_num,
                        "span": (line_num, line_num),
                    })
                    
                    if self._sqlite_store and file_id:
                        symbol_id = self._sqlite_store.store_symbol(
                            file_id,
                            dep_name,
                            "dependency",
                            line_num,
                            line_num,
                            signature=f"require {dep_name} {dep_version}"
                        )
                        self._indexer.add_symbol(
                            dep_name, 
                            str(path), 
                            line_num,
                            {"symbol_id": symbol_id, "file_id": file_id}
                        )
        
        return {"file": str(path), "symbols": symbols, "language": "go-mod"}

    def getDefinition(self, symbol: str) -> SymbolDef | None:
        """Get definition location for a Go symbol."""
        for path in Path(".").rglob("*.go"):
            try:
                content = path.read_text()
                parsed_symbols = self._parser.parse_go_file(content)
                
                # Search through all symbol types
                for symbol_type, symbol_list in parsed_symbols.items():
                    if symbol_type in ['package', 'imports']:
                        continue
                    
                    for symbol_data in symbol_list:
                        if symbol_data['name'] == symbol:
                            return {
                                "symbol": symbol,
                                "kind": symbol_type.rstrip('s'),  # Remove plural
                                "language": self.lang,
                                "signature": symbol_data['signature'],
                                "doc": "",  # Go doc extraction would need more sophisticated parsing
                                "defined_in": str(path),
                                "line": symbol_data['line'],
                                "span": (symbol_data['line'], symbol_data['line'] + 1),
                            }
            except Exception:
                continue
        return None

    def findReferences(self, symbol: str) -> List[Reference]:
        """Find references to a Go symbol."""
        refs: List[Reference] = []
        seen: set[tuple[str, int]] = set()
        
        # Simple text-based reference finding
        symbol_pattern = re.compile(r'\b' + re.escape(symbol) + r'\b')
        
        for path in Path(".").rglob("*.go"):
            try:
                content = path.read_text()
                lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    if symbol_pattern.search(line):
                        key = (str(path), line_num)
                        if key not in seen:
                            refs.append(Reference(file=str(path), line=line_num))
                            seen.add(key)
            except Exception:
                continue
        
        return refs

    def search(self, query: str, opts: SearchOpts | None = None) -> List[SearchResult]:
        """Search for Go symbols and code patterns."""
        limit = 20
        if opts and "limit" in opts:
            limit = opts["limit"]
        if opts and opts.get("semantic"):
            return []
        return self._indexer.search(query, limit=limit)
    
    def get_indexed_count(self) -> int:
        """Return the number of indexed files."""
        stats = self._indexer.get_stats()
        return stats.get('files', 0)