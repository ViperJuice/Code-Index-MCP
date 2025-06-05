"""
Basic Provider Tests

Quick tests to verify provider implementations work correctly.
"""

import asyncio
import pytest
from typing import List

from mcp_server.interfaces.embedding_interfaces import (
    EmbeddingConfig,
    EmbeddingType
)
from mcp_server.semantic.providers import (
    EmbeddingProviderFactory,
    ProviderRegistry,
    MockProvider
)


async def test_mock_provider():
    """Test mock provider basic functionality"""
    # Create mock provider
    config = EmbeddingConfig(
        model_name="mock-embedding",
        dimension=384,
        batch_size=10
    )
    
    provider = MockProvider()
    
    # Initialize
    init_result = await provider.initialize(config)
    assert init_result.is_ok(), f"Failed to initialize: {init_result.error_value}"
    
    # Test embedding generation
    texts = ["Hello world", "Code embeddings", "Test data"]
    result = await provider.embed_batch(texts, EmbeddingType.DOCUMENT)
    
    assert result.is_ok(), f"Failed to generate embeddings: {result.error_value}"
    
    embeddings = result.value
    assert len(embeddings.embeddings) == 3
    assert embeddings.dimension == 384
    assert embeddings.provider == "mock"
    
    # Cleanup
    await provider.cleanup()
    print("✓ Mock provider test passed")


async def test_factory_creation():
    """Test factory can create providers"""
    factory = EmbeddingProviderFactory()
    
    # Test creating mock provider
    config = EmbeddingConfig(
        model_name="mock-embedding",
        dimension=384
    )
    
    provider = factory.create_provider("mock-embedding", config)
    assert provider is not None
    assert isinstance(provider, MockProvider)
    
    print("✓ Factory creation test passed")


async def test_registry():
    """Test registry functionality"""
    registry = ProviderRegistry.get_default()
    
    # Check providers are registered
    providers = registry.list_providers()
    expected_providers = ["cohere", "google", "huggingface", "local", "mock", "openai", "voyage"]
    assert providers == expected_providers, f"Expected {expected_providers}, got {providers}"
    
    # Check model mappings
    assert registry.get_provider_for_model("voyage-code-3") == "voyage"
    assert registry.get_provider_for_model("text-embedding-3-small") == "openai"
    assert registry.get_provider_for_model("mock-embedding") == "mock"
    
    print("✓ Registry test passed")


async def test_deterministic_embeddings():
    """Test mock provider generates deterministic embeddings"""
    config = EmbeddingConfig(
        model_name="mock-embedding",
        dimension=384,
        provider_config={"deterministic": True}
    )
    
    provider = MockProvider()
    await provider.initialize(config)
    
    # Generate embeddings twice for same text
    text = ["This is a test"]
    result1 = await provider.embed_batch(text, EmbeddingType.DOCUMENT)
    result2 = await provider.embed_batch(text, EmbeddingType.DOCUMENT)
    
    assert result1.is_ok() and result2.is_ok()
    
    # Should be identical
    emb1 = result1.value.embeddings[0]
    emb2 = result2.value.embeddings[0]
    assert emb1 == emb2, "Deterministic embeddings should be identical"
    
    # Different text should give different embeddings
    result3 = await provider.embed_batch(["Different text"], EmbeddingType.DOCUMENT)
    assert result3.is_ok()
    emb3 = result3.value.embeddings[0]
    assert emb1 != emb3, "Different texts should have different embeddings"
    
    await provider.cleanup()
    print("✓ Deterministic embeddings test passed")


async def main():
    """Run all tests"""
    print("Running provider tests...\n")
    
    await test_mock_provider()
    await test_factory_creation()
    await test_registry()
    await test_deterministic_embeddings()
    
    print("\n✅ All tests passed!")


if __name__ == "__main__":
    asyncio.run(main())