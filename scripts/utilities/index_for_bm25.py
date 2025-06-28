#!/usr/bin/env python3
"""
Index existing files into BM25 for testing.
"""

import logging
from pathlib import Path
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.indexer.bm25_indexer import BM25Indexer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def index_files_for_bm25():
    """Index all files in the database into BM25."""
    storage = SQLiteStore('/app/code_index.db')
    indexer = BM25Indexer(storage)
    
    # Get all files from the database
    with storage._get_connection() as conn:
        cursor = conn.execute("""
            SELECT id, path, content FROM files 
            WHERE content IS NOT NULL AND content != ''
            LIMIT 100
        """)
        
        files = cursor.fetchall()
        logger.info(f"Found {len(files)} files to index")
        
        # Index each file
        for file_id, filepath, content in files:
            if not content:
                continue
                
            # Prepare document for indexing
            doc = {
                'file_id': file_id,
                'filepath': filepath,
                'content': content,
                'metadata': {
                    'language': Path(filepath).suffix.lstrip('.'),
                    'size': len(content)
                }
            }
            
            # Index the document
            try:
                indexer.index_documents([doc])
                logger.debug(f"Indexed: {filepath}")
            except Exception as e:
                logger.error(f"Failed to index {filepath}: {e}")
        
        logger.info("Indexing complete")
        
        # Verify indexing
        cursor = conn.execute("SELECT COUNT(*) FROM bm25_content")
        count = cursor.fetchone()[0]
        logger.info(f"Total documents in BM25 index: {count}")
        
        # Test search
        results = indexer.search("def", limit=5)
        logger.info(f"Test search for 'def' returned {len(results)} results")


if __name__ == "__main__":
    index_files_for_bm25()