"""Comprehensive Scala plugin with support for Scala 2 and Scala 3."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional, List, Dict, Any, Set, Tuple
import hashlib
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
from ...core.logging import get_logger


class ScalaParser:
    """Parser for Scala 2 and Scala 3 language constructs."""
    
    def __init__(self):
        self.logger = get_logger(f"{__class__.__module__}.{__class__.__name__}")
        
        # Package and import patterns
        self.package_pattern = re.compile(r'^\s*package\s+([\w.]+)(?:\s*{)?', re.MULTILINE)
        self.import_pattern = re.compile(r'^\s*import\s+((?:[\w.]+(?:\.\{[^}]+\})?(?:\._)?)+)', re.MULTILINE)
        
        # Class-like patterns (handles Scala 2 and Scala 3 syntax)
        self.class_pattern = re.compile(
            r'^\s*(?:(?:sealed\s+)?(?:abstract\s+)?(?:final\s+)?(?:case\s+)?(?:implicit\s+)?(?:private\s+)?(?:protected\s+)?)*'
            r'(class|trait|object|enum)\s+(\w+)(?:\[[^\]]+\])?(?:\([^)]*\))?(?:\s+extends\s+[^{]+)?(?:\s+with\s+[^{]+)*\s*(?:{|$)',
            re.MULTILINE
        )
        
        # Case class and case object patterns
        self.case_class_pattern = re.compile(
            r'^\s*(?:(?:private|protected|sealed|final)\s+)*case\s+(class|object)\s+(\w+)(?:\[[^\]]+\])?(?:\([^)]*\))?',
            re.MULTILINE
        )
        
        # Method/Function patterns
        self.def_pattern = re.compile(
            r'^\s*(?:(?:override|private|protected|final|implicit|inline|transparent|lazy)\s+)*'
            r'def\s+(\w+)(?:\[[^\]]+\])?(?:\([^)]*\))*(?:\s*:\s*[^={\n]+)?(?:\s*=)?',
            re.MULTILINE
        )
        
        # Val/Var patterns
        self.val_var_pattern = re.compile(
            r'^\s*(?:(?:override|private|protected|final|implicit|lazy)\s+)*'
            r'(val|var)\s+(\w+)(?:\s*:\s*[^=\n]+)?(?:\s*=)?',
            re.MULTILINE
        )
        
        # Type alias pattern
        self.type_pattern = re.compile(
            r'^\s*(?:(?:private|protected)\s+)?type\s+(\w+)(?:\[[^\]]+\])?(?:\s*=\s*[^;\n]+)?',
            re.MULTILINE
        )
        
        # Companion object pattern
        self.companion_object_pattern = re.compile(
            r'^\s*(?:(?:private|protected)\s+)?object\s+(\w+)(?:\s+extends\s+[^{]+)?(?:\s+with\s+[^{]+)*\s*{',
            re.MULTILINE
        )
        
        # Pattern matching patterns
        self.case_pattern = re.compile(
            r'^\s*case\s+([^=>]+)(?:\s+if\s+[^=>]+)?\s*=>',
            re.MULTILINE
        )
        
        # Implicit patterns
        self.implicit_def_pattern = re.compile(
            r'^\s*implicit\s+(?:(?:val|def|class|object)\s+)?(\w+)',
            re.MULTILINE
        )
        
        # Given/Using patterns (Scala 3)
        self.given_pattern = re.compile(
            r'^\s*given\s+(?:(\w+)\s*:\s*)?([^=\n]+)(?:\s*=)?',
            re.MULTILINE
        )
        
        self.using_pattern = re.compile(
            r'^\s*(?:def\s+\w+.*?)?\(?\s*using\s+([^)]+)\)?',
            re.MULTILINE
        )
        
        # Extension methods (Scala 3)
        self.extension_pattern = re.compile(
            r'^\s*extension\s*(?:\[[^\]]+\])?\s*\(([^)]+)\)(?:\s*{)?',
            re.MULTILINE
        )
        
        # For comprehension pattern
        self.for_comprehension_pattern = re.compile(
            r'^\s*for\s*\{([^}]+)\}\s*yield',
            re.MULTILINE | re.DOTALL
        )
        
        # Akka Actor patterns
        self.actor_pattern = re.compile(
            r'^\s*(?:(?:private|protected)\s+)?(?:class|object)\s+(\w+)(?:\[[^\]]+\])?(?:\([^)]*\))?\s+extends\s+(?:[\w.]*Actor)',
            re.MULTILINE
        )
        
        self.receive_pattern = re.compile(
            r'^\s*(?:override\s+)?(?:def\s+)?receive(?:\s*:\s*Receive)?\s*=\s*\{',
            re.MULTILINE
        )
        
        # Play Framework patterns
        self.controller_pattern = re.compile(
            r'^\s*(?:(?:@Singleton|@Inject)\s+)*(?:class|object)\s+(\w+)(?:\[[^\]]+\])?(?:\([^)]*\))?\s+extends\s+(?:[\w.]*Controller)',
            re.MULTILINE
        )
        
        self.action_pattern = re.compile(
            r'^\s*def\s+(\w+)(?:\[[^\]]+\])?(?:\([^)]*\))?\s*=\s*Action(?:\.async)?\s*\{',
            re.MULTILINE
        )
        
        # Spark patterns
        self.spark_job_pattern = re.compile(
            r'^\s*(?:object|class)\s+(\w+).*?SparkContext|SparkSession',
            re.MULTILINE | re.DOTALL
        )
        
        self.rdd_pattern = re.compile(
            r'^\s*(?:val|var)\s+(\w+)(?:\s*:\s*RDD\[[^\]]+\])?\s*=.*?(?:parallelize|textFile|sparkContext)',
            re.MULTILINE
        )
        
        self.dataframe_pattern = re.compile(
            r'^\s*(?:val|var)\s+(\w+)(?:\s*:\s*(?:DataFrame|Dataset\[[^\]]+\]))?\s*=.*?(?:spark\.read|toDF|createDataFrame)',
            re.MULTILINE
        )
    
    def parse_scala_file(self, content: str) -> Dict[str, Any]:
        """Parse Scala file content and extract symbols."""
        symbols = {
            'classes': [],
            'traits': [],
            'objects': [],
            'methods': [],
            'vals': [],
            'vars': [],
            'types': [],
            'implicits': [],
            'givens': [],
            'extensions': [],
            'actors': [],
            'controllers': [],
            'spark_components': [],
            'package': None,
            'imports': []
        }
        
        lines = content.split('\n')
        
        # Parse package
        package_match = self.package_pattern.search(content)
        if package_match:
            symbols['package'] = package_match.group(1)
        
        # Parse imports
        for match in self.import_pattern.finditer(content):
            symbols['imports'].append(match.group(1))
        
        # Parse class-like constructs
        for match in self.class_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            construct_type = match.group(1)
            name = match.group(2)
            signature = match.group(0).strip()
            
            # Extract modifiers
            modifiers = self._extract_modifiers(signature)
            
            if construct_type == 'class':
                # Check if it's a case class
                case_match = self.case_class_pattern.search(signature)
                if case_match:
                    symbols['classes'].append({
                        'name': name,
                        'line': line_num,
                        'signature': signature,
                        'kind': 'case_class',
                        'modifiers': modifiers
                    })
                else:
                    symbols['classes'].append({
                        'name': name,
                        'line': line_num,
                        'signature': signature,
                        'kind': 'class',
                        'modifiers': modifiers
                    })
            elif construct_type == 'trait':
                symbols['traits'].append({
                    'name': name,
                    'line': line_num,
                    'signature': signature,
                    'kind': 'trait',
                    'modifiers': modifiers
                })
            elif construct_type == 'object':
                symbols['objects'].append({
                    'name': name,
                    'line': line_num,
                    'signature': signature,
                    'kind': 'object',
                    'modifiers': modifiers
                })
            elif construct_type == 'enum':
                symbols['classes'].append({
                    'name': name,
                    'line': line_num,
                    'signature': signature,
                    'kind': 'enum',
                    'modifiers': modifiers
                })
        
        # Parse case objects separately
        for match in self.case_class_pattern.finditer(content):
            if match.group(1) == 'object':
                line_num = content[:match.start()].count('\n') + 1
                name = match.group(2)
                
                # Check if not already added
                if not any(obj['name'] == name and obj['line'] == line_num for obj in symbols['objects']):
                    symbols['objects'].append({
                        'name': name,
                        'line': line_num,
                        'signature': match.group(0).strip(),
                        'kind': 'case_object',
                        'modifiers': self._extract_modifiers(match.group(0))
                    })
        
        # Parse methods
        for match in self.def_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            method_name = match.group(1)
            signature = match.group(0).strip()
            
            symbols['methods'].append({
                'name': method_name,
                'line': line_num,
                'signature': signature,
                'kind': 'def',
                'modifiers': self._extract_modifiers(signature)
            })
        
        # Parse vals and vars
        for match in self.val_var_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            val_type = match.group(1)
            name = match.group(2)
            signature = match.group(0).strip()
            
            if val_type == 'val':
                symbols['vals'].append({
                    'name': name,
                    'line': line_num,
                    'signature': signature,
                    'kind': 'val',
                    'modifiers': self._extract_modifiers(signature)
                })
            else:
                symbols['vars'].append({
                    'name': name,
                    'line': line_num,
                    'signature': signature,
                    'kind': 'var',
                    'modifiers': self._extract_modifiers(signature)
                })
        
        # Parse type aliases
        for match in self.type_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            type_name = match.group(1)
            
            symbols['types'].append({
                'name': type_name,
                'line': line_num,
                'signature': match.group(0).strip(),
                'kind': 'type'
            })
        
        # Parse implicits
        for match in self.implicit_def_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            implicit_name = match.group(1)
            
            symbols['implicits'].append({
                'name': implicit_name,
                'line': line_num,
                'signature': match.group(0).strip(),
                'kind': 'implicit'
            })
        
        # Parse givens (Scala 3)
        for match in self.given_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            given_name = match.group(1) or f"given_{line_num}"
            given_type = match.group(2)
            
            symbols['givens'].append({
                'name': given_name,
                'line': line_num,
                'signature': match.group(0).strip(),
                'kind': 'given',
                'type': given_type.strip()
            })
        
        # Parse extensions (Scala 3)
        for match in self.extension_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            param_info = match.group(1)
            
            symbols['extensions'].append({
                'name': f"extension_{line_num}",
                'line': line_num,
                'signature': match.group(0).strip(),
                'kind': 'extension',
                'target': param_info.strip()
            })
        
        # Parse Akka actors
        for match in self.actor_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            actor_name = match.group(1)
            
            symbols['actors'].append({
                'name': actor_name,
                'line': line_num,
                'signature': match.group(0).strip(),
                'kind': 'actor'
            })
        
        # Parse Play controllers
        for match in self.controller_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            controller_name = match.group(1)
            
            symbols['controllers'].append({
                'name': controller_name,
                'line': line_num,
                'signature': match.group(0).strip(),
                'kind': 'controller'
            })
        
        # Parse Play actions
        for match in self.action_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            action_name = match.group(1)
            
            # Add to methods with special kind
            symbols['methods'].append({
                'name': action_name,
                'line': line_num,
                'signature': match.group(0).strip(),
                'kind': 'action'
            })
        
        # Parse Spark components
        for match in self.spark_job_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            job_name = match.group(1)
            
            symbols['spark_components'].append({
                'name': job_name,
                'line': line_num,
                'signature': match.group(0).strip(),
                'kind': 'spark_job'
            })
        
        # Parse RDDs
        for match in self.rdd_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            rdd_name = match.group(1)
            
            symbols['spark_components'].append({
                'name': rdd_name,
                'line': line_num,
                'signature': match.group(0).strip(),
                'kind': 'rdd'
            })
        
        # Parse DataFrames
        for match in self.dataframe_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            df_name = match.group(1)
            
            symbols['spark_components'].append({
                'name': df_name,
                'line': line_num,
                'signature': match.group(0).strip(),
                'kind': 'dataframe'
            })
        
        return symbols
    
    def _extract_modifiers(self, signature: str) -> Set[str]:
        """Extract modifiers from a signature."""
        modifiers = set()
        modifier_keywords = [
            'private', 'protected', 'public', 'sealed', 'abstract', 'final',
            'case', 'implicit', 'lazy', 'override', 'inline', 'transparent',
            'const', 'static'
        ]
        
        for mod in modifier_keywords:
            if re.search(rf'\b{mod}\b', signature):
                modifiers.add(mod)
        
        return modifiers
    
    def parse_sbt_file(self, content: str) -> Dict[str, Any]:
        """Parse SBT build file content."""
        symbols = {
            'settings': [],
            'dependencies': [],
            'plugins': [],
            'tasks': []
        }
        
        lines = content.split('\n')
        
        # Parse project settings
        setting_pattern = re.compile(r'^\s*(\w+)\s*:=\s*(.+)', re.MULTILINE)
        for match in setting_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            setting_name = match.group(1)
            setting_value = match.group(2).strip()
            
            symbols['settings'].append({
                'name': setting_name,
                'line': line_num,
                'value': setting_value,
                'signature': match.group(0).strip()
            })
        
        # Parse library dependencies
        lib_pattern = re.compile(r'libraryDependencies\s*\+\+?=\s*(?:Seq\()?"([^"]+)"\s*%+\s*"([^"]+)"\s*%\s*"([^"]+)"', re.MULTILINE)
        for match in lib_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            org = match.group(1)
            artifact = match.group(2)
            version = match.group(3)
            
            symbols['dependencies'].append({
                'name': f"{org}:{artifact}",
                'line': line_num,
                'version': version,
                'signature': match.group(0).strip()
            })
        
        # Parse plugins
        plugin_pattern = re.compile(r'addSbtPlugin\("([^"]+)"\s*%\s*"([^"]+)"\s*%\s*"([^"]+)"\)', re.MULTILINE)
        for match in plugin_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            org = match.group(1)
            plugin = match.group(2)
            version = match.group(3)
            
            symbols['plugins'].append({
                'name': f"{org}:{plugin}",
                'line': line_num,
                'version': version,
                'signature': match.group(0).strip()
            })
        
        # Parse custom tasks
        task_pattern = re.compile(r'^\s*lazy\s+val\s+(\w+)\s*=\s*(?:taskKey|settingKey|inputKey)\[', re.MULTILINE)
        for match in task_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            task_name = match.group(1)
            
            symbols['tasks'].append({
                'name': task_name,
                'line': line_num,
                'signature': match.group(0).strip()
            })
        
        return symbols


class Plugin(IPlugin):
    """Comprehensive Scala plugin with support for functional and OOP paradigms."""
    
    lang = "scala"
    
    def __init__(self, sqlite_store: Optional[SQLiteStore] = None) -> None:
        self.logger = get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        self._parser = ScalaParser()
        self._indexer = FuzzyIndexer(sqlite_store=sqlite_store)
        self._sqlite_store = sqlite_store
        self._repository_id = None
        
        # Create or get repository if SQLite is enabled
        if self._sqlite_store:
            self._repository_id = self._sqlite_store.create_repository(
                str(Path.cwd()), 
                Path.cwd().name,
                {"language": "scala"}
            )
        
        self._preindex()
    
    def _preindex(self) -> None:
        """Pre-index all Scala files in the current directory."""
        extensions = ["*.scala", "*.sc", "*.sbt"]
        
        for pattern in extensions:
            for path in Path(".").rglob(pattern):
                try:
                    text = path.read_text(encoding='utf-8')
                    self._indexer.add_file(str(path), text)
                    self.logger.debug(f"Pre-indexed {path}")
                except Exception as e:
                    self.logger.error(f"Failed to pre-index {path}: {e}")
    
    def supports(self, path: str | Path) -> bool:
        """Return True if file extension matches Scala files."""
        path_obj = Path(path) if isinstance(path, str) else path
        return path_obj.suffix in [".scala", ".sc", ".sbt"]
    
    def indexFile(self, path: str | Path, content: str) -> IndexShard:
        """Index a Scala file and extract symbols."""
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
                language="scala",
                size=len(content),
                hash=file_hash
            )
        
        # Parse based on file type
        if path.suffix == ".sbt":
            parsed_symbols = self._parser.parse_sbt_file(content)
            return self._create_sbt_index_shard(path, content, parsed_symbols, file_id)
        else:
            parsed_symbols = self._parser.parse_scala_file(content)
            return self._create_index_shard(path, content, parsed_symbols, file_id)
    
    def _create_index_shard(self, path: Path, content: str, parsed_symbols: Dict[str, Any], 
                           file_id: Optional[int]) -> IndexShard:
        """Create index shard from parsed symbols."""
        symbols: List[Dict[str, Any]] = []
        
        # Map symbol categories to their types
        symbol_mappings = {
            'classes': 'class',
            'traits': 'trait',
            'objects': 'object',
            'methods': 'def',
            'vals': 'val',
            'vars': 'var',
            'types': 'type',
            'implicits': 'implicit',
            'givens': 'given',
            'extensions': 'extension',
            'actors': 'actor',
            'controllers': 'controller',
            'spark_components': 'spark'
        }
        
        for category, symbol_list in parsed_symbols.items():
            if category in ['package', 'imports'] or not symbol_list:
                continue
            
            base_kind = symbol_mappings.get(category, 'unknown')
            
            for symbol_data in symbol_list:
                name = symbol_data['name']
                line = symbol_data['line']
                signature = symbol_data['signature']
                # Use specific kind from symbol data if available
                kind = symbol_data.get('kind', base_kind)
                
                # Store symbol in SQLite if available
                if self._sqlite_store and file_id:
                    symbol_id = self._sqlite_store.store_symbol(
                        file_id,
                        name,
                        kind,
                        line,
                        line + 1,  # End line approximation
                        signature=signature,
                        docstring=symbol_data.get('doc', '')
                    )
                    # Add to fuzzy indexer with metadata
                    self._indexer.add_symbol(
                        name, 
                        str(path), 
                        line,
                        {"symbol_id": symbol_id, "file_id": file_id}
                    )
                
                symbol_entry = {
                    "symbol": name,
                    "kind": kind,
                    "signature": signature,
                    "line": line,
                    "span": (line, line + 1),
                }
                
                # Add additional metadata if available
                if 'modifiers' in symbol_data:
                    symbol_entry['modifiers'] = list(symbol_data['modifiers'])
                if 'type' in symbol_data:
                    symbol_entry['type'] = symbol_data['type']
                
                symbols.append(symbol_entry)
        
        return {
            "file": str(path), 
            "symbols": symbols, 
            "language": "scala",
            "package": parsed_symbols.get('package'),
            "imports": parsed_symbols.get('imports', [])
        }
    
    def _create_sbt_index_shard(self, path: Path, content: str, parsed_symbols: Dict[str, Any], 
                               file_id: Optional[int]) -> IndexShard:
        """Create index shard for SBT files."""
        symbols: List[Dict[str, Any]] = []
        
        # Process settings
        for setting in parsed_symbols.get('settings', []):
            if self._sqlite_store and file_id:
                symbol_id = self._sqlite_store.store_symbol(
                    file_id,
                    setting['name'],
                    'setting',
                    setting['line'],
                    setting['line'],
                    signature=setting['signature']
                )
                self._indexer.add_symbol(
                    setting['name'], 
                    str(path), 
                    setting['line'],
                    {"symbol_id": symbol_id, "file_id": file_id}
                )
            
            symbols.append({
                "symbol": setting['name'],
                "kind": "setting",
                "signature": setting['signature'],
                "line": setting['line'],
                "span": (setting['line'], setting['line']),
                "value": setting['value']
            })
        
        # Process dependencies
        for dep in parsed_symbols.get('dependencies', []):
            if self._sqlite_store and file_id:
                symbol_id = self._sqlite_store.store_symbol(
                    file_id,
                    dep['name'],
                    'dependency',
                    dep['line'],
                    dep['line'],
                    signature=dep['signature']
                )
                self._indexer.add_symbol(
                    dep['name'], 
                    str(path), 
                    dep['line'],
                    {"symbol_id": symbol_id, "file_id": file_id}
                )
            
            symbols.append({
                "symbol": dep['name'],
                "kind": "dependency",
                "signature": dep['signature'],
                "line": dep['line'],
                "span": (dep['line'], dep['line']),
                "version": dep['version']
            })
        
        # Process plugins
        for plugin in parsed_symbols.get('plugins', []):
            if self._sqlite_store and file_id:
                symbol_id = self._sqlite_store.store_symbol(
                    file_id,
                    plugin['name'],
                    'plugin',
                    plugin['line'],
                    plugin['line'],
                    signature=plugin['signature']
                )
                self._indexer.add_symbol(
                    plugin['name'], 
                    str(path), 
                    plugin['line'],
                    {"symbol_id": symbol_id, "file_id": file_id}
                )
            
            symbols.append({
                "symbol": plugin['name'],
                "kind": "plugin",
                "signature": plugin['signature'],
                "line": plugin['line'],
                "span": (plugin['line'], plugin['line']),
                "version": plugin['version']
            })
        
        # Process tasks
        for task in parsed_symbols.get('tasks', []):
            if self._sqlite_store and file_id:
                symbol_id = self._sqlite_store.store_symbol(
                    file_id,
                    task['name'],
                    'task',
                    task['line'],
                    task['line'],
                    signature=task['signature']
                )
                self._indexer.add_symbol(
                    task['name'], 
                    str(path), 
                    task['line'],
                    {"symbol_id": symbol_id, "file_id": file_id}
                )
            
            symbols.append({
                "symbol": task['name'],
                "kind": "task",
                "signature": task['signature'],
                "line": task['line'],
                "span": (task['line'], task['line'])
            })
        
        return {
            "file": str(path), 
            "symbols": symbols, 
            "language": "sbt"
        }
    
    def getDefinition(self, symbol: str) -> SymbolDef | None:
        """Get definition location for a Scala symbol."""
        # First try SQLite if available
        if self._sqlite_store:
            # Search in database
            results = self._sqlite_store.search_symbols(symbol, limit=1)
            if results:
                result = results[0]
                return {
                    "symbol": result['name'],
                    "kind": result['kind'],
                    "language": "scala",
                    "signature": result.get('signature', ''),
                    "doc": result.get('docstring', ''),
                    "defined_in": result['file_path'],
                    "line": result['start_line'],
                    "span": (result['start_line'], result['end_line'])
                }
        
        # Fallback to file search
        extensions = ["*.scala", "*.sc"]
        
        for pattern in extensions:
            for path in Path(".").rglob(pattern):
                try:
                    content = path.read_text(encoding='utf-8')
                    parsed_symbols = self._parser.parse_scala_file(content)
                    
                    # Search through all symbol types
                    for symbol_type, symbol_list in parsed_symbols.items():
                        if symbol_type in ['package', 'imports']:
                            continue
                        
                        for symbol_data in symbol_list:
                            if symbol_data['name'] == symbol:
                                kind = symbol_data.get('kind', symbol_type.rstrip('s'))
                                return {
                                    "symbol": symbol,
                                    "kind": kind,
                                    "language": "scala",
                                    "signature": symbol_data['signature'],
                                    "doc": "",  # Doc extraction would need more sophisticated parsing
                                    "defined_in": str(path),
                                    "line": symbol_data['line'],
                                    "span": (symbol_data['line'], symbol_data['line'] + 1),
                                }
                except Exception as e:
                    self.logger.error(f"Error reading {path}: {e}")
                    continue
        
        return None
    
    def findReferences(self, symbol: str) -> List[Reference]:
        """Find references to a Scala symbol."""
        refs: List[Reference] = []
        seen: Set[Tuple[str, int]] = set()
        
        # Simple text-based reference finding
        symbol_pattern = re.compile(r'\b' + re.escape(symbol) + r'\b')
        extensions = ["*.scala", "*.sc", "*.sbt"]
        
        for pattern in extensions:
            for path in Path(".").rglob(pattern):
                try:
                    content = path.read_text(encoding='utf-8')
                    lines = content.split('\n')
                    
                    for line_num, line in enumerate(lines, 1):
                        if symbol_pattern.search(line):
                            key = (str(path), line_num)
                            if key not in seen:
                                refs.append(Reference(file=str(path), line=line_num))
                                seen.add(key)
                except Exception as e:
                    self.logger.error(f"Error reading {path}: {e}")
                    continue
        
        return refs
    
    def search(self, query: str, opts: SearchOpts | None = None) -> List[SearchResult]:
        """Search for Scala symbols and code patterns."""
        limit = 20
        if opts and "limit" in opts:
            limit = opts["limit"]
        if opts and opts.get("semantic"):
            # Semantic search not yet implemented
            return []
        return self._indexer.search(query, limit=limit)
    
    def get_indexed_count(self) -> int:
        """Return the number of indexed files."""
        stats = self._indexer.get_stats()
        return stats.get('files', 0)
    
    def get_plugin_info(self) -> Dict[str, Any]:
        """Get information about this plugin."""
        return {
            "name": self.__class__.__name__,
            "language": self.lang,
            "extensions": [".scala", ".sc", ".sbt"],
            "features": [
                "Scala 2 and Scala 3 support",
                "Case classes and objects",
                "Traits and mixins",
                "Implicit parameters and conversions",
                "Given/using (Scala 3)",
                "Extension methods (Scala 3)",
                "Pattern matching",
                "SBT build file parsing",
                "Akka actor detection",
                "Play Framework support",
                "Apache Spark support"
            ],
            "indexed_files": self.get_indexed_count()
        }