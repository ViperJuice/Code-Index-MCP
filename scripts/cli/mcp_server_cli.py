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
import time
from typing import Any, Sequence
from dotenv import load_dotenv
from mcp_server.core.path_utils import PathUtils

# Load environment variables from .env file
load_dotenv()

# Enable debug mode
DEBUG_MODE = os.getenv("MCP_DEBUG", "0") == "1"

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.dispatcher.simple_dispatcher import SimpleDispatcher
from mcp_server.plugin_system import PluginManager
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.utils.index_discovery import IndexDiscovery
from mcp_server.config.index_paths import IndexPathConfig
from pathlib import Path
import logging
import signal
import threading
from contextlib import contextmanager

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
dispatcher: EnhancedDispatcher | SimpleDispatcher | None = None
plugin_manager: PluginManager | None = None
sqlite_store: SQLiteStore | None = None
initialization_error: str | None = None

# Configuration from environment
USE_SIMPLE_DISPATCHER = os.getenv("MCP_USE_SIMPLE_DISPATCHER", "false").lower() == "true"
PLUGIN_LOAD_TIMEOUT = int(os.getenv("MCP_PLUGIN_TIMEOUT", "5"))

@contextmanager
def timeout(seconds):
    """Context manager for timeout operations."""
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Operation timed out after {seconds} seconds")
    
    # Set the timeout handler
    original_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    
    try:
        yield
    finally:
        # Cancel the alarm
        signal.alarm(0)
        # Restore the original handler
        signal.signal(signal.SIGALRM, original_handler)


