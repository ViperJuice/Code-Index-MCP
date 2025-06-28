#!/usr/bin/env python3
"""
Download index files from GitHub Actions Artifacts with compatibility checking.

This script downloads and installs index files from GitHub Actions Artifacts,
ensuring only compatible versions are downloaded.
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
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mcp_server.config.settings import get_settings
from mcp_server.utils.semantic_indexer import SemanticIndexer


class CompatibilityAwareDownloader:
    """Handle downloading index files with compatibility checking."""
    
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
        
        # Determine index location
        self.index_path = self._find_index_location()
        
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
            
            # Parse GitHub URL
            if 'github.com' in url:
                if url.startswith('git@'):
                    # SSH format
                    parts = url.split(':')[1].replace('.git', '').strip()
                else:
                    # HTTPS format
                    parts = url.split('github.com/')[1].replace('.git', '').strip()
                return parts
        except:
            pass
        
        return os.environ.get('GITHUB_REPOSITORY', 'unknown/unknown')
    
    def _find_index_location(self) -> Path:
        """Find the index location - create .indexes/ directory if needed."""
        # Check for local .indexes/ directory
        mcp_server_dir = Path(__file__).parent.parent
        local_indexes = mcp_server_dir / ".indexes"
        
        # Get repository hash
        try:
            result = subprocess.run(
                ['git', 'remote', 'get-url', 'origin'],
                capture_output=True,
                text=True,
                check=True
            )
            remote_url = result.stdout.strip()
            repo_hash = hashlib.sha256(remote_url.encode()).hexdigest()[:12]
            
            # Create directory structure if needed
            repo_index_dir = local_indexes / repo_hash
            repo_index_dir.mkdir(parents=True, exist_ok=True)
            
            print(f"📂 Using index location: .indexes/{repo_hash}/")
            return repo_index_dir
            
        except Exception as e:
            print(f"⚠️  Could not determine repository hash: {e}")
            # Fallback to .mcp-index in current directory
            local_index = Path.cwd() / ".mcp-index"
            local_index.mkdir(exist_ok=True)
            print("📂 Using fallback location: .mcp-index/")
            return local_index
    
    def generate_compatibility_hash(self) -> str:
        """Generate a hash representing the current index compatibility configuration."""
        settings = get_settings()
        
        # Must match the logic in upload script
        factors = {
            'embedding_model': settings.semantic_embedding_model,
            'embedding_dimensions': 1024,
            'distance_metric': 'cosine',
            'schema_version': '2.0',
            'python_version': f"{sys.version_info.major}.{sys.version_info.minor}",
        }
        
        # Add language plugin versions if available
        try:
            from mcp_server.plugins.language_registry import get_all_languages
            factors['language_plugins'] = sorted(get_all_languages())
        except:
            factors['language_plugins'] = []
        
        # Create deterministic hash
        factors_json = json.dumps(factors, sort_keys=True)
        return hashlib.sha256(factors_json.encode()).hexdigest()[:8]
    
    def list_artifacts(self) -> List[Dict[str, Any]]:
        """List all index artifacts from GitHub."""
        print("📋 Listing available artifacts...")
        
        if not self.token:
            # Try using gh CLI
            try:
                result = subprocess.run(
                    ['gh', 'api', f'/repos/{self.repo}/actions/artifacts', 
                     '--paginate', '-q', '.artifacts[] | select(.name | startswith("index-"))'],
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                # Parse JSON lines
                artifacts = []
                for line in result.stdout.strip().split('\n'):
                    if line:
                        artifacts.append(json.loads(line))
                return artifacts
            except Exception as e:
                print(f"⚠️  Error using gh CLI: {e}")
                return []
        
        # Use API directly
        headers = {
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        try:
            all_artifacts = []
            page = 1
            
            while True:
                response = requests.get(
                    f"{self.api_base}/actions/artifacts",
                    headers=headers,
                    params={'per_page': 100, 'page': page}
                )
                response.raise_for_status()
                
                data = response.json()
                artifacts = data.get('artifacts', [])
                
                # Filter index artifacts
                index_artifacts = [a for a in artifacts if a['name'].startswith('index-')]
                all_artifacts.extend(index_artifacts)
                
                # Check if more pages
                if len(artifacts) < 100:
                    break
                page += 1
            
            return all_artifacts
            
        except Exception as e:
            print(f"❌ Error listing artifacts: {e}")
            return []
    
    def categorize_artifacts(self, artifacts: List[Dict[str, Any]], current_hash: str) -> Dict[str, List[Dict[str, Any]]]:
        """Categorize artifacts by compatibility."""
        categories = {
            'compatible': [],
            'incompatible': [],
            'unknown': []
        }
        
        for artifact in artifacts:
            name = artifact['name']
            
            # Extract compatibility hash from name (index-{hash}-{commit}-{timestamp})
            parts = name.split('-')
            if len(parts) >= 4 and parts[0] == 'index':
                artifact_hash = parts[1]
                
                if artifact_hash == current_hash:
                    categories['compatible'].append(artifact)
                else:
                    categories['incompatible'].append(artifact)
            else:
                categories['unknown'].append(artifact)
        
        return categories
    
    def download_artifact(self, artifact: Dict[str, Any], output_dir: Path) -> bool:
        """Download a specific artifact."""
        artifact_id = artifact['id']
        artifact_name = artifact['name']
        
        print(f"\n📥 Downloading {artifact_name}...")
        
        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)
        archive_path = output_dir / 'index-archive.tar.gz'
        
        if not self.token:
            # Use gh CLI
            try:
                subprocess.run(
                    ['gh', 'api', f'/repos/{self.repo}/actions/artifacts/{artifact_id}/zip',
                     '--output', str(archive_path)],
                    check=True
                )
                return True
            except Exception as e:
                print(f"❌ Download failed: {e}")
                return False
        
        # Use API directly
        headers = {
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        try:
            # Get download URL
            response = requests.get(
                f"{self.api_base}/actions/artifacts/{artifact_id}/zip",
                headers=headers,
                allow_redirects=True,
                stream=True
            )
            response.raise_for_status()
            
            # Save to file
            with open(archive_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"✅ Downloaded to {archive_path}")
            return True
            
        except Exception as e:
            print(f"❌ Download failed: {e}")
            return False
    
    def extract_and_verify(self, archive_path: Path, extract_dir: Path) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Extract and verify the downloaded artifact."""
        print("\n📦 Extracting archive...")
        
        try:
            # Handle zip file (GitHub artifacts are zipped)
            if archive_path.suffix == '.zip' or not tarfile.is_tarfile(archive_path):
                import zipfile
                with zipfile.ZipFile(archive_path, 'r') as zf:
                    zf.extractall(extract_dir)
            else:
                # Handle tar.gz
                with tarfile.open(archive_path, 'r:*') as tar:
                    tar.extractall(extract_dir)
            
            # Load metadata
            metadata_path = extract_dir / 'artifact-metadata.json'
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                print("✅ Metadata loaded successfully")
                return True, metadata
            else:
                print("⚠️  No metadata found in artifact")
                return True, None
                
        except Exception as e:
            print(f"❌ Extraction failed: {e}")
            return False, None
    
    def install_indexes(self, source_dir: Path, metadata: Optional[Dict[str, Any]] = None, 
                       backup: bool = True) -> None:
        """Install downloaded indexes to the correct index location."""
        print("\n📝 Installing indexes...")
        
        # Backup existing indexes if requested
        existing_files = ['code_index.db', 'vector_index.qdrant', '.index_metadata.json', 'current.db']
        if backup and any((self.index_path / f).exists() for f in existing_files):
            backup_dir = self.index_path / f'backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
            backup_dir.mkdir(exist_ok=True)
            
            for file_name in existing_files:
                src = self.index_path / file_name
                if src.exists():
                    print(f"  Backing up {file_name}...")
                    if src.is_dir():
                        shutil.copytree(src, backup_dir / file_name)
                    else:
                        shutil.copy2(src, backup_dir / file_name)
            
            print(f"  ✅ Backup created in {backup_dir}")
        
        # Install new indexes
        installed_files = []
        
        # Extract the inner archive if it exists
        inner_archive = source_dir / 'index-archive.tar.gz'
        if inner_archive.exists():
            print("  Extracting inner archive...")
            with tarfile.open(inner_archive, 'r:gz') as tar:
                tar.extractall(source_dir)
        
        for item in source_dir.iterdir():
            if item.name in ['code_index.db', 'vector_index.qdrant', '.index_metadata.json']:
                dest = self.index_path / item.name
                
                # Remove existing
                if dest.exists():
                    if dest.is_dir():
                        shutil.rmtree(dest)
                    else:
                        dest.unlink()
                
                # Copy new
                print(f"  Installing {item.name} to {self.index_path}/...")
                if item.is_dir():
                    shutil.copytree(item, dest)
                else:
                    shutil.copy2(item, dest)
                installed_files.append(item.name)
        
        # Create/update symlink for current.db
        if 'code_index.db' in installed_files:
            current_link = self.index_path / 'current.db'
            if current_link.exists():
                current_link.unlink()
            
            # Get git info for naming
            try:
                branch = subprocess.run(
                    ['git', 'branch', '--show-current'],
                    capture_output=True,
                    text=True,
                    check=True
                ).stdout.strip() or 'main'
                
                commit = subprocess.run(
                    ['git', 'rev-parse', 'HEAD'],
                    capture_output=True,
                    text=True,
                    check=True
                ).stdout.strip()[:7]
                
                # Rename the db file to include branch and commit
                new_db_name = f"{branch}_{commit}.db"
                old_db = self.index_path / 'code_index.db'
                new_db = self.index_path / new_db_name
                old_db.rename(new_db)
                
                # Create symlink
                current_link.symlink_to(new_db_name)
                print(f"  Created symlink: current.db -> {new_db_name}")
            except:
                # Fallback to simple symlink
                current_link.symlink_to('code_index.db')
                print("  Created symlink: current.db -> code_index.db")
        
        # Update metadata if provided
        if metadata:
            compatibility_info = metadata.get('compatibility', {})
            print(f"\n📊 Installed index info:")
            print(f"   Compatibility hash: {compatibility_info.get('hash', 'unknown')}")
            print(f"   Embedding model: {compatibility_info.get('embedding_model', 'unknown')}")
            print(f"   Schema version: {compatibility_info.get('schema_version', 'unknown')}")
            print(f"   Created: {metadata.get('timestamp', 'unknown')}")
            print(f"   Git commit: {metadata.get('commit', 'unknown')[:8]}")
        
        print(f"\n✅ Installed {len(installed_files)} index files successfully!")


