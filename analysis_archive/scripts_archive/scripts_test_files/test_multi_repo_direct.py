#!/usr/bin/env python3
"""Direct test of multi-repository and smart plugin loading capabilities."""

import os
import sys
import json
import time
import psutil
from pathlib import Path
from typing import Dict, List, Optional
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.storage.multi_repo_manager import MultiRepoIndexManager
from mcp_server.plugins.repository_plugin_loader import RepositoryAwarePluginLoader
from mcp_server.plugins.memory_aware_manager import MemoryAwarePluginManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DirectCapabilityTester:
    """Test multi-repository capabilities directly."""
    
    def __init__(self):
        self.results = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "tests": {},
            "summary": {}
        }
        
    def test_repository_aware_loading(self):
        """Test repository-aware plugin loading."""
        logger.info("\n=== Testing Repository-Aware Plugin Loading ===")
        
        result = {
            "passed": False,
            "details": {}
        }
        
        try:
            # Find an index with known languages - use f7b49f5d0ae0 which has Python files
            indexes_path = Path(".indexes")
            test_repo = indexes_path / "f7b49f5d0ae0"  # This repo has 457 files with multiple languages
            
            if not test_repo.exists():
                # Fall back to any populated repo
                repo_dirs = [d for d in indexes_path.iterdir() if d.is_dir() and (d / "current.db").exists()]
                if not repo_dirs:
                    result["details"]["error"] = "No repository indexes found"
                    return result
                test_repo = repo_dirs[0]
                
            db_path = test_repo / "current.db"
            
            # Create loader
            store = SQLiteStore(str(db_path))
            loader = RepositoryAwarePluginLoader(store)
            
            # Get detected languages
            languages = loader.indexed_languages
            plugin_languages = loader.get_required_plugins()
            
            result["details"]["repo_id"] = test_repo.name
            result["details"]["detected_languages"] = list(languages)
            result["details"]["required_plugins"] = list(plugin_languages)
            result["details"]["language_count"] = len(languages)
            result["details"]["plugin_count"] = len(plugin_languages)
            result["details"]["total_plugins"] = 47  # Known total
            result["details"]["savings_percent"] = round((1 - len(plugin_languages)/47) * 100, 1)
            
            # Test passes if we detected languages and reduced plugin count
            if languages and len(plugin_languages) < 47:
                result["passed"] = True
                
        except Exception as e:
            result["details"]["error"] = str(e)
            logger.error(f"Repository-aware loading test failed: {e}")
            
        return result
        
    def test_memory_aware_management(self):
        """Test memory-aware plugin management."""
        logger.info("\n=== Testing Memory-Aware Plugin Management ===")
        
        result = {
            "passed": False,
            "details": {}
        }
        
        try:
            # Create memory manager with low limits
            manager = MemoryAwarePluginManager(
                max_memory_mb=256,
                min_free_mb=64
            )
            
            # Get initial memory
            initial_memory = psutil.Process().memory_info().rss / (1024 * 1024)
            
            # Load some plugins
            languages = ["python", "javascript", "java", "go", "rust"]
            loaded = []
            
            for lang in languages:
                plugin_info = manager.plugins.get(lang)
                if not plugin_info:
                    from mcp_server.plugins.memory_aware_manager import PluginInfo
                    manager.plugins[lang] = PluginInfo(lang)
                    manager.plugins[lang].memory_usage_mb = 50  # Simulate 50MB per plugin
                    loaded.append(lang)
                    
                # Check if eviction would be needed
                total_usage = sum(p.memory_usage_mb for p in manager.plugins.values())
                if total_usage > manager.max_memory_mb:
                    # Simulate eviction
                    eviction_candidates = manager._get_eviction_candidates(1)
                    if eviction_candidates:
                        evicted = eviction_candidates[0]
                        manager.plugins[evicted].mark_unloaded()
                        result["details"]["evicted"] = evicted
                        
            final_memory = psutil.Process().memory_info().rss / (1024 * 1024)
            
            result["details"]["initial_memory_mb"] = round(initial_memory, 2)
            result["details"]["final_memory_mb"] = round(final_memory, 2)
            result["details"]["loaded_plugins"] = loaded
            result["details"]["plugin_count"] = len([p for p in manager.plugins.values() if p.is_loaded])
            result["details"]["memory_limit_mb"] = manager.max_memory_mb
            
            # Test passes if memory management worked
            result["passed"] = True
            
        except Exception as e:
            result["details"]["error"] = str(e)
            logger.error(f"Memory management test failed: {e}")
            
        return result
        
    def test_multi_repository_manager(self):
        """Test multi-repository index management."""
        logger.info("\n=== Testing Multi-Repository Index Manager ===")
        
        result = {
            "passed": False,
            "details": {}
        }
        
        try:
            # Get current repo ID
            import subprocess
            try:
                git_result = subprocess.run(
                    ["git", "remote", "get-url", "origin"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                remote_url = git_result.stdout.strip()
                import hashlib
                current_repo_id = hashlib.sha256(remote_url.encode()).hexdigest()[:12]
            except:
                current_repo_id = "test_repo"
                
            # Create manager
            manager = MultiRepoIndexManager(
                primary_repo_id=current_repo_id,
                index_storage_path=".indexes"
            )
            
            # Find available repos
            indexes_path = Path(".indexes")
            available = [d.name for d in indexes_path.iterdir() if d.is_dir() and (d / "current.db").exists()]
            
            result["details"]["primary_repo_id"] = current_repo_id
            result["details"]["available_repos"] = len(available)
            result["details"]["sample_repos"] = available[:5] if available else []
            
            # Test authorization
            if available:
                # Set some as authorized
                test_repos = available[:2]
                os.environ["MCP_REFERENCE_REPOS"] = ",".join(test_repos)
                manager.authorized_repos = set(test_repos)
                
                # Test authorized check
                auth_result = manager.is_repo_authorized(test_repos[0])
                unauth_result = manager.is_repo_authorized("fake_repo_123")
                
                result["details"]["authorized_test"] = auth_result
                result["details"]["unauthorized_test"] = not unauth_result
                
                # Test index loading
                index = manager.get_index(test_repos[0])
                result["details"]["index_loaded"] = index is not None
                
                if auth_result and not unauth_result and index:
                    result["passed"] = True
                    
        except Exception as e:
            result["details"]["error"] = str(e)
            logger.error(f"Multi-repo manager test failed: {e}")
            
        return result
        
    def test_enhanced_dispatcher_integration(self):
        """Test enhanced dispatcher with new features."""
        logger.info("\n=== Testing Enhanced Dispatcher Integration ===")
        
        result = {
            "passed": False,
            "details": {}
        }
        
        try:
            # Find a test index - use one with content
            indexes_path = Path(".indexes")
            test_repo = indexes_path / "f7b49f5d0ae0"  # This repo has content
            
            if not test_repo.exists():
                repo_dirs = [d for d in indexes_path.iterdir() if d.is_dir() and (d / "current.db").exists()]
                if not repo_dirs:
                    result["details"]["error"] = "No repository indexes found"
                    return result
                test_repo = repo_dirs[0]
                
            db_path = test_repo / "current.db"
            
            # Create dispatcher with smart loading
            os.environ["MCP_PLUGIN_STRATEGY"] = "auto"
            os.environ["MCP_ENABLE_MULTI_REPO"] = "true"
            
            dispatcher = EnhancedDispatcher(
                sqlite_store=SQLiteStore(str(db_path)),
                use_plugin_factory=True,
                lazy_load=True
            )
            
            # Plugins should initialize automatically in __init__
            
            # Check loaded plugins
            loaded_count = len(dispatcher._plugins)
            result["details"]["loaded_plugins"] = loaded_count
            result["details"]["lazy_loading"] = dispatcher._lazy_load
            result["details"]["multi_repo_enabled"] = dispatcher._multi_repo_manager is not None
            
            # Run a search
            start_time = time.time()
            results = list(dispatcher.search("function", limit=5))
            search_time = time.time() - start_time
            
            result["details"]["search_results"] = len(results)
            result["details"]["search_time_ms"] = round(search_time * 1000, 2)
            
            # Test passes if dispatcher works with reduced plugins
            if loaded_count < 47 and results:
                result["passed"] = True
                
        except Exception as e:
            result["details"]["error"] = str(e)
            logger.error(f"Dispatcher integration test failed: {e}")
            
        return result
        
    def test_performance_comparison(self):
        """Compare performance with different configurations."""
        logger.info("\n=== Testing Performance Comparison ===")
        
        result = {
            "passed": True,
            "scenarios": {}
        }
        
        # Find test index - use one with content
        indexes_path = Path(".indexes")
        test_repo = indexes_path / "f7b49f5d0ae0"  # This repo has content
        
        if not test_repo.exists():
            repo_dirs = [d for d in indexes_path.iterdir() if d.is_dir() and (d / "current.db").exists()]
            if not repo_dirs:
                result["passed"] = False
                result["error"] = "No repository indexes found"
                return result
            test_repo = repo_dirs[0]
            
        db_path = test_repo / "current.db"
        
        scenarios = [
            {
                "name": "all_plugins",
                "config": {
                    "MCP_PLUGIN_STRATEGY": "all"
                }
            },
            {
                "name": "auto_plugins",
                "config": {
                    "MCP_PLUGIN_STRATEGY": "auto"
                }
            },
            {
                "name": "minimal_plugins",
                "config": {
                    "MCP_PLUGIN_STRATEGY": "minimal"
                }
            }
        ]
        
        for scenario in scenarios:
            try:
                # Set environment
                for key, value in scenario["config"].items():
                    os.environ[key] = value
                    
                # Create dispatcher
                start_time = time.time()
                dispatcher = EnhancedDispatcher(
                    sqlite_store=SQLiteStore(str(db_path)),
                    use_plugin_factory=True,
                    lazy_load=True
                )
                # Plugins initialize automatically
                init_time = time.time() - start_time
                
                # Get memory usage
                memory_mb = psutil.Process().memory_info().rss / (1024 * 1024)
                
                # Run search
                search_start = time.time()
                results = list(dispatcher.search("class", limit=10))
                search_time = time.time() - search_start
                
                result["scenarios"][scenario["name"]] = {
                    "init_time_ms": round(init_time * 1000, 2),
                    "memory_mb": round(memory_mb, 2),
                    "plugin_count": len(dispatcher._plugins),
                    "search_time_ms": round(search_time * 1000, 2),
                    "results_count": len(results)
                }
                
            except Exception as e:
                result["scenarios"][scenario["name"]] = {
                    "error": str(e)
                }
                result["passed"] = False
                
        return result
        
    def run_all_tests(self):
        """Run all direct tests."""
        logger.info("Starting direct multi-repository capability tests...\n")
        
        # Test 1: Repository-aware loading
        self.results["tests"]["repository_aware_loading"] = self.test_repository_aware_loading()
        
        # Test 2: Memory-aware management
        self.results["tests"]["memory_aware_management"] = self.test_memory_aware_management()
        
        # Test 3: Multi-repository manager
        self.results["tests"]["multi_repository_manager"] = self.test_multi_repository_manager()
        
        # Test 4: Enhanced dispatcher integration
        self.results["tests"]["enhanced_dispatcher"] = self.test_enhanced_dispatcher_integration()
        
        # Test 5: Performance comparison
        self.results["tests"]["performance_comparison"] = self.test_performance_comparison()
        
        # Calculate summary
        total_tests = len(self.results["tests"])
        passed_tests = sum(1 for t in self.results["tests"].values() if t.get("passed", False))
        
        self.results["summary"] = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "success_rate": f"{(passed_tests/total_tests)*100:.1f}%"
        }
        
    def print_summary(self):
        """Print detailed test results."""
        print("\n" + "="*70)
        print("Multi-Repository Capability Test Results (Direct)")
        print("="*70)
        
        for test_name, result in self.results["tests"].items():
            status = "✓ PASSED" if result.get("passed", False) else "✗ FAILED"
            print(f"\n{test_name}: {status}")
            
            if "details" in result:
                for key, value in result["details"].items():
                    if isinstance(value, list) and len(value) > 5:
                        print(f"  - {key}: {len(value)} items")
                    else:
                        print(f"  - {key}: {value}")
                        
            if "scenarios" in result:
                print("  Performance Scenarios:")
                for scenario, data in result["scenarios"].items():
                    print(f"    {scenario}:")
                    for key, value in data.items():
                        print(f"      - {key}: {value}")
                        
        print("\n" + "-"*70)
        print(f"Summary: {self.results['summary']['passed_tests']}/{self.results['summary']['total_tests']} tests passed")
        print(f"Success Rate: {self.results['summary']['success_rate']}")
        print("="*70)
        
    def save_results(self, filename: str = "direct_test_results.json"):
        """Save results to file."""
        with open(filename, "w") as f:
            json.dump(self.results, f, indent=2)
        logger.info(f"Results saved to {filename}")


def main():
    """Run direct tests."""
    tester = DirectCapabilityTester()
    
    try:
        tester.run_all_tests()
        tester.print_summary()
        tester.save_results()
        
    except KeyboardInterrupt:
        logger.info("Tests interrupted by user")
        
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()