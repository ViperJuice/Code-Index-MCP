#!/usr/bin/env python3
"""Generate semantic plugin versions for all language plugins."""

import os
from pathlib import Path


PLUGIN_TEMPLATE = '''"""%(lang_display)s plugin with semantic search support."""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Iterable, Dict, List, Any
import logging

from ...plugin_base import (
    IndexShard,
    SymbolDef,
    Reference,
    SearchResult,
    SearchOpts,
)
from ...plugin_base_enhanced import PluginWithSemanticSearch
from ...utils.fuzzy_indexer import FuzzyIndexer
from ...storage.sqlite_store import SQLiteStore

logger = logging.getLogger(__name__)


class %(class_name)s(PluginWithSemanticSearch):
    """%(lang_display)s plugin with semantic search capabilities."""
    
    lang = "%(lang_code)s"

    def __init__(self, sqlite_store: Optional[SQLiteStore] = None, enable_semantic: bool = True) -> None:
        # Initialize enhanced base class
        super().__init__(sqlite_store=sqlite_store, enable_semantic=enable_semantic)
        
        # Initialize language-specific components
        self._indexer = FuzzyIndexer(sqlite_store=sqlite_store)
        self._repository_id = None
        
        # Create or get repository if SQLite is enabled
        if self._sqlite_store:
            try:
                self._repository_id = self._sqlite_store.create_repository(
                    str(Path.cwd()), 
                    Path.cwd().name,
                    {"language": "%(lang_code)s"}
                )
            except Exception as e:
                logger.warning(f"Failed to create repository: {e}")
                self._repository_id = None
        
        self._preindex()

    def _preindex(self) -> None:
        """Pre-index %(lang_display)s files in the current directory."""
        for ext in self._get_extensions():
            for path in Path(".").rglob(f"*{ext}"):
                try:
                    text = path.read_text()
                    self._indexer.add_file(str(path), text)
                except Exception:
                    continue

    def _get_extensions(self) -> List[str]:
        """Get file extensions for this language."""
        %(extensions)s

    def supports(self, path: str | Path) -> bool:
        """Return True if file extension matches %(lang_display)s."""
        return Path(path).suffix in self._get_extensions()

    def indexFile(self, path: str | Path, content: str) -> IndexShard:
        """Index a %(lang_display)s file with optional semantic embeddings."""
        if isinstance(path, str):
            path = Path(path)
            
        # Add to fuzzy indexer
        self._indexer.add_file(str(path), content)
        
        # Store file in SQLite if available
        file_id = None
        if self._sqlite_store and self._repository_id:
            import hashlib
            file_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
            file_id = self._sqlite_store.store_file(
                self._repository_id,
                str(path),
                str(path.relative_to(Path.cwd()) if path.is_absolute() else path),
                language="%(lang_code)s",
                size=len(content),
                hash=file_hash
            )
        
        # Extract symbols (simplified for now)
        symbols = self._extract_symbols(content, file_id)
        
        # Create semantic embeddings if enabled
        if self._enable_semantic and symbols:
            self.index_with_embeddings(path, content, symbols)
        
        return IndexShard(
            file=str(path),
            symbols=symbols,
            language="%(lang_code)s"
        )
    
    def _extract_symbols(self, content: str, file_id: Optional[int] = None) -> List[Dict]:
        """Extract symbols from %(lang_display)s code."""
        symbols = []
        lines = content.split('\\n')
        
        # Basic symbol extraction - override in actual implementation
        for i, line in enumerate(lines):
            %(symbol_extraction)s
        
        return symbols

    def getDefinition(self, symbol: str) -> SymbolDef | None:
        """Get symbol definition."""
        # Simple search through indexed files
        for ext in self._get_extensions():
            for path in Path(".").rglob(f"*{ext}"):
                try:
                    content = path.read_text()
                    if symbol in content:
                        lines = content.split('\\n')
                        for i, line in enumerate(lines):
                            if symbol in line:
                                return SymbolDef(
                                    symbol=symbol,
                                    kind='symbol',
                                    language='%(lang_code)s',
                                    signature=line.strip(),
                                    doc=None,
                                    defined_in=str(path),
                                    line=i + 1,
                                    span=(i + 1, i + 3)
                                )
                except Exception:
                    continue
        return None

    def findReferences(self, symbol: str) -> list[Reference]:
        """Find all references to a symbol."""
        refs: list[Reference] = []
        seen: set[tuple[str, int]] = set()
        
        for ext in self._get_extensions():
            for path in Path(".").rglob(f"*{ext}"):
                try:
                    content = path.read_text()
                    lines = content.split('\\n')
                    
                    for i, line in enumerate(lines):
                        if symbol in line:
                            key = (str(path), i + 1)
                            if key not in seen:
                                refs.append(Reference(file=str(path), line=i + 1))
                                seen.add(key)
                except Exception:
                    continue
        
        return refs

    def _traditional_search(self, query: str, opts: SearchOpts | None = None) -> Iterable[SearchResult]:
        """Traditional fuzzy search implementation."""
        limit = 20
        if opts and "limit" in opts:
            limit = opts["limit"]
        return self._indexer.search(query, limit=limit)
    
    def get_indexed_count(self) -> int:
        """Return the number of indexed files."""
        if hasattr(self._indexer, '_file_contents'):
            return len(self._indexer._file_contents)
        return 0
'''

