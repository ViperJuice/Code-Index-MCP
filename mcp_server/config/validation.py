"""
Configuration validation for production deployments.
"""

import os
import secrets
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

from .environment import Environment, get_environment, is_production
from .settings import Settings


class ConfigurationError(Exception):
    """Base configuration error."""


class SecurityConfigurationError(ConfigurationError):
    """Security-specific configuration error."""


def validate_security_config(settings: Settings) -> List[str]:
    """
    Validate security configuration.

    Args:
        settings: Application settings to validate

    Returns:
        List[str]: List of validation warnings/errors

    Raises:
        SecurityConfigurationError: For critical security issues
    """
    errors = []
    warnings = []

    security = settings.security

    # JWT Secret Key validation
    if len(security.jwt_secret_key) < 32:
        errors.append("JWT secret key must be at least 32 characters long")

    if is_production():
        # Production-specific security checks

        # Check for weak JWT secret
        if security.jwt_secret_key in [
            "your-secret-key",
            "secret",
            "admin123!",
            "changeme",
        ]:
            errors.append("JWT secret key appears to be a default/weak value")

        # Check token expiration times
        if security.access_token_expire_minutes > 60:
            warnings.append("Access token expiration > 60 minutes may be too long for production")

        if security.refresh_token_expire_days > 30:
            warnings.append("Refresh token expiration > 30 days may be too long for production")

        # CORS validation
        if "*" in security.cors_allowed_origins:
            errors.append("CORS wildcard (*) not allowed in production")

        # Rate limiting validation
        if not security.rate_limit_enabled:
            warnings.append("Rate limiting is disabled in production")
        elif security.rate_limit_requests > 1000:
            warnings.append("Rate limit may be too high for production (>1000 req/hour)")

        # Admin settings validation
        if security.default_admin_email == "admin@localhost":
            errors.append("Default admin email must be changed from localhost in production")

    # Password policy validation
    if not any(
        [
            security.password_require_uppercase,
            security.password_require_lowercase,
            security.password_require_numbers,
            security.password_require_special,
        ]
    ):
        warnings.append("Password policy is very weak - no character requirements")

    if security.password_min_length < 8:
        warnings.append("Password minimum length < 8 characters is weak")

    # Combine and check for critical errors
    all_issues = errors + warnings

    if errors and is_production():
        raise SecurityConfigurationError(
            f"Critical security configuration errors: {'; '.join(errors)}"
        )

    return all_issues


def validate_database_config(settings: Settings) -> List[str]:
    """
    Validate database configuration.

    Args:
        settings: Application settings to validate

    Returns:
        List[str]: List of validation warnings/errors
    """
    issues = []
    db = settings.database

    # Parse database URL
    try:
        parsed = urlparse(db.url)
    except Exception as e:
        issues.append(f"Invalid database URL: {e}")
        return issues

    # Production database validation
    if is_production():
        if parsed.scheme == "sqlite":
            issues.append("SQLite not recommended for production - use PostgreSQL")

        if parsed.scheme == "postgresql":
            # PostgreSQL production checks
            if not parsed.password or len(parsed.password) < 12:
                issues.append("Database password should be at least 12 characters for production")

            if parsed.hostname in ["localhost", "127.0.0.1"]:
                issues.append("Database host should not be localhost in production")

        # Connection pool validation
        if db.pool_size < 5:
            issues.append("Database pool size < 5 may be too small for production")
        elif db.pool_size > 50:
            issues.append("Database pool size > 50 may be excessive")

    return issues


def validate_cache_config(settings: Settings) -> List[str]:
    """
    Validate cache configuration.

    Args:
        settings: Application settings to validate

    Returns:
        List[str]: List of validation warnings/errors
    """
    issues = []
    cache = settings.cache

    if is_production():
        if not cache.redis_url:
            issues.append("Redis cache recommended for production environments")
        else:
            # Redis URL validation
            try:
                parsed = urlparse(cache.redis_url)
                if parsed.hostname in ["localhost", "127.0.0.1"]:
                    issues.append("Redis host should not be localhost in production")
            except Exception as e:
                issues.append(f"Invalid Redis URL: {e}")

        # TTL validation
        if cache.default_ttl < 300:
            issues.append("Cache TTL < 5 minutes may cause excessive database load")
        elif cache.default_ttl > 86400:
            issues.append("Cache TTL > 24 hours may cause stale data issues")

    return issues


def validate_logging_config(settings: Settings) -> List[str]:
    """
    Validate logging configuration.

    Args:
        settings: Application settings to validate

    Returns:
        List[str]: List of validation warnings/errors
    """
    issues = []
    logging = settings.logging

    if is_production():
        # Production logging checks
        if logging.level == "DEBUG":
            issues.append("DEBUG logging level not recommended for production")

        if not logging.json_format:
            issues.append("JSON logging format recommended for production")

        if logging.log_request_body or logging.log_response_body:
            issues.append("Request/response body logging may expose sensitive data")

        if logging.log_file:
            # Check log file path
            log_path = Path(logging.log_file)
            if not log_path.parent.exists():
                issues.append(f"Log directory does not exist: {log_path.parent}")

            # Check permissions (if file exists)
            if log_path.exists():
                try:
                    with open(log_path, "a"):
                        pass
                except PermissionError:
                    issues.append(f"Cannot write to log file: {log_path}")

    return issues


