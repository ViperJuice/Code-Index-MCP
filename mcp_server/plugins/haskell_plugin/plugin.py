"""Comprehensive Haskell language plugin with advanced features.

This plugin provides comprehensive support for Haskell code analysis including:
- Type signatures and type class detection
- Data type and newtype declarations
- Pattern matching analysis
- Module imports and exports
- Language pragmas ({-# LANGUAGE ... #-})
- Literate Haskell support (.lhs files)
- Cabal/Stack project file parsing
"""

from __future__ import annotations

import re
import json
import hashlib
from pathlib import Path
from typing import Optional, List, Dict, Any, Set, Tuple
from dataclasses import dataclass, field

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
from ...core.logging import get_logger


@dataclass
class HaskellSymbol:
    """Represents a Haskell symbol with its metadata."""
    name: str
    kind: str
    line: int
    signature: Optional[str] = None
    type_signature: Optional[str] = None
    end_line: Optional[int] = None
    docstring: Optional[str] = None
    context: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class HaskellTreeSitterWrapper:
    """Enhanced Haskell parser with comprehensive pattern support."""
    
    def __init__(self):
        # Type signatures (can span multiple lines)
        self.type_sig_pattern = re.compile(
            r'^\s*(\w+(?:\s*,\s*\w+)*)\s*::\s*(.+?)(?=\n(?:\s*\w+\s*::|^\s*\w+\s*[^:]*=|^\s*$))',
            re.MULTILINE | re.DOTALL
        )
        
        # Function definitions (including guards and pattern matching)
        self.function_def_pattern = re.compile(
            r'^\s*(\w+)\s+(?:[^=\n]*?)(?:\s*=|\s*\|)',
            re.MULTILINE
        )
        
        # Data type declarations (including GADTs)
        self.data_type_pattern = re.compile(
            r'^\s*data\s+(\w+)(?:\s+[^=\n]*)?(?:\s*=|\s+where)',
            re.MULTILINE
        )
        
        # Newtype declarations
        self.newtype_pattern = re.compile(
            r'^\s*newtype\s+(\w+)(?:\s+[^=\n]*)?(?:\s*=)',
            re.MULTILINE
        )
        
        # Type synonyms/aliases
        self.type_alias_pattern = re.compile(
            r'^\s*type\s+(?:family\s+)?(\w+)(?:\s+[^=\n]*)?(?:\s*=)?',
            re.MULTILINE
        )
        
        # Type class declarations
        self.type_class_pattern = re.compile(
            r'^\s*class\s+(?:\([^)]*\)\s*=>\s*)?(\w+)',
            re.MULTILINE
        )
        
        # Instance declarations
        self.instance_pattern = re.compile(
            r'^\s*instance\s+(?:\([^)]*\)\s*=>\s*)?(?:.*?\s+)?(\w+)\s+',
            re.MULTILINE
        )
        
        # Module declaration with exports
        self.module_pattern = re.compile(
            r'^\s*module\s+(\S+)(?:\s*\(([^)]*)\))?\s+where',
            re.MULTILINE | re.DOTALL
        )
        
        # Import statements
        self.import_pattern = re.compile(
            r'^\s*import\s+(?:(qualified)\s+)?(\S+)(?:\s+as\s+(\w+))?(?:\s+(hiding))?\s*(?:\(([^)]*)\))?',
            re.MULTILINE
        )
        
        # Language pragmas
        self.pragma_pattern = re.compile(
            r'^\s*\{-#\s*(LANGUAGE|OPTIONS_GHC|INLINE|NOINLINE|SPECIALIZE|PRAGMA)\s+([^#]+)#-\}',
            re.MULTILINE
        )
        
        # Pattern bindings and named patterns
        self.pattern_binding_pattern = re.compile(
            r'^\s*(\w+)\s*@\s*[(\[]',
            re.MULTILINE
        )
        
        # Infix operators and fixity declarations
        self.infix_op_pattern = re.compile(
            r'^\s*(?:infixl|infixr|infix)\s+(\d+)\s+(.+?)$',
            re.MULTILINE
        )
        
        # Record field declarations
        self.record_field_pattern = re.compile(
            r'^\s*(\w+)\s*::\s*([^,}\n]+)',
            re.MULTILINE
        )
        
        # Deriving clauses
        self.deriving_pattern = re.compile(
            r'^\s*deriving\s+(?:\(([^)]+)\)|(\w+))',
            re.MULTILINE
        )
        
        # Type family instances
        self.type_family_instance_pattern = re.compile(
            r'^\s*type\s+instance\s+(\w+)',
            re.MULTILINE
        )
        
        # Data family instances
        self.data_family_instance_pattern = re.compile(
            r'^\s*data\s+instance\s+(\w+)',
            re.MULTILINE
        )
    
    def parse_haskell_file(self, content: str, is_literate: bool = False) -> Dict[str, Any]:
        """Parse Haskell file content and extract comprehensive symbol information."""
        if is_literate:
            content = self._extract_code_from_literate(content)
        
        symbols = {
            'module': None,
            'exports': [],
            'pragmas': [],
            'imports': [],
            'functions': [],
            'types': [],
            'classes': [],
            'instances': [],
            'operators': [],
            'type_signatures': {},
            'deriving': []
        }
        
        # Extract module declaration
        module_match = self.module_pattern.search(content)
        if module_match:
            symbols['module'] = {
                'name': module_match.group(1),
                'exports': self._parse_export_list(module_match.group(2)) if module_match.group(2) else None,
                'line': content[:module_match.start()].count('\n') + 1
            }
        
        # Extract language pragmas
        for match in self.pragma_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            pragma_type = match.group(1)
            pragma_content = match.group(2).strip()
            
            if pragma_type == 'LANGUAGE':
                extensions = [ext.strip() for ext in pragma_content.split(',')]
                for ext in extensions:
                    symbols['pragmas'].append({
                        'type': 'LANGUAGE',
                        'content': ext,
                        'line': line_num
                    })
            else:
                symbols['pragmas'].append({
                    'type': pragma_type,
                    'content': pragma_content,
                    'line': line_num
                })
        
        # Extract imports
        for match in self.import_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            import_info = {
                'module': match.group(2),
                'qualified': bool(match.group(1)),
                'alias': match.group(3),
                'hiding': bool(match.group(4)),
                'imports': self._parse_import_list(match.group(5)) if match.group(5) else None,
                'line': line_num,
                'signature': match.group(0).strip()
            }
            symbols['imports'].append(import_info)
        
        # Extract type signatures first (they come before function definitions)
        for match in self.type_sig_pattern.finditer(content):
            names = [n.strip() for n in match.group(1).split(',')]
            type_sig = match.group(2).strip()
            line_num = content[:match.start()].count('\n') + 1
            
            for name in names:
                symbols['type_signatures'][name] = {
                    'signature': f"{name} :: {type_sig}",
                    'type': type_sig,
                    'line': line_num
                }
        
        # Extract function definitions
        seen_functions = set()
        for match in self.function_def_pattern.finditer(content):
            func_name = match.group(1)
            if func_name not in seen_functions and not func_name[0].isupper():
                line_num = content[:match.start()].count('\n') + 1
                
                func_info = {
                    'name': func_name,
                    'line': line_num,
                    'signature': match.group(0).strip()
                }
                
                # Add type signature if available
                if func_name in symbols['type_signatures']:
                    func_info['type_signature'] = symbols['type_signatures'][func_name]['signature']
                    func_info['type'] = symbols['type_signatures'][func_name]['type']
                    # Use type signature line if it comes before the function
                    if symbols['type_signatures'][func_name]['line'] < line_num:
                        func_info['line'] = symbols['type_signatures'][func_name]['line']
                
                symbols['functions'].append(func_info)
                seen_functions.add(func_name)
        
        # Extract data types
        for match in self.data_type_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            type_name = match.group(1)
            
            # Extract constructors if it's not a GADT
            if '=' in match.group(0):
                constructors = self._extract_constructors(content, match.end())
            else:
                constructors = []
            
            symbols['types'].append({
                'name': type_name,
                'kind': 'data',
                'line': line_num,
                'signature': match.group(0).strip(),
                'constructors': constructors
            })
        
        # Extract newtypes
        for match in self.newtype_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            symbols['types'].append({
                'name': match.group(1),
                'kind': 'newtype',
                'line': line_num,
                'signature': match.group(0).strip()
            })
        
        # Extract type aliases
        for match in self.type_alias_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            type_name = match.group(1)
            kind = 'type_family' if 'family' in match.group(0) else 'type_alias'
            
            symbols['types'].append({
                'name': type_name,
                'kind': kind,
                'line': line_num,
                'signature': match.group(0).strip()
            })
        
        # Extract type classes
        for match in self.type_class_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            class_name = match.group(1)
            
            # Extract class methods
            methods = self._extract_class_methods(content, match.end())
            
            symbols['classes'].append({
                'name': class_name,
                'line': line_num,
                'signature': match.group(0).strip(),
                'methods': methods
            })
        
        # Extract instances
        for match in self.instance_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            # Try to extract the type class being instantiated
            instance_text = match.group(0)
            class_name = match.group(1)
            
            symbols['instances'].append({
                'class': class_name,
                'line': line_num,
                'signature': instance_text.strip()
            })
        
        # Extract infix operators
        for match in self.infix_op_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            precedence = match.group(1)
            operators = match.group(2).strip().split()
            
            for op in operators:
                symbols['operators'].append({
                    'name': op,
                    'precedence': precedence,
                    'line': line_num,
                    'signature': match.group(0).strip()
                })
        
        # Extract type family instances
        for match in self.type_family_instance_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            symbols['instances'].append({
                'class': f"type {match.group(1)}",
                'line': line_num,
                'signature': match.group(0).strip(),
                'kind': 'type_family_instance'
            })
        
        # Extract data family instances
        for match in self.data_family_instance_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            symbols['instances'].append({
                'class': f"data {match.group(1)}",
                'line': line_num,
                'signature': match.group(0).strip(),
                'kind': 'data_family_instance'
            })
        
        return symbols
    
    def _extract_code_from_literate(self, content: str) -> str:
        """Extract code blocks from literate Haskell files."""
        lines = content.splitlines()
        code_lines = []
        in_code_block = False
        
        for line in lines:
            # Bird-style literate Haskell
            if line.startswith('> '):
                code_lines.append(line[2:])
            # LaTeX-style literate Haskell
            elif line.strip() == '\\begin{code}':
                in_code_block = True
            elif line.strip() == '\\end{code}':
                in_code_block = False
            elif in_code_block:
                code_lines.append(line)
        
        return '\n'.join(code_lines)
    
    def _parse_export_list(self, export_str: str) -> List[str]:
        """Parse module export list."""
        if not export_str:
            return []
        
        # Simple split by comma, handling nested parentheses
        exports = []
        current = []
        paren_depth = 0
        
        for char in export_str:
            if char == ',' and paren_depth == 0:
                exports.append(''.join(current).strip())
                current = []
            else:
                if char == '(':
                    paren_depth += 1
                elif char == ')':
                    paren_depth -= 1
                current.append(char)
        
        if current:
            exports.append(''.join(current).strip())
        
        return [e for e in exports if e]
    
    def _parse_import_list(self, import_str: str) -> List[str]:
        """Parse import list."""
        return self._parse_export_list(import_str)
    
    def _extract_constructors(self, content: str, start_pos: int) -> List[Dict[str, Any]]:
        """Extract data constructors from a data type declaration."""
        constructors = []
        
        # Find the end of the data declaration
        lines = content[start_pos:].split('\n')
        constructor_pattern = re.compile(r'^\s*\|?\s*(\w+)\s*(?:\{[^}]*\}|[^|]*)')
        
        for i, line in enumerate(lines):
            if i > 0 and re.match(r'^\s*(?:data|newtype|type|class|instance|import|\w+\s*::)', line):
                break
            
            match = constructor_pattern.match(line)
            if match:
                constructors.append({
                    'name': match.group(1),
                    'line': content[:start_pos].count('\n') + i + 1
                })
        
        return constructors
    
    def _extract_class_methods(self, content: str, start_pos: int) -> List[Dict[str, Any]]:
        """Extract method signatures from a type class."""
        methods = []
        lines = content[start_pos:].split('\n')
        method_pattern = re.compile(r'^\s*(\w+)\s*::\s*(.+?)$')
        
        in_class = True
        for i, line in enumerate(lines):
            # Check if we've left the class definition
            if re.match(r'^(?:data|newtype|type|class|instance|import|\w+\s*=)', line):
                break
            
            match = method_pattern.match(line)
            if match:
                methods.append({
                    'name': match.group(1),
                    'type': match.group(2).strip(),
                    'line': content[:start_pos].count('\n') + i + 1
                })
        
        return methods


