"""
File resource handler for code://file/* URIs.

Provides access to indexed source files with syntax highlighting support,
partial file reading, and comprehensive metadata.
"""

import json
import mimetypes
from typing import List, Optional, Dict, Any
from pathlib import Path
from dataclasses import dataclass
import logging

from ...interfaces.mcp_interfaces import IMCPResource
from ...storage.sqlite_store import SQLiteStore
from ..registry import ResourceHandler, ResourceFilter

logger = logging.getLogger(__name__)

# Syntax highlighting language mappings
LANGUAGE_MAPPINGS = {
    '.py': 'python',
    '.js': 'javascript',
    '.ts': 'typescript',
    '.jsx': 'javascript',
    '.tsx': 'typescript',
    '.java': 'java',
    '.c': 'c',
    '.cpp': 'cpp',
    '.cc': 'cpp',
    '.cxx': 'cpp',
    '.h': 'c',
    '.hpp': 'cpp',
    '.cs': 'csharp',
    '.go': 'go',
    '.rs': 'rust',
    '.rb': 'ruby',
    '.php': 'php',
    '.swift': 'swift',
    '.kt': 'kotlin',
    '.scala': 'scala',
    '.r': 'r',
    '.m': 'objectivec',
    '.mm': 'objectivecpp',
    '.pl': 'perl',
    '.sh': 'bash',
    '.bash': 'bash',
    '.zsh': 'zsh',
    '.fish': 'fish',
    '.ps1': 'powershell',
    '.lua': 'lua',
    '.vim': 'vim',
    '.dart': 'dart',
    '.elm': 'elm',
    '.clj': 'clojure',
    '.ex': 'elixir',
    '.exs': 'elixir',
    '.erl': 'erlang',
    '.hrl': 'erlang',
    '.fs': 'fsharp',
    '.fsx': 'fsharp',
    '.fsi': 'fsharp',
    '.ml': 'ocaml',
    '.mli': 'ocaml',
    '.pas': 'pascal',
    '.pp': 'pascal',
    '.hs': 'haskell',
    '.lhs': 'haskell',
    '.jl': 'julia',
    '.nim': 'nim',
    '.nims': 'nim',
    '.cr': 'crystal',
    '.d': 'd',
    '.zig': 'zig',
    '.v': 'v',
    '.sv': 'systemverilog',
    '.svh': 'systemverilog',
    '.vhd': 'vhdl',
    '.vhdl': 'vhdl',
    '.sql': 'sql',
    '.html': 'html',
    '.htm': 'html',
    '.xml': 'xml',
    '.css': 'css',
    '.scss': 'scss',
    '.sass': 'sass',
    '.less': 'less',
    '.json': 'json',
    '.jsonc': 'jsonc',
    '.json5': 'json5',
    '.yaml': 'yaml',
    '.yml': 'yaml',
    '.toml': 'toml',
    '.ini': 'ini',
    '.cfg': 'ini',
    '.conf': 'conf',
    '.properties': 'properties',
    '.gradle': 'gradle',
    '.cmake': 'cmake',
    '.make': 'makefile',
    '.makefile': 'makefile',
    '.dockerfile': 'dockerfile',
    '.dockerignore': 'dockerfile',
    '.gitignore': 'gitignore',
    '.gitattributes': 'gitattributes',
    '.editorconfig': 'editorconfig',
    '.env': 'dotenv',
    '.md': 'markdown',
    '.markdown': 'markdown',
    '.rst': 'restructuredtext',
    '.tex': 'latex',
    '.bib': 'bibtex',
}

# Binary file extensions
BINARY_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico', '.svg',
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    '.zip', '.tar', '.gz', '.bz2', '.xz', '.7z', '.rar',
    '.exe', '.dll', '.so', '.dylib', '.lib', '.a', '.o',
    '.class', '.jar', '.war', '.ear',
    '.wasm', '.pyc', '.pyo',
    '.ttf', '.otf', '.woff', '.woff2', '.eot',
    '.mp3', '.mp4', '.avi', '.mkv', '.mov', '.wmv',
    '.sqlite', '.db', '.mdb',
}