INIT_TEMPLATE = '''"""%(lang_display)s plugin for Code-Index-MCP."""

import os

# Use semantic plugin if enabled, otherwise fallback to basic plugin
if os.getenv("SEMANTIC_SEARCH_ENABLED", "false").lower() == "true":
    try:
        from .plugin_semantic import %(class_name)s as Plugin
    except ImportError:
        from .plugin import Plugin
else:
    from .plugin import Plugin

__all__ = ["Plugin"]
'''


def create_semantic_plugin(plugin_dir, lang_code, lang_display, class_name, extensions, symbol_extraction):
    """Create semantic version of a plugin."""
    
    # Create plugin_semantic.py
    semantic_file = plugin_dir / "plugin_semantic.py"
    if semantic_file.exists():
        print(f"  Skipping {lang_display} - semantic version already exists")
        return
    
    content = PLUGIN_TEMPLATE % {
        'lang_code': lang_code,
        'lang_display': lang_display,
        'class_name': class_name,
        'extensions': extensions,
        'symbol_extraction': symbol_extraction
    }
    
    semantic_file.write_text(content)
    print(f"  Created {semantic_file}")
    
    # Update __init__.py
    init_file = plugin_dir / "__init__.py"
    init_content = INIT_TEMPLATE % {
        'lang_display': lang_display,
        'class_name': class_name
    }
    
    # Check if already has semantic import
    current_init = init_file.read_text()
    if "SEMANTIC_SEARCH_ENABLED" not in current_init:
        init_file.write_text(init_content)
        print(f"  Updated {init_file}")
    else:
        print(f"  {init_file} already has semantic import")


