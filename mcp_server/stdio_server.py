#!/usr/bin/env python3
"""
Stdio MCP server for MCP Inspector compatibility.
"""

import asyncio
import json
import logging
import sys
import os
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Run startup checks first
try:
    from mcp_server.startup_check import check_startup
    # Set MCP_MODE for proper error formatting
    os.environ["MCP_MODE"] = "1"
    check_startup()
except Exception as e:
    # If startup check itself fails, provide clear error
    error_msg = {
        "jsonrpc": "2.0",
        "error": {
            "code": -32603,
            "message": f"Startup check failed: {str(e)}",
            "data": {"hint": "Run 'python -m mcp_server.startup_check' for diagnostics"}
        },
        "id": None
    }
    print(json.dumps(error_msg))
    sys.exit(1)

from mcp_server.protocol import MCPProtocolHandler, JSONRPCRequest, JSONRPCResponse, JSONRPCError
from mcp_server.tools import get_registry, list_available_tools
from mcp_server.resources import ResourceRegistry
from mcp_server.prompts import get_prompt_registry
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.dispatcher.dispatcher import Dispatcher
from mcp_server.plugin_system.plugin_manager import PluginManager
from mcp_server.config.enhanced_settings import enhanced_settings as settings
from mcp_server.utils.feature_flags import feature_manager
from mcp_server.features import (
    setup_cache, setup_health_monitoring, setup_metrics,
    setup_rate_limiter, setup_memory_monitor, setup_graceful_shutdown
)

# Features are now directly imported above

