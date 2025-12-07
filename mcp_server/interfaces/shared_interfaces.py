"""
Shared Interfaces for MCP Server

Cross-cutting interfaces and common types used across all modules.
These interfaces define the contracts for logging, metrics, configuration,
caching, events, and other shared concerns.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import (
    Any,
    Awaitable,
    Callable,
    ContextManager,
    Dict,
    Generic,
    List,
    Optional,
    TypeVar,
)

T = TypeVar("T")

# ========================================
# Common Enums
# ========================================


class LogLevel(Enum):
    """Log levels for the logging system"""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class IndexStatus(Enum):
    """Status of indexing operations"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PluginStatus(Enum):
    """Status of plugin lifecycle"""

    UNLOADED = "unloaded"
    LOADING = "loading"
    READY = "ready"
    ERROR = "error"
    DISABLED = "disabled"


# ========================================
# Common Data Types
# ========================================


@dataclass
class Event:
    """Event data structure for the event bus"""

    event_type: str
    timestamp: datetime
    source: str
    data: Dict[str, Any]


@dataclass
class Error:
    """Error information with context"""

    code: str
    message: str
    details: Dict[str, Any]
    timestamp: datetime


@dataclass
class Result(Generic[T]):
    """Result wrapper for operations that can succeed or fail"""

    success: bool
    value: Optional[T] = None
    error: Optional[Error] = None
    metadata: Dict[str, Any] = None

    @classmethod
    def success_result(cls, value: T, metadata: Dict[str, Any] = None) -> "Result[T]":
        """Create a successful result"""
        return cls(success=True, value=value, metadata=metadata or {})

    @classmethod
    def error_result(cls, error: Error, metadata: Dict[str, Any] = None) -> "Result[T]":
        """Create an error result"""
        return cls(success=False, error=error, metadata=metadata or {})


# ========================================
# Cross-Cutting Interfaces
# ========================================


class ILogger(ABC):
    """Logging interface for all components"""

    @abstractmethod
    def log(self, level: LogLevel, message: str, context: Dict[str, Any] = None) -> None:
        """Log a message with specified level and context"""

    @abstractmethod
    def debug(self, message: str, context: Dict[str, Any] = None) -> None:
        """Log a debug message"""

    @abstractmethod
    def info(self, message: str, context: Dict[str, Any] = None) -> None:
        """Log an info message"""

    @abstractmethod
    def warning(self, message: str, context: Dict[str, Any] = None) -> None:
        """Log a warning message"""

    @abstractmethod
    def error(
        self, message: str, exception: Exception = None, context: Dict[str, Any] = None
    ) -> None:
        """Log an error message with optional exception"""


class IMetrics(ABC):
    """Metrics collection interface"""

    @abstractmethod
    def increment(self, metric: str, value: int = 1, tags: Dict[str, str] = None) -> None:
        """Increment a counter metric"""

    @abstractmethod
    def gauge(self, metric: str, value: float, tags: Dict[str, str] = None) -> None:
        """Set a gauge metric value"""

    @abstractmethod
    def histogram(self, metric: str, value: float, tags: Dict[str, str] = None) -> None:
        """Record a histogram value"""

    @abstractmethod
    def timer(self, metric: str, tags: Dict[str, str] = None) -> ContextManager[None]:
        """Create a timing context manager"""


