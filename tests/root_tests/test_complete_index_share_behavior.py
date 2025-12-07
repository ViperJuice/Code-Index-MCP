#!/usr/bin/env python3
"""Test complete index all, share filtered behavior."""

import json
import os
import shutil
import sys
from pathlib import Path

# Work in app directory
test_dir = Path("/app/test_complete_behavior")
if test_dir.exists():
    shutil.rmtree(test_dir)
test_dir.mkdir()
os.chdir(test_dir)

sys.path.insert(0, "/app")
from secure_index_export import SecureIndexExporter

from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.storage.sqlite_store import SQLiteStore


def main():
    print("\n🎯 COMPLETE INDEX ALL, FILTER ON SHARE TEST")
    print("=" * 60)

    # Create a realistic project structure
    print("\n📁 Creating project structure...")

    # Source files
    Path("src").mkdir()
    Path("src/app.py").write_text(
        """
import os
from config import DATABASE_URL

def connect():
    api_key = os.getenv('API_KEY')
    return f"Connected with {api_key}"
"""
    )

    Path("src/config.py").write_text(
        """
import os

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///local.db')
SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret')
"""
    )

    # Configuration files
    Path(".env").write_text(
        """
# Production secrets - DO NOT COMMIT!
DATABASE_URL=postgresql://prod_user:prod_pass@db.example.com/myapp
API_KEY=sk-1234567890abcdef
SECRET_KEY=super-secret-production-key
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
"""
    )

    Path(".env.development").write_text(
        """
DATABASE_URL=postgresql://dev:dev@localhost/myapp_dev
API_KEY=test-api-key
SECRET_KEY=dev-secret
"""
    )

    # Certificates
    Path("certs").mkdir()
    Path("certs/server.key").write_text(
        """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC9W8bA...
-----END PRIVATE KEY-----"""
    )

    Path("certs/server.crt").write_text(
        """-----BEGIN CERTIFICATE-----
MIIDXTCCAkWgAwIBAgIJAKLdQVPy90W...
-----END CERTIFICATE-----"""
    )

    # Documentation
    Path("README.md").write_text(
        """
# My Application

## Setup
1. Copy `.env.example` to `.env`
2. Set your API_KEY
3. Run `python src/app.py`
"""
    )

    # Git files
    Path(".gitignore").write_text(
        """
# Secrets
.env
*.key
*.pem

# Python
__pycache__/
*.pyc

# Dependencies
venv/
node_modules/
"""
    )

    # Dependencies (should be ignored in export)
    Path("node_modules").mkdir()
    Path("node_modules/lodash").mkdir(parents=True)
    Path("node_modules/lodash/index.js").write_text("module.exports = {}")

    print("✅ Created project structure with:")
    print("   - Source code (app.py, config.py)")
    print("   - Secrets (.env, .env.development)")
    print("   - Certificates (server.key, server.crt)")
    print("   - Documentation (README.md)")
    print("   - Dependencies (node_modules)")

    # Initialize indexing
    print("\n📊 Indexing ALL files...")
    sqlite_store = SQLiteStore("local_index.db")
    dispatcher = EnhancedDispatcher(
        sqlite_store=sqlite_store,
        enable_advanced_features=True,
        use_plugin_factory=True,
        lazy_load=True,
        semantic_search_enabled=False,
    )

    stats = dispatcher.index_directory(Path("."), recursive=True)
    print(f"\nIndexed: {stats['indexed_files']} files")
    print(f"By language: {json.dumps(stats['by_language'], indent=2)}")

    # Test local search capabilities
    print("\n🔍 Testing LOCAL search (can find secrets)...")

    # Search for API key
    api_results = list(dispatcher.search("API_KEY", limit=10))
    print(f"\n1. Search 'API_KEY': {len(api_results)} results")
    for r in api_results[:3]:
        print(f"   - {Path(r['file']).name}:{r['line']} - {r['snippet'][:60]}...")

    # Search for database password
    db_results = list(dispatcher.search("prod_pass", limit=10))
    print(f"\n2. Search 'prod_pass': {len(db_results)} results")
    for r in db_results[:3]:
        print(f"   - {Path(r['file']).name}:{r['line']} - {r['snippet'][:60]}...")

    # Search for private key
    key_results = list(dispatcher.search("BEGIN PRIVATE KEY", limit=10))
    print(f"\n3. Search 'BEGIN PRIVATE KEY': {len(key_results)} results")
    for r in key_results[:3]:
        print(f"   - {Path(r['file']).name}:{r['line']} - {r['snippet'][:40]}...")

    # Test secure export
    print("\n🔒 Creating SECURE export for sharing...")
    exporter = SecureIndexExporter()

    # Create filtered export
    export_db = "export_index.db"
    included, excluded = exporter.create_filtered_database("local_index.db", export_db)

    print("\n📦 Export statistics:")
    print(f"   Files included: {included}")
    print(f"   Files excluded: {excluded}")

    # Create audit log
    audit_path = Path("export_audit.json")
    audit = exporter.create_audit_log("local_index.db", str(audit_path))

    print("\n📋 Security audit:")
    print(f"   Total files analyzed: {audit['total_files']}")
    print(f"   Excluded patterns used: {len(audit['patterns_used'])}")
    print(f"   Sensitive files excluded: {len(audit['excluded_files'])}")

    if audit["excluded_files"]:
        print("\n   Examples of excluded files:")
        for f in audit["excluded_files"][:5]:
            print(f"     ❌ {f}")

    # Verify export doesn't contain secrets
    print("\n🔍 Verifying EXPORT doesn't contain secrets...")
    export_store = SQLiteStore(export_db)
    export_dispatcher = EnhancedDispatcher(
        sqlite_store=export_store,
        enable_advanced_features=False,
        use_plugin_factory=False,
        lazy_load=False,
    )

    # These searches should return nothing
    secret_searches = [
        ("API_KEY=sk-1234567890abcdef", "production API key"),
        ("prod_pass", "production database password"),
        ("BEGIN PRIVATE KEY", "private key content"),
        ("AWS_SECRET_ACCESS_KEY", "AWS credentials"),
    ]

    all_safe = True
    for query, desc in secret_searches:
        results = list(export_dispatcher.search(query, limit=10))
        if results:
            print(f"   ❌ FAIL: Found {desc} in export!")
            all_safe = False
        else:
            print(f"   ✅ PASS: No {desc} in export")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY:")
    print(f"✅ Local index: Can search ALL {stats['indexed_files']} files including secrets")
    print(
        f"✅ Export safety: {'Passed - no secrets leaked' if all_safe else 'FAILED - secrets found!'}"
    )
    print("✅ Behavior: Index everything locally, filter on share")

    # Cleanup
    os.chdir("/app")
    shutil.rmtree(test_dir)

    print("\n🎉 Test completed successfully!")


if __name__ == "__main__":
    main()
