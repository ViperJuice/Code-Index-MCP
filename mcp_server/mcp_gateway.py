"""MCP Server Gateway - Main entry point for MCP protocol server"""
import asyncio
import logging
import signal
from typing import Optional, Dict, Any
from pathlib import Path

from .protocol import MCPProtocolHandler
from .transport import WebSocketTransport, StdioTransport
from .tools.manager import ToolManager
from .resources.manager import ResourceManager
from .dispatcher import Dispatcher
from .storage.sqlite_store import SQLiteStore
from .watcher import FileWatcher
from .settings import settings

logger = logging.getLogger(__name__)

class MCPServer:
    """Main MCP server that coordinates all components"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize MCP server
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        
        # Core components
        self.storage = None
        self.dispatcher = None
        self.watcher = None
        self.protocol_handler = None
        self.tool_manager = None
        self.resource_manager = None
        self.transport = None
        
        # Server state
        self._running = False
        self._shutdown_event = asyncio.Event()
        
    async def initialize(self):
        """Initialize all server components"""
        logger.info("Initializing MCP server...")
        
        try:
            # Initialize storage
            db_path = self.config.get('db_path', str(settings.db_path))
            self.storage = SQLiteStore(db_path)
            
            # Initialize dispatcher with empty plugins list initially
            # Plugins will be loaded by the plugin system later
            self.dispatcher = Dispatcher([])
            
            # Initialize file watcher
            from pathlib import Path
            watch_path = Path(self.config.get('watch_paths', ['.'])[0])
            # Note: The file watcher will need to be updated to work with the dispatcher
            # For now, we'll create a simple watcher without dispatcher dependency
            self.watcher = None  # TODO: Implement compatible file watcher
            
            # Initialize protocol handler
            self.protocol_handler = MCPProtocolHandler(
                dispatcher=self.dispatcher,
                storage=self.storage,
                watcher=self.watcher
            )
            
            # Initialize tool manager
            self.tool_manager = ToolManager(
                dispatcher=self.dispatcher,
                storage=self.storage
            )
            
            # Initialize resource manager
            self.resource_manager = ResourceManager(
                storage=self.storage,
                dispatcher=self.dispatcher
            )
            
            # Set base path for resource manager
            base_path = self.config.get('base_path', '.')
            self.resource_manager.set_base_path(base_path)
            
            # Connect managers to protocol handler
            self.protocol_handler.set_tool_manager(self.tool_manager)
            self.protocol_handler.set_resource_manager(self.resource_manager)
            
            # Initialize transport based on config
            transport_type = self.config.get('transport', 'websocket')
            if transport_type == 'websocket':
                self.transport = WebSocketTransport(self.protocol_handler)
            elif transport_type == 'stdio':
                self.transport = StdioTransport(self.protocol_handler)
            else:
                raise ValueError(f"Unknown transport type: {transport_type}")
            
            # Setup watcher notifications
            await self._setup_watcher_notifications()
            
            logger.info("MCP server initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize MCP server: {e}", exc_info=True)
            raise
    
    async def _setup_watcher_notifications(self):
        """Setup file watcher to send MCP notifications"""
        if not self.watcher or not self.transport:
            return
        
        async def on_file_changed(event):
            """Handle file change events"""
            try:
                # Create notification
                notification = {
                    "method": "notifications/resources/changed",
                    "params": {
                        "changes": [{
                            "uri": f"code://file/{event.path}",
                            "type": event.type  # created, modified, deleted
                        }]
                    }
                }
                
                # Send to all connected clients
                if hasattr(self.transport, 'send_notification'):
                    await self.transport.send_notification(
                        method=notification["method"],
                        params=notification["params"]
                    )
                    
                # Notify resource manager
                await self.resource_manager.notify_resource_change(
                    f"code://file/{event.path}",
                    event.type
                )
                
            except Exception as e:
                logger.error(f"Error sending file change notification: {e}")
        
        # Register callback
        self.watcher.on_change = on_file_changed
    
    async def start(self):
        """Start the MCP server"""
        if self._running:
            logger.warning("Server already running")
            return
        
        logger.info("Starting MCP server...")
        
        try:
            # Start protocol handler
            await self.protocol_handler.start()
            
            # Start file watcher
            if self.watcher:
                await self.watcher.start()
            
            # Start transport
            if self.transport:
                transport_config = self.config.get('transport_config', {})
                await self.transport.connect(**transport_config)
            
            self._running = True
            logger.info("MCP server started successfully")
            
            # Wait for shutdown
            await self._shutdown_event.wait()
            
        except Exception as e:
            logger.error(f"Error starting MCP server: {e}", exc_info=True)
            raise
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the MCP server"""
        if not self._running:
            return
        
        logger.info("Stopping MCP server...")
        
        try:
            # Stop transport
            if self.transport:
                await self.transport.disconnect()
            
            # Stop file watcher
            if self.watcher:
                await self.watcher.stop()
            
            # Stop protocol handler
            if self.protocol_handler:
                await self.protocol_handler.stop()
            
            # Close dispatcher
            if self.dispatcher:
                await self.dispatcher.close()
            
            # Close storage
            if self.storage:
                await self.storage.close()
            
            self._running = False
            logger.info("MCP server stopped")
            
        except Exception as e:
            logger.error(f"Error stopping MCP server: {e}", exc_info=True)
    
    def shutdown(self):
        """Signal server shutdown"""
        logger.info("Shutdown requested")
        self._shutdown_event.set()
    
    async def handle_signal(self, sig):
        """Handle system signals"""
        logger.info(f"Received signal {sig.name}")
        self.shutdown()

async def main():
    """Main entry point"""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Load configuration
    config = {
        'transport': 'websocket',
        'transport_config': {
            'host': '0.0.0.0',
            'port': 8765
        },
        'db_path': './code_index.db',
        'watch_paths': ['.'],
        'base_path': '.',
        'dispatcher': {
            'max_workers': 4,
            'batch_size': 100
        }
    }
    
    # Create and initialize server
    server = MCPServer(config)
    await server.initialize()
    
    # Setup signal handlers
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(
            sig,
            lambda s=sig: asyncio.create_task(server.handle_signal(s))
        )
    
    # Start server
    try:
        await server.start()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
    finally:
        await server.stop()

if __name__ == "__main__":
    asyncio.run(main())