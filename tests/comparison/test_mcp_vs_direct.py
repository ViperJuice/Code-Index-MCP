#!/usr/bin/env python3
"""
Comprehensive comparison tests between MCP server and direct file operations.

This module measures and compares:
- Token usage (input/output)
- Retrieval time and latency
- Result quality (precision/recall)
- Resource usage (memory/CPU)
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil

# Token counting - we'll use a simple approximation if tiktoken isn't available
try:
    import tiktoken

    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    print("Warning: tiktoken not available. Using approximate token counting.")

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.plugin_system import PluginManager
from mcp_server.storage.sqlite_store import SQLiteStore


@dataclass
class TokenUsage:
    """Track token usage for operations."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    def add(self, input_tokens: int, output_tokens: int):
        """Add token counts."""
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.total_tokens = self.input_tokens + self.output_tokens


@dataclass
class PerformanceMetrics:
    """Performance metrics for an operation."""

    operation: str
    start_time: float = 0.0
    end_time: float = 0.0
    duration_ms: float = 0.0
    memory_mb: float = 0.0
    cpu_percent: float = 0.0

    def start(self):
        """Start timing."""
        self.start_time = time.perf_counter()

    def stop(self):
        """Stop timing and calculate duration."""
        self.end_time = time.perf_counter()
        self.duration_ms = (self.end_time - self.start_time) * 1000


@dataclass
class SearchResult:
    """Unified search result format."""

    file_path: str
    line_number: int
    content: str
    score: float = 1.0
    context: str = ""


@dataclass
class ComparisonResult:
    """Results from comparing MCP vs direct approaches."""

    query: str
    operation_type: str

    # Token usage
    mcp_tokens: TokenUsage = field(default_factory=TokenUsage)
    direct_tokens: TokenUsage = field(default_factory=TokenUsage)

    # Performance
    mcp_performance: PerformanceMetrics = field(default_factory=lambda: PerformanceMetrics("mcp"))
    direct_performance: PerformanceMetrics = field(
        default_factory=lambda: PerformanceMetrics("direct")
    )

    # Results
    mcp_results: List[SearchResult] = field(default_factory=list)
    direct_results: List[SearchResult] = field(default_factory=list)

    # Quality metrics
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0

    def calculate_quality_metrics(self, ground_truth: Optional[List[str]] = None):
        """Calculate precision, recall, and F1 score."""
        if not ground_truth:
            # Use overlap between methods as proxy
            mcp_files = {r.file_path for r in self.mcp_results}
            direct_files = {r.file_path for r in self.direct_results}

            if not mcp_files and not direct_files:
                return

            overlap = mcp_files & direct_files

            self.precision = len(overlap) / len(mcp_files) if mcp_files else 0
            self.recall = len(overlap) / len(direct_files) if direct_files else 0
        else:
            # Use provided ground truth
            truth_set = set(ground_truth)
            mcp_files = {r.file_path for r in self.mcp_results}

            true_positives = len(mcp_files & truth_set)
            false_positives = len(mcp_files - truth_set)
            false_negatives = len(truth_set - mcp_files)

            self.precision = (
                true_positives / (true_positives + false_positives)
                if (true_positives + false_positives) > 0
                else 0
            )
            self.recall = (
                true_positives / (true_positives + false_negatives)
                if (true_positives + false_negatives) > 0
                else 0
            )

        # Calculate F1 score
        if self.precision + self.recall > 0:
            self.f1_score = 2 * (self.precision * self.recall) / (self.precision + self.recall)


