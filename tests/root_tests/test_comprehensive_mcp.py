#!/usr/bin/env python3
"""
Comprehensive MCP Server Testing with Small Repositories
Tests all 7 specialized language plugins with efficient database management.
"""

import asyncio
import hashlib
import json
import logging
import os
import shutil
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Test repositories - small, focused codebases
SMALL_TEST_REPOSITORIES = {
    "python": {
        "name": "click",
        "url": "https://github.com/pallets/click.git",
        "description": "Python CLI framework",
        "expected_files": 30,
        "test_files": ["src/click/core.py", "src/click/decorators.py"],
        "key_symbols": ["Command", "Group", "option", "argument"],
    },
    "javascript": {
        "name": "axios",
        "url": "https://github.com/axios/axios.git",
        "description": "HTTP client library",
        "expected_files": 50,
        "test_files": ["lib/axios.js", "lib/core/Axios.js"],
        "key_symbols": ["axios", "request", "response", "interceptors"],
    },
    "typescript": {
        "name": "zod",
        "url": "https://github.com/colinhacks/zod.git",
        "description": "TypeScript schema validation",
        "expected_files": 40,
        "test_files": ["src/index.ts", "src/types.ts"],
        "key_symbols": ["ZodSchema", "ZodType", "parse", "safeParse"],
    },
    "java": {
        "name": "gson",
        "url": "https://github.com/google/gson.git",
        "description": "JSON library for Java",
        "expected_files": 80,
        "test_files": ["gson/src/main/java/com/google/gson/Gson.java"],
        "key_symbols": ["Gson", "JsonElement", "fromJson", "toJson"],
    },
    "go": {
        "name": "gin",
        "url": "https://github.com/gin-gonic/gin.git",
        "description": "Go web framework",
        "expected_files": 100,
        "test_files": ["gin.go", "context.go"],
        "key_symbols": ["Engine", "Context", "HandlerFunc", "RouterGroup"],
    },
    "rust": {
        "name": "serde",
        "url": "https://github.com/serde-rs/serde.git",
        "description": "Rust serialization framework",
        "expected_files": 120,
        "test_files": ["serde/src/lib.rs", "serde/src/ser.rs"],
        "key_symbols": ["Serialize", "Deserialize", "Serializer", "Deserializer"],
    },
    "csharp": {
        "name": "newtonsoft-json",
        "url": "https://github.com/JamesNK/Newtonsoft.Json.git",
        "description": "JSON framework for .NET",
        "expected_files": 200,
        "test_files": ["Src/Newtonsoft.Json/JsonConvert.cs"],
        "key_symbols": ["JsonConvert", "JsonSerializer", "SerializeObject", "DeserializeObject"],
    },
    "swift": {
        "name": "alamofire",
        "url": "https://github.com/Alamofire/Alamofire.git",
        "description": "Swift HTTP networking library",
        "expected_files": 60,
        "test_files": ["Source/Alamofire.swift", "Source/Session.swift"],
        "key_symbols": ["Session", "Request", "Response", "DataRequest"],
    },
    "kotlin": {
        "name": "kotlinx-coroutines",
        "url": "https://github.com/Kotlin/kotlinx.coroutines.git",
        "description": "Kotlin coroutines library",
        "expected_files": 300,
        "test_files": ["kotlinx-coroutines-core/common/src/Deferred.kt"],
        "key_symbols": ["Deferred", "CoroutineScope", "suspend", "async"],
    },
}


