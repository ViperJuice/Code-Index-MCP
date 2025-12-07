"""Authentication and authorization manager."""

import fnmatch
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import jwt
from passlib.context import CryptContext

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


class AuthenticationError(Exception):
    """Authentication related errors."""


class AuthorizationError(Exception):
    """Authorization related errors."""


class SecurityError(Exception):
    """General security related errors."""


class IAuthenticator:
    """Interface for authentication services."""

    async def authenticate_user(self, credentials: AuthCredentials) -> Optional[User]:
        """Authenticate user with credentials."""
        raise NotImplementedError

    async def create_access_token(self, user: User) -> str:
        """Create JWT access token for user."""
        raise NotImplementedError

    async def create_refresh_token(self, user: User) -> str:
        """Create refresh token for user."""
        raise NotImplementedError

    async def verify_token(self, token: str) -> Optional[TokenData]:
        """Verify and decode JWT token."""
        raise NotImplementedError

    async def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """Refresh access token using refresh token."""
        raise NotImplementedError


class IAuthorizer:
    """Interface for authorization services."""

    async def authorize_request(self, request: AccessRequest) -> bool:
        """Authorize user request based on path and operation."""
        raise NotImplementedError

    async def check_permission(self, user: User, permission: Permission) -> bool:
        """Check if user has specific permission."""
        raise NotImplementedError

    async def check_role(self, user: User, required_role: UserRole) -> bool:
        """Check if user has required role or higher."""
        raise NotImplementedError


class PasswordManager:
    """Password hashing and verification utilities."""

    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt."""
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash."""
        return self.pwd_context.verify(plain_password, hashed_password)

    def is_strong_password(self, password: str, min_length: int = 8) -> bool:
        """Check if password meets strength requirements."""
        if len(password) < min_length:
            return False

        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)

        return sum([has_upper, has_lower, has_digit, has_special]) >= 3


class RateLimiter:
    """Rate limiting for security protection."""

    def __init__(self, max_requests: int = 100, window_minutes: int = 1):
        self.max_requests = max_requests
        self.window_minutes = window_minutes
        self.rate_limits: Dict[str, RateLimitInfo] = {}

    def is_rate_limited(self, identifier: str) -> bool:
        """Check if identifier is rate limited."""
        now = datetime.utcnow()

        if identifier not in self.rate_limits:
            self.rate_limits[identifier] = RateLimitInfo(identifier=identifier)
            return False

        rate_limit = self.rate_limits[identifier]

        # Check if currently blocked
        if rate_limit.is_blocked and rate_limit.blocked_until:
            if now < rate_limit.blocked_until:
                return True
            else:
                # Unblock and reset
                rate_limit.is_blocked = False
                rate_limit.blocked_until = None
                rate_limit.requests_count = 0
                rate_limit.window_start = now

        # Check if window has expired
        window_end = rate_limit.window_start + timedelta(minutes=self.window_minutes)
        if now > window_end:
            rate_limit.requests_count = 0
            rate_limit.window_start = now

        # Check rate limit
        if rate_limit.requests_count >= self.max_requests:
            rate_limit.is_blocked = True
            rate_limit.blocked_until = now + timedelta(minutes=self.window_minutes)
            return True

        rate_limit.requests_count += 1
        return False


