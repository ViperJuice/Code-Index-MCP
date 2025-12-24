"""Plugin router components for enhanced routing and file type matching.

This module provides advanced plugin routing capabilities including:
- Enhanced plugin routing by file extension, language, and MIME type
- Plugin capability matching and priority routing
- Load balancing across plugins
- Caching for performance optimization
"""

import logging
import mimetypes
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from ..plugin_base import IPlugin
from ..plugins.language_registry import get_language_by_extension

logger = logging.getLogger(__name__)


@dataclass
class PluginCapability:
    """Represents a capability that a plugin provides."""

    name: str
    version: str = "1.0.0"
    description: str = ""
    priority: int = 0  # Higher values = higher priority
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FileTypeInfo:
    """Information about a file type for routing decisions."""

    extension: str
    mime_type: Optional[str] = None
    language: Optional[str] = None
    is_binary: bool = False
    encoding: str = "utf-8"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RouteResult:
    """Result of plugin routing operation."""

    plugin: IPlugin
    confidence: float  # 0.0 to 1.0
    match_reasons: List[str]
    capabilities: List[PluginCapability]
    metadata: Dict[str, Any] = field(default_factory=dict)


class IFileTypeMatcher(ABC):
    """Interface for matching files to their types and characteristics."""

    @abstractmethod
    def get_file_info(self, path: Path) -> FileTypeInfo:
        """Get detailed information about a file type.

        Args:
            path: Path to the file

        Returns:
            FileTypeInfo containing details about the file type
        """

    @abstractmethod
    def is_supported(self, path: Path) -> bool:
        """Check if a file type is supported by any plugin.

        Args:
            path: Path to the file

        Returns:
            True if file type is supported
        """

    @abstractmethod
    def get_language(self, path: Path) -> Optional[str]:
        """Detect the programming language of a file.

        Args:
            path: Path to the file

        Returns:
            Programming language name or None if not detected
        """


class IPluginRouter(ABC):
    """Interface for routing requests to appropriate plugins."""

    @abstractmethod
    def route_file(self, path: Path) -> List[RouteResult]:
        """Route a file to appropriate plugins.

        Args:
            path: Path to the file

        Returns:
            List of RouteResults ordered by confidence/priority
        """

    @abstractmethod
    def route_by_capability(self, capability: str, **kwargs) -> List[RouteResult]:
        """Route based on required capability.

        Args:
            capability: Required capability name
            **kwargs: Additional routing parameters

        Returns:
            List of RouteResults for plugins with the capability
        """

    @abstractmethod
    def route_by_language(self, language: str) -> List[RouteResult]:
        """Route based on programming language.

        Args:
            language: Programming language name

        Returns:
            List of RouteResults for plugins supporting the language
        """

    @abstractmethod
    def get_best_plugin(self, path: Path) -> Optional[RouteResult]:
        """Get the single best plugin for a file.

        Args:
            path: Path to the file

        Returns:
            Best RouteResult or None if no suitable plugin found
        """


