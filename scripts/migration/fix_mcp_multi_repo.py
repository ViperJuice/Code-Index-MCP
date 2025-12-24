#!/usr/bin/env python3
"""
Fix MCP multi-repository search by updating configuration and testing.
"""

import os
import sys
import json
import logging
from pathlib import Path
from mcp_server.core.path_utils import PathUtils

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server.storage.multi_repo_manager import MultiRepositoryManager
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fix_mcp_config():
    """Update .mcp.json to include repository registry path."""
    config_path = Path("PathUtils.get_workspace_root()/.mcp.json")
    
    # Read current config
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    # Update environment variables
    env = config["mcpServers"]["code-index-mcp"]["env"]
    env["MCP_REPO_REGISTRY"] = "PathUtils.get_workspace_root()/PathUtils.get_repo_registry_path()"
    
    # Write updated config
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    logger.info("Updated .mcp.json with MCP_REPO_REGISTRY path")
    return config


def test_multi_repo_manager():
    """Test MultiRepositoryManager with correct registry path."""
    registry_path = Path("PathUtils.get_workspace_root()/PathUtils.get_repo_registry_path()")
    
    # Initialize manager
    manager = MultiRepositoryManager(central_index_path=registry_path)
    
    # List registered repositories
    repos = manager.registry.list_all()
    logger.info(f"Found {len(repos)} registered repositories")
    
    # Show a few repos
    for info in repos[:5]:
        logger.info(f"  - {info.name}: {info.path}")
    
    return manager


def test_dispatcher_with_multi_repo():
    """Test EnhancedDispatcher with multi-repo support."""
    # Set environment variables
    os.environ["MCP_ENABLE_MULTI_REPO"] = "true"
    os.environ["MCP_REPO_REGISTRY"] = "PathUtils.get_workspace_root()/PathUtils.get_repo_registry_path()"
    os.environ["MCP_INDEX_STORAGE_PATH"] = "PathUtils.get_workspace_root()/.indexes"
    
    # Create a dummy SQLite store for current repo
    current_index = Path("PathUtils.get_workspace_root()/.mcp-index/code_index.db")
    if current_index.exists():
        sqlite_store = SQLiteStore(str(current_index))
    else:
        # Create minimal store
        sqlite_store = SQLiteStore(":memory:")
    
    # Initialize dispatcher
    dispatcher = EnhancedDispatcher(
        sqlite_store=sqlite_store,
        multi_repo_enabled=True,
        semantic_search_enabled=True
    )
    
    logger.info(f"Dispatcher initialized with multi-repo support: {dispatcher._multi_repo_manager is not None}")
    
    if dispatcher._multi_repo_manager:
        # Test searching in a specific repository
        results = dispatcher.search("Model", repository="django", limit=5)
        logger.info(f"Search results from Django: {len(results)} items")
        
        for i, result in enumerate(results[:3]):
            logger.info(f"  {i+1}. {result.file}:{result.line} - {result.snippet[:50]}...")
    
    return dispatcher


def test_direct_index_search():
    """Test searching directly in a specific index."""
    # Find Django index
    django_index = Path("PathUtils.get_workspace_root()/.indexes/d8df70cdcd6e/code_index.db")
    
    if not django_index.exists():
        logger.error(f"Django index not found at {django_index}")
        return
    
    # Open index directly
    store = SQLiteStore(str(django_index))
    
    # Search for "Model"
    results = store.search_bm25("Model", limit=5)
    logger.info(f"Direct search in Django index: {len(results)} results")
    
    for i, result in enumerate(results[:3]):
        logger.info(f"  {i+1}. {result.file}:{result.line} - {result.content[:50]}...")


def main():
    """Run multi-repo fixes and tests."""
    logger.info("Fixing MCP multi-repository search")
    logger.info("="*60)
    
    # Step 1: Update MCP configuration
    logger.info("\n1. Updating MCP configuration...")
    fix_mcp_config()
    
    # Step 2: Test MultiRepositoryManager
    logger.info("\n2. Testing MultiRepositoryManager...")
    manager = test_multi_repo_manager()
    
    # Step 3: Test direct index search
    logger.info("\n3. Testing direct index search...")
    test_direct_index_search()
    
    # Step 4: Test dispatcher with multi-repo
    logger.info("\n4. Testing EnhancedDispatcher with multi-repo...")
    dispatcher = test_dispatcher_with_multi_repo()
    
    logger.info("\n" + "="*60)
    logger.info("Multi-repo fix complete!")
    logger.info("\nTo apply changes:")
    logger.info("1. Restart the MCP server in Claude Code")
    logger.info("2. Try searching with repository parameter:")
    logger.info('   search_code(query="Model", repository="django")')


if __name__ == "__main__":
    main()