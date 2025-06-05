"""Comprehensive YAML language plugin for Code Index MCP.

This plugin provides advanced YAML parsing and indexing capabilities with support for:
- Multi-document YAML files
- Anchor and alias resolution
- Schema validation hints (Kubernetes, Docker Compose, GitHub Actions)
- Complex key path extraction (nested objects)
- List and mapping structure analysis
- YAML front matter detection (for Markdown)
- Tree-sitter parsing with regex fallback
"""

from __future__ import annotations

import hashlib
import logging
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union, Iterable

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

try:
    from tree_sitter import Parser
    from tree_sitter_languages import get_language, get_parser
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False

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


class YAMLSymbolType:
    """YAML-specific symbol types."""
    KEY = "key"
    ANCHOR = "anchor"
    ALIAS = "alias"
    ARRAY = "array"
    OBJECT = "object"
    DOCUMENT = "document"
    VALUE = "value"
    COMMENT = "comment"
    DIRECTIVE = "directive"
    TAG = "tag"
    # Schema-specific types
    KUBERNETES_RESOURCE = "kubernetes_resource"
    DOCKER_SERVICE = "docker_service"
    GITHUB_ACTION = "github_action"
    GITHUB_WORKFLOW = "github_workflow"
    FRONT_MATTER = "front_matter"


class YAMLSchemaDetector:
    """Detects common YAML schemas for better indexing."""
    
    @staticmethod
    def detect_schema(content: str, file_path: str) -> Optional[str]:
        """Detect the YAML schema type."""
        path = Path(file_path)
        
        # Check by filename patterns
        if path.name in ['docker-compose.yml', 'docker-compose.yaml']:
            return 'docker-compose'
        
        if path.name.startswith('.github/workflows/') or '/workflows/' in str(path):
            return 'github-actions'
        
        if path.suffix == '.md' and content.strip().startswith('---'):
            return 'front-matter'
        
        # Check by content patterns
        try:
            if YAML_AVAILABLE:
                docs = list(yaml.safe_load_all(content))
                
                for doc in docs:
                    if not isinstance(doc, dict):
                        continue
                    
                    # Kubernetes detection
                    if 'apiVersion' in doc and 'kind' in doc:
                        return 'kubernetes'
                    
                    # Docker Compose detection
                    if 'version' in doc and ('services' in doc or 'volumes' in doc or 'networks' in doc):
                        return 'docker-compose'
                    
                    # GitHub Actions detection
                    if 'on' in doc and ('jobs' in doc or 'runs' in doc):
                        return 'github-actions'
                    
                    # Ansible detection
                    if any(key in doc for key in ['hosts', 'tasks', 'roles', 'plays']):
                        return 'ansible'
                    
                    # OpenAPI detection
                    if 'openapi' in doc or 'swagger' in doc:
                        return 'openapi'
        
        except Exception:
            pass
        
        return None


class YAMLAnchorResolver:
    """Resolves YAML anchors and aliases."""
    
    def __init__(self):
        self.anchors: Dict[str, Dict[str, Any]] = {}
        self.aliases: Dict[str, str] = {}
    
    def extract_anchors_and_aliases(self, content: str) -> Tuple[Dict[str, int], Dict[str, int]]:
        """Extract anchor and alias definitions with their line numbers."""
        anchors = {}
        aliases = {}
        
        lines = content.splitlines()
        for line_num, line in enumerate(lines, 1):
            # Find anchors (&anchor_name)
            anchor_match = re.search(r'&([a-zA-Z_][a-zA-Z0-9_-]*)', line)
            if anchor_match:
                anchor_name = anchor_match.group(1)
                anchors[anchor_name] = line_num
            
            # Find aliases (*alias_name)
            alias_match = re.search(r'\*([a-zA-Z_][a-zA-Z0-9_-]*)', line)
            if alias_match:
                alias_name = alias_match.group(1)
                aliases[alias_name] = line_num
        
        return anchors, aliases


