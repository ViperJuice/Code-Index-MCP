"""
Security Interfaces

All interfaces related to authentication, authorization, and security management.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass
from datetime import datetime, timedelta
from .shared_interfaces import Result, ISecurityContext

# ========================================
# Security Data Types
# ========================================


@dataclass
class User:
    """User information"""

    user_id: str
    username: str
    email: str
    roles: List[str]
    permissions: List[str]
    created_at: datetime
    last_login: Optional[datetime] = None
    is_active: bool = True
    metadata: Dict[str, Any] = None


@dataclass
class Role:
    """Role definition"""

    role_id: str
    name: str
    description: str
    permissions: List[str]
    created_at: datetime
    is_system_role: bool = False


@dataclass
class Permission:
    """Permission definition"""

    permission_id: str
    name: str
    description: str
    resource: str
    action: str
    created_at: datetime


@dataclass
class AuthToken:
    """Authentication token"""

    token_id: str
    user_id: str
    token_type: str  # access, refresh, api_key
    token_value: str
    expires_at: datetime
    created_at: datetime
    last_used: Optional[datetime] = None
    is_revoked: bool = False
    metadata: Dict[str, Any] = None


@dataclass
class SecurityPolicy:
    """Security policy"""

    policy_id: str
    name: str
    description: str
    rules: List[Dict[str, Any]]
    priority: int
    is_active: bool = True
    created_at: datetime


# ========================================
# Authentication Interfaces
# ========================================


class IAuthenticator(ABC):
    """Interface for user authentication"""

    @abstractmethod
    async def authenticate_user(self, username: str, password: str) -> Result[User]:
        """Authenticate user with username/password"""
        pass

    @abstractmethod
    async def authenticate_token(self, token: str) -> Result[User]:
        """Authenticate user with token"""
        pass

    @abstractmethod
    async def authenticate_api_key(self, api_key: str) -> Result[User]:
        """Authenticate user with API key"""
        pass

    @abstractmethod
    async def refresh_token(self, refresh_token: str) -> Result[AuthToken]:
        """Refresh an authentication token"""
        pass

    @abstractmethod
    async def revoke_token(self, token: str) -> Result[None]:
        """Revoke an authentication token"""
        pass


class IPasswordManager(ABC):
    """Interface for password management"""

    @abstractmethod
    def hash_password(self, password: str) -> str:
        """Hash a password"""
        pass

    @abstractmethod
    def verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        pass

    @abstractmethod
    def generate_random_password(self, length: int = 12) -> str:
        """Generate a random password"""
        pass

    @abstractmethod
    def validate_password_strength(self, password: str) -> Result[bool]:
        """Validate password strength"""
        pass


class IJWTManager(ABC):
    """Interface for JWT token management"""

    @abstractmethod
    def generate_access_token(self, user: User, expires_in: timedelta = None) -> str:
        """Generate an access token"""
        pass

    @abstractmethod
    def generate_refresh_token(self, user: User, expires_in: timedelta = None) -> str:
        """Generate a refresh token"""
        pass

    @abstractmethod
    def decode_token(self, token: str) -> Result[Dict[str, Any]]:
        """Decode and validate a JWT token"""
        pass

    @abstractmethod
    def is_token_expired(self, token: str) -> bool:
        """Check if a token is expired"""
        pass

    @abstractmethod
    def revoke_token(self, token: str) -> None:
        """Add token to revocation list"""
        pass


# ========================================
# Authorization Interfaces
# ========================================


class IAuthorizer(ABC):
    """Interface for authorization decisions"""

    @abstractmethod
    def is_authorized(
        self, user: User, resource: str, action: str, context: Dict[str, Any] = None
    ) -> bool:
        """Check if user is authorized for action on resource"""
        pass

    @abstractmethod
    def get_user_permissions(self, user: User) -> List[str]:
        """Get all permissions for a user"""
        pass

    @abstractmethod
    def check_role(self, user: User, required_role: str) -> bool:
        """Check if user has required role"""
        pass

    @abstractmethod
    def filter_resources(
        self, user: User, resources: List[str], action: str
    ) -> List[str]:
        """Filter resources user can access"""
        pass


class IAccessController(ABC):
    """Interface for access control"""

    @abstractmethod
    async def check_access(
        self, context: ISecurityContext, resource: str, action: str
    ) -> bool:
        """Check if security context has access"""
        pass

    @abstractmethod
    async def grant_access(
        self, user_id: str, resource: str, permissions: List[str]
    ) -> Result[None]:
        """Grant access to a user"""
        pass

    @abstractmethod
    async def revoke_access(
        self, user_id: str, resource: str, permissions: List[str]
    ) -> Result[None]:
        """Revoke access from a user"""
        pass

    @abstractmethod
    async def list_user_access(self, user_id: str) -> Result[List[Dict[str, Any]]]:
        """List all access for a user"""
        pass


class IRoleManager(ABC):
    """Interface for role management"""

    @abstractmethod
    async def create_role(self, role: Role) -> Result[str]:
        """Create a new role"""
        pass

    @abstractmethod
    async def update_role(self, role_id: str, updates: Dict[str, Any]) -> Result[None]:
        """Update a role"""
        pass

    @abstractmethod
    async def delete_role(self, role_id: str) -> Result[None]:
        """Delete a role"""
        pass

    @abstractmethod
    async def assign_role(self, user_id: str, role_id: str) -> Result[None]:
        """Assign role to user"""
        pass

    @abstractmethod
    async def revoke_role(self, user_id: str, role_id: str) -> Result[None]:
        """Revoke role from user"""
        pass

    @abstractmethod
    async def get_user_roles(self, user_id: str) -> Result[List[Role]]:
        """Get all roles for a user"""
        pass


class IPermissionManager(ABC):
    """Interface for permission management"""

    @abstractmethod
    async def create_permission(self, permission: Permission) -> Result[str]:
        """Create a new permission"""
        pass

    @abstractmethod
    async def delete_permission(self, permission_id: str) -> Result[None]:
        """Delete a permission"""
        pass

    @abstractmethod
    async def grant_permission(self, role_id: str, permission_id: str) -> Result[None]:
        """Grant permission to role"""
        pass

    @abstractmethod
    async def revoke_permission(self, role_id: str, permission_id: str) -> Result[None]:
        """Revoke permission from role"""
        pass

    @abstractmethod
    async def get_role_permissions(self, role_id: str) -> Result[List[Permission]]:
        """Get all permissions for a role"""
        pass


# ========================================
# Policy Engine Interfaces
# ========================================


class IPolicyEngine(ABC):
    """Interface for policy-based access control"""

    @abstractmethod
    async def evaluate_policy(
        self, policy_id: str, context: Dict[str, Any]
    ) -> Result[bool]:
        """Evaluate a policy against context"""
        pass

    @abstractmethod
    async def create_policy(self, policy: SecurityPolicy) -> Result[str]:
        """Create a new policy"""
        pass

    @abstractmethod
    async def update_policy(
        self, policy_id: str, updates: Dict[str, Any]
    ) -> Result[None]:
        """Update a policy"""
        pass

    @abstractmethod
    async def delete_policy(self, policy_id: str) -> Result[None]:
        """Delete a policy"""
        pass

    @abstractmethod
    async def list_applicable_policies(
        self, context: Dict[str, Any]
    ) -> Result[List[SecurityPolicy]]:
        """List policies applicable to context"""
        pass


class IRuleEvaluator(ABC):
    """Interface for rule evaluation"""

    @abstractmethod
    def evaluate_rule(self, rule: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Evaluate a single rule"""
        pass

    @abstractmethod
    def evaluate_rules(
        self, rules: List[Dict[str, Any]], context: Dict[str, Any]
    ) -> bool:
        """Evaluate multiple rules"""
        pass

    @abstractmethod
    def validate_rule_syntax(self, rule: Dict[str, Any]) -> Result[bool]:
        """Validate rule syntax"""
        pass


