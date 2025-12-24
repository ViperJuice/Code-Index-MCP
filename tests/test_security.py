"""Comprehensive tests for the security layer."""

import asyncio
from datetime import datetime, timedelta

import jwt
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from mcp_server.security import (
    AccessLevel,
    AccessRequest,
    AccessRule,
    AuthCredentials,
    AuthenticationError,
    AuthManager,
    PasswordManager,
    Permission,
    RateLimiter,
    SecurityConfig,
    SecurityError,
    UserRole,
)
from mcp_server.security.security_middleware import (
    RequestValidationMiddleware,
    SecurityHeadersMiddleware,
)


@pytest.fixture
def security_config():
    """Create test security configuration."""
    return SecurityConfig(
        jwt_secret_key="test-secret-key-at-least-32-characters-long",
        jwt_algorithm="HS256",
        access_token_expire_minutes=30,
        refresh_token_expire_days=7,
        password_min_length=8,
        max_login_attempts=3,
        lockout_duration_minutes=5,
        rate_limit_requests=10,
        rate_limit_window_minutes=1,
    )


@pytest.fixture
def auth_manager(security_config):
    """Create test authentication manager."""
    return AuthManager(security_config)


@pytest.fixture
async def test_user(auth_manager):
    """Create a test user."""
    return await auth_manager.create_user(
        username="testuser",
        password="testpass123!",
        email="test@example.com",
        role=UserRole.USER,
    )


@pytest.fixture
async def admin_user(auth_manager):
    """Create an admin user."""
    return await auth_manager.create_user(
        username="admin",
        password="adminpass123!",
        email="admin@example.com",
        role=UserRole.ADMIN,
    )


class TestSecurityConfig:
    """Test security configuration validation."""

    def test_valid_config(self):
        """Test valid security configuration."""
        config = SecurityConfig(jwt_secret_key="test-secret-key-at-least-32-characters-long")
        assert config.jwt_secret_key == "test-secret-key-at-least-32-characters-long"
        assert config.jwt_algorithm == "HS256"
        assert config.access_token_expire_minutes == 30

    def test_invalid_secret_key(self):
        """Test invalid JWT secret key."""
        with pytest.raises(ValueError, match="JWT secret key must be at least 32 characters long"):
            SecurityConfig(jwt_secret_key="short")

    def test_invalid_token_expire_time(self):
        """Test invalid token expiration time."""
        with pytest.raises(ValueError, match="Access token expire minutes must be positive"):
            SecurityConfig(
                jwt_secret_key="test-secret-key-at-least-32-characters-long",
                access_token_expire_minutes=0,
            )


class TestPasswordManager:
    """Test password management functionality."""

    def test_hash_and_verify_password(self):
        """Test password hashing and verification."""
        pwd_manager = PasswordManager()
        password = "testpassword123!"

        hashed = pwd_manager.hash_password(password)
        assert hashed != password
        assert pwd_manager.verify_password(password, hashed)
        assert not pwd_manager.verify_password("wrongpassword", hashed)

    def test_password_strength_validation(self):
        """Test password strength validation."""
        pwd_manager = PasswordManager()

        # Strong password
        assert pwd_manager.is_strong_password("StrongPass123!")

        # Weak passwords
        assert not pwd_manager.is_strong_password("short")
        assert not pwd_manager.is_strong_password("alllowercase")
        assert not pwd_manager.is_strong_password("ALLUPPERCASE")
        assert not pwd_manager.is_strong_password("12345678")


class TestRateLimiter:
    """Test rate limiting functionality."""

    def test_rate_limiting(self):
        """Test basic rate limiting."""
        rate_limiter = RateLimiter(max_requests=3, window_minutes=1)

        # First 3 requests should pass
        for i in range(3):
            assert not rate_limiter.is_rate_limited("test_client")

        # 4th request should be blocked
        assert rate_limiter.is_rate_limited("test_client")

    def test_rate_limit_window_reset(self):
        """Test rate limit window reset."""
        rate_limiter = RateLimiter(max_requests=2, window_minutes=1)

        # Use up the rate limit
        assert not rate_limiter.is_rate_limited("test_client")
        assert not rate_limiter.is_rate_limited("test_client")
        assert rate_limiter.is_rate_limited("test_client")

        # Manually reset the window by updating the start time
        rate_limit_info = rate_limiter.rate_limits["test_client"]
        rate_limit_info.window_start = datetime.utcnow() - timedelta(minutes=2)

        # Should work again
        assert not rate_limiter.is_rate_limited("test_client")


