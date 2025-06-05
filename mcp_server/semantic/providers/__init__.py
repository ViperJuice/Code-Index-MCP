"""
Semantic Search Providers

This module contains embedding provider implementations for model-agnostic
semantic search functionality.
"""

from .base import BaseEmbeddingProvider
from .factory import EmbeddingProviderFactory
from .registry import ProviderRegistry
from .exceptions import (
    ProviderError,
    ProviderNotFoundError,
    ModelNotSupportedError,
    APIKeyError,
    EmbeddingGenerationError,
    ProviderInitializationError,
    ProviderNotAvailableError
)

# Import concrete providers
from .voyage_provider import VoyageProvider
from .openai_provider import OpenAIProvider
from .cohere_provider import CohereProvider
from .local_provider import LocalProvider
from .mock_provider import MockProvider
from .google_provider import GoogleProvider
from .huggingface_provider import HuggingFaceProvider

__all__ = [
    # Base classes
    "BaseEmbeddingProvider",
    
    # Factory and Registry
    "EmbeddingProviderFactory",
    "ProviderRegistry",
    
    # Concrete Providers
    "VoyageProvider",
    "OpenAIProvider",
    "CohereProvider",
    "LocalProvider",
    "MockProvider",
    "GoogleProvider",
    "HuggingFaceProvider",
    
    # Exceptions
    "ProviderError",
    "ProviderNotFoundError",
    "ModelNotSupportedError",
    "APIKeyError",
    "EmbeddingGenerationError",
    "ProviderInitializationError",
    "ProviderNotAvailableError",
]