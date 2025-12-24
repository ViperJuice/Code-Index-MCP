#!/usr/bin/env python3
"""Test that ALL files are indexed locally but filtered on export."""

import sqlite3
import tempfile
from pathlib import Path

from secure_index_export import SecureIndexExporter

from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.storage.sqlite_store import SQLiteStore


def test_index_all_filter_on_share():
    """Test the 'index everything, filter on share' behavior."""
    print("\n🧪 TESTING INDEX ALL, FILTER ON SHARE")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)

        # Create test files
        print("\n📁 Creating test files...")

        # Create .gitignore
        (root / ".gitignore").write_text(
            """
.env
*.key
node_modules/
__pycache__/
"""
        )

        # Create sensitive files that should be indexed but not shared
        (root / ".env").write_text(
            """
DATABASE_URL=postgresql://user:password@localhost/db
API_KEY=super-secret-key-12345
AWS_SECRET_ACCESS_KEY=aws-secret-123
"""
        )

        (root / "private.key").write_text("-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkq...")

        # Create normal files
        (root / "app.py").write_text(
            """
import os

def get_api_key():
    return os.getenv('API_KEY')
    
class Application:
    def __init__(self):
        self.db_url = os.getenv('DATABASE_URL')
"""
        )

        (root / "config.json").write_text('{"debug": true, "port": 3000}')

        # Create node_modules (should be indexed but not shared)
        (root / "node_modules").mkdir()
        (root / "node_modules" / "lodash.js").write_text("module.exports = {}")

        print("✅ Created files:")
        print("   - .env (sensitive)")
        print("   - private.key (sensitive)")
        print("   - app.py (normal)")
        print("   - config.json (normal)")
        print("   - node_modules/lodash.js (gitignored)")

        # Initialize storage and dispatcher
        db_path = root / "test_index.db"
        sqlite_store = SQLiteStore(str(db_path))

        dispatcher = EnhancedDispatcher(
            sqlite_store=sqlite_store,
            enable_advanced_features=True,
            use_plugin_factory=True,
            lazy_load=True,
            semantic_search_enabled=False,
        )

        # Index the directory
        print("\n📊 Indexing directory...")
        stats = dispatcher.index_directory(root, recursive=True)

        print("\nIndexing results:")
        print(f"  Total files: {stats['total_files']}")
        print(f"  Indexed files: {stats['indexed_files']}")
        print(f"  Ignored files: {stats['ignored_files']}")  # Should be 0 now!

        # Check what was indexed
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT path FROM files ORDER BY path")
        indexed_files = [row[0] for row in cursor.fetchall()]

        print("\n📋 Files in local index:")
        for f in indexed_files:
            relative_path = Path(f).relative_to(root)
            is_sensitive = any(
                pattern in str(relative_path) for pattern in [".env", ".key", "node_modules"]
            )
            status = "🔐 SENSITIVE" if is_sensitive else "✅ Normal"
            print(f"   {status} {relative_path}")

        # Verify sensitive files ARE indexed
        env_indexed = any(".env" in f for f in indexed_files)
        key_indexed = any("private.key" in f for f in indexed_files)
        node_indexed = any("node_modules" in f for f in indexed_files)

        print("\n🔍 Local search capabilities:")
        print(f"   Can search .env files: {'✅ YES' if env_indexed else '❌ NO'}")
        print(f"   Can search .key files: {'✅ YES' if key_indexed else '❌ NO'}")
        print(f"   Can search node_modules: {'✅ YES' if node_indexed else '❌ NO'}")

        # Test searching for secrets
        print("\n🔎 Testing local search for secrets...")
        results = list(dispatcher.search("API_KEY", limit=10))
        if results:
            print(f"   ✅ Found {len(results)} results for 'API_KEY'")
            for r in results:
                print(f"      - {Path(r['file']).name}: {r['snippet'][:50]}...")
        else:
            print("   ❌ No results for 'API_KEY' (should find it!)")

        # Now test export filtering
        print("\n🔒 Testing secure export...")

        # Create export
        export_db = root / "export_index.db"
        exporter = SecureIndexExporter()

        # First, let's see what would be excluded
        excluded_count = 0
        for file_path in indexed_files:
            if exporter._should_exclude(file_path):
                excluded_count += 1
                print(f"   Will exclude: {Path(file_path).name}")

        # Create filtered export
        included, excluded = exporter.create_filtered_database(str(db_path), str(export_db))

        print("\n📦 Export results:")
        print(f"   Files included: {included}")
        print(f"   Files excluded: {excluded}")

        # Check what's in the exported database
        export_conn = sqlite3.connect(export_db)
        export_cursor = export_conn.cursor()

        export_cursor.execute("SELECT path FROM files ORDER BY path")
        exported_files = [row[0] for row in export_cursor.fetchall()]

        print("\n📋 Files in exported index:")
        for f in exported_files:
            relative_path = Path(f).relative_to(root)
            print(f"   ✅ {relative_path}")

        # Verify sensitive files are NOT in export
        env_exported = any(".env" in f for f in exported_files)
        key_exported = any("private.key" in f for f in exported_files)
        node_exported = any("node_modules" in f for f in exported_files)

        print("\n🔐 Security verification:")
        print(f"   .env in export: {'❌ FAIL' if env_exported else '✅ NO (correct)'}")
        print(f"   .key in export: {'❌ FAIL' if key_exported else '✅ NO (correct)'}")
        print(f"   node_modules in export: {'❌ FAIL' if node_exported else '✅ NO (correct)'}")

        # Summary
        print("\n" + "=" * 60)
        print("SUMMARY:")

        all_indexed = env_indexed and key_indexed and node_indexed
        none_exported = not env_exported and not key_exported and not node_exported

        if all_indexed and none_exported:
            print("✅ SUCCESS: All files indexed locally, sensitive files filtered on export!")
            print("   - Local search includes .env, secrets, node_modules")
            print("   - Exported index is clean and safe to share")
        else:
            print("❌ FAIL:")
            if not all_indexed:
                print("   - Not all files were indexed locally")
            if not none_exported:
                print("   - Sensitive files leaked to export!")

        conn.close()
        export_conn.close()

        return all_indexed and none_exported


if __name__ == "__main__":
    success = test_index_all_filter_on_share()
    exit(0 if success else 1)
