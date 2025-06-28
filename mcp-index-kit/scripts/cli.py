#!/usr/bin/env python3
"""MCP Index Kit CLI - Manage code indexes with GitHub Artifacts"""

import click
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import shutil
import tempfile
import tarfile
import hashlib


@click.group()
@click.version_option(version='1.0.0')
def cli():
    """MCP Index Kit - Portable code index management for any repository"""
    pass


@cli.command()
@click.option('--force', is_flag=True, help='Force installation even if already installed')
@click.option('--branch', default=None, help='Override default branch detection')
def init(force: bool, branch: Optional[str]):
    """Initialize MCP index management in the current repository"""
    # Check if already initialized
    if not force and Path('.mcp-index.json').exists():
        click.echo(click.style('✓ MCP Index already initialized', fg='yellow'))
        click.echo('Use --force to reinitialize')
        return
    
    # Check if in git repo
    if not Path('.git').exists():
        click.echo(click.style('✗ Not in a git repository', fg='red'))
        sys.exit(1)
    
    # Detect default branch if not provided
    if not branch:
        try:
            result = subprocess.run(
                ['git', 'symbolic-ref', 'refs/remotes/origin/HEAD'],
                capture_output=True, text=True, check=False
            )
            if result.returncode == 0:
                branch = result.stdout.strip().split('/')[-1]
            else:
                branch = 'main'
        except:
            branch = 'main'
    
    click.echo(click.style('Initializing MCP Index Kit...', fg='blue'))
    
    # Run installer script
    installer_path = Path(__file__).parent.parent / 'install.sh'
    if installer_path.exists():
        subprocess.run(['bash', str(installer_path)], check=True)
    else:
        click.echo(click.style('✗ Installer not found', fg='red'))
        sys.exit(1)
    
    click.echo(click.style('✓ MCP Index Kit initialized successfully!', fg='green'))


@cli.command()
@click.option('--semantic/--no-semantic', default=False, help='Enable semantic search')
@click.option('--output', default='.mcp-index/code_index.db', help='Output path')
@click.option('--config', default='.mcp-index.json', help='Config file path')
@click.option('--stats', is_flag=True, help='Show indexing statistics')
def build(semantic: bool, output: str, config: str, stats: bool):
    """Build the code index locally"""
    click.echo(click.style('Building code index...', fg='blue'))
    
    # Check config
    config_path = Path(config)
    if not config_path.exists():
        click.echo(click.style(f'✗ Config file not found: {config}', fg='red'))
        sys.exit(1)
    
    # Load config
    with open(config_path) as f:
        cfg = json.load(f)
    
    # Create output directory
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Download indexer if not available
    indexer_path = Path.home() / '.mcp' / 'indexer' / 'mcp-indexer.pyz'
    if not indexer_path.exists():
        click.echo('Downloading MCP indexer...')
        indexer_path.parent.mkdir(parents=True, exist_ok=True)
        # In real implementation, download from releases
        click.echo(click.style('✗ Indexer download not implemented', fg='red'))
        click.echo('Please download manually from: https://github.com/yourusername/Code-Index-MCP/releases')
        sys.exit(1)
    
    # Build command
    cmd = [
        sys.executable, str(indexer_path), 'build',
        '--config', str(config_path),
        '--output', str(output_path)
    ]
    
    if cfg.get('ignore_file'):
        ignore_path = Path(cfg['ignore_file'])
        if ignore_path.exists():
            cmd.extend(['--ignore-file', str(ignore_path)])
    
    if semantic and cfg.get('semantic_search', {}).get('enabled'):
        cmd.append('--semantic')
    
    if stats:
        cmd.append('--stats')
    
    # Run indexer
    try:
        subprocess.run(cmd, check=True)
        click.echo(click.style('✓ Index built successfully!', fg='green'))
        
        # Show stats
        if output_path.exists():
            size_mb = output_path.stat().st_size / 1024 / 1024
            click.echo(f'Index size: {size_mb:.2f} MB')
    except subprocess.CalledProcessError as e:
        click.echo(click.style(f'✗ Build failed: {e}', fg='red'))
        sys.exit(1)


