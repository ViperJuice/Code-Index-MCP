#!/usr/bin/env python3
"""
Download release artifacts from GitHub releases.

Supports both legacy pre-built index archives and the current package-release
artifacts (wheel, sdist, changelog, deployment guide, and SBOM).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import Any, Optional

import requests

PACKAGE_ASSET_PATTERNS = {
    "wheel": ("index_it_mcp-", ".whl"),
    "sdist": ("index_it_mcp-", ".tar.gz"),
    "changelog": ("CHANGELOG", ".md"),
    "deployment_guide": ("DEPLOYMENT-GUIDE", ".md"),
    "sbom": ("sbom", ".json"),
}
LEGACY_INDEX_PREFIX = "code-index-"


class GitHubReleaseDownloader:
    """Download release artifacts from GitHub releases."""

    def __init__(self, repo: Optional[str] = None):
        self.repo = repo or self._detect_repository()
        self.api_base = f"https://api.github.com/repos/{self.repo}"

    def _detect_repository(self) -> str:
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                check=True,
            )
            url = result.stdout.strip()
            if "github.com" in url:
                if url.startswith("git@"):
                    return url.split(":")[1].replace(".git", "").strip()
                return url.split("github.com/")[1].replace(".git", "").strip()
        except Exception:
            pass

        return "ViperJuice/Code-Index-MCP"

    def _classify_asset(self, asset_name: str) -> Optional[str]:
        for asset_kind, (prefix, suffix) in PACKAGE_ASSET_PATTERNS.items():
            if asset_name.startswith(prefix) and asset_name.endswith(suffix):
                return asset_kind
        if asset_name.startswith(LEGACY_INDEX_PREFIX) and asset_name.endswith(".tar.gz"):
            return "legacy_index"
        return None

    def _fetch_releases(self) -> list[dict[str, Any]]:
        try:
            result = subprocess.run(
                ["gh", "api", f"/repos/{self.repo}/releases", "--paginate"],
                capture_output=True,
                text=True,
                check=True,
            )
            return json.loads(result.stdout)
        except Exception:
            response = requests.get(f"{self.api_base}/releases", timeout=30)
            response.raise_for_status()
            return response.json()

    def list_releases(self) -> list[dict[str, Any]]:
        print(f"📋 Fetching releases from {self.repo}...")

        try:
            releases = self._fetch_releases()
        except Exception as exc:
            print(f"❌ Error fetching releases: {exc}")
            return []

        artifact_releases = []
        for release in releases:
            assets = []
            for asset in release.get("assets", []):
                asset_kind = self._classify_asset(asset["name"])
                if asset_kind is None:
                    continue
                assets.append(
                    {
                        "asset_kind": asset_kind,
                        "asset_name": asset["name"],
                        "asset_size": asset["size"],
                        "download_url": asset["browser_download_url"],
                    }
                )
            if assets:
                artifact_releases.append(
                    {
                        "tag": release["tag_name"],
                        "name": release["name"],
                        "published": release["published_at"],
                        "assets": assets,
                    }
                )

        return artifact_releases

    def _download_asset(self, tag: str, asset_name: str, download_url: str, output_path: Path) -> None:
        try:
            subprocess.run(
                [
                    "gh",
                    "release",
                    "download",
                    tag,
                    "--repo",
                    self.repo,
                    "--pattern",
                    asset_name,
                    "--output",
                    str(output_path),
                ],
                check=True,
            )
            return
        except Exception:
            response = requests.get(download_url, stream=True, timeout=60)
            response.raise_for_status()
            with output_path.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=8192):
                    handle.write(chunk)

    def download_release(self, tag: Optional[str] = None, output_dir: str = ".") -> bool:
        releases = self.list_releases()
        if not releases:
            print("❌ No releases with downloadable artifacts found")
            return False

        if tag:
            release = next((row for row in releases if row["tag"] == tag), None)
            if release is None:
                print(f"❌ Release {tag} not found")
                return False
        else:
            release = releases[0]
            print(f"📥 Downloading latest release: {release['tag']}")

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        try:
            downloaded_assets: list[str] = []
            for asset in release["assets"]:
                asset_name = asset["asset_name"]
                size_mb = asset["asset_size"] / (1024 * 1024)
                print(f"📦 Downloading {asset_name} ({size_mb:.1f} MB)...")

                if asset["asset_kind"] == "legacy_index":
                    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
                        tmp_path = Path(tmp.name)
                    try:
                        self._download_asset(
                            release["tag"],
                            asset_name,
                            asset["download_url"],
                            tmp_path,
                        )
                        print(f"📂 Extracting {asset_name} to {output_path}...")
                        with tarfile.open(tmp_path, "r:gz") as archive:
                            archive.extractall(output_path)
                    finally:
                        tmp_path.unlink(missing_ok=True)
                    downloaded_assets.append(f"{asset_name} -> extracted")
                    continue

                destination = output_path / asset_name
                self._download_asset(
                    release["tag"],
                    asset_name,
                    asset["download_url"],
                    destination,
                )
                downloaded_assets.append(asset_name)

            print(f"✅ Successfully downloaded artifacts from {release['tag']}")
            print(f"📍 Location: {output_path.absolute()}")
            for name in downloaded_assets:
                print(f"   - {name}")
            return True
        except Exception as exc:
            print(f"❌ Error downloading release: {exc}")
            return False

    def show_releases(self) -> None:
        releases = self.list_releases()
        if not releases:
            print("❌ No releases with downloadable artifacts found")
            return

        print("\n📦 Available Code Index Release Artifacts:\n")
        print(f"{'Tag':<15} {'Name':<30} {'Published':<20} Assets")
        print("-" * 100)

        for release in releases:
            asset_kinds = ", ".join(asset["asset_kind"] for asset in release["assets"])
            print(
                f"{release['tag']:<15} "
                f"{release['name'][:29]:<30} "
                f"{release['published'].split('T')[0]:<20} "
                f"{asset_kinds}"
            )

        print(f"\n💡 To download a specific release: {sys.argv[0]} --tag <tag>")
        print(f"💡 To download latest: {sys.argv[0]} --latest")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download release artifacts from GitHub releases"
    )
    parser.add_argument("--list", action="store_true", help="List available releases")
    parser.add_argument(
        "--latest",
        action="store_true",
        help="Download the newest available release artifact",
    )
    parser.add_argument("--tag", help="Download specific release tag")
    parser.add_argument(
        "--output",
        "-o",
        default=".",
        help="Output directory (default: current directory)",
    )
    parser.add_argument(
        "--repo",
        help="GitHub repository (owner/name). Auto-detected if not specified.",
    )

    args = parser.parse_args()
    downloader = GitHubReleaseDownloader(repo=args.repo)

    if args.list:
        downloader.show_releases()
        return 0
    if args.latest or args.tag:
        tag = args.tag if args.tag else None
        return 0 if downloader.download_release(tag=tag, output_dir=args.output) else 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
