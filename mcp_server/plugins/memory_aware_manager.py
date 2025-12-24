"""
Memory-Aware Plugin Management System

This module implements intelligent memory management for language plugins,
including LRU caching, configurable memory limits, and transparent reloading.
"""

import gc
import logging
import os
import threading
import time
import weakref
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    import psutil
except ImportError:  # pragma: no cover - optional dependency
    psutil = None

# from mcp_server.plugin_system.models import LoadedPlugin
from mcp_server.plugins.plugin_factory import PluginFactory

logger = logging.getLogger(__name__)


@dataclass
class LoadedPlugin:
    """Represents a loaded plugin instance."""

    name: str
    instance: Any
    metadata: Dict[str, Any]


@dataclass
class PluginMemoryInfo:
    """Memory usage information for a plugin."""

    plugin_name: str
    memory_bytes: int
    last_used: datetime
    load_time: float
    usage_count: int
    is_high_priority: bool


class MemoryAwarePluginManager:
    """
    Manages plugins with memory awareness using LRU caching.

    Features:
    - Configurable memory limits (default 1GB)
    - LRU eviction of unused plugins
    - High-priority plugin protection
    - Transparent plugin reloading
    - Memory usage monitoring
    """

    def __init__(self, max_memory_mb: int = 1024, high_priority_langs: Optional[List[str]] = None):
        """
        Initialize the memory-aware plugin manager.

        Args:
            max_memory_mb: Maximum memory limit in MB (default 1024)
            high_priority_langs: Languages to keep in memory (e.g., ['python', 'javascript'])
        """
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.high_priority_langs = set(
            high_priority_langs or ["python", "javascript", "typescript"]
        )

        # Plugin storage with LRU ordering
        self._plugins: OrderedDict[str, LoadedPlugin] = OrderedDict()
        self._plugin_info: Dict[str, PluginMemoryInfo] = {}

        # Weak references for garbage collection tracking
        self._weak_refs: Dict[str, weakref.ref] = {}

        # Thread safety
        self._lock = threading.RLock()

        # Plugin factory for loading
        self._factory = PluginFactory()

        # Memory monitoring
        if psutil is None:
            self._process = None
            self._base_memory = 0
            logger.warning("psutil is not available; memory tracking is disabled")
        else:
            self._process = psutil.Process()
            self._base_memory = self._get_current_memory()

        logger.info(f"Memory-aware plugin manager initialized with {max_memory_mb}MB limit")

    def get_plugin(self, language: str) -> Optional[Any]:
        """
        Get a plugin for the specified language, loading if necessary.

        Args:
            language: Programming language name

        Returns:
            Plugin instance or None if not available
        """
        with self._lock:
            # Check if already loaded
            if language in self._plugins:
                # Move to end (most recently used)
                self._plugins.move_to_end(language)
                self._update_usage(language)
                return self._plugins[language].instance

            # Try to load the plugin
            return self._load_plugin(language)

    def _load_plugin(self, language: str) -> Optional[Any]:
        """Load a plugin with memory management."""
        start_time = time.time()

        # Check memory before loading
        if not self._ensure_memory_available():
            logger.warning(f"Cannot load {language} plugin - memory limit reached")
            return None

        try:
            # Load through factory
            plugin = self._factory.get_plugin(language)
            if not plugin:
                return None

            # Measure memory impact
            memory_before = self._get_current_memory()

            # Create loaded plugin wrapper
            loaded = LoadedPlugin(
                name=language,
                instance=plugin,
                metadata={"language": language, "loaded_at": datetime.now().isoformat()},
            )

            # Store plugin
            self._plugins[language] = loaded

            # Calculate memory usage
            memory_after = self._get_current_memory()
            memory_used = max(0, memory_after - memory_before)

            # Store memory info
            self._plugin_info[language] = PluginMemoryInfo(
                plugin_name=language,
                memory_bytes=memory_used,
                last_used=datetime.now(),
                load_time=time.time() - start_time,
                usage_count=1,
                is_high_priority=language in self.high_priority_langs,
            )

            # Create weak reference for GC tracking
            self._weak_refs[language] = weakref.ref(
                plugin, lambda ref, lang=language: self._on_plugin_deleted(lang)
            )

            logger.info(
                f"Loaded {language} plugin in {self._plugin_info[language].load_time:.2f}s, "
                f"using {memory_used / 1024 / 1024:.1f}MB"
            )

            return plugin

        except Exception as e:
            logger.error(f"Failed to load {language} plugin: {e}")
            return None

    def _ensure_memory_available(self) -> bool:
        """
        Ensure enough memory is available, evicting plugins if necessary.

        Returns:
            True if memory is available, False otherwise
        """
        current_memory = self._get_plugin_memory_usage()

        # Check if under limit
        if current_memory < self.max_memory_bytes:
            return True

        # Need to free memory - get eviction candidates
        candidates = self._get_eviction_candidates()

        # Evict until we have enough space (aim for 10% buffer)
        target_memory = self.max_memory_bytes * 0.9

        for language in candidates:
            if current_memory < target_memory:
                break

            evicted_memory = self._evict_plugin(language)
            current_memory -= evicted_memory

        return current_memory < self.max_memory_bytes

    def _get_eviction_candidates(self) -> List[str]:
        """Get list of plugins that can be evicted, ordered by priority."""
        candidates = []

        # Sort by last used time (LRU), excluding high priority
        for language, info in self._plugin_info.items():
            if not info.is_high_priority:
                candidates.append((info.last_used, language))

        # Sort by last used (oldest first)
        candidates.sort()

        return [lang for _, lang in candidates]

    def _evict_plugin(self, language: str) -> int:
        """
        Evict a plugin from memory.

        Returns:
            Memory freed in bytes
        """
        if language not in self._plugins:
            return 0

        info = self._plugin_info.get(language)
        memory_freed = info.memory_bytes if info else 0

        # Remove plugin
        plugin = self._plugins.pop(language, None)
        self._plugin_info.pop(language, None)
        self._weak_refs.pop(language, None)

        # Force garbage collection
        del plugin
        gc.collect()

        logger.info(f"Evicted {language} plugin, freed {memory_freed / 1024 / 1024:.1f}MB")

        return memory_freed

    def _update_usage(self, language: str):
        """Update usage statistics for a plugin."""
        if language in self._plugin_info:
            info = self._plugin_info[language]
            info.last_used = datetime.now()
            info.usage_count += 1

    def _get_current_memory(self) -> int:
        """Get current process memory usage in bytes."""
        if not self._process:
            return 0
        return self._process.memory_info().rss

    def _get_plugin_memory_usage(self) -> int:
        """Get total memory used by plugins."""
        return sum(info.memory_bytes for info in self._plugin_info.values())

    def _on_plugin_deleted(self, language: str):
        """Callback when a plugin is garbage collected."""
        logger.debug(f"Plugin {language} was garbage collected")
        self._plugin_info.pop(language, None)

    def get_memory_status(self) -> Dict[str, Any]:
        """Get current memory usage status."""
        with self._lock:
            current_memory = self._get_plugin_memory_usage()

            return {
                "max_memory_mb": self.max_memory_bytes / 1024 / 1024,
                "used_memory_mb": current_memory / 1024 / 1024,
                "available_memory_mb": (self.max_memory_bytes - current_memory) / 1024 / 1024,
                "usage_percent": (current_memory / self.max_memory_bytes) * 100,
                "loaded_plugins": len(self._plugins),
                "high_priority_plugins": list(self.high_priority_langs),
                "plugin_details": [
                    {
                        "language": info.plugin_name,
                        "memory_mb": info.memory_bytes / 1024 / 1024,
                        "last_used": info.last_used.isoformat(),
                        "usage_count": info.usage_count,
                        "is_high_priority": info.is_high_priority,
                        "load_time_seconds": info.load_time,
                    }
                    for info in sorted(
                        self._plugin_info.values(), key=lambda x: x.memory_bytes, reverse=True
                    )
                ],
            }

    def preload_high_priority(self):
        """Preload high-priority plugins."""
        logger.info(f"Preloading high-priority plugins: {self.high_priority_langs}")

        for language in self.high_priority_langs:
            self.get_plugin(language)

    def clear_cache(self, keep_high_priority: bool = True):
        """
        Clear plugin cache.

        Args:
            keep_high_priority: Whether to keep high-priority plugins loaded
        """
        with self._lock:
            languages = list(self._plugins.keys())

            for language in languages:
                info = self._plugin_info.get(language)
                if not keep_high_priority or not info or not info.is_high_priority:
                    self._evict_plugin(language)

    def set_high_priority_languages(self, languages: List[str]):
        """Update the list of high-priority languages."""
        with self._lock:
            self.high_priority_langs = set(languages)

            # Update existing plugin info
            for language, info in self._plugin_info.items():
                info.is_high_priority = language in self.high_priority_langs

    def get_plugin_info(self, language: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific plugin."""
        with self._lock:
            info = self._plugin_info.get(language)
            if not info:
                return None

            return {
                "language": info.plugin_name,
                "memory_mb": info.memory_bytes / 1024 / 1024,
                "last_used": info.last_used.isoformat(),
                "usage_count": info.usage_count,
                "is_high_priority": info.is_high_priority,
                "load_time_seconds": info.load_time,
                "is_loaded": language in self._plugins,
            }


# Singleton instance
_manager_instance: Optional[MemoryAwarePluginManager] = None
_manager_lock = threading.Lock()


def get_memory_aware_manager(
    max_memory_mb: Optional[int] = None, high_priority_langs: Optional[List[str]] = None
) -> MemoryAwarePluginManager:
    """
    Get the singleton memory-aware plugin manager.

    Args:
        max_memory_mb: Maximum memory limit (from env or default 1024)
        high_priority_langs: High-priority languages (from env or defaults)

    Returns:
        MemoryAwarePluginManager instance
    """
    global _manager_instance

    with _manager_lock:
        if _manager_instance is None:
            # Get configuration from environment
            if max_memory_mb is None:
                max_memory_mb = int(os.environ.get("MCP_MAX_MEMORY_MB", "1024"))

            if high_priority_langs is None:
                env_langs = os.environ.get("MCP_HIGH_PRIORITY_LANGS", "")
                if env_langs:
                    high_priority_langs = [lang.strip() for lang in env_langs.split(",")]
                else:
                    high_priority_langs = ["python", "javascript", "typescript"]

            _manager_instance = MemoryAwarePluginManager(
                max_memory_mb=max_memory_mb, high_priority_langs=high_priority_langs
            )

            # Preload high-priority plugins if configured
            if os.environ.get("MCP_PRELOAD_PLUGINS", "false").lower() == "true":
                _manager_instance.preload_high_priority()

        return _manager_instance
