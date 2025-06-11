#!/usr/bin/env python3
"""Quick BM25 index population script."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_server.indexer.bm25_indexer import BM25Indexer
from mcp_server.storage.sqlite_store import SQLiteStore
import asyncio

def main():
    print("🚀 Starting BM25 index population...")
    
    # Initialize components
    store = SQLiteStore("code_index.db")
    indexer = BM25Indexer(store)
    
    # Get all indexed files from main index
    print("📂 Fetching indexed files...")
    import sqlite3
    conn = sqlite3.connect("code_index.db")
    cursor = conn.cursor()
    cursor.execute("SELECT file_path, content, language, type FROM files WHERE content IS NOT NULL LIMIT 10000")
    results = cursor.fetchall()
    print(f"Found {len(results)} files to index")
    
    # Index each file
    indexed_count = 0
    for i, (file_path, content, language, type_) in enumerate(results):
        if i % 100 == 0:
            print(f"Progress: {i}/{len(results)} files...")
            
        try:
            if file_path and content:
                indexer.add_document(
                    doc_id=str(hash(file_path)),
                    content=content,
                    metadata={
                        'file_path': file_path,
                        'language': language or 'unknown',
                        'type': type_ or 'unknown'
                    }
                )
                indexed_count += 1
        except Exception as e:
            print(f"Error indexing {file_path}: {e}")
    
    print(f"✅ Successfully indexed {indexed_count} files into BM25 index")
    conn.close()
    
    # Test the index
    print("\n🧪 Testing BM25 search...")
    test_results = indexer.search("reranking", limit=5)
    print(f"Found {len(test_results)} results for 'reranking'")
    for r in test_results[:3]:
        print(f"  - {r.get('file_path')}: {r.get('score', 0):.2f}")

if __name__ == "__main__":
    main()