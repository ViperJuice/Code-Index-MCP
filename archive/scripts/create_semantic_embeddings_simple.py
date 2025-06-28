#!/usr/bin/env python3
"""Create semantic embeddings for indexed repositories using Voyage AI."""

import os
import sys
import json
import sqlite3
from pathlib import Path
from typing import List, Dict, Any
import logging
from datetime import datetime
import voyageai
from qdrant_client import QdrantClient, models
from qdrant_client.http.models import PointStruct

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_repository_info(index_path: Path) -> Dict[str, Any]:
    """Extract repository information from metadata.json."""
    metadata_path = index_path / "metadata.json"
    if metadata_path.exists():
        with open(metadata_path, 'r') as f:
            return json.load(f)
    return {}


def create_embeddings(texts: List[str], voyage_client) -> List[List[float]]:
    """Create embeddings for a list of texts."""
    if not texts:
        return []
    
    try:
        result = voyage_client.embed(
            texts,
            model="voyage-code-3",
            input_type="document",
            output_dimension=1024,
            output_dtype="float"
        )
        return result.embeddings
    except Exception as e:
        logger.error(f"Error creating embeddings: {e}")
        return []


def process_repository(index_dir: Path, qdrant_client: QdrantClient, voyage_client, collection_name: str):
    """Process a single repository and create embeddings."""
    # Find the SQLite database
    db_path = index_dir / "current.db"
    if not db_path.exists():
        # Try to find any .db file
        db_files = list(index_dir.glob("*.db"))
        if not db_files:
            logger.warning(f"No database found in {index_dir}")
            return
        db_path = db_files[0]
    
    logger.info(f"Processing repository at {index_dir}")
    logger.info(f"Using database: {db_path}")
    
    # Get repository metadata
    metadata = get_repository_info(index_dir)
    repo_name = metadata.get('repository_name', index_dir.name)
    
    # Connect to SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Get all indexed files
        cursor.execute("""
            SELECT DISTINCT filepath, content 
            FROM bm25_content 
            WHERE content IS NOT NULL AND content != ''
            LIMIT 500
        """)
        
        files = cursor.fetchall()
        logger.info(f"Found {len(files)} files to process")
        
        # Process in batches
        batch_size = 10
        points = []
        
        for i in range(0, len(files), batch_size):
            batch = files[i:i+batch_size]
            texts = []
            metadatas = []
            
            for file_path, content in batch:
                if not content:
                    continue
                    
                # Skip non-code files
                if not any(file_path.endswith(ext) for ext in [
                    '.py', '.js', '.ts', '.java', '.go', '.rs', '.cpp', '.c', '.h',
                    '.cs', '.rb', '.php', '.swift', '.kt', '.scala', '.r', '.jl'
                ]):
                    continue
                
                # Simple chunking - take first 1000 lines
                lines = content.split('\n')[:1000]
                chunk_content = '\n'.join(lines)
                
                texts.append(chunk_content)
                metadatas.append({
                    'file_path': file_path,
                    'repository': repo_name,
                    'language': Path(file_path).suffix[1:] or 'unknown',
                    'indexed_at': datetime.now().isoformat()
                })
            
            if texts:
                # Create embeddings
                embeddings = create_embeddings(texts, voyage_client)
                
                if embeddings:
                    # Create points for Qdrant
                    for j, (embedding, metadata) in enumerate(zip(embeddings, metadatas)):
                        point_id = abs(hash(f"{repo_name}:{metadata['file_path']}")) % (10**8)
                        points.append(
                            PointStruct(
                                id=point_id,
                                vector=embedding,
                                payload=metadata
                            )
                        )
                    
                    logger.info(f"Created {len(embeddings)} embeddings for batch {i//batch_size + 1}")
        
        # Upload all points to Qdrant
        if points:
            qdrant_client.upsert(
                collection_name=collection_name,
                points=points
            )
            logger.info(f"Uploaded {len(points)} embeddings to Qdrant")
                
    except Exception as e:
        logger.error(f"Error processing repository: {e}")
    finally:
        conn.close()


def main():
    """Main function to create embeddings for all repositories."""
    # Setup paths
    indexes_dir = Path(".indexes")
    qdrant_path = indexes_dir / "qdrant" / "main.qdrant"
    
    # Ensure Qdrant directory exists
    qdrant_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Initialize Voyage AI client
    api_key = os.environ.get("VOYAGE_AI_API_KEY")
    if not api_key:
        logger.error("VOYAGE_AI_API_KEY environment variable not set")
        return
    
    voyage_client = voyageai.Client(api_key=api_key)
    
    # Initialize Qdrant client
    logger.info("Initializing Qdrant client...")
    qdrant_client = QdrantClient(path=str(qdrant_path))
    
    # Create collection if it doesn't exist
    collection_name = "code-embeddings"
    try:
        qdrant_client.get_collection(collection_name)
        logger.info(f"Collection '{collection_name}' already exists")
    except:
        logger.info(f"Creating collection '{collection_name}'")
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=1024,
                distance=models.Distance.COSINE
            )
        )
    
    # Get all repository indexes
    repo_dirs = []
    for item in indexes_dir.iterdir():
        if item.is_dir() and item.name != "qdrant":
            # Check if it contains a database
            if any(item.glob("*.db")):
                repo_dirs.append(item)
    
    logger.info(f"Found {len(repo_dirs)} repositories to process")
    
    # Process each repository (limit to 5 for testing)
    for i, repo_dir in enumerate(repo_dirs[:5], 1):
        logger.info(f"\nProcessing repository {i}/{min(5, len(repo_dirs))}: {repo_dir.name}")
        try:
            process_repository(repo_dir, qdrant_client, voyage_client, collection_name)
        except Exception as e:
            logger.error(f"Failed to process {repo_dir}: {e}")
            continue
    
    # Get final statistics
    try:
        collection_info = qdrant_client.get_collection(collection_name)
        logger.info(f"\nIndexing complete!")
        logger.info(f"Total embeddings: {collection_info.points_count}")
    except:
        logger.info("Indexing complete!")


if __name__ == "__main__":
    main()