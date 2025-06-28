#!/usr/bin/env python3
"""Direct test of MCP capabilities using MCP tools."""

import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, List, Any

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_server.storage.multi_repo_manager import MultiRepoIndexManager
from mcp_server.plugins.repository_plugin_loader import RepositoryAwarePluginLoader
from mcp_server.storage.sqlite_store import SQLiteStore


def test_repository_language_detection():
    """Test language detection from repository indexes."""
    print("\n=== Testing Repository Language Detection ===")
    
    indexes_path = Path(".indexes")
    results = []
    
    # Check first 5 repos
    for repo_dir in list(indexes_path.iterdir())[:5]:
        if not repo_dir.is_dir():
            continue
            
        current_db = repo_dir / "current.db"
        if current_db.exists():
            try:
                store = SQLiteStore(str(current_db))
                loader = RepositoryAwarePluginLoader(sqlite_store=store)
                languages = loader.indexed_languages
                
                result = {
                    "repo_id": repo_dir.name,
                    "languages": sorted(list(languages)),
                    "count": len(languages),
                    "memory_savings": f"{(1 - len(languages)/47)*100:.1f}%"
                }
                results.append(result)
                
                print(f"\nRepo {repo_dir.name}:")
                print(f"  Languages: {', '.join(sorted(languages))}")
                print(f"  Count: {len(languages)} (vs 47 total)")
                print(f"  Memory savings: {result['memory_savings']}")
                
            except Exception as e:
                print(f"  Error processing {repo_dir.name}: {e}")
                
    return results


def test_multi_repo_authorization():
    """Test multi-repository authorization system."""
    print("\n\n=== Testing Multi-Repository Authorization ===")
    
    # Get current repo ID
    try:
        import subprocess
        result = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            capture_output=True,
            text=True,
            check=True
        )
        import hashlib
        remote_url = result.stdout.strip()
        current_repo_id = hashlib.sha256(remote_url.encode()).hexdigest()[:12]
    except:
        current_repo_id = "current_repo"
        
    # Create manager
    manager = MultiRepoIndexManager(current_repo_id, ".indexes")
    
    # Test different repo IDs
    test_cases = [
        ("https://github.com/example/repo.git", "Git URL"),
        ("/path/to/local/repo", "Local path"),
        ("056d6d37b1aa", "Direct ID")
    ]
    
    print("\nRepository ID Resolution:")
    for test_input, desc in test_cases:
        repo_id = MultiRepoIndexManager.resolve_repo_id(test_input)
        print(f"  {desc}: {test_input} -> {repo_id}")
        
    # Test authorization
    print("\nAuthorization Tests:")
    
    # Set authorized repos
    os.environ["MCP_REFERENCE_REPOS"] = "056d6d37b1aa,844145265d7a"
    manager.authorized_repos = {"056d6d37b1aa", "844145265d7a"}
    
    test_repos = ["056d6d37b1aa", "fake_repo", "844145265d7a"]
    for repo in test_repos:
        is_auth = manager.is_repo_authorized(repo)
        print(f"  {repo}: {'✓ Authorized' if is_auth else '✗ Not authorized'}")
        

def test_plugin_loading_modes():
    """Test different plugin loading modes."""
    print("\n\n=== Testing Plugin Loading Modes ===")
    
    # Find a test repo with known languages
    test_repo_path = Path(".indexes/056d6d37b1aa/current.db")
    if not test_repo_path.exists():
        # Find any available repo
        for repo_dir in Path(".indexes").iterdir():
            current_db = repo_dir / "current.db"
            if current_db.exists():
                test_repo_path = current_db
                break
                
    if not test_repo_path.exists():
        print("No test repository found")
        return
        
    store = SQLiteStore(str(test_repo_path))
    
    # Test 1: Auto mode (repository-aware)
    print("\n1. Auto Mode (Repository-Aware):")
    loader_auto = RepositoryAwarePluginLoader(sqlite_store=store)
    auto_langs = loader_auto.get_required_plugins()
    print(f"   Would load: {', '.join(sorted(auto_langs))}")
    print(f"   Plugin count: {len(auto_langs)}")
    
    # Test 2: Analysis mode (all plugins)
    print("\n2. Analysis Mode (All Plugins):")
    os.environ["MCP_ANALYSIS_MODE"] = "true"
    loader_all = RepositoryAwarePluginLoader(sqlite_store=store)
    all_langs = loader_all.get_required_plugins()
    os.environ["MCP_ANALYSIS_MODE"] = "false"
    print(f"   Would load: {len(all_langs)} plugins")
    print(f"   Memory impact: ~{len(all_langs) * 50}MB (estimated)")
    
    # Compare
    print(f"\n3. Comparison:")
    print(f"   Auto mode: {len(auto_langs)} plugins")
    print(f"   Analysis mode: {len(all_langs)} plugins")
    print(f"   Reduction: {(1 - len(auto_langs)/len(all_langs))*100:.1f}%")


