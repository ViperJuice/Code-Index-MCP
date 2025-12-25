import asyncio
import json
import subprocess
import time
import os
import shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from unittest.mock import MagicMock
import sys

# Mocks for missing deps if needed (though we use uv run now, so real deps might be there)
# But tree-sitter bindings might still be an issue if not installed system-wide
# We'll try to rely on the environment, but fallback to mocks if import fails
try:
    import tree_sitter
except ImportError:
    sys.modules["tree_sitter"] = MagicMock()
    sys.modules["tree_sitter_languages"] = MagicMock()
    # Mock wrappers if needed
    class MockTreeSitterWrapper:
        def __init__(self):
            pass
        def parse(self, content):
            mock = MagicMock()
            mock.children = []
            mock.root_node.named_children = []
            return mock
            
    sys.modules["mcp_server.utils.treesitter_wrapper"] = MagicMock()
    sys.modules["mcp_server.utils.treesitter_wrapper"].TreeSitterWrapper = MockTreeSitterWrapper

# Add project root to sys.path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.dispatcher import Dispatcher # EnhancedDispatcher
from mcp_server.plugins.python_plugin.plugin import Plugin as PythonPlugin
from mcp_server.utils.semantic_indexer import SemanticIndexer

class CurrentBenchmark:
    def __init__(self, workspace_path: str = "."):
        self.workspace_path = Path(workspace_path).resolve()
        self.results = defaultdict(list)
        self.store = None
        self.dispatcher = None
        self.plugins = []
        self.semantic_indexer = None

    def setup_mcp(self):
        print("Setting up MCP components...")
        start_time = time.time()

        # Database
        db_path = "benchmark.db"
        if os.path.exists(db_path):
            os.remove(db_path)
        self.store = SQLiteStore(db_path)

        # Plugins
        # We manually load PythonPlugin for this benchmark
        py_plugin = PythonPlugin(sqlite_store=self.store)
        self.plugins = [py_plugin]

        # Semantic Indexer (Memory)
        enable_semantic = os.environ.get("BENCHMARK_ENABLE_SEMANTIC", "true").lower() == "true"
        if enable_semantic and os.environ.get("VOYAGE_AI_API_KEY"):
            try:
                self.semantic_indexer = SemanticIndexer(qdrant_path=":memory:")
                print("  Semantic Indexer initialized.")
            except Exception as e:
                print(f"  Semantic Indexer init failed: {e}")

        # Dispatcher
        self.dispatcher = Dispatcher(self.plugins)
        
        # Inject semantic indexer into dispatcher logic if needed, 
        # but EnhancedDispatcher usually takes a list of plugins.
        # Ideally we'd use HybridSearch, but Dispatcher has .search().
        
        setup_time = time.time() - start_time
        print(f"MCP setup completed in {setup_time:.2f}s")

    def build_index(self):
        print(f"Building index for workspace: {self.workspace_path}")
        start_time = time.time()
        count = 0
        
        # Simple indexing loop
        for file_path in self.workspace_path.rglob("*.py"):
            if "venv" in file_path.parts or ".venv" in file_path.parts or "__pycache__" in file_path.parts:
                continue
                
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                abs_path = file_path.resolve()
                
                # 1. SQLite FTS
                self.plugins[0].indexFile(abs_path, content)
                
                # 2. Semantic
                if self.semantic_indexer:
                    self.semantic_indexer.index_file(abs_path)
                    
                count += 1
            except Exception:
                pass
                
        index_time = time.time() - start_time
        print(f"Indexed {count} files in {index_time:.2f}s")
        self.results["indexing"] = {"count": count, "time": index_time}

    def run_grep(self, pattern: str) -> Tuple[int, float]:
        start = time.time()
        try:
            cmd = ["grep", "-r", "-l", pattern, str(self.workspace_path), "--include=*.py"]
            res = subprocess.run(cmd, capture_output=True, text=True)
            count = len(res.stdout.strip().splitlines()) if res.stdout else 0
        except Exception:
            count = 0
        return count, time.time() - start

    def run_ripgrep(self, pattern: str) -> Tuple[int, float]:
        start = time.time()
        try:
            # -l for filenames only
            cmd = ["rg", "-l", "-g", "*.py", pattern, str(self.workspace_path)]
            res = subprocess.run(cmd, capture_output=True, text=True)
            count = len(res.stdout.strip().splitlines()) if res.stdout else 0
        except FileNotFoundError:
            return -1, 0
        return count, time.time() - start

    def run_mcp_search(self, query: str) -> Tuple[int, float]:
        start = time.time()
        # Dispatcher.search returns generator
        results = list(self.dispatcher.search(query, limit=100))
        return len(results), time.time() - start

    def run_mcp_semantic(self, query: str) -> Tuple[int, float]:
        if not self.semantic_indexer:
            return 0, 0
        start = time.time()
        results = self.semantic_indexer.search(query, limit=100)
        return len(results), time.time() - start

    def benchmark(self):
        queries = ["def __init__", "class ", "import ", "TODO"]
        
        print("\n=== Search Benchmarks ===")
        print(f"{'Query':<20} | {'Tool':<10} | {'Count':<5} | {'Time (s)':<10}")
        print("-" * 55)
        
        for q in queries:
            # Grep
            g_count, g_time = self.run_grep(q)
            print(f"{q:<20} | {'grep':<10} | {g_count:<5} | {g_time:.4f}")
            
            # Ripgrep
            r_count, r_time = self.run_ripgrep(q)
            if r_count != -1:
                print(f"{q:<20} | {'ripgrep':<10} | {r_count:<5} | {r_time:.4f}")
            
            # MCP FTS
            m_count, m_time = self.run_mcp_search(q)
            print(f"{q:<20} | {'MCP (FTS)':<10} | {m_count:<5} | {m_time:.4f}")
            
            # MCP Semantic (Intent)
            # Use same query for comparison, though semantic is meant for intent
            if self.semantic_indexer:
                s_count, s_time = self.run_mcp_semantic(q)
                print(f"{q:<20} | {'MCP (Sem)':<10} | {s_count:<5} | {s_time:.4f}")
            
            print("-" * 55)

if __name__ == "__main__":
    # Ensure VOYAGE key is loaded if present and semantic is enabled
    enable_semantic = os.environ.get("BENCHMARK_ENABLE_SEMANTIC", "true").lower() == "true"
    env_path = Path(".env")
    if enable_semantic and env_path.exists() and not os.environ.get("VOYAGE_AI_API_KEY"):
        with open(env_path) as f:
            for line in f:
                if line.startswith("VOYAGE_AI_API_KEY="):
                    os.environ["VOYAGE_AI_API_KEY"] = line.split("=", 1)[1].strip()
                    break

    bm = CurrentBenchmark(".")
    bm.setup_mcp()
    bm.build_index()
    bm.benchmark()
    
    # Cleanup
    if os.path.exists("benchmark.db"):
        os.remove("benchmark.db")
