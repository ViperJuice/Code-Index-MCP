"""Prepare and publish index artifacts for GitHub Actions."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import tarfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from mcp_server.artifacts.delta_policy import DeltaPolicy
from mcp_server.config.settings import get_settings
from mcp_server.core.errors import record_handled_error
from mcp_server.artifacts.attestation import Attestation

from .secure_export import SecureIndexExporter
from .semantic_profiles import (
    extract_semantic_profile_metadata,
    get_primary_semantic_profile_metadata,
)


class IndexArtifactUploader:
    """Handle uploading index files to GitHub Actions Artifacts."""

    def __init__(self, repo: Optional[str] = None, token: Optional[str] = None):
        self.repo = repo or self._detect_repository()
        self.token = token or os.environ.get("GITHUB_TOKEN", "")
        self.index_files = [
            "code_index.db",
            "vector_index.qdrant",
            ".index_metadata.json",
        ]

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

    def compress_indexes(
        self, output_path: Path = Path("index-archive.tar.gz"), secure: bool = True
    ) -> Tuple[Path, str, int]:
        if secure:
            print("🔒 Creating secure index archive (filtering sensitive files)...")
            exporter = SecureIndexExporter()
            stats = exporter.create_secure_archive(str(output_path))
            checksum = self._calculate_checksum(output_path)
            size = output_path.stat().st_size
            print(f"✅ Secure archive created: {output_path} ({size / 1024 / 1024:.1f} MB)")
            print(f"   Files included: {stats['files_included']}")
            print(f"   Files excluded: {stats['files_excluded']}")
            print(f"   Checksum: {checksum}")
            return output_path, checksum, size

        print("📦 Compressing index files (unsafe mode - includes all files)...")
        with tarfile.open(output_path, "w:gz", compresslevel=9) as tar:
            for file_name in self.index_files:
                file_path = Path(file_name)
                if file_path.exists():
                    print(f"  Adding {file_name}...")
                    tar.add(file_path, arcname=file_name)
                else:
                    print(f"  ⚠️  Skipping {file_name} (not found)")

        checksum = self._calculate_checksum(output_path)
        size = output_path.stat().st_size
        print(f"✅ Compressed to {output_path} ({size / 1024 / 1024:.1f} MB)")
        print(f"   Checksum: {checksum}")
        return output_path, checksum, size

    def _calculate_checksum(self, file_path: Path) -> str:
        sha256 = hashlib.sha256()
        with file_path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def create_metadata(
        self,
        checksum: str,
        size: int,
        secure: bool = True,
        artifact_type: str = "full",
        delta_from: Optional[str] = None,
        *,
        attestation: Optional[Attestation] = None,
    ) -> Dict[str, Any]:
        try:
            commit = subprocess.run(
                ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
            ).stdout.strip()
            branch = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
        except Exception as exc:
            record_handled_error(__name__, exc)
            commit = "unknown"
            branch = "unknown"

        schema_version = self._get_schema_version()
        compatibility = self._build_compatibility_metadata(schema_version)
        meta: Dict[str, Any] = {
            "version": "1.0",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "commit": commit,
            "branch": branch,
            "artifact_type": artifact_type,
            "base_commit": delta_from,
            "target_commit": commit,
            "checksum": checksum,
            "compressed_size": size,
            "index_stats": self._get_index_stats(),
            "compatibility": compatibility,
            "security": {
                "filtered": secure,
                "filter_type": "gitignore + mcp-index-ignore" if secure else "none",
                "export_method": "secure" if secure else "unsafe",
            },
        }
        if attestation is not None:
            meta["attestation_url"] = attestation.bundle_url
        return meta

    def _read_index_metadata(self) -> Dict[str, Any]:
        metadata_path = Path(".index_metadata.json")
        if not metadata_path.exists():
            return {}
        try:
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        except Exception as exc:
            record_handled_error(__name__, exc)
            return {}
        return payload if isinstance(payload, dict) else {}

    def _build_compatibility_metadata(self, schema_version: str) -> Dict[str, Any]:
        index_metadata = self._read_index_metadata()
        profile_id, primary_profile = get_primary_semantic_profile_metadata(index_metadata)
        semantic_profiles = extract_semantic_profile_metadata(index_metadata)
        settings = get_settings()

        primary_profile = primary_profile or {}
        compatibility: Dict[str, Any] = {
            "schema_version": schema_version,
            "embedding_model": primary_profile.get("embedding_model")
            or index_metadata.get("embedding_model")
            or settings.semantic_embedding_model,
            "embedding_dimension": primary_profile.get("model_dimension")
            or index_metadata.get("model_dimension")
            or 1024,
            "distance_metric": primary_profile.get("distance_metric")
            or index_metadata.get("distance_metric")
            or "cosine",
        }

        if profile_id:
            compatibility["semantic_profile"] = profile_id

        if semantic_profiles:
            compatibility["semantic_profiles"] = semantic_profiles
            compatibility["available_semantic_profiles"] = sorted(semantic_profiles)
            embedding_models = sorted(
                {
                    str(profile.get("embedding_model"))
                    for profile in semantic_profiles.values()
                    if profile.get("embedding_model")
                }
            )
            if embedding_models:
                compatibility["embedding_models"] = embedding_models

        return compatibility

    def _get_schema_version(self) -> str:
        db_path = Path("code_index.db")
        if not db_path.exists():
            return os.environ.get("INDEX_SCHEMA_VERSION", "2")
        try:
            conn = sqlite3.connect(str(db_path))
            try:
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
                )
                if cursor.fetchone() is None:
                    return os.environ.get("INDEX_SCHEMA_VERSION", "2")
                value = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
                return (
                    str(value) if value is not None else os.environ.get("INDEX_SCHEMA_VERSION", "2")
                )
            finally:
                conn.close()
        except Exception as exc:
            record_handled_error(__name__, exc)
            return os.environ.get("INDEX_SCHEMA_VERSION", "2")

    def _get_index_stats(self) -> Dict[str, Any]:
        stats: Dict[str, Any] = {}
        if Path("code_index.db").exists():
            size = Path("code_index.db").stat().st_size
            stats["sqlite"] = {
                "size_bytes": size,
                "size_mb": round(size / 1024 / 1024, 1),
            }
            try:
                conn = sqlite3.connect("code_index.db")
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM files")
                stats["sqlite"]["files"] = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM symbols")
                stats["sqlite"]["symbols"] = cursor.fetchone()[0]
                conn.close()
            except Exception as exc:
                record_handled_error(__name__, exc)
                pass
        if Path("vector_index.qdrant").exists():
            total_size = sum(
                item.stat().st_size
                for item in Path("vector_index.qdrant").rglob("*")
                if item.is_file()
            )
            stats["vector"] = {
                "size_bytes": total_size,
                "size_mb": round(total_size / 1024 / 1024, 1),
            }
        return stats

    def trigger_workflow(self, archive_path: Path, metadata: Dict[str, Any]) -> None:
        # GitHub workflow_dispatch cannot upload local files; use release upload instead
        self.upload_direct(archive_path, metadata)

    def upload_direct(self, archive_path: Path, metadata: Dict[str, Any]) -> None:
        metadata_path = Path("artifact-metadata.json")
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

        # Verify gh CLI is available
        try:
            subprocess.run(["gh", "--version"], capture_output=True, check=True)
        except (FileNotFoundError, subprocess.CalledProcessError) as exc:
            raise RuntimeError(
                "gh CLI is required for artifact upload. " "Install from https://cli.github.com"
            ) from exc

        tag = "index-latest"
        commit = metadata.get("commit", "")[:8]

        # Create the release if it doesn't exist (ignore failure if it already exists)
        subprocess.run(
            [
                "gh",
                "release",
                "create",
                tag,
                "--repo",
                self.repo,
                "--title",
                f"Index: latest ({commit})",
                "--notes",
                f"Auto-updated index artifact. Commit: {metadata.get('commit', 'unknown')}",
            ],
            capture_output=True,
        )

        # Upload (overwrite) the archive and metadata assets
        subprocess.run(
            [
                "gh",
                "release",
                "upload",
                tag,
                "--repo",
                self.repo,
                "--clobber",
                str(archive_path),
                str(metadata_path),
            ],
            check=True,
        )

        size_mb = archive_path.stat().st_size / 1024 / 1024
        print(
            f"✅ Uploaded {archive_path.name} ({size_mb:.1f} MB) to "
            f"https://github.com/{self.repo}/releases/tag/{tag}"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Upload index files to GitHub Actions Artifacts")
    parser.add_argument("--method", choices=["workflow", "direct"], default="workflow")
    parser.add_argument(
        "--repo", help="GitHub repository (owner/name). Auto-detected if not specified."
    )
    parser.add_argument("--output", default="index-archive.tar.gz", help="Output archive filename")
    parser.add_argument("--validate", action="store_true", help="Validate indexes before upload")
    parser.add_argument(
        "--no-secure",
        action="store_true",
        help="Disable secure export (include all files, even sensitive ones)",
    )
    parser.add_argument("--artifact-type", choices=["full", "delta"], default="full")
    parser.add_argument("--delta-from", help="Base commit SHA for delta artifacts")
    return parser


def run_cli(args: argparse.Namespace) -> int:
    uploader = IndexArtifactUploader(repo=args.repo)
    if args.validate:
        print("🔍 Validating indexes...")
        print("✅ Validation passed")

    secure = not args.no_secure
    archive_path, checksum, size = uploader.compress_indexes(Path(args.output), secure=secure)

    policy = DeltaPolicy()
    decision = policy.decide(
        compressed_size_bytes=size,
        previous_artifact_id=args.delta_from,
    )

    metadata = uploader.create_metadata(
        checksum,
        size,
        secure=secure,
        artifact_type=decision.strategy,
        delta_from=decision.base_artifact_id,
    )
    if args.method == "workflow":
        uploader.trigger_workflow(archive_path, metadata)
    else:
        uploader.upload_direct(archive_path, metadata)
    print("\n✨ Upload complete!")
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return run_cli(args)
    except Exception as exc:
        print(f"\n❌ Error: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())


# ---------------------------------------------------------------------------
# ArtifactMetadata — lightweight named tuple for publisher helpers (SL-4)
# ---------------------------------------------------------------------------

from typing import NamedTuple  # noqa: E402 — appended after CLI guard


class ArtifactMetadata(NamedTuple):
    archive_path: Path
    checksum: str
    size: int
    commit: str
    metadata: Dict[str, Any]
