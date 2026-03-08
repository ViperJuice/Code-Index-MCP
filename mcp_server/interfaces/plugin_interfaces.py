"""
Plugin System Interfaces

All interfaces related to the plugin system including plugin base interface,
plugin management, discovery, loading, and lifecycle management.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .shared_interfaces import IObservable, PluginStatus, Result

# ========================================
# Plugin Data Types
# ========================================


@dataclass
class SymbolDefinition:
    """Symbol definition information"""

    symbol: str
    file_path: str
    line: int
    column: int
    symbol_type: str  # function, class, variable, etc.
    signature: Optional[str] = None
    docstring: Optional[str] = None
    scope: Optional[str] = None


@dataclass
class SymbolReference:
    """Symbol reference information"""

    symbol: str
    file_path: str
    line: int
    column: int
    context: Optional[str] = None


@dataclass
class SearchResult:
    """Search result information"""

    file_path: str
    line: int
    column: int
    snippet: str
    match_type: str  # exact, fuzzy, semantic
    score: float
    context: Optional[str] = None


@dataclass
class IndexedFile:
    """Information about an indexed file"""

    file_path: str
    last_modified: float
    size: int
    symbols: List[SymbolDefinition]
    language: str
    encoding: str = "utf-8"


@dataclass
class PluginMetadata:
    """Plugin metadata information"""

    name: str
    version: str
    description: str
    author: str
    supported_extensions: List[str]
    supported_languages: List[str]
    dependencies: List[str] = field(default_factory=list)
    entry_point: str = "plugin.py"
    config_schema: Optional[Dict[str, Any]] = None


@dataclass
class PluginRuntimeInfo:
    """Stable runtime status shared across plugin managers and status endpoints."""

    name: str
    status: PluginStatus
    enabled: bool
    version: Optional[str] = None
    language: Optional[str] = None
    error: Optional[str] = None


# ========================================
# Core Plugin Interface
# ========================================


class IPlugin(ABC):
    """Base interface that all language plugins must implement"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Get the plugin name"""

    @property
    @abstractmethod
    def supported_extensions(self) -> List[str]:
        """Get list of file extensions this plugin supports"""

    @property
    @abstractmethod
    def supported_languages(self) -> List[str]:
        """Get list of programming languages this plugin supports"""

    @abstractmethod
    def can_handle(self, file_path: str) -> bool:
        """Check if this plugin can handle the given file"""

    @abstractmethod
    def index(
        self, file_path: str, content: Optional[str] = None
    ) -> Result[IndexedFile]:
        """Index a file and extract symbols"""

    @abstractmethod
    def get_definition(
        self, symbol: str, context: Dict[str, Any]
    ) -> Result[Optional[SymbolDefinition]]:
        """Get the definition of a symbol"""

    @abstractmethod
    def get_references(
        self, symbol: str, context: Dict[str, Any]
    ) -> Result[List[SymbolReference]]:
        """Get all references to a symbol"""

    @abstractmethod
    def search(self, query: str, options: Dict[str, Any]) -> Result[List[SearchResult]]:
        """Search for code patterns"""

    @abstractmethod
    def validate_syntax(self, content: str) -> Result[bool]:
        """Validate syntax of code content"""

    @abstractmethod
    def get_completions(
        self, file_path: str, line: int, column: int
    ) -> Result[List[str]]:
        """Get code completions at a position"""


class ILanguageAnalyzer(ABC):
    """Interface for language-specific analysis capabilities"""

    @abstractmethod
    def parse_imports(self, content: str) -> Result[List[str]]:
        """Parse import statements from content"""

    @abstractmethod
    def extract_symbols(self, content: str) -> Result[List[SymbolDefinition]]:
        """Extract all symbols from content"""

    @abstractmethod
    def resolve_type(
        self, symbol: str, context: Dict[str, Any]
    ) -> Result[Optional[str]]:
        """Resolve the type of a symbol"""

    @abstractmethod
    def get_call_hierarchy(
        self, symbol: str, context: Dict[str, Any]
    ) -> Result[Dict[str, List[str]]]:
        """Get call hierarchy for a symbol"""


# ========================================
# Plugin Management Interfaces
# ========================================


class IPluginRegistry(ABC):
    """Interface for plugin registry operations"""

    @abstractmethod
    def register(self, plugin: IPlugin, metadata: PluginMetadata) -> Result[None]:
        """Register a plugin"""

    @abstractmethod
    def unregister(self, plugin_name: str) -> Result[None]:
        """Unregister a plugin"""

    @abstractmethod
    def get_plugin(self, plugin_name: str) -> Optional[IPlugin]:
        """Get a plugin by name"""

    @abstractmethod
    def get_plugins_for_extension(self, extension: str) -> List[IPlugin]:
        """Get all plugins that support a file extension"""

    @abstractmethod
    def get_plugins_for_language(self, language: str) -> List[IPlugin]:
        """Get all plugins that support a language"""

    @abstractmethod
    def list_plugins(self) -> List[str]:
        """List all registered plugin names"""

    @abstractmethod
    def get_metadata(self, plugin_name: str) -> Optional[PluginMetadata]:
        """Get metadata for a plugin"""


class IPluginDiscovery(ABC):
    """Interface for discovering available plugins"""

    @abstractmethod
    def discover_plugins(
        self, search_paths: List[str | Path]
    ) -> Result[List[PluginMetadata]]:
        """Discover plugins in the given search paths"""

    @abstractmethod
    def scan_directory(self, directory: str | Path) -> Result[List[PluginMetadata]]:
        """Scan a directory for plugins"""

    @abstractmethod
    def validate_plugin(self, plugin_path: str | Path) -> Result[bool]:
        """Validate a plugin path before loading it"""


