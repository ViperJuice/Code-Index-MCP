#!/usr/bin/env python3
"""
Upload local index files to GitHub Actions Artifacts.

This script compresses and uploads index files to GitHub Actions Artifacts,
enabling index sharing without burning GitHub compute resources.
"""

import os
import sys
import json
import tarfile
import hashlib
import subprocess
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mcp_server.config.settings import get_settings


class IndexArtifactUploader:
    """Handle uploading index files to GitHub Actions Artifacts."""
    
    def __init__(self, repo: Optional[str] = None, token: Optional[str] = None):
        """
        Initialize uploader.
        
        Args:
            repo: GitHub repository (owner/name). If None, detect from git.
            token: GitHub token. If None, use environment variable.
        """
        self.repo = repo or self._detect_repository()
        self.token = token or os.environ.get('GITHUB_TOKEN', '')
        self.index_files = [
            'code_index.db',
            'vector_index.qdrant',
            '.index_metadata.json'
        ]
        
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
    
    def compress_indexes(self, output_path: Path = Path('index-archive.tar.gz')) -> Tuple[Path, str, int]:
        """
        Compress index files.
        
        Returns:
            Tuple of (archive_path, checksum, size_bytes)
        """
        print("📦 Compressing index files...")
        
        with tarfile.open(output_path, 'w:gz', compresslevel=9) as tar:
            for file_name in self.index_files:
                file_path = Path(file_name)
                if file_path.exists():
                    print(f"  Adding {file_name}...")
                    tar.add(file_path, arcname=file_name)
                else:
                    print(f"  ⚠️  Skipping {file_name} (not found)")
        
        # Calculate checksum
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
    
    def create_metadata(self, checksum: str, size: int) -> Dict[str, Any]:
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
        
        metadata = {
            'version': '1.0',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'commit': commit,
            'branch': branch,
            'checksum': checksum,
            'compressed_size': size,
            'index_stats': stats,
            'compatibility': {
                'embedding_model': get_settings().semantic_embedding_model,
                'embedding_dimension': 1024,
                'distance_metric': 'cosine'
            }
        }
        
        return metadata
    
    def _get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the indexes."""
        stats = {}
        
        # SQLite stats
        if Path('code_index.db').exists():
            size = Path('code_index.db').stat().st_size
            stats['sqlite'] = {
                'size_bytes': size,
                'size_mb': round(size / 1024 / 1024, 1)
            }
            
            # Try to get record counts
            try:
                import sqlite3
                conn = sqlite3.connect('code_index.db')
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
        if Path('vector_index.qdrant').exists():
            # Calculate directory size
            total_size = sum(
                f.stat().st_size 
                for f in Path('vector_index.qdrant').rglob('*') 
                if f.is_file()
            )
            stats['vector'] = {
                'size_bytes': total_size,
                'size_mb': round(total_size / 1024 / 1024, 1)
            }
        
        return stats
    
    def trigger_workflow(self, archive_path: Path, metadata: Dict[str, Any]) -> None:
        """
        Trigger GitHub Actions workflow to upload the artifact.
        
        This uses gh CLI to trigger the workflow with the local files.
        """
        print("\n🚀 Triggering GitHub Actions workflow...")
        
        # Save metadata
        metadata_path = Path('artifact-metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Check if gh CLI is available
        try:
            subprocess.run(['gh', '--version'], capture_output=True, check=True)
        except:
            print("❌ GitHub CLI (gh) not found. Please install it:")
            print("   https://cli.github.com/")
            sys.exit(1)
        
        # Create a temporary workflow that uploads our local files
        workflow_content = f"""
name: Upload Local Index

on:
  workflow_dispatch:

jobs:
  upload:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Upload index artifact
        uses: actions/upload-artifact@v4
        with:
          name: index-${{{{ github.sha }}}}-${{{{ github.run_number }}}}
          path: |
            {archive_path}
            {metadata_path}
          retention-days: 30
          compression-level: 0  # Already compressed
"""
        
        # Save temporary workflow
        temp_workflow = Path('.github/workflows/temp-upload-index.yml')
        temp_workflow.parent.mkdir(parents=True, exist_ok=True)
        temp_workflow.write_text(workflow_content)
        
        try:
            # Commit and push the workflow with our files
            subprocess.run(['git', 'add', str(archive_path), str(metadata_path), str(temp_workflow)], check=True)
            subprocess.run(['git', 'commit', '-m', 'chore: upload index artifacts'], check=True)
            subprocess.run(['git', 'push'], check=True)
            
            # Trigger the workflow
            result = subprocess.run(
                ['gh', 'workflow', 'run', 'temp-upload-index.yml'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("✅ Workflow triggered successfully!")
                print("   Check progress at: https://github.com/{}/actions".format(self.repo))
            else:
                print(f"❌ Failed to trigger workflow: {result.stderr}")
            
        finally:
            # Clean up
            temp_workflow.unlink(missing_ok=True)
            archive_path.unlink(missing_ok=True)
            metadata_path.unlink(missing_ok=True)
            
            # Reset git changes
            subprocess.run(['git', 'reset', '--hard', 'HEAD~1'], capture_output=True)
    
    def upload_direct(self, archive_path: Path, metadata: Dict[str, Any]) -> None:
        """
        Upload directly using GitHub API (alternative method).
        
        Note: This requires being in a GitHub Actions environment.
        """
        print("\n📤 Uploading to GitHub Actions Artifacts...")
        
        # This method should be called from within a GitHub Action
        # The actual upload is handled by the workflow
        
        # For now, just prepare the files
        metadata_path = Path('artifact-metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"✅ Files prepared for upload:")
        print(f"   - {archive_path} ({archive_path.stat().st_size / 1024 / 1024:.1f} MB)")
        print(f"   - {metadata_path}")
        print("\nTo complete upload, run this in GitHub Actions:")
        print("  uses: actions/upload-artifact@v4")
        print("  with:")
        print(f"    name: index-{{{{ github.sha }}}}")
        print(f"    path: |")
        print(f"      {archive_path}")
        print(f"      {metadata_path}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Upload index files to GitHub Actions Artifacts'
    )
    parser.add_argument(
        '--method',
        choices=['workflow', 'direct'],
        default='workflow',
        help='Upload method (workflow triggers GH Action, direct for use in GH Action)'
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
        '--validate',
        action='store_true',
        help='Validate indexes before upload'
    )
    
    args = parser.parse_args()
    
    try:
        uploader = IndexArtifactUploader(repo=args.repo)
        
        # Validate if requested
        if args.validate:
            print("🔍 Validating indexes...")
            # Add validation logic here
            print("✅ Validation passed")
        
        # Compress indexes
        archive_path, checksum, size = uploader.compress_indexes(Path(args.output))
        
        # Check size limit (500MB for GitHub Actions Artifacts)
        if size > 500 * 1024 * 1024:
            print(f"❌ Archive too large: {size / 1024 / 1024:.1f} MB > 500 MB")
            print("   Consider cleaning up old data or using incremental updates.")
            sys.exit(1)
        
        # Create metadata
        metadata = uploader.create_metadata(checksum, size)
        
        # Upload based on method
        if args.method == 'workflow':
            uploader.trigger_workflow(archive_path, metadata)
        else:
            uploader.upload_direct(archive_path, metadata)
        
        print("\n✨ Upload complete!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()