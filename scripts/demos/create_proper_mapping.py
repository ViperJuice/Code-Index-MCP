#!/usr/bin/env python3
"""
Create a proper mapping between repositories, SQL indexes, and Qdrant collections.
"""

import os
import json
import sqlite3
from pathlib import Path
from qdrant_client import QdrantClient
import hashlib
from mcp_server.core.path_utils import PathUtils

def create_proper_mapping():
    """Create proper mapping between repos and databases."""
    print("=" * 60)
    print("CREATING PROPER REPOSITORY DATABASE MAPPING")
    print("=" * 60)
    
    # Step 1: Map SQL indexes to their repositories
    print("\n1. MAPPING SQL INDEXES TO REPOSITORIES:")
    indexes_dir = Path("PathUtils.get_workspace_root()/.indexes")
    
    index_mapping = {}
    
    for index_dir in sorted(indexes_dir.iterdir()):
        if index_dir.is_dir() and len(index_dir.name) == 12 and index_dir.name not in ['qdrant', 'artifacts']:
            # Find main database
            db_path = None
            for db_name in ['current.db', 'new_index.db', 'main.db', 'index.db']:
                potential_db = index_dir / db_name
                if potential_db.exists():
                    db_path = potential_db
                    break
            
            if not db_path:
                # Find any .db file
                db_files = list(index_dir.glob("*.db"))
                if db_files:
                    db_path = max(db_files, key=lambda x: x.stat().st_size)
            
            if db_path and db_path.exists():
                try:
                    # Connect and sample the database
                    conn = sqlite3.connect(str(db_path))
                    cursor = conn.cursor()
                    
                    # Get document count
                    cursor.execute("SELECT COUNT(*) FROM bm25_content")
                    doc_count = cursor.fetchone()[0]
                    
                    # Sample file paths to identify repository
                    cursor.execute("SELECT DISTINCT filepath FROM bm25_content LIMIT 10")
                    sample_paths = [row[0] for row in cursor.fetchall()]
                    
                    conn.close()
                    
                    # Try to identify repository from paths
                    repo_name = "unknown"
                    repo_lang = "unknown"
                    
                    for path in sample_paths:
                        path_lower = path.lower()
                        
                        # Check for known repo patterns
                        if 'django' in path_lower:
                            repo_name = "django"
                            repo_lang = "python"
                            break
                        elif 'react' in path_lower:
                            repo_name = "react"
                            repo_lang = "javascript"
                            break
                        elif 'typescript' in path_lower:
                            repo_name = "typescript"
                            repo_lang = "typescript"
                            break
                        elif 'aspnetcore' in path_lower:
                            repo_name = "aspnetcore"
                            repo_lang = "csharp"
                            break
                        elif 'gin' in path_lower and 'go' in path_lower:
                            repo_name = "gin"
                            repo_lang = "go"
                            break
                        elif 'tokio' in path_lower:
                            repo_name = "tokio"
                            repo_lang = "rust"
                            break
                        elif 'kafka' in path_lower:
                            repo_name = "kafka"
                            repo_lang = "java"
                            break
                        elif 'grpc' in path_lower:
                            repo_name = "grpc"
                            repo_lang = "cpp"
                            break
                        elif 'redis' in path_lower and '.c' in path_lower:
                            repo_name = "redis"
                            repo_lang = "c"
                            break
                    
                    index_mapping[index_dir.name] = {
                        'path': str(db_path),
                        'documents': doc_count,
                        'repo_name': repo_name,
                        'language': repo_lang,
                        'sample_paths': sample_paths[:3]
                    }
                    
                    print(f"\n  Index: {index_dir.name}")
                    print(f"    Documents: {doc_count}")
                    print(f"    Identified as: {repo_name} ({repo_lang})")
                    
                except Exception as e:
                    print(f"  Error reading {index_dir.name}: {e}")
    
    # Step 2: Check Qdrant collections for semantic embeddings
    print("\n\n2. CHECKING QDRANT COLLECTIONS:")
    
    qdrant_mapping = {}
    qdrant_paths = [
        "PathUtils.get_workspace_root()/.indexes/qdrant/main.qdrant",
        "PathUtils.get_workspace_root()/vector_index.qdrant"
    ]
    
    for qdrant_path in qdrant_paths:
        if not Path(qdrant_path).exists():
            continue
            
        # Remove lock
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
                
                if info.points_count > 0:
                    # Sample to identify content
                    sample = client.scroll(
                        collection_name=collection.name,
                        limit=10,
                        with_payload=True
                    )
                    
                    repo_hint = "unknown"
                    sample_files = []
                    
                    if sample[0]:
                        for point in sample[0]:
                            file_path = (
                                point.payload.get('file_path') or
                                point.payload.get('file') or
                                point.payload.get('filepath') or
                                ""
                            )
                            if file_path:
                                sample_files.append(file_path)
                                
                                # Try to identify repo
                                path_lower = file_path.lower()
                                if 'typescript' in path_lower:
                                    repo_hint = "typescript"
                                elif 'django' in path_lower:
                                    repo_hint = "django"
                                elif 'react' in path_lower:
                                    repo_hint = "react"
                    
                    qdrant_mapping[collection.name] = {
                        'path': qdrant_path,
                        'points': info.points_count,
                        'repo_hint': repo_hint,
                        'sample_files': sample_files[:3]
                    }
                    
                    print(f"\n  Collection: {collection.name}")
                    print(f"    Points: {info.points_count}")
                    print(f"    Repo hint: {repo_hint}")
                    
        except Exception as e:
            print(f"  Error reading Qdrant at {qdrant_path}: {e}")
    
    # Step 3: Create final mapping for key repositories
    print("\n\n3. FINAL REPOSITORY MAPPING:")
    
    # Key repositories for testing
    key_repos = [
        ('python_django', 'python', ['django']),
        ('javascript_react', 'javascript', ['react']),
        ('typescript_typescript', 'typescript', ['typescript']),
        ('go_gin', 'go', ['gin']),
        ('rust_tokio', 'rust', ['tokio']),
        ('java_kafka', 'java', ['kafka']),
        ('csharp_aspnetcore', 'csharp', ['aspnetcore', 'aspnet']),
        ('cpp_grpc', 'cpp', ['grpc']),
        ('c_redis', 'c', ['redis'])
    ]
    
    final_mapping = {}
    
    for repo_id, language, patterns in key_repos:
        print(f"\n  {repo_id}:")
        
        # Find SQL index
        sql_index = None
        for index_id, index_info in index_mapping.items():
            if any(pattern in index_info['repo_name'].lower() for pattern in patterns):
                sql_index = index_id
                print(f"    ✅ SQL: {index_id} ({index_info['documents']} docs)")
                break
        
        if not sql_index:
            # Try broader search
            for index_id, index_info in index_mapping.items():
                if any(any(pattern in path.lower() for pattern in patterns) 
                      for path in index_info['sample_paths']):
                    sql_index = index_id
                    print(f"    ✅ SQL: {index_id} ({index_info['documents']} docs) [path match]")
                    break
        
        if not sql_index:
            print(f"    ❌ SQL: Not found")
        
        # Find Qdrant collection
        qdrant_collection = None
        for coll_name, coll_info in qdrant_mapping.items():
            if any(pattern in coll_name.lower() or pattern in coll_info['repo_hint'].lower() 
                  for pattern in patterns):
                qdrant_collection = coll_name
                print(f"    ✅ Qdrant: {coll_name} ({coll_info['points']} points)")
                break
        
        if not qdrant_collection:
            print(f"    ❌ Qdrant: Not found")
        
        final_mapping[repo_id] = {
            'language': language,
            'sql_index': sql_index,
            'sql_path': index_mapping.get(sql_index, {}).get('path') if sql_index else None,
            'qdrant_collection': qdrant_collection,
            'qdrant_path': qdrant_mapping.get(qdrant_collection, {}).get('path') if qdrant_collection else None
        }
    
    # Save comprehensive mapping
    output = {
        'sql_indexes': index_mapping,
        'qdrant_collections': qdrant_mapping,
        'repository_mapping': final_mapping,
        'summary': {
            'total_sql_indexes': len(index_mapping),
            'total_qdrant_collections': len(qdrant_mapping),
            'mapped_repositories': len([r for r in final_mapping.values() if r['sql_index']])
        }
    }
    
    output_path = Path("PathUtils.get_workspace_root()/proper_repo_mapping.json")
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n\n📄 Mapping saved to: {output_path}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("MAPPING COMPLETE")
    print("=" * 60)
    
    print(f"\n📊 SUMMARY:")
    print(f"  - SQL indexes found: {len(index_mapping)}")
    print(f"  - Qdrant collections found: {len(qdrant_mapping)}")
    print(f"  - Key repositories mapped: {len([r for r in final_mapping.values() if r['sql_index']])}")
    
    # Show which repos are ready for testing
    print(f"\n✅ REPOSITORIES READY FOR TESTING (have SQL index):")
    for repo_id, info in final_mapping.items():
        if info['sql_index']:
            has_qdrant = "✅" if info['qdrant_collection'] else "❌"
            print(f"  - {repo_id} (Qdrant: {has_qdrant})")

if __name__ == "__main__":
    create_proper_mapping()