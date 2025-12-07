"""
API Gateway Interfaces

All interfaces related to the API gateway including request handling,
authentication, validation, and health monitoring.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

from .shared_interfaces import ISecurityContext, IValidator, Result

# ========================================
# Request/Response Data Types
# ========================================


@dataclass
class APIRequest:
    """API request information"""

    method: str
    path: str
    headers: Dict[str, str]
    query_params: Dict[str, str]
    body: Optional[Any]
    user_id: Optional[str] = None
    security_context: Optional[ISecurityContext] = None


@dataclass
class APIResponse:
    """API response information"""

    status_code: int
    headers: Dict[str, str]
    body: Any
    metadata: Dict[str, Any] = None


@dataclass
class HealthStatus:
    """Health check status"""

    service: str
    status: str  # healthy, unhealthy, degraded
    timestamp: float
    details: Dict[str, Any]
    dependencies: List["HealthStatus"] = None


@dataclass
class ValidationResult:
    """Validation result"""

    is_valid: bool
    errors: List[str]
    sanitized_data: Optional[Any] = None


# ========================================
# Core Gateway Interfaces
# ========================================


class IRequestHandler(ABC):
    """Interface for handling API requests"""

    @abstractmethod
    async def handle_request(self, request: APIRequest) -> APIResponse:
        """Handle an API request"""

    @abstractmethod
    def supports_path(self, path: str, method: str) -> bool:
        """Check if this handler supports the given path and method"""

    @abstractmethod
    def get_openapi_spec(self) -> Dict[str, Any]:
        """Get OpenAPI specification for this handler"""


class IRouteRegistry(ABC):
    """Interface for route registration and discovery"""

    @abstractmethod
    def register_handler(self, path: str, method: str, handler: IRequestHandler) -> None:
        """Register a request handler for a path and method"""

    @abstractmethod
    def unregister_handler(self, path: str, method: str) -> None:
        """Unregister a request handler"""

    @abstractmethod
    def find_handler(self, path: str, method: str) -> Optional[IRequestHandler]:
        """Find a handler for the given path and method"""

    @abstractmethod
    def get_all_routes(self) -> List[tuple[str, str, IRequestHandler]]:
        """Get all registered routes"""


class IGatewayController(ABC):
    """Main gateway controller interface"""

    @abstractmethod
    async def process_request(self, request: APIRequest) -> APIResponse:
        """Process an incoming request through the gateway"""

    @abstractmethod
    def register_middleware(self, middleware: "IMiddleware") -> None:
        """Register middleware in the request pipeline"""

    @abstractmethod
    def get_health_status(self) -> HealthStatus:
        """Get gateway health status"""


# ========================================
# Authentication & Authorization
# ========================================


class IAuthenticationProvider(ABC):
    """Interface for authentication providers"""

    @abstractmethod
    async def authenticate(self, credentials: Dict[str, Any]) -> Result[ISecurityContext]:
        """Authenticate a user with credentials"""

    @abstractmethod
    async def validate_token(self, token: str) -> Result[ISecurityContext]:
        """Validate an authentication token"""

    @abstractmethod
    async def refresh_token(self, refresh_token: str) -> Result[str]:
        """Refresh an authentication token"""

    @abstractmethod
    async def revoke_token(self, token: str) -> Result[None]:
        """Revoke an authentication token"""


class IAuthorizationProvider(ABC):
    """Interface for authorization providers"""

    @abstractmethod
    def is_authorized(self, context: ISecurityContext, resource: str, action: str) -> bool:
        """Check if a security context is authorized for an action on a resource"""

    @abstractmethod
    def get_permissions(self, context: ISecurityContext) -> List[str]:
        """Get all permissions for a security context"""

    @abstractmethod
    def check_role(self, context: ISecurityContext, required_role: str) -> bool:
        """Check if a security context has a required role"""


class IAuthMiddleware(ABC):
    """Interface for authentication middleware"""

    @abstractmethod
    async def authenticate_request(self, request: APIRequest) -> Result[APIRequest]:
        """Authenticate a request and add security context"""

    @abstractmethod
    def extract_credentials(self, request: APIRequest) -> Optional[Dict[str, Any]]:
        """Extract credentials from a request"""

    @abstractmethod
    def requires_authentication(self, path: str, method: str) -> bool:
        """Check if a path requires authentication"""


# ========================================
# Request Validation
# ========================================


class IRequestValidator(ABC, IValidator):
    """Interface for request validation"""

    @abstractmethod
    def validate_request(self, request: APIRequest) -> ValidationResult:
        """Validate an entire request"""

    @abstractmethod
    def validate_path_params(self, path: str, params: Dict[str, str]) -> ValidationResult:
        """Validate path parameters"""

    @abstractmethod
    def validate_query_params(self, params: Dict[str, str]) -> ValidationResult:
        """Validate query parameters"""

    @abstractmethod
    def validate_headers(self, headers: Dict[str, str]) -> ValidationResult:
        """Validate request headers"""

    @abstractmethod
    def validate_body(self, body: Any, content_type: str) -> ValidationResult:
        """Validate request body"""


class IInputSanitizer(ABC):
    """Interface for input sanitization"""

    @abstractmethod
    def sanitize_string(self, value: str) -> str:
        """Sanitize a string input"""

    @abstractmethod
    def sanitize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize a dictionary of data"""

    @abstractmethod
    def detect_malicious_input(self, data: Any) -> List[str]:
        """Detect potentially malicious input patterns"""


