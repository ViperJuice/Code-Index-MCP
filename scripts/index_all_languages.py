#!/usr/bin/env python3
"""
Index all fetched repositories with comprehensive metrics collection.

This script:
1. Creates BM25, symbol, and semantic indexes for each repository
2. Measures indexing performance (time, memory, size)
3. Validates index quality
4. Saves metrics for analysis
"""

import os
import sys
import json
import time
import psutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import sqlite3

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.indexer.bm25_indexer import BM25Indexer
from mcp_server.plugin_system import PluginManager
from mcp_server.dispatcher.dispatcher import Dispatcher


class RepositoryIndexer:
    """Indexes repositories and collects detailed metrics."""
    
    def __init__(self, base_dir: str = "test_repos", index_dir: str = "test_indexes"):
        self.base_dir = Path(base_dir)
        self.index_dir = Path(index_dir)
        self.metrics_file = Path("test_results/indexing_metrics.json")
        self.metrics = {}
        
        # Create directories
        self.index_dir.mkdir(exist_ok=True)
        self.metrics_file.parent.mkdir(exist_ok=True)
        
    def load_repository_stats(self) -> Dict:
        """Load repository statistics from fetch phase."""
        stats_file = Path("test_results/repository_stats.json")
        if not stats_file.exists():
            print("ERROR: Repository stats not found. Run fetch_diverse_repos.py first!")
            sys.exit(1)
            
        with open(stats_file) as f:
            return json.load(f)
            
    def index_repository(self, repo_info: Dict) -> Dict:
        """Index a single repository and collect metrics."""
        repo_name = repo_info["repository"]
        repo_path = Path(repo_info["path"])
        language = repo_info["language"]
        
        print(f"\n{'='*60}")
        print(f"Indexing {repo_name} ({language})")
        print(f"Path: {repo_path}")
        print(f"{'='*60}")
        
        # Prepare index directory for this repo
        safe_name = repo_name.replace("/", "_")
        repo_index_dir = self.index_dir / safe_name
        repo_index_dir.mkdir(exist_ok=True)
        
        metrics = {
            "repository": repo_name,
            "language": language,
            "started_at": datetime.now().isoformat(),
            "repo_metrics": repo_info["metrics"],
            "indexing": {}
        }
        
        # 1. Create BM25 Index
        print("\n1. Creating BM25 Index...")
        bm25_metrics = self._create_bm25_index(repo_path, repo_index_dir)
        metrics["indexing"]["bm25"] = bm25_metrics
        
        # 2. Create Symbol Index
        print("\n2. Creating Symbol Index...")
        symbol_metrics = self._create_symbol_index(repo_path, repo_index_dir)
        metrics["indexing"]["symbols"] = symbol_metrics
        
        # 3. Test index quality
        print("\n3. Testing Index Quality...")
        quality_metrics = self._test_index_quality(repo_index_dir, repo_path, language)
        metrics["quality"] = quality_metrics
        
        metrics["completed_at"] = datetime.now().isoformat()
        
        # Print summary
        print(f"\nIndexing Summary:")
        print(f"  BM25 Index: {bm25_metrics['size_mb']:.1f} MB in {bm25_metrics['time_seconds']:.1f}s")
        print(f"  Symbols: {symbol_metrics['symbol_count']} in {symbol_metrics['time_seconds']:.1f}s")
        print(f"  Quality Score: {quality_metrics['overall_score']:.2f}/1.0")
        
        return metrics
        
    def _create_bm25_index(self, repo_path: Path, index_dir: Path) -> Dict:
        """Create BM25 full-text search index."""
        db_path = index_dir / "bm25_index.db"
        
        # Measure initial memory
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        start_time = time.time()
        
        try:
            # Initialize storage and indexer
            storage = SQLiteStore(str(db_path))
            bm25_indexer = BM25Indexer(storage)
            
            # Index all text files
            files_indexed = 0
            total_chars = 0
            
            for file_path in repo_path.rglob("*"):
                if file_path.is_file() and self._is_text_file(file_path):
                    try:
                        content = file_path.read_text(encoding='utf-8', errors='ignore')
                        if content:
                            # Store file first
                            relative_path = str(file_path.relative_to(repo_path))
                            storage.store_file(relative_path, {
                                "content": content,
                                "size": len(content),
                                "extension": file_path.suffix
                            })
                            
                            # Add to BM25 index
                            bm25_indexer.add_document(
                                relative_path,
                                content,
                                {"language": file_path.suffix}
                            )
                            
                            files_indexed += 1
                            total_chars += len(content)
                            
                            if files_indexed % 100 == 0:
                                print(f"    Indexed {files_indexed} files...")
                                
                    except Exception as e:
                        pass  # Skip problematic files
                        
            # Get final metrics
            elapsed_time = time.time() - start_time
            peak_memory = process.memory_info().rss / 1024 / 1024
            memory_used = peak_memory - initial_memory
            
            # Get index size
            db_size = db_path.stat().st_size / 1024 / 1024  # MB
            
            # Get index statistics
            stats = bm25_indexer.get_statistics()
            
            return {
                "files_indexed": files_indexed,
                "total_chars": total_chars,
                "time_seconds": elapsed_time,
                "memory_used_mb": memory_used,
                "size_mb": db_size,
                "documents_per_second": files_indexed / elapsed_time if elapsed_time > 0 else 0,
                "compression_ratio": total_chars / (db_size * 1024 * 1024) if db_size > 0 else 0,
                "statistics": stats
            }
            
        except Exception as e:
            print(f"    ERROR: {e}")
            return {
                "error": str(e),
                "files_indexed": 0,
                "time_seconds": time.time() - start_time
            }
            
    def _create_symbol_index(self, repo_path: Path, index_dir: Path) -> Dict:
        """Create symbol index using language plugins."""
        db_path = index_dir / "symbol_index.db"
        
        start_time = time.time()
        
        try:
            # Initialize plugin system
            plugin_manager = PluginManager()
            # Load plugins using the correct method
            plugin_manager.load_plugins()
            dispatcher = Dispatcher(plugin_manager.plugins)
            
            # Initialize storage for symbols
            storage = SQLiteStore(str(db_path))
            
            # Index files
            symbols_found = 0
            files_processed = 0
            
            for file_path in repo_path.rglob("*"):
                if file_path.is_file():
                    try:
                        # Use dispatcher to index file
                        dispatcher.index_file(file_path)
                        files_processed += 1
                        
                        if files_processed % 50 == 0:
                            print(f"    Processed {files_processed} files...")
                            
                    except Exception:
                        pass  # Skip unsupported files
                        
            # Get symbol count from dispatcher stats
            stats = dispatcher.get_statistics()
            
            elapsed_time = time.time() - start_time
            db_size = db_path.stat().st_size / 1024 / 1024 if db_path.exists() else 0
            
            return {
                "files_processed": files_processed,
                "symbol_count": stats.get("total", 0),
                "time_seconds": elapsed_time,
                "size_mb": db_size,
                "symbols_per_second": stats.get("total", 0) / elapsed_time if elapsed_time > 0 else 0,
                "language_breakdown": stats.get("by_language", {})
            }
            
        except Exception as e:
            print(f"    ERROR: {e}")
            return {
                "error": str(e),
                "symbol_count": 0,
                "time_seconds": time.time() - start_time
            }
            
    def _test_index_quality(self, index_dir: Path, repo_path: Path, language: str) -> Dict:
        """Test index quality with sample queries."""
        quality_tests = []
        
        # Test queries based on language
        test_queries = self._get_test_queries(language)
        
        db_path = index_dir / "bm25_index.db"
        if not db_path.exists():
            return {"error": "No BM25 index found", "overall_score": 0}
            
        try:
            storage = SQLiteStore(str(db_path))
            bm25_indexer = BM25Indexer(storage)
            
            for query_name, query_text in test_queries.items():
                start = time.time()
                results = bm25_indexer.search(query_text, limit=10)
                search_time = time.time() - start
                
                # Simple relevance check: do results contain query terms?
                relevant = 0
                for result in results:
                    if any(term.lower() in result.get("snippet", "").lower() 
                          for term in query_text.split()):
                        relevant += 1
                        
                precision = relevant / len(results) if results else 0
                
                quality_tests.append({
                    "query": query_name,
                    "results_found": len(results),
                    "search_time_ms": search_time * 1000,
                    "precision": precision
                })
                
            # Calculate overall quality score
            if quality_tests:
                avg_precision = sum(t["precision"] for t in quality_tests) / len(quality_tests)
                avg_results = sum(t["results_found"] for t in quality_tests) / len(quality_tests)
                avg_time = sum(t["search_time_ms"] for t in quality_tests) / len(quality_tests)
                
                # Score based on precision (50%), results found (30%), speed (20%)
                score = (avg_precision * 0.5 + 
                        min(avg_results / 5, 1.0) * 0.3 +  # Normalize to 5+ results
                        min(50 / max(avg_time, 1), 1.0) * 0.2)  # Bonus for <50ms
            else:
                score = 0
                
            return {
                "test_queries": quality_tests,
                "overall_score": score,
                "index_responsive": True
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "overall_score": 0,
                "index_responsive": False
            }
            
    def _get_test_queries(self, language: str) -> Dict[str, str]:
        """Get language-specific test queries."""
        # Common queries for all languages
        common = {
            "find_main": "main function",
            "find_test": "test",
            "find_error": "error",
            "find_todo": "TODO"
        }
        
        # Language-specific queries
        specific = {
            "python": {
                "find_class": "class",
                "find_import": "import",
                "find_decorator": "@"
            },
            "javascript": {
                "find_function": "function",
                "find_const": "const",
                "find_require": "require"
            },
            "go": {
                "find_func": "func",
                "find_interface": "interface",
                "find_goroutine": "go"
            },
            "rust": {
                "find_fn": "fn",
                "find_trait": "trait",
                "find_unsafe": "unsafe"
            },
            "java": {
                "find_class": "class",
                "find_interface": "interface", 
                "find_annotation": "@"
            }
        }
        
        queries = common.copy()
        if language in specific:
            queries.update(specific[language])
            
        return queries
        
    def _is_text_file(self, path: Path) -> bool:
        """Check if file is likely a text file."""
        # Common text file extensions
        text_extensions = {
            '.py', '.js', '.ts', '.go', '.rs', '.java', '.c', '.cpp', '.h', '.hpp',
            '.cs', '.rb', '.php', '.swift', '.kt', '.scala', '.clj', '.ex', '.exs',
            '.hs', '.dart', '.lua', '.pl', '.zig', '.txt', '.md', '.json', '.xml',
            '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf', '.sh', '.bash'
        }
        
        if path.suffix.lower() in text_extensions:
            return True
            
        # Check if no extension but might be text (like Makefile, README)
        if not path.suffix:
            try:
                with open(path, 'rb') as f:
                    chunk = f.read(512)
                    # Simple heuristic: if mostly ASCII, probably text
                    text_chars = sum(1 for b in chunk if 32 <= b < 127 or b in (9, 10, 13))
                    return text_chars / len(chunk) > 0.7 if chunk else False
            except:
                return False
                
        return False
        
    def index_all(self):
        """Index all fetched repositories."""
        # Load repository stats
        repo_data = self.load_repository_stats()
        repositories = repo_data["repositories"]
        
        print(f"\nIndexing {len(repositories)} repositories...")
        
        all_metrics = []
        
        for i, repo_info in enumerate(repositories, 1):
            print(f"\n[{i}/{len(repositories)}]", end="")
            
            try:
                metrics = self.index_repository(repo_info)
                all_metrics.append(metrics)
                self.metrics[repo_info["repository"]] = metrics
                
                # Save incrementally
                self._save_metrics(all_metrics)
                
            except Exception as e:
                print(f"\nERROR indexing {repo_info['repository']}: {e}")
                all_metrics.append({
                    "repository": repo_info["repository"],
                    "language": repo_info["language"],
                    "error": str(e)
                })
                
        # Final summary
        self._print_summary(all_metrics)
        
    def _save_metrics(self, metrics: List[Dict]):
        """Save metrics to file."""
        summary = self._calculate_summary(metrics)
        
        with open(self.metrics_file, 'w') as f:
            json.dump({
                "summary": summary,
                "repositories": metrics
            }, f, indent=2)
            
    def _calculate_summary(self, metrics: List[Dict]) -> Dict:
        """Calculate summary statistics."""
        successful = [m for m in metrics if "error" not in m]
        
        if not successful:
            return {"error": "No successful indexes"}
            
        # Aggregate by language
        by_language = {}
        for m in successful:
            lang = m["language"]
            if lang not in by_language:
                by_language[lang] = {
                    "count": 0,
                    "total_files": 0,
                    "total_symbols": 0,
                    "avg_index_time": 0,
                    "avg_quality_score": 0
                }
                
            by_language[lang]["count"] += 1
            by_language[lang]["total_files"] += m["indexing"]["bm25"].get("files_indexed", 0)
            by_language[lang]["total_symbols"] += m["indexing"]["symbols"].get("symbol_count", 0)
            
        # Calculate averages
        for lang, stats in by_language.items():
            lang_metrics = [m for m in successful if m["language"] == lang]
            stats["avg_index_time"] = sum(
                m["indexing"]["bm25"].get("time_seconds", 0) + 
                m["indexing"]["symbols"].get("time_seconds", 0)
                for m in lang_metrics
            ) / len(lang_metrics)
            
            quality_scores = [m["quality"].get("overall_score", 0) 
                            for m in lang_metrics if "quality" in m]
            stats["avg_quality_score"] = sum(quality_scores) / len(quality_scores) if quality_scores else 0
            
        return {
            "total_repositories": len(metrics),
            "successful": len(successful),
            "failed": len(metrics) - len(successful),
            "indexing_date": datetime.now().isoformat(),
            "by_language": by_language,
            "total_index_size_mb": sum(
                m["indexing"]["bm25"].get("size_mb", 0) + 
                m["indexing"]["symbols"].get("size_mb", 0)
                for m in successful
            )
        }
        
    def _print_summary(self, metrics: List[Dict]):
        """Print indexing summary."""
        summary = self._calculate_summary(metrics)
        
        print(f"\n{'='*60}")
        print(f"INDEXING COMPLETE")
        print(f"{'='*60}")
        print(f"Total repositories: {summary['total_repositories']}")
        print(f"Successful: {summary['successful']}")
        print(f"Failed: {summary['failed']}")
        print(f"Total index size: {summary['total_index_size_mb']:.1f} MB")
        
        print(f"\nBy Language:")
        for lang, stats in sorted(summary["by_language"].items()):
            print(f"  {lang}:")
            print(f"    Repositories: {stats['count']}")
            print(f"    Files indexed: {stats['total_files']:,}")
            print(f"    Symbols found: {stats['total_symbols']:,}")
            print(f"    Avg index time: {stats['avg_index_time']:.1f}s")
            print(f"    Avg quality: {stats['avg_quality_score']:.2f}")


def main():
    """Main entry point."""
    indexer = RepositoryIndexer()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--stats":
        # Show current stats
        if indexer.metrics_file.exists():
            with open(indexer.metrics_file) as f:
                data = json.load(f)
            print(json.dumps(data["summary"], indent=2))
        else:
            print("No indexing metrics found. Run without --stats to index repositories.")
    else:
        indexer.index_all()


if __name__ == "__main__":
    main()