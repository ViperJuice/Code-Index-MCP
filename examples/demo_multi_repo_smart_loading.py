#!/usr/bin/env python3
"""Demo script showcasing multi-repository support and smart plugin loading."""

import os
import sys
import logging
import sqlite3
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.storage.multi_repo_manager import MultiRepoIndexManager
from mcp_server.plugins.repository_plugin_loader import RepositoryAwarePluginLoader
from mcp_server.plugins.memory_aware_manager import MemoryAwarePluginManager
from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def demo_repository_language_detection():
    """Demonstrate language detection from repository index."""
    print("\n" + "="*60)
    print("Demo: Repository Language Detection")
    print("="*60)
    
    # Use current repository index
    index_path = Path(".indexes/f7b49f5d0ae0/current.db")
    if not index_path.exists():
        print(f"Index not found at {index_path}")
        return
        
    store = SQLiteStore(str(index_path))
    loader = RepositoryAwarePluginLoader(store)
    
    # Show detected languages
    print(f"\nLanguages detected in repository:")
    stats = loader.get_language_stats()
    for lang, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
        plugin_lang = loader._map_to_plugin_language(lang)
        print(f"  {lang:15} -> {plugin_lang:15} ({count} files)")
        
    # Show plugin loading plan
    print(f"\nPlugin loading strategy: {os.getenv('MCP_PLUGIN_STRATEGY', 'auto')}")
    required = loader.get_required_plugins()
    print(f"Plugins to load: {len(required)} (vs 47 total)")
    print(f"Memory savings: ~{(1 - len(required)/47) * 100:.0f}%")
    

def demo_memory_aware_loading():
    """Demonstrate memory-aware plugin loading."""
    print("\n" + "="*60)
    print("Demo: Memory-Aware Plugin Loading")
    print("="*60)
    
    # Create memory manager
    manager = MemoryAwarePluginManager(
        max_memory_mb=1024,
        min_free_mb=256
    )
    
    # Simulate loading plugins
    print("\nSimulating plugin loads with memory tracking:")
    
    import asyncio
    
    async def load_plugins():
        languages = ["python", "javascript", "typescript", "go", "rust"]
        
        for lang in languages:
            print(f"\nLoading {lang} plugin...")
            
            # Mock plugin creation
            from unittest.mock import Mock
            mock_plugin = Mock()
            mock_plugin.lang = lang
            
            # Simulate memory usage
            manager._cache_plugin(lang, mock_plugin)
            
            # Show memory stats
            stats = manager.get_memory_usage()
            print(f"  Loaded plugins: {stats['loaded_plugins']}")
            print(f"  Plugin memory: {stats['plugin_memory_mb']:.1f} MB")
            print(f"  Memory pressure: {stats['memory_pressure']:.2f}")
            
    asyncio.run(load_plugins())
    
    # Demonstrate eviction
    print("\nDemonstrating LRU eviction:")
    print("Eviction candidates (in order):")
    candidates = manager._get_eviction_candidates()
    for i, lang in enumerate(candidates[:3]):
        print(f"  {i+1}. {lang}")
        

def demo_multi_repository_search():
    """Demonstrate multi-repository search capabilities."""
    print("\n" + "="*60)
    print("Demo: Multi-Repository Search")
    print("="*60)
    
    # Check available repositories
    index_base = Path(".indexes")
    if not index_base.exists():
        print("No .indexes directory found")
        return
        
    # List available repositories
    print("\nAvailable repository indexes:")
    repo_count = 0
    for repo_dir in index_base.iterdir():
        if repo_dir.is_dir() and (repo_dir / "current.db").exists():
            repo_count += 1
            
            # Try to get language stats
            try:
                conn = sqlite3.connect(str(repo_dir / "current.db"))
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(DISTINCT language) as lang_count,
                           COUNT(*) as file_count
                    FROM files
                    WHERE language IS NOT NULL
                """)
                lang_count, file_count = cursor.fetchone()
                conn.close()
                
                print(f"  {repo_dir.name}: {lang_count} languages, {file_count} files")
            except:
                print(f"  {repo_dir.name}: <unable to read stats>")
                
    print(f"\nTotal repositories: {repo_count}")
    
    # Demonstrate repository ID resolution
    print("\nRepository ID resolution examples:")
    test_ids = [
        "https://github.com/user/repo.git",
        "/home/user/projects/myproject",
        "f7b49f5d0ae0"  # Already a repo ID
    ]
    
    for test_id in test_ids:
        repo_id = MultiRepoIndexManager.resolve_repo_id(test_id)
        print(f"  {test_id:40} -> {repo_id}")
        

def demo_enhanced_dispatcher_config():
    """Demonstrate enhanced dispatcher configuration."""
    print("\n" + "="*60)
    print("Demo: Enhanced Dispatcher Configuration")
    print("="*60)
    
    # Show configuration options
    print("\nConfiguration environment variables:")
    config_vars = [
        ("MCP_PLUGIN_STRATEGY", "auto", "Plugin loading strategy (auto/all/minimal)"),
        ("MCP_ENABLE_MULTI_REPO", "false", "Enable multi-repository support"),
        ("MCP_REFERENCE_REPOS", "", "Comma-separated authorized repository IDs"),
        ("MCP_MAX_MEMORY_MB", "1024", "Maximum memory for plugins"),
        ("MCP_MIN_FREE_MB", "256", "Minimum free memory to maintain"),
        ("MCP_ANALYSIS_MODE", "false", "Load all plugins for analysis"),
        ("MCP_CACHE_HIGH_PRIORITY_LANGS", "python,javascript,typescript", "Priority languages"),
    ]
    
    for var, default, desc in config_vars:
        value = os.getenv(var, default)
        print(f"  {var:30} = {value:20} # {desc}")
        
    # Show example configurations
    print("\n\nExample configurations:")
    
    print("\n1. Single Repository Development (default):")
    print("   export MCP_PLUGIN_STRATEGY=auto")
    print("   # Loads only plugins for languages in the repository")
    
    print("\n2. Multi-Repository Reference:")
    print("   export MCP_ENABLE_MULTI_REPO=true")
    print("   export MCP_REFERENCE_REPOS=repo1,repo2,repo3")
    print("   export MCP_PLUGIN_STRATEGY=auto")
    print("   # Enables searching across authorized repositories")
    
    print("\n3. Comprehensive Analysis Mode:")
    print("   export MCP_ANALYSIS_MODE=true")
    print("   export MCP_MAX_MEMORY_MB=4096")
    print("   # Loads all 47 plugins for testing")
    

def main():
    """Run all demos."""
    print("Code-Index-MCP: Multi-Repository and Smart Plugin Loading Demo")
    print("="*60)
    
    demos = [
        ("Repository Language Detection", demo_repository_language_detection),
        ("Memory-Aware Plugin Loading", demo_memory_aware_loading),
        ("Multi-Repository Search", demo_multi_repository_search),
        ("Enhanced Dispatcher Configuration", demo_enhanced_dispatcher_config),
    ]
    
    for title, demo_func in demos:
        try:
            demo_func()
        except Exception as e:
            print(f"\nError in {title}: {e}")
            import traceback
            traceback.print_exc()
            
    print("\n" + "="*60)
    print("Demo completed!")
    print("="*60)


if __name__ == "__main__":
    main()