class IPluginLoader(ABC):
    """Interface for loading and unloading plugins"""

    @abstractmethod
    def load_plugin(
        self, plugin_path: str | Path, metadata: PluginMetadata
    ) -> Result[type[IPlugin]]:
        """Load a plugin class from the given path"""

    @abstractmethod
    def unload_plugin(self, plugin_name: str) -> Result[None]:
        """Unload a plugin"""

    @abstractmethod
    def reload_plugin(self, plugin_name: str) -> Result[None]:
        """Reload a plugin"""

    @abstractmethod
    def is_loaded(self, plugin_name: str) -> bool:
        """Check if a plugin is loaded"""

    @abstractmethod
    def get_load_errors(self, plugin_name: str) -> List[str]:
        """Get any load errors for a plugin"""


class IPluginManager(IObservable):
    """Interface for overall plugin management"""

    @abstractmethod
    def load_plugins(
        self, config_path: Optional[str | Path] = None
    ) -> Result[List[str]]:
        """Discover, load, and optionally initialize configured plugins."""

    @abstractmethod
    def shutdown(self) -> Result[None]:
        """Shutdown the plugin manager and destroy active instances."""

    @abstractmethod
    def reload_plugin(self, plugin_name: str) -> Result[None]:
        """Reload a specific plugin."""

    @abstractmethod
    def enable_plugin(self, plugin_name: str) -> Result[None]:
        """Enable and initialize a plugin if configured."""

    @abstractmethod
    def disable_plugin(self, plugin_name: str) -> Result[None]:
        """Disable a plugin and stop any active instance."""

    @abstractmethod
    def get_plugin_by_language(self, language: str) -> Optional[IPlugin]:
        """Return an active plugin instance for a language."""

    @abstractmethod
    def get_plugin_for_file(self, file_path: str | Path) -> Optional[IPlugin]:
        """Return the best active plugin instance for a file path."""

    @abstractmethod
    def get_plugin_status(self) -> Dict[str, PluginRuntimeInfo]:
        """Return runtime status for all known plugins."""

    @abstractmethod
    def get_detailed_plugin_status(self) -> Dict[str, Dict[str, Any]]:
        """Return expanded runtime and configuration details for plugins."""


# ========================================
# Tree-sitter Integration Interfaces
# ========================================


class ITreeSitterAdapter(ABC):
    """Interface for Tree-sitter parser integration"""

    @abstractmethod
    def parse_content(self, content: str, language: str) -> Result[Any]:
        """Parse content using Tree-sitter"""

    @abstractmethod
    def get_node_text(self, node: Any, content: str) -> str:
        """Get text content of a node"""

    @abstractmethod
    def find_nodes_by_type(self, tree: Any, node_type: str) -> List[Any]:
        """Find all nodes of a specific type"""

    @abstractmethod
    def get_node_position(self, node: Any) -> tuple[int, int]:
        """Get line and column position of a node"""

    @abstractmethod
    def is_language_supported(self, language: str) -> bool:
        """Check if a language is supported"""


# ========================================
# Language-Specific Plugin Interfaces
# ========================================


class IPythonPlugin(IPlugin):
    """Interface specific to Python plugins"""

    @abstractmethod
    def get_import_graph(self, file_path: str) -> Result[Dict[str, List[str]]]:
        """Get import dependency graph"""

    @abstractmethod
    def resolve_module(
        self, module_name: str, context: Dict[str, Any]
    ) -> Result[Optional[str]]:
        """Resolve a module to its file path"""


class ICppPlugin(IPlugin):
    """Interface specific to C++ plugins"""

    @abstractmethod
    def resolve_includes(self, file_path: str) -> Result[List[str]]:
        """Resolve #include directives"""

    @abstractmethod
    def parse_templates(self, content: str) -> Result[List[SymbolDefinition]]:
        """Parse template definitions"""


class IJavaScriptPlugin(IPlugin):
    """Interface specific to JavaScript/TypeScript plugins"""

    @abstractmethod
    def parse_jsx(self, content: str) -> Result[List[SymbolDefinition]]:
        """Parse JSX components"""

    @abstractmethod
    def resolve_modules(self, file_path: str) -> Result[Dict[str, str]]:
        """Resolve module imports"""


class IDartPlugin(IPlugin):
    """Interface specific to Dart plugins"""

    @abstractmethod
    def parse_flutter_widgets(self, content: str) -> Result[List[SymbolDefinition]]:
        """Parse Flutter widget definitions"""

    @abstractmethod
    def resolve_packages(self, file_path: str) -> Result[List[str]]:
        """Resolve package dependencies"""


class IHtmlCssPlugin(IPlugin):
    """Interface specific to HTML/CSS plugins"""

    @abstractmethod
    def extract_selectors(self, css_content: str) -> Result[List[str]]:
        """Extract CSS selectors"""

    @abstractmethod
    def find_css_usage(self, html_content: str) -> Result[List[str]]:
        """Find CSS class/ID usage in HTML"""


class ICPlugin(IPlugin):
    """Interface specific to C plugins"""

    @abstractmethod
    def parse_preprocessor(self, content: str) -> Result[List[str]]:
        """Parse preprocessor directives"""

    @abstractmethod
    def resolve_headers(self, file_path: str) -> Result[List[str]]:
        """Resolve header file dependencies"""
