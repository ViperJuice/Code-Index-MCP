#!/usr/bin/env python3
"""
Map all test repositories to their corresponding Qdrant databases.
Find all repos, all Qdrant DBs, and create a comprehensive mapping.
"""

import os
import json
import sqlite3
from pathlib import Path
from qdrant_client import QdrantClient
from collections import defaultdict
from mcp_server.core.path_utils import PathUtils

def find_all_repositories():
    """Find all test repositories in the workspace."""
    print("=" * 60)
    print("MAPPING REPOSITORIES TO QDRANT DATABASES")
    print("=" * 60)
    
    # Step 1: Find all test repositories
    print("\n1. FINDING ALL TEST REPOSITORIES:")
    test_repos_locations = [
        "PathUtils.get_workspace_root()/test_repos",
        "PathUtils.get_workspace_root()/test_indexes",
        "PathUtils.get_workspace_root()PathUtils.get_data_path() / test_repos"
    ]
    
    all_repos = {}
    
    for location in test_repos_locations:
        if Path(location).exists():
            print(f"\n📁 Checking {location}...")
            
            # Find repository directories
            for root, dirs, files in os.walk(location):
                # Look for indicators of a repo (e.g., .git, README, package.json, etc.)
                if any(indicator in files for indicator in ['.git', 'README.md', 'package.json', 'Cargo.toml', 'go.mod', 'pom.xml', 'build.gradle']):
                    repo_name = Path(root).name
                    repo_path = root
                    
                    # Try to identify language
                    language = "unknown"
                    if 'package.json' in files:
                        language = "javascript"
                    elif 'Cargo.toml' in files:
                        language = "rust"
                    elif 'go.mod' in files:
                        language = "go"
                    elif 'pom.xml' in files or 'build.gradle' in files:
                        language = "java"
                    elif 'requirements.txt' in files or 'setup.py' in files:
                        language = "python"
                    elif any(f.endswith('.csproj') for f in files):
                        language = "csharp"
                    
                    # Check parent directories for language hints
                    path_parts = Path(root).parts
                    for part in path_parts:
                        if part in ['python', 'javascript', 'typescript', 'java', 'go', 'rust', 'csharp', 'cpp', 'c']:
                            language = part
                            break
                    
                    all_repos[repo_path] = {
                        'name': repo_name,
                        'language': language,
                        'path': repo_path,
                        'location': location
                    }
    
    print(f"\nFound {len(all_repos)} repositories:")
    
    # Group by language
    by_language = defaultdict(list)
    for repo_info in all_repos.values():
        by_language[repo_info['language']].append(repo_info['name'])
    
    for lang, repos in sorted(by_language.items()):
        print(f"  {lang}: {len(repos)} repos")
        for repo in sorted(repos)[:3]:
            print(f"    - {repo}")
        if len(repos) > 3:
            print(f"    ... and {len(repos) - 3} more")
    
    # Step 2: Find all SQL indexes
    print("\n\n2. FINDING ALL SQL INDEXES:")
    indexes_dir = Path("PathUtils.get_workspace_root()/.indexes")
    sql_indexes = {}
    
    if indexes_dir.exists():
        for index_dir in indexes_dir.iterdir():
            if index_dir.is_dir() and index_dir.name not in ['qdrant', 'artifacts']:
                # Look for database files
                db_files = list(index_dir.glob("*.db"))
                if db_files:
                    sql_indexes[index_dir.name] = {
                        'path': str(index_dir),
                        'databases': [db.name for db in db_files],
                        'main_db': None
                    }
                    
                    # Find the main database
                    for db in db_files:
                        if db.name in ['current.db', 'main.db', 'index.db']:
                            sql_indexes[index_dir.name]['main_db'] = str(db)
                            break
                    
                    # If no main db found, use the largest one
                    if not sql_indexes[index_dir.name]['main_db'] and db_files:
                        largest_db = max(db_files, key=lambda x: x.stat().st_size)
                        sql_indexes[index_dir.name]['main_db'] = str(largest_db)
    
    print(f"Found {len(sql_indexes)} SQL indexes")
    
    # Step 3: Find all Qdrant collections
    print("\n\n3. FINDING ALL QDRANT COLLECTIONS:")
    qdrant_locations = [
        "PathUtils.get_workspace_root()/.indexes/qdrant/main.qdrant",
        "PathUtils.get_workspace_root()/vector_index.qdrant",
    ]
    
    all_collections = {}
    
    for qdrant_path in qdrant_locations:
        if Path(qdrant_path).exists():
            print(f"\n📊 Checking Qdrant at {qdrant_path}...")
            
            # Remove lock file
            lock_file = Path(qdrant_path) / ".lock"
            if lock_file.exists():
                try:
                    lock_file.unlink()
                except:
                    pass
            
            try:
                client = QdrantClient(path=qdrant_path)
                collections = client.get_collections()
                
                for collection in collections.collections:
                    info = client.get_collection(collection.name)
                    
                    # Sample to understand content
                    sample_info = {'files': [], 'repos': set()}
                    if info.points_count > 0:
                        sample = client.scroll(
                            collection_name=collection.name,
                            limit=20,
                            with_payload=True
                        )
                        
                        for point in sample[0]:
                            file_path = point.payload.get('file_path') or point.payload.get('file') or ''
                            repo = point.payload.get('repository') or ''
                            
                            if file_path:
                                sample_info['files'].append(file_path)
                            if repo:
                                sample_info['repos'].add(repo)
                    
                    all_collections[collection.name] = {
                        'path': qdrant_path,
                        'points': info.points_count,
                        'sample_files': sample_info['files'][:5],
                        'repositories': list(sample_info['repos'])
                    }
                    
            except Exception as e:
                print(f"  Error: {e}")
    
    print(f"\nFound {len(all_collections)} Qdrant collections:")
    for name, info in sorted(all_collections.items(), key=lambda x: x[1]['points'], reverse=True):
        if info['points'] > 0:
            print(f"  {name}: {info['points']} points")
            if info['repositories']:
                print(f"    Repos: {', '.join(info['repositories'][:3])}")
    
    # Step 4: Create mapping
    print("\n\n4. CREATING REPOSITORY TO DATABASE MAPPING:")
    
    # Try to match SQL indexes to repos
    repo_mapping = {}
    
    # Check repository registry if it exists
    registry_path = Path("PathUtils.get_workspace_root()/PathUtils.get_repo_registry_path()")
    if registry_path.exists():
        print("\n📋 Found repository registry!")
        with open(registry_path) as f:
            registry = json.load(f)
            
        for repo_id, repo_info in registry.items():
            # Handle both dict and string values
            if isinstance(repo_info, dict):
                print(f"\n  Repository: {repo_info.get('name', repo_id)}")
                print(f"    ID: {repo_id}")
                print(f"    Path: {repo_info.get('path', 'unknown')}")
            else:
                print(f"\n  Repository: {repo_id}")
                print(f"    ID: {repo_id}")
                print(f"    Path: {repo_info}")
            
            # Find SQL index
            if repo_id in sql_indexes:
                print(f"    ✅ SQL Index: {sql_indexes[repo_id]['main_db']}")
            else:
                print(f"    ❌ SQL Index: Not found")
            
            # Find Qdrant collection
            matching_collections = []
            for coll_name, coll_info in all_collections.items():
                if repo_id in coll_info['repositories'] or repo_id in coll_name:
                    matching_collections.append(coll_name)
            
            if matching_collections:
                print(f"    ✅ Qdrant: {', '.join(matching_collections)}")
            else:
                print(f"    ❌ Qdrant: Not found")
    
    # Step 5: Test a few mappings
    print("\n\n5. TESTING SAMPLE MAPPINGS:")
    
    # Pick a few repos to test
    test_repos = ['python_django', 'javascript_react', 'go_gin', 'rust_tokio']
    
    for repo_name in test_repos:
        print(f"\n🔍 Testing {repo_name}:")
        
        # Find SQL index
        sql_found = False
        for index_id, index_info in sql_indexes.items():
            if repo_name in index_id or index_id in repo_name:
                print(f"  SQL: {index_info['main_db']}")
                sql_found = True
                
                # Check if DB is accessible and has data
                if index_info['main_db'] and Path(index_info['main_db']).exists():
                    try:
                        conn = sqlite3.connect(index_info['main_db'])
                        cursor = conn.cursor()
                        cursor.execute("SELECT COUNT(*) FROM bm25_content")
                        count = cursor.fetchone()[0]
                        print(f"       Contains {count} documents")
                        conn.close()
                    except Exception as e:
                        print(f"       Error reading DB: {e}")
                break
        
        if not sql_found:
            print(f"  SQL: ❌ Not found")
        
        # Find Qdrant collection
        qdrant_found = False
        for coll_name, coll_info in all_collections.items():
            if repo_name in coll_name or any(repo_name in str(f) for f in coll_info['sample_files']):
                print(f"  Qdrant: {coll_name} ({coll_info['points']} points)")
                qdrant_found = True
                break
        
        if not qdrant_found:
            print(f"  Qdrant: ❌ Not found")
    
    # Save mapping to file
    mapping = {
        'repositories': all_repos,
        'sql_indexes': sql_indexes,
        'qdrant_collections': {k: {**v, 'sample_files': v['sample_files'][:2]} for k, v in all_collections.items()},
        'summary': {
            'total_repos': len(all_repos),
            'total_sql_indexes': len(sql_indexes),
            'total_qdrant_collections': len(all_collections),
            'populated_qdrant_collections': sum(1 for c in all_collections.values() if c['points'] > 0)
        }
    }
    
    output_path = Path("PathUtils.get_workspace_root()/repo_db_mapping.json")
    with open(output_path, 'w') as f:
        json.dump(mapping, f, indent=2)
    
    print(f"\n\n📄 Mapping saved to: {output_path}")
    
    print("\n" + "=" * 60)
    print("MAPPING COMPLETE")
    print("=" * 60)
    
    print(f"\n📊 SUMMARY:")
    print(f"  - Found {len(all_repos)} repositories")
    print(f"  - Found {len(sql_indexes)} SQL indexes")
    print(f"  - Found {len(all_collections)} Qdrant collections")
    print(f"  - Populated Qdrant collections: {sum(1 for c in all_collections.values() if c['points'] > 0)}")

if __name__ == "__main__":
    find_all_repositories()