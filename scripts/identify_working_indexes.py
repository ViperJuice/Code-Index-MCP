#!/usr/bin/env python3
"""
Identify test repositories with working BM25 indexes in centralized storage.
"""

import sqlite3
import json
import subprocess
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple
from mcp_server.core.path_utils import PathUtils


def get_repo_hash(repo_path: Path) -> str:
    """Get repository hash from git remote URL."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            cwd=str(repo_path)
        )
        if result.returncode == 0:
            remote_url = result.stdout.strip()
            return hashlib.sha256(remote_url.encode()).hexdigest()[:12]
    except:
        pass
    
    # Fallback to path-based hash
    return hashlib.sha256(str(repo_path.absolute()).encode()).hexdigest()[:12]


def check_index_health(db_path: Path) -> Tuple[bool, Dict]:
    """Check if an index is healthy and contains data."""
    info = {
        'path': str(db_path),
        'exists': db_path.exists(),
        'size_mb': 0,
        'table_exists': False,
        'row_count': 0,
        'sample_files': []
    }
    
    if not db_path.exists():
        return False, info
    
    info['size_mb'] = db_path.stat().st_size / (1024 * 1024)
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Check if bm25_content table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='bm25_content'
        """)
        if cursor.fetchone():
            info['table_exists'] = True
            
            # Get row count
            cursor.execute("SELECT COUNT(*) FROM bm25_content")
            info['row_count'] = cursor.fetchone()[0]
            
            # Get sample files
            cursor.execute("""
                SELECT DISTINCT filepath 
                FROM bm25_content 
                LIMIT 5
            """)
            info['sample_files'] = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        
        # Consider healthy if has table and data
        return info['table_exists'] and info['row_count'] > 0, info
        
    except Exception as e:
        info['error'] = str(e)
        return False, info


def find_test_repos():
    """Find all test repositories."""
    test_repos = []
    
    # Check main test_repos directory
    test_repos_dir = Path("PathUtils.get_workspace_root()/test_repos")
    if test_repos_dir.exists():
        for category in test_repos_dir.iterdir():
            if category.is_dir() and not category.name.startswith('.'):
                for lang in category.iterdir():
                    if lang.is_dir():
                        for repo in lang.iterdir():
                            if repo.is_dir() and (repo / ".git").exists():
                                test_repos.append({
                                    'name': repo.name,
                                    'path': repo,
                                    'category': category.name,
                                    'language': lang.name
                                })
    
    # Also check test_indexes directory references
    test_indexes_dir = Path("PathUtils.get_workspace_root()/test_indexes")
    if test_indexes_dir.exists():
        summary_file = test_indexes_dir / "mcp_indexing_summary.json"
        if summary_file.exists():
            with open(summary_file) as f:
                data = json.load(f)
                for repo in data.get('repositories', []):
                    repo_path = Path(repo['path'])
                    if repo_path.exists():
                        # Extract category and language from path
                        parts = repo_path.parts
                        if 'test_repos' in parts:
                            idx = parts.index('test_repos')
                            if idx + 3 < len(parts):
                                test_repos.append({
                                    'name': repo['repository'],
                                    'path': repo_path,
                                    'category': parts[idx + 1],
                                    'language': parts[idx + 2],
                                    'indexed_files': repo.get('indexed_files', 0)
                                })
    
    # Deduplicate by path
    seen_paths = set()
    unique_repos = []
    for repo in test_repos:
        path_str = str(repo['path'])
        if path_str not in seen_paths:
            seen_paths.add(path_str)
            unique_repos.append(repo)
    
    return unique_repos


def main():
    """Find repositories with working BM25 indexes."""
    
    print("Identifying Test Repositories with Working BM25 Indexes")
    print("=" * 80)
    
    # Find test repositories
    test_repos = find_test_repos()
    print(f"\nFound {len(test_repos)} test repositories")
    
    # Check centralized indexes
    central_index_dir = Path.home() / ".mcp" / "indexes"
    
    working_repos = []
    broken_repos = []
    missing_repos = []
    
    for repo in test_repos:
        repo_hash = get_repo_hash(repo['path'])
        repo['hash'] = repo_hash
        
        # Check for index
        index_dir = central_index_dir / repo_hash
        current_db = index_dir / "current.db"
        
        if current_db.exists():
            # Check if it's a symlink and resolve
            if current_db.is_symlink():
                actual_db = current_db.resolve()
            else:
                actual_db = current_db
            
            is_healthy, info = check_index_health(actual_db)
            repo['index_info'] = info
            
            if is_healthy:
                working_repos.append(repo)
            else:
                broken_repos.append(repo)
        else:
            # Check for any .db files in the directory
            if index_dir.exists():
                db_files = list(index_dir.glob("*.db"))
                if db_files:
                    # Try the most recent one
                    latest_db = max(db_files, key=lambda p: p.stat().st_mtime)
                    is_healthy, info = check_index_health(latest_db)
                    repo['index_info'] = info
                    
                    if is_healthy:
                        repo['index_info']['note'] = f"No current.db symlink, using {latest_db.name}"
                        working_repos.append(repo)
                    else:
                        broken_repos.append(repo)
                else:
                    missing_repos.append(repo)
            else:
                missing_repos.append(repo)
    
    # Print results
    print(f"\n\nSummary:")
    print(f"  Working indexes: {len(working_repos)}")
    print(f"  Broken indexes: {len(broken_repos)}")
    print(f"  Missing indexes: {len(missing_repos)}")
    
    print(f"\n\nWorking Repositories:")
    print("-" * 80)
    for i, repo in enumerate(working_repos[:10], 1):  # Show first 10
        info = repo['index_info']
        print(f"\n{i}. {repo['name']} ({repo['language']}/{repo['category']})")
        print(f"   Path: {repo['path']}")
        print(f"   Hash: {repo['hash']}")
        print(f"   Index: {info['path']}")
        print(f"   Size: {info['size_mb']:.1f} MB")
        print(f"   Files: {info['row_count']}")
        print(f"   Sample: {', '.join(info['sample_files'][:3])}")
        if 'note' in info:
            print(f"   Note: {info['note']}")
    
    if len(working_repos) > 10:
        print(f"\n... and {len(working_repos) - 10} more working repositories")
    
    # Save results
    results = {
        'working_repos': working_repos,
        'broken_repos': broken_repos,
        'missing_repos': missing_repos,
        'summary': {
            'total': len(test_repos),
            'working': len(working_repos),
            'broken': len(broken_repos),
            'missing': len(missing_repos)
        }
    }
    
    output_file = Path("PathUtils.get_workspace_root()/working_indexes_analysis.json")
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n\nResults saved to: {output_file}")
    
    # Recommend repositories for testing
    print(f"\n\nRecommended Test Repositories (diverse languages/sizes):")
    recommendations = []
    
    # Try to get diverse set
    languages_seen = set()
    for repo in working_repos:
        if repo['language'] not in languages_seen and len(recommendations) < 10:
            languages_seen.add(repo['language'])
            recommendations.append(repo)
    
    for i, repo in enumerate(recommendations, 1):
        print(f"{i}. {repo['name']} - {repo['language']} ({repo['index_info']['row_count']} files)")


if __name__ == "__main__":
    main()