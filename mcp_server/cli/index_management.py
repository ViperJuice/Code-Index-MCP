"""
CLI commands for index management.

Provides convenient commands for managing SQLite and vector indexes.
"""

import json
import os
import sys
from pathlib import Path

import click

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from mcp_server.storage.sqlite_store import SQLiteStore  # noqa: E402
from mcp_server.utils import get_semantic_indexer  # noqa: E402


def _get_semantic_indexer_instance():
    """Get SemanticIndexer instance if available."""
    SemanticIndexer = get_semantic_indexer()
    if SemanticIndexer is None:
        return None
    try:
        return SemanticIndexer()
    except Exception:
        return None


@click.group()
def index():
    """Index management commands."""


@index.command()
@click.option(
    "--detailed", "-d", is_flag=True, help="Show detailed compatibility information"
)
def check_compatibility(detailed: bool):
    """Check if current configuration is compatible with existing indexes."""
    try:
        # Check vector index
        indexer = _get_semantic_indexer_instance()
        vector_compatible = indexer.check_compatibility() if indexer else False
        vector_available = indexer is not None

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
                with open(".index_metadata.json", "r") as f:
                    metadata = json.load(f)
            except Exception as e:
                if detailed:
                    click.echo(f"Metadata error: {e}", err=True)

        # Display results
        click.echo("Index Compatibility Status:")
        click.echo(
            f"  SQLite index: {'✅ Compatible' if sqlite_compatible else '❌ Incompatible'}"
        )
        if not vector_available:
            click.echo("  Vector index: ⚠️ Not available (semantic deps not installed)")
        else:
            click.echo(
                f"  Vector index: {'✅ Compatible' if vector_compatible else '❌ Incompatible'}"
            )
        click.echo(f"  Metadata: {'✅ Present' if metadata_exists else '❌ Missing'}")

        if sqlite_exists:
            click.echo(f"  Symbol count: {symbol_count:,}")

        if detailed and metadata:
            click.echo("\nMetadata details:")
            click.echo(
                f"  Embedding model: {metadata.get('embedding_model', 'unknown')}"
            )
            click.echo(f"  Created: {metadata.get('created_at', 'unknown')}")
            click.echo(f"  Git commit: {metadata.get('git_commit', 'unknown')}")

        # Overall compatible if SQLite works (vector is optional)
        overall_compatible = sqlite_compatible and metadata_exists
        if vector_available:
            overall_compatible = overall_compatible and vector_compatible
        click.echo(
            f"\nOverall: {'✅ All compatible' if overall_compatible else '❌ Issues found'}"
        )

        sys.exit(0 if overall_compatible else 1)

    except Exception as e:
        click.echo(f"Error checking compatibility: {e}", err=True)
        sys.exit(1)


