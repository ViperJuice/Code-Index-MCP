#!/usr/bin/env python3
"""
Check the complete status of repository indexing (SQL and Semantic).
"""

import os
import sys
import json
import sqlite3
from pathlib import Path
from qdrant_client import QdrantClient
from datetime import datetime
from mcp_server.core.path_utils import PathUtils

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

def check_sql_indexes():
    """Check SQL index status."""
    indexes_dir = Path(".indexes")
    sql_status = {}
    
    for idx_dir in indexes_dir.iterdir():
        if idx_dir.is_dir() and idx_dir.name not in ['qdrant', 'artifacts']:
            db_files = list(idx_dir.glob("*.db"))
            if db_files:
                db_path = db_files[0]
                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    
                    # Get document count
                    cursor.execute("SELECT COUNT(*) FROM bm25_content")
                    doc_count = cursor.fetchone()[0]
                    
                    # Get sample file to identify repo
                    cursor.execute("SELECT filepath FROM bm25_content LIMIT 1")
                    sample = cursor.fetchone()
                    repo_name = "unknown"
                    if sample:
                        path_parts = sample[0].split('/')
                        for part in path_parts:
                            if part in ['django', 'react', 'flask', 'gin', 'redis', 'grpc', 'typescript']:
                                repo_name = part
                                break
                    
                    conn.close()
                    
                    if doc_count > 0:
                        sql_status[idx_dir.name] = {
                            'documents': doc_count,
                            'repo': repo_name,
                            'db_path': str(db_path)
                        }
                except Exception as e:
                    pass
    
    return sql_status


def check_semantic_indexes():
    """Check semantic index status."""
    semantic_status = {}
    
    try:
        client = QdrantClient(path=".indexes/qdrant/main.qdrant")
        collections = client.get_collections()
        
        for coll in collections.collections:
            try:
                info = client.get_collection(coll.name)
                if info.points_count > 0:
                    semantic_status[coll.name] = {
                        'points': info.points_count,
                        'vectors_config': info.config.params.vectors.size if hasattr(info.config.params.vectors, 'size') else 1024
                    }
            except:
                pass
    except Exception as e:
        print(f"Error checking Qdrant: {e}")
    
    return semantic_status


def find_all_test_repos():
    """Find all test repositories."""
    test_repos_dir = Path("PathUtils.get_workspace_root()/test_repos")
    repos = []
    
    for git_dir in test_repos_dir.rglob(".git"):
        if git_dir.is_dir():
            repo_dir = git_dir.parent
            repos.append(repo_dir.name)
    
    return sorted(set(repos))


def main():
    """Main function to check index status."""
    print("Code Index Status Report")
    print("=" * 80)
    print(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Check SQL indexes
    sql_status = check_sql_indexes()
    print(f"SQL Indexes: {len(sql_status)} repositories indexed")
    print("-" * 40)
    
    total_sql_docs = 0
    for idx, info in sorted(sql_status.items(), key=lambda x: x[1]['documents'], reverse=True):
        if info['documents'] > 100:  # Only show significant indexes
            print(f"  {info['repo']:20} {info['documents']:8,} documents")
            total_sql_docs += info['documents']
    
    print(f"\nTotal SQL documents: {total_sql_docs:,}")
    
    # Check semantic indexes
    print("\n" + "=" * 80)
    semantic_status = check_semantic_indexes()
    print(f"Semantic Indexes: {len(semantic_status)} collections")
    print("-" * 40)
    
    total_embeddings = 0
    for coll, info in sorted(semantic_status.items(), key=lambda x: x[1]['points'], reverse=True):
        print(f"  {coll:30} {info['points']:8,} embeddings")
        total_embeddings += info['points']
    
    print(f"\nTotal embeddings: {total_embeddings:,}")
    
    # Find missing repositories
    print("\n" + "=" * 80)
    all_repos = find_all_test_repos()
    
    # Extract repo names from indexes
    sql_repos = {info['repo'] for info in sql_status.values() if info['repo'] != 'unknown'}
    semantic_repos = set()
    for coll_name in semantic_status.keys():
        # Extract repo name from collection name (e.g., "c_redis" -> "redis")
        parts = coll_name.split('_')
        if len(parts) > 1:
            semantic_repos.add(parts[-1])
    
    print(f"Total repositories found: {len(all_repos)}")
    print(f"Repositories with SQL index: {len(sql_repos)}")
    print(f"Repositories with semantic index: {len(semantic_repos)}")
    
    # Missing repositories
    missing_sql = set(all_repos) - sql_repos
    missing_semantic = set(all_repos) - semantic_repos
    
    if missing_sql:
        print(f"\nMissing SQL indexes ({len(missing_sql)}):")
        for repo in sorted(missing_sql)[:10]:  # Show first 10
            print(f"  - {repo}")
        if len(missing_sql) > 10:
            print(f"  ... and {len(missing_sql) - 10} more")
    
    if missing_semantic:
        print(f"\nMissing semantic indexes ({len(missing_semantic)}):")
        for repo in sorted(missing_semantic)[:10]:  # Show first 10
            print(f"  - {repo}")
        if len(missing_semantic) > 10:
            print(f"  ... and {len(missing_semantic) - 10} more")
    
    # Save status report
    status_report = {
        'timestamp': datetime.now().isoformat(),
        'sql_indexes': {
            'count': len(sql_status),
            'total_documents': total_sql_docs,
            'repositories': sql_status
        },
        'semantic_indexes': {
            'count': len(semantic_status),
            'total_embeddings': total_embeddings,
            'collections': semantic_status
        },
        'summary': {
            'total_repos': len(all_repos),
            'sql_indexed': len(sql_repos),
            'semantic_indexed': len(semantic_repos),
            'missing_sql': len(missing_sql),
            'missing_semantic': len(missing_semantic)
        }
    }
    
    with open('INDEXING_STATUS.json', 'w') as f:
        json.dump(status_report, f, indent=2)
    
    print(f"\n\nDetailed status saved to: INDEXING_STATUS.json")


if __name__ == "__main__":
    main()