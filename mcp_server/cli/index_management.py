"""
CLI commands for index management.

Provides convenient commands for managing SQLite and vector indexes.
"""

import os
import sys
import click
import json
from pathlib import Path
from typing import Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from mcp_server.utils.semantic_indexer import SemanticIndexer
from mcp_server.storage.sqlite_store import SQLiteStore


@click.group()
def index():
    """Index management commands."""
    pass


@index.command()
@click.option('--detailed', '-d', is_flag=True, help='Show detailed compatibility information')
def check_compatibility(detailed: bool):
    """Check if current configuration is compatible with existing indexes."""
    try:
        # Check vector index
        indexer = SemanticIndexer()
        vector_compatible = indexer.check_compatibility()
        
        # Check SQLite index
        sqlite_exists = os.path.exists("code_index.db")
        sqlite_compatible = True
        symbol_count = 0
        
        if sqlite_exists:
            try:
                store = SQLiteStore("code_index.db")
                with store._get_connection() as conn:
                    cursor = conn.execute("SELECT COUNT(*) FROM symbols")
                    symbol_count = cursor.fetchone()[0]
            except Exception as e:
                sqlite_compatible = False
                if detailed:
                    click.echo(f"SQLite error: {e}", err=True)
        
        # Check metadata
        metadata_exists = os.path.exists(".index_metadata.json")
        metadata = {}
        if metadata_exists:
            try:
                with open(".index_metadata.json", 'r') as f:
                    metadata = json.load(f)
            except Exception as e:
                if detailed:
                    click.echo(f"Metadata error: {e}", err=True)
        
        # Display results
        click.echo("Index Compatibility Status:")
        click.echo(f"  SQLite index: {'✅ Compatible' if sqlite_compatible else '❌ Incompatible'}")
        click.echo(f"  Vector index: {'✅ Compatible' if vector_compatible else '❌ Incompatible'}")
        click.echo(f"  Metadata: {'✅ Present' if metadata_exists else '❌ Missing'}")
        
        if sqlite_exists:
            click.echo(f"  Symbol count: {symbol_count:,}")
        
        if detailed and metadata:
            click.echo("\nMetadata details:")
            click.echo(f"  Embedding model: {metadata.get('embedding_model', 'unknown')}")
            click.echo(f"  Created: {metadata.get('created_at', 'unknown')}")
            click.echo(f"  Git commit: {metadata.get('git_commit', 'unknown')}")
        
        overall_compatible = sqlite_compatible and vector_compatible and metadata_exists
        click.echo(f"\nOverall: {'✅ All compatible' if overall_compatible else '❌ Issues found'}")
        
        sys.exit(0 if overall_compatible else 1)
        
    except Exception as e:
        click.echo(f"Error checking compatibility: {e}", err=True)
        sys.exit(1)


@index.command()
@click.option('--force', '-f', is_flag=True, help='Force rebuild even if compatible')
@click.option('--sqlite-only', is_flag=True, help='Rebuild SQLite index only')
@click.option('--vector-only', is_flag=True, help='Rebuild vector index only')
@click.option('--sample-size', default=100, help='Number of files to index (default: 100)')
def rebuild(force: bool, sqlite_only: bool, vector_only: bool, sample_size: int):
    """Rebuild index artifacts."""
    
    if not force:
        # Check if rebuild is needed
        try:
            indexer = SemanticIndexer()
            compatible = indexer.check_compatibility()
            if compatible and os.path.exists("code_index.db"):
                click.echo("Indexes appear compatible. Use --force to rebuild anyway.")
                return
        except Exception:
            pass  # Proceed with rebuild if check fails
    
    click.echo("Starting index rebuild...")
    
    if not sqlite_only:
        click.echo("Rebuilding vector index...")
        try:
            # Remove old vector index
            vector_path = "vector_index.qdrant"
            if os.path.exists(vector_path):
                import shutil
                shutil.rmtree(vector_path)
            
            # Create new vector index
            indexer = SemanticIndexer()
            
            # Find Python files to index
            import glob
            python_files = glob.glob("**/*.py", recursive=True)
            python_files = [f for f in python_files 
                          if not any(exclude in f for exclude in ["test_repos", ".git", "__pycache__", ".venv"])]
            
            if sample_size > 0:
                python_files = python_files[:sample_size]
            
            indexed_count = 0
            with click.progressbar(python_files, label='Indexing files') as files:
                for file_path in files:
                    try:
                        result = indexer.index_file(Path(file_path))
                        if result:
                            indexed_count += 1
                    except Exception as e:
                        if force:
                            continue  # Skip errors in force mode
                        else:
                            click.echo(f"\nError indexing {file_path}: {e}", err=True)
                            return
            
            click.echo(f"✅ Vector index rebuilt with {indexed_count} files")
            
        except Exception as e:
            click.echo(f"❌ Vector index rebuild failed: {e}", err=True)
            if not force:
                return
    
    if not vector_only:
        click.echo("Rebuilding SQLite index...")
        try:
            # Remove old SQLite index
            if os.path.exists("code_index.db"):
                os.remove("code_index.db")
            
            # Create new SQLite index
            store = SQLiteStore("code_index.db")
            click.echo("✅ SQLite index schema created")
            
            # TODO: Add actual file indexing here when dispatcher is available
            click.echo("Note: Run full indexing via the main application to populate SQLite index")
            
        except Exception as e:
            click.echo(f"❌ SQLite index rebuild failed: {e}", err=True)
            if not force:
                return
    
    click.echo("🎉 Index rebuild completed!")


