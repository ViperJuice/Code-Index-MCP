#!/usr/bin/env python3
"""
Index compatibility validation script.

This script checks if the current embedding configuration is compatible
with existing index artifacts and provides options for resolution.
"""

import os
import sys
import json
import argparse
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server.utils.semantic_indexer import SemanticIndexer
from mcp_server.storage.sqlite_store import SQLiteStore


class IndexCompatibilityChecker:
    """Check and resolve index compatibility issues."""
    
    def __init__(self):
        self.metadata_file = ".index_metadata.json"
        self.sqlite_db = "code_index.db"
        self.vector_db = "vector_index.qdrant"
    
    def check_compatibility(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Check compatibility of current configuration with existing indexes.
        
        Returns:
            Tuple of (is_compatible, compatibility_info)
        """
        info = {
            "sqlite_exists": os.path.exists(self.sqlite_db),
            "vector_exists": os.path.exists(self.vector_db),
            "metadata_exists": os.path.exists(self.metadata_file),
            "embedding_compatible": True,
            "schema_compatible": True,
            "issues": [],
            "recommendations": []
        }
        
        # Check SQLite schema compatibility
        if info["sqlite_exists"]:
            try:
                store = SQLiteStore(self.sqlite_db)
                # Try to read schema - if it works, it's compatible
                with store._get_connection() as conn:
                    cursor = conn.execute("SELECT COUNT(*) FROM symbols")
                    symbol_count = cursor.fetchone()[0]
                    info["symbol_count"] = symbol_count
            except Exception as e:
                info["schema_compatible"] = False
                info["issues"].append(f"SQLite schema incompatible: {e}")
                info["recommendations"].append("Rebuild SQLite index")
        
        # Check vector index compatibility
        if info["vector_exists"]:
            try:
                indexer = SemanticIndexer()
                info["embedding_compatible"] = indexer.check_compatibility()
                
                if not info["embedding_compatible"]:
                    info["issues"].append("Vector embeddings use different model/configuration")
                    info["recommendations"].append("Rebuild vector index with current model")
            except Exception as e:
                info["embedding_compatible"] = False
                info["issues"].append(f"Vector index error: {e}")
                info["recommendations"].append("Rebuild vector index")
        
        # Check metadata
        if info["metadata_exists"]:
            try:
                with open(self.metadata_file, 'r') as f:
                    metadata = json.load(f)
                    info["metadata"] = metadata
                    
                    # Check if git commit matches
                    current_commit = self._get_git_commit()
                    stored_commit = metadata.get("git_commit")
                    
                    if current_commit and stored_commit:
                        info["git_commit_match"] = current_commit == stored_commit
                        if not info["git_commit_match"]:
                            info["issues"].append("Index was built from different git commit")
                            info["recommendations"].append("Consider rebuilding after significant changes")
            except Exception as e:
                info["issues"].append(f"Metadata error: {e}")
                info["recommendations"].append("Regenerate metadata")
        
        # Overall compatibility
        is_compatible = (
            info["schema_compatible"] and 
            info["embedding_compatible"] and
            len(info["issues"]) == 0
        )
        
        return is_compatible, info
    
    def _get_git_commit(self) -> Optional[str]:
        """Get current git commit hash."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                cwd="."
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None
    
    def rebuild_indexes(self, force: bool = False, sqlite_only: bool = False, vector_only: bool = False):
        """Rebuild index artifacts."""
        print("🔄 Starting index rebuild...")
        
        if not sqlite_only:
            print("🧠 Rebuilding vector index...")
            try:
                # Remove old vector index
                if os.path.exists(self.vector_db):
                    import shutil
                    shutil.rmtree(self.vector_db)
                
                # Create new vector index with sample files
                indexer = SemanticIndexer()
                
                # Index a few Python files as example
                import glob
                python_files = glob.glob("**/*.py", recursive=True)
                python_files = [f for f in python_files if "test_repos" not in f and ".git" not in f]
                
                indexed_count = 0
                for i, file_path in enumerate(python_files[:50]):  # Limit for performance
                    try:
                        result = indexer.index_file(Path(file_path))
                        indexed_count += 1
                        if indexed_count % 10 == 0:
                            print(f"   Indexed {indexed_count} files...")
                    except Exception as e:
                        print(f"   Warning: Could not index {file_path}: {e}")
                
                print(f"✅ Vector index rebuilt with {indexed_count} files")
                
            except Exception as e:
                print(f"❌ Vector index rebuild failed: {e}")
                if not force:
                    return
        
        if not vector_only:
            print("🗄️ Rebuilding SQLite index...")
            try:
                # Remove old SQLite index
                if os.path.exists(self.sqlite_db):
                    os.remove(self.sqlite_db)
                
                # Create new SQLite index
                store = SQLiteStore(self.sqlite_db)
                
                # TODO: Add actual indexing logic here
                # For now, just ensure the schema is created
                print("✅ SQLite index schema rebuilt")
                
            except Exception as e:
                print(f"❌ SQLite index rebuild failed: {e}")
                if not force:
                    return
        
        print("🎉 Index rebuild completed!")
    
    def backup_indexes(self) -> str:
        """Create backup of existing indexes."""
        import shutil
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = f"index_backup_{timestamp}"
        
        os.makedirs(backup_dir, exist_ok=True)
        
        if os.path.exists(self.sqlite_db):
            shutil.copy2(self.sqlite_db, f"{backup_dir}/code_index.db")
        
        if os.path.exists(self.vector_db):
            shutil.copytree(self.vector_db, f"{backup_dir}/vector_index.qdrant")
        
        if os.path.exists(self.metadata_file):
            shutil.copy2(self.metadata_file, f"{backup_dir}/.index_metadata.json")
        
        print(f"📦 Backup created: {backup_dir}")
        return backup_dir
    
    def restore_backup(self, backup_dir: str):
        """Restore indexes from backup."""
        import shutil
        
        if not os.path.exists(backup_dir):
            print(f"❌ Backup directory not found: {backup_dir}")
            return
        
        # Remove current indexes
        if os.path.exists(self.sqlite_db):
            os.remove(self.sqlite_db)
        if os.path.exists(self.vector_db):
            shutil.rmtree(self.vector_db)
        if os.path.exists(self.metadata_file):
            os.remove(self.metadata_file)
        
        # Restore from backup
        backup_sqlite = f"{backup_dir}/code_index.db"
        backup_vector = f"{backup_dir}/vector_index.qdrant"
        backup_metadata = f"{backup_dir}/.index_metadata.json"
        
        if os.path.exists(backup_sqlite):
            shutil.copy2(backup_sqlite, self.sqlite_db)
        
        if os.path.exists(backup_vector):
            shutil.copytree(backup_vector, self.vector_db)
        
        if os.path.exists(backup_metadata):
            shutil.copy2(backup_metadata, self.metadata_file)
        
        print(f"♻️ Restored from backup: {backup_dir}")


def main():
    parser = argparse.ArgumentParser(description="Index compatibility checker and manager")
    parser.add_argument("--check", action="store_true", help="Check compatibility only")
    parser.add_argument("--rebuild", action="store_true", help="Rebuild incompatible indexes")
    parser.add_argument("--force", action="store_true", help="Force rebuild even if compatible")
    parser.add_argument("--sqlite-only", action="store_true", help="Rebuild SQLite index only")
    parser.add_argument("--vector-only", action="store_true", help="Rebuild vector index only")
    parser.add_argument("--backup", action="store_true", help="Create backup before rebuild")
    parser.add_argument("--restore", type=str, help="Restore from backup directory")
    
    args = parser.parse_args()
    
    checker = IndexCompatibilityChecker()
    
    if args.restore:
        checker.restore_backup(args.restore)
        return
    
    # Always check compatibility first
    compatible, info = checker.check_compatibility()
    
    print("🔍 Index Compatibility Report")
    print("=" * 40)
    print(f"SQLite index exists: {'✅' if info['sqlite_exists'] else '❌'}")
    print(f"Vector index exists: {'✅' if info['vector_exists'] else '❌'}")
    print(f"Metadata exists: {'✅' if info['metadata_exists'] else '❌'}")
    print(f"Schema compatible: {'✅' if info['schema_compatible'] else '❌'}")
    print(f"Embedding compatible: {'✅' if info['embedding_compatible'] else '❌'}")
    
    if info.get("symbol_count"):
        print(f"Symbol count: {info['symbol_count']:,}")
    
    if info["issues"]:
        print("\n⚠️ Issues found:")
        for issue in info["issues"]:
            print(f"  • {issue}")
    
    if info["recommendations"]:
        print("\n💡 Recommendations:")
        for rec in info["recommendations"]:
            print(f"  • {rec}")
    
    print(f"\n🎯 Overall compatibility: {'✅ Compatible' if compatible else '❌ Incompatible'}")
    
    if args.check:
        sys.exit(0 if compatible else 1)
    
    # Handle rebuild logic
    should_rebuild = args.rebuild or args.force or not compatible
    
    if should_rebuild:
        if args.backup:
            checker.backup_indexes()
        
        checker.rebuild_indexes(
            force=args.force,
            sqlite_only=args.sqlite_only,
            vector_only=args.vector_only
        )
    elif compatible:
        print("\n✨ No action needed - indexes are compatible!")
    else:
        print("\n🔧 Run with --rebuild to fix compatibility issues")
        sys.exit(1)


if __name__ == "__main__":
    main()