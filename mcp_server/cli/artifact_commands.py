"""
CLI commands for managing index artifacts in GitHub Actions.

This module provides commands for uploading, downloading, and managing
index artifacts using GitHub Actions Artifacts storage.
"""

import subprocess
import sys
import json
from pathlib import Path
from typing import Optional

import click

from mcp_server.indexing.change_detector import ChangeDetector, FileChange

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def _run_artifact_command(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    """Run an artifact helper command and relay output."""
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.stdout:
        click.echo(result.stdout)

    if result.stderr:
        click.echo(result.stderr, err=True)

    return result


def _get_restored_index_paths() -> list[Path]:
    """Return restored index artifacts present in the working directory."""
    expected_paths = [
        Path("code_index.db"),
        Path(".index_metadata.json"),
        Path("artifact-metadata.json"),
        Path("semantic_index_metadata.json"),
        Path("vector_index.qdrant"),
    ]
    return [path for path in expected_paths if path.exists()]


def _verify_local_index_restored() -> bool:
    """Check whether artifact retrieval restored a usable local index."""
    return bool(_get_restored_index_paths())


def _load_json_file(path: Path) -> dict | None:
    """Load JSON data if the file exists and is valid."""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _get_artifact_identity() -> dict[str, str | None]:
    """Return restored artifact commit and branch metadata."""
    artifact_metadata = _load_json_file(Path("artifact-metadata.json")) or {}
    index_metadata = _load_json_file(Path(".index_metadata.json")) or {}

    return {
        "commit": artifact_metadata.get("commit") or index_metadata.get("git_commit"),
        "branch": artifact_metadata.get("branch"),
        "embedding_model": artifact_metadata.get("compatibility", {}).get(
            "embedding_model"
        )
        or index_metadata.get("embedding_model"),
        "schema_version": artifact_metadata.get("compatibility", {}).get(
            "schema_version"
        )
        or index_metadata.get("chunk_schema_version"),
    }


def _get_git_ref_info() -> dict[str, str | None]:
    """Return current repository HEAD and branch information."""
    info: dict[str, str | None] = {"head": None, "branch": None}
    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        info["head"] = head.stdout.strip()
    except Exception:
        return info

    try:
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        info["branch"] = branch.stdout.strip()
    except Exception:
        pass

    return info


def _merge_changes(*change_groups: list[FileChange]) -> list:
    """Combine file changes while preserving unique path/type pairs."""
    merged = []
    seen: set[tuple[str, str, str | None]] = set()
    for changes in change_groups:
        for change in changes:
            key = (change.path, change.change_type, change.old_path)
            if key in seen:
                continue
            seen.add(key)
            merged.append(change)
    return merged


def _print_reconcile_guidance() -> None:
    """Print reconcile guidance after restore or sync."""
    artifact_identity = _get_artifact_identity()
    git_info = _get_git_ref_info()

    if artifact_identity.get("commit"):
        click.echo(
            f"📦 Restored artifact commit: {artifact_identity['commit']}"
            + (
                f" ({artifact_identity['branch']})"
                if artifact_identity.get("branch")
                else ""
            )
        )
    if artifact_identity.get("embedding_model"):
        click.echo(
            f"🧠 Artifact embedding model: {artifact_identity['embedding_model']}"
        )

    if not artifact_identity.get("commit") or not git_info.get("head"):
        click.echo("ℹ️  Artifact restore complete. Git drift could not be determined.")
        return

    if artifact_identity["commit"] == git_info["head"]:
        click.echo("✅ Local HEAD matches the restored artifact commit.")
    detector = ChangeDetector(Path.cwd())
    committed_changes = []
    if artifact_identity["commit"] != git_info["head"]:
        from_commit = artifact_identity["commit"]
        if from_commit is not None:
            committed_changes = detector.get_changes_since_commit(from_commit, "HEAD")

    uncommitted_changes = detector.get_uncommitted_changes()
    all_changes = _merge_changes(committed_changes, uncommitted_changes)

    if not all_changes:
        click.echo("✅ No local drift detected. The restored artifact is ready to use.")
        return

    cost = detector.estimate_reindex_cost(all_changes)
    change_summary = (
        f"added/modified={cost['files_to_index']}, "
        f"deleted={cost['files_to_remove']}, moved={cost['files_to_move']}"
    )
    click.echo(
        f"🔄 Local drift detected relative to the restored artifact: {change_summary}"
    )
    if detector.should_use_incremental(all_changes):
        click.echo(
            "💡 Recommended: keep the restored artifact and let local incremental reindexing "
            "catch up these changes."
        )
    else:
        click.echo(
            "⚠️  Change volume is large; a local rebuild may be simpler than incremental catch-up."
        )


@click.group()
def artifact():
    """Manage index artifacts in GitHub Actions."""


@artifact.command()
@click.option("--validate", is_flag=True, help="Validate indexes before upload")
@click.option("--compress-only", is_flag=True, help="Only compress, do not upload")
@click.option(
    "--no-secure", is_flag=True, help="Disable secure export (include all files)"
)
def push(validate: bool, compress_only: bool, no_secure: bool):
    """Upload local indexes to GitHub Actions Artifacts."""
    try:
        # Check if indexes exist
        if not Path("code_index.db").exists():
            click.echo("❌ No code_index.db found. Run indexing first.")
            return

        # Build command
        cmd = [
            sys.executable,
            str(project_root / "scripts" / "index-artifact-upload.py"),
        ]

        if validate:
            cmd.append("--validate")

        if compress_only:
            cmd.extend(["--method", "direct"])

        if no_secure:
            cmd.append("--no-secure")

        # Run upload script
        result = _run_artifact_command(cmd)

        if result.returncode != 0:
            click.echo("❌ Upload failed", err=True)
            sys.exit(1)

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@artifact.command()
@click.option("--latest", is_flag=True, help="Download latest compatible artifact")
@click.option("--artifact-id", type=int, help="Download specific artifact by ID")
@click.option("--no-backup", is_flag=True, help="Skip backup of existing indexes")
def pull(latest: bool, artifact_id: Optional[int], no_backup: bool):
    """Download indexes from GitHub Actions Artifacts."""
    try:
        # Build command
        cmd = [
            sys.executable,
            str(project_root / "scripts" / "index-artifact-download.py"),
            "download",
        ]

        if latest:
            cmd.append("--latest")
        elif artifact_id:
            cmd.extend(["--artifact-id", str(artifact_id)])
        else:
            click.echo("❌ Specify --latest or --artifact-id")
            return

        if no_backup:
            cmd.append("--no-backup")

        # Run download script
        result = _run_artifact_command(cmd)

        if result.returncode != 0:
            click.echo("❌ Download failed", err=True)
            sys.exit(1)

        if not _verify_local_index_restored():
            click.echo(
                "❌ Download completed but no local index files were restored", err=True
            )
            sys.exit(1)

        restored = ", ".join(path.name for path in _get_restored_index_paths())
        click.echo(f"✅ Local index files restored: {restored}")
        _print_reconcile_guidance()

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@artifact.command()
@click.option("--filter", help="Filter artifact names")
def list(filter: Optional[str]):
    """List available index artifacts."""
    try:
        # Build command
        cmd = [
            sys.executable,
            str(project_root / "scripts" / "index-artifact-download.py"),
            "list",
        ]

        if filter:
            cmd.extend(["--filter", filter])

        # Run list command
        result = _run_artifact_command(cmd)

        if result.returncode != 0:
            click.echo("❌ List failed", err=True)
            sys.exit(1)

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@artifact.command()
def sync():
    """Sync indexes with GitHub (pull if needed, push if local is newer)."""
    try:
        click.echo("🔄 Checking index synchronization status...")

        # Check if we have local indexes
        has_local = Path("code_index.db").exists()

        if not has_local:
            click.echo("📥 No local indexes found. Pulling latest...")
            # Pull latest
            cmd = [
                sys.executable,
                str(project_root / "scripts" / "index-artifact-download.py"),
                "download",
                "--latest",
            ]
            result = _run_artifact_command(cmd)

            if result.returncode == 0:
                if not _verify_local_index_restored():
                    click.echo(
                        "❌ Sync download completed but no local index files were restored",
                        err=True,
                    )
                    sys.exit(1)
                restored = ", ".join(path.name for path in _get_restored_index_paths())
                click.echo(f"✅ Indexes synchronized! Restored: {restored}")
                _print_reconcile_guidance()
            else:
                click.echo("❌ Sync failed", err=True)
                sys.exit(1)

        else:
            # Check if local is newer than remote
            # For now, just show status
            click.echo("📊 Local indexes found:")

            # Get local stats
            import sqlite3

            conn = sqlite3.connect("code_index.db")
            cursor = conn.cursor()

            try:
                cursor.execute("SELECT COUNT(*) FROM files")
                file_count = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM symbols")
                symbol_count = cursor.fetchone()[0]

                click.echo(f"   Files: {file_count}")
                click.echo(f"   Symbols: {symbol_count}")

            except Exception:
                pass
            finally:
                conn.close()

            # Check remote artifacts
            click.echo("\n📡 Checking remote artifacts...")
            _print_reconcile_guidance()

            cmd = [
                sys.executable,
                str(project_root / "scripts" / "index-artifact-download.py"),
                "list",
            ]
            result = _run_artifact_command(cmd)

            if result.returncode == 0 and "Available Index Artifacts:" in result.stdout:
                # Parse output to check if update available
                lines = result.stdout.split("\n")
                has_artifacts = False

                for line in lines:
                    if "index-" in line and "MB" in line:
                        has_artifacts = True
                        break

                if has_artifacts:
                    click.echo("\n✅ Remote artifacts available")
                    click.echo("   Use 'mcp_cli.py artifact pull --latest' to update")
                    click.echo(
                        "   Use 'mcp_cli.py artifact push' to upload your indexes"
                    )
                else:
                    click.echo("\n📤 No remote artifacts found")
                    click.echo(
                        "   Use 'mcp_cli.py artifact push' to upload your indexes"
                    )

            click.echo("\n✅ Sync check complete!")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@artifact.command()
@click.option(
    "--older-than", type=int, default=30, help="Delete artifacts older than N days"
)
@click.option(
    "--keep-latest", type=int, default=5, help="Keep at least N latest artifacts"
)
@click.option(
    "--dry-run", is_flag=True, help="Show what would be deleted without deleting"
)
def cleanup(older_than: int, keep_latest: int, dry_run: bool):
    """Clean up old artifacts to save storage."""
    try:
        click.echo(f"🧹 Cleaning up artifacts older than {older_than} days...")
        click.echo(f"   Keeping at least {keep_latest} latest artifacts")

        if dry_run:
            click.echo("   🔍 DRY RUN - no changes will be made")

        # This would trigger the GitHub Actions workflow
        # For now, just show instructions
        click.echo("\n📝 To clean up artifacts, run:")
        click.echo("   gh workflow run index-artifact-management.yml -f action=cleanup")

        click.echo("\nOr use the GitHub Actions UI to trigger the cleanup workflow.")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@artifact.command()
@click.argument("artifact_id", type=int)
def info(artifact_id: int):
    """Show detailed information about a specific artifact."""
    try:
        # Build command
        cmd = [
            sys.executable,
            str(project_root / "scripts" / "index-artifact-download.py"),
            "info",
            str(artifact_id),
        ]

        # Run info command
        result = _run_artifact_command(cmd)

        if result.returncode != 0:
            click.echo("❌ Info failed", err=True)
            sys.exit(1)

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@artifact.command()
@click.option("--branch", help="Recover artifact for a branch")
@click.option("--commit", help="Recover artifact for a commit SHA")
@click.option("--no-backup", is_flag=True, help="Skip backup of existing indexes")
def recover(branch: Optional[str], commit: Optional[str], no_backup: bool):
    """Recover indexes from artifact matching branch/commit."""
    try:
        if not branch and not commit:
            click.echo("❌ Specify at least one of --branch or --commit", err=True)
            sys.exit(1)

        cmd = [
            sys.executable,
            str(project_root / "scripts" / "index-artifact-download.py"),
            "recover",
        ]

        if branch:
            cmd.extend(["--branch", branch])
        if commit:
            cmd.extend(["--commit", commit])
        if no_backup:
            cmd.append("--no-backup")

        result = _run_artifact_command(cmd)

        if result.returncode != 0:
            click.echo("❌ Recovery failed", err=True)
            sys.exit(1)

        if not _verify_local_index_restored():
            click.echo(
                "❌ Recovery completed but no local index files were restored", err=True
            )
            sys.exit(1)

        restored = ", ".join(path.name for path in _get_restored_index_paths())
        click.echo(f"✅ Local index files restored: {restored}")
        _print_reconcile_guidance()

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)
