"""CLI commands for repository management and git integration.

This module provides commands for managing the repository registry,
tracking repositories, and syncing indexes with git.
"""

import os
import sys
from pathlib import Path
from typing import Optional

import click

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from mcp_server.artifacts.commit_artifacts import CommitArtifactManager  # noqa: E402
from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher  # noqa: E402
from mcp_server.storage.git_index_manager import GitAwareIndexManager  # noqa: E402
from mcp_server.storage.repository_registry import RepositoryRegistry  # noqa: E402
from mcp_server.storage.sqlite_store import SQLiteStore  # noqa: E402
from mcp_server.watcher_multi_repo import MultiRepositoryWatcher  # noqa: E402


@click.group()
def repository():
    """Repository management commands."""


@repository.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--auto-sync/--no-auto-sync", default=True, help="Enable automatic synchronization")
@click.option("--artifacts/--no-artifacts", default=True, help="Enable artifact generation")
def register(path: str, auto_sync: bool, artifacts: bool):
    """Register a repository for tracking and indexing."""
    try:
        registry = RepositoryRegistry()
        repo_id = registry.register_repository(path, auto_sync=auto_sync)

        # Set artifact preference
        if not artifacts:
            registry.set_artifact_enabled(repo_id, False)

        repo_info = registry.get_repository(repo_id)

        click.echo(click.style(f"✓ Registered repository: {repo_info.name}", fg="green"))
        click.echo(f"  ID: {repo_id}")
        click.echo(f"  Path: {repo_info.path}")
        click.echo(f"  Remote: {repo_info.url or 'None'}")
        click.echo(f"  Auto-sync: {'Yes' if auto_sync else 'No'}")
        click.echo(f"  Artifacts: {'Yes' if artifacts else 'No'}")

        # Check if index exists
        index_path = Path(repo_info.index_location) / "current.db"
        if not index_path.exists():
            click.echo(
                click.style(
                    "\nNote: No index found. Run 'mcp index sync' to create index.", fg="yellow"
                )
            )

    except Exception as e:
        click.echo(click.style(f"✗ Failed to register repository: {e}", fg="red"), err=True)
        sys.exit(1)


@repository.command()
@click.option("--verbose", "-v", is_flag=True, help="Show detailed information")
def list(verbose: bool):
    """List all registered repositories."""
    try:
        registry = RepositoryRegistry()
        repos = registry.get_all_repositories()

        if not repos:
            click.echo("No repositories registered.")
            click.echo("Register a repository with: mcp repository register <path>")
            return

        click.echo(f"Registered repositories ({len(repos)}):\n")

        for repo_id, repo_info in repos.items():
            status_icon = "✓" if not repo_info.needs_update() else "⚠"
            sync_status = "auto" if repo_info.auto_sync else "manual"

            click.echo(f"{status_icon} {repo_info.name} [{repo_id[:8]}...]")
            click.echo(f"  Path: {repo_info.path}")

            if verbose:
                click.echo(f"  Remote: {repo_info.url or 'None'}")
                click.echo(
                    f"  Current commit: {repo_info.current_commit[:8] if repo_info.current_commit else 'None'}"
                )
                click.echo(
                    f"  Indexed commit: {repo_info.last_indexed_commit[:8] if repo_info.last_indexed_commit else 'Never'}"
                )
                click.echo(f"  Last indexed: {repo_info.last_indexed or 'Never'}")
                click.echo(f"  Sync: {sync_status}")
                click.echo(
                    f"  Artifacts: {'enabled' if repo_info.artifact_enabled else 'disabled'}"
                )

                if repo_info.needs_update():
                    click.echo(click.style("  Status: Needs update", fg="yellow"))
                else:
                    click.echo(click.style("  Status: Up to date", fg="green"))

            click.echo()

    except Exception as e:
        click.echo(click.style(f"✗ Error listing repositories: {e}", fg="red"), err=True)
        sys.exit(1)


