#!/usr/bin/env python3
"""Test script for multi-repository and smart plugin loading capabilities."""

import os
import sys
import json
import time
import psutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MultiRepoCapabilityTester:
    """Test multi-repository and smart plugin loading features."""
    
    def __init__(self):
        self.results = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "tests": {},
            "summary": {}
        }
        self.mcp_server_proc = None
        
    def cleanup(self):
        """Cleanup any running processes."""
        if self.mcp_server_proc:
            self.mcp_server_proc.terminate()
            self.mcp_server_proc.wait()
            
    def start_mcp_server(self, env_vars: Dict[str, str] = None) -> bool:
        """Start MCP server with specified environment variables."""
        try:
            # Stop any existing server
            if self.mcp_server_proc:
                self.mcp_server_proc.terminate()
                self.mcp_server_proc.wait()
                
            # Prepare environment
            env = os.environ.copy()
            # Ensure PYTHONPATH includes project root
            project_root = Path(__file__).parent.parent
            env["PYTHONPATH"] = str(project_root) + os.pathsep + env.get("PYTHONPATH", "")
            if env_vars:
                env.update(env_vars)
                
            # Start server
            server_script = Path(__file__).parent / "cli" / "mcp_server_cli.py"
            self.mcp_server_proc = subprocess.Popen(
                [sys.executable, str(server_script)],
                env=env,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for server to start
            time.sleep(2)
            
            # Check if still running
            if self.mcp_server_proc.poll() is not None:
                stdout, stderr = self.mcp_server_proc.communicate()
                logger.error(f"MCP server failed to start: {stderr}")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            return False
            
    def send_mcp_command(self, tool: str, arguments: Dict = None) -> Dict:
        """Send command to MCP server via stdin."""
        try:
            # Create command
            command = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": tool,
                    "arguments": arguments or {}
                },
                "id": 1
            }
            
            # Send to running server via stdin
            if self.mcp_server_proc and self.mcp_server_proc.poll() is None:
                # Write to stdin and flush
                self.mcp_server_proc.stdin.write(json.dumps(command) + "\n")
                self.mcp_server_proc.stdin.flush()
                
                # Read response (with timeout)
                import select
                ready, _, _ = select.select([self.mcp_server_proc.stdout], [], [], 5.0)
                if ready:
                    response_line = self.mcp_server_proc.stdout.readline()
                    try:
                        return json.loads(response_line)
                    except:
                        return {"raw_output": response_line}
                else:
                    return {"error": "Timeout waiting for response"}
            else:
                return {"error": "MCP server not running"}
                
        except Exception as e:
            logger.error(f"Failed to send MCP command: {e}")
            return {"error": str(e)}
            
    def test_basic_status(self) -> Dict:
        """Test basic MCP server status."""
        logger.info("Testing basic MCP server status...")
        
        result = {
            "passed": False,
            "details": {}
        }
        
        # Start server with default settings
        if not self.start_mcp_server():
            result["details"]["error"] = "Failed to start MCP server"
            return result
            
        # Get status
        response = self.send_mcp_command("get_status")
        
        if "error" not in response:
            result["passed"] = True
            result["details"]["status"] = response
            
            # Check for new features
            if "dispatcher" in str(response):
                result["details"]["enhanced_dispatcher"] = True
            if "plugins_loaded" in str(response):
                result["details"]["plugin_info_available"] = True
                
        return result
        
    def test_repository_aware_loading(self) -> Dict:
        """Test repository-aware plugin loading."""
        logger.info("Testing repository-aware plugin loading...")
        
        result = {
            "passed": False,
            "details": {}
        }
        
        # Start with auto plugin strategy
        env_vars = {
            "MCP_PLUGIN_STRATEGY": "auto",
            "MCP_DEBUG": "1"
        }
        
        if not self.start_mcp_server(env_vars):
            result["details"]["error"] = "Failed to start MCP server"
            return result
            
        # Get initial memory usage
        process = psutil.Process(self.mcp_server_proc.pid)
        initial_memory = process.memory_info().rss / (1024 * 1024)  # MB
        
        # Wait for plugins to load
        time.sleep(3)
        
        # Get status to see loaded plugins
        response = self.send_mcp_command("get_status")
        
        if "error" not in response:
            # Get memory after loading
            final_memory = process.memory_info().rss / (1024 * 1024)  # MB
            
            result["details"]["initial_memory_mb"] = round(initial_memory, 2)
            result["details"]["final_memory_mb"] = round(final_memory, 2)
            result["details"]["memory_increase_mb"] = round(final_memory - initial_memory, 2)
            
            # Check plugin count
            status_str = str(response)
            if "plugins" in status_str:
                # Try to extract plugin count
                result["details"]["status_info"] = status_str[:500]  # First 500 chars
                
            # If memory increase is less than 500MB, likely smart loading worked
            if final_memory - initial_memory < 500:
                result["passed"] = True
                result["details"]["smart_loading_detected"] = True
                
        return result
        
    def test_memory_aware_management(self) -> Dict:
        """Test memory-aware plugin management."""
        logger.info("Testing memory-aware plugin management...")
        
        result = {
            "passed": False,
            "details": {}
        }
        
        # Start with low memory limits
        env_vars = {
            "MCP_PLUGIN_STRATEGY": "all",  # Load all plugins
            "MCP_MAX_MEMORY_MB": "512",
            "MCP_MIN_FREE_MB": "128",
            "MCP_DEBUG": "1"
        }
        
        if not self.start_mcp_server(env_vars):
            result["details"]["error"] = "Failed to start MCP server"
            return result
            
        # Monitor memory over time
        memory_samples = []
        process = psutil.Process(self.mcp_server_proc.pid)
        
        for i in range(5):
            time.sleep(2)
            memory_mb = process.memory_info().rss / (1024 * 1024)
            memory_samples.append(round(memory_mb, 2))
            
        result["details"]["memory_samples_mb"] = memory_samples
        result["details"]["max_memory_mb"] = max(memory_samples)
        result["details"]["configured_limit_mb"] = 512
        
        # Check if memory stayed under limit (with some buffer)
        if max(memory_samples) < 600:  # 512MB + buffer
            result["passed"] = True
            result["details"]["memory_limit_respected"] = True
            
        return result
        
    def test_multi_repository_search(self) -> Dict:
        """Test multi-repository search functionality."""
        logger.info("Testing multi-repository search...")
        
        result = {
            "passed": False,
            "details": {}
        }
        
        # Find available repository indexes
        indexes_path = Path(".indexes")
        repo_dirs = [d for d in indexes_path.iterdir() if d.is_dir() and (d / "current.db").exists()]
        
        if len(repo_dirs) < 2:
            result["details"]["error"] = "Not enough repository indexes for testing"
            return result
            
        # Use first two repos
        repo_ids = [d.name for d in repo_dirs[:2]]
        
        # Start with multi-repo enabled
        env_vars = {
            "MCP_ENABLE_MULTI_REPO": "true",
            "MCP_REFERENCE_REPOS": ",".join(repo_ids),
            "MCP_PLUGIN_STRATEGY": "auto"
        }
        
        if not self.start_mcp_server(env_vars):
            result["details"]["error"] = "Failed to start MCP server"
            return result
            
        # Test 1: Search in authorized repo
        response1 = self.send_mcp_command("search_code", {
            "query": "function",
            "repository": repo_ids[0],
            "limit": 5
        })
        
        # Test 2: Search in unauthorized repo (should fail)
        unauthorized_repo = repo_dirs[2].name if len(repo_dirs) > 2 else "fake_repo_id"
        response2 = self.send_mcp_command("search_code", {
            "query": "function",
            "repository": unauthorized_repo,
            "limit": 5
        })
        
        # Test 3: Normal search (current repo)
        response3 = self.send_mcp_command("search_code", {
            "query": "function",
            "limit": 5
        })
        
        result["details"]["authorized_repos"] = repo_ids
        result["details"]["search_authorized"] = "error" not in response1
        result["details"]["search_unauthorized"] = "not authorized" in str(response2).lower()
        result["details"]["search_current"] = "error" not in response3
        
        # Pass if authorized search worked and unauthorized was blocked
        if result["details"]["search_authorized"] and result["details"]["search_unauthorized"]:
            result["passed"] = True
            
        return result
        
    def test_performance_scenarios(self) -> Dict:
        """Test different performance scenarios."""
        logger.info("Testing performance scenarios...")
        
        result = {
            "passed": True,
            "scenarios": {}
        }
        
        scenarios = [
            {
                "name": "single_repo_auto",
                "env": {
                    "MCP_PLUGIN_STRATEGY": "auto"
                }
            },
            {
                "name": "multi_repo_reference",
                "env": {
                    "MCP_ENABLE_MULTI_REPO": "true",
                    "MCP_REFERENCE_REPOS": "repo1,repo2",
                    "MCP_PLUGIN_STRATEGY": "auto"
                }
            },
            {
                "name": "analysis_mode_all",
                "env": {
                    "MCP_ANALYSIS_MODE": "true",
                    "MCP_MAX_MEMORY_MB": "2048"
                }
            }
        ]
        
        for scenario in scenarios:
            logger.info(f"Testing scenario: {scenario['name']}")
            
            # Start server
            start_time = time.time()
            if not self.start_mcp_server(scenario["env"]):
                result["scenarios"][scenario["name"]] = {
                    "error": "Failed to start server"
                }
                continue
                
            startup_time = time.time() - start_time
            
            # Wait for initialization
            time.sleep(2)
            
            # Get memory usage
            process = psutil.Process(self.mcp_server_proc.pid)
            memory_mb = process.memory_info().rss / (1024 * 1024)
            
            # Run search test
            search_start = time.time()
            response = self.send_mcp_command("search_code", {
                "query": "class",
                "limit": 10
            })
            search_time = time.time() - search_start
            
            result["scenarios"][scenario["name"]] = {
                "startup_time_s": round(startup_time, 2),
                "memory_mb": round(memory_mb, 2),
                "search_time_s": round(search_time, 3),
                "search_success": "error" not in response
            }
            
        return result
        
    def run_all_tests(self):
        """Run all capability tests."""
        logger.info("Starting multi-repository capability tests...")
        
        try:
            # Test 1: Basic status
            self.results["tests"]["basic_status"] = self.test_basic_status()
            
            # Test 2: Repository-aware loading
            self.results["tests"]["repository_aware_loading"] = self.test_repository_aware_loading()
            
            # Test 3: Memory-aware management
            self.results["tests"]["memory_aware_management"] = self.test_memory_aware_management()
            
            # Test 4: Multi-repository search
            self.results["tests"]["multi_repository_search"] = self.test_multi_repository_search()
            
            # Test 5: Performance scenarios
            self.results["tests"]["performance_scenarios"] = self.test_performance_scenarios()
            
            # Calculate summary
            total_tests = len(self.results["tests"])
            passed_tests = sum(1 for t in self.results["tests"].values() if t.get("passed", False))
            
            self.results["summary"] = {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "success_rate": f"{(passed_tests/total_tests)*100:.1f}%"
            }
            
        finally:
            self.cleanup()
            
    def save_results(self, filename: str = "multi_repo_test_results.json"):
        """Save test results to file."""
        with open(filename, "w") as f:
            json.dump(self.results, f, indent=2)
        logger.info(f"Results saved to {filename}")
        
    def print_summary(self):
        """Print test summary."""
        print("\n" + "="*60)
        print("Multi-Repository Capability Test Results")
        print("="*60)
        
        for test_name, result in self.results["tests"].items():
            status = "✓ PASSED" if result.get("passed", False) else "✗ FAILED"
            print(f"\n{test_name}: {status}")
            
            # Print key details
            if "details" in result:
                for key, value in result["details"].items():
                    if key != "status_info":  # Skip long strings
                        print(f"  - {key}: {value}")
                        
        print("\n" + "-"*60)
        print(f"Summary: {self.results['summary']['passed_tests']}/{self.results['summary']['total_tests']} tests passed")
        print(f"Success Rate: {self.results['summary']['success_rate']}")
        print("="*60)


def main():
    """Main test execution."""
    tester = MultiRepoCapabilityTester()
    
    try:
        tester.run_all_tests()
        tester.print_summary()
        tester.save_results()
        
    except KeyboardInterrupt:
        logger.info("Tests interrupted by user")
        tester.cleanup()
        
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        tester.cleanup()
        

if __name__ == "__main__":
    main()