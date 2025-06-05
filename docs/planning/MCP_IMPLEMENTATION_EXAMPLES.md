# MCP Native Implementation Examples

This document provides concrete code examples for implementing the native MCP architecture in the Code-Index-MCP project.

## File Structure Reference

For the complete file structure and directory organization of the MCP refactor, see [MCP_FILE_STRUCTURE.md](MCP_FILE_STRUCTURE.md). That document shows:
- Exact file locations for all the examples below
- Which files are new vs. modified
- Complete directory tree with all components

## Native MCP Architecture Examples

### 1. Core Protocol Handler

```python
# mcp_server/protocol/handler.py
import json
from typing import Dict, Any, Optional, Callable, Awaitable
from dataclasses import dataclass, asdict
import asyncio
import logging

logger = logging.getLogger(__name__)

@dataclass
class JSONRPCRequest:
    jsonrpc: str = "2.0"
    method: str = None
    params: Optional[Dict[str, Any]] = None
    id: Optional[Union[str, int]] = None

@dataclass
class JSONRPCResponse:
    jsonrpc: str = "2.0"
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[Union[str, int]] = None

@dataclass
class JSONRPCError:
    code: int
    message: str
    data: Optional[Any] = None

class MCPProtocolHandler:
    """Core MCP protocol handler implementing JSON-RPC 2.0"""
    
    def __init__(self):
        self.handlers: Dict[str, Callable[[Dict[str, Any]], Awaitable[Any]]] = {}
        self.sessions: Dict[str, MCPSession] = {}
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Register all MCP method handlers"""
        self.handlers.update({
            # Session management
            "initialize": self.handle_initialize,
            "initialized": self.handle_initialized,
            "shutdown": self.handle_shutdown,
            
            # Resources
            "resources/list": self.handle_list_resources,
            "resources/read": self.handle_read_resource,
            "resources/subscribe": self.handle_subscribe_resource,
            
            # Tools
            "tools/list": self.handle_list_tools,
            "tools/call": self.handle_call_tool,
            
            # Prompts
            "prompts/list": self.handle_list_prompts,
            "prompts/get": self.handle_get_prompt,
            
            # Sampling
            "sampling/createMessage": self.handle_create_message,
            
            # Completions
            "completion/complete": self.handle_complete,
        })
    
    async def handle_message(self, message: str, session_id: str) -> Optional[str]:
        """Handle incoming JSON-RPC message"""
        try:
            data = json.loads(message)
            request = JSONRPCRequest(**data)
            
            if request.method not in self.handlers:
                error = JSONRPCError(
                    code=-32601,
                    message=f"Method not found: {request.method}"
                )
                response = JSONRPCResponse(
                    error=asdict(error),
                    id=request.id
                )
                return json.dumps(asdict(response))
            
            # Get session context
            session = self.sessions.get(session_id)
            if not session and request.method != "initialize":
                error = JSONRPCError(
                    code=-32002,
                    message="Not initialized"
                )
                response = JSONRPCResponse(
                    error=asdict(error),
                    id=request.id
                )
                return json.dumps(asdict(response))
            
            # Call handler
            handler = self.handlers[request.method]
            result = await handler(request.params or {}, session)
            
            # Return response
            response = JSONRPCResponse(
                result=result,
                id=request.id
            )
            return json.dumps(asdict(response))
            
        except json.JSONDecodeError as e:
            error = JSONRPCError(
                code=-32700,
                message="Parse error",
                data=str(e)
            )
            response = JSONRPCResponse(error=asdict(error))
            return json.dumps(asdict(response))
        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)
            error = JSONRPCError(
                code=-32603,
                message="Internal error",
                data=str(e)
            )
            response = JSONRPCResponse(
                error=asdict(error),
                id=request.id if 'request' in locals() else None
            )
            return json.dumps(asdict(response))
    
    async def handle_initialize(self, params: Dict[str, Any], session: MCPSession) -> Dict[str, Any]:
        """Handle initialize request"""
        # Create new session
        client_info = params.get("clientInfo", {})
        protocol_version = params.get("protocolVersion", "1.0")
        
        new_session = MCPSession(
            session_id=generate_session_id(),
            client_info=client_info,
            protocol_version=protocol_version,
            capabilities={}
        )
        
        self.sessions[new_session.session_id] = new_session
        
        # Return server capabilities
        return {
            "serverInfo": {
                "name": "code-index-mcp",
                "version": "1.0.0"
            },
            "capabilities": {
                "resources": {
                    "subscribe": True,
                    "listChanged": True
                },
                "tools": {},
                "prompts": {},
                "sampling": {},
                "completion": {
                    "models": ["code-complete"]
                }
            },
            "instructions": "Code indexing and search MCP server"
        }
```

