"""CLI commands for index management."""
import os
import tarfile
import json
import shutil
import hashlib
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from mcp_server.indexer.index_engine import IndexEngine
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.config.settings import Settings
from mcp_server.plugin_system.plugin_manager import PluginManager
from mcp_server.utils.fuzzy_indexer import FuzzyIndexer

console = Console()


def generate_compatibility_hash(embedding_config: Dict[str, Any]) -> str:
    """Generate a hash for embedding compatibility checking."""
    key_components = [
        embedding_config.get("model_name", ""),
        str(embedding_config.get("dimension", 0)),
        embedding_config.get("provider", ""),
        embedding_config.get("normalize", False)
    ]
    hash_input = "|".join(str(c) for c in key_components)
    return hashlib.sha256(hash_input.encode()).hexdigest()[:16]


def generate_index_filename(model_name: str, dimension: int, version: str = "1.0") -> str:
    """Generate model-aware index filename."""
    # Clean model name for filename
    clean_model = model_name.replace('/', '-').replace(':', '-').replace(' ', '_')
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"code-index-{clean_model}-{dimension}d-v{version}-{timestamp}.tar.gz"


def validate_index_compatibility(metadata: Dict[str, Any], local_settings: Settings) -> tuple[bool, str]:
    """Validate that index is compatible with local embedding configuration."""
    if 'embedding_model' not in metadata:
        return False, "Index missing embedding model metadata (legacy format)"
    
    index_model = metadata['embedding_model']
    local_semantic = local_settings.semantic_search
    
    # Check model name compatibility
    if index_model.get('model_name') != local_semantic.embedding_model:
        return False, (
            f"Model mismatch: index uses '{index_model.get('model_name')}', "
            f"local config uses '{local_semantic.embedding_model}'"
        )
    
    # Check dimension compatibility
    if index_model.get('dimension') != local_semantic.embedding_dimension:
        return False, (
            f"Dimension mismatch: index uses {index_model.get('dimension')}d, "
            f"local config uses {local_semantic.embedding_dimension}d"
        )
    
    # Check provider compatibility
    if index_model.get('provider') != local_semantic.embedding_provider:
        return False, (
            f"Provider mismatch: index uses '{index_model.get('provider')}', "
            f"local config uses '{local_semantic.embedding_provider}'"
        )
    
    # Check compatibility hash if available
    local_hash = generate_compatibility_hash({
        "model_name": local_semantic.embedding_model,
        "dimension": local_semantic.embedding_dimension,
        "provider": local_semantic.embedding_provider,
        "normalize": local_semantic.normalize_embeddings
    })
    
    if index_model.get('compatibility_hash') and index_model.get('compatibility_hash') != local_hash:
        return False, (
            f"Configuration mismatch: index configuration hash {index_model.get('compatibility_hash')} "
            f"does not match local configuration hash {local_hash}"
        )
    
    return True, "Compatible"


@click.group()
def index():
    """MCP index management commands."""
    pass

