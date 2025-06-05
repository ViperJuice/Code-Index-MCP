"""
Enhanced file watcher with subscription support.

This module extends the basic file watcher to integrate with the subscription
system for real-time notifications.
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from .dispatcher import Dispatcher
from .resources.subscriptions import (
    SubscriptionManager, 
    FileWatcherIntegration, 
    NotificationType
)

logger = logging.getLogger(__name__)


class _EnhancedHandler(FileSystemEventHandler):
    """Enhanced file system event handler with subscription support."""
    
    def __init__(self, 
                 dispatcher: Dispatcher, 
                 subscription_manager: Optional[SubscriptionManager] = None,
                 query_cache=None):
        self.dispatcher = dispatcher
        self.query_cache = query_cache
        self.subscription_manager = subscription_manager
        
        # Track supported file extensions
        self.code_extensions = {".py", ".js", ".c", ".cpp", ".dart", ".html", ".css"}
        
        # Set up subscription integration
        if self.subscription_manager:
            self.subscription_integration = FileWatcherIntegration(subscription_manager)
        else:
            self.subscription_integration = None
    
    async def invalidate_cache_for_file(self, path: Path):
        """Invalidate cache entries that depend on the changed file."""
        if self.query_cache:
            try:
                count = await self.query_cache.invalidate_file_queries(str(path))
                if count > 0:
                    logger.debug(f"Invalidated {count} cache entries for file {path}")
            except Exception as e:
                logger.error(f"Error invalidating cache for {path}: {e}")
    
    def trigger_reindex(self, path: Path):
        """Trigger re-indexing of a single file through the dispatcher."""
        try:
            if path.suffix in self.code_extensions:
                logger.info(f"Triggering re-index for {path}")
                self.dispatcher.index_file(path)
                
                # Invalidate cache entries for this file
                if self.query_cache:
                    import asyncio
                    try:
                        # Run cache invalidation in background
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            asyncio.create_task(self.invalidate_cache_for_file(path))
                        else:
                            asyncio.run(self.invalidate_cache_for_file(path))
                    except Exception as e:
                        logger.warning(f"Failed to invalidate cache for {path}: {e}")
        except Exception as e:
            logger.error(f"Error re-indexing {path}: {e}")
    
    async def notify_subscribers(self, event_type: NotificationType, path: Path):
        """Notify subscribers about file system events."""
        if self.subscription_integration:
            try:
                # Determine file language based on extension
                language_map = {
                    ".py": "python",
                    ".js": "javascript", 
                    ".c": "c",
                    ".cpp": "cpp",
                    ".dart": "dart",
                    ".html": "html",
                    ".css": "css"
                }
                
                metadata = {
                    "language": language_map.get(path.suffix, "unknown"),
                    "file_size": path.stat().st_size if path.exists() else 0,
                    "extension": path.suffix
                }
                
                if event_type == NotificationType.FILE_CREATED:
                    await self.subscription_integration.on_file_created(path, metadata)
                elif event_type == NotificationType.FILE_MODIFIED:
                    await self.subscription_integration.on_file_modified(path, metadata)
                elif event_type == NotificationType.FILE_DELETED:
                    await self.subscription_integration.on_file_deleted(path, metadata)
                    
            except Exception as e:
                logger.error(f"Error notifying subscribers about {path}: {e}")
    
    def on_created(self, event):
        """Handle file creation events."""
        if event.is_directory:
            return
        
        path = Path(event.src_path)
        logger.debug(f"File created: {path}")
        
        # Trigger re-indexing for code files
        if path.suffix in self.code_extensions:
            self.trigger_reindex(path)
        
        # Notify subscribers
        if self.subscription_integration:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self.notify_subscribers(NotificationType.FILE_CREATED, path))
                else:
                    asyncio.run(self.notify_subscribers(NotificationType.FILE_CREATED, path))
            except Exception as e:
                logger.warning(f"Failed to notify subscribers for created file {path}: {e}")
    
    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return
        
        path = Path(event.src_path)
        logger.debug(f"File modified: {path}")
        
        # Trigger re-indexing for code files
        if path.suffix in self.code_extensions:
            self.trigger_reindex(path)
        
        # Notify subscribers
        if self.subscription_integration:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self.notify_subscribers(NotificationType.FILE_MODIFIED, path))
                else:
                    asyncio.run(self.notify_subscribers(NotificationType.FILE_MODIFIED, path))
            except Exception as e:
                logger.warning(f"Failed to notify subscribers for modified file {path}: {e}")
    
    def on_deleted(self, event):
        """Handle file deletion events."""
        if event.is_directory:
            return
        
        path = Path(event.src_path)
        logger.debug(f"File deleted: {path}")
        
        # TODO: Remove file from index (handled by dispatcher)
        # For now, just log the deletion
        if path.suffix in self.code_extensions:
            logger.info(f"Code file deleted: {path}")
        
        # Notify subscribers
        if self.subscription_integration:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self.notify_subscribers(NotificationType.FILE_DELETED, path))
                else:
                    asyncio.run(self.notify_subscribers(NotificationType.FILE_DELETED, path))
            except Exception as e:
                logger.warning(f"Failed to notify subscribers for deleted file {path}: {e}")
    
    def on_moved(self, event):
        """Handle file move events."""
        if event.is_directory:
            return
        
        old_path = Path(event.src_path)
        new_path = Path(event.dest_path)
        logger.debug(f"File moved: {old_path} -> {new_path}")
        
        # Handle code file moves
        if old_path.suffix in self.code_extensions or new_path.suffix in self.code_extensions:
            if old_path.suffix in self.code_extensions:
                logger.info(f"Code file moved from {old_path}")
                # TODO: Remove old file from index
            
            if new_path.suffix in self.code_extensions and new_path.exists():
                self.trigger_reindex(new_path)
        
        # Notify subscribers about move
        if self.subscription_integration:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(
                        self.subscription_integration.on_file_moved(old_path, new_path)
                    )
                else:
                    asyncio.run(
                        self.subscription_integration.on_file_moved(old_path, new_path)
                    )
            except Exception as e:
                logger.warning(f"Failed to notify subscribers for moved file {old_path} -> {new_path}: {e}")


class EnhancedFileWatcher:
    """Enhanced file watcher with subscription support."""
    
    def __init__(self, 
                 root: Path, 
                 dispatcher: Dispatcher, 
                 subscription_manager: Optional[SubscriptionManager] = None,
                 query_cache=None):
        """
        Initialize enhanced file watcher.
        
        Args:
            root: Root directory to watch
            dispatcher: Dispatcher for re-indexing
            subscription_manager: Optional subscription manager for notifications
            query_cache: Optional query cache for invalidation
        """
        self.root = root
        self.dispatcher = dispatcher
        self.subscription_manager = subscription_manager
        self.query_cache = query_cache
        
        self._observer = Observer()
        self._handler = _EnhancedHandler(
            dispatcher, 
            subscription_manager, 
            query_cache
        )
        
        # Schedule the handler for the root directory
        self._observer.schedule(self._handler, str(root), recursive=True)
        
        logger.info(f"Enhanced file watcher initialized for {root}")
        if subscription_manager:
            logger.info("Subscription notifications enabled")
    
    def start(self):
        """Start watching for file system events."""
        self._observer.start()
        logger.info(f"Enhanced file watcher started for {self.root}")
    
    def stop(self):
        """Stop watching for file system events."""
        self._observer.stop()
        logger.info(f"Enhanced file watcher stopped for {self.root}")
    
    def join(self, timeout=None):
        """Wait for the watcher thread to finish."""
        self._observer.join(timeout)


# Convenience function for creating an enhanced watcher
def create_enhanced_watcher(root: Path, 
                          dispatcher: Dispatcher,
                          subscription_manager: Optional[SubscriptionManager] = None,
                          query_cache=None) -> EnhancedFileWatcher:
    """
    Create an enhanced file watcher with optional subscription support.
    
    Args:
        root: Root directory to watch
        dispatcher: Dispatcher for re-indexing
        subscription_manager: Optional subscription manager for notifications
        query_cache: Optional query cache for invalidation
    
    Returns:
        Configured EnhancedFileWatcher instance
    """
    return EnhancedFileWatcher(root, dispatcher, subscription_manager, query_cache)