### 2. Resource System Implementation

```python
# mcp_server/resources/manager.py
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import mimetypes

@dataclass
class MCPResource:
    uri: str
    name: str
    description: Optional[str] = None
    mimeType: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class MCPResourceContent:
    uri: str
    mimeType: str
    text: Optional[str] = None
    blob: Optional[bytes] = None
    metadata: Optional[Dict[str, Any]] = None

class ResourceManager:
    """Manages MCP resources for code indexing"""
    
    def __init__(self, storage, dispatcher):
        self.storage = storage
        self.dispatcher = dispatcher
        self.subscriptions: Dict[str, List[Callable]] = {}
    
    async def list_resources(self, cursor: Optional[str] = None) -> Dict[str, Any]:
        """List available resources"""
        resources = []
        
        # Indexed files
        files = await self.storage.get_indexed_files(cursor=cursor, limit=100)
        for file in files:
            mime_type = mimetypes.guess_type(file.path)[0] or "text/plain"
            resources.append(MCPResource(
                uri=f"code://file/{file.path}",
                name=Path(file.path).name,
                description=f"Indexed file: {file.path}",
                mimeType=mime_type,
                metadata={
                    "lastModified": file.last_modified,
                    "symbols": file.symbol_count,
                    "language": file.language
                }
            ))
        
        # Symbol definitions
        symbols = await self.storage.get_recent_symbols(limit=50)
        for symbol in symbols:
            resources.append(MCPResource(
                uri=f"code://symbol/{symbol.name}",
                name=symbol.name,
                description=f"{symbol.kind}: {symbol.name}",
                mimeType="application/json",
                metadata={
                    "kind": symbol.kind,
                    "file": symbol.file_path,
                    "line": symbol.line
                }
            ))
        
        # Search results (as dynamic resources)
        resources.append(MCPResource(
            uri="code://search",
            name="Code Search",
            description="Search through indexed code",
            mimeType="application/json",
            metadata={"type": "dynamic"}
        ))
        
        return {
            "resources": [asdict(r) for r in resources],
            "nextCursor": files[-1].id if files and len(files) == 100 else None
        }
    
    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """Read a specific resource"""
        if uri.startswith("code://file/"):
            # Read file content
            file_path = uri[len("code://file/"):]
            content = await self.storage.get_file_content(file_path)
            
            if not content:
                raise MCPError(f"File not found: {file_path}")
            
            return asdict(MCPResourceContent(
                uri=uri,
                mimeType=mimetypes.guess_type(file_path)[0] or "text/plain",
                text=content.text,
                metadata={
                    "encoding": content.encoding,
                    "lastIndexed": content.last_indexed
                }
            ))
            
        elif uri.startswith("code://symbol/"):
            # Get symbol definition
            symbol_name = uri[len("code://symbol/"):]
            symbol = await self.dispatcher.lookup(symbol_name)
            
            if not symbol:
                raise MCPError(f"Symbol not found: {symbol_name}")
            
            return asdict(MCPResourceContent(
                uri=uri,
                mimeType="application/json",
                text=json.dumps({
                    "name": symbol.name,
                    "kind": symbol.kind,
                    "signature": symbol.signature,
                    "docstring": symbol.docstring,
                    "file": str(symbol.file),
                    "line": symbol.line,
                    "column": symbol.column
                }),
                metadata={
                    "language": symbol.language
                }
            ))
            
        elif uri == "code://search":
            # Return search interface description
            return asdict(MCPResourceContent(
                uri=uri,
                mimeType="application/json",
                text=json.dumps({
                    "description": "Use the search_code tool to search",
                    "example": {
                        "tool": "search_code",
                        "params": {
                            "query": "function definition",
                            "semantic": True
                        }
                    }
                })
            ))
        
        else:
            raise MCPError(f"Unknown resource URI: {uri}")
```