# Setup logging to stderr so it doesn't interfere with stdio protocol
# Use enhanced settings for logging configuration
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
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
        self.cache_integration = None
        self.metrics_collector = None
        self.rate_limiter = None
        self.memory_monitor = None
        self.graceful_shutdown = None
        self.initialized = False
        self.start_time = time.time()
        # Initialize stdio for testing/mocking
        self.stdin = sys.stdin
        self.stdout = sys.stdout
    
    async def initialize(self):
        """Initialize server components."""
        # Get startup timeout from environment
        startup_timeout = int(os.getenv("STARTUP_TIMEOUT", "60"))  # Default 60 seconds
        
        try:
            logger.info(f"Initializing MCP stdio server (timeout: {startup_timeout}s)...")
            
            # Wrap entire initialization in timeout
            await asyncio.wait_for(self._do_initialize(), timeout=startup_timeout)
            
        except asyncio.TimeoutError:
            logger.error(f"Server initialization timed out after {startup_timeout}s")
            # For MCP compatibility, still mark as initialized but with reduced functionality
            self.initialized = True
            logger.warning("Server started with minimal features due to timeout")
        except Exception as e:
            logger.error(f"Failed to initialize server: {e}")
            raise
    
    async def _do_initialize(self):
        """Actual initialization logic."""
        # Initialize feature manager
        feature_manager.initialize_from_env()
        
        # Initialize storage
        self.storage = SQLiteStore(str(settings.db_path))
        logger.info("Storage initialized")
        
        # Check for minimal startup mode BEFORE creating plugin manager
        startup_mode = os.getenv("PLUGIN_STARTUP_MODE", "normal").lower()
        minimal_startup = startup_mode == "minimal"
        
        if minimal_startup:
            # Minimal startup: don't even create plugin manager, fastest possible start
            logger.info("Minimal startup mode enabled - plugins disabled for fastest startup")
            self.plugin_manager = None
            loaded_plugins = []
        else:
            # Initialize plugin manager only when needed
            plugin_manager = PluginManager(sqlite_store=self.storage)
            
            # Check if lazy loading is enabled
            lazy_loading = os.getenv("PLUGIN_LAZY_LOADING", "false").lower() in ("true", "1", "yes")
            
            if lazy_loading:
                # Lazy loading: skip all plugin loading, initialize on demand
                logger.info("Lazy plugin loading enabled - plugins will be initialized on first use")
                
                # Store plugin manager for lazy initialization without loading any plugins
                self.plugin_manager = plugin_manager
                loaded_plugins = []  # Start with no plugins loaded
            else:
                # Traditional loading: initialize all plugins now
                plugin_manager.load_plugins()
                
                # Get loaded plugin instances
                loaded_plugins = []
                for plugin_name in plugin_manager._instances:
                    plugin_instance = plugin_manager.get_plugin_instance(plugin_name)
                    if plugin_instance:
                        loaded_plugins.append(plugin_instance)
                logger.info(f"Loaded {len(loaded_plugins)} plugins")
                self.plugin_manager = plugin_manager
        
        # Initialize dispatcher with storage and plugins
        if minimal_startup or (hasattr(self, 'plugin_manager') and self.plugin_manager is not None):
            # Pass plugin manager for lazy loading or normal operation
            self.dispatcher = Dispatcher(plugins=loaded_plugins, storage=self.storage, plugin_manager=self.plugin_manager)
        else:
            self.dispatcher = Dispatcher(plugins=loaded_plugins, storage=self.storage)
        logger.info("Dispatcher initialized")
        
        # Initialize registries
        self.tool_registry = get_registry()
        self.resource_registry = ResourceRegistry()
        self.prompt_registry = get_prompt_registry()
        logger.info("Registries initialized")
        
        # Initialize protocol handler
        self.protocol_handler = MCPProtocolHandler()
        logger.info("Protocol handler initialized")
        
        # Check if we should auto-index
        if os.getenv("MCP_AUTO_INDEX", "").lower() in ("true", "1", "yes"):
            await self._auto_index_if_needed()
        
        # Initialize features after main initialization
        await self._initialize_features()
        
        self.initialized = True
        logger.info("MCP stdio server initialization complete")
    
    async def _auto_index_if_needed(self):
        """Auto-index codebase if database is empty."""
        try:
            # Check if we have any indexed files
            with self.storage._get_connection() as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM files")
                file_count = cursor.fetchone()[0]
            
            if file_count == 0:
                logger.info("No indexed files found, starting auto-indexing...")
                
                # Get workspace directory
                workspace_dir = os.getenv("CODEX_WORKSPACE_DIR", os.getcwd())
                
                # Find all supported files to index
                import glob
                from pathlib import Path
                
                # Common source file patterns
                patterns = [
                    "**/*.py",   # Python
                    "**/*.js",   # JavaScript
                    "**/*.ts",   # TypeScript
                    "**/*.jsx",  # React
                    "**/*.tsx",  # React TypeScript
                    "**/*.java", # Java
                    "**/*.kt",   # Kotlin
                    "**/*.go",   # Go
                    "**/*.rs",   # Rust
                    "**/*.c",    # C
                    "**/*.cpp",  # C++
                    "**/*.h",    # C/C++ headers
                    "**/*.cs",   # C#
                    "**/*.rb",   # Ruby
                    "**/*.php",  # PHP
                    "**/*.dart", # Dart
                    "**/*.swift",# Swift
                ]
                
                all_files = []
                for pattern in patterns:
                    files = glob.glob(f"{workspace_dir}/{pattern}", recursive=True)
                    all_files.extend(files)
                
                # Remove duplicates and filter out common non-source directories
                unique_files = []
                seen = set()
                for file_path in all_files:
                    if file_path not in seen:
                        # Skip common non-source directories
                        if any(skip in file_path for skip in [
                            "__pycache__", ".venv", "venv", "env",
                            "node_modules", ".git", "dist", "build",
                            "target", ".idea", ".vscode", "__pycache__"
                        ]):
                            continue
                        seen.add(file_path)
                        unique_files.append(file_path)
                
                indexed_count = 0
                # Index files using the dispatcher (limit for initial indexing)
                for file_path in unique_files[:100]:  # Limit to 100 files
                    try:
                        # The dispatcher will automatically detect language
                        # and route to the appropriate plugin
                        await self.dispatcher.index_file(Path(file_path))
                        indexed_count += 1
                    except Exception as e:
                        logger.debug(f"Failed to index {file_path}: {e}")
                
                logger.info(f"Auto-indexed {indexed_count} files")
            else:
                logger.info(f"Database contains {file_count} files, skipping auto-index")
                
        except Exception as e:
            logger.warning(f"Auto-indexing failed: {e}")
            # Don't fail server startup if auto-indexing fails
    
    async def _initialize_features(self):
        """Initialize all enabled features concurrently."""
        try:
            # Initialize feature manager from environment
            feature_manager.initialize_from_env()
            
            # Collect initialization tasks for enabled features
            initialization_tasks = []
            feature_names = []
            
            # Cache
            if feature_manager.is_enabled('cache'):
                initialization_tasks.append(self._init_cache())
                feature_names.append('cache')
            
            # Health monitoring  
            if feature_manager.is_enabled('health'):
                initialization_tasks.append(self._init_health())
                feature_names.append('health')
            
            # Metrics
            if feature_manager.is_enabled('metrics'):
                initialization_tasks.append(self._init_metrics())
                feature_names.append('metrics')
            
            # Rate limiting
            if feature_manager.is_enabled('rate_limit'):
                initialization_tasks.append(self._init_rate_limiter())
                feature_names.append('rate_limit')
            
            # Memory monitoring
            if feature_manager.is_enabled('memory_monitor'):
                initialization_tasks.append(self._init_memory_monitor())
                feature_names.append('memory_monitor')
            
            # Initialize all features concurrently
            if initialization_tasks:
                logger.info(f"Initializing {len(initialization_tasks)} features...")
                results = await asyncio.gather(*initialization_tasks, return_exceptions=True)
                
                # Check for errors and log successful initializations
                successful_features = []
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        logger.error(f"Failed to initialize feature {feature_names[i]}: {result}")
                    else:
                        successful_features.append(feature_names[i])
                
                if successful_features:
                    logger.info(f"Successfully initialized features: {', '.join(successful_features)}")
            else:
                logger.debug("No optional features enabled")
            
            # Set up graceful shutdown integration (after other features)
            # Skip graceful shutdown in minimal startup mode to avoid conflicts
            startup_mode = os.getenv("PLUGIN_STARTUP_MODE", "normal").lower()
            if startup_mode != "minimal":
                self.graceful_shutdown = setup_graceful_shutdown(self)
                if self.graceful_shutdown:
                    await self.graceful_shutdown.initialize()
                    logger.info("Graceful shutdown handlers installed")
            else:
                logger.debug("Graceful shutdown disabled in minimal startup mode")
                
        except Exception as e:
            logger.error(f"Feature initialization failed: {e}")
            # Don't fail server startup if feature initialization fails
    
    async def _init_cache(self):
        """Initialize cache integration."""
        try:
            self.cache_integration = await setup_cache(self)
            if self.cache_integration:
                logger.info("✓ Cache integration initialized")
        except Exception as e:
            logger.error(f"Failed to initialize cache: {e}")
            raise
    
    async def _init_health(self):
        """Initialize health monitoring integration."""
        try:
            self.health_monitor = await setup_health_monitoring(self)
            if self.health_monitor:
                logger.info("✓ Health monitoring initialized")
        except Exception as e:
            logger.error(f"Failed to initialize health monitoring: {e}")
            raise
    
    async def _init_metrics(self):
        """Initialize metrics integration."""
        try:
            self.metrics_collector = await setup_metrics(self)
            if self.metrics_collector:
                logger.info("✓ Metrics collection initialized")
        except Exception as e:
            logger.error(f"Failed to initialize metrics: {e}")
            raise
    
    async def _init_rate_limiter(self):
        """Initialize rate limiter integration."""
        try:
            self.rate_limiter = await setup_rate_limiter(self)
            if self.rate_limiter:
                logger.info("✓ Rate limiter initialized")
        except Exception as e:
            logger.error(f"Failed to initialize rate limiter: {e}")
            raise
    
    async def _init_memory_monitor(self):
        """Initialize memory monitor integration."""
        try:
            self.memory_monitor = await setup_memory_monitor(self)
            if self.memory_monitor:
                logger.info("✓ Memory monitor initialized")
        except Exception as e:
            logger.error(f"Failed to initialize memory monitor: {e}")
            raise
    
    async def handle_request(self, request_data: str) -> str:
        """Handle request with feature integrations."""
        # Check if shutting down
        if self.graceful_shutdown and self.graceful_shutdown.is_shutdown_requested():
            return self._shutdown_response()
        
        # Track operation for graceful shutdown
        if self.graceful_shutdown:
            return await self.graceful_shutdown.track_operation(
                self._handle_request_internal(request_data)
            )
        else:
            return await self._handle_request_internal(request_data)
    
    async def _handle_request_internal(self, request_data: str) -> str:
        """Internal request handler with metrics and rate limiting."""
        start_time = time.time()
        method = None
        status = "success"
        
        try:
            # Parse JSON-RPC request
            data = json.loads(request_data.strip())
            method = data.get("method", "unknown")
            
            # Check rate limiting if available
            if hasattr(self, 'rate_limiter') and self.rate_limiter and hasattr(self.rate_limiter, 'check_rate_limit'):
                is_allowed, wait_time = await self.rate_limiter.check_rate_limit(method)
                if not is_allowed:
                    error = JSONRPCError(
                        code=-32603,
                        message=f"Rate limit exceeded. Try again in {wait_time:.1f}s",
                        data={"retry_after": wait_time}
                    )
                    response = JSONRPCResponse(error=error, id=data.get("id"))
                    return json.dumps(response.to_dict())
            
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
                # Check if resources are disabled
                if os.getenv("MCP_DISABLE_RESOURCES", "").lower() in ("true", "1", "yes"):
                    error = JSONRPCError(code=-32601, message="Resources not supported", data={"method": request.method})
                    response = JSONRPCResponse(error=error, id=request.id)
                    return json.dumps(response.to_dict())
                return await self.handle_resources_list(request)
            elif request.method == "resources/read":
                # Check if resources are disabled
                if os.getenv("MCP_DISABLE_RESOURCES", "").lower() in ("true", "1", "yes"):
                    error = JSONRPCError(code=-32601, message="Resources not supported", data={"method": request.method})
                    response = JSONRPCResponse(error=error, id=request.id)
                    return json.dumps(response.to_dict())
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
            status = "error"
            # Parse error
            error = JSONRPCError(
                code=-32700,
                message="Parse error",
                data={"error": str(e)}
            )
            response = JSONRPCResponse(error=error, id=None)
            return json.dumps(response.to_dict())
        
        except Exception as e:
            status = "error"
            # Internal error
            error = JSONRPCError(
                code=-32603,
                message="Internal error",
                data={"error": str(e)}
            )
            response = JSONRPCResponse(error=error, id=data.get("id") if 'data' in locals() else None)
            return json.dumps(response.to_dict())
        
        finally:
            # Record metrics if available
            if self.metrics_collector and method:
                duration = time.time() - start_time
                await self.metrics_collector.record_request_metrics(
                    method, duration, status
                )
    
    def _shutdown_response(self):
        """Return shutdown response."""
        return json.dumps({
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": "Server is shutting down"
            },
            "id": None
        })
    
    async def handle_initialize(self, request: JSONRPCRequest) -> str:
        """Handle initialize request."""
        # Check if resources should be disabled for Claude Code compatibility
        disable_resources = os.getenv("MCP_DISABLE_RESOURCES", "").lower() in ("true", "1", "yes")
        
        capabilities = {
            "tools": {
                "listChanged": True
            },
            "prompts": {
                "listChanged": True
            }
        }
        
        # Only add resources if not disabled
        if not disable_resources:
            capabilities["resources"] = {
                "subscribe": True,
                "listChanged": True
            }
        
        result = {
            "protocolVersion": "2024-11-05",
            "capabilities": capabilities,
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
        
        logger.info(f"Executing tool: {tool_name} with arguments: {arguments}")
        
        try:
            # Create execution context with dispatcher
            context = {
                "dispatcher": self.dispatcher,
                "storage": self.storage
            }
            
            # Execute the tool through the registry
            start_time = time.time()
            result = await self.tool_registry.execute(tool_name, arguments, context)
            execution_time = time.time() - start_time
            
            # Format the result based on the tool and its output
            if isinstance(result, dict):
                # Tool returned structured data - format it nicely
                if tool_name == "search_code" and "results" in result:
                    results = result["results"]
                    result_text = f"🔍 **Code Search Results for '{arguments.get('query', '')}'**\n\n"
                    if results:
                        for i, r in enumerate(results[:10], 1):
                            result_text += f"{i}. `{r['file']}:{r['line']}` - {r['content'].strip()[:100]}...\n"
                        if len(results) > 10:
                            result_text += f"\n... and {len(results) - 10} more results"
                    else:
                        result_text += "No results found."
                    result_text += f"\n\n⏱️ Search completed in {execution_time:.2f}s"
                    
                elif tool_name == "index_file" and "statistics" in result:
                    stats = result["statistics"]
                    result_text = f"✅ **Indexing Complete**\n\n"
                    result_text += f"📁 Path: `{result.get('path', 'unknown')}`\n"
                    result_text += f"📊 Files: {stats.get('successful_files', 0)} succeeded, {stats.get('failed_files', 0)} failed\n"
                    result_text += f"🔤 Symbols: {stats.get('total_symbols', 0)} found\n"
                    result_text += f"💾 Size: {stats.get('total_size_mb', 0):.1f} MB processed\n"
                    result_text += f"⏱️ Time: {stats.get('total_time_seconds', 0):.2f}s\n"
                    
                    # Add language breakdown if available
                    if "languages" in stats and stats["languages"]:
                        result_text += f"\n🗣️ **Languages:**\n"
                        for lang, count in stats["languages"].items():
                            result_text += f"  • {lang}: {count} files\n"
                    
                elif tool_name == "lookup_symbol" and "symbol" in result:
                    result_text = f"🔎 **Symbol: `{result['symbol']}`**\n\n"
                    if result.get("found"):
                        result_text += f"📁 File: `{result['file']}:{result['line']}`\n"
                        result_text += f"🏷️ Type: {result.get('type', 'unknown')}\n"
                        result_text += f"✍️ Signature: `{result.get('signature', 'N/A')}`\n"
                        if result.get("docstring"):
                            result_text += f"\n📝 **Documentation:**\n{result['docstring']}\n"
                    else:
                        result_text += "Symbol not found in indexed files."
                        
                elif tool_name == "find_references" and "references" in result:
                    refs = result["references"]
                    result_text = f"📍 **References for `{arguments.get('symbol', '')}`**\n\n"
                    if refs:
                        result_text += f"Found {len(refs)} reference(s):\n\n"
                        for i, ref in enumerate(refs[:10], 1):
                            result_text += f"{i}. `{ref['file']}:{ref['line']}` - {ref.get('context', '').strip()[:80]}...\n"
                        if len(refs) > 10:
                            result_text += f"\n... and {len(refs) - 10} more references"
                    else:
                        result_text += "No references found."
                        
                else:
                    # Generic structured result
                    result_text = f"✅ **{tool_name} completed**\n\n"
                    result_text += json.dumps(result, indent=2)
                    
            elif isinstance(result, str):
                # Tool returned plain text
                result_text = result
            else:
                # Tool returned something else
                result_text = f"✅ Tool '{tool_name}' executed successfully.\n\nResult: {str(result)}"
            
            # Log execution for debugging
            logger.info(f"Tool {tool_name} completed in {execution_time:.2f}s")
            
            # Handle cache invalidation and metrics updates for successful indexing operations
            if tool_name == "index_file" and isinstance(result, dict) and "statistics" in result:
                # Cache invalidation after successful indexing
                if self.cache_integration:
                    try:
                        await self.cache_integration.clear()
                        logger.debug("Cleared cache after successful indexing operation")
                    except Exception as e:
                        logger.warning(f"Failed to clear cache after indexing: {e}")
                
                # Update index metrics after successful indexing
                if self.metrics_collector:
                    try:
                        stats = result.get("statistics", {})
                        # Record indexing metrics
                        self.metrics_collector.increment_counter("index_operations_total", 1.0, {"tool": "index_file"})
                        self.metrics_collector.set_gauge("index_files_processed", stats.get("successful_files", 0))
                        self.metrics_collector.set_gauge("index_symbols_total", stats.get("total_symbols", 0))
                        self.metrics_collector.observe_histogram("index_operation_duration_seconds", execution_time)
                        logger.debug("Updated index metrics after successful indexing operation")
                    except Exception as e:
                        logger.warning(f"Failed to update index metrics: {e}")
            
            response_data = {
                "content": [
                    {
                        "type": "text",
                        "text": result_text
                    }
                ]
            }
            
            response = JSONRPCResponse(result=response_data, id=request.id)
            return json.dumps(response.to_dict())
            
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
            error = JSONRPCError(
                code=-32603,
                message=f"Error executing tool: {str(e)}"
            )
            response = JSONRPCResponse(error=error, id=request.id)
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
        
        # Create async stdin reader for continuous operation
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        
        # Connect to stdin using asyncio
        transport, _ = await asyncio.get_event_loop().connect_read_pipe(
            lambda: protocol, sys.stdin
        )
        
        try:
            # Continuously read from stdin
            while True:
                try:
                    # Check for graceful shutdown
                    if self.graceful_shutdown and self.graceful_shutdown.is_shutdown_requested():
                        logger.info("Graceful shutdown requested, stopping request processing")
                        break
                    
                    # Read line from stdin with timeout to allow shutdown checks
                    try:
                        line_bytes = await asyncio.wait_for(reader.readline(), timeout=1.0)
                    except asyncio.TimeoutError:
                        # Timeout allows us to check shutdown status periodically
                        continue
                    
                    # Check if stdin was closed (EOF)
                    if not line_bytes:
                        logger.info("Stdin closed (EOF), shutting down server")
                        break
                    
                    line = line_bytes.decode('utf-8').strip()
                    if not line:
                        continue
                    
                    logger.info(f"Received request: {line[:100]}...")
                    
                    # Handle the request
                    response = await self.handle_request(line)
                    
                    # Send response to stdout
                    print(response)
                    sys.stdout.flush()
                    
                    logger.info(f"Sent response: {response[:100]}...")
                    
                except asyncio.CancelledError:
                    logger.info("Request processing cancelled")
                    break
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
        
        finally:
            # Close transport when done
            transport.close()
    

    async def get_server_status(self) -> dict:
        """Get comprehensive server status."""
        # Initialize feature manager if not already done
        if not feature_manager._initialized:
            feature_manager.initialize_from_env()
            
        status = {
            "server": "running",
            "features": feature_manager.get_enabled_features(),
            "uptime": self._get_uptime()
        }
        
        # Add feature-specific status if available
        if hasattr(self, 'health_monitor') and self.health_monitor:
            try:
                status["health"] = await self.health_monitor.get_health_report()
            except Exception as e:
                status["health"] = {"error": str(e)}
        
        if hasattr(self, 'metrics_collector') and self.metrics_collector:
            try:
                status["metrics"] = await self.metrics_collector.get_metrics_summary()
            except Exception as e:
                status["metrics"] = {"error": str(e)}
        
        if hasattr(self, 'cache_integration') and self.cache_integration:
            try:
                status["cache"] = await self.cache_integration.get_cache_stats()
            except Exception as e:
                status["cache"] = {"error": str(e)}
        
        if hasattr(self, 'rate_limiter') and self.rate_limiter:
            try:
                status["rate_limits"] = await self.rate_limiter.get_rate_limit_stats()
            except Exception as e:
                status["rate_limits"] = {"error": str(e)}
        
        if hasattr(self, 'memory_monitor') and self.memory_monitor:
            try:
                status["memory"] = await self.memory_monitor.get_memory_report()
            except Exception as e:
                status["memory"] = {"error": str(e)}
        
        return status

    async def shutdown(self):
        """Shutdown server with graceful handling."""
        logger.info("Shutting down MCP stdio server...")
        
        # Use graceful shutdown if available
        if hasattr(self, 'graceful_shutdown') and self.graceful_shutdown:
            try:
                await self.graceful_shutdown.shutdown()
            except Exception as e:
                logger.error(f"Graceful shutdown failed: {e}")
                await self._manual_shutdown()
        else:
            # Manual shutdown if graceful shutdown not available
            await self._manual_shutdown()

    async def _manual_shutdown(self):
        """Manual shutdown of all features."""
        logger.info("Performing manual shutdown of server features...")
        shutdown_tasks = []
        
        # Shutdown feature integrations if they exist
        if hasattr(self, 'cache_integration') and self.cache_integration:
            try:
                shutdown_tasks.append(self.cache_integration.shutdown())
            except Exception as e:
                logger.error(f"Cache shutdown error: {e}")
        
        if hasattr(self, 'health_monitor') and self.health_monitor:
            try:
                shutdown_tasks.append(self.health_monitor.shutdown())
            except Exception as e:
                logger.error(f"Health monitor shutdown error: {e}")
        
        if hasattr(self, 'metrics_collector') and self.metrics_collector:
            try:
                shutdown_tasks.append(self.metrics_collector.shutdown())
            except Exception as e:
                logger.error(f"Metrics collector shutdown error: {e}")
        
        if hasattr(self, 'rate_limiter') and self.rate_limiter:
            try:
                shutdown_tasks.append(self.rate_limiter.shutdown())
            except Exception as e:
                logger.error(f"Rate limiter shutdown error: {e}")
        
        if hasattr(self, 'memory_monitor') and self.memory_monitor:
            try:
                shutdown_tasks.append(self.memory_monitor.shutdown())
            except Exception as e:
                logger.error(f"Memory monitor shutdown error: {e}")
        
        # Shutdown core components
        if self.storage:
            try:
                # Close storage connections
                if hasattr(self.storage, 'close'):
                    shutdown_tasks.append(self.storage.close())
            except Exception as e:
                logger.error(f"Storage shutdown error: {e}")
        
        # Shutdown all features concurrently
        if shutdown_tasks:
            try:
                await asyncio.gather(*shutdown_tasks, return_exceptions=True)
            except Exception as e:
                logger.error(f"Error during concurrent shutdown: {e}")
        
        logger.info("Server shutdown complete")

    def _get_uptime(self) -> str:
        """Get server uptime in human-readable format."""
        uptime_seconds = time.time() - self.start_time
        
        if uptime_seconds < 60:
            return f"{uptime_seconds:.1f} seconds"
        elif uptime_seconds < 3600:
            minutes = uptime_seconds / 60
            return f"{minutes:.1f} minutes"
        else:
            hours = uptime_seconds / 3600
            return f"{hours:.1f} hours"


async def main():
    """Main entry point for stdio server with enhanced error handling."""
    import signal
    
    server = StdioMCPServer()
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        if server.graceful_shutdown:
            server.graceful_shutdown.signal_shutdown()
        else:
            # Fallback for immediate shutdown
            sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await server.run()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
    finally:
        await server.shutdown()


if __name__ == "__main__":
    asyncio.run(main())