def main():
    """Generate semantic plugins for all languages."""
    plugins_dir = Path("/app/mcp_server/plugins")
    
    plugins_config = [
        {
            'dir': 'c_plugin',
            'lang_code': 'c',
            'lang_display': 'C',
            'class_name': 'CPluginSemantic',
            'extensions': 'return [".c", ".h"]',
            'symbol_extraction': '''if 'struct' in line or 'typedef' in line or 'void' in line or 'int' in line:
                stripped = line.strip()
                if stripped and not stripped.startswith('//'):
                    # Extract function or struct name
                    parts = stripped.split()
                    if len(parts) > 1:
                        name = parts[1].split('(')[0] if '(' in parts[1] else parts[1]
                        symbols.append({
                            'symbol': name,
                            'kind': 'function' if '(' in line else 'struct',
                            'signature': stripped,
                            'line': i + 1,
                            'end_line': i + 1,
                            'span': [i + 1, i + 1]
                        })'''
        },
        {
            'dir': 'cpp_plugin',
            'lang_code': 'cpp',
            'lang_display': 'C++',
            'class_name': 'CppPluginSemantic',
            'extensions': 'return [".cpp", ".cc", ".cxx", ".hpp", ".h++", ".hh"]',
            'symbol_extraction': '''if 'class' in line or 'struct' in line or 'void' in line or 'template' in line:
                stripped = line.strip()
                if stripped and not stripped.startswith('//'):
                    # Extract class/function name
                    if 'class' in stripped:
                        parts = stripped.split()
                        idx = parts.index('class') if 'class' in parts else -1
                        if idx >= 0 and idx + 1 < len(parts):
                            name = parts[idx + 1].rstrip(':')
                            symbols.append({
                                'symbol': name,
                                'kind': 'class',
                                'signature': stripped,
                                'line': i + 1,
                                'end_line': i + 1,
                                'span': [i + 1, i + 1]
                            })'''
        },
        {
            'dir': 'dart_plugin',
            'lang_code': 'dart',
            'lang_display': 'Dart',
            'class_name': 'DartPluginSemantic',
            'extensions': 'return [".dart"]',
            'symbol_extraction': '''if 'class' in line or 'void' in line or 'Future' in line or 'Stream' in line:
                stripped = line.strip()
                if stripped and not stripped.startswith('//'):
                    # Extract Dart symbols
                    if 'class' in stripped:
                        parts = stripped.split()
                        idx = parts.index('class') if 'class' in parts else -1
                        if idx >= 0 and idx + 1 < len(parts):
                            name = parts[idx + 1].split()[0]
                            symbols.append({
                                'symbol': name,
                                'kind': 'class',
                                'signature': stripped,
                                'line': i + 1,
                                'end_line': i + 1,
                                'span': [i + 1, i + 1]
                            })'''
        },
        {
            'dir': 'html_css_plugin',
            'lang_code': 'html_css',
            'lang_display': 'HTML/CSS',
            'class_name': 'HtmlCssPluginSemantic',
            'extensions': 'return [".html", ".htm", ".css", ".scss", ".sass", ".less"]',
            'symbol_extraction': '''# HTML/CSS specific extraction
            # Check if line contains HTML tags
            if '<' in line and '>' in line:
                # Extract HTML IDs and classes
                import re
                for match in re.finditer(r'id=["\']([\w-]+)["\']', line):
                    symbols.append({
                        'symbol': f'#{match.group(1)}',
                        'kind': 'id',
                        'signature': line.strip(),
                        'line': i + 1,
                        'end_line': i + 1,
                        'span': [i + 1, i + 1]
                    })
                for match in re.finditer(r'class=["\']([\w-\s]+)["\']', line):
                    for cls in match.group(1).split():
                        symbols.append({
                            'symbol': f'.{cls}',
                            'kind': 'class',
                            'signature': line.strip(),
                            'line': i + 1,
                            'end_line': i + 1,
                            'span': [i + 1, i + 1]
                        })
            # Check if line contains CSS selectors
            elif '{' in line:
                # Extract CSS selectors
                stripped = line.strip()
                if stripped and not stripped.startswith('//') and not stripped.startswith('/*'):
                    selector = stripped.split('{')[0].strip()
                    if selector:
                        symbols.append({
                            'symbol': selector,
                            'kind': 'selector',
                            'signature': stripped,
                            'line': i + 1,
                            'end_line': i + 1,
                            'span': [i + 1, i + 1]
                        })'''
        }
    ]
    
    print("Creating semantic plugin versions...\n")
    
    for config in plugins_config:
        plugin_dir = plugins_dir / config['dir']
        if plugin_dir.exists():
            print(f"{config['lang_display']} Plugin:")
            create_semantic_plugin(
                plugin_dir,
                config['lang_code'],
                config['lang_display'],
                config['class_name'],
                config['extensions'],
                config['symbol_extraction']
            )
            print()
        else:
            print(f"Warning: {plugin_dir} does not exist")
    
    print("Done! All plugins now have semantic versions.")
    print("\nTo enable semantic search:")
    print("1. Set SEMANTIC_SEARCH_ENABLED=true")
    print("2. Ensure Voyage AI API key is set")
    print("3. Have Qdrant running (or use in-memory mode)")


if __name__ == "__main__":
    main()