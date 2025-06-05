#!/usr/bin/env python3
"""
Simple script to index the Code-Index-MCP codebase.
"""

import asyncio
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_server.indexer import IndexEngine
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.utils.fuzzy_indexer import FuzzyIndexer
from mcp_server.plugin_system.plugin_manager import PluginManager

async def main():
    """Index the Code-Index-MCP codebase."""
    project_path = Path(__file__).parent
    db_path = project_path / "code_index.db"
    
    print(f"🚀 Indexing Code-Index-MCP codebase")
    print(f"📁 Project path: {project_path}")
    print(f"💾 Database: {db_path}")
    print("=" * 50)
    
    # Initialize components
    print("🔧 Initializing components...")
    
    # Initialize storage
    storage = SQLiteStore(str(db_path))
    
    # Initialize fuzzy indexer
    fuzzy_indexer = FuzzyIndexer(storage)
    
    # Initialize plugin manager
    plugin_manager = PluginManager()
    plugin_manager.load_plugins()
    
    # Create index engine
    engine = IndexEngine(
        plugin_manager=plugin_manager,
        storage=storage,
        fuzzy_indexer=fuzzy_indexer,
        repository_path=str(project_path)
    )
    
    print("✅ Components initialized successfully")
    
    # Index the entire codebase
    print(f"\n📂 Starting recursive indexing...")
    print("⏳ This may take a few minutes depending on the codebase size...")
    
    # Index with file patterns for common code files
    patterns = ["*.py", "*.js", "*.ts", "*.jsx", "*.tsx", "*.c", "*.cpp", "*.h", "*.hpp", "*.java", "*.kt", "*.go", "*.rs", "*.rb", "*.php"]
    
    batch_result = await engine.index_directory(
        str(project_path), 
        recursive=True,
        patterns=patterns
    )
    
    print(f"\n✅ Indexing complete!")
    print(f"📊 Results:")
    print(f"  • Total files: {batch_result.total_files}")
    print(f"  • Successful: {batch_result.successful}")
    print(f"  • Failed: {batch_result.failed}")
    print(f"  • Duration: {batch_result.total_duration_ms / 1000:.2f} seconds")
    
    if batch_result.errors:
        print(f"\n⚠️ Errors encountered:")
        for error in batch_result.errors[:5]:  # Show first 5 errors
            print(f"  • {error}")
        if len(batch_result.errors) > 5:
            print(f"  • ... and {len(batch_result.errors) - 5} more errors")
    
    # Get index status
    print("\n📊 Index status:")
    status = engine.get_index_status(str(project_path))
    print(f"  • Total files indexed: {status.get('total_files', 0)}")
    print(f"  • Total symbols: {status.get('total_symbols', 0)}")
    print(f"  • Total references: {status.get('total_references', 0)}")
    
    print("\n✅ Indexing process completed successfully!")
    print(f"📍 Index database: {db_path}")

if __name__ == "__main__":
    asyncio.run(main())