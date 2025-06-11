#!/usr/bin/env python3
"""
Test script to demonstrate Phase 3: Contextual embeddings for document chunks.
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.plugins.markdown_plugin.plugin import MarkdownPlugin
from mcp_server.plugins.plaintext_plugin.plugin import PlainTextPlugin

def test_contextual_embeddings():
    """Test the enhanced contextual embedding functionality."""
    
    # Initialize storage
    store = SQLiteStore(":memory:")
    
    # Test data with hierarchical structure
    test_markdown = """# Code Index MCP Server Documentation

## Overview

The Code Index MCP Server is a powerful semantic code search tool that integrates with Model Context Protocol (MCP).

## Installation

### Prerequisites

Before installing the Code Index MCP Server, ensure you have:
- Python 3.8 or higher
- Node.js 16 or higher
- Git

### Quick Start

1. Clone the repository:
   ```bash
   git clone https://github.com/your-org/mcp-code-index
   cd mcp-code-index
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

### Environment Variables

The server uses several environment variables for configuration:

- `VOYAGE_API_KEY`: Your Voyage AI API key for embeddings
- `QDRANT_URL`: URL for the Qdrant vector database
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)

### Plugin Configuration

Plugins can be configured through the `plugins.yaml` file:

```yaml
plugins:
  - name: python
    enabled: true
    extensions: [.py, .pyi]
  - name: markdown
    enabled: true
    extensions: [.md, .mdx]
