"""MCP Resource Manager - manages code resources"""
from typing import List, Dict, Any, Optional, Set, Callable
from dataclasses import dataclass, asdict
import json
import logging
from pathlib import Path
import mimetypes

from .base import (
    MCPResource, MCPResourceContent, ResourceType,
    create_file_resource, create_symbol_resource, 
    create_search_resource, create_index_resource
)
from ..protocol.jsonrpc import JSONRPCError, JSONRPCErrorCode

logger = logging.getLogger(__name__)

class ResourceManager:
    """Manages MCP resources for code indexing"""
    
    def __init__(self, storage=None, dispatcher=None):
        """
        Initialize resource manager
        
        Args:
            storage: Storage instance for data access
            dispatcher: Dispatcher instance for code operations
        """
        self.storage = storage
        self.dispatcher = dispatcher
        self.subscriptions: Dict[str, Set[str]] = {}  # resource_uri -> set of session_ids
        self.subscription_callbacks: Dict[str, Callable] = {}
        self.base_path = Path.cwd()  # Base path for relative file paths
    
    def set_base_path(self, path: str):
        """Set base path for relative file display"""
        self.base_path = Path(path)
    
    async def list_resources(self, cursor: Optional[str] = None) -> Dict[str, Any]:
        """
        List available resources
        
        Args:
            cursor: Optional pagination cursor
            
        Returns:
            Dictionary with resources list and optional next cursor
        """
        resources = []
        
        try:
            # Add dynamic resources (always available)
            resources.extend([
                create_search_resource(),
                create_index_resource()
            ])
            
            if self.storage:
                # Get indexed files
                limit = 50
                offset = int(cursor) if cursor else 0
                
                files = await self.storage.get_indexed_files(
                    offset=offset,
                    limit=limit
                )
                
                for file_info in files:
                    resource = create_file_resource(
                        file_info.path,
                        str(self.base_path)
                    )
                    
                    # Add additional metadata
                    resource.metadata.update({
                        "lastModified": file_info.last_modified.isoformat() if hasattr(file_info, 'last_modified') else None,
                        "symbolCount": getattr(file_info, 'symbol_count', 0),
                        "language": getattr(file_info, 'language', None),
                        "size": getattr(file_info, 'size', 0)
                    })
                    
                    resources.append(resource)
                
                # Get recent symbols
                symbols = await self.storage.get_recent_symbols(limit=20)
                for symbol_info in symbols:
                    resource = create_symbol_resource(
                        name=symbol_info.name,
                        kind=symbol_info.kind,
                        file_path=symbol_info.file_path,
                        line=symbol_info.line,
                        language=getattr(symbol_info, 'language', None)
                    )
                    resources.append(resource)
                
                # Calculate next cursor
                next_cursor = str(offset + limit) if len(files) == limit else None
            else:
                next_cursor = None
            
            # Convert resources to dictionaries
            result = {
                "resources": [r.to_dict() for r in resources]
            }
            
            if next_cursor:
                result["nextCursor"] = next_cursor
            
            return result
            
        except Exception as e:
            logger.error(f"Error listing resources: {e}", exc_info=True)
            raise JSONRPCError(
                code=JSONRPCErrorCode.INTERNAL_ERROR,
                message=f"Failed to list resources: {str(e)}"
            )
    
    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """
        Read a specific resource
        
        Args:
            uri: Resource URI
            
        Returns:
            Resource content dictionary
        """
        try:
            if uri.startswith("code://file/"):
                return await self._read_file_resource(uri)
            elif uri.startswith("code://symbol/"):
                return await self._read_symbol_resource(uri)
            elif uri == "code://search":
                return await self._read_search_resource()
            elif uri == "code://index":
                return await self._read_index_resource()
            else:
                raise JSONRPCError(
                    code=JSONRPCErrorCode.INVALID_PARAMS,
                    message=f"Unknown resource URI: {uri}"
                )
                
        except JSONRPCError:
            raise
        except Exception as e:
            logger.error(f"Error reading resource {uri}: {e}", exc_info=True)
            raise JSONRPCError(
                code=JSONRPCErrorCode.INTERNAL_ERROR,
                message=f"Failed to read resource: {str(e)}"
            )
    
    async def _read_file_resource(self, uri: str) -> Dict[str, Any]:
        """Read file resource content"""
        file_path = uri[len("code://file/"):]
        
        if not self.storage:
            raise JSONRPCError(
                code=JSONRPCErrorCode.INTERNAL_ERROR,
                message="Storage not available"
            )
        
        # Get file content from storage
        content_info = await self.storage.get_file_content(file_path)
        
        if not content_info:
            raise JSONRPCError(
                code=JSONRPCErrorCode.INVALID_PARAMS,
                message=f"File not found: {file_path}"
            )
        
        mime_type = mimetypes.guess_type(file_path)[0] or "text/plain"
        
        content = MCPResourceContent(
            uri=uri,
            mimeType=mime_type,
            text=content_info.content,
            metadata={
                "encoding": getattr(content_info, 'encoding', 'utf-8'),
                "lastIndexed": getattr(content_info, 'last_indexed', None),
                "language": getattr(content_info, 'language', None),
                "symbols": getattr(content_info, 'symbol_count', 0)
            }
        )
        
        return content.to_dict()
    
    async def _read_symbol_resource(self, uri: str) -> Dict[str, Any]:
        """Read symbol resource content"""
        symbol_name = uri[len("code://symbol/"):]
        
        if not self.dispatcher:
            raise JSONRPCError(
                code=JSONRPCErrorCode.INTERNAL_ERROR,
                message="Dispatcher not available"
            )
        
        # Look up symbol
        symbol_info = await self.dispatcher.lookup(symbol_name)
        
        if not symbol_info:
            raise JSONRPCError(
                code=JSONRPCErrorCode.INVALID_PARAMS,
                message=f"Symbol not found: {symbol_name}"
            )
        
        # Create JSON representation
        symbol_data = {
            "name": symbol_info.name,
            "kind": symbol_info.kind,
            "signature": getattr(symbol_info, 'signature', None),
            "docstring": getattr(symbol_info, 'docstring', None),
            "file": str(symbol_info.file),
            "line": symbol_info.line,
            "column": symbol_info.column,
            "language": getattr(symbol_info, 'language', None),
            "scope": getattr(symbol_info, 'scope', None),
            "references": getattr(symbol_info, 'reference_count', 0)
        }
        
        content = MCPResourceContent(
            uri=uri,
            mimeType="application/json",
            text=json.dumps(symbol_data, indent=2),
            metadata={
                "language": symbol_data.get("language")
            }
        )
        
        return content.to_dict()
    
    async def _read_search_resource(self) -> Dict[str, Any]:
        """Read search resource (instructions)"""
        search_info = {
            "description": "Use the search_code tool to search through indexed code",
            "tools": {
                "search_code": {
                    "description": "Search for code patterns",
                    "example": {
                        "name": "search_code",
                        "arguments": {
                            "query": "function definition",
                            "semantic": True,
                            "limit": 10
                        }
                    }
                }
            },
            "capabilities": {
                "textSearch": True,
                "semanticSearch": self.dispatcher is not None,
                "regexSearch": True,
                "languageFilter": True,
                "filePatternFilter": True
            }
        }
        
        content = MCPResourceContent(
            uri="code://search",
            mimeType="application/json",
            text=json.dumps(search_info, indent=2)
        )
        
        return content.to_dict()
    
    async def _read_index_resource(self) -> Dict[str, Any]:
        """Read index status resource"""
        if not self.storage:
            index_info = {
                "status": "unavailable",
                "message": "Storage not configured"
            }
        else:
            # Get index statistics
            stats = await self.storage.get_index_statistics()
            
            index_info = {
                "status": "active",
                "statistics": {
                    "totalFiles": getattr(stats, 'total_files', 0),
                    "totalSymbols": getattr(stats, 'total_symbols', 0),
                    "totalLines": getattr(stats, 'total_lines', 0),
                    "languages": getattr(stats, 'languages', {}),
                    "lastUpdate": getattr(stats, 'last_update', None)
                },
                "capabilities": {
                    "incrementalIndexing": True,
                    "fileWatching": True,
                    "parallelIndexing": True
                }
            }
        
        content = MCPResourceContent(
            uri="code://index",
            mimeType="application/json",
            text=json.dumps(index_info, indent=2)
        )
        
        return content.to_dict()
    
    def subscribe(self, uri: str, session_id: str):
        """
        Subscribe to resource changes
        
        Args:
            uri: Resource URI to subscribe to
            session_id: Session ID of subscriber
        """
        if uri not in self.subscriptions:
            self.subscriptions[uri] = set()
        
        self.subscriptions[uri].add(session_id)
        logger.debug(f"Session {session_id} subscribed to {uri}")
    
    def unsubscribe(self, uri: str, session_id: str):
        """
        Unsubscribe from resource changes
        
        Args:
            uri: Resource URI to unsubscribe from
            session_id: Session ID of subscriber
        """
        if uri in self.subscriptions:
            self.subscriptions[uri].discard(session_id)
            if not self.subscriptions[uri]:
                del self.subscriptions[uri]
        
        logger.debug(f"Session {session_id} unsubscribed from {uri}")
    
    def unsubscribe_all(self, session_id: str):
        """
        Unsubscribe session from all resources
        
        Args:
            session_id: Session ID to unsubscribe
        """
        for uri in list(self.subscriptions.keys()):
            self.unsubscribe(uri, session_id)
    
    async def notify_resource_change(self, uri: str, change_type: str = "updated"):
        """
        Notify subscribers of resource change
        
        Args:
            uri: Resource URI that changed
            change_type: Type of change (updated, deleted, etc.)
        """
        if uri in self.subscriptions and self.subscriptions[uri]:
            # Get callback for notifications
            if uri in self.subscription_callbacks:
                callback = self.subscription_callbacks[uri]
                for session_id in self.subscriptions[uri]:
                    try:
                        await callback(session_id, uri, change_type)
                    except Exception as e:
                        logger.error(f"Error notifying {session_id} about {uri}: {e}")
    
    def set_subscription_callback(self, uri: str, callback: Callable):
        """
        Set callback for resource subscription notifications
        
        Args:
            uri: Resource URI
            callback: Async function(session_id, uri, change_type)
        """
        self.subscription_callbacks[uri] = callback
    
    async def get_resource_dependencies(self, uri: str) -> List[str]:
        """
        Get dependencies for a resource
        
        Args:
            uri: Resource URI
            
        Returns:
            List of dependent resource URIs
        """
        dependencies = []
        
        if uri.startswith("code://file/"):
            # File might depend on other files (imports, includes)
            file_path = uri[len("code://file/"):]
            if self.dispatcher:
                deps = await self.dispatcher.get_file_dependencies(file_path)
                dependencies.extend([f"code://file/{dep}" for dep in deps])
        
        return dependencies