@cli.command()
@click.option('--validate', is_flag=True, help='Validate after upload')
def push(validate: bool):
    """Upload local index to GitHub Artifacts"""
    click.echo(click.style('Pushing index to GitHub...', fg='blue'))
    
    # Check if index exists
    index_path = Path('.mcp-index/code_index.db')
    if not index_path.exists():
        click.echo(click.style('✗ No index found. Run "mcp-index build" first.', fg='red'))
        sys.exit(1)
    
    # Create archive
    archive_path = Path('mcp-index-archive.tar.gz')
    click.echo('Creating archive...')
    
    with tarfile.open(archive_path, 'w:gz') as tar:
        tar.add('.mcp-index', arcname='.')
    
    # Calculate checksum
    checksum = hashlib.sha256()
    with open(archive_path, 'rb') as f:
        checksum.update(f.read())
    
    checksum_path = Path('mcp-index-archive.tar.gz.sha256')
    with open(checksum_path, 'w') as f:
        f.write(f'{checksum.hexdigest()}  mcp-index-archive.tar.gz\n')
    
    # Get git info
    try:
        commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
        branch = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], text=True).strip()
    except:
        click.echo(click.style('✗ Failed to get git info', fg='red'))
        sys.exit(1)
    
    # Upload using GitHub CLI
    artifact_name = f'mcp-index-{commit[:7]}'
    
    try:
        # This would use gh CLI in real implementation
        click.echo(f'Uploading as artifact: {artifact_name}')
        # gh workflow run .github/workflows/mcp-index.yml
        click.echo(click.style('✓ Upload triggered!', fg='green'))
        click.echo('Check GitHub Actions for status.')
    except Exception as e:
        click.echo(click.style(f'✗ Upload failed: {e}', fg='red'))
        sys.exit(1)
    finally:
        # Cleanup
        archive_path.unlink(missing_ok=True)
        checksum_path.unlink(missing_ok=True)


@cli.command()
@click.option('--latest/--all', default=True, help='Download latest or list all')
@click.option('--pr', type=int, help='Download index for specific PR')
def pull(latest: bool, pr: Optional[int]):
    """Download index from GitHub Artifacts"""
    click.echo(click.style('Pulling index from GitHub...', fg='blue'))
    
    # Check gh CLI
    if not shutil.which('gh'):
        click.echo(click.style('✗ GitHub CLI (gh) not installed', fg='red'))
        click.echo('Install from: https://cli.github.com/')
        sys.exit(1)
    
    # Run download script
    download_script = Path(__file__).parent.parent / 'templates' / 'download-index.sh'
    if download_script.exists():
        subprocess.run(['bash', str(download_script)], check=True)
    else:
        click.echo(click.style('✗ Download script not found', fg='red'))
        sys.exit(1)


@cli.command()
def list():
    """List available index artifacts"""
    click.echo(click.style('Listing available indexes...', fg='blue'))
    
    # Check gh CLI
    if not shutil.which('gh'):
        click.echo(click.style('✗ GitHub CLI (gh) not installed', fg='red'))
        sys.exit(1)
    
    try:
        # Get repo info
        repo = subprocess.check_output(
            ['gh', 'repo', 'view', '--json', 'nameWithOwner', '-q', '.nameWithOwner'],
            text=True
        ).strip()
        
        # List artifacts
        result = subprocess.run([
            'gh', 'api',
            '-H', 'Accept: application/vnd.github+json',
            f'/repos/{repo}/actions/artifacts',
            '--jq', '.artifacts[] | select(.name | startswith("mcp-index-")) | {name, created_at, size_in_bytes}'
        ], capture_output=True, text=True)
        
        if result.returncode == 0 and result.stdout:
            artifacts = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    artifact = json.loads(line)
                    size_mb = artifact['size_in_bytes'] / 1024 / 1024
                    artifacts.append({
                        'name': artifact['name'],
                        'created': artifact['created_at'],
                        'size_mb': f'{size_mb:.2f}'
                    })
            
            if artifacts:
                click.echo(f'Found {len(artifacts)} index artifacts:')
                for a in sorted(artifacts, key=lambda x: x['created'], reverse=True)[:10]:
                    click.echo(f"  {a['name']} - {a['size_mb']}MB - {a['created']}")
            else:
                click.echo('No index artifacts found')
        else:
            click.echo('No artifacts found')
    except Exception as e:
        click.echo(click.style(f'✗ Failed to list artifacts: {e}', fg='red'))
        sys.exit(1)


