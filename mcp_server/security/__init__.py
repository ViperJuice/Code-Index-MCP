"""Security package for authentication and authorization."""

from .auth_manager import (
    AuthenticationError,
    AuthManager,
    AuthorizationError,
    IAuthenticator,
    IAuthorizer,
    PasswordManager,
    RateLimiter,
    SecurityError,
)
from .models import (
    DEFAULT_ACCESS_RULES,
    DEFAULT_ROLE_PERMISSIONS,
    AccessLevel,
    AccessRequest,
    AccessRule,
    AuthCredentials,
    Permission,
    RateLimitInfo,
    RefreshTokenData,
    SecurityConfig,
    SecurityEvent,
    SessionInfo,
    TokenData,
    User,
    UserRole,
)
from .security_middleware import (
    AuthenticationMiddleware,
    AuthorizationMiddleware,
    RateLimitMiddleware,
    RequestValidationMiddleware,
    SecurityHeaders,
    SecurityHeadersMiddleware,
    SecurityMiddlewareStack,
    get_current_active_user,
    get_current_user,
    require_permission,
    require_role,
)

__all__ = [
    # Models
    "User",
    "UserRole",
    "Permission",
    "TokenData",
    "AuthCredentials",
    "RefreshTokenData",
    "AccessRequest",
    "AccessRule",
    "SecurityConfig",
    "SecurityEvent",
    "RateLimitInfo",
    "SessionInfo",
    "AccessLevel",
    "DEFAULT_ROLE_PERMISSIONS",
    "DEFAULT_ACCESS_RULES",
    # Auth Manager
    "AuthManager",
    "IAuthenticator",
    "IAuthorizer",
    "PasswordManager",
    "RateLimiter",
    "AuthenticationError",
    "AuthorizationError",
    "SecurityError",
    # Middleware
    "SecurityHeaders",
    "RateLimitMiddleware",
    "SecurityHeadersMiddleware",
    "AuthenticationMiddleware",
    "AuthorizationMiddleware",
    "RequestValidationMiddleware",
    "SecurityMiddlewareStack",
    "get_current_user",
    "get_current_active_user",
    "require_permission",
    "require_role",
]

# Version information
__version__ = "1.0.0"
__author__ = "Code Index MCP"
__description__ = "Security layer with authentication and authorization capabilities"