class TokenCounter:
    """Utilities for counting tokens."""

    def __init__(self):
        self.encoder = None
        if TIKTOKEN_AVAILABLE:
            try:
                self.encoder = tiktoken.get_encoding("cl100k_base")
            except Exception:
                self.encoder = None

    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        if self.encoder:
            return len(self.encoder.encode(text))
        else:
            # Simple approximation: ~4 characters per token
            return len(text) // 4

    def count_query_tokens(self, query: str, context: Dict[str, Any] = None) -> int:
        """Count tokens in a query with optional context."""
        total = self.count_tokens(query)

        if context:
            # Add context tokens (file paths, metadata, etc.)
            context_str = json.dumps(context, default=str)
            total += self.count_tokens(context_str)

        return total

    def count_result_tokens(self, results: List[Any]) -> int:
        """Count tokens in results."""
        if not results:
            return 0

        # Convert results to string representation
        if isinstance(results[0], SearchResult):
            text = "\n".join([f"{r.file_path}:{r.line_number} {r.content}" for r in results])
        else:
            text = json.dumps(results, default=str)

        return self.count_tokens(text)


class DirectSearcher:
    """Direct file search implementation using grep/ripgrep."""

    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.process = psutil.Process(os.getpid())

        # Check for ripgrep availability
        self.use_ripgrep = shutil.which("rg") is not None
        if not self.use_ripgrep:
            print("Warning: ripgrep not found. Using grep (slower).")

    def search_symbol(self, symbol: str) -> List[SearchResult]:
        """Search for symbol definitions using grep/ripgrep."""
        results = []

        # Build search pattern for common symbol definitions
        patterns = [
            f"def {symbol}",  # Python
            f"function {symbol}",  # JavaScript
            f"func {symbol}",  # Go
            f"class {symbol}",  # Multiple languages
            f"struct {symbol}",  # C/C++/Rust
            f"interface {symbol}",  # TypeScript/Java
            f"trait {symbol}",  # Rust
            f"protocol {symbol}",  # Swift
        ]

        if self.use_ripgrep:
            # Use ripgrep for faster searching
            cmd = [
                "rg",
                "--no-heading",
                "--line-number",
                "--type-add",
                "code:*.{py,js,ts,go,java,rs,c,cpp,h,hpp,swift,kt}",
                "--type",
                "code",
                "-e",
                "|".join(patterns),
                str(self.workspace_path),
            ]
        else:
            # Fall back to grep
            pattern = "|".join(patterns)
            cmd = [
                "grep",
                "-r",
                "-n",
                "-E",
                pattern,
                "--include=*.py",
                "--include=*.js",
                "--include=*.ts",
                "--include=*.go",
                "--include=*.java",
                "--include=*.rs",
                "--include=*.c",
                "--include=*.cpp",
                "--include=*.h",
                "--include=*.hpp",
                "--include=*.swift",
                "--include=*.kt",
                str(self.workspace_path),
            ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            for line in result.stdout.splitlines():
                if self.use_ripgrep:
                    # Format: path:line:content
                    parts = line.split(":", 2)
                    if len(parts) >= 3:
                        results.append(
                            SearchResult(
                                file_path=parts[0],
                                line_number=int(parts[1]),
                                content=parts[2].strip(),
                            )
                        )
                else:
                    # grep format: path:line:content
                    match = re.match(r"^(.+?):(\d+):(.*)$", line)
                    if match:
                        results.append(
                            SearchResult(
                                file_path=match.group(1),
                                line_number=int(match.group(2)),
                                content=match.group(3).strip(),
                            )
                        )

        except subprocess.TimeoutExpired:
            print(f"Search timed out for symbol: {symbol}")
        except Exception as e:
            print(f"Search error: {e}")

        return results

    def search_pattern(self, pattern: str, semantic: bool = False) -> List[SearchResult]:
        """Search for patterns in code."""
        if semantic:
            # Can't do semantic search with grep
            print("Warning: Semantic search not available with direct approach")
            return []

        results = []

        if self.use_ripgrep:
            cmd = [
                "rg",
                "--no-heading",
                "--line-number",
                "--type-add",
                "code:*.{py,js,ts,go,java,rs,c,cpp,h,hpp,swift,kt}",
                "--type",
                "code",
                pattern,
                str(self.workspace_path),
            ]
        else:
            cmd = [
                "grep",
                "-r",
                "-n",
                "-E",
                pattern,
                "--include=*.py",
                "--include=*.js",
                "--include=*.ts",
                "--include=*.go",
                "--include=*.java",
                "--include=*.rs",
                "--include=*.c",
                "--include=*.cpp",
                "--include=*.h",
                "--include=*.hpp",
                "--include=*.swift",
                "--include=*.kt",
                str(self.workspace_path),
            ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            for line in result.stdout.splitlines():
                if self.use_ripgrep:
                    parts = line.split(":", 2)
                    if len(parts) >= 3:
                        results.append(
                            SearchResult(
                                file_path=parts[0],
                                line_number=int(parts[1]),
                                content=parts[2].strip(),
                            )
                        )
                else:
                    match = re.match(r"^(.+?):(\d+):(.*)$", line)
                    if match:
                        results.append(
                            SearchResult(
                                file_path=match.group(1),
                                line_number=int(match.group(2)),
                                content=match.group(3).strip(),
                            )
                        )

        except subprocess.TimeoutExpired:
            print(f"Search timed out for pattern: {pattern}")
        except Exception as e:
            print(f"Search error: {e}")

        return results

    def get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        return self.process.memory_info().rss / (1024 * 1024)

    def get_cpu_percent(self) -> float:
        """Get CPU usage percentage."""
        return self.process.cpu_percent(interval=0.1)


class MCPComparison:
    """Main comparison test runner."""

    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.token_counter = TokenCounter()
        self.direct_searcher = DirectSearcher(workspace_path)

        # Initialize MCP components
        self.dispatcher = None
        self.plugin_manager = None
        self.sqlite_store = None

        # Results storage
        self.results: List[ComparisonResult] = []

    def setup_mcp(self):
        """Initialize MCP server components."""
        print("Setting up MCP server...")

        # Create temporary database
        db_path = self.workspace_path / "test_index.db"
        self.sqlite_store = SQLiteStore(str(db_path))

        # Initialize plugin manager
        self.plugin_manager = PluginManager(sqlite_store=self.sqlite_store)
        self.plugin_manager.load_plugins_safe()

        # Get active plugins
        active_plugins = self.plugin_manager.get_active_plugins()
        plugin_instances = list(active_plugins.values())

        # Create dispatcher
        self.dispatcher = EnhancedDispatcher(
            plugins=plugin_instances,
            sqlite_store=self.sqlite_store,
            enable_advanced_features=True,
            use_plugin_factory=True,
            lazy_load=True,
            semantic_search_enabled=False,  # Disable for fair comparison
        )

        print(f"MCP setup complete. {len(plugin_instances)} plugins loaded.")

    def index_workspace(self):
        """Index the workspace with MCP."""
        print(f"Indexing workspace: {self.workspace_path}")

        start_time = time.time()
        file_count = 0

        for root, _, files in os.walk(self.workspace_path):
            for file in files:
                if file.endswith(
                    (
                        ".py",
                        ".js",
                        ".ts",
                        ".go",
                        ".java",
                        ".rs",
                        ".c",
                        ".cpp",
                        ".h",
                        ".hpp",
                        ".swift",
                        ".kt",
                    )
                ):
                    file_path = Path(root) / file
                    try:
                        self.dispatcher.index_file(str(file_path))
                        file_count += 1
                    except Exception as e:
                        print(f"Failed to index {file_path}: {e}")

        duration = time.time() - start_time
        print(f"Indexed {file_count} files in {duration:.2f} seconds")

    def compare_symbol_lookup(self, symbol: str) -> ComparisonResult:
        """Compare symbol lookup between MCP and direct search."""
        result = ComparisonResult(query=symbol, operation_type="symbol_lookup")

        # Count input tokens
        input_tokens = self.token_counter.count_query_tokens(symbol)

        # MCP search
        print(f"  MCP: Searching for symbol '{symbol}'...")
        result.mcp_performance.start()

        try:
            mcp_result = self.dispatcher.lookup(symbol)
            if mcp_result:
                result.mcp_results.append(
                    SearchResult(
                        file_path=mcp_result.get("defined_in", ""),
                        line_number=mcp_result.get("line", 0),
                        content=mcp_result.get("signature", ""),
                        context=json.dumps(mcp_result),
                    )
                )
        except Exception as e:
            print(f"    Error: {e}")

        result.mcp_performance.stop()
        result.mcp_performance.memory_mb = self.direct_searcher.get_memory_usage()
        result.mcp_performance.cpu_percent = self.direct_searcher.get_cpu_percent()

        # Count MCP output tokens
        mcp_output_tokens = self.token_counter.count_result_tokens(result.mcp_results)
        result.mcp_tokens.add(input_tokens, mcp_output_tokens)

        # Direct search
        print(f"  Direct: Searching for symbol '{symbol}'...")
        result.direct_performance.start()

        direct_results = self.direct_searcher.search_symbol(symbol)
        result.direct_results = direct_results

        result.direct_performance.stop()
        result.direct_performance.memory_mb = self.direct_searcher.get_memory_usage()
        result.direct_performance.cpu_percent = self.direct_searcher.get_cpu_percent()

        # Count direct output tokens
        direct_output_tokens = self.token_counter.count_result_tokens(result.direct_results)
        result.direct_tokens.add(input_tokens, direct_output_tokens)

        # Calculate quality metrics
        result.calculate_quality_metrics()

        return result

    def compare_pattern_search(self, pattern: str, semantic: bool = False) -> ComparisonResult:
        """Compare pattern search between MCP and direct search."""
        result = ComparisonResult(
            query=pattern, operation_type="pattern_search" if not semantic else "semantic_search"
        )

        # Count input tokens
        input_tokens = self.token_counter.count_query_tokens(pattern)

        # MCP search
        print(f"  MCP: Searching for pattern '{pattern}' (semantic={semantic})...")
        result.mcp_performance.start()

        try:
            mcp_results = list(self.dispatcher.search(pattern, semantic=semantic, limit=50))
            for r in mcp_results:
                result.mcp_results.append(
                    SearchResult(
                        file_path=r.file_path,
                        line_number=r.line_number,
                        content=r.content,
                        score=getattr(r, "score", 1.0),
                    )
                )
        except Exception as e:
            print(f"    Error: {e}")

        result.mcp_performance.stop()
        result.mcp_performance.memory_mb = self.direct_searcher.get_memory_usage()
        result.mcp_performance.cpu_percent = self.direct_searcher.get_cpu_percent()

        # Count MCP output tokens
        mcp_output_tokens = self.token_counter.count_result_tokens(result.mcp_results)
        result.mcp_tokens.add(input_tokens, mcp_output_tokens)

        # Direct search
        if not semantic:  # Can't do semantic with grep
            print(f"  Direct: Searching for pattern '{pattern}'...")
            result.direct_performance.start()

            direct_results = self.direct_searcher.search_pattern(pattern, semantic=False)
            result.direct_results = direct_results

            result.direct_performance.stop()
            result.direct_performance.memory_mb = self.direct_searcher.get_memory_usage()
            result.direct_performance.cpu_percent = self.direct_searcher.get_cpu_percent()

            # Count direct output tokens
            direct_output_tokens = self.token_counter.count_result_tokens(result.direct_results)
            result.direct_tokens.add(input_tokens, direct_output_tokens)

        # Calculate quality metrics
        result.calculate_quality_metrics()

        return result

    def run_test_suite(self, test_queries: Dict[str, List[str]]) -> List[ComparisonResult]:
        """Run a suite of comparison tests."""
        print("\nRunning comparison test suite...")
        print("=" * 60)

        # Symbol lookups
        if "symbols" in test_queries:
            print("\nSymbol Lookup Tests:")
            print("-" * 40)
            for symbol in test_queries["symbols"]:
                result = self.compare_symbol_lookup(symbol)
                self.results.append(result)
                self._print_result_summary(result)

        # Pattern searches
        if "patterns" in test_queries:
            print("\nPattern Search Tests:")
            print("-" * 40)
            for pattern in test_queries["patterns"]:
                result = self.compare_pattern_search(pattern)
                self.results.append(result)
                self._print_result_summary(result)

        # Semantic searches (MCP only)
        if "semantic" in test_queries:
            print("\nSemantic Search Tests (MCP only):")
            print("-" * 40)
            for query in test_queries["semantic"]:
                result = self.compare_pattern_search(query, semantic=True)
                self.results.append(result)
                self._print_result_summary(result)

        return self.results

    def _print_result_summary(self, result: ComparisonResult):
        """Print a summary of a single comparison result."""
        print(f"\nQuery: {result.query}")
        print(
            f"  MCP: {len(result.mcp_results)} results in {result.mcp_performance.duration_ms:.2f}ms"
        )
        print(
            f"       Tokens: {result.mcp_tokens.total_tokens} (in:{result.mcp_tokens.input_tokens}, out:{result.mcp_tokens.output_tokens})"
        )

        if result.direct_results is not None:
            print(
                f"  Direct: {len(result.direct_results)} results in {result.direct_performance.duration_ms:.2f}ms"
            )
            print(
                f"          Tokens: {result.direct_tokens.total_tokens} (in:{result.direct_tokens.input_tokens}, out:{result.direct_tokens.output_tokens})"
            )

            # Performance comparison
            speedup = (
                result.direct_performance.duration_ms / result.mcp_performance.duration_ms
                if result.mcp_performance.duration_ms > 0
                else 0
            )
            print(
                f"  Speedup: {speedup:.2f}x {'(MCP faster)' if speedup > 1 else '(Direct faster)'}"
            )

            # Token comparison
            token_ratio = (
                result.mcp_tokens.total_tokens / result.direct_tokens.total_tokens
                if result.direct_tokens.total_tokens > 0
                else 0
            )
            print(
                f"  Token ratio: {token_ratio:.2f}x {'(MCP uses more)' if token_ratio > 1 else '(Direct uses more)'}"
            )

        if result.precision > 0 or result.recall > 0:
            print(
                f"  Quality: Precision={result.precision:.2f}, Recall={result.recall:.2f}, F1={result.f1_score:.2f}"
            )

    def generate_report(self, output_file: Optional[Path] = None):
        """Generate a comprehensive comparison report."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "workspace": str(self.workspace_path),
            "summary": {
                "total_tests": len(self.results),
                "avg_mcp_latency_ms": 0,
                "avg_direct_latency_ms": 0,
                "total_mcp_tokens": 0,
                "total_direct_tokens": 0,
                "mcp_wins": 0,
                "direct_wins": 0,
            },
            "details": [],
        }

        # Calculate summaries
        mcp_latencies = []
        direct_latencies = []

        for result in self.results:
            # Latencies
            mcp_latencies.append(result.mcp_performance.duration_ms)
            if result.direct_performance.duration_ms > 0:
                direct_latencies.append(result.direct_performance.duration_ms)

            # Tokens
            report["summary"]["total_mcp_tokens"] += result.mcp_tokens.total_tokens
            report["summary"]["total_direct_tokens"] += result.direct_tokens.total_tokens

            # Win counts
            if result.direct_performance.duration_ms > 0:
                if result.mcp_performance.duration_ms < result.direct_performance.duration_ms:
                    report["summary"]["mcp_wins"] += 1
                else:
                    report["summary"]["direct_wins"] += 1

            # Detailed results
            report["details"].append(
                {
                    "query": result.query,
                    "operation": result.operation_type,
                    "mcp": {
                        "results": len(result.mcp_results),
                        "latency_ms": result.mcp_performance.duration_ms,
                        "tokens": {
                            "input": result.mcp_tokens.input_tokens,
                            "output": result.mcp_tokens.output_tokens,
                            "total": result.mcp_tokens.total_tokens,
                        },
                        "memory_mb": result.mcp_performance.memory_mb,
                        "cpu_percent": result.mcp_performance.cpu_percent,
                    },
                    "direct": {
                        "results": len(result.direct_results) if result.direct_results else 0,
                        "latency_ms": result.direct_performance.duration_ms,
                        "tokens": {
                            "input": result.direct_tokens.input_tokens,
                            "output": result.direct_tokens.output_tokens,
                            "total": result.direct_tokens.total_tokens,
                        },
                        "memory_mb": result.direct_performance.memory_mb,
                        "cpu_percent": result.direct_performance.cpu_percent,
                    },
                    "quality": {
                        "precision": result.precision,
                        "recall": result.recall,
                        "f1_score": result.f1_score,
                    },
                }
            )

        # Calculate averages
        if mcp_latencies:
            report["summary"]["avg_mcp_latency_ms"] = sum(mcp_latencies) / len(mcp_latencies)
        if direct_latencies:
            report["summary"]["avg_direct_latency_ms"] = sum(direct_latencies) / len(
                direct_latencies
            )

        # Token cost estimates (using Voyage AI pricing as example)
        voyage_cost_per_million = 0.05  # $0.05 per 1M tokens
        report["summary"]["estimated_costs"] = {
            "mcp_cost_usd": (report["summary"]["total_mcp_tokens"] / 1_000_000)
            * voyage_cost_per_million,
            "direct_cost_usd": (report["summary"]["total_direct_tokens"] / 1_000_000)
            * voyage_cost_per_million,
            "note": "Cost estimates based on typical embedding API pricing",
        }

        # Print summary
        print("\n" + "=" * 60)
        print("COMPARISON SUMMARY")
        print("=" * 60)
        print(f"Total tests run: {report['summary']['total_tests']}")
        print("\nPerformance:")
        print(f"  Average MCP latency: {report['summary']['avg_mcp_latency_ms']:.2f}ms")
        print(f"  Average Direct latency: {report['summary']['avg_direct_latency_ms']:.2f}ms")
        if report["summary"]["avg_direct_latency_ms"] > 0:
            speedup = (
                report["summary"]["avg_direct_latency_ms"] / report["summary"]["avg_mcp_latency_ms"]
            )
            print(
                f"  Overall speedup: {speedup:.2f}x {'(MCP faster)' if speedup > 1 else '(Direct faster)'}"
            )

        print("\nToken Usage:")
        print(f"  Total MCP tokens: {report['summary']['total_mcp_tokens']:,}")
        print(f"  Total Direct tokens: {report['summary']['total_direct_tokens']:,}")
        if report["summary"]["total_direct_tokens"] > 0:
            ratio = report["summary"]["total_mcp_tokens"] / report["summary"]["total_direct_tokens"]
            print(f"  Token ratio: {ratio:.2f}x")

        print("\nEstimated Costs:")
        print(f"  MCP: ${report['summary']['estimated_costs']['mcp_cost_usd']:.4f}")
        print(f"  Direct: ${report['summary']['estimated_costs']['direct_cost_usd']:.4f}")

        print("\nWin/Loss:")
        print(f"  MCP faster: {report['summary']['mcp_wins']} times")
        print(f"  Direct faster: {report['summary']['direct_wins']} times")

        # Save report if requested
        if output_file:
            with open(output_file, "w") as f:
                json.dump(report, f, indent=2)
            print(f"\nDetailed report saved to: {output_file}")

        return report


def create_test_repository() -> Path:
    """Create a test repository with sample code."""
    test_dir = Path(tempfile.mkdtemp(prefix="mcp_comparison_test_"))

    # Create Python files
    (test_dir / "main.py").write_text(
        """
def calculate_sum(a: int, b: int) -> int:
    \"\"\"Calculate the sum of two numbers.\"\"\"
    return a + b

class Calculator:
    def __init__(self):
        self.history = []
    
    def add(self, a: float, b: float) -> float:
        result = a + b
        self.history.append(f"{a} + {b} = {result}")
        return result
    
    def multiply(self, a: float, b: float) -> float:
        result = a * b
        self.history.append(f"{a} * {b} = {result}")
        return result

async def fetch_data(url: str) -> dict:
    \"\"\"Fetch data from a URL asynchronously.\"\"\"
    # Simulated async operation
    return {"url": url, "data": "sample"}
"""
    )

    # Create JavaScript files
    (test_dir / "utils.js").write_text(
        """
function parseJSON(jsonString) {
    try {
        return JSON.parse(jsonString);
    } catch (error) {
        console.error('Failed to parse JSON:', error);
        return null;
    }
}

class DataProcessor {
    constructor() {
        this.cache = new Map();
    }
    
    process(data) {
        if (this.cache.has(data.id)) {
            return this.cache.get(data.id);
        }
        
        const result = this.transform(data);
        this.cache.set(data.id, result);
        return result;
    }
    
    transform(data) {
        return {
            ...data,
            processed: true,
            timestamp: Date.now()
        };
    }
}

module.exports = { parseJSON, DataProcessor };
"""
    )

    # Create Go file
    (test_dir / "server.go").write_text(
        """
package main

import (
    "fmt"
    "net/http"
)

func handleRequest(w http.ResponseWriter, r *http.Request) {
    fmt.Fprintf(w, "Hello, World!")
}

func authenticate(token string) bool {
    // Simple token validation
    return token == "valid-token"
}

type Server struct {
    port string
}

func (s *Server) Start() error {
    http.HandleFunc("/", handleRequest)
    return http.ListenAndServe(":"+s.port, nil)
}

func main() {
    server := &Server{port: "8080"}
    server.Start()
}
"""
    )

    return test_dir


def main():
    """Run the comparison tests."""
    print("MCP vs Direct Search Comparison Test")
    print("=" * 60)

    # Create test repository
    print("\nCreating test repository...")
    test_repo = create_test_repository()
    print(f"Test repository created at: {test_repo}")

    try:
        # Initialize comparison
        comparison = MCPComparison(test_repo)

        # Setup MCP
        comparison.setup_mcp()

        # Index the workspace
        comparison.index_workspace()

        # Define test queries
        test_queries = {
            "symbols": [
                "calculate_sum",
                "Calculator",
                "DataProcessor",
                "handleRequest",
                "Server",
                "fetch_data",
            ],
            "patterns": ["def .*\\(", "class .*:", "function.*\\{", "async", "return", "error"],
            "semantic": [
                "function that calculates sum of numbers",
                "class for processing data with caching",
                "asynchronous operation handler",
                "HTTP request handling logic",
            ],
        }

        # Run tests
        results = comparison.run_test_suite(test_queries)

        # Generate report
        report_file = Path("mcp_vs_direct_comparison_report.json")
        comparison.generate_report(report_file)

        print("\n" + "=" * 60)
        print("RECOMMENDATIONS")
        print("=" * 60)

        # Analyze results for recommendations
        avg_mcp_latency = sum(r.mcp_performance.duration_ms for r in results) / len(results)
        avg_direct_latency = sum(
            r.direct_performance.duration_ms
            for r in results
            if r.direct_performance.duration_ms > 0
        ) / max(1, len([r for r in results if r.direct_performance.duration_ms > 0]))

        print("\nWhen to use MCP Server:")
        print("✓ Complex codebases with many files (>1000)")
        print("✓ Need for semantic search capabilities")
        print("✓ Frequent repeated searches (benefits from caching)")
        print("✓ Multi-language projects requiring specialized parsing")
        print("✓ When result ranking and relevance matter")

        print("\nWhen to use Direct Search (grep/ripgrep):")
        print("✓ Small to medium codebases (<1000 files)")
        print("✓ Simple pattern matching is sufficient")
        print("✓ One-time searches without need for caching")
        print("✓ Minimal setup required")
        print("✓ When token usage costs are a concern")

        if avg_mcp_latency < avg_direct_latency * 0.5:
            print("\n🚀 MCP shows significant performance benefits in your tests!")
        elif avg_direct_latency < avg_mcp_latency * 0.5:
            print("\n⚡ Direct search is notably faster for your use case!")
        else:
            print("\n⚖️  Performance is comparable - choose based on features needed!")

    finally:
        # Cleanup
        if test_repo.exists():
            shutil.rmtree(test_repo)
            print("\nCleaned up test repository")


if __name__ == "__main__":
    main()