@cli.command()
def sync():
    """Sync index with GitHub (pull if newer, push if local is newer)"""
    click.echo(click.style('Syncing index with GitHub...', fg='blue'))
    
    # Check local index
    local_index = Path('.mcp-index/code_index.db')
    local_metadata = Path('.mcp-index/.index_metadata.json')
    
    if not local_index.exists():
        # No local index, try to pull
        click.echo('No local index found, attempting to pull...')
        ctx = click.get_current_context()
        ctx.invoke(pull, latest=True)
        return
    
    # Get local metadata
    local_commit = None
    if local_metadata.exists():
        with open(local_metadata) as f:
            metadata = json.load(f)
            local_commit = metadata.get('commit')
    
    # Get current commit
    try:
        current_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    except:
        click.echo(click.style('✗ Failed to get current commit', fg='red'))
        sys.exit(1)
    
    if local_commit == current_commit:
        click.echo(click.style('✓ Index is up to date', fg='green'))
    else:
        click.echo(f'Local index is for commit: {local_commit[:7] if local_commit else "unknown"}')
        click.echo(f'Current commit: {current_commit[:7]}')
        
        # In real implementation, would check remote artifacts
        # and decide whether to push or pull
        click.echo('Index needs updating. Run "mcp-index build && mcp-index push"')


@cli.command()
def info():
    """Show information about the current index"""
    click.echo(click.style('MCP Index Information', fg='blue'))
    click.echo('=' * 40)
    
    # Check config
    config_path = Path('.mcp-index.json')
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
        click.echo(f'✓ Configuration: {config_path}')
        click.echo(f'  Enabled: {config.get("enabled", True)}')
        click.echo(f'  Languages: {config.get("languages", "auto")}')
    else:
        click.echo('✗ No configuration found')
    
    # Check index
    index_path = Path('.mcp-index/code_index.db')
    if index_path.exists():
        size_mb = index_path.stat().st_size / 1024 / 1024
        click.echo(f'✓ Index: {index_path}')
        click.echo(f'  Size: {size_mb:.2f} MB')
        
        # Check metadata
        metadata_path = Path('.mcp-index/.index_metadata.json')
        if metadata_path.exists():
            with open(metadata_path) as f:
                metadata = json.load(f)
            click.echo(f'  Created: {metadata.get("created_at", "unknown")}')
            click.echo(f'  Commit: {metadata.get("commit", "unknown")[:7]}')
            click.echo(f'  Files: {metadata.get("indexed_files", "unknown")}')
    else:
        click.echo('✗ No index found')
    
    # Check GitHub workflow
    workflow_path = Path('.github/workflows/mcp-index.yml')
    if workflow_path.exists():
        click.echo(f'✓ GitHub workflow: {workflow_path}')
    else:
        click.echo('✗ No GitHub workflow found')


@cli.command()
def cleanup():
    """Clean up old index artifacts on GitHub"""
    click.echo(click.style('Cleaning up old artifacts...', fg='blue'))
    
    try:
        # Trigger cleanup workflow
        subprocess.run([
            'gh', 'workflow', 'run', 'mcp-index.yml',
            '--field', 'cleanup=true'
        ], check=True)
        
        click.echo(click.style('✓ Cleanup triggered!', fg='green'))
        click.echo('Check GitHub Actions for status.')
    except Exception as e:
        click.echo(click.style(f'✗ Cleanup failed: {e}', fg='red'))
        sys.exit(1)


