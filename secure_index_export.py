#!/usr/bin/env python3
"""Secure index export with gitignore filtering."""

import sqlite3
import shutil
import tempfile
from pathlib import Path
import fnmatch
import tarfile
import json
from typing import Set, List, Tuple, Dict, Any
from datetime import datetime

class SecureIndexExporter:
    """Export index artifacts with gitignore filtering."""
    
    def __init__(self):
        self.gitignore_patterns = self._load_gitignore_patterns()
        self.mcp_ignore_patterns = self._load_mcp_ignore_patterns()
        self.all_patterns = self.gitignore_patterns + self.mcp_ignore_patterns
        
    def _load_gitignore_patterns(self) -> List[str]:
        """Load patterns from .gitignore file."""
        patterns = []
        gitignore_path = Path(".gitignore")
        
        if gitignore_path.exists():
            with open(gitignore_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and not line.startswith('!'):
                        patterns.append(line)
                        
        return patterns
        
    def _load_mcp_ignore_patterns(self) -> List[str]:
        """Load patterns from .mcp-index-ignore file."""
        patterns = []
        ignore_path = Path(".mcp-index-ignore")
        
        # Default patterns if file doesn't exist
        default_patterns = [
            "*.env",
            ".env*",
            "*.key",
            "*.pem",
            "*secret*",
            "*password*",
            ".aws/*",
            ".ssh/*",
            "node_modules/*",
            "__pycache__/*",
            "*.pyc",
        ]
        
        if ignore_path.exists():
            with open(ignore_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        patterns.append(line)
        else:
            patterns = default_patterns
            
        return patterns
        
    def _should_exclude(self, file_path: str) -> bool:
        """Check if file should be excluded from export."""
        path = Path(file_path)
        
        for pattern in self.all_patterns:
            # Handle directory patterns
            if pattern.endswith('/'):
                if any(part == pattern[:-1] for part in path.parts):
                    return True
            # Handle file patterns
            elif fnmatch.fnmatch(str(path), pattern):
                return True
            elif fnmatch.fnmatch(path.name, pattern):
                return True
                
        return False
        
    def create_filtered_database(self, source_db: str, target_db: str) -> Tuple[int, int]:
        """Create a filtered copy of the database excluding gitignored files."""
        # Copy database structure
        shutil.copy2(source_db, target_db)
        
        conn = sqlite3.connect(target_db)
        cursor = conn.cursor()
        
        excluded_count = 0
        total_count = 0
        
        try:
            # Get all file paths - try relative_path first, fall back to path
            try:
                cursor.execute("SELECT id, relative_path FROM files WHERE relative_path IS NOT NULL")
                files = cursor.fetchall()
            except sqlite3.OperationalError:
                # Fall back to path column for older schemas
                cursor.execute("SELECT id, path FROM files")
                files = cursor.fetchall()
            
            total_count = len(files)
            
            # Build list of IDs to delete
            ids_to_delete = []
            excluded_files = []
            
            for file_id, file_path in files:
                if self._should_exclude(file_path):
                    ids_to_delete.append(file_id)
                    excluded_files.append(file_path)
                    excluded_count += 1
                    
            # Delete excluded files and their related data
            if ids_to_delete:
                # Delete from files table
                placeholders = ','.join('?' * len(ids_to_delete))
                cursor.execute(f"DELETE FROM files WHERE id IN ({placeholders})", ids_to_delete)
                
                # Delete from symbols table
                cursor.execute(f"DELETE FROM symbols WHERE file_id IN ({placeholders})", ids_to_delete)
                
                # Delete from imports table if exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='imports'")
                if cursor.fetchone():
                    cursor.execute(f"DELETE FROM imports WHERE file_id IN ({placeholders})", ids_to_delete)
                    
            # Vacuum to reclaim space
            cursor.execute("VACUUM")
            conn.commit()
            
            # Log excluded files
            if excluded_files:
                log_path = Path("excluded_files.log")
                with open(log_path, 'w') as f:
                    f.write(f"Excluded {len(excluded_files)} files from index export:\n\n")
                    for file_path in sorted(excluded_files):
                        f.write(f"{file_path}\n")
                        
        finally:
            conn.close()
            
        return total_count - excluded_count, excluded_count
        
    def create_secure_archive(self, output_path: str = "secure_index_archive.tar.gz") -> Dict[str, Any]:
        """Create a secure archive of index artifacts."""
        stats = {
            "timestamp": datetime.now().isoformat(),
            "files_included": 0,
            "files_excluded": 0,
            "archive_size": 0,
            "components": []
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # 1. Create filtered SQLite database
            print("🔒 Creating filtered SQLite database...")
            source_db = Path("code_index.db")
            if source_db.exists():
                target_db = temp_path / "code_index.db"
                included, excluded = self.create_filtered_database(str(source_db), str(target_db))
                stats["files_included"] = included
                stats["files_excluded"] = excluded
                stats["components"].append("code_index.db")
                print(f"   ✅ Included: {included} files")
                print(f"   ❌ Excluded: {excluded} files")
            
            # 2. Copy vector index (if exists)
            # Note: Vector embeddings don't contain file content, so they're safe
            vector_dir = Path("vector_index.qdrant")
            if vector_dir.exists():
                print("📦 Copying vector index...")
                shutil.copytree(vector_dir, temp_path / "vector_index.qdrant")
                stats["components"].append("vector_index.qdrant")
                
            # 3. Create filtered metadata
            print("📄 Creating filtered metadata...")
            metadata_path = Path(".index_metadata.json")
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                    
                # Add security info
                metadata["security"] = {
                    "filtered": True,
                    "excluded_patterns": len(self.all_patterns),
                    "export_timestamp": stats["timestamp"],
                    "files_excluded": stats["files_excluded"]
                }
                
                with open(temp_path / ".index_metadata.json", 'w') as f:
                    json.dump(metadata, f, indent=2)
                    
                stats["components"].append(".index_metadata.json")
                
            # 4. Create the archive
            print("📦 Creating secure archive...")
            with tarfile.open(output_path, "w:gz") as tar:
                for item in temp_path.iterdir():
                    tar.add(item, arcname=item.name)
                    
            # Calculate archive size
            archive_path = Path(output_path)
            stats["archive_size"] = archive_path.stat().st_size
            
        return stats


def main():
    """Main entry point."""
    print("SECURE INDEX EXPORTER")
    print("="*60)
    
    exporter = SecureIndexExporter()
    
    # Show patterns being used
    print(f"\n📋 Loaded {len(exporter.all_patterns)} exclusion patterns")
    print("\nExample patterns:")
    for pattern in exporter.all_patterns[:5]:
        print(f"   - {pattern}")
        
    # Create secure archive
    print("\n🔐 Creating secure index archive...")
    stats = exporter.create_secure_archive()
    
    # Show results
    print(f"\n✅ Secure archive created successfully!")
    print(f"📊 Statistics:")
    print(f"   - Files included: {stats['files_included']}")
    print(f"   - Files excluded: {stats['files_excluded']}")
    print(f"   - Archive size: {stats['archive_size'] / 1024 / 1024:.2f} MB")
    print(f"   - Components: {', '.join(stats['components'])}")
    
    # Save stats
    with open("secure_export_stats.json", 'w') as f:
        json.dump(stats, f, indent=2)
        
    print(f"\n📄 Export stats saved to: secure_export_stats.json")
    print(f"📦 Secure archive saved to: secure_index_archive.tar.gz")
    print(f"📝 Excluded files logged to: excluded_files.log")
    
    # Recommendations
    print("\n💡 Next steps:")
    print("   1. Review excluded_files.log to verify correct filtering")
    print("   2. Test the archive by extracting and checking contents")
    print("   3. Use this archive for GitHub Actions artifact upload")
    print("   4. Update CI/CD scripts to use secure export")


if __name__ == "__main__":
    main()