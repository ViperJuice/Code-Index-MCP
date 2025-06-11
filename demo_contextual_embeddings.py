#!/usr/bin/env python3
"""Demonstration of the contextual embeddings service."""

import asyncio
import os
from pathlib import Path

from mcp_server.document_processing import (
    DocumentChunk,
    ChunkType,
    ChunkMetadata,
    ContextualEmbeddingService,
    DocumentCategory
)


async def main():
    """Demonstrate contextual embeddings generation."""
    
    # Create service (requires ANTHROPIC_API_KEY environment variable)
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Please set ANTHROPIC_API_KEY environment variable")
        return
    
    service = ContextualEmbeddingService(
        api_key=api_key,
        enable_prompt_caching=True,
        max_concurrent_requests=3
    )
    
    # Create sample chunks from different document types
    chunks = [
        # Code chunk
        DocumentChunk(
            id="chunk_1",
            content="""def calculate_fibonacci(n: int) -> int:
    if n <= 1:
        return n
    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)""",
            type=ChunkType.CODE_BLOCK,
            metadata=ChunkMetadata(
                document_path="/src/math_utils.py",
                section_hierarchy=["Math Utilities", "Fibonacci Functions"],
                chunk_index=0,
                total_chunks=3,
                has_code=True,
                language="python"
            )
        ),
        
        # Documentation chunk
        DocumentChunk(
            id="chunk_2",
            content="""## Installation Guide

To install the MCP Server, you need Python 3.8 or higher. 
First, clone the repository and then install the dependencies:

```bash
pip install -r requirements.txt
```""",
            type=ChunkType.PARAGRAPH,
            metadata=ChunkMetadata(
                document_path="/docs/README.md",
                section_hierarchy=["Getting Started", "Installation Guide"],
                chunk_index=1,
                total_chunks=5,
                has_code=True
            )
        ),
        
        # Configuration chunk
        DocumentChunk(
            id="chunk_3",
            content="""[database]
host = "localhost"
port = 5432
name = "mcp_index"
pool_size = 10
timeout = 30""",
            type=ChunkType.CODE_BLOCK,
            metadata=ChunkMetadata(
                document_path="/config/database.toml",
                section_hierarchy=["Database Configuration"],
                chunk_index=0,
                total_chunks=2,
                has_code=False,
                language="toml"
            )
        )
    ]
    
    # Define progress callback
    def progress_callback(processed: int, total: int):
        print(f"Progress: {processed}/{total} chunks processed")
    
    # Generate contexts for all chunks
    print("Generating contexts for chunks...")
    print("-" * 50)
    
    contexts = await service.generate_contexts_batch(
        chunks,
        document_context={"project": "MCP Server", "version": "1.0.0"},
        progress_callback=progress_callback
    )
    
    # Display results
    print("\n" + "=" * 50)
    print("GENERATED CONTEXTS")
    print("=" * 50)
    
    for chunk in chunks:
        print(f"\nChunk ID: {chunk.id}")
        print(f"Document: {chunk.metadata.document_path}")
        print(f"Type: {chunk.type.value}")
        print(f"Category: {service.detect_document_category(chunk, chunk.metadata.document_path).value}")
        print(f"\nOriginal Content:")
        print(chunk.content)
        print(f"\nGenerated Context:")
        print(contexts[chunk.id])
        print("-" * 50)
    
    # Display metrics
    metrics = service.get_metrics()
    print("\n" + "=" * 50)
    print("PROCESSING METRICS")
    print("=" * 50)
    print(f"Total chunks: {metrics.total_chunks}")
    print(f"Processed chunks: {metrics.processed_chunks}")
    print(f"Cached chunks: {metrics.cached_chunks}")
    print(f"Total input tokens: {metrics.total_tokens_input:,}")
    print(f"Total output tokens: {metrics.total_tokens_output:,}")
    print(f"Estimated cost: ${metrics.total_cost:.4f}")
    print(f"Processing time: {metrics.processing_time:.2f} seconds")
    
    if metrics.errors:
        print(f"\nErrors encountered:")
        for error in metrics.errors:
            print(f"  - {error}")
    
    # Test caching
    print("\n" + "=" * 50)
    print("TESTING CACHE")
    print("=" * 50)
    
    # Process the same chunks again
    print("Processing same chunks again (should use cache)...")
    
    service.current_metrics = service.current_metrics.__class__()  # Reset metrics
    contexts_cached = await service.generate_contexts_batch(chunks)
    
    metrics_cached = service.get_metrics()
    print(f"Cached chunks: {metrics_cached.cached_chunks}/{metrics_cached.total_chunks}")
    print(f"Processing time with cache: {metrics_cached.processing_time:.2f} seconds")
    print(f"Cost with cache: ${metrics_cached.total_cost:.4f}")


if __name__ == "__main__":
    asyncio.run(main())