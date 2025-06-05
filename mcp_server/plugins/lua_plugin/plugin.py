"""
Comprehensive Lua language plugin with advanced features.

Supports:
- Functions (global, local, anonymous, method definitions)
- Tables (constructors, metatables, class simulations)
- Modules (require statements, module definitions, LuaRocks)
- Coroutines
- Love2D game framework patterns
- OpenResty/Nginx Lua patterns
- Object-oriented patterns
- Multiple Lua versions (5.1, 5.2, 5.3, 5.4, LuaJIT)
"""

from typing import Dict, List, Optional, Any
import re
import hashlib
from pathlib import Path

from ...plugin_base import IPlugin, IndexShard, SymbolDef, Reference, SearchResult, SearchOpts
from ...storage.sqlite_store import SQLiteStore
from ...utils.fuzzy_indexer import FuzzyIndexer


class LuaParser:
    """Enhanced parser for Lua source files with comprehensive pattern support."""
    
    def __init__(self):
        # Core function patterns
        self.function_patterns = [
            # Global functions
            re.compile(r'^function\s+(\w+)\s*\((.*?)\)', re.MULTILINE),
            # Local functions
            re.compile(r'^local\s+function\s+(\w+)\s*\((.*?)\)', re.MULTILINE),
            # Function assignments
            re.compile(r'^(?:local\s+)?(\w+)\s*=\s*function\s*\((.*?)\)', re.MULTILINE),
            # Method definitions with colon
            re.compile(r'^function\s+(\w+):(\w+)\s*\((.*?)\)', re.MULTILINE),
            # Method assignments with dot
            re.compile(r'^(\w+)\.(\w+)\s*=\s*function\s*\((.*?)\)', re.MULTILINE),
        ]
        
        # Class/table patterns
        self.class_patterns = [
            # Table constructor as class
            re.compile(r'^local\s+(\w+)\s*=\s*\{', re.MULTILINE),
            # Metatable pattern
            re.compile(r'setmetatable\s*\(\s*(\w+)\s*,', re.MULTILINE),
            # Class library patterns
            re.compile(r'^local\s+(\w+)\s*=\s*(?:class|Class)\s*\(', re.MULTILINE),
        ]
        
        # Variable patterns
        self.variable_patterns = [
            # Local variables
            re.compile(r'^local\s+((?:\w+\s*,\s*)*\w+)(?:\s*=\s*(.+?))?$', re.MULTILINE),
            # Global constants (uppercase)
            re.compile(r'^([A-Z][A-Z0-9_]*)\s*=\s*(.+?)$', re.MULTILINE),
        ]
        
        # Module patterns
        self.module_patterns = [
            # Require with assignment
            re.compile(r'^(?:local\s+)?(\w+)\s*=\s*require\s*[\(\s]*["\']([^"\']+)["\']', re.MULTILINE),
            # Standalone require
            re.compile(r'^require\s*[\(\s]*["\']([^"\']+)["\']', re.MULTILINE),
            # Module definition
            re.compile(r'^module\s*\(\s*["\']([^"\']+)["\']', re.MULTILINE),
        ]
        
        # Special patterns
        self.coroutine_pattern = re.compile(r'^(?:local\s+)?(\w+)\s*=\s*coroutine\.(?:create|wrap)\s*\(', re.MULTILINE)
        self.metatable_pattern = re.compile(r'setmetatable\s*\(\s*(?:\w+|\{[^}]*\})\s*,\s*(\w+)\s*\)')
        self.love2d_pattern = re.compile(r'^function\s+(love\.(?:\w+\.)*\w+)\s*\(', re.MULTILINE)
        self.field_pattern = re.compile(r'^(\w+)\.(\w+)\s*=\s*(?!function)(.+?)$', re.MULTILINE)
        
    def parse_lua_file(self, content: str) -> Dict[str, List[Dict[str, Any]]]:
        """Parse Lua file and extract all symbols."""
        symbols = {
            'functions': [],
            'classes': [],
            'variables': [],
            'modules': [],
            'methods': [],
            'fields': [],
            'coroutines': [],
            'constants': []
        }
        
        lines = content.splitlines()
        
        # Extract functions
        for pattern in self.function_patterns[:3]:  # First 3 are regular functions
            for match in pattern.finditer(content):
                line_num = content[:match.start()].count('\n') + 1
                name = match.group(1)
                params = match.group(2) if match.lastindex >= 2 else ""
                
                # Check if it's a coroutine by looking at the current match context
                is_coroutine = False
                if line_num <= len(lines):
                    # Check if this function is being assigned to a coroutine.create/wrap
                    current_line = lines[line_num - 1]
                    is_coroutine = bool(self.coroutine_pattern.search(current_line))
                
                symbols['coroutines' if is_coroutine else 'functions'].append({
                    'name': name,
                    'line': line_num,
                    'signature': f"function {name}({params})",
                    'params': params,
                    'type': 'coroutine' if is_coroutine else 'function'
                })
        
        # Extract methods (colon syntax)
        pattern = self.function_patterns[3]  # Colon method pattern
        for match in pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            class_name = match.group(1)
            method_name = match.group(2)
            params = match.group(3)
            
            symbols['methods'].append({
                'name': method_name,
                'class': class_name,
                'line': line_num,
                'signature': f"function {class_name}:{method_name}({params})",
                'params': params
            })
        
        # Extract method assignments (dot syntax)
        pattern = self.function_patterns[4]  # Dot method pattern
        for match in pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            class_name = match.group(1)
            method_name = match.group(2)
            params = match.group(3)
            
            symbols['methods'].append({
                'name': method_name,
                'class': class_name,
                'line': line_num,
                'signature': f"{class_name}.{method_name} = function({params})",
                'params': params
            })
        
        # Extract classes/tables
        for pattern in self.class_patterns:
            for match in pattern.finditer(content):
                line_num = content[:match.start()].count('\n') + 1
                name = match.group(1)
                
                # Check if it has a metatable (either as target or as metatable)
                has_metatable = bool(
                    re.search(rf'setmetatable\s*\(\s*(?:\w+|\{{[^}}]*\}})\s*,\s*{re.escape(name)}\s*\)', content) or
                    re.search(rf'{re.escape(name)}\.__index\s*=\s*{re.escape(name)}', content)
                )
                
                symbols['classes'].append({
                    'name': name,
                    'line': line_num,
                    'signature': lines[line_num - 1].strip() if line_num <= len(lines) else f"local {name} = {{}}",
                    'has_metatable': has_metatable
                })
        
        # Extract variables
        for match in self.variable_patterns[0].finditer(content):  # Local variables
            line_num = content[:match.start()].count('\n') + 1
            var_names = match.group(1)
            value = match.group(2) if match.lastindex >= 2 else None
            
            # Split multiple variable declarations
            for var_name in re.split(r'\s*,\s*', var_names):
                var_name = var_name.strip()
                if var_name and not any(var_name == s['name'] for s in symbols['functions'] + symbols['classes']):
                    symbols['variables'].append({
                        'name': var_name,
                        'line': line_num,
                        'signature': lines[line_num - 1].strip() if line_num <= len(lines) else f"local {var_name}",
                        'value': value
                    })
        
        # Extract constants (global uppercase)
        for match in self.variable_patterns[1].finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            name = match.group(1)
            value = match.group(2)
            
            symbols['constants'].append({
                'name': name,
                'line': line_num,
                'signature': f"{name} = {value}",
                'value': value
            })
        
        # Extract modules
        for pattern in self.module_patterns[:2]:  # Require patterns
            for match in pattern.finditer(content):
                line_num = content[:match.start()].count('\n') + 1
                if match.lastindex >= 2:  # Assigned require
                    var_name = match.group(1)
                    module_path = match.group(2)
                else:  # Standalone require
                    var_name = match.group(1).split('.')[-1]  # Use last part of module path
                    module_path = match.group(1)
                
                symbols['modules'].append({
                    'name': var_name,
                    'line': line_num,
                    'signature': f"require '{module_path}'",
                    'module_path': module_path
                })
        
        # Extract Love2D callbacks
        for match in self.love2d_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            name = match.group(1)
            
            symbols['functions'].append({
                'name': name,
                'line': line_num,
                'signature': lines[line_num - 1].strip() if line_num <= len(lines) else f"function {name}()",
                'framework': 'love2d'
            })
        
        # Extract fields
        for match in self.field_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            table_name = match.group(1)
            field_name = match.group(2)
            value = match.group(3)
            
            symbols['fields'].append({
                'name': field_name,
                'table': table_name,
                'line': line_num,
                'signature': f"{table_name}.{field_name} = {value}",
                'value': value
            })
        
        # Extract coroutines specifically
        for match in self.coroutine_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            name = match.group(1)
            
            # Don't add if already detected as a function
            if not any(f['name'] == name for f in symbols['functions'] + symbols['coroutines']):
                symbols['coroutines'].append({
                    'name': name,
                    'line': line_num,
                    'signature': lines[line_num - 1].strip() if line_num <= len(lines) else f"{name} = coroutine.create(...)",
                    'type': 'coroutine'
                })
        
        return symbols


