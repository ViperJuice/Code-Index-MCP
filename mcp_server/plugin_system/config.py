"""
Plugin configuration management.
Handles loading, validation, and management of plugin configurations.
"""

import json
import logging
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .models import PluginConfig, PluginSystemConfig

logger = logging.getLogger(__name__)


class PluginConfigManager:
    """Manages plugin configurations."""

    def __init__(self, config_dir: str = None):
        """
        Initialize configuration manager.

        Args:
            config_dir: Directory containing plugin configurations
        """
        self.config_dir = Path(config_dir) if config_dir else Path("config/plugins")
        self.configs: Dict[str, PluginConfig] = {}
        self.system_config: Optional[PluginSystemConfig] = None

    def load_system_config(self, config_file: str = None) -> PluginSystemConfig:
        """
        Load system-wide plugin configuration.

        Args:
            config_file: Path to system config file

        Returns:
            Plugin system configuration
        """
        if config_file and Path(config_file).exists():
            config_path = Path(config_file)
        else:
            # Try default locations
            for location in ["plugins.yaml", "config/plugins.yaml", ".plugins.yaml"]:
                if Path(location).exists():
                    config_path = Path(location)
                    break
            else:
                # Return default config
                logger.info("No system config found, using defaults")
                self.system_config = PluginSystemConfig()
                return self.system_config

        try:
            logger.info(f"Loading system config from {config_path}")
            with open(config_path, "r") as f:
                data = yaml.safe_load(f)

            self.system_config = PluginSystemConfig.from_dict(data)

            # Apply environment overrides
            environment = os.getenv("ENVIRONMENT", "development")
            self.system_config.apply_environment_overrides(environment)

            logger.info(f"System config loaded successfully for environment: {environment}")
            return self.system_config

        except Exception as e:
            logger.error(f"Failed to load system config: {e}")
            self.system_config = PluginSystemConfig()
            return self.system_config

    def load_plugin_config(self, plugin_name: str) -> Optional[PluginConfig]:
        """
        Load configuration for a specific plugin.

        Args:
            plugin_name: Name of the plugin

        Returns:
            Plugin configuration or None
        """
        # Check if already loaded
        if plugin_name in self.configs:
            return self.configs[plugin_name]

        # Try to load from system config
        if self.system_config and plugin_name in self.system_config.plugin_configs:
            config = self.system_config.plugin_configs[plugin_name]
            self.configs[plugin_name] = config
            return config

        # Try to load from individual file
        config_file = self.config_dir / f"{plugin_name}.yaml"
        if config_file.exists():
            try:
                with open(config_file, "r") as f:
                    data = yaml.safe_load(f)
                config = PluginConfig.from_dict(data)
                self.configs[plugin_name] = config
                logger.info(f"Loaded config for plugin: {plugin_name}")
                return config
            except Exception as e:
                logger.error(f"Failed to load config for {plugin_name}: {e}")

        # Return default config
        config = PluginConfig()
        self.configs[plugin_name] = config
        return config

    def save_plugin_config(self, plugin_name: str, config: PluginConfig):
        """
        Save plugin configuration.

        Args:
            plugin_name: Name of the plugin
            config: Plugin configuration
        """
        self.configs[plugin_name] = config

        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Save to file
        config_file = self.config_dir / f"{plugin_name}.yaml"
        try:
            with open(config_file, "w") as f:
                yaml.dump(asdict(config), f, default_flow_style=False)
            logger.info(f"Saved config for plugin: {plugin_name}")
        except Exception as e:
            logger.error(f"Failed to save config for {plugin_name}: {e}")

    def get_enabled_plugins(self) -> List[str]:
        """Get list of enabled plugins."""
        if not self.system_config:
            return []

        enabled = []
        for name, config in self.system_config.plugin_configs.items():
            if config.enabled and name not in self.system_config.disabled_plugins:
                enabled.append(name)

        return enabled

    def enable_plugin(self, plugin_name: str):
        """Enable a plugin."""
        if plugin_name in self.system_config.disabled_plugins:
            self.system_config.disabled_plugins.remove(plugin_name)

        config = self.load_plugin_config(plugin_name)
        config.enabled = True
        self.save_plugin_config(plugin_name, config)

    def disable_plugin(self, plugin_name: str):
        """Disable a plugin."""
        self.system_config.disabled_plugins.add(plugin_name)

        config = self.load_plugin_config(plugin_name)
        config.enabled = False
        self.save_plugin_config(plugin_name, config)

    def update_plugin_settings(self, plugin_name: str, settings: Dict[str, Any]):
        """
        Update plugin settings.

        Args:
            plugin_name: Name of the plugin
            settings: Settings to update
        """
        config = self.load_plugin_config(plugin_name)
        config.settings.update(settings)
        self.save_plugin_config(plugin_name, config)

    def get_plugin_setting(self, plugin_name: str, key: str, default: Any = None) -> Any:
        """
        Get a specific plugin setting.

        Args:
            plugin_name: Name of the plugin
            key: Setting key
            default: Default value if not found

        Returns:
            Setting value
        """
        config = self.load_plugin_config(plugin_name)
        return config.settings.get(key, default)

    def validate_config(self, plugin_name: str, schema: Dict[str, Any]) -> bool:
        """
        Validate plugin configuration against schema.

        Args:
            plugin_name: Name of the plugin
            schema: Configuration schema

        Returns:
            True if valid, False otherwise
        """
        config = self.load_plugin_config(plugin_name)

        # Simple validation - check required fields and types
        for field, spec in schema.items():
            if spec.get("required", False) and field not in config.settings:
                logger.error(f"Missing required field '{field}' for plugin {plugin_name}")
                return False

            if field in config.settings:
                value = config.settings[field]
                expected_type = spec.get("type")

                if expected_type == "boolean" and not isinstance(value, bool):
                    logger.error(f"Invalid type for '{field}': expected boolean")
                    return False
                elif expected_type == "integer" and not isinstance(value, int):
                    logger.error(f"Invalid type for '{field}': expected integer")
                    return False
                elif expected_type == "string" and not isinstance(value, str):
                    logger.error(f"Invalid type for '{field}': expected string")
                    return False

                # Check constraints
                if "minimum" in spec and value < spec["minimum"]:
                    logger.error(f"Value for '{field}' below minimum: {value} < {spec['minimum']}")
                    return False
                if "maximum" in spec and value > spec["maximum"]:
                    logger.error(f"Value for '{field}' above maximum: {value} > {spec['maximum']}")
                    return False

        return True

    def export_config(self, output_file: str):
        """Export all configurations to a file."""
        all_configs = {
            "system": asdict(self.system_config) if self.system_config else {},
            "plugins": {name: asdict(config) for name, config in self.configs.items()},
        }

        with open(output_file, "w") as f:
            if output_file.endswith(".json"):
                json.dump(all_configs, f, indent=2)
            else:
                yaml.dump(all_configs, f, default_flow_style=False)

        logger.info(f"Exported configuration to {output_file}")

    def import_config(self, input_file: str):
        """Import configurations from a file."""
        with open(input_file, "r") as f:
            if input_file.endswith(".json"):
                data = json.load(f)
            else:
                data = yaml.safe_load(f)

        # Import system config
        if "system" in data:
            self.system_config = PluginSystemConfig.from_dict(data["system"])

        # Import plugin configs
        if "plugins" in data:
            for name, config_data in data["plugins"].items():
                config = PluginConfig.from_dict(config_data)
                self.configs[name] = config

        logger.info(f"Imported configuration from {input_file}")


# Global configuration manager
_config_manager = None


def get_config_manager() -> PluginConfigManager:
    """Get the global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = PluginConfigManager()
        _config_manager.load_system_config()
    return _config_manager
