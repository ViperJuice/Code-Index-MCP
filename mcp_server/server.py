"""
Main MCP server with all advanced features integrated.

This is the consolidated entry point for the complete MCP server.
"""

import asyncio
import logging
import signal
import sys
from typing import Optional, Dict, Any
from pathlib import Path
import json

# Core MCP components
from .protocol.handler import ProtocolHandler
from .protocol.advanced import AdvancedProtocolHandler
from .transport.stdio import StdioTransport
from .transport.websocket import WebSocketTransport
from .session.manager import SessionManager
from .tools.manager import ToolManager
from .resources.manager import ResourceManager
from .prompts.registry import prompt_registry
from .dispatcher.dispatcher import Dispatcher

# Performance and production features
from .performance.connection_pool import connection_pool_manager
from .performance.memory_optimizer import memory_optimizer
from .performance.rate_limiter import rate_limiter
from .production.logger import production_logger, LogConfig, LogLevel
from .production.health import health_checker
from .production.monitoring import monitoring_system
from .production.middleware import middleware_stack

# Cache system
from .cache.cache_manager import CacheManager, CacheConfig, CacheBackendType

# Plugin system
from .plugin_system.plugin_manager import PluginManager

# Configuration
from .config.settings import Settings

logger = logging.getLogger(__name__)


