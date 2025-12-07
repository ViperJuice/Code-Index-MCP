import logging
from pathlib import Path
from typing import Optional

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from .core.path_resolver import PathResolver
from .dispatcher.dispatcher_enhanced import EnhancedDispatcher
from .plugins.language_registry import get_all_extensions

# Note: We've removed ignore pattern checks - ALL files are indexed locally
# from .core.ignore_patterns import should_ignore_file

logger = logging.getLogger(__name__)


class _Handler(FileSystemEventHandler):
    def __init__(
        self,
        dispatcher: EnhancedDispatcher,
        query_cache=None,
        path_resolver: Optional[PathResolver] = None,
    ):
        self.dispatcher = dispatcher
        self.query_cache = query_cache
        self.path_resolver = path_resolver or PathResolver()
        # Track supported file extensions - dynamically get all supported extensions
        self.code_extensions = get_all_extensions()

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

    def remove_file_from_index(self, path: Path):
        """Remove a file from all indexes."""
        try:
            if path.suffix in self.code_extensions:
                logger.info(f"Removing file from index: {path}")
                self.dispatcher.remove_file(path)

                # Invalidate cache entries for this file
                if self.query_cache:
                    import asyncio

                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            asyncio.create_task(self.invalidate_cache_for_file(path))
                        else:
                            asyncio.run(self.invalidate_cache_for_file(path))
                    except Exception as e:
                        logger.warning(f"Failed to invalidate cache for {path}: {e}")
        except Exception as e:
            logger.error(f"Error removing {path} from index: {e}")

    def handle_file_move(self, old_path: Path, new_path: Path):
        """Handle file move operations efficiently."""
        try:
            if old_path.suffix in self.code_extensions and new_path.suffix in self.code_extensions:
                # Compute content hash to check if file actually changed
                if new_path.exists():
                    content_hash = self.path_resolver.compute_content_hash(new_path)
                    logger.info(f"Moving file in index: {old_path} -> {new_path}")
                    self.dispatcher.move_file(old_path, new_path, content_hash)
                else:
                    # New path doesn't exist, just remove old
                    self.remove_file_from_index(old_path)
        except Exception as e:
            logger.error(f"Error handling file move {old_path} -> {new_path}: {e}")

    def on_any_event(self, event):
        """Handle any file system event and trigger re-indexing for code files."""
        if event.is_directory:
            return

        path = Path(event.src_path)

        # For creation and modification events, trigger re-indexing
        if event.event_type in ("created", "modified"):
            if path.suffix in self.code_extensions and path.exists():
                self.trigger_reindex(path)

        # For move events, handle both source and destination
        elif event.event_type == "moved":
            old_path = Path(event.src_path)
            new_path = Path(event.dest_path)
            self.handle_file_move(old_path, new_path)

        # For deletion events, remove from index
        elif event.event_type == "deleted":
            if path.suffix in self.code_extensions:
                self.remove_file_from_index(path)

    def on_modified(self, event):
        """Handle file modification events."""
        # Let on_any_event handle this

    def on_deleted(self, event):
        """Handle file deletion events."""
        # Let on_any_event handle this

    def on_moved(self, event):
        """Handle file move events."""
        # Let on_any_event handle this

    def on_created(self, event):
        """Handle file creation events."""
        # Let on_any_event handle this


class FileWatcher:
    def __init__(
        self,
        root: Path,
        dispatcher: EnhancedDispatcher,
        query_cache=None,
        path_resolver: Optional[PathResolver] = None,
    ):
        self._observer = Observer()
        self._observer.schedule(
            _Handler(dispatcher, query_cache, path_resolver), str(root), recursive=True
        )

    def start(self):
        self._observer.start()

    def stop(self):
        self._observer.stop()