@index.command()
@click.option("--force", "-f", is_flag=True, help="Force rebuild even if compatible")
@click.option("--sqlite-only", is_flag=True, help="Rebuild SQLite index only")
@click.option("--vector-only", is_flag=True, help="Rebuild vector index only")
@click.option(
    "--sample-size", default=100, help="Number of files to index (default: 100)"
)
def rebuild(force: bool, sqlite_only: bool, vector_only: bool, sample_size: int):
    """Rebuild index artifacts."""

    if not force:
        # Check if rebuild is needed
        try:
            indexer = _get_semantic_indexer_instance()
            if indexer:
                compatible = indexer.check_compatibility()
                if compatible and os.path.exists("code_index.db"):
                    click.echo(
                        "Indexes appear compatible. Use --force to rebuild anyway."
                    )
                    return
        except Exception:
            pass  # Proceed with rebuild if check fails

    click.echo("Starting index rebuild...")

    if not sqlite_only:
        indexer = _get_semantic_indexer_instance()
        if indexer is None:
            click.echo("⚠️ Skipping vector index (semantic dependencies not installed)")
            click.echo("   Install with: pip install code-index-mcp[semantic]")
        else:
            click.echo("Rebuilding vector index...")
            try:
                # Remove old vector index
                vector_path = "vector_index.qdrant"
                if os.path.exists(vector_path):
                    import shutil

                    shutil.rmtree(vector_path)

                # Find Python files to index
                import glob

                python_files = glob.glob("**/*.py", recursive=True)
                python_files = [
                    f
                    for f in python_files
                    if not any(
                        exclude in f
                        for exclude in ["test_repos", ".git", "__pycache__", ".venv"]
                    )
                ]

                if sample_size > 0:
                    python_files = python_files[:sample_size]

                indexed_count = 0
                with click.progressbar(python_files, label="Indexing files") as files:
                    for file_path in files:
                        try:
                            result = indexer.index_file(Path(file_path))
                            if result:
                                indexed_count += 1
                        except Exception as e:
                            if force:
                                continue  # Skip errors in force mode
                            else:
                                click.echo(
                                    f"\nError indexing {file_path}: {e}", err=True
                                )
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
            _ = SQLiteStore("code_index.db")
            click.echo("✅ SQLite index schema created")

            # TODO: Add actual file indexing here when dispatcher is available
            click.echo(
                "Note: Run full indexing via the main application to populate SQLite index"
            )

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

                click.echo("SQLite Index:")
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
            indexer = _get_semantic_indexer_instance()
            if indexer:
                try:
                    collections = indexer.qdrant.get_collections()
                    collection_count = len(collections.collections)
                    click.echo("Vector Index:")
                    click.echo(f"  🧠 Collections: {collection_count}")
                    click.echo(f"  💾 Storage size: {vector_size:.1f} MB")
                except Exception:
                    click.echo("Vector Index:")
                    click.echo(f"  💾 Storage size: {vector_size:.1f} MB")
                    click.echo("  ⚠️ Could not read collection info")
            else:
                click.echo("Vector Index:")
                click.echo(f"  💾 Storage size: {vector_size:.1f} MB")
                click.echo(
                    "  ⚠️ Semantic deps not installed - install with: pip install code-index-mcp[semantic]"
                )

        except Exception as e:
            click.echo(f"Vector Index: ❌ Error reading ({e})")
    else:
        click.echo("Vector Index: ❌ Not found (optional - requires semantic deps)")

    # Metadata
    metadata_path = ".index_metadata.json"
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, "r") as f:
                metadata = json.load(f)

            click.echo("Metadata:")
            click.echo(
                f"  🤖 Embedding model: {metadata.get('embedding_model', 'unknown')}"
            )
            click.echo(f"  📅 Created: {metadata.get('created_at', 'unknown')}")
            click.echo(
                f"  🔗 Git commit: {metadata.get('git_commit', 'unknown')[:8]}..."
            )

        except Exception as e:
            click.echo(f"Metadata: ❌ Error reading ({e})")
    else:
        click.echo("Metadata: ❌ Not found")


@index.command()
@click.argument("backup_dir")
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
        click.echo("📦 Backed up SQLite index")

    # Backup vector index
    if os.path.exists("vector_index.qdrant"):
        shutil.copytree("vector_index.qdrant", f"{backup_dir}/vector_index.qdrant")
        files_backed_up += 1
        click.echo("📦 Backed up vector index")

    # Backup metadata
    if os.path.exists(".index_metadata.json"):
        shutil.copy2(".index_metadata.json", f"{backup_dir}/.index_metadata.json")
        files_backed_up += 1
        click.echo("📦 Backed up metadata")

    if files_backed_up > 0:
        click.echo(f"✅ Backup completed: {backup_dir} ({files_backed_up} items)")
    else:
        click.echo("❌ No index files found to backup")


@index.command()
@click.argument("backup_dir")
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