class MCPServer:
    """Main MCP server with all advanced features."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.settings = Settings()
        if config_path:
            self.settings.load_from_file(config_path)
        
        # Core components
        self.session_manager = SessionManager()
        self.tool_manager = ToolManager()
        self.resource_manager = ResourceManager()
        self.dispatcher = Dispatcher([])
        self.plugin_manager = PluginManager()
        
        # Protocol handlers
        self.protocol_handler = ProtocolHandler(
            self.session_manager,
            self.tool_manager,
            self.resource_manager,
            prompt_registry
        )
        self.advanced_handler = AdvancedProtocolHandler(self.protocol_handler.handle_request)
        
        # Transport
        self.transport: Optional[Any] = None
        
        # Performance and production
        self.cache_manager: Optional[CacheManager] = None
        
        # State
        self.running = False
        self._shutdown_event = asyncio.Event()
    
    async def initialize(self) -> None:
        """Initialize all server components."""
        logger.info("Initializing MCP server...")
        
        # Initialize production logging
        log_config = LogConfig(
            level=LogLevel.INFO if not self.settings.debug else LogLevel.DEBUG,
            enable_console=True,
            enable_file=True,
            file_path=self.settings.log_file
        )
        production_logger.config = log_config
        production_logger.start()
        
        # Initialize cache manager
        cache_config = CacheConfig(
            backend_type=CacheBackendType.MEMORY,
            max_entries=self.settings.cache_max_entries,
            max_memory_mb=self.settings.cache_max_memory_mb,
            default_ttl=self.settings.cache_default_ttl
        )
        self.cache_manager = CacheManager(cache_config)
        await self.cache_manager.initialize()
        
        # Initialize memory optimizer
        await memory_optimizer.start_monitoring()
        
        # Initialize rate limiter
        await rate_limiter.start()
        
        # Initialize monitoring system
        await monitoring_system.start()
        
        # Initialize health checker
        health_checker.register_callback(self._health_callback)
        await health_checker.start_monitoring()
        
        # Initialize connection pool manager
        await connection_pool_manager.start_all()
        
        # Initialize plugin manager
        await self.plugin_manager.initialize()
        await self.plugin_manager.discover_plugins()
        
        # Load and register plugins
        for plugin_name in self.settings.enabled_plugins:
            try:
                await self.plugin_manager.load_plugin(plugin_name)
                plugin = self.plugin_manager.get_plugin(plugin_name)
                if plugin:
                    # Register plugin tools
                    tools = await plugin.get_tools()
                    for tool in tools:
                        self.tool_manager.register_tool(tool)
                    
                    # Register plugin resources
                    resources = await plugin.get_resources()
                    for resource in resources:
                        self.resource_manager.register_resource(resource)
                        
                logger.info(f"Loaded plugin: {plugin_name}")
            except Exception as e:
                logger.error(f"Failed to load plugin {plugin_name}: {e}")
        
        # Initialize transport
        if self.settings.transport_type == "stdio":
            self.transport = StdioTransport()
        elif self.settings.transport_type == "websocket":
            self.transport = WebSocketTransport(
                host=self.settings.websocket_host,
                port=self.settings.websocket_port
            )
        else:
            raise ValueError(f"Unknown transport type: {self.settings.transport_type}")
        
        # Set up protocol handler
        self.transport.set_handler(self._handle_message)
        
        # Initialize session manager
        await self.session_manager.initialize()
        
        logger.info("MCP server initialized successfully")
    
    async def start(self) -> None:
        """Start the MCP server."""
        if self.running:
            logger.warning("Server already running")
            return
        
        try:
            await self.initialize()
            
            self.running = True
            logger.info(f"Starting MCP server with {self.settings.transport_type} transport...")
            
            # Set up signal handlers
            self._setup_signal_handlers()
            
            # Start transport
            await self.transport.start()
            
            # Record server start metrics
            await monitoring_system.metrics.counter("server_starts_total")
            await monitoring_system.metrics.gauge("server_uptime_seconds", 0)
            
            logger.info("MCP server started successfully")
            
            # Wait for shutdown
            await self._shutdown_event.wait()
            
        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            raise
        finally:
            await self.shutdown()
    
    async def shutdown(self) -> None:
        """Shutdown the MCP server."""
        if not self.running:
            return
        
        logger.info("Shutting down MCP server...")
        self.running = False
        
        try:
            # Stop transport
            if self.transport:
                await self.transport.stop()
            
            # Stop all components
            await health_checker.stop_monitoring()
            await monitoring_system.stop()
            await rate_limiter.stop()
            await memory_optimizer.stop_monitoring()
            await connection_pool_manager.stop_all()
            
            # Shutdown cache manager
            if self.cache_manager:
                await self.cache_manager.shutdown()
            
            # Shutdown plugin manager
            await self.plugin_manager.shutdown()
            
            # Shutdown session manager
            await self.session_manager.shutdown()
            
            # Stop production logging
            production_logger.stop()
            
            logger.info("MCP server shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating shutdown...")
            self._shutdown_event.set()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def _handle_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle incoming messages through middleware and protocol handlers."""
        from .protocol.jsonrpc import JsonRpcRequest, JsonRpcNotification
        
        try:
            # Parse message
            if "id" in message:
                request = JsonRpcRequest.from_dict(message)
            else:
                request = JsonRpcNotification.from_dict(message)
            
            # Process through middleware stack
            response = await middleware_stack.process_request(
                request,
                self._route_request,
                self._get_client_info()
            )
            
            # Convert response to dict if needed
            if response:
                return response.to_dict() if hasattr(response, 'to_dict') else response
            
            return None
            
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            # Return error response for requests with ID
            if "id" in message:
                from .protocol.errors import McpError, ErrorCode
                error = McpError(
                    code=ErrorCode.INTERNAL_ERROR,
                    message=f"Message handling error: {str(e)}"
                )
                return {
                    "jsonrpc": "2.0",
                    "id": message.get("id"),
                    "error": error.to_dict()
                }
            return None
    
    async def _route_request(self, request) -> Optional[Any]:
        """Route request to appropriate handler."""
        method = request.method
        
        # Route to advanced features
        if method.startswith("completion/"):
            return await self.advanced_handler.handle_completion(request.params or {})
        elif method.startswith("stream/"):
            if method == "stream/start":
                return await self.advanced_handler.handle_stream_start(request.params or {})
            elif method == "stream/read":
                return await self.advanced_handler.handle_stream_read(request.params or {})
            elif method == "stream/close":
                return await self.advanced_handler.handle_stream_close(request.params or {})
        elif method == "batch":
            return await self.advanced_handler.handle_batch(request.params or {})
        
        # Route to standard protocol handler
        return await self.protocol_handler.handle_request(request)
    
    def _get_client_info(self) -> Dict[str, Any]:
        """Get client information for middleware."""
        # This would be populated by transport layer
        return {
            "client_ip": "127.0.0.1",  # Default for local connections
            "user_agent": "MCP Client"
        }
    
    def _health_callback(self, report) -> None:
        """Callback for health check reports."""
        if report.overall_status.value in ["unhealthy", "critical"]:
            logger.warning(f"Health check failed: {report.overall_status.value}")
    
    async def get_server_status(self) -> Dict[str, Any]:
        """Get comprehensive server status."""
        health_report = await health_checker.run_checks()
        dashboard_data = await monitoring_system.get_dashboard_data()
        middleware_stats = middleware_stack.get_combined_stats()
        
        return {
            "server": {
                "running": self.running,
                "transport": self.settings.transport_type,
                "version": "1.0.0"
            },
            "health": health_checker.to_dict(health_report),
            "metrics": dashboard_data["metrics"],
            "alerts": dashboard_data["alerts"],
            "middleware": middleware_stats,
            "plugins": {
                "loaded": list(self.plugin_manager.get_loaded_plugins().keys()),
                "available": list(self.plugin_manager.get_available_plugins().keys())
            },
            "tools": {
                "count": len(self.tool_manager.list_tools())
            },
            "resources": {
                "count": len(self.resource_manager.list_resources())
            },
            "timestamp": dashboard_data["timestamp"]
        }


async def main():
    """Main entry point for the MCP server."""
    import argparse
    
    parser = argparse.ArgumentParser(description="MCP Server")
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument("--transport", choices=["stdio", "websocket"], 
                       default="stdio", help="Transport type")
    parser.add_argument("--host", default="localhost", help="WebSocket host")
    parser.add_argument("--port", type=int, default=8000, help="WebSocket port")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
    args = parser.parse_args()
    
    # Create server
    server = MCPServer(args.config)
    
    # Override settings from command line
    if args.transport:
        server.settings.transport_type = args.transport
    if args.host:
        server.settings.websocket_host = args.host
    if args.port:
        server.settings.websocket_port = args.port
    if args.debug:
        server.settings.debug = args.debug
    
    try:
        await server.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())