def format_artifact_table(artifacts: List[Dict[str, Any]], current_hash: str) -> None:
    """Pretty print artifacts as a table with compatibility info."""
    if not artifacts:
        print("No artifacts found.")
        return
    
    print("\n📦 Available Index Artifacts:")
    print("=" * 100)
    print(f"{'Name':<50} {'Compatible':<12} {'Size':>10} {'Created':<20}")
    print("-" * 100)
    
    for artifact in artifacts[:20]:  # Show latest 20
        name = artifact['name']
        
        # Check compatibility
        parts = name.split('-')
        if len(parts) >= 4 and parts[0] == 'index':
            artifact_hash = parts[1]
            compatible = "✅ Yes" if artifact_hash == current_hash else "❌ No"
        else:
            compatible = "❓ Unknown"
        
        # Format name
        if len(name) > 50:
            name = name[:47] + '...'
        
        size_mb = artifact['size_in_bytes'] / (1024 * 1024)
        created = artifact['created_at'][:19].replace('T', ' ')
        
        print(f"{name:<50} {compatible:<12} {size_mb:>9.1f}M {created:<20}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Download compatible index files from GitHub Artifacts'
    )
    parser.add_argument(
        '--repo',
        help='GitHub repository (owner/name). Auto-detected if not specified.'
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='List available artifacts with compatibility info'
    )
    parser.add_argument(
        '--latest',
        action='store_true',
        help='Download latest compatible artifact'
    )
    parser.add_argument(
        '--artifact',
        help='Download specific artifact by name'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Download even if incompatible'
    )
    parser.add_argument(
        '--no-backup',
        action='store_true',
        help='Skip backup of existing indexes'
    )
    
    args = parser.parse_args()
    
    try:
        downloader = CompatibilityAwareDownloader(repo=args.repo)
        
        # Generate current compatibility hash
        current_hash = downloader.generate_compatibility_hash()
        print(f"🔑 Current compatibility hash: {current_hash}")
        
        # List artifacts
        artifacts = downloader.list_artifacts()
        
        if args.list:
            # Just list and exit
            format_artifact_table(artifacts, current_hash)
            
            # Show summary
            categories = downloader.categorize_artifacts(artifacts, current_hash)
            print(f"\n📊 Summary:")
            print(f"   Compatible artifacts: {len(categories['compatible'])}")
            print(f"   Incompatible artifacts: {len(categories['incompatible'])}")
            print(f"   Unknown format: {len(categories['unknown'])}")
            return
        
        # Categorize artifacts
        categories = downloader.categorize_artifacts(artifacts, current_hash)
        
        # Determine which artifact to download
        artifact_to_download = None
        
        if args.artifact:
            # Find specific artifact
            for artifact in artifacts:
                if artifact['name'] == args.artifact:
                    artifact_to_download = artifact
                    break
            
            if not artifact_to_download:
                print(f"❌ Artifact not found: {args.artifact}")
                sys.exit(1)
            
            # Check compatibility
            if not args.force and artifact_to_download not in categories['compatible']:
                print(f"❌ Artifact is incompatible with current configuration")
                print(f"   Use --force to download anyway")
                sys.exit(1)
        
        elif args.latest or True:  # Default to latest
            # Get latest compatible artifact
            if categories['compatible']:
                artifact_to_download = categories['compatible'][0]  # Already sorted by date
                print(f"\n✅ Found latest compatible artifact: {artifact_to_download['name']}")
            else:
                print("\n❌ No compatible artifacts found!")
                
                if categories['incompatible']:
                    print(f"\n📋 Found {len(categories['incompatible'])} incompatible artifacts:")
                    for artifact in categories['incompatible'][:5]:
                        print(f"   - {artifact['name']}")
                    
                    if not args.force:
                        print("\nOptions:")
                        print("1. Update your configuration to match an existing artifact")
                        print("2. Use --force to download an incompatible version")
                        print("3. Build a new index locally")
                        sys.exit(1)
                    else:
                        # Force download latest incompatible
                        artifact_to_download = categories['incompatible'][0]
                        print(f"\n⚠️  Force downloading incompatible artifact: {artifact_to_download['name']}")
                else:
                    print("No artifacts available")
                    sys.exit(1)
        
        if artifact_to_download:
            # Create temporary directory for download
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Download artifact
                if downloader.download_artifact(artifact_to_download, temp_path):
                    # Extract and verify
                    archive_path = temp_path / 'index-archive.tar.gz'
                    if not archive_path.exists():
                        # Try zip format
                        archive_path = temp_path / 'index-archive.zip'
                        if not archive_path.exists():
                            # GitHub artifacts come as zip, find the downloaded file
                            for f in temp_path.iterdir():
                                if f.suffix in ['.zip', '.tar', '.gz']:
                                    archive_path = f
                                    break
                    
                    extract_dir = temp_path / 'extracted'
                    extract_dir.mkdir(exist_ok=True)
                    
                    success, metadata = downloader.extract_and_verify(archive_path, extract_dir)
                    
                    if success:
                        # Install indexes
                        downloader.install_indexes(
                            extract_dir,
                            metadata=metadata,
                            backup=not args.no_backup
                        )
                    else:
                        print("❌ Failed to extract artifact")
                        sys.exit(1)
                else:
                    print("❌ Failed to download artifact")
                    sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()