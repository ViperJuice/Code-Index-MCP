"""
Example usage of ResourceRegistry in MCP server components.
"""

from mcp_server.resources import ResourceRegistry, ResourceFilter, PaginationOptions
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.cache.cache_manager import CacheManagerFactory


async def setup_resource_registry():
    """Example of setting up and using the resource registry."""
    
    # Create storage and cache
    storage = SQLiteStore(db_path="code_index.db")
    cache = CacheManagerFactory.create_memory_cache(max_entries=5000)
    await cache.initialize()
    
    # Create and initialize registry
    registry = ResourceRegistry(storage=storage, cache_manager=cache)
    await registry.initialize()
    
    # The registry is now ready to use
    
    # Example 1: List all resources
    result = await registry.list_resources()
    if result.success:
        resources, total = result.value
        print(f"Found {total} resources")
    
    # Example 2: Filter by language
    python_filter = ResourceFilter(languages=["python"])
    result = await registry.list_resources(filter_options=python_filter)
    if result.success:
        resources, total = result.value
        print(f"Found {total} Python resources")
    
    # Example 3: Paginated listing
    pagination = PaginationOptions(page=1, page_size=20, sort_by="name")
    result = await registry.list_resources(pagination=pagination)
    if result.success:
        resources, total = result.value
        print(f"Page 1: {len(resources)} items (total: {total})")
    
    # Example 4: Get specific resource
    result = await registry.get_resource("code://file/src/main.py")
    if result.success and result.value:
        resource = result.value
        print(f"Found resource: {resource.get_uri()}")
    
    # Example 5: Complex filtering
    complex_filter = ResourceFilter(
        languages=["python", "javascript"],
        tags=["file"],
        name_pattern="test",
        min_size=1000,
        max_size=50000
    )
    result = await registry.list_resources(filter_options=complex_filter)
    if result.success:
        resources, total = result.value
        print(f"Found {total} resources matching complex filter")
    
    # Cleanup
    await registry.shutdown()
    await cache.shutdown()
    
    return registry


# Integration with MCP protocol handlers
class ResourcesListHandler:
    """Handler for resources/list MCP method."""
    
    def __init__(self, registry: ResourceRegistry):
        self.registry = registry
    
    async def handle(self, params: dict) -> dict:
        """Handle resources/list request."""
        # Parse filter options from params
        filter_options = None
        if "filter" in params:
            filter_dict = params["filter"]
            filter_options = ResourceFilter(
                languages=filter_dict.get("languages"),
                tags=filter_dict.get("tags"),
                mime_types=filter_dict.get("mimeTypes"),
                name_pattern=filter_dict.get("namePattern"),
                uri_pattern=filter_dict.get("uriPattern")
            )
        
        # Parse pagination options
        pagination = None
        if "pagination" in params:
            page_dict = params["pagination"]
            pagination = PaginationOptions(
                page=page_dict.get("page", 1),
                page_size=page_dict.get("pageSize", 50),
                sort_by=page_dict.get("sortBy", "name"),
                sort_order=page_dict.get("sortOrder", "asc")
            )
        
        # Get resources
        result = await self.registry.list_resources(filter_options, pagination)
        
        if result.success:
            resources, total = result.value
            return {
                "resources": [
                    {
                        "uri": r.uri,
                        "name": r.name,
                        "description": r.description,
                        "mimeType": r.mime_type,
                        "tags": r.tags,
                        "language": r.language,
                        "size": r.size
                    }
                    for r in resources
                ],
                "total": total,
                "page": pagination.page if pagination else 1,
                "pageSize": pagination.page_size if pagination else len(resources)
            }
        else:
            raise Exception(f"Failed to list resources: {result.error.message}")


class ResourceGetHandler:
    """Handler for resources/get MCP method."""
    
    def __init__(self, registry: ResourceRegistry):
        self.registry = registry
    
    async def handle(self, params: dict) -> dict:
        """Handle resources/get request."""
        uri = params.get("uri")
        if not uri:
            raise ValueError("Missing required parameter: uri")
        
        result = await self.registry.get_resource(uri)
        
        if result.success:
            resource = result.value
            if resource:
                return {
                    "uri": resource.get_uri(),
                    "metadata": resource.get_metadata(),
                    "content": getattr(resource, "content", None)
                }
            else:
                raise Exception(f"Resource not found: {uri}")
        else:
            raise Exception(f"Failed to get resource: {result.error.message}")