class TestAuthManager:
    """Test authentication manager functionality."""

    @pytest.mark.asyncio
    async def test_create_user(self, auth_manager):
        """Test user creation."""
        user = await auth_manager.create_user(
            username="newuser", password="newpass123!", email="new@example.com"
        )

        assert user.username == "newuser"
        assert user.email == "new@example.com"
        assert user.role == UserRole.USER
        assert user.is_active
        assert Permission.READ in user.permissions

    @pytest.mark.asyncio
    async def test_create_user_duplicate_username(self, auth_manager):
        """Test duplicate username error."""
        await auth_manager.create_user("duplicate", "pass123!", "test1@example.com")

        with pytest.raises(SecurityError, match="Username already exists"):
            await auth_manager.create_user("duplicate", "pass123!", "test2@example.com")

    @pytest.mark.asyncio
    async def test_create_user_weak_password(self, auth_manager):
        """Test weak password rejection."""
        with pytest.raises(SecurityError, match="Password does not meet strength requirements"):
            await auth_manager.create_user("user", "weak", "test@example.com")

    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, auth_manager, test_user):
        """Test successful user authentication."""
        credentials = AuthCredentials(username="testuser", password="testpass123!")
        authenticated_user = await auth_manager.authenticate_user(credentials)

        assert authenticated_user is not None
        assert authenticated_user.username == "testuser"

    @pytest.mark.asyncio
    async def test_authenticate_user_invalid_credentials(self, auth_manager, test_user):
        """Test authentication with invalid credentials."""
        credentials = AuthCredentials(username="testuser", password="wrongpassword")

        with pytest.raises(AuthenticationError, match="Invalid credentials"):
            await auth_manager.authenticate_user(credentials)

    @pytest.mark.asyncio
    async def test_authenticate_user_nonexistent(self, auth_manager):
        """Test authentication with nonexistent user."""
        credentials = AuthCredentials(username="nonexistent", password="password")

        with pytest.raises(AuthenticationError, match="Invalid credentials"):
            await auth_manager.authenticate_user(credentials)

    @pytest.mark.asyncio
    async def test_failed_login_lockout(self, auth_manager, test_user):
        """Test account lockout after failed attempts."""
        credentials = AuthCredentials(username="testuser", password="wrongpassword")

        # Exceed max login attempts
        for _ in range(auth_manager.config.max_login_attempts):
            with pytest.raises(AuthenticationError):
                await auth_manager.authenticate_user(credentials)

        # Next attempt should be locked out
        with pytest.raises(AuthenticationError, match="Account is locked"):
            await auth_manager.authenticate_user(credentials)

    @pytest.mark.asyncio
    async def test_create_access_token(self, auth_manager, test_user):
        """Test access token creation."""
        token = await auth_manager.create_access_token(test_user)

        assert isinstance(token, str)
        assert len(token) > 0

        # Verify token content
        payload = jwt.decode(
            token,
            auth_manager.config.jwt_secret_key,
            algorithms=[auth_manager.config.jwt_algorithm],
        )
        assert payload["user_id"] == test_user.id
        assert payload["username"] == test_user.username
        assert payload["type"] == "access"

    @pytest.mark.asyncio
    async def test_verify_token(self, auth_manager, test_user):
        """Test token verification."""
        token = await auth_manager.create_access_token(test_user)
        token_data = await auth_manager.verify_token(token)

        assert token_data is not None
        assert token_data.user_id == test_user.id
        assert token_data.username == test_user.username
        assert token_data.role == test_user.role

    @pytest.mark.asyncio
    async def test_verify_invalid_token(self, auth_manager):
        """Test verification of invalid token."""
        token_data = await auth_manager.verify_token("invalid.token.here")
        assert token_data is None

    @pytest.mark.asyncio
    async def test_refresh_token_flow(self, auth_manager, test_user):
        """Test refresh token creation and usage."""
        refresh_token = await auth_manager.create_refresh_token(test_user)
        new_access_token = await auth_manager.refresh_access_token(refresh_token)

        assert new_access_token is not None
        assert isinstance(new_access_token, str)

        # Verify new token works
        token_data = await auth_manager.verify_token(new_access_token)
        assert token_data.user_id == test_user.id

    @pytest.mark.asyncio
    async def test_revoke_refresh_token(self, auth_manager, test_user):
        """Test refresh token revocation."""
        refresh_token = await auth_manager.create_refresh_token(test_user)

        # Revoke the token
        success = await auth_manager.revoke_refresh_token(refresh_token)
        assert success

        # Should not be able to use revoked token
        new_access_token = await auth_manager.refresh_access_token(refresh_token)
        assert new_access_token is None

    @pytest.mark.asyncio
    async def test_check_permission(self, auth_manager, test_user, admin_user):
        """Test permission checking."""
        # Regular user should have read permission
        assert await auth_manager.check_permission(test_user, Permission.READ)

        # Regular user should not have admin permission
        assert not await auth_manager.check_permission(test_user, Permission.ADMIN)

        # Admin user should have admin permission
        assert await auth_manager.check_permission(admin_user, Permission.ADMIN)

    @pytest.mark.asyncio
    async def test_check_role(self, auth_manager, test_user, admin_user):
        """Test role checking."""
        # User should have user role or lower
        assert await auth_manager.check_role(test_user, UserRole.USER)
        assert await auth_manager.check_role(test_user, UserRole.READONLY)
        assert await auth_manager.check_role(test_user, UserRole.GUEST)

        # User should not have admin role
        assert not await auth_manager.check_role(test_user, UserRole.ADMIN)

        # Admin should have all roles
        assert await auth_manager.check_role(admin_user, UserRole.ADMIN)
        assert await auth_manager.check_role(admin_user, UserRole.USER)

    @pytest.mark.asyncio
    async def test_authorize_request(self, auth_manager, test_user):
        """Test request authorization."""
        # Add a test access rule
        rule = AccessRule(
            path_pattern="/api/v1/test/*",
            access_level=AccessLevel.PROTECTED,
            required_permissions=[Permission.READ],
            allowed_operations=[Permission.READ],
        )
        await auth_manager.add_access_rule(rule)

        # Test authorized request
        request = AccessRequest(
            user_id=test_user.id,
            path="/api/v1/test/resource",
            operation=Permission.READ,
        )
        assert await auth_manager.authorize_request(request)

        # Test unauthorized operation
        request.operation = Permission.DELETE
        assert not await auth_manager.authorize_request(request)