# ========================================
# Security Monitoring Interfaces
# ========================================


class ISecurityAuditor(ABC):
    """Interface for security auditing"""

    @abstractmethod
    async def log_authentication_attempt(
        self, username: str, success: bool, ip_address: str
    ) -> None:
        """Log authentication attempt"""
        pass

    @abstractmethod
    async def log_authorization_check(
        self, user_id: str, resource: str, action: str, allowed: bool
    ) -> None:
        """Log authorization check"""
        pass

    @abstractmethod
    async def log_security_event(
        self, event_type: str, details: Dict[str, Any]
    ) -> None:
        """Log security event"""
        pass

    @abstractmethod
    async def get_security_events(
        self, filters: Dict[str, Any]
    ) -> Result[List[Dict[str, Any]]]:
        """Get security events"""
        pass


class IThreatDetector(ABC):
    """Interface for threat detection"""

    @abstractmethod
    async def detect_brute_force(self, username: str, ip_address: str) -> bool:
        """Detect brute force attacks"""
        pass

    @abstractmethod
    async def detect_suspicious_activity(
        self, user_id: str, activity: Dict[str, Any]
    ) -> bool:
        """Detect suspicious user activity"""
        pass

    @abstractmethod
    async def analyze_request_pattern(
        self, requests: List[Dict[str, Any]]
    ) -> List[str]:
        """Analyze request patterns for threats"""
        pass

    @abstractmethod
    async def block_ip_address(self, ip_address: str, duration: timedelta) -> None:
        """Block an IP address"""
        pass


