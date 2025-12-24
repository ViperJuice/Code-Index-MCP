#!/usr/bin/env python3
"""
Migration script to convert absolute paths to relative paths in all indexes.

This script:
1. Updates SQLite database to use relative paths
2. Computes content hashes for all files
3. Updates Qdrant vector embeddings with relative paths
4. Removes duplicate entries
5. Creates file_moves tracking table
"""

import sqlite3
import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import hashlib
from dataclasses import dataclass
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server.core.path_resolver import PathResolver
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.utils.semantic_indexer import SemanticIndexer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class MigrationStats:
    """Track migration statistics."""
    total_files: int = 0
    migrated_files: int = 0
    duplicate_files: int = 0
    failed_files: int = 0
    total_vectors: int = 0
    migrated_vectors: int = 0
    duplicate_vectors: int = 0
    failed_vectors: int = 0
    start_time: float = 0.0
    end_time: float = 0.0
    
    def duration(self) -> float:
        """Get migration duration in seconds."""
        return self.end_time - self.start_time
    
    def summary(self) -> str:
        """Get summary of migration results."""
        return f"""
Migration Summary:
==================
Duration: {self.duration():.2f} seconds

SQLite Migration:
- Total files: {self.total_files}
- Migrated: {self.migrated_files}
- Duplicates removed: {self.duplicate_files}
- Failed: {self.failed_files}

Vector Migration:
- Total vectors: {self.total_vectors}
- Migrated: {self.migrated_vectors}
- Duplicates removed: {self.duplicate_vectors}
- Failed: {self.failed_vectors}
"""