class TestSecurityMiddleware:
    """Test security middleware functionality."""

    def test_security_headers_middleware(self):
        """Test security headers middleware."""
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)

        @app.get("/test")
        def test_endpoint():
            return {"message": "test"}

        client = TestClient(app)
        response = client.get("/test")

        # Check security headers
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "X-XSS-Protection" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"

    def test_request_validation_middleware(self):
        """Test request validation middleware."""
        app = FastAPI()
        app.add_middleware(RequestValidationMiddleware)

        @app.post("/test")
        def test_endpoint():
            return {"message": "test"}

        client = TestClient(app)

        # Test valid request
        response = client.post(
            "/test", json={"data": "test"}, headers={"content-type": "application/json"}
        )
        assert response.status_code != 415

        # Test invalid content type
        response = client.post("/test", data="test data", headers={"content-type": "invalid/type"})
        assert response.status_code == 415

    def test_request_validation_suspicious_patterns(self):
        """Test request validation for suspicious patterns."""
        app = FastAPI()
        app.add_middleware(RequestValidationMiddleware)

        @app.get("/test")
        def test_endpoint():
            return {"message": "test"}

        client = TestClient(app)

        # Test suspicious path patterns
        suspicious_paths = [
            "/test/../../../etc/passwd",
            "/test?param=<script>alert('xss')</script>",
            "/test?param=javascript:alert(1)",
        ]

        for path in suspicious_paths:
            response = client.get(path)
            assert response.status_code == 400


