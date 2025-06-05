"""
Enhanced settings management for MCP server.

Provides unified configuration from multiple sources:
1. Environment variables (highest priority)
2. Configuration file
3. Defaults
"""
import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class EnhancedSettings:
    """Enhanced settings with support for all MCP features."""
    
    # Core settings
    transport_type: str = 'stdio'
    debug: bool = False
    log_level: str = 'INFO'
    log_file: Optional[str] = None
    config_file: Optional[str] = None
    db_path: str = 'code_index.db'
    
    # Auto-indexing settings
    auto_index: bool = False
    auto_index_patterns: list = field(default_factory=lambda: ['**/*.py', '**/*.js', '**/*.ts'])
    auto_index_exclude: list = field(default_factory=lambda: ['.git', 'node_modules', '.venv', '__pycache__'])
    auto_index_max_files: int = 1000
    
    # Claude Code compatibility
    disable_resources: bool = False
    
    # Performance settings
    cache_enabled: bool = False
    cache_backend: str = 'memory'
    cache_max_entries: int = 1000
    cache_ttl: int = 3600
    
    rate_limit_enabled: bool = False
    rate_limit_requests: int = 100
    rate_limit_window: int = 60
    
    memory_monitor_enabled: bool = False
    memory_limit_mb: int = 512
    
    # Production settings
    health_enabled: bool = False
    health_check_interval: int = 30
    
    metrics_enabled: bool = False
    metrics_port: int = 9090
    
    # Protocol settings
    websocket_enabled: bool = False
    websocket_host: str = 'localhost'
    websocket_port: int = 8765
    
    batch_enabled: bool = False
    batch_max_size: int = 10
    
    # Feature settings
    watcher_enabled: bool = False
    middleware_enabled: bool = False
    
    # Session settings
    session_timeout: int = 3600
    session_persist: bool = False
    
    @classmethod
    def from_env(cls) -> 'EnhancedSettings':
        """Create settings from environment variables."""
        settings = cls()
        
        # Map environment variables to settings attributes
        env_mappings = {
            # Core
            'MCP_TRANSPORT': ('transport_type', str),
            'MCP_DEBUG': ('debug', lambda x: x.lower() in ('true', '1', 'yes')),
            'MCP_LOG_LEVEL': ('log_level', str),
            'MCP_LOG_FILE': ('log_file', str),
            'MCP_CONFIG_FILE': ('config_file', str),
            'MCP_DB_PATH': ('db_path', str),
            
            # Auto-indexing
            'MCP_AUTO_INDEX': ('auto_index', lambda x: x.lower() in ('true', '1', 'yes')),
            'MCP_AUTO_INDEX_PATTERNS': ('auto_index_patterns', lambda x: x.split(',')),
            'MCP_AUTO_INDEX_EXCLUDE': ('auto_index_exclude', lambda x: x.split(',')),
            'MCP_AUTO_INDEX_MAX_FILES': ('auto_index_max_files', int),
            
            # Claude Code
            'MCP_DISABLE_RESOURCES': ('disable_resources', lambda x: x.lower() in ('true', '1', 'yes')),
            
            # Performance
            'MCP_ENABLE_CACHE': ('cache_enabled', lambda x: x.lower() in ('true', '1', 'yes')),
            'MCP_CACHE_BACKEND': ('cache_backend', str),
            'MCP_CACHE_MAX_ENTRIES': ('cache_max_entries', int),
            'MCP_CACHE_TTL': ('cache_ttl', int),
            
            'MCP_ENABLE_RATE_LIMIT': ('rate_limit_enabled', lambda x: x.lower() in ('true', '1', 'yes')),
            'MCP_RATE_LIMIT_REQUESTS': ('rate_limit_requests', int),
            'MCP_RATE_LIMIT_WINDOW': ('rate_limit_window', int),
            
            'MCP_MONITOR_MEMORY': ('memory_monitor_enabled', lambda x: x.lower() in ('true', '1', 'yes')),
            'MCP_MEMORY_LIMIT_MB': ('memory_limit_mb', int),
            
            # Production
            'MCP_ENABLE_HEALTH': ('health_enabled', lambda x: x.lower() in ('true', '1', 'yes')),
            'MCP_HEALTH_CHECK_INTERVAL': ('health_check_interval', int),
            
            'MCP_ENABLE_METRICS': ('metrics_enabled', lambda x: x.lower() in ('true', '1', 'yes')),
            'MCP_METRICS_PORT': ('metrics_port', int),
            
            # Protocol
            'MCP_ENABLE_WEBSOCKET': ('websocket_enabled', lambda x: x.lower() in ('true', '1', 'yes')),
            'MCP_WEBSOCKET_HOST': ('websocket_host', str),
            'MCP_WEBSOCKET_PORT': ('websocket_port', int),
            
            'MCP_ENABLE_BATCH': ('batch_enabled', lambda x: x.lower() in ('true', '1', 'yes')),
            'MCP_BATCH_MAX_SIZE': ('batch_max_size', int),
            
            # Features
            'MCP_ENABLE_WATCHER': ('watcher_enabled', lambda x: x.lower() in ('true', '1', 'yes')),
            'MCP_ENABLE_MIDDLEWARE': ('middleware_enabled', lambda x: x.lower() in ('true', '1', 'yes')),
            
            # Session
            'MCP_SESSION_TIMEOUT': ('session_timeout', int),
            'MCP_SESSION_PERSIST': ('session_persist', lambda x: x.lower() in ('true', '1', 'yes')),
        }
        
        # Apply environment variables
        for env_var, (attr_name, converter) in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                try:
                    setattr(settings, attr_name, converter(value))
                except Exception as e:
                    logger.warning(f"Failed to parse {env_var}={value}: {e}")
        
        # Load from config file if specified
        if settings.config_file:
            settings._load_from_file(settings.config_file)
        
        # Sync with feature manager to handle auto-enabled dependencies
        settings._sync_with_feature_manager()
        
        return settings
    
    def _load_from_file(self, config_file: str) -> None:
        """Load settings from a JSON configuration file."""
        try:
            path = Path(config_file)
            if path.exists():
                with open(path, 'r') as f:
                    config_data = json.load(f)
                
                # Get default values from a fresh instance
                defaults = self.__class__()
                
                # Update settings with config file values
                # (environment variables take precedence)
                for key, value in config_data.items():
                    if hasattr(self, key):
                        # Only set if the current value is still the default value
                        # (i.e., not already set by environment variables)
                        current_value = getattr(self, key)
                        default_value = getattr(defaults, key)
                        if current_value == default_value:
                            setattr(self, key, value)
                
                logger.info(f"Loaded configuration from {config_file}")
            else:
                logger.warning(f"Configuration file {config_file} not found")
        except Exception as e:
            logger.error(f"Failed to load configuration from {config_file}: {e}")
    
    def _sync_with_feature_manager(self) -> None:
        """Sync settings with feature manager to handle auto-enabled dependencies."""
        try:
            # Import here to avoid circular imports
            from ..utils.feature_flags import feature_manager
            
            # Initialize feature manager to handle dependencies
            feature_manager.initialize_from_env()
            
            # Get enabled features from feature manager
            enabled_features = feature_manager.get_enabled_features()
            
            # Map feature names to setting attributes
            feature_to_setting = {
                'cache': 'cache_enabled',
                'health': 'health_enabled',
                'metrics': 'metrics_enabled',
                'rate_limit': 'rate_limit_enabled',
                'memory_monitor': 'memory_monitor_enabled',
                'websocket': 'websocket_enabled',
                'batch': 'batch_enabled',
                'watcher': 'watcher_enabled',
                'middleware': 'middleware_enabled',
            }
            
            # Update settings based on auto-enabled features
            for feature_name in enabled_features:
                setting_attr = feature_to_setting.get(feature_name)
                if setting_attr and hasattr(self, setting_attr):
                    current_value = getattr(self, setting_attr)
                    if not current_value:
                        logger.info(f"Auto-enabling {setting_attr} due to feature dependency")
                        setattr(self, setting_attr, True)
                        
        except ImportError:
            logger.warning("Feature manager not available for dependency sync")
        except Exception as e:
            logger.warning(f"Failed to sync with feature manager: {e}")
    
    def save_to_file(self, config_file: str) -> None:
        """Save current settings to a JSON file."""
        try:
            config_data = {}
            for key, value in self.__dict__.items():
                if not key.startswith('_'):
                    config_data[key] = value
            
            path = Path(config_file)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            logger.info(f"Saved configuration to {config_file}")
        except Exception as e:
            logger.error(f"Failed to save configuration to {config_file}: {e}")
    
    def validate(self) -> List[str]:
        """Validate settings and return list of warnings."""
        warnings = []
        
        # Validate transport type
        if self.transport_type not in ('stdio', 'websocket'):
            warnings.append(f"Invalid transport type: {self.transport_type}")
        
        # Validate log level
        valid_log_levels = ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
        if self.log_level.upper() not in valid_log_levels:
            warnings.append(f"Invalid log level: {self.log_level}")
        
        # Validate cache backend
        if self.cache_enabled and self.cache_backend not in ('memory', 'redis'):
            warnings.append(f"Invalid cache backend: {self.cache_backend}")
        
        # Validate numeric limits
        if self.cache_max_entries <= 0:
            warnings.append("cache_max_entries must be positive")
        
        if self.rate_limit_requests <= 0:
            warnings.append("rate_limit_requests must be positive")
        
        if self.memory_limit_mb <= 0:
            warnings.append("memory_limit_mb must be positive")
        
        # WebSocket specific validation
        if self.websocket_enabled:
            if self.websocket_port < 1 or self.websocket_port > 65535:
                warnings.append(f"Invalid WebSocket port: {self.websocket_port}")
        
        return warnings
    
    def print_summary(self) -> None:
        """Print configuration summary for debugging."""
        print("\n=== MCP Server Configuration ===")
        print(f"Transport: {self.transport_type}")
        print(f"Debug: {self.debug}")
        print(f"Log Level: {self.log_level}")
        
        if self.auto_index:
            print(f"\nAuto-indexing: ENABLED")
            print(f"  Patterns: {', '.join(self.auto_index_patterns)}")
            print(f"  Max files: {self.auto_index_max_files}")
        
        print(f"\nClaude Code Mode: {'YES' if self.disable_resources else 'NO'}")
        
        if self.cache_enabled:
            print(f"\nCache: ENABLED ({self.cache_backend})")
            print(f"  Max entries: {self.cache_max_entries}")
            print(f"  TTL: {self.cache_ttl}s")
        
        if self.health_enabled:
            print(f"\nHealth Monitoring: ENABLED")
            print(f"  Check interval: {self.health_check_interval}s")
        
        if self.websocket_enabled:
            print(f"\nWebSocket: ENABLED")
            print(f"  Host: {self.websocket_host}:{self.websocket_port}")
        
        print("===============================\n")


# Global settings instance
enhanced_settings = EnhancedSettings.from_env()