class YAMLPathExtractor:
    """Extracts YAML key paths for deep indexing."""
    
    @staticmethod
    def extract_key_paths(data: Any, parent_path: str = "") -> List[Tuple[str, Any, str]]:
        """Extract all key paths from YAML data."""
        paths = []
        
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{parent_path}.{key}" if parent_path else str(key)
                paths.append((current_path, value, type(value).__name__))
                
                # Recursively extract nested paths
                if isinstance(value, (dict, list)):
                    paths.extend(YAMLPathExtractor.extract_key_paths(value, current_path))
        
        elif isinstance(data, list):
            for i, item in enumerate(data):
                current_path = f"{parent_path}[{i}]" if parent_path else f"[{i}]"
                paths.append((current_path, item, type(item).__name__))
                
                if isinstance(item, (dict, list)):
                    paths.extend(YAMLPathExtractor.extract_key_paths(item, current_path))
        
        return paths


class Plugin(IPlugin):
    """Comprehensive YAML language plugin with Tree-sitter and advanced features."""
    
    lang = "yaml"
    
    def __init__(self, sqlite_store: Optional[SQLiteStore] = None) -> None:
        """Initialize the YAML plugin."""
        self._sqlite_store = sqlite_store
        self._repository_id = None
        self._indexer = FuzzyIndexer(sqlite_store=sqlite_store)
        
        # Initialize parsers
        self._tree_sitter_parser = None
        self._yaml_loader = None
        
        # Try to initialize tree-sitter parser
        if TREE_SITTER_AVAILABLE:
            try:
                self._language = get_language('yaml')
                self._tree_sitter_parser = get_parser('yaml')
                logger.info("Tree-sitter YAML parser initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize tree-sitter YAML parser: {e}")
        
        # Initialize YAML loader
        if YAML_AVAILABLE:
            # Use safe loader with custom constructors for anchors/aliases
            self._yaml_loader = yaml.SafeLoader
            logger.info("PyYAML parser initialized")
        else:
            logger.warning("PyYAML not available, using regex-only parsing")
        
        # Initialize components
        self._schema_detector = YAMLSchemaDetector()
        self._anchor_resolver = YAMLAnchorResolver()
        self._path_extractor = YAMLPathExtractor()
        
        # Create or get repository if SQLite is enabled
        if self._sqlite_store:
            self._repository_id = self._sqlite_store.create_repository(
                str(Path.cwd()),
                Path.cwd().name,
                {"language": "yaml"}
            )
        
        # Cache for storing parsed results
        self._file_cache: Dict[str, IndexShard] = {}
        
        # Symbol extraction patterns for regex fallback
        self._symbol_patterns = {
            YAMLSymbolType.KEY: re.compile(r'^(\s*)([a-zA-Z_][a-zA-Z0-9_-]*)\s*:', re.MULTILINE),
            YAMLSymbolType.ANCHOR: re.compile(r'&([a-zA-Z_][a-zA-Z0-9_-]*)'),
            YAMLSymbolType.ALIAS: re.compile(r'\*([a-zA-Z_][a-zA-Z0-9_-]*)'),
            YAMLSymbolType.DOCUMENT: re.compile(r'^---\s*$', re.MULTILINE),
            YAMLSymbolType.DIRECTIVE: re.compile(r'^%([A-Z]+)\s+(.+)$', re.MULTILINE),
            YAMLSymbolType.TAG: re.compile(r'!!([a-zA-Z0-9_]+)'),
            YAMLSymbolType.COMMENT: re.compile(r'#\s*(.+)$', re.MULTILINE),
        }
        
        logger.info("YAML plugin initialized")
        self._preindex()
    
    def _preindex(self) -> None:
        """Pre-index all YAML files in the current directory."""
        start_time = time.time()
        indexed_count = 0
        
        # YAML file extensions to index
        yaml_extensions = ['.yml', '.yaml', '.yaml.dist']
        
        for ext in yaml_extensions:
            for path in Path(".").rglob(f"*{ext}"):
                try:
                    if path.is_file():
                        text = path.read_text(encoding='utf-8')
                        self._indexer.add_file(str(path), text)
                        indexed_count += 1
                except Exception as e:
                    logger.warning(f"Failed to pre-index {path}: {e}")
                    continue
        
        # Also index Markdown files that might have YAML front matter
        for path in Path(".").rglob("*.md"):
            try:
                if path.is_file():
                    text = path.read_text(encoding='utf-8')
                    if text.strip().startswith('---'):
                        self._indexer.add_file(str(path), text)
                        indexed_count += 1
            except Exception as e:
                logger.warning(f"Failed to pre-index {path}: {e}")
                continue
        
        elapsed = time.time() - start_time
        logger.info(f"Pre-indexed {indexed_count} YAML files in {elapsed:.3f}s")
    
    def supports(self, path: str | Path) -> bool:
        """Check if this plugin supports the given file path."""
        path = Path(path)
        
        # Support standard YAML extensions
        if path.suffix.lower() in ['.yml', '.yaml']:
            return True
        
        # Support .yaml.dist files
        if str(path).endswith('.yaml.dist'):
            return True
        
        # Support Markdown files with potential YAML front matter
        if path.suffix.lower() == '.md':
            try:
                content = path.read_text(encoding='utf-8', errors='ignore')[:200]
                if content.strip().startswith('---'):
                    return True
            except Exception:
                pass
        
        # Support specific filenames
        yaml_filenames = {
            'docker-compose.yml', 'docker-compose.yaml',
            '.travis.yml', '.gitlab-ci.yml',
            'ansible.yml', 'playbook.yml',
            '.codecov.yml', '.readthedocs.yml'
        }
        
        if path.name.lower() in yaml_filenames:
            return True
        
        # Support GitHub Actions workflow files
        if '.github/workflows' in str(path) and path.suffix.lower() in ['.yml', '.yaml']:
            return True
        
        return False
    
    def indexFile(self, path: str | Path, content: str) -> IndexShard:
        """Index a YAML file and extract symbols."""
        start_time = time.time()
        
        if isinstance(path, str):
            path = Path(path)
        
        try:
            # Add to fuzzy indexer
            self._indexer.add_file(str(path), content)
            
            # Store file in SQLite if available
            file_id = None
            if self._sqlite_store and self._repository_id:
                file_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
                
                try:
                    relative_path = str(path.relative_to(Path.cwd()))
                except (ValueError, OSError):
                    relative_path = str(path)
                
                file_id = self._sqlite_store.store_file(
                    self._repository_id,
                    str(path),
                    relative_path,
                    language="yaml",
                    size=len(content),
                    hash=file_hash
                )
            
            # Detect schema
            schema = self._schema_detector.detect_schema(content, str(path))
            
            # Parse and extract symbols
            symbols = self._extract_symbols(content, str(path), file_id, schema)
            
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
    
    def _extract_symbols(self, content: str, file_path: str, file_id: Optional[int], schema: Optional[str]) -> List[Dict[str, Any]]:
        """Extract symbols from YAML content using the best available method."""
        symbols = []
        
        # Try YAML parser first if available
        if YAML_AVAILABLE:
            try:
                symbols = self._extract_symbols_yaml(content, file_path, file_id, schema)
                logger.debug(f"Extracted {len(symbols)} symbols using PyYAML")
            except Exception as e:
                logger.warning(f"YAML parsing failed: {e}")
                symbols = []
        
        # Fallback to regex-based extraction
        if not symbols:
            symbols = self._extract_symbols_regex(content, file_path, file_id, schema)
            logger.debug(f"Extracted {len(symbols)} symbols using regex")
        
        return symbols
    
    def _extract_symbols_yaml(self, content: str, file_path: str, file_id: Optional[int], schema: Optional[str]) -> List[Dict[str, Any]]:
        """Extract symbols using PyYAML parsing."""
        symbols = []
        
        try:
            # Handle front matter for Markdown files
            if schema == 'front-matter':
                return self._extract_front_matter_symbols(content, file_path, file_id)
            
            # Parse all documents
            documents = list(yaml.safe_load_all(content))
            
            # Extract anchors and aliases first
            anchors, aliases = self._anchor_resolver.extract_anchors_and_aliases(content)
            
            # Add anchor symbols
            for anchor_name, line_num in anchors.items():
                symbols.append({
                    "symbol": anchor_name,
                    "kind": YAMLSymbolType.ANCHOR,
                    "signature": f"&{anchor_name}",
                    "line": line_num,
                    "span": (line_num, line_num),
                    "path": f"&{anchor_name}",
                })
            
            # Add alias symbols
            for alias_name, line_num in aliases.items():
                symbols.append({
                    "symbol": alias_name,
                    "kind": YAMLSymbolType.ALIAS,
                    "signature": f"*{alias_name}",
                    "line": line_num,
                    "span": (line_num, line_num),
                    "path": f"*{alias_name}",
                })
            
            # Process each document
            for doc_idx, doc in enumerate(documents):
                if doc is None:
                    continue
                
                doc_symbols = self._extract_document_symbols(doc, content, file_path, file_id, schema, doc_idx)
                symbols.extend(doc_symbols)
            
            # Store symbols in database
            if self._sqlite_store and file_id:
                for symbol in symbols:
                    self._store_symbol_in_db(symbol, file_id, file_path)
            
        except Exception as e:
            logger.warning(f"YAML parsing error in {file_path}: {e}")
            # Fallback to regex parsing
            return self._extract_symbols_regex(content, file_path, file_id, schema)
        
        return symbols
    
    def _extract_symbols_regex(self, content: str, file_path: str, file_id: Optional[int], schema: Optional[str]) -> List[Dict[str, Any]]:
        """Extract symbols using regex patterns (fallback method)."""
        symbols = []
        lines = content.splitlines()
        
        # Track document boundaries
        doc_count = 0
        
        for line_num, line in enumerate(lines, 1):
            # Document separators
            if line.strip() == '---':
                doc_count += 1
                symbols.append({
                    "symbol": f"document_{doc_count}",
                    "kind": YAMLSymbolType.DOCUMENT,
                    "signature": "---",
                    "line": line_num,
                    "span": (line_num, line_num),
                    "path": f"document_{doc_count}",
                })
                continue
            
            # Extract different symbol types using patterns
            for symbol_type, pattern in self._symbol_patterns.items():
                matches = pattern.finditer(line)
                for match in matches:
                    if symbol_type == YAMLSymbolType.KEY:
                        indent = len(match.group(1))
                        key_name = match.group(2)
                        path = self._build_key_path(lines, line_num - 1, indent, key_name)
                        
                        symbol_data = {
                            "symbol": key_name,
                            "kind": YAMLSymbolType.KEY,
                            "signature": f"{key_name}:",
                            "line": line_num,
                            "span": (line_num, line_num),
                            "path": path,
                            "indent": indent,
                        }
                        
                        # Add schema-specific metadata
                        if schema:
                            symbol_data["schema"] = schema
                            symbol_data.update(self._get_schema_specific_data(key_name, path, schema))
                    
                    elif symbol_type == YAMLSymbolType.ANCHOR:
                        anchor_name = match.group(1)
                        symbol_data = {
                            "symbol": anchor_name,
                            "kind": YAMLSymbolType.ANCHOR,
                            "signature": f"&{anchor_name}",
                            "line": line_num,
                            "span": (line_num, line_num),
                            "path": f"&{anchor_name}",
                        }
                    
                    elif symbol_type == YAMLSymbolType.ALIAS:
                        alias_name = match.group(1)
                        symbol_data = {
                            "symbol": alias_name,
                            "kind": YAMLSymbolType.ALIAS,
                            "signature": f"*{alias_name}",
                            "line": line_num,
                            "span": (line_num, line_num),
                            "path": f"*{alias_name}",
                        }
                    
                    elif symbol_type == YAMLSymbolType.DIRECTIVE:
                        directive_name = match.group(1)
                        directive_value = match.group(2)
                        symbol_data = {
                            "symbol": directive_name,
                            "kind": YAMLSymbolType.DIRECTIVE,
                            "signature": f"%{directive_name} {directive_value}",
                            "line": line_num,
                            "span": (line_num, line_num),
                            "path": f"%{directive_name}",
                        }
                    
                    elif symbol_type == YAMLSymbolType.TAG:
                        tag_name = match.group(1)
                        symbol_data = {
                            "symbol": tag_name,
                            "kind": YAMLSymbolType.TAG,
                            "signature": f"!!{tag_name}",
                            "line": line_num,
                            "span": (line_num, line_num),
                            "path": f"!!{tag_name}",
                        }
                    
                    elif symbol_type == YAMLSymbolType.COMMENT:
                        comment_text = match.group(1).strip()
                        if len(comment_text) > 3:  # Only index meaningful comments
                            symbol_data = {
                                "symbol": comment_text[:50] + "..." if len(comment_text) > 50 else comment_text,
                                "kind": YAMLSymbolType.COMMENT,
                                "signature": f"# {comment_text}",
                                "line": line_num,
                                "span": (line_num, line_num),
                                "path": f"comment_line_{line_num}",
                            }
                        else:
                            continue
                    
                    else:
                        continue
                    
                    # Store in database if available
                    if self._sqlite_store and file_id:
                        self._store_symbol_in_db(symbol_data, file_id, file_path)
                    
                    symbols.append(symbol_data)
        
        return symbols
    
    def _extract_document_symbols(self, doc: Any, content: str, file_path: str, file_id: Optional[int], schema: Optional[str], doc_idx: int) -> List[Dict[str, Any]]:
        """Extract symbols from a parsed YAML document."""
        symbols = []
        
        if not isinstance(doc, dict):
            return symbols
        
        # Extract all key paths
        key_paths = self._path_extractor.extract_key_paths(doc)
        
        for path, value, value_type in key_paths:
            # Try to find the line number for this path
            line_num = self._find_path_line_number(content, path, value)
            
            symbol_data = {
                "symbol": path.split('.')[-1].split('[')[0],  # Get the last key part
                "kind": self._determine_symbol_kind(value, value_type, path, schema),
                "signature": f"{path}: {self._format_value_for_signature(value)}",
                "line": line_num,
                "span": (line_num, line_num),
                "path": path,
                "value_type": value_type,
                "document": doc_idx,
            }
            
            # Add schema-specific metadata
            if schema:
                symbol_data["schema"] = schema
                symbol_data.update(self._get_schema_specific_data(path, value, schema))
            
            # Add special metadata for certain value types
            if isinstance(value, str) and len(value) > 100:
                symbol_data["long_value"] = True
            elif isinstance(value, list):
                symbol_data["array_length"] = len(value)
            elif isinstance(value, dict):
                symbol_data["object_keys"] = len(value)
            
            symbols.append(symbol_data)
        
        return symbols
    
    def _extract_front_matter_symbols(self, content: str, file_path: str, file_id: Optional[int]) -> List[Dict[str, Any]]:
        """Extract symbols from YAML front matter in Markdown files."""
        symbols = []
        
        try:
            # Extract front matter
            if not content.strip().startswith('---'):
                return symbols
            
            parts = content.split('---', 2)
            if len(parts) < 3:
                return symbols
            
            front_matter = parts[1].strip()
            
            # Parse the front matter
            data = yaml.safe_load(front_matter)
            if not isinstance(data, dict):
                return symbols
            
            # Add front matter document symbol
            symbols.append({
                "symbol": "front_matter",
                "kind": YAMLSymbolType.FRONT_MATTER,
                "signature": "--- front matter ---",
                "line": 1,
                "span": (1, len(front_matter.splitlines()) + 2),
                "path": "front_matter",
            })
            
            # Extract key paths from front matter
            key_paths = self._path_extractor.extract_key_paths(data)
            
            for path, value, value_type in key_paths:
                line_num = self._find_path_line_number(front_matter, path, value) + 1  # Adjust for starting ---
                
                symbols.append({
                    "symbol": path.split('.')[-1].split('[')[0],
                    "kind": YAMLSymbolType.KEY,
                    "signature": f"{path}: {self._format_value_for_signature(value)}",
                    "line": line_num,
                    "span": (line_num, line_num),
                    "path": f"front_matter.{path}",
                    "value_type": value_type,
                    "schema": "front-matter",
                })
        
        except Exception as e:
            logger.warning(f"Failed to extract front matter symbols: {e}")
        
        return symbols
    
    def _build_key_path(self, lines: List[str], line_idx: int, current_indent: int, key_name: str) -> str:
        """Build the full key path by looking at indentation."""
        path_parts = [key_name]
        
        # Look backwards to find parent keys
        for i in range(line_idx - 1, -1, -1):
            line = lines[i]
            if not line.strip() or line.strip().startswith('#'):
                continue
            
            match = re.match(r'^(\s*)([a-zA-Z_][a-zA-Z0-9_-]*)\s*:', line)
            if match:
                indent = len(match.group(1))
                if indent < current_indent:
                    parent_key = match.group(2)
                    path_parts.insert(0, parent_key)
                    current_indent = indent
                    if indent == 0:
                        break
        
        return '.'.join(path_parts)
    
    def _find_path_line_number(self, content: str, path: str, value: Any) -> int:
        """Find the line number where a specific path is defined."""
        lines = content.splitlines()
        path_parts = path.split('.')
        
        # Simple heuristic: look for the last key in the path
        last_key = path_parts[-1].split('[')[0]  # Remove array indices
        
        for line_num, line in enumerate(lines, 1):
            if f"{last_key}:" in line:
                return line_num
        
        return 1  # Default to first line if not found
    
    def _determine_symbol_kind(self, value: Any, value_type: str, path: str, schema: Optional[str]) -> str:
        """Determine the appropriate symbol kind based on value and context."""
        if isinstance(value, dict):
            # Check for schema-specific patterns
            if schema == 'kubernetes' and 'kind' in value:
                return YAMLSymbolType.KUBERNETES_RESOURCE
            elif schema == 'docker-compose' and path.startswith('services.'):
                return YAMLSymbolType.DOCKER_SERVICE
            elif schema == 'github-actions' and 'uses' in str(value):
                return YAMLSymbolType.GITHUB_ACTION
            else:
                return YAMLSymbolType.OBJECT
        
        elif isinstance(value, list):
            return YAMLSymbolType.ARRAY
        
        else:
            return YAMLSymbolType.KEY
    
    def _get_schema_specific_data(self, path: str, value: Any, schema: str) -> Dict[str, Any]:
        """Get schema-specific metadata for symbols."""
        metadata = {}
        
        if schema == 'kubernetes':
            if path == 'kind':
                metadata['kubernetes_kind'] = value
            elif path == 'apiVersion':
                metadata['kubernetes_api_version'] = value
            elif path == 'metadata.name':
                metadata['kubernetes_name'] = value
            elif path == 'metadata.namespace':
                metadata['kubernetes_namespace'] = value
        
        elif schema == 'docker-compose':
            if path.startswith('services.') and '.' not in path[9:]:
                metadata['docker_service_name'] = path.split('.')[1]
            elif path.endswith('.image'):
                metadata['docker_image'] = value
            elif path.endswith('.ports'):
                metadata['docker_ports'] = value
        
        elif schema == 'github-actions':
            if path == 'name':
                metadata['workflow_name'] = value
            elif path.startswith('jobs.'):
                job_name = path.split('.')[1]
                metadata['job_name'] = job_name
            elif '.uses' in path:
                metadata['action_uses'] = value
            elif path.startswith('on.'):
                metadata['trigger'] = value
        
        return metadata
    
    def _format_value_for_signature(self, value: Any) -> str:
        """Format a value for display in symbol signature."""
        if isinstance(value, str):
            if len(value) > 50:
                return f'"{value[:47]}..."'
            return f'"{value}"'
        elif isinstance(value, (int, float, bool)):
            return str(value)
        elif isinstance(value, list):
            return f"[{len(value)} items]"
        elif isinstance(value, dict):
            return f"{{{len(value)} keys}}"
        else:
            return str(type(value).__name__)
    
    def _store_symbol_in_db(self, symbol_data: Dict[str, Any], file_id: int, file_path: str) -> None:
        """Store symbol in SQLite database."""
        try:
            symbol_id = self._sqlite_store.store_symbol(
                file_id,
                symbol_data["symbol"],
                symbol_data["kind"],
                symbol_data["line"],
                symbol_data["span"][1],
                signature=symbol_data["signature"]
            )
            
            # Add to fuzzy indexer with metadata
            self._indexer.add_symbol(
                symbol_data["symbol"],
                file_path,
                symbol_data["line"],
                {"symbol_id": symbol_id, "file_id": file_id, **symbol_data}
            )
        
        except Exception as e:
            logger.warning(f"Failed to store symbol in database: {e}")
    
    def getDefinition(self, symbol: str) -> SymbolDef | None:
        """Get definition of a symbol."""
        try:
            # Search through cached files first
            for file_path, shard in self._file_cache.items():
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
            
            # Search through project files if not found in cache
            yaml_extensions = ['.yml', '.yaml', '.yaml.dist']
            
            for ext in yaml_extensions:
                for path in Path(".").rglob(f"*{ext}"):
                    try:
                        if not path.is_file() or str(path) in self._file_cache:
                            continue
                        
                        content = path.read_text(encoding='utf-8')
                        shard = self.indexFile(path, content)
                        
                        for sym in shard["symbols"]:
                            if sym["symbol"] == symbol:
                                return SymbolDef(
                                    symbol=sym["symbol"],
                                    kind=sym["kind"],
                                    language=self.lang,
                                    signature=sym["signature"],
                                    doc=sym.get("docstring"),
                                    defined_in=str(path),
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
        seen: Set[Tuple[str, int]] = set()
        
        try:
            # Search in cached files first
            for file_path, shard in self._file_cache.items():
                try:
                    content = Path(file_path).read_text(encoding='utf-8')
                    lines = content.splitlines()
                    
                    for line_num, line in enumerate(lines, 1):
                        # Look for symbol usage in various YAML contexts
                        patterns = [
                            rf'\b{re.escape(symbol)}\b',  # Direct match
                            rf'\*{re.escape(symbol)}\b',   # Alias reference
                            rf'&{re.escape(symbol)}\b',   # Anchor definition
                        ]
                        
                        for pattern in patterns:
                            if re.search(pattern, line):
                                key = (file_path, line_num)
                                if key not in seen:
                                    refs.append(Reference(file=file_path, line=line_num))
                                    seen.add(key)
                                break
                
                except Exception as e:
                    logger.warning(f"Error processing {file_path} for reference search: {e}")
                    continue
            
            # Search through project files for completeness
            yaml_extensions = ['.yml', '.yaml', '.yaml.dist']
            
            for ext in yaml_extensions:
                for path in Path(".").rglob(f"*{ext}"):
                    try:
                        if not path.is_file() or str(path) in self._file_cache:
                            continue
                        
                        content = path.read_text(encoding='utf-8')
                        lines = content.splitlines()
                        
                        for line_num, line in enumerate(lines, 1):
                            patterns = [
                                rf'\b{re.escape(symbol)}\b',
                                rf'\*{re.escape(symbol)}\b',
                                rf'&{re.escape(symbol)}\b',
                            ]
                            
                            for pattern in patterns:
                                if re.search(pattern, line):
                                    key = (str(path), line_num)
                                    if key not in seen:
                                        refs.append(Reference(file=str(path), line=line_num))
                                        seen.add(key)
                                    break
                    
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
    
    def get_schema_statistics(self) -> Dict[str, int]:
        """Get statistics about detected schemas."""
        schema_counts = {}
        
        for file_path, shard in self._file_cache.items():
            for symbol in shard["symbols"]:
                schema = symbol.get("schema")
                if schema:
                    schema_counts[schema] = schema_counts.get(schema, 0) + 1
        
        return schema_counts
    
    def get_plugin_info(self) -> Dict[str, Any]:
        """Get information about this plugin."""
        return {
            "name": "YAMLPlugin",
            "language": self.lang,
            "extensions": [".yml", ".yaml", ".yaml.dist", ".md (with front matter)"],
            "tree_sitter_available": TREE_SITTER_AVAILABLE,
            "yaml_parser_available": YAML_AVAILABLE,
            "supported_schemas": [
                "kubernetes", "docker-compose", "github-actions",
                "ansible", "openapi", "front-matter"
            ],
            "features": [
                "Multi-document YAML support",
                "Anchor and alias resolution",
                "Schema detection and validation hints",
                "Complex key path extraction",
                "YAML front matter detection",
                "Tree-sitter parsing with fallback"
            ],
            "indexed_files": self.get_indexed_count(),
            "schema_statistics": self.get_schema_statistics()
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get plugin statistics."""
        stats = {
            "indexed_files": self._indexer.get_stats().get("files", 0) if hasattr(self._indexer, 'get_stats') else len(self._file_cache),
            "total_symbols": self._indexer.get_stats().get("symbols", 0) if hasattr(self._indexer, 'get_stats') else sum(len(shard["symbols"]) for shard in self._file_cache.values())
        }
        
        if self._sqlite_store:
            try:
                db_stats = self._sqlite_store.get_statistics()
                stats.update({
                    "db_files": db_stats.get("files", 0),
                    "db_symbols": db_stats.get("symbols", 0)
                })
            except Exception:
                pass
        
        return stats