#!/usr/bin/env python3
"""
Migrate large unified index to multiple per-repository indexes.

This script splits the 2.2GB unified index containing 40+ repositories
into separate indexes compatible with the multi-repository architecture.
"""

import os
import sys
import json
import sqlite3
import shutil
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass, asdict
import argparse

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from mcp_server.core.path_utils import PathUtils

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class RepositoryMigration:
    """Track migration progress for a repository."""
    repository_id: str
    name: str
    path: str
    file_count: int
    status: str = "pending"
    error: str = ""
    index_path: str = ""


class LargeIndexMigrator:
    """Migrates large unified index to per-repository indexes."""
    
    def __init__(self, source_db_path: Path, output_dir: Path):
        """
        Initialize the migrator.
        
        Args:
            source_db_path: Path to large unified index
            output_dir: Directory for output indexes (.indexes/)
        """
        self.source_db_path = source_db_path
        self.output_dir = output_dir
        self.registry_path = output_dir / "repository_registry.json"
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Track migrations
        self.migrations: List[RepositoryMigration] = []
        
        # Load existing registry if it exists
        self.existing_registry = self._load_existing_registry()
        
    def _load_existing_registry(self) -> Dict[str, Any]:
        """Load existing repository registry."""
        if self.registry_path.exists():
            try:
                with open(self.registry_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load existing registry: {e}")
        return {}
        
    def analyze_source_index(self) -> List[Tuple[str, str, int]]:
        """
        Analyze source index to find all repositories.
        
        Returns:
            List of (repo_path, repo_name, file_count) tuples
        """
        logger.info(f"Analyzing source index: {self.source_db_path}")
        
        conn = sqlite3.connect(str(self.source_db_path))
        cursor = conn.cursor()
        
        # Get unique repository paths from files
        cursor.execute("""
            SELECT DISTINCT 
                CASE 
                    -- Extract repository base paths
                    WHEN filepath LIKE '%/test_repos/web/python/django/%' 
                        THEN SUBSTR(filepath, 1, INSTR(filepath, '/django/') + 6)
                    WHEN filepath LIKE '%/test_repos/web/python/flask/%' 
                        THEN SUBSTR(filepath, 1, INSTR(filepath, '/flask/') + 5)
                    WHEN filepath LIKE '%/test_repos/web/javascript/react/%' 
                        THEN SUBSTR(filepath, 1, INSTR(filepath, '/react/') + 5)
                    WHEN filepath LIKE '%/test_repos/web/javascript/express/%' 
                        THEN SUBSTR(filepath, 1, INSTR(filepath, '/express/') + 7)
                    WHEN filepath LIKE '%/test_repos/web/typescript/TypeScript/%' 
                        THEN SUBSTR(filepath, 1, INSTR(filepath, '/TypeScript/') + 10)
                    WHEN filepath LIKE '%/test_repos/web/ruby/rails/%' 
                        THEN SUBSTR(filepath, 1, INSTR(filepath, '/rails/') + 5)
                    WHEN filepath LIKE '%/test_repos/jvm/java/kafka/%' 
                        THEN SUBSTR(filepath, 1, INSTR(filepath, '/kafka/') + 5)
                    WHEN filepath LIKE '%/test_repos/jvm/scala/akka/%' 
                        THEN SUBSTR(filepath, 1, INSTR(filepath, '/akka/') + 4)
                    WHEN filepath LIKE '%/test_repos/other/csharp/aspnetcore/%' 
                        THEN SUBSTR(filepath, 1, INSTR(filepath, '/aspnetcore/') + 10)
                    WHEN filepath LIKE '%/test_repos/other/go/gin/%' 
                        THEN SUBSTR(filepath, 1, INSTR(filepath, '/gin/') + 3)
                    WHEN filepath LIKE '%/test_repos/other/c/redis/%' 
                        THEN SUBSTR(filepath, 1, INSTR(filepath, '/redis/') + 5)
                    WHEN filepath LIKE '%/test_repos/other/c/phoenix/%' 
                        THEN SUBSTR(filepath, 1, INSTR(filepath, '/phoenix/') + 7)
                    WHEN filepath LIKE '%/test_repos/other/cpp/grpc/%' 
                        THEN SUBSTR(filepath, 1, INSTR(filepath, '/grpc/') + 4)
                    WHEN filepath LIKE '%/test_repos/other/lua/kong/%' 
                        THEN SUBSTR(filepath, 1, INSTR(filepath, '/kong/') + 4)
                    WHEN filepath LIKE '%/test_repos/jvm/clojure/ring/%' 
                        THEN SUBSTR(filepath, 1, INSTR(filepath, '/ring/') + 4)
                    WHEN filepath LIKE '%/test_repos/web/perl/mojo/%' 
                        THEN SUBSTR(filepath, 1, INSTR(filepath, '/mojo/') + 4)
                    WHEN filepath LIKE '/workspaces/Code-Index-MCP/%' AND filepath NOT LIKE '%/test_repos/%'
                        THEN '/workspaces/Code-Index-MCP'
                    ELSE NULL
                END as repo_path,
                COUNT(*) as file_count
            FROM bm25_content
            WHERE repo_path IS NOT NULL
            GROUP BY repo_path
            HAVING file_count > 10  -- Skip tiny repos
            ORDER BY file_count DESC
        """)
        
        repositories = []
        for repo_path, file_count in cursor.fetchall():
            # Extract repository name
            if '/test_repos/' in repo_path:
                # Extract last directory name
                repo_name = repo_path.rstrip('/').split('/')[-1]
            else:
                repo_name = 'Code-Index-MCP'
                
            repositories.append((repo_path, repo_name, file_count))
            
        conn.close()
        
        logger.info(f"Found {len(repositories)} repositories to migrate")
        return repositories
        
    def migrate_repository(self, repo_path: str, repo_name: str) -> RepositoryMigration:
        """
        Migrate a single repository to its own index.
        
        Args:
            repo_path: Repository base path
            repo_name: Repository name
            
        Returns:
            Migration result
        """
        # Generate repository ID
        repo_id = hashlib.sha256(repo_path.encode()).hexdigest()[:12]
        
        migration = RepositoryMigration(
            repository_id=repo_id,
            name=repo_name,
            path=repo_path,
            file_count=0
        )
        
        logger.info(f"Migrating {repo_name} ({repo_id})...")
        
        try:
            # Create output directory
            repo_output_dir = self.output_dir / repo_id
            repo_output_dir.mkdir(exist_ok=True)
            
            # Output database path
            output_db_path = repo_output_dir / "code_index.db"
            migration.index_path = str(output_db_path)
            
            # Skip if already exists
            if output_db_path.exists():
                logger.info(f"  Index already exists, skipping: {output_db_path}")
                migration.status = "skipped"
                return migration
                
            # Connect to source and create target
            source_conn = sqlite3.connect(str(self.source_db_path))
            target_conn = sqlite3.connect(str(output_db_path))
            
            # Copy schema
            self._copy_schema(source_conn, target_conn)
            
            # Migrate data
            file_count = self._migrate_repository_data(
                source_conn, target_conn, repo_path, repo_id
            )
            
            migration.file_count = file_count
            migration.status = "completed"
            
            # Close connections
            source_conn.close()
            target_conn.close()
            
            logger.info(f"  Migrated {file_count} files to {output_db_path}")
            
        except Exception as e:
            logger.error(f"  Failed to migrate {repo_name}: {e}")
            migration.status = "failed"
            migration.error = str(e)
            
        return migration
        
    def _copy_schema(self, source_conn: sqlite3.Connection, target_conn: sqlite3.Connection):
        """Copy database schema from source to target."""
        # Get all CREATE statements including virtual tables
        cursor = source_conn.cursor()
        
        # First get regular tables
        cursor.execute("""
            SELECT sql FROM sqlite_master 
            WHERE type = 'table'
            AND sql IS NOT NULL
            AND name NOT LIKE 'sqlite_%'
            AND name NOT LIKE '%_data'
            AND name NOT LIKE '%_idx'
            AND name NOT LIKE '%_content'
            AND name NOT LIKE '%_docsize'
            AND name NOT LIKE '%_config'
            ORDER BY name
        """)
        
        regular_tables = cursor.fetchall()
        
        # Then get virtual tables (FTS5)
        cursor.execute("""
            SELECT sql FROM sqlite_master 
            WHERE type = 'table'
            AND sql IS NOT NULL
            AND sql LIKE '%VIRTUAL TABLE%'
            ORDER BY name
        """)
        
        virtual_tables = cursor.fetchall()
        
        # Execute CREATE statements in target
        target_cursor = target_conn.cursor()
        
        # Create regular tables first
        for (sql,) in regular_tables:
            if sql and 'VIRTUAL TABLE' not in sql:
                try:
                    target_cursor.execute(sql)
                except sqlite3.OperationalError as e:
                    if "already exists" not in str(e):
                        logger.warning(f"Failed to create table: {e}")
                        
        # Create virtual tables
        for (sql,) in virtual_tables:
            if sql:
                try:
                    target_cursor.execute(sql)
                except sqlite3.OperationalError as e:
                    if "already exists" not in str(e):
                        logger.warning(f"Failed to create virtual table: {e}")
                        
        # Create indexes
        cursor.execute("""
            SELECT sql FROM sqlite_master 
            WHERE type = 'index'
            AND sql IS NOT NULL
            ORDER BY name
        """)
        
        for (sql,) in cursor.fetchall():
            if sql:
                try:
                    target_cursor.execute(sql)
                except sqlite3.OperationalError as e:
                    if "already exists" not in str(e):
                        logger.warning(f"Failed to create index: {e}")
                        
        target_conn.commit()
        
    def _migrate_repository_data(self, source_conn: sqlite3.Connection, 
                                target_conn: sqlite3.Connection,
                                repo_path: str, repo_id: str) -> int:
        """
        Migrate all data for a specific repository.
        
        Returns:
            Number of files migrated
        """
        source_cursor = source_conn.cursor()
        target_cursor = target_conn.cursor()
        
        # First, insert repository entry
        target_cursor.execute("""
            INSERT INTO repositories (id, path, name, created_at, updated_at, metadata)
            VALUES (1, ?, ?, datetime('now'), datetime('now'), '{}')
        """, (repo_path, repo_path.split('/')[-1]))
        
        # Get all files for this repository
        source_cursor.execute("""
            SELECT DISTINCT b.file_id, b.filepath
            FROM bm25_content b
            WHERE b.filepath LIKE ? || '%'
        """, (repo_path,))
        
        file_mapping = {}  # old_file_id -> new_file_id
        new_file_id = 1
        
        for old_file_id, filepath in source_cursor.fetchall():
            # Insert into files table
            relative_path = filepath[len(repo_path):].lstrip('/')
            language = self._detect_language(filepath)
            
            target_cursor.execute("""
                INSERT INTO files (id, repository_id, path, relative_path, language, 
                                 size, hash, last_modified, indexed_at, metadata)
                VALUES (?, 1, ?, ?, ?, 0, '', datetime('now'), datetime('now'), '{}')
            """, (new_file_id, filepath, relative_path, language))
            
            file_mapping[old_file_id] = new_file_id
            new_file_id += 1
            
        # Copy bm25_content entries
        for old_file_id, new_file_id in file_mapping.items():
            source_cursor.execute("""
                SELECT filepath, filename, content, language, symbols, imports, comments
                FROM bm25_content
                WHERE file_id = ?
            """, (old_file_id,))
            
            row = source_cursor.fetchone()
            if row:
                target_cursor.execute("""
                    INSERT INTO bm25_content 
                    (file_id, filepath, filename, content, language, symbols, imports, comments)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (new_file_id,) + row)
                
        # Copy fts_code entries if they exist
        try:
            for old_file_id, new_file_id in file_mapping.items():
                source_cursor.execute("""
                    SELECT content FROM fts_code WHERE file_id = ?
                """, (old_file_id,))
                
                row = source_cursor.fetchone()
                if row:
                    target_cursor.execute("""
                        INSERT INTO fts_code (content, file_id) VALUES (?, ?)
                    """, (row[0], new_file_id))
        except sqlite3.OperationalError:
            # fts_code table might not exist in all indexes
            pass
            
        # Copy symbols if they exist
        try:
            for old_file_id, new_file_id in file_mapping.items():
                source_cursor.execute("""
                    SELECT name, kind, signature, line_start, line_end, 
                           column_start, column_end, documentation, metadata
                    FROM symbols WHERE file_id = ?
                """, (old_file_id,))
                
                for row in source_cursor.fetchall():
                    target_cursor.execute("""
                        INSERT INTO symbols 
                        (file_id, name, kind, signature, line_start, line_end,
                         column_start, column_end, documentation, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (new_file_id,) + row)
        except sqlite3.OperationalError:
            # symbols table might not exist
            pass
            
        target_conn.commit()
        return len(file_mapping)
        
    def _detect_language(self, filepath: str) -> str:
        """Detect language from file path."""
        ext = Path(filepath).suffix.lower()
        language_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.jsx': 'javascript',
            '.java': 'java',
            '.scala': 'scala',
            '.rb': 'ruby',
            '.cs': 'csharp',
            '.go': 'go',
            '.c': 'c',
            '.cpp': 'cpp',
            '.cc': 'cpp',
            '.h': 'c',
            '.hpp': 'cpp',
            '.lua': 'lua',
            '.clj': 'clojure',
            '.pl': 'perl',
            '.pm': 'perl',
        }
        return language_map.get(ext, 'text')
        
    def update_registry(self):
        """Update repository registry with migration results."""
        logger.info("Updating repository registry...")
        
        # Start with existing registry
        registry = self.existing_registry.copy()
        
        # Add migrated repositories
        for migration in self.migrations:
            if migration.status == "completed":
                # Analyze the new index for statistics
                stats = self._analyze_index(Path(migration.index_path))
                
                registry[migration.repository_id] = {
                    "repository_id": migration.repository_id,
                    "name": migration.name,
                    "path": migration.path,
                    "index_path": migration.index_path,
                    "language_stats": stats.get("languages", {}),
                    "total_files": migration.file_count,
                    "total_symbols": stats.get("total_symbols", 0),
                    "indexed_at": datetime.now().isoformat(),
                    "active": True,
                    "priority": 0
                }
                
        # Write registry
        with open(self.registry_path, 'w') as f:
            json.dump(registry, f, indent=2)
            
        logger.info(f"Updated registry with {len(registry)} repositories")
        
    def _analyze_index(self, index_path: Path) -> Dict[str, Any]:
        """Analyze index for statistics."""
        stats = {
            "languages": {},
            "total_symbols": 0
        }
        
        if not index_path.exists():
            return stats
            
        try:
            conn = sqlite3.connect(str(index_path))
            cursor = conn.cursor()
            
            # Count files by language
            cursor.execute("""
                SELECT language, COUNT(*) FROM files
                WHERE language IS NOT NULL
                GROUP BY language
            """)
            
            for language, count in cursor.fetchall():
                stats["languages"][language] = count
                
            # Count symbols
            try:
                cursor.execute("SELECT COUNT(*) FROM symbols")
                stats["total_symbols"] = cursor.fetchone()[0]
            except sqlite3.OperationalError:
                pass
                
            conn.close()
            
        except Exception as e:
            logger.warning(f"Failed to analyze {index_path}: {e}")
            
        return stats
        
    def run_migration(self, repos_to_migrate: List[str] = None):
        """
        Run the complete migration process.
        
        Args:
            repos_to_migrate: Optional list of repository names to migrate
        """
        # Analyze source
        repositories = self.analyze_source_index()
        
        # Filter if specific repos requested
        if repos_to_migrate:
            repositories = [
                (path, name, count) for path, name, count in repositories
                if name in repos_to_migrate
            ]
            
        logger.info(f"Migrating {len(repositories)} repositories...")
        
        # Migrate each repository
        for repo_path, repo_name, file_count in repositories:
            migration = self.migrate_repository(repo_path, repo_name)
            self.migrations.append(migration)
            
        # Update registry
        self.update_registry()
        
        # Print summary
        self.print_summary()
        
    def print_summary(self):
        """Print migration summary."""
        print("\n" + "="*60)
        print("MIGRATION SUMMARY")
        print("="*60)
        
        completed = sum(1 for m in self.migrations if m.status == "completed")
        failed = sum(1 for m in self.migrations if m.status == "failed")
        skipped = sum(1 for m in self.migrations if m.status == "skipped")
        
        print(f"Total repositories: {len(self.migrations)}")
        print(f"Completed: {completed}")
        print(f"Failed: {failed}")
        print(f"Skipped: {skipped}")
        
        if failed > 0:
            print("\nFailed migrations:")
            for m in self.migrations:
                if m.status == "failed":
                    print(f"  - {m.name}: {m.error}")
                    
        print(f"\nRegistry updated: {self.registry_path}")


def main():
    """Main migration function."""
    parser = argparse.ArgumentParser(
        description="Migrate large unified index to per-repository indexes"
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("/workspaces/Code-Index-MCP/.indexes/f7b49f5d0ae0/new_index.db"),
        help="Path to source unified index"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PathUtils.get_index_storage_path(),
        help="Output directory for indexes"
    )
    parser.add_argument(
        "--repos",
        nargs="+",
        help="Specific repositories to migrate (default: all)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without doing it"
    )
    
    args = parser.parse_args()
    
    # Verify source exists
    if not args.source.exists():
        print(f"Error: Source index not found: {args.source}")
        sys.exit(1)
        
    # Create migrator
    migrator = LargeIndexMigrator(args.source, args.output)
    
    if args.dry_run:
        print("DRY RUN - Analyzing repositories to migrate:")
        repositories = migrator.analyze_source_index()
        for path, name, count in repositories:
            repo_id = hashlib.sha256(path.encode()).hexdigest()[:12]
            print(f"  {name} ({repo_id}): {count} files")
            print(f"    Path: {path}")
            print(f"    Output: {args.output}/{repo_id}/code_index.db")
    else:
        # Run migration
        migrator.run_migration(args.repos)


if __name__ == "__main__":
    main()