class FileTypeMatcher(IFileTypeMatcher):
    """Advanced file type matcher with support for extensions, MIME types, and language detection."""

    # DEPRECATED: Use get_language_by_extension from language_registry instead
    # Keeping for backward compatibility only
    LANGUAGE_MAP = {
        ".py": "python",
        ".pyi": "python",
        ".pyx": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".mjs": "javascript",
        ".cjs": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".c": "c",
        ".h": "c",
        ".cpp": "cpp",
        ".cxx": "cpp",
        ".cc": "cpp",
        ".hpp": "cpp",
        ".hxx": "cpp",
        ".hh": "cpp",
        ".java": "java",
        ".kt": "kotlin",
        ".kts": "kotlin",
        ".go": "go",
        ".rs": "rust",
        ".rb": "ruby",
        ".php": "php",
        ".swift": "swift",
        ".dart": "dart",
        ".scala": "scala",
        ".clj": "clojure",
        ".cljs": "clojure",
        ".hs": "haskell",
        ".ml": "ocaml",
        ".mli": "ocaml",
        ".fs": "fsharp",
        ".fsx": "fsharp",
        ".r": "r",
        ".R": "r",
        ".m": "objective-c",
        ".mm": "objective-c",
        ".sh": "shell",
        ".bash": "shell",
        ".zsh": "shell",
        ".fish": "shell",
        ".ps1": "powershell",
        ".psm1": "powershell",
        ".sql": "sql",
        ".lua": "lua",
        ".pl": "perl",
        ".pm": "perl",
        ".vim": "vim",
        ".html": "html",
        ".htm": "html",
        ".xhtml": "html",
        ".css": "css",
        ".scss": "scss",
        ".sass": "sass",
        ".less": "less",
        ".xml": "xml",
        ".xsl": "xml",
        ".xsd": "xml",
        ".json": "json",
        ".jsonc": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".toml": "toml",
        ".ini": "ini",
        ".cfg": "ini",
        ".conf": "config",
        ".md": "markdown",
        ".markdown": "markdown",
        ".mdown": "markdown",
        ".mkd": "markdown",
        ".tex": "latex",
        ".dockerfile": "dockerfile",
        ".makefile": "makefile",
        ".cmake": "cmake",
        ".gradle": "gradle",
        ".sbt": "sbt",
    }

    # Binary file extensions
    BINARY_EXTENSIONS = {
        ".exe",
        ".dll",
        ".so",
        ".dylib",
        ".a",
        ".lib",
        ".o",
        ".obj",
        ".zip",
        ".tar",
        ".gz",
        ".bz2",
        ".xz",
        ".7z",
        ".rar",
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".bmp",
        ".tiff",
        ".webp",
        ".ico",
        ".mp3",
        ".mp4",
        ".avi",
        ".mov",
        ".wmv",
        ".flv",
        ".mkv",
        ".webm",
        ".pdf",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
        ".bin",
        ".dat",
        ".db",
        ".sqlite",
        ".sqlite3",
        ".class",
        ".jar",
        ".war",
        ".ear",
        ".pyc",
        ".pyo",
        ".pyd",
    }

    def __init__(self):
        """Initialize the file type matcher."""
        # Initialize MIME types
        mimetypes.init()

        # Cache for file info lookups
        self._cache: Dict[str, FileTypeInfo] = {}
        self._cache_timeout = 300  # 5 minutes
        self._cache_timestamps: Dict[str, float] = {}

    @lru_cache(maxsize=1000)
    def get_file_info(self, path: Path) -> FileTypeInfo:
        """Get detailed information about a file type."""
        path_str = str(path)
        current_time = time.time()

        # Check cache
        if (
            path_str in self._cache
            and path_str in self._cache_timestamps
            and current_time - self._cache_timestamps[path_str] < self._cache_timeout
        ):
            return self._cache[path_str]

        # Determine file characteristics
        extension = path.suffix.lower()
        mime_type, _ = mimetypes.guess_type(str(path))
        language = get_language_by_extension(extension)
        is_binary = extension in self.BINARY_EXTENSIONS

        # Special handling for files without extensions
        if not extension:
            name_lower = path.name.lower()
            if name_lower in ["dockerfile", "makefile", "rakefile", "gemfile"]:
                language = name_lower
                mime_type = "text/plain"
            elif name_lower.startswith("makefile"):
                language = "makefile"
                mime_type = "text/plain"

        # Determine encoding
        encoding = "utf-8"
        if is_binary:
            encoding = "binary"
        elif extension in {".txt", ".log", ".out"}:
            encoding = "utf-8"

        file_info = FileTypeInfo(
            extension=extension,
            mime_type=mime_type,
            language=language,
            is_binary=is_binary,
            encoding=encoding,
            metadata={
                "path": str(path),
                "name": path.name,
                "stem": path.stem,
                "size": path.stat().st_size if path.exists() else 0,
            },
        )

        # Cache the result
        self._cache[path_str] = file_info
        self._cache_timestamps[path_str] = current_time

        return file_info

    def is_supported(self, path: Path) -> bool:
        """Check if a file type is supported by any plugin."""
        file_info = self.get_file_info(path)

        # Binary files are generally not supported
        if file_info.is_binary:
            return False

        # Files with known languages are supported
        if file_info.language:
            return True

        # Text files might be supported
        if file_info.mime_type and file_info.mime_type.startswith("text/"):
            return True

        return False

    def get_language(self, path: Path) -> Optional[str]:
        """Detect the programming language of a file."""
        file_info = self.get_file_info(path)
        return file_info.language

    def clear_cache(self) -> None:
        """Clear the file info cache."""
        self._cache.clear()
        self._cache_timestamps.clear()


