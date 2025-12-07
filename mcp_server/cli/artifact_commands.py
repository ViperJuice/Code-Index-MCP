"""
CLI commands for managing index artifacts in GitHub Actions.

This module provides commands for uploading, downloading, and managing
index artifacts using GitHub Actions Artifacts storage.
"""

import subprocess
import sys
from pathlib import Path
from typing import Optional

import click

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


@click.group()
def artifact():
    """Manage index artifacts in GitHub Actions."""


@artifact.command()
@click.option("--validate", is_flag=True, help="Validate indexes before upload")
@click.option("--compress-only", is_flag=True, help="Only compress, do not upload")
@click.option("--no-secure", is_flag=True, help="Disable secure export (include all files)")
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
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.stdout:
            click.echo(result.stdout)

        if result.stderr:
            click.echo(result.stderr, err=True)

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
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.stdout:
            click.echo(result.stdout)

        if result.stderr:
            click.echo(result.stderr, err=True)

        if result.returncode != 0:
            click.echo("❌ Download failed", err=True)
            sys.exit(1)

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
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.stdout:
            click.echo(result.stdout)

        if result.stderr:
            click.echo(result.stderr, err=True)

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
            result = subprocess.run(cmd)

            if result.returncode == 0:
                click.echo("✅ Indexes synchronized!")
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

            cmd = [
                sys.executable,
                str(project_root / "scripts" / "index-artifact-download.py"),
                "list",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)

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
                    click.echo("   Use 'mcp_cli.py artifact push' to upload your indexes")
                else:
                    click.echo("\n📤 No remote artifacts found")
                    click.echo("   Use 'mcp_cli.py artifact push' to upload your indexes")

            click.echo("\n✅ Sync check complete!")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@artifact.command()
@click.option("--older-than", type=int, default=30, help="Delete artifacts older than N days")
@click.option("--keep-latest", type=int, default=5, help="Keep at least N latest artifacts")
@click.option("--dry-run", is_flag=True, help="Show what would be deleted without deleting")
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
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.stdout:
            click.echo(result.stdout)

        if result.stderr:
            click.echo(result.stderr, err=True)

        if result.returncode != 0:
            click.echo("❌ Info failed", err=True)
            sys.exit(1)

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)
