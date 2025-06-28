#!/usr/bin/env python3
"""
Download index files from GitHub releases.

This script downloads pre-built index files from GitHub releases,
providing a quick way to get started without building the index locally.
"""

import os
import sys
import json
import subprocess
import argparse
import tempfile
import tarfile
import hashlib
import requests
from pathlib import Path
from typing import Optional, List, Dict, Any


class GitHubReleaseDownloader:
    """Download index files from GitHub releases."""
    
    def __init__(self, repo: Optional[str] = None):
        """Initialize downloader."""
        self.repo = repo or self._detect_repository()
        self.api_base = f"https://api.github.com/repos/{self.repo}"
        
    def _detect_repository(self) -> str:
        """Detect repository from git remote."""
        try:
            result = subprocess.run(
                ['git', 'remote', 'get-url', 'origin'],
                capture_output=True,
                text=True,
                check=True
            )
            url = result.stdout.strip()
            
            if 'github.com' in url:
                if url.startswith('git@'):
                    parts = url.split(':')[1].replace('.git', '').strip()
                    return parts
                else:
                    parts = url.split('github.com/')[1].replace('.git', '').strip()
                    return parts
        except:
            pass
        
        # Default fallback
        return 'ViperJuice/Code-Index-MCP'
    
    def list_releases(self) -> List[Dict[str, Any]]:
        """List available releases with index artifacts."""
        print(f"📋 Fetching releases from {self.repo}...")
        
        try:
            # Try using gh CLI first
            result = subprocess.run(
                ['gh', 'api', f'/repos/{self.repo}/releases', '--paginate'],
                capture_output=True,
                text=True,
                check=True
            )
            releases = json.loads(result.stdout)
        except:
            # Fallback to direct API
            try:
                response = requests.get(f"{self.api_base}/releases")
                response.raise_for_status()
                releases = response.json()
            except Exception as e:
                print(f"❌ Error fetching releases: {e}")
                return []
        
        # Filter releases with index artifacts
        index_releases = []
        for release in releases:
            for asset in release.get('assets', []):
                if asset['name'].startswith('code-index-') and asset['name'].endswith('.tar.gz'):
                    index_releases.append({
                        'tag': release['tag_name'],
                        'name': release['name'],
                        'published': release['published_at'],
                        'asset_name': asset['name'],
                        'asset_url': asset['browser_download_url'],
                        'asset_size': asset['size'],
                        'download_url': asset['url']
                    })
                    break
        
        return index_releases
    
    def download_release(self, tag: Optional[str] = None, output_dir: str = '.') -> bool:
        """
        Download and extract a release.
        
        Args:
            tag: Release tag to download. If None, downloads latest.
            output_dir: Directory to extract files to.
            
        Returns:
            True if successful
        """
        releases = self.list_releases()
        
        if not releases:
            print("❌ No releases with index artifacts found")
            return False
        
        # Find the requested release
        if tag:
            release = next((r for r in releases if r['tag'] == tag), None)
            if not release:
                print(f"❌ Release {tag} not found")
                return False
        else:
            release = releases[0]  # Latest
            print(f"📥 Downloading latest release: {release['tag']}")
        
        # Download the asset
        asset_name = release['asset_name']
        asset_url = release['asset_url']
        size_mb = release['asset_size'] / (1024 * 1024)
        
        print(f"📦 Downloading {asset_name} ({size_mb:.1f} MB)...")
        
        try:
            # Create temp file
            with tempfile.NamedTemporaryFile(suffix='.tar.gz', delete=False) as tmp:
                tmp_path = tmp.name
            
            # Download using gh CLI if available
            try:
                subprocess.run(
                    ['gh', 'release', 'download', release['tag'], 
                     '--repo', self.repo, '--pattern', asset_name,
                     '--output', tmp_path],
                    check=True
                )
            except:
                # Fallback to direct download
                response = requests.get(release['download_url'], stream=True)
                response.raise_for_status()
                
                with open(tmp_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
            
            print("✅ Download complete")
            
            # Extract the archive
            print(f"📂 Extracting to {output_dir}...")
            
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            with tarfile.open(tmp_path, 'r:gz') as tar:
                # List contents
                members = tar.getmembers()
                print(f"📋 Archive contains {len(members)} files")
                
                # Extract
                tar.extractall(output_path)
            
            # Clean up temp file
            Path(tmp_path).unlink()
            
            print(f"✅ Successfully installed index from {release['tag']}")
            print(f"📍 Location: {output_path.absolute()}")
            
            # Show what was extracted
            for pattern in ['*.db', '*.json', 'vector_index.qdrant']:
                files = list(output_path.rglob(pattern))
                if files:
                    print(f"   - {pattern}: {len(files)} file(s)")
            
            return True
            
        except Exception as e:
            print(f"❌ Error downloading release: {e}")
            return False
    
    def show_releases(self) -> None:
        """Display available releases."""
        releases = self.list_releases()
        
        if not releases:
            print("❌ No releases with index artifacts found")
            return
        
        print(f"\n📦 Available Code Index Releases:\n")
        print(f"{'Tag':<15} {'Name':<30} {'Published':<20} {'Size':<10}")
        print("-" * 75)
        
        for release in releases:
            tag = release['tag']
            name = release['name'][:29]
            published = release['published'].split('T')[0]
            size = f"{release['asset_size'] / (1024*1024):.1f} MB"
            
            print(f"{tag:<15} {name:<30} {published:<20} {size:<10}")
        
        print(f"\n💡 To download a specific release: {sys.argv[0]} --tag <tag>")
        print(f"💡 To download latest: {sys.argv[0]} --latest")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Download pre-built index from GitHub releases"
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='List available releases'
    )
    parser.add_argument(
        '--latest',
        action='store_true',
        help='Download latest release'
    )
    parser.add_argument(
        '--tag',
        help='Download specific release tag'
    )
    parser.add_argument(
        '--output', '-o',
        default='.',
        help='Output directory (default: current directory)'
    )
    parser.add_argument(
        '--repo',
        help='GitHub repository (owner/name). Auto-detected if not specified.'
    )
    
    args = parser.parse_args()
    
    # Initialize downloader
    downloader = GitHubReleaseDownloader(repo=args.repo)
    
    # Handle commands
    if args.list:
        downloader.show_releases()
    elif args.latest or args.tag:
        tag = args.tag if args.tag else None
        success = downloader.download_release(tag=tag, output_dir=args.output)
        return 0 if success else 1
    else:
        parser.print_help()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())