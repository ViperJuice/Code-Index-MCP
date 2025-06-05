#!/usr/bin/env python3
"""Simple test of indexing and retrieval functionality."""

import sys
from pathlib import Path
import logging
import time
import json

sys.path.insert(0, str(Path(__file__).parent))

from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.plugin_system.plugin_manager import PluginManager
from mcp_server.plugins.python_plugin.plugin import Plugin as PythonPlugin
from mcp_server.plugins.js_plugin.plugin import Plugin as JSPlugin
from mcp_server.plugins.jvm_plugin.plugin import Plugin as JVMPlugin
from mcp_server.plugins.go_plugin.plugin import Plugin as GoPlugin
from mcp_server.plugins.ruby_plugin.plugin import Plugin as RubyPlugin
from mcp_server.plugins.php_plugin.plugin import Plugin as PHPPlugin

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_simple_indexing():
    """Test basic indexing functionality."""
    logger.info("Starting simple indexing test...")
    
    # Initialize SQLite store
    db_path = Path("test_simple.db")
    if db_path.exists():
        db_path.unlink()
    
    sqlite_store = SQLiteStore(str(db_path))
    
    # Initialize plugins
    plugins = {
        "python": PythonPlugin(sqlite_store),
        "javascript": JSPlugin(sqlite_store),
        "java": JVMPlugin(sqlite_store),
        "go": GoPlugin(sqlite_store),
        "ruby": RubyPlugin(sqlite_store),
        "php": PHPPlugin(sqlite_store),
    }
    
    # Test repos directory
    test_repos_dir = Path("test_repos")
    
    # Statistics
    stats = {
        "total_files": 0,
        "indexed_files": 0,
        "total_symbols": 0,
        "by_language": {},
        "by_type": {}
    }
    
    # Index each repository
    for repo_dir in test_repos_dir.iterdir():
        if not repo_dir.is_dir():
            continue
            
        logger.info(f"\nIndexing repository: {repo_dir.name}")
        
        for file_path in repo_dir.rglob("*"):
            if not file_path.is_file():
                continue
                
            stats["total_files"] += 1
            
            # Find matching plugin
            plugin = None
            for p in plugins.values():
                if p.supports(str(file_path)):
                    plugin = p
                    break
            
            if not plugin:
                continue
            
            try:
                # Read file
                content = file_path.read_text(encoding='utf-8')
                
                # Index file
                result = plugin.indexFile(str(file_path), content)
                
                if result and "symbols" in result:
                    stats["indexed_files"] += 1
                    symbols = result["symbols"]
                    stats["total_symbols"] += len(symbols)
                    
                    # Track language
                    language = result.get("language", "unknown")
                    stats["by_language"][language] = stats["by_language"].get(language, 0) + 1
                    
                    # Track symbol types
                    for symbol in symbols:
                        kind = symbol.get("kind", "unknown")
                        stats["by_type"][kind] = stats["by_type"].get(kind, 0) + 1
                    
                    if symbols:
                        logger.info(f"  ✓ {file_path.name}: {len(symbols)} symbols")
                        # Show first few symbols
                        for sym in symbols[:3]:
                            logger.info(f"    - {sym['symbol']} ({sym['kind']}) at line {sym['line']}")
                        if len(symbols) > 3:
                            logger.info(f"    ... and {len(symbols) - 3} more")
                            
            except Exception as e:
                logger.error(f"  ✗ Failed to index {file_path.name}: {e}")
    
    # Test search functionality
    logger.info("\n" + "="*60)
    logger.info("Testing search functionality...")
    
    test_searches = [
        ("main", "Entry point functions"),
        ("config", "Configuration related"),
        ("error", "Error handling"),
        ("test", "Test functions"),
        ("get", "Getter methods/functions"),
    ]
    
    search_results = {}
    
    for query, description in test_searches:
        logger.info(f"\nSearching for '{query}' ({description})...")
        all_results = []
        
        for lang, plugin in plugins.items():
            try:
                results = plugin.search(query, {"limit": 3})
                for r in results:
                    r["language"] = lang
                    all_results.append(r)
            except Exception as e:
                logger.error(f"  Search failed for {lang}: {e}")
        
        # Sort by score
        all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
        search_results[query] = all_results[:5]  # Top 5
        
        logger.info(f"  Found {len(all_results)} total results")
        for i, result in enumerate(all_results[:3]):
            logger.info(f"  [{i+1}] {Path(result['file']).name}:{result['line']} - {result['symbol']} ({result['language']})")
    
    # Test symbol lookup
    logger.info("\n" + "="*60)
    logger.info("Testing symbol definition lookup...")
    
    test_symbols = ["Application", "main", "Config", "app", "index"]
    
    for symbol in test_symbols:
        logger.info(f"\nLooking up '{symbol}'...")
        found = False
        
        for lang, plugin in plugins.items():
            try:
                definition = plugin.getDefinition(symbol)
                if definition:
                    logger.info(f"  ✓ Found in {Path(definition['defined_in']).name} ({lang})")
                    logger.info(f"    Type: {definition['kind']}")
                    logger.info(f"    Line: {definition['line']}")
                    found = True
                    break
            except:
                pass
        
        if not found:
            logger.info("  ✗ Not found")
    
    # Print summary
    print("\n" + "="*60)
    print("INDEXING SUMMARY")
    print("="*60)
    print(f"Total files scanned: {stats['total_files']}")
    print(f"Files indexed: {stats['indexed_files']}")
    print(f"Total symbols: {stats['total_symbols']}")
    print(f"\nBy Language:")
    for lang, count in sorted(stats['by_language'].items()):
        print(f"  {lang}: {count} files")
    print(f"\nBy Symbol Type:")
    for kind, count in sorted(stats['by_type'].items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {kind}: {count}")
    print("="*60)
    
    # Save results
    results = {
        "stats": stats,
        "search_results": {k: [{"file": Path(r["file"]).name, "symbol": r["symbol"], "line": r["line"]} 
                               for r in v] for k, v in search_results.items()}
    }
    
    with open("test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    logger.info("\nResults saved to test_results.json")
    
    # Cleanup
    if db_path.exists():
        db_path.unlink()

if __name__ == "__main__":
    test_simple_indexing()