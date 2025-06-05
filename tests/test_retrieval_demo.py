#!/usr/bin/env python3
"""Demo script showing retrieval capabilities."""

import sys
from pathlib import Path
import logging
from typing import List, Dict, Any
import json

sys.path.insert(0, str(Path(__file__).parent))

from mcp_server.plugins.python_plugin.plugin import Plugin as PythonPlugin
from mcp_server.plugins.js_plugin.plugin import Plugin as JSPlugin
from mcp_server.plugins.jvm_plugin.plugin import Plugin as JVMPlugin
from mcp_server.plugins.go_plugin.plugin import Plugin as GoPlugin

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

class RetrievalDemo:
    """Demonstrate code retrieval capabilities."""
    
    def __init__(self):
        self.plugins = {
            "python": PythonPlugin(None),
            "javascript": JSPlugin(None),
            "java": JVMPlugin(None),
            "go": GoPlugin(None),
        }
        self.index = []
    
    def build_index(self):
        """Build a simple in-memory index."""
        logger.info("Building code index...\n")
        
        test_files = [
            ("test_repos/flask-app/app/main/views.py", "python"),
            ("test_repos/express-api/src/api/index.js", "javascript"),
            ("test_repos/spring-boot/complete/src/main/java/com/example/springboot/HelloController.java", "java"),
            ("test_repos/go-examples/hello/hello.go", "go"),
        ]
        
        for file_path, lang in test_files:
            path = Path(file_path)
            if not path.exists():
                continue
            
            plugin = self.plugins[lang]
            try:
                content = path.read_text(encoding='utf-8')
                result = plugin.indexFile(str(path), content)
                
                if result and "symbols" in result:
                    for symbol in result["symbols"]:
                        self.index.append({
                            "file": str(path),
                            "language": lang,
                            "symbol": symbol["symbol"],
                            "kind": symbol["kind"],
                            "line": symbol["line"],
                            "signature": symbol.get("signature", "")[:100]
                        })
            except:
                pass
        
        logger.info(f"✓ Indexed {len(self.index)} symbols\n")
    
    def demonstrate_queries(self):
        """Show different types of queries and their results."""
        logger.info("="*60)
        logger.info("CODE RETRIEVAL DEMONSTRATION")
        logger.info("="*60)
        
        demos = [
            {
                "title": "1. Find all main/entry functions",
                "query": lambda s: "main" in s["symbol"].lower(),
                "description": "Entry points across different languages"
            },
            {
                "title": "2. Find HTTP route handlers",
                "query": lambda s: any(k in s["symbol"].lower() for k in ["route", "handler", "controller", "get", "post"]),
                "description": "Web request handlers"
            },
            {
                "title": "3. Find classes/types",
                "query": lambda s: s["kind"] in ["class", "struct", "interface"],
                "description": "Type definitions"
            },
            {
                "title": "4. Find test code",
                "query": lambda s: "test" in s["symbol"].lower() or s["kind"] == "test",
                "description": "Test functions and classes"
            },
            {
                "title": "5. Cross-language pattern: initialization",
                "query": lambda s: any(k in s["symbol"].lower() for k in ["init", "create", "new", "setup"]),
                "description": "Initialization/setup code"
            }
        ]
        
        for demo in demos:
            logger.info(f"\n{demo['title']}")
            logger.info(f"Description: {demo['description']}")
            logger.info("-" * 60)
            
            results = [s for s in self.index if demo["query"](s)]
            
            if results:
                # Group by language
                by_lang = {}
                for r in results:
                    lang = r["language"]
                    if lang not in by_lang:
                        by_lang[lang] = []
                    by_lang[lang].append(r)
                
                for lang, symbols in by_lang.items():
                    logger.info(f"\n{lang.upper()}:")
                    for sym in symbols[:3]:  # Show up to 3 per language
                        logger.info(f"  • {sym['symbol']} ({sym['kind']})")
                        logger.info(f"    File: {Path(sym['file']).name}, Line: {sym['line']}")
                        if sym['signature']:
                            logger.info(f"    Signature: {sym['signature']}...")
            else:
                logger.info("  No matches found")
        
        # Show language statistics
        logger.info("\n" + "="*60)
        logger.info("INDEX STATISTICS")
        logger.info("="*60)
        
        lang_stats = {}
        kind_stats = {}
        
        for entry in self.index:
            # Language stats
            lang = entry["language"]
            lang_stats[lang] = lang_stats.get(lang, 0) + 1
            
            # Kind stats
            kind = entry["kind"]
            kind_stats[kind] = kind_stats.get(kind, 0) + 1
        
        logger.info("\nBy Language:")
        for lang, count in sorted(lang_stats.items()):
            logger.info(f"  {lang}: {count} symbols")
        
        logger.info("\nBy Symbol Type:")
        for kind, count in sorted(kind_stats.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"  {kind}: {count}")
        
        # Show semantic search capabilities
        logger.info("\n" + "="*60)
        logger.info("SEMANTIC SEARCH CAPABILITIES")
        logger.info("="*60)
        logger.info("\nWithout Voyage AI (current):")
        logger.info("  ✓ Exact keyword matching")
        logger.info("  ✓ Pattern-based search")
        logger.info("  ✓ Symbol type filtering")
        logger.info("  ✓ Cross-language search")
        
        logger.info("\nWith Voyage AI + Qdrant:")
        logger.info("  ✓ Natural language queries")
        logger.info("  ✓ Semantic understanding")
        logger.info("  ✓ Code similarity search")
        logger.info("  ✓ Context-aware retrieval")
        logger.info("\nExample semantic queries:")
        logger.info('  - "function that validates user input"')
        logger.info('  - "code that handles database connections"')
        logger.info('  - "error handling and logging"')
        logger.info('  - "REST API endpoint implementations"')

def main():
    """Run the retrieval demo."""
    demo = RetrievalDemo()
    demo.build_index()
    demo.demonstrate_queries()
    
    logger.info("\n" + "="*60)
    logger.info("To enable semantic search:")
    logger.info("  1. Set VOYAGE_API_KEY environment variable")
    logger.info("  2. Run Qdrant: docker run -p 6333:6333 qdrant/qdrant")
    logger.info("  3. Use SemanticIndexer for embeddings")
    logger.info("="*60)

if __name__ == "__main__":
    main()