"""MCP Tool Manager - integrates with dispatcher for code operations"""
from typing import List, Dict, Any, Callable, Awaitable, Optional
from dataclasses import dataclass, asdict
import logging
import json

from .base import MCPTool, ToolResult, ToolHandler, AsyncToolHandler
from ..protocol.jsonrpc import JSONRPCError, JSONRPCErrorCode

logger = logging.getLogger(__name__)

class SearchCodeHandler(AsyncToolHandler):
    """Handler for code search tool"""
    
    def __init__(self, dispatcher):
        super().__init__()
        self.dispatcher = dispatcher
    
    async def execute(self, params: Dict[str, Any], context: Dict[str, Any] = None) -> ToolResult:
        """Execute code search with enhanced context support"""
        try:
            query = params.get("query")
            if not query:
                return ToolResult(success=False, error="Query parameter is required")
            
            # Call dispatcher search method
            results = await self.dispatcher.search(
                query=query,
                semantic=params.get("semantic", False),
                limit=params.get("limit", 20),
                file_pattern=params.get("file_pattern"),
                language=params.get("language")
            )
            
            # Format results for MCP
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "file": str(result.file),
                    "line": result.line,
                    "column": result.column,
                    "text": result.text,
                    "score": result.score,
                    "context": getattr(result, 'context', None)
                })
            
            return ToolResult(success=True, result=formatted_results)
            
        except Exception as e:
            logger.error(f"Error in search_code: {e}", exc_info=True)
            return ToolResult(success=False, error=str(e))

class LookupSymbolHandler(AsyncToolHandler):
    """Handler for symbol lookup tool"""
    
    def __init__(self, dispatcher):
        super().__init__()
        self.dispatcher = dispatcher
    
    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        """Execute symbol lookup"""
        try:
            symbol = params.get("symbol")
            if not symbol:
                return ToolResult(success=False, error="Symbol parameter is required")
            
            # Call dispatcher lookup method
            result = await self.dispatcher.lookup(
                symbol=symbol,
                fuzzy=params.get("fuzzy", False)
            )
            
            if not result:
                return ToolResult(success=True, result=None)
            
            # Format result for MCP
            formatted_result = {
                "name": result.name,
                "kind": result.kind,
                "signature": getattr(result, 'signature', None),
                "docstring": getattr(result, 'docstring', None),
                "file": str(result.file),
                "line": result.line,
                "column": result.column,
                "language": getattr(result, 'language', None)
            }
            
            return ToolResult(success=True, result=formatted_result)
            
        except Exception as e:
            logger.error(f"Error in lookup_symbol: {e}", exc_info=True)
            return ToolResult(success=False, error=str(e))

class FindReferencesHandler(AsyncToolHandler):
    """Handler for finding references tool"""
    
    def __init__(self, dispatcher):
        super().__init__()
        self.dispatcher = dispatcher
    
    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        """Execute find references"""
        try:
            symbol = params.get("symbol")
            if not symbol:
                return ToolResult(success=False, error="Symbol parameter is required")
            
            # Call dispatcher find_references method
            results = await self.dispatcher.find_references(
                symbol=symbol,
                include_definitions=params.get("include_definitions", False)
            )
            
            # Format results for MCP
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "file": str(result.file),
                    "line": result.line,
                    "column": result.column,
                    "text": result.text,
                    "kind": getattr(result, 'kind', 'reference')
                })
            
            return ToolResult(success=True, result=formatted_results)
            
        except Exception as e:
            logger.error(f"Error in find_references: {e}", exc_info=True)
            return ToolResult(success=False, error=str(e))

class IndexFileHandler(AsyncToolHandler):
    """Handler for indexing files"""
    
    def __init__(self, dispatcher):
        super().__init__()
        self.dispatcher = dispatcher
    
    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        """Execute file indexing"""
        try:
            path = params.get("path")
            if not path:
                return ToolResult(success=False, error="Path parameter is required")
            
            # Call dispatcher index method
            result = await self.dispatcher.index_file(
                path=path,
                force=params.get("force", False)
            )
            
            return ToolResult(
                success=True, 
                result={
                    "status": "indexed",
                    "path": path,
                    "symbols": getattr(result, 'symbol_count', 0),
                    "language": getattr(result, 'language', None)
                }
            )
            
        except Exception as e:
            logger.error(f"Error in index_file: {e}", exc_info=True)
            return ToolResult(success=False, error=str(e))

class GetFileOutlineHandler(AsyncToolHandler):
    """Handler for getting file outline"""
    
    def __init__(self, dispatcher):
        super().__init__()
        self.dispatcher = dispatcher
    
    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        """Execute get file outline"""
        try:
            path = params.get("path")
            if not path:
                return ToolResult(success=False, error="Path parameter is required")
            
            # Call dispatcher get_outline method
            outline = await self.dispatcher.get_file_outline(path)
            
            # Format outline for MCP
            formatted_outline = []
            for item in outline:
                formatted_outline.append({
                    "name": item.name,
                    "kind": item.kind,
                    "line": item.line,
                    "children": getattr(item, 'children', [])
                })
            
            return ToolResult(success=True, result=formatted_outline)
            
        except Exception as e:
            logger.error(f"Error in get_file_outline: {e}", exc_info=True)
            return ToolResult(success=False, error=str(e))