@dataclass
class FileResource(IMCPResource):
    """Represents a file resource with comprehensive metadata."""
    
    uri: str
    path: str
    relative_path: str
    language: Optional[str] = None
    size: Optional[int] = None
    content: Optional[str] = None
    is_binary: bool = False
    line_count: Optional[int] = None
    encoding: str = 'utf-8'
    mime_type: Optional[str] = None
    syntax_language: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        """Initialize computed fields."""
        if self.metadata is None:
            self.metadata = {}
            
        # Determine syntax language if not set
        if not self.syntax_language and self.relative_path:
            ext = Path(self.relative_path).suffix.lower()
            self.syntax_language = LANGUAGE_MAPPINGS.get(ext, self.language)
            
        # Determine mime type if not set
        if not self.mime_type and self.relative_path:
            self.mime_type, _ = mimetypes.guess_type(self.relative_path)
            
        # Check if binary
        if self.relative_path:
            ext = Path(self.relative_path).suffix.lower()
            self.is_binary = ext in BINARY_EXTENSIONS
            
        # Count lines if content is provided
        if self.content and not self.is_binary:
            self.line_count = len(self.content.splitlines())
    
    def get_uri(self) -> str:
        """Get the resource URI."""
        return self.uri
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get comprehensive resource metadata."""
        meta = {
            "name": Path(self.relative_path).name,
            "path": self.path,
            "relative_path": self.relative_path,
            "type": "file",
            "is_binary": self.is_binary,
            "encoding": self.encoding,
        }
        
        if self.language:
            meta["language"] = self.language
        if self.syntax_language:
            meta["syntax_language"] = self.syntax_language
        if self.size is not None:
            meta["size"] = self.size
            meta["size_human"] = self._human_readable_size(self.size)
        if self.line_count is not None:
            meta["line_count"] = self.line_count
        if self.mime_type:
            meta["mime_type"] = self.mime_type
        if self.metadata:
            meta.update(self.metadata)
            
        return meta
    
    def _human_readable_size(self, size: int) -> str:
        """Convert size to human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"