# ========================================
# Security Configuration Interfaces
# ========================================


class ISecurityConfigManager(ABC):
    """Interface for security configuration management"""

    @abstractmethod
    async def get_security_config(self) -> Result[Dict[str, Any]]:
        """Get security configuration"""
        pass

    @abstractmethod
    async def update_security_config(self, config: Dict[str, Any]) -> Result[None]:
        """Update security configuration"""
        pass

    @abstractmethod
    async def validate_config(self, config: Dict[str, Any]) -> Result[bool]:
        """Validate security configuration"""
        pass

    @abstractmethod
    async def reset_to_defaults(self) -> Result[None]:
        """Reset to default configuration"""
        pass


class ISecretManager(ABC):
    """Interface for secret management"""

    @abstractmethod
    async def store_secret(
        self, key: str, value: str, metadata: Dict[str, Any] = None
    ) -> Result[None]:
        """Store a secret"""
        pass

    @abstractmethod
    async def retrieve_secret(self, key: str) -> Result[str]:
        """Retrieve a secret"""
        pass

    @abstractmethod
    async def delete_secret(self, key: str) -> Result[None]:
        """Delete a secret"""
        pass

    @abstractmethod
    async def rotate_secret(self, key: str, new_value: str) -> Result[None]:
        """Rotate a secret"""
        pass

    @abstractmethod
    async def list_secrets(self) -> Result[List[str]]:
        """List secret keys (not values)"""
        pass


# ========================================
# Security Middleware Interfaces
# ========================================


class ISecurityMiddleware(ABC):
    """Interface for security middleware"""

    @abstractmethod
    async def authenticate_request(self, request: Any) -> Result[ISecurityContext]:
        """Authenticate a request"""
        pass

    @abstractmethod
    async def authorize_request(
        self, context: ISecurityContext, resource: str, action: str
    ) -> Result[bool]:
        """Authorize a request"""
        pass

    @abstractmethod
    async def validate_request_security(self, request: Any) -> Result[bool]:
        """Validate request security"""
        pass

    @abstractmethod
    async def apply_security_headers(self, response: Any) -> Any:
        """Apply security headers to response"""
        pass
