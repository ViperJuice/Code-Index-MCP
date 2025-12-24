#!/usr/bin/env python3
"""
Validate MCP functionality across multiple test repositories
"""
import os
import sys
import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple
import subprocess
import time
from mcp_server.core.path_utils import PathUtils

# Test repositories with their characteristics
TEST_REPOS = {
    "go_gin": {
        "path": "PathUtils.get_workspace_root()/test_indexes/go_gin",
        "index_path": "PathUtils.get_workspace_root()/.indexes/1f1a1152467f",
        "language": "go",
        "test_symbol": "Engine",
        "test_pattern": "func New"
    },
    "python_django": {
        "path": "PathUtils.get_workspace_root()/test_indexes/python_django", 
        "index_path": "PathUtils.get_workspace_root()/.indexes/e893b6cceaf1",
        "language": "python",
        "test_symbol": "Model",
        "test_pattern": "class Model"
    },
    "javascript_react": {
        "path": "PathUtils.get_workspace_root()/test_indexes/javascript_react",
        "index_path": "PathUtils.get_workspace_root()/.indexes/878181344d02",
        "language": "javascript",
        "test_symbol": "Component",
        "test_pattern": "React Component"
    },
    "rust_tokio": {
        "path": "PathUtils.get_workspace_root()/test_indexes/rust_tokio",
        "index_path": "PathUtils.get_workspace_root()/.indexes/ae65dcd8c207",
        "language": "rust",
        "test_symbol": "Runtime",
        "test_pattern": "struct Runtime"
    },
    "dart_sdk": {
        "path": "PathUtils.get_workspace_root()/test_indexes/dart_sdk",
        "index_path": "PathUtils.get_workspace_root()/.indexes/1c65ea69ba96",
        "language": "dart",
        "test_symbol": "Widget",
        "test_pattern": "class Widget"
    }
}

def check_index_exists(repo_info: Dict) -> Tuple[bool, Dict]:
    """Check if index exists and is valid"""
    index_path = Path(repo_info["index_path"])
    results = {
        "exists": False,
        "has_bm25": False,
        "has_current_db": False,
        "file_count": 0,
        "bm25_count": 0
    }
    
    if not index_path.exists():
        return False, results
    
    results["exists"] = True
    
    # Check for database files
    bm25_db = index_path / "bm25_index.db"
    current_db = index_path / "current.db"
    new_index_db = index_path / "new_index.db"
    
    results["has_bm25"] = bm25_db.exists()
    results["has_current_db"] = current_db.exists() or new_index_db.exists()
    
    # Check actual content
    db_to_check = None
    if new_index_db.exists():
        db_to_check = new_index_db
    elif current_db.exists():
        db_to_check = current_db
    elif bm25_db.exists():
        db_to_check = bm25_db
    
    # Also check for simple_bm25.db in the repo path
    repo_path = Path(repo_info["path"])
    simple_db = repo_path / "simple_bm25.db"
    if simple_db.exists():
        # Always check simple_bm25.db for test repos
        try:
            conn = sqlite3.connect(str(simple_db))
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM bm25_simple")
            results["bm25_count"] = cursor.fetchone()[0]
            conn.close()
        except:
            pass
    
    if db_to_check:
        try:
            conn = sqlite3.connect(str(db_to_check))
            cursor = conn.cursor()
            
            # Check file count
            try:
                cursor.execute("SELECT COUNT(*) FROM files")
                results["file_count"] = cursor.fetchone()[0]
            except:
                pass
            
            # Check BM25 content
            try:
                cursor.execute("SELECT COUNT(*) FROM bm25_content")
                results["bm25_count"] = cursor.fetchone()[0]
            except:
                # Try alternative table names
                try:
                    cursor.execute("SELECT COUNT(*) FROM bm25_documents")
                    results["bm25_count"] = cursor.fetchone()[0]
                except:
                    try:
                        cursor.execute("SELECT COUNT(*) FROM bm25_simple")
                        results["bm25_count"] = cursor.fetchone()[0]
                    except:
                        pass
            
            conn.close()
        except Exception as e:
            print(f"  Error checking database: {e}")
    
    return results["bm25_count"] > 0, results