class IConfig(ABC):
    """Configuration management interface"""

    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value"""

    @abstractmethod
    def get_int(self, key: str, default: int = 0) -> int:
        """Get an integer configuration value"""

    @abstractmethod
    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get a boolean configuration value"""

    @abstractmethod
    def get_str(self, key: str, default: str = "") -> str:
        """Get a string configuration value"""

    @abstractmethod
    def get_dict(self, key: str, default: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get a dictionary configuration value"""

    @abstractmethod
    def reload(self) -> None:
        """Reload configuration from source"""


class ICache(ABC):
    """Caching interface"""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Get a value from cache"""

    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set a value in cache with optional TTL"""

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete a value from cache"""

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if a key exists in cache"""

    @abstractmethod
    def clear(self) -> None:
        """Clear all cache entries"""


class IEventBus(ABC):
    """Event bus interface for pub/sub messaging"""

    @abstractmethod
    def publish(self, event: Event) -> None:
        """Publish an event"""

    @abstractmethod
    def subscribe(self, event_type: str, handler: Callable[[Event], None]) -> None:
        """Subscribe to an event type"""

    @abstractmethod
    def unsubscribe(self, event_type: str, handler: Callable[[Event], None]) -> None:
        """Unsubscribe from an event type"""


# ========================================
# Security Interfaces
# ========================================


class ISecurityContext(ABC):
    """Security context for requests"""

    @property
    @abstractmethod
    def user_id(self) -> Optional[str]:
        """Get the current user ID"""

    @property
    @abstractmethod
    def roles(self) -> List[str]:
        """Get the current user's roles"""

    @property
    @abstractmethod
    def permissions(self) -> List[str]:
        """Get the current user's permissions"""

    @property
    @abstractmethod
    def is_authenticated(self) -> bool:
        """Check if the user is authenticated"""

    @abstractmethod
    def is_authorized(self, permission: str) -> bool:
        """Check if the user has a specific permission"""


class IValidator(ABC):
    """Validation interface"""

    @abstractmethod
    def validate(self, data: Any, schema: Any) -> Result[Any]:
        """Validate data against a schema"""

    @abstractmethod
    def sanitize(self, data: Any) -> Any:
        """Sanitize input data"""


# ========================================
# Async Support
# ========================================


class IAsyncSupport(ABC):
    """Async utilities interface"""

    @abstractmethod
    async def run_async(self, func: Callable, *args, **kwargs) -> Any:
        """Run a function asynchronously"""

    @abstractmethod
    async def gather(self, *awaitables: Awaitable) -> List[Any]:
        """Gather multiple awaitables"""

    @abstractmethod
    def create_task(self, coro) -> Any:
        """Create an async task"""


# ========================================
# Repository Pattern
# ========================================


class IRepository(ABC, Generic[T]):
    """Repository interface for data access"""

    @abstractmethod
    def find(self, id: str) -> Optional[T]:
        """Find an entity by ID"""

    @abstractmethod
    def find_all(self, filter_criteria: Dict[str, Any] = None) -> List[T]:
        """Find all entities matching criteria"""

    @abstractmethod
    def save(self, entity: T) -> T:
        """Save an entity"""

    @abstractmethod
    def delete(self, id: str) -> bool:
        """Delete an entity by ID"""

    @abstractmethod
    def exists(self, id: str) -> bool:
        """Check if an entity exists"""


class IAsyncRepository(ABC, Generic[T]):
    """Async repository interface for data access"""

    @abstractmethod
    async def find(self, id: str) -> Optional[T]:
        """Find an entity by ID"""

    @abstractmethod
    async def find_all(self, filter_criteria: Dict[str, Any] = None) -> List[T]:
        """Find all entities matching criteria"""

    @abstractmethod
    async def save(self, entity: T) -> T:
        """Save an entity"""

    @abstractmethod
    async def delete(self, id: str) -> bool:
        """Delete an entity by ID"""

    @abstractmethod
    async def exists(self, id: str) -> bool:
        """Check if an entity exists"""


# ========================================
# Factory Pattern
# ========================================


class IFactory(ABC, Generic[T]):
    """Factory interface for creating objects"""

    @abstractmethod
    def create(self, *args, **kwargs) -> T:
        """Create an object"""

    @abstractmethod
    def create_from_config(self, config: Dict[str, Any]) -> T:
        """Create an object from configuration"""


# ========================================
# Observer Pattern
# ========================================


class IObserver(ABC):
    """Observer interface for the observer pattern"""

    @abstractmethod
    def update(self, event: Event) -> None:
        """Handle an update event"""


class IObservable(ABC):
    """Observable interface for the observer pattern"""

    @abstractmethod
    def attach(self, observer: IObserver) -> None:
        """Attach an observer"""

    @abstractmethod
    def detach(self, observer: IObserver) -> None:
        """Detach an observer"""

    @abstractmethod
    def notify(self, event: Event) -> None:
        """Notify all observers"""


# ========================================
# Common Exceptions
# ========================================


class ValidationError(Exception):
    """Validation error exception"""

    def __init__(self, field: str, value: Any, constraint: str):
        self.field = field
        self.value = value
        self.constraint = constraint
        super().__init__(f"Validation error for field '{field}': {constraint}")


class NotFoundError(Exception):
    """Resource not found exception"""

    def __init__(self, resource_type: str, resource_id: str):
        self.resource_type = resource_type
        self.resource_id = resource_id
        super().__init__(f"{resource_type} with ID '{resource_id}' not found")


class PermissionError(Exception):
    """Permission denied exception"""

    def __init__(self, required_permission: str, user_id: str):
        self.required_permission = required_permission
        self.user_id = user_id
        super().__init__(f"User '{user_id}' lacks permission '{required_permission}'")


class ConfigurationError(Exception):
    """Configuration error exception"""

    def __init__(self, config_key: str, expected_type: str, actual_value: Any):
        self.config_key = config_key
        self.expected_type = expected_type
        self.actual_value = actual_value
        super().__init__(
            f"Config key '{config_key}' expected {expected_type}, got {type(actual_value).__name__}"
        )


class PluginError(Exception):
    """Plugin operation error exception"""

    def __init__(self, plugin_name: str, operation: str, cause: Exception = None):
        self.plugin_name = plugin_name
        self.operation = operation
        self.cause = cause
        super().__init__(f"Plugin '{plugin_name}' failed during '{operation}': {cause}")
