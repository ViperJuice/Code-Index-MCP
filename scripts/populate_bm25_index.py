#!/usr/bin/env python3
"""
Populate BM25 Index Script

This script reads all files from the SQLite database and indexes them into the BM25
tables using parallel processing for efficient indexing of large codebases.

Usage:
    python scripts/populate_bm25_index.py [options]

Options:
    --db-path PATH      Path to SQLite database (default: code_index.db)
    --batch-size SIZE   Number of files to process per batch (default: 100)
    --workers NUM       Number of parallel workers (default: CPU count)
    --language LANG     Only index files of specific language
    --repository REPO   Only index files from specific repository
    --force             Force reindex even if content hasn't changed
    --verbose           Enable verbose logging
"""

import argparse
import logging
import multiprocessing as mp
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import hashlib
import json

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.indexer.bm25_indexer import BM25Indexer
from mcp_server.plugin_system.plugin_manager import PluginManager
from mcp_server.plugin_system.plugin_loader import PluginLoader

# Configure logging
logger = logging.getLogger(__name__)


class BM25PopulateIndexer:
    """Handles population of BM25 index from existing database files."""
    
    def __init__(self, db_path: str = "code_index.db", verbose: bool = False):
        """Initialize the indexer with database path."""
        self.db_path = db_path
        self.storage = SQLiteStore(db_path)
        self.bm25_indexer = BM25Indexer(self.storage)
        
        # Set up logging
        log_level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Initialize plugin system for metadata extraction
        self.plugin_manager = PluginManager()
        self._load_plugins()
        
    def _load_plugins(self):
        """Load all available plugins."""
        loader = PluginLoader()
        plugins_dir = Path(__file__).parent.parent / "mcp_server" / "plugins"
        
        if plugins_dir.exists():
            discovered = loader.discover_plugins(str(plugins_dir))
            for plugin_info in discovered:
                try:
                    plugin = loader.load_plugin(plugin_info)
                    self.plugin_manager.register_plugin(plugin)
                except Exception as e:
                    logger.warning(f"Failed to load plugin {plugin_info.name}: {e}")
    
    def get_all_files(self, language: Optional[str] = None, 
                     repository_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get all files from database with optional filters."""
        with self.storage._get_connection() as conn:
            # Build query
            query = """
                SELECT f.*, r.path as repo_path
                FROM files f
                LEFT JOIN repositories r ON f.repository_id = r.id
                WHERE 1=1
            """
            params = []
            
            if language:
                query += " AND f.language = ?"
                params.append(language)
                
            if repository_id:
                query += " AND f.repository_id = ?"
                params.append(repository_id)
                
            query += " ORDER BY f.id"
            
            cursor = conn.execute(query, params)
            files = []
            for row in cursor:
                files.append(dict(row))
                
            return files
    
    def read_file_content(self, filepath: str) -> Optional[str]:
        """Read file content from disk."""
        try:
            path = Path(filepath)
            if path.exists() and path.is_file():
                # Check file size - skip very large files
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
    
    def extract_metadata(self, filepath: str, content: str, language: str) -> Dict[str, Any]:
        """Extract metadata from file content using appropriate plugin."""
        metadata = {
            'language': language,
            'symbols': [],
            'imports': [],
            'comments': [],
            'symbol_list': []
        }
        
        try:
            # Find appropriate plugin
            plugin = self.plugin_manager.get_plugin_for_file(filepath)
            if plugin and hasattr(plugin, 'extract_symbols'):
                # Extract symbols
                symbols = plugin.extract_symbols(content)
                metadata['symbols'] = [s.name for s in symbols]
                metadata['symbol_list'] = [
                    {
                        'id': hash(f"{filepath}:{s.name}:{s.line_start}"),
                        'name': s.name,
                        'kind': s.kind,
                        'signature': getattr(s, 'signature', ''),
                        'documentation': getattr(s, 'documentation', ''),
                        'line_start': s.line_start,
                        'line_end': s.line_end
                    }
                    for s in symbols
                ]
                
            if plugin and hasattr(plugin, 'extract_imports'):
                # Extract imports
                imports = plugin.extract_imports(content)
                metadata['imports'] = [imp.module_name for imp in imports]
                
            # Extract comments (simple regex-based for now)
            import re
            # Single line comments
            single_comments = re.findall(r'(?://|#)\s*(.+)', content)
            # Multi-line comments
            multi_comments = re.findall(r'/\*\s*(.*?)\s*\*/', content, re.DOTALL)
            metadata['comments'] = single_comments + multi_comments
            
        except Exception as e:
            logger.warning(f"Error extracting metadata for {filepath}: {e}")
            
        return metadata
    
    def process_file(self, file_info: Dict[str, Any], force_reindex: bool = False) -> Tuple[str, bool, str]:
        """
        Process a single file for BM25 indexing.
        
        Returns:
            Tuple of (filepath, success, message)
        """
        filepath = file_info['path']
        
        try:
            # Read file content
            content = self.read_file_content(filepath)
            if content is None:
                return filepath, False, "Could not read file"
            
            # Extract metadata
            language = file_info.get('language', '')
            metadata = self.extract_metadata(filepath, content, language)
            
            # Preserve all original metadata from database
            metadata.update({
                'file_id': file_info['id'],
                'repository_id': file_info['repository_id'],
                'relative_path': file_info['relative_path'],
                'size': file_info.get('size', len(content)),
                'hash': file_info.get('hash', hashlib.md5(content.encode()).hexdigest()),
                'last_modified': file_info.get('last_modified'),
                'original_metadata': json.loads(file_info.get('metadata', '{}'))
            })
            
            # Index the document
            self.bm25_indexer.add_document(filepath, content, metadata)
            
            return filepath, True, "Successfully indexed"
            
        except Exception as e:
            logger.error(f"Error processing {filepath}: {e}")
            return filepath, False, str(e)
    
    def process_batch(self, files: List[Dict[str, Any]], force_reindex: bool = False) -> List[Tuple[str, bool, str]]:
        """Process a batch of files."""
        results = []
        for file_info in files:
            result = self.process_file(file_info, force_reindex)
            results.append(result)
        return results
    
    def index_all_files(self, batch_size: int = 100, num_workers: int = None,
                       language: Optional[str] = None, repository_id: Optional[int] = None,
                       force_reindex: bool = False):
        """
        Index all files from the database using parallel processing.
        
        Args:
            batch_size: Number of files per batch
            num_workers: Number of parallel workers (default: CPU count)
            language: Filter by language
            repository_id: Filter by repository
            force_reindex: Force reindexing even if content unchanged
        """
        if num_workers is None:
            num_workers = mp.cpu_count()
            
        logger.info(f"Starting BM25 indexing with {num_workers} workers")
        
        # Get all files
        files = self.get_all_files(language, repository_id)
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
                executor.submit(self.process_batch, batch, force_reindex): i 
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
    parser = argparse.ArgumentParser(
        description="Populate BM25 index from SQLite database files"
    )
    parser.add_argument(
        "--db-path", 
        default="code_index.db",
        help="Path to SQLite database (default: code_index.db)"
    )
    parser.add_argument(
        "--batch-size", 
        type=int, 
        default=100,
        help="Number of files to process per batch (default: 100)"
    )
    parser.add_argument(
        "--workers", 
        type=int,
        help="Number of parallel workers (default: CPU count)"
    )
    parser.add_argument(
        "--language",
        help="Only index files of specific language"
    )
    parser.add_argument(
        "--repository",
        help="Only index files from specific repository path"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force reindex even if content hasn't changed"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Get repository ID if path provided
    repository_id = None
    if args.repository:
        storage = SQLiteStore(args.db_path)
        repo = storage.get_repository(args.repository)
        if repo:
            repository_id = repo['id']
        else:
            logger.error(f"Repository not found: {args.repository}")
            return 1
    
    # Create indexer and run
    indexer = BM25PopulateIndexer(args.db_path, args.verbose)
    
    try:
        indexer.index_all_files(
            batch_size=args.batch_size,
            num_workers=args.workers,
            language=args.language,
            repository_id=repository_id,
            force_reindex=args.force
        )
        return 0
    except KeyboardInterrupt:
        logger.info("\nIndexing interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Indexing failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())