class Plugin(IPlugin):
    """Comprehensive Lua plugin with advanced pattern recognition."""
    
    lang = "lua"

    def __init__(self, sqlite_store: Optional[SQLiteStore] = None) -> None:
        """Initialize the Lua plugin."""
        self._parser = LuaParser()
        self._indexer = FuzzyIndexer(sqlite_store=sqlite_store)
        self._sqlite_store = sqlite_store
        self._repository_id = None
        
        # Lua-specific configuration
        self.lua_version = "5.4"  # Default to latest
        self._frameworks_cache = None  # Lazy detection
        
        # Create or get repository if SQLite is enabled
        if self._sqlite_store:
            self._repository_id = self._sqlite_store.create_repository(
                str(Path.cwd()), 
                Path.cwd().name,
                {"language": "lua"}
            )
        
        self._preindex()

    def _preindex(self) -> None:
        """Pre-index all Lua files in the current directory."""
        for path in Path(".").rglob("*.lua"):
            try:
                text = path.read_text(encoding='utf-8')
                self._indexer.add_file(str(path), text)
            except Exception:
                continue

    @property
    def frameworks(self) -> Dict[str, bool]:
        """Detect frameworks lazily."""
        if self._frameworks_cache is None:
            self._frameworks_cache = {
                "love2d": self._detect_love2d(),
                "openresty": self._detect_openresty(),
                "luajit": self._detect_luajit()
            }
        return self._frameworks_cache

    def supports(self, path: str | Path) -> bool:
        """Return True if file extension matches Lua files."""
        path_obj = Path(path) if isinstance(path, str) else path
        return path_obj.suffix in [".lua", ".rockspec"] or path_obj.name == ".luacheckrc"

    def indexFile(self, path: str | Path, content: str) -> IndexShard:
        """Index a Lua file and extract symbols."""
        if isinstance(path, str):
            path = Path(path)
        
        # Handle .rockspec files specially
        if path.suffix == ".rockspec":
            return self._index_rockspec(path, content)
        
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
                # Path is not relative to cwd, use absolute path
                relative_path = str(path)
                
            file_id = self._sqlite_store.store_file(
                self._repository_id,
                str(path),
                relative_path,
                language="lua",
                size=len(content),
                hash=file_hash
            )
        
        # Parse the Lua file
        parsed_symbols = self._parser.parse_lua_file(content)
        
        # Convert to IndexShard format
        symbols = []
        
        # Process all symbol types
        for symbol_type, symbol_list in parsed_symbols.items():
            if symbol_type == 'methods':
                # Methods are special - they have a class scope
                for symbol_data in symbol_list:
                    symbol_entry = {
                        "symbol": symbol_data['name'],
                        "kind": "method",
                        "signature": symbol_data['signature'],
                        "line": symbol_data['line'],
                        "span": (symbol_data['line'], symbol_data['line']),
                        "scope": symbol_data.get('class', ''),
                        "modifiers": []
                    }
                    
                    # Add framework modifiers
                    if 'framework' in symbol_data:
                        symbol_entry['modifiers'].append(symbol_data['framework'])
                    
                    symbols.append(symbol_entry)
                    
                    # Store in SQLite
                    if self._sqlite_store and file_id:
                        symbol_id = self._sqlite_store.store_symbol(
                            file_id,
                            symbol_data['name'],
                            "method",
                            symbol_data['line'],
                            symbol_data['line'],
                            signature=symbol_data['signature'],
                            scope=symbol_data.get('class', '')
                        )
                        
                        # Add to fuzzy indexer with metadata
                        self._indexer.add_symbol(
                            symbol_data['name'],
                            str(path),
                            symbol_data['line'],
                            {"symbol_id": symbol_id, "file_id": file_id}
                        )
            
            elif symbol_type == 'fields':
                # Fields have table scope
                for symbol_data in symbol_list:
                    symbol_entry = {
                        "symbol": symbol_data['name'],
                        "kind": "field",
                        "signature": symbol_data['signature'],
                        "line": symbol_data['line'],
                        "span": (symbol_data['line'], symbol_data['line']),
                        "scope": symbol_data.get('table', ''),
                        "modifiers": []
                    }
                    symbols.append(symbol_entry)
                    
                    # Store in SQLite
                    if self._sqlite_store and file_id:
                        symbol_id = self._sqlite_store.store_symbol(
                            file_id,
                            symbol_data['name'],
                            "field",
                            symbol_data['line'],
                            symbol_data['line'],
                            signature=symbol_data['signature'],
                            scope=symbol_data.get('table', '')
                        )
                        
                        self._indexer.add_symbol(
                            symbol_data['name'],
                            str(path),
                            symbol_data['line'],
                            {"symbol_id": symbol_id, "file_id": file_id}
                        )
            
            else:
                # Regular symbols
                kind_map = {
                    'functions': 'function',
                    'classes': 'class',
                    'variables': 'variable',
                    'modules': 'module',
                    'coroutines': 'function',  # Coroutines are special functions
                    'constants': 'constant'
                }
                
                for symbol_data in symbol_list:
                    kind = kind_map.get(symbol_type, symbol_type.rstrip('s'))
                    
                    symbol_entry = {
                        "symbol": symbol_data['name'],
                        "kind": kind,
                        "signature": symbol_data['signature'],
                        "line": symbol_data['line'],
                        "span": (symbol_data['line'], symbol_data['line']),
                        "modifiers": []
                    }
                    
                    # Add special modifiers
                    if symbol_type == 'coroutines':
                        symbol_entry['modifiers'].append('coroutine')
                    if symbol_data.get('has_metatable') or (symbol_type == 'classes' and symbol_data.get('has_metatable')):
                        symbol_entry['modifiers'].append('metatable')
                    if 'framework' in symbol_data:
                        symbol_entry['modifiers'].append(symbol_data['framework'])
                    
                    # Add metadata
                    if 'module_path' in symbol_data:
                        symbol_entry['metadata'] = {"module_path": symbol_data['module_path']}
                    
                    symbols.append(symbol_entry)
                    
                    # Store in SQLite
                    if self._sqlite_store and file_id:
                        symbol_id = self._sqlite_store.store_symbol(
                            file_id,
                            symbol_data['name'],
                            kind,
                            symbol_data['line'],
                            symbol_data['line'],
                            signature=symbol_data['signature']
                        )
                        
                        # Add to fuzzy indexer with metadata
                        self._indexer.add_symbol(
                            symbol_data['name'],
                            str(path),
                            symbol_data['line'],
                            {"symbol_id": symbol_id, "file_id": file_id}
                        )
        
        return {"file": str(path), "symbols": symbols, "language": "lua"}

    def _index_rockspec(self, path: Path, content: str) -> IndexShard:
        """Parse and index .rockspec files."""
        symbols = []
        
        # Extract package name
        package_match = re.search(r'package\s*=\s*["\']([^"\']+)["\']', content)
        if package_match:
            line_num = content[:package_match.start()].count('\n') + 1
            symbols.append({
                "symbol": package_match.group(1),
                "kind": "module",
                "signature": "LuaRocks package",
                "line": line_num,
                "span": (line_num, line_num),
                "metadata": {"file_type": "rockspec"}
            })
            
            if self._sqlite_store and self._repository_id:
                file_id = self._sqlite_store.store_file(
                    self._repository_id,
                    str(path),
                    str(path),
                    language="rockspec",
                    size=len(content),
                    hash=hashlib.sha256(content.encode('utf-8')).hexdigest()
                )
                
                symbol_id = self._sqlite_store.store_symbol(
                    file_id,
                    package_match.group(1),
                    "module",
                    line_num,
                    line_num,
                    signature="LuaRocks package"
                )
                
                self._indexer.add_symbol(
                    package_match.group(1),
                    str(path),
                    line_num,
                    {"symbol_id": symbol_id, "file_id": file_id}
                )
        
        # Extract dependencies
        deps_match = re.search(r'dependencies\s*=\s*\{([^}]+)\}', content, re.DOTALL)
        if deps_match:
            deps_content = deps_match.group(1)
            for dep_match in re.finditer(r'["\']([^"\']+)["\']', deps_content):
                dep_name = dep_match.group(1)
                line_num = content[:dep_match.start()].count('\n') + 1
                
                symbols.append({
                    "symbol": dep_name,
                    "kind": "import",
                    "signature": f"dependency: {dep_name}",
                    "line": line_num,
                    "span": (line_num, line_num),
                    "metadata": {"dependency": True}
                })
                
                if self._sqlite_store and file_id:
                    symbol_id = self._sqlite_store.store_symbol(
                        file_id,
                        dep_name,
                        "import",
                        line_num,
                        line_num,
                        signature=f"dependency: {dep_name}"
                    )
                    
                    self._indexer.add_symbol(
                        dep_name,
                        str(path),
                        line_num,
                        {"symbol_id": symbol_id, "file_id": file_id}
                    )
        
        return {"file": str(path), "symbols": symbols, "language": "rockspec"}

    def getDefinition(self, symbol: str) -> SymbolDef | None:
        """Get definition location for a Lua symbol."""
        # First try SQLite store
        if self._sqlite_store:
            result = self._sqlite_store.find_symbol_definition(symbol, "lua")
            if result:
                return {
                    "symbol": result["name"],
                    "kind": result["kind"],
                    "language": "lua",
                    "signature": result.get("signature", ""),
                    "doc": result.get("docstring"),
                    "defined_in": result["file_path"],
                    "line": result["start_line"],
                    "span": (result["start_line"], result["end_line"])
                }
        
        # Fallback to file search
        for path in Path(".").rglob("*.lua"):
            try:
                content = path.read_text(encoding='utf-8')
                parsed_symbols = self._parser.parse_lua_file(content)
                
                # Search through all symbol types
                for symbol_type, symbol_list in parsed_symbols.items():
                    for symbol_data in symbol_list:
                        if symbol_data['name'] == symbol:
                            return {
                                "symbol": symbol,
                                "kind": symbol_type.rstrip('s'),  # Remove plural
                                "language": self.lang,
                                "signature": symbol_data['signature'],
                                "doc": "",  # LuaDoc extraction would need more sophisticated parsing
                                "defined_in": str(path),
                                "line": symbol_data['line'],
                                "span": (symbol_data['line'], symbol_data['line'] + 1),
                            }
            except Exception:
                continue
        return None

    def findReferences(self, symbol: str) -> List[Reference]:
        """Find references to a Lua symbol."""
        # First try SQLite store
        if self._sqlite_store:
            results = self._sqlite_store.find_symbol_references(symbol, "lua")
            if results:
                return [Reference(file=r["file"], line=r["line"]) for r in results]
        
        # Fallback to text search
        refs: List[Reference] = []
        seen: set[tuple[str, int]] = set()
        
        # Simple text-based reference finding
        symbol_pattern = re.compile(r'\b' + re.escape(symbol) + r'\b')
        
        for path in Path(".").rglob("*.lua"):
            try:
                content = path.read_text(encoding='utf-8')
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
        """Search for Lua symbols and code patterns."""
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

    def _detect_love2d(self) -> bool:
        """Detect if this is a Love2D project."""
        # Check for main.lua or conf.lua in project root
        for pattern in ["main.lua", "conf.lua", "**/main.lua", "**/conf.lua"]:
            if list(Path(".").glob(pattern)):
                return True
        return False
    
    def _detect_openresty(self) -> bool:
        """Detect if this is an OpenResty/Nginx Lua project."""
        # Check for nginx.conf or resty modules
        for pattern in ["nginx.conf", "**/nginx.conf", "**/resty/**/*.lua"]:
            if list(Path(".").glob(pattern)):
                return True
        return False
    
    def _detect_luajit(self) -> bool:
        """Detect if LuaJIT is being used."""
        # Check for LuaJIT specific files or FFI usage
        for pattern in ["**/*.lua"]:
            for file in Path(".").glob(pattern):
                try:
                    content = file.read_text(encoding='utf-8')
                    if 'require("ffi")' in content or 'require "ffi"' in content:
                        return True
                except Exception:
                    continue
        return False
    
    def get_plugin_info(self) -> Dict[str, Any]:
        """Get Lua plugin information."""
        return {
            "name": self.__class__.__name__,
            "language": self.lang,
            "extensions": [".lua", ".rockspec", ".luacheckrc"],
            "lua_version": self.lua_version,
            "frameworks": self.frameworks,
            "features": [
                "functions", "methods", "tables", "metatables",
                "modules", "coroutines", "love2d", "openresty"
            ],
            "indexed_files": self.get_indexed_count()
        }