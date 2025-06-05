"""
Result wrapper for embedding providers

Provides a simple Result type for async operations that can succeed or fail.
"""

from typing import TypeVar, Generic, Optional, Any, Union
from dataclasses import dataclass

T = TypeVar('T')


@dataclass
class Result(Generic[T]):
    """Result wrapper for operations that can succeed or fail"""
    _success: bool
    _value: Optional[T] = None
    _error: Optional[Union[str, Exception]] = None
    
    @classmethod
    def success(cls, value: T) -> 'Result[T]':
        """Create a successful result"""
        return cls(_success=True, _value=value, _error=None)
    
    @classmethod
    def error(cls, error: Union[str, Exception]) -> 'Result[T]':
        """Create an error result"""
        return cls(_success=False, _value=None, _error=error)
    
    def is_ok(self) -> bool:
        """Check if result is successful"""
        return self._success
    
    def is_error(self) -> bool:
        """Check if result is an error"""
        return not self._success
    
    @property
    def value(self) -> T:
        """Get the value (raises if error)"""
        if not self._success:
            raise ValueError(f"Result is an error: {self._error}")
        return self._value
    
    @property
    def error_value(self) -> Optional[Union[str, Exception]]:
        """Get the error value (None if success)"""
        return self._error
    
    def unwrap(self) -> T:
        """Unwrap the value or raise the error"""
        if not self._success:
            if isinstance(self._error, Exception):
                raise self._error
            raise RuntimeError(str(self._error))
        return self._value
    
    def unwrap_or(self, default: T) -> T:
        """Unwrap the value or return default"""
        return self._value if self._success else default
    
    def map(self, func: Any) -> 'Result[Any]':
        """Map the value if successful"""
        if self._success:
            try:
                return Result.success(func(self._value))
            except Exception as e:
                return Result.error(e)
        return self
    
    def __bool__(self) -> bool:
        """Allow if result: checks"""
        return self._success