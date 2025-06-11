#!/usr/bin/env python3
"""Integration demo showing contextual embeddings with document processing pipeline."""

import asyncio
import os
from pathlib import Path

from mcp_server.document_processing import (
    DocumentChunk,
    ChunkType,
    ChunkMetadata,
    SemanticChunker,
    create_semantic_chunker,
    ContextualEmbeddingService,
    DocumentCategory
)
from mcp_server.plugins.markdown_plugin import MarkdownPlugin
from mcp_server.plugins.plaintext_plugin import PlaintextPlugin


async def process_document_with_context(file_path: str, service: ContextualEmbeddingService):
    """Process a document and generate contextual embeddings for its chunks."""
    
    print(f"\nProcessing: {file_path}")
    print("=" * 70)
    
    # Determine plugin based on file extension
    if file_path.endswith('.md'):
        plugin = MarkdownPlugin()
    else:
        plugin = PlaintextPlugin()
    
    # Read file content
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Process document to get chunks
    processed_doc = plugin.process_document(file_path, content)
    
    # Create semantic chunker for better chunking
    chunker = create_semantic_chunker()
    
    # Get chunks from processed document
    chunks = processed_doc.chunks
    
    print(f"Document has {len(chunks)} chunks")
    
    # Generate contexts for all chunks
    document_context = {
        "file_name": Path(file_path).name,
        "total_sections": len(processed_doc.structure.sections),
        "document_type": processed_doc.metadata.get("document_type", "unknown")
    }
    
    def progress_callback(processed: int, total: int):
        print(f"  Progress: {processed}/{total} chunks", end='\r')
    
    contexts = await service.generate_contexts_batch(
        chunks,
        document_context=document_context,
        progress_callback=progress_callback
    )
    
    print()  # New line after progress
    
    # Display sample results
    print("\nSample chunks with generated contexts:")
    print("-" * 70)
    
    # Show first 3 chunks
    for i, chunk in enumerate(chunks[:3]):
        print(f"\nChunk {i+1}:")
        print(f"  Type: {chunk.type.value}")
        print(f"  Section: {' > '.join(chunk.metadata.section_hierarchy)}")
        print(f"  Content preview: {chunk.content[:100]}...")
        print(f"  Generated context: {contexts.get(chunk.id, 'No context generated')}")
    
    return contexts


async def main():
    """Main demo function."""
    
    # Check for API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("⚠️  ANTHROPIC_API_KEY not set. Using mock mode for demonstration.")
        print("To use real Claude API, set: export ANTHROPIC_API_KEY=your_key")
        print()
        
        # Create mock service for demo
        from unittest.mock import AsyncMock, MagicMock
        import sys
        sys.modules['anthropic'] = MagicMock()
        
        # Reload to get mocked version
        import importlib
        import mcp_server.document_processing.contextual_embeddings
        importlib.reload(mcp_server.document_processing.contextual_embeddings)
        from mcp_server.document_processing.contextual_embeddings import ContextualEmbeddingService
        
        service = ContextualEmbeddingService(api_key="mock")
        
        # Mock the generate_context_for_chunk method
        async def mock_generate_context(chunk, document_context=None, category=None):
            # Generate mock context based on chunk type
            if chunk.type == ChunkType.CODE_BLOCK:
                return f"Code implementation for {chunk.metadata.section_hierarchy[-1] if chunk.metadata.section_hierarchy else 'main'} functionality", False
            elif chunk.type == ChunkType.HEADING:
                return f"Section introducing {chunk.content.strip('#').strip()}", False
            else:
                words = chunk.content.split()[:10]
                return f"Content about {' '.join(words)}...", False
        
        service.generate_context_for_chunk = mock_generate_context
    else:
        service = ContextualEmbeddingService(
            api_key=api_key,
            enable_prompt_caching=True,
            max_concurrent_requests=3
        )
    
    print("Contextual Embeddings Integration Demo")
    print("=" * 70)
    
    # Create test files if they don't exist
    test_dir = Path("test_data/contextual_demo")
    test_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a Python file
    python_file = test_dir / "example.py"
    python_file.write_text("""#!/usr/bin/env python3
\"\"\"Example Python module for demonstrating contextual embeddings.\"\"\"

def calculate_fibonacci(n: int) -> int:
    \"\"\"Calculate the nth Fibonacci number recursively.\"\"\"
    if n <= 1:
        return n
    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)

def factorial(n: int) -> int:
    \"\"\"Calculate factorial of n.\"\"\"
    if n <= 1:
        return 1
    return n * factorial(n-1)

class MathOperations:
    \"\"\"Class containing various mathematical operations.\"\"\"
    
    @staticmethod
    def gcd(a: int, b: int) -> int:
        \"\"\"Calculate greatest common divisor.\"\"\"
        while b:
            a, b = b, a % b
        return a
    
    @staticmethod
    def lcm(a: int, b: int) -> int:
        \"\"\"Calculate least common multiple.\"\"\"
        return abs(a * b) // MathOperations.gcd(a, b)
""")
    
    # Create a Markdown file
    markdown_file = test_dir / "documentation.md"
    markdown_file.write_text("""# MCP Server Documentation

## Overview

The MCP Server is a high-performance code indexing system designed for semantic search and code understanding.

## Installation

To install the MCP Server, follow these steps:

1. Clone the repository:
   ```bash
   git clone https://github.com/your-org/mcp-server.git
   cd mcp-server
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure your environment:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

## Configuration

The server can be configured using environment variables or a configuration file.

### Environment Variables

- `MCP_PORT`: Server port (default: 8080)
- `MCP_HOST`: Server host (default: 0.0.0.0)
- `ANTHROPIC_API_KEY`: API key for Claude integration

### Configuration File

You can also use a YAML configuration file:

```yaml
server:
  host: 0.0.0.0
  port: 8080
  
indexing:
  batch_size: 100
  max_workers: 4
```

## Usage

Start the server with:

```bash
python -m mcp_server
```

The server will be available at `http://localhost:8080`.
""")
    
    # Process both files
    for file_path in [python_file, markdown_file]:
        await process_document_with_context(str(file_path), service)
    
    # Display metrics
    if hasattr(service, 'get_metrics'):
        metrics = service.get_metrics()
        print("\n" + "=" * 70)
        print("OVERALL METRICS")
        print("=" * 70)
        print(f"Total chunks processed: {metrics.processed_chunks}")
        print(f"Chunks from cache: {metrics.cached_chunks}")
        print(f"Total processing time: {metrics.processing_time:.2f}s")
        
        if api_key and api_key != "mock":
            print(f"Total tokens used: {metrics.total_tokens_input + metrics.total_tokens_output:,}")
            print(f"Estimated cost: ${metrics.total_cost:.4f}")
    
    print("\n✅ Demo completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())