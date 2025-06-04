"""
Resource registry for MCP.

Manages available resources and their metadata.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
import json

from ..interfaces.mcp_interfaces import IMCPResource
from ..interfaces.shared_interfaces import Result, Error
from ..storage.sqlite_store import SQLiteStore

logger = logging.getLogger(__name__)


@dataclass
class ResourceMetadata:
    """Metadata for a registered resource."""
    uri: str
    name: str
    description: Optional[str] = None
    mime_type: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    size: Optional[int] = None
    language: Optional[str] = None
    extra_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResourceFilter:
    """Filter criteria for resource queries."""
    mime_types: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    languages: Optional[List[str]] = None
    name_pattern: Optional[str] = None
    uri_pattern: Optional[str] = None
    min_size: Optional[int] = None
    max_size: Optional[int] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None


@dataclass 
class PaginationOptions:
    """Pagination options for resource listings."""
    page: int = 1
    page_size: int = 50
    sort_by: str = "name"
    sort_order: str = "asc"


class ResourceHandler:
    """Base class for resource handlers."""
    
    def __init__(self, uri_pattern: str):
        self.uri_pattern = uri_pattern
    
    async def can_handle(self, uri: str) -> bool:
        """Check if this handler can handle the given URI."""
        # Simple pattern matching - can be extended
        return uri.startswith(self.uri_pattern)
    
    async def get_resource(self, uri: str) -> Optional[IMCPResource]:
        """Get resource for the given URI."""
        raise NotImplementedError
    
    async def list_resources(self, filter_options: Optional[ResourceFilter] = None) -> List[IMCPResource]:
        """List resources this handler manages."""
        raise NotImplementedError


class ResourceRegistry:
    """
    Central registry for managing MCP resources.
    
    This registry manages resource handlers, discovers available resources,
    provides filtering and pagination, and integrates with storage and caching.
    """
    
    def __init__(self, storage: Optional[SQLiteStore] = None, cache_manager: Optional[Any] = None):
        """
        Initialize the resource registry.
        
        Args:
            storage: Storage backend for discovering resources
            cache_manager: Cache manager for resource listings
        """
        self.storage = storage or SQLiteStore()
        self.cache = cache_manager
        self.handlers: Dict[str, ResourceHandler] = {}
        self.resource_metadata: Dict[str, ResourceMetadata] = {}
        self._discovery_tasks: Set[asyncio.Task] = set()
        self._initialized = False
        
    async def initialize(self) -> Result[None]:
        """Initialize the registry and start resource discovery."""
        try:
            if self._initialized:
                return Result.success_result(None)
                
            # Initialize built-in resource handlers
            await self._register_builtin_handlers()
            
            # Start initial resource discovery
            await self.discover_resources()
            
            self._initialized = True
            logger.info("Resource registry initialized successfully")
            return Result.success_result(None)
            
        except Exception as e:
            logger.error(f"Failed to initialize resource registry: {e}")
            return Result.error_result(
                Error(
                    code="REGISTRY_INIT_ERROR",
                    message=str(e),
                    details={"exception": type(e).__name__},
                    timestamp=datetime.now()
                )
            )
    
    async def shutdown(self) -> Result[None]:
        """Shutdown the registry and cancel discovery tasks."""
        try:
            # Cancel all discovery tasks
            for task in self._discovery_tasks:
                if not task.done():
                    task.cancel()
                    
            # Wait for cancellation
            if self._discovery_tasks:
                await asyncio.gather(*self._discovery_tasks, return_exceptions=True)
                
            self._discovery_tasks.clear()
            self._initialized = False
            
            logger.info("Resource registry shutdown successfully")
            return Result.success_result(None)
            
        except Exception as e:
            logger.error(f"Error during registry shutdown: {e}")
            return Result.error_result(
                Error(
                    code="REGISTRY_SHUTDOWN_ERROR", 
                    message=str(e),
                    details={"exception": type(e).__name__},
                    timestamp=datetime.now()
                )
            )
    
    def register_handler(self, uri_pattern: str, handler: ResourceHandler) -> Result[None]:
        """
        Register a resource handler for a URI pattern.
        
        Args:
            uri_pattern: URI pattern this handler manages (e.g., "code://file/")
            handler: The resource handler instance
            
        Returns:
            Result indicating success or failure
        """
        try:
            if uri_pattern in self.handlers:
                logger.warning(f"Overwriting existing handler for pattern: {uri_pattern}")
                
            self.handlers[uri_pattern] = handler
            logger.info(f"Registered resource handler for pattern: {uri_pattern}")
            
            # Trigger discovery for this handler
            if self._initialized:
                task = asyncio.create_task(self._discover_handler_resources(handler))
                self._discovery_tasks.add(task)
                task.add_done_callback(self._discovery_tasks.discard)
            
            return Result.success_result(None)
            
        except Exception as e:
            logger.error(f"Failed to register handler for {uri_pattern}: {e}")
            return Result.error_result(
                Error(
                    code="HANDLER_REGISTRATION_ERROR",
                    message=str(e),
                    details={"pattern": uri_pattern},
                    timestamp=datetime.now()
                )
            )
    
    def unregister_handler(self, uri_pattern: str) -> Result[None]:
        """
        Unregister a resource handler.
        
        Args:
            uri_pattern: URI pattern to unregister
            
        Returns:
            Result indicating success or failure
        """
        try:
            if uri_pattern not in self.handlers:
                return Result.error_result(
                    Error(
                        code="HANDLER_NOT_FOUND",
                        message=f"No handler registered for pattern: {uri_pattern}",
                        details={"pattern": uri_pattern},
                        timestamp=datetime.now()
                    )
                )
            
            del self.handlers[uri_pattern]
            
            # Remove associated metadata
            uris_to_remove = [uri for uri in self.resource_metadata if uri.startswith(uri_pattern)]
            for uri in uris_to_remove:
                del self.resource_metadata[uri]
            
            logger.info(f"Unregistered handler for pattern: {uri_pattern}")
            return Result.success_result(None)
            
        except Exception as e:
            logger.error(f"Failed to unregister handler for {uri_pattern}: {e}")
            return Result.error_result(
                Error(
                    code="HANDLER_UNREGISTRATION_ERROR",
                    message=str(e),
                    details={"pattern": uri_pattern},
                    timestamp=datetime.now()
                )
            )
    
    async def list_resources(
        self,
        filter_options: Optional[ResourceFilter] = None,
        pagination: Optional[PaginationOptions] = None
    ) -> Result[Tuple[List[ResourceMetadata], int]]:
        """
        List resources with filtering and pagination.
        
        Args:
            filter_options: Optional filtering criteria
            pagination: Optional pagination options
            
        Returns:
            Result containing tuple of (resources, total_count)
        """
        try:
            # Check cache first
            cache_key = self._generate_cache_key(filter_options, pagination)
            if self.cache:
                cached_result = await self.cache.get(cache_key)
                if cached_result:
                    return Result.success_result(cached_result)
            
            # Get all resources
            all_resources = list(self.resource_metadata.values())
            
            # Apply filters
            if filter_options:
                all_resources = self._apply_filters(all_resources, filter_options)
            
            total_count = len(all_resources)
            
            # Apply sorting
            if pagination:
                all_resources = self._apply_sorting(all_resources, pagination)
            
            # Apply pagination
            if pagination:
                start_idx = (pagination.page - 1) * pagination.page_size
                end_idx = start_idx + pagination.page_size
                all_resources = all_resources[start_idx:end_idx]
            
            result = (all_resources, total_count)
            
            # Cache the result
            if self.cache:
                await self.cache.set(cache_key, result, ttl=300)  # 5 minute TTL
            
            return Result.success_result(result)
            
        except Exception as e:
            logger.error(f"Failed to list resources: {e}")
            return Result.error_result(
                Error(
                    code="RESOURCE_LIST_ERROR",
                    message=str(e),
                    details={"exception": type(e).__name__},
                    timestamp=datetime.now()
                )
            )
    
    async def get_resource(self, uri: str) -> Result[Optional[IMCPResource]]:
        """
        Get a specific resource by URI.
        
        Args:
            uri: Resource URI
            
        Returns:
            Result containing the resource or None if not found
        """
        try:
            # Find appropriate handler
            for pattern, handler in self.handlers.items():
                if await handler.can_handle(uri):
                    resource = await handler.get_resource(uri)
                    return Result.success_result(resource)
            
            return Result.success_result(None)
            
        except Exception as e:
            logger.error(f"Failed to get resource {uri}: {e}")
            return Result.error_result(
                Error(
                    code="RESOURCE_GET_ERROR",
                    message=str(e),
                    details={"uri": uri},
                    timestamp=datetime.now()
                )
            )
    
    async def get_resource_metadata(self, uri: str) -> Result[Optional[ResourceMetadata]]:
        """
        Get metadata for a specific resource.
        
        Args:
            uri: Resource URI
            
        Returns:
            Result containing the metadata or None if not found
        """
        try:
            metadata = self.resource_metadata.get(uri)
            return Result.success_result(metadata)
            
        except Exception as e:
            logger.error(f"Failed to get metadata for {uri}: {e}")
            return Result.error_result(
                Error(
                    code="METADATA_GET_ERROR",
                    message=str(e),
                    details={"uri": uri},
                    timestamp=datetime.now()
                )
            )
    
    async def update_resource_metadata(self, uri: str, metadata: ResourceMetadata) -> Result[None]:
        """
        Update metadata for a resource.
        
        Args:
            uri: Resource URI
            metadata: Updated metadata
            
        Returns:
            Result indicating success or failure
        """
        try:
            metadata.updated_at = datetime.now()
            self.resource_metadata[uri] = metadata
            
            # Invalidate cache
            if self.cache:
                await self.cache.invalidate_pattern("resource_list:*")
            
            return Result.success_result(None)
            
        except Exception as e:
            logger.error(f"Failed to update metadata for {uri}: {e}")
            return Result.error_result(
                Error(
                    code="METADATA_UPDATE_ERROR",
                    message=str(e),
                    details={"uri": uri},
                    timestamp=datetime.now()
                )
            )
    
    async def discover_resources(self) -> Result[int]:
        """
        Discover resources from workspace content via storage.
        
        Returns:
            Result containing the number of discovered resources
        """
        try:
            discovered_count = 0
            
            # Discover from storage
            if self.storage:
                storage_result = await self._discover_storage_resources()
                if storage_result.success:
                    discovered_count += storage_result.value
            
            # Discover from handlers
            handler_tasks = []
            for handler in self.handlers.values():
                task = asyncio.create_task(self._discover_handler_resources(handler))
                handler_tasks.append(task)
                self._discovery_tasks.add(task)
                task.add_done_callback(self._discovery_tasks.discard)
            
            if handler_tasks:
                results = await asyncio.gather(*handler_tasks, return_exceptions=True)
                for result in results:
                    if isinstance(result, Result) and result.success:
                        discovered_count += result.value
            
            logger.info(f"Discovered {discovered_count} resources")
            return Result.success_result(discovered_count)
            
        except Exception as e:
            logger.error(f"Failed to discover resources: {e}")
            return Result.error_result(
                Error(
                    code="DISCOVERY_ERROR",
                    message=str(e),
                    details={"exception": type(e).__name__},
                    timestamp=datetime.now()
                )
            )
    
    async def _register_builtin_handlers(self):
        """Register built-in resource handlers."""
        # Import here to avoid circular imports
        from .handlers.file import FileResourceHandler
        from .handlers.symbol import SymbolResourceHandler
        
        # Register handlers
        self.register_handler("code://file/", FileResourceHandler(self.storage))
        
        # TODO: Register other handlers when implemented
        self.register_handler("code://symbol/", SymbolResourceHandler(self.storage))
        # self.register_handler("code://project/", ProjectResourceHandler(self.storage))
        # self.register_handler("code://search/", SearchResourceHandler(self.storage))
    
    async def _discover_storage_resources(self) -> Result[int]:
        """Discover resources from storage backend."""
        try:
            count = 0
            
            # Discover files
            with self.storage._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT path, relative_path, language, size, last_modified
                    FROM files
                    WHERE indexed_at IS NOT NULL
                """)
                
                for row in cursor:
                    uri = f"code://file/{row['relative_path']}"
                    metadata = ResourceMetadata(
                        uri=uri,
                        name=Path(row['relative_path']).name,
                        description=f"Source file: {row['relative_path']}",
                        mime_type=self._get_mime_type(row['language']),
                        language=row['language'],
                        size=row['size'],
                        tags=["file", row['language']] if row['language'] else ["file"],
                        created_at=datetime.fromisoformat(row['last_modified']) if row['last_modified'] else datetime.now()
                    )
                    self.resource_metadata[uri] = metadata
                    count += 1
            
            # Discover symbols
            with self.storage._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT s.name, s.kind, f.relative_path, f.language
                    FROM symbols s
                    JOIN files f ON s.file_id = f.id
                """)
                
                for row in cursor:
                    uri = f"code://symbol/{row['relative_path']}/{row['name']}"
                    metadata = ResourceMetadata(
                        uri=uri,
                        name=row['name'],
                        description=f"{row['kind']} in {row['relative_path']}",
                        tags=["symbol", row['kind'], row['language']] if row['language'] else ["symbol", row['kind']],
                        language=row['language']
                    )
                    self.resource_metadata[uri] = metadata
                    count += 1
            
            return Result.success_result(count)
            
        except Exception as e:
            logger.error(f"Failed to discover storage resources: {e}")
            return Result.error_result(
                Error(
                    code="STORAGE_DISCOVERY_ERROR",
                    message=str(e),
                    details={"exception": type(e).__name__},
                    timestamp=datetime.now()
                )
            )
    
    async def _discover_handler_resources(self, handler: ResourceHandler) -> Result[int]:
        """Discover resources from a specific handler."""
        try:
            resources = await handler.list_resources()
            count = 0
            
            for resource in resources:
                uri = resource.get_uri()
                metadata_dict = resource.get_metadata()
                
                metadata = ResourceMetadata(
                    uri=uri,
                    name=metadata_dict.get("name", Path(uri).name),
                    description=metadata_dict.get("description"),
                    mime_type=metadata_dict.get("mime_type"),
                    tags=metadata_dict.get("tags", []),
                    language=metadata_dict.get("language"),
                    size=metadata_dict.get("size"),
                    extra_metadata=metadata_dict
                )
                
                self.resource_metadata[uri] = metadata
                count += 1
            
            return Result.success_result(count)
            
        except Exception as e:
            logger.error(f"Failed to discover handler resources: {e}")
            return Result.error_result(
                Error(
                    code="HANDLER_DISCOVERY_ERROR",
                    message=str(e),
                    details={"handler": type(handler).__name__},
                    timestamp=datetime.now()
                )
            )
    
    def _apply_filters(self, resources: List[ResourceMetadata], filter_options: ResourceFilter) -> List[ResourceMetadata]:
        """Apply filters to resource list."""
        filtered = resources
        
        if filter_options.mime_types:
            filtered = [r for r in filtered if r.mime_type in filter_options.mime_types]
        
        if filter_options.tags:
            filter_tags = set(filter_options.tags)
            filtered = [r for r in filtered if filter_tags.intersection(set(r.tags))]
        
        if filter_options.languages:
            filtered = [r for r in filtered if r.language in filter_options.languages]
        
        if filter_options.name_pattern:
            import re
            pattern = re.compile(filter_options.name_pattern, re.IGNORECASE)
            filtered = [r for r in filtered if pattern.search(r.name)]
        
        if filter_options.uri_pattern:
            import re
            pattern = re.compile(filter_options.uri_pattern)
            filtered = [r for r in filtered if pattern.search(r.uri)]
        
        if filter_options.min_size is not None:
            filtered = [r for r in filtered if r.size is not None and r.size >= filter_options.min_size]
        
        if filter_options.max_size is not None:
            filtered = [r for r in filtered if r.size is not None and r.size <= filter_options.max_size]
        
        if filter_options.created_after:
            filtered = [r for r in filtered if r.created_at >= filter_options.created_after]
        
        if filter_options.created_before:
            filtered = [r for r in filtered if r.created_at <= filter_options.created_before]
        
        return filtered
    
    def _apply_sorting(self, resources: List[ResourceMetadata], pagination: PaginationOptions) -> List[ResourceMetadata]:
        """Apply sorting to resource list."""
        reverse = pagination.sort_order == "desc"
        
        if pagination.sort_by == "name":
            return sorted(resources, key=lambda r: r.name.lower(), reverse=reverse)
        elif pagination.sort_by == "uri":
            return sorted(resources, key=lambda r: r.uri, reverse=reverse)
        elif pagination.sort_by == "created_at":
            return sorted(resources, key=lambda r: r.created_at, reverse=reverse)
        elif pagination.sort_by == "updated_at":
            return sorted(resources, key=lambda r: r.updated_at, reverse=reverse)
        elif pagination.sort_by == "size":
            return sorted(resources, key=lambda r: r.size or 0, reverse=reverse)
        else:
            return resources
    
    def _generate_cache_key(self, filter_options: Optional[ResourceFilter], pagination: Optional[PaginationOptions]) -> str:
        """Generate cache key for resource listings."""
        key_parts = ["resource_list"]
        
        if filter_options:
            filter_dict = {
                "mime_types": sorted(filter_options.mime_types) if filter_options.mime_types else None,
                "tags": sorted(filter_options.tags) if filter_options.tags else None,
                "languages": sorted(filter_options.languages) if filter_options.languages else None,
                "name_pattern": filter_options.name_pattern,
                "uri_pattern": filter_options.uri_pattern,
                "min_size": filter_options.min_size,
                "max_size": filter_options.max_size,
                "created_after": filter_options.created_after.isoformat() if filter_options.created_after else None,
                "created_before": filter_options.created_before.isoformat() if filter_options.created_before else None,
            }
            key_parts.append(hashlib.md5(json.dumps(filter_dict, sort_keys=True).encode()).hexdigest())
        
        if pagination:
            key_parts.extend([
                str(pagination.page),
                str(pagination.page_size),
                pagination.sort_by,
                pagination.sort_order
            ])
        
        return ":".join(key_parts)
    
    def _get_mime_type(self, language: Optional[str]) -> Optional[str]:
        """Get MIME type for a language."""
        mime_map = {
            "python": "text/x-python",
            "javascript": "text/javascript",
            "typescript": "text/typescript",
            "java": "text/x-java",
            "c": "text/x-c",
            "cpp": "text/x-c++",
            "go": "text/x-go",
            "rust": "text/x-rust",
            "html": "text/html",
            "css": "text/css",
            "markdown": "text/markdown",
            "json": "application/json",
            "yaml": "text/yaml",
            "xml": "text/xml",
        }
        return mime_map.get(language.lower()) if language else None