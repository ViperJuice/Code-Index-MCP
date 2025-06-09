#!/usr/bin/env python3
"""
MCP Server CLI for Code Index MCP - Claude Code compatible version
This server provides tools only (no resources) to ensure compatibility with Claude Code.
"""
import asyncio
import json
import sys
from typing import Any, Sequence
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.plugin_system import PluginManager
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.utils.index_discovery import IndexDiscovery
from pathlib import Path
import logging

# Set up logging - send all logs to stderr to avoid interfering with MCP protocol on stdout
import sys
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)  # Send all logs to stderr
    ]
)
logger = logging.getLogger(__name__)

# Initialize the MCP server
server = Server("code-index-mcp")

# Global instances
dispatcher: EnhancedDispatcher | None = None
plugin_manager: PluginManager | None = None
sqlite_store: SQLiteStore | None = None


async def initialize_services():
    """Initialize all services needed for the MCP server."""
    global dispatcher, plugin_manager, sqlite_store
    
    try:
        # Check for portable index first
        workspace_root = Path.cwd()
        discovery = IndexDiscovery(workspace_root)
        
        if discovery.is_index_enabled():
            logger.info("MCP portable index detected")
            
            # Try to use existing index
            index_path = discovery.get_local_index_path()
            
            if not index_path and discovery.should_download_index():
                logger.info("Attempting to download index from GitHub artifacts...")
                if discovery.download_latest_index():
                    index_path = discovery.get_local_index_path()
                    logger.info("Successfully downloaded index")
                else:
                    logger.info("Could not download index, will use default")
            
            if index_path:
                logger.info(f"Using portable index: {index_path}")
                sqlite_store = SQLiteStore(str(index_path))
                
                # Log index metadata
                metadata = discovery.get_index_metadata()
                if metadata:
                    logger.info(f"Index version: {metadata.get('version', 'unknown')}")
                    logger.info(f"Index created: {metadata.get('created_at', 'unknown')}")
                    logger.info(f"Indexed files: {metadata.get('indexed_files', 'unknown')}")
            else:
                logger.info("No portable index found, using default")
                sqlite_store = SQLiteStore("code_index.db")
        else:
            # Initialize SQLite store with default
            logger.info("Initializing SQLite store with default path...")
            sqlite_store = SQLiteStore("code_index.db")
        
        # Initialize plugin manager
        logger.info("Initializing plugin system...")
        config_path = Path("plugins.yaml")
        plugin_manager = PluginManager(sqlite_store=sqlite_store)
        
        # Load plugins
        logger.info("Loading plugins...")
        load_result = plugin_manager.load_plugins_safe(config_path if config_path.exists() else None)
        
        if not load_result.success:
            logger.error(f"Plugin loading failed: {load_result.error.message}")
        else:
            logger.info(f"Plugin loading completed: {load_result.metadata}")
        
        # Get active plugin instances from plugin manager (for existing 6 plugins)
        active_plugins = plugin_manager.get_active_plugins()
        plugin_instances = list(active_plugins.values())
        
        logger.info(f"Loaded {len(plugin_instances)} active plugins from plugin manager")
        
        # Create enhanced dispatcher with dynamic plugin loading
        logger.info("Creating enhanced dispatcher with dynamic plugin loading...")
        dispatcher = EnhancedDispatcher(
            plugins=plugin_instances,  # Use existing plugins as base
            sqlite_store=sqlite_store,
            enable_advanced_features=True,
            use_plugin_factory=True,  # Enable dynamic loading
            lazy_load=True,  # Load plugins on demand
            semantic_search_enabled=True
        )
        
        supported_languages = dispatcher.supported_languages
        logger.info(f"Enhanced dispatcher created - supports {len(supported_languages)} languages")
        logger.info(f"Languages: {', '.join(supported_languages[:10])}{'...' if len(supported_languages) > 10 else ''}")
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}", exc_info=True)
        raise


