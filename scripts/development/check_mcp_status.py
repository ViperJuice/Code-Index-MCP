#!/usr/bin/env python3
"""
Quick status check for MCP server components.
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def check_mcp_status():
    """Check MCP server component status."""
    print("MCP Server Status Check")
    print("=" * 50)
    
    try:
        # Test settings
        print("1. Testing settings...")
        from mcp_server.settings import settings
        print(f"   ✅ Workspace: {settings.workspace_dir}")
        print(f"   ✅ Database: {settings.db_path}")
        print(f"   ✅ MCP Port: {settings.mcp_port}")
        
        # Test storage
        print("\n2. Testing storage...")
        from mcp_server.storage.sqlite_store import SQLiteStore
        storage = SQLiteStore(str(settings.db_path))
        stats = storage.get_statistics()
        print(f"   ✅ Storage initialized")
        print(f"   ✅ Files indexed: {stats.get('total_files', 0)}")
        print(f"   ✅ Symbols indexed: {stats.get('total_symbols', 0)}")
        
        # Test dispatcher
        print("\n3. Testing dispatcher...")
        from mcp_server.dispatcher.dispatcher import Dispatcher
        dispatcher = Dispatcher(plugins=[])
        print(f"   ✅ Dispatcher initialized")
        
        # Test protocol handler
        print("\n4. Testing protocol handler...")
        from mcp_server.protocol import MCPProtocolHandler
        protocol_handler = MCPProtocolHandler()
        print(f"   ✅ Protocol handler created")
        
        # Test tool registry
        print("\n5. Testing tool registry...")
        from mcp_server.tools import get_registry, list_available_tools
        tool_registry = get_registry()
        tools = list_available_tools()
        print(f"   ✅ Tool registry initialized")
        print(f"   ✅ Available tools: {len(tools)}")
        for tool in tools:
            print(f"      - {tool}")
        
        # Test resource registry
        print("\n6. Testing resource registry...")
        from mcp_server.resources import ResourceRegistry
        resource_registry = ResourceRegistry()
        result = await resource_registry.list_resources()
        resources = result.data if hasattr(result, 'data') else []
        print(f"   ✅ Resource registry initialized")
        print(f"   ✅ Available resources: {len(resources)}")
        
        print("\n" + "=" * 50)
        print("✅ ALL COMPONENTS WORKING!")
        print("MCP server is ready for operation.")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(check_mcp_status())
    sys.exit(0 if success else 1)