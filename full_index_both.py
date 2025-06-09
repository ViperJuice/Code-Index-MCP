#!/usr/bin/env python3
"""Perform complete indexing: both SQLite and vector embeddings."""

import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.utils.semantic_indexer import SemanticIndexer
from mcp_server.utils.treesitter_wrapper import TreeSitterWrapper
from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.plugins.plugin_factory import PluginFactory


def index_with_sqlite(store, dispatcher, root_path):
    """Index files using SQLite store."""
    print("\n📊 Phase 1: SQLite Indexing")
    print("=" * 50)
    
    # Get all code files
    extensions = [
        '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go', '.rs', '.cpp', '.c', 
        '.h', '.hpp', '.cs', '.rb', '.php', '.swift', '.kt', '.scala', '.r',
        '.md', '.txt', '.json', '.yaml', '.yml', '.toml', '.xml', '.html', '.css'
    ]
    
    all_files = []
    exclude_dirs = {
        '.git', '__pycache__', '.venv', 'venv', 'node_modules', 'test_repos', 
        '.pytest_cache', 'htmlcov', '.tox', 'dist', 'build', '.eggs'
    }
    
    for root, dirs, files in os.walk(root_path):
        # Remove excluded directories from dirs to prevent walking into them
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                file_path = Path(root) / file
                if not any(excluded in str(file_path) for excluded in exclude_dirs):
                    all_files.append(file_path)
    
    print(f"Found {len(all_files)} files to index")
    
    # Index each file using dispatcher
    indexed_count = 0
    symbol_count = 0
    
    for i, file_path in enumerate(all_files):
        try:
            # Determine language
            ext = file_path.suffix.lower()
            language = {
                '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
                '.jsx': 'javascript', '.tsx': 'typescript', '.java': 'java',
                '.go': 'go', '.rs': 'rust', '.cpp': 'cpp', '.c': 'c',
                '.h': 'c', '.hpp': 'cpp', '.cs': 'csharp', '.rb': 'ruby',
                '.php': 'php', '.swift': 'swift', '.kt': 'kotlin',
                '.scala': 'scala', '.r': 'r', '.md': 'markdown',
                '.txt': 'plaintext', '.json': 'json', '.yaml': 'yaml',
                '.yml': 'yaml', '.toml': 'toml', '.xml': 'xml',
                '.html': 'html', '.css': 'css'
            }.get(ext, 'plaintext')
            
            # Get or create plugin for this language
            plugin = dispatcher.get_plugin(language)
            if plugin:
                # Read file content
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                
                # Index the file
                result = plugin.index_file(str(file_path), content)
                if result and 'symbols' in result:
                    indexed_count += 1
                    symbol_count += len(result['symbols'])
            
            if (i + 1) % 100 == 0:
                print(f"Progress: {i + 1}/{len(all_files)} files processed ({indexed_count} indexed, {symbol_count} symbols)")
                
        except Exception as e:
            # Silently skip files that can't be indexed
            continue
    
    print(f"\n✅ SQLite indexing complete!")
    print(f"   Files indexed: {indexed_count}")
    print(f"   Symbols found: {symbol_count}")
    
    return indexed_count, all_files


def index_with_vectors(indexer, files, max_files=500):
    """Create vector embeddings for files."""
    print("\n🧠 Phase 2: Vector Embeddings")
    print("=" * 50)
    
    # Filter to only code files for vector indexing
    code_extensions = {'.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go', '.rs', 
                      '.cpp', '.c', '.h', '.hpp', '.cs', '.rb', '.php', '.swift', 
                      '.kt', '.scala', '.r'}
    
    code_files = [f for f in files if f.suffix.lower() in code_extensions]
    
    # Limit number of files for vector indexing to avoid API limits
    if len(code_files) > max_files:
        print(f"Limiting vector indexing to {max_files} files (from {len(code_files)} total)")
        code_files = code_files[:max_files]
    
    print(f"Creating embeddings for {len(code_files)} code files...")
    
    indexed_count = 0
    batch_size = 10
    
    for i in range(0, len(code_files), batch_size):
        batch = code_files[i:i + batch_size]
        
        for file_path in batch:
            try:
                result = indexer.index_file(file_path)
                if result:
                    indexed_count += 1
            except Exception as e:
                # Skip files that fail
                continue
        
        print(f"Progress: {min(i + batch_size, len(code_files))}/{len(code_files)} files embedded")
        time.sleep(0.1)  # Small delay to avoid rate limits
    
    print(f"\n✅ Vector indexing complete! Created embeddings for {indexed_count} files")
    
    return indexed_count


def main():
    """Perform full indexing of the repository."""
    print("🚀 Starting complete repository indexing (SQLite + Vectors)")
    print("=" * 70)
    
    try:
        # Initialize SQLite store
        print("\n📦 Initializing storage...")
        store = SQLiteStore("code_index.db")
        
        # Initialize dispatcher
        print("🔧 Initializing plugin system...")
        dispatcher = EnhancedDispatcher(
            plugins=[],
            sqlite_store=store,
            use_plugin_factory=True,
            lazy_load=False,
            semantic_search_enabled=False  # We'll handle semantic separately
        )
        
        # Perform SQLite indexing
        root_path = Path("/app")
        sqlite_count, all_files = index_with_sqlite(store, dispatcher, root_path)
        
        # Initialize semantic indexer for vector embeddings
        print("\n🔍 Initializing semantic indexer...")
        try:
            indexer = SemanticIndexer(
                collection="code-embeddings",
                qdrant_path="./vector_index.qdrant"
            )
            
            # Perform vector indexing
            vector_count = index_with_vectors(indexer, all_files)
            
        except Exception as e:
            print(f"⚠️  Vector indexing failed: {e}")
            print("Continuing with SQLite index only...")
            vector_count = 0
        
        # Final report
        print("\n" + "=" * 70)
        print("🎉 INDEXING COMPLETE!")
        print("=" * 70)
        
        # Get final stats
        stats = store.get_stats()
        print(f"\n📊 Final Statistics:")
        print(f"   SQLite Index:")
        print(f"     - Files: {stats.get('file_count', 0)}")
        print(f"     - Symbols: {stats.get('symbol_count', 0)}")
        print(f"   Vector Index:")
        print(f"     - Embeddings: {vector_count}")
        
        # Show index status
        print("\n📋 Index Status Report:")
        print("-" * 50)
        os.system("python mcp_cli.py index status")
        
        print("\n✅ All indexing operations completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Fatal error during indexing: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())