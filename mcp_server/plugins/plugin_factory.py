"""Factory for creating language plugins.

This factory supports creating plugins for various programming languages and document formats,
including specialized plugins for:
- Programming languages: Python, JavaScript, TypeScript, C, C++, Java, Go, Rust, etc.
- Document formats: Markdown (.md, .markdown), Plain Text (.txt, .text, .log)
- Web technologies: HTML, CSS, Dart
- Other languages: Swift, Kotlin, C#

The factory will use specialized plugins when available, falling back to generic
tree-sitter based plugins for languages without specific implementations.
"""

import logging
from pathlib import Path
from typing import Callable, Dict, Optional, Type, Union

from ..storage.sqlite_store import SQLiteStore
from .generic_treesitter_plugin import GenericTreeSitterPlugin
from .language_registry import LANGUAGE_CONFIGS, get_language_by_extension

logger = logging.getLogger(__name__)

# Import specific plugins if they exist
# Can be either a plugin class or a factory function
SPECIFIC_PLUGINS: Dict[str, Union[Type, Callable]] = {}

try:
    from .python_plugin import Plugin as PythonPlugin

    SPECIFIC_PLUGINS["python"] = PythonPlugin
except ImportError:
    logger.info("Python plugin not available, will use generic")

try:
    from .js_plugin import Plugin as JsPlugin

    SPECIFIC_PLUGINS["javascript"] = JsPlugin
except ImportError:
    logger.info("JavaScript plugin not available, will use generic")

try:
    from .typescript_plugin import Plugin as TypeScriptPlugin

    SPECIFIC_PLUGINS["typescript"] = TypeScriptPlugin
except ImportError:
    logger.info("TypeScript plugin not available, will use generic")

try:
    from .c_plugin import Plugin as CPlugin

    SPECIFIC_PLUGINS["c"] = CPlugin
except ImportError:
    logger.info("C plugin not available, will use generic")

try:
    from .cpp_plugin import Plugin as CppPlugin

    SPECIFIC_PLUGINS["cpp"] = CppPlugin
except ImportError:
    logger.info("C++ plugin not available, will use generic")

try:
    from .dart_plugin import Plugin as DartPlugin

    SPECIFIC_PLUGINS["dart"] = DartPlugin
except ImportError:
    logger.info("Dart plugin not available, will use generic")

try:
    from .html_css_plugin import Plugin as HtmlCssPlugin

    SPECIFIC_PLUGINS["html"] = HtmlCssPlugin
    SPECIFIC_PLUGINS["css"] = HtmlCssPlugin
except ImportError:
    logger.info("HTML/CSS plugin not available, will use generic")

# Specialized plugins for advanced language support
try:
    from .java_plugin import Plugin as JavaPlugin

    SPECIFIC_PLUGINS["java"] = JavaPlugin
except ImportError:
    logger.info("Java plugin not available, will use generic")

try:
    from .go_plugin import Plugin as GoPlugin

    SPECIFIC_PLUGINS["go"] = GoPlugin
except ImportError:
    logger.info("Go plugin not available, will use generic")

try:
    from .rust_plugin import Plugin as RustPlugin

    SPECIFIC_PLUGINS["rust"] = RustPlugin
except ImportError:
    logger.info("Rust plugin not available, will use generic")

try:
    from .csharp_plugin import Plugin as CSharpPlugin

    SPECIFIC_PLUGINS["c_sharp"] = CSharpPlugin
    SPECIFIC_PLUGINS["csharp"] = CSharpPlugin
except ImportError:
    logger.info("C# plugin not available, will use generic")

try:
    from .swift_plugin import Plugin as SwiftPlugin

    SPECIFIC_PLUGINS["swift"] = SwiftPlugin
except ImportError:
    logger.info("Swift plugin not available, will use generic")

try:
    from .kotlin_plugin import Plugin as KotlinPlugin

    SPECIFIC_PLUGINS["kotlin"] = KotlinPlugin
except ImportError:
    logger.info("Kotlin plugin not available, will use generic")

try:
    # Try simple text plugin first for config files
    from .simple_text_plugin import SimpleTextPlugin

    # Create a wrapper that provides the correct initialization
    def create_plaintext_plugin(sqlite_store=None, enable_semantic=True):
        return SimpleTextPlugin(sqlite_store)

    SPECIFIC_PLUGINS["plaintext"] = create_plaintext_plugin
except ImportError:
    logger.info("Plain text plugin not available, will use generic")

