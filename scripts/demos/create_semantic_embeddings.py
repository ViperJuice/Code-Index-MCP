#!/usr/bin/env python3
"""Create semantic embeddings for all indexed repositories."""

import os
import sys
import json
import sqlite3
import hashlib
from pathlib import Path
from typing import List, Dict, Any
import logging
from datetime import datetime

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server.utils.semantic_indexer import SemanticIndexer
from mcp_server.document_processing.semantic_chunker import SemanticChunker, ChunkingConfig, ChunkingStrategy
from mcp_server.document_processing.document_interfaces import DocumentStructure
from mcp_server.storage.sqlite_store import SQLiteStore

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


def process_repository(index_dir: Path, semantic_indexer: SemanticIndexer):
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
            LIMIT 1000
        """)
        
        files = cursor.fetchall()
        logger.info(f"Found {len(files)} files to process")
        
        for file_path, content in files:
            if not content:
                continue
                
            # Skip non-code files
            if not any(file_path.endswith(ext) for ext in [
                '.py', '.js', '.ts', '.java', '.go', '.rs', '.cpp', '.c', '.h',
                '.cs', '.rb', '.php', '.swift', '.kt', '.scala', '.r', '.jl'
            ]):
                continue
            
            try:
                # Simple chunking for code files
                # Split into chunks of ~500 lines with overlap
                lines = content.split('\n')
                chunk_size = 500
                overlap = 50
                chunks = []
                
                for start in range(0, len(lines), chunk_size - overlap):
                    end = min(start + chunk_size, len(lines))
                    chunk_lines = lines[start:end]
                    chunk_content = '\n'.join(chunk_lines)
                    if chunk_content.strip():
                        chunks.append(chunk_content)
                
                # Index each chunk
                for i, chunk in enumerate(chunks):
                    chunk_id = f"{file_path}:chunk_{i}"
                    
                    # Add metadata
                    metadata = {
                        'file_path': file_path,
                        'repository': repo_name,
                        'chunk_index': i,
                        'language': Path(file_path).suffix[1:],
                        'indexed_at': datetime.now().isoformat()
                    }
                    
                    # Create embedding using the semantic indexer's index_code method
                    semantic_indexer.index_code(
                        code=chunk,
                        file_path=chunk_id,
                        metadata=metadata
                    )
                    
                logger.info(f"Indexed {len(chunks)} chunks from {file_path}")
                
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                continue
                
    finally:
        conn.close()


def main():
    """Main function to create embeddings for all repositories."""
    # Setup paths
    indexes_dir = Path(".indexes")
    qdrant_path = indexes_dir / "qdrant" / "main.qdrant"
    
    # Ensure Qdrant directory exists
    qdrant_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Initialize semantic indexer
    logger.info("Initializing semantic indexer...")
    semantic_indexer = SemanticIndexer(
        qdrant_path=str(qdrant_path),
        collection="code-embeddings"
    )
    
    # Note: Using simple chunking for now since SemanticChunker is designed for documents
    # TODO: Use proper code chunking when available
    
    # Get all repository indexes
    repo_dirs = []
    for item in indexes_dir.iterdir():
        if item.is_dir() and item.name != "qdrant":
            # Check if it contains a database
            if any(item.glob("*.db")):
                repo_dirs.append(item)
    
    logger.info(f"Found {len(repo_dirs)} repositories to process")
    
    # Process each repository
    for i, repo_dir in enumerate(repo_dirs, 1):
        logger.info(f"\nProcessing repository {i}/{len(repo_dirs)}: {repo_dir.name}")
        try:
            process_repository(repo_dir, semantic_indexer)
        except Exception as e:
            logger.error(f"Failed to process {repo_dir}: {e}")
            continue
    
    # Get final statistics
    try:
        stats = semantic_indexer.get_stats()
        logger.info(f"\nIndexing complete!")
        logger.info(f"Total embeddings: {stats.get('total_points', 0)}")
        logger.info(f"Collections: {stats.get('collections', [])}")
    except:
        logger.info("Indexing complete!")


if __name__ == "__main__":
    main()