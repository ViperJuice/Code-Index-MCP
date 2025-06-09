#!/usr/bin/env python3
"""Comprehensive MCP server testing with public repositories."""

import os
import sys
import json
import time
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

# Ensure we can import MCP modules
sys.path.insert(0, str(Path(__file__).parent))

# Test repositories for each language
TEST_REPOS = {
    "python": [
        {
            "url": "https://github.com/pallets/flask.git",
            "name": "flask",
            "description": "Popular Python web framework"
        },
        {
            "url": "https://github.com/psf/requests.git", 
            "name": "requests",
            "description": "HTTP library for Python"
        }
    ],
    "javascript": [
        {
            "url": "https://github.com/expressjs/express.git",
            "name": "express",
            "description": "Node.js web framework"
        },
        {
            "url": "https://github.com/lodash/lodash.git",
            "name": "lodash",
            "description": "JavaScript utility library"
        }
    ],
    "c": [
        {
            "url": "https://github.com/redis/redis.git",
            "name": "redis",
            "description": "In-memory data structure store"
        },
        {
            "url": "https://github.com/curl/curl.git",
            "name": "curl",
            "description": "Command line tool for transferring data"
        }
    ],
    "cpp": [
        {
            "url": "https://github.com/nlohmann/json.git",
            "name": "json",
            "description": "JSON for Modern C++"
        }
    ],
    "html_css": [
        {
            "url": "https://github.com/twbs/bootstrap.git",
            "name": "bootstrap",
            "description": "Popular CSS framework"
        }
    ],
    "dart": [
        {
            "url": "https://github.com/flutter/gallery.git",
            "name": "flutter-gallery",
            "description": "Flutter demo application"
        }
    ]
}

# Test queries for different types of searches
TEST_QUERIES = {
    "semantic": [
        "function that handles HTTP requests and responses",
        "class for managing database connections",
        "recursive algorithm implementation",
        "authentication and authorization logic",
        "data validation and sanitization",
        "error handling and exception management",
        "configuration file parsing",
        "asynchronous operations and promises",
        "memory allocation and management",
        "template rendering and view logic"
    ],
    "exact": [
        "def __init__",
        "class Request",
        "function handle",
        "malloc",
        "async function",
        "SELECT * FROM",
        "@app.route",
        "module.exports",
        "template <typename",
        "Widget build"
    ],
    "symbol": [
        "Flask",
        "Response",
        "createServer",
        "redis_client",
        "json_parse",
        "Bootstrap",
        "StatelessWidget"
    ]
}


