#!/usr/bin/env python3
"""
MCP Client Wrapper for accurate performance testing.

This module provides a wrapper around the actual MCP server functionality
to enable real performance comparisons instead of simulations.
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, Tuple

import httpx

from ..dispatcher.dispatcher import Dispatcher
from ..indexer.bm25_indexer import BM25Indexer
from ..indexer.hybrid_search import HybridSearch, HybridSearchConfig
from ..plugin_system import PluginManager
from ..storage.sqlite_store import SQLiteStore


class MCPClientWrapper:
    """Wrapper for MCP server functionality with token tracking."""

    def __init__(self, index_path: str = ".mcp-index/code_index.db"):
        """Initialize MCP client with actual server components."""
        self.index_path = Path(index_path)
        self.storage = None
        self.bm25_indexer = None
        self.hybrid_search = None
        self.dispatcher = None

        # Token tracking
        self.last_input_tokens = 0
        self.last_output_tokens = 0

        # Initialize components
        self._initialize_components()

    def _initialize_components(self):
        """Initialize actual MCP server components."""
        try:
            # Initialize storage
            self.storage = SQLiteStore(str(self.index_path))

            # Initialize BM25 indexer
            self.bm25_indexer = BM25Indexer(self.storage)

            # Initialize hybrid search
            config = HybridSearchConfig(
                enable_bm25=True,
                enable_semantic=False,  # Disable for now to focus on BM25
                enable_fuzzy=False,
                individual_limit=50,
                final_limit=20,
            )
            self.hybrid_search = HybridSearch(
                self.storage, bm25_indexer=self.bm25_indexer, config=config
            )

            # Initialize plugin manager and dispatcher
            plugin_manager = PluginManager()
            plugins = plugin_manager.load_all_plugins()
            self.dispatcher = Dispatcher(plugins)

        except Exception as e:
            print(f"Warning: Could not initialize MCP components: {e}")
            print("Falling back to HTTP client mode")

    def _count_tokens(self, text: str) -> int:
        """Estimate token count (roughly 4 chars = 1 token)."""
        return len(text) // 4

    def symbol_lookup(self, symbol: str) -> Dict[str, Any]:
        """
        Perform actual symbol lookup using MCP indexes.

        Returns dict with:
        - results: List of symbol definitions
        - elapsed_time: Time taken
        - input_tokens: Tokens in query
        - output_tokens: Tokens in response
        - total_tokens: Total token count
        """
        start_time = time.time()

        # Track input tokens
        query = f"symbol:{symbol}"
        self.last_input_tokens = self._count_tokens(query)

        try:
            # Use dispatcher for symbol lookup
            if self.dispatcher:
                symbol_def = self.dispatcher.lookup(symbol)

                if symbol_def:
                    results = [
                        {
                            "symbol": symbol,
                            "file": symbol_def.location.file,
                            "line": symbol_def.location.line,
                            "kind": symbol_def.symbol_type,
                            "signature": getattr(symbol_def, "signature", ""),
                            "documentation": getattr(symbol_def, "documentation", ""),
                        }
                    ]
                else:
                    results = []
            else:
                # Fallback to BM25 search
                search_results = self.bm25_indexer.search(symbol, limit=10, search_type="symbols")
                results = [
                    {
                        "symbol": r.get("name", symbol),
                        "file": r["filepath"],
                        "line": r.get("line", 1),
                        "kind": r.get("kind", "unknown"),
                        "signature": r.get("signature", ""),
                        "documentation": r.get("documentation", ""),
                    }
                    for r in search_results
                ]

        except Exception as e:
            print(f"Error in symbol lookup: {e}")
            results = []

        elapsed_time = time.time() - start_time

        # Create response and count output tokens
        response = {
            "query": query,
            "results": results,
            "total_matches": len(results),
            "search_time_ms": int(elapsed_time * 1000),
        }

        response_text = json.dumps(response, indent=2)
        self.last_output_tokens = self._count_tokens(response_text)

        return {
            "results": results,
            "elapsed_time": elapsed_time,
            "input_tokens": self.last_input_tokens,
            "output_tokens": self.last_output_tokens,
            "total_tokens": self.last_input_tokens + self.last_output_tokens,
            "response_json": response,
        }

    def search_code(self, pattern: str, semantic: bool = False) -> Dict[str, Any]:
        """
        Perform code search using MCP indexes.

        Returns dict with token breakdown and results.
        """
        start_time = time.time()

        # Track input tokens
        query = f"pattern:{pattern}" if not semantic else f"semantic:{pattern}"
        self.last_input_tokens = self._count_tokens(query)

        try:
            if self.bm25_indexer and not semantic:
                # Use BM25 for pattern search
                search_results = self.bm25_indexer.search(pattern, limit=20, search_type="content")

                results = [
                    {
                        "file": r["filepath"],
                        "line": r.get("line", 1),
                        "snippet": r.get("snippet", ""),
                        "score": r.get("score", 0),
                        "language": r.get("language", ""),
                    }
                    for r in search_results
                ]
            else:
                # Use dispatcher search
                search_results = list(self.dispatcher.search(pattern, semantic=semantic, limit=20))
                results = [
                    {
                        "file": r.file,
                        "line": r.line,
                        "snippet": r.snippet,
                        "score": getattr(r, "score", 0),
                        "language": getattr(r, "language", ""),
                    }
                    for r in search_results
                ]

        except Exception as e:
            print(f"Error in code search: {e}")
            results = []

        elapsed_time = time.time() - start_time

        # Create response and count output tokens
        response = {
            "query": query,
            "pattern": pattern,
            "semantic": semantic,
            "results": results[:20],  # Limit to 20 results
            "total_matches": len(results),
            "search_time_ms": int(elapsed_time * 1000),
        }

        response_text = json.dumps(response, indent=2)
        self.last_output_tokens = self._count_tokens(response_text)

        return {
            "results": results,
            "elapsed_time": elapsed_time,
            "input_tokens": self.last_input_tokens,
            "output_tokens": self.last_output_tokens,
            "total_tokens": self.last_input_tokens + self.last_output_tokens,
            "response_json": response,
        }

    async def search_code_async(self, pattern: str, semantic: bool = False) -> Dict[str, Any]:
        """Async version of search_code for hybrid search."""
        start_time = time.time()

        query = f"pattern:{pattern}" if not semantic else f"semantic:{pattern}"
        self.last_input_tokens = self._count_tokens(query)

        try:
            if self.hybrid_search:
                # Use hybrid search
                results = await self.hybrid_search.search(pattern, limit=20)

                # Convert to our format
                formatted_results = [
                    {
                        "file": r["filepath"],
                        "line": r.get("line", 1),
                        "snippet": r.get("snippet", ""),
                        "score": r.get("score", 0),
                        "source": r.get("source", "unknown"),
                    }
                    for r in results
                ]
            else:
                # Fall back to sync search
                sync_result = self.search_code(pattern, semantic)
                return sync_result

        except Exception as e:
            print(f"Error in async search: {e}")
            formatted_results = []

        elapsed_time = time.time() - start_time

        # Create response
        response = {
            "query": query,
            "pattern": pattern,
            "semantic": semantic,
            "results": formatted_results[:20],
            "total_matches": len(formatted_results),
            "search_time_ms": int(elapsed_time * 1000),
        }

        response_text = json.dumps(response, indent=2)
        self.last_output_tokens = self._count_tokens(response_text)

        return {
            "results": formatted_results,
            "elapsed_time": elapsed_time,
            "input_tokens": self.last_input_tokens,
            "output_tokens": self.last_output_tokens,
            "total_tokens": self.last_input_tokens + self.last_output_tokens,
            "response_json": response,
        }

    def get_file_content(self, filepath: str) -> Tuple[str, int]:
        """
        Get file content and count tokens.
        Used for direct search comparison.
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            tokens = self._count_tokens(content)
            return content, tokens
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
            return "", 0

    def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the MCP index."""
        try:
            if self.bm25_indexer:
                stats = self.bm25_indexer.get_statistics()
                return stats
            else:
                return {"error": "BM25 indexer not initialized"}
        except Exception as e:
            return {"error": str(e)}


class MCPHTTPClient:
    """HTTP client for MCP server when direct access isn't available."""

    def __init__(self, base_url: str = "http://localhost:8765"):
        self.base_url = base_url
        self.client = httpx.Client()

    def _count_tokens(self, text: str) -> int:
        """Estimate token count."""
        return len(text) // 4

    async def symbol_lookup(self, symbol: str) -> Dict[str, Any]:
        """Lookup symbol via HTTP API."""
        start_time = time.time()

        query = f"symbol:{symbol}"
        input_tokens = self._count_tokens(query)

        try:
            response = self.client.get(f"{self.base_url}/lookup/{symbol}")
            response.raise_for_status()

            data = response.json()
            elapsed_time = time.time() - start_time

            response_text = json.dumps(data, indent=2)
            output_tokens = self._count_tokens(response_text)

            return {
                "results": data.get("results", []),
                "elapsed_time": elapsed_time,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "response_json": data,
            }

        except Exception as e:
            print(f"HTTP error: {e}")
            return {
                "results": [],
                "elapsed_time": time.time() - start_time,
                "input_tokens": input_tokens,
                "output_tokens": 0,
                "total_tokens": input_tokens,
                "response_json": {"error": str(e)},
            }
