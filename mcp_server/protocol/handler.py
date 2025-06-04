"""Core MCP protocol handler implementing JSON-RPC 2.0"""
import json
import logging
from typing import Dict, Any, Optional, Callable, Awaitable, Union, List
from dataclasses import dataclass, asdict

from .jsonrpc import (
    JSONRPCRequest, JSONRPCResponse, JSONRPCError, JSONRPCParser,
    JSONRPCSerializer, JSONRPCHandler, JSONRPCErrorCode
)
from .session import MCPSession, SessionManager, ClientInfo, MCPCapabilities, SessionState

logger = logging.getLogger(__name__)

class MCPError(Exception):
    """MCP-specific error"""
    pass

@dataclass
class MCPServerInfo:
    """MCP server information"""
    name: str = "code-index-mcp"
    version: str = "1.0.0"
    vendor: str = "Code-Index-MCP"

class MCPProtocolHandler:
    """Core MCP protocol handler implementing JSON-RPC 2.0"""
    
    def __init__(self, session_manager=None, tool_manager=None, resource_manager=None, 
                 prompt_manager=None, dispatcher=None, storage=None, watcher=None):
        """
        Initialize MCP protocol handler
        
        Args:
            session_manager: Session manager instance
            tool_manager: Tool manager instance
            resource_manager: Resource manager instance
            prompt_manager: Prompt manager instance
            dispatcher: Dispatcher instance for code operations
            storage: Storage instance for data access
            watcher: File watcher instance for notifications
        """
        self.session_manager = session_manager
        self.tool_manager = tool_manager
        self.resource_manager = resource_manager
        self.prompt_manager = prompt_manager
        self.dispatcher = dispatcher
        self.storage = storage
        self.watcher = watcher
        
        # Core components
        self.jsonrpc_handler = JSONRPCHandler()
        if session_manager is None:
            self.session_manager = SessionManager()
        else:
            self.session_manager = session_manager
        self.server_info = MCPServerInfo()
        
        # Use passed managers or None
        if resource_manager is None:
            self.resource_manager = None
        else:
            self.resource_manager = resource_manager
            
        if tool_manager is None:
            self.tool_manager = None
        else:
            self.tool_manager = tool_manager
            
        if prompt_manager is None:
            self.prompt_manager = None
        else:
            self.prompt_manager = prompt_manager
        
        # Setup handlers
        self._setup_handlers()
        
        logger.info(f"MCP Protocol Handler initialized for {self.server_info.name} v{self.server_info.version}")
    
    def _setup_handlers(self):
        """Register all MCP method handlers"""
        # Session management
        self.jsonrpc_handler.register_method("initialize", self.handle_initialize)
        self.jsonrpc_handler.register_method("initialized", self.handle_initialized)
        self.jsonrpc_handler.register_method("shutdown", self.handle_shutdown)
        
        # Resources
        self.jsonrpc_handler.register_method("resources/list", self.handle_list_resources)
        self.jsonrpc_handler.register_method("resources/read", self.handle_read_resource)
        self.jsonrpc_handler.register_method("resources/subscribe", self.handle_subscribe_resource)
        self.jsonrpc_handler.register_method("resources/unsubscribe", self.handle_unsubscribe_resource)
        
        # Tools
        self.jsonrpc_handler.register_method("tools/list", self.handle_list_tools)
        self.jsonrpc_handler.register_method("tools/call", self.handle_call_tool)
        
        # Prompts
        self.jsonrpc_handler.register_method("prompts/list", self.handle_list_prompts)
        self.jsonrpc_handler.register_method("prompts/get", self.handle_get_prompt)
        
        # Sampling
        self.jsonrpc_handler.register_method("sampling/createMessage", self.handle_create_message)
        
        # Completions
        self.jsonrpc_handler.register_method("completion/complete", self.handle_complete)
        
        # Logging
        self.jsonrpc_handler.register_method("logging/setLevel", self.handle_set_log_level)
        
        logger.debug("MCP method handlers registered")
    
    async def start(self):
        """Start protocol handler and its components"""
        await self.session_manager.start()
        logger.info("MCP Protocol Handler started")
    
    async def stop(self):
        """Stop protocol handler and cleanup"""
        await self.session_manager.stop()
        logger.info("MCP Protocol Handler stopped")
    
    async def handle_message(self, message: str, session_id: Optional[str] = None) -> Optional[str]:
        """
        Handle incoming JSON-RPC message
        
        Args:
            message: Raw JSON-RPC message
            session_id: Optional session ID for the connection
            
        Returns:
            JSON-RPC response string or None for notifications
        """
        try:
            # Parse request
            request = JSONRPCParser.parse_request(message)
            
            # Get or create session
            session = None
            if session_id:
                session = await self.session_manager.get_session(session_id)
            
            # Check if session is required
            if isinstance(request, JSONRPCRequest):
                requests = [request]
            else:
                requests = request
            
            # Validate session state for non-initialize methods
            for req in requests:
                if req.method != "initialize" and req.method != "shutdown":
                    if not session or not session.is_initialized():
                        error = JSONRPCError(
                            code=JSONRPCErrorCode.SERVER_NOT_INITIALIZED,
                            message="Server not initialized"
                        )
                        if req.id is not None:
                            return JSONRPCSerializer.serialize_response(
                                JSONRPCResponse.error_response(req.id, error)
                            )
                        else:
                            logger.error("Received request before initialization")
                            return None
            
            # Store session in request context
            for req in requests:
                if hasattr(req, 'params') and req.params is None:
                    req.params = {}
                if hasattr(req, 'params') and isinstance(req.params, dict):
                    req.params['_session'] = session
                    req.params['_session_id'] = session_id
            
            # Handle request(s)
            response = await self.jsonrpc_handler.handle_request(request)
            
            # Serialize response if any
            if response:
                return JSONRPCSerializer.serialize_response(response)
            
            return None
            
        except JSONRPCError as e:
            # Return error response
            return JSONRPCSerializer.serialize_response(
                JSONRPCResponse.error_response(None, e)
            )
        except Exception as e:
            logger.error(f"Unexpected error handling message: {e}", exc_info=True)
            error = JSONRPCError(
                code=JSONRPCErrorCode.INTERNAL_ERROR,
                message="Internal error",
                data=str(e)
            )
            return JSONRPCSerializer.serialize_response(
                JSONRPCResponse.error_response(None, error)
            )
    
    # Session Management Handlers
    
    async def handle_initialize(self, **params) -> Dict[str, Any]:
        """Handle initialize request"""
        session_id = params.get('_session_id')
        if not session_id:
            session = await self.session_manager.create_session()
            session_id = session.session_id
        else:
            session = await self.session_manager.get_session(session_id)
            if session and session.state != SessionState.CREATED:
                raise JSONRPCError(
                    code=JSONRPCErrorCode.INVALID_REQUEST,
                    message="Already initialized"
                )
        
        # Parse client info
        client_info = ClientInfo(
            name=params.get("clientInfo", {}).get("name", "Unknown"),
            version=params.get("clientInfo", {}).get("version", "0.0.0"),
            extension_data=params.get("clientInfo", {})
        )
        
        protocol_version = params.get("protocolVersion", "1.0")
        
        # Define server capabilities
        capabilities = MCPCapabilities(
            resources={
                "subscribe": True,
                "listChanged": True
            },
            tools={},
            prompts={},
            sampling={},
            completion={
                "models": ["code-complete"]
            },
            logging={
                "levels": ["debug", "info", "warning", "error"]
            }
        )
        
        # Initialize session
        await self.session_manager.initialize_session(
            session_id, client_info, protocol_version, capabilities
        )
        
        # Return server info and capabilities
        return {
            "serverInfo": asdict(self.server_info),
            "capabilities": capabilities.to_dict(),
            "instructions": "Code indexing and search MCP server. Use tools to search code, lookup symbols, and manage indexed files.",
            "sessionId": session_id  # Include session ID for client tracking
        }
    
    async def handle_initialized(self, **params) -> None:
        """Handle initialized notification"""
        session = params.get('_session')
        if session:
            logger.info(f"Client confirmed initialization for session {session.session_id}")
        return None  # No response for notifications
    
    async def handle_shutdown(self, **params) -> Dict[str, Any]:
        """Handle shutdown request"""
        session = params.get('_session')
        session_id = params.get('_session_id')
        
        if session_id:
            await self.session_manager.shutdown_session(session_id)
        
        return {}  # Empty response per spec
    
    # Resource Handlers
    
    async def handle_list_resources(self, **params) -> Dict[str, Any]:
        """Handle resources/list request"""
        if not self.resource_manager:
            return {"resources": []}
        
        cursor = params.get("cursor")
        return await self.resource_manager.list_resources(cursor=cursor)
    
    async def handle_read_resource(self, **params) -> Dict[str, Any]:
        """Handle resources/read request"""
        if not self.resource_manager:
            raise JSONRPCError(
                code=JSONRPCErrorCode.INVALID_REQUEST,
                message="Resource system not available"
            )
        
        uri = params.get("uri")
        if not uri:
            raise JSONRPCError(
                code=JSONRPCErrorCode.INVALID_PARAMS,
                message="Missing required parameter: uri"
            )
        
        return await self.resource_manager.read_resource(uri)
    
    async def handle_subscribe_resource(self, **params) -> Dict[str, Any]:
        """Handle resources/subscribe request"""
        session = params.get('_session')
        uri = params.get("uri")
        
        if not uri:
            raise JSONRPCError(
                code=JSONRPCErrorCode.INVALID_PARAMS,
                message="Missing required parameter: uri"
            )
        
        if session:
            session.subscribe(uri)
        
        return {}  # Empty response per spec
    
    async def handle_unsubscribe_resource(self, **params) -> Dict[str, Any]:
        """Handle resources/unsubscribe request"""
        session = params.get('_session')
        uri = params.get("uri")
        
        if not uri:
            raise JSONRPCError(
                code=JSONRPCErrorCode.INVALID_PARAMS,
                message="Missing required parameter: uri"
            )
        
        if session:
            session.unsubscribe(uri)
        
        return {}  # Empty response per spec
    
    # Tool Handlers
    
    async def handle_list_tools(self, **params) -> Dict[str, Any]:
        """Handle tools/list request with enhanced descriptions"""
        from ..tools.enhanced_descriptions import get_enhanced_tool_descriptions
        
        if not self.tool_manager:
            return {"tools": []}
        
        # Get agent information from session
        session = params.get('_session')
        agent_name = None
        if session and hasattr(session, 'client_info'):
            agent_name = session.client_info.name
        
        # Get base tools
        tools_response = await self.tool_manager.list_tools()
        tools = tools_response.get("tools", [])
        
        # Enhance tool descriptions with structured request guidance
        enhanced_descriptions = get_enhanced_tool_descriptions(agent_name)
        
        for tool in tools:
            tool_name = tool.get("name", "")
            if tool_name in enhanced_descriptions:
                tool["description"] = enhanced_descriptions[tool_name]
        
        # Add search guidance tool
        tools.append({
            "name": "get_search_guidance",
            "description": enhanced_descriptions.get("get_search_guidance", "Get search guidance"),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "Description of what you're trying to accomplish"
                    }
                },
                "required": ["task"]
            }
        })
        
        return {"tools": tools}
    
    async def handle_call_tool(self, **params) -> Dict[str, Any]:
        """Handle tools/call request with enhanced context"""
        if not self.tool_manager:
            raise JSONRPCError(
                code=JSONRPCErrorCode.INVALID_REQUEST,
                message="Tool system not available"
            )
        
        name = params.get("name")
        arguments = params.get("arguments", {})
        session = params.get('_session')
        
        if not name:
            raise JSONRPCError(
                code=JSONRPCErrorCode.INVALID_PARAMS,
                message="Missing required parameter: name"
            )
        
        # Handle search guidance tool
        if name == "get_search_guidance":
            from ..tools.guidance_handler import search_guidance_handler
            agent_info = {}
            if session and hasattr(session, 'client_info'):
                agent_info = {
                    "name": session.client_info.name,
                    "version": session.client_info.version
                }
            
            result = await search_guidance_handler(arguments, {"agent_info": agent_info})
            return {
                "content": [
                    {
                        "type": "text", 
                        "text": str(result)
                    }
                ]
            }
        
        # Prepare enhanced context for regular tools
        enhanced_context = {}
        if session and hasattr(session, 'client_info'):
            enhanced_context["agent_info"] = {
                "name": session.client_info.name,
                "version": session.client_info.version
            }
        
        # Call the tool with enhanced context
        result = await self.tool_manager.call_tool(name, arguments, enhanced_context)
        
        return {
            "content": [
                {
                    "type": "text",
                    "text": result
                }
            ]
        }
    
    # Prompt Handlers
    
    async def handle_list_prompts(self, **params) -> Dict[str, Any]:
        """Handle prompts/list request"""
        if not self.prompt_manager:
            return {"prompts": []}
        
        return await self.prompt_manager.list_prompts()
    
    async def handle_get_prompt(self, **params) -> Dict[str, Any]:
        """Handle prompts/get request"""
        if not self.prompt_manager:
            raise JSONRPCError(
                code=JSONRPCErrorCode.INVALID_REQUEST,
                message="Prompt system not available"
            )
        
        name = params.get("name")
        arguments = params.get("arguments", {})
        
        if not name:
            raise JSONRPCError(
                code=JSONRPCErrorCode.INVALID_PARAMS,
                message="Missing required parameter: name"
            )
        
        return await self.prompt_manager.get_prompt(name, arguments)
    
    # Sampling Handler
    
    async def handle_create_message(self, **params) -> Dict[str, Any]:
        """Handle sampling/createMessage request"""
        # This would integrate with an LLM for code completion
        # For now, return not implemented
        raise JSONRPCError(
            code=JSONRPCErrorCode.METHOD_NOT_FOUND,
            message="Sampling not implemented"
        )
    
    # Completion Handler
    
    async def handle_complete(self, **params) -> Dict[str, Any]:
        """Handle completion/complete request"""
        # This would provide code completion
        # For now, return not implemented
        raise JSONRPCError(
            code=JSONRPCErrorCode.METHOD_NOT_FOUND,
            message="Completion not implemented"
        )
    
    # Logging Handler
    
    async def handle_set_log_level(self, **params) -> Dict[str, Any]:
        """Handle logging/setLevel request"""
        level = params.get("level", "info").upper()
        
        # Map MCP log levels to Python logging levels
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "WARN": logging.WARNING,
            "ERROR": logging.ERROR
        }
        
        if level not in level_map:
            raise JSONRPCError(
                code=JSONRPCErrorCode.INVALID_PARAMS,
                message=f"Invalid log level: {level}"
            )
        
        logging.getLogger().setLevel(level_map[level])
        logger.info(f"Log level set to {level}")
        
        return {}  # Empty response per spec
    
    # Helper methods
    
    def set_resource_manager(self, resource_manager):
        """Set resource manager instance"""
        self.resource_manager = resource_manager
        logger.debug("Resource manager set")
    
    def set_tool_manager(self, tool_manager):
        """Set tool manager instance"""
        self.tool_manager = tool_manager
        logger.debug("Tool manager set")
    
    def set_prompt_manager(self, prompt_manager):
        """Set prompt manager instance"""
        self.prompt_manager = prompt_manager
        logger.debug("Prompt manager set")
    
    async def handle_request(self, request):
        """Handle a request object (compatibility method)."""
        # Convert request object to JSON and handle via handle_message
        try:
            if hasattr(request, 'to_dict'):
                message = json.dumps(request.to_dict())
            else:
                message = json.dumps(request)
            return await self.handle_message(message)
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return None

# Common alias for backward compatibility
ProtocolHandler = MCPProtocolHandler