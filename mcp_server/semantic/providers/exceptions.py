"""
Custom exceptions for embedding providers

Provides specific exception types for different provider-related errors.
"""

from typing import Optional


class ProviderError(Exception):
    """Base exception for all provider-related errors"""
    pass


class ProviderNotFoundError(ProviderError):
    """Raised when a requested provider is not found in registry"""
    pass


class ModelNotSupportedError(ProviderError):
    """Raised when a model is not supported by any provider"""
    pass


class APIKeyError(ProviderError):
    """Raised when API key is missing or invalid"""
    pass


class EmbeddingGenerationError(ProviderError):
    """Raised when embedding generation fails"""
    pass


class ProviderInitializationError(ProviderError):
    """Raised when provider fails to initialize"""
    pass


class RateLimitError(ProviderError):
    """Raised when API rate limit is exceeded"""
    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message)
        self.retry_after = retry_after


class TokenLimitError(ProviderError):
    """Raised when text exceeds token limit"""
    def __init__(self, message: str, token_count: int, limit: int):
        super().__init__(message)
        self.token_count = token_count
        self.limit = limit


class DimensionMismatchError(ProviderError):
    """Raised when embedding dimensions don't match expected"""
    def __init__(self, message: str, expected: int, actual: int):
        super().__init__(message)
        self.expected = expected
        self.actual = actual


class ProviderTimeoutError(ProviderError):
    """Raised when provider request times out"""
    pass


class CacheError(ProviderError):
    """Raised when cache operations fail"""
    pass


class ValidationError(ProviderError):
    """Raised when input validation fails"""
    pass


class ProviderNotAvailableError(ProviderError):
    """Raised when a provider is not yet available or implemented"""
    pass