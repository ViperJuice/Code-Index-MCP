"""
Comprehensive Bash/Shell plugin for code indexing and analysis.

This plugin supports multiple shell languages and provides advanced parsing
for DevOps scripts, build scripts, and system administration tools.
"""

from __future__ import annotations

import re
import json
import hashlib
from pathlib import Path
from typing import Optional, List, Dict, Any, Set, Tuple
from enum import Enum

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


class ShellType(Enum):
    """Supported shell types."""
    BASH = "bash"
    ZSH = "zsh"
    FISH = "fish"
    KSH = "ksh"
    CSH = "csh"
    SH = "sh"
    UNKNOWN = "unknown"


class BashTreeSitterWrapper:
    """Advanced shell script parser using regex patterns with Tree-sitter compatibility."""
    
    def __init__(self):
        """Initialize the parser with comprehensive shell patterns."""
        # Function patterns for different shell types
        self.function_patterns = {
            ShellType.BASH: [
                re.compile(r'^\s*function\s+(\w+)\s*\(\s*\)\s*\{', re.MULTILINE),
                re.compile(r'^\s*(\w+)\s*\(\s*\)\s*\{', re.MULTILINE),
                re.compile(r'^\s*function\s+(\w+)\s*\{', re.MULTILINE),
            ],
            ShellType.ZSH: [
                re.compile(r'^\s*function\s+(\w+)\s*\(\s*\)\s*\{', re.MULTILINE),
                re.compile(r'^\s*(\w+)\s*\(\s*\)\s*\{', re.MULTILINE),
                re.compile(r'^\s*function\s+(\w+)\s*\{', re.MULTILINE),
            ],
            ShellType.FISH: [
                re.compile(r'^\s*function\s+(\w+)', re.MULTILINE),
            ],
            ShellType.KSH: [
                re.compile(r'^\s*function\s+(\w+)\s*\{', re.MULTILINE),
                re.compile(r'^\s*(\w+)\s*\(\s*\)\s*\{', re.MULTILINE),
            ],
            ShellType.CSH: [
                re.compile(r'^\s*alias\s+(\w+)', re.MULTILINE),  # csh uses aliases more than functions
            ],
            ShellType.SH: [
                re.compile(r'^\s*(\w+)\s*\(\s*\)\s*\{', re.MULTILINE),
            ],
        }
        
        # Variable patterns
        self.variable_patterns = [
            re.compile(r'^\s*(\w+)=(.*)$', re.MULTILINE),  # Basic assignment
            re.compile(r'^\s*export\s+(\w+)(?:=(.*))?$', re.MULTILINE),  # Export
            re.compile(r'^\s*declare\s+(?:-\w+\s+)?(\w+)(?:=(.*))?$', re.MULTILINE),  # Declare
            re.compile(r'^\s*local\s+(\w+)(?:=(.*))?$', re.MULTILINE),  # Local
            re.compile(r'^\s*readonly\s+(\w+)(?:=(.*))?$', re.MULTILINE),  # Readonly
            re.compile(r'^\s*typeset\s+(?:-\w+\s+)?(\w+)(?:=(.*))?$', re.MULTILINE),  # Typeset
        ]
        
        # Alias patterns
        self.alias_patterns = [
            re.compile(r'^\s*alias\s+(\w+)=([\'"]?)([^\'"\n]*)\2', re.MULTILINE),
            re.compile(r'^\s*alias\s+(\w+)\s+([\'"]?)([^\'"\n]*)\2', re.MULTILINE),
        ]
        
        # Control structure patterns
        self.control_patterns = {
            'if': re.compile(r'^\s*if\s+(.+?);\s*then', re.MULTILINE),
            'for': re.compile(r'^\s*for\s+(\w+)\s+in\s+(.+?);\s*do', re.MULTILINE),
            'while': re.compile(r'^\s*while\s+(.+?);\s*do', re.MULTILINE),
            'until': re.compile(r'^\s*until\s+(.+?);\s*do', re.MULTILINE),
            'case': re.compile(r'^\s*case\s+(\$?\w+)\s+in', re.MULTILINE),
            'select': re.compile(r'^\s*select\s+(\w+)\s+in\s+(.+?);\s*do', re.MULTILINE),
        }
        
        # Sourcing/inclusion patterns
        self.source_patterns = [
            re.compile(r'^\s*source\s+([^\s]+)', re.MULTILINE),
            re.compile(r'^\s*\.\s+([^\s]+)', re.MULTILINE),  # dot notation
            re.compile(r'^\s*include\s+([^\s]+)', re.MULTILINE),  # some shells
        ]
        
        # Shebang pattern
        self.shebang_pattern = re.compile(r'^#!\s*([^\s]+)', re.MULTILINE)
        
        # Comment patterns
        self.comment_pattern = re.compile(r'^\s*#\s*(.+)$', re.MULTILINE)
        
        # Command substitution patterns
        self.substitution_patterns = [
            re.compile(r'\$\(([^)]+)\)', re.MULTILINE),  # $(...) form
            re.compile(r'`([^`]+)`', re.MULTILINE),        # backtick form
        ]
        
        # Parameter expansion patterns
        self.param_expansion_patterns = [
            re.compile(r'\$\{([^}]+)\}', re.MULTILINE),  # ${...} form
            re.compile(r'\$(\w+)', re.MULTILINE),         # $var form
        ]
    
    def detect_shell_type(self, content: str, filename: str = "") -> ShellType:
        """Detect the shell type from content and filename."""
        # Check shebang first
        shebang_match = self.shebang_pattern.search(content)
        if shebang_match:
            shebang = shebang_match.group(1).lower()
            if 'bash' in shebang:
                return ShellType.BASH
            elif 'zsh' in shebang:
                return ShellType.ZSH
            elif 'fish' in shebang:
                return ShellType.FISH
            elif 'ksh' in shebang:
                return ShellType.KSH
            elif 'csh' in shebang or 'tcsh' in shebang:
                return ShellType.CSH
            elif 'sh' in shebang:
                return ShellType.SH
        
        # Check file extension
        if filename:
            if filename.endswith('.bash'):
                return ShellType.BASH
            elif filename.endswith('.zsh'):
                return ShellType.ZSH
            elif filename.endswith('.fish'):
                return ShellType.FISH
            elif filename.endswith('.ksh'):
                return ShellType.KSH
            elif filename.endswith('.csh'):
                return ShellType.CSH
        
        # Check for shell-specific syntax
        if re.search(r'function\s+\w+\s*\{', content):
            return ShellType.BASH  # or ZSH, but BASH is more common
        elif re.search(r'function\s+\w+\s*\n', content):
            return ShellType.FISH
        
        # Default to bash for .sh files
        return ShellType.BASH if filename.endswith('.sh') else ShellType.UNKNOWN
    
    def parse_shell_file(self, content: str, filename: str = "") -> Dict[str, Any]:
        """Parse shell file content and extract symbols."""
        shell_type = self.detect_shell_type(content, filename)
        
        symbols = {
            'shell_type': shell_type.value,
            'functions': [],
            'variables': [],
            'aliases': [],
            'exports': [],
            'control_structures': [],
            'sources': [],
            'shebang': None,
            'metadata': {
                'has_error_handling': False,
                'has_logging': False,
                'complexity_score': 0,
                'external_deps': set(),
                'environment_vars': set(),
            }
        }
        
        # Parse shebang
        shebang_match = self.shebang_pattern.search(content)
        if shebang_match:
            symbols['shebang'] = shebang_match.group(1)
        
        # Parse functions
        self._parse_functions(content, symbols, shell_type)
        
        # Parse variables and exports
        self._parse_variables(content, symbols)
        
        # Parse aliases
        self._parse_aliases(content, symbols)
        
        # Parse control structures
        self._parse_control_structures(content, symbols)
        
        # Parse sourcing/inclusion
        self._parse_sources(content, symbols)
        
        # Calculate metadata
        self._calculate_metadata(content, symbols)
        
        return symbols
    
    def _parse_functions(self, content: str, symbols: Dict[str, Any], shell_type: ShellType) -> None:
        """Parse function definitions."""
        patterns = self.function_patterns.get(shell_type, self.function_patterns[ShellType.BASH])
        
        for pattern in patterns:
            for match in pattern.finditer(content):
                line_num = content[:match.start()].count('\n') + 1
                func_name = match.group(1)
                
                symbols['functions'].append({
                    'name': func_name,
                    'line': line_num,
                    'signature': match.group(0).strip(),
                    'type': shell_type.value
                })
    
    def _parse_variables(self, content: str, symbols: Dict[str, Any]) -> None:
        """Parse variable declarations and exports."""
        for pattern in self.variable_patterns:
            for match in pattern.finditer(content):
                line_num = content[:match.start()].count('\n') + 1
                var_name = match.group(1)
                var_value = match.group(2) if match.groups() and len(match.groups()) > 1 else ""
                
                # Determine if it's an export
                line_text = content.split('\n')[line_num - 1].strip()
                is_export = line_text.startswith('export')
                is_local = line_text.startswith('local')
                is_readonly = line_text.startswith('readonly')
                is_declare = line_text.startswith('declare')
                
                var_info = {
                    'name': var_name,
                    'line': line_num,
                    'value': var_value.strip() if var_value else "",
                    'signature': line_text,
                    'is_export': is_export,
                    'is_local': is_local,
                    'is_readonly': is_readonly,
                    'is_declare': is_declare
                }
                
                if is_export:
                    symbols['exports'].append(var_info)
                    symbols['metadata']['environment_vars'].add(var_name)
                else:
                    symbols['variables'].append(var_info)
    
    def _parse_aliases(self, content: str, symbols: Dict[str, Any]) -> None:
        """Parse alias definitions."""
        for pattern in self.alias_patterns:
            for match in pattern.finditer(content):
                line_num = content[:match.start()].count('\n') + 1
                alias_name = match.group(1)
                alias_value = match.group(3) if len(match.groups()) >= 3 else match.group(2)
                
                symbols['aliases'].append({
                    'name': alias_name,
                    'line': line_num,
                    'value': alias_value,
                    'signature': match.group(0).strip()
                })
    
    def _parse_control_structures(self, content: str, symbols: Dict[str, Any]) -> None:
        """Parse control flow structures."""
        for struct_type, pattern in self.control_patterns.items():
            for match in pattern.finditer(content):
                line_num = content[:match.start()].count('\n') + 1
                condition = match.group(1) if match.groups() else ""
                
                symbols['control_structures'].append({
                    'type': struct_type,
                    'line': line_num,
                    'condition': condition.strip(),
                    'signature': match.group(0).strip()
                })
    
    def _parse_sources(self, content: str, symbols: Dict[str, Any]) -> None:
        """Parse source/include statements."""
        for pattern in self.source_patterns:
            for match in pattern.finditer(content):
                line_num = content[:match.start()].count('\n') + 1
                source_file = match.group(1)
                
                symbols['sources'].append({
                    'file': source_file,
                    'line': line_num,
                    'signature': match.group(0).strip()
                })
                
                symbols['metadata']['external_deps'].add(source_file)
    
    def _calculate_metadata(self, content: str, symbols: Dict[str, Any]) -> None:
        """Calculate complexity and feature metadata."""
        metadata = symbols['metadata']
        
        # Check for error handling
        if re.search(r'set\s+-e|trap\s+|if\s+.*\[\s*\$\?\s*', content, re.IGNORECASE):
            metadata['has_error_handling'] = True
        
        # Check for logging
        if re.search(r'echo\s+|printf\s+|logger\s+|log\s+', content, re.IGNORECASE):
            metadata['has_logging'] = True
        
        # Calculate complexity score
        complexity = 0
        complexity += len(symbols['functions']) * 2
        complexity += len(symbols['control_structures']) * 1.5
        
        metadata['complexity_score'] = int(complexity)
        
        # Convert sets to lists for JSON serialization
        metadata['external_deps'] = list(metadata['external_deps'])
        metadata['environment_vars'] = list(metadata['environment_vars'])


