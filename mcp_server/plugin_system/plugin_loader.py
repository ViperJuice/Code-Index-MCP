"""Plugin loader implementation."""

import importlib
import importlib.util
import logging
import sys
from datetime import datetime
from typing import Any, Dict, Type

from ..interfaces.shared_interfaces import Error, Result
from ..plugin_base import IPlugin
from .interfaces import IPluginLoader
from .models import PluginInfo, PluginLoadError

logger = logging.getLogger(__name__)


class PluginLoader(IPluginLoader):
    """Dynamically loads plugin modules."""

    def __init__(self):
        self._loaded_modules: Dict[str, Any] = {}

    def load_plugin(self, plugin_info: PluginInfo) -> Type[IPlugin]:
        """Load a plugin class from the given plugin information."""
        try:
            # Check if already loaded
            if plugin_info.name in self._loaded_modules:
                module = self._loaded_modules[plugin_info.name]
                return self._get_plugin_class(module, plugin_info)

            # Try to load the module
            module = self._load_module(plugin_info)

            # Cache the loaded module
            self._loaded_modules[plugin_info.name] = module

            # Get the plugin class
            plugin_class = self._get_plugin_class(module, plugin_info)

            # Validate the plugin class
            if not self._validate_plugin_class(plugin_class):
                raise PluginLoadError(
                    f"Plugin {plugin_info.name} does not implement IPlugin interface correctly"
                )

            logger.info(f"Successfully loaded plugin: {plugin_info.name}")
            return plugin_class

        except Exception as e:
            logger.error(f"Failed to load plugin {plugin_info.name}: {e}")
            raise PluginLoadError(f"Failed to load plugin {plugin_info.name}: {str(e)}") from e

    def load_plugin_safe(self, plugin_info: PluginInfo) -> Result[Type[IPlugin]]:
        """Load a plugin class using Result pattern for error handling."""
        try:
            plugin_class = self.load_plugin(plugin_info)
            return Result.success_result(
                plugin_class,
                metadata={
                    "plugin_name": plugin_info.name,
                    "plugin_version": plugin_info.version,
                    "loaded_at": datetime.now().isoformat(),
                },
            )
        except Exception as e:
            error = Error(
                code="PLUGIN_LOAD_ERROR",
                message=f"Failed to load plugin {plugin_info.name}",
                details={
                    "plugin_name": plugin_info.name,
                    "plugin_path": str(plugin_info.path),
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                timestamp=datetime.now(),
            )
            return Result.error_result(error)

    def unload_plugin(self, plugin_name: str) -> None:
        """Unload a plugin module."""
        if plugin_name in self._loaded_modules:
            module = self._loaded_modules[plugin_name]
            module_name = module.__name__

            # Remove from cache
            del self._loaded_modules[plugin_name]

            # Remove from sys.modules
            if module_name in sys.modules:
                del sys.modules[module_name]

            # Also remove any submodules
            to_remove = [name for name in sys.modules if name.startswith(f"{module_name}.")]
            for name in to_remove:
                del sys.modules[name]

            logger.info(f"Unloaded plugin: {plugin_name}")

    def unload_plugin_safe(self, plugin_name: str) -> Result[None]:
        """Unload a plugin module using Result pattern for error handling."""
        try:
            self.unload_plugin(plugin_name)
            return Result.success_result(
                None,
                metadata={
                    "plugin_name": plugin_name,
                    "unloaded_at": datetime.now().isoformat(),
                },
            )
        except Exception as e:
            error = Error(
                code="PLUGIN_UNLOAD_ERROR",
                message=f"Failed to unload plugin {plugin_name}",
                details={
                    "plugin_name": plugin_name,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                timestamp=datetime.now(),
            )
            return Result.error_result(error)

    def _load_module(self, plugin_info: PluginInfo) -> Any:
        """Load a module from plugin info."""
        # First try standard import for built-in plugins
        if plugin_info.module_name.startswith("mcp_server.plugins."):
            try:
                # Try to import the plugin module directly
                module_name = f"{plugin_info.module_name}.plugin"
                module = importlib.import_module(module_name)
                return module
            except ImportError:
                # Fallback to package import
                try:
                    module = importlib.import_module(plugin_info.module_name)
                    # Check if it has a plugin submodule
                    if hasattr(module, "plugin"):
                        return getattr(module, "plugin")
                    return module
                except ImportError as e:
                    logger.debug(f"Standard import failed for {plugin_info.module_name}: {e}")

        # Try loading from file path
        module_path = plugin_info.path / "plugin.py"
        if not module_path.exists():
            module_path = plugin_info.path / "__init__.py"

        if not module_path.exists():
            raise PluginLoadError(f"Plugin module not found at {plugin_info.path}")

        # Load module from file
        spec = importlib.util.spec_from_file_location(plugin_info.module_name, module_path)
        if spec is None or spec.loader is None:
            raise PluginLoadError(f"Failed to create module spec for {module_path}")

        module = importlib.util.module_from_spec(spec)

        # Add to sys.modules before executing
        sys.modules[plugin_info.module_name] = module

        try:
            spec.loader.exec_module(module)
        except Exception as e:
            # Remove from sys.modules on failure
            if plugin_info.module_name in sys.modules:
                del sys.modules[plugin_info.module_name]
            raise PluginLoadError(
                f"Failed to execute module {plugin_info.module_name}: {str(e)}"
            ) from e

        return module

    def _get_plugin_class(self, module: Any, plugin_info: PluginInfo) -> Type[IPlugin]:
        """Extract the plugin class from a module."""
        # Try to get the class by name
        if hasattr(module, plugin_info.class_name):
            plugin_class = getattr(module, plugin_info.class_name)
            if isinstance(plugin_class, type) and issubclass(plugin_class, IPlugin):
                return plugin_class

        # Look for any class that implements IPlugin
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and issubclass(attr, IPlugin) and attr is not IPlugin:
                return attr

        raise PluginLoadError(f"No IPlugin implementation found in {plugin_info.module_name}")

    def _validate_plugin_class(self, plugin_class: Type[IPlugin]) -> bool:
        """Validate that a plugin class properly implements IPlugin."""
        required_methods = [
            "supports",
            "indexFile",
            "getDefinition",
            "findReferences",
            "search",
        ]

        for method_name in required_methods:
            if not hasattr(plugin_class, method_name):
                logger.error(f"Plugin class missing required method: {method_name}")
                return False

            method = getattr(plugin_class, method_name)
            if not callable(method):
                logger.error(f"Plugin class {method_name} is not callable")
                return False

        # Check for lang attribute
        if not hasattr(plugin_class, "lang"):
            # Check if it's defined on instance
            try:
                instance = plugin_class()
                if not hasattr(instance, "lang"):
                    logger.error("Plugin class missing 'lang' attribute")
                    return False
            except Exception:
                # If we can't instantiate, assume it needs constructor args
                pass

        return True
