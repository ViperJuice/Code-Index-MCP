"""
MCP method routing and handling.

Maps MCP method names to handler functions and manages
method registration and dispatch according to the Model Context Protocol specification.
"""

import logging
from typing import Dict, Any, Callable, Optional, List, Union, Awaitable
from dataclasses import dataclass, field
from enum import Enum
import inspect

from .jsonrpc import JSONRPCError, JSONRPCErrorCode
from ..interfaces.mcp_interfaces import MCPRequest, MCPResponse

logger = logging.getLogger(__name__)


class MCPMethod(str, Enum):
    """Standard MCP method names."""
    
    # Core lifecycle methods
    INITIALIZE = "initialize"
    SHUTDOWN = "shutdown"
    PING = "ping"
    
    # Resource methods
    RESOURCES_LIST = "resources/list"
    RESOURCES_READ = "resources/read"
    RESOURCES_SUBSCRIBE = "resources/subscribe"
    RESOURCES_UNSUBSCRIBE = "resources/unsubscribe"
    
    # Tool methods
    TOOLS_LIST = "tools/list"
    TOOLS_CALL = "tools/call"
    
    # Prompt methods
    PROMPTS_LIST = "prompts/list"
    PROMPTS_GET = "prompts/get"
    
    # Sampling methods (optional)
    SAMPLING_CREATE_MESSAGE = "sampling/createMessage"
    
    # Logging methods
    LOGGING_SET_LEVEL = "logging/setLevel"


@dataclass
class MethodHandler:
    """Container for method handler information."""
    
    handler: Callable[..., Awaitable[Any]]
    params_schema: Optional[Dict[str, Any]] = None
    requires_initialization: bool = True
    description: str = ""
    
    async def validate_params(self, params: Optional[Dict[str, Any]]) -> None:
        """Validate parameters against schema if provided."""
        if self.params_schema:
            # TODO: Implement JSON Schema validation
            pass


class MethodRegistry:
    """Registry for MCP method handlers."""
    
    def __init__(self):
        """Initialize the method registry."""
        self._handlers: Dict[str, MethodHandler] = {}
        self._initialized = False
        
    def register(
        self,
        method: Union[str, MCPMethod],
        handler: Callable[..., Awaitable[Any]],
        params_schema: Optional[Dict[str, Any]] = None,
        requires_initialization: bool = True,
        description: str = ""
    ) -> None:
        """
        Register a method handler.
        
        Args:
            method: Method name or MCPMethod enum value
            handler: Async callable that handles the method
            params_schema: Optional JSON Schema for parameter validation
            requires_initialization: Whether method requires initialized session
            description: Human-readable description of the method
        """
        method_name = method.value if isinstance(method, MCPMethod) else str(method)
        
        if not inspect.iscoroutinefunction(handler):
            raise ValueError(f"Handler for {method_name} must be an async function")
        
        self._handlers[method_name] = MethodHandler(
            handler=handler,
            params_schema=params_schema,
            requires_initialization=requires_initialization,
            description=description
        )
        
        logger.debug(f"Registered MCP method handler: {method_name}")
    
    def unregister(self, method: Union[str, MCPMethod]) -> None:
        """
        Unregister a method handler.
        
        Args:
            method: Method name to unregister
        """
        method_name = method.value if isinstance(method, MCPMethod) else str(method)
        if method_name in self._handlers:
            del self._handlers[method_name]
            logger.debug(f"Unregistered MCP method handler: {method_name}")
    
    def get_handler(self, method: str) -> Optional[MethodHandler]:
        """
        Get handler for a method.
        
        Args:
            method: Method name
            
        Returns:
            MethodHandler if found, None otherwise
        """
        return self._handlers.get(method)
    
    def list_methods(self) -> List[str]:
        """Get list of registered method names."""
        return list(self._handlers.keys())
    
    def is_initialized(self) -> bool:
        """Check if the registry has been initialized."""
        return self._initialized
    
    def set_initialized(self, initialized: bool) -> None:
        """Set the initialization state."""
        self._initialized = initialized


