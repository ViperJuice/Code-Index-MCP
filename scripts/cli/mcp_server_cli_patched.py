#!/usr/bin/env python3
"""
MCP Server CLI for Code Index MCP - Claude Code compatible version
This server provides tools only (no resources) to ensure compatibility with Claude Code.
"""
import asyncio
import json
import os
import sys
import hashlib
import subprocess
from typing import Any, Sequence
from dotenv import load_dotenv
from mcp_server.core.path_utils import PathUtils

# Load environment variables from .env file
load_dotenv()

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.plugin_system import PluginManager
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.utils.index_discovery import IndexDiscovery

# Import BM25 direct dispatcher
sys.path.insert(0, "PathUtils.get_workspace_root()/scripts")
from fix_mcp_bm25_integration import BM25DirectDispatcher
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
server = Server("code-index-mcp-fast-search")

# Global instances
dispatcher: EnhancedDispatcher | None = None
plugin_manager: PluginManager | None = None
sqlite_store: SQLiteStore | None = None


async def initialize_services():
    """Initialize all services needed for the MCP server."""
    global dispatcher, plugin_manager, sqlite_store
    
    try:
        # Always use central storage location
        central_storage = os.getenv("MCP_INDEX_STORAGE_PATH", "~/.mcp/indexes")
        central_path = Path(central_storage).expanduser()
        
        # Generate repo ID from git remote
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                check=True
            )
            remote_url = result.stdout.strip()
            repo_id = hashlib.sha256(remote_url.encode()).hexdigest()[:12]
        except Exception as e:
            # Fallback to path-based hash if no git remote
            repo_path = Path.cwd()
            repo_id = hashlib.sha256(str(repo_path.absolute()).encode()).hexdigest()[:12]
            logger.warning(f"No git remote found, using path-based repo ID: {repo_id}")
        
        # Check for current.db symlink in central location
        current_db = central_path / repo_id / "current.db"
        
        if current_db.exists():
            index_path = current_db.resolve()
            logger.info(f"Using index: {index_path}")
            sqlite_store = SQLiteStore(str(index_path))
            
            # Log index metadata if available
            metadata_path = Path(index_path).with_suffix(".metadata.json")
            if metadata_path.exists():
                with open(metadata_path) as f:
                    metadata = json.load(f)
                    logger.info(f"Index branch: {metadata.get('branch', 'unknown')}")
                    logger.info(f"Index commit: {metadata.get('commit', 'unknown')}")
                    logger.info(f"Index created: {metadata.get('moved_at', metadata.get('created_at', 'unknown'))}")
        else:
            # No index found - provide helpful message
            logger.error(f"No index found for repository ID: {repo_id}")
            logger.error(f"Expected location: {current_db}")
            logger.error("To create an index, run: mcp-index index")
            logger.error("To move an existing index, run: python scripts/move_indexes_to_central.py")
            raise FileNotFoundError(f"No index found at {current_db}")
        
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
        
        # Use BM25 direct dispatcher instead
        logger.info("Creating BM25 direct dispatcher...")
        dispatcher = BM25DirectDispatcher()
        
        # Check if index exists
        health = dispatcher.health_check()
        if health['status'] != 'operational':
            logger.error(f"BM25 dispatcher not operational: {health}")
            raise RuntimeError("No valid BM25 index found")
        
        logger.info(f"BM25 dispatcher initialized with index: {health['index']}")
        logger.info(f"Supports all languages via BM25 full-text search")
        
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
            description="[MCP-FIRST] Look up symbol definitions. ALWAYS use this before grep/find for symbol searches. Returns exact file location with line number. Usage: offset=(line-1) for direct navigation.",
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
            description="[MCP-FIRST] Search code patterns. ALWAYS use this before grep/find for content searches. Returns snippets with line numbers. Usage: offset=(line-1) for context.",
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
            description="Get the status of the code index server. Shows index health, supported languages, and performance statistics.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="list_plugins",
            description="List all loaded plugins. Shows 48 supported languages with specialized and generic plugin information.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="reindex",
            description="Reindex files in the codebase. Updates the index for changed files or specific paths.",
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
                response_data = {
                    "symbol": result.get("symbol"),
                    "kind": result.get("kind"),
                    "language": result.get("language"),
                    "signature": result.get("signature"),
                    "doc": result.get("doc"),
                    "defined_in": result.get("defined_in"),
                    "line": result.get("line"),
                    "span": result.get("span")
                }
                
                # Add navigation hint if line number is available
                if result.get("line") and result.get("defined_in"):
                    offset = result.get("line", 1) - 1
                    response_data["_usage_hint"] = f"To view definition: Read(file_path='{result.get('defined_in')}', offset={offset}, limit=20)"
                
                return [types.TextContent(type="text", text=json.dumps(response_data, indent=2))]
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
                    result_item = {
                        "file": r.get("file"),
                        "line": r.get("line"),
                        "snippet": r.get("snippet")
                    }
                    
                    # Add navigation hint if line number is available
                    if r.get("line") and r.get("file"):
                        offset = r.get("line", 1) - 1
                        result_item["_usage_hint"] = f"For more context: Read(file_path='{r.get('file')}', offset={offset}, limit=30)"
                    
                    results_data.append(result_item)
                    
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
                
                if target_path.is_file():
                    # Single file - use index_file
                    try:
                        dispatcher.index_file(target_path)
                        return [types.TextContent(type="text", text=f"Reindexed file: {path}")]
                    except Exception as e:
                        return [types.TextContent(type="text", text=f"Error reindexing {path}: {str(e)}")]
                else:
                    # Directory - use index_directory which handles ignore patterns
                    stats = dispatcher.index_directory(target_path, recursive=True)
                    
                    response_data = {
                        "path": str(target_path),
                        "indexed_files": stats["indexed_files"],
                        "ignored_files": stats["ignored_files"],
                        "failed_files": stats["failed_files"],
                        "total_files": stats["total_files"],
                        "by_language": stats["by_language"]
                    }
                    
                    return [types.TextContent(type="text", text=json.dumps(response_data, indent=2))]
            else:
                # Reindex all files in current directory
                stats = dispatcher.index_directory(Path("."), recursive=True)
                
                response_data = {
                    "path": ".",
                    "indexed_files": stats["indexed_files"],
                    "ignored_files": stats["ignored_files"],
                    "failed_files": stats["failed_files"],
                    "total_files": stats["total_files"],
                    "by_language": stats["by_language"]
                }
                
                return [types.TextContent(type="text", text=json.dumps(response_data, indent=2))]
        
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