class MCPTestOrchestrator:
    """Comprehensive MCP server testing orchestrator."""

    def __init__(self, workspace_dir: str = "test_workspace_mcp"):
        self.workspace_dir = Path(workspace_dir)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)

        self.repos_dir = self.workspace_dir / "repositories"
        self.results_dir = self.workspace_dir / "results"
        self.temp_dir = self.workspace_dir / "temp"

        for d in [self.repos_dir, self.results_dir, self.temp_dir]:
            d.mkdir(exist_ok=True)

        self.test_session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.test_results = {
            "session_id": self.test_session_id,
            "start_time": datetime.now().isoformat(),
            "repositories": {},
            "plugins_tested": {},
            "overall_stats": {},
            "performance_metrics": {},
            "errors": [],
        }

    def download_repository(self, language: str, config: Dict) -> bool:
        """Download a small test repository."""
        repo_path = self.repos_dir / language / config["name"]

        if repo_path.exists():
            logger.info(f"Repository {config['name']} already exists, skipping download")
            return True

        repo_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Downloading {config['name']} for {language} testing...")

        try:
            # Clone with depth=1 for faster download
            cmd = ["git", "clone", "--depth=1", config["url"], str(repo_path)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

            if result.returncode == 0:
                # Count actual files
                file_count = self._count_source_files(repo_path, language)
                logger.info(f"✅ Downloaded {config['name']} ({file_count} files)")

                # Store repository info
                self.test_results["repositories"][language] = {
                    "name": config["name"],
                    "description": config["description"],
                    "file_count": file_count,
                    "download_success": True,
                    "test_files": config["test_files"],
                    "key_symbols": config["key_symbols"],
                }
                return True
            else:
                logger.error(f"❌ Failed to download {config['name']}: {result.stderr}")
                self.test_results["errors"].append(
                    {"stage": "download", "language": language, "error": result.stderr}
                )
                return False

        except Exception as e:
            logger.error(f"❌ Error downloading {config['name']}: {e}")
            self.test_results["errors"].append(
                {"stage": "download", "language": language, "error": str(e)}
            )
            return False

    def _count_source_files(self, repo_path: Path, language: str) -> int:
        """Count source files for the given language."""
        extensions = {
            "python": [".py"],
            "javascript": [".js", ".mjs"],
            "typescript": [".ts", ".tsx"],
            "java": [".java"],
            "go": [".go"],
            "rust": [".rs"],
            "csharp": [".cs"],
            "swift": [".swift"],
            "kotlin": [".kt"],
        }

        count = 0
        for ext in extensions.get(language, []):
            count += len(list(repo_path.rglob(f"*{ext}")))
        return count

    async def test_mcp_server_integration(self) -> Dict[str, Any]:
        """Test full MCP server integration with all plugins."""
        logger.info("Testing MCP server integration...")

        try:
            # Import MCP components
            from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
            from mcp_server.plugin_system import PluginManager
            from mcp_server.storage.sqlite_store import SQLiteStore

            # Create temporary database
            db_path = self.temp_dir / f"test_mcp_{self.test_session_id}.db"
            sqlite_store = SQLiteStore(str(db_path))

            # Initialize plugin manager
            plugin_manager = PluginManager(sqlite_store=sqlite_store)
            load_result = plugin_manager.load_plugins_safe()

            if not load_result.success:
                raise Exception(f"Plugin loading failed: {load_result.error}")

            # Create enhanced dispatcher
            active_plugins = plugin_manager.get_active_plugins()
            dispatcher = EnhancedDispatcher(
                plugins=list(active_plugins.values()),
                sqlite_store=sqlite_store,
                enable_advanced_features=True,
                use_plugin_factory=True,
                lazy_load=True,
                semantic_search_enabled=False,  # Disable to avoid token usage
            )

            # Test dispatcher capabilities
            stats = dispatcher.get_statistics() if hasattr(dispatcher, "get_statistics") else {}
            health = dispatcher.health_check() if hasattr(dispatcher, "health_check") else {}

            integration_results = {
                "mcp_server_startup": True,
                "plugin_manager_loaded": load_result.success,
                "enhanced_dispatcher_created": True,
                "supported_languages": len(dispatcher.supported_languages),
                "language_list": sorted(dispatcher.supported_languages),
                "statistics": stats,
                "health_check": health,
                "database_path": str(db_path),
                "database_size_mb": db_path.stat().st_size / 1024 / 1024 if db_path.exists() else 0,
            }

            # Clean up database
            if db_path.exists():
                db_path.unlink()

            return integration_results

        except Exception as e:
            logger.error(f"MCP server integration test failed: {e}")
            return {"mcp_server_startup": False, "error": str(e)}

    async def test_language_plugin(self, language: str, repo_config: Dict) -> Dict[str, Any]:
        """Test a specific language plugin with its repository."""
        logger.info(f"Testing {language} plugin...")

        repo_path = self.repos_dir / language / repo_config["name"]
        if not repo_path.exists():
            return {"error": f"Repository not found: {repo_path}"}

        try:
            # Import required modules
            from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
            from mcp_server.storage.sqlite_store import SQLiteStore

            # Create temporary database for this test
            db_path = self.temp_dir / f"test_{language}_{self.test_session_id}.db"
            sqlite_store = SQLiteStore(str(db_path))

            # Create dispatcher with plugin factory
            dispatcher = EnhancedDispatcher(
                plugins=[],  # Start empty, let factory load
                sqlite_store=sqlite_store,
                enable_advanced_features=True,
                use_plugin_factory=True,
                lazy_load=True,
                semantic_search_enabled=False,
            )

            test_results = {
                "language": language,
                "repository": repo_config["name"],
                "plugin_loaded": False,
                "files_indexed": 0,
                "symbols_found": 0,
                "test_files_processed": [],
                "symbol_lookup_tests": [],
                "search_tests": [],
                "reference_tests": [],
                "advanced_features": {},
                "performance": {},
                "errors": [],
            }

            start_time = time.time()

            # Test file indexing
            indexed_files = 0
            total_symbols = 0

            for test_file_rel in repo_config.get("test_files", []):
                test_file_path = repo_path / test_file_rel
                if test_file_path.exists():
                    try:
                        # Index the file
                        result = dispatcher.index_file(test_file_path)
                        if result:
                            indexed_files += 1
                            file_symbols = len(result.get("symbols", []))
                            total_symbols += file_symbols

                            test_results["test_files_processed"].append(
                                {"file": test_file_rel, "symbols": file_symbols, "success": True}
                            )
                        else:
                            test_results["errors"].append(f"Failed to index {test_file_rel}")

                    except Exception as e:
                        test_results["errors"].append(f"Error indexing {test_file_rel}: {str(e)}")
                else:
                    test_results["errors"].append(f"Test file not found: {test_file_rel}")

            test_results["files_indexed"] = indexed_files
            test_results["symbols_found"] = total_symbols
            test_results["plugin_loaded"] = indexed_files > 0

            # Test symbol lookup
            for symbol in repo_config.get("key_symbols", [])[:3]:  # Test first 3 symbols
                try:
                    lookup_result = dispatcher.lookup(symbol)
                    test_results["symbol_lookup_tests"].append(
                        {
                            "symbol": symbol,
                            "found": lookup_result is not None,
                            "result": lookup_result,
                        }
                    )
                except Exception as e:
                    test_results["symbol_lookup_tests"].append(
                        {"symbol": symbol, "found": False, "error": str(e)}
                    )

            # Test search functionality
            search_queries = [language, "function", "class"]
            for query in search_queries:
                try:
                    search_results = list(dispatcher.search(query, semantic=False, limit=5))
                    test_results["search_tests"].append(
                        {"query": query, "results_count": len(search_results), "success": True}
                    )
                except Exception as e:
                    test_results["search_tests"].append(
                        {"query": query, "results_count": 0, "success": False, "error": str(e)}
                    )

            # Performance metrics
            end_time = time.time()
            test_results["performance"] = {
                "total_time_seconds": round(end_time - start_time, 3),
                "indexing_speed_files_per_sec": (
                    round(indexed_files / (end_time - start_time), 2)
                    if end_time > start_time
                    else 0
                ),
                "symbols_per_second": (
                    round(total_symbols / (end_time - start_time), 2)
                    if end_time > start_time
                    else 0
                ),
            }

            # Clean up database
            if db_path.exists():
                db_size = db_path.stat().st_size
                test_results["performance"]["database_size_bytes"] = db_size
                db_path.unlink()

            return test_results

        except Exception as e:
            logger.error(f"Error testing {language} plugin: {e}")
            return {"language": language, "error": str(e), "plugin_loaded": False}

    async def run_comprehensive_tests(self) -> Dict[str, Any]:
        """Run all tests in sequence."""
        logger.info(f"Starting comprehensive MCP testing session: {self.test_session_id}")

        # Phase 1: Download repositories
        logger.info("Phase 1: Downloading test repositories...")
        download_results = {}
        for language, config in SMALL_TEST_REPOSITORIES.items():
            download_results[language] = self.download_repository(language, config)

        successful_downloads = sum(1 for success in download_results.values() if success)
        logger.info(
            f"Downloaded {successful_downloads}/{len(SMALL_TEST_REPOSITORIES)} repositories"
        )

        # Phase 2: Test MCP server integration
        logger.info("Phase 2: Testing MCP server integration...")
        integration_results = await self.test_mcp_server_integration()
        self.test_results["mcp_integration"] = integration_results

        # Phase 3: Test individual language plugins
        logger.info("Phase 3: Testing individual language plugins...")
        for language, config in SMALL_TEST_REPOSITORIES.items():
            if download_results.get(language, False):
                plugin_results = await self.test_language_plugin(language, config)
                self.test_results["plugins_tested"][language] = plugin_results
            else:
                logger.warning(f"Skipping {language} plugin test - repository download failed")

        # Phase 4: Calculate overall statistics
        self._calculate_overall_stats()

        # Phase 5: Save results
        self._save_results()

        self.test_results["end_time"] = datetime.now().isoformat()
        return self.test_results

    def _calculate_overall_stats(self):
        """Calculate overall test statistics."""
        plugins_tested = self.test_results["plugins_tested"]

        total_plugins = len(plugins_tested)
        successful_plugins = sum(
            1 for p in plugins_tested.values() if p.get("plugin_loaded", False)
        )
        total_files = sum(p.get("files_indexed", 0) for p in plugins_tested.values())
        total_symbols = sum(p.get("symbols_found", 0) for p in plugins_tested.values())

        successful_lookups = 0
        total_lookups = 0
        for p in plugins_tested.values():
            for lookup in p.get("symbol_lookup_tests", []):
                total_lookups += 1
                if lookup.get("found", False):
                    successful_lookups += 1

        successful_searches = 0
        total_searches = 0
        for p in plugins_tested.values():
            for search in p.get("search_tests", []):
                total_searches += 1
                if search.get("success", False):
                    successful_searches += 1

        self.test_results["overall_stats"] = {
            "total_languages": total_plugins,
            "successful_plugins": successful_plugins,
            "plugin_success_rate": (
                round(successful_plugins / total_plugins * 100, 1) if total_plugins > 0 else 0
            ),
            "total_files_indexed": total_files,
            "total_symbols_extracted": total_symbols,
            "symbol_lookup_success_rate": (
                round(successful_lookups / total_lookups * 100, 1) if total_lookups > 0 else 0
            ),
            "search_success_rate": (
                round(successful_searches / total_searches * 100, 1) if total_searches > 0 else 0
            ),
        }

    def _save_results(self):
        """Save test results to JSON file."""
        results_file = self.results_dir / f"mcp_test_results_{self.test_session_id}.json"

        with open(results_file, "w") as f:
            json.dump(self.test_results, f, indent=2, default=str)

        logger.info(f"Test results saved to: {results_file}")

        # Also save a summary file
        summary_file = self.results_dir / "latest_test_summary.json"
        summary = {
            "session_id": self.test_session_id,
            "timestamp": self.test_results.get("start_time"),
            "overall_stats": self.test_results.get("overall_stats", {}),
            "languages_tested": list(self.test_results.get("plugins_tested", {}).keys()),
            "mcp_integration_success": self.test_results.get("mcp_integration", {}).get(
                "mcp_server_startup", False
            ),
        }

        with open(summary_file, "w") as f:
            json.dump(summary, f, indent=2)

        logger.info(f"Test summary saved to: {summary_file}")

    def cleanup_temp_files(self):
        """Clean up temporary files and databases."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            logger.info("Cleaned up temporary files")

    def print_results_summary(self):
        """Print a formatted summary of test results."""
        stats = self.test_results.get("overall_stats", {})

        print(f"\n{'='*60}")
        print(f"MCP COMPREHENSIVE TEST RESULTS - {self.test_session_id}")
        print(f"{'='*60}")

        print(f"\n📊 OVERALL STATISTICS:")
        print(f"   Languages Tested: {stats.get('total_languages', 0)}")
        print(f"   Successful Plugins: {stats.get('successful_plugins', 0)}")
        print(f"   Plugin Success Rate: {stats.get('plugin_success_rate', 0)}%")
        print(f"   Files Indexed: {stats.get('total_files_indexed', 0)}")
        print(f"   Symbols Extracted: {stats.get('total_symbols_extracted', 0)}")
        print(f"   Symbol Lookup Success: {stats.get('symbol_lookup_success_rate', 0)}%")
        print(f"   Search Success Rate: {stats.get('search_success_rate', 0)}%")

        print(f"\n🔌 PLUGIN RESULTS:")
        for language, results in self.test_results.get("plugins_tested", {}).items():
            status = "✅" if results.get("plugin_loaded", False) else "❌"
            symbols = results.get("symbols_found", 0)
            files = results.get("files_indexed", 0)
            print(f"   {status} {language:12s} | {files:2d} files | {symbols:3d} symbols")

        if self.test_results.get("errors"):
            print(f"\n⚠️  ERRORS ({len(self.test_results['errors'])}):")
            for error in self.test_results["errors"][:5]:  # Show first 5 errors
                print(
                    f"   - {error.get('stage', 'unknown')}: {error.get('error', 'Unknown error')[:60]}..."
                )


async def main():
    """Main test execution."""
    orchestrator = MCPTestOrchestrator()

    try:
        # Run comprehensive tests
        results = await orchestrator.run_comprehensive_tests()

        # Print summary
        orchestrator.print_results_summary()

        # Cleanup
        orchestrator.cleanup_temp_files()

        # Return success/failure based on results
        stats = results.get("overall_stats", {})
        success_rate = stats.get("plugin_success_rate", 0)

        if success_rate >= 80:
            print(f"\n🎉 TESTING COMPLETED SUCCESSFULLY!")
            print(f"   Results saved in: {orchestrator.results_dir}")
            return 0
        else:
            print(f"\n⚠️  TESTING COMPLETED WITH ISSUES")
            print(f"   Plugin success rate: {success_rate}% (target: 80%+)")
            return 1

    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        orchestrator.cleanup_temp_files()
        return 1


if __name__ == "__main__":
    import sys

    exit_code = asyncio.run(main())
    sys.exit(exit_code)
