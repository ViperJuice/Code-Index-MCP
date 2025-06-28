#!/usr/bin/env python3
"""Simple demonstration of the contextual embeddings service."""

import asyncio
import os
from pathlib import Path

# Setup paths
import sys
sys.path.insert(0, str(Path(__file__).parent))

from mcp_server.document_processing import (
    DocumentChunk,
    ChunkType,
    ChunkMetadata,
    ContextualEmbeddingService,
    DocumentCategory
)


async def main():
    """Simple demo of contextual embeddings."""
    
    print("Contextual Embeddings Service Demo")
    print("=" * 50)
    
    # Create service (will use mock mode if anthropic not installed)
    service = ContextualEmbeddingService()
    
    # Create sample chunks
    chunks = [
        DocumentChunk(
            id="chunk_1",
            content="""def calculate_prime_factors(n):
    factors = []
    d = 2
    while d * d <= n:
        while (n % d) == 0:
            factors.append(d)
            n //= d
        d += 1
    if n > 1:
        factors.append(n)
    return factors""",
            type=ChunkType.CODE_BLOCK,
            metadata=ChunkMetadata(
                document_path="/src/math_utils.py",
                section_hierarchy=["Math Utilities", "Prime Numbers"],
                chunk_index=0,
                total_chunks=1,
                has_code=True,
                language="python"
            )
        ),
        
        DocumentChunk(
            id="chunk_2",
            content="""# Getting Started with MCP Server

This guide will help you set up and run the MCP Server for the first time.

## Prerequisites

- Python 3.8 or higher
- pip package manager
- Git""",
            type=ChunkType.PARAGRAPH,
            metadata=ChunkMetadata(
                document_path="/docs/getting-started.md",
                section_hierarchy=["Getting Started"],
                chunk_index=0,
                total_chunks=3,
                has_code=False
            )
        ),
        
        DocumentChunk(
            id="chunk_3",
            content="""server:
  host: 0.0.0.0
  port: 8080
  workers: 4
  
database:
  url: postgresql://localhost/mcp
  pool_size: 10""",
            type=ChunkType.CODE_BLOCK,
            metadata=ChunkMetadata(
                document_path="/config/server.yaml",
                section_hierarchy=["Server Configuration"],
                chunk_index=0,
                total_chunks=1,
                has_code=False,
                language="yaml"
            )
        )
    ]
    
    # Test document category detection
    print("\nDocument Category Detection:")
    print("-" * 50)
    for chunk in chunks:
        category = service.detect_document_category(chunk, chunk.metadata.document_path)
        print(f"{chunk.metadata.document_path}: {category.value}")
    
    # Generate contexts
    print("\n\nGenerating Contexts:")
    print("-" * 50)
    
    contexts = await service.generate_contexts_batch(
        chunks,
        progress_callback=lambda p, t: print(f"Progress: {p}/{t}", end='\r')
    )
    
    print("\n")
    
    # Display results
    print("\nGenerated Contexts:")
    print("=" * 50)
    
    for chunk in chunks:
        print(f"\nFile: {chunk.metadata.document_path}")
        print(f"Type: {chunk.type.value}")
        print(f"Category: {service.detect_document_category(chunk, chunk.metadata.document_path).value}")
        print(f"\nContent:")
        print(chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content)
        print(f"\nGenerated Context:")
        print(contexts[chunk.id])
        print("-" * 50)
    
    # Test caching
    print("\nTesting Cache:")
    print("=" * 50)
    
    # Reset metrics
    service.current_metrics = service.current_metrics.__class__()
    
    # Process same chunks again
    contexts_cached = await service.generate_contexts_batch(chunks)
    
    metrics = service.get_metrics()
    print(f"Total chunks: {metrics.total_chunks}")
    print(f"Cached chunks: {metrics.cached_chunks}")
    print(f"Cache hit rate: {metrics.cached_chunks/metrics.total_chunks*100:.1f}%")
    
    # Test prompt templates
    print("\n\nPrompt Template Examples:")
    print("=" * 50)
    
    for category in [DocumentCategory.CODE, DocumentCategory.DOCUMENTATION, DocumentCategory.CONFIGURATION]:
        template = service.template_registry.get_template(category)
        print(f"\n{category.value.upper()} Template:")
        print(f"System: {template.system_prompt[:100]}...")
        
    print("\n\n✅ Demo completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())