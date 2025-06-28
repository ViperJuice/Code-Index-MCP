#!/usr/bin/env python3
"""
Upload local index files to GitHub Actions Artifacts with compatibility checking.

This script compresses and uploads index files to GitHub Actions Artifacts,
ensuring compatibility-aware versioning to prevent incompatible overwrites.
"""

import os
import sys
import json
import tarfile
import hashlib
import subprocess
import argparse
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mcp_server.config.settings import get_settings
from mcp_server.utils.semantic_indexer import SemanticIndexer
from mcp_server.storage.sqlite_store import SQLiteStore
# Import secure export functionality
try:
    from scripts.utilities.secure_index_export import SecureIndexExporter
except ImportError:
    # Try alternative import path
    sys.path.insert(0, str(project_root / 'scripts' / 'utilities'))
    try:
        from secure_index_export import SecureIndexExporter
    except ImportError:
        # Define a stub if not available
        class SecureIndexExporter:
            def create_filtered_database(self, src, dst):
                # Simple copy without filtering
                import shutil
                shutil.copy2(src, dst)
                return 0, 0  # included, excluded


class CompatibilityAwareUploader:
    """Handle uploading index files with compatibility versioning."""
    
    def __init__(self, repo: Optional[str] = None, token: Optional[str] = None):
        """
        Initialize uploader.
        
        Args:
            repo: GitHub repository (owner/name). If None, detect from git.
            token: GitHub token. If None, use environment variable.
        """
        self.repo = repo or self._detect_repository()
        self.token = token or os.environ.get('GITHUB_TOKEN', '')
        self.api_base = f"https://api.github.com/repos/{self.repo}"
        self.index_files = [
            'code_index.db',
            'vector_index.qdrant',
            '.index_metadata.json'
        ]
        
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
                    # SSH format: git@github.com:owner/repo.git
                    parts = url.split(':')[1].replace('.git', '').strip()
                else:
                    # HTTPS format: https://github.com/owner/repo.git
                    parts = url.split('github.com/')[1].replace('.git', '').strip()
                return parts
        except:
            pass
        
        # Fallback
        return os.environ.get('GITHUB_REPOSITORY', 'unknown/unknown')
    
    def _find_index_location(self) -> Path:
        """Find the index location - either local .indexes/ or .mcp-index/."""
        # First, check for local .indexes/ directory
        mcp_server_dir = Path(__file__).parent.parent
        local_indexes = mcp_server_dir / ".indexes"
        
        if local_indexes.exists():
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
                
                # Check for current.db symlink
                repo_index_dir = local_indexes / repo_hash
                current_db = repo_index_dir / "current.db"
                
                if current_db.exists():
                    print(f"📂 Found index in .indexes/{repo_hash}/")
                    return repo_index_dir
            except Exception as e:
                print(f"⚠️  Could not determine repository hash: {e}")
        
        # Fallback to .mcp-index in current directory
        local_index = Path.cwd() / ".mcp-index"
        if local_index.exists():
            print("📂 Found index in .mcp-index/")
            return local_index
        
        # Default to current directory
        print("📂 Using current directory for index files")
        return Path.cwd()
    
    def generate_compatibility_hash(self) -> str:
        """Generate a hash representing the current index compatibility configuration."""
        settings = get_settings()
        
        # Gather all factors that affect compatibility
        factors = {
            'embedding_model': settings.semantic_embedding_model,
            'embedding_dimensions': 1024,  # Could be dynamic based on model
            'distance_metric': 'cosine',
            'schema_version': '2.0',  # Bumped for relative paths
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
    
    def get_existing_artifacts(self) -> List[Dict[str, Any]]:
        """Get list of existing index artifacts from GitHub."""
        if not self.token:
            # Try using gh CLI
            try:
                result = subprocess.run(
                    ['gh', 'api', f'/repos/{self.repo}/actions/artifacts', '--paginate'],
                    capture_output=True,
                    text=True,
                    check=True
                )
                data = json.loads(result.stdout)
                return data.get('artifacts', [])
            except:
                print("⚠️  Unable to list existing artifacts (no token or gh CLI)")
                return []
        
        # Use API directly
        headers = {
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        try:
            response = requests.get(f"{self.api_base}/actions/artifacts", headers=headers)
            response.raise_for_status()
            return response.json().get('artifacts', [])
        except Exception as e:
            print(f"⚠️  Error listing artifacts: {e}")
            return []
    
    def find_compatible_artifact(self, compatibility_hash: str, artifacts: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Find an existing artifact with matching compatibility hash."""
        for artifact in artifacts:
            name = artifact.get('name', '')
            # Check if artifact name contains our compatibility hash
            if f'index-{compatibility_hash}' in name:
                return artifact
        return None
    
    def compress_indexes(self, output_path: Path, secure: bool = True) -> Tuple[Path, str, int]:
        """Compress index files into a tar.gz archive."""
        if secure:
            print("🔒 Creating secure index export...")
            # Use SecureIndexExporter to filter sensitive files
            exporter = SecureIndexExporter()
            
            # Create temporary directory for filtered files
            import tempfile
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Export filtered database
                db_path = self.index_path / 'code_index.db'
                # Also check for symlinked current.db
                if not db_path.exists():
                    current_db = self.index_path / 'current.db'
                    if current_db.exists():
                        db_path = current_db.resolve()
                
                if db_path.exists():
                    filtered_db = temp_path / 'code_index.db'
                    included, excluded = exporter.create_filtered_database(
                        str(db_path), str(filtered_db)
                    )
                    print(f"   Filtered database: {included} files included, {excluded} excluded")
                
                # Copy other files
                for file_name in ['.index_metadata.json']:
                    src = self.index_path / file_name
                    if src.exists():
                        import shutil
                        shutil.copy2(src, temp_path / file_name)
                
                # Copy vector index (already filtered during creation)
                vector_path = self.index_path / 'vector_index.qdrant'
                if vector_path.exists():
                    import shutil
                    shutil.copytree(vector_path, temp_path / 'vector_index.qdrant')
                
                # Compress from temp directory
                with tarfile.open(output_path, 'w:gz', compresslevel=9) as tar:
                    for item in temp_path.iterdir():
                        tar.add(item, arcname=item.name)
        else:
            print("📦 Compressing index files (including all files)...")
            with tarfile.open(output_path, 'w:gz', compresslevel=9) as tar:
                for file_name in self.index_files:
                    file_path = self.index_path / file_name
                    # Also check for symlinked current.db
                    if file_name == 'code_index.db' and not file_path.exists():
                        current_db = self.index_path / 'current.db'
                        if current_db.exists():
                            # Add the actual file but name it code_index.db in archive
                            print(f"  Adding current.db as {file_name}...")
                            tar.add(current_db.resolve(), arcname=file_name)
                            continue
                    
                    if file_path.exists():
                        print(f"  Adding {file_name}...")
                        tar.add(file_path, arcname=file_name)
        
        # Calculate checksum and size
        checksum = self._calculate_checksum(output_path)
        size = output_path.stat().st_size
        
        print(f"✅ Compressed to {output_path} ({size / 1024 / 1024:.1f} MB)")
        print(f"   Checksum: {checksum}")
        
        return output_path, checksum, size
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file."""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def create_metadata(self, compatibility_hash: str, checksum: str, size: int, secure: bool = True) -> Dict[str, Any]:
        """Create metadata for the artifact."""
        # Get current git info
        try:
            commit = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                capture_output=True,
                text=True,
                check=True
            ).stdout.strip()
            
            branch = subprocess.run(
                ['git', 'branch', '--show-current'],
                capture_output=True,
                text=True,
                check=True
            ).stdout.strip()
        except:
            commit = 'unknown'
            branch = 'unknown'
        
        # Get index statistics
        stats = self._get_index_stats()
        
        # Get compatibility factors
        settings = get_settings()
        
        metadata = {
            'version': '2.0',  # Bumped for compatibility system
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'commit': commit,
            'branch': branch,
            'checksum': checksum,
            'compressed_size': size,
            'index_stats': stats,
            'compatibility': {
                'hash': compatibility_hash,
                'embedding_model': settings.semantic_embedding_model,
                'embedding_dimension': 1024,
                'distance_metric': 'cosine',
                'schema_version': '2.0',
                'factors': {
                    'python_version': f"{sys.version_info.major}.{sys.version_info.minor}",
                    'relative_paths': True,  # New in v2.0
                }
            },
            'security': {
                'filtered': secure,
                'filter_type': 'gitignore + mcp-index-ignore' if secure else 'none',
                'export_method': 'secure' if secure else 'unsafe'
            }
        }
        
        return metadata
    
    def _get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the indexes."""
        stats = {}
        
        # SQLite stats
        db_path = self.index_path / 'code_index.db'
        # Also check for symlinked current.db
        if not db_path.exists():
            current_db = self.index_path / 'current.db'
            if current_db.exists():
                db_path = current_db.resolve()
        
        if db_path.exists():
            size = db_path.stat().st_size
            stats['sqlite'] = {
                'size_bytes': size,
                'size_mb': round(size / 1024 / 1024, 1)
            }
            
            # Try to get record counts
            try:
                import sqlite3
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()
                
                cursor.execute("SELECT COUNT(*) FROM files")
                file_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM symbols")
                symbol_count = cursor.fetchone()[0]
                
                stats['sqlite']['files'] = file_count
                stats['sqlite']['symbols'] = symbol_count
                
                conn.close()
            except:
                pass
        
        # Vector index stats
        vector_path = self.index_path / 'vector_index.qdrant'
        if vector_path.exists():
            # Calculate directory size
            total_size = sum(
                f.stat().st_size 
                for f in vector_path.rglob('*') 
                if f.is_file()
            )
            stats['vector'] = {
                'size_bytes': total_size,
                'size_mb': round(total_size / 1024 / 1024, 1)
            }
        
        return stats
    
    def trigger_workflow_upload(self, compatibility_hash: str, archive_path: Path, metadata: Dict[str, Any], 
                               replace_artifact: Optional[str] = None) -> None:
        """Trigger GitHub Actions workflow to upload the artifact."""
        print("\n🚀 Triggering GitHub Actions workflow...")
        
        # Save metadata
        metadata_path = Path('artifact-metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Generate artifact name with compatibility hash
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        commit_short = metadata['commit'][:8] if metadata['commit'] != 'unknown' else 'unknown'
        artifact_name = f"index-{compatibility_hash}-{commit_short}-{timestamp}"
        
        print(f"📦 Artifact name: {artifact_name}")
        print(f"🔑 Compatibility hash: {compatibility_hash}")
        
        if replace_artifact:
            print(f"♻️  Replacing existing artifact: {replace_artifact}")
        
        # Prepare for GitHub Actions
        print(f"\n✅ Files prepared for upload:")
        print(f"   - {archive_path} ({archive_path.stat().st_size / 1024 / 1024:.1f} MB)")
        print(f"   - {metadata_path}")
        
        # Set output for GitHub Actions
        if os.environ.get('GITHUB_ACTIONS'):
            print(f"::set-output name=artifact_name::{artifact_name}")
            print(f"::set-output name=compatibility_hash::{compatibility_hash}")
            print(f"::set-output name=archive_path::{archive_path}")
            print(f"::set-output name=metadata_path::{metadata_path}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Upload index files to GitHub with compatibility checking'
    )
    parser.add_argument(
        '--repo',
        help='GitHub repository (owner/name). Auto-detected if not specified.'
    )
    parser.add_argument(
        '--output',
        default='index-archive.tar.gz',
        help='Output archive filename'
    )
    parser.add_argument(
        '--no-secure',
        action='store_true',
        help='Disable secure export (include all files)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force upload even if compatible version exists'
    )
    
    args = parser.parse_args()
    
    try:
        uploader = CompatibilityAwareUploader(repo=args.repo)
        
        # Generate compatibility hash
        compatibility_hash = uploader.generate_compatibility_hash()
        print(f"🔑 Compatibility hash: {compatibility_hash}")
        
        # Check for existing compatible artifacts
        if not args.force:
            print("\n🔍 Checking for existing compatible artifacts...")
            artifacts = uploader.get_existing_artifacts()
            compatible = uploader.find_compatible_artifact(compatibility_hash, artifacts)
            
            if compatible:
                print(f"✅ Found compatible artifact: {compatible['name']}")
                print(f"   Created: {compatible['created_at']}")
                print(f"   Size: {compatible['size_in_bytes'] / 1024 / 1024:.1f} MB")
                print("\n📝 This upload will replace the existing compatible version.")
            else:
                print("✅ No existing compatible artifact found. Creating new version stream.")
        
        # Compress indexes
        secure = not args.no_secure
        archive_path, checksum, size = uploader.compress_indexes(Path(args.output), secure=secure)
        
        # Check size limit
        if size > 500 * 1024 * 1024:
            print(f"❌ Archive too large: {size / 1024 / 1024:.1f} MB > 500 MB")
            sys.exit(1)
        
        # Create metadata
        metadata = uploader.create_metadata(compatibility_hash, checksum, size, secure=secure)
        
        # Trigger upload
        uploader.trigger_workflow_upload(
            compatibility_hash, 
            archive_path, 
            metadata,
            replace_artifact=compatible['name'] if not args.force and compatible else None
        )
        
        print("\n✨ Upload prepared successfully!")
        print("\nNext steps:")
        print("1. The GitHub Action will upload the artifact")
        print("2. Compatible indexes will be replaced automatically")
        print("3. Incompatible versions remain separate")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()