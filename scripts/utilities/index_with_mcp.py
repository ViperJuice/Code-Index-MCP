#!/usr/bin/env python3
"""Index repository using MCP server components."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import asyncio

# Load environment variables
load_dotenv()

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.watcher import FileWatcher
from mcp_server.dispatcher.dispatcher import Dispatcher
from mcp_server.plugin_system import PluginManager


async def main():
    """Index the repository using MCP components."""
    print("🚀 Starting MCP-based repository indexing...")
    
    # Initialize SQLite store
    print("\n📊 Initializing SQLite store...")
    sqlite_store = SQLiteStore("code_index.db")
    
    # Initialize plugin manager
    print("🔌 Initializing plugin manager...")
    plugin_manager = PluginManager()
    plugin_instances = await plugin_manager.load_plugins(sqlite_store=sqlite_store)
    print(f"✅ Loaded {len(plugin_instances)} plugins")
    
    # Create dispatcher with plugins
    print("🔧 Creating dispatcher...")
    dispatcher = Dispatcher(plugin_instances)
    
    # Create file watcher (which handles indexing)
    print("👁️ Creating file watcher...")
    root_path = Path("/app")
    watcher = FileWatcher(root_path, dispatcher)
    
    # Index all files in the directory
    print(f"\n📁 Indexing all files in {root_path}...")
    
    # Get all files recursively
    all_files = []
    for ext in ['*.py', '*.js', '*.ts', '*.go', '*.rs', '*.java', '*.md', '*.txt']:
        all_files.extend(root_path.rglob(ext))
    
    # Filter out unwanted directories
    filtered_files = []
    exclude_dirs = {'.git', '__pycache__', '.venv', 'venv', 'node_modules', 'test_repos', '.pytest_cache'}
    for file_path in all_files:
        if not any(excluded in str(file_path) for excluded in exclude_dirs):
            filtered_files.append(file_path)
    
    print(f"Found {len(filtered_files)} files to index")
    
    # Index each file
    indexed_count = 0
    for i, file_path in enumerate(filtered_files):
        try:
            # Trigger indexing through the watcher's on_created event
            await watcher.on_created(str(file_path))
            indexed_count += 1
            
            if (i + 1) % 50 == 0:
                print(f"Progress: {i + 1}/{len(filtered_files)} files processed")
                
        except Exception as e:
            print(f"Warning: Failed to index {file_path}: {e}")
            continue
    
    print(f"\n✅ SQLite indexing complete! Indexed {indexed_count} files")
    
    # Get final statistics
    stats = sqlite_store.get_stats()
    print(f"\n📊 Final Statistics:")
    print(f"   Files indexed: {stats.get('file_count', 0)}")
    print(f"   Symbols found: {stats.get('symbol_count', 0)}")
    
    # Check current status
    print("\n" + "="*50)
    os.system("python mcp_cli.py index status")
    
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))