class MethodRouter:
    """Routes MCP method calls to appropriate handlers."""
    
    def __init__(self, registry: Optional[MethodRegistry] = None):
        """
        Initialize the method router.
        
        Args:
            registry: Method registry to use (creates new one if not provided)
        """
        self.registry = registry or MethodRegistry()
        self._session_data: Dict[str, Any] = {}
        
    async def route(self, request: MCPRequest) -> MCPResponse:
        """
        Route a method request to its handler.
        
        Args:
            request: MCP request to route
            
        Returns:
            MCP response
            
        Raises:
            JSONRPCError: If method not found or other errors occur
        """
        method_handler = self.registry.get_handler(request.method)
        
        if not method_handler:
            raise JSONRPCError(
                JSONRPCErrorCode.METHOD_NOT_FOUND,
                f"Method not found: {request.method}"
            )
        
        # Check initialization requirement
        if method_handler.requires_initialization and not self.registry.is_initialized():
            if request.method != MCPMethod.INITIALIZE.value:
                raise JSONRPCError(
                    JSONRPCErrorCode.SERVER_NOT_INITIALIZED,
                    "Server not initialized. Call 'initialize' first."
                )
        
        try:
            # Validate parameters
            await method_handler.validate_params(request.params)
            
            # Execute handler
            if request.params is None:
                result = await method_handler.handler()
            else:
                result = await method_handler.handler(**request.params)
            
            # Special handling for initialize method
            if request.method == MCPMethod.INITIALIZE.value:
                self.registry.set_initialized(True)
                self._session_data = result.get("sessionData", {})
            
            return MCPResponse(result=result)
            
        except JSONRPCError:
            raise
        except TypeError as e:
            raise JSONRPCError(
                JSONRPCErrorCode.INVALID_PARAMS,
                f"Invalid parameters: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Error in method handler for {request.method}: {e}")
            raise JSONRPCError(
                JSONRPCErrorCode.INTERNAL_ERROR,
                "Internal error",
                data=str(e)
            )
    
    def get_session_data(self) -> Dict[str, Any]:
        """Get current session data."""
        return self._session_data.copy()


# Default method handlers

