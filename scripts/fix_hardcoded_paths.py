#!/usr/bin/env python3
"""
Fix hardcoded paths in the codebase.

This script updates hardcoded absolute paths to use the PathUtils module
for environment-agnostic path management.
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple, Dict
import argparse
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


# Path patterns to replace
PATH_REPLACEMENTS = [
    # Workspace paths
    (r'/workspaces/Code-Index-MCP', 'PathUtils.get_workspace_root()'),
    (r'Path\("/workspaces/Code-Index-MCP"\)', 'PathUtils.get_workspace_root()'),
    (r'"/workspaces/Code-Index-MCP"', 'str(PathUtils.get_workspace_root())'),
    
    # Docker app paths
    (r'/app/', 'PathUtils.get_workspace_root() / '),
    (r'Path\("/app"\)', 'PathUtils.get_workspace_root()'),
    (r'"/app"', 'str(PathUtils.get_workspace_root())'),
    
    # Index paths
    (r'/workspaces/Code-Index-MCP/\.indexes', 'PathUtils.get_index_storage_path()'),
    (r'\.indexes/repository_registry\.json', 'PathUtils.get_repo_registry_path()'),
    
    # Test repo paths
    (r'/workspaces/Code-Index-MCP/test_repos', 'PathUtils.get_test_repos_path()'),
    
    # Temp paths
    (r'/tmp/mcp-indexes', 'PathUtils.get_temp_path() / "mcp-indexes"'),
    (r'/tmp/mcp_', 'PathUtils.get_temp_path() / "mcp_'),
    
    # Home paths
    (r'/home/vscode/\.claude', 'Path.home() / ".claude"'),
    
    # Data paths
    (r'/data/', 'PathUtils.get_data_path() / '),
    (r'"/data"', 'str(PathUtils.get_data_path())'),
    
    # Log paths
    (r'/var/log/mcp-server', 'PathUtils.get_log_path()'),
]

# Files to skip
SKIP_FILES = {
    'fix_hardcoded_paths.py',  # This file
    'path_utils.py',  # Path utilities module
    '.git',  # Git directory
    'node_modules',  # Node modules
    '__pycache__',  # Python cache
    '.pytest_cache',  # Pytest cache
    'testing-env',  # Testing environment
    'archive',  # Archive directory
}

# Import statement to add
PATHUTILS_IMPORT = "from mcp_server.core.path_utils import PathUtils"
PATH_IMPORT = "from pathlib import Path"


def should_process_file(file_path: Path) -> bool:
    """Check if file should be processed."""
    # Skip if in skip list
    for skip in SKIP_FILES:
        if skip in str(file_path):
            return False
    
    # Only process Python files
    if not file_path.suffix == '.py':
        return False
        
    # Skip if file doesn't exist
    if not file_path.exists():
        return False
        
    return True


def add_imports(content: str) -> str:
    """Add necessary imports if not present."""
    lines = content.split('\n')
    
    # Check if imports already exist
    has_pathutils = any('PathUtils' in line and 'import' in line for line in lines)
    has_path = any('from pathlib import Path' in line for line in lines)
    
    # Find where to insert imports (after other imports)
    import_index = 0
    for i, line in enumerate(lines):
        if line.startswith('import ') or line.startswith('from '):
            import_index = i + 1
        elif import_index > 0 and line.strip() and not line.startswith(' '):
            # End of import section
            break
    
    # Add imports if needed
    if not has_pathutils and 'PathUtils' in content:
        lines.insert(import_index, PATHUTILS_IMPORT)
        import_index += 1
        
    if not has_path and 'Path(' in content:
        # Check if Path is already imported differently
        has_other_path = any('Path' in line and 'import' in line for line in lines)
        if not has_other_path:
            lines.insert(import_index, PATH_IMPORT)
    
    return '\n'.join(lines)


def fix_file_paths(file_path: Path, dry_run: bool = False) -> List[str]:
    """Fix hardcoded paths in a single file."""
    changes = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = original_content = f.read()
    except Exception as e:
        logger.error(f"Error reading {file_path}: {e}")
        return changes
    
    # Apply replacements
    for pattern, replacement in PATH_REPLACEMENTS:
        matches = list(re.finditer(pattern, content))
        if matches:
            for match in matches:
                old_text = match.group()
                # Skip if already using PathUtils
                if 'PathUtils' in content[max(0, match.start()-50):match.end()+50]:
                    continue
                    
                changes.append(f"  {old_text} -> {replacement}")
            
            content = re.sub(pattern, replacement, content)
    
    # Only process if changes were made
    if content != original_content:
        # Add necessary imports
        content = add_imports(content)
        
        if not dry_run:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.info(f"✓ Fixed: {file_path}")
                for change in changes:
                    logger.debug(change)
            except Exception as e:
                logger.error(f"Error writing {file_path}: {e}")
        else:
            logger.info(f"Would fix: {file_path}")
            for change in changes:
                logger.info(change)
    
    return changes


def fix_json_configs(dry_run: bool = False):
    """Fix JSON configuration files."""
    workspace_root = Path.cwd()
    
    # Fix docker-compose.yml
    compose_files = [
        workspace_root / "docker-compose.yml",
        workspace_root / "docker" / "compose" / "development" / "docker-compose.dev.yml",
        workspace_root / "docker" / "compose" / "production" / "docker-compose.production.yml",
    ]
    
    for compose_path in compose_files:
        if compose_path.exists():
            try:
                with open(compose_path, 'r') as f:
                    content = original = f.read()
                
                # Replace hardcoded paths with environment variables
                content = content.replace(
                    '/workspaces/Code-Index-MCP',
                    '${MCP_WORKSPACE_ROOT:-/app}'
                )
                content = content.replace(
                    'DATABASE_URL=sqlite:///app/data/code_index.db',
                    'DATABASE_URL=sqlite:///${MCP_DATA_PATH:-/app/data}/code_index.db'
                )
                
                if content != original and not dry_run:
                    with open(compose_path, 'w') as f:
                        f.write(content)
                    logger.info(f"✓ Fixed: {compose_path}")
                elif content != original:
                    logger.info(f"Would fix: {compose_path}")
                    
            except Exception as e:
                logger.error(f"Error processing {compose_path}: {e}")


def find_remaining_paths(workspace_root: Path) -> Dict[str, List[str]]:
    """Find any remaining hardcoded paths."""
    remaining = {}
    
    patterns = [
        r'/workspaces/Code-Index-MCP',
        r'/app/',
        r'/home/vscode',
        r'/tmp/mcp',
        r'/data/',
        r'/var/log/mcp-server'
    ]
    
    for py_file in workspace_root.rglob("*.py"):
        if not should_process_file(py_file):
            continue
            
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            for pattern in patterns:
                if re.search(pattern, content):
                    if str(py_file) not in remaining:
                        remaining[str(py_file)] = []
                    remaining[str(py_file)].append(pattern)
                    
        except Exception:
            pass
            
    return remaining


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Fix hardcoded paths in codebase")
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Show what would be changed without modifying files"
    )
    parser.add_argument(
        "--check", "-c",
        action="store_true",
        help="Check for remaining hardcoded paths"
    )
    parser.add_argument(
        "--file", "-f",
        type=Path,
        help="Fix a specific file"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed changes"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    workspace_root = Path.cwd()
    
    if args.check:
        logger.info("Checking for remaining hardcoded paths...")
        remaining = find_remaining_paths(workspace_root)
        
        if remaining:
            logger.warning(f"\nFound hardcoded paths in {len(remaining)} files:")
            for file_path, patterns in remaining.items():
                logger.warning(f"\n{file_path}:")
                for pattern in patterns:
                    logger.warning(f"  - {pattern}")
        else:
            logger.info("✓ No hardcoded paths found!")
        return
    
    if args.file:
        # Fix single file
        if should_process_file(args.file):
            fix_file_paths(args.file, dry_run=args.dry_run)
        else:
            logger.error(f"Cannot process file: {args.file}")
        return
    
    # Fix all Python files
    logger.info("Fixing hardcoded paths in Python files...")
    logger.info("=" * 60)
    
    total_files = 0
    fixed_files = 0
    
    for py_file in workspace_root.rglob("*.py"):
        if should_process_file(py_file):
            total_files += 1
            changes = fix_file_paths(py_file, dry_run=args.dry_run)
            if changes:
                fixed_files += 1
    
    # Fix configuration files
    logger.info("\nFixing configuration files...")
    fix_json_configs(dry_run=args.dry_run)
    
    logger.info("\n" + "=" * 60)
    logger.info(f"Processed {total_files} Python files")
    logger.info(f"Fixed {fixed_files} files with hardcoded paths")
    
    if args.dry_run:
        logger.info("\nThis was a dry run. Use without --dry-run to apply changes.")
    else:
        logger.info("\n✓ Path fixes complete!")
        logger.info("\nNext steps:")
        logger.info("1. Run: python scripts/setup_environment.py")
        logger.info("2. Test the changes")
        logger.info("3. Run: python scripts/fix_hardcoded_paths.py --check")


if __name__ == "__main__":
    main()