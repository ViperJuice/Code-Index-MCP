#!/usr/bin/env python3
"""Quick test of indexing specific files."""

import sys
from pathlib import Path
import logging

sys.path.insert(0, str(Path(__file__).parent))

from mcp_server.plugins.python_plugin.plugin import Plugin as PythonPlugin
from mcp_server.plugins.js_plugin.plugin import Plugin as JSPlugin
from mcp_server.plugins.jvm_plugin.plugin import Plugin as JVMPlugin
from mcp_server.plugins.go_plugin.plugin import Plugin as GoPlugin

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_single_file_indexing():
    """Test indexing single files from each language."""
    
    # Initialize plugins without SQLite to avoid pre-indexing
    plugins = {
        "python": PythonPlugin(None),
        "javascript": JSPlugin(None),
        "java": JVMPlugin(None),
        "go": GoPlugin(None),
    }
    
    # Test files
    test_files = [
        ("test_repos/flask-app/app/__init__.py", "python"),
        ("test_repos/express-api/src/index.js", "javascript"),
        ("test_repos/spring-boot/complete/src/main/java/com/example/springboot/Application.java", "java"),
        ("test_repos/go-examples/hello/hello.go", "go"),
    ]
    
    for file_path, expected_lang in test_files:
        path = Path(file_path)
        if not path.exists():
            logger.warning(f"File not found: {file_path}")
            continue
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Testing: {path.name} ({expected_lang})")
        logger.info(f"{'='*60}")
        
        plugin = plugins.get(expected_lang)
        if not plugin:
            logger.error(f"No plugin for {expected_lang}")
            continue
        
        try:
            # Read file
            content = path.read_text(encoding='utf-8')
            logger.info(f"File size: {len(content)} bytes")
            
            # Index file
            result = plugin.indexFile(str(path), content)
            
            if result and "symbols" in result:
                symbols = result["symbols"]
                logger.info(f"✓ Indexed successfully: {len(symbols)} symbols found")
                
                # Group symbols by type
                by_type = {}
                for sym in symbols:
                    kind = sym.get("kind", "unknown")
                    if kind not in by_type:
                        by_type[kind] = []
                    by_type[kind].append(sym)
                
                # Show symbols by type
                for kind, syms in by_type.items():
                    logger.info(f"\n{kind.upper()}S ({len(syms)}):")
                    for sym in syms[:3]:  # Show first 3 of each type
                        logger.info(f"  - {sym['symbol']} (line {sym['line']})")
                    if len(syms) > 3:
                        logger.info(f"  ... and {len(syms) - 3} more")
                
                # Test search
                logger.info("\nTesting search...")
                test_queries = ["main", "get", "init", "config"]
                for query in test_queries:
                    results = plugin.search(query, {"limit": 3})
                    if results:
                        logger.info(f"  '{query}': {len(results)} results")
                        
            else:
                logger.error("✗ Indexing failed or no symbols found")
                
        except Exception as e:
            logger.error(f"✗ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_single_file_indexing()