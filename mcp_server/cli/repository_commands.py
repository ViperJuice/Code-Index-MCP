"""CLI commands for repository management and git integration.

This module provides commands for managing the repository registry,
tracking repositories, and syncing indexes with git.
"""

import os
import sys
from pathlib import Path
from typing import Any, Optional, cast

import click

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from mcp_server.artifacts.commit_artifacts import CommitArtifactManager  # noqa: E402
from mcp_server.config.settings import reload_settings  # noqa: E402
from mcp_server.core.repo_resolver import RepoResolver  # noqa: E402
from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher  # noqa: E402
from mcp_server.health.repo_status import build_health_row  # noqa: E402
from mcp_server.health.repository_readiness import ReadinessClassifier  # noqa: E402
from mcp_server.setup.semantic_preflight import run_semantic_preflight  # noqa: E402
from mcp_server.storage.git_index_manager import GitAwareIndexManager  # noqa: E402
from mcp_server.storage.repository_registry import (  # noqa: E402
    MultipleWorktreesUnsupportedError,
    RepositoryRegistry,
)
from mcp_server.storage.sqlite_store import SQLiteStore  # noqa: E402,F401
from mcp_server.storage.store_registry import StoreRegistry  # noqa: E402
from mcp_server.watcher_multi_repo import MultiRepositoryWatcher  # noqa: E402


@click.group()
def repository():
    """Repository management commands."""


def _print_rollout_surface(prefix: str, health_row: dict[str, Any]) -> None:
    rollout = health_row["rollout_status"]
    rollout_color = "green" if rollout == "ready" else "yellow"
    click.echo(click.style(f"{prefix}Rollout status: {rollout}", fg=rollout_color))
    if health_row.get("rollout_remediation"):
        click.echo(f"{prefix}Rollout remediation: {health_row['rollout_remediation']}")
    query_status = health_row["query_status"]
    query_color = "green" if query_status == "ready" else "yellow"
    click.echo(click.style(f"{prefix}Query surface: {query_status}", fg=query_color))
    if health_row.get("query_remediation"):
        click.echo(f"{prefix}Query remediation: {health_row['query_remediation']}")


