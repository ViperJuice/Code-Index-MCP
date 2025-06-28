#!/usr/bin/env python3
"""
Simple BM25 Index Population Script
"""

import logging
import multiprocessing as mp
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import hashlib
import json

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.indexer.bm25_indexer import BM25Indexer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SimpleBM25Indexer:
    """Simple BM25 indexer without plugin dependencies."""
    
    def __init__(self, db_path: str = "code_index.db"):
        """Initialize the indexer."""
        self.db_path = db_path
        self.storage = SQLiteStore(db_path)
        self.bm25_indexer = BM25Indexer(self.storage)
        
    def get_all_files(self) -> List[Dict[str, Any]]:
        """Get all files from database."""
        with self.storage._get_connection() as conn:
            query = """
                SELECT f.*, r.path as repo_path
                FROM files f
                LEFT JOIN repositories r ON f.repository_id = r.id
                ORDER BY f.id
            """
            
            cursor = conn.execute(query)
            files = []
            for row in cursor:
                files.append(dict(row))
                
            return files
    
    def read_file_content(self, filepath: str) -> Optional[str]:
        """Read file content from disk."""
        try:
            path = Path(filepath)
            if path.exists() and path.is_file():
                # Skip very large files
                if path.stat().st_size > 10 * 1024 * 1024:  # 10MB
                    logger.warning(f"Skipping large file: {filepath}")
                    return None
                    
                # Try to read with UTF-8, fallback to other encodings
                encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
                for encoding in encodings:
                    try:
                        return path.read_text(encoding=encoding)
                    except UnicodeDecodeError:
                        continue
                        
                logger.warning(f"Could not decode file: {filepath}")
                return None
            else:
                logger.warning(f"File not found: {filepath}")
                return None
        except Exception as e:
            logger.error(f"Error reading file {filepath}: {e}")
            return None
    
    def process_file(self, file_info: Dict[str, Any]) -> Tuple[str, bool, str]:
        """Process a single file for BM25 indexing."""
        filepath = file_info['path']
        
        try:
            # Read file content
            content = self.read_file_content(filepath)
            if content is None:
                return filepath, False, "Could not read file"
            
            # Simple metadata
            metadata = {
                'file_id': file_info['id'],
                'repository_id': file_info['repository_id'],
                'relative_path': file_info['relative_path'],
                'language': file_info.get('language', ''),
                'size': file_info.get('size', len(content)),
                'hash': file_info.get('hash', hashlib.md5(content.encode()).hexdigest()),
                'last_modified': file_info.get('last_modified'),
                'original_metadata': json.loads(file_info.get('metadata', '{}'))
            }
            
            # Index the document
            self.bm25_indexer.add_document(filepath, content, metadata)
            
            return filepath, True, "Successfully indexed"
            
        except Exception as e:
            logger.error(f"Error processing {filepath}: {e}")
            return filepath, False, str(e)
    
    def process_batch(self, files: List[Dict[str, Any]]) -> List[Tuple[str, bool, str]]:
        """Process a batch of files."""
        results = []
        for file_info in files:
            result = self.process_file(file_info)
            results.append(result)
        return results
    
    def index_all_files(self, batch_size: int = 100, num_workers: int = None):
        """Index all files using parallel processing."""
        if num_workers is None:
            num_workers = mp.cpu_count()
            
        logger.info(f"Starting BM25 indexing with {num_workers} workers")
        
        # Get all files
        files = self.get_all_files()
        total_files = len(files)
        
        if total_files == 0:
            logger.info("No files found to index")
            return
            
        logger.info(f"Found {total_files} files to index")
        
        # Statistics
        successful = 0
        failed = 0
        start_time = time.time()
        
        # Process files in batches
        batches = [files[i:i + batch_size] for i in range(0, total_files, batch_size)]
        
        # Use ThreadPoolExecutor for I/O bound operations
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            # Submit all batches
            future_to_batch = {
                executor.submit(self.process_batch, batch): i 
                for i, batch in enumerate(batches)
            }
            
            # Process completed batches
            completed_files = 0
            for future in as_completed(future_to_batch):
                batch_idx = future_to_batch[future]
                try:
                    results = future.result()
                    
                    # Update statistics
                    for filepath, success, message in results:
                        completed_files += 1
                        if success:
                            successful += 1
                        else:
                            failed += 1
                            logger.warning(f"Failed to index {filepath}: {message}")
                        
                        # Progress update
                        if completed_files % 100 == 0:
                            elapsed = time.time() - start_time
                            rate = completed_files / elapsed
                            eta = (total_files - completed_files) / rate if rate > 0 else 0
                            logger.info(
                                f"Progress: {completed_files}/{total_files} files "
                                f"({completed_files/total_files*100:.1f}%) - "
                                f"Rate: {rate:.1f} files/sec - "
                                f"ETA: {eta:.0f}s"
                            )
                            
                except Exception as e:
                    logger.error(f"Error processing batch {batch_idx}: {e}")
                    failed += len(batches[batch_idx])
        
        # Final statistics
        elapsed_time = time.time() - start_time
        logger.info(f"\nIndexing completed in {elapsed_time:.1f} seconds")
        logger.info(f"Total files: {total_files}")
        logger.info(f"Successfully indexed: {successful}")
        logger.info(f"Failed: {failed}")
        logger.info(f"Average rate: {total_files/elapsed_time:.1f} files/second")
        
        # Optimize index after bulk loading
        logger.info("Optimizing BM25 index...")
        self.bm25_indexer.optimize()
        
        # Print index statistics
        stats = self.bm25_indexer.get_statistics()
        logger.info("\nIndex Statistics:")
        logger.info(f"  Total documents: {stats['total_documents']}")
        logger.info(f"  Total symbols: {stats['total_symbols']}")
        logger.info(f"  Language distribution: {stats['language_distribution']}")


def main():
    """Main entry point."""
    # Create indexer and run
    indexer = SimpleBM25Indexer("code_index.db")
    
    try:
        # Use 8 workers and batch size of 100
        indexer.index_all_files(batch_size=100, num_workers=8)
        return 0
    except KeyboardInterrupt:
        logger.info("\nIndexing interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Indexing failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())