```

## API Reference

### Search Endpoints

#### `search_code`

Search for code symbols using natural language queries.

**Parameters:**
- `query` (string): Natural language search query
- `limit` (int): Maximum number of results (default: 20)
- `semantic` (bool): Use semantic search (default: true)

**Example:**
```python
results = mcp.search_code(
    query="function to parse markdown headers",
    limit=10,
    semantic=True
)
```

### Symbol Lookup

#### `symbol_lookup`

Find exact symbol definitions by name.

**Parameters:**
- `symbol` (string): Symbol name to look up
- `type` (string): Symbol type filter (function, class, etc.)

## Advanced Features

### Semantic Search

The server uses Voyage AI's code-3 embeddings for semantic search capabilities.

### Document Processing

Documents are processed with:
- Intelligent chunking
- Section hierarchy preservation
- Contextual embeddings

## Troubleshooting

### Common Issues

1. **API Key not found**: Ensure VOYAGE_API_KEY is set
2. **Vector DB connection failed**: Check QDRANT_URL
3. **Plugin not loading**: Verify plugin configuration

## Contributing

See CONTRIBUTING.md for guidelines.
"""

    # Create test files
    test_files = {
        "README.md": test_markdown,
        "installation.txt": """Installation Guide

This document provides detailed installation instructions for the Code Index MCP Server.

System Requirements:
- Operating System: Linux, macOS, or Windows
- Python: Version 3.8 or higher
- Memory: At least 4GB RAM recommended
- Disk Space: 2GB for base installation

Step-by-step Installation:

1. Prepare your environment
   First, ensure you have Python installed. You can check this by running:
   python --version

2. Create a virtual environment
   It's recommended to use a virtual environment:
   python -m venv mcp-env
   source mcp-env/bin/activate  # On Windows: mcp-env\\Scripts\\activate

3. Install the package
   You can install via pip:
   pip install mcp-code-index

4. Configure the server
   Copy the example configuration:
   cp config.example.yaml config.yaml
   
   Edit config.yaml with your settings.

5. Verify installation
   Run the test command:
   mcp-server --test

Troubleshooting:
- If you encounter permission errors, try using sudo (Linux/macOS)
- On Windows, run as Administrator if needed
- Check the logs in ~/.mcp/logs/ for detailed error messages
"""
    }
    
    # Initialize plugins
    markdown_plugin = MarkdownPlugin(
        language_config={'name': 'markdown', 'code': 'md'},
        sqlite_store=store,
        enable_semantic=True
    )
    
    plaintext_plugin = PlainTextPlugin(
        language_config={'name': 'plaintext', 'code': 'txt'},
        sqlite_store=store,
        enable_semantic=True
    )
    
    print("Testing Contextual Embeddings Implementation")
    print("=" * 60)
    
    # Index test files
    for filename, content in test_files.items():
        print(f"\nIndexing {filename}...")
        
        if filename.endswith('.md'):
            result = markdown_plugin.indexFile(filename, content)
        else:
            result = plaintext_plugin.indexFile(filename, content)
        
        print(f"  - Indexed {len(result['symbols'])} symbols")
    
    print("\n" + "=" * 60)
    print("Testing Semantic Search with Context")
    print("=" * 60)
    
    # Test queries
    test_queries = [
        "how to install the mcp server",
        "configure voyage api key",
        "search for markdown headers",
        "troubleshooting installation issues",
        "python version requirements"
    ]
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        
        # Search in markdown
        md_results = markdown_plugin.search(query, {'semantic': True, 'limit': 3})
        
        if md_results:
            print("\nMarkdown Results:")
            for i, result in enumerate(md_results, 1):
                print(f"\n  {i}. File: {result['file']}")
                print(f"     Score: {result.get('score', 'N/A'):.3f}")
                
                metadata = result.get('metadata', {})
                if metadata.get('section_hierarchy'):
                    print(f"     Section: {' > '.join(metadata['section_hierarchy'])}")
                elif metadata.get('section'):
                    print(f"     Section: {metadata['section']}")
                
                print(f"     Snippet: {result['snippet'][:100]}...")
                
                # Show context if available
                if result.get('context_before'):
                    print(f"     Context Before: ...{result['context_before'][-50:]}")
                if result.get('context_after'):
                    print(f"     Context After: {result['context_after'][:50]}...")
        
        # Search in plaintext
        txt_results = plaintext_plugin.search(query, {'semantic': True, 'limit': 2})
        
        if txt_results:
            print("\nPlaintext Results:")
            for i, result in enumerate(txt_results, 1):
                print(f"\n  {i}. File: {result['file']}")
                print(f"     Snippet: {result['snippet'][:100]}...")
    
    print("\n" + "=" * 60)
    print("Contextual Embedding Features Demonstrated:")
    print("=" * 60)
    print("✓ Document-level context (title, type, tags)")
    print("✓ Section hierarchy preservation")
    print("✓ Surrounding chunk context (before/after)")
    print("✓ Enhanced metadata in search results")
    print("✓ Contextual text used for embedding generation")
    
    # Demonstrate chunk inspection
    print("\n" + "=" * 60)
    print("Chunk Metadata Example")
    print("=" * 60)
    
    # Get a chunk from the cache to show metadata
    if hasattr(markdown_plugin, '_chunk_cache') and markdown_plugin._chunk_cache:
        file_path, chunks = next(iter(markdown_plugin._chunk_cache.items()))
        if chunks:
            chunk = chunks[0]
            print(f"\nChunk from {file_path}:")
            print(f"  Index: {chunk.chunk_index}")
            print(f"  Content preview: {chunk.content[:80]}...")
            print(f"  Metadata keys: {list(chunk.metadata.keys())}")
            
            if chunk.metadata.get('contextual_text'):
                print(f"\nContextual Text Structure:")
                context_lines = chunk.metadata['contextual_text'].split('\n\n')
                for line in context_lines[:5]:  # Show first 5 lines
                    if line.strip():
                        print(f"  - {line[:80]}...")

if __name__ == "__main__":
    # Set a dummy API key if not present (for testing without actual API)
    if 'VOYAGE_API_KEY' not in os.environ:
        os.environ['VOYAGE_API_KEY'] = 'dummy-key-for-testing'
    
    try:
        test_contextual_embeddings()
    except Exception as e:
        print(f"\nError during testing: {e}")
        import traceback
        traceback.print_exc()