"""
Example of full feature integration into StdioMCPServer.

This shows how all the features would be integrated. The actual implementation
would be done by patching the existing stdio_server.py file.
"""
import os
import asyncio
import logging
from typing import Optional

# Import feature integrations
from mcp_server.utils.feature_flags import feature_manager
from mcp_server.config.enhanced_settings import enhanced_settings
from mcp_server.features import (
    setup_cache, setup_health_monitoring, setup_metrics,
    setup_rate_limiter, setup_memory_monitor, setup_graceful_shutdown
)

logger = logging.getLogger(__name__)


class EnhancedStdioMCPServer:
    """Enhanced StdioMCPServer with all optional features."""
    
    def __init__(self):
        # ... existing initialization ...
        
        # Feature integrations
        self.cache_integration = None
        self.health_monitor = None
        self.metrics_collector = None
        self.rate_limiter = None
        self.memory_monitor = None
        self.graceful_shutdown = None
        
        # Initialize feature manager
        feature_manager.initialize_from_env()
        
        # Apply enhanced settings
        self._apply_settings()
        
        # Show feature status in debug mode
        if enhanced_settings.debug:
            feature_manager.print_feature_status()
            enhanced_settings.print_summary()
    
    def _apply_settings(self):
        """Apply enhanced settings."""
        # Configure logging
        if enhanced_settings.log_level:
            logging.getLogger().setLevel(enhanced_settings.log_level.upper())
        
        if enhanced_settings.log_file:
            # Add file handler
            file_handler = logging.FileHandler(enhanced_settings.log_file)
            file_handler.setFormatter(
                logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            )
            logging.getLogger().addHandler(file_handler)
    
    async def initialize(self):
        """Initialize server with all features."""
        # ... existing initialization ...
        
        # Initialize optional features
        await self._initialize_features()
        
        # Set up graceful shutdown
        self.graceful_shutdown = setup_graceful_shutdown(self)
    
    async def _initialize_features(self):
        """Initialize all enabled features."""
        initialization_tasks = []
        
        # Cache
        if feature_manager.is_enabled('cache'):
            initialization_tasks.append(self._init_cache())
        
        # Health monitoring
        if feature_manager.is_enabled('health'):
            initialization_tasks.append(self._init_health())
        
        # Metrics
        if feature_manager.is_enabled('metrics'):
            initialization_tasks.append(self._init_metrics())
        
        # Rate limiting
        if feature_manager.is_enabled('rate_limit'):
            initialization_tasks.append(self._init_rate_limiter())
        
        # Memory monitoring
        if feature_manager.is_enabled('memory_monitor'):
            initialization_tasks.append(self._init_memory_monitor())
        
        # Initialize all features concurrently
        if initialization_tasks:
            logger.info(f"Initializing {len(initialization_tasks)} features...")
            results = await asyncio.gather(*initialization_tasks, return_exceptions=True)
            
            # Check for errors
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Failed to initialize feature: {result}")
    
    async def _init_cache(self):
        """Initialize cache integration."""
        self.cache_integration = await setup_cache(self)
        if self.cache_integration:
            logger.info("✓ Cache integration initialized")
    
    async def _init_health(self):
        """Initialize health monitoring."""
        self.health_monitor = await setup_health_monitoring(self)
        if self.health_monitor:
            logger.info("✓ Health monitoring initialized")
    
    async def _init_metrics(self):
        """Initialize metrics collection."""
        self.metrics_collector = await setup_metrics(self)
        if self.metrics_collector:
            logger.info("✓ Metrics collection initialized")
    
    async def _init_rate_limiter(self):
        """Initialize rate limiting."""
        self.rate_limiter = await setup_rate_limiter(self)
        if self.rate_limiter:
            logger.info("✓ Rate limiting initialized")
    
    async def _init_memory_monitor(self):
        """Initialize memory monitoring."""
        self.memory_monitor = await setup_memory_monitor(self)
        if self.memory_monitor:
            logger.info("✓ Memory monitoring initialized")
    
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
        """Internal request handler with metrics."""
        import time
        start_time = time.time()
        method = None
        status = "success"
        
        try:
            # Parse request to get method
            import json
            data = json.loads(request_data.strip())
            method = data.get("method", "unknown")
            
            # ... existing request handling ...
            result = await self._process_request(data)
            
            return result
            
        except Exception as e:
            status = "error"
            logger.error(f"Request error: {e}")
            raise
            
        finally:
            # Record metrics
            if self.metrics_collector and method:
                duration = time.time() - start_time
                await self.metrics_collector.record_request_metrics(
                    method, duration, status
                )
    
    async def handle_tools_call(self, request):
        """Handle tools/call with cache invalidation."""
        # ... existing implementation ...
        
        # If indexing completed successfully, clear cache
        if self.cache_integration and request.params.get("name") == "index_file":
            # Check if indexing was successful
            # Clear cache to ensure fresh results
            await self.cache_integration.clear_cache()
            logger.debug("Cleared cache after indexing")
        
        # Update metrics after indexing
        if self.metrics_collector and request.params.get("name") == "index_file":
            await self.metrics_collector.update_index_metrics()
    
    async def get_server_status(self) -> dict:
        """Get comprehensive server status."""
        status = {
            "server": "running",
            "features": feature_manager.get_enabled_features(),
            "uptime": self._get_uptime()
        }
        
        # Add feature-specific status
        if self.health_monitor:
            status["health"] = await self.health_monitor.get_health_report()
        
        if self.metrics_collector:
            status["metrics"] = await self.metrics_collector.get_metrics_summary()
        
        if self.cache_integration:
            status["cache"] = await self.cache_integration.get_cache_stats()
        
        if self.rate_limiter:
            status["rate_limits"] = await self.rate_limiter.get_rate_limit_stats()
        
        if self.memory_monitor:
            status["memory"] = await self.memory_monitor.get_memory_report()
        
        return status
    
    async def shutdown(self):
        """Shutdown server with all features."""
        logger.info("Shutting down enhanced MCP server...")
        
        # Graceful shutdown handles everything
        if self.graceful_shutdown:
            await self.graceful_shutdown.shutdown()
        else:
            # Manual shutdown if graceful shutdown not available
            await self._manual_shutdown()
    
    async def _manual_shutdown(self):
        """Manual shutdown of all features."""
        shutdown_tasks = []
        
        if self.cache_integration:
            shutdown_tasks.append(self.cache_integration.shutdown())
        
        if self.health_monitor:
            shutdown_tasks.append(self.health_monitor.shutdown())
        
        if self.metrics_collector:
            shutdown_tasks.append(self.metrics_collector.shutdown())
        
        if self.rate_limiter:
            shutdown_tasks.append(self.rate_limiter.shutdown())
        
        if self.memory_monitor:
            shutdown_tasks.append(self.memory_monitor.shutdown())
        
        # Shutdown all features concurrently
        if shutdown_tasks:
            await asyncio.gather(*shutdown_tasks, return_exceptions=True)
        
        logger.info("Server shutdown complete")
    
    def _shutdown_response(self):
        """Return shutdown response."""
        import json
        return json.dumps({
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": "Server is shutting down"
            },
            "id": None
        })
    
    def _get_uptime(self):
        """Get server uptime."""
        # Implementation depends on when server started
        return "N/A"


# Example usage showing all features
async def main():
    """Main entry point with all features."""
    server = EnhancedStdioMCPServer()
    
    try:
        await server.initialize()
        logger.info("Enhanced MCP server ready")
        
        # Wait for shutdown signal
        if server.graceful_shutdown:
            await server.graceful_shutdown.wait_for_shutdown()
        else:
            # Simple wait
            await asyncio.Event().wait()
            
    except Exception as e:
        logger.error(f"Server error: {e}")
    finally:
        await server.shutdown()


if __name__ == "__main__":
    # Example with all features enabled
    os.environ["MCP_ENABLE_CACHE"] = "true"
    os.environ["MCP_ENABLE_HEALTH"] = "true"
    os.environ["MCP_ENABLE_METRICS"] = "true"
    os.environ["MCP_ENABLE_RATE_LIMIT"] = "true"
    os.environ["MCP_MONITOR_MEMORY"] = "true"
    os.environ["MCP_LOG_LEVEL"] = "INFO"
    
    asyncio.run(main())