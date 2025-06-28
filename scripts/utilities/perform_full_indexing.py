#!/usr/bin/env python3
"""Perform full repository indexing with both SQLite and vector embeddings."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.utils.semantic_indexer import SemanticIndexer


def main():
    """Perform full indexing of the repository."""
    print("🚀 Starting full repository indexing...")
    
    # Initialize SQLite store
    print("\n📊 Initializing SQLite store...")
    store = SQLiteStore("code_index.db")
    
    # Initialize dispatcher with plugin factory
    print("🔧 Initializing dispatcher...")
    dispatcher = EnhancedDispatcher(
        plugins=[],  # Empty list, will use plugin factory
        sqlite_store=store,
        use_plugin_factory=True,
        lazy_load=False  # Load all plugins immediately
    )
    
    # Initialize semantic indexer
    print("🧠 Initializing semantic indexer...")
    try:
        indexer = SemanticIndexer()
        semantic_enabled = True
        print("✅ Semantic indexer initialized successfully")
    except Exception as e:
        print(f"⚠️  Semantic indexer failed to initialize: {e}")
        semantic_enabled = False
    
    # Index the repository
    print("\n📁 Starting repository indexing...")
    root_path = Path("/app")
    
    try:
        # Perform indexing
        dispatcher.index_directory(str(root_path))
        
        # Get statistics
        stats = store.get_stats()
        print(f"\n✅ SQLite indexing complete!")
        print(f"   Files indexed: {stats.get('file_count', 0)}")
        print(f"   Symbols found: {stats.get('symbol_count', 0)}")
        
        # If semantic indexing is enabled, also create vector embeddings
        if semantic_enabled:
            print("\n🔍 Creating vector embeddings...")
            
            # Get all indexed files
            with store._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT DISTINCT f.path, f.language 
                    FROM files f
                    WHERE f.language IN ('python', 'javascript', 'typescript', 'go', 'rust', 'java')
                    LIMIT 100
                """)
                files = cursor.fetchall()
            
            print(f"   Found {len(files)} code files for vector indexing")
            
            indexed_count = 0
            for file_path, language in files:
                try:
                    if os.path.exists(file_path):
                        result = indexer.index_file(Path(file_path))
                        if result:
                            indexed_count += 1
                            if indexed_count % 10 == 0:
                                print(f"   Indexed {indexed_count} files...")
                except Exception as e:
                    print(f"   Warning: Failed to index {file_path}: {e}")
                    continue
            
            print(f"\n✅ Vector indexing complete! Indexed {indexed_count} files")
        
        print("\n🎉 Full indexing completed successfully!")
        
        # Show final status
        print("\n" + "="*50)
        os.system("python mcp_cli.py index status")
        
    except Exception as e:
        print(f"\n❌ Indexing failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())