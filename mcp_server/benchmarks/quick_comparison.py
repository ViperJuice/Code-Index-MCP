#!/usr/bin/env python3
"""Quick comparison benchmark between MCP and direct search tools.

This lightweight benchmark suite compares MCP indexing/search performance
against direct grep/ripgrep searches, focusing on essential metrics:
- Token usage (for MCP)
- Search latency
- Result count accuracy

Designed to run in under 5 minutes for rapid feedback.
"""

import asyncio
import json
import subprocess
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from mcp_server.dispatcher import Dispatcher
from mcp_server.indexer import Indexer
from mcp_server.plugin_system import PluginLoader


class QuickBenchmark:
    """Lightweight benchmark runner for MCP vs direct search comparison."""

    def __init__(self, workspace_path: str = "."):
        self.workspace_path = Path(workspace_path).resolve()
        self.results = defaultdict(list)
        self.mcp_initialized = False
        self.indexer = None
        self.dispatcher = None

    async def setup_mcp(self):
        """Initialize MCP components."""
        if self.mcp_initialized:
            return

        print("Setting up MCP components...")
        start_time = time.time()

        # Initialize plugin loader
        plugin_loader = PluginLoader()
        await plugin_loader.discover_plugins()

        # Initialize indexer
        self.indexer = Indexer(
            db_path=str(self.workspace_path / ".mcp_benchmark.db"),
            workspace_path=str(self.workspace_path),
        )

        # Initialize dispatcher
        self.dispatcher = Dispatcher(plugin_loader=plugin_loader, indexer=self.indexer)

        setup_time = time.time() - start_time
        self.results["setup"]["mcp_init_time"] = setup_time
        self.mcp_initialized = True
        print(f"MCP setup completed in {setup_time:.2f}s")

    async def build_index(self, file_patterns: List[str] = None):
        """Build MCP index for specified file patterns."""
        if not file_patterns:
            file_patterns = ["**/*.py", "**/*.js", "**/*.ts", "**/*.go"]

        print(f"Building index for patterns: {file_patterns}")
        start_time = time.time()

        indexed_count = 0
        for pattern in file_patterns:
            files = list(self.workspace_path.glob(pattern))[:100]  # Limit for speed
            for file_path in files:
                if file_path.is_file():
                    try:
                        await self.indexer.index_file(str(file_path))
                        indexed_count += 1
                    except Exception as e:
                        print(f"Error indexing {file_path}: {e}")

        index_time = time.time() - start_time
        self.results["indexing"]["files_indexed"] = indexed_count
        self.results["indexing"]["index_time"] = index_time
        print(f"Indexed {indexed_count} files in {index_time:.2f}s")

    def run_ripgrep(self, pattern: str, file_type: Optional[str] = None) -> Tuple[List[str], float]:
        """Run ripgrep search and return results with timing."""
        cmd = ["rg", "--json", pattern, str(self.workspace_path)]
        if file_type:
            cmd.extend(["-t", file_type])

        start_time = time.time()
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            search_time = time.time() - start_time

            matches = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    try:
                        data = json.loads(line)
                        if data.get("type") == "match":
                            matches.append(data["data"]["path"]["text"])
                    except json.JSONDecodeError:
                        pass

            return matches, search_time
        except subprocess.TimeoutExpired:
            return [], 30.0
        except FileNotFoundError:
            print("ripgrep (rg) not found. Please install it for comparisons.")
            return [], 0.0

    def run_grep(self, pattern: str, file_pattern: str = "*") -> Tuple[List[str], float]:
        """Run grep search and return results with timing."""
        cmd = ["grep", "-r", "-l", pattern, str(self.workspace_path), "--include=" + file_pattern]

        start_time = time.time()
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            search_time = time.time() - start_time

            matches = [line.strip() for line in result.stdout.strip().split("\n") if line]
            return matches, search_time
        except subprocess.TimeoutExpired:
            return [], 30.0

    async def run_mcp_search(
        self, query: str, search_type: str = "code"
    ) -> Tuple[List[Dict], float, int]:
        """Run MCP search and return results with timing and token usage."""
        start_time = time.time()

        # Track token usage (simplified - in real implementation would use actual tokenizer)
        query_tokens = len(query.split()) * 2  # Rough estimate

        if search_type == "symbol":
            results = await self.dispatcher.symbol_lookup(query)
        else:
            results = await self.dispatcher.search_code(query, limit=100)

        search_time = time.time() - start_time

        # Estimate result tokens (simplified)
        result_tokens = sum(len(str(r).split()) * 2 for r in results[:10])  # Sample first 10
        total_tokens = query_tokens + result_tokens

        return results, search_time, total_tokens

    async def compare_symbol_search(self):
        """Compare symbol search performance."""
        print("\n=== Symbol Search Comparison ===")

        test_symbols = ["def main", "class Config", "function init", "const API", "interface User"]

        for symbol in test_symbols:
            print(f"\nSearching for: '{symbol}'")

            # MCP search
            if self.mcp_initialized:
                mcp_results, mcp_time, tokens = await self.run_mcp_search(symbol, "symbol")
                print(f"  MCP: {len(mcp_results)} results in {mcp_time:.3f}s ({tokens} tokens)")
                self.results["symbol_search"].append(
                    {
                        "query": symbol,
                        "mcp_results": len(mcp_results),
                        "mcp_time": mcp_time,
                        "mcp_tokens": tokens,
                    }
                )

            # Ripgrep search
            rg_results, rg_time = self.run_ripgrep(symbol)
            print(f"  Ripgrep: {len(rg_results)} results in {rg_time:.3f}s")

            if "symbol_search" in self.results and self.results["symbol_search"]:
                self.results["symbol_search"][-1].update(
                    {"rg_results": len(rg_results), "rg_time": rg_time}
                )

    async def compare_pattern_search(self):
        """Compare pattern search performance."""
        print("\n=== Pattern Search Comparison ===")

        test_patterns = [
            "TODO|FIXME",
            "import.*from",
            "async.*await",
            "error.*handling",
            "\\btest\\w*",
        ]

        for pattern in test_patterns:
            print(f"\nSearching for pattern: '{pattern}'")

            # MCP search
            if self.mcp_initialized:
                mcp_results, mcp_time, tokens = await self.run_mcp_search(pattern, "code")
                print(f"  MCP: {len(mcp_results)} results in {mcp_time:.3f}s ({tokens} tokens)")
                self.results["pattern_search"].append(
                    {
                        "query": pattern,
                        "mcp_results": len(mcp_results),
                        "mcp_time": mcp_time,
                        "mcp_tokens": tokens,
                    }
                )

            # Ripgrep search
            rg_results, rg_time = self.run_ripgrep(pattern)
            print(f"  Ripgrep: {len(rg_results)} results in {rg_time:.3f}s")

            # Grep search
            grep_results, grep_time = self.run_grep(pattern)
            print(f"  Grep: {len(grep_results)} results in {grep_time:.3f}s")

            if "pattern_search" in self.results and self.results["pattern_search"]:
                self.results["pattern_search"][-1].update(
                    {
                        "rg_results": len(rg_results),
                        "rg_time": rg_time,
                        "grep_results": len(grep_results),
                        "grep_time": grep_time,
                    }
                )

    def generate_summary(self):
        """Generate a summary report of benchmark results."""
        print("\n" + "=" * 60)
        print("BENCHMARK SUMMARY")
        print("=" * 60)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"Generated: {timestamp}")
        print(f"Workspace: {self.workspace_path}")

        # Indexing summary
        if "indexing" in self.results:
            print("\nIndexing:")
            print(f"  Files indexed: {self.results['indexing'].get('files_indexed', 0)}")
            print(f"  Index time: {self.results['indexing'].get('index_time', 0):.2f}s")

        # Symbol search summary
        if "symbol_search" in self.results:
            print("\nSymbol Search Performance:")
            total_mcp_time = sum(r["mcp_time"] for r in self.results["symbol_search"])
            total_rg_time = sum(r["rg_time"] for r in self.results["symbol_search"])
            total_tokens = sum(r["mcp_tokens"] for r in self.results["symbol_search"])

            print(f"  MCP total time: {total_mcp_time:.3f}s")
            print(f"  Ripgrep total time: {total_rg_time:.3f}s")
            print(f"  MCP total tokens: {total_tokens}")
            print(f"  Speed ratio (rg/mcp): {total_rg_time/max(total_mcp_time, 0.001):.2f}x")

        # Pattern search summary
        if "pattern_search" in self.results:
            print("\nPattern Search Performance:")
            total_mcp_time = sum(r["mcp_time"] for r in self.results["pattern_search"])
            total_rg_time = sum(r["rg_time"] for r in self.results["pattern_search"])
            total_grep_time = sum(r["grep_time"] for r in self.results["pattern_search"])
            total_tokens = sum(r["mcp_tokens"] for r in self.results["pattern_search"])

            print(f"  MCP total time: {total_mcp_time:.3f}s")
            print(f"  Ripgrep total time: {total_rg_time:.3f}s")
            print(f"  Grep total time: {total_grep_time:.3f}s")
            print(f"  MCP total tokens: {total_tokens}")
            print(f"  Speed ratio (rg/mcp): {total_rg_time/max(total_mcp_time, 0.001):.2f}x")
            print(f"  Speed ratio (grep/mcp): {total_grep_time/max(total_mcp_time, 0.001):.2f}x")

        # Save detailed results
        results_path = self.workspace_path / "benchmark_results.json"
        with open(results_path, "w") as f:
            json.dump(self.results, f, indent=2, default=str)
        print(f"\nDetailed results saved to: {results_path}")

        print("\n" + "=" * 60)

    async def run(self, skip_mcp: bool = False):
        """Run the complete benchmark suite."""
        start_total = time.time()

        if not skip_mcp:
            await self.setup_mcp()
            await self.build_index()

        await self.compare_symbol_search()
        await self.compare_pattern_search()

        total_time = time.time() - start_total
        print(f"\nTotal benchmark time: {total_time:.2f}s")

        self.generate_summary()


async def main():
    """Main entry point for the benchmark."""
    import argparse

    parser = argparse.ArgumentParser(description="Quick MCP vs Direct Search Comparison")
    parser.add_argument("--workspace", "-w", default=".", help="Workspace path to benchmark")
    parser.add_argument("--skip-mcp", action="store_true", help="Skip MCP tests (grep/rg only)")

    args = parser.parse_args()

    benchmark = QuickBenchmark(args.workspace)
    await benchmark.run(skip_mcp=args.skip_mcp)


if __name__ == "__main__":
    asyncio.run(main())