class TestIntegration:
    """Integration tests for the complete security system."""

    @pytest.mark.asyncio
    async def test_full_authentication_flow(self, security_config):
        """Test complete authentication flow."""
        # Create auth manager
        auth_manager = AuthManager(security_config)

        # Create user
        user = await auth_manager.create_user(
            username="integration_user",
            password="integration_pass123!",
            email="integration@example.com",
        )

        # Authenticate
        credentials = AuthCredentials(username="integration_user", password="integration_pass123!")
        authenticated_user = await auth_manager.authenticate_user(credentials)
        assert authenticated_user.id == user.id

        # Create tokens
        access_token = await auth_manager.create_access_token(authenticated_user)
        refresh_token = await auth_manager.create_refresh_token(authenticated_user)

        # Verify access token
        token_data = await auth_manager.verify_token(access_token)
        assert token_data.user_id == user.id

        # Refresh token
        new_access_token = await auth_manager.refresh_access_token(refresh_token)
        assert new_access_token is not None

        # Verify new token
        new_token_data = await auth_manager.verify_token(new_access_token)
        assert new_token_data.user_id == user.id

    @pytest.mark.asyncio
    async def test_authorization_flow(self, auth_manager, test_user):
        """Test complete authorization flow."""
        # Add access rules
        public_rule = AccessRule(
            path_pattern="/public/*",
            access_level=AccessLevel.PUBLIC,
            allowed_operations=[Permission.READ],
        )
        protected_rule = AccessRule(
            path_pattern="/protected/*",
            access_level=AccessLevel.PROTECTED,
            required_permissions=[Permission.READ],
            allowed_operations=[Permission.READ, Permission.WRITE],
        )
        admin_rule = AccessRule(
            path_pattern="/admin/*",
            access_level=AccessLevel.RESTRICTED,
            required_role=UserRole.ADMIN,
            allowed_operations=[Permission.READ, Permission.WRITE, Permission.DELETE],
        )

        await auth_manager.add_access_rule(public_rule)
        await auth_manager.add_access_rule(protected_rule)
        await auth_manager.add_access_rule(admin_rule)

        # Test public access
        public_request = AccessRequest(
            user_id=test_user.id, path="/public/resource", operation=Permission.READ
        )
        assert await auth_manager.authorize_request(public_request)

        # Test protected access (should work for authenticated user)
        protected_request = AccessRequest(
            user_id=test_user.id, path="/protected/resource", operation=Permission.READ
        )
        assert await auth_manager.authorize_request(protected_request)

        # Test admin access (should fail for regular user)
        admin_request = AccessRequest(
            user_id=test_user.id, path="/admin/resource", operation=Permission.READ
        )
        assert not await auth_manager.authorize_request(admin_request)

    def test_security_event_logging(self, auth_manager):
        """Test security event logging."""
        # Events should be empty initially
        events = asyncio.run(auth_manager.get_security_events())
        initial_count = len(events)

        # Log a security event
        asyncio.run(
            auth_manager._log_security_event(
                "test_event",
                user_id="test_user_id",
                username="test_user",
                details={"test": "data"},
            )
        )

        # Check that event was logged
        events = asyncio.run(auth_manager.get_security_events())
        assert len(events) == initial_count + 1

        latest_event = events[-1]
        assert latest_event.event_type == "test_event"
        assert latest_event.user_id == "test_user_id"
        assert latest_event.username == "test_user"
        assert latest_event.details["test"] == "data"


if __name__ == "__main__":
    pytest.main([__file__])