async def handle_initialize(
    protocolVersion: str,
    capabilities: Dict[str, Any],
    clientInfo: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Handle MCP initialization.
    
    Args:
        protocolVersion: Protocol version requested by client
        capabilities: Client capabilities
        clientInfo: Optional client information
        
    Returns:
        Server capabilities and information
    """
    # TODO: Implement actual initialization logic
    return {
        "protocolVersion": "1.0",
        "capabilities": {
            "resources": {"subscribe": True},
            "tools": {},
            "prompts": {},
            "logging": {}
        },
        "serverInfo": {
            "name": "code-index-mcp",
            "version": "0.1.0"
        },
        "instructions": """Code-Index-MCP: Enhanced Code Search & Navigation

🚀 **Prioritize These Tools for Code Operations:**
• search_code - Structured code pattern search (use BEFORE native file search)
• lookup_symbol - Symbol definition lookup (use BEFORE grep/language servers)  
• find_references - Smart reference discovery (use BEFORE text search)
• index_file - File indexing and re-indexing with repository metadata
• get_search_guidance - Request optimization help when unsure

🔄 **Repository Management for Translation/Refactoring:**
• add_reference_repository - Add external codebases for cross-language translation
• list_repositories - View all indexed repositories with cleanup dates
• cleanup_repositories - Remove temporary/expired reference repositories
• repository_stats - Analyze repository contents and usage

⚡ **Optimized Request Format (Recommended):**
{
  "request_type": "symbol_search|edit_preparation|explain_code|goto_definition",
  "target": {"query": "search terms", "symbol": "exact_name"},
  "context_spec": {"depth": "minimal|standard|comprehensive|edit_ready"},
  "response_format": {"format": "summary|detailed|navigation|diff_ready"}
}

🔄 **Progressive Discovery Pattern:**
1. Discovery: symbol_search to explore codebase
2. Understanding: explain_code for detailed analysis  
3. Navigation: goto_definition/find_references for precise location
4. Modification: edit_preparation for change-ready context

📋 **Tool Priority (Code Operations Only):**
Code Search: search_code → native file search → text search
Symbol Lookup: lookup_symbol → language servers → manual search
Reference Finding: find_references → IDE features → text search

🎯 **Translation/Refactoring Workflow:**
1. Add reference: add_reference_repository("/path/to/rust_examples", language="rust", days_to_keep=30)
2. Index reference: index_file("/path/to/rust_examples", repository_metadata={"type": "reference"})
3. Cross-search: search_code("authentication", repository_filter={"group_by_repository": true})
4. Compare patterns across languages for translation
5. Cleanup when done: cleanup_repositories(cleanup_expired=true)

🎯 **Fallback Strategy:**
If no results: Follow automatic suggestions → Try broader terms → Use native tools → Check external sources

💡 **Benefits:** 70-95% token reduction, semantic understanding, right-sized context, progressive loading, smart fallbacks, cross-language pattern discovery."""
    }


async def handle_shutdown() -> Dict[str, Any]:
    """Handle server shutdown request."""
    # TODO: Implement graceful shutdown
    return {"status": "ok"}


async def handle_ping() -> Dict[str, Any]:
    """Handle ping request."""
    return {"pong": True}


async def handle_resources_list() -> Dict[str, Any]:
    """List available resources."""
    # TODO: Implement resource listing from registry
    return {"resources": []}


async def handle_resources_read(uri: str) -> Dict[str, Any]:
    """
    Read a specific resource.
    
    Args:
        uri: Resource URI to read
        
    Returns:
        Resource content
    """
    # TODO: Implement resource reading
    raise JSONRPCError(
        JSONRPCErrorCode.INVALID_REQUEST,
        f"Resource not found: {uri}"
    )


async def handle_tools_list() -> Dict[str, Any]:
    """List available tools."""
    # TODO: Implement tool listing from registry
    return {"tools": []}


async def handle_tools_call(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call a specific tool.
    
    Args:
        name: Tool name
        arguments: Tool arguments
        
    Returns:
        Tool execution result
    """
    # TODO: Implement tool execution
    raise JSONRPCError(
        JSONRPCErrorCode.INVALID_REQUEST,
        f"Tool not found: {name}"
    )


async def handle_prompts_list() -> Dict[str, Any]:
    """List available prompts."""
    # TODO: Implement prompt listing from registry
    return {"prompts": []}


async def handle_prompts_get(name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Get a specific prompt.
    
    Args:
        name: Prompt name
        arguments: Optional prompt arguments
        
    Returns:
        Prompt content
    """
    # TODO: Implement prompt retrieval
    raise JSONRPCError(
        JSONRPCErrorCode.INVALID_REQUEST,
        f"Prompt not found: {name}"
    )


def create_default_registry() -> MethodRegistry:
    """Create a method registry with default handlers."""
    registry = MethodRegistry()
    
    # Register core methods
    registry.register(
        MCPMethod.INITIALIZE,
        handle_initialize,
        params_schema={
            "type": "object",
            "properties": {
                "protocolVersion": {"type": "string"},
                "capabilities": {"type": "object"},
                "clientInfo": {"type": "object"}
            },
            "required": ["protocolVersion", "capabilities"]
        },
        requires_initialization=False,
        description="Initialize MCP session"
    )
    
    registry.register(
        MCPMethod.SHUTDOWN,
        handle_shutdown,
        requires_initialization=False,
        description="Shutdown server gracefully"
    )
    
    registry.register(
        MCPMethod.PING,
        handle_ping,
        requires_initialization=False,
        description="Ping server for liveness check"
    )
    
    # Register resource methods
    registry.register(
        MCPMethod.RESOURCES_LIST,
        handle_resources_list,
        description="List available resources"
    )
    
    registry.register(
        MCPMethod.RESOURCES_READ,
        handle_resources_read,
        params_schema={
            "type": "object",
            "properties": {
                "uri": {"type": "string"}
            },
            "required": ["uri"]
        },
        description="Read a specific resource"
    )
    
    # Register tool methods
    registry.register(
        MCPMethod.TOOLS_LIST,
        handle_tools_list,
        description="List available tools"
    )
    
    registry.register(
        MCPMethod.TOOLS_CALL,
        handle_tools_call,
        params_schema={
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "arguments": {"type": "object"}
            },
            "required": ["name", "arguments"]
        },
        description="Call a specific tool"
    )
    
    # Register prompt methods
    registry.register(
        MCPMethod.PROMPTS_LIST,
        handle_prompts_list,
        description="List available prompts"
    )
    
    registry.register(
        MCPMethod.PROMPTS_GET,
        handle_prompts_get,
        params_schema={
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "arguments": {"type": "object"}
            },
            "required": ["name"]
        },
        description="Get a specific prompt"
    )
    
    return registry


# Global default registry instance
default_registry = create_default_registry()
