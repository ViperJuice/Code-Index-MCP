"""Plugin discovery implementation."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from ..interfaces.shared_interfaces import Error, Result
from .interfaces import IPluginDiscovery
from .models import PluginInfo, PluginType, PluginValidationError

logger = logging.getLogger(__name__)


class PluginDiscovery(IPluginDiscovery):
    """Discovers plugins in the filesystem."""

    PLUGIN_MANIFEST = "plugin.json"
    PLUGIN_MODULE = "plugin.py"

    def discover_plugins(self, plugin_dirs: List[Path]) -> List[PluginInfo]:
        """Discover all plugins in the specified directories."""
        discovered_plugins = []

        for plugin_dir in plugin_dirs:
            if not plugin_dir.exists():
                logger.warning(f"Plugin directory does not exist: {plugin_dir}")
                continue

            logger.info(f"Scanning for plugins in: {plugin_dir}")

            # Look for plugin directories (those containing plugin.json or plugin.py)
            for path in plugin_dir.iterdir():
                if path.is_dir() and self.validate_plugin(path):
                    try:
                        plugin_info = self._load_plugin_info(path)
                        if plugin_info:
                            discovered_plugins.append(plugin_info)
                            logger.info(
                                f"Discovered plugin: {plugin_info.name} v{plugin_info.version}"
                            )
                    except Exception as e:
                        logger.error(f"Error loading plugin from {path}: {e}")

        # Also check if the plugin_dirs themselves are plugins
        # (but skip if they're the main plugins directory)
        for plugin_dir in plugin_dirs:
            if (
                plugin_dir.exists()
                and plugin_dir.name != "plugins"  # Skip the main plugins directory
                and self.validate_plugin(plugin_dir)
            ):
                try:
                    plugin_info = self._load_plugin_info(plugin_dir)
                    if plugin_info and plugin_info not in discovered_plugins:
                        discovered_plugins.append(plugin_info)
                        logger.info(f"Discovered plugin: {plugin_info.name} v{plugin_info.version}")
                except Exception as e:
                    logger.error(f"Error loading plugin from {plugin_dir}: {e}")

        return discovered_plugins

    def discover_plugins_safe(self, plugin_dirs: List[Path]) -> Result[List[PluginInfo]]:
        """Discover plugins using Result pattern for error handling."""
        try:
            plugins = self.discover_plugins(plugin_dirs)
            return Result.success_result(
                plugins,
                metadata={
                    "discovered_count": len(plugins),
                    "scanned_directories": [str(d) for d in plugin_dirs],
                    "discovery_time": datetime.now().isoformat(),
                },
            )
        except Exception as e:
            error = Error(
                code="PLUGIN_DISCOVERY_ERROR",
                message="Failed to discover plugins",
                details={
                    "scanned_directories": [str(d) for d in plugin_dirs],
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                timestamp=datetime.now(),
            )
            return Result.error_result(error)

    def validate_plugin(self, plugin_path: Path) -> bool:
        """Validate if a path contains a valid plugin."""
        if not plugin_path.is_dir():
            return False

        # Check for plugin manifest
        manifest_path = plugin_path / self.PLUGIN_MANIFEST
        if manifest_path.exists():
            return True

        # Check for plugin module with __plugin_info__
        module_path = plugin_path / self.PLUGIN_MODULE
        if module_path.exists():
            return True

        # Check for __init__.py with plugin info
        init_path = plugin_path / "__init__.py"
        if init_path.exists():
            content = init_path.read_text()
            if "__plugin_info__" in content or "Plugin" in content:
                return True

        return False

    def validate_plugin_safe(self, plugin_path: Path) -> Result[bool]:
        """Validate a plugin using Result pattern for error handling."""
        try:
            is_valid = self.validate_plugin(plugin_path)
            return Result.success_result(
                is_valid,
                metadata={
                    "plugin_path": str(plugin_path),
                    "validated_at": datetime.now().isoformat(),
                },
            )
        except Exception as e:
            error = Error(
                code="PLUGIN_VALIDATION_ERROR",
                message=f"Failed to validate plugin at {plugin_path}",
                details={
                    "plugin_path": str(plugin_path),
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                timestamp=datetime.now(),
            )
            return Result.error_result(error)

    def _load_plugin_info(self, plugin_path: Path) -> Optional[PluginInfo]:
        """Load plugin information from a plugin directory."""
        # First try to load from plugin.json
        manifest_path = plugin_path / self.PLUGIN_MANIFEST
        if manifest_path.exists():
            return self._load_from_manifest(manifest_path)

        # Then try to load from Python module
        return self._load_from_module(plugin_path)

    def _load_from_manifest(self, manifest_path: Path) -> Optional[PluginInfo]:
        """Load plugin info from plugin.json manifest."""
        try:
            with open(manifest_path, "r") as f:
                data = json.load(f)

            # Validate required fields
            required_fields = ["name", "version", "description", "author"]
            for field in required_fields:
                if field not in data:
                    raise PluginValidationError(f"Missing required field: {field}")

            # Determine plugin type
            plugin_type = PluginType(data.get("type", "language"))

            # Build module name from path
            plugin_dir = manifest_path.parent
            module_name = f"mcp_server.plugins.{plugin_dir.name}"

            return PluginInfo(
                name=data["name"],
                version=data["version"],
                description=data["description"],
                author=data["author"],
                plugin_type=plugin_type,
                language=data.get("language"),
                file_extensions=data.get("file_extensions", []),
                path=plugin_dir,
                module_name=module_name,
                class_name=data.get("class_name", "Plugin"),
                dependencies=data.get("dependencies", []),
                config_schema=data.get("config_schema", {}),
                metadata=data.get("metadata", {}),
            )
        except Exception as e:
            logger.error(f"Error loading manifest {manifest_path}: {e}")
            return None

    def _load_from_module(self, plugin_path: Path) -> Optional[PluginInfo]:
        """Load plugin info from Python module."""
        try:
            # Check for plugin.py or __init__.py
            module_file = None
            if (plugin_path / self.PLUGIN_MODULE).exists():
                module_file = plugin_path / self.PLUGIN_MODULE
            elif (plugin_path / "__init__.py").exists():
                module_file = plugin_path / "__init__.py"
            else:
                return None

            # Read the file to extract __plugin_info__
            content = module_file.read_text()

            # Try to extract plugin info from the module
            # This is a simple approach - in production, we'd use AST parsing
            plugin_info = self._extract_plugin_info_from_source(content, plugin_path)

            if not plugin_info:
                # Fallback: create basic info from directory name
                plugin_name = plugin_path.name.replace("_plugin", "").replace("_", " ").title()
                language = plugin_path.name.replace("_plugin", "")

                # Determine file extensions based on language
                extension_map = {
                    "python": [".py"],
                    "js": [".js", ".jsx", ".ts", ".tsx"],
                    "javascript": [".js", ".jsx", ".ts", ".tsx"],
                    "c": [".c", ".h"],
                    "cpp": [".cpp", ".cc", ".cxx", ".hpp", ".h"],
                    "dart": [".dart"],
                    "html_css": [".html", ".htm", ".css", ".scss", ".sass"],
                }

                file_extensions = extension_map.get(language, [])

                plugin_info = PluginInfo(
                    name=plugin_name,
                    version="1.0.0",
                    description=f"{plugin_name} Plugin",
                    author="Unknown",
                    plugin_type=PluginType.LANGUAGE,
                    language=language,
                    file_extensions=file_extensions,
                    path=plugin_path,
                    module_name=f"mcp_server.plugins.{plugin_path.name}",
                    class_name="Plugin",
                )

            return plugin_info

        except Exception as e:
            logger.error(f"Error loading plugin from {plugin_path}: {e}")
            return None

    def _extract_plugin_info_from_source(
        self, source: str, plugin_path: Path
    ) -> Optional[PluginInfo]:
        """Extract plugin info from Python source code."""
        # This is a simplified version - in production, use AST parsing
        try:
            # Look for __plugin_info__ dictionary
            if "__plugin_info__" in source:
                # Extract the dictionary (simplified approach)
                start = source.find("__plugin_info__")
                if start != -1:
                    # Find the dictionary bounds
                    dict_start = source.find("{", start)
                    if dict_start != -1:
                        # Count braces to find the end
                        brace_count = 1
                        i = dict_start + 1
                        while i < len(source) and brace_count > 0:
                            if source[i] == "{":
                                brace_count += 1
                            elif source[i] == "}":
                                brace_count -= 1
                            i += 1

                        if brace_count == 0:
                            dict_str = source[dict_start:i]
                            # Safely evaluate the dictionary
                            # In production, use ast.literal_eval
                            try:
                                # Very basic extraction - just get quoted values
                                info = {}
                                for key in [
                                    "name",
                                    "version",
                                    "description",
                                    "author",
                                    "language",
                                ]:
                                    import re

                                    pattern = rf'"{key}"\s*:\s*"([^"]+)"'
                                    match = re.search(pattern, dict_str)
                                    if match:
                                        info[key] = match.group(1)

                                if "name" in info:
                                    return PluginInfo(
                                        name=info.get("name", plugin_path.name),
                                        version=info.get("version", "1.0.0"),
                                        description=info.get("description", ""),
                                        author=info.get("author", "Unknown"),
                                        plugin_type=PluginType.LANGUAGE,
                                        language=info.get("language"),
                                        file_extensions=self._get_extensions_from_language(
                                            info.get("language", "")
                                        ),
                                        path=plugin_path,
                                        module_name=f"mcp_server.plugins.{plugin_path.name}",
                                        class_name="Plugin",
                                    )
                            except Exception:
                                pass

            return None

        except Exception as e:
            logger.debug(f"Could not extract plugin info from source: {e}")
            return None

    def _get_extensions_from_language(self, language: str) -> List[str]:
        """Get file extensions for a language."""
        extension_map = {
            "python": [".py"],
            "javascript": [".js", ".jsx", ".ts", ".tsx"],
            "c": [".c", ".h"],
            "cpp": [".cpp", ".cc", ".cxx", ".hpp", ".h"],
            "dart": [".dart"],
            "html": [".html", ".htm"],
            "css": [".css", ".scss", ".sass"],
        }
        return extension_map.get(language.lower(), [])
