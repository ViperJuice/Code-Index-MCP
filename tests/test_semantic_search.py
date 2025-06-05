#!/usr/bin/env python3
"""Test semantic search capabilities with Voyage AI embeddings."""

import os
import sys
from pathlib import Path
import logging
import json
from typing import List, Dict, Any

sys.path.insert(0, str(Path(__file__).parent))

from mcp_server.plugins.python_plugin.plugin import Plugin as PythonPlugin
from mcp_server.plugins.js_plugin.plugin import Plugin as JSPlugin
from mcp_server.plugins.jvm_plugin.plugin import Plugin as JVMPlugin
from mcp_server.plugins.go_plugin.plugin import Plugin as GoPlugin
from mcp_server.utils.semantic_indexer import SemanticIndexer

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SemanticSearchTest:
    """Test semantic search functionality."""
    
    def __init__(self):
        # Initialize plugins
        self.plugins = {
            "python": PythonPlugin(None),
            "javascript": JSPlugin(None),
            "java": JVMPlugin(None),
            "go": GoPlugin(None),
        }
        
        # Initialize semantic indexer if credentials available
        self.semantic_indexer = None
        voyage_key = os.getenv("VOYAGE_API_KEY")
        qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        
        if voyage_key:
            try:
                self.semantic_indexer = SemanticIndexer(
                    voyage_api_key=voyage_key,
                    qdrant_url=qdrant_url,
                    collection_name="test_semantic_search"
                )
                logger.info("✓ Semantic indexer initialized with Voyage AI")
            except Exception as e:
                logger.warning(f"Could not initialize semantic indexer: {e}")
        else:
            logger.warning("VOYAGE_API_KEY not set - running without semantic search")
        
        self.indexed_symbols = []
    
    def index_repositories(self):
        """Index all test repositories."""
        logger.info("\nIndexing repositories...")
        
        test_repos_dir = Path("test_repos")
        total_symbols = 0
        
        for repo_dir in test_repos_dir.iterdir():
            if not repo_dir.is_dir():
                continue
            
            logger.info(f"\nProcessing {repo_dir.name}...")
            repo_symbols = 0
            
            for file_path in repo_dir.rglob("*"):
                if not file_path.is_file():
                    continue
                
                # Find matching plugin
                plugin = None
                for p in self.plugins.values():
                    if p.supports(str(file_path)):
                        plugin = p
                        break
                
                if not plugin:
                    continue
                
                try:
                    content = file_path.read_text(encoding='utf-8')
                    result = plugin.indexFile(str(file_path), content)
                    
                    if result and "symbols" in result:
                        symbols = result["symbols"]
                        language = result.get("language", "unknown")
                        
                        for symbol in symbols:
                            # Create searchable entry
                            entry = {
                                "file": str(file_path),
                                "symbol": symbol["symbol"],
                                "kind": symbol["kind"],
                                "line": symbol["line"],
                                "language": language,
                                "signature": symbol.get("signature", ""),
                                "context": self._extract_context(content, symbol["line"])
                            }
                            self.indexed_symbols.append(entry)
                            repo_symbols += 1
                            
                except Exception as e:
                    logger.debug(f"Skipped {file_path.name}: {e}")
            
            logger.info(f"  Indexed {repo_symbols} symbols from {repo_dir.name}")
            total_symbols += repo_symbols
        
        logger.info(f"\nTotal symbols indexed: {total_symbols}")
        
        # Add to semantic index if available
        if self.semantic_indexer:
            logger.info("\nBuilding semantic index...")
            self._build_semantic_index()
    
    def _extract_context(self, content: str, line_num: int, context_lines: int = 3) -> str:
        """Extract code context around a line."""
        lines = content.split('\n')
        start = max(0, line_num - context_lines - 1)
        end = min(len(lines), line_num + context_lines)
        return '\n'.join(lines[start:end])
    
    def _build_semantic_index(self):
        """Build semantic index from symbols."""
        if not self.semantic_indexer:
            return
        
        # Create embeddings for symbols
        texts_to_embed = []
        metadata = []
        
        for entry in self.indexed_symbols:
            # Create rich text representation for embedding
            text = f"{entry['symbol']} ({entry['kind']} in {entry['language']})\n"
            text += f"Signature: {entry['signature']}\n" if entry['signature'] else ""
            text += f"Context:\n{entry['context']}"
            
            texts_to_embed.append(text)
            metadata.append({
                "file": Path(entry["file"]).name,
                "symbol": entry["symbol"],
                "kind": entry["kind"],
                "line": entry["line"],
                "language": entry["language"]
            })
        
        # Embed and store
        try:
            self.semantic_indexer.index_batch(texts_to_embed, metadata)
            logger.info(f"✓ Added {len(texts_to_embed)} symbols to semantic index")
        except Exception as e:
            logger.error(f"Failed to build semantic index: {e}")
    
    def test_semantic_queries(self):
        """Test various semantic search queries."""
        logger.info("\n" + "="*60)
        logger.info("TESTING SEMANTIC SEARCH")
        logger.info("="*60)
        
        # Semantic queries that require understanding
        semantic_queries = [
            "function that handles HTTP requests",
            "code that validates user input",
            "method for database operations",
            "error handling logic",
            "configuration initialization",
            "authentication and authorization",
            "data transformation functions",
            "API endpoint definitions",
            "logging and debugging utilities",
            "test helper functions"
        ]
        
        results = {}
        
        for query in semantic_queries:
            logger.info(f"\nQuery: '{query}'")
            
            if self.semantic_indexer:
                # Semantic search
                try:
                    semantic_results = self.semantic_indexer.search(query, limit=5)
                    results[query] = {
                        "semantic": True,
                        "count": len(semantic_results),
                        "results": semantic_results[:3]  # Top 3
                    }
                    
                    logger.info(f"  Found {len(semantic_results)} semantic matches:")
                    for i, (text, metadata, score) in enumerate(semantic_results[:3]):
                        logger.info(f"  [{i+1}] {metadata['symbol']} ({metadata['kind']}) in {metadata['file']}")
                        logger.info(f"      Score: {score:.3f}, Language: {metadata['language']}")
                        
                except Exception as e:
                    logger.error(f"  Semantic search failed: {e}")
                    results[query] = {"error": str(e)}
            else:
                # Fallback to keyword search
                keyword_results = self._keyword_search(query)
                results[query] = {
                    "semantic": False,
                    "count": len(keyword_results),
                    "results": keyword_results[:3]
                }
                
                logger.info(f"  Found {len(keyword_results)} keyword matches:")
                for i, result in enumerate(keyword_results[:3]):
                    logger.info(f"  [{i+1}] {result['symbol']} ({result['kind']}) in {Path(result['file']).name}")
        
        return results
    
    def _keyword_search(self, query: str) -> List[Dict[str, Any]]:
        """Simple keyword-based search fallback."""
        query_words = query.lower().split()
        results = []
        
        for entry in self.indexed_symbols:
            # Simple scoring based on keyword matches
            score = 0
            searchable = f"{entry['symbol']} {entry['kind']} {entry['signature']}".lower()
            
            for word in query_words:
                if word in searchable:
                    score += 1
                if word in entry['symbol'].lower():
                    score += 2  # Higher weight for symbol name matches
            
            if score > 0:
                results.append({**entry, "score": score})
        
        # Sort by score
        results.sort(key=lambda x: x["score"], reverse=True)
        return results
    
    def test_cross_language_search(self):
        """Test searching across multiple languages."""
        logger.info("\n" + "="*60)
        logger.info("CROSS-LANGUAGE SEARCH")
        logger.info("="*60)
        
        # Common patterns across languages
        patterns = [
            ("main entry point", ["main", "Main", "__main__"]),
            ("configuration class", ["Config", "Configuration", "Settings"]),
            ("HTTP handler", ["Handler", "Controller", "Route"]),
            ("test functions", ["test_", "Test", "should"]),
        ]
        
        for description, keywords in patterns:
            logger.info(f"\nSearching for: {description}")
            
            # Find matches across all languages
            matches_by_lang = {}
            
            for entry in self.indexed_symbols:
                for keyword in keywords:
                    if keyword in entry['symbol']:
                        lang = entry['language']
                        if lang not in matches_by_lang:
                            matches_by_lang[lang] = []
                        matches_by_lang[lang].append(entry)
                        break
            
            # Show results by language
            for lang, matches in matches_by_lang.items():
                logger.info(f"  {lang}: {len(matches)} matches")
                for match in matches[:2]:  # Show first 2
                    logger.info(f"    - {match['symbol']} ({match['kind']})")
    
    def generate_report(self, semantic_results: Dict[str, Any]):
        """Generate test report."""
        report = {
            "total_symbols": len(self.indexed_symbols),
            "languages": {},
            "semantic_search_enabled": self.semantic_indexer is not None,
            "semantic_queries": semantic_results
        }
        
        # Count by language
        for entry in self.indexed_symbols:
            lang = entry['language']
            if lang not in report['languages']:
                report['languages'][lang] = 0
            report['languages'][lang] += 1
        
        # Save report
        with open("semantic_search_report.json", "w") as f:
            json.dump(report, f, indent=2)
        
        logger.info("\n" + "="*60)
        logger.info("SUMMARY")
        logger.info("="*60)
        logger.info(f"Total symbols indexed: {report['total_symbols']}")
        logger.info(f"Languages: {', '.join(f'{k}({v})' for k, v in report['languages'].items())}")
        logger.info(f"Semantic search: {'ENABLED' if report['semantic_search_enabled'] else 'DISABLED'}")
        logger.info(f"Report saved to: semantic_search_report.json")

def main():
    """Run semantic search tests."""
    tester = SemanticSearchTest()
    
    # Index repositories
    tester.index_repositories()
    
    # Test semantic queries
    semantic_results = tester.test_semantic_queries()
    
    # Test cross-language search
    tester.test_cross_language_search()
    
    # Generate report
    tester.generate_report(semantic_results)

if __name__ == "__main__":
    main()