def validate_environment_variables() -> List[str]:
    """
    Validate critical environment variables are set.

    Returns:
        List[str]: List of missing or invalid environment variables
    """
    issues = []
    env = get_environment()

    # Critical environment variables for production
    if env == Environment.PRODUCTION:
        required_vars = ["DATABASE_URL", "JWT_SECRET_KEY", "DEFAULT_ADMIN_EMAIL"]

        for var in required_vars:
            if not os.getenv(var):
                issues.append(f"Required environment variable not set: {var}")

        # Check for default/insecure values
        insecure_vars = {
            "JWT_SECRET_KEY": ["your-secret-key", "secret", "changeme"],
            "DEFAULT_ADMIN_PASSWORD": ["admin", "password", "admin123!"],
        }

        for var, insecure_values in insecure_vars.items():
            value = os.getenv(var, "")
            if value in insecure_values:
                issues.append(f"Environment variable {var} has insecure default value")

    return issues


def validate_production_config(
    settings: Optional[Settings] = None,
) -> Dict[str, List[str]]:
    """
    Comprehensive production configuration validation.

    Args:
        settings: Settings to validate (defaults to current settings)

    Returns:
        Dict[str, List[str]]: Validation results by category

    Raises:
        SecurityConfigurationError: For critical security issues
    """
    if settings is None:
        from .settings import get_settings

        settings = get_settings()

    results = {
        "security": validate_security_config(settings),
        "database": validate_database_config(settings),
        "cache": validate_cache_config(settings),
        "logging": validate_logging_config(settings),
        "environment": validate_environment_variables(),
    }

    # Count total issues
    total_issues = sum(len(issues) for issues in results.values())

    if total_issues > 0 and is_production():
        # Log summary for production
        print("\n🔍 Configuration Validation Summary:")
        print(f"Total issues found: {total_issues}")

        for category, issues in results.items():
            if issues:
                print(f"\n{category.upper()} Issues ({len(issues)}):")
                for issue in issues:
                    print(f"  - {issue}")

    return results


def generate_secure_defaults() -> Dict[str, str]:
    """
    Generate secure default values for configuration.

    Returns:
        Dict[str, str]: Secure default environment variables
    """
    return {
        "JWT_SECRET_KEY": secrets.token_urlsafe(32),
        "DEFAULT_ADMIN_PASSWORD": secrets.token_urlsafe(16),
        "CACHE_SECRET_KEY": secrets.token_urlsafe(16),
    }


def create_env_template(environment: Environment) -> str:
    """
    Create environment variable template for specific environment.

    Args:
        environment: Target environment

    Returns:
        str: Environment variable template content
    """
    secure_defaults = generate_secure_defaults()

    if environment == Environment.PRODUCTION:
        return f"""# Production Environment Configuration
# DO NOT commit this file with real values!

# Environment
MCP_ENVIRONMENT=production

# Database (Required)
DATABASE_URL=postgresql://mcp_user:secure_password@db-host:5432/mcp_production

# Security (Required)
JWT_SECRET_KEY={secure_defaults['JWT_SECRET_KEY']}
DEFAULT_ADMIN_EMAIL=admin@yourdomain.com
DEFAULT_ADMIN_PASSWORD={secure_defaults['DEFAULT_ADMIN_PASSWORD']}

# Cache (Required for production)
REDIS_URL=redis://redis-host:6379

# Server
HOST=0.0.0.0
PORT=8000
WORKERS=4

# CORS (Specify your domain)
CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://api.yourdomain.com

# Rate Limiting
RATE_LIMIT_REQUESTS=60
RATE_LIMIT_WINDOW=3600

# Logging
LOG_LEVEL=INFO
LOG_FILE=PathUtils.get_log_path()/app.log
LOG_JSON_FORMAT=true

# Monitoring
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=8001

# Features
DYNAMIC_PLUGIN_LOADING=true
SEMANTIC_SEARCH_ENABLED=false
"""

    elif environment == Environment.STAGING:
        return f"""# Staging Environment Configuration

# Environment
MCP_ENVIRONMENT=staging

# Database
DATABASE_URL=postgresql://mcp_user:staging_password@staging-db:5432/mcp_staging

# Security
JWT_SECRET_KEY={secure_defaults['JWT_SECRET_KEY']}
DEFAULT_ADMIN_EMAIL=admin@staging.yourdomain.com
DEFAULT_ADMIN_PASSWORD={secure_defaults['DEFAULT_ADMIN_PASSWORD']}

# Cache
REDIS_URL=redis://staging-redis:6379

# Server
HOST=0.0.0.0
PORT=8000
WORKERS=2

# CORS
CORS_ALLOWED_ORIGINS=https://staging.yourdomain.com

# Logging
LOG_LEVEL=DEBUG
LOG_JSON_FORMAT=true

# Monitoring
PROMETHEUS_ENABLED=true
"""

    else:  # Development
        return f"""# Development Environment Configuration

# Environment
MCP_ENVIRONMENT=development

# Database (SQLite for development)
DATABASE_URL=sqlite:///./dev_code_index.db

# Security
JWT_SECRET_KEY={secure_defaults['JWT_SECRET_KEY']}
DEFAULT_ADMIN_EMAIL=admin@localhost
DEFAULT_ADMIN_PASSWORD=admin123!

# Cache (Optional Redis)
# REDIS_URL=redis://localhost:6379

# Server
HOST=127.0.0.1
PORT=8000
DEBUG=true

# CORS (Allow all for development)
CORS_ALLOWED_ORIGINS=*

# Logging
LOG_LEVEL=DEBUG
LOG_JSON_FORMAT=false

# Monitoring
PROMETHEUS_ENABLED=true

# Features
DYNAMIC_PLUGIN_LOADING=true
SEMANTIC_SEARCH_ENABLED=true
"""
