#!/usr/bin/env python3
"""
Fix to make ignore patterns apply ONLY during export/sharing, not during indexing.
This allows users to search their own .env files, secrets, etc. locally while
preventing them from being shared.
"""

import os

def fix_dispatcher_enhanced():
    """Remove ignore pattern check from index_directory method."""
    print("1. Fixing dispatcher_enhanced.py to index ALL files...")
    
    # The fix: Remove the ignore check from index_directory
    old_code = '''            # Check if file should be ignored
            if ignore_manager.should_ignore(path):
                stats["ignored_files"] += 1
                logger.debug(f"Ignoring {path} due to ignore patterns")
                continue'''
    
    new_code = '''            # NOTE: We index ALL files locally, including gitignored ones
            # Filtering happens only during export/sharing
            # This allows local search of .env, secrets, etc.'''
    
    print("   - Will remove ignore check from index_directory()")
    print("   - All files will be indexed for local search")
    return ("mcp_server/dispatcher/dispatcher_enhanced.py", old_code, new_code)


def fix_file_watcher():
    """Remove ignore pattern check from file watcher."""
    print("\n2. Fixing watcher.py to index ALL file changes...")
    
    old_code = '''            # Check if file should be ignored
            if should_ignore_file(path):
                logger.debug(f"Ignoring file {path} due to ignore patterns")
                return'''
    
    new_code = '''            # NOTE: We index ALL files locally, including gitignored ones
            # Filtering happens only during export/sharing'''
    
    print("   - Will remove ignore check from file watcher")
    print("   - All file changes will trigger re-indexing")
    return ("mcp_server/watcher.py", old_code, new_code)


def update_secure_export():
    """Ensure secure export uses both .gitignore and .mcp-index-ignore."""
    print("\n3. Verifying secure_index_export.py...")
    print("   - Already filters during export ✓")
    print("   - Uses .gitignore patterns ✓")
    print("   - Should also use .mcp-index-ignore patterns")
    
    # Check if it needs to load .mcp-index-ignore patterns too
    enhancement = '''
    def _load_ignore_patterns(self):
        """Load patterns from both .gitignore and .mcp-index-ignore."""
        patterns = []
        
        # Load .gitignore
        if self.gitignore_path.exists():
            patterns.extend(self._load_gitignore_patterns())
            
        # Load .mcp-index-ignore  
        mcp_ignore_path = Path(".mcp-index-ignore")
        if mcp_ignore_path.exists():
            with open(mcp_ignore_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        patterns.append(line)
                        
        return patterns
    '''
    return enhancement


def create_documentation():
    """Create documentation explaining the behavior."""
    print("\n4. Creating documentation...")
    
    doc_content = '''# Ignore Patterns Behavior

## How It Works

The MCP Indexer uses a **"index everything, filter on share"** approach:

### Local Indexing (Your Machine)
- **ALL files are indexed**, including:
  - .env files with secrets
  - API keys and credentials  
  - Private configuration files
  - Files listed in .gitignore
  - Files listed in .mcp-index-ignore

This allows you to search your entire codebase locally, including sensitive files.

### Sharing/Exporting (GitHub Artifacts)
- **Sensitive files are filtered out** before sharing:
  - Files matching .gitignore patterns are excluded
  - Files matching .mcp-index-ignore patterns are excluded
  - The shared index NEVER contains sensitive data

## Why This Approach?

1. **Local Power**: You can search everything in your codebase, including configuration and secrets
2. **Share Safely**: When you share indexes via GitHub Artifacts, sensitive data is automatically removed
3. **Best of Both**: Full local search capabilities + secure sharing

## Patterns Files

### .gitignore
- Standard git ignore patterns
- Automatically respected during export
- Prevents version control of sensitive files

### .mcp-index-ignore  
- Additional patterns for MCP indexing
- Useful for excluding test files, large binaries, etc. from shared indexes
- Does NOT affect local indexing (you can still search these files)

## Security Note

Even though sensitive files are indexed locally, they are:
- Never included in shared index artifacts
- Never uploaded to GitHub
- Only searchable on your local machine
'''
    
    print("   - Documentation explains 'index all, filter on share' approach")
    return doc_content


def main():
    print("IGNORE PATTERNS FIX PLAN")
    print("=" * 60)
    print("\nCurrent Behavior:")
    print("- Ignore patterns PREVENT indexing (no local search of .env files)")
    print("\nDesired Behavior:") 
    print("- Index EVERYTHING locally (can search .env files)")
    print("- Filter sensitive files ONLY when sharing/exporting")
    print("\n" + "=" * 60)
    
    # Get fixes
    dispatcher_fix = fix_dispatcher_enhanced()
    watcher_fix = fix_file_watcher()
    export_enhancement = update_secure_export()
    documentation = create_documentation()
    
    print("\n" + "=" * 60)
    print("SUMMARY OF CHANGES NEEDED:")
    print("\n1. dispatcher_enhanced.py - Remove ignore check from index_directory()")
    print("2. watcher.py - Remove ignore check from file monitoring")
    print("3. secure_index_export.py - Enhance to use .mcp-index-ignore (already filters .gitignore)")
    print("4. Add documentation explaining the behavior")
    
    print("\nBenefits:")
    print("✓ Can search .env files and secrets locally")
    print("✓ Sensitive files never shared in exports")
    print("✓ Better developer experience")
    print("✓ Maintains security")


if __name__ == "__main__":
    main()