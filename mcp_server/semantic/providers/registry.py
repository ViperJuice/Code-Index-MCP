"""
Provider Registry

Central registry for embedding providers with dynamic registration support.
"""

from typing import Dict, Type, Optional, List, Any
import logging
from threading import Lock

from mcp_server.interfaces.embedding_interfaces import IEmbeddingProvider
from .exceptions import ProviderError

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """Registry for embedding provider implementations"""
    
    _instance: Optional['ProviderRegistry'] = None
    _lock = Lock()
    
    def __init__(self):
        """Initialize empty registry"""
        self._providers: Dict[str, Type[IEmbeddingProvider]] = {}
        self._model_mappings: Dict[str, str] = {}  # model -> provider
        self._provider_models: Dict[str, Dict[str, Dict[str, Any]]] = {}  # provider -> models -> config
        
    @classmethod
    def get_default(cls) -> 'ProviderRegistry':
        """Get singleton default registry instance"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
                    cls._instance._register_builtin_providers()
        return cls._instance
    
    def _register_builtin_providers(self) -> None:
        """Register built-in providers"""
        logger.info("Registering built-in providers")
        
        # Import providers here to avoid circular imports
        from .voyage_provider import VoyageProvider
        from .openai_provider import OpenAIProvider
        from .cohere_provider import CohereProvider
        from .local_provider import LocalProvider
        from .mock_provider import MockProvider
        from .google_provider import GoogleProvider
        from .huggingface_provider import HuggingFaceProvider
        
        # Register Voyage AI provider
        self.register_provider(
            "voyage",
            VoyageProvider,
            VoyageProvider.get_supported_models()
        )
        
        # Register OpenAI provider
        self.register_provider(
            "openai",
            OpenAIProvider,
            OpenAIProvider.get_supported_models()
        )
        
        # Register Cohere provider
        self.register_provider(
            "cohere",
            CohereProvider,
            CohereProvider.get_supported_models()
        )
        
        # Register local provider
        self.register_provider(
            "local",
            LocalProvider,
            LocalProvider.get_supported_models()
        )
        
        # Register mock provider for testing
        self.register_provider(
            "mock",
            MockProvider,
            MockProvider.get_supported_models()
        )
        
        # Register Google provider
        self.register_provider(
            "google",
            GoogleProvider,
            GoogleProvider.get_supported_models()
        )
        
        # Register HuggingFace provider
        self.register_provider(
            "huggingface",
            HuggingFaceProvider,
            HuggingFaceProvider.get_supported_models()
        )
    
    def register_provider(
        self,
        name: str,
        provider_class: Type[IEmbeddingProvider],
        models: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> None:
        """
        Register a provider with optional model configurations
        
        Args:
            name: Unique name for the provider
            provider_class: Provider class implementing IEmbeddingProvider
            models: Optional dict of model_name -> config
        """
        if name in self._providers:
            logger.warning(f"Overwriting existing provider: {name}")
        
        # Validate provider class
        if not issubclass(provider_class, IEmbeddingProvider):
            raise ProviderError(
                f"Provider class {provider_class.__name__} must implement IEmbeddingProvider"
            )
        
        self._providers[name] = provider_class
        
        # Register model mappings
        if models:
            self._provider_models[name] = models
            for model_name in models:
                if model_name in self._model_mappings:
                    logger.warning(
                        f"Model '{model_name}' already registered with provider "
                        f"'{self._model_mappings[model_name]}', overwriting with '{name}'"
                    )
                self._model_mappings[model_name] = name
        
        logger.info(
            f"Registered provider '{name}' with {len(models or {})} models"
        )
    
    def unregister_provider(self, name: str) -> bool:
        """
        Unregister a provider
        
        Args:
            name: Provider name to unregister
            
        Returns:
            True if provider was removed, False if not found
        """
        if name not in self._providers:
            return False
        
        # Remove provider
        del self._providers[name]
        
        # Remove model mappings
        models_to_remove = [
            model for model, provider in self._model_mappings.items() 
            if provider == name
        ]
        for model in models_to_remove:
            del self._model_mappings[model]
        
        # Remove provider models
        if name in self._provider_models:
            del self._provider_models[name]
        
        logger.info(f"Unregistered provider '{name}' and {len(models_to_remove)} models")
        return True
    
    def get_provider_class(self, name: str) -> Optional[Type[IEmbeddingProvider]]:
        """
        Get provider class by name
        
        Args:
            name: Provider name
            
        Returns:
            Provider class or None if not found
        """
        return self._providers.get(name)
    
    def get_provider_for_model(self, model_name: str) -> Optional[str]:
        """
        Get provider name for a specific model
        
        Args:
            model_name: Model name
            
        Returns:
            Provider name or None if model not found
        """
        return self._model_mappings.get(model_name)
    
    def get_models_for_provider(self, provider_name: str) -> Dict[str, Dict[str, Any]]:
        """
        Get all models supported by a provider
        
        Args:
            provider_name: Provider name
            
        Returns:
            Dict of model_name -> config
        """
        return self._provider_models.get(provider_name, {})
    
    def list_providers(self) -> List[str]:
        """List all registered provider names"""
        return sorted(list(self._providers.keys()))
    
    def list_available_models(self) -> List[str]:
        """List all available model names"""
        return sorted(list(self._model_mappings.keys()))
    
    def get_provider_info(self, name: str) -> Dict[str, Any]:
        """
        Get detailed information about a provider
        
        Args:
            name: Provider name
            
        Returns:
            Provider information dict
        """
        if name not in self._providers:
            return {"error": f"Provider '{name}' not found"}
        
        provider_class = self._providers[name]
        models = self.get_models_for_provider(name)
        
        return {
            "name": name,
            "class": provider_class.__name__,
            "module": provider_class.__module__,
            "models": list(models.keys()),
            "model_count": len(models)
        }
    
    def clear(self) -> None:
        """Clear all registrations (useful for testing)"""
        self._providers.clear()
        self._model_mappings.clear()
        self._provider_models.clear()
        logger.info("Cleared provider registry")
    
    def __contains__(self, provider_name: str) -> bool:
        """Check if provider is registered"""
        return provider_name in self._providers
    
    def __len__(self) -> int:
        """Get number of registered providers"""
        return len(self._providers)