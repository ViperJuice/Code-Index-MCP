from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import logging
from typing import Optional
from .dispatcher import Dispatcher

logger = logging.getLogger(__name__)

class _Handler(FileSystemEventHandler):
    def __init__(self, dispatcher: Dispatcher, query_cache=None):
        self.dispatcher = dispatcher
        self.query_cache = query_cache
        # Track supported file extensions
        self.code_extensions = {'.py', '.js', '.c', '.cpp', '.dart', '.html', '.css'}
    
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
    
    def on_any_event(self, event):
        """Handle any file system event and trigger re-indexing for code files."""
        if event.is_directory:
            return
        
        path = Path(event.src_path)
        
        # Check if this is a code file we should index
        if path.suffix in self.code_extensions and path.exists():
            # For creation and modification events, trigger re-indexing
            if event.event_type in ('created', 'modified'):
                self.trigger_reindex(path)
            # For move events, handle both source and destination
            elif event.event_type == 'moved':
                # Remove old file from index (handled by dispatcher)
                old_path = Path(event.src_path)
                if old_path.suffix in self.code_extensions:
                    logger.info(f"File moved from {old_path}")
                    # TODO: Add remove_file method to dispatcher
                # Index new file location
                new_path = Path(event.dest_path)
                if new_path.suffix in self.code_extensions and new_path.exists():
                    self.trigger_reindex(new_path)

    def on_modified(self, event):
        """Handle file modification events."""
        # Let on_any_event handle this
        pass

class FileWatcher:
    def __init__(self, root: Path, dispatcher: Dispatcher, query_cache=None):
        self._observer = Observer()
        self._observer.schedule(_Handler(dispatcher, query_cache), str(root), recursive=True)

    def start(self): self._observer.start()
    def stop(self): self._observer.stop()