@index.command()
@click.option('--path', default='.', help='Path to index')
@click.option('--output', required=True, help='Output directory for index export')
@click.option('--include-embeddings', is_flag=True, help='Include semantic embeddings')
@click.option('--compress', is_flag=True, help='Compress the output')
@click.option('--show-progress', is_flag=True, help='Show progress bar')
@click.option('--incremental', is_flag=True, help='Only index changed files')
@click.option('--files', type=click.File('r'), help='File containing list of files to index')
@click.option('--quiet', is_flag=True, help='Suppress output')
def build(path: str, output: str, include_embeddings: bool, compress: bool, 
         show_progress: bool, incremental: bool, files, quiet: bool):
    """Build MCP index for a codebase."""
    output_path = Path(output)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Initialize components
    settings = Settings()
    
    # Initialize storage
    db_path = os.path.join(os.getcwd(), "code_index.db")
    storage = SQLiteStore(db_path)
    
    # Initialize plugin manager
    plugin_manager = PluginManager(sqlite_store=storage)
    plugin_manager.load_plugins()
    
    # Initialize fuzzy indexer
    fuzzy_indexer = FuzzyIndexer(storage)
    
    # Create index engine with proper components
    index_engine = IndexEngine(
        plugin_manager=plugin_manager,
        storage=storage,
        fuzzy_indexer=fuzzy_indexer,
        repository_path=path or os.getcwd()
    )
    
    # Suppress console output if quiet
    if quiet:
        console = Console(quiet=True)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        console=console,
        disable=not show_progress or quiet
    ) as progress:
        # Index the codebase
        task = progress.add_task("Indexing codebase...", total=None)
        
        # Determine files to index
        if files:
            # Read file list from input
            file_list = [line.strip() for line in files if line.strip()]
            progress.update(task, description=f"Indexing {len(file_list)} specified files...")
            for file_path in file_list:
                index_engine.index_file(Path(file_path))
        elif incremental:
            # Only index changed files (would need git integration)
            progress.update(task, description="Incremental indexing...")
            # TODO: Implement incremental indexing based on git diff
            index_engine.index_directory(Path(path))
        else:
            # Full directory indexing
            progress.update(task, description="Indexing entire codebase...")
            index_engine.index_directory(Path(path))
        
        progress.update(task, description="Exporting index...")
        
        # Generate embedding model metadata
        semantic_config = settings.semantic_search
        embedding_metadata = {
            'model_name': semantic_config.embedding_model,
            'provider': semantic_config.embedding_provider,
            'dimension': semantic_config.embedding_dimension,
            'model_version': getattr(semantic_config, 'model_version', 'v1.0'),
            'normalize': semantic_config.normalize_embeddings,
            'batch_size': semantic_config.batch_size,
            'max_tokens': semantic_config.max_tokens,
            'compatibility_hash': generate_compatibility_hash({
                "model_name": semantic_config.embedding_model,
                "dimension": semantic_config.embedding_dimension,
                "provider": semantic_config.embedding_provider,
                "normalize": semantic_config.normalize_embeddings
            })
        }
        
        # Export index components with enhanced metadata
        export_data = {
            'version': '2.0',  # Increment version for compatibility checking
            'path': str(path),
            'timestamp': datetime.now().isoformat(),
            'created_by': f"MCP-Server v{settings.app_version}",
            'embedding_model': embedding_metadata,
            'index_stats': {
                'semantic_search_enabled': semantic_config.enabled,
                'include_embeddings': include_embeddings,
                'indexing_mode': 'incremental' if incremental else 'full'
            },
            'settings': settings.dict()
        }
        
        # Copy SQLite database
        db_path = settings.DATABASE_URL.replace('sqlite:///', '')
        if os.path.exists(db_path):
            shutil.copy2(db_path, output_path / 'code_index.db')
        
        # Export metadata
        with open(output_path / 'index_metadata.json', 'w') as f:
            json.dump(export_data, f, indent=2)
        
        # Handle embeddings if requested
        if include_embeddings:
            progress.update(task, description="Exporting embeddings...")
            # Copy vector store data if available
            cache_dir = Path(settings.cache.redis_url or settings.CACHE_DIR) if hasattr(settings, 'CACHE_DIR') else None
            if cache_dir and cache_dir.exists():
                shutil.copytree(cache_dir, output_path / 'cache', dirs_exist_ok=True)
        
        # Optionally compress the output
        if compress:
            progress.update(task, description="Compressing index...")
            filename = generate_index_filename(
                semantic_config.embedding_model,
                semantic_config.embedding_dimension,
                export_data['version']
            )
            archive_path = output_path.parent / filename
            
            with tarfile.open(archive_path, 'w:gz') as tar:
                tar.add(output_path, arcname=output_path.name)
            
            # Remove uncompressed directory
            shutil.rmtree(output_path)
            output_path = archive_path
        
        progress.update(task, description="Index built successfully!", completed=True)
    
    if not quiet:
        console.print(f"[green]✓ Index exported to: {output_path}[/green]")
        
        # Show enhanced summary
        if output_path.is_file():
            file_size = output_path.stat().st_size
            console.print(f"Archive size: {file_size / 1024 / 1024:.2f} MB")
        else:
            total_size = sum(f.stat().st_size for f in output_path.rglob('*') if f.is_file())
            console.print(f"Total size: {total_size / 1024 / 1024:.2f} MB")
        
        # Show embedding model info
        console.print(f"[blue]Embedding Model: {semantic_config.embedding_model} ({semantic_config.embedding_dimension}d)[/blue]")
        console.print(f"[blue]Provider: {semantic_config.embedding_provider}[/blue]")
        console.print(f"[blue]Compatibility Hash: {embedding_metadata['compatibility_hash']}[/blue]")

