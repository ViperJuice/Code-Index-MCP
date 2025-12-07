"""Security data models for authentication and authorization."""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


class UserRole(str, Enum):
    """User roles for role-based access control."""

    ADMIN = "admin"
    USER = "user"
    READONLY = "readonly"
    GUEST = "guest"


class Permission(str, Enum):
    """Available permissions in the system."""

    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    EXECUTE = "execute"
    ADMIN = "admin"


class AccessLevel(str, Enum):
    """Access levels for path-based authorization."""

    PUBLIC = "public"
    PROTECTED = "protected"
    PRIVATE = "private"
    RESTRICTED = "restricted"


class User(BaseModel):
    """User model for authentication."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    email: Optional[str] = None
    hashed_password: str
    role: UserRole = UserRole.USER
    permissions: List[Permission] = Field(default_factory=list)
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @validator("username")
    def username_must_be_valid(cls, v):
        if not v or len(v) < 3:
            raise ValueError("Username must be at least 3 characters long")
        if not v.isalnum() and "_" not in v and "-" not in v:
            raise ValueError(
                "Username can only contain alphanumeric characters, underscores, and hyphens"
            )
        return v

    @validator("email")
    def email_must_be_valid(cls, v):
        if v and "@" not in v:
            raise ValueError("Invalid email format")
        return v


class TokenData(BaseModel):
    """JWT token data structure."""

    user_id: str
    username: str
    role: UserRole
    permissions: List[Permission]
    issued_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    token_type: str = "access"
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @validator("expires_at")
    def expires_at_must_be_future(cls, v, values):
        if "issued_at" in values and v <= values["issued_at"]:
            raise ValueError("Expiration time must be in the future")
        return v


class AuthCredentials(BaseModel):
    """Authentication credentials."""

    username: str
    password: str

    @validator("username")
    def username_required(cls, v):
        if not v or not v.strip():
            raise ValueError("Username is required")
        return v.strip()

    @validator("password")
    def password_required(cls, v):
        if not v:
            raise ValueError("Password is required")
        return v


class RefreshTokenData(BaseModel):
    """Refresh token data structure."""

    user_id: str
    token_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    issued_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    is_revoked: bool = False


class AccessRequest(BaseModel):
    """Access request for path-based authorization."""

    user_id: str
    path: str
    operation: Permission
    resource_type: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AccessRule(BaseModel):
    """Access rule for path-based authorization."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    path_pattern: str
    access_level: AccessLevel
    required_role: Optional[UserRole] = None
    required_permissions: List[Permission] = Field(default_factory=list)
    allowed_operations: List[Permission] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @validator("path_pattern")
    def path_pattern_required(cls, v):
        if not v or not v.strip():
            raise ValueError("Path pattern is required")
        return v.strip()


class SecurityConfig(BaseModel):
    """Security configuration model."""

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    password_min_length: int = 8
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 15
    rate_limit_requests: int = 100
    rate_limit_window_minutes: int = 1
    cors_origins: List[str] = Field(default_factory=lambda: ["*"])
    cors_methods: List[str] = Field(default_factory=lambda: ["GET", "POST", "PUT", "DELETE"])
    cors_headers: List[str] = Field(default_factory=lambda: ["*"])
    security_headers: Dict[str, str] = Field(
        default_factory=lambda: {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        }
    )

    @validator("jwt_secret_key")
    def jwt_secret_key_required(cls, v):
        if not v or len(v) < 32:
            raise ValueError("JWT secret key must be at least 32 characters long")
        return v

    @validator("access_token_expire_minutes")
    def access_token_expire_minutes_positive(cls, v):
        if v <= 0:
            raise ValueError("Access token expire minutes must be positive")
        return v

    @validator("refresh_token_expire_days")
    def refresh_token_expire_days_positive(cls, v):
        if v <= 0:
            raise ValueError("Refresh token expire days must be positive")
        return v


class SecurityEvent(BaseModel):
    """Security event for audit logging."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str
    user_id: Optional[str] = None
    username: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: Dict[str, Any] = Field(default_factory=dict)
    severity: str = "info"  # info, warning, error, critical


class RateLimitInfo(BaseModel):
    """Rate limiting information."""

    identifier: str  # IP address or user ID
    requests_count: int = 0
    window_start: datetime = Field(default_factory=datetime.utcnow)
    is_blocked: bool = False
    blocked_until: Optional[datetime] = None


class SessionInfo(BaseModel):
    """User session information."""

    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True


# Default role permissions mapping
DEFAULT_ROLE_PERMISSIONS = {
    UserRole.ADMIN: [
        Permission.READ,
        Permission.WRITE,
        Permission.DELETE,
        Permission.EXECUTE,
        Permission.ADMIN,
    ],
    UserRole.USER: [Permission.READ, Permission.WRITE, Permission.EXECUTE],
    UserRole.READONLY: [Permission.READ],
    UserRole.GUEST: [],
}

# Default access rules
DEFAULT_ACCESS_RULES = [
    AccessRule(
        path_pattern="/api/v1/public/*",
        access_level=AccessLevel.PUBLIC,
        allowed_operations=[Permission.READ],
    ),
    AccessRule(
        path_pattern="/api/v1/auth/*",
        access_level=AccessLevel.PUBLIC,
        allowed_operations=[Permission.READ, Permission.WRITE],
    ),
    AccessRule(
        path_pattern="/api/v1/admin/*",
        access_level=AccessLevel.RESTRICTED,
        required_role=UserRole.ADMIN,
        required_permissions=[Permission.ADMIN],
        allowed_operations=[
            Permission.READ,
            Permission.WRITE,
            Permission.DELETE,
            Permission.EXECUTE,
        ],
    ),
    AccessRule(
        path_pattern="/api/v1/*",
        access_level=AccessLevel.PROTECTED,
        required_permissions=[Permission.READ],
        allowed_operations=[Permission.READ, Permission.WRITE, Permission.EXECUTE],
    ),
]
