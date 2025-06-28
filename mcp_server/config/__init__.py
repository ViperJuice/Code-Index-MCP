"""
Production configuration management for MCP Server.

This module provides environment-specific configuration management
with validation, security, and production best practices.
"""

from .environment import (
    Environment,
    get_environment,
    is_production,
    is_development,
    is_testing,
)

from .settings import (
    Settings,
    DatabaseSettings,
    SecuritySettings,
    CacheSettings,
    MetricsSettings,
    LoggingSettings,
    get_settings,
)

from .validation import (
    validate_production_config,
    validate_security_config,
    ConfigurationError,
    SecurityConfigurationError,
)

__all__ = [
    # Environment management
    "Environment",
    "get_environment",
    "is_production",
    "is_development",
    "is_testing",
    # Settings
    "Settings",
    "DatabaseSettings",
    "SecuritySettings",
    "CacheSettings",
    "MetricsSettings",
    "LoggingSettings",
    "get_settings",
    # Validation
    "validate_production_config",
    "validate_security_config",
    "ConfigurationError",
    "SecurityConfigurationError",
]

__version__ = "1.0.0"
__description__ = "Production configuration management for MCP Server"
