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
import requests

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
        self.token = token or os.environ.get('GITHUB_TOKEN', '')
        self.api_base = f"https://api.github.com/repos/{self.repo}"
        
        if not self.token:
            print("⚠️  No GitHub token found. Using gh CLI for authentication.")
            
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
            
            # Extract owner/repo from URL
            if 'github.com' in url:
                if url.startswith('git@'):
                    # SSH format: git@github.com:owner/repo.git
                    parts = url.split(':')[1]
                else:
                    # HTTPS format: https://github.com/owner/repo.git
                    parts = url.split('github.com/')[1]
                
                return parts.rstrip('.git')
            
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
            cmd = ['gh', 'api', f'/repos/{self.repo}/actions/artifacts', '--jq', '.artifacts[]']
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            artifacts = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    artifact = json.loads(line)
                    # Filter for index artifacts
                    if artifact['name'].startswith('index-'):
                        if not name_filter or name_filter in artifact['name']:
                            artifacts.append(artifact)
            
            # Sort by created date (newest first)
            artifacts.sort(key=lambda x: x['created_at'], reverse=True)
            
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
                'gh', 'api',
                f'/repos/{self.repo}/actions/artifacts/{artifact_id}/zip',
                '--output', str(temp_dir / 'artifact.zip')
            ]
            subprocess.run(cmd, check=True)
            
            # Extract zip file
            import zipfile
            with zipfile.ZipFile(temp_dir / 'artifact.zip', 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # Find the tar.gz archive
            archive_path = None
            metadata_path = None
            
            for file in temp_dir.iterdir():
                if file.name.endswith('.tar.gz'):
                    archive_path = file
                elif file.name == 'artifact-metadata.json':
                    metadata_path = file
            
            if not archive_path:
                raise ValueError("No archive found in artifact")
            
            # Verify and extract
            if metadata_path:
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                
                # Verify checksum
                expected_checksum = metadata.get('checksum')
                if expected_checksum:
                    actual_checksum = self._calculate_checksum(archive_path)
                    if actual_checksum != expected_checksum:
                        raise ValueError(f"Checksum mismatch! Expected: {expected_checksum}, Got: {actual_checksum}")
                    print("✅ Checksum verified")
            
            # Extract archive
            print("📦 Extracting index files...")
            with tarfile.open(archive_path, 'r:gz') as tar:
                tar.extractall(output_dir)
            
            # Copy metadata if exists
            if metadata_path:
                shutil.copy2(metadata_path, output_dir / 'artifact-metadata.json')
            
            return output_dir
            
        finally:
            # Clean up temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file."""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def check_compatibility(self, metadata: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Check if artifact is compatible with current configuration.
        
        Returns:
            Tuple of (is_compatible, list_of_issues)
        """
        issues = []
        
        # Check embedding model
        artifact_model = metadata.get('compatibility', {}).get('embedding_model')
        if artifact_model:
            try:
                from mcp_server.config.settings import get_settings
                current_model = get_settings().semantic_embedding_model
                
                if artifact_model != current_model:
                    issues.append(f"Embedding model mismatch: artifact={artifact_model}, current={current_model}")
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
        promoted = [a for a in artifacts if '-promoted' in a['name']]
        if promoted:
            return promoted[0]
        
        # Otherwise, return the latest
        if artifacts:
            return artifacts[0]
        
        return None
    
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
            backup_dir = Path(f'index_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
            backup_dir.mkdir(exist_ok=True)
            
            for file_name in ['code_index.db', 'vector_index.qdrant', '.index_metadata.json']:
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
            if item.name in ['code_index.db', 'vector_index.qdrant', '.index_metadata.json', 'artifact-metadata.json']:
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
        name = artifact['name']
        if len(name) > 40:
            name = name[:37] + '...'
        
        size_mb = artifact['size_in_bytes'] / 1024 / 1024
        created = datetime.fromisoformat(artifact['created_at'].replace('Z', '+00:00'))
        created_str = created.strftime('%Y-%m-%d %H:%M')
        promoted = '✓' if '-promoted' in artifact['name'] else ''
        
        print(f"{name:<40} {size_mb:>8.1f}MB {created_str:<20} {promoted}")
    
    if len(artifacts) > 10:
        print(f"\n... and {len(artifacts) - 10} more artifacts")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Download index files from GitHub Actions Artifacts'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List available artifacts')
    list_parser.add_argument('--filter', help='Filter artifact names')
    
    # Download command
    download_parser = subparsers.add_parser('download', help='Download and install indexes')
    download_parser.add_argument('--artifact-id', type=int, help='Specific artifact ID to download')
    download_parser.add_argument('--latest', action='store_true', help='Download latest compatible artifact')
    download_parser.add_argument('--no-backup', action='store_true', help='Skip backup of existing indexes')
    download_parser.add_argument('--output-dir', default='.', help='Output directory')
    
    # Info command
    info_parser = subparsers.add_parser('info', help='Show artifact information')
    info_parser.add_argument('artifact_id', type=int, help='Artifact ID')
    
    parser.add_argument('--repo', help='GitHub repository (owner/name)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        downloader = IndexArtifactDownloader(repo=args.repo)
        
        if args.command == 'list':
            artifacts = downloader.list_artifacts(name_filter=args.filter)
            format_artifact_table(artifacts)
            
            if artifacts:
                print(f"\nTotal: {len(artifacts)} artifacts")
            
        elif args.command == 'download':
            if args.artifact_id:
                # Download specific artifact
                output_dir = Path(args.output_dir) / 'artifact_download'
                output_dir.mkdir(exist_ok=True)
                
                extracted_dir = downloader.download_artifact(args.artifact_id, output_dir)
                
                # Check compatibility
                metadata_file = extracted_dir / 'artifact-metadata.json'
                if metadata_file.exists():
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    
                    compatible, issues = downloader.check_compatibility(metadata)
                    if not compatible:
                        print("\n⚠️  Compatibility issues detected:")
                        for issue in issues:
                            print(f"   - {issue}")
                        
                        response = input("\nContinue anyway? [y/N]: ")
                        if response.lower() != 'y':
                            print("Aborted.")
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
                output_dir = Path(args.output_dir) / 'artifact_download'
                output_dir.mkdir(exist_ok=True)
                
                extracted_dir = downloader.download_artifact(best['id'], output_dir)
                downloader.install_indexes(extracted_dir, backup=not args.no_backup)
                
                # Clean up
                shutil.rmtree(output_dir, ignore_errors=True)
                
            else:
                print("❌ Specify --artifact-id or --latest")
                sys.exit(1)
        
        elif args.command == 'info':
            # Show artifact info
            artifacts = downloader.list_artifacts()
            artifact = next((a for a in artifacts if a['id'] == args.artifact_id), None)
            
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
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()