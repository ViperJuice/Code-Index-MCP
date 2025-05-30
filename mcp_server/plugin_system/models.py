"""Plugin system data models."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Set


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
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PluginConfig':
        """Create from dictionary."""
        return cls(
            enabled=data.get('enabled', True),
            priority=data.get('priority', 0),
            settings=data.get('settings', {})
        )


@dataclass
class PluginInstance:
    """Runtime information about a plugin instance."""
    info: PluginInfo
    config: PluginConfig
    instance: Any  # The actual plugin instance
    state: PluginState = PluginState.DISCOVERED
    error: Optional[str] = None
    
    @property
    def is_active(self) -> bool:
        """Check if plugin is in an active state."""
        return self.state in (PluginState.INITIALIZED, PluginState.STARTED)
    
    @property
    def is_error(self) -> bool:
        """Check if plugin is in error state."""
        return self.state == PluginState.ERROR


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
    config_file: Optional[Path] = None
    disabled_plugins: Set[str] = field(default_factory=set)
    plugin_configs: Dict[str, PluginConfig] = field(default_factory=dict)
    
    def __post_init__(self):
        """Ensure paths are Path objects."""
        self.plugin_dirs = [Path(p) if isinstance(p, str) else p for p in self.plugin_dirs]
        if self.config_file and isinstance(self.config_file, str):
            self.config_file = Path(self.config_file)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PluginSystemConfig':
        """Create from dictionary."""
        config = cls()
        
        if 'plugin_dirs' in data:
            config.plugin_dirs = [Path(p) for p in data['plugin_dirs']]
        
        if 'auto_discover' in data:
            config.auto_discover = data['auto_discover']
        
        if 'auto_load' in data:
            config.auto_load = data['auto_load']
        
        if 'validate_interfaces' in data:
            config.validate_interfaces = data['validate_interfaces']
        
        if 'enable_hot_reload' in data:
            config.enable_hot_reload = data['enable_hot_reload']
        
        if 'config_file' in data:
            config.config_file = Path(data['config_file'])
        
        if 'disabled_plugins' in data:
            config.disabled_plugins = set(data['disabled_plugins'])
        
        if 'plugins' in data:
            for name, plugin_data in data['plugins'].items():
                config.plugin_configs[name] = PluginConfig.from_dict(plugin_data)
        
        return config


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
    pass


class PluginNotFoundError(PluginError):
    """Plugin not found."""
    pass


class PluginLoadError(PluginError):
    """Error loading plugin."""
    pass


class PluginInitError(PluginError):
    """Error initializing plugin."""
    pass


class PluginValidationError(PluginError):
    """Plugin validation failed."""
    pass


class PluginConfigError(PluginError):
    """Plugin configuration error."""
    pass