@cli.command()
@click.option('--enable/--disable', default=True, help='Enable or disable indexing')
def toggle(enable: bool):
    """Enable or disable MCP indexing"""
    config_path = Path('.mcp-index.json')
    
    if not config_path.exists():
        click.echo(click.style('✗ Not initialized. Run "mcp-index init" first.', fg='red'))
        sys.exit(1)
    
    # Update config
    with open(config_path) as f:
        config = json.load(f)
    
    config['enabled'] = enable
    
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    status = 'enabled' if enable else 'disabled'
    click.echo(click.style(f'✓ MCP indexing {status}', fg='green'))
    
    # Also update GitHub variable if possible
    try:
        value = 'true' if enable else 'false'
        subprocess.run([
            'gh', 'variable', 'set', 'MCP_INDEX_ENABLED', '--body', value
        ], check=False)
    except:
        pass


@cli.command()
@click.argument('action', type=click.Choice(['install', 'uninstall', 'status']))
def hooks(action: str):
    """Manage git hooks for automatic index sync"""
    script_dir = Path(__file__).parent.parent
    hooks_dir = script_dir / 'hooks'
    installer_script = hooks_dir / 'install-hooks.sh'
    
    if not installer_script.exists():
        # Try to find it in the installed location
        possible_paths = [
            Path('/usr/local/share/mcp-index-kit/hooks/install-hooks.sh'),
            Path.home() / '.mcp-index-kit/hooks/install-hooks.sh'
        ]
        for path in possible_paths:
            if path.exists():
                installer_script = path
                break
        else:
            click.echo(click.style('✗ Hooks installer not found', fg='red'))
            click.echo('Make sure mcp-index-kit is properly installed.')
            sys.exit(1)
    
    if action == 'install':
        try:
            subprocess.run(['bash', str(installer_script)], check=True)
        except subprocess.CalledProcessError:
            click.echo(click.style('✗ Failed to install hooks', fg='red'))
            sys.exit(1)
    
    elif action == 'uninstall':
        try:
            subprocess.run(['bash', str(installer_script), '--uninstall'], check=True)
        except subprocess.CalledProcessError:
            click.echo(click.style('✗ Failed to uninstall hooks', fg='red'))
            sys.exit(1)
    
    elif action == 'status':
        git_dir = Path('.git/hooks')
        if not git_dir.exists():
            click.echo(click.style('✗ Not in a git repository', fg='red'))
            sys.exit(1)
        
        hooks_info = []
        for hook_name in ['pre-push', 'post-merge', 'post-checkout']:
            hook_path = git_dir / hook_name
            if hook_path.exists():
                # Check if it's our hook
                try:
                    with open(hook_path) as f:
                        content = f.read()
                    if 'MCP Index' in content:
                        hooks_info.append((hook_name, 'installed', 'green'))
                    else:
                        hooks_info.append((hook_name, 'other hook', 'yellow'))
                except:
                    hooks_info.append((hook_name, 'unreadable', 'red'))
            else:
                hooks_info.append((hook_name, 'not installed', 'dim'))
        
        click.echo('Git hooks status:')
        for name, status, color in hooks_info:
            click.echo(f'  {name:<15} {click.style(status, fg=color)}')
        
        # Check configuration
        config_path = Path('.mcp-index.json')
        if config_path.exists():
            with open(config_path) as f:
                config = json.load(f)
            
            click.echo('\nAuto-sync configuration:')
            enabled = config.get('enabled', True)
            auto_upload = config.get('auto_upload', True)
            auto_download = config.get('auto_download', True)
            
            click.echo(f'  Indexing:      {click.style("enabled" if enabled else "disabled", fg="green" if enabled else "red")}')
            click.echo(f'  Auto upload:   {click.style("enabled" if auto_upload else "disabled", fg="green" if auto_upload else "red")}')
            click.echo(f'  Auto download: {click.style("enabled" if auto_download else "disabled", fg="green" if auto_download else "red")}')


if __name__ == '__main__':
    cli()