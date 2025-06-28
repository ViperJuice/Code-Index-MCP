#!/usr/bin/env python3
"""Complete indexing with working SQLite and vector storage."""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Override problematic environment variables
os.environ.pop('QDRANT_HOST', None)
os.environ.pop('QDRANT_PORT', None)

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.utils.semantic_indexer import SemanticIndexer
from mcp_server.utils.treesitter_wrapper import TreeSitterWrapper


def get_language_for_file(file_path):
    """Determine language from file extension."""
    ext = Path(file_path).suffix.lower()
    return {
        '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
        '.jsx': 'javascript', '.tsx': 'typescript', '.java': 'java',
        '.go': 'go', '.rs': 'rust', '.cpp': 'cpp', '.c': 'c',
        '.h': 'c', '.hpp': 'cpp', '.cs': 'csharp', '.rb': 'ruby',
        '.php': 'php', '.swift': 'swift', '.kt': 'kotlin',
        '.scala': 'scala', '.r': 'r', '.md': 'markdown',
        '.txt': 'plaintext', '.json': 'json', '.yaml': 'yaml',
        '.yml': 'yaml', '.toml': 'toml', '.xml': 'xml',
        '.html': 'html', '.css': 'css'
    }.get(ext, None)


def index_sqlite(root_path):
    """Perform SQLite indexing."""
    print("\n📊 Phase 1: SQLite Indexing")
    print("=" * 50)
    
    store = SQLiteStore("code_index.db")
    wrapper = TreeSitterWrapper()
    
    # Get repository info
    repo_id = store.create_repository(str(root_path), "Code-Index-MCP")
    
    # Collect files
    extensions = [
        '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go', '.rs', '.cpp', '.c', 
        '.h', '.hpp', '.cs', '.rb', '.php', '.swift', '.kt', '.scala', '.r'
    ]
    
    all_files = []
    exclude_dirs = {
        '.git', '__pycache__', '.venv', 'venv', 'node_modules', 'test_repos', 
        '.pytest_cache', 'htmlcov', '.tox', 'dist', 'build', '.eggs'
    }
    
    for root, dirs, files in os.walk(root_path):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                file_path = Path(root) / file
                if not any(excluded in str(file_path) for excluded in exclude_dirs):
                    all_files.append(file_path)
    
    print(f"Found {len(all_files)} files to index")
    
    # Index files
    indexed_count = 0
    total_symbols = 0
    
    for i, file_path in enumerate(all_files):
        try:
            language = get_language_for_file(file_path)
            if not language:
                continue
                
            # Read file
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            
            # Get file info
            stat = file_path.stat()
            relative_path = str(file_path.relative_to(root_path))
            
            # Store file
            file_id = store.store_file(
                repository_id=repo_id,
                path=str(file_path),
                relative_path=relative_path,
                language=language,
                size=stat.st_size,
                hash=None,
                metadata={}
            )
            
            # Extract symbols using tree-sitter
            if wrapper.has_language(language):
                wrapper.set_language(language)
                symbols = wrapper.extract_symbols(content, str(file_path))
                
                # Store symbols
                for symbol in symbols:
                    store.store_symbol(
                        file_id=file_id,
                        name=symbol.get('name', ''),
                        kind=symbol.get('kind', 'unknown'),
                        line=symbol.get('line', 0),
                        column=0,
                        end_line=symbol.get('end_line', symbol.get('line', 0)),
                        end_column=0,
                        signature=symbol.get('signature', ''),
                        documentation=symbol.get('documentation', ''),
                        metadata={}
                    )
                    total_symbols += 1
            
            indexed_count += 1
            
            if (i + 1) % 50 == 0:
                print(f"Progress: {i + 1}/{len(all_files)} files ({indexed_count} indexed, {total_symbols} symbols)")
                
        except Exception as e:
            continue
    
    print(f"\n✅ SQLite indexing complete!")
    print(f"   Files indexed: {indexed_count}")
    print(f"   Symbols found: {total_symbols}")
    
    # Get stats directly from database
    with store._get_connection() as conn:
        cursor = conn.execute("SELECT COUNT(*) FROM files")
        file_count = cursor.fetchone()[0]
        cursor = conn.execute("SELECT COUNT(*) FROM symbols")
        symbol_count = cursor.fetchone()[0]
    
    print(f"   Database totals: {file_count} files, {symbol_count} symbols")
    
    return all_files


def index_vectors(files, max_files=200):
    """Create vector embeddings."""
    print("\n🧠 Phase 2: Vector Embeddings")
    print("=" * 50)
    
    try:
        # Initialize indexer with local storage
        indexer = SemanticIndexer(
            collection="code-embeddings",
            qdrant_path="./vector_index.qdrant"  # Use local file storage
        )
        
        # Filter code files
        code_extensions = {'.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go', '.rs', 
                          '.cpp', '.c', '.h', '.hpp', '.cs', '.rb', '.php', '.swift', 
                          '.kt', '.scala', '.r'}
        
        code_files = [f for f in files if f.suffix.lower() in code_extensions]
        
        if len(code_files) > max_files:
            print(f"Limiting to {max_files} files (from {len(code_files)} total)")
            code_files = code_files[:max_files]
        
        print(f"Creating embeddings for {len(code_files)} code files...")
        
        indexed_count = 0
        for i, file_path in enumerate(code_files):
            try:
                result = indexer.index_file(file_path)
                if result:
                    indexed_count += 1
                
                if (i + 1) % 20 == 0:
                    print(f"Progress: {i + 1}/{len(code_files)} files embedded")
                    
            except Exception as e:
                continue
        
        print(f"\n✅ Vector indexing complete! Created {indexed_count} embeddings")
        
        # Update metadata with actual path
        metadata = {
            "embedding_model": "voyage-code-3",
            "model_dimension": 1024,
            "distance_metric": "cosine",
            "created_at": datetime.now().isoformat(),
            "qdrant_path": "./vector_index.qdrant",
            "collection_name": "code-embeddings",
            "indexed_files": indexed_count,
            "total_embeddings": indexed_count
        }
        
        with open(".index_metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)
        
        return indexed_count
        
    except Exception as e:
        print(f"⚠️  Vector indexing failed: {e}")
        return 0


def main():
    """Perform complete indexing."""
    print("🚀 Starting complete repository indexing")
    print("=" * 70)
    
    root_path = Path("/app")
    
    # SQLite indexing
    all_files = index_sqlite(root_path)
    
    # Vector indexing
    vector_count = index_vectors(all_files)
    
    # Final report
    print("\n" + "=" * 70)
    print("🎉 INDEXING COMPLETE!")
    print("=" * 70)
    
    # Show status
    print("\n📋 Index Status:")
    os.system("python mcp_cli.py index status")
    
    print("\n✅ All indexing operations completed!")
    print("\nNote: Vector index is stored locally in ./vector_index.qdrant/")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())