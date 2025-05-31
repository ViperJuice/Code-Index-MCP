"""
Plugin System Interfaces

All interfaces related to the plugin system including plugin base interface,
plugin management, discovery, loading, and lifecycle management.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Set, Type, Callable
from dataclasses import dataclass
from .shared_interfaces import Result, PluginStatus, IObservable, Event

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
    dependencies: List[str]
    entry_point: str
    config_schema: Optional[Dict[str, Any]] = None

# ========================================
# Core Plugin Interface
# ========================================

class IPlugin(ABC):
    """Base interface that all language plugins must implement"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Get the plugin name"""
        pass
    
    @property
    @abstractmethod
    def supported_extensions(self) -> List[str]:
        """Get list of file extensions this plugin supports"""
        pass
    
    @property
    @abstractmethod
    def supported_languages(self) -> List[str]:
        """Get list of programming languages this plugin supports"""
        pass
    
    @abstractmethod
    def can_handle(self, file_path: str) -> bool:
        """Check if this plugin can handle the given file"""
        pass
    
    @abstractmethod
    def index(self, file_path: str, content: Optional[str] = None) -> Result[IndexedFile]:
        """Index a file and extract symbols"""
        pass
    
    @abstractmethod
    def get_definition(self, symbol: str, context: Dict[str, Any]) -> Result[Optional[SymbolDefinition]]:
        """Get the definition of a symbol"""
        pass
    
    @abstractmethod
    def get_references(self, symbol: str, context: Dict[str, Any]) -> Result[List[SymbolReference]]:
        """Get all references to a symbol"""
        pass
    
    @abstractmethod
    def search(self, query: str, options: Dict[str, Any]) -> Result[List[SearchResult]]:
        """Search for code patterns"""
        pass
    
    @abstractmethod
    def validate_syntax(self, content: str) -> Result[bool]:
        """Validate syntax of code content"""
        pass
    
    @abstractmethod
    def get_completions(self, file_path: str, line: int, column: int) -> Result[List[str]]:
        """Get code completions at a position"""
        pass

class ILanguageAnalyzer(ABC):
    """Interface for language-specific analysis capabilities"""
    
    @abstractmethod
    def parse_imports(self, content: str) -> Result[List[str]]:
        """Parse import statements from content"""
        pass
    
    @abstractmethod
    def extract_symbols(self, content: str) -> Result[List[SymbolDefinition]]:
        """Extract all symbols from content"""
        pass
    
    @abstractmethod
    def resolve_type(self, symbol: str, context: Dict[str, Any]) -> Result[Optional[str]]:
        """Resolve the type of a symbol"""
        pass
    
    @abstractmethod
    def get_call_hierarchy(self, symbol: str, context: Dict[str, Any]) -> Result[Dict[str, List[str]]]:
        """Get call hierarchy for a symbol"""
        pass

# ========================================
# Plugin Management Interfaces
# ========================================

class IPluginRegistry(ABC):
    """Interface for plugin registry operations"""
    
    @abstractmethod
    def register(self, plugin: IPlugin, metadata: PluginMetadata) -> Result[None]:
        """Register a plugin"""
        pass
    
    @abstractmethod
    def unregister(self, plugin_name: str) -> Result[None]:
        """Unregister a plugin"""
        pass
    
    @abstractmethod
    def get_plugin(self, plugin_name: str) -> Optional[IPlugin]:
        """Get a plugin by name"""
        pass
    
    @abstractmethod
    def get_plugins_for_extension(self, extension: str) -> List[IPlugin]:
        """Get all plugins that support a file extension"""
        pass
    
    @abstractmethod
    def get_plugins_for_language(self, language: str) -> List[IPlugin]:
        """Get all plugins that support a language"""
        pass
    
    @abstractmethod
    def list_plugins(self) -> List[str]:
        """List all registered plugin names"""
        pass
    
    @abstractmethod
    def get_metadata(self, plugin_name: str) -> Optional[PluginMetadata]:
        """Get metadata for a plugin"""
        pass

class IPluginDiscovery(ABC):
    """Interface for discovering available plugins"""
    
    @abstractmethod
    def discover_plugins(self, search_paths: List[str]) -> Result[List[PluginMetadata]]:
        """Discover plugins in the given search paths"""
        pass
    
    @abstractmethod
    def scan_directory(self, directory: str) -> Result[List[PluginMetadata]]:
        """Scan a directory for plugins"""
        pass
    
    @abstractmethod
    def validate_plugin(self, plugin_path: str) -> Result[PluginMetadata]:
        """Validate a plugin and extract its metadata"""
        pass

class IPluginLoader(ABC):
    """Interface for loading and unloading plugins"""
    
    @abstractmethod
    def load_plugin(self, plugin_path: str, metadata: PluginMetadata) -> Result[IPlugin]:
        """Load a plugin from the given path"""
        pass
    
    @abstractmethod
    def unload_plugin(self, plugin_name: str) -> Result[None]:
        """Unload a plugin"""
        pass
    
    @abstractmethod
    def reload_plugin(self, plugin_name: str) -> Result[IPlugin]:
        """Reload a plugin"""
        pass
    
    @abstractmethod
    def is_loaded(self, plugin_name: str) -> bool:
        """Check if a plugin is loaded"""
        pass
    
    @abstractmethod
    def get_load_errors(self, plugin_name: str) -> List[str]:
        """Get any load errors for a plugin"""
        pass

