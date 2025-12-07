"""Plugin system data models."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


class PluginState(Enum):
    """Plugin lifecycle states."""

    DISCOVERED = "discovered"
    LOADED = "loaded"
    INITIALIZED = "initialized"
    STARTED = "started"
    STOPPED = "stopped"
    ERROR = "error"
    DISABLED = "disabled"


class PluginType(Enum):
    """Types of plugins."""

    LANGUAGE = "language"
    INDEXER = "indexer"
    ANALYZER = "analyzer"
    FORMATTER = "formatter"
    CUSTOM = "custom"


@dataclass
class PluginInfo:
    """Information about a plugin."""

    name: str
    version: str
    description: str
    author: str
    plugin_type: PluginType
    language: Optional[str]  # For language plugins
    file_extensions: List[str]  # Supported file extensions
    path: Path  # Path to plugin module
    module_name: str  # Python module name
    class_name: str = "Plugin"  # Name of the plugin class
    dependencies: List[str] = field(default_factory=list)
    config_schema: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate and normalize data after initialization."""
        if isinstance(self.path, str):
            self.path = Path(self.path)
        if isinstance(self.plugin_type, str):
            self.plugin_type = PluginType(self.plugin_type)


@dataclass
class PluginConfig:
    """Configuration for a plugin."""

    enabled: bool = True
    priority: int = 0  # Higher priority plugins are used first
    settings: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    health_check: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PluginConfig":
        """Create from dictionary."""
        health_check_defaults = {
            "enabled": True,
            "interval_seconds": 60,
            "timeout_seconds": 5,
        }

        health_check = data.get("health_check", {})
        # Merge with defaults
        for key, default_value in health_check_defaults.items():
            if key not in health_check:
                health_check[key] = default_value

        return cls(
            enabled=data.get("enabled", True),
            priority=data.get("priority", 0),
            settings=data.get("settings", {}),
            dependencies=data.get("dependencies", []),
            health_check=health_check,
        )


@dataclass
class PluginInstance:
    """Runtime information about a plugin instance."""

    info: PluginInfo
    config: PluginConfig
    instance: Any  # The actual plugin instance
    state: PluginState = PluginState.DISCOVERED
    error: Optional[str] = None
    load_time: Optional[float] = None  # Time taken to load (seconds)
    last_health_check: Optional[float] = None  # Timestamp of last health check
    health_status: str = "unknown"  # healthy, unhealthy, unknown
    metrics: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_active(self) -> bool:
        """Check if plugin is in an active state."""
        return self.state in (PluginState.INITIALIZED, PluginState.STARTED)

    @property
    def is_error(self) -> bool:
        """Check if plugin is in error state."""
        return self.state == PluginState.ERROR

    @property
    def is_healthy(self) -> bool:
        """Check if plugin is healthy based on last health check."""
        return self.health_status == "healthy"

    def update_metrics(self, metrics: Dict[str, Any]) -> None:
        """Update plugin performance metrics."""
        import time

        self.metrics.update(metrics)
        self.metrics["last_updated"] = time.time()


@dataclass
class PluginLoadResult:
    """Result of plugin loading operation."""

    success: bool
    plugin_name: str
    message: str
    error: Optional[Exception] = None