async def initialize_services():
    """Initialize all services needed for the MCP server."""
    global dispatcher, plugin_manager, sqlite_store, initialization_error
    
    try:
        # Use multi-path discovery to find index
        current_dir = Path.cwd()
        enable_multi_path = os.getenv("MCP_ENABLE_MULTI_PATH", "true").lower() == "true"
        
        logger.info("Searching for index using multi-path discovery...")
        discovery = IndexDiscovery(current_dir, enable_multi_path=enable_multi_path)
        
        # Get information about index discovery
        index_info = discovery.get_index_info()
        
        if not index_info["enabled"]:
            logger.error("MCP indexing is not enabled for this repository")
            raise RuntimeError("MCP indexing not enabled. Create .mcp-index.json to enable.")
            
        # Find the index
        index_path = discovery.get_local_index_path()
        
        if index_path:
            logger.info(f"Found index at: {index_path}")
            logger.info(f"Location type: {discovery._classify_location(index_path.parent)}")
            sqlite_store = SQLiteStore(str(index_path))
            
            # Validate index
            validation_result = validate_index(sqlite_store, current_dir)
            if not validation_result["valid"]:
                logger.warning(f"Index validation issues found:")
                for issue in validation_result["issues"]:
                    logger.warning(f"  - {issue}")
            else:
                logger.info(f"Index validation passed: {validation_result['stats']}")
            
            # Log search paths that were checked
            if enable_multi_path and index_info.get("search_paths"):
                logger.debug(f"Searched {len(index_info['search_paths'])} paths:")
                for i, path in enumerate(index_info['search_paths'][:5]):
                    logger.debug(f"  {i+1}. {path}")
                if len(index_info['search_paths']) > 5:
                    logger.debug(f"  ... and {len(index_info['search_paths']) - 5} more")
        else:
            # No index found - provide detailed help
            logger.error("No index found after searching all configured paths")
            
            # Show what paths were searched
            if enable_multi_path and index_info.get("search_paths"):
                logger.error(f"Searched {len(index_info['search_paths'])} locations:")
                path_config = IndexPathConfig()
                validation = path_config.validate_paths(discovery._get_repository_identifier())
                
                for path, exists in list(validation.items())[:5]:
                    status = "EXISTS" if exists else "missing"
                    logger.error(f"  - {path} [{status}]")
                    
            logger.error("\nTo create an index:")
            logger.error("  1. Run: mcp-index index")
            logger.error("  2. Or copy an existing index to one of the search paths")
            logger.error("\nTo customize search paths:")
            logger.error("  export MCP_INDEX_PATHS=path1:path2:path3")
            
            raise FileNotFoundError("No index found in any configured location")
        
        # Check if we should use simple dispatcher
        if USE_SIMPLE_DISPATCHER:
            logger.info("Using SimpleDispatcher (BM25-only mode)")
            dispatcher = SimpleDispatcher(sqlite_store=sqlite_store)
        else:
            # Initialize plugin manager
            logger.info("Initializing plugin system...")
            config_path = Path("plugins.yaml")
            plugin_manager = PluginManager(sqlite_store=sqlite_store)
            
            # Load plugins with timeout protection
            logger.info(f"Loading plugins (timeout: {PLUGIN_LOAD_TIMEOUT}s)...")
            try:
                with timeout(PLUGIN_LOAD_TIMEOUT):
                    load_result = plugin_manager.load_plugins_safe(config_path if config_path.exists() else None)
                    
                    if not load_result.success:
                        logger.error(f"Plugin loading failed: {load_result.error.message}")
                    else:
                        logger.info(f"Plugin loading completed: {load_result.metadata}")
            except TimeoutError:
                logger.warning(f"Plugin loading timed out after {PLUGIN_LOAD_TIMEOUT} seconds")
                # Continue with empty plugin list
            
            # Get active plugin instances from plugin manager (for existing 6 plugins)
            active_plugins = plugin_manager.get_active_plugins() if plugin_manager else {}
            plugin_instances = list(active_plugins.values())
            
            logger.info(f"Loaded {len(plugin_instances)} active plugins from plugin manager")
            
            # Create enhanced dispatcher with dynamic plugin loading
            logger.info("Creating enhanced dispatcher with timeout protection...")
            # Note: EnhancedDispatcher has built-in 5-second timeout in _load_all_plugins()
            dispatcher = EnhancedDispatcher(
                plugins=plugin_instances,  # Use existing plugins as base
                sqlite_store=sqlite_store,
                enable_advanced_features=True,
                use_plugin_factory=True,  # Enable dynamic loading
                lazy_load=True,  # Load plugins on demand
                semantic_search_enabled=True,
                memory_aware=True,  # Enable memory-aware plugin management
                multi_repo_enabled=None  # Auto-detect from environment
            )
        
        supported_languages = dispatcher.supported_languages
        logger.info(f"Enhanced dispatcher created - supports {len(supported_languages)} languages")
        logger.info(f"Languages: {', '.join(supported_languages[:10])}{'...' if len(supported_languages) > 10 else ''}")
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}", exc_info=True)
        initialization_error = str(e)
        # Don't raise - let the server run but return errors in tools


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
                    "repository": {
                        "type": "string",
                        "description": "Repository ID, path, or git URL. Defaults to current repository."
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


def validate_index(store: SQLiteStore, repo_path: Path) -> dict:
    """Validate that the index is up-to-date and accessible."""
    import sqlite3
    
    issues = []
    stats = {}
    
    try:
        conn = sqlite3.connect(store.db_path)
        cursor = conn.cursor()
        
        # Check total file count
        cursor.execute("SELECT COUNT(*) FROM files")
        total_files = cursor.fetchone()[0]
        stats["total_files"] = total_files
        
        # Check BM25 content count
        cursor.execute("SELECT COUNT(*) FROM bm25_content")
        bm25_count = cursor.fetchone()[0]
        stats["bm25_documents"] = bm25_count
        
        # Check for current repository files
        cursor.execute("SELECT COUNT(*) FROM bm25_content WHERE filepath LIKE ?", (f"{repo_path}%",))
        current_repo_files = cursor.fetchone()[0]
        stats["current_repo_files"] = current_repo_files
        
        # Check for stale Docker paths
        cursor.execute("SELECT COUNT(*) FROM bm25_content WHERE filepath LIKE 'PathUtils.get_workspace_root() / %'")
        docker_files = cursor.fetchone()[0]
        stats["docker_files"] = docker_files
        
        # Validation checks
        if total_files == 0:
            issues.append("Index is empty - no files indexed")
        
        if bm25_count == 0:
            issues.append("No BM25 documents in index")
        
        if current_repo_files == 0 and docker_files > 0:
            issues.append(f"Index contains {docker_files} Docker paths but no files from current repo")
        
        # Sample path accessibility check
        cursor.execute("SELECT filepath FROM bm25_content LIMIT 10")
        sample_paths = cursor.fetchall()
        inaccessible_count = 0
        for (path,) in sample_paths:
            if not Path(path).exists():
                inaccessible_count += 1
        
        if inaccessible_count > len(sample_paths) * 0.5:
            issues.append(f"{inaccessible_count}/{len(sample_paths)} sampled paths are inaccessible")
        
        conn.close()
        
    except Exception as e:
        issues.append(f"Database error: {str(e)}")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "stats": stats
    }


