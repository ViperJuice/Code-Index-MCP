#!/usr/bin/env python3
"""
Populate semantic index for the current codebase.
This will create embeddings for the current repository in the correct collection.
"""

import os
import sys
import json
import sqlite3
from pathlib import Path
from typing import List, Dict, Any
import logging
from datetime import datetime
from mcp_server.core.path_utils import PathUtils

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server.utils.semantic_discovery import SemanticDatabaseDiscovery

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def populate_semantic_index():
    """Populate semantic index for the current codebase."""
    print("=" * 60)
    print("POPULATING SEMANTIC INDEX FOR CURRENT CODEBASE")
    print("=" * 60)
    
    # Step 1: Discovery and setup
    workspace_root = Path.cwd()
    discovery = SemanticDatabaseDiscovery(workspace_root)
    
    repo_id = discovery.get_repository_identifier()
    print(f"Repository ID: {repo_id}")
    
    # Get the collection configuration
    qdrant_path, collection_name = discovery.get_default_collection_config()
    print(f"Target collection: {collection_name}")
    print(f"Qdrant path: {qdrant_path}")
    
    # Check if Voyage AI API key is available
    api_key = os.environ.get("VOYAGE_AI_API_KEY")
    if not api_key:
        print("❌ VOYAGE_AI_API_KEY environment variable not set")
        print("   Semantic search requires Voyage AI for embeddings")
        print("   Set the API key to populate semantic index")
        return False
    
    print("✅ Voyage AI API key found")
    
    # Step 2: Check if we can connect to Qdrant
    try:
        from qdrant_client import QdrantClient, models
        from qdrant_client.http.models import PointStruct
        import voyageai
        
        # Remove stale lock if it exists
        lock_file = Path(qdrant_path) / ".lock"
        if lock_file.exists():
            try:
                lock_file.unlink()
                print(f"Removed stale lock: {lock_file}")
            except OSError:
                pass
        
        client = QdrantClient(path=qdrant_path)
        voyage_client = voyageai.Client(api_key=api_key)
        print("✅ Connected to Qdrant and Voyage AI")
        
    except ImportError as e:
        print(f"❌ Missing dependencies: {e}")
        print("   Install with: pip install qdrant-client voyageai")
        return False
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        return False
    
    # Step 3: Ensure collection exists
    try:
        client.get_collection(collection_name)
        print(f"✅ Collection '{collection_name}' exists")
    except:
        print(f"Creating collection '{collection_name}'...")
        client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=1024,  # Voyage Code 3 dimension
                distance=models.Distance.COSINE
            )
        )
        print(f"✅ Created collection '{collection_name}'")
    
    # Step 4: Get data from SQL index
    sql_db_path = Path(f".indexes/{repo_id}/current.db")
    if not sql_db_path.exists():
        print(f"❌ SQL database not found at: {sql_db_path}")
        return False
    
    print(f"✅ SQL database found: {sql_db_path}")
    
    # Step 5: Extract and process files
    conn = sqlite3.connect(sql_db_path)
    cursor = conn.cursor()
    
    try:
        # Get code files for semantic indexing
        cursor.execute("""
            SELECT DISTINCT filepath, content 
            FROM bm25_content 
            WHERE content IS NOT NULL 
            AND content != ''
            AND (
                filepath LIKE '%.py' OR
                filepath LIKE '%.js' OR
                filepath LIKE '%.ts' OR
                filepath LIKE '%.java' OR
                filepath LIKE '%.go' OR
                filepath LIKE '%.rs' OR
                filepath LIKE '%.cpp' OR
                filepath LIKE '%.c' OR
                filepath LIKE '%.h' OR
                filepath LIKE '%.cs' OR
                filepath LIKE '%.rb' OR
                filepath LIKE '%.php' OR
                filepath LIKE '%.swift' OR
                filepath LIKE '%.kt' OR
                filepath LIKE '%.scala'
            )
            LIMIT 100
        """)
        
        files = cursor.fetchall()
        print(f"Found {len(files)} code files to process")
        
        if not files:
            print("❌ No code files found in SQL database")
            return False
        
        # Step 6: Create embeddings in batches
        batch_size = 5  # Small batches to avoid API limits
        points = []
        total_processed = 0
        
        for i in range(0, len(files), batch_size):
            batch = files[i:i+batch_size]
            texts = []
            metadatas = []
            
            for file_path, content in batch:
                if not content:
                    continue
                
                # Simple chunking - take first 1000 characters
                chunk_content = content[:1000] if len(content) > 1000 else content
                
                # Convert absolute paths to relative paths
                relative_path = file_path
                if file_path.startswith('PathUtils.get_workspace_root()/'):
                    relative_path = file_path.replace('PathUtils.get_workspace_root()/', '')
                elif file_path.startswith('PathUtils.get_workspace_root() / '):
                    relative_path = file_path.replace('PathUtils.get_workspace_root() / ', '')
                
                texts.append(chunk_content)
                metadatas.append({
                    'file': relative_path,
                    'relative_path': relative_path,
                    'filepath': relative_path,
                    'repository_id': repo_id,
                    'language': Path(file_path).suffix[1:] or 'unknown',
                    'indexed_at': datetime.now().isoformat(),
                    'workspace_root': str(workspace_root)
                })
            
            if texts:
                try:
                    # Create embeddings
                    result = voyage_client.embed(
                        texts,
                        model="voyage-code-2",  # Use code-2 for consistency
                        input_type="document"
                    )
                    embeddings = result.embeddings
                    
                    # Create points for Qdrant
                    batch_points = []
                    for j, (embedding, metadata) in enumerate(zip(embeddings, metadatas)):
                        point_id = abs(hash(f"{repo_id}:{metadata['relative_path']}")) % (10**8)
                        batch_points.append(
                            PointStruct(
                                id=point_id,
                                vector=embedding,
                                payload=metadata
                            )
                        )
                    
                    # Upload to Qdrant
                    client.upsert(
                        collection_name=collection_name,
                        points=batch_points
                    )
                    
                    total_processed += len(batch_points)
                    print(f"Processed batch {i//batch_size + 1}: {len(batch_points)} embeddings")
                    
                except Exception as e:
                    print(f"❌ Error processing batch {i//batch_size + 1}: {e}")
                    continue
        
        print(f"\n✅ Successfully processed {total_processed} files")
        
        # Step 7: Verify the results
        try:
            collection_info = client.get_collection(collection_name)
            print(f"Collection now contains {collection_info.points_count} points")
            
            # Test a sample search
            sample_results = client.search(
                collection_name=collection_name,
                query_vector=embeddings[0] if embeddings else None,
                limit=3
            )
            
            if sample_results:
                print(f"✅ Semantic search test successful: {len(sample_results)} results")
                for i, result in enumerate(sample_results[:2]):
                    print(f"  {i+1}. {result.payload.get('relative_path', 'unknown')} (score: {result.score:.3f})")
            
        except Exception as e:
            print(f"Warning: Could not verify results: {e}")
        
    except Exception as e:
        print(f"❌ Error processing files: {e}")
        return False
    finally:
        conn.close()
    
    print(f"\n" + "=" * 60)
    print("SEMANTIC INDEX POPULATION COMPLETE")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    success = populate_semantic_index()
    if success:
        print("\n🎉 Semantic search is now ready!")
        print("   You can now test hybrid search with both BM25 and semantic results.")
    else:
        print("\n❌ Failed to populate semantic index")
        print("   Semantic and hybrid search will not work until this is resolved.")