#!/usr/bin/env python3
"""
Script to reindex the current repository with proper paths
"""
import os
import sys
import sqlite3
from pathlib import Path
from mcp_server.core.path_utils import PathUtils

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.indexer.bm25_indexer import BM25Indexer

def main():
    # Repository path
    repo_path = Path("PathUtils.get_workspace_root()")
    
    # Index path (same as used by MCP)
    index_db_path = repo_path / ".indexes" / "f7b49f5d0ae0" / "new_index.db"
    
    print(f"Reindexing repository: {repo_path}")
    print(f"Index database: {index_db_path}")
    
    # Create SQLiteStore
    store = SQLiteStore(str(index_db_path))
    
    # Clear existing BM25 content for repository 2
    conn = sqlite3.connect(str(index_db_path))
    cursor = conn.cursor()
    
    # Get repository ID for current repo
    cursor.execute("SELECT id FROM repositories WHERE path = ?", (str(repo_path),))
    result = cursor.fetchone()
    if result:
        repo_id = result[0]
        print(f"Found repository ID: {repo_id}")
    else:
        # Insert repository
        cursor.execute(
            "INSERT OR REPLACE INTO repositories (path, name) VALUES (?, ?)",
            (str(repo_path), "Code-Index-MCP")
        )
        repo_id = cursor.lastrowid
        print(f"Created repository ID: {repo_id}")
        conn.commit()
    
    # Clear old BM25 content
    cursor.execute("DELETE FROM bm25_content WHERE filepath LIKE 'PathUtils.get_workspace_root() / %'")
    deleted = cursor.rowcount
    print(f"Cleared {deleted} old entries from bm25_content")
    conn.commit()
    conn.close()
    
    # Create BM25 indexer
    indexer = BM25Indexer(store, "bm25_content")
    
    # Walk through repository and index files
    indexed_count = 0
    error_count = 0
    
    for root, dirs, files in os.walk(repo_path):
        # Skip hidden directories and common exclusions
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in [
            '__pycache__', 'node_modules', 'venv', 'env', '.git', 
            'vector_index.qdrant', 'test_results', 'coverage_html'
        ]]
        
        for file in files:
            # Index various file types
            if file.endswith((
                '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.h',
                '.cs', '.go', '.rs', '.rb', '.php', '.swift', '.kt', '.scala',
                '.md', '.txt', '.json', '.yaml', '.yml', '.toml', '.ini', '.cfg'
            )):
                file_path = Path(root) / file
                relative_path = file_path.relative_to(repo_path)
                
                try:
                    # Read file content
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                    
                    # Determine language
                    ext = file_path.suffix.lower()
                    language_map = {
                        '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
                        '.java': 'java', '.cpp': 'cpp', '.c': 'c', '.h': 'c',
                        '.cs': 'csharp', '.go': 'go', '.rs': 'rust', '.rb': 'ruby',
                        '.php': 'php', '.swift': 'swift', '.kt': 'kotlin',
                        '.md': 'markdown', '.txt': 'text', '.json': 'json',
                        '.yaml': 'yaml', '.yml': 'yaml'
                    }
                    language = language_map.get(ext, 'text')
                    
                    # Add to BM25 index
                    doc_data = {
                        'filepath': str(file_path),
                        'filename': file,  # Just use the filename string
                        'content': content,
                        'language': language,
                        'symbols': '',  # Would need proper parsing
                        'imports': '',  # Would need proper parsing
                        'comments': ''  # Would need proper parsing
                    }
                    
                    # Insert into database
                    conn = sqlite3.connect(str(index_db_path))
                    cursor = conn.cursor()
                    
                    # First, insert into files table if not exists
                    cursor.execute("""
                        INSERT OR IGNORE INTO files (repository_id, path, relative_path, language, size)
                        VALUES (?, ?, ?, ?, ?)
                    """, (repo_id, str(file_path), str(relative_path), language, len(content)))
                    
                    file_id = cursor.lastrowid
                    if file_id == 0:
                        cursor.execute("SELECT id FROM files WHERE path = ?", (str(file_path),))
                        file_id = cursor.fetchone()[0]
                    
                    # Insert into BM25 content
                    cursor.execute(f"""
                        INSERT OR REPLACE INTO bm25_content 
                        (file_id, filepath, filename, content, language, symbols, imports, comments)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (file_id, str(file_path), file, content, language, '', '', ''))
                    
                    conn.commit()
                    conn.close()
                    
                    indexed_count += 1
                    if indexed_count % 100 == 0:
                        print(f"  Indexed {indexed_count} files...")
                        
                except Exception as e:
                    error_count += 1
                    if error_count < 5:
                        print(f"  Error indexing {file_path}: {e}")
    
    print(f"\nIndexing complete!")
    print(f"  Total files indexed: {indexed_count}")
    print(f"  Errors encountered: {error_count}")
    
    # Verify the index
    conn = sqlite3.connect(str(index_db_path))
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM bm25_content WHERE filepath LIKE '/workspaces/%'")
    workspace_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM bm25_content")
    total_count = cursor.fetchone()[0]
    
    print(f"\nIndex verification:")
    print(f"  Files from /workspaces: {workspace_count}")
    print(f"  Total files in index: {total_count}")
    
    # Test search for BM25Indexer
    cursor.execute("""
        SELECT filepath, snippet(bm25_content, -1, '', '', '...', 20)
        FROM bm25_content
        WHERE bm25_content MATCH 'class BM25Indexer'
        LIMIT 5
    """)
    
    results = cursor.fetchall()
    print(f"\nTest search for 'class BM25Indexer':")
    for path, snippet in results:
        print(f"  - {path}")
        print(f"    {snippet}")
    
    conn.close()

if __name__ == "__main__":
    main()