class FileResourceHandler(ResourceHandler):
    """Handler for file resources with advanced features."""
    
    # Maximum file size for full content retrieval (10MB)
    MAX_FULL_CONTENT_SIZE = 10 * 1024 * 1024
    
    # Default chunk size for partial reads (64KB)
    DEFAULT_CHUNK_SIZE = 64 * 1024
    
    def __init__(self, storage: SQLiteStore):
        """
        Initialize the file resource handler.
        
        Args:
            storage: Storage backend for accessing files
        """
        super().__init__("code://file/")
        self.storage = storage
    
    async def get_resource(self, uri: str, start_line: Optional[int] = None, 
                         end_line: Optional[int] = None) -> Optional[IMCPResource]:
        """
        Get a file resource by URI with optional partial reading.
        
        Args:
            uri: Resource URI (e.g., code://file/src/main.py)
            start_line: Optional starting line number (1-based)
            end_line: Optional ending line number (1-based)
            
        Returns:
            FileResource or None if not found
        """
        # Extract relative path from URI
        if not uri.startswith(self.uri_pattern):
            return None
            
        relative_path = uri[len(self.uri_pattern):]
        
        # Handle query parameters if present
        if '?' in relative_path:
            relative_path, query = relative_path.split('?', 1)
            # Parse query parameters for line ranges
            params = {}
            for param in query.split('&'):
                if '=' in param:
                    key, value = param.split('=', 1)
                    params[key] = value
            
            if 'start' in params and start_line is None:
                try:
                    start_line = int(params['start'])
                except ValueError:
                    pass
            
            if 'end' in params and end_line is None:
                try:
                    end_line = int(params['end'])
                except ValueError:
                    pass
        
        try:
            # Query storage for file
            with self.storage._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT id, path, relative_path, language, size, hash, 
                           last_modified, metadata, repository_id
                    FROM files
                    WHERE relative_path = ? AND indexed_at IS NOT NULL
                """, (relative_path,))
                
                row = cursor.fetchone()
                if not row:
                    logger.warning(f"File not found: {relative_path}")
                    return None
                
                # Parse metadata
                metadata = {}
                if row['metadata']:
                    try:
                        metadata = json.loads(row['metadata'])
                    except json.JSONDecodeError:
                        logger.error(f"Invalid JSON in metadata for file {relative_path}")
                
                metadata.update({
                    'hash': row['hash'],
                    'last_modified': row['last_modified'],
                    'repository_id': row['repository_id']
                })
                
                # Check if file is binary
                ext = Path(relative_path).suffix.lower()
                is_binary = ext in BINARY_EXTENSIONS
                
                content = None
                if not is_binary:
                    # Get file content from FTS if available
                    if row['size'] and row['size'] <= self.MAX_FULL_CONTENT_SIZE:
                        content_cursor = conn.execute("""
                            SELECT content
                            FROM fts_code
                            WHERE file_id = ?
                            LIMIT 1
                        """, (row['id'],))
                        
                        content_row = content_cursor.fetchone()
                        if content_row:
                            content = content_row['content']
                            
                            # Apply line range if requested
                            if content and (start_line is not None or end_line is not None):
                                lines = content.splitlines(keepends=True)
                                start_idx = (start_line - 1) if start_line else 0
                                end_idx = end_line if end_line else len(lines)
                                content = ''.join(lines[start_idx:end_idx])
                                
                                # Update metadata to indicate partial content
                                metadata['partial_content'] = True
                                metadata['start_line'] = start_idx + 1
                                metadata['end_line'] = min(end_idx, len(lines))
                                metadata['total_lines'] = len(lines)
                    else:
                        # File too large, indicate partial content available
                        metadata['content_truncated'] = True
                        metadata['truncation_reason'] = 'file_too_large'
                        metadata['max_size'] = self.MAX_FULL_CONTENT_SIZE
                
                # Create and return resource
                return FileResource(
                    uri=uri,
                    path=row['path'],
                    relative_path=row['relative_path'],
                    language=row['language'],
                    size=row['size'],
                    content=content,
                    is_binary=is_binary,
                    metadata=metadata
                )
                
        except Exception as e:
            logger.error(f"Error retrieving file resource {uri}: {e}")
            return None
    
    async def list_resources(self, filter_options: Optional[ResourceFilter] = None) -> List[IMCPResource]:
        """
        List file resources with optional filtering.
        
        Args:
            filter_options: Optional filter criteria
            
        Returns:
            List of FileResource objects
        """
        resources = []
        
        try:
            with self.storage._get_connection() as conn:
                # Build query
                query = """
                    SELECT path, relative_path, language, size, hash, 
                           last_modified, metadata, repository_id
                    FROM files
                    WHERE indexed_at IS NOT NULL
                """
                params = []
                
                # Apply filters
                if filter_options:
                    conditions = []
                    
                    if filter_options.languages:
                        placeholders = ','.join(['?' for _ in filter_options.languages])
                        conditions.append(f"language IN ({placeholders})")
                        params.extend(filter_options.languages)
                    
                    if filter_options.min_size is not None:
                        conditions.append("size >= ?")
                        params.append(filter_options.min_size)
                    
                    if filter_options.max_size is not None:
                        conditions.append("size <= ?")
                        params.append(filter_options.max_size)
                    
                    if filter_options.name_pattern:
                        conditions.append("relative_path LIKE ?")
                        params.append(f"%{filter_options.name_pattern}%")
                    
                    if conditions:
                        query += " AND " + " AND ".join(conditions)
                
                # Add ordering
                query += " ORDER BY relative_path"
                
                cursor = conn.execute(query, params)
                
                for row in cursor:
                    uri = f"{self.uri_pattern}{row['relative_path']}"
                    
                    metadata = {}
                    if row['metadata']:
                        try:
                            metadata = json.loads(row['metadata'])
                        except json.JSONDecodeError:
                            logger.error(f"Invalid JSON in metadata for file {row['relative_path']}")
                    
                    metadata.update({
                        'hash': row['hash'],
                        'last_modified': row['last_modified'],
                        'repository_id': row['repository_id']
                    })
                    
                    # Check if binary
                    ext = Path(row['relative_path']).suffix.lower()
                    is_binary = ext in BINARY_EXTENSIONS
                    
                    resource = FileResource(
                        uri=uri,
                        path=row['path'],
                        relative_path=row['relative_path'],
                        language=row['language'],
                        size=row['size'],
                        is_binary=is_binary,
                        metadata=metadata
                    )
                    resources.append(resource)
                    
        except Exception as e:
            logger.error(f"Error listing file resources: {e}")
        
        return resources
    
    async def get_file_chunk(self, uri: str, offset: int = 0, 
                           size: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Get a chunk of file content for large files.
        
        Args:
            uri: Resource URI
            offset: Byte offset to start reading from
            size: Number of bytes to read (defaults to DEFAULT_CHUNK_SIZE)
            
        Returns:
            Dict with chunk data or None if error
        """
        if size is None:
            size = self.DEFAULT_CHUNK_SIZE
            
        resource = await self.get_resource(uri)
        if not resource or resource.is_binary:
            return None
            
        try:
            # Read directly from disk for large files
            with open(resource.path, 'r', encoding='utf-8') as f:
                f.seek(offset)
                chunk = f.read(size)
                
            return {
                'content': chunk,
                'offset': offset,
                'size': len(chunk),
                'total_size': resource.size,
                'has_more': offset + len(chunk) < resource.size
            }
        except Exception as e:
            logger.error(f"Error reading file chunk from {uri}: {e}")
            return None
