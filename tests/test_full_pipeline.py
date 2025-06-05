#!/usr/bin/env python3
"""Test the full indexing and retrieval pipeline with real repositories."""

import os
import sys
import asyncio
import logging
import time
from pathlib import Path
from typing import Dict, List, Any
import json

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.plugin_system.plugin_manager import PluginManager
from mcp_server.dispatcher.dispatcher import Dispatcher
from mcp_server.indexer.index_engine import IndexEngine
from mcp_server.config.settings import Settings
from mcp_server.utils.semantic_indexer import SemanticIndexer
from mcp_server.watcher import FileWatcher

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PipelineTest:
    """Test the full indexing and retrieval pipeline."""
    
    def __init__(self, test_repos_dir: Path):
        self.test_repos_dir = test_repos_dir
        self.db_path = Path("test_index.db")
        self.settings = Settings()
        
        # Initialize components
        self.sqlite_store = SQLiteStore(str(self.db_path))
        self.plugin_manager = PluginManager(self.settings)
        self.dispatcher = Dispatcher(self.plugin_manager)
        
        # Initialize semantic indexer if available
        self.semantic_indexer = None
        if os.getenv("VOYAGE_API_KEY") and os.getenv("QDRANT_URL"):
            try:
                self.semantic_indexer = SemanticIndexer(
                    voyage_api_key=os.getenv("VOYAGE_API_KEY"),
                    qdrant_url=os.getenv("QDRANT_URL"),
                    collection_name="test_code_index"
                )
                logger.info("Semantic indexer initialized")
            except Exception as e:
                logger.warning(f"Could not initialize semantic indexer: {e}")
        
        self.index_engine = IndexEngine(
            dispatcher=self.dispatcher,
            sqlite_store=self.sqlite_store,
            semantic_indexer=self.semantic_indexer
        )
        
        self.file_watcher = FileWatcher(
            watch_paths=[str(test_repos_dir)],
            dispatcher=self.dispatcher
        )
    
    async def index_repositories(self) -> Dict[str, Any]:
        """Index all repositories in the test directory."""
        logger.info("Starting repository indexing...")
        start_time = time.time()
        
        stats = {
            "total_files": 0,
            "indexed_files": 0,
            "failed_files": 0,
            "by_language": {},
            "errors": []
        }
        
        # Start the file watcher
        await self.file_watcher.start()
        
        # Index each repository
        for repo_dir in self.test_repos_dir.iterdir():
            if not repo_dir.is_dir():
                continue
                
            logger.info(f"Indexing repository: {repo_dir.name}")
            
            # Walk through all files
            for file_path in repo_dir.rglob("*"):
                if not file_path.is_file():
                    continue
                    
                stats["total_files"] += 1
                
                try:
                    # Check if any plugin supports this file
                    plugin = self.plugin_manager.get_plugin_for_file(str(file_path))
                    if not plugin:
                        continue
                    
                    # Read file content
                    try:
                        content = file_path.read_text(encoding='utf-8')
                    except Exception:
                        # Skip binary files
                        continue
                    
                    # Index the file
                    result = await self.index_engine.index_file(str(file_path), content)
                    
                    if result:
                        stats["indexed_files"] += 1
                        language = result.get("language", "unknown")
                        stats["by_language"][language] = stats["by_language"].get(language, 0) + 1
                        
                        logger.debug(f"Indexed {file_path.name}: {len(result.get('symbols', []))} symbols")
                    
                except Exception as e:
                    stats["failed_files"] += 1
                    stats["errors"].append(f"{file_path}: {str(e)}")
                    logger.error(f"Failed to index {file_path}: {e}")
        
        # Stop the file watcher
        await self.file_watcher.stop()
        
        stats["indexing_time"] = time.time() - start_time
        logger.info(f"Indexing complete in {stats['indexing_time']:.2f}s")
        logger.info(f"Indexed {stats['indexed_files']}/{stats['total_files']} files")
        
        return stats
    
    async def test_search_queries(self) -> Dict[str, Any]:
        """Test various search queries."""
        logger.info("Testing search functionality...")
        
        test_queries = [
            # Language-specific queries
            ("Python function that handles requests", "python"),
            ("Java class with Spring annotations", "java"),
            ("Go function that returns error", "go"),
            ("JavaScript async function", "javascript"),
            ("Ruby method definition", "ruby"),
            ("PHP namespace declaration", "php"),
            
            # Cross-language queries
            ("main function", None),
            ("database connection", None),
            ("error handling", None),
            ("authentication", None),
            ("configuration", None),
            
            # Semantic queries (if available)
            ("code that validates user input", None),
            ("functions that process data", None),
            ("classes that handle HTTP requests", None),
        ]
        
        results = {}
        
        for query, language in test_queries:
            logger.info(f"Searching: '{query}'" + (f" (language: {language})" if language else ""))
            
            try:
                # Perform search
                search_results = await self.index_engine.search(
                    query=query,
                    language=language,
                    limit=5,
                    semantic=self.semantic_indexer is not None
                )
                
                results[query] = {
                    "count": len(search_results),
                    "results": []
                }
                
                for i, result in enumerate(search_results[:3]):  # Show top 3
                    results[query]["results"].append({
                        "file": Path(result["file"]).name,
                        "symbol": result.get("symbol", ""),
                        "score": result.get("score", 0),
                        "line": result.get("line", 0)
                    })
                    logger.info(f"  [{i+1}] {Path(result['file']).name}:{result.get('line', 0)} - {result.get('symbol', 'N/A')}")
                
            except Exception as e:
                logger.error(f"Search failed for '{query}': {e}")
                results[query] = {"error": str(e)}
        
        return results
    
    async def test_symbol_resolution(self) -> Dict[str, Any]:
        """Test symbol definition and reference finding."""
        logger.info("Testing symbol resolution...")
        
        # Test symbols from different languages
        test_symbols = [
            ("main", "go"),
            ("Application", "java"),
            ("app", "javascript"),
            ("Config", "ruby"),
            ("index", "php"),
        ]
        
        results = {}
        
        for symbol, hint_language in test_symbols:
            logger.info(f"Looking up symbol: {symbol}")
            
            try:
                # Get definition
                definition = await self.index_engine.get_definition(symbol)
                
                if definition:
                    results[symbol] = {
                        "found": True,
                        "file": Path(definition["defined_in"]).name,
                        "line": definition["line"],
                        "kind": definition["kind"],
                        "signature": definition.get("signature", "")[:100] + "..."
                    }
                    logger.info(f"  Found in {Path(definition['defined_in']).name}:{definition['line']} ({definition['kind']})")
                    
                    # Find references
                    references = await self.index_engine.find_references(symbol)
                    results[symbol]["references"] = len(references)
                    logger.info(f"  Found {len(references)} references")
                else:
                    results[symbol] = {"found": False}
                    logger.info(f"  Not found")
                    
            except Exception as e:
                logger.error(f"Symbol lookup failed for '{symbol}': {e}")
                results[symbol] = {"error": str(e)}
        
        return results
    
    def generate_report(self, index_stats: Dict, search_results: Dict, symbol_results: Dict):
        """Generate a comprehensive test report."""
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "indexing": index_stats,
            "search": search_results,
            "symbols": symbol_results,
            "configuration": {
                "semantic_search": self.semantic_indexer is not None,
                "repositories": [d.name for d in self.test_repos_dir.iterdir() if d.is_dir()]
            }
        }
        
        # Save report
        report_file = Path("test_report.json")
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Report saved to {report_file}")
        
        # Print summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        print(f"Indexed Files: {index_stats['indexed_files']}/{index_stats['total_files']}")
        print(f"Languages: {', '.join(f'{k}({v})' for k, v in index_stats['by_language'].items())}")
        print(f"Indexing Time: {index_stats['indexing_time']:.2f}s")
        print(f"Failed Files: {index_stats['failed_files']}")
        
        print("\nSearch Results:")
        successful_searches = sum(1 for r in search_results.values() if "count" in r and r["count"] > 0)
        print(f"  Successful: {successful_searches}/{len(search_results)}")
        
        print("\nSymbol Resolution:")
        found_symbols = sum(1 for r in symbol_results.values() if r.get("found", False))
        print(f"  Found: {found_symbols}/{len(symbol_results)}")
        
        if self.semantic_indexer:
            print("\n✓ Semantic search enabled (Voyage AI + Qdrant)")
        else:
            print("\n✗ Semantic search disabled (set VOYAGE_API_KEY and QDRANT_URL)")
        
        print("="*60)
    
    async def cleanup(self):
        """Clean up resources."""
        if self.db_path.exists():
            self.db_path.unlink()
        
        if self.semantic_indexer:
            # Clean up vector collection
            try:
                await self.semantic_indexer.clear_collection()
            except:
                pass

async def main():
    """Run the full pipeline test."""
    test_repos_dir = Path("test_repos")
    
    if not test_repos_dir.exists():
        logger.error("Test repositories not found. Run download_simple_repos.py first.")
        return
    
    pipeline = PipelineTest(test_repos_dir)
    
    try:
        # Run tests
        index_stats = await pipeline.index_repositories()
        search_results = await pipeline.test_search_queries()
        symbol_results = await pipeline.test_symbol_resolution()
        
        # Generate report
        pipeline.generate_report(index_stats, search_results, symbol_results)
        
    finally:
        await pipeline.cleanup()

if __name__ == "__main__":
    asyncio.run(main())