def _print_semantic_evidence(prefix: str, evidence: dict[str, Any]) -> None:
    click.echo(f"{prefix}Summary-backed chunks: {evidence.get('summary_count', 0)}")
    click.echo(f"{prefix}Chunks missing summaries: {evidence.get('missing_summaries', 0)}")
    click.echo(f"{prefix}Vector-linked chunks: {evidence.get('vector_link_count', 0)}")
    click.echo(f"{prefix}Chunks missing vectors: {evidence.get('missing_vectors', 0)}")
    if evidence.get("collection") is not None:
        click.echo(f"{prefix}Active collection: {evidence.get('collection')}")
        click.echo(
            f"{prefix}Collection-matched links: {evidence.get('matching_collection_links', 0)}"
        )
        click.echo(
            f"{prefix}Collection mismatches: {evidence.get('collection_mismatches', 0)}"
        )


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
        if repo_info is None:
            raise ValueError(f"Failed to load registered repository: {repo_id}")
        repo_info = cast(Any, repo_info)

        click.echo(click.style(f"✓ Registered repository: {repo_info.name}", fg="green"))
        click.echo(f"  ID: {repo_id}")
        click.echo(f"  Path: {repo_info.path}")
        click.echo(f"  Remote: {repo_info.url or 'None'}")
        click.echo(f"  Auto-sync: {'Yes' if auto_sync else 'No'}")
        click.echo(f"  Artifacts: {'Yes' if artifacts else 'No'}")
        click.echo(f"  Artifact backend: {repo_info.artifact_backend or 'local_workspace'}")
        click.echo(f"  Artifact health: {repo_info.artifact_health or 'missing'}")

        # Check if index exists
        index_path = Path(repo_info.index_location) / "current.db"
        if not index_path.exists():
            click.echo(
                click.style(
                    "\nNote: No local runtime index found. Run 'mcp-index artifact pull --latest' or 'mcp repository sync' to prepare this repository.",
                    fg="yellow",
                )
            )

    except MultipleWorktreesUnsupportedError as e:
        details = e.to_dict()
        click.echo(click.style("✗ Failed to register repository", fg="red"), err=True)
        click.echo(f"  Code: {details['code']}", err=True)
        click.echo(f"  Registered path: {details['registered_path']}", err=True)
        click.echo(f"  Requested path: {details['requested_path']}", err=True)
        click.echo(f"  Git common dir: {details['git_common_dir']}", err=True)
        click.echo(f"  Remediation: {details['remediation']}", err=True)
        sys.exit(1)
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
                click.echo(f"  Artifact backend: {repo_info.artifact_backend or 'local_workspace'}")
                click.echo(f"  Artifact health: {repo_info.artifact_health or 'missing'}")
                click.echo(
                    "  Semantic profiles: "
                    + (
                        ", ".join(repo_info.available_semantic_profiles)
                        if repo_info.available_semantic_profiles
                        else "none"
                    )
                )
                click.echo(
                    f"  Last recovered commit: {repo_info.last_recovered_commit[:8] if repo_info.last_recovered_commit else 'Never'}"
                )
                click.echo(
                    f"  Last published commit: {repo_info.last_published_commit[:8] if repo_info.last_published_commit else 'Never'}"
                )

                health_row = build_health_row(repo_info)
                readiness = health_row["readiness"]
                color = "green" if health_row["ready"] else "yellow"
                click.echo(click.style(f"  Readiness: {readiness}", fg=color))
                if health_row["remediation"]:
                    click.echo(f"  Remediation: {health_row['remediation']}")
                _print_rollout_surface("  ", health_row)

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

        store_registry = StoreRegistry.for_registry(registry)
        store_registry.close(repo_id)
        try:
            from mcp_server.plugins.plugin_set_registry import PluginSetRegistry

            PluginSetRegistry().evict(repo_id)
        except Exception:
            pass
        try:
            from mcp_server.utils.semantic_indexer_registry import SemanticIndexerRegistry

            SemanticIndexerRegistry(registry).evict(repo_id)
        except Exception:
            pass

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
        store_registry = StoreRegistry.for_registry(registry)
        repo_resolver = RepoResolver(registry, store_registry)

        if sync_all:
            # Sync all repositories
            click.echo("Synchronizing all repositories...")

            # Create index manager
            index_manager = GitAwareIndexManager(
                registry,
                repo_resolver=repo_resolver,
                store_registry=store_registry,
            )
            results = index_manager.sync_all_repositories()

            for rid, result in results.items():
                repo_info = registry.get_repository(rid)
                if repo_info:
                    if result.action == "up_to_date":
                        click.echo(
                            click.style(f"✓ {repo_info.name}: Already up to date", fg="green")
                        )
                    elif result.action in {"indexed", "incremental_update", "full_index"}:
                        click.echo(
                            click.style(
                                f"✓ {repo_info.name}: Indexed {result.files_processed} files in {result.duration_seconds:.1f}s",
                                fg="green",
                            )
                        )
                    elif result.action == "downloaded":
                        click.echo(
                            click.style(
                                f"✓ {repo_info.name}: Downloaded from artifact",
                                fg="green",
                            )
                        )
                    else:
                        click.echo(click.style(f"✗ {repo_info.name}: {result.error}", fg="red"))

        else:
            # Sync single repository
            if not repo_id:
                # Try current directory
                repo_info = registry.get_repository_by_path(os.getcwd())
                if repo_info:
                    repo_id = repo_info.repository_id
                else:
                    click.echo(
                        click.style(
                            "✗ Current directory is not a registered repository",
                            fg="red",
                        ),
                        err=True,
                    )
                    click.echo("Register with: mcp repository register .")
                    sys.exit(1)

            assert repo_id is not None

            # Create dispatcher and index manager
            repo_info = registry.get_repository(repo_id)
            if not repo_info:
                click.echo(
                    click.style(f"✗ Repository not found: {repo_id}", fg="red"),
                    err=True,
                )
                sys.exit(1)

            # Create necessary components
            dispatcher = EnhancedDispatcher()
            index_manager = GitAwareIndexManager(
                registry,
                dispatcher,
                repo_resolver=repo_resolver,
                store_registry=store_registry,
            )

            click.echo(f"Synchronizing {repo_info.name}...")

            # Update current commit
            registry.update_current_commit(repo_id)

            # Sync the repository
            result = index_manager.sync_repository_index(repo_id, force_full=force_full)

            if result.action == "up_to_date":
                click.echo(click.style("✓ Repository is already up to date", fg="green"))
            elif result.action in {"indexed", "incremental_update", "full_index"}:
                click.echo(
                    click.style(
                        f"✓ Indexed {result.files_processed} files in {result.duration_seconds:.1f}s",
                        fg="green",
                    )
                )
            elif result.action == "downloaded":
                click.echo(click.style("✓ Downloaded index from artifact", fg="green"))
                click.echo(
                    "  Next step: run 'mcp-index artifact reconcile-workspace' if you manage multiple local repositories."
                )
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
        store_registry = StoreRegistry.for_registry(registry)
        repo_resolver = RepoResolver(registry, store_registry)

        if not repo_id:
            # Try current directory
            repo_info = registry.get_repository_by_path(os.getcwd())
            if repo_info:
                repo_id = repo_info.repository_id
            else:
                click.echo(
                    click.style("✗ Current directory is not a registered repository", fg="red"),
                    err=True,
                )
                sys.exit(1)

        assert repo_id is not None

        # Get repository status
        index_manager = GitAwareIndexManager(
            registry,
            repo_resolver=repo_resolver,
            store_registry=store_registry,
        )
        repo_id_str = repo_id
        status = index_manager.get_repository_status(repo_id_str)

        if "error" in status:
            click.echo(click.style(f"✗ {status['error']}", fg="red"), err=True)
            sys.exit(1)

        settings = reload_settings()
        semantic_preflight = run_semantic_preflight(
            settings=settings,
            profile=settings.get_semantic_default_profile(),
            strict=settings.semantic_strict_mode,
        ).to_dict()
        repo_ctx = None
        if hasattr(repo_resolver, "resolve"):
            repo_ctx = repo_resolver.resolve(Path(status["path"]))
        if repo_ctx is not None:
            semantic_readiness = ReadinessClassifier.classify_semantic_registered(
                repo_ctx.registry_entry,
                repo_ctx.sqlite_store,
            )
            status["semantic_readiness"] = semantic_readiness.state.value
            status["semantic_ready"] = semantic_readiness.ready
            status["semantic_readiness_code"] = semantic_readiness.code
            status["semantic_remediation"] = semantic_readiness.remediation
            status.setdefault("features", {}).setdefault("semantic", {})[
                "readiness"
            ] = semantic_readiness.to_dict()
        status["features"]["semantic"]["preflight"] = semantic_preflight

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
        click.echo(
            click.style(
                f"  Readiness: {status['readiness']}",
                fg="green" if status["ready"] else "yellow",
            )
        )
        if status["remediation"]:
            click.echo(f"  Remediation: {status['remediation']}")
        click.echo(
            click.style(
                f"  Semantic readiness: {status['semantic_readiness']}",
                fg="green" if status.get("semantic_ready") else "yellow",
            )
        )
        if status.get("semantic_remediation"):
            click.echo(f"  Semantic remediation: {status['semantic_remediation']}")
        _print_rollout_surface("  ", status)

        # Index status
        click.echo("\nIndex Status:")
        if status["index_exists"]:
            click.echo(f"  Index size: {status['index_size_mb']:.1f} MB")
            click.echo(f"  Last indexed: {status['last_indexed'] or 'Unknown'}")
        else:
            click.echo(click.style("  No index found", fg="yellow"))
        if status.get("staleness_reason"):
            click.echo(f"  Staleness reason: {status['staleness_reason']}")

        semantic_preflight = status["features"]["semantic"].get("preflight") or {}
        blocker = semantic_preflight.get("blocker") or {}
        effective_config = semantic_preflight.get("effective_config") or {}
        click.echo("\nSemantic Preflight:")
        click.echo(
            "  Active-profile preflight: "
            + ("ready" if semantic_preflight.get("overall_ready") else "blocked")
        )
        click.echo(
            "  Can write semantic vectors: "
            + ("yes" if semantic_preflight.get("can_write_semantic_vectors") else "no")
        )
        if blocker:
            click.echo(f"  Blocker: {blocker.get('code')} - {blocker.get('message')}")
            for fix in blocker.get("remediation") or []:
                click.echo(f"  Remediation: {fix}")
        if effective_config:
            click.echo(f"  Active profile: {effective_config.get('selected_profile')}")
            click.echo(f"  Active collection: {effective_config.get('collection_name')}")
            bootstrap_state = (
                "reused"
                if semantic_preflight.get("can_write_semantic_vectors")
                else "blocked"
            )
            click.echo(f"  Collection bootstrap state: {bootstrap_state}")
        semantic_evidence = (
            status.get("features", {}).get("semantic", {}).get("readiness", {}).get("evidence") or {}
        )
        if semantic_evidence:
            click.echo("\nSemantic Evidence:")
            _print_semantic_evidence("  ", semantic_evidence)

        # Settings
        click.echo("\nSettings:")
        click.echo(f"  Auto-sync: {'Yes' if status['auto_sync'] else 'No'}")
        click.echo(f"  Artifacts: {'Yes' if status['artifact_enabled'] else 'No'}")
        click.echo(f"  Artifact backend: {status['artifact_backend'] or 'local_workspace'}")
        click.echo(f"  Artifact health: {status['artifact_health'] or 'missing'}")

    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg="red"), err=True)
        sys.exit(1)


