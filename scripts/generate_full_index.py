
import os
import sys
import shutil
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))

from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.utils.semantic_indexer import SemanticIndexer
from mcp_server.plugins.python_plugin.plugin import Plugin as PythonPlugin

def generate_index():
    print("🚀 Starting Full Index Generation...")
    
    # Configuration
    db_path = Path("code_index.db")
    qdrant_path = "vector_index.qdrant"
    
    # Clean old indexes
    if db_path.exists():
        os.remove(db_path)
    if Path(qdrant_path).exists():
        shutil.rmtree(qdrant_path)
        
    # Check API Key for Semantic
    semantic_enabled = "VOYAGE_AI_API_KEY" in os.environ
    if not semantic_enabled:
        print("⚠️ VOYAGE_AI_API_KEY not found. Skipping semantic indexing.")
        
    # Initialize Storage
    print(f"🔹 Initializing SQLiteStore at {db_path}...")
    store = SQLiteStore(str(db_path))
    
    # Initialize Plugins/Indexers
    python_plugin = PythonPlugin(sqlite_store=store)
    
    semantic_indexer = None
    if semantic_enabled:
        print(f"🔹 Initializing SemanticIndexer at {qdrant_path}...")
        # Use file-based Qdrant for artifact
        semantic_indexer = SemanticIndexer(qdrant_path=qdrant_path, collection="code-index")
    
    # Index Files
    print("🔹 Indexing files...")
    count = 0
    # Index current directory (project root) recursively
    for file_path in Path(".").rglob("*.py"):
        # Exclude common ignores
        if any(part.startswith(".") for part in file_path.parts): continue
        if "venv" in file_path.parts: continue
        if "__pycache__" in file_path.parts: continue
        
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            abs_path = file_path.resolve()
            
            # 1. SQLite FTS
            python_plugin.indexFile(abs_path, content)
            
            # 2. Semantic
            if semantic_indexer:
                semantic_indexer.index_file(abs_path)
                
            count += 1
            if count % 10 == 0:
                print(f"   Indexed {count} files...")
                
        except Exception as e:
            print(f"   ❌ Error indexing {file_path}: {e}")
            
    print(f"✅ Indexing complete. Total files: {count}")
    
    # Create Metadata
    import json
    import subprocess
    from datetime import datetime
    
    commit = "unknown"
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
    except: pass
    
    metadata = {
        "timestamp": datetime.utcnow().isoformat(),
        "commit": commit,
        "file_count": count,
        "semantic_enabled": semantic_enabled
    }
    
    with open(".index_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
        
    print("✅ Metadata created.")

if __name__ == "__main__":
    generate_index()