class AuthManager(IAuthenticator, IAuthorizer):
    """Main authentication and authorization manager."""

    def __init__(self, config: SecurityConfig):
        self.config = config
        self.password_manager = PasswordManager()
        self.rate_limiter = RateLimiter(
            max_requests=config.rate_limit_requests,
            window_minutes=config.rate_limit_window_minutes,
        )

        # In-memory storage (replace with database in production)
        self.users: Dict[str, User] = {}
        self.refresh_tokens: Dict[str, RefreshTokenData] = {}
        self.access_rules: List[AccessRule] = DEFAULT_ACCESS_RULES.copy()
        self.security_events: List[SecurityEvent] = []
        self.sessions: Dict[str, SessionInfo] = {}
        self.failed_attempts: Dict[str, int] = {}
        self.lockouts: Dict[str, datetime] = {}

    # User Management

    async def create_user(
        self,
        username: str,
        password: str,
        email: Optional[str] = None,
        role: UserRole = UserRole.USER,
    ) -> User:
        """Create a new user."""
        if not self.password_manager.is_strong_password(password, self.config.password_min_length):
            raise SecurityError("Password does not meet strength requirements")

        if any(u.username == username for u in self.users.values()):
            raise SecurityError("Username already exists")

        if email and any(u.email == email for u in self.users.values() if u.email):
            raise SecurityError("Email already exists")

        user = User(
            username=username,
            email=email,
            hashed_password=self.password_manager.hash_password(password),
            role=role,
            permissions=DEFAULT_ROLE_PERMISSIONS.get(role, []),
        )

        self.users[user.id] = user
        await self._log_security_event("user_created", user_id=user.id, username=username)
        return user

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        return next((u for u in self.users.values() if u.username == username), None)

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return self.users.get(user_id)

    # Authentication

    async def authenticate_user(self, credentials: AuthCredentials) -> Optional[User]:
        """Authenticate user with credentials."""
        username = credentials.username

        # Check rate limiting
        if self.rate_limiter.is_rate_limited(username):
            await self._log_security_event("authentication_rate_limited", username=username)
            raise AuthenticationError("Rate limit exceeded")

        # Check account lockout
        if username in self.lockouts:
            if datetime.utcnow() < self.lockouts[username]:
                await self._log_security_event("authentication_locked_out", username=username)
                raise AuthenticationError("Account is locked")
            else:
                del self.lockouts[username]
                self.failed_attempts.pop(username, None)

        user = await self.get_user_by_username(username)
        if not user:
            await self._increment_failed_attempts(username)
            await self._log_security_event(
                "authentication_failed",
                username=username,
                details={"reason": "user_not_found"},
            )
            raise AuthenticationError("Invalid credentials")

        if not user.is_active:
            await self._log_security_event(
                "authentication_failed",
                username=username,
                details={"reason": "user_inactive"},
            )
            raise AuthenticationError("Account is inactive")

        if not self.password_manager.verify_password(credentials.password, user.hashed_password):
            await self._increment_failed_attempts(username)
            await self._log_security_event(
                "authentication_failed",
                username=username,
                details={"reason": "invalid_password"},
            )
            raise AuthenticationError("Invalid credentials")

        # Reset failed attempts on successful login
        self.failed_attempts.pop(username, None)
        user.last_login = datetime.utcnow()
        await self._log_security_event("authentication_success", user_id=user.id, username=username)

        return user

    async def _increment_failed_attempts(self, username: str):
        """Increment failed login attempts and apply lockout if needed."""
        self.failed_attempts[username] = self.failed_attempts.get(username, 0) + 1

        if self.failed_attempts[username] >= self.config.max_login_attempts:
            lockout_until = datetime.utcnow() + timedelta(
                minutes=self.config.lockout_duration_minutes
            )
            self.lockouts[username] = lockout_until
            await self._log_security_event(
                "account_locked",
                username=username,
                details={"lockout_until": lockout_until.isoformat()},
            )

    async def create_access_token(self, user: User) -> str:
        """Create JWT access token for user."""
        now = datetime.utcnow()
        expires_at = now + timedelta(minutes=self.config.access_token_expire_minutes)

        token_data = TokenData(
            user_id=user.id,
            username=user.username,
            role=user.role,
            permissions=user.permissions,
            issued_at=now,
            expires_at=expires_at,
        )

        payload = {
            "user_id": token_data.user_id,
            "username": token_data.username,
            "role": token_data.role.value,
            "permissions": [p.value for p in token_data.permissions],
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
            "type": "access",
        }

        token = jwt.encode(payload, self.config.jwt_secret_key, algorithm=self.config.jwt_algorithm)
        await self._log_security_event(
            "access_token_created", user_id=user.id, username=user.username
        )
        return token

    async def create_refresh_token(self, user: User) -> str:
        """Create refresh token for user."""
        now = datetime.utcnow()
        expires_at = now + timedelta(days=self.config.refresh_token_expire_days)

        refresh_data = RefreshTokenData(user_id=user.id, issued_at=now, expires_at=expires_at)

        self.refresh_tokens[refresh_data.token_id] = refresh_data

        payload = {
            "token_id": refresh_data.token_id,
            "user_id": refresh_data.user_id,
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
            "type": "refresh",
        }

        token = jwt.encode(payload, self.config.jwt_secret_key, algorithm=self.config.jwt_algorithm)
        await self._log_security_event(
            "refresh_token_created", user_id=user.id, username=user.username
        )
        return token

    async def verify_token(self, token: str) -> Optional[TokenData]:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(
                token,
                self.config.jwt_secret_key,
                algorithms=[self.config.jwt_algorithm],
            )

            if payload.get("type") != "access":
                return None

            user_id = payload.get("user_id")
            if not user_id:
                return None

            user = await self.get_user_by_id(user_id)
            if not user or not user.is_active:
                return None

            return TokenData(
                user_id=payload["user_id"],
                username=payload["username"],
                role=UserRole(payload["role"]),
                permissions=[Permission(p) for p in payload["permissions"]],
                issued_at=datetime.fromtimestamp(payload["iat"]),
                expires_at=datetime.fromtimestamp(payload["exp"]),
            )

        except jwt.ExpiredSignatureError:
            await self._log_security_event("token_expired", details={"token_type": "access"})
            return None
        except jwt.InvalidTokenError:
            await self._log_security_event("token_invalid", details={"token_type": "access"})
            return None

    async def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """Refresh access token using refresh token."""
        try:
            payload = jwt.decode(
                refresh_token,
                self.config.jwt_secret_key,
                algorithms=[self.config.jwt_algorithm],
            )

            if payload.get("type") != "refresh":
                return None

            token_id = payload.get("token_id")
            if not token_id or token_id not in self.refresh_tokens:
                return None

            refresh_data = self.refresh_tokens[token_id]
            if refresh_data.is_revoked or datetime.utcnow() > refresh_data.expires_at:
                return None

            user = await self.get_user_by_id(refresh_data.user_id)
            if not user or not user.is_active:
                return None

            new_access_token = await self.create_access_token(user)
            await self._log_security_event(
                "token_refreshed", user_id=user.id, username=user.username
            )
            return new_access_token

        except jwt.ExpiredSignatureError:
            await self._log_security_event("token_expired", details={"token_type": "refresh"})
            return None
        except jwt.InvalidTokenError:
            await self._log_security_event("token_invalid", details={"token_type": "refresh"})
            return None

    async def revoke_refresh_token(self, refresh_token: str) -> bool:
        """Revoke refresh token."""
        try:
            payload = jwt.decode(
                refresh_token,
                self.config.jwt_secret_key,
                algorithms=[self.config.jwt_algorithm],
            )
            token_id = payload.get("token_id")

            if token_id and token_id in self.refresh_tokens:
                self.refresh_tokens[token_id].is_revoked = True
                await self._log_security_event(
                    "refresh_token_revoked", details={"token_id": token_id}
                )
                return True

        except jwt.InvalidTokenError:
            pass

        return False

    # Authorization

    async def authorize_request(self, request: AccessRequest) -> bool:
        """Authorize user request based on path and operation."""
        user = await self.get_user_by_id(request.user_id)
        if not user or not user.is_active:
            return False

        # Find matching access rule
        matching_rule = self._find_matching_rule(request.path)
        if not matching_rule:
            # Default deny if no rule matches
            return False

        # Check access level
        if matching_rule.access_level == AccessLevel.PUBLIC:
            return request.operation in matching_rule.allowed_operations

        # Check role requirement
        if matching_rule.required_role:
            if not await self.check_role(user, matching_rule.required_role):
                return False

        # Check permission requirements
        for required_permission in matching_rule.required_permissions:
            if not await self.check_permission(user, required_permission):
                return False

        # Check if operation is allowed
        return request.operation in matching_rule.allowed_operations

    def _find_matching_rule(self, path: str) -> Optional[AccessRule]:
        """Find the most specific matching access rule for a path."""
        matching_rules = []

        for rule in self.access_rules:
            if fnmatch.fnmatch(path, rule.path_pattern):
                matching_rules.append(rule)

        if not matching_rules:
            return None

        # Return the most specific rule (longest pattern)
        return max(matching_rules, key=lambda r: len(r.path_pattern))

    async def check_permission(self, user: User, permission: Permission) -> bool:
        """Check if user has specific permission."""
        return permission in user.permissions

    async def check_role(self, user: User, required_role: UserRole) -> bool:
        """Check if user has required role or higher."""
        role_hierarchy = [
            UserRole.GUEST,
            UserRole.READONLY,
            UserRole.USER,
            UserRole.ADMIN,
        ]

        try:
            user_level = role_hierarchy.index(user.role)
            required_level = role_hierarchy.index(required_role)
            return user_level >= required_level
        except ValueError:
            return False

    # Access Rules Management

    async def add_access_rule(self, rule: AccessRule):
        """Add a new access rule."""
        self.access_rules.append(rule)
        await self._log_security_event(
            "access_rule_added",
            details={"rule_id": rule.id, "pattern": rule.path_pattern},
        )

    async def remove_access_rule(self, rule_id: str) -> bool:
        """Remove an access rule."""
        for i, rule in enumerate(self.access_rules):
            if rule.id == rule_id:
                removed_rule = self.access_rules.pop(i)
                await self._log_security_event(
                    "access_rule_removed",
                    details={"rule_id": rule_id, "pattern": removed_rule.path_pattern},
                )
                return True
        return False

    # Security Event Logging

    async def _log_security_event(
        self,
        event_type: str,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        severity: str = "info",
    ):
        """Log security event."""
        event = SecurityEvent(
            event_type=event_type,
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details or {},
            severity=severity,
        )
        self.security_events.append(event)

        # Keep only last 1000 events to prevent memory issues
        if len(self.security_events) > 1000:
            self.security_events = self.security_events[-1000:]

    async def get_security_events(self, limit: int = 100) -> List[SecurityEvent]:
        """Get recent security events."""
        return self.security_events[-limit:]