class Plugin(IPlugin):
    """Comprehensive Bash/Shell plugin."""
    
    lang = "shell"
    
    def __init__(self, sqlite_store: Optional[SQLiteStore] = None) -> None:
        """Initialize the shell plugin."""
        self._parser = BashTreeSitterWrapper()
        self._indexer = FuzzyIndexer(sqlite_store=sqlite_store)
        self._sqlite_store = sqlite_store
        self._repository_id = None
        
        # Create or get repository if SQLite is enabled
        if self._sqlite_store:
            self._repository_id = self._sqlite_store.create_repository(
                str(Path.cwd()),
                Path.cwd().name,
                {"language": "shell", "plugin": "bash_plugin"}
            )
        
        self._preindex()
    
    def _preindex(self) -> None:
        """Pre-index all shell files in the current directory."""
        shell_extensions = {'.sh', '.bash', '.zsh', '.fish', '.ksh', '.csh'}
        
        for ext in shell_extensions:
            for path in Path(".").rglob(f"*{ext}"):
                try:
                    if path.is_file():
                        text = path.read_text(encoding='utf-8', errors='ignore')
                        self._indexer.add_file(str(path), text)
                except Exception:
                    continue
    
    def supports(self, path: str | Path) -> bool:
        """Check if the file is a shell script."""
        path_obj = Path(path) if isinstance(path, str) else path
        
        # Check extension
        if path_obj.suffix.lower() in {'.sh', '.bash', '.zsh', '.fish', '.ksh', '.csh'}:
            return True
        
        # Check if it's an executable shell script by reading the first line
        if path_obj.is_file():
            try:
                with open(path_obj, 'r', encoding='utf-8', errors='ignore') as f:
                    first_line = f.readline().strip()
                    if first_line.startswith('#!') and any(shell in first_line.lower() 
                        for shell in ['sh', 'bash', 'zsh', 'fish', 'ksh', 'csh']):
                        return True
            except Exception:
                pass
        
        return False
    
    def indexFile(self, path: str | Path, content: str) -> IndexShard:
        """Index a shell script file."""
        if isinstance(path, str):
            path = Path(path)
        
        self._indexer.add_file(str(path), content)
        
        # Store file in SQLite if available
        file_id = None
        if self._sqlite_store and self._repository_id:
            file_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
            try:
                if path.is_absolute():
                    relative_path = str(path.relative_to(Path.cwd()))
                else:
                    relative_path = str(path)
            except ValueError:
                relative_path = path.name
            
            file_id = self._sqlite_store.store_file(
                self._repository_id,
                str(path),
                relative_path,
                language="shell",
                size=len(content),
                hash=file_hash
            )
        
        # Parse the shell file
        parsed_symbols = self._parser.parse_shell_file(content, str(path))
        
        symbols: List[Dict[str, Any]] = []
        
        # Process functions
        for func in parsed_symbols.get('functions', []):
            symbols.append({
                "symbol": func['name'],
                "kind": "function",
                "signature": func['signature'],
                "line": func['line'],
                "span": (func['line'], func['line'] + 1),
                "metadata": {"shell_type": func.get('type')}
            })
            
            if self._sqlite_store and file_id:
                symbol_id = self._sqlite_store.store_symbol(
                    file_id, func['name'], "function", func['line'], func['line'] + 1,
                    signature=func['signature']
                )
                self._indexer.add_symbol(func['name'], str(path), func['line'], 
                                       {"symbol_id": symbol_id, "file_id": file_id})
        
        # Process variables and exports
        for var in parsed_symbols.get('variables', []) + parsed_symbols.get('exports', []):
            kind = "export" if var.get('is_export') else "variable"
            symbols.append({
                "symbol": var['name'],
                "kind": kind,
                "signature": var['signature'],
                "line": var['line'],
                "span": (var['line'], var['line']),
                "metadata": {
                    "value": var.get('value'),
                    "is_local": var.get('is_local', False),
                    "is_readonly": var.get('is_readonly', False)
                }
            })
            
            if self._sqlite_store and file_id:
                symbol_id = self._sqlite_store.store_symbol(
                    file_id, var['name'], kind, var['line'], var['line'],
                    signature=var['signature']
                )
                self._indexer.add_symbol(var['name'], str(path), var['line'],
                                       {"symbol_id": symbol_id, "file_id": file_id})
        
        # Process aliases
        for alias in parsed_symbols.get('aliases', []):
            symbols.append({
                "symbol": alias['name'],
                "kind": "alias",
                "signature": alias['signature'],
                "line": alias['line'],
                "span": (alias['line'], alias['line']),
                "metadata": {"value": alias.get('value')}
            })
            
            if self._sqlite_store and file_id:
                symbol_id = self._sqlite_store.store_symbol(
                    file_id, alias['name'], "alias", alias['line'], alias['line'],
                    signature=alias['signature']
                )
                self._indexer.add_symbol(alias['name'], str(path), alias['line'],
                                       {"symbol_id": symbol_id, "file_id": file_id})
        
        return {
            "file": str(path),
            "symbols": symbols,
            "language": self.lang,
            "shell_type": parsed_symbols.get('shell_type'),
            "shebang": parsed_symbols.get('shebang'),
            "metadata": parsed_symbols.get('metadata', {}),
            "sources": parsed_symbols.get('sources', []),
            "control_structures": len(parsed_symbols.get('control_structures', [])),
        }
    
    def getDefinition(self, symbol: str) -> SymbolDef | None:
        """Get definition location for a shell symbol."""
        shell_extensions = {'.sh', '.bash', '.zsh', '.fish', '.ksh', '.csh'}
        
        for ext in shell_extensions:
            for path in Path(".").rglob(f"*{ext}"):
                try:
                    if not path.is_file():
                        continue
                    
                    content = path.read_text(encoding='utf-8', errors='ignore')
                    parsed_symbols = self._parser.parse_shell_file(content, str(path))
                    
                    # Search in functions
                    for func in parsed_symbols.get('functions', []):
                        if func['name'] == symbol:
                            return {
                                "symbol": symbol,
                                "kind": "function",
                                "language": self.lang,
                                "signature": func['signature'],
                                "doc": "",
                                "defined_in": str(path),
                                "line": func['line'],
                                "span": (func['line'], func['line'] + 1),
                            }
                    
                    # Search in variables and exports
                    for var in parsed_symbols.get('variables', []) + parsed_symbols.get('exports', []):
                        if var['name'] == symbol:
                            kind = "export" if var.get('is_export') else "variable"
                            return {
                                "symbol": symbol,
                                "kind": kind,
                                "language": self.lang,
                                "signature": var['signature'],
                                "doc": f"Value: {var.get('value', '')}",
                                "defined_in": str(path),
                                "line": var['line'],
                                "span": (var['line'], var['line']),
                            }
                    
                    # Search in aliases
                    for alias in parsed_symbols.get('aliases', []):
                        if alias['name'] == symbol:
                            return {
                                "symbol": symbol,
                                "kind": "alias",
                                "language": self.lang,
                                "signature": alias['signature'],
                                "doc": f"Alias for: {alias.get('value', '')}",
                                "defined_in": str(path),
                                "line": alias['line'],
                                "span": (alias['line'], alias['line']),
                            }
                            
                except Exception:
                    continue
        
        return None
    
    def findReferences(self, symbol: str) -> List[Reference]:
        """Find references to a shell symbol."""
        refs: List[Reference] = []
        seen: Set[Tuple[str, int]] = set()
        
        # Create pattern for finding symbol usage
        symbol_pattern = re.compile(r'\b' + re.escape(symbol) + r'\b')
        
        shell_extensions = {'.sh', '.bash', '.zsh', '.fish', '.ksh', '.csh'}
        
        for ext in shell_extensions:
            for path in Path(".").rglob(f"*{ext}"):
                try:
                    if not path.is_file():
                        continue
                    
                    content = path.read_text(encoding='utf-8', errors='ignore')
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
        """Search for shell symbols and code patterns."""
        limit = 20
        if opts and "limit" in opts:
            limit = opts["limit"]
        if opts and opts.get("semantic"):
            return []  # Semantic search not implemented yet
        
        return self._indexer.search(query, limit=limit)
    
    def get_indexed_count(self) -> int:
        """Return the number of indexed files."""
        stats = self._indexer.get_stats()
        return stats.get('files', 0)
    
    def get_shell_analysis(self, path: str | Path, content: str) -> Dict[str, Any]:
        """Get comprehensive shell script analysis."""
        parsed = self._parser.parse_shell_file(content, str(path))
        
        return {
            "shell_type": parsed.get('shell_type'),
            "shebang": parsed.get('shebang'),
            "function_count": len(parsed.get('functions', [])),
            "variable_count": len(parsed.get('variables', [])),
            "export_count": len(parsed.get('exports', [])),
            "alias_count": len(parsed.get('aliases', [])),
            "complexity_score": parsed.get('metadata', {}).get('complexity_score', 0),
            "has_error_handling": parsed.get('metadata', {}).get('has_error_handling', False),
            "has_logging": parsed.get('metadata', {}).get('has_logging', False),
            "external_dependencies": parsed.get('metadata', {}).get('external_deps', []),
            "environment_variables": parsed.get('metadata', {}).get('environment_vars', []),
            "sources_includes": parsed.get('sources', []),
            "control_structures": len(parsed.get('control_structures', [])),
        }