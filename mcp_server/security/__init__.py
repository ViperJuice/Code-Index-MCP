"""Security package for authentication and authorization."""

from .models import (
    User, UserRole, Permission, TokenData, AuthCredentials, RefreshTokenData,
    AccessRequest, AccessRule, SecurityConfig, SecurityEvent, RateLimitInfo,
    SessionInfo, AccessLevel, DEFAULT_ROLE_PERMISSIONS, DEFAULT_ACCESS_RULES
)

from .auth_manager import (
    AuthManager, IAuthenticator, IAuthorizer, PasswordManager, RateLimiter,
    AuthenticationError, AuthorizationError, SecurityError
)

# Security middleware has been moved to production module
# from .security_middleware import (...)

__all__ = [
    # Models
    "User", "UserRole", "Permission", "TokenData", "AuthCredentials", "RefreshTokenData",
    "AccessRequest", "AccessRule", "SecurityConfig", "SecurityEvent", "RateLimitInfo",
    "SessionInfo", "AccessLevel", "DEFAULT_ROLE_PERMISSIONS", "DEFAULT_ACCESS_RULES",
    
    # Auth Manager
    "AuthManager", "IAuthenticator", "IAuthorizer", "PasswordManager", "RateLimiter",
    "AuthenticationError", "AuthorizationError", "SecurityError"
    
    # Note: Middleware components have been moved to mcp_server.production.middleware
]

# Version information
__version__ = "1.0.0"
__author__ = "Code Index MCP"
__description__ = "Security layer with authentication and authorization capabilities"