# Tool: Symbol Lookup
@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """List available tools."""
    return [
        types.Tool(
            name="symbol_lookup",
            description="Look up a symbol definition in the codebase",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "The symbol name to look up"
                    }
                },
                "required": ["symbol"]
            }
        ),
        types.Tool(
            name="search_code",
            description="Search for code in the codebase",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query"
                    },
                    "semantic": {
                        "type": "boolean",
                        "description": "Whether to use semantic search",
                        "default": False
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results",
                        "default": 20
                    }
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="get_status",
            description="Get the status of the code index server",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="list_plugins",
            description="List all loaded plugins",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="reindex",
            description="Reindex files in the codebase",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Optional path to reindex. If not provided, reindexes all files."
                    }
                }
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict | None) -> Sequence[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool calls."""
    if dispatcher is None:
        await initialize_services()
    
    try:
        if name == "symbol_lookup":
            symbol = arguments.get("symbol") if arguments else None
            if not symbol:
                return [types.TextContent(type="text", text="Error: 'symbol' parameter is required")]
            
            result = dispatcher.lookup(symbol)
            if result:
                return [types.TextContent(type="text", text=json.dumps({
                    "symbol": result.get("symbol"),
                    "kind": result.get("kind"),
                    "language": result.get("language"),
                    "signature": result.get("signature"),
                    "doc": result.get("doc"),
                    "defined_in": result.get("defined_in"),
                    "line": result.get("line"),
                    "span": result.get("span")
                }, indent=2))]
            else:
                return [types.TextContent(type="text", text=f"Symbol '{symbol}' not found")]
        
        elif name == "search_code":
            query = arguments.get("query") if arguments else None
            if not query:
                return [types.TextContent(type="text", text="Error: 'query' parameter is required")]
            
            semantic = arguments.get("semantic", False) if arguments else False
            limit = arguments.get("limit", 20) if arguments else 20
            
            results = list(dispatcher.search(query, semantic=semantic, limit=limit))
            
            if results:
                results_data = []
                for r in results:
                    results_data.append({
                        "file": r.get("file"),
                        "line": r.get("line"),
                        "snippet": r.get("snippet")
                    })
                return [types.TextContent(type="text", text=json.dumps(results_data, indent=2))]
            else:
                return [types.TextContent(type="text", text="No results found")]
        
        elif name == "get_status":
            # Get comprehensive statistics from enhanced dispatcher
            if hasattr(dispatcher, 'get_statistics'):
                stats = dispatcher.get_statistics()
                health = dispatcher.health_check() if hasattr(dispatcher, 'health_check') else {}
            else:
                # Fallback for basic dispatcher
                plugin_count = len(dispatcher._plugins) if hasattr(dispatcher, '_plugins') else 0
                stats = {
                    "total_plugins": plugin_count,
                    "loaded_languages": [],
                    "supported_languages": plugin_count,
                    "operations": {},
                    "by_language": {}
                }
                health = {"status": "unknown"}
            
            status_data = {
                "status": health.get("status", "operational"),
                "version": "0.2.0",
                "dispatcher_type": dispatcher.__class__.__name__,
                "features": {
                    "dynamic_loading": getattr(dispatcher, '_use_factory', False),
                    "lazy_loading": getattr(dispatcher, '_lazy_load', False),
                    "semantic_search": getattr(dispatcher, '_semantic_enabled', False),
                    "advanced_features": getattr(dispatcher, '_enable_advanced', False)
                },
                "languages": {
                    "supported": stats.get("supported_languages", 0),
                    "loaded": len(stats.get("loaded_languages", [])),
                    "loaded_list": stats.get("loaded_languages", [])
                },
                "plugins": {
                    "total": stats.get("total_plugins", 0),
                    "by_language": stats.get("by_language", {})
                },
                "operations": stats.get("operations", {}),
                "health": health
            }
            
            return [types.TextContent(type="text", text=json.dumps(status_data, indent=2))]
        
        elif name == "list_plugins":
            response_data = {
                "plugin_manager_plugins": [],
                "supported_languages": [],
                "loaded_plugins": []
            }
            
            # Get plugin manager plugins (existing 6)
            if plugin_manager is not None:
                plugin_infos = plugin_manager._registry.list_plugins()
                plugin_status = plugin_manager.get_plugin_status()
                
                for info in plugin_infos:
                    status = plugin_status.get(info.name, {})
                    plugin_data = {
                        "name": info.name,
                        "version": info.version,
                        "description": info.description,
                        "language": info.language,
                        "file_extensions": info.file_extensions,
                        "state": status.get('state', 'unknown'),
                        "enabled": status.get('enabled', False)
                    }
                    response_data["plugin_manager_plugins"].append(plugin_data)
            
            # Get all supported languages from enhanced dispatcher
            if hasattr(dispatcher, 'supported_languages'):
                response_data["supported_languages"] = dispatcher.supported_languages
            
            # Get loaded plugin details
            if hasattr(dispatcher, '_by_lang'):
                for lang, plugin in dispatcher._by_lang.items():
                    loaded_plugin_data = {
                        "language": lang,
                        "class": plugin.__class__.__name__,
                        "is_generic": "GenericTreeSitterPlugin" in plugin.__class__.__name__,
                        "semantic_enabled": getattr(plugin, '_enable_semantic', False)
                    }
                    if hasattr(plugin, 'get_indexed_count'):
                        loaded_plugin_data["indexed_files"] = plugin.get_indexed_count()
                    response_data["loaded_plugins"].append(loaded_plugin_data)
            
            return [types.TextContent(type="text", text=json.dumps(response_data, indent=2))]
        
        elif name == "reindex":
            path = arguments.get("path") if arguments else None
            
            if path:
                # Reindex specific path
                target_path = Path(path)
                if not target_path.exists():
                    return [types.TextContent(type="text", text=f"Error: Path not found: {path}")]
                
                indexed_count = 0
                if target_path.is_file():
                    dispatcher.index_file(target_path)
                    indexed_count = 1
                else:
                    # Directory - find all supported files
                    for file_path in target_path.rglob("*"):
                        if file_path.is_file():
                            try:
                                for plugin in dispatcher._plugins:
                                    if plugin.supports(file_path):
                                        dispatcher.index_file(file_path)
                                        indexed_count += 1
                                        break
                            except Exception as e:
                                logger.warning(f"Failed to index {file_path}: {e}")
                
                return [types.TextContent(type="text", text=f"Reindexed {indexed_count} files in {path}")]
            else:
                # Reindex all files
                indexed_count = 0
                for file_path in Path(".").rglob("*"):
                    if file_path.is_file():
                        try:
                            for plugin in dispatcher._plugins:
                                if plugin.supports(file_path):
                                    dispatcher.index_file(file_path)
                                    indexed_count += 1
                                    break
                        except Exception as e:
                            logger.warning(f"Failed to index {file_path}: {e}")
                
                return [types.TextContent(type="text", text=f"Reindexed {indexed_count} files")]
        
        else:
            return [types.TextContent(type="text", text=f"Unknown tool: {name}")]
    
    except Exception as e:
        logger.error(f"Error in tool {name}: {e}", exc_info=True)
        return [types.TextContent(type="text", text=f"Error: {str(e)}")]


async def main():
    """Main entry point."""
    # Initialize services on startup
    await initialize_services()
    
    # Run the stdio server
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())