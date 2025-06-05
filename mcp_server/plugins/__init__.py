"""Plugin system for MCP server.

This package provides a comprehensive plugin template system for creating
language-specific plugins with support for Tree-sitter parsing, regex-based
fallback, and hybrid approaches.
"""

from .plugin_template import (
    LanguagePluginBase,
    ParsedSymbol,
    SymbolType,
    PluginConfig,
    PluginError,
    ParsingError
)

from .tree_sitter_plugin_base import (
    TreeSitterPluginBase,
    AdvancedTreeSitterPlugin
)

from .regex_plugin_base import (
    RegexPluginBase,
    RegexPattern,
    SimpleRegexPlugin
)

from .hybrid_plugin_base import HybridPluginBase

from .plugin_utils import (
    CacheStrategy,
    PluginMetrics,
    PluginCache,
    timing_decorator,
    error_handler,
    cached_method,
    SymbolExtractor,
    FileAnalyzer,
    AsyncPluginHelper,
    PluginValidator,
    create_cache_key,
    safe_file_read,
    normalize_symbol_name,
    get_file_language_from_extension
)

from .plugin_generator import (
    PluginGenerator,
    PluginSpec,
    PluginType,
    create_plugin_from_cli
)

__all__ = [
    # Core template classes
    'LanguagePluginBase',
    'ParsedSymbol',
    'SymbolType',
    'PluginConfig',
    'PluginError',
    'ParsingError',
    
    # Specialized base classes
    'TreeSitterPluginBase',
    'AdvancedTreeSitterPlugin',
    'RegexPluginBase',
    'RegexPattern',
    'SimpleRegexPlugin',
    'HybridPluginBase',
    
    # Utilities
    'CacheStrategy',
    'PluginMetrics',
    'PluginCache',
    'timing_decorator',
    'error_handler',
    'cached_method',
    'SymbolExtractor',
    'FileAnalyzer',
    'AsyncPluginHelper',
    'PluginValidator',
    'create_cache_key',
    'safe_file_read',
    'normalize_symbol_name',
    'get_file_language_from_extension',
    
    # Plugin generator
    'PluginGenerator',
    'PluginSpec',
    'PluginType',
    'create_plugin_from_cli'
]