# ========================================
# Middleware System
# ========================================


class IMiddleware(ABC):
    """Base interface for middleware components"""

    @abstractmethod
    async def process_request(self, request: APIRequest) -> Union[APIRequest, APIResponse]:
        """Process a request before it reaches the handler"""

    @abstractmethod
    async def process_response(self, request: APIRequest, response: APIResponse) -> APIResponse:
        """Process a response before it's returned to the client"""

    @abstractmethod
    def get_priority(self) -> int:
        """Get middleware priority (lower number = higher priority)"""


class IErrorHandler(ABC):
    """Interface for error handling"""

    @abstractmethod
    def handle_error(self, error: Exception, request: APIRequest) -> APIResponse:
        """Handle an error and convert it to an API response"""

    @abstractmethod
    def can_handle(self, error: Exception) -> bool:
        """Check if this handler can handle the given error"""


# ========================================
# Health Monitoring
# ========================================


class IHealthCheck(ABC):
    """Interface for health check providers"""

    @abstractmethod
    async def check_health(self) -> HealthStatus:
        """Perform a health check"""

    @abstractmethod
    def get_check_name(self) -> str:
        """Get the name of this health check"""

    @abstractmethod
    def get_dependencies(self) -> List[str]:
        """Get list of dependencies this check monitors"""


class IHealthMonitor(ABC):
    """Interface for health monitoring system"""

    @abstractmethod
    def register_check(self, health_check: IHealthCheck) -> None:
        """Register a health check"""

    @abstractmethod
    def unregister_check(self, check_name: str) -> None:
        """Unregister a health check"""

    @abstractmethod
    async def run_all_checks(self) -> List[HealthStatus]:
        """Run all registered health checks"""

    @abstractmethod
    async def run_check(self, check_name: str) -> Optional[HealthStatus]:
        """Run a specific health check"""

    @abstractmethod
    def get_overall_status(self) -> HealthStatus:
        """Get overall system health status"""


# ========================================
# Rate Limiting
# ========================================


class IRateLimiter(ABC):
    """Interface for rate limiting"""

    @abstractmethod
    async def is_allowed(self, key: str, limit: int, window: int) -> bool:
        """Check if a request is allowed under rate limits"""

    @abstractmethod
    async def get_current_usage(self, key: str) -> int:
        """Get current usage for a key"""

    @abstractmethod
    async def reset_usage(self, key: str) -> None:
        """Reset usage for a key"""


# ========================================
# OpenAPI Documentation
# ========================================


class IOpenAPIGenerator(ABC):
    """Interface for OpenAPI documentation generation"""

    @abstractmethod
    def generate_spec(self, handlers: List[IRequestHandler]) -> Dict[str, Any]:
        """Generate OpenAPI specification"""

    @abstractmethod
    def add_security_schemes(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Add security schemes to the spec"""

    @abstractmethod
    def add_common_responses(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Add common response definitions"""