def translate_path(path: str) -> str:
    """Translate Docker paths to current environment paths."""
    if not path:
        return ""
    
    # Handle Docker PathUtils.get_workspace_root() /  paths
    if path.startswith('PathUtils.get_workspace_root() / '):
        # Replace PathUtils.get_workspace_root() /  with current working directory
        translated = path.replace('PathUtils.get_workspace_root() / ', str(Path.cwd()) + '/', 1)
        # Verify the translated path exists
        if Path(translated).exists():
            return translated
        # Return relative path as fallback
        return path.replace('PathUtils.get_workspace_root() / ', '', 1)
    
    # Handle absolute paths that already exist
    if path.startswith('/') and Path(path).exists():
        return path
    
    # Handle relative paths
    if not path.startswith('/'):
        full_path = Path.cwd() / path
        if full_path.exists():
            return str(full_path)
    
    # Return original path if no translation worked
    return path


def ensure_response(data: Any) -> str:
    """Ensure response is never empty and always valid JSON."""
    if data is None:
        data = {"status": "empty", "message": "No data returned"}
    
    try:
        # Ensure it's valid JSON
        response = json.dumps(data, indent=2)
        
        # Log response in debug mode
        if DEBUG_MODE:
            logger.info(f"MCP Response: {response[:200]}...")
        
        # Ensure minimum size
        if len(response) < 10:
            response = json.dumps({
                "status": "minimal", 
                "original": str(data),
                "timestamp": time.time()
            }, indent=2)
        
        return response
    except Exception as e:
        # Fallback to ensure we always return something
        return json.dumps({
            "error": "Response serialization failed",
            "details": str(e),
            "timestamp": time.time()
        }, indent=2)


