"""
Symbol resource handler for code://symbol/* URIs.

Provides access to code symbols (functions, classes, methods, variables, etc.)
with comprehensive metadata including type, signature, docstring, and relationships.
"""

import json
import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, parse_qs, urlparse

from ...interfaces.mcp_interfaces import IMCPResource
from ...storage.sqlite_store import SQLiteStore
from ..registry import ResourceHandler, ResourceFilter

logger = logging.getLogger(__name__)

# Symbol type mappings for different languages
SYMBOL_TYPE_ICONS = {
    'function': '🔧',
    'method': '📍',
    'class': '📦',
    'interface': '🔌',
    'enum': '🔢',
    'struct': '📋',
    'variable': '📝',
    'constant': '🔒',
    'property': '🏷️',
    'parameter': '📎',
    'module': '📁',
    'namespace': '🗂️',
    'trait': '🧬',
    'type': '🏷️',
    'field': '🔖',
    'constructor': '🏗️',
    'decorator': '🎨',
    'import': '📥',
    'export': '📤',
}


@dataclass
class SymbolResource(IMCPResource):
    """Represents a symbol resource with comprehensive metadata."""
    
    uri: str
    name: str
    qualified_name: str
    kind: str
    signature: Optional[str] = None
    docstring: Optional[str] = None
    file_path: str = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    start_column: Optional[int] = None
    end_column: Optional[int] = None
    language: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        """Initialize computed fields."""
        if self.metadata is None:
            self.metadata = {}
            
        # Add icon based on symbol type
        if self.kind and self.kind in SYMBOL_TYPE_ICONS:
            self.metadata['icon'] = SYMBOL_TYPE_ICONS[self.kind]
    
    def get_uri(self) -> str:
        """Get the resource URI."""
        return self.uri
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get comprehensive symbol metadata."""
        meta = {
            "name": self.name,
            "qualified_name": self.qualified_name,
            "type": "symbol",
            "kind": self.kind,
            "language": self.language,
        }
        
        if self.signature:
            meta["signature"] = self.signature
        if self.docstring:
            meta["docstring"] = self.docstring
        if self.file_path:
            meta["file_path"] = self.file_path
            meta["file_name"] = Path(self.file_path).name
        if self.start_line is not None:
            meta["location"] = {
                "start_line": self.start_line,
                "end_line": self.end_line,
                "start_column": self.start_column,
                "end_column": self.end_column
            }
        if self.metadata:
            meta.update(self.metadata)
            
        return meta


class SymbolResourceHandler(ResourceHandler):
    """Handler for symbol resources with advanced features."""
    
    def __init__(self, storage: SQLiteStore):
        """
        Initialize the symbol resource handler.
        
        Args:
            storage: Storage backend for accessing symbols
        """
        super().__init__("code://symbol/")
        self.storage = storage
    
    async def get_resource(self, uri: str) -> Optional[IMCPResource]:
        """
        Get a symbol resource by URI.
        
        URI formats supported:
        - code://symbol/MyClass
        - code://symbol/my_function
        - code://symbol/MyClass?file=/path/to/file.py
        - code://symbol/function?kind=function&language=python
        
        Args:
            uri: Resource URI
            
        Returns:
            SymbolResource or None if not found
        """
        if not uri.startswith(self.uri_pattern):
            return None
            
        # Parse URI
        parsed = urlparse(uri)
        # Handle the URI parsing correctly for code://symbol/name format
        if parsed.netloc == 'symbol' and parsed.path.startswith('/'):
            symbol_name = unquote(parsed.path[1:])
        else:
            symbol_name = unquote(parsed.path[len('/symbol/'):] if parsed.path.startswith('/symbol/') else parsed.path)
        
        # Parse query parameters
        query_params = parse_qs(parsed.query) if parsed.query else {}
        file_filter = query_params.get('file', [None])[0]
        kind_filter = query_params.get('kind', [None])[0]
        language_filter = query_params.get('language', [None])[0]
        
        try:
            # Query storage for symbol
            with self.storage._get_connection() as conn:
                # Build query based on available filters
                query = """
                    SELECT s.id, s.name, s.kind, s.signature, s.documentation,
                           s.line_start, s.line_end, s.column_start, s.column_end,
                           s.metadata,
                           f.path as file_path, f.relative_path, f.language
                    FROM symbols s
                    JOIN files f ON s.file_id = f.id
                    WHERE s.name = ?
                """
                params = [symbol_name]
                
                # Add optional filters
                if kind_filter:
                    query += " AND s.kind = ?"
                    params.append(kind_filter)
                
                if language_filter:
                    query += " AND f.language = ?"
                    params.append(language_filter)
                    
                if file_filter:
                    query += " AND (f.path = ? OR f.relative_path = ?)"
                    params.extend([file_filter, file_filter])
                
                # Limit to first match
                query += " LIMIT 1"
                
                cursor = conn.execute(query, params)
                row = cursor.fetchone()
                
                if not row:
                    logger.warning(f"Symbol not found: {symbol_name}")
                    return None
                
                # Parse metadata
                metadata = {}
                if row['metadata']:
                    try:
                        metadata = json.loads(row['metadata'])
                    except json.JSONDecodeError:
                        logger.error(f"Invalid JSON in metadata for symbol {symbol_name}")
                
                # Get references count
                ref_cursor = conn.execute(
                    "SELECT COUNT(*) as count FROM symbol_references WHERE symbol_id = ?",
                    (row['id'],)
                )
                ref_count_row = ref_cursor.fetchone()
                if ref_count_row:
                    metadata['reference_count'] = ref_count_row['count']
                
                # Create and return resource
                return SymbolResource(
                    uri=uri,
                    name=row['name'],
                    qualified_name=symbol_name,  # Use the requested name as qualified name
                    kind=row['kind'],
                    signature=row['signature'],
                    docstring=row['documentation'],
                    file_path=row['file_path'],
                    start_line=row['line_start'],
                    end_line=row['line_end'],
                    start_column=row['column_start'],
                    end_column=row['column_end'],
                    language=row['language'],
                    metadata=metadata
                )
                
        except Exception as e:
            logger.error(f"Error retrieving symbol resource {uri}: {e}")
            return None
    
    async def list_resources(self, filter_options: Optional[ResourceFilter] = None) -> List[IMCPResource]:
        """
        List symbol resources with optional filtering.
        
        Args:
            filter_options: Optional filter criteria
            
        Returns:
            List of SymbolResource objects
        """
        resources = []
        
        try:
            with self.storage._get_connection() as conn:
                # Build query
                query = """
                    SELECT s.id, s.name, s.kind, s.signature, s.documentation,
                           s.line_start, s.line_end, s.column_start, s.column_end,
                           s.metadata,
                           f.path as file_path, f.relative_path, f.language
                    FROM symbols s
                    JOIN files f ON s.file_id = f.id
                    WHERE 1=1
                """
                params = []
                
                # Apply filters
                if filter_options:
                    conditions = []
                    
                    if filter_options.languages:
                        placeholders = ','.join(['?' for _ in filter_options.languages])
                        conditions.append(f"f.language IN ({placeholders})")
                        params.extend(filter_options.languages)
                    
                    if filter_options.name_pattern:
                        conditions.append("s.name LIKE ?")
                        params.append(f"%{filter_options.name_pattern}%")
                    
                    # Support filtering by symbol type via tags
                    if filter_options.tags:
                        kind_conditions = []
                        for tag in filter_options.tags:
                            if tag in SYMBOL_TYPE_ICONS:
                                kind_conditions.append("s.kind = ?")
                                params.append(tag)
                        if kind_conditions:
                            conditions.append(f"({' OR '.join(kind_conditions)})")
                    
                    if conditions:
                        query += " AND " + " AND ".join(conditions)
                
                # Add ordering
                query += " ORDER BY s.name, f.relative_path"
                
                # Add limit for performance
                query += " LIMIT 1000"
                
                cursor = conn.execute(query, params)
                
                # Track seen symbols to avoid duplicates
                seen_symbols = set()
                
                for row in cursor:
                    # Create unique key
                    symbol_key = f"{row['name']}:{row['file_path']}:{row['kind']}"
                    if symbol_key in seen_symbols:
                        continue
                    seen_symbols.add(symbol_key)
                    
                    # Parse metadata
                    metadata = {}
                    if row['metadata']:
                        try:
                            metadata = json.loads(row['metadata'])
                        except json.JSONDecodeError:
                            logger.error(f"Invalid JSON in metadata for symbol {row['name']}")
                    
                    uri = f"{self.uri_pattern}{row['name']}"
                    
                    resource = SymbolResource(
                        uri=uri,
                        name=row['name'],
                        qualified_name=row['name'],
                        kind=row['kind'],
                        signature=row['signature'],
                        docstring=row['documentation'],
                        file_path=row['file_path'],
                        start_line=row['line_start'],
                        end_line=row['line_end'],
                        start_column=row['column_start'],
                        end_column=row['column_end'],
                        language=row['language'],
                        metadata=metadata
                    )
                    resources.append(resource)
                    
        except Exception as e:
            logger.error(f"Error listing symbol resources: {e}")
        
        return resources
    
    async def get_symbol_references(self, uri: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get all references to a symbol.
        
        Args:
            uri: Symbol resource URI
            
        Returns:
            List of reference locations or None if error
        """
        resource = await self.get_resource(uri)
        if not resource:
            return None
            
        try:
            with self.storage._get_connection() as conn:
                # Get symbol ID
                cursor = conn.execute("""
                    SELECT s.id 
                    FROM symbols s
                    JOIN files f ON s.file_id = f.id
                    WHERE s.name = ? AND f.path = ?
                """, (resource.name, resource.file_path))
                
                row = cursor.fetchone()
                if not row:
                    return []
                
                symbol_id = row['id']
                
                # Get all references
                ref_cursor = conn.execute("""
                    SELECT r.line_number, r.column_number, r.reference_kind,
                           f.path as file_path, f.relative_path
                    FROM symbol_references r
                    JOIN files f ON r.file_id = f.id
                    WHERE r.symbol_id = ?
                    ORDER BY f.relative_path, r.line_number, r.column_number
                """, (symbol_id,))
                
                references = []
                for ref_row in ref_cursor:
                    references.append({
                        'file_path': ref_row['file_path'],
                        'relative_path': ref_row['relative_path'],
                        'line': ref_row['line_number'],
                        'column': ref_row['column_number'],
                        'kind': ref_row['reference_kind'],
                        'uri': f"code://file/{ref_row['relative_path']}?line={ref_row['line_number']}"
                    })
                
                return references
                
        except Exception as e:
            logger.error(f"Error getting symbol references for {uri}: {e}")
            return None