@index.command()
@click.argument('index_path')
@click.option('--target', help='Target directory to import to')
@click.option('--show-progress', is_flag=True, help='Show progress bar')
@click.option('--force', is_flag=True, help='Skip compatibility validation')
@click.option('--dry-run', is_flag=True, help='Validate compatibility without importing')
@click.option('--auto-reindex', is_flag=True, default=True, help='Automatically reindex if incompatible (default: true)')
@click.option('--source-path', help='Source code path for auto-reindexing')
def import_index(index_path: str, target: Optional[str], show_progress: bool, force: bool, dry_run: bool, auto_reindex: bool, source_path: Optional[str]):
    """Import a pre-built MCP index with compatibility validation."""
    index_path = Path(index_path)
    
    if not index_path.exists():
        console.print(f"[red]Error: Index path does not exist: {index_path}[/red]")
        return
    
    # Determine target directory
    if target:
        target_dir = Path(target)
    else:
        target_dir = Path.home() / '.mcp' / 'indexes' / 'imported'
    
    # Load local settings for compatibility check
    try:
        local_settings = Settings.from_environment()
    except Exception as e:
        console.print(f"[red]Error loading local settings: {e}[/red]")
        return
    
    temp_extract_dir = None
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        disable=not show_progress
    ) as progress:
        task = progress.add_task("Validating index...", total=None)
        
        # Extract to temporary location for validation
        try:
            if index_path.suffix in ['.tar', '.gz', '.tgz']:
                progress.update(task, description="Extracting archive for validation...")
                temp_extract_dir = target_dir.parent / f"temp_extract_{index_path.stem}"
                temp_extract_dir.mkdir(parents=True, exist_ok=True)
                
                with tarfile.open(index_path, 'r:*') as tar:
                    tar.extractall(temp_extract_dir)
                
                # Find the actual index directory inside the extracted content
                extracted_dirs = [d for d in temp_extract_dir.iterdir() if d.is_dir()]
                if extracted_dirs:
                    validation_dir = extracted_dirs[0]
                else:
                    validation_dir = temp_extract_dir
            else:
                validation_dir = index_path if index_path.is_dir() else index_path.parent
            
            # Load and validate metadata
            metadata_path = validation_dir / 'index_metadata.json'
            if not metadata_path.exists():
                if not force:
                    console.print("[yellow]⚠ No metadata found - this appears to be a legacy index[/yellow]")
                    console.print("[yellow]Use --force to import anyway (compatibility not guaranteed)[/yellow]")
                    return
                else:
                    console.print("[yellow]⚠ Importing legacy index without validation[/yellow]")
                    metadata = {}
            else:
                with open(metadata_path) as f:
                    metadata = json.load(f)
            
            # Validate compatibility
            if metadata and not force:
                progress.update(task, description="Checking compatibility...")
                is_compatible, message = validate_index_compatibility(metadata, local_settings)
                
                if not is_compatible:
                    console.print(f"[yellow]⚠ Compatibility check failed: {message}[/yellow]")
                    
                    if auto_reindex:
                        # Auto-reindex with current settings
                        console.print("[blue]🔄 Auto-reindexing with current embedding model settings...[/blue]")
                        
                        # Determine source path
                        if not source_path:
                            # Try to infer from index metadata or use current directory
                            source_path = metadata.get('path', '.')
                        
                        source_path = Path(source_path)
                        if not source_path.exists():
                            console.print(f"[red]✗ Source path not found: {source_path}[/red]")
                            console.print("[yellow]Specify --source-path or use --force to import incompatible index[/yellow]")
                            return
                        
                        # Build new index with current settings
                        progress.update(task, description="Building compatible index...")
                        index_engine = IndexEngine(local_settings)
                        
                        try:
                            index_engine.index_directory(source_path)
                            console.print(f"[green]✓ Successfully built compatible index from {source_path}[/green]")
                            
                            # Export the new index to target location
                            target_dir.mkdir(parents=True, exist_ok=True)
                            
                            # Copy the newly built database
                            db_path = local_settings.get_database_url().replace('sqlite:///', '')
                            if Path(db_path).exists():
                                shutil.copy2(db_path, target_dir / 'code_index.db')
                            
                            # Create new metadata
                            semantic_config = local_settings.semantic_search
                            new_metadata = {
                                'version': '2.0',
                                'timestamp': datetime.now().isoformat(),
                                'created_by': f"MCP-Server v{local_settings.app_version} (auto-reindexed)",
                                'path': str(source_path),
                                'embedding_model': {
                                    'model_name': semantic_config.embedding_model,
                                    'provider': semantic_config.embedding_provider,
                                    'dimension': semantic_config.embedding_dimension,
                                    'model_version': getattr(semantic_config, 'model_version', 'v1.0'),
                                    'normalize': semantic_config.normalize_embeddings,
                                    'batch_size': semantic_config.batch_size,
                                    'max_tokens': semantic_config.max_tokens,
                                    'compatibility_hash': generate_compatibility_hash({
                                        "model_name": semantic_config.embedding_model,
                                        "dimension": semantic_config.embedding_dimension,
                                        "provider": semantic_config.embedding_provider,
                                        "normalize": semantic_config.normalize_embeddings
                                    })
                                },
                                'index_stats': {
                                    'semantic_search_enabled': semantic_config.enabled,
                                    'include_embeddings': True,
                                    'indexing_mode': 'auto-reindex'
                                },
                                'settings': local_settings.dict()
                            }
                            
                            # Save new metadata
                            with open(target_dir / 'index_metadata.json', 'w') as f:
                                json.dump(new_metadata, f, indent=2)
                            
                            progress.update(task, description="Auto-reindex completed!", completed=True)
                            console.print(f"[green]✓ Compatible index created at: {target_dir}[/green]")
                            console.print(f"[green]Ready for semantic search with {semantic_config.embedding_model} model[/green]")
                            return
                            
                        except Exception as e:
                            console.print(f"[red]✗ Auto-reindex failed: {e}[/red]")
                            console.print("[yellow]Use --force to import original index anyway[/yellow]")
                            return
                    else:
                        console.print("[yellow]Use --auto-reindex to automatically build compatible index[/yellow]")
                        console.print("[yellow]Or use --force to import anyway (may cause issues)[/yellow]")
                        return
                else:
                    console.print(f"[green]✓ Compatibility check passed: {message}[/green]")
            
            # Show index information
            if metadata:
                embedding_model = metadata.get('embedding_model', {})
                console.print(f"[blue]Index Information:[/blue]")
                console.print(f"  Version: {metadata.get('version', 'unknown')}")
                console.print(f"  Created: {metadata.get('timestamp', 'unknown')}")
                console.print(f"  Model: {embedding_model.get('model_name', 'unknown')}")
                console.print(f"  Provider: {embedding_model.get('provider', 'unknown')}")
                console.print(f"  Dimension: {embedding_model.get('dimension', 'unknown')}")
                
                if embedding_model.get('compatibility_hash'):
                    console.print(f"  Compatibility Hash: {embedding_model['compatibility_hash']}")
            
            # If dry-run, stop here
            if dry_run:
                console.print("[green]✓ Dry run completed - index is compatible[/green]")
                return
            
            # Proceed with actual import
            target_dir.mkdir(parents=True, exist_ok=True)
            
            if index_path.suffix in ['.tar', '.gz', '.tgz']:
                progress.update(task, description="Extracting to target location...")
                with tarfile.open(index_path, 'r:*') as tar:
                    tar.extractall(target_dir)
            else:
                progress.update(task, description="Copying index files...")
                if index_path.is_dir():
                    shutil.copytree(index_path, target_dir, dirs_exist_ok=True)
                else:
                    shutil.copy2(index_path, target_dir)
            
            progress.update(task, description="Verifying index integrity...")
            
            # Verify index integrity
            db_files = list(target_dir.rglob('code_index.db'))
            if db_files:
                progress.update(task, description="Index imported successfully!", completed=True)
                console.print(f"[green]✓ Index imported to: {target_dir}[/green]")
                
                # Show final summary
                if metadata:
                    embedding_info = metadata.get('embedding_model', {})
                    console.print(f"[green]Ready for semantic search with {embedding_info.get('model_name', 'unknown')} model[/green]")
            else:
                console.print("[red]Error: Invalid index format - no database found[/red]")
                
        except Exception as e:
            console.print(f"[red]Error during import: {e}[/red]")
            
        finally:
            # Clean up temporary extraction directory
            if temp_extract_dir and temp_extract_dir.exists():
                shutil.rmtree(temp_extract_dir)