@repository.command()
@click.argument("repo_id")
def unregister(repo_id: str):
    """Remove a repository from tracking."""
    try:
        registry = RepositoryRegistry()
        repo_info = registry.get_repository(repo_id)

        if not repo_info:
            # Try to find by name or path
            for rid, info in registry.get_all_repositories().items():
                if info.name == repo_id or info.path == repo_id:
                    repo_id = rid
                    repo_info = info
                    break

        if not repo_info:
            click.echo(click.style(f"✗ Repository not found: {repo_id}", fg="red"), err=True)
            sys.exit(1)

        # Confirm
        if not click.confirm(f"Remove {repo_info.name} from tracking?"):
            return

        if registry.unregister_repository(repo_id):
            click.echo(click.style(f"✓ Unregistered repository: {repo_info.name}", fg="green"))
        else:
            click.echo(click.style("✗ Failed to unregister repository", fg="red"), err=True)
            sys.exit(1)

    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg="red"), err=True)
        sys.exit(1)


@repository.command()
@click.option("--repo-id", help="Repository ID (default: current directory)")
@click.option("--force-full", is_flag=True, help="Force full reindex instead of incremental")
@click.option("--all", "sync_all", is_flag=True, help="Sync all repositories")
def sync(repo_id: Optional[str], force_full: bool, sync_all: bool):
    """Synchronize repository index with current git state."""
    try:
        registry = RepositoryRegistry()

        if sync_all:
            # Sync all repositories
            click.echo("Synchronizing all repositories...")

            # Create index manager
            index_manager = GitAwareIndexManager(registry)
            results = index_manager.sync_all_repositories()

            for rid, result in results.items():
                repo_info = registry.get_repository(rid)
                if repo_info:
                    if result.action == "up_to_date":
                        click.echo(
                            click.style(f"✓ {repo_info.name}: Already up to date", fg="green")
                        )
                    elif result.action == "indexed":
                        click.echo(
                            click.style(
                                f"✓ {repo_info.name}: Indexed {result.files_processed} files in {result.duration_seconds:.1f}s",
                                fg="green",
                            )
                        )
                    elif result.action == "downloaded":
                        click.echo(
                            click.style(f"✓ {repo_info.name}: Downloaded from artifact", fg="green")
                        )
                    else:
                        click.echo(click.style(f"✗ {repo_info.name}: {result.error}", fg="red"))

        else:
            # Sync single repository
            if not repo_id:
                # Try current directory
                repo_info = registry.get_repository_by_path(os.getcwd())
                if repo_info:
                    repo_id = repo_info.repo_id
                else:
                    click.echo(
                        click.style("✗ Current directory is not a registered repository", fg="red"),
                        err=True,
                    )
                    click.echo("Register with: mcp repository register .")
                    sys.exit(1)

            # Create dispatcher and index manager
            repo_info = registry.get_repository(repo_id)
            if not repo_info:
                click.echo(click.style(f"✗ Repository not found: {repo_id}", fg="red"), err=True)
                sys.exit(1)

            # Create necessary components
            index_path = Path(repo_info.index_location) / "current.db"
            store = SQLiteStore(str(index_path)) if index_path.exists() else None
            dispatcher = EnhancedDispatcher(sqlite_store=store)
            index_manager = GitAwareIndexManager(registry, dispatcher)

            click.echo(f"Synchronizing {repo_info.name}...")

            # Update current commit
            registry.update_current_commit(repo_id)

            # Sync the repository
            result = index_manager.sync_repository_index(repo_id, force_full=force_full)

            if result.action == "up_to_date":
                click.echo(click.style("✓ Repository is already up to date", fg="green"))
            elif result.action == "indexed":
                click.echo(
                    click.style(
                        f"✓ Indexed {result.files_processed} files in {result.duration_seconds:.1f}s",
                        fg="green",
                    )
                )
            elif result.action == "downloaded":
                click.echo(click.style("✓ Downloaded index from artifact", fg="green"))
            elif result.action == "failed":
                click.echo(click.style(f"✗ Sync failed: {result.error}", fg="red"), err=True)
                sys.exit(1)

    except Exception as e:
        click.echo(click.style(f"✗ Sync failed: {e}", fg="red"), err=True)
        sys.exit(1)


