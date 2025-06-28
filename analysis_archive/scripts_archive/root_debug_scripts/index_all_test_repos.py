#!/usr/bin/env python3
"""
Index all test repositories using the existing indexing infrastructure.
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
                                os.chdir(repo_dir)
                                result = subprocess.run(['git', 'remote', 'get-url', 'origin'], 
                                                      capture_output=True, text=True)
                                if result.returncode == 0:
                                    url = result.stdout.strip()
                                    repo_hash = hashlib.sha256(url.encode()).hexdigest()[:12]
                                    repos.append({
                                        'name': repo_dir.name,
                                        'path': str(repo_dir.absolute()),
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
        
        # Create SQLite store
        store = SQLiteStore(str(db_path))
        
        # Create dispatcher
        dispatcher = EnhancedDispatcher(
            plugins=[],
            sqlite_store=store,
            use_plugin_factory=True,
            lazy_load=False
        )
        
        # Index the repository
        print(f"Indexing files...")
        old_cwd = os.getcwd()
        try:
            os.chdir(repo['path'])
            dispatcher.index_directory('.')
        finally:
            os.chdir(old_cwd)
        
        # Get statistics
        stats = store.get_stats()
        
        print(f"Results:")
        print(f"  Files indexed: {stats.get('file_count', 0)}")
        print(f"  Symbols found: {stats.get('symbol_count', 0)}")
        
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
            'stats': stats
        }
        
        with open(index_dir / 'metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return True, stats
        
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
    
    # Start with just a few for testing
    for i, repo in enumerate(repos[:5]):  # Only first 5 for now
        print(f"\nProcessing {i+1}/5...")
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
    print(f"Total processed: 5")
    print(f"Successfully indexed: {successful}")
    print(f"Failed: {failed}")
    
    # Save results
    with open('test_repo_indexing_results.json', 'w') as f:
        json.dump({
            'total': len(repos),
            'processed': 5,
            'successful': successful,
            'failed': failed,
            'results': results
        }, f, indent=2)
    
    print("\nResults saved to test_repo_indexing_results.json")
    
    if successful == 5:
        print("\nAll test repositories indexed successfully!")
        print(f"Run again with all {len(repos)} repositories by removing the [:5] limit")

if __name__ == "__main__":
    main()