@repository.command()
@click.argument("search_paths", nargs=-1, required=True)
@click.option(
    "--register/--no-register",
    default=True,
    help="Automatically register found repositories",
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
        discover = cast(Any, registry).discover_repositories
        discovered = discover(paths)

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
                        click.style(
                            f"  ✓ {repo_name} (registered as {repo_id[:8]}...)",
                            fg="green",
                        )
                    )
                    registered_count += 1
                except Exception as e:
                    click.echo(click.style(f"  ✗ {repo_name} (failed: {e})", fg="red"))
            else:
                click.echo(f"  - {repo_name} at {repo_path}")

        if register and registered_count > 0:
            click.echo(f"\nRegistered {registered_count} new repository(ies)")
            click.echo("Run 'mcp repository list -v' to inspect readiness across repos")
            click.echo(
                "Run 'mcp-index artifact workspace-status' to see local-first artifact/runtime readiness"
            )

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
        store_registry = StoreRegistry.for_registry(registry)
        repo_resolver = RepoResolver(registry, store_registry)

        if not watch_all:
            click.echo(
                click.style("✗ Please specify --all to watch all repositories", fg="red"),
                err=True,
            )
            click.echo("Individual repository watching coming soon")
            sys.exit(1)

        # Create components
        dispatcher = EnhancedDispatcher()
        index_manager = GitAwareIndexManager(
            registry,
            dispatcher,
            repo_resolver=repo_resolver,
            store_registry=store_registry,
        )
        artifact_manager = CommitArtifactManager()

        # Create watcher
        watcher = MultiRepositoryWatcher(
            registry=registry,
            dispatcher=dispatcher,
            index_manager=index_manager,
            artifact_manager=artifact_manager,
            repo_resolver=repo_resolver,
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