@repository.command()
@click.option("--repo-id", help="Repository ID")
def status(repo_id: Optional[str]):
    """Show detailed repository status."""
    try:
        registry = RepositoryRegistry()

        if not repo_id:
            # Try current directory
            repo_info = registry.get_repository_by_path(os.getcwd())
            if repo_info:
                repo_id = repo_info.repo_id
            else:
                click.echo(
                    click.style("✗ Current directory is not a registered repository", fg="red"),
                    err=True,
                )
                sys.exit(1)

        # Get repository status
        index_manager = GitAwareIndexManager(registry)
        status = index_manager.get_repository_status(repo_id)

        if "error" in status:
            click.echo(click.style(f"✗ {status['error']}", fg="red"), err=True)
            sys.exit(1)

        # Display status
        click.echo(f"Repository: {status['name']}")
        click.echo(f"Path: {status['path']}")
        click.echo(f"ID: {status['repo_id']}")
        click.echo()

        # Git status
        click.echo("Git Status:")
        click.echo(
            f"  Current commit: {status['current_commit'][:8] if status['current_commit'] else 'None'}"
        )
        click.echo(
            f"  Indexed commit: {status['last_indexed_commit'][:8] if status['last_indexed_commit'] else 'Never'}"
        )

        if status["needs_update"]:
            click.echo(click.style("  Status: Index needs update", fg="yellow"))
        else:
            click.echo(click.style("  Status: Index is up to date", fg="green"))

        # Index status
        click.echo("\nIndex Status:")
        if status["index_exists"]:
            click.echo(f"  Index size: {status['index_size_mb']:.1f} MB")
            click.echo(f"  Last indexed: {status['last_indexed'] or 'Unknown'}")
        else:
            click.echo(click.style("  No index found", fg="yellow"))

        # Settings
        click.echo("\nSettings:")
        click.echo(f"  Auto-sync: {'Yes' if status['auto_sync'] else 'No'}")
        click.echo(f"  Artifacts: {'Yes' if status['artifact_enabled'] else 'No'}")

    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg="red"), err=True)
        sys.exit(1)


@repository.command()
@click.argument("search_paths", nargs=-1, required=True)
@click.option(
    "--register/--no-register", default=True, help="Automatically register found repositories"
)
def discover(search_paths: tuple, register: bool):
    """Discover git repositories in given paths."""
    try:
        registry = RepositoryRegistry()

        # Expand paths
        paths = []
        for path in search_paths:
            expanded = Path(path).expanduser().resolve()
            if expanded.exists():
                paths.append(str(expanded))
            else:
                click.echo(click.style(f"Warning: Path does not exist: {path}", fg="yellow"))

        if not paths:
            click.echo(click.style("✗ No valid paths provided", fg="red"), err=True)
            sys.exit(1)

        click.echo(f"Searching for repositories in {len(paths)} path(s)...")

        # Discover repositories
        discovered = registry.discover_repositories(paths)

        if not discovered:
            click.echo("No git repositories found.")
            return

        click.echo(f"\nFound {len(discovered)} repository(ies):")

        registered_count = 0
        for repo_path in discovered:
            repo_name = Path(repo_path).name

            # Check if already registered
            existing = registry.get_repository_by_path(repo_path)
            if existing:
                click.echo(f"  ✓ {repo_name} (already registered)")
                continue

            if register:
                try:
                    repo_id = registry.register_repository(repo_path)
                    click.echo(
                        click.style(f"  ✓ {repo_name} (registered as {repo_id[:8]}...)", fg="green")
                    )
                    registered_count += 1
                except Exception as e:
                    click.echo(click.style(f"  ✗ {repo_name} (failed: {e})", fg="red"))
            else:
                click.echo(f"  - {repo_name} at {repo_path}")

        if register and registered_count > 0:
            click.echo(f"\nRegistered {registered_count} new repository(ies)")
            click.echo("Run 'mcp repository sync --all' to index them")

    except Exception as e:
        click.echo(click.style(f"✗ Discovery failed: {e}", fg="red"), err=True)
        sys.exit(1)


