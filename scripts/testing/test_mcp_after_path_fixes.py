#!/usr/bin/env python3
"""
Comprehensive test suite to verify MCP retrieval functionality after path fixes.
Tests all retrieval methods and generates a detailed report.
"""

import os
import sys
import json
import subprocess
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from mcp_server.core.path_utils import PathUtils

class MCPComprehensiveTest:
    """Test all MCP retrieval methods after path fixes."""
    
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "environment": self._get_environment_info(),
            "tests": [],
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "errors": 0
            }
        }
        
    def _get_environment_info(self) -> Dict[str, Any]:
        """Get current environment information."""
        return {
            "workspace_root": str(PathUtils.get_workspace_root()),
            "index_storage_path": str(PathUtils.get_index_storage_path()),
            "repo_registry_path": str(PathUtils.get_repo_registry_path()),
            "python_version": sys.version,
            "platform": sys.platform,
            "env_vars": {
                "MCP_WORKSPACE_ROOT": os.environ.get("MCP_WORKSPACE_ROOT"),
                "MCP_INDEX_STORAGE_PATH": os.environ.get("MCP_INDEX_STORAGE_PATH"),
                "MCP_ENABLE_MULTI_REPO": os.environ.get("MCP_ENABLE_MULTI_REPO"),
                "SEMANTIC_SEARCH_ENABLED": os.environ.get("SEMANTIC_SEARCH_ENABLED")
            }
        }
    
    def _run_mcp_command(self, args: List[str], timeout: int = 30) -> Dict[str, Any]:
        """Run MCP command and capture results."""
        env = os.environ.copy()
        env['MCP_WORKSPACE_ROOT'] = str(PathUtils.get_workspace_root())
        env['MCP_INDEX_STORAGE_PATH'] = str(PathUtils.get_index_storage_path())
        env['MCP_REPO_REGISTRY'] = str(PathUtils.get_repo_registry_path())
        env['MCP_ENABLE_MULTI_REPO'] = 'true'
        env['MCP_ENABLE_MULTI_PATH'] = 'true'
        env['SEMANTIC_SEARCH_ENABLED'] = 'true'
        env['PYTHONPATH'] = str(PathUtils.get_workspace_root())
        
        cmd = [
            sys.executable,
            str(PathUtils.get_workspace_root() / "scripts/cli/mcp_server_cli.py")
        ] + args
        
        start_time = time.time()
        try:
            result = subprocess.run(
                cmd, 
                env=env, 
                capture_output=True, 
                text=True, 
                timeout=timeout
            )
            duration = time.time() - start_time
            
            return {
                "success": result.returncode == 0,
                "duration": duration,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "duration": timeout,
                "error": f"Command timed out after {timeout} seconds",
                "stdout": "",
                "stderr": ""
            }
        except Exception as e:
            return {
                "success": False,
                "duration": time.time() - start_time,
                "error": str(e),
                "stdout": "",
                "stderr": ""
            }
    
    def _add_test_result(self, test_name: str, result: Dict[str, Any]):
        """Add test result and update summary."""
        test_entry = {
            "name": test_name,
            "timestamp": datetime.now().isoformat(),
            **result
        }
        self.results["tests"].append(test_entry)
        self.results["summary"]["total"] += 1
        
        if result.get("success"):
            self.results["summary"]["passed"] += 1
        elif "error" in result:
            self.results["summary"]["errors"] += 1
        else:
            self.results["summary"]["failed"] += 1
    
    def test_status(self):
        """Test MCP status command."""
        print("\n[TEST] MCP Status")
        print("=" * 60)
        
        result = self._run_mcp_command(["status"])
        
        if result["success"]:
            print("✓ Status command succeeded")
            print(f"Output preview: {result['stdout'][:200]}...")
        else:
            print("✗ Status command failed")
            print(f"Error: {result.get('error', result['stderr'])}")
        
        self._add_test_result("status", result)
    
    def test_list_plugins(self):
        """Test plugin listing."""
        print("\n[TEST] List Plugins")
        print("=" * 60)
        
        result = self._run_mcp_command(["list-plugins"])
        
        if result["success"]:
            print("✓ List plugins command succeeded")
            # Count plugins
            plugin_count = result["stdout"].count("Plugin:")
            print(f"Found {plugin_count} plugins")
        else:
            print("✗ List plugins command failed")
            print(f"Error: {result.get('error', result['stderr'])}")
        
        self._add_test_result("list_plugins", result)
    
    def test_symbol_lookup(self):
        """Test symbol lookup functionality."""
        print("\n[TEST] Symbol Lookup")
        print("=" * 60)
        
        test_symbols = ["PathUtils", "EnhancedDispatcher", "SQLiteStore", "PluginManager"]
        
        for symbol in test_symbols:
            print(f"\nLooking up symbol: {symbol}")
            result = self._run_mcp_command(["search", "symbol_lookup", symbol])
            
            if result["success"]:
                # Check if we got results
                if "Found" in result["stdout"] or symbol in result["stdout"]:
                    print(f"✓ Found symbol {symbol}")
                else:
                    print(f"⚠ No results for symbol {symbol}")
                    result["warning"] = "No results found"
            else:
                print(f"✗ Failed to lookup symbol {symbol}")
            
            self._add_test_result(f"symbol_lookup_{symbol}", result)
    
    def test_code_search_sql(self):
        """Test SQL-based code search."""
        print("\n[TEST] SQL Code Search")
        print("=" * 60)
        
        test_queries = [
            "def test",
            "class Plugin",
            "import os",
            "README"
        ]
        
        for query in test_queries:
            print(f"\nSearching for: {query}")
            result = self._run_mcp_command([
                "search", "search_code", query, 
                "--limit", "5"
            ])
            
            if result["success"]:
                # Count results
                result_count = result["stdout"].count("File:")
                print(f"✓ Search succeeded, found {result_count} results")
                if result_count == 0:
                    result["warning"] = "No results found"
            else:
                print(f"✗ Search failed for '{query}'")
            
            self._add_test_result(f"sql_search_{query}", result)
    
    def test_semantic_search(self):
        """Test semantic search functionality."""
        print("\n[TEST] Semantic Search")
        print("=" * 60)
        
        # Check if semantic search is available
        check_result = self._run_mcp_command(["search", "search_code", "--semantic", "true", "test query"])
        
        if "VOYAGE_AI_API_KEY" not in check_result.get("stderr", "") and check_result["success"]:
            test_queries = [
                "implement path resolution for different environments",
                "handle multi-repository indexing",
                "process Python code with tree-sitter"
            ]
            
            for query in test_queries:
                print(f"\nSemantic search for: {query}")
                result = self._run_mcp_command([
                    "search", "search_code", 
                    "--semantic", "true",
                    query,
                    "--limit", "5"
                ])
                
                if result["success"]:
                    result_count = result["stdout"].count("File:")
                    print(f"✓ Semantic search succeeded, found {result_count} results")
                else:
                    print(f"✗ Semantic search failed")
                
                self._add_test_result(f"semantic_search_{query[:30]}", result)
        else:
            print("⚠ Semantic search not available (missing API key)")
            self._add_test_result("semantic_search", {
                "success": False,
                "warning": "Semantic search not configured"
            })
    
    def test_hybrid_search(self):
        """Test hybrid search functionality."""
        print("\n[TEST] Hybrid Search")
        print("=" * 60)
        
        result = self._run_mcp_command([
            "search", "search_code",
            "--hybrid", "true",
            "process repository index",
            "--limit", "5"
        ])
        
        if result["success"]:
            result_count = result["stdout"].count("File:")
            print(f"✓ Hybrid search succeeded, found {result_count} results")
        else:
            print("✗ Hybrid search failed")
            if "VOYAGE_AI_API_KEY" in result.get("stderr", ""):
                result["warning"] = "Hybrid search requires semantic search to be configured"
        
        self._add_test_result("hybrid_search", result)
    
    def test_repository_specific_search(self):
        """Test searching in specific repositories."""
        print("\n[TEST] Repository-Specific Search")
        print("=" * 60)
        
        # First, check available repositories
        registry_path = PathUtils.get_repo_registry_path()
        if registry_path.exists():
            with open(registry_path) as f:
                registry = json.load(f)
                repos = list(registry.get("repositories", {}).keys())[:3]  # Test first 3
                
            for repo_id in repos:
                print(f"\nSearching in repository: {repo_id}")
                result = self._run_mcp_command([
                    "search", "search_code",
                    "--repository", repo_id,
                    "function",
                    "--limit", "3"
                ])
                
                if result["success"]:
                    result_count = result["stdout"].count("File:")
                    print(f"✓ Found {result_count} results in {repo_id}")
                else:
                    print(f"✗ Search failed in {repo_id}")
                
                self._add_test_result(f"repo_search_{repo_id}", result)
        else:
            print("⚠ No repository registry found")
            self._add_test_result("repo_search", {
                "success": False,
                "warning": "Repository registry not found"
            })
    
    def test_direct_database_access(self):
        """Test direct database access to verify indexes."""
        print("\n[TEST] Direct Database Access")
        print("=" * 60)
        
        # Find available index databases
        index_path = PathUtils.get_index_storage_path()
        db_files = list(index_path.glob("*/code_index.db"))
        
        if db_files:
            print(f"Found {len(db_files)} index databases")
            
            # Test first database
            test_db = db_files[0]
            repo_id = test_db.parent.name
            
            test_script = f"""
import sys
sys.path.insert(0, '{PathUtils.get_workspace_root()}')
from mcp_server.storage.sqlite_store import SQLiteStore

try:
    store = SQLiteStore('{test_db}')
    
    # Test BM25 search
    bm25_results = store.search_bm25('function', limit=3)
    print(f"BM25 search: Found {{len(bm25_results)}} results")
    
    # Test FTS search
    fts_results = store.search_fts('class', limit=3)
    print(f"FTS search: Found {{len(fts_results)}} results")
    
    # Check content
    if bm25_results and hasattr(bm25_results[0], 'content'):
        content_preview = bm25_results[0].content[:50]
        if content_preview.startswith('sha256:'):
            print("WARNING: BM25 content contains hashes instead of text!")
        else:
            print("✓ BM25 content looks correct")
    
    print("✓ Direct database access succeeded")
except Exception as e:
    print(f"✗ Direct database access failed: {{e}}")
"""
            
            result = subprocess.run(
                [sys.executable, "-c", test_script],
                capture_output=True,
                text=True
            )
            
            print(result.stdout)
            if result.stderr:
                print(f"Stderr: {result.stderr}")
            
            self._add_test_result("direct_db_access", {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "repo_id": repo_id
            })
        else:
            print("⚠ No index databases found")
            self._add_test_result("direct_db_access", {
                "success": False,
                "warning": "No index databases found"
            })
    
    def test_path_resolution(self):
        """Test PathUtils functionality."""
        print("\n[TEST] Path Resolution")
        print("=" * 60)
        
        test_script = f"""
import sys
sys.path.insert(0, '{PathUtils.get_workspace_root()}')
from mcp_server.core.path_utils import PathUtils

print(f"Workspace root: {{PathUtils.get_workspace_root()}}")
print(f"Index storage: {{PathUtils.get_index_storage_path()}}")
print(f"Repo registry: {{PathUtils.get_repo_registry_path()}}")
print(f"Temp path: {{PathUtils.get_temp_path()}}")

# Test Docker path translation
docker_path = "/app/test.py"
native_path = PathUtils.translate_docker_path(docker_path)
print(f"Docker {{docker_path}} -> Native {{native_path}}")

# Test environment detection
print(f"Is Docker: {{PathUtils.is_docker_environment()}}")
print("✓ Path resolution working correctly")
"""
        
        result = subprocess.run(
            [sys.executable, "-c", test_script],
            capture_output=True,
            text=True
        )
        
        print(result.stdout)
        
        self._add_test_result("path_resolution", {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr
        })
    
    def generate_report(self):
        """Generate comprehensive test report."""
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        summary = self.results["summary"]
        print(f"Total tests: {summary['total']}")
        print(f"Passed: {summary['passed']} ({summary['passed']/summary['total']*100:.1f}%)")
        print(f"Failed: {summary['failed']}")
        print(f"Errors: {summary['errors']}")
        
        # Identify key issues
        print("\n[KEY FINDINGS]")
        
        issues = []
        warnings = []
        
        for test in self.results["tests"]:
            if not test.get("success"):
                if "error" in test:
                    issues.append(f"- {test['name']}: {test['error']}")
                elif "stderr" in test and test["stderr"]:
                    issues.append(f"- {test['name']}: {test['stderr'][:100]}")
            
            if "warning" in test:
                warnings.append(f"- {test['name']}: {test['warning']}")
        
        if issues:
            print("\nIssues found:")
            for issue in issues[:5]:  # Show first 5
                print(issue)
        
        if warnings:
            print("\nWarnings:")
            for warning in warnings:
                print(warning)
        
        # Check for BM25 content issue
        for test in self.results["tests"]:
            if "BM25 content contains hashes" in test.get("stdout", ""):
                print("\n⚠️  CRITICAL: BM25 indexes contain content hashes instead of actual text!")
                print("   This is why searches return 0 results.")
                print("   Action needed: Re-index all repositories with proper content extraction.")
        
        # Save detailed report
        report_path = PathUtils.get_workspace_root() / "mcp_path_fix_test_results.json"
        with open(report_path, "w") as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\nDetailed report saved to: {report_path}")
        
        # Return overall status
        return summary["passed"] == summary["total"]


def main():
    """Run comprehensive MCP tests."""
    print("MCP Comprehensive Test Suite - Post Path Fix Verification")
    print("=" * 60)
    print(f"Timestamp: {datetime.now()}")
    
    tester = MCPComprehensiveTest()
    
    # Run all tests
    tester.test_status()
    tester.test_list_plugins()
    tester.test_symbol_lookup()
    tester.test_code_search_sql()
    tester.test_semantic_search()
    tester.test_hybrid_search()
    tester.test_repository_specific_search()
    tester.test_direct_database_access()
    tester.test_path_resolution()
    
    # Generate report
    success = tester.generate_report()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()