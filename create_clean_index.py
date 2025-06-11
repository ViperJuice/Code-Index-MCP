#!/usr/bin/env python3
"""
Create a clean version of the code index database without sensitive files.
"""

import sqlite3
import shutil
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Sensitive file patterns to exclude
SENSITIVE_PATTERNS = [
    '.env',
    '.env.*',
    '*.key',
    '*.pem',
    '*.pfx',
    'secrets.*',
    'credentials.*',
    'password.*',
    '*.sqlite',
    '*.db',
    'node_modules/',
    '.git/',
    '__pycache__/',
    '*.pyc',
    '.DS_Store',
    'temp_cookbook/',
    'test_repos/',
]

def should_exclude(file_path: str) -> bool:
    """Check if a file should be excluded based on sensitive patterns."""
    path_lower = file_path.lower()
    
    for pattern in SENSITIVE_PATTERNS:
        if pattern.endswith('/'):
            # Directory pattern
            if f'/{pattern}' in path_lower or path_lower.startswith(pattern):
                return True
        elif '*' in pattern:
            # Wildcard pattern
            import fnmatch
            if fnmatch.fnmatch(path_lower, pattern.lower()):
                return True
        else:
            # Exact match or substring
            if pattern.lower() in path_lower:
                return True
    
    return False

def create_clean_database(source_db: str, target_db: str):
    """Create a clean copy of the database without sensitive files."""
    logger.info("🔒 Creating clean database...")
    
    # First copy the entire database
    shutil.copy2(source_db, target_db)
    
    # Connect to the copy
    conn = sqlite3.connect(target_db)
    cursor = conn.cursor()
    
    try:
        # Get all files
        cursor.execute("SELECT id, relative_path FROM files WHERE relative_path IS NOT NULL")
        files = cursor.fetchall()
        
        total_files = len(files)
        excluded_files = []
        ids_to_delete = []
        
        # Check each file
        for file_id, file_path in files:
            if should_exclude(file_path):
                ids_to_delete.append(file_id)
                excluded_files.append(file_path)
        
        excluded_count = len(excluded_files)
        
        if ids_to_delete:
            logger.info(f"📊 Found {excluded_count} sensitive files to remove")
            
            # Delete from all related tables
            placeholders = ','.join('?' * len(ids_to_delete))
            
            # Delete from main files table
            cursor.execute(f"DELETE FROM files WHERE id IN ({placeholders})", ids_to_delete)
            
            # Delete from related tables
            for table in ['symbols', 'symbol_references', 'imports', 'embeddings', 'fts_code']:
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
                if cursor.fetchone():
                    cursor.execute(f"DELETE FROM {table} WHERE file_id IN ({placeholders})", ids_to_delete)
        
        conn.commit()
        
        # Log results
        logger.info(f"✅ Clean database created")
        logger.info(f"   - Total files: {total_files}")
        logger.info(f"   - Excluded: {excluded_count}")
        logger.info(f"   - Remaining: {total_files - excluded_count}")
        
        # Log some examples of excluded files
        if excluded_files:
            logger.info("\n📝 Examples of excluded files:")
            for path in excluded_files[:10]:
                logger.info(f"   - {path}")
            if len(excluded_files) > 10:
                logger.info(f"   ... and {len(excluded_files) - 10} more")
        
        # Write full list to log file
        with open('excluded_files.log', 'w') as f:
            f.write(f"Excluded {len(excluded_files)} sensitive files:\n\n")
            for path in sorted(excluded_files):
                f.write(f"{path}\n")
        
        return total_files - excluded_count, excluded_count
        
    finally:
        conn.close()
        
        # Vacuum the database in a separate connection
        logger.info("🗜️  Optimizing database...")
        conn2 = sqlite3.connect(target_db)
        conn2.execute("VACUUM")
        conn2.close()

def main():
    """Main entry point."""
    source_db = "code_index.db"
    target_db = "code_index_clean.db"
    
    if not Path(source_db).exists():
        logger.error(f"❌ Source database not found: {source_db}")
        return 1
    
    logger.info("CLEAN INDEX CREATOR")
    logger.info("=" * 60)
    
    # Get original size
    original_size = Path(source_db).stat().st_size / (1024 * 1024)  # MB
    logger.info(f"📁 Original database size: {original_size:.2f} MB")
    
    # Create clean database
    included, excluded = create_clean_database(source_db, target_db)
    
    # Get new size
    new_size = Path(target_db).stat().st_size / (1024 * 1024)  # MB
    logger.info(f"📁 Clean database size: {new_size:.2f} MB")
    logger.info(f"💾 Size reduction: {original_size - new_size:.2f} MB ({(1 - new_size/original_size) * 100:.1f}%)")
    
    logger.info(f"\n✅ Clean database created: {target_db}")
    logger.info(f"📋 Exclusion log written: excluded_files.log")
    
    return 0

if __name__ == "__main__":
    exit(main())