try:
    from .markdown_plugin import MarkdownPlugin

    SPECIFIC_PLUGINS["markdown"] = MarkdownPlugin
except ImportError:
    logger.info("Markdown plugin not available, will use generic")


class PluginFactory:
    """Factory for creating language plugins."""

    @classmethod
    def create_plugin(
        cls,
        language: str,
        sqlite_store: Optional[SQLiteStore] = None,
        enable_semantic: bool = True,
    ):
        """Create appropriate plugin for the language.

        Args:
            language: Language code (e.g., 'python', 'go', 'rust')
            sqlite_store: Optional SQLite storage
            enable_semantic: Whether to enable semantic search

        Returns:
            Plugin instance

        Raises:
            ValueError: If language is not supported
        """
        # Normalize language name
        language = language.lower().replace("-", "_")

        # Check for language-specific implementation first
        if language in SPECIFIC_PLUGINS:
            logger.info(f"Using specific plugin for {language}")
            plugin_class_or_factory = SPECIFIC_PLUGINS[language]
            # Check if it's a callable (factory function) or a class
            if callable(plugin_class_or_factory) and not isinstance(plugin_class_or_factory, type):
                # It's a factory function
                return plugin_class_or_factory(
                    sqlite_store=sqlite_store, enable_semantic=enable_semantic
                )
            else:
                # It's a class
                return plugin_class_or_factory(sqlite_store=sqlite_store)

        # Check if language is supported by generic plugin
        if language in LANGUAGE_CONFIGS:
            logger.info(f"Using generic plugin for {language}")
            config = LANGUAGE_CONFIGS[language]
            return GenericTreeSitterPlugin(config, sqlite_store, enable_semantic)

        # Language not supported
        supported = sorted(list(SPECIFIC_PLUGINS.keys()) + list(LANGUAGE_CONFIGS.keys()))
        raise ValueError(
            f"Unsupported language: {language}. " f"Supported languages: {', '.join(supported)}"
        )

    @classmethod
    def get_plugin(
        cls,
        language: str,
        sqlite_store: Optional[SQLiteStore] = None,
        enable_semantic: bool = True,
    ):
        """Alias for create_plugin for backward compatibility.

        Args:
            language: Language code (e.g., 'python', 'go', 'rust')
            sqlite_store: Optional SQLite storage
            enable_semantic: Whether to enable semantic search

        Returns:
            Plugin instance
        """
        return cls.create_plugin(language, sqlite_store, enable_semantic)

    @classmethod
    def create_plugin_for_file(
        cls,
        file_path: str | Path,
        sqlite_store: Optional[SQLiteStore] = None,
        enable_semantic: bool = True,
    ):
        """Create appropriate plugin based on file extension.

        Args:
            file_path: Path to the file
            sqlite_store: Optional SQLite storage
            enable_semantic: Whether to enable semantic search

        Returns:
            Plugin instance or None if no suitable plugin found
        """
        path = Path(file_path)
        extension = path.suffix.lower()

        # Get language from extension
        language = get_language_by_extension(extension)
        if language:
            return cls.create_plugin(language, sqlite_store, enable_semantic)

        logger.warning(f"No plugin found for extension: {extension}")
        return None

    @classmethod
    def get_supported_languages(cls) -> list[str]:
        """Get list of all supported languages."""
        # Combine specific and generic plugin languages
        all_languages = set(SPECIFIC_PLUGINS.keys())
        all_languages.update(LANGUAGE_CONFIGS.keys())
        return sorted(list(all_languages))

    @classmethod
    def get_language_info(cls, language: str) -> dict:
        """Get information about a language.

        Returns:
            Dictionary with language info or empty dict if not found
        """
        language = language.lower().replace("-", "_")

        if language in LANGUAGE_CONFIGS:
            config = LANGUAGE_CONFIGS[language].copy()
            config["has_specific_plugin"] = language in SPECIFIC_PLUGINS
            return config

        return {}

    @classmethod
    def create_all_plugins(
        cls, sqlite_store: Optional[SQLiteStore] = None, enable_semantic: bool = True
    ) -> Dict[str, object]:
        """Create plugins for all supported languages.

        Returns:
            Dictionary mapping language code to plugin instance
        """
        plugins = {}

        for language in cls.get_supported_languages():
            try:
                plugin = cls.create_plugin(language, sqlite_store, enable_semantic)
                plugins[language] = plugin
                logger.info(f"Created plugin for {language}")
            except Exception as e:
                logger.error(f"Failed to create plugin for {language}: {e}")

        return plugins
