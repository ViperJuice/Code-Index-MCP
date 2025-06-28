#!/usr/bin/env python3
"""Comprehensive verification of all MCP indexes."""

import os
import sys
import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


class IndexVerifier:
    """Verify MCP indexes and test retrieval."""
    
    def __init__(self):
        self.indexes_path = Path(".indexes")
        self.results = {
            "summary": {},
            "indexes": [],
            "sql_tests": [],
            "semantic_tests": [],
            "errors": []
        }
    
    def find_all_indexes(self) -> List[Dict[str, Any]]:
        """Find all indexes with their metadata."""
        indexes = []
        
        for repo_dir in self.indexes_path.iterdir():
            if not repo_dir.is_dir():
                continue
                
            db_path = repo_dir / "current.db"
            if not db_path.exists():
                # Check for symlinks
                if db_path.is_symlink():
                    target = db_path.readlink()
                    if not (repo_dir / target).exists():
                        continue
                    db_path = repo_dir / target
                else:
                    continue
            
            try:
                # Get basic info
                size_mb = db_path.stat().st_size / (1024 * 1024)
                
                # Try to connect and get stats
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()
                
                # Get file count
                try:
                    cursor.execute("SELECT COUNT(*) FROM files")
                    file_count = cursor.fetchone()[0]
                except:
                    file_count = 0
                
                # Get symbol count
                try:
                    cursor.execute("SELECT COUNT(*) FROM symbols")
                    symbol_count = cursor.fetchone()[0]
                except:
                    symbol_count = 0
                
                # Get BM25 content count
                try:
                    cursor.execute("SELECT COUNT(*) FROM bm25_content")
                    bm25_count = cursor.fetchone()[0]
                except:
                    bm25_count = 0
                
                # Get language distribution
                languages = {}
                try:
                    cursor.execute("""
                        SELECT language, COUNT(*) as cnt 
                        FROM files 
                        WHERE language IS NOT NULL 
                        GROUP BY language 
                        ORDER BY cnt DESC 
                        LIMIT 10
                    """)
                    languages = dict(cursor.fetchall())
                except:
                    pass
                
                conn.close()
                
                indexes.append({
                    "repo_id": repo_dir.name,
                    "db_path": str(db_path),
                    "size_mb": round(size_mb, 2),
                    "file_count": file_count,
                    "symbol_count": symbol_count,
                    "bm25_count": bm25_count,
                    "languages": languages,
                    "has_content": file_count > 0 or symbol_count > 0 or bm25_count > 0
                })
                
            except Exception as e:
                self.results["errors"].append({
                    "repo_id": repo_dir.name,
                    "error": str(e)
                })
        
        # Sort by file count
        indexes.sort(key=lambda x: x["file_count"], reverse=True)
        return indexes
    
    def test_sql_search(self, db_path: str, repo_id: str) -> Dict[str, Any]:
        """Test SQL/BM25 search on an index."""
        results = {
            "repo_id": repo_id,
            "db_path": db_path,
            "queries": []
        }
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Test queries
            test_queries = [
                ("SELECT * FROM symbols WHERE name LIKE '%Service%' LIMIT 5", "Service classes"),
                ("SELECT * FROM symbols WHERE kind = 'function' LIMIT 5", "Functions"),
                ("SELECT filepath, snippet(bm25_content, -1, '<<', '>>', '...', 10) FROM bm25_content WHERE bm25_content MATCH 'def' LIMIT 5", "BM25 'def'"),
                ("SELECT filepath, snippet(bm25_content, -1, '<<', '>>', '...', 10) FROM bm25_content WHERE bm25_content MATCH 'class' LIMIT 5", "BM25 'class'"),
                ("SELECT DISTINCT language FROM files WHERE language IS NOT NULL LIMIT 10", "Languages")
            ]
            
            for query, description in test_queries:
                try:
                    cursor.execute(query)
                    rows = cursor.fetchall()
                    results["queries"].append({
                        "description": description,
                        "query": query,
                        "result_count": len(rows),
                        "sample": rows[:2] if rows else []
                    })
                except Exception as e:
                    results["queries"].append({
                        "description": description,
                        "query": query,
                        "error": str(e)
                    })
            
            conn.close()
            
        except Exception as e:
            results["error"] = str(e)
        
        return results
    
    def test_dispatcher_search(self, db_path: str, repo_id: str) -> Dict[str, Any]:
        """Test search using EnhancedDispatcher."""
        results = {
            "repo_id": repo_id,
            "dispatcher_tests": []
        }
        
        try:
            from mcp_server.storage.sqlite_store import SQLiteStore
            from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
            
            # Disable semantic search to avoid Qdrant issues
            store = SQLiteStore(db_path)
            dispatcher = EnhancedDispatcher(
                sqlite_store=store,
                semantic_search_enabled=False,
                lazy_load=False
            )
            
            # Test queries
            test_queries = ["def", "class", "function", "import", "Service"]
            
            for query in test_queries:
                try:
                    search_results = list(dispatcher.search(query, limit=5))
                    results["dispatcher_tests"].append({
                        "query": query,
                        "result_count": len(search_results),
                        "has_results": len(search_results) > 0
                    })
                except Exception as e:
                    results["dispatcher_tests"].append({
                        "query": query,
                        "error": str(e)
                    })
            
        except Exception as e:
            results["error"] = str(e)
        
        return results
    
    def generate_report(self):
        """Generate comprehensive report."""
        print("\n" + "="*80)
        print("MCP INDEX VERIFICATION REPORT")
        print("="*80)
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Find all indexes
        print("\n1. DISCOVERING INDEXES...")
        indexes = self.find_all_indexes()
        self.results["indexes"] = indexes
        
        # Summary statistics
        total_indexes = len(indexes)
        populated_indexes = [idx for idx in indexes if idx["has_content"]]
        total_files = sum(idx["file_count"] for idx in indexes)
        total_symbols = sum(idx["symbol_count"] for idx in indexes)
        total_size_mb = sum(idx["size_mb"] for idx in indexes)
        
        print(f"\nFound {total_indexes} indexes:")
        print(f"  - Populated: {len(populated_indexes)}")
        print(f"  - Empty: {total_indexes - len(populated_indexes)}")
        print(f"  - Total files: {total_files:,}")
        print(f"  - Total symbols: {total_symbols:,}")
        print(f"  - Total size: {total_size_mb:.1f} MB")
        
        self.results["summary"] = {
            "total_indexes": total_indexes,
            "populated_indexes": len(populated_indexes),
            "total_files": total_files,
            "total_symbols": total_symbols,
            "total_size_mb": round(total_size_mb, 1)
        }
        
        # Show top indexes
        print("\n2. TOP INDEXES BY FILE COUNT:")
        print("-" * 80)
        print(f"{'Repo ID':<40} {'Files':>10} {'Symbols':>10} {'Size MB':>10} {'Top Language':<15}")
        print("-" * 80)
        
        for idx in populated_indexes[:10]:
            top_lang = max(idx["languages"].items(), key=lambda x: x[1])[0] if idx["languages"] else "N/A"
            print(f"{idx['repo_id']:<40} {idx['file_count']:>10,} {idx['symbol_count']:>10,} {idx['size_mb']:>10.1f} {top_lang:<15}")
        
        # Test SQL search on top indexes
        print("\n3. TESTING SQL/BM25 SEARCH...")
        print("-" * 80)
        
        for idx in populated_indexes[:5]:  # Test top 5
            print(f"\nTesting {idx['repo_id']}...")
            sql_results = self.test_sql_search(idx["db_path"], idx["repo_id"])
            self.results["sql_tests"].append(sql_results)
            
            for query_result in sql_results.get("queries", []):
                if "error" not in query_result:
                    print(f"  ✓ {query_result['description']}: {query_result['result_count']} results")
                else:
                    print(f"  ✗ {query_result['description']}: {query_result['error']}")
        
        # Test dispatcher search
        print("\n4. TESTING DISPATCHER SEARCH...")
        print("-" * 80)
        
        for idx in populated_indexes[:3]:  # Test top 3
            print(f"\nTesting dispatcher on {idx['repo_id']}...")
            dispatcher_results = self.test_dispatcher_search(idx["db_path"], idx["repo_id"])
            
            if "error" not in dispatcher_results:
                for test in dispatcher_results["dispatcher_tests"]:
                    if "error" not in test:
                        status = "✓" if test["has_results"] else "✗"
                        print(f"  {status} Query '{test['query']}': {test['result_count']} results")
                    else:
                        print(f"  ✗ Query '{test['query']}': {test['error']}")
            else:
                print(f"  ✗ Dispatcher error: {dispatcher_results['error']}")
        
        # Save results
        with open("index_verification_report.json", "w") as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n\nDetailed results saved to: index_verification_report.json")
        
        # Final summary
        print("\n5. VERIFICATION SUMMARY:")
        print("-" * 80)
        
        # Check if searches are working
        sql_working = any(
            query.get("result_count", 0) > 0 
            for test in self.results["sql_tests"] 
            for query in test.get("queries", [])
        )
        
        print(f"✓ Found {len(populated_indexes)} populated indexes")
        print(f"{'✓' if sql_working else '✗'} SQL/BM25 search is {'working' if sql_working else 'NOT working'}")
        print(f"✓ Total indexed content: {total_files:,} files, {total_symbols:,} symbols")
        
        if self.results["errors"]:
            print(f"\n⚠️  {len(self.results['errors'])} errors encountered during verification")


def main():
    """Run the verification."""
    verifier = IndexVerifier()
    verifier.generate_report()


if __name__ == "__main__":
    main()