### 3. Tool System Implementation

```python
# mcp_server/tools/manager.py
from typing import List, Dict, Any, Callable, Awaitable
from dataclasses import dataclass, asdict
import json

@dataclass
class MCPTool:
    name: str
    description: str
    inputSchema: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None

class ToolManager:
    """Manages MCP tools for code operations"""
    
    def __init__(self, dispatcher, storage):
        self.dispatcher = dispatcher
        self.storage = storage
        self.tools: Dict[str, MCPTool] = {}
        self.handlers: Dict[str, Callable[[Dict[str, Any]], Awaitable[Any]]] = {}
        self._register_tools()
    
    def _register_tools(self):
        """Register all available tools"""
        
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
                            "description": "Optional file pattern filter"
                        }
                    },
                    "required": ["query"]
                }
            ),
            self.handle_search_code
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
            self.handle_lookup_symbol
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
            self.handle_find_references
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
            self.handle_index_file
        )
    
    def register_tool(self, tool: MCPTool, handler: Callable[[Dict[str, Any]], Awaitable[Any]]):
        """Register a new tool"""
        self.tools[tool.name] = tool
        self.handlers[tool.name] = handler
    
    async def list_tools(self) -> Dict[str, Any]:
        """List all available tools"""
        return {
            "tools": [asdict(tool) for tool in self.tools.values()]
        }
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a specific tool"""
        if name not in self.tools:
            raise MCPError(f"Unknown tool: {name}")
        
        handler = self.handlers[name]
        try:
            result = await handler(arguments)
            return {
                "result": result
            }
        except Exception as e:
            logger.error(f"Tool {name} failed: {e}", exc_info=True)
            return {
                "error": {
                    "type": "tool_error",
                    "message": str(e)
                }
            }
    
    async def handle_search_code(self, args: Dict[str, Any]) -> Any:
        """Handle code search"""
        results = await self.dispatcher.search(
            query=args["query"],
            semantic=args.get("semantic", False),
            limit=args.get("limit", 20)
        )
        
        return [
            {
                "file": str(result.file),
                "line": result.line,
                "column": result.column,
                "text": result.text,
                "score": result.score,
                "context": result.context
            }
            for result in results
        ]
```

## Testing Examples

### MCP Client Test

```python
# tests/test_mcp_client.py
import asyncio
import json
import websockets

async def test_mcp_connection():
    """Test basic MCP connection and initialization"""
    
    async with websockets.connect("ws://localhost:8000/mcp") as websocket:
        # Send initialize
        await websocket.send(json.dumps({
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0"
                }
            },
            "id": 1
        }))
        
        # Receive response
        response = json.loads(await websocket.recv())
        assert response["result"]["serverInfo"]["name"]
        assert "resources" in response["result"]["capabilities"]
        
        # List resources
        await websocket.send(json.dumps({
            "jsonrpc": "2.0",
            "method": "resources/list",
            "params": {},
            "id": 2
        }))
        
        response = json.loads(await websocket.recv())
        assert "resources" in response["result"]
        
        # Call a tool
        await websocket.send(json.dumps({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "search_code",
                "arguments": {
                    "query": "function"
                }
            },
            "id": 3
        }))
        
        response = json.loads(await websocket.recv())
        assert "result" in response["result"]

if __name__ == "__main__":
    asyncio.run(test_mcp_connection())
```

This provides concrete implementation examples for the native MCP architecture, showing how the code would actually look in practice.