@index.command()
def check_semantic():
    """Check semantic search configuration and status."""
    click.echo("Semantic Search Configuration Check")
    click.echo("=" * 40)

    # Check API keys
    voyage_key = os.environ.get("VOYAGE_API_KEY") or os.environ.get("VOYAGE_AI_API_KEY")
    semantic_enabled = (
        os.environ.get("SEMANTIC_SEARCH_ENABLED", "false").lower() == "true"
    )

    click.echo("\n📋 Environment Variables:")
    click.echo(f"  VOYAGE_AI_API_KEY: {'✅ Set' if voyage_key else '❌ Not set'}")
    if voyage_key:
        click.echo(f"    Key prefix: {voyage_key[:10]}...")
    click.echo(
        f"  SEMANTIC_SEARCH_ENABLED: {'✅ true' if semantic_enabled else '❌ false'}"
    )

    # Check .env file
    env_file = Path(".env")
    if env_file.exists():
        click.echo("\n📄 .env file: ✅ Found")
        try:
            with open(env_file, "r") as f:
                content = f.read()
                if "VOYAGE_AI_API_KEY" in content or "VOYAGE_API_KEY" in content:
                    click.echo("    Contains API key configuration")
                if "SEMANTIC_SEARCH_ENABLED" in content:
                    click.echo("    Contains semantic search setting")
        except Exception as e:
            click.echo(f"    ⚠️ Could not read .env file: {e}")
    else:
        click.echo("\n📄 .env file: ❌ Not found")

    # Check .mcp.json configurations
    _ = Path(".mcp.json")
    mcp_local_json = Path(".mcp.local.json")

    if mcp_local_json.exists():
        click.echo("\n📄 .mcp.local.json: ✅ Found")
        try:
            with open(mcp_local_json, "r") as f:
                config = json.load(f)
                servers = config.get("mcpServers", {})
                if "code-index-mcp" in servers:
                    env_vars = servers["code-index-mcp"].get("env", {})
                    if "VOYAGE_AI_API_KEY" in env_vars:
                        click.echo("    ✅ Contains API key configuration")
                    if env_vars.get("SEMANTIC_SEARCH_ENABLED") == "true":
                        click.echo("    ✅ Semantic search enabled")
        except Exception as e:
            click.echo(f"    ⚠️ Could not read .mcp.local.json: {e}")

    # Test Voyage AI connection
    click.echo("\n🧪 Testing Voyage AI Connection:")
    if voyage_key:
        try:
            import voyageai

            client = voyageai.Client(api_key=voyage_key)
            # Try a simple embedding
            result = client.embed(
                ["test"], model="voyage-code-3", input_type="document"
            )
            click.echo("  ✅ Successfully connected to Voyage AI")
            click.echo("  ✅ Model: voyage-code-3")
            click.echo(f"  ✅ Embedding dimension: {len(result.embeddings[0])}")
        except ImportError:
            click.echo("  ❌ voyageai package not installed")
            click.echo("     Install with: pip install code-index-mcp[semantic]")
        except Exception as e:
            click.echo(f"  ❌ Failed to connect: {e}")
    else:
        click.echo("  ❌ Cannot test - no API key configured")

    # Configuration recommendations
    click.echo("\n💡 Configuration Methods:")
    if not voyage_key:
        click.echo("\n1. Claude Code (.mcp.json):")
        click.echo("   Create .mcp.json with:")
        click.echo("   {")
        click.echo('     "mcpServers": {')
        click.echo('       "code-index-mcp": {')
        click.echo('         "command": "uvicorn",')
        click.echo('         "args": ["mcp_server.gateway:app"],')
        click.echo('         "env": {')
        click.echo('           "VOYAGE_AI_API_KEY": "your-key-here",')
        click.echo('           "SEMANTIC_SEARCH_ENABLED": "true"')
        click.echo("         }")
        click.echo("       }")
        click.echo("     }")
        click.echo("   }")
        click.echo("\n2. Environment File (.env):")
        click.echo("   VOYAGE_AI_API_KEY=your-key-here")
        click.echo("   SEMANTIC_SEARCH_ENABLED=true")
        click.echo("\n3. Get API Key:")
        click.echo("   Visit https://www.voyageai.com/")

    # Overall status
    click.echo("\n📊 Overall Status:")
    if voyage_key and semantic_enabled:
        click.echo("  ✅ Semantic search is fully configured and ready!")
    elif voyage_key and not semantic_enabled:
        click.echo("  ⚠️ API key is set but semantic search is disabled")
        click.echo("     Set SEMANTIC_SEARCH_ENABLED=true to enable")
    elif not voyage_key and semantic_enabled:
        click.echo("  ❌ Semantic search is enabled but no API key is configured")
    else:
        click.echo("  ❌ Semantic search is not configured")


if __name__ == "__main__":
    index()