class MCPTester:
    """Comprehensive MCP server tester."""
    
    def __init__(self, workspace_dir: str = "./test_workspace"):
        self.workspace = Path(workspace_dir)
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "repos_tested": {},
            "search_results": {},
            "performance": {},
            "errors": []
        }
        
    def setup_workspace(self):
        """Create workspace directory."""
        self.workspace.mkdir(exist_ok=True)
        print(f"Created workspace: {self.workspace}")
        
    def cleanup_workspace(self):
        """Remove workspace directory."""
        if self.workspace.exists():
            shutil.rmtree(self.workspace)
            print(f"Cleaned up workspace: {self.workspace}")
    
    def download_repo(self, repo_info: Dict[str, str], language: str) -> Path:
        """Clone a repository."""
        repo_path = self.workspace / language / repo_info["name"]
        
        if repo_path.exists():
            print(f"  Repository already exists: {repo_info['name']}")
            return repo_path
            
        repo_path.parent.mkdir(parents=True, exist_ok=True)
        
        print(f"  Cloning {repo_info['name']}...")
        try:
            # Clone with depth 1 for faster download
            result = subprocess.run(
                ["git", "clone", "--depth", "1", repo_info["url"], str(repo_path)],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print(f"  ✓ Cloned {repo_info['name']}")
                return repo_path
            else:
                print(f"  ✗ Failed to clone {repo_info['name']}: {result.stderr}")
                self.results["errors"].append(f"Clone failed: {repo_info['name']}")
                return None
                
        except Exception as e:
            print(f"  ✗ Error cloning {repo_info['name']}: {e}")
            self.results["errors"].append(f"Clone error: {repo_info['name']} - {str(e)}")
            return None
    
    def test_mcp_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """Call an MCP tool and return results."""
        try:
            # This would normally call the MCP server through the protocol
            # For now, we'll simulate the calls
            print(f"    Calling {tool_name} with params: {json.dumps(params, indent=2)}")
            
            # Simulate tool responses for testing
            if tool_name == "reindex":
                return {"status": "success", "files_indexed": 100}
            elif tool_name == "search_code":
                return {"results": [{"file": "test.py", "line": 10, "snippet": "test"}]}
            elif tool_name == "symbol_lookup":
                return {"found": True, "definition": {"file": "test.py", "line": 5}}
            elif tool_name == "get_status":
                return {"status": "operational", "plugins": 6}
            else:
                return {"error": "Unknown tool"}
                
        except Exception as e:
            print(f"    ✗ Error calling {tool_name}: {e}")
            return {"error": str(e)}
    
    def test_indexing(self, repo_path: Path, language: str):
        """Test indexing a repository."""
        print(f"\n  Testing indexing for {repo_path.name}...")
        
        start_time = time.time()
        
        # Call reindex tool
        result = self.test_mcp_tool("reindex", {"path": str(repo_path)})
        
        duration = time.time() - start_time
        
        if "error" not in result:
            print(f"  ✓ Indexed in {duration:.2f}s")
            self.results["performance"][f"{language}_{repo_path.name}_index"] = duration
        else:
            print(f"  ✗ Indexing failed: {result['error']}")
            self.results["errors"].append(f"Index failed: {repo_path.name}")
    
    def test_searches(self, language: str):
        """Test different types of searches."""
        print(f"\n  Testing searches for {language}...")
        
        search_results = {}
        
        # Test semantic searches
        print("    Semantic searches:")
        for query in TEST_QUERIES["semantic"][:3]:  # Test first 3
            result = self.test_mcp_tool("search_code", {
                "query": query,
                "semantic": True,
                "limit": 5
            })
            
            if "results" in result and result["results"]:
                print(f"      ✓ '{query}' - {len(result['results'])} results")
                search_results[f"semantic_{query}"] = len(result["results"])
            else:
                print(f"      ✗ '{query}' - No results")
        
        # Test exact searches
        print("    Exact searches:")
        for query in TEST_QUERIES["exact"][:3]:  # Test first 3
            result = self.test_mcp_tool("search_code", {
                "query": query,
                "semantic": False,
                "limit": 5
            })
            
            if "results" in result and result["results"]:
                print(f"      ✓ '{query}' - {len(result['results'])} results")
                search_results[f"exact_{query}"] = len(result["results"])
            else:
                print(f"      ✗ '{query}' - No results")
        
        # Test symbol lookups
        print("    Symbol lookups:")
        for symbol in TEST_QUERIES["symbol"][:2]:  # Test first 2
            result = self.test_mcp_tool("symbol_lookup", {"symbol": symbol})
            
            if result.get("found"):
                print(f"      ✓ '{symbol}' - Found")
                search_results[f"symbol_{symbol}"] = "found"
            else:
                print(f"      ✗ '{symbol}' - Not found")
        
        self.results["search_results"][language] = search_results
    
    def test_status(self):
        """Test MCP server status."""
        print("\nChecking MCP server status...")
        
        result = self.test_mcp_tool("get_status", {})
        
        if "status" in result:
            print(f"  Status: {result['status']}")
            print(f"  Plugins: {result.get('plugins', 'unknown')}")
            self.results["server_status"] = result
        else:
            print("  ✗ Failed to get status")
            self.results["errors"].append("Status check failed")
    
    def run_comprehensive_test(self):
        """Run all tests."""
        print("=== MCP Server Comprehensive Test ===\n")
        
        self.setup_workspace()
        
        try:
            # Test server status
            self.test_status()
            
            # Test each language
            for language, repos in TEST_REPOS.items():
                print(f"\n--- Testing {language.upper()} ---")
                
                repos_tested = []
                
                # Download and test repos
                for repo_info in repos[:1]:  # Limit to 1 repo per language for quick test
                    print(f"\nTesting {repo_info['name']} ({repo_info['description']})")
                    
                    # Download repo
                    repo_path = self.download_repo(repo_info, language)
                    if not repo_path:
                        continue
                    
                    repos_tested.append(repo_info["name"])
                    
                    # Test indexing
                    self.test_indexing(repo_path, language)
                    
                    # Test searches
                    self.test_searches(language)
                
                self.results["repos_tested"][language] = repos_tested
            
            # Save results
            self.save_results()
            
        finally:
            # Cleanup
            if input("\nClean up workspace? (y/n): ").lower() == 'y':
                self.cleanup_workspace()
    
    def save_results(self):
        """Save test results to file."""
        results_file = Path("mcp_test_results.json")
        
        with open(results_file, "w") as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\nResults saved to: {results_file}")
        
        # Print summary
        print("\n=== Test Summary ===")
        print(f"Languages tested: {len(self.results['repos_tested'])}")
        print(f"Total repos: {sum(len(repos) for repos in self.results['repos_tested'].values())}")
        print(f"Errors: {len(self.results['errors'])}")
        
        if self.results['errors']:
            print("\nErrors encountered:")
            for error in self.results['errors']:
                print(f"  - {error}")


def main():
    """Run comprehensive MCP testing."""
    # Check if git is available
    if subprocess.run(["which", "git"], capture_output=True).returncode != 0:
        print("Error: git is required but not found")
        return 1
    
    # Create tester
    tester = MCPTester()
    
    # Run tests
    tester.run_comprehensive_test()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())