@index.command()
@click.option('--path', help='Index path to verify')
@click.option('--check-compatibility', is_flag=True, help='Check compatibility with local settings')
def verify(path: Optional[str], check_compatibility: bool):
    """Verify index integrity and compatibility."""
    if path:
        index_dir = Path(path)
    else:
        index_dir = Path.home() / '.mcp' / 'indexes'
    
    if not index_dir.exists():
        console.print(f"[red]No index found at: {index_dir}[/red]")
        return
    
    # Check for required files
    db_files = list(index_dir.rglob('code_index.db'))
    metadata_files = list(index_dir.rglob('index_metadata.json'))
    
    console.print(f"Checking index at: {index_dir}")
    
    if db_files:
        console.print("[green]✓ Database found[/green]")
        size = db_files[0].stat().st_size / 1024 / 1024
        console.print(f"  Size: {size:.2f} MB")
        console.print(f"  Location: {db_files[0]}")
    else:
        console.print("[red]✗ Database not found[/red]")
    
    # Check metadata
    metadata = None
    if metadata_files:
        console.print("[green]✓ Metadata found[/green]")
        with open(metadata_files[0]) as f:
            metadata = json.load(f)
            console.print(f"  Version: {metadata.get('version', 'unknown')}")
            console.print(f"  Created: {metadata.get('timestamp', 'unknown')}")
            
            # Show embedding model information
            if 'embedding_model' in metadata:
                embedding_info = metadata['embedding_model']
                console.print(f"  Model: {embedding_info.get('model_name', 'unknown')}")
                console.print(f"  Provider: {embedding_info.get('provider', 'unknown')}")
                console.print(f"  Dimension: {embedding_info.get('dimension', 'unknown')}")
                console.print(f"  Compatibility Hash: {embedding_info.get('compatibility_hash', 'none')}")
            else:
                console.print("  [yellow]Legacy format - no embedding model metadata[/yellow]")
    else:
        console.print("[yellow]⚠ Metadata not found (legacy index)[/yellow]")
    
    # Check cache/embeddings
    cache_dirs = list(index_dir.rglob('cache'))
    if cache_dirs:
        console.print("[green]✓ Embeddings cache found[/green]")
        cache_size = sum(f.stat().st_size for f in cache_dirs[0].rglob('*') if f.is_file())
        console.print(f"  Size: {cache_size / 1024 / 1024:.2f} MB")
    else:
        console.print("[yellow]⚠ No embeddings cache[/yellow]")
    
    # Compatibility check
    if check_compatibility and metadata:
        try:
            local_settings = Settings.from_environment()
            is_compatible, message = validate_index_compatibility(metadata, local_settings)
            
            if is_compatible:
                console.print(f"[green]✓ Compatible with local configuration: {message}[/green]")
            else:
                console.print(f"[red]✗ Incompatible with local configuration: {message}[/red]")
                
        except Exception as e:
            console.print(f"[red]Error checking compatibility: {e}[/red]")
    elif check_compatibility:
        console.print("[yellow]⚠ Cannot check compatibility - no metadata found[/yellow]")

