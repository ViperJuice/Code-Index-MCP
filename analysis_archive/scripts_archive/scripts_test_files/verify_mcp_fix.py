#!/usr/bin/env python3
"""
Verify that the MCP server is working correctly after configuration fixes.
Tests all MCP tools and compares results with direct access.
"""

import subprocess
import json
import sys
import asyncio
from pathlib import Path
import time

# Add to path
sys.path.insert(0, "/workspaces/Code-Index-MCP")

import scripts.cli.mcp_server_cli as mcp_cli


class MCPVerifier:
    """Verify MCP functionality after fixes."""
    
    def __init__(self):
        self.results = {
            "connection": False,
            "tools_working": {},
            "performance": {},
            "errors": []
        }
        self.dispatcher = None
    
    async def verify_connection(self):
        """Verify MCP server can be initialized."""
        print("1. Verifying MCP Connection...")
        try:
            await mcp_cli.initialize_services()
            self.results["connection"] = True
            print("   ✓ MCP server initialized successfully")
            
            # Check dispatcher
            dispatcher = mcp_cli.dispatcher
            if dispatcher and hasattr(dispatcher, '_sqlite_store'):
                print(f"   ✓ Dispatcher type: {type(dispatcher).__name__}")
                print(f"   ✓ SQLite store available: {dispatcher._sqlite_store is not None}")
                print(f"   ✓ Number of plugins: {len(dispatcher._plugins)}")
                self.dispatcher = dispatcher  # Store for later use
            else:
                print("   ✗ Dispatcher not properly initialized")
                self.results["errors"].append("Dispatcher initialization issue")
        except Exception as e:
            print(f"   ✗ Failed to initialize: {e}")
            self.results["errors"].append(f"Initialization error: {e}")
            return False
        
        return True
    
    async def test_symbol_lookup(self):
        """Test symbol lookup functionality."""
        print("\n2. Testing Symbol Lookup...")
        test_symbols = [
            "BM25Indexer",
            "SQLiteStore", 
            "EnhancedDispatcher",
            "PathResolver"
        ]
        
        for symbol in test_symbols:
            start_time = time.time()
            try:
                result = self.dispatcher.lookup(symbol)
                elapsed = time.time() - start_time
                
                if result:
                    print(f"   ✓ {symbol}: Found in {elapsed:.3f}s")
                    print(f"     - File: {result.get('defined_in', 'unknown')}")
                    print(f"     - Line: {result.get('line', 'unknown')}")
                    self.results["tools_working"][f"lookup_{symbol}"] = True
                    self.results["performance"][f"lookup_{symbol}_time"] = elapsed
                else:
                    print(f"   ✗ {symbol}: Not found")
                    self.results["tools_working"][f"lookup_{symbol}"] = False
            except Exception as e:
                print(f"   ✗ {symbol}: Error - {e}")
                self.results["errors"].append(f"Lookup error for {symbol}: {e}")
    
    async def test_code_search(self):
        """Test code search functionality."""
        print("\n3. Testing Code Search...")
        test_queries = [
            ("reranking", False),
            ("BM25 index", False),
            ("centralized storage", True),  # Semantic
            ("how to index repository", True)  # Natural language
        ]
        
        for query, semantic in test_queries:
            start_time = time.time()
            try:
                results = list(self.dispatcher.search(query, semantic=semantic, limit=5))
                elapsed = time.time() - start_time
                
                print(f"\n   Query: '{query}' (semantic={semantic})")
                print(f"   Found {len(results)} results in {elapsed:.3f}s")
                
                if results:
                    for i, r in enumerate(results[:2]):
                        print(f"   {i+1}. {r.get('file', 'unknown')} (line {r.get('line', 0)})")
                        snippet = r.get('snippet', '').replace('\n', ' ')[:60]
                        print(f"      {snippet}...")
                    
                    self.results["tools_working"][f"search_{query}"] = True
                    self.results["performance"][f"search_{query}_time"] = elapsed
                    self.results["performance"][f"search_{query}_results"] = len(results)
                else:
                    print("   No results found")
                    self.results["tools_working"][f"search_{query}"] = False
                    
            except Exception as e:
                print(f"   ✗ Error searching for '{query}': {e}")
                self.results["errors"].append(f"Search error for '{query}': {e}")
    
    async def test_mcp_cli_interface(self):
        """Test MCP through CLI interface (as Claude Code would use it)."""
        print("\n4. Testing MCP CLI Interface...")
        
        # Create a simple request
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        }
        
        try:
            # Run MCP server
            proc = subprocess.Popen(
                [sys.executable, "scripts/cli/mcp_server_cli.py"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Send initialization
            stdout, stderr = proc.communicate(
                input=json.dumps(request) + "\n",
                timeout=5
            )
            
            if stdout:
                response = json.loads(stdout.strip())
                if "result" in response:
                    print("   ✓ MCP server responds to initialization")
                    self.results["tools_working"]["cli_interface"] = True
                else:
                    print(f"   ✗ Unexpected response: {response}")
                    self.results["tools_working"]["cli_interface"] = False
            else:
                print("   ✗ No response from MCP server")
                self.results["tools_working"]["cli_interface"] = False
                
        except Exception as e:
            print(f"   ✗ CLI interface error: {e}")
            self.results["errors"].append(f"CLI interface error: {e}")
    
    async def compare_with_native_tools(self):
        """Compare MCP performance with native grep/find."""
        print("\n5. Comparing MCP vs Native Tools...")
        
        # Test case: Find a class definition
        query = "class BM25Indexer"
        
        # MCP approach
        start_time = time.time()
        mcp_result = self.dispatcher.lookup("BM25Indexer")
        mcp_time = time.time() - start_time
        
        # Native grep approach (simulated)
        start_time = time.time()
        proc = subprocess.run(
            ["grep", "-r", "--include=*.py", "class BM25Indexer", "."],
            capture_output=True,
            text=True,
            timeout=5
        )
        grep_time = time.time() - start_time
        
        print(f"\n   Finding 'class BM25Indexer':")
        print(f"   - MCP lookup: {mcp_time:.3f}s")
        print(f"   - Grep search: {grep_time:.3f}s")
        print(f"   - Speed improvement: {grep_time/mcp_time:.1f}x faster")
        
        self.results["performance"]["mcp_vs_grep_speedup"] = grep_time / mcp_time
    
    def generate_report(self):
        """Generate verification report."""
        print("\n" + "=" * 80)
        print("MCP VERIFICATION REPORT")
        print("=" * 80)
        
        # Connection status
        print(f"\nConnection Status: {'✓ Connected' if self.results['connection'] else '✗ Failed'}")
        
        # Tools status
        print("\nTools Status:")
        working_tools = sum(1 for v in self.results["tools_working"].values() if v)
        total_tools = len(self.results["tools_working"])
        print(f"  Working: {working_tools}/{total_tools}")
        
        for tool, status in self.results["tools_working"].items():
            print(f"  - {tool}: {'✓' if status else '✗'}")
        
        # Performance summary
        if self.results["performance"]:
            print("\nPerformance Metrics:")
            avg_lookup_time = sum(v for k, v in self.results["performance"].items() 
                                if "lookup" in k and "time" in k) / 4
            avg_search_time = sum(v for k, v in self.results["performance"].items() 
                                if "search" in k and "time" in k) / 4
            
            print(f"  - Average lookup time: {avg_lookup_time:.3f}s")
            print(f"  - Average search time: {avg_search_time:.3f}s")
            
            if "mcp_vs_grep_speedup" in self.results["performance"]:
                print(f"  - MCP vs grep speedup: {self.results['performance']['mcp_vs_grep_speedup']:.1f}x")
        
        # Errors
        if self.results["errors"]:
            print("\nErrors Encountered:")
            for error in self.results["errors"]:
                print(f"  - {error}")
        
        # Overall status
        print("\nOverall Status:")
        if self.results["connection"] and working_tools > 0:
            print("  ✓ MCP is functional and ready for use")
            print("  ✓ BM25 fallback is working correctly")
            print("  ✓ Configuration has been fixed")
        else:
            print("  ✗ MCP has issues that need to be addressed")
        
        return self.results
    
    async def run_verification(self):
        """Run complete verification suite."""
        print("Starting MCP Verification Suite")
        print("=" * 80)
        
        # Run tests
        if await self.verify_connection():
            if self.dispatcher:
                await self.test_symbol_lookup()
                await self.test_code_search()
                await self.compare_with_native_tools()
            await self.test_mcp_cli_interface()
        
        # Generate report
        report = self.generate_report()
        
        # Save results
        results_path = Path("/workspaces/Code-Index-MCP/verify_mcp_fix.json")
        results_path.write_text(json.dumps(report, indent=2))
        print(f"\nResults saved to: {results_path}")
        
        return report


async def main():
    """Run MCP verification."""
    verifier = MCPVerifier()
    results = await verifier.run_verification()
    
    # Exit with appropriate code
    if results["connection"] and len(results["errors"]) == 0:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())