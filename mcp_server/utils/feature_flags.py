"""
Feature flags management for MCP server.

Provides centralized control over optional features through environment variables.
"""
import os
import logging
from typing import Dict, Any, Optional, Set
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class FeatureConfig:
    """Configuration for a single feature."""
    name: str
    env_var: str
    default: bool = False
    description: str = ""
    dependencies: Set[str] = field(default_factory=set)
    config_vars: Dict[str, Any] = field(default_factory=dict)


class FeatureManager:
    """Manages feature flags and their configurations."""
    
    # Define all available features
    FEATURES = {
        'cache': FeatureConfig(
            name='cache',
            env_var='MCP_ENABLE_CACHE',
            default=False,
            description='Enable caching system for improved performance',
            config_vars={
                'backend': ('MCP_CACHE_BACKEND', 'memory'),
                'max_entries': ('MCP_CACHE_MAX_ENTRIES', 1000),
                'ttl': ('MCP_CACHE_TTL', 3600),
            }
        ),
        'health': FeatureConfig(
            name='health',
            env_var='MCP_ENABLE_HEALTH',
            default=False,
            description='Enable health monitoring and checks',
            config_vars={
                'interval': ('MCP_HEALTH_CHECK_INTERVAL', 30),
            }
        ),
        'metrics': FeatureConfig(
            name='metrics',
            env_var='MCP_ENABLE_METRICS',
            default=False,
            description='Enable metrics collection and reporting',
            config_vars={
                'port': ('MCP_METRICS_PORT', 9090),
            }
        ),
        'rate_limit': FeatureConfig(
            name='rate_limit',
            env_var='MCP_ENABLE_RATE_LIMIT',
            default=False,
            description='Enable rate limiting for API protection',
            config_vars={
                'requests': ('MCP_RATE_LIMIT_REQUESTS', 100),
                'window': ('MCP_RATE_LIMIT_WINDOW', 60),
            }
        ),
        'memory_monitor': FeatureConfig(
            name='memory_monitor',
            env_var='MCP_MONITOR_MEMORY',
            default=False,
            description='Enable memory usage monitoring',
            config_vars={
                'limit_mb': ('MCP_MEMORY_LIMIT_MB', 512),
            }
        ),
        'websocket': FeatureConfig(
            name='websocket',
            env_var='MCP_ENABLE_WEBSOCKET',
            default=False,
            description='Enable WebSocket transport',
            dependencies={'health'},  # WebSocket needs health checks
            config_vars={
                'host': ('MCP_WEBSOCKET_HOST', 'localhost'),
                'port': ('MCP_WEBSOCKET_PORT', 8765),
            }
        ),
        'batch': FeatureConfig(
            name='batch',
            env_var='MCP_ENABLE_BATCH',
            default=False,
            description='Enable batch operations',
            config_vars={
                'max_size': ('MCP_BATCH_MAX_SIZE', 10),
            }
        ),
        'watcher': FeatureConfig(
            name='watcher',
            env_var='MCP_ENABLE_WATCHER',
            default=False,
            description='Enable file system watcher for auto-reindexing',
        ),
        'middleware': FeatureConfig(
            name='middleware',
            env_var='MCP_ENABLE_MIDDLEWARE',
            default=False,
            description='Enable request/response middleware system',
        ),
    }
    
    def __init__(self):
        self._enabled_features: Set[str] = set()
        self._feature_configs: Dict[str, Dict[str, Any]] = {}
        self._initialized = False
    
    def initialize_from_env(self) -> None:
        """Initialize features based on environment variables."""
        if self._initialized:
            return
            
        for feature_name, feature_config in self.FEATURES.items():
            # Check if feature is enabled
            env_value = os.getenv(feature_config.env_var, '').lower()
            is_enabled = env_value in ('true', '1', 'yes') if env_value else feature_config.default
            
            if is_enabled:
                # Check dependencies
                if feature_config.dependencies:
                    missing_deps = feature_config.dependencies - self._enabled_features
                    if missing_deps:
                        logger.warning(
                            f"Feature '{feature_name}' requires {missing_deps} to be enabled. "
                            f"Enabling dependencies automatically."
                        )
                        for dep in missing_deps:
                            self._enable_feature(dep)
                
                self._enable_feature(feature_name)
        
        self._initialized = True
        logger.info(f"Features enabled: {sorted(self._enabled_features)}")
    
    def _enable_feature(self, feature_name: str) -> None:
        """Enable a feature and load its configuration."""
        if feature_name not in self.FEATURES:
            logger.error(f"Unknown feature: {feature_name}")
            return
            
        feature_config = self.FEATURES[feature_name]
        self._enabled_features.add(feature_name)
        
        # Load feature-specific configuration
        feature_settings = {}
        for config_key, (env_var, default) in feature_config.config_vars.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                # Try to parse as int/float if possible
                try:
                    if '.' in env_value:
                        value = float(env_value)
                    else:
                        value = int(env_value)
                except ValueError:
                    value = env_value
            else:
                value = default
            feature_settings[config_key] = value
        
        self._feature_configs[feature_name] = feature_settings
        logger.debug(f"Enabled feature '{feature_name}' with config: {feature_settings}")
    
    def is_enabled(self, feature_name: str) -> bool:
        """Check if a feature is enabled."""
        return feature_name in self._enabled_features
    
    def get_config(self, feature_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a feature."""
        return self._feature_configs.get(feature_name)
    
    def get_config_value(self, feature_name: str, config_key: str, default: Any = None) -> Any:
        """Get a specific configuration value for a feature."""
        feature_config = self._feature_configs.get(feature_name, {})
        return feature_config.get(config_key, default)
    
    def get_enabled_features(self) -> Set[str]:
        """Get set of all enabled features."""
        return self._enabled_features.copy()
    
    def get_all_features(self) -> Dict[str, FeatureConfig]:
        """Get all available features."""
        return self.FEATURES.copy()
    
    def print_feature_status(self) -> None:
        """Print current feature status for debugging."""
        print("\n=== MCP Server Feature Status ===")
        for feature_name, feature_config in sorted(self.FEATURES.items()):
            status = "✓ ENABLED" if self.is_enabled(feature_name) else "✗ DISABLED"
            print(f"{feature_name:15} {status:12} - {feature_config.description}")
            if self.is_enabled(feature_name) and self._feature_configs.get(feature_name):
                for key, value in self._feature_configs[feature_name].items():
                    print(f"  └─ {key}: {value}")
        print("================================\n")


# Global feature manager instance
feature_manager = FeatureManager()