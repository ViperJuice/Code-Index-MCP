#!/usr/bin/env python3
"""Direct indexing script for Code-Index-MCP."""

import asyncio
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_server.dispatcher.dispatcher import Dispatcher
from mcp_server.plugin_system.plugin_manager import PluginManager
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.tools.handlers.index_file import index_file_handler

async def main():
    """Run indexing directly."""
    print("Initializing components...")
    
    # Initialize storage
    store = SQLiteStore("code_index.db")
    await store.initialize()
    
    # Initialize plugin manager
    plugin_manager = PluginManager()
    await plugin_manager.initialize()
    
    # Initialize dispatcher
    dispatcher = Dispatcher(plugin_manager)
    
    # Call index_file handler
    params = {
        "path": "/home/jenner/Code/Code-Index-MCP",
        "recursive": True,
        "verbose": True
    }
    
    context = {
        "store": store,
        "dispatcher": dispatcher
    }
    
    print("\nStarting indexing...")
    result = await index_file_handler(params, context)
    
    print("\nIndexing complete!")
    print(f"Result: {result}")
    
    # Clean up
    await store.cleanup()

if __name__ == "__main__":
    asyncio.run(main())