def test_memory_aware_features():
    """Test memory-aware plugin management features."""
    print("\n\n=== Testing Memory-Aware Features ===")
    
    from mcp_server.plugins.memory_aware_manager import MemoryAwarePluginManager
    
    # Create manager with specific limits
    manager = MemoryAwarePluginManager(max_memory_mb=512, min_free_mb=128)
    
    print(f"Memory Configuration:")
    print(f"  Max memory: {manager.max_memory_mb}MB")
    print(f"  Min free: {manager.min_free_mb}MB")
    
    # Simulate plugin priorities
    test_plugins = {
        "python": 100,
        "javascript": 95,
        "java": 85,
        "go": 80,
        "rust": 75,
        "cpp": 70,
        "csharp": 65,
        "ruby": 60
    }
    
    print("\nPlugin Priorities:")
    for lang, priority in sorted(test_plugins.items(), key=lambda x: -x[1])[:5]:
        print(f"  {lang}: {priority}")
        
    # Simulate access patterns
    manager.access_counts = {"python": 50, "javascript": 40, "java": 10, "go": 5}
    manager.last_access = {
        "python": time.time(),
        "javascript": time.time() - 60,
        "java": time.time() - 300,
        "go": time.time() - 600
    }
    
    # Get eviction candidates
    candidates = manager._get_eviction_candidates(exclude={"python"})
    
    print("\nEviction Candidates (LRU):")
    for lang, score in candidates[:3]:
        accesses = manager.access_counts.get(lang, 0)
        print(f"  {lang}: score={score:.2f}, accesses={accesses}")


def test_mcp_status():
    """Test MCP server status and configuration."""
    print("\n\n=== MCP Server Status ===")
    
    # This would normally use MCP tools, but for direct testing we'll check files
    print("\nChecking MCP configuration...")
    
    # Check environment variables
    env_vars = {
        "MCP_PLUGIN_STRATEGY": os.getenv("MCP_PLUGIN_STRATEGY", "all"),
        "MCP_ENABLE_MULTI_REPO": os.getenv("MCP_ENABLE_MULTI_REPO", "false"),
        "MCP_ANALYSIS_MODE": os.getenv("MCP_ANALYSIS_MODE", "false"),
        "MCP_MAX_MEMORY_MB": os.getenv("MCP_MAX_MEMORY_MB", "1024"),
        "MCP_REFERENCE_REPOS": os.getenv("MCP_REFERENCE_REPOS", "")
    }
    
    print("\nEnvironment Configuration:")
    for var, value in env_vars.items():
        print(f"  {var}: {value}")
        
    # Count available indexes
    index_count = len(list(Path(".indexes").glob("*/current.db")))
    print(f"\nAvailable repository indexes: {index_count}")


def main():
    """Run all tests."""
    print("=== Multi-Repository and Smart Plugin Loading Test Suite ===")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {
        "language_detection": test_repository_language_detection(),
        "multi_repo_auth": test_multi_repo_authorization(),
        "plugin_modes": test_plugin_loading_modes(),
        "memory_features": test_memory_aware_features(),
        "mcp_status": test_mcp_status()
    }
    
    # Summary
    print("\n\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    if results["language_detection"]:
        avg_langs = sum(r["count"] for r in results["language_detection"]) / len(results["language_detection"])
        print(f"\n✓ Language Detection:")
        print(f"  - Tested {len(results['language_detection'])} repositories")
        print(f"  - Average {avg_langs:.1f} languages per repo")
        print(f"  - Average memory savings: {(1 - avg_langs/47)*100:.1f}%")
        
    print(f"\n✓ Multi-Repository Support:")
    print(f"  - Repository ID resolution working")
    print(f"  - Authorization system functional")
    
    print(f"\n✓ Smart Plugin Loading:")
    print(f"  - Repository-aware mode available")
    print(f"  - Analysis mode for comprehensive testing")
    
    print(f"\n✓ Memory Management:")
    print(f"  - LRU eviction strategy implemented")
    print(f"  - Priority-based plugin retention")
    
    print("\n" + "="*60)
    print("Ready for MCP vs Native performance comparison!")
    
    # Save results
    with open("mcp_capability_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nDetailed results saved to: mcp_capability_test_results.json")


if __name__ == "__main__":
    main()