@dataclass
class PluginSystemConfig:
    """Configuration for the plugin system."""

    plugin_dirs: List[Path] = field(default_factory=list)
    auto_discover: bool = True
    auto_load: bool = True
    validate_interfaces: bool = True
    enable_hot_reload: bool = False
    max_concurrent_loads: int = 5
    load_timeout_seconds: int = 30
    config_file: Optional[Path] = None
    disabled_plugins: Set[str] = field(default_factory=set)
    plugin_configs: Dict[str, PluginConfig] = field(default_factory=dict)

    # Enhanced configuration options
    defaults: Dict[str, Any] = field(default_factory=dict)
    environments: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    loading: Dict[str, Any] = field(default_factory=dict)
    monitoring: Dict[str, Any] = field(default_factory=dict)
    security: Dict[str, Any] = field(default_factory=dict)
    resource_limits: Dict[str, Any] = field(default_factory=dict)
    backup: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Ensure paths are Path objects and set defaults."""
        self.plugin_dirs = [Path(p) if isinstance(p, str) else p for p in self.plugin_dirs]
        if self.config_file and isinstance(self.config_file, str):
            self.config_file = Path(self.config_file)

        # Set default values for enhanced options
        if not self.defaults:
            self.defaults = {
                "max_file_size": 1048576,
                "cache_enabled": True,
                "timeout_seconds": 10,
                "retry_attempts": 3,
            }

        if not self.loading:
            self.loading = {
                "strategy": "priority",
                "parallel_loading": True,
                "fail_fast": False,
                "retry_failed": True,
            }

        if not self.monitoring:
            self.monitoring = {
                "enable_metrics": True,
                "enable_health_checks": True,
                "metric_collection_interval": 30,
            }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PluginSystemConfig":
        """Create from dictionary."""
        config = cls()

        # Basic settings
        if "plugin_dirs" in data:
            config.plugin_dirs = [Path(p) for p in data["plugin_dirs"]]

        config.auto_discover = data.get("auto_discover", True)
        config.auto_load = data.get("auto_load", True)
        config.validate_interfaces = data.get("validate_interfaces", True)
        config.enable_hot_reload = data.get("enable_hot_reload", False)
        config.max_concurrent_loads = data.get("max_concurrent_loads", 5)
        config.load_timeout_seconds = data.get("load_timeout_seconds", 30)

        if "config_file" in data:
            config.config_file = Path(data["config_file"])

        if "disabled_plugins" in data:
            config.disabled_plugins = set(data["disabled_plugins"])

        # Plugin-specific configurations
        if "plugins" in data:
            for name, plugin_data in data["plugins"].items():
                plugin_config = PluginConfig.from_dict(plugin_data)
                # Apply defaults from global config
                if config.defaults:
                    for key, value in config.defaults.items():
                        if key not in plugin_config.settings:
                            plugin_config.settings[key] = value
                config.plugin_configs[name] = plugin_config

        # Enhanced configuration sections
        config.defaults = data.get("defaults", {})
        config.environments = data.get("environments", {})
        config.loading = data.get("loading", {})
        config.monitoring = data.get("monitoring", {})
        config.security = data.get("security", {})
        config.resource_limits = data.get("resource_limits", {})
        config.backup = data.get("backup", {})

        return config

    def get_environment_config(self, environment: str = None) -> Dict[str, Any]:
        """Get configuration for specific environment."""
        if not environment:
            import os

            environment = os.getenv("ENVIRONMENT", "development")

        return self.environments.get(environment, {})

    def apply_environment_overrides(self, environment: str = None) -> None:
        """Apply environment-specific configuration overrides."""
        env_config = self.get_environment_config(environment)

        if "enable_hot_reload" in env_config:
            self.enable_hot_reload = env_config["enable_hot_reload"]
        if "validate_interfaces" in env_config:
            self.validate_interfaces = env_config["validate_interfaces"]
        if "auto_load" in env_config:
            self.auto_load = env_config["auto_load"]


@dataclass
class PluginEvent:
    """Event emitted by the plugin system."""

    event_type: str
    plugin_name: str
    timestamp: float
    data: Dict[str, Any] = field(default_factory=dict)


# Exception classes
class PluginError(Exception):
    """Base exception for plugin system errors."""


class PluginNotFoundError(PluginError):
    """Plugin not found."""


class PluginLoadError(PluginError):
    """Error loading plugin."""


class PluginInitError(PluginError):
    """Error initializing plugin."""


class PluginValidationError(PluginError):
    """Plugin validation failed."""


class PluginConfigError(PluginError):
    """Plugin configuration error."""
