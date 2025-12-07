#!/usr/bin/env python3
"""Test that ALL files are indexed locally but filtered on export."""

import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

# Test in a subdirectory of /app
test_dir = Path("/app/test_index_behavior")
if test_dir.exists():
    shutil.rmtree(test_dir)
test_dir.mkdir()

os.chdir(test_dir)

# Import after changing directory
sys.path.insert(0, "/app")
from secure_index_export import SecureIndexExporter

from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.storage.sqlite_store import SQLiteStore


def main():
    """Test the 'index everything, filter on share' behavior."""
    print("\n🧪 TESTING INDEX ALL, FILTER ON SHARE")
    print("=" * 60)

    # Create test files
    print("\n📁 Creating test files...")

    # Create .gitignore
    Path(".gitignore").write_text(
        """
.env
*.key
node_modules/
__pycache__/
build/
"""
    )

    # Create sensitive files that should be indexed but not shared
    Path(".env").write_text(
        """
DATABASE_URL=postgresql://user:password@localhost/db
API_KEY=super-secret-key-12345
AWS_SECRET_ACCESS_KEY=aws-secret-123
"""
    )

    Path("private.key").write_text("-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkq...")

    # Create normal files
    Path("app.py").write_text(
        """
import os

def get_api_key():
    return os.getenv('API_KEY')
    
class Application:
    def __init__(self):
        self.db_url = os.getenv('DATABASE_URL')
"""
    )

    Path("README.md").write_text("# Test Project\n\nThis is a test.")

    # Create gitignored directory
    Path("node_modules").mkdir()
    Path("node_modules/lodash.js").write_text("module.exports = {}")

    print("✅ Created files:")
    print("   - .env (sensitive)")
    print("   - private.key (sensitive)")
    print("   - app.py (normal)")
    print("   - README.md (normal)")
    print("   - node_modules/lodash.js (gitignored)")

    # Initialize storage and dispatcher
    sqlite_store = SQLiteStore("test_index.db")

    dispatcher = EnhancedDispatcher(
        sqlite_store=sqlite_store,
        enable_advanced_features=True,
        use_plugin_factory=True,
        lazy_load=True,
        semantic_search_enabled=False,
    )

    # Index the directory
    print("\n📊 Indexing directory...")
    stats = dispatcher.index_directory(Path("."), recursive=True)

    print(f"\nIndexing results:")
    print(f"  Total files: {stats['total_files']}")
    print(f"  Indexed files: {stats['indexed_files']}")

    # Check what was indexed
    conn = sqlite3.connect("test_index.db")
    cursor = conn.cursor()

    # Get the correct column name
    cursor.execute("PRAGMA table_info(files)")
    columns = [row[1] for row in cursor.fetchall()]
    path_column = "path" if "path" in columns else "file_path"

    cursor.execute(f"SELECT {path_column} FROM files ORDER BY {path_column}")
    indexed_files = [row[0] for row in cursor.fetchall()]

    print(f"\n📋 Files in local index ({len(indexed_files)} total):")
    for f in indexed_files:
        # Extract just the filename
        filename = Path(f).name
        is_sensitive = (
            any(pattern in filename for pattern in [".env", ".key"]) or "node_modules" in f
        )
        status = "🔐 SENSITIVE" if is_sensitive else "✅ Normal"
        print(f"   {status} {filename}")

    # Check if sensitive files ARE indexed
    env_indexed = any(".env" in f for f in indexed_files)
    key_indexed = any("private.key" in f for f in indexed_files)
    node_indexed = any("node_modules" in f for f in indexed_files)

    print(f"\n🔍 Local search capabilities:")
    print(f"   Can search .env files: {'✅ YES' if env_indexed else '❌ NO'}")
    print(f"   Can search .key files: {'✅ YES' if key_indexed else '❌ NO'}")
    print(f"   Can search node_modules: {'✅ YES' if node_indexed else '❌ NO'}")

    if not (env_indexed and key_indexed and node_indexed):
        print("\n⚠️  WARNING: Not all files were indexed!")
        print("   The current implementation still filters during indexing.")
        print("   To enable 'index all, filter on share' behavior:")
        print("   1. Remove ignore checks from dispatcher_enhanced.py")
        print("   2. Remove ignore checks from watcher.py")
        print("   3. Keep filtering in secure_index_export.py")

    # Test export filtering
    print(f"\n🔒 Testing secure export (simulation)...")
    exporter = SecureIndexExporter()

    # Simulate what would be excluded
    excluded_files = []
    included_files = []

    for file_path in indexed_files:
        if exporter._should_exclude(file_path):
            excluded_files.append(Path(file_path).name)
        else:
            included_files.append(Path(file_path).name)

    # Also check files that WOULD be indexed if we indexed everything
    all_possible_files = [".env", "private.key", "app.py", "README.md", "node_modules/lodash.js"]

    print(f"\n📦 Export simulation (if all files were indexed):")
    for filename in all_possible_files:
        test_path = str(Path.cwd() / filename)
        would_exclude = exporter._should_exclude(test_path)
        status = "❌ EXCLUDE" if would_exclude else "✅ INCLUDE"
        print(f"   {status} {filename}")

    print(f"\n🎯 Desired Behavior:")
    print("   1. ALL files indexed locally (including .env, secrets)")
    print("   2. Sensitive files filtered ONLY during export")
    print("   3. Developers can search everything locally")
    print("   4. Shared indexes are always safe")

    conn.close()

    # Cleanup
    os.chdir("/app")
    shutil.rmtree(test_dir)

    print("\n✅ Test completed!")


if __name__ == "__main__":
    main()
