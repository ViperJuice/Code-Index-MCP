#!/usr/bin/env python3
"""
Stdio MCP server for MCP Inspector compatibility.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mcp_server.protocol import MCPProtocolHandler, JSONRPCRequest, JSONRPCResponse, JSONRPCError
from mcp_server.tools import get_registry, list_available_tools
from mcp_server.resources import ResourceRegistry
from mcp_server.prompts import get_prompt_registry
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.dispatcher.dispatcher import Dispatcher
from mcp_server.settings import settings

# Setup logging to stderr so it doesn't interfere with stdio protocol
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr
)
logger = logging.getLogger(__name__)


class StdioMCPServer:
    """Simple stdio-based MCP server for Inspector compatibility."""
    
    def __init__(self):
        self.storage = None
        self.dispatcher = None
        self.protocol_handler = None
        self.tool_registry = None
        self.resource_registry = None
        self.prompt_registry = None
        self.initialized = False
    
    async def initialize(self):
        """Initialize server components."""
        try:
            logger.info("Initializing MCP stdio server...")
            
            # Initialize storage
            self.storage = SQLiteStore(str(settings.db_path))
            logger.info("Storage initialized")
            
            # Initialize dispatcher
            self.dispatcher = Dispatcher(plugins=[])
            logger.info("Dispatcher initialized")
            
            # Initialize registries
            self.tool_registry = get_registry()
            self.resource_registry = ResourceRegistry()
            self.prompt_registry = get_prompt_registry()
            logger.info("Registries initialized")
            
            # Initialize protocol handler
            self.protocol_handler = MCPProtocolHandler()
            logger.info("Protocol handler initialized")
            
            self.initialized = True
            logger.info("MCP stdio server initialization complete")
            
        except Exception as e:
            logger.error(f"Failed to initialize server: {e}")
            raise
    
    async def handle_request(self, request_data: str) -> str:
        """Handle a single MCP request."""
        try:
            # Parse JSON-RPC request
            data = json.loads(request_data.strip())
            
            # Create request object
            request = JSONRPCRequest(
                method=data.get("method"),
                params=data.get("params", {}),
                id=data.get("id")
            )
            
            # Handle different MCP methods
            if request.method == "initialize":
                return await self.handle_initialize(request)
            elif request.method == "tools/list":
                return await self.handle_tools_list(request)
            elif request.method == "tools/call":
                return await self.handle_tools_call(request)
            elif request.method == "resources/list":
                return await self.handle_resources_list(request)
            elif request.method == "resources/read":
                return await self.handle_resources_read(request)
            elif request.method == "prompts/list":
                return await self.handle_prompts_list(request)
            elif request.method == "prompts/get":
                return await self.handle_prompts_get(request)
            else:
                # Method not found
                error = JSONRPCError(
                    code=-32601,
                    message="Method not found",
                    data={"method": request.method}
                )
                response = JSONRPCResponse(error=error, id=request.id)
                return json.dumps(response.to_dict())
        
        except json.JSONDecodeError as e:
            # Parse error
            error = JSONRPCError(
                code=-32700,
                message="Parse error",
                data={"error": str(e)}
            )
            response = JSONRPCResponse(error=error, id=None)
            return json.dumps(response.to_dict())
        
        except Exception as e:
            # Internal error
            error = JSONRPCError(
                code=-32603,
                message="Internal error",
                data={"error": str(e)}
            )
            response = JSONRPCResponse(error=error, id=data.get("id") if 'data' in locals() else None)
            return json.dumps(response.to_dict())
    
    async def handle_initialize(self, request: JSONRPCRequest) -> str:
        """Handle initialize request."""
        result = {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {
                    "listChanged": True
                },
                "resources": {
                    "subscribe": True,
                    "listChanged": True
                },
                "prompts": {
                    "listChanged": True
                }
            },
            "serverInfo": {
                "name": "code-index-mcp",
                "version": "1.0.0"
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
        
        response = JSONRPCResponse(result=result, id=request.id)
        return json.dumps(response.to_dict())
    
    async def handle_tools_list(self, request: JSONRPCRequest) -> str:
        """Handle tools/list request."""
        tools = list_available_tools()
        
        # Convert to MCP format
        mcp_tools = []
        for tool_name in tools:
            mcp_tools.append({
                "name": tool_name,
                "description": f"Tool for {tool_name.replace('_', ' ')}",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            })
        
        result = {"tools": mcp_tools}
        response = JSONRPCResponse(result=result, id=request.id)
        return json.dumps(response.to_dict())
    
    async def handle_tools_call(self, request: JSONRPCRequest) -> str:
        """Handle tools/call request."""
        tool_name = request.params.get("name")
        arguments = request.params.get("arguments", {})
        
        # Simulate tool execution
        result = {
            "content": [
                {
                    "type": "text",
                    "text": f"Tool '{tool_name}' executed with arguments: {arguments}"
                }
            ]
        }
        
        response = JSONRPCResponse(result=result, id=request.id)
        return json.dumps(response.to_dict())
    
    async def handle_resources_list(self, request: JSONRPCRequest) -> str:
        """Handle resources/list request."""
        # Get sample resources
        resources = [
            {
                "uri": "file:///workspace/main.py",
                "name": "main.py",
                "mimeType": "text/x-python"
            },
            {
                "uri": "file:///workspace/README.md", 
                "name": "README.md",
                "mimeType": "text/markdown"
            }
        ]
        
        result = {"resources": resources}
        response = JSONRPCResponse(result=result, id=request.id)
        return json.dumps(response.to_dict())
    
    async def handle_resources_read(self, request: JSONRPCRequest) -> str:
        """Handle resources/read request."""
        uri = request.params.get("uri")
        
        result = {
            "contents": [
                {
                    "uri": uri,
                    "mimeType": "text/plain",
                    "text": f"Content of {uri}"
                }
            ]
        }
        
        response = JSONRPCResponse(result=result, id=request.id)
        return json.dumps(response.to_dict())
    
    async def handle_prompts_list(self, request: JSONRPCRequest) -> str:
        """Handle prompts/list request."""
        try:
            prompts = self.prompt_registry.list_prompts()
            
            mcp_prompts = []
            for prompt in prompts:
                # Handle different prompt object types safely
                prompt_name = getattr(prompt, 'name', str(prompt))
                prompt_description = getattr(prompt, 'description', f"Prompt template for {prompt_name}")
                
                mcp_prompts.append({
                    "name": prompt_name,
                    "description": prompt_description,
                    "arguments": [
                        {
                            "name": "code",
                            "description": "Code to analyze",
                            "required": True
                        },
                        {
                            "name": "language",
                            "description": "Programming language",
                            "required": False
                        }
                    ]
                })
            
            result = {"prompts": mcp_prompts}
            response = JSONRPCResponse(result=result, id=request.id)
            return json.dumps(response.to_dict())
        except Exception as e:
            # Return error response
            error = JSONRPCError(
                code=-32603,
                message="Internal error in prompts/list",
                data={"error": str(e)}
            )
            response = JSONRPCResponse(error=error, id=request.id)
            return json.dumps(response.to_dict())
    
    async def handle_prompts_get(self, request: JSONRPCRequest) -> str:
        """Handle prompts/get request."""
        prompt_name = request.params.get("name")
        arguments = request.params.get("arguments", {})
        
        try:
            generated_prompt = await self.prompt_registry.generate_prompt(prompt_name, arguments)
            
            result = {
                "description": f"Generated prompt for {prompt_name}",
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": generated_prompt
                        }
                    }
                ]
            }
        except Exception as e:
            result = {
                "description": f"Error generating prompt: {str(e)}",
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": f"Failed to generate prompt '{prompt_name}': {str(e)}"
                        }
                    }
                ]
            }
        
        response = JSONRPCResponse(result=result, id=request.id)
        return json.dumps(response.to_dict())
    
    async def run(self):
        """Run the stdio server."""
        await self.initialize()
        
        logger.info("MCP stdio server ready for requests")
        
        # Read from stdin and write to stdout
        for line in sys.stdin:
            try:
                line = line.strip()
                if not line:
                    continue
                
                logger.info(f"Received request: {line[:100]}...")
                
                # Handle the request
                response = await self.handle_request(line)
                
                # Send response to stdout
                print(response)
                sys.stdout.flush()
                
                logger.info(f"Sent response: {response[:100]}...")
                
            except Exception as e:
                logger.error(f"Error processing request: {e}")
                # Send error response
                error = JSONRPCError(
                    code=-32603,
                    message="Internal error",
                    data={"error": str(e)}
                )
                response = JSONRPCResponse(error=error, id=None)
                print(json.dumps(response.to_dict()))
                sys.stdout.flush()


async def main():
    """Main entry point for stdio server."""
    server = StdioMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())