@index.command()
@click.option('--path', help='Index directory path')
@click.option('--files', type=click.File('r'), help='File containing list of files to update')
@click.option('--commit', help='Git commit hash for tracking')
@click.option('--background', is_flag=True, help='Run in background mode')
def update(path: Optional[str], files, commit: Optional[str], background: bool):
    """Update index incrementally with changed files."""
    if path:
        index_dir = Path(path)
    else:
        index_dir = Path.home() / '.mcp' / 'indexes' / Path.cwd().name
    
    if not index_dir.exists():
        console.print(f"[red]No existing index at: {index_dir}[/red]")
        console.print("[yellow]Creating new index...[/yellow]")
        index_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize components
    settings = Settings()
    settings.DATABASE_URL = f"sqlite:///{index_dir}/code_index.db"
    settings.CACHE_DIR = str(index_dir / 'cache')
    
    index_engine = IndexEngine(settings)
    
    if files:
        # Read file list
        file_list = [line.strip() for line in files if line.strip()]
        if not background:
            console.print(f"[yellow]Updating {len(file_list)} files...[/yellow]")
        
        # Update each file
        for file_path in file_list:
            try:
                index_engine.index_file(Path(file_path))
            except Exception as e:
                if not background:
                    console.print(f"[red]Error indexing {file_path}: {e}[/red]")
    
    # Save commit info if provided
    if commit:
        metadata_path = index_dir / '.last_indexed_commit'
        with open(metadata_path, 'w') as f:
            f.write(commit)
    
    if not background:
        console.print("[green]✓ Index updated successfully![/green]")