@server.call_tool()
async def call_tool(name: str, arguments: dict | None) -> Sequence[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool calls."""
    # Always log tool calls for debugging
    logger.info(f"=== MCP Tool Call ===")
    logger.info(f"Tool: {name}")
    logger.info(f"Arguments: {arguments}")
    logger.info(f"Thread: {threading.current_thread().name}")
    logger.info(f"Event loop: {asyncio.get_running_loop()}")
    
    # Track request time
    start_time = time.time()
    response = None
    
    try:
        if dispatcher is None:
            await initialize_services()
        
        # Check if initialization failed
        if initialization_error:
            error_response = {
                "error": "MCP server initialization failed",
                "details": initialization_error,
                "suggestion": "Check index exists at ~/.mcp/indexes/{repo_id}/current.db"
            }
            response = [types.TextContent(type="text", text=ensure_response(error_response))]
            return response
        
        # Check if dispatcher is still None
        if dispatcher is None:
            error_response = {
                "error": "MCP dispatcher not initialized",
                "details": "Unable to load dispatcher after initialization",
                "suggestion": "Check server logs for errors"
            }
            response = [types.TextContent(type="text", text=ensure_response(error_response))]
            return response
        if name == "symbol_lookup":
            symbol = arguments.get("symbol") if arguments else None
            if not symbol:
                error_response = {"error": "Missing parameter", "details": "'symbol' parameter is required"}
                response = [types.TextContent(type="text", text=ensure_response(error_response))]
            
            result = dispatcher.lookup(symbol)
            if result:
                # Translate Docker paths to current environment
                defined_in = result.get("defined_in", "")
                translated_path = translate_path(defined_in)
                
                response_data = {
                    "symbol": result.get("symbol"),
                    "kind": result.get("kind"),
                    "language": result.get("language"),
                    "signature": result.get("signature"),
                    "doc": result.get("doc"),
                    "defined_in": translated_path,
                    "line": result.get("line"),
                    "span": result.get("span")
                }
                
                # Add navigation hint if line number is available
                if result.get("line") and translated_path:
                    offset = result.get("line", 1) - 1
                    response_data["_usage_hint"] = f"To view definition: Read(file_path='{translated_path}', offset={offset}, limit=20)"
                
                response = [types.TextContent(type="text", text=ensure_response(response_data))]
            else:
                # Check index validation
                response_data = {
                    "result": "not_found",
                    "symbol": symbol,
                    "message": f"Symbol '{symbol}' not found in index"
                }
                
                if hasattr(dispatcher, '_sqlite_store') and dispatcher._sqlite_store:
                    validation_result = validate_index(dispatcher._sqlite_store, Path.cwd())
                    if not validation_result["valid"]:
                        response_data["index_issues"] = validation_result["issues"]
                        response_data["suggestion"] = "Index may be stale. Run 'python scripts/reindex_current_repo.py'"
                
                response = [types.TextContent(type="text", text=ensure_response(response_data))]
        
        elif name == "search_code":
            query = arguments.get("query") if arguments else None
            if not query:
                error_response = {"error": "Missing parameter", "details": "'query' parameter is required"}
                response = [types.TextContent(type="text", text=ensure_response(error_response))]
            
            semantic = arguments.get("semantic", False) if arguments else False
            limit = arguments.get("limit", 20) if arguments else 20
            repository = arguments.get("repository") if arguments else None
            
            # Handle multi-repository search if enabled
            if repository and hasattr(dispatcher, '_multi_repo_manager') and dispatcher._multi_repo_manager:
                try:
                    from ..storage.multi_repo_manager import MultiRepoIndexManager
                    repo_id = MultiRepoIndexManager.resolve_repo_id(repository)
                    
                    # Check authorization
                    if not dispatcher._multi_repo_manager.is_repo_authorized(repo_id):
                        error_response = {
                            "error": "Repository not authorized",
                            "repository": repository,
                            "repo_id": repo_id,
                            "message": "Add to MCP_REFERENCE_REPOS environment variable"
                        }
                        response = [types.TextContent(type="text", text=ensure_response(error_response))]
                        return response
                    
                    # Properly handle multi-repo search with timeout protection
                    try:
                        # Set a 10-second timeout for multi-repo search
                        search_results = await asyncio.wait_for(
                            dispatcher._multi_repo_manager.search_code(
                                query, 
                                repository_ids=[repo_id], 
                                limit=limit
                            ),
                            timeout=10.0
                        )
                        
                        # Convert CrossRepoSearchResult to standard format
                        results = []
                        for repo_result in search_results:
                            for r in repo_result.results:
                                results.append({
                                    'file': r.get('file', r.get('file_path', '')),
                                    'line': r.get('line', 0),
                                    'snippet': r.get('snippet', r.get('context', '')),
                                    'score': r.get('score', 0.0),
                                    'repository': repo_result.repository_name
                                })
                        
                        logger.info(f"Multi-repo search completed for '{query}' in repository {repository}")
                        
                    except asyncio.TimeoutError:
                        logger.warning(f"Multi-repo search timed out after 10s, falling back to single-repo search")
                        try:
                            results = await asyncio.wait_for(
                                asyncio.get_event_loop().run_in_executor(None,
                                    lambda: list(dispatcher.search(query, semantic=semantic, limit=limit))
                                ),
                                timeout=5.0  # Shorter timeout for fallback
                            )
                        except asyncio.TimeoutError:
                            logger.error(f"Fallback search also timed out")
                            results = []
                    except AttributeError as e:
                        # Handle case where search_code method doesn't exist
                        logger.warning(f"Multi-repo search method not available: {e}, falling back to single-repo search")
                        try:
                            results = await asyncio.wait_for(
                                asyncio.get_event_loop().run_in_executor(None,
                                    lambda: list(dispatcher.search(query, semantic=semantic, limit=limit))
                                ),
                                timeout=10.0
                            )
                        except asyncio.TimeoutError:
                            logger.error(f"Fallback search timed out")
                            results = []
                    except Exception as e:
                        logger.error(f"Multi-repo search failed: {e}, falling back to single-repo search")
                        try:
                            results = await asyncio.wait_for(
                                asyncio.get_event_loop().run_in_executor(None,
                                    lambda: list(dispatcher.search(query, semantic=semantic, limit=limit))
                                ),
                                timeout=10.0
                            )
                        except asyncio.TimeoutError:
                            logger.error(f"Fallback search timed out")
                            results = []
                    
                except Exception as e:
                    logger.error(f"Multi-repo search failed: {e}")
                    # Fall back to normal search with timeout
                    try:
                        results = await asyncio.wait_for(
                            asyncio.get_event_loop().run_in_executor(None,
                                lambda: list(dispatcher.search(query, semantic=semantic, limit=limit))
                            ),
                            timeout=10.0
                        )
                    except asyncio.TimeoutError:
                        logger.error(f"Fallback search also timed out")
                        results = []
            else:
                # Normal single-repo search with timeout protection
                logger.info(f"Executing single-repo search for query: {query}")
                try:
                    # Use asyncio timeout for consistency
                    # Create async wrapper for sync search method
                    async def async_search():
                        return list(dispatcher.search(query, semantic=semantic, limit=limit))
                    
                    # Run with timeout
                    results = await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(None, 
                            lambda: list(dispatcher.search(query, semantic=semantic, limit=limit))
                        ),
                        timeout=10.0
                    )
                    logger.info(f"Single-repo search completed with {len(results)} results")
                except asyncio.TimeoutError:
                    logger.error(f"Single-repo search timed out after 10s for query: {query}")
                    error_response = {
                        "error": "Search timeout",
                        "details": "Search operation exceeded 10 second timeout",
                        "query": query,
                        "suggestion": "Try a simpler query or check index status with get_status"
                    }
                    response = [types.TextContent(type="text", text=ensure_response(error_response))]
                    return response
                except Exception as e:
                    logger.error(f"Single-repo search failed: {e}")
                    error_response = {
                        "error": "Search failed",
                        "details": str(e),
                        "query": query
                    }
                    response = [types.TextContent(type="text", text=ensure_response(error_response))]
                    return response
            
            # Check if we have index validation info
            if hasattr(dispatcher, '_sqlite_store') and dispatcher._sqlite_store:
                validation_result = validate_index(dispatcher._sqlite_store, Path.cwd())
                if not validation_result["valid"] and len(results) == 0:
                    error_response = {
                        "error": "No results found - index may be stale",
                        "query": query,
                        "index_stats": validation_result["stats"],
                        "issues": validation_result["issues"],
                        "suggestion": "Run 'python scripts/reindex_current_repo.py' to update index"
                    }
                    response = [types.TextContent(type="text", text=ensure_response(error_response))]
                    return response
            
            # Add note if repository was specified
            multi_repo_info = None
            if repository and hasattr(dispatcher, '_multi_repo_manager') and dispatcher._multi_repo_manager:
                # Check if results include repository info
                has_repo_info = any('repository' in r for r in results if isinstance(r, dict))
                if has_repo_info:
                    multi_repo_info = f"Searched in repository: {repository}"
            
            if results:
                results_data = []
                for r in results:
                    # Translate Docker paths to current environment
                    file_path = translate_path(r.get("file", ""))
                    
                    result_item = {
                        "file": file_path,
                        "line": r.get("line"),
                        "snippet": r.get("snippet")
                    }
                    
                    # Add navigation hint if line number is available
                    if r.get("line") and file_path:
                        offset = r.get("line", 1) - 1
                        result_item["_usage_hint"] = f"For more context: Read(file_path='{file_path}', offset={offset}, limit=30)"
                    
                    results_data.append(result_item)
                    
                # Include repository info in response if applicable
                if multi_repo_info:
                    response_with_info = {
                        "results": results_data,
                        "search_scope": multi_repo_info,
                        "multi_repo": True
                    }
                    response = [types.TextContent(type="text", text=ensure_response(response_with_info))]
                else:
                    response = [types.TextContent(type="text", text=ensure_response(results_data))]
            else:
                response_data = {
                    "results": [],
                    "query": query,
                    "message": "No results found in index"
                }
                response = [types.TextContent(type="text", text=ensure_response(response_data))]
        
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
                "dispatcher_mode": "simple" if USE_SIMPLE_DISPATCHER else "enhanced",
                "features": {
                    "dynamic_loading": getattr(dispatcher, '_use_factory', False),
                    "lazy_loading": getattr(dispatcher, '_lazy_load', False),
                    "semantic_search": getattr(dispatcher, '_semantic_enabled', False),
                    "advanced_features": getattr(dispatcher, '_enable_advanced', False),
                    "timeout_protection": True  # All dispatchers now have timeout protection
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
            
            response = [types.TextContent(type="text", text=ensure_response(status_data))]
        
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
            
            response = [types.TextContent(type="text", text=ensure_response(response_data))]
        
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
                    
                    response = [types.TextContent(type="text", text=ensure_response(response_data))]
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
                
                response = [types.TextContent(type="text", text=ensure_response(response_data))]
        
        else:
            response = [types.TextContent(type="text", text=ensure_response({
                "error": "Unknown tool",
                "tool": name,
                "available_tools": ["symbol_lookup", "search_code", "get_status", "list_plugins", "reindex"]
            }))]
    
    except Exception as e:
        logger.error(f"Error in tool {name}: {e}", exc_info=True)
        error_response = {
            "error": f"Tool execution failed: {name}",
            "details": str(e),
            "tool": name
        }
        response = [types.TextContent(type="text", text=ensure_response(error_response))]
    finally:
        # Log response time and ensure we always return something
        elapsed = time.time() - start_time
        if DEBUG_MODE:
            logger.info(f"MCP Response time: {elapsed:.3f}s for tool {name}")
        
        # Ensure we have a response
        if response is None:
            response = [types.TextContent(type="text", text=ensure_response({
                "error": "No response generated",
                "tool": name,
                "elapsed": elapsed
            }))]
    
    # Log response
    elapsed = time.time() - start_time
    logger.info(f"=== MCP Tool Response ===")
    logger.info(f"Tool: {name}")
    logger.info(f"Elapsed: {elapsed:.2f}s")
    logger.info(f"Response type: {type(response)}")
    if response and len(response) > 0:
        logger.info(f"Response length: {len(response[0].text) if hasattr(response[0], 'text') else 'N/A'}")
    
    # Return the response
    return response


async def main():
    """Main entry point."""
    # Log configuration
    logger.info("=" * 60)
    logger.info("Code Index MCP Server Starting")
    logger.info(f"Dispatcher Mode: {'Simple (BM25-only)' if USE_SIMPLE_DISPATCHER else 'Enhanced (with plugins)'}")
    logger.info(f"Plugin Timeout: {PLUGIN_LOAD_TIMEOUT} seconds")
    logger.info(f"Debug Mode: {'Enabled' if DEBUG_MODE else 'Disabled'}")
    logger.info("=" * 60)
    
    # Try to initialize services on startup but don't fail if it doesn't work
    try:
        await initialize_services()
    except Exception as e:
        logger.error(f"Failed to initialize services on startup: {e}", exc_info=True)
        # Continue running - tools will return error messages
    
    # Run the stdio server
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())