@repository.command()
@click.option("--all", "watch_all", is_flag=True, help="Watch all registered repositories")
@click.option("--daemon", is_flag=True, help="Run as background daemon")
def watch(watch_all: bool, daemon: bool):
    """Start watching repositories for changes."""
    try:
        registry = RepositoryRegistry()

        if not watch_all:
            click.echo(
                click.style("✗ Please specify --all to watch all repositories", fg="red"), err=True
            )
            click.echo("Individual repository watching coming soon")
            sys.exit(1)

        # Create components
        dispatcher = EnhancedDispatcher()
        index_manager = GitAwareIndexManager(registry, dispatcher)
        artifact_manager = CommitArtifactManager()

        # Create watcher
        watcher = MultiRepositoryWatcher(
            registry=registry,
            dispatcher=dispatcher,
            index_manager=index_manager,
            artifact_manager=artifact_manager,
        )

        click.echo("Starting multi-repository watcher...")

        # Start watching
        watcher.start_watching_all()

        # Get status
        status = watcher.get_status()
        click.echo(f"Watching {status['watching']} repository(ies)")

        if daemon:
            click.echo("Running as daemon. Press Ctrl+C to stop.")
            try:
                import time

                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                click.echo("\nStopping watcher...")
                watcher.stop_watching_all()
        else:
            click.echo("Watcher started. Run with --daemon to keep running.")

    except Exception as e:
        click.echo(click.style(f"✗ Watch failed: {e}", fg="red"), err=True)
        sys.exit(1)


@repository.command()
@click.option("--enable/--disable", "enable", default=True, help="Enable or disable git hooks")
def init_hooks(enable: bool):
    """Install git hooks for automatic index synchronization."""
    try:
        # Check if in a git repository
        if not Path(".git").exists():
            click.echo(click.style("✗ Not in a git repository", fg="red"), err=True)
            sys.exit(1)

        hooks_dir = Path(".git/hooks")
        hooks_dir.mkdir(exist_ok=True)

        # Source hooks directory
        source_hooks = Path(__file__).parent.parent.parent / "mcp-index-kit" / "hooks"

        hooks_to_install = ["post-commit", "pre-push", "post-checkout", "post-merge"]

        if enable:
            click.echo("Installing git hooks...")

            for hook_name in hooks_to_install:
                source = source_hooks / hook_name
                target = hooks_dir / hook_name

                if source.exists():
                    # Copy hook
                    import shutil

                    shutil.copy2(source, target)

                    # Make executable
                    import stat

                    st = target.stat()
                    target.chmod(st.st_mode | stat.S_IEXEC)

                    click.echo(click.style(f"  ✓ Installed {hook_name}", fg="green"))
                else:
                    click.echo(click.style(f"  ⚠ Source hook not found: {hook_name}", fg="yellow"))

            click.echo("\nGit hooks installed. Index will now sync automatically on:")
            click.echo("  - commit: Update index incrementally")
            click.echo("  - push: Upload index artifacts")
            click.echo("  - checkout/merge: Check for index updates")

        else:
            click.echo("Removing git hooks...")

            for hook_name in hooks_to_install:
                target = hooks_dir / hook_name
                if target.exists():
                    target.unlink()
                    click.echo(click.style(f"  ✓ Removed {hook_name}", fg="green"))

            click.echo("\nGit hooks removed. Manual index management required.")

    except Exception as e:
        click.echo(click.style(f"✗ Hook installation failed: {e}", fg="red"), err=True)
        sys.exit(1)
