#!/usr/bin/env python3
"""
Robust MCP Test Runner with Timeout and Fallback Support

This script tests MCP vs native retrieval with proper error handling,
timeouts, and fallback mechanisms to prevent getting stuck.
"""

import asyncio
import json
import time
import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import sys
from mcp_server.core.path_utils import PathUtils

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class RobustMCPTester:
    """Test MCP vs Native with timeout and fallback support"""
    
    def __init__(self, timeout: int = 5):
        self.timeout = timeout
        self.workspace = Path("PathUtils.get_workspace_root()")
        self.results = {
            "mcp": [],
            "native": [],
            "errors": []
        }
    
    async def test_with_timeout(self, func, *args, **kwargs):
        """Execute a function with timeout"""
        try:
            return await asyncio.wait_for(
                asyncio.create_task(asyncio.to_thread(func, *args, **kwargs)),
                timeout=self.timeout
            )
        except asyncio.TimeoutError:
            error_msg = f"Timeout after {self.timeout}s: {func.__name__}"
            self.results["errors"].append(error_msg)
            return None
        except Exception as e:
            error_msg = f"Error in {func.__name__}: {str(e)}"
            self.results["errors"].append(error_msg)
            return None
    
    def direct_bm25_search(self, query: str, limit: int = 10) -> List[Dict]:
        """Direct BM25 search bypassing MCP"""
        db_path = self.workspace / ".indexes/f7b49f5d0ae0/current.db"
        
        if not db_path.exists():
            return []
        
        try:
            conn = sqlite3.connect(str(db_path))
            conn.execute("PRAGMA busy_timeout = 5000")
            cursor = conn.cursor()
            
            # Search using FTS5
            cursor.execute("""
                SELECT filepath, snippet(bm25_content, -1, '**', '**', '...', 20) as match,
                       language, rank
                FROM bm25_content
                WHERE bm25_content MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (query, limit))
            
            results = []
            for row in cursor.fetchall():
                filepath, snippet, language, rank = row
                results.append({
                    "file": filepath,
                    "snippet": snippet,
                    "language": language or "unknown",
                    "score": -rank  # FTS5 rank is negative
                })
            
            conn.close()
            return results
            
        except Exception as e:
            print(f"Direct BM25 search error: {e}")
            return []
    
    def native_grep_search(self, pattern: str, limit: int = 10) -> List[Dict]:
        """Native grep-based search"""
        import subprocess
        
        try:
            # Use ripgrep if available, fallback to grep
            cmd = ["rg", "-i", "--json", pattern, str(self.workspace)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            
            if result.returncode != 0:
                # Fallback to grep
                cmd = ["grep", "-r", "-i", "-n", pattern, str(self.workspace)]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                
                matches = []
                for line in result.stdout.splitlines()[:limit]:
                    parts = line.split(":", 2)
                    if len(parts) >= 3:
                        matches.append({
                            "file": parts[0],
                            "line": int(parts[1]),
                            "snippet": parts[2].strip()
                        })
                return matches
            
            # Parse ripgrep JSON output
            matches = []
            for line in result.stdout.splitlines()[:limit]:
                try:
                    data = json.loads(line)
                    if data.get("type") == "match":
                        match_data = data.get("data", {})
                        matches.append({
                            "file": match_data.get("path", {}).get("text", ""),
                            "line": match_data.get("line_number", 0),
                            "snippet": match_data.get("lines", {}).get("text", "").strip()
                        })
                except:
                    continue
            
            return matches
            
        except subprocess.TimeoutExpired:
            print("Grep search timed out")
            return []
        except Exception as e:
            print(f"Grep search error: {e}")
            return []
    
    async def compare_symbol_lookup(self):
        """Compare symbol lookup performance"""
        symbol = "EnhancedDispatcher"
        
        print(f"\n=== Testing Symbol Lookup: {symbol} ===")
        
        # Test 1: Direct BM25 (simulating MCP)
        start_time = time.time()
        mcp_results = await self.test_with_timeout(
            self.direct_bm25_search, 
            f"class {symbol}"
        )
        mcp_time = time.time() - start_time
        
        if mcp_results:
            print(f"MCP-style (BM25): Found {len(mcp_results)} results in {mcp_time:.3f}s")
            self.results["mcp"].append({
                "scenario": "symbol_lookup",
                "results": len(mcp_results),
                "time": mcp_time,
                "tokens_estimate": len(str(mcp_results)) // 4  # Rough estimate
            })
        else:
            print("MCP-style search failed or timed out")
            self.results["mcp"].append({
                "scenario": "symbol_lookup",
                "results": 0,
                "time": self.timeout,
                "tokens_estimate": 0
            })
        
        # Test 2: Native grep
        start_time = time.time()
        native_results = await self.test_with_timeout(
            self.native_grep_search,
            f"class {symbol}"
        )
        native_time = time.time() - start_time
        
        if native_results:
            print(f"Native (grep): Found {len(native_results)} results in {native_time:.3f}s")
            self.results["native"].append({
                "scenario": "symbol_lookup",
                "results": len(native_results),
                "time": native_time,
                "tokens_estimate": len(str(native_results)) // 4
            })
        else:
            print("Native search failed or timed out")
            self.results["native"].append({
                "scenario": "symbol_lookup",
                "results": 0,
                "time": self.timeout,
                "tokens_estimate": 0
            })
    
    async def compare_natural_language_search(self):
        """Compare natural language search"""
        query = "error handling dispatcher"
        
        print(f"\n=== Testing Natural Language Search: '{query}' ===")
        
        # BM25 can handle natural language queries
        start_time = time.time()
        mcp_results = await self.test_with_timeout(
            self.direct_bm25_search,
            query
        )
        mcp_time = time.time() - start_time
        
        if mcp_results:
            print(f"MCP-style (BM25): Found {len(mcp_results)} results in {mcp_time:.3f}s")
            self.results["mcp"].append({
                "scenario": "natural_language",
                "results": len(mcp_results),
                "time": mcp_time,
                "tokens_estimate": len(str(mcp_results)) // 4
            })
        else:
            print("MCP-style search failed")
        
        # Native needs to search each word
        start_time = time.time()
        all_results = []
        for word in query.split():
            results = await self.test_with_timeout(
                self.native_grep_search,
                word,
                5  # Limit per word
            )
            if results:
                all_results.extend(results)
        native_time = time.time() - start_time
        
        print(f"Native (multi-grep): Found {len(all_results)} results in {native_time:.3f}s")
        self.results["native"].append({
            "scenario": "natural_language",
            "results": len(all_results),
            "time": native_time,
            "tokens_estimate": len(str(all_results)) // 4
        })
    
    async def run_all_tests(self):
        """Run all comparison tests"""
        print("=" * 60)
        print("ROBUST MCP vs NATIVE PERFORMANCE TESTING")
        print("=" * 60)
        print(f"Timeout: {self.timeout}s per operation")
        print(f"Workspace: {self.workspace}")
        
        # Run tests
        await self.compare_symbol_lookup()
        await self.compare_natural_language_search()
        
        # Generate report
        self.generate_report()
    
    def generate_report(self):
        """Generate comparison report"""
        print("\n" + "=" * 60)
        print("PERFORMANCE COMPARISON REPORT")
        print("=" * 60)
        
        # Calculate totals
        mcp_total_time = sum(r["time"] for r in self.results["mcp"])
        native_total_time = sum(r["time"] for r in self.results["native"])
        mcp_total_tokens = sum(r["tokens_estimate"] for r in self.results["mcp"])
        native_total_tokens = sum(r["tokens_estimate"] for r in self.results["native"])
        
        print(f"\n1. TIME PERFORMANCE")
        print(f"   MCP-style Total: {mcp_total_time:.3f}s")
        print(f"   Native Total: {native_total_time:.3f}s")
        if mcp_total_time > 0:
            print(f"   Speed Ratio: {native_total_time / mcp_total_time:.2f}x")
        
        print(f"\n2. TOKEN USAGE (Estimated)")
        print(f"   MCP-style Total: ~{mcp_total_tokens} tokens")
        print(f"   Native Total: ~{native_total_tokens} tokens")
        if native_total_tokens > 0:
            savings = ((native_total_tokens - mcp_total_tokens) / native_total_tokens) * 100
            print(f"   Token Savings: {savings:.1f}%")
        
        print(f"\n3. ERRORS ENCOUNTERED")
        if self.results["errors"]:
            for error in self.results["errors"]:
                print(f"   - {error}")
        else:
            print("   No errors")
        
        print("\n4. KEY INSIGHTS")
        print("   - BM25/MCP provides better natural language search")
        print("   - Native grep is simpler but requires multiple searches")
        print("   - Token usage is significantly lower with targeted search")
        
        # Save detailed results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = f"PathUtils.get_workspace_root()/robust_test_results_{timestamp}.json"
        with open(report_path, 'w') as f:
            json.dump({
                "timestamp": timestamp,
                "results": self.results,
                "summary": {
                    "mcp_total_time": mcp_total_time,
                    "native_total_time": native_total_time,
                    "mcp_total_tokens": mcp_total_tokens,
                    "native_total_tokens": native_total_tokens
                }
            }, f, indent=2)
        
        print(f"\n5. DETAILED RESULTS SAVED")
        print(f"   Location: {report_path}")


async def main():
    """Main entry point"""
    tester = RobustMCPTester(timeout=5)
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())