class PluginRouter(IPluginRouter):
    """Advanced plugin router with capability matching, priority routing, and load balancing."""

    def __init__(self, file_matcher: Optional[IFileTypeMatcher] = None):
        """Initialize the plugin router.

        Args:
            file_matcher: File type matcher to use. If None, creates default FileTypeMatcher
        """
        self._file_matcher = file_matcher or FileTypeMatcher()
        self._plugins: List[IPlugin] = []
        self._plugin_capabilities: Dict[IPlugin, List[PluginCapability]] = {}
        self._language_plugins: Dict[str, List[IPlugin]] = defaultdict(list)
        self._extension_plugins: Dict[str, List[IPlugin]] = defaultdict(list)
        self._capability_plugins: Dict[str, List[IPlugin]] = defaultdict(list)

        # Load balancing and performance tracking
        self._plugin_usage_count: Dict[IPlugin, int] = defaultdict(int)
        self._plugin_performance: Dict[IPlugin, List[float]] = defaultdict(list)
        self._plugin_last_used: Dict[IPlugin, float] = {}

        # Configuration
        self._load_balance_enabled = True
        self._performance_tracking_enabled = True
        self._max_performance_samples = 100

    def register_plugin(
        self, plugin: IPlugin, capabilities: Optional[List[PluginCapability]] = None
    ) -> None:
        """Register a plugin with the router.

        Args:
            plugin: Plugin to register
            capabilities: List of capabilities the plugin provides
        """
        if plugin not in self._plugins:
            self._plugins.append(plugin)

            # Index by language
            if hasattr(plugin, "lang") and plugin.lang:
                self._language_plugins[plugin.lang].append(plugin)

            # Index by supported extensions
            for ext in self._get_plugin_extensions(plugin):
                self._extension_plugins[ext].append(plugin)

            # Register capabilities
            if capabilities:
                self._plugin_capabilities[plugin] = capabilities
                for cap in capabilities:
                    self._capability_plugins[cap.name].append(plugin)

    def unregister_plugin(self, plugin: IPlugin) -> None:
        """Unregister a plugin from the router.

        Args:
            plugin: Plugin to unregister
        """
        if plugin in self._plugins:
            self._plugins.remove(plugin)

            # Remove from language index
            if hasattr(plugin, "lang") and plugin.lang:
                if plugin in self._language_plugins[plugin.lang]:
                    self._language_plugins[plugin.lang].remove(plugin)

            # Remove from extension index
            for ext_list in self._extension_plugins.values():
                if plugin in ext_list:
                    ext_list.remove(plugin)

            # Remove from capability index
            if plugin in self._plugin_capabilities:
                capabilities = self._plugin_capabilities[plugin]
                for cap in capabilities:
                    if plugin in self._capability_plugins[cap.name]:
                        self._capability_plugins[cap.name].remove(plugin)
                del self._plugin_capabilities[plugin]

            # Clean up tracking data
            self._plugin_usage_count.pop(plugin, None)
            self._plugin_performance.pop(plugin, None)
            self._plugin_last_used.pop(plugin, None)

    def _get_plugin_extensions(self, plugin: IPlugin) -> Set[str]:
        """Get the file extensions supported by a plugin."""
        extensions = set()

        # Test common extensions to see what the plugin supports
        test_extensions = [
            ".py",
            ".js",
            ".ts",
            ".jsx",
            ".tsx",
            ".c",
            ".cpp",
            ".h",
            ".hpp",
            ".java",
            ".go",
            ".rs",
            ".rb",
            ".php",
            ".swift",
            ".dart",
            ".kt",
            ".html",
            ".css",
            ".scss",
            ".xml",
            ".json",
            ".yaml",
            ".md",
            ".sh",
            ".sql",
            ".lua",
            ".pl",
            ".r",
            ".scala",
            ".clj",
        ]

        for ext in test_extensions:
            test_path = Path(f"test{ext}")
            if plugin.supports(test_path):
                extensions.add(ext)

        return extensions

    def route_file(self, path: Path) -> List[RouteResult]:
        """Route a file to appropriate plugins."""
        results = []
        file_info = self._file_matcher.get_file_info(path)

        # Skip binary files
        if file_info.is_binary:
            logger.debug(f"Skipping binary file: {path}")
            return results

        # Find matching plugins
        candidate_plugins = set()

        # Match by extension
        if file_info.extension in self._extension_plugins:
            candidate_plugins.update(self._extension_plugins[file_info.extension])

        # Match by language
        if file_info.language and file_info.language in self._language_plugins:
            candidate_plugins.update(self._language_plugins[file_info.language])

        # Test all plugins if no specific matches found
        if not candidate_plugins:
            candidate_plugins = set(self._plugins)

        # Evaluate each candidate plugin
        for plugin in candidate_plugins:
            if plugin.supports(path):
                confidence, reasons = self._calculate_confidence(plugin, path, file_info)
                capabilities = self._plugin_capabilities.get(plugin, [])

                result = RouteResult(
                    plugin=plugin,
                    confidence=confidence,
                    match_reasons=reasons,
                    capabilities=capabilities,
                    metadata={
                        "file_info": file_info,
                        "usage_count": self._plugin_usage_count[plugin],
                        "avg_performance": self._get_avg_performance(plugin),
                    },
                )
                results.append(result)

        # Sort by confidence (descending) and apply load balancing
        results.sort(
            key=lambda r: (r.confidence, -self._plugin_usage_count[r.plugin]),
            reverse=True,
        )

        # Apply load balancing if enabled
        if self._load_balance_enabled and len(results) > 1:
            results = self._apply_load_balancing(results)

        return results

    def route_by_capability(self, capability: str, **kwargs) -> List[RouteResult]:
        """Route based on required capability."""
        results = []

        if capability in self._capability_plugins:
            plugins = self._capability_plugins[capability]

            for plugin in plugins:
                capabilities = self._plugin_capabilities.get(plugin, [])
                matching_caps = [cap for cap in capabilities if cap.name == capability]

                if matching_caps:
                    # Use capability priority as confidence
                    confidence = min(1.0, max(0.1, matching_caps[0].priority / 100.0))

                    result = RouteResult(
                        plugin=plugin,
                        confidence=confidence,
                        match_reasons=[f"Provides capability: {capability}"],
                        capabilities=matching_caps,
                        metadata={
                            "requested_capability": capability,
                            "usage_count": self._plugin_usage_count[plugin],
                            "avg_performance": self._get_avg_performance(plugin),
                        },
                    )
                    results.append(result)

        # Sort by confidence and capability priority
        results.sort(
            key=lambda r: (
                r.confidence,
                max((cap.priority for cap in r.capabilities), default=0),
            ),
            reverse=True,
        )

        return results

    def route_by_language(self, language: str) -> List[RouteResult]:
        """Route based on programming language."""
        results = []

        if language in self._language_plugins:
            plugins = self._language_plugins[language]

            for plugin in plugins:
                # High confidence for exact language match
                confidence = 0.9
                reasons = [f"Supports language: {language}"]

                # Boost confidence if plugin explicitly declares this language
                if hasattr(plugin, "lang") and plugin.lang == language:
                    confidence = 1.0
                    reasons.append("Primary language match")

                capabilities = self._plugin_capabilities.get(plugin, [])

                result = RouteResult(
                    plugin=plugin,
                    confidence=confidence,
                    match_reasons=reasons,
                    capabilities=capabilities,
                    metadata={
                        "requested_language": language,
                        "plugin_language": getattr(plugin, "lang", None),
                        "usage_count": self._plugin_usage_count[plugin],
                        "avg_performance": self._get_avg_performance(plugin),
                    },
                )
                results.append(result)

        # Sort by confidence
        results.sort(key=lambda r: r.confidence, reverse=True)

        return results

    def get_best_plugin(self, path: Path) -> Optional[RouteResult]:
        """Get the single best plugin for a file."""
        results = self.route_file(path)

        if results:
            best_result = results[0]

            # Update usage tracking
            self._plugin_usage_count[best_result.plugin] += 1
            self._plugin_last_used[best_result.plugin] = time.time()

            return best_result

        return None

    def _calculate_confidence(
        self, plugin: IPlugin, path: Path, file_info: FileTypeInfo
    ) -> Tuple[float, List[str]]:
        """Calculate confidence score and reasons for plugin match."""
        confidence = 0.0
        reasons = []

        # Base confidence for supporting the file
        confidence += 0.3
        reasons.append("Plugin supports file")

        # Language match
        if hasattr(plugin, "lang") and plugin.lang:
            if plugin.lang == file_info.language:
                confidence += 0.5
                reasons.append(f"Language match: {plugin.lang}")
            elif file_info.language and plugin.lang.lower() in file_info.language.lower():
                confidence += 0.3
                reasons.append(f"Partial language match: {plugin.lang}")

        # Extension match
        if file_info.extension:
            plugin_extensions = self._get_plugin_extensions(plugin)
            if file_info.extension in plugin_extensions:
                confidence += 0.2
                reasons.append(f"Extension match: {file_info.extension}")

        # Performance bonus (plugins with better average performance get slight boost)
        avg_perf = self._get_avg_performance(plugin)
        if avg_perf > 0:
            # Normalize performance (lower is better, so invert)
            perf_bonus = max(0, (2.0 - avg_perf) / 10.0)  # Small bonus
            confidence += perf_bonus
            if perf_bonus > 0:
                reasons.append(f"Performance bonus: {perf_bonus:.3f}")

        # Load balancing penalty for heavily used plugins
        if self._load_balance_enabled:
            usage_count = self._plugin_usage_count[plugin]
            if usage_count > 10:  # Only apply penalty after significant usage
                total_usage = sum(self._plugin_usage_count.values())
                if total_usage > 0:
                    usage_ratio = usage_count / total_usage
                    penalty = min(0.1, usage_ratio * 0.2)  # Max 10% penalty
                    confidence -= penalty
                    reasons.append(f"Load balancing penalty: {penalty:.3f}")

        # Ensure confidence is in valid range
        confidence = max(0.0, min(1.0, confidence))

        return confidence, reasons

    def _apply_load_balancing(self, results: List[RouteResult]) -> List[RouteResult]:
        """Apply load balancing to route results."""
        if len(results) <= 1:
            return results

        # Group results by confidence tier
        tiers = {}
        for result in results:
            tier = int(result.confidence * 10)  # 0-10 tiers
            if tier not in tiers:
                tiers[tier] = []
            tiers[tier].append(result)

        # Within each tier, prefer less-used plugins
        balanced_results = []
        for tier in sorted(tiers.keys(), reverse=True):
            tier_results = tiers[tier]
            tier_results.sort(key=lambda r: self._plugin_usage_count[r.plugin])
            balanced_results.extend(tier_results)

        return balanced_results

    def _get_avg_performance(self, plugin: IPlugin) -> float:
        """Get average performance time for a plugin."""
        if plugin in self._plugin_performance and self._plugin_performance[plugin]:
            performances = self._plugin_performance[plugin]
            return sum(performances) / len(performances)
        return 0.0

    def record_performance(self, plugin: IPlugin, execution_time: float) -> None:
        """Record performance data for a plugin.

        Args:
            plugin: Plugin that was executed
            execution_time: Time taken in seconds
        """
        if not self._performance_tracking_enabled:
            return

        performances = self._plugin_performance[plugin]
        performances.append(execution_time)

        # Keep only recent samples
        if len(performances) > self._max_performance_samples:
            performances.pop(0)

    def get_plugin_stats(self) -> Dict[str, Any]:
        """Get statistics about plugin usage and performance."""
        stats = {
            "total_plugins": len(self._plugins),
            "total_usage": sum(self._plugin_usage_count.values()),
            "language_coverage": dict(self._language_plugins),
            "extension_coverage": dict(self._extension_plugins),
            "capability_coverage": dict(self._capability_plugins),
            "plugin_usage": dict(self._plugin_usage_count),
            "plugin_performance": {
                plugin: self._get_avg_performance(plugin) for plugin in self._plugins
            },
        }

        return stats

    def configure(
        self,
        load_balance_enabled: bool = True,
        performance_tracking_enabled: bool = True,
        max_performance_samples: int = 100,
    ) -> None:
        """Configure router behavior.

        Args:
            load_balance_enabled: Enable load balancing
            performance_tracking_enabled: Enable performance tracking
            max_performance_samples: Maximum performance samples to keep per plugin
        """
        self._load_balance_enabled = load_balance_enabled
        self._performance_tracking_enabled = performance_tracking_enabled
        self._max_performance_samples = max_performance_samples