class Plugin(IPlugin):
    """Comprehensive Haskell language plugin."""
    
    lang = "haskell"
    
    def __init__(self, sqlite_store: Optional[SQLiteStore] = None) -> None:
        self._parser = HaskellTreeSitterWrapper()
        self._indexer = FuzzyIndexer(sqlite_store=sqlite_store)
        self._sqlite_store = sqlite_store
        self._repository_id = None
        self.logger = get_logger(self.__class__.__name__)
        
        # Create or get repository if SQLite is enabled
        if self._sqlite_store:
            self._repository_id = self._sqlite_store.create_repository(
                str(Path.cwd()), 
                Path.cwd().name,
                {"language": "haskell"}
            )
        
        self._preindex()
    
    def _preindex(self) -> None:
        """Pre-index all Haskell files in the current directory."""
        extensions = [".hs", ".lhs", ".hsc"]
        for ext in extensions:
            for path in Path(".").rglob(f"*{ext}"):
                try:
                    text = path.read_text()
                    self._indexer.add_file(str(path), text)
                except Exception as e:
                    self.logger.warning(f"Failed to pre-index {path}: {e}")
                    continue
    
    def supports(self, path: str | Path) -> bool:
        """Return True if file extension matches Haskell files or project files."""
        path_obj = Path(path) if isinstance(path, str) else path
        
        # Haskell source files
        if path_obj.suffix.lower() in [".hs", ".lhs", ".hsc"]:
            return True
        
        # Cabal files
        if path_obj.suffix == ".cabal":
            return True
        
        # Stack files
        if path_obj.name in ["stack.yaml", "stack.yaml.lock", "package.yaml"]:
            return True
        
        return False
    
    def indexFile(self, path: str | Path, content: str) -> IndexShard:
        """Index a Haskell file and extract symbols."""
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
                language="haskell",
                size=len(content),
                hash=file_hash
            )
        
        # Handle special file types
        if path.suffix == ".cabal":
            return self._index_cabal_file(path, content, file_id)
        elif path.name in ["stack.yaml", "package.yaml"]:
            return self._index_stack_file(path, content, file_id)
        
        # Parse Haskell source files
        is_literate = path.suffix == ".lhs"
        parsed_symbols = self._parser.parse_haskell_file(content, is_literate)
        
        symbols: List[Dict[str, Any]] = []
        
        # Add module symbol
        if parsed_symbols['module']:
            mod = parsed_symbols['module']
            symbols.append({
                "symbol": mod['name'],
                "kind": "module",
                "signature": f"module {mod['name']}",
                "line": mod['line'],
                "span": (mod['line'], mod['line']),
                "metadata": {"exports": mod['exports']} if mod['exports'] else {}
            })
            
            if self._sqlite_store and file_id:
                symbol_id = self._sqlite_store.store_symbol(
                    file_id,
                    mod['name'],
                    "module",
                    mod['line'],
                    mod['line'],
                    signature=f"module {mod['name']}"
                )
                self._indexer.add_symbol(
                    mod['name'], 
                    str(path), 
                    mod['line'],
                    {"symbol_id": symbol_id, "file_id": file_id}
                )
        
        # Add import symbols
        for imp in parsed_symbols['imports']:
            symbols.append({
                "symbol": imp['module'],
                "kind": "import",
                "signature": imp['signature'],
                "line": imp['line'],
                "span": (imp['line'], imp['line']),
                "metadata": {
                    "qualified": imp['qualified'],
                    "alias": imp['alias'],
                    "hiding": imp['hiding']
                }
            })
            
            if self._sqlite_store and file_id:
                symbol_id = self._sqlite_store.store_symbol(
                    file_id,
                    imp['module'],
                    "import",
                    imp['line'],
                    imp['line'],
                    signature=imp['signature']
                )
                self._indexer.add_symbol(
                    imp['module'], 
                    str(path), 
                    imp['line'],
                    {"symbol_id": symbol_id, "file_id": file_id}
                )
        
        # Add function symbols
        for func in parsed_symbols['functions']:
            signature = func.get('type_signature', func['signature'])
            symbols.append({
                "symbol": func['name'],
                "kind": "function",
                "signature": signature,
                "line": func['line'],
                "span": (func['line'], func['line'] + 1),
                "metadata": {"has_type_signature": 'type_signature' in func}
            })
            
            if self._sqlite_store and file_id:
                symbol_id = self._sqlite_store.store_symbol(
                    file_id,
                    func['name'],
                    "function",
                    func['line'],
                    func['line'] + 1,
                    signature=signature
                )
                self._indexer.add_symbol(
                    func['name'], 
                    str(path), 
                    func['line'],
                    {"symbol_id": symbol_id, "file_id": file_id}
                )
        
        # Add type symbols
        for type_sym in parsed_symbols['types']:
            symbols.append({
                "symbol": type_sym['name'],
                "kind": type_sym['kind'],
                "signature": type_sym['signature'],
                "line": type_sym['line'],
                "span": (type_sym['line'], type_sym['line'] + 1),
                "metadata": {"constructors": type_sym.get('constructors', [])}
            })
            
            if self._sqlite_store and file_id:
                symbol_id = self._sqlite_store.store_symbol(
                    file_id,
                    type_sym['name'],
                    type_sym['kind'],
                    type_sym['line'],
                    type_sym['line'] + 1,
                    signature=type_sym['signature']
                )
                self._indexer.add_symbol(
                    type_sym['name'], 
                    str(path), 
                    type_sym['line'],
                    {"symbol_id": symbol_id, "file_id": file_id}
                )
        
        # Add class symbols
        for cls in parsed_symbols['classes']:
            symbols.append({
                "symbol": cls['name'],
                "kind": "class",
                "signature": cls['signature'],
                "line": cls['line'],
                "span": (cls['line'], cls['line'] + 1),
                "metadata": {"methods": cls.get('methods', [])}
            })
            
            if self._sqlite_store and file_id:
                symbol_id = self._sqlite_store.store_symbol(
                    file_id,
                    cls['name'],
                    "class",
                    cls['line'],
                    cls['line'] + 1,
                    signature=cls['signature']
                )
                self._indexer.add_symbol(
                    cls['name'], 
                    str(path), 
                    cls['line'],
                    {"symbol_id": symbol_id, "file_id": file_id}
                )
        
        # Add instance symbols
        for inst in parsed_symbols['instances']:
            symbols.append({
                "symbol": f"instance {inst['class']}",
                "kind": "instance",
                "signature": inst['signature'],
                "line": inst['line'],
                "span": (inst['line'], inst['line'] + 1),
                "metadata": {"kind": inst.get('kind', 'instance')}
            })
            
            if self._sqlite_store and file_id:
                symbol_id = self._sqlite_store.store_symbol(
                    file_id,
                    f"instance {inst['class']}",
                    "instance",
                    inst['line'],
                    inst['line'] + 1,
                    signature=inst['signature']
                )
                self._indexer.add_symbol(
                    f"instance {inst['class']}", 
                    str(path), 
                    inst['line'],
                    {"symbol_id": symbol_id, "file_id": file_id}
                )
        
        # Add operator symbols
        for op in parsed_symbols['operators']:
            symbols.append({
                "symbol": op['name'],
                "kind": "operator",
                "signature": op['signature'],
                "line": op['line'],
                "span": (op['line'], op['line']),
                "metadata": {"precedence": op['precedence']}
            })
            
            if self._sqlite_store and file_id:
                symbol_id = self._sqlite_store.store_symbol(
                    file_id,
                    op['name'],
                    "operator",
                    op['line'],
                    op['line'],
                    signature=op['signature']
                )
                self._indexer.add_symbol(
                    op['name'], 
                    str(path), 
                    op['line'],
                    {"symbol_id": symbol_id, "file_id": file_id}
                )
        
        return {
            "file": str(path), 
            "symbols": symbols, 
            "language": self.lang,
            "metadata": {
                "pragmas": parsed_symbols['pragmas'],
                "is_literate": is_literate
            }
        }
    
    def _index_cabal_file(self, path: Path, content: str, file_id: Optional[int]) -> IndexShard:
        """Index a Cabal project file."""
        symbols = []
        lines = content.splitlines()
        
        # Extract package name
        name_pattern = re.compile(r'^name:\s*(\S+)', re.MULTILINE | re.IGNORECASE)
        name_match = name_pattern.search(content)
        if name_match:
            line_num = content[:name_match.start()].count('\n') + 1
            pkg_name = name_match.group(1)
            symbols.append({
                "symbol": pkg_name,
                "kind": "package",
                "signature": name_match.group(0).strip(),
                "line": line_num,
                "span": (line_num, line_num)
            })
            
            if self._sqlite_store and file_id:
                symbol_id = self._sqlite_store.store_symbol(
                    file_id,
                    pkg_name,
                    "package",
                    line_num,
                    line_num,
                    signature=name_match.group(0).strip()
                )
                self._indexer.add_symbol(
                    pkg_name, 
                    str(path), 
                    line_num,
                    {"symbol_id": symbol_id, "file_id": file_id}
                )
        
        # Extract library, executable, test-suite, and benchmark sections
        section_pattern = re.compile(
            r'^(library|executable|test-suite|benchmark)\s*(\S*)',
            re.MULTILINE | re.IGNORECASE
        )
        for match in section_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            section_type = match.group(1).lower()
            section_name = match.group(2) or "(default)"
            
            symbols.append({
                "symbol": section_name,
                "kind": section_type,
                "signature": match.group(0).strip(),
                "line": line_num,
                "span": (line_num, line_num)
            })
            
            if self._sqlite_store and file_id:
                symbol_id = self._sqlite_store.store_symbol(
                    file_id,
                    section_name,
                    section_type,
                    line_num,
                    line_num,
                    signature=match.group(0).strip()
                )
                self._indexer.add_symbol(
                    section_name, 
                    str(path), 
                    line_num,
                    {"symbol_id": symbol_id, "file_id": file_id}
                )
        
        # Extract exposed modules
        exposed_modules_pattern = re.compile(
            r'^\s*exposed-modules:\s*(.+?)(?=^\s*\w+:|\Z)',
            re.MULTILINE | re.IGNORECASE | re.DOTALL
        )
        exposed_match = exposed_modules_pattern.search(content)
        if exposed_match:
            modules_text = exposed_match.group(1)
            modules = re.findall(r'(\S+)', modules_text)
            base_line = content[:exposed_match.start()].count('\n') + 1
            
            for i, module in enumerate(modules):
                if module and not module.endswith(','):
                    module = module.rstrip(',')
                    symbols.append({
                        "symbol": module,
                        "kind": "exposed-module",
                        "signature": f"exposed-modules: {module}",
                        "line": base_line + i,
                        "span": (base_line + i, base_line + i)
                    })
        
        # Extract dependencies
        build_depends_pattern = re.compile(
            r'^\s*build-depends:\s*(.+?)(?=^\s*\w+:|\Z)',
            re.MULTILINE | re.IGNORECASE | re.DOTALL
        )
        depends_match = build_depends_pattern.search(content)
        if depends_match:
            deps_text = depends_match.group(1)
            # Parse dependencies with version constraints
            dep_pattern = re.compile(r'([a-zA-Z0-9-]+)\s*(?:[><=]+\s*[\d.]+)?')
            deps = dep_pattern.findall(deps_text)
            base_line = content[:depends_match.start()].count('\n') + 1
            
            for dep in deps:
                if dep and dep not in ['', ',']:
                    symbols.append({
                        "symbol": dep,
                        "kind": "dependency",
                        "signature": f"dependency: {dep}",
                        "line": base_line,
                        "span": (base_line, base_line)
                    })
        
        return {
            "file": str(path),
            "symbols": symbols,
            "language": "cabal"
        }
    
    def _index_stack_file(self, path: Path, content: str, file_id: Optional[int]) -> IndexShard:
        """Index a Stack project file."""
        symbols = []
        
        # For stack.yaml
        if path.name == 'stack.yaml':
            # Extract resolver
            resolver_pattern = re.compile(r'^resolver:\s*(\S+)', re.MULTILINE)
            resolver_match = resolver_pattern.search(content)
            if resolver_match:
                line_num = content[:resolver_match.start()].count('\n') + 1
                resolver = resolver_match.group(1)
                symbols.append({
                    "symbol": resolver,
                    "kind": "resolver",
                    "signature": resolver_match.group(0).strip(),
                    "line": line_num,
                    "span": (line_num, line_num)
                })
                
                if self._sqlite_store and file_id:
                    symbol_id = self._sqlite_store.store_symbol(
                        file_id,
                        resolver,
                        "resolver",
                        line_num,
                        line_num,
                        signature=resolver_match.group(0).strip()
                    )
                    self._indexer.add_symbol(
                        resolver, 
                        str(path), 
                        line_num,
                        {"symbol_id": symbol_id, "file_id": file_id}
                    )
            
            # Extract packages
            packages_pattern = re.compile(
                r'^packages:\s*\n((?:\s*-\s*.+\n?)+)',
                re.MULTILINE
            )
            packages_match = packages_pattern.search(content)
            if packages_match:
                pkg_text = packages_match.group(1)
                pkg_lines = pkg_text.strip().split('\n')
                base_line = content[:packages_match.start()].count('\n') + 2
                
                for i, line in enumerate(pkg_lines):
                    pkg_match = re.match(r'\s*-\s*(.+)', line)
                    if pkg_match:
                        pkg_path = pkg_match.group(1).strip()
                        symbols.append({
                            "symbol": pkg_path,
                            "kind": "package",
                            "signature": f"package: {pkg_path}",
                            "line": base_line + i,
                            "span": (base_line + i, base_line + i)
                        })
        
        # For package.yaml (hpack)
        elif path.name == 'package.yaml':
            # Extract package name
            name_pattern = re.compile(r'^name:\s*(\S+)', re.MULTILINE)
            name_match = name_pattern.search(content)
            if name_match:
                line_num = content[:name_match.start()].count('\n') + 1
                pkg_name = name_match.group(1)
                symbols.append({
                    "symbol": pkg_name,
                    "kind": "package",
                    "signature": name_match.group(0).strip(),
                    "line": line_num,
                    "span": (line_num, line_num)
                })
                
                if self._sqlite_store and file_id:
                    symbol_id = self._sqlite_store.store_symbol(
                        file_id,
                        pkg_name,
                        "package",
                        line_num,
                        line_num,
                        signature=name_match.group(0).strip()
                    )
                    self._indexer.add_symbol(
                        pkg_name, 
                        str(path), 
                        line_num,
                        {"symbol_id": symbol_id, "file_id": file_id}
                    )
            
            # Extract executables
            exec_pattern = re.compile(r'^executables:\s*\n((?:\s{2}\w+:.*\n(?:\s{4}.*\n)*)+)', re.MULTILINE)
            exec_match = exec_pattern.search(content)
            if exec_match:
                exec_text = exec_match.group(1)
                exec_name_pattern = re.compile(r'^\s{2}(\w+):', re.MULTILINE)
                base_line = content[:exec_match.start()].count('\n') + 1
                
                for match in exec_name_pattern.finditer(exec_text):
                    exec_name = match.group(1)
                    line_offset = exec_text[:match.start()].count('\n')
                    symbols.append({
                        "symbol": exec_name,
                        "kind": "executable",
                        "signature": f"executable: {exec_name}",
                        "line": base_line + line_offset + 1,
                        "span": (base_line + line_offset + 1, base_line + line_offset + 1)
                    })
        
        return {
            "file": str(path),
            "symbols": symbols,
            "language": "yaml"
        }
    
    def getDefinition(self, symbol: str) -> SymbolDef | None:
        """Get definition location for a Haskell symbol."""
        # First try database lookup if available
        if self._sqlite_store:
            result = self._sqlite_store.find_symbol_definition(symbol, self.lang)
            if result:
                return {
                    "symbol": result["name"],
                    "kind": result["kind"],
                    "language": self.lang,
                    "signature": result.get("signature", ""),
                    "doc": result.get("docstring"),
                    "defined_in": result["file_path"],
                    "line": result["start_line"],
                    "span": (result["start_line"], result["end_line"])
                }
        
        # Fallback to file search
        extensions = [".hs", ".lhs", ".hsc"]
        for ext in extensions:
            for path in Path(".").rglob(f"*{ext}"):
                try:
                    content = path.read_text()
                    is_literate = path.suffix == ".lhs"
                    parsed_symbols = self._parser.parse_haskell_file(content, is_literate)
                    
                    # Search in functions
                    for func in parsed_symbols['functions']:
                        if func['name'] == symbol:
                            return {
                                "symbol": symbol,
                                "kind": "function",
                                "language": self.lang,
                                "signature": func.get('type_signature', func['signature']),
                                "doc": "",
                                "defined_in": str(path),
                                "line": func['line'],
                                "span": (func['line'], func['line'] + 1),
                            }
                    
                    # Search in types
                    for type_sym in parsed_symbols['types']:
                        if type_sym['name'] == symbol:
                            return {
                                "symbol": symbol,
                                "kind": type_sym['kind'],
                                "language": self.lang,
                                "signature": type_sym['signature'],
                                "doc": "",
                                "defined_in": str(path),
                                "line": type_sym['line'],
                                "span": (type_sym['line'], type_sym['line'] + 1),
                            }
                    
                    # Search in classes
                    for cls in parsed_symbols['classes']:
                        if cls['name'] == symbol:
                            return {
                                "symbol": symbol,
                                "kind": "class",
                                "language": self.lang,
                                "signature": cls['signature'],
                                "doc": "",
                                "defined_in": str(path),
                                "line": cls['line'],
                                "span": (cls['line'], cls['line'] + 1),
                            }
                    
                except Exception:
                    continue
        
        return None
    
    def findReferences(self, symbol: str) -> List[Reference]:
        """Find references to a Haskell symbol."""
        refs: List[Reference] = []
        seen: set[tuple[str, int]] = set()
        
        # Simple text-based reference finding with word boundaries
        symbol_pattern = re.compile(r'\b' + re.escape(symbol) + r'\b')
        
        extensions = [".hs", ".lhs", ".hsc", ".cabal"]
        for ext in extensions:
            for path in Path(".").rglob(f"*{ext}"):
                try:
                    content = path.read_text()
                    
                    # For literate Haskell, extract code first
                    if path.suffix == ".lhs":
                        content = self._parser._extract_code_from_literate(content)
                    
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
        """Search for Haskell symbols and code patterns."""
        limit = 20
        if opts and "limit" in opts:
            limit = opts["limit"]
        
        if opts and opts.get("semantic"):
            # TODO: Implement semantic search for Haskell
            return []
        
        return self._indexer.search(query, limit=limit)
    
    def get_indexed_count(self) -> int:
        """Return the number of indexed files."""
        stats = self._indexer.get_stats()
        return stats.get('files', 0)