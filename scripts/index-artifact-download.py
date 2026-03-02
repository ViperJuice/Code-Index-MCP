#!/usr/bin/env python3
"""
Download index files from GitHub Actions Artifacts.

This script downloads and installs index files from GitHub Actions Artifacts,
enabling developers to quickly get up-to-date indexes without rebuilding.
"""

import os
import sys
import json
import tarfile
import hashlib
import subprocess
import argparse
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class IndexArtifactDownloader:
    """Handle downloading index files from GitHub Actions Artifacts."""

    def __init__(self, repo: Optional[str] = None, token: Optional[str] = None):
        """
        Initialize downloader.

        Args:
            repo: GitHub repository (owner/name). If None, detect from git.
            token: GitHub token. If None, use environment variable.
        """
        self.repo = repo or self._detect_repository()
        self.token = token or os.environ.get("GITHUB_TOKEN", "")
        self.api_base = f"https://api.github.com/repos/{self.repo}"

        if not self.token:
            print("⚠️  No GitHub token found. Using gh CLI for authentication.")

    def _detect_repository(self) -> str:
        """Detect repository from git remote."""
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                check=True,
            )
            url = result.stdout.strip()

            # Extract owner/repo from URL
            if "github.com" in url:
                if url.startswith("git@"):
                    # SSH format: git@github.com:owner/repo.git
                    parts = url.split(":")[1]
                else:
                    # HTTPS format: https://github.com/owner/repo.git
                    parts = url.split("github.com/")[1]

                return parts.rstrip(".git")

            raise ValueError(f"Not a GitHub repository: {url}")

        except Exception as e:
            raise RuntimeError(f"Failed to detect repository: {e}")

    def list_artifacts(self, name_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List available index artifacts.

        Args:
            name_filter: Optional filter for artifact names

        Returns:
            List of artifact metadata
        """
        print("🔍 Fetching available artifacts...")

        # Use gh CLI to list artifacts
        try:
            cmd = [
                "gh",
                "api",
                f"/repos/{self.repo}/actions/artifacts",
                "--jq",
                ".artifacts[]",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            artifacts = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    artifact = json.loads(line)
                    # Filter for index artifacts produced by both workflows
                    if artifact["name"].startswith(("index-", "mcp-index-")):
                        if not name_filter or name_filter in artifact["name"]:
                            artifacts.append(artifact)

            # Sort by created date (newest first)
            artifacts.sort(key=lambda x: x["created_at"], reverse=True)

            return artifacts

        except Exception as e:
            print(f"❌ Failed to list artifacts: {e}")
            return []

    def download_artifact(self, artifact_id: int, output_dir: Path) -> Path:
        """
        Download a specific artifact.

        Args:
            artifact_id: GitHub artifact ID
            output_dir: Directory to extract files to

        Returns:
            Path to extracted files
        """
        print(f"📥 Downloading artifact {artifact_id}...")

        # Create temp directory for download
        temp_dir = Path(tempfile.mkdtemp())

        try:
            # Use gh CLI to download
            cmd = [
                "gh",
                "api",
                f"/repos/{self.repo}/actions/artifacts/{artifact_id}/zip",
                "--output",
                str(temp_dir / "artifact.zip"),
            ]
            subprocess.run(cmd, check=True)

            # Extract zip file
            import zipfile

            with zipfile.ZipFile(temp_dir / "artifact.zip", "r") as zip_ref:
                zip_ref.extractall(temp_dir)

            # Find the tar.gz archive
            archive_path = None
            metadata_path = None
            checksum_path = None

            for file in temp_dir.iterdir():
                if file.name.endswith(".tar.gz"):
                    archive_path = file
                elif file.name == "artifact-metadata.json":
                    metadata_path = file
                elif file.name.endswith(".sha256"):
                    checksum_path = file

            if not archive_path:
                raise ValueError("No archive found in artifact")

            if not metadata_path:
                raise ValueError("Artifact metadata file is required but missing")

            with open(metadata_path, "r") as f:
                metadata = json.load(f)

            metadata_error = self._validate_metadata(metadata)
            if metadata_error:
                raise ValueError(f"Invalid artifact metadata: {metadata_error}")

            # Verify checksum (required)
            if checksum_path and checksum_path.exists():
                expected_checksum = checksum_path.read_text().split()[0]
            else:
                expected_checksum = metadata.get("checksum")

            if not expected_checksum:
                raise ValueError("Artifact checksum is required but missing")

            actual_checksum = self._calculate_checksum(archive_path)
            if actual_checksum != expected_checksum:
                raise ValueError(
                    f"Checksum mismatch! Expected: {expected_checksum}, Got: {actual_checksum}"
                )
            print("✅ Checksum verified")

            compatible, issues = self.check_compatibility(metadata)
            if not compatible:
                issue_text = "; ".join(issues)
                raise ValueError(f"Artifact compatibility validation failed: {issue_text}")

            # Extract archive
            print("📦 Extracting index files...")
            with tarfile.open(archive_path, "r:gz") as tar:
                members = tar.getmembers()
                for member in members:
                    if not self._validate_tar_member(member, output_dir):
                        raise ValueError(f"Unsafe archive member blocked: {member.name}")

                tar.extractall(output_dir, members=members)

            # Copy metadata if exists
            if metadata_path:
                shutil.copy2(metadata_path, output_dir / "artifact-metadata.json")

            return output_dir

        finally:
            # Clean up temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def check_compatibility(self, metadata: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Check if artifact is compatible with current configuration.

        Returns:
            Tuple of (is_compatible, list_of_issues)
        """
        issues = []

        compatibility = metadata.get("compatibility", {})
        artifact_model = compatibility.get("embedding_model")
        artifact_schema = compatibility.get("schema_version")

        required_schema = os.environ.get("INDEX_SCHEMA_VERSION", "2")
        if artifact_schema != required_schema:
            issues.append(
                f"Schema mismatch: artifact={artifact_schema}, required={required_schema}"
            )

        if artifact_model:
            try:
                from mcp_server.config.settings import get_settings

                current_model = get_settings().semantic_embedding_model

                if artifact_model != current_model:
                    issues.append(
                        f"Embedding model mismatch: artifact={artifact_model}, current={current_model}"
                    )
            except:
                pass

        # Check file structure
        # Could add more checks here

        return len(issues) == 0, issues

    def find_best_artifact(self, artifacts: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Find the best compatible artifact to download.

        Args:
            artifacts: List of available artifacts

        Returns:
            Best artifact or None
        """
        print("\n🔎 Finding best compatible artifact...")

        # Look for promoted artifacts first
        promoted = [a for a in artifacts if "-promoted" in a["name"]]
        if promoted:
            return promoted[0]

        # Prefer default-branch artifacts before PR/branch-scoped artifacts
        default_branch = [
            a
            for a in artifacts
            if a["name"].startswith("mcp-index-") and not a["name"].startswith("mcp-index-pr-")
        ]
        if default_branch:
            return default_branch[0]

        # Otherwise, return the latest
        if artifacts:
            return artifacts[0]

        return None

    def find_recovery_artifact(
        self,
        artifacts: List[Dict[str, Any]],
        branch: Optional[str],
        commit: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        """Find the best artifact matching recovery criteria."""
        if not artifacts:
            return None

        selected = artifacts

        if branch:
            selected = [
                a
                for a in selected
                if branch in a.get("name", "")
                or a.get("workflow_run", {}).get("head_branch") == branch
            ]

        if commit:
            short_commit = commit[:8]
            selected = [
                a
                for a in selected
                if commit in a.get("name", "")
                or short_commit in a.get("name", "")
                or a.get("workflow_run", {}).get("head_sha", "") == commit
            ]

        if not selected:
            return None

        promoted = [a for a in selected if "-promoted" in a["name"]]
        if promoted:
            return promoted[0]

        return selected[0]

    def _validate_metadata(self, metadata: Dict[str, Any]) -> Optional[str]:
        """Validate required artifact metadata fields."""
        required_keys = ["checksum", "commit", "branch", "timestamp", "compatibility"]
        for key in required_keys:
            if key not in metadata:
                return f"missing key: {key}"

        compatibility = metadata.get("compatibility")
        if not isinstance(compatibility, dict):
            return "compatibility must be an object"

        for key in ["schema_version", "embedding_model"]:
            if key not in compatibility:
                return f"missing compatibility key: {key}"

        return None

    def _is_within_directory(self, base_dir: Path, candidate_path: Path) -> bool:
        """Check if candidate resolves under base directory."""
        try:
            candidate_path.resolve().relative_to(base_dir.resolve())
            return True
        except ValueError:
            return False

    def _validate_tar_member(self, member: tarfile.TarInfo, extraction_dir: Path) -> bool:
        """Validate tar member path and link safety."""
        target_path = extraction_dir / member.name
        if not self._is_within_directory(extraction_dir, target_path):
            return False

        if member.issym():
            if not member.linkname:
                return False
            link_target = target_path.parent / member.linkname
            if not self._is_within_directory(extraction_dir, link_target):
                return False

        if member.islnk():
            if not member.linkname:
                return False
            link_target = extraction_dir / member.linkname
            if not self._is_within_directory(extraction_dir, link_target):
                return False

        if member.isdev():
            return False

        return True

    def install_indexes(self, source_dir: Path, backup: bool = True) -> None:
        """
        Install downloaded indexes to the working directory.

        Args:
            source_dir: Directory containing extracted index files
            backup: Whether to backup existing indexes
        """
        print("\n📝 Installing indexes...")

        # Backup existing indexes if requested
        if backup:
            backup_dir = Path(f"index_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            backup_dir.mkdir(exist_ok=True)

            for file_name in [
                "code_index.db",
                "vector_index.qdrant",
                ".index_metadata.json",
            ]:
                src = Path(file_name)
                if src.exists():
                    print(f"  Backing up {file_name}...")
                    if src.is_dir():
                        shutil.copytree(src, backup_dir / file_name)
                    else:
                        shutil.copy2(src, backup_dir / file_name)

            print(f"  ✅ Backup created in {backup_dir}")

        # Install new indexes
        for item in source_dir.iterdir():
            if item.name in [
                "code_index.db",
                "vector_index.qdrant",
                ".index_metadata.json",
                "artifact-metadata.json",
            ]:
                dest = Path(item.name)

                # Remove existing
                if dest.exists():
                    if dest.is_dir():
                        shutil.rmtree(dest)
                    else:
                        dest.unlink()

                # Copy new
                print(f"  Installing {item.name}...")
                if item.is_dir():
                    shutil.copytree(item, dest)
                else:
                    shutil.copy2(item, dest)

        print("✅ Indexes installed successfully!")


def format_artifact_table(artifacts: List[Dict[str, Any]]) -> None:
    """Pretty print artifacts as a table."""
    if not artifacts:
        print("No artifacts found.")
        return

    print("\n📦 Available Index Artifacts:")
    print("=" * 80)
    print(f"{'Name':<40} {'Size':>10} {'Created':<20} {'Promoted'}")
    print("-" * 80)

    for artifact in artifacts[:10]:  # Show latest 10
        name = artifact["name"]
        if len(name) > 40:
            name = name[:37] + "..."

        size_mb = artifact["size_in_bytes"] / 1024 / 1024
        created = datetime.fromisoformat(artifact["created_at"].replace("Z", "+00:00"))
        created_str = created.strftime("%Y-%m-%d %H:%M")
        promoted = "✓" if "-promoted" in artifact["name"] else ""

        print(f"{name:<40} {size_mb:>8.1f}MB {created_str:<20} {promoted}")

    if len(artifacts) > 10:
        print(f"\n... and {len(artifacts) - 10} more artifacts")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Download index files from GitHub Actions Artifacts"
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # List command
    list_parser = subparsers.add_parser("list", help="List available artifacts")
    list_parser.add_argument("--filter", help="Filter artifact names")

    # Download command
    download_parser = subparsers.add_parser("download", help="Download and install indexes")
    download_parser.add_argument("--artifact-id", type=int, help="Specific artifact ID to download")
    download_parser.add_argument(
        "--latest", action="store_true", help="Download latest compatible artifact"
    )
    download_parser.add_argument(
        "--no-backup", action="store_true", help="Skip backup of existing indexes"
    )
    download_parser.add_argument("--output-dir", default=".", help="Output directory")

    # Info command
    info_parser = subparsers.add_parser("info", help="Show artifact information")
    info_parser.add_argument("artifact_id", type=int, help="Artifact ID")

    # Recover command
    recover_parser = subparsers.add_parser(
        "recover",
        help="Recover index from artifact matching branch/commit",
    )
    recover_parser.add_argument("--branch", help="Target branch name")
    recover_parser.add_argument("--commit", help="Target commit SHA")
    recover_parser.add_argument(
        "--no-backup", action="store_true", help="Skip backup of existing indexes"
    )
    recover_parser.add_argument("--output-dir", default=".", help="Output directory")

    parser.add_argument("--repo", help="GitHub repository (owner/name)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        downloader = IndexArtifactDownloader(repo=args.repo)

        if args.command == "list":
            artifacts = downloader.list_artifacts(name_filter=args.filter)
            format_artifact_table(artifacts)

            if artifacts:
                print(f"\nTotal: {len(artifacts)} artifacts")

        elif args.command == "download":
            if args.artifact_id:
                # Download specific artifact
                output_dir = Path(args.output_dir) / "artifact_download"
                output_dir.mkdir(exist_ok=True)

                extracted_dir = downloader.download_artifact(args.artifact_id, output_dir)

                # Check compatibility
                metadata_file = extracted_dir / "artifact-metadata.json"
                if metadata_file.exists():
                    with open(metadata_file, "r") as f:
                        metadata = json.load(f)

                    compatible, issues = downloader.check_compatibility(metadata)
                    if not compatible:
                        print("\n❌ Compatibility issues detected:")
                        for issue in issues:
                            print(f"   - {issue}")
                        sys.exit(1)

                # Install
                downloader.install_indexes(extracted_dir, backup=not args.no_backup)

                # Clean up
                shutil.rmtree(output_dir, ignore_errors=True)

            elif args.latest:
                # Find and download latest compatible
                artifacts = downloader.list_artifacts()
                best = downloader.find_best_artifact(artifacts)

                if not best:
                    print("❌ No compatible artifacts found")
                    sys.exit(1)

                print(f"\n✅ Selected: {best['name']}")

                # Download and install
                output_dir = Path(args.output_dir) / "artifact_download"
                output_dir.mkdir(exist_ok=True)

                extracted_dir = downloader.download_artifact(best["id"], output_dir)
                downloader.install_indexes(extracted_dir, backup=not args.no_backup)

                # Clean up
                shutil.rmtree(output_dir, ignore_errors=True)

            else:
                print("❌ Specify --artifact-id or --latest")
                sys.exit(1)

        elif args.command == "info":
            # Show artifact info
            artifacts = downloader.list_artifacts()
            artifact = next((a for a in artifacts if a["id"] == args.artifact_id), None)

            if not artifact:
                print(f"❌ Artifact {args.artifact_id} not found")
                sys.exit(1)

            print(f"\n📋 Artifact Information:")
            print(f"   Name: {artifact['name']}")
            print(f"   ID: {artifact['id']}")
            print(f"   Size: {artifact['size_in_bytes'] / 1024 / 1024:.1f} MB")
            print(f"   Created: {artifact['created_at']}")
            print(f"   Expires: {artifact['expires_at']}")

            # Try to get metadata
            # (Would need to download to get full metadata)

        elif args.command == "recover":
            if not args.branch and not args.commit:
                print("❌ Specify at least one of --branch or --commit")
                sys.exit(1)

            artifacts = downloader.list_artifacts()
            selected = downloader.find_recovery_artifact(
                artifacts,
                branch=args.branch,
                commit=args.commit,
            )

            if not selected:
                print("❌ No matching artifact found for recovery criteria")
                if args.branch:
                    print(f"   branch={args.branch}")
                if args.commit:
                    print(f"   commit={args.commit}")
                sys.exit(1)

            print(f"\n✅ Recovery artifact selected: {selected['name']}")

            output_dir = Path(args.output_dir) / "artifact_recovery"
            output_dir.mkdir(exist_ok=True)

            extracted_dir = downloader.download_artifact(selected["id"], output_dir)
            downloader.install_indexes(extracted_dir, backup=not args.no_backup)

            shutil.rmtree(output_dir, ignore_errors=True)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
