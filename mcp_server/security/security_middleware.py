"""FastAPI security middleware for authentication and authorization."""

import logging
from typing import Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

from .auth_manager import (
    AuthManager,
)
from .models import (
    AccessRequest,
    Permission,
    SecurityConfig,
    TokenData,
    User,
    UserRole,
)

logger = logging.getLogger(__name__)


class SecurityHeaders:
    """Security headers configuration."""

    @staticmethod
    def get_default_headers() -> Dict[str, str]:
        """Get default security headers."""
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "X-Permitted-Cross-Domain-Policies": "none",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": "default-src 'self'",
            "X-Download-Options": "noopen",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        }


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware."""

    def __init__(self, app: FastAPI, auth_manager: AuthManager):
        super().__init__(app)
        self.auth_manager = auth_manager

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Process request with rate limiting."""
        client_ip = self._get_client_ip(request)

        # Check rate limiting
        if self.auth_manager.rate_limiter.is_rate_limited(client_ip):
            await self.auth_manager._log_security_event(
                "rate_limit_exceeded",
                ip_address=client_ip,
                user_agent=request.headers.get("user-agent"),
                severity="warning",
            )
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded. Please try again later."},
            )

        response = await call_next(request)
        return response

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check for forwarded headers first
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        # Fallback to client IP
        return request.client.host if request.client else "unknown"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Security headers middleware."""

    def __init__(self, app: FastAPI, security_headers: Optional[Dict[str, str]] = None):
        super().__init__(app)
        self.security_headers = security_headers or SecurityHeaders.get_default_headers()

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Add security headers to response."""
        response = await call_next(request)

        # Add security headers
        for header, value in self.security_headers.items():
            response.headers[header] = value

        return response


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Authentication middleware."""

    def __init__(
        self,
        app: FastAPI,
        auth_manager: AuthManager,
        excluded_paths: Optional[List[str]] = None,
    ):
        super().__init__(app)
        self.auth_manager = auth_manager
        self.excluded_paths = excluded_paths or [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/metrics",
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/refresh",
        ]

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Process request with authentication."""
        # Skip authentication for excluded paths
        if self._is_excluded_path(request.url.path):
            return await call_next(request)

        # Extract and verify token
        token = self._extract_token(request)
        if not token:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Missing authentication token"},
            )

        token_data = await self.auth_manager.verify_token(token)
        if not token_data:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid or expired token"},
            )

        # Add user info to request state
        request.state.user_id = token_data.user_id
        request.state.username = token_data.username
        request.state.user_role = token_data.role
        request.state.user_permissions = token_data.permissions
        request.state.token_data = token_data

        # Log authentication
        await self.auth_manager._log_security_event(
            "request_authenticated",
            user_id=token_data.user_id,
            username=token_data.username,
            ip_address=self._get_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )

        return await call_next(request)

    def _is_excluded_path(self, path: str) -> bool:
        """Check if path is excluded from authentication."""
        return any(path.startswith(excluded) for excluded in self.excluded_paths)

    def _extract_token(self, request: Request) -> Optional[str]:
        """Extract Bearer token from Authorization header."""
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return None

        if not auth_header.startswith("Bearer "):
            return None

        return auth_header[7:]  # Remove "Bearer " prefix

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        return request.client.host if request.client else "unknown"


class AuthorizationMiddleware(BaseHTTPMiddleware):
    """Authorization middleware."""

    def __init__(self, app: FastAPI, auth_manager: AuthManager):
        super().__init__(app)
        self.auth_manager = auth_manager

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Process request with authorization."""
        # Skip authorization if not authenticated
        if not hasattr(request.state, "user_id"):
            return await call_next(request)

        # Determine operation from HTTP method
        operation = self._get_operation_from_method(request.method)

        # Create access request
        access_request = AccessRequest(
            user_id=request.state.user_id,
            path=request.url.path,
            operation=operation,
            metadata={
                "method": request.method,
                "query_params": dict(request.query_params),
                "ip_address": self._get_client_ip(request),
                "user_agent": request.headers.get("user-agent"),
            },
        )

        # Check authorization
        is_authorized = await self.auth_manager.authorize_request(access_request)
        if not is_authorized:
            await self.auth_manager._log_security_event(
                "authorization_denied",
                user_id=request.state.user_id,
                username=request.state.username,
                ip_address=self._get_client_ip(request),
                details={
                    "path": request.url.path,
                    "method": request.method,
                    "operation": operation.value,
                },
                severity="warning",
            )
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Insufficient permissions"},
            )

        # Log successful authorization
        await self.auth_manager._log_security_event(
            "authorization_granted",
            user_id=request.state.user_id,
            username=request.state.username,
            ip_address=self._get_client_ip(request),
            details={
                "path": request.url.path,
                "method": request.method,
                "operation": operation.value,
            },
        )

        return await call_next(request)

    def _get_operation_from_method(self, method: str) -> Permission:
        """Map HTTP method to permission."""
        method_mapping = {
            "GET": Permission.READ,
            "HEAD": Permission.READ,
            "OPTIONS": Permission.READ,
            "POST": Permission.WRITE,
            "PUT": Permission.WRITE,
            "PATCH": Permission.WRITE,
            "DELETE": Permission.DELETE,
        }
        return method_mapping.get(method.upper(), Permission.READ)

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        return request.client.host if request.client else "unknown"


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """Request validation and sanitization middleware."""

    def __init__(self, app: FastAPI, max_request_size: int = 10 * 1024 * 1024):  # 10MB
        super().__init__(app)
        self.max_request_size = max_request_size

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Validate and sanitize incoming requests."""
        # Check request size
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_request_size:
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={"detail": "Request too large"},
            )

        # Validate content type for POST/PUT requests
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "")
            if not self._is_valid_content_type(content_type):
                return JSONResponse(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    content={"detail": "Unsupported media type"},
                )

        # Check for suspicious patterns in URL
        if self._has_suspicious_patterns(request.url.path):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "Invalid request format"},
            )

        return await call_next(request)

    def _is_valid_content_type(self, content_type: str) -> bool:
        """Check if content type is allowed."""
        allowed_types = [
            "application/json",
            "application/x-www-form-urlencoded",
            "multipart/form-data",
            "text/plain",
        ]
        return any(content_type.startswith(allowed) for allowed in allowed_types)

    def _has_suspicious_patterns(self, path: str) -> bool:
        """Check for suspicious patterns in URL path."""
        suspicious_patterns = [
            "../",
            "..\\",
            "..",
            "%2e%2e",
            "%2f",
            "%5c",
            "<script",
            "</script>",
            "javascript:",
            "vbscript:",
            "onload=",
            "onerror=",
            "onclick=",
            "onmouseover=",
        ]
        path_lower = path.lower()
        return any(pattern in path_lower for pattern in suspicious_patterns)