@index.command()
def status():
    """Show current index status."""
    click.echo("Index Status Report")
    click.echo("=" * 30)
    
    # SQLite index
    sqlite_path = "code_index.db"
    if os.path.exists(sqlite_path):
        try:
            store = SQLiteStore(sqlite_path)
            with store._get_connection() as conn:
                # Get symbol count
                cursor = conn.execute("SELECT COUNT(*) FROM symbols")
                symbol_count = cursor.fetchone()[0]
                
                # Get file count
                cursor = conn.execute("SELECT COUNT(*) FROM files")
                file_count = cursor.fetchone()[0]
                
                # Get database size
                db_size = os.path.getsize(sqlite_path) / (1024 * 1024)  # MB
                
                click.echo(f"SQLite Index:")
                click.echo(f"  📁 Files indexed: {file_count:,}")
                click.echo(f"  🔍 Symbols found: {symbol_count:,}")
                click.echo(f"  💾 Database size: {db_size:.1f} MB")
                
        except Exception as e:
            click.echo(f"SQLite Index: ❌ Error reading ({e})")
    else:
        click.echo("SQLite Index: ❌ Not found")
    
    # Vector index
    vector_path = "vector_index.qdrant"
    if os.path.exists(vector_path):
        try:
            # Calculate directory size
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(vector_path):
                for filename in filenames:
                    total_size += os.path.getsize(os.path.join(dirpath, filename))
            
            vector_size = total_size / (1024 * 1024)  # MB
            
            # Try to get collection info
            indexer = SemanticIndexer()
            try:
                collections = indexer.qdrant.get_collections()
                collection_count = len(collections.collections)
                click.echo(f"Vector Index:")
                click.echo(f"  🧠 Collections: {collection_count}")
                click.echo(f"  💾 Storage size: {vector_size:.1f} MB")
            except Exception:
                click.echo(f"Vector Index:")
                click.echo(f"  💾 Storage size: {vector_size:.1f} MB")
                click.echo(f"  ⚠️ Could not read collection info")
            
        except Exception as e:
            click.echo(f"Vector Index: ❌ Error reading ({e})")
    else:
        click.echo("Vector Index: ❌ Not found")
    
    # Metadata
    metadata_path = ".index_metadata.json"
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            click.echo(f"Metadata:")
            click.echo(f"  🤖 Embedding model: {metadata.get('embedding_model', 'unknown')}")
            click.echo(f"  📅 Created: {metadata.get('created_at', 'unknown')}")
            click.echo(f"  🔗 Git commit: {metadata.get('git_commit', 'unknown')[:8]}...")
            
        except Exception as e:
            click.echo(f"Metadata: ❌ Error reading ({e})")
    else:
        click.echo("Metadata: ❌ Not found")


@index.command()
@click.argument('backup_dir')
def backup(backup_dir: str):
    """Create backup of current indexes."""
    import shutil
    from datetime import datetime
    
    if not backup_dir:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = f"index_backup_{timestamp}"
    
    os.makedirs(backup_dir, exist_ok=True)
    
    files_backed_up = 0
    
    # Backup SQLite index
    if os.path.exists("code_index.db"):
        shutil.copy2("code_index.db", f"{backup_dir}/code_index.db")
        files_backed_up += 1
        click.echo(f"📦 Backed up SQLite index")
    
    # Backup vector index
    if os.path.exists("vector_index.qdrant"):
        shutil.copytree("vector_index.qdrant", f"{backup_dir}/vector_index.qdrant")
        files_backed_up += 1
        click.echo(f"📦 Backed up vector index")
    
    # Backup metadata
    if os.path.exists(".index_metadata.json"):
        shutil.copy2(".index_metadata.json", f"{backup_dir}/.index_metadata.json")
        files_backed_up += 1
        click.echo(f"📦 Backed up metadata")
    
    if files_backed_up > 0:
        click.echo(f"✅ Backup completed: {backup_dir} ({files_backed_up} items)")
    else:
        click.echo("❌ No index files found to backup")


@index.command()
@click.argument('backup_dir')
def restore(backup_dir: str):
    """Restore indexes from backup."""
    import shutil
    
    if not os.path.exists(backup_dir):
        click.echo(f"❌ Backup directory not found: {backup_dir}")
        return
    
    click.echo(f"Restoring from backup: {backup_dir}")
    
    # Remove current indexes
    if os.path.exists("code_index.db"):
        os.remove("code_index.db")
        click.echo("🗑️ Removed current SQLite index")
    
    if os.path.exists("vector_index.qdrant"):
        shutil.rmtree("vector_index.qdrant")
        click.echo("🗑️ Removed current vector index")
    
    if os.path.exists(".index_metadata.json"):
        os.remove(".index_metadata.json")
        click.echo("🗑️ Removed current metadata")
    
    files_restored = 0
    
    # Restore SQLite index
    backup_sqlite = f"{backup_dir}/code_index.db"
    if os.path.exists(backup_sqlite):
        shutil.copy2(backup_sqlite, "code_index.db")
        files_restored += 1
        click.echo("♻️ Restored SQLite index")
    
    # Restore vector index
    backup_vector = f"{backup_dir}/vector_index.qdrant"
    if os.path.exists(backup_vector):
        shutil.copytree(backup_vector, "vector_index.qdrant")
        files_restored += 1
        click.echo("♻️ Restored vector index")
    
    # Restore metadata
    backup_metadata = f"{backup_dir}/.index_metadata.json"
    if os.path.exists(backup_metadata):
        shutil.copy2(backup_metadata, ".index_metadata.json")
        files_restored += 1
        click.echo("♻️ Restored metadata")
    
    if files_restored > 0:
        click.echo(f"✅ Restore completed ({files_restored} items)")
    else:
        click.echo("❌ No backup files found to restore")


if __name__ == '__main__':
    index()