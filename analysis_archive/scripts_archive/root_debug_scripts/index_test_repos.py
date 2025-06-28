#!/usr/bin/env python3
"""
Index all test repositories for MCP testing.
"""

import os
import sys
import subprocess
import hashlib
from pathlib import Path
import json

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.indexer.bm25_indexer import BM25Indexer

def find_test_repos():
    """Find all test repositories."""
    repos = []
    test_repos_dir = Path('test_repos')
    
    for category in ['web', 'modern', 'jvm', 'functional', 'other', 'systems']:
        cat_dir = test_repos_dir / category
        if cat_dir.exists():
            for lang_dir in cat_dir.iterdir():
                if lang_dir.is_dir():
                    for repo_dir in lang_dir.iterdir():
                        if repo_dir.is_dir() and (repo_dir / '.git').exists():
                            try:
                                # Store absolute path before changing directory
                                repo_abs_path = str(repo_dir.absolute())
                                os.chdir(repo_dir)
                                result = subprocess.run(['git', 'remote', 'get-url', 'origin'], 
                                                      capture_output=True, text=True)
                                if result.returncode == 0:
                                    url = result.stdout.strip()
                                    repo_hash = hashlib.sha256(url.encode()).hexdigest()[:12]
                                    repos.append({
                                        'name': repo_dir.name,
                                        'path': repo_abs_path,
                                        'category': category,
                                        'language': lang_dir.name,
                                        'url': url,
                                        'hash': repo_hash
                                    })
                            except Exception as e:
                                print(f"Error processing {repo_dir}: {e}")
                            finally:
                                os.chdir('/workspaces/Code-Index-MCP')
    
    return repos

def index_repository(repo):
    """Index a single repository using the dispatcher."""
    print(f"\n{'='*60}")
    print(f"Indexing: {repo['name']} ({repo['language']})")
    print(f"Path: {repo['path']}")
    print(f"Hash: {repo['hash']}")
    
    try:
        # Create index directory
        index_dir = Path('.indexes') / repo['hash']
        index_dir.mkdir(parents=True, exist_ok=True)
        
        # Create database path
        db_path = index_dir / 'code_index.db'
        
        # Remove old index if exists
        if db_path.exists():
            db_path.unlink()
        
        # Create SQLite store with absolute path
        store = SQLiteStore(str(db_path.absolute()))
        
        # Create repository record
        repo_id = store.create_repository(
            path=repo['path'],
            name=repo['name'],
            metadata={'remote_url': repo['url']}
        )
        
        # Change to repository directory for indexing
        old_cwd = os.getcwd()
        try:
            os.chdir(repo['path'])
            
            # Create dispatcher
            dispatcher = EnhancedDispatcher(
                plugins=[],
                sqlite_store=store,
                use_plugin_factory=True,
                lazy_load=False
            )
            
            # Index the repository
            print(f"Indexing files...")
            dispatcher.index_directory(Path('.'))
            
        finally:
            os.chdir(old_cwd)
        
        # Get statistics
        stats = store.get_statistics()
        
        print(f"Results:")
        print(f"  Files indexed: {stats.get('total_files', 0)}")
        print(f"  Symbols found: {stats.get('total_symbols', 0)}")
        
        # Now populate BM25 index
        print(f"Populating BM25 index...")
        bm25_indexer = BM25Indexer(store)
        
        # Get all files from the store
        with store._get_connection() as conn:
            cursor = conn.execute("SELECT id, path FROM files")
            files = cursor.fetchall()
        
        # Index each file content in BM25
        bm25_count = 0
        for file_id, file_path in files:
            try:
                # Try to read file content
                if os.path.exists(file_path) and os.path.isfile(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Extract basic metadata
                    metadata = {
                        'language': Path(file_path).suffix.lstrip('.') or 'text'
                    }
                    
                    # Add to BM25 index
                    bm25_indexer.add_document(file_path, content, metadata)
                    bm25_count += 1
            except Exception as e:
                # Skip files that can't be read
                pass
        
        # Optimize BM25 index
        bm25_indexer.optimize()
        
        print(f"  BM25 documents indexed: {bm25_count}")
        
        # Create current.db symlink
        current_link = index_dir / 'current.db'
        if current_link.exists():
            current_link.unlink()
        current_link.symlink_to('code_index.db')
        
        # Save metadata
        metadata = {
            'repository': repo['name'],
            'url': repo['url'],
            'hash': repo['hash'],
            'category': repo['category'],
            'language': repo['language'],
            'indexed_at': str(Path(repo['path']).stat().st_mtime),
            'stats': {
                'file_count': stats.get('total_files', 0),
                'symbol_count': stats.get('total_symbols', 0),
                'bm25_count': bm25_count
            }
        }
        
        with open(index_dir / 'metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return True, metadata['stats']
        
    except Exception as e:
        print(f"ERROR: Failed to index {repo['name']}: {e}")
        import traceback
        traceback.print_exc()
        return False, {'error': str(e)}

def main():
    """Main function."""
    print("Test Repository Indexing")
    print("=" * 80)
    
    # Find all test repos
    repos = find_test_repos()
    print(f"Found {len(repos)} test repositories")
    
    # Index each repo
    results = []
    successful = 0
    failed = 0
    
    # Index all repositories
    for repo in repos:
        success, stats = index_repository(repo)
        results.append({
            'repo': repo,
            'success': success,
            'stats': stats
        })
        
        if success:
            successful += 1
        else:
            failed += 1
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total repositories: {len(repos)}")
    print(f"Successfully indexed: {successful}")
    print(f"Failed: {failed}")
    
    # Save results
    with open('test_repo_indexing_results.json', 'w') as f:
        json.dump({
            'total': len(repos),
            'successful': successful,
            'failed': failed,
            'results': results
        }, f, indent=2)
    
    print("\nResults saved to test_repo_indexing_results.json")

if __name__ == "__main__":
    main()