# Dependency functions for FastAPI


def get_current_user(request: Request) -> TokenData:
    """Get current user from request state."""
    if not hasattr(request.state, "token_data"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return request.state.token_data


def get_current_active_user(request: Request, auth_manager: AuthManager = Depends()) -> User:
    """Get current active user."""
    token_data = get_current_user(request)
    # In a real implementation, you'd fetch the user from the database
    # For now, we'll create a user object from token data
    user = User(
        id=token_data.user_id,
        username=token_data.username,
        hashed_password="",  # Not needed for verification
        role=token_data.role,
        permissions=token_data.permissions,
    )
    return user


def require_permission(permission: Permission):
    """Decorator to require specific permission."""

    def permission_checker(current_user: User = Depends(get_current_active_user)):
        if permission not in current_user.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission.value}' required",
            )
        return current_user

    return permission_checker


def require_role(role: UserRole):
    """Decorator to require specific role or higher."""

    def role_checker(current_user: User = Depends(get_current_active_user)):
        role_hierarchy = [
            UserRole.GUEST,
            UserRole.READONLY,
            UserRole.USER,
            UserRole.ADMIN,
        ]

        try:
            user_level = role_hierarchy.index(current_user.role)
            required_level = role_hierarchy.index(role)
            if user_level < required_level:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Role '{role.value}' or higher required",
                )
        except ValueError:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid role")

        return current_user

    return role_checker


class SecurityMiddlewareStack:
    """Complete security middleware stack for FastAPI applications."""

    def __init__(self, app: FastAPI, config: SecurityConfig, auth_manager: AuthManager):
        self.app = app
        self.config = config
        self.auth_manager = auth_manager

    def setup_middleware(self):
        """Set up all security middleware in the correct order."""
        # Add CORS middleware first
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.config.cors_origins,
            allow_credentials=True,
            allow_methods=self.config.cors_methods,
            allow_headers=self.config.cors_headers,
        )

        # Add security headers middleware
        self.app.add_middleware(
            SecurityHeadersMiddleware, security_headers=self.config.security_headers
        )

        # Add request validation middleware
        self.app.add_middleware(RequestValidationMiddleware)

        # Add rate limiting middleware
        self.app.add_middleware(RateLimitMiddleware, auth_manager=self.auth_manager)

        # Add authorization middleware
        self.app.add_middleware(AuthorizationMiddleware, auth_manager=self.auth_manager)

        # Add authentication middleware last (executes first)
        self.app.add_middleware(AuthenticationMiddleware, auth_manager=self.auth_manager)

    def add_security_routes(self):
        """Add security-related routes."""

        @self.app.post("/api/v1/auth/login")
        async def login(credentials: dict):
            """Login endpoint."""
            # This would be implemented in the gateway

        @self.app.post("/api/v1/auth/logout")
        async def logout(current_user: User = Depends(get_current_active_user)):
            """Logout endpoint."""
            # This would be implemented in the gateway

        @self.app.post("/api/v1/auth/refresh")
        async def refresh_token(refresh_token: str):
            """Refresh token endpoint."""
            # This would be implemented in the gateway

        @self.app.get("/api/v1/auth/me")
        async def get_current_user_info(
            current_user: User = Depends(get_current_active_user),
        ):
            """Get current user information."""
            return {
                "id": current_user.id,
                "username": current_user.username,
                "role": current_user.role,
                "permissions": current_user.permissions,
            }

        @self.app.get("/api/v1/security/events")
        async def get_security_events(
            limit: int = 100, current_user: User = Depends(require_role(UserRole.ADMIN))
        ):
            """Get security events (admin only)."""
            events = await self.auth_manager.get_security_events(limit)
            return {"events": events}
