#!/usr/bin/env python3
"""
Simple BM25 indexing for test repositories.
"""

import os
import sys
import subprocess
import hashlib
from pathlib import Path
import json
import sqlite3

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.indexer.bm25_indexer import BM25Indexer
from mcp_server.core.ignore_patterns import get_ignore_manager

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

def create_simple_index(repo):
    """Create a simple BM25 index for a repository."""
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
        
        # Create database with minimal schema
        conn = sqlite3.connect(str(db_path))
        
        # Create minimal tables
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS repositories (
                id INTEGER PRIMARY KEY,
                path TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL
            );
            
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY,
                path TEXT UNIQUE NOT NULL,
                repository_id INTEGER,
                language TEXT,
                FOREIGN KEY (repository_id) REFERENCES repositories(id)
            );
            
            CREATE VIRTUAL TABLE IF NOT EXISTS bm25_content USING fts5(
                file_id UNINDEXED,
                filepath,
                filename,
                content,
                language,
                symbols,
                imports,
                comments,
                tokenize = 'porter unicode61',
                prefix = '2 3'
            );
            
            CREATE TABLE IF NOT EXISTS bm25_index_status (
                file_id INTEGER PRIMARY KEY,
                filepath TEXT NOT NULL,
                content_hash TEXT,
                indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Insert repository
        cursor = conn.execute(
            "INSERT INTO repositories (path, name) VALUES (?, ?)",
            (repo['path'], repo['name'])
        )
        repo_id = cursor.lastrowid
        conn.commit()
        
        # Walk through files and index
        repo_path = Path(repo['path'])
        ignore_manager = get_ignore_manager(repo_path)
        
        indexed = 0
        skipped = 0
        errors = 0
        
        for file_path in repo_path.rglob('*'):
            if file_path.is_file():
                # Skip ignored files
                if ignore_manager.should_ignore(file_path):
                    skipped += 1
                    continue
                
                # Skip binary files and large files
                try:
                    if file_path.stat().st_size > 1_000_000:  # 1MB
                        skipped += 1
                        continue
                        
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Insert file record
                    file_path_str = str(file_path)
                    language = file_path.suffix.lstrip('.') or 'text'
                    
                    cursor = conn.execute(
                        "INSERT INTO files (path, repository_id, language) VALUES (?, ?, ?)",
                        (file_path_str, repo_id, language)
                    )
                    file_id = cursor.lastrowid
                    
                    # Insert into BM25 index
                    conn.execute("""
                        INSERT INTO bm25_content 
                        (file_id, filepath, filename, content, language, symbols, imports, comments)
                        VALUES (?, ?, ?, ?, ?, '', '', '')
                    """, (file_id, file_path_str, file_path.name, content, language))
                    
                    indexed += 1
                    
                    # Commit every 100 files
                    if indexed % 100 == 0:
                        conn.commit()
                        print(f"  Indexed {indexed} files...")
                        
                except Exception as e:
                    errors += 1
                    if errors <= 5:
                        print(f"  Error: {e}")
        
        # Final commit
        conn.commit()
        
        # Get final count
        cursor = conn.execute("SELECT COUNT(*) FROM bm25_content")
        bm25_count = cursor.fetchone()[0]
        
        conn.close()
        
        print(f"Results:")
        print(f"  Files indexed: {indexed}")
        print(f"  Files skipped: {skipped}")
        print(f"  Errors: {errors}")
        print(f"  BM25 entries: {bm25_count}")
        
        # Create SQLite store to initialize remaining tables
        store = SQLiteStore(str(db_path.absolute()))
        
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
            'stats': {
                'indexed': indexed,
                'skipped': skipped,
                'errors': errors,
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
    print("Simple BM25 Test Repository Indexing")
    print("=" * 80)
    
    # Find all test repos
    repos = find_test_repos()
    print(f"Found {len(repos)} test repositories")
    
    # Index each repo
    results = []
    successful = 0
    failed = 0
    
    for i, repo in enumerate(repos):
        print(f"\nProcessing {i+1}/{len(repos)}...")
        success, stats = create_simple_index(repo)
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
    with open('simple_indexing_results.json', 'w') as f:
        json.dump({
            'total': len(repos),
            'successful': successful,
            'failed': failed,
            'results': results
        }, f, indent=2)
    
    print("\nResults saved to simple_indexing_results.json")

if __name__ == "__main__":
    main()