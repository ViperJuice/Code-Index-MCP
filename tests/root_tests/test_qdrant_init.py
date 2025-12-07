#!/usr/bin/env python3
"""Test Qdrant initialization to debug IDNA error."""

import os

from dotenv import load_dotenv

load_dotenv()

# Test different Qdrant client initialization methods
print("Testing Qdrant initialization...")

try:
    from qdrant_client import QdrantClient

    # Test 1: Local path
    print("\n1. Testing local path initialization:")
    try:
        client = QdrantClient(location="./vector_index.qdrant")
        print("✅ Local path works!")
    except Exception as e:
        print(f"❌ Local path failed: {e}")

    # Test 2: Memory mode
    print("\n2. Testing memory mode:")
    try:
        client = QdrantClient(location=":memory:")
        print("✅ Memory mode works!")
    except Exception as e:
        print(f"❌ Memory mode failed: {e}")

    # Test 3: Check if it's trying to connect to a URL
    print("\n3. Checking environment variables:")
    print(f"QDRANT_HOST: {os.getenv('QDRANT_HOST')}")
    print(f"QDRANT_PORT: {os.getenv('QDRANT_PORT')}")

    # Test 4: Try with explicit path
    print("\n4. Testing with Path object:")
    try:
        from pathlib import Path

        client = QdrantClient(path=str(Path("./vector_index.qdrant").absolute()))
        print("✅ Path object works!")
    except Exception as e:
        print(f"❌ Path object failed: {e}")

except Exception as e:
    print(f"Failed to import qdrant_client: {e}")

# Now test the SemanticIndexer
print("\n\nTesting SemanticIndexer initialization...")
try:
    from mcp_server.utils.semantic_indexer import SemanticIndexer

    # Try with explicit local path
    indexer = SemanticIndexer(
        collection="code-embeddings", qdrant_path=":memory:"  # Use memory mode to avoid IDNA error
    )
    print("✅ SemanticIndexer initialized successfully!")

except Exception as e:
    print(f"❌ SemanticIndexer failed: {e}")
    import traceback

    traceback.print_exc()
