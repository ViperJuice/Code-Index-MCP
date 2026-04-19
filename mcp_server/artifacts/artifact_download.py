"""Download and install index artifacts from GitHub Actions."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import shutil
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from mcp_server.storage.schema_migrator import SchemaMigrator, UnknownSchemaVersionError

logger = logging.getLogger(__name__)

from mcp_server.config.settings import get_settings
from mcp_server.core.errors import record_handled_error

from .attestation import Attestation, verify_attestation
from .integrity_gate import (
    ArtifactIntegrityGateResult,
    validate_artifact_integrity,
    validate_required_metadata_fields,
)
from .freshness import FreshnessVerdict, verify_artifact_freshness
from .semantic_profiles import extract_semantic_profile_metadata


@dataclass
class ArtifactDownloadResult:
    artifact: Optional[Dict[str, Any]] = None
    installed_items: Optional[List[str]] = None


class IndexArtifactDownloader:
    """Handle downloading index files from GitHub Actions Artifacts."""

    def __init__(self, repo: Optional[str] = None, token: Optional[str] = None):
        self.repo = repo or self._detect_repository()
        self.token = token or os.environ.get("GITHUB_TOKEN", "")
        self.api_base = f"https://api.github.com/repos/{self.repo}"
        if not self.token:
            print("⚠️  No GitHub token found. Using gh CLI for authentication.")

    def _detect_repository(self) -> str:
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                check=True,
            )
            url = result.stdout.strip()
            if "github.com" not in url:
                raise ValueError(f"Not a GitHub repository: {url}")
            if url.startswith("git@"):
                parts = url.split(":", 1)[1]
            else:
                parts = url.split("github.com/", 1)[1]
            return parts.rstrip(".git")
        except Exception as exc:
            raise RuntimeError(
                "Failed to detect repository. Pass --repo owner/name or run inside a "
                f"git clone with origin configured: {exc}"
            ) from exc

    def list_artifacts(self, name_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        print("🔍 Fetching available artifacts...")
        try:
            result = subprocess.run(
                [
                    "gh",
                    "api",
                    f"/repos/{self.repo}/actions/artifacts",
                    "--jq",
                    ".artifacts[]",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
        except FileNotFoundError as exc:
            raise RuntimeError("gh CLI is required for artifact download flows") from exc
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(f"Failed to list artifacts: {exc.stderr or exc}") from exc

        artifacts = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            artifact = json.loads(line)
            if artifact["name"].startswith(("index-", "mcp-index-")):
                if not name_filter or name_filter in artifact["name"]:
                    artifacts.append(artifact)

        artifacts.sort(key=lambda item: item["created_at"], reverse=True)
        return artifacts

    def download_artifact(self, artifact_id: int, output_dir: Path) -> Path:
        print(f"📥 Downloading artifact {artifact_id}...")
        temp_dir = Path(tempfile.mkdtemp())
        try:
            with (temp_dir / "artifact.zip").open("wb") as zip_file:
                subprocess.run(
                    [
                        "gh",
                        "api",
                        f"/repos/{self.repo}/actions/artifacts/{artifact_id}/zip",
                    ],
                    check=True,
                    stdout=zip_file,
                )

            import zipfile

            with zipfile.ZipFile(temp_dir / "artifact.zip", "r") as zip_ref:
                zip_ref.extractall(temp_dir)  # nosec B202 - temp dir, contents re-validated below

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

            if archive_path is None:
                raise ValueError("No archive found in artifact")
            if metadata_path is None:
                raise ValueError("Artifact metadata file is required but missing")

            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            gate_result = self._run_integrity_gate(metadata, archive_path, checksum_path)
            if gate_result.manifest_v2_validated:
                print("✅ Manifest v2 verified")

            compatible, issues = self.check_compatibility(metadata)
            if not compatible:
                raise ValueError("Artifact compatibility validation failed: " + "; ".join(issues))

            att_url = metadata.get("attestation_url")
            if att_url:
                sidecar_path = archive_path.with_suffix(archive_path.suffix + ".attestation.jsonl")
                att = Attestation(
                    bundle_url=att_url,
                    bundle_path=sidecar_path,
                    subject_digest="",
                    signed_at=datetime.now(timezone.utc),
                )
                verify_attestation(archive_path, att, expected_repo=self.repo, gh_cmd="gh")

            print("📦 Extracting index files...")
            with tarfile.open(archive_path, "r:gz") as tar:
                members = tar.getmembers()
                for member in members:
                    if not self._validate_tar_member(member, output_dir):
                        raise ValueError(f"Unsafe archive member blocked: {member.name}")
                tar.extractall(output_dir, members=members)  # nosec B202 - members validated above

            shutil.copy2(metadata_path, output_dir / "artifact-metadata.json")
            return output_dir
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _calculate_checksum(self, file_path: Path) -> str:
        sha256 = hashlib.sha256()
        with file_path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def check_compatibility(self, metadata: Dict[str, Any]) -> Tuple[bool, List[str]]:
        issues = []
        compatibility = metadata.get("compatibility", {})
        artifact_model = compatibility.get("embedding_model")
        artifact_schema = compatibility.get("schema_version")
        artifact_profiles = extract_semantic_profile_metadata(compatibility)

        required_schema = os.environ.get("INDEX_SCHEMA_VERSION")
        if not required_schema:
            local_db = Path("code_index.db")
            if local_db.exists():
                conn = None
                try:
                    conn = sqlite3.connect(str(local_db))
                    required_schema = str(
                        conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
                    )
                except Exception as exc:
                    record_handled_error(__name__, exc)
                    required_schema = None
                finally:
                    if conn is not None:
                        conn.close()
        if not required_schema:
            required_schema = "2"
        if artifact_schema != required_schema:
            migrator = SchemaMigrator(store=None)
            if not migrator.is_known(artifact_schema):
                raise UnknownSchemaVersionError(
                    f"Artifact schema version {artifact_schema!r} is unknown; "
                    f"supported: {migrator.SUPPORTED_VERSIONS}"
                )
            # Known older version — migration is possible; skip the hard mismatch issue.

        if artifact_profiles:
            try:
                requested_profiles = self._get_requested_semantic_profiles()
                if requested_profiles:
                    overlap = sorted(set(requested_profiles).intersection(artifact_profiles))
                    compatible_profiles = []
                    mismatched_profiles = []
                    for profile_id in overlap:
                        expected = requested_profiles.get(profile_id)
                        discovered = artifact_profiles[profile_id].get(
                            "compatibility_fingerprint"
                        ) or artifact_profiles[profile_id].get("compatibility_hash")
                        if expected and discovered and expected != discovered:
                            mismatched_profiles.append(profile_id)
                        else:
                            compatible_profiles.append(profile_id)

                    if not compatible_profiles:
                        if mismatched_profiles:
                            issues.append(
                                "Semantic profile fingerprint mismatch for profiles: "
                                + ", ".join(mismatched_profiles)
                            )
                        else:
                            issues.append(
                                "No compatible semantic profiles found: artifact has "
                                + ", ".join(sorted(artifact_profiles))
                                + "; local config expects "
                                + ", ".join(sorted(requested_profiles))
                            )
            except Exception as exc:
                record_handled_error(__name__, exc)
                pass
        elif artifact_model:
            try:
                current_model = None
                metadata_path = Path(".index_metadata.json")
                if metadata_path.exists():
                    current_model = json.loads(metadata_path.read_text(encoding="utf-8")).get(
                        "embedding_model"
                    )
                if not current_model:
                    current_model = get_settings().semantic_embedding_model
                if artifact_model != current_model:
                    issues.append(
                        f"Embedding model mismatch: artifact={artifact_model}, current={current_model}"
                    )
            except Exception as exc:
                record_handled_error(__name__, exc)
                pass

        return len(issues) == 0, issues

    def _get_requested_semantic_profiles(self) -> Dict[str, Optional[str]]:
        """Return locally configured semantic profile fingerprints, if available."""
        try:
            settings = get_settings()
            profiles = settings.get_semantic_profiles_config()
            requested: Dict[str, Optional[str]] = {}
            for profile_id, payload in profiles.items():
                if not isinstance(profile_id, str) or not isinstance(payload, dict):
                    continue
                requested[profile_id] = str(payload.get("compatibility_fingerprint", "")) or None

            if any(value for value in requested.values()):
                return requested

            from .semantic_profiles import SemanticProfileRegistry

            registry = SemanticProfileRegistry.from_raw(
                profiles,
                settings.get_semantic_default_profile(),
                tool_version=settings.app_version,
            )
            return {
                profile_id: profile.compatibility_fingerprint
                for profile_id, profile in registry.list().items()
            }
        except Exception as exc:
            record_handled_error(__name__, exc)
            return {}

    def find_best_artifact(self, artifacts: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        print("\n🔎 Finding best compatible artifact...")
        promoted = [artifact for artifact in artifacts if "-promoted" in artifact["name"]]
        if promoted:
            return promoted[0]
        default_branch = [
            artifact
            for artifact in artifacts
            if artifact["name"].startswith("mcp-index-")
            and not artifact["name"].startswith("mcp-index-pr-")
        ]
        if default_branch:
            return default_branch[0]
        return artifacts[0] if artifacts else None

    def find_recovery_artifact(
        self,
        artifacts: List[Dict[str, Any]],
        branch: Optional[str],
        commit: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        selected = artifacts
        if branch:
            selected = [
                artifact
                for artifact in selected
                if branch in artifact.get("name", "")
                or artifact.get("workflow_run", {}).get("head_branch") == branch
            ]
        if commit:
            short_commit = commit[:8]
            selected = [
                artifact
                for artifact in selected
                if commit in artifact.get("name", "")
                or short_commit in artifact.get("name", "")
                or artifact.get("workflow_run", {}).get("head_sha", "") == commit
            ]
        if not selected:
            return None
        promoted = [artifact for artifact in selected if "-promoted" in artifact["name"]]
        return promoted[0] if promoted else selected[0]

    def _run_integrity_gate(
        self,
        metadata: Dict[str, Any],
        archive_path: Path,
        checksum_path: Optional[Path],
    ) -> ArtifactIntegrityGateResult:
        gate_result = validate_artifact_integrity(
            metadata=metadata,
            archive_path=archive_path,
            checksum_path=checksum_path,
        )
        if not gate_result.passed:
            raise ValueError("Artifact integrity gate failed: " + "; ".join(gate_result.reasons))
        print("✅ Integrity gate passed")
        return gate_result

    def _validate_metadata(self, metadata: Dict[str, Any]) -> Optional[str]:
        reasons = validate_required_metadata_fields(metadata)
        return reasons[0] if reasons else None

    def _is_within_directory(self, base_dir: Path, candidate_path: Path) -> bool:
        try:
            candidate_path.resolve().relative_to(base_dir.resolve())
            return True
        except ValueError:
            return False

    def _validate_tar_member(self, member: tarfile.TarInfo, extraction_dir: Path) -> bool:
        target_path = extraction_dir / member.name
        if not self._is_within_directory(extraction_dir, target_path):
            return False
        if member.issym():
            if not member.linkname:
                return False
            if not self._is_within_directory(extraction_dir, target_path.parent / member.linkname):
                return False
        if member.islnk():
            if not member.linkname:
                return False
            if not self._is_within_directory(extraction_dir, extraction_dir / member.linkname):
                return False
        return not member.isdev()

    def install_indexes(self, source_dir: Path, backup: bool = True) -> List[str]:
        print("\n📝 Installing indexes...")
        if backup:
            backup_dir = Path(f"index_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            backup_dir.mkdir(exist_ok=True)
            for file_name in [
                "code_index.db",
                "vector_index.qdrant",
                ".index_metadata.json",
            ]:
                src = Path(file_name)
                if not src.exists():
                    continue
                print(f"  Backing up {file_name}...")
                if src.is_dir():
                    shutil.copytree(src, backup_dir / file_name)
                else:
                    shutil.copy2(src, backup_dir / file_name)
            print(f"  ✅ Backup created in {backup_dir}")

        installed_items: List[str] = []
        for item in source_dir.iterdir():
            if item.name not in {
                "code_index.db",
                "vector_index.qdrant",
                ".index_metadata.json",
                "artifact-metadata.json",
            }:
                continue
            dest = Path(item.name)
            if dest.exists():
                if dest.is_dir():
                    shutil.rmtree(dest)
                else:
                    dest.unlink()
            print(f"  Installing {item.name}...")
            if item.is_dir():
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)
            installed_items.append(item.name)

        print("✅ Indexes installed successfully!")
        if installed_items:
            print(f"📦 Restored items: {', '.join(installed_items)}")
        metadata_path = source_dir / "artifact-metadata.json"
        if metadata_path.exists():
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                commit = metadata.get("commit")
                branch = metadata.get("branch")
                if commit:
                    label = f"{commit} ({branch})" if branch else commit
                    print(f"🔖 Restored artifact commit: {label}")
            except Exception as exc:
                record_handled_error(__name__, exc)
                pass
        return installed_items

    def download_selected_artifact(
        self,
        artifact: Dict[str, Any],
        *,
        output_dir: Path,
        backup: bool = True,
    ) -> ArtifactDownloadResult:
        try:
            extracted_dir = self.download_artifact(artifact["id"], output_dir)
        except (subprocess.CalledProcessError, urllib.error.URLError, RuntimeError) as exc:
            logger.warning(
                "GitHub outage detected, keeping local index (artifact download failed: %s)", exc
            )
            return ArtifactDownloadResult(artifact=artifact, installed_items=[])

        # Freshness gate — between metadata-load and install_indexes.
        meta_path = extracted_dir / "artifact-metadata.json"
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception as exc:
                record_handled_error(__name__, exc)
                meta = {}
        else:
            meta = {}

        max_age_days = int(os.environ.get("MCP_ARTIFACT_MAX_AGE_DAYS", "14"))
        head_commit = artifact.get("workflow_run", {}).get("head_sha", "HEAD")
        verdict = verify_artifact_freshness(meta, head_commit, max_age_days)
        if verdict is FreshnessVerdict.STALE_COMMIT:
            logger.warning(
                "Artifact commit %s is not an ancestor of %s (STALE_COMMIT); proceeding with install",
                meta.get("commit"),
                head_commit,
            )
        elif verdict is FreshnessVerdict.STALE_AGE:
            logger.warning(
                "Artifact is older than %d days (STALE_AGE); proceeding with install",
                max_age_days,
            )
        elif verdict is FreshnessVerdict.INVALID:
            logger.warning("Artifact metadata missing or malformed (INVALID); proceeding with install")

        installed_items = self.install_indexes(extracted_dir, backup=backup)
        return ArtifactDownloadResult(artifact=artifact, installed_items=installed_items)

    def download_latest(
        self,
        *,
        output_dir: Path,
        backup: bool = True,
        full_only: bool = False,
    ) -> ArtifactDownloadResult:
        artifacts = self.list_artifacts()
        if full_only:
            artifacts = [a for a in artifacts if "-delta-" not in a.get("name", "")]
        best = self.find_best_artifact(artifacts)
        if not best:
            raise RuntimeError("No compatible artifacts found")
        print(f"\n✅ Selected: {best['name']}")
        return self.download_selected_artifact(best, output_dir=output_dir, backup=backup)

    def recover(
        self,
        *,
        branch: Optional[str],
        commit: Optional[str],
        output_dir: Path,
        backup: bool = True,
    ) -> ArtifactDownloadResult:
        artifacts = self.list_artifacts()
        selected = self.find_recovery_artifact(artifacts, branch=branch, commit=commit)
        if not selected:
            details = []
            if branch:
                details.append(f"branch={branch}")
            if commit:
                details.append(f"commit={commit}")
            raise RuntimeError(
                "No matching artifact found for recovery criteria"
                + (f" ({', '.join(details)})" if details else "")
            )
        print(f"\n✅ Recovery artifact selected: {selected['name']}")
        return self.download_selected_artifact(selected, output_dir=output_dir, backup=backup)


def format_artifact_table(artifacts: List[Dict[str, Any]]) -> None:
    if not artifacts:
        print("No artifacts found.")
        return
    print("\n📦 Available Index Artifacts:")
    print("=" * 80)
    print(f"{'Name':<40} {'Size':>10} {'Created':<20} {'Promoted'}")
    print("-" * 80)
    for artifact in artifacts[:10]:
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Download index files from GitHub Actions Artifacts"
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    list_parser = subparsers.add_parser("list", help="List available artifacts")
    list_parser.add_argument("--filter", help="Filter artifact names")

    download_parser = subparsers.add_parser("download", help="Download and install indexes")
    download_parser.add_argument("--artifact-id", type=int, help="Specific artifact ID to download")
    download_parser.add_argument(
        "--latest", action="store_true", help="Download latest compatible artifact"
    )
    download_parser.add_argument(
        "--full-only",
        action="store_true",
        help="Only allow full artifacts (skip delta artifacts)",
    )
    download_parser.add_argument(
        "--no-backup", action="store_true", help="Skip backup of existing indexes"
    )
    download_parser.add_argument("--output-dir", default=".", help="Output directory")

    info_parser = subparsers.add_parser("info", help="Show artifact information")
    info_parser.add_argument("artifact_id", type=int, help="Artifact ID")

    recover_parser = subparsers.add_parser(
        "recover", help="Recover index from artifact matching branch/commit"
    )
    recover_parser.add_argument("--branch", help="Target branch name")
    recover_parser.add_argument("--commit", help="Target commit SHA")
    recover_parser.add_argument(
        "--no-backup", action="store_true", help="Skip backup of existing indexes"
    )
    recover_parser.add_argument("--output-dir", default=".", help="Output directory")

    parser.add_argument("--repo", help="GitHub repository (owner/name)")
    return parser


def run_cli(args: argparse.Namespace) -> int:
    downloader = IndexArtifactDownloader(repo=args.repo)
    if args.command == "list":
        artifacts = downloader.list_artifacts(name_filter=args.filter)
        format_artifact_table(artifacts)
        if artifacts:
            print(f"\nTotal: {len(artifacts)} artifacts")
        return 0

    if args.command == "download":
        output_dir = Path(args.output_dir) / "artifact_download"
        output_dir.mkdir(exist_ok=True)
        try:
            if args.artifact_id:
                artifact = next(
                    (
                        item
                        for item in downloader.list_artifacts()
                        if item["id"] == args.artifact_id
                    ),
                    {"id": args.artifact_id, "name": str(args.artifact_id)},
                )
                downloader.download_selected_artifact(
                    artifact, output_dir=output_dir, backup=not args.no_backup
                )
            elif args.latest:
                downloader.download_latest(
                    output_dir=output_dir,
                    backup=not args.no_backup,
                    full_only=args.full_only,
                )
            else:
                print("❌ Specify --artifact-id or --latest")
                return 1
        finally:
            shutil.rmtree(output_dir, ignore_errors=True)
        return 0

    if args.command == "info":
        artifacts = downloader.list_artifacts()
        artifact = next((item for item in artifacts if item["id"] == args.artifact_id), None)
        if artifact is None:
            print(f"❌ Artifact {args.artifact_id} not found")
            return 1
        print("\n📋 Artifact Information:")
        print(f"   Name: {artifact['name']}")
        print(f"   ID: {artifact['id']}")
        print(f"   Size: {artifact['size_in_bytes'] / 1024 / 1024:.1f} MB")
        print(f"   Created: {artifact['created_at']}")
        print(f"   Expires: {artifact['expires_at']}")
        return 0

    if args.command == "recover":
        if not args.branch and not args.commit:
            print("❌ Specify at least one of --branch or --commit")
            return 1
        output_dir = Path(args.output_dir) / "artifact_recovery"
        output_dir.mkdir(exist_ok=True)
        try:
            downloader.recover(
                branch=args.branch,
                commit=args.commit,
                output_dir=output_dir,
                backup=not args.no_backup,
            )
        finally:
            shutil.rmtree(output_dir, ignore_errors=True)
        return 0

    print(build_parser().format_help())
    return 1


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 1
    try:
        return run_cli(args)
    except Exception as exc:
        print(f"\n❌ Error: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
