#!/usr/bin/env python3
"""Test SQL/BM25 retrieval directly on populated indexes."""

import sqlite3
from pathlib import Path
import json

def test_sql_retrieval():
    """Test SQL retrieval on the largest populated indexes."""
    
    print("TESTING SQL/BM25 RETRIEVAL")
    print("=" * 80)
    
    # Test the Code-Index-MCP's own index
    test_indexes = [
        ("f7b49f5d0ae0", "Code-Index-MCP (457 files, 1.1M symbols)"),
        ("d6be0c062f54e636635b23a0a0a5b1b96a459704f8d7a871345be35ff16830b4", "Code-Index-MCP alt (457 files)"),
        ("e3acd2328eea", "TypeScript project (74K files)"),
        ("48f70bd595a6", "Dart project (51K files)"),
        ("d72d7e1e17d2", "JavaScript project (6K files)")
    ]
    
    results = []
    
    for repo_id, description in test_indexes:
        db_path = Path(f".indexes/{repo_id}/current.db")
        if not db_path.exists():
            print(f"\n❌ {description}: Database not found")
            continue
            
        print(f"\n📁 Testing {description}")
        print("-" * 60)
        
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # Test 1: Check tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            print(f"Tables: {', '.join(tables)}")
            
            # Test 2: Symbol search (if table exists)
            if "symbols" in tables:
                cursor.execute("""
                    SELECT name, kind, file_path, line 
                    FROM symbols 
                    WHERE name LIKE '%Index%' 
                    LIMIT 5
                """)
                symbols = cursor.fetchall()
                print(f"\n✓ Symbol search for 'Index': {len(symbols)} results")
                for name, kind, file_path, line in symbols[:3]:
                    print(f"  - {name} ({kind}) at {file_path}:{line}")
            else:
                print("⚠️  No symbols table")
            
            # Test 3: BM25 full-text search
            if "bm25_content" in tables:
                queries = ["def", "class", "function", "import", "return"]
                
                for query in queries:
                    try:
                        cursor.execute("""
                            SELECT COUNT(*) 
                            FROM bm25_content 
                            WHERE bm25_content MATCH ?
                        """, (query,))
                        count = cursor.fetchone()[0]
                        
                        # Get sample results
                        cursor.execute("""
                            SELECT filepath, 
                                   snippet(bm25_content, -1, '**', '**', '...', 20)
                            FROM bm25_content 
                            WHERE bm25_content MATCH ? 
                            LIMIT 3
                        """, (query,))
                        samples = cursor.fetchall()
                        
                        print(f"\n✓ BM25 search for '{query}': {count} total results")
                        for filepath, snippet in samples:
                            print(f"  - {filepath}")
                            print(f"    {snippet}")
                        
                        results.append({
                            "repo_id": repo_id,
                            "query": query,
                            "count": count,
                            "has_results": count > 0
                        })
                        
                    except Exception as e:
                        print(f"✗ BM25 search for '{query}' failed: {e}")
            else:
                print("⚠️  No bm25_content table")
            
            # Test 4: File statistics
            if "files" in tables:
                cursor.execute("SELECT COUNT(*) FROM files")
                file_count = cursor.fetchone()[0]
                
                cursor.execute("""
                    SELECT language, COUNT(*) as cnt 
                    FROM files 
                    WHERE language IS NOT NULL 
                    GROUP BY language 
                    ORDER BY cnt DESC 
                    LIMIT 5
                """)
                languages = cursor.fetchall()
                
                print(f"\n📊 Statistics:")
                print(f"  Total files: {file_count}")
                print(f"  Top languages:")
                for lang, count in languages:
                    print(f"    - {lang}: {count} files")
            
            conn.close()
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    successful_searches = [r for r in results if r["has_results"]]
    print(f"\n✓ Successful searches: {len(successful_searches)}/{len(results)}")
    
    if successful_searches:
        print("\n✅ SQL/BM25 retrieval is WORKING!")
        print(f"   - Found results in {len(set(r['repo_id'] for r in successful_searches))} indexes")
        print(f"   - Average results per query: {sum(r['count'] for r in successful_searches) / len(successful_searches):.0f}")
    else:
        print("\n❌ SQL/BM25 retrieval is NOT working properly")
    
    # Save detailed results
    with open("sql_retrieval_test_results.json", "w") as f:
        json.dump({
            "timestamp": str(Path.cwd()),
            "results": results,
            "summary": {
                "total_tests": len(results),
                "successful": len(successful_searches)
            }
        }, f, indent=2)
    
    print("\nDetailed results saved to: sql_retrieval_test_results.json")


if __name__ == "__main__":
    test_sql_retrieval()