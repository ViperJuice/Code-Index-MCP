"""
Embedding Provider Factory

Creates embedding provider instances based on model names or provider types.
"""

from typing import Dict, Type, Optional, Any, Tuple, List
import logging

from mcp_server.interfaces.embedding_interfaces import (
    IEmbeddingProvider,
    EmbeddingConfig
)
from mcp_server.config.semantic_settings import SemanticSearchSettings
from .base import BaseEmbeddingProvider
from .registry import ProviderRegistry
from .exceptions import (
    ProviderNotFoundError,
    ModelNotSupportedError,
    ProviderInitializationError
)

logger = logging.getLogger(__name__)


class EmbeddingProviderFactory:
    """Factory for creating embedding provider instances"""
    
    # Default model to provider mappings
    _default_model_mappings: Dict[str, Tuple[str, Dict[str, Any]]] = {
        # Voyage AI models
        "voyage-code-3": ("voyage", {"dimension": 1024, "max_tokens": 16000}),
        "voyage-code-2": ("voyage", {"dimension": 1536, "max_tokens": 4000}),
        "voyage-2": ("voyage", {"dimension": 1024, "max_tokens": 4000}),
        "voyage-large-2": ("voyage", {"dimension": 1536, "max_tokens": 16000}),
        
        # OpenAI models
        "text-embedding-3-small": ("openai", {"dimension": 1536, "max_tokens": 8191}),
        "text-embedding-3-large": ("openai", {"dimension": 3072, "max_tokens": 8191}),
        "text-embedding-ada-002": ("openai", {"dimension": 1536, "max_tokens": 8191}),
        
        # Cohere models
        "embed-english-v3.0": ("cohere", {"dimension": 1024, "max_tokens": 512}),
        "embed-multilingual-v3.0": ("cohere", {"dimension": 1024, "max_tokens": 512}),
        "embed-english-light-v3.0": ("cohere", {"dimension": 384, "max_tokens": 512}),
        
        # Local models (Sentence Transformers)
        "all-MiniLM-L6-v2": ("local", {"dimension": 384, "max_tokens": 256}),
        "all-mpnet-base-v2": ("local", {"dimension": 768, "max_tokens": 384}),
        "all-distilroberta-v1": ("local", {"dimension": 768, "max_tokens": 512}),
        "msmarco-distilbert-base-v4": ("local", {"dimension": 768, "max_tokens": 512}),
        "multi-qa-mpnet-base-dot-v1": ("local", {"dimension": 768, "max_tokens": 512}),
        "instructor-base": ("local", {"dimension": 768, "max_tokens": 512}),
        "instructor-large": ("local", {"dimension": 768, "max_tokens": 512}),
        "e5-base": ("local", {"dimension": 768, "max_tokens": 512}),
        "e5-large": ("local", {"dimension": 1024, "max_tokens": 512}),
        
        # Mock provider for testing
        "mock-embedding": ("mock", {"dimension": 384, "max_tokens": 1000}),
        
        # Google models
        "text-embedding-004": ("google", {"dimension": 768, "max_tokens": 2048}),
        "embedding-001": ("google", {"dimension": 768, "max_tokens": 2048}),
        "text-embedding-preview-0409": ("google", {"dimension": 768, "max_tokens": 2048}),
        "textembedding-gecko@003": ("google", {"dimension": 768, "max_tokens": 3072}),
        "textembedding-gecko@002": ("google", {"dimension": 768, "max_tokens": 3072}),
        "textembedding-gecko@001": ("google", {"dimension": 768, "max_tokens": 3072}),
        
        # HuggingFace models (NV-Embed-v2 is default for HF)
        "nvidia/NV-Embed-v2": ("huggingface", {"dimension": 4096, "max_tokens": 32768}),
        "nvidia/NV-Embed-v1": ("huggingface", {"dimension": 4096, "max_tokens": 32768}),
        "sentence-transformers/all-MiniLM-L6-v2": ("huggingface", {"dimension": 384, "max_tokens": 256}),
        "sentence-transformers/all-mpnet-base-v2": ("huggingface", {"dimension": 768, "max_tokens": 384}),
        "sentence-transformers/all-distilroberta-v1": ("huggingface", {"dimension": 768, "max_tokens": 512}),
        "sentence-transformers/paraphrase-multilingual-mpnet-base-v2": ("huggingface", {"dimension": 768, "max_tokens": 128}),
        "intfloat/multilingual-e5-large": ("huggingface", {"dimension": 1024, "max_tokens": 512}),
        "BAAI/bge-large-en-v1.5": ("huggingface", {"dimension": 1024, "max_tokens": 512}),
        "BAAI/bge-m3": ("huggingface", {"dimension": 1024, "max_tokens": 8192}),
        "thenlper/gte-large": ("huggingface", {"dimension": 1024, "max_tokens": 512}),
        "jinaai/jina-embeddings-v2-base-en": ("huggingface", {"dimension": 768, "max_tokens": 8192}),
        "microsoft/unixcoder-base": ("huggingface", {"dimension": 768, "max_tokens": 512}),
        "microsoft/codebert-base": ("huggingface", {"dimension": 768, "max_tokens": 512}),
    }
    
    def __init__(self, registry: Optional[ProviderRegistry] = None):
        """
        Initialize factory with optional custom registry
        
        Args:
            registry: Custom provider registry, uses default if None
        """
        self.registry = registry or ProviderRegistry.get_default()
        self._provider_instances: Dict[str, IEmbeddingProvider] = {}
        
    @classmethod
    def create_from_settings(
        cls,
        settings: SemanticSearchSettings
    ) -> IEmbeddingProvider:
        """
        Create provider from semantic search settings
        
        Args:
            settings: Semantic search configuration
            
        Returns:
            Initialized embedding provider
            
        Raises:
            ProviderInitializationError: If provider cannot be created
        """
        factory = cls()
        
        # Create config from settings
        model_config = settings.get_model_config()
        
        config = EmbeddingConfig(
            model_name=settings.embedding_model,
            dimension=settings.embedding_dimension,
            batch_size=settings.batch_size,
            max_tokens=model_config.get("max_tokens", 8192),
            normalize=settings.normalize_embeddings,
            timeout_seconds=settings.timeout_seconds,
            max_retries=settings.max_retries,
            provider_config={
                "api_key": settings.get_api_key_for_provider(settings.embedding_provider),
                "device": settings.local_model_device,
                "cache_dir": settings.local_model_cache_dir
            }
        )
        
        return factory.create_provider(settings.embedding_model, config)
    
    def create_provider(
        self,
        model_name: str,
        config: Optional[EmbeddingConfig] = None
    ) -> IEmbeddingProvider:
        """
        Create an embedding provider for a specific model
        
        Args:
            model_name: Name of the embedding model
            config: Optional custom configuration
            
        Returns:
            Initialized embedding provider instance
            
        Raises:
            ModelNotSupportedError: If model is not recognized
            ProviderNotFoundError: If provider class is not found
            ProviderInitializationError: If provider fails to initialize
        """
        logger.info(f"Creating provider for model: {model_name}")
        
        # Get provider info for model
        provider_info = self._get_provider_info(model_name)
        if not provider_info:
            # Provide helpful suggestions
            available = self.list_available_models()
            suggestions = []
            model_lower = model_name.lower()
            
            # Find similar models
            for model in available:
                if model_lower in model.lower() or model.lower() in model_lower:
                    suggestions.append(model)
            
            error_msg = f"Model '{model_name}' is not in the predefined list.\n"
            if suggestions:
                error_msg += f"Did you mean one of these? {', '.join(suggestions[:5])}\n"
            
            # Check if it might be a HuggingFace model
            if "/" in model_name:
                error_msg += (
                    f"\nThis looks like a HuggingFace model. To use it:\n"
                    f"1. Use the HuggingFace provider directly:\n"
                    f"   provider = factory.create_provider_by_name('huggingface', config)\n"
                    f"2. Or add it to your config with provider='huggingface'"
                )
            else:
                error_msg += f"\nAvailable models: {', '.join(available[:10])}..."
            
            logger.error(f"Model not supported: {model_name}")
            raise ModelNotSupportedError(error_msg)
        
        provider_name, default_config = provider_info
        
        # Create config if not provided
        if not config:
            config = EmbeddingConfig(
                model_name=model_name,
                **default_config
            )
        
        # Get provider class from registry
        provider_class = self.registry.get_provider_class(provider_name)
        if not provider_class:
            raise ProviderNotFoundError(
                f"Provider '{provider_name}' not found in registry. "
                f"Available providers: {', '.join(self.registry.list_providers())}"
            )
        
        # Create provider instance
        try:
            provider = provider_class()
            logger.info(f"Created {provider_name} provider instance for {model_name}")
            return provider
            
        except Exception as e:
            raise ProviderInitializationError(
                f"Failed to create provider '{provider_name}': {str(e)}"
            )
    
    def create_provider_by_name(
        self,
        provider_name: str,
        config: EmbeddingConfig
    ) -> IEmbeddingProvider:
        """
        Create a provider by provider name instead of model name
        
        Args:
            provider_name: Name of the provider (e.g., 'openai', 'voyage')
            config: Provider configuration
            
        Returns:
            Provider instance
            
        Raises:
            ProviderNotFoundError: If provider is not found
        """
        provider_class = self.registry.get_provider_class(provider_name)
        if not provider_class:
            raise ProviderNotFoundError(
                f"Provider '{provider_name}' not found. "
                f"Available: {', '.join(self.registry.list_providers())}"
            )
        
        try:
            provider = provider_class()
            logger.info(f"Created {provider_name} provider by name")
            return provider
            
        except Exception as e:
            raise ProviderInitializationError(
                f"Failed to create provider '{provider_name}': {str(e)}"
            )
    
    def _get_provider_info(self, model_name: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """Get provider info for a model"""
        # First check custom registry
        provider_name = self.registry.get_provider_for_model(model_name)
        if provider_name:
            # Get default config from registry or use minimal config
            models_info = self.registry.get_models_for_provider(provider_name)
            model_config = models_info.get(model_name, {"dimension": 768})
            return (provider_name, model_config)
        
        # Fall back to default mappings
        return self._default_model_mappings.get(model_name)
    
    def list_available_models(self) -> List[str]:
        """List all available models"""
        # Combine registry models and default models
        registry_models = self.registry.list_available_models()
        default_models = list(self._default_model_mappings.keys())
        
        # Return unique models
        all_models = list(set(registry_models + default_models))
        return sorted(all_models)
    
    def list_providers(self) -> List[str]:
        """List all available providers"""
        return self.registry.list_providers()
    
    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """Get detailed information about a model"""
        provider_info = self._get_provider_info(model_name)
        if not provider_info:
            return {"error": f"Model '{model_name}' not found"}
        
        provider_name, config = provider_info
        return {
            "model": model_name,
            "provider": provider_name,
            "dimension": config.get("dimension"),
            "max_tokens": config.get("max_tokens"),
            "supported": True
        }
    
    @classmethod
    def register_model(
        cls,
        model_name: str,
        provider_name: str,
        config: Dict[str, Any]
    ) -> None:
        """
        Register a new model mapping
        
        Args:
            model_name: Name of the model
            provider_name: Provider that supports this model
            config: Model configuration (dimension, max_tokens, etc.)
        """
        cls._default_model_mappings[model_name] = (provider_name, config)
        logger.info(f"Registered model '{model_name}' with provider '{provider_name}'")