class ToolManager:
    """Manages MCP tools for code operations"""
    
    def __init__(self, dispatcher=None, storage=None):
        """
        Initialize tool manager
        
        Args:
            dispatcher: Dispatcher instance for code operations
            storage: Storage instance for data access
        """
        self.dispatcher = dispatcher
        self.storage = storage
        self.tools: Dict[str, MCPTool] = {}
        self.handlers: Dict[str, ToolHandler] = {}
        
        if dispatcher:
            self._register_default_tools()
    
    def _register_default_tools(self):
        """Register default code indexing tools"""
        
        # Search tool
        self.register_tool(
            MCPTool(
                name="search_code",
                description="Search for code patterns across indexed files",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        },
                        "semantic": {
                            "type": "boolean",
                            "description": "Use semantic search",
                            "default": False
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum results",
                            "default": 20
                        },
                        "file_pattern": {
                            "type": "string",
                            "description": "Optional file pattern filter (e.g., '*.py')"
                        },
                        "language": {
                            "type": "string",
                            "description": "Optional language filter"
                        }
                    },
                    "required": ["query"]
                }
            ),
            SearchCodeHandler(self.dispatcher)
        )
        
        # Symbol lookup tool
        self.register_tool(
            MCPTool(
                name="lookup_symbol",
                description="Look up symbol definition",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "symbol": {
                            "type": "string",
                            "description": "Symbol name to look up"
                        },
                        "fuzzy": {
                            "type": "boolean",
                            "description": "Use fuzzy matching",
                            "default": False
                        }
                    },
                    "required": ["symbol"]
                }
            ),
            LookupSymbolHandler(self.dispatcher)
        )
        
        # Find references tool
        self.register_tool(
            MCPTool(
                name="find_references",
                description="Find all references to a symbol",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "symbol": {
                            "type": "string",
                            "description": "Symbol to find references for"
                        },
                        "include_definitions": {
                            "type": "boolean",
                            "description": "Include definitions in results",
                            "default": False
                        }
                    },
                    "required": ["symbol"]
                }
            ),
            FindReferencesHandler(self.dispatcher)
        )
        
        # Index file tool
        self.register_tool(
            MCPTool(
                name="index_file",
                description="Index or re-index a specific file",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "File path to index"
                        },
                        "force": {
                            "type": "boolean",
                            "description": "Force re-indexing",
                            "default": False
                        }
                    },
                    "required": ["path"]
                }
            ),
            IndexFileHandler(self.dispatcher)
        )
        
        # Get file outline tool
        self.register_tool(
            MCPTool(
                name="get_file_outline",
                description="Get hierarchical outline of a file's structure",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "File path to analyze"
                        }
                    },
                    "required": ["path"]
                }
            ),
            GetFileOutlineHandler(self.dispatcher)
        )
        
        logger.info(f"Registered {len(self.tools)} default tools")
    
    def register_tool(self, tool: MCPTool, handler: ToolHandler):
        """
        Register a new tool
        
        Args:
            tool: Tool definition
            handler: Tool handler implementation
        """
        self.tools[tool.name] = tool
        self.handlers[tool.name] = handler
        logger.debug(f"Registered tool: {tool.name}")
    
    def unregister_tool(self, name: str):
        """
        Unregister a tool
        
        Args:
            name: Tool name to unregister
        """
        self.tools.pop(name, None)
        self.handlers.pop(name, None)
        logger.debug(f"Unregistered tool: {name}")
    
    async def list_tools(self) -> Dict[str, Any]:
        """List all available tools"""
        return {
            "tools": [tool.to_dict() for tool in self.tools.values()]
        }
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a specific tool
        
        Args:
            name: Tool name
            arguments: Tool arguments
            
        Returns:
            Tool result dictionary
        """
        if name not in self.tools:
            raise JSONRPCError(
                code=JSONRPCErrorCode.INVALID_PARAMS,
                message=f"Unknown tool: {name}"
            )
        
        tool = self.tools[name]
        handler = self.handlers[name]
        
        # Validate parameters
        error = handler.validate_params(arguments, tool.inputSchema)
        if error:
            raise JSONRPCError(
                code=JSONRPCErrorCode.INVALID_PARAMS,
                message=error
            )
        
        try:
            # Execute tool
            result = await handler.execute(arguments)
            return result.to_dict()
            
        except Exception as e:
            logger.error(f"Tool {name} failed: {e}", exc_info=True)
            return {
                "error": {
                    "type": "tool_error",
                    "message": str(e)
                }
            }
    
    def get_tool_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific tool"""
        tool = self.tools.get(name)
        return tool.to_dict() if tool else None
    
    def add_plugin_tools(self, plugin_name: str, tools: List[MCPTool], handlers: Dict[str, ToolHandler]):
        """
        Add tools from a plugin
        
        Args:
            plugin_name: Name of the plugin
            tools: List of tool definitions
            handlers: Dictionary of tool handlers
        """
        for tool in tools:
            if tool.name in handlers:
                # Add plugin metadata
                tool.metadata["plugin"] = plugin_name
                self.register_tool(tool, handlers[tool.name])
        
        logger.info(f"Added {len(tools)} tools from plugin {plugin_name}")