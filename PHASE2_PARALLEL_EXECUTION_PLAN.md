# Phase 2 Parallel Execution Plan: Provider Implementations

## Overview
Phase 2 implements concrete embedding providers using the infrastructure from Phase 1. All providers can be implemented in parallel since they share the same interface.

## Parallel Task Groups

### Group A: API-Based Providers (Independent)
**Files to create simultaneously:**
1. `mcp_server/semantic/providers/voyage_provider.py` - Voyage AI implementation
2. `mcp_server/semantic/providers/openai_provider.py` - OpenAI implementation
3. `mcp_server/semantic/providers/cohere_provider.py` - Cohere implementation

### Group B: Local & Test Providers (Independent)
**Files to create simultaneously:**
1. `mcp_server/semantic/providers/local_provider.py` - Sentence Transformers implementation
2. `mcp_server/semantic/providers/mock_provider.py` - Mock provider for testing
3. `mcp_server/semantic/providers/anthropic_provider.py` - Anthropic placeholder (future)

### Group C: Integration Updates (Independent)
**Files to modify simultaneously:**
1. Update `mcp_server/semantic/providers/__init__.py` - Export all providers
2. Update `mcp_server/semantic/providers/registry.py` - Register built-in providers
3. Create `mcp_server/semantic/providers/provider_tests.py` - Basic provider tests

### Group D: Refactoring Existing Code (Dependent on A1)
**Files to modify after Voyage provider is ready:**
1. Refactor `mcp_server/semantic/enhanced/batch_indexer.py` - Use provider factory
2. Refactor `mcp_server/utils/semantic_indexer.py` - Use provider factory
3. Create migration guide documentation

## Execution Timeline
- Groups A, B, C can execute in parallel
- Group D depends on Group A completion (specifically Voyage provider)
- Estimated time: 45-60 minutes for Groups A, B, C
- Additional 20 minutes for Group D

## Task Details

### Group A: API Providers
Each provider will:
- Inherit from `BaseEmbeddingProvider`
- Implement `_initialize_provider()` and `_embed_batch_impl()`
- Handle API-specific authentication
- Map embedding types to provider-specific formats
- Handle rate limiting and errors

### Group B: Local/Test Providers
- **Local**: Use sentence-transformers library
- **Mock**: Return deterministic embeddings for testing
- **Anthropic**: Placeholder for future Claude embeddings

### Group C: Integration
- Update exports to include all providers
- Register providers with model mappings
- Create basic unit tests

### Group D: Refactoring
- Replace hardcoded Voyage AI usage with factory
- Maintain backward compatibility
- Update configuration examples

## Implementation Pattern

Each provider follows this structure:
```python
class ProviderNameProvider(BaseEmbeddingProvider):
    async def _initialize_provider(self) -> Result[None]:
        # Provider-specific initialization
        
    async def _embed_batch_impl(
        self,
        texts: List[str],
        embedding_type: EmbeddingType
    ) -> Result[EmbeddingResult]:
        # Provider-specific implementation
        
    async def validate_api_key(self) -> Result[bool]:
        # API key validation
```

## Dependencies to Install
```bash
pip install voyageai openai cohere sentence-transformers
```

## Success Criteria
- All providers implement the interface correctly
- Each provider handles its specific API quirks
- Mock provider enables testing without API calls
- Existing code refactored to use new system
- No breaking changes for current users