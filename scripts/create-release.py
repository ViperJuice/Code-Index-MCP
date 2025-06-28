#!/usr/bin/env python3
"""
Create a GitHub release with index artifacts.

This script creates a new GitHub release and uploads the index files as release assets.
"""

import os
import sys
import json
import subprocess
import argparse
import tempfile
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from secure_index_export import SecureIndexExporter


class GitHubReleaseCreator:
    """Create GitHub releases with index artifacts."""
    
    def __init__(self, repo: Optional[str] = None):
        """Initialize release creator."""
        self.repo = repo or self._detect_repository()
        
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
            
            # Parse the repository from the URL
            if 'github.com' in url:
                if url.startswith('git@'):
                    # SSH format: git@github.com:owner/repo.git
                    parts = url.split(':')[1].replace('.git', '').strip()
                    return parts
                else:
                    # HTTPS format: https://github.com/owner/repo.git
                    parts = url.split('github.com/')[1].replace('.git', '').strip()
                    return parts
        except:
            pass
        
        return os.environ.get('GITHUB_REPOSITORY', 'unknown/unknown')
    
    def _get_version_tag(self, version: Optional[str] = None) -> str:
        """Get or generate version tag."""
        if version:
            return f"v{version}" if not version.startswith('v') else version
        
        # Generate version from date
        now = datetime.now(timezone.utc)
        return f"v{now.strftime('%Y.%m.%d')}"
    
    def _create_release_archive(self, output_path: Path) -> Dict[str, Any]:
        """Create a release archive with secure export."""
        print("📦 Creating secure release archive...")
        
        # Use secure exporter
        exporter = SecureIndexExporter()
        
        # Export with secure settings
        export_path = exporter.export_index(
            output_path=str(output_path),
            include_metadata=True,
            compress=True
        )
        
        # Calculate checksum
        sha256_hash = hashlib.sha256()
        with open(export_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256_hash.update(chunk)
        
        checksum = sha256_hash.hexdigest()
        size_mb = Path(export_path).stat().st_size / (1024 * 1024)
        
        return {
            'path': export_path,
            'checksum': checksum,
            'size_mb': round(size_mb, 1)
        }
    
    def _generate_release_notes(self, tag: str, archive_info: Dict[str, Any]) -> str:
        """Generate release notes."""
        return f"""# Code Index MCP Release {tag}

## 📥 Download

Download the pre-built index archive below to get started quickly.

### Archive Contents
- **SQLite Database**: Full-text search index with symbol definitions
- **Vector Embeddings**: Semantic search capabilities  
- **Metadata**: Index configuration and statistics

### Archive Info
- **Size**: {archive_info['size_mb']} MB
- **SHA256**: `{archive_info['checksum']}`
- **Format**: tar.gz

## 🚀 Quick Start

1. Download `code-index-{tag}.tar.gz` from the assets below
2. Extract to your project:
   ```bash
   tar -xzf code-index-{tag}.tar.gz
   ```
3. Install Code Index MCP:
   ```bash
   pip install code-index-mcp
   ```
4. Start using the index!

## 📊 Index Statistics

This index was built from the current state of the repository and includes:
- All supported programming languages
- Full symbol extraction and cross-referencing
- Semantic embeddings for intelligent search

## 🔒 Security

This release archive has been filtered to exclude:
- Environment files (.env, .env.*)
- Private keys and certificates
- Credentials and secrets
- Temporary and cache files

## 📝 Changelog

See [CHANGELOG.md](https://github.com/{self.repo}/blob/main/CHANGELOG.md) for detailed changes.

---
*Generated on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*
"""
    
    def create_release(self, tag: str, name: str, draft: bool = True) -> bool:
        """
        Create a GitHub release.
        
        Args:
            tag: Version tag for the release
            name: Release name
            draft: Whether to create as draft
            
        Returns:
            True if successful
        """
        try:
            # Create release archive
            with tempfile.TemporaryDirectory() as tmpdir:
                archive_name = f"code-index-{tag}.tar.gz"
                archive_path = Path(tmpdir) / archive_name
                
                archive_info = self._create_release_archive(archive_path)
                print(f"✅ Created archive: {archive_info['size_mb']} MB")
                
                # Generate release notes
                notes = self._generate_release_notes(tag, archive_info)
                
                # Create release using gh CLI
                print(f"\n📝 Creating GitHub release {tag}...")
                
                cmd = [
                    'gh', 'release', 'create', tag,
                    '--repo', self.repo,
                    '--title', name,
                    '--notes', notes
                ]
                
                if draft:
                    cmd.append('--draft')
                
                # Add the archive file
                cmd.append(str(archive_info['path']))
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    print(f"✅ Release created successfully!")
                    print(f"🔗 View at: https://github.com/{self.repo}/releases/tag/{tag}")
                    return True
                else:
                    print(f"❌ Failed to create release: {result.stderr}")
                    return False
                    
        except subprocess.CalledProcessError as e:
            print(f"❌ Error: {e}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Create GitHub release with index artifacts"
    )
    parser.add_argument(
        '--version', '-v',
        help='Version tag (e.g., 1.0.0). Auto-generated if not specified.'
    )
    parser.add_argument(
        '--name', '-n',
        help='Release name. Defaults to "Code Index MCP vX.Y.Z"'
    )
    parser.add_argument(
        '--repo',
        help='GitHub repository (owner/name). Auto-detected if not specified.'
    )
    parser.add_argument(
        '--publish',
        action='store_true',
        help='Publish immediately (default is to create as draft)'
    )
    
    args = parser.parse_args()
    
    # Check for gh CLI
    try:
        subprocess.run(['gh', '--version'], capture_output=True, check=True)
    except:
        print("❌ Error: GitHub CLI (gh) is required but not found.")
        print("📥 Install from: https://cli.github.com/")
        return 1
    
    # Create release
    creator = GitHubReleaseCreator(repo=args.repo)
    
    # Determine version and name
    version = creator._get_version_tag(args.version)
    name = args.name or f"Code Index MCP {version}"
    
    # Create the release
    success = creator.create_release(
        tag=version,
        name=name,
        draft=not args.publish
    )
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())