class PathMigrationManager:
    """Manages the migration from absolute to relative paths."""
    
    def __init__(self, db_path: str, qdrant_path: str, repository_root: Optional[Path] = None):
        """Initialize migration manager.
        
        Args:
            db_path: Path to SQLite database
            qdrant_path: Path to Qdrant vector store
            repository_root: Repository root directory (auto-detected if None)
        """
        self.db_path = db_path
        self.qdrant_path = qdrant_path
        self.path_resolver = PathResolver(repository_root)
        self.stats = MigrationStats()
        
        logger.info(f"Initialized migration manager")
        logger.info(f"Repository root: {self.path_resolver.repository_root}")
        logger.info(f"SQLite database: {self.db_path}")
        logger.info(f"Qdrant store: {self.qdrant_path}")
    
    def migrate(self, batch_size: int = 100, dry_run: bool = False) -> MigrationStats:
        """Run the complete migration process.
        
        Args:
            batch_size: Number of records to process at once
            dry_run: If True, don't make any changes
            
        Returns:
            Migration statistics
        """
        self.stats.start_time = time.time()
        
        logger.info(f"Starting migration (dry_run={dry_run})...")
        
        try:
            # Phase 1: Backup database
            if not dry_run:
                self._backup_database()
            
            # Phase 2: Migrate SQLite
            self._migrate_sqlite(batch_size, dry_run)
            
            # Phase 3: Migrate vectors
            self._migrate_vectors(batch_size, dry_run)
            
            # Phase 4: Cleanup duplicates
            if not dry_run:
                self._cleanup_duplicates()
            
            self.stats.end_time = time.time()
            
            logger.info("Migration completed successfully!")
            logger.info(self.stats.summary())
            
        except Exception as e:
            logger.error(f"Migration failed: {e}", exc_info=True)
            self.stats.end_time = time.time()
            raise
        
        return self.stats
    
    def _backup_database(self):
        """Create a backup of the SQLite database."""
        backup_path = f"{self.db_path}.backup_{int(time.time())}"
        logger.info(f"Creating database backup: {backup_path}")
        
        # Use SQLite backup API
        source = sqlite3.connect(self.db_path)
        dest = sqlite3.connect(backup_path)
        
        with dest:
            source.backup(dest)
        
        source.close()
        dest.close()
        
        logger.info("Database backup completed")
    
    def _migrate_sqlite(self, batch_size: int, dry_run: bool):
        """Migrate SQLite database to use relative paths."""
        logger.info("Starting SQLite migration...")
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            # Check if migration is needed
            cursor = conn.execute("PRAGMA table_info(files)")
            columns = [row['name'] for row in cursor]
            
            if 'content_hash' not in columns:
                logger.info("Running schema migration...")
                if not dry_run:
                    # Run the migration SQL
                    migration_path = Path(__file__).parent.parent / "mcp_server" / "storage" / "migrations" / "002_relative_paths.sql"
                    if migration_path.exists():
                        with open(migration_path, 'r') as f:
                            conn.executescript(f.read())
                        logger.info("Schema migration completed")
                    else:
                        logger.warning(f"Migration file not found: {migration_path}")
            
            # Get all files
            cursor = conn.execute("SELECT * FROM files")
            files = cursor.fetchall()
            self.stats.total_files = len(files)
            
            logger.info(f"Found {self.stats.total_files} files to migrate")
            
            # Process in batches
            for i in range(0, len(files), batch_size):
                batch = files[i:i + batch_size]
                self._process_file_batch(conn, batch, dry_run)
                
                # Log progress
                progress = min(i + batch_size, len(files))
                logger.info(f"Progress: {progress}/{len(files)} files processed")
            
            if not dry_run:
                conn.commit()
                
        except Exception as e:
            logger.error(f"SQLite migration failed: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _process_file_batch(self, conn: sqlite3.Connection, files: List[sqlite3.Row], dry_run: bool):
        """Process a batch of files for migration."""
        for file_row in files:
            try:
                file_id = file_row['id']
                abs_path = file_row['path']
                
                # Skip if already has relative path
                if file_row['relative_path'] and not abs_path.startswith('/'):
                    self.stats.migrated_files += 1
                    continue
                
                # Convert to relative path
                try:
                    path = Path(abs_path)
                    relative_path = self.path_resolver.normalize_path(path)
                    
                    # Compute content hash if file exists
                    content_hash = None
                    if path.exists():
                        content_hash = self.path_resolver.compute_content_hash(path)
                    
                    # Update record
                    if not dry_run:
                        conn.execute("""
                            UPDATE files 
                            SET relative_path = ?, content_hash = ?
                            WHERE id = ?
                        """, (relative_path, content_hash, file_id))
                    
                    self.stats.migrated_files += 1
                    
                except ValueError as e:
                    # Path is outside repository
                    logger.warning(f"File outside repository: {abs_path}")
                    if not dry_run:
                        # Mark as deleted since it's outside repo
                        conn.execute("""
                            UPDATE files 
                            SET is_deleted = TRUE, deleted_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        """, (file_id,))
                    self.stats.failed_files += 1
                    
            except Exception as e:
                logger.error(f"Failed to migrate file {file_row['path']}: {e}")
                self.stats.failed_files += 1
    
    def _migrate_vectors(self, batch_size: int, dry_run: bool):
        """Migrate vector embeddings to use relative paths."""
        logger.info("Starting vector migration...")
        
        try:
            # Initialize semantic indexer
            indexer = SemanticIndexer(qdrant_path=self.qdrant_path)
            
            # Get all collections
            collections = ['code-index']  # Add other collections as needed
            
            for collection in collections:
                logger.info(f"Migrating collection: {collection}")
                self._migrate_collection(indexer, collection, batch_size, dry_run)
                
        except Exception as e:
            logger.error(f"Vector migration failed: {e}")
            raise
    
    def _migrate_collection(self, indexer: SemanticIndexer, collection: str, batch_size: int, dry_run: bool):
        """Migrate a single Qdrant collection."""
        try:
            # Search for all points (using a dummy vector)
            from qdrant_client.http.models import Filter, FieldCondition, MatchValue
            
            offset = 0
            total_migrated = 0
            
            while True:
                # Fetch batch of points
                results = indexer.qdrant.scroll(
                    collection_name=collection,
                    limit=batch_size,
                    offset=offset,
                    with_payload=True,
                    with_vectors=True
                )
                
                if not results or len(results[0]) == 0:
                    break
                
                points, _ = results
                self.stats.total_vectors += len(points)
                
                # Process each point
                updated_points = []
                for point in points:
                    payload = point.payload
                    
                    # Check if already has relative_path
                    if 'relative_path' in payload:
                        continue
                    
                    # Convert file path
                    abs_path = payload.get('file', '')
                    if not abs_path:
                        continue
                    
                    try:
                        relative_path = self.path_resolver.normalize_path(abs_path)
                        
                        # Update payload
                        new_payload = payload.copy()
                        new_payload['relative_path'] = relative_path
                        new_payload['is_deleted'] = False
                        
                        # Compute content hash if available
                        if 'content' in payload:
                            content_hash = hashlib.sha256(payload['content'].encode()).hexdigest()
                            new_payload['content_hash'] = content_hash
                        
                        updated_points.append({
                            'id': point.id,
                            'vector': point.vector,
                            'payload': new_payload
                        })
                        
                        total_migrated += 1
                        
                    except ValueError:
                        # Path outside repository
                        logger.warning(f"Vector has path outside repository: {abs_path}")
                        self.stats.failed_vectors += 1
                
                # Update points in Qdrant
                if updated_points and not dry_run:
                    from qdrant_client.http.models import PointStruct
                    
                    point_structs = [
                        PointStruct(
                            id=p['id'],
                            vector=p['vector'],
                            payload=p['payload']
                        )
                        for p in updated_points
                    ]
                    
                    indexer.qdrant.upsert(
                        collection_name=collection,
                        points=point_structs
                    )
                
                self.stats.migrated_vectors = total_migrated
                offset += batch_size
                
                logger.info(f"Vector progress: {offset} points processed, {total_migrated} migrated")
                
        except Exception as e:
            logger.error(f"Failed to migrate collection {collection}: {e}")
            raise
    
    def _cleanup_duplicates(self):
        """Remove duplicate entries after migration."""
        logger.info("Cleaning up duplicates...")
        
        # SQLite duplicates
        conn = sqlite3.connect(self.db_path)
        try:
            # Find duplicates by content_hash
            cursor = conn.execute("""
                SELECT content_hash, COUNT(*) as cnt
                FROM files
                WHERE content_hash IS NOT NULL
                  AND is_deleted = FALSE
                GROUP BY content_hash
                HAVING COUNT(*) > 1
            """)
            
            duplicates = cursor.fetchall()
            logger.info(f"Found {len(duplicates)} duplicate content hashes")
            
            for content_hash, count in duplicates:
                # Keep the most recent, delete others
                cursor = conn.execute("""
                    SELECT id, relative_path, indexed_at
                    FROM files
                    WHERE content_hash = ?
                      AND is_deleted = FALSE
                    ORDER BY indexed_at DESC
                """, (content_hash,))
                
                entries = cursor.fetchall()
                
                # Mark all but the first as deleted
                for entry in entries[1:]:
                    conn.execute("""
                        UPDATE files
                        SET is_deleted = TRUE, deleted_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (entry[0],))
                    
                    self.stats.duplicate_files += 1
                    logger.debug(f"Marked duplicate as deleted: {entry[1]}")
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Failed to cleanup SQLite duplicates: {e}")
            conn.rollback()
        finally:
            conn.close()
        
        # TODO: Implement vector duplicate cleanup
        logger.info("Duplicate cleanup completed")
    
    def verify_migration(self) -> bool:
        """Verify that migration was successful."""
        logger.info("Verifying migration...")
        
        conn = sqlite3.connect(self.db_path)
        try:
            # Check for files without relative_path
            cursor = conn.execute("""
                SELECT COUNT(*) FROM files
                WHERE relative_path IS NULL OR relative_path = ''
                  AND is_deleted = FALSE
            """)
            
            missing_relative = cursor.fetchone()[0]
            if missing_relative > 0:
                logger.warning(f"Found {missing_relative} files without relative paths")
                return False
            
            # Check for files with absolute paths in relative_path
            cursor = conn.execute("""
                SELECT COUNT(*) FROM files
                WHERE relative_path LIKE '/%'
                  AND is_deleted = FALSE
            """)
            
            absolute_in_relative = cursor.fetchone()[0]
            if absolute_in_relative > 0:
                logger.warning(f"Found {absolute_in_relative} files with absolute paths in relative_path column")
                return False
            
            logger.info("Migration verification passed!")
            return True
            
        except Exception as e:
            logger.error(f"Migration verification failed: {e}")
            return False
        finally:
            conn.close()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate code index to use relative paths")
    parser.add_argument("--db-path", default="code_index.db", help="Path to SQLite database")
    parser.add_argument("--qdrant-path", default="./vector_index.qdrant", help="Path to Qdrant store")
    parser.add_argument("--repo-root", help="Repository root (auto-detected if not specified)")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size for processing")
    parser.add_argument("--dry-run", action="store_true", help="Perform dry run without changes")
    parser.add_argument("--verify-only", action="store_true", help="Only verify migration status")
    
    args = parser.parse_args()
    
    # Create migration manager
    repo_root = Path(args.repo_root) if args.repo_root else None
    manager = PathMigrationManager(args.db_path, args.qdrant_path, repo_root)
    
    if args.verify_only:
        # Just verify status
        if manager.verify_migration():
            logger.info("Migration verification successful")
            sys.exit(0)
        else:
            logger.error("Migration verification failed")
            sys.exit(1)
    
    # Run migration
    try:
        stats = manager.migrate(batch_size=args.batch_size, dry_run=args.dry_run)
        
        # Verify if not dry run
        if not args.dry_run:
            if manager.verify_migration():
                logger.info("Migration completed and verified successfully!")
            else:
                logger.warning("Migration completed but verification found issues")
                sys.exit(1)
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()