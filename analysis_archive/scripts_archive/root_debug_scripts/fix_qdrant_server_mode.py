#!/usr/bin/env python3
"""Update semantic indexer to use Qdrant server mode."""

import os

def create_qdrant_init_patch():
    """Create a patch for Qdrant initialization to support server mode."""
    
    patch_content = '''--- a/mcp_server/utils/semantic_indexer.py
+++ b/mcp_server/utils/semantic_indexer.py
@@ -75,17 +75,46 @@ class SemanticIndexer:
         self.metadata_file = ".index_metadata.json"
         self.path_resolver = path_resolver or PathResolver()
 
-        # Support both memory and HTTP URLs
-        if qdrant_path.startswith("http"):
-            # For HTTP URLs, parse properly
-            self.qdrant = QdrantClient(url=qdrant_path)
-        elif qdrant_path == ":memory:":
-            # Memory mode
-            self.qdrant = QdrantClient(location=":memory:")
-        else:
-            # Local file path - use path parameter to avoid IDNA issues
-            self.qdrant = QdrantClient(path=qdrant_path)
+        # Initialize Qdrant client with server mode preference
+        self.qdrant = self._init_qdrant_client(qdrant_path)
         self.wrapper = TreeSitterWrapper()
+        
+    def _init_qdrant_client(self, qdrant_path: str) -> QdrantClient:
+        """Initialize Qdrant client with server mode preference."""
+        # First, try server mode (recommended for concurrent access)
+        server_url = os.environ.get("QDRANT_URL", "http://localhost:6333")
+        
+        if os.environ.get("QDRANT_USE_SERVER", "true").lower() == "true":
+            try:
+                # Try connecting to Qdrant server
+                client = QdrantClient(url=server_url, timeout=5)
+                # Test connection
+                client.get_collections()
+                logger.info(f"Connected to Qdrant server at {server_url}")
+                return client
+            except Exception as e:
+                logger.warning(f"Qdrant server not available at {server_url}: {e}")
+        
+        # Support explicit HTTP URLs
+        if qdrant_path.startswith("http"):
+            return QdrantClient(url=qdrant_path)
+        
+        # Memory mode
+        if qdrant_path == ":memory:":
+            return QdrantClient(location=":memory:")
+        
+        # Local file path with lock cleanup
+        try:
+            # Clean up any stale locks
+            lock_file = Path(qdrant_path) / ".lock"
+            if lock_file.exists():
+                logger.warning(f"Removing stale Qdrant lock file: {lock_file}")
+                lock_file.unlink()
+            
+            client = QdrantClient(path=qdrant_path)
+            logger.info(f"Using file-based Qdrant at {qdrant_path}")
+            return client
+        except Exception as e:
+            logger.error(f"Failed to initialize Qdrant: {e}")
+            raise
 
         # Initialize Voyage AI client with proper API key handling
         api_key = os.environ.get("VOYAGE_API_KEY") or os.environ.get(
'''
    
    with open("qdrant_server_mode.patch", "w") as f:
        f.write(patch_content)
    
    print("Created patch file: qdrant_server_mode.patch")
    print("\nTo apply the patch:")
    print("  patch -p1 < qdrant_server_mode.patch")
    print("\nOr manually apply the changes to:")
    print("  mcp_server/utils/semantic_indexer.py")


def create_docker_compose_qdrant():
    """Create a docker-compose file for running Qdrant server."""
    
    compose_content = """version: '3.8'

services:
  qdrant:
    image: qdrant/qdrant:latest
    container_name: mcp_qdrant
    restart: unless-stopped
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - ./qdrant_storage:/qdrant/storage:z
    environment:
      - QDRANT__SERVICE__GRPC_PORT=6334
"""
    
    with open("docker-compose.qdrant.yml", "w") as f:
        f.write(compose_content)
    
    print("\nCreated docker-compose.qdrant.yml")
    print("\nTo start Qdrant server:")
    print("  docker-compose -f docker-compose.qdrant.yml up -d")
    print("\nTo stop Qdrant server:")
    print("  docker-compose -f docker-compose.qdrant.yml down")


def create_qdrant_test_script():
    """Create a test script for Qdrant functionality."""
    
    test_content = '''#!/usr/bin/env python3
"""Test Qdrant server connectivity and semantic search."""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set environment to use server mode
os.environ["QDRANT_USE_SERVER"] = "true"
os.environ["QDRANT_URL"] = "http://localhost:6333"


def test_qdrant_connection():
    """Test basic Qdrant connectivity."""
    try:
        from qdrant_client import QdrantClient
        
        print("Testing Qdrant connection...")
        client = QdrantClient(url="http://localhost:6333", timeout=5)
        
        # Test connection
        collections = client.get_collections()
        print(f"✓ Connected to Qdrant server")
        print(f"  Collections: {len(collections.collections)}")
        
        for collection in collections.collections:
            info = client.get_collection(collection.name)
            print(f"  - {collection.name}: {info.vectors_count} vectors")
        
        return True
        
    except Exception as e:
        print(f"✗ Failed to connect to Qdrant: {e}")
        print("\\nMake sure Qdrant server is running:")
        print("  docker-compose -f docker-compose.qdrant.yml up -d")
        return False


def test_semantic_search():
    """Test semantic search functionality."""
    if not test_qdrant_connection():
        return
    
    # Check for Voyage API key
    if not os.environ.get("VOYAGE_API_KEY") and not os.environ.get("VOYAGE_AI_API_KEY"):
        print("\\n⚠️  No Voyage AI API key found")
        print("Set VOYAGE_AI_API_KEY environment variable to test semantic search")
        return
    
    try:
        from mcp_server.utils.semantic_indexer import SemanticIndexer
        
        print("\\nTesting semantic indexer...")
        indexer = SemanticIndexer()
        
        # Test search
        results = indexer.search("function definition", limit=5)
        print(f"✓ Semantic search returned {len(results)} results")
        
        if results:
            print("\\nSample results:")
            for i, result in enumerate(results[:3]):
                print(f"  {i+1}. {result.get('file_path', 'Unknown')}")
                print(f"     Score: {result.get('score', 0):.3f}")
        
    except Exception as e:
        print(f"✗ Semantic search error: {e}")


if __name__ == "__main__":
    test_semantic_search()
'''
    
    with open("test_qdrant_server.py", "w") as f:
        f.write(test_content)
    
    os.chmod("test_qdrant_server.py", 0o755)
    
    print("\nCreated test_qdrant_server.py")
    print("\nTo test Qdrant:")
    print("  python test_qdrant_server.py")


if __name__ == "__main__":
    create_qdrant_init_patch()
    create_docker_compose_qdrant()
    create_qdrant_test_script()
    
    print("\n" + "="*60)
    print("NEXT STEPS:")
    print("="*60)
    print("1. Start Qdrant server:")
    print("   docker-compose -f docker-compose.qdrant.yml up -d")
    print("\n2. Apply the patch:")
    print("   patch -p1 < qdrant_server_mode.patch")
    print("\n3. Test the connection:")
    print("   python test_qdrant_server.py")
    print("\n4. Set environment variables in .env:")
    print("   QDRANT_USE_SERVER=true")
    print("   QDRANT_URL=http://localhost:6333")
    print("   VOYAGE_AI_API_KEY=your_key_here")