class IPluginManager(IObservable):
    """Interface for overall plugin management"""
    
    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> Result[None]:
        """Initialize the plugin manager"""
        pass
    
    @abstractmethod
    def shutdown(self) -> Result[None]:
        """Shutdown the plugin manager"""
        pass
    
    @abstractmethod
    def load_all_plugins(self, plugin_directories: List[str]) -> Result[List[str]]:
        """Load all plugins from directories"""
        pass
    
    @abstractmethod
    def enable_plugin(self, plugin_name: str) -> Result[None]:
        """Enable a plugin"""
        pass
    
    @abstractmethod
    def disable_plugin(self, plugin_name: str) -> Result[None]:
        """Disable a plugin"""
        pass
    
    @abstractmethod
    def get_plugin_status(self, plugin_name: str) -> PluginStatus:
        """Get the status of a plugin"""
        pass
    
    @abstractmethod
    def get_all_plugin_statuses(self) -> Dict[str, PluginStatus]:
        """Get the status of all plugins"""
        pass
    
    @abstractmethod
    def execute_on_plugin(self, plugin_name: str, operation: Callable[[IPlugin], Any]) -> Result[Any]:
        """Execute an operation on a specific plugin"""
        pass
    
    @abstractmethod
    def execute_on_all_plugins(self, operation: Callable[[IPlugin], Any]) -> Dict[str, Result[Any]]:
        """Execute an operation on all plugins"""
        pass

# ========================================
# Tree-sitter Integration Interfaces
# ========================================

class ITreeSitterAdapter(ABC):
    """Interface for Tree-sitter parser integration"""
    
    @abstractmethod
    def parse_content(self, content: str, language: str) -> Result[Any]:
        """Parse content using Tree-sitter"""
        pass
    
    @abstractmethod
    def get_node_text(self, node: Any, content: str) -> str:
        """Get text content of a node"""
        pass
    
    @abstractmethod
    def find_nodes_by_type(self, tree: Any, node_type: str) -> List[Any]:
        """Find all nodes of a specific type"""
        pass
    
    @abstractmethod
    def get_node_position(self, node: Any) -> tuple[int, int]:
        """Get line and column position of a node"""
        pass
    
    @abstractmethod
    def is_language_supported(self, language: str) -> bool:
        """Check if a language is supported"""
        pass

# ========================================
# Language-Specific Plugin Interfaces
# ========================================

class IPythonPlugin(IPlugin):
    """Interface specific to Python plugins"""
    
    @abstractmethod
    def get_import_graph(self, file_path: str) -> Result[Dict[str, List[str]]]:
        """Get import dependency graph"""
        pass
    
    @abstractmethod
    def resolve_module(self, module_name: str, context: Dict[str, Any]) -> Result[Optional[str]]:
        """Resolve a module to its file path"""
        pass

class ICppPlugin(IPlugin):
    """Interface specific to C++ plugins"""
    
    @abstractmethod
    def resolve_includes(self, file_path: str) -> Result[List[str]]:
        """Resolve #include directives"""
        pass
    
    @abstractmethod
    def parse_templates(self, content: str) -> Result[List[SymbolDefinition]]:
        """Parse template definitions"""
        pass

class IJavaScriptPlugin(IPlugin):
    """Interface specific to JavaScript/TypeScript plugins"""
    
    @abstractmethod
    def parse_jsx(self, content: str) -> Result[List[SymbolDefinition]]:
        """Parse JSX components"""
        pass
    
    @abstractmethod
    def resolve_modules(self, file_path: str) -> Result[Dict[str, str]]:
        """Resolve module imports"""
        pass

class IDartPlugin(IPlugin):
    """Interface specific to Dart plugins"""
    
    @abstractmethod
    def parse_flutter_widgets(self, content: str) -> Result[List[SymbolDefinition]]:
        """Parse Flutter widget definitions"""
        pass
    
    @abstractmethod
    def resolve_packages(self, file_path: str) -> Result[List[str]]:
        """Resolve package dependencies"""
        pass

class IHtmlCssPlugin(IPlugin):
    """Interface specific to HTML/CSS plugins"""
    
    @abstractmethod
    def extract_selectors(self, css_content: str) -> Result[List[str]]:
        """Extract CSS selectors"""
        pass
    
    @abstractmethod
    def find_css_usage(self, html_content: str) -> Result[List[str]]:
        """Find CSS class/ID usage in HTML"""
        pass

class ICPlugin(IPlugin):
    """Interface specific to C plugins"""
    
    @abstractmethod
    def parse_preprocessor(self, content: str) -> Result[List[str]]:
        """Parse preprocessor directives"""
        pass
    
    @abstractmethod
    def resolve_headers(self, file_path: str) -> Result[List[str]]:
        """Resolve header file dependencies"""
        pass