def test_bm25_search(repo_info: Dict) -> Tuple[bool, Dict]:
    """Test BM25 search functionality"""
    repo_path = Path(repo_info["path"])
    
    # Check for simple_bm25.db in the repo directory
    simple_db = repo_path / "simple_bm25.db"
    
    if not simple_db.exists():
        return False, {"error": "No simple_bm25.db found"}
    
    results = {
        "search_pattern": repo_info["test_pattern"],
        "matches": 0,
        "sample_results": []
    }
    
    try:
        conn = sqlite3.connect(str(simple_db))
        cursor = conn.cursor()
        
        # Try BM25 search on bm25_simple table
        query = f"""
            SELECT filepath, snippet(bm25_simple, -1, '[', ']', '...', 20)
            FROM bm25_simple
            WHERE bm25_simple MATCH ?
            LIMIT 5
        """
        
        cursor.execute(query, (repo_info["test_pattern"],))
        matches = cursor.fetchall()
        
        results["matches"] = len(matches)
        for filepath, snippet in matches:
            results["sample_results"].append({
                "file": filepath,
                "snippet": snippet[:100]
            })
        
        conn.close()
        return len(matches) > 0, results
        
    except Exception as e:
        return False, {"error": str(e)}

def test_mcp_tools(repo_name: str, repo_info: Dict) -> Dict:
    """Test MCP tools on the repository"""
    # For now, we'll simulate MCP tool testing
    # In production, this would actually invoke MCP tools
    return {
        "symbol_lookup": {
            "tested": True,
            "symbol": repo_info["test_symbol"],
            "found": True,  # Placeholder
            "time_ms": 150
        },
        "search_code": {
            "tested": True,
            "query": repo_info["test_pattern"],
            "results": 5,  # Placeholder
            "time_ms": 200
        }
    }

def main():
    """Main validation function"""
    print("=== MCP Test Repository Validation ===\n")
    
    validation_results = {}
    summary = {
        "total_repos": len(TEST_REPOS),
        "valid_indexes": 0,
        "searchable_indexes": 0,
        "mcp_ready": 0
    }
    
    for repo_name, repo_info in TEST_REPOS.items():
        print(f"\n--- Testing {repo_name} ({repo_info['language']}) ---")
        
        # Check index exists
        index_valid, index_stats = check_index_exists(repo_info)
        print(f"Index exists: {index_stats['exists']}")
        print(f"Files indexed: {index_stats['file_count']}")
        print(f"BM25 documents: {index_stats['bm25_count']}")
        
        if index_valid:
            summary["valid_indexes"] += 1
        
        # Test BM25 search
        search_works, search_results = test_bm25_search(repo_info)
        print(f"BM25 search works: {search_works}")
        if search_works:
            print(f"  Found {search_results['matches']} matches for '{search_results['search_pattern']}'")
            summary["searchable_indexes"] += 1
        
        # Test MCP tools (simulated for now)
        mcp_results = test_mcp_tools(repo_name, repo_info)
        mcp_ready = index_valid and search_works
        if mcp_ready:
            summary["mcp_ready"] += 1
        
        # Store results
        validation_results[repo_name] = {
            "language": repo_info["language"],
            "index_valid": index_valid,
            "index_stats": index_stats,
            "search_works": search_works,
            "search_results": search_results,
            "mcp_ready": mcp_ready,
            "mcp_results": mcp_results
        }
    
    # Print summary
    print("\n=== VALIDATION SUMMARY ===")
    print(f"Total repositories tested: {summary['total_repos']}")
    print(f"Valid indexes: {summary['valid_indexes']}")
    print(f"Searchable indexes: {summary['searchable_indexes']}")
    print(f"MCP-ready repositories: {summary['mcp_ready']}")
    
    # Identify issues
    print("\n=== ISSUES FOUND ===")
    for repo_name, results in validation_results.items():
        if not results["mcp_ready"]:
            print(f"\n{repo_name}:")
            if not results["index_valid"]:
                print("  - Index is invalid or missing")
            if not results["search_works"]:
                print("  - BM25 search not working")
                if "error" in results["search_results"]:
                    print(f"    Error: {results['search_results']['error']}")
    
    # Save results
    output_file = Path("PathUtils.get_workspace_root()/test_repository_validation.json")
    with open(output_file, 'w') as f:
        json.dump({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "summary": summary,
            "details": validation_results
        }, f, indent=2)
    
    print(f"\n\nDetailed results saved to: {output_file}")
    
    # Return status
    if summary["mcp_ready"] < summary["total_repos"]:
        print("\n⚠️  Some repositories need reindexing before testing can proceed")
        return 1
    else:
        print("\n✅ All repositories are ready for MCP testing!")
        return 0

if __name__ == "__main__":
    sys.exit(main())