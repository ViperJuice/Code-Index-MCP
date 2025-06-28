#!/usr/bin/env python3
"""
Claude Index Management CLI

A command-line tool for managing MCP indexes across repositories.
Provides easy commands for creating, validating, and migrating indexes.
"""

import os
import sys
import json
import argparse
import asyncio
import subprocess
import hashlib
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
import sqlite3

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mcp_server.utils.index_discovery import IndexDiscovery
from mcp_server.config.index_paths import IndexPathConfig
from mcp_server.core.preflight_validator import PreFlightValidator
from mcp_server.utils.mcp_health_check import MCPDiagnostics
from mcp_server.cli.index_commands import (
    CreateIndexCommand,
    ValidateIndexCommand,
    ListIndexesCommand,
    MigrateIndexCommand,
    SyncIndexCommand,
)


class ClaudeIndexCLI:
    """Main CLI application for index management."""
    
    def __init__(self):
        """Initialize the CLI."""
        self.parser = self._create_parser()
        
    def _create_parser(self) -> argparse.ArgumentParser:
        """Create the argument parser."""
        parser = argparse.ArgumentParser(
            prog="claude-index",
            description="Manage MCP indexes for Claude Code",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  claude-index create --repo my-project --path /path/to/code
  claude-index validate --repo my-project
  claude-index list
  claude-index migrate --from docker --to native
  claude-index sync --repo my-project
  claude-index diagnose
  claude-index preflight
            """
        )
        
        # Global options
        parser.add_argument(
            "--debug",
            action="store_true",
            help="Enable debug output"
        )
        parser.add_argument(
            "--quiet",
            action="store_true",
            help="Suppress non-error output"
        )
        
        # Subcommands
        subparsers = parser.add_subparsers(
            dest="command",
            help="Available commands"
        )
        
        # Create command
        create_parser = subparsers.add_parser(
            "create",
            help="Create a new index for a repository"
        )
        create_parser.add_argument(
            "--repo",
            required=True,
            help="Repository name or identifier"
        )
        create_parser.add_argument(
            "--path",
            required=True,
            help="Path to repository source code"
        )
        create_parser.add_argument(
            "--languages",
            nargs="+",
            help="Specific languages to index (default: all)"
        )
        create_parser.add_argument(
            "--exclude",
            nargs="+",
            help="Patterns to exclude from indexing"
        )
        
        # Validate command
        validate_parser = subparsers.add_parser(
            "validate",
            help="Validate an existing index"
        )
        validate_parser.add_argument(
            "--repo",
            help="Repository to validate (default: current directory)"
        )
        validate_parser.add_argument(
            "--fix",
            action="store_true",
            help="Attempt to fix validation issues"
        )
        
        # List command
        list_parser = subparsers.add_parser(
            "list",
            help="List all available indexes"
        )
        list_parser.add_argument(
            "--format",
            choices=["table", "json", "simple"],
            default="table",
            help="Output format"
        )
        list_parser.add_argument(
            "--filter",
            help="Filter by repository name pattern"
        )
        
        # Migrate command
        migrate_parser = subparsers.add_parser(
            "migrate",
            help="Migrate indexes between environments"
        )
        migrate_parser.add_argument(
            "--from",
            dest="from_env",
            required=True,
            choices=["docker", "native", "legacy"],
            help="Source environment"
        )
        migrate_parser.add_argument(
            "--to",
            dest="to_env",
            required=True,
            choices=["docker", "native", "centralized"],
            help="Target environment"
        )
        migrate_parser.add_argument(
            "--repo",
            help="Specific repository to migrate (default: all)"
        )
        
        # Sync command
        sync_parser = subparsers.add_parser(
            "sync",
            help="Sync index with repository state"
        )
        sync_parser.add_argument(
            "--repo",
            help="Repository to sync (default: current directory)"
        )
        sync_parser.add_argument(
            "--incremental",
            action="store_true",
            help="Only index changed files"
        )
        
        # Diagnose command
        diagnose_parser = subparsers.add_parser(
            "diagnose",
            help="Run MCP diagnostics"
        )
        diagnose_parser.add_argument(
            "--fix",
            action="store_true",
            help="Apply suggested fixes automatically"
        )
        
        # Preflight command
        preflight_parser = subparsers.add_parser(
            "preflight",
            help="Run pre-flight validation checks"
        )
        preflight_parser.add_argument(
            "--strict",
            action="store_true",
            help="Fail on any warning"
        )
        
        # Info command
        info_parser = subparsers.add_parser(
            "info",
            help="Show information about an index"
        )
        info_parser.add_argument(
            "--repo",
            help="Repository to inspect (default: current directory)"
        )
        
        # Clean command
        clean_parser = subparsers.add_parser(
            "clean",
            help="Clean up old or invalid indexes"
        )
        clean_parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be cleaned without doing it"
        )
        clean_parser.add_argument(
            "--older-than",
            type=int,
            help="Clean indexes older than N days"
        )
        
        return parser
        
    async def run(self, args: Optional[List[str]] = None) -> int:
        """
        Run the CLI application.
        
        Args:
            args: Command line arguments (default: sys.argv[1:])
            
        Returns:
            Exit code (0 for success, non-zero for error)
        """
        parsed_args = self.parser.parse_args(args)
        
        # Set up logging
        if parsed_args.debug:
            import logging
            logging.basicConfig(level=logging.DEBUG)
        elif parsed_args.quiet:
            import logging
            logging.basicConfig(level=logging.ERROR)
            
        # Handle commands
        if not parsed_args.command:
            self.parser.print_help()
            return 1
            
        try:
            if parsed_args.command == "create":
                return await self._handle_create(parsed_args)
            elif parsed_args.command == "validate":
                return await self._handle_validate(parsed_args)
            elif parsed_args.command == "list":
                return await self._handle_list(parsed_args)
            elif parsed_args.command == "migrate":
                return await self._handle_migrate(parsed_args)
            elif parsed_args.command == "sync":
                return await self._handle_sync(parsed_args)
            elif parsed_args.command == "diagnose":
                return await self._handle_diagnose(parsed_args)
            elif parsed_args.command == "preflight":
                return await self._handle_preflight(parsed_args)
            elif parsed_args.command == "info":
                return await self._handle_info(parsed_args)
            elif parsed_args.command == "clean":
                return await self._handle_clean(parsed_args)
            else:
                print(f"Unknown command: {parsed_args.command}")
                return 1
                
        except Exception as e:
            if parsed_args.debug:
                raise
            else:
                print(f"Error: {str(e)}", file=sys.stderr)
                return 1
                
    async def _handle_create(self, args) -> int:
        """Handle the create command."""
        command = CreateIndexCommand()
        result = await command.execute(
            repo=args.repo,
            path=args.path,
            languages=args.languages,
            exclude=args.exclude
        )
        
        if result.success:
            print(f"✅ Index created successfully for {args.repo}")
            print(f"   Location: {result.data.get('index_path')}")
            print(f"   Files indexed: {result.data.get('file_count', 0)}")
            return 0
        else:
            print(f"❌ Failed to create index: {result.error}")
            return 1
            
    async def _handle_validate(self, args) -> int:
        """Handle the validate command."""
        command = ValidateIndexCommand()
        repo = args.repo or self._get_current_repo()
        
        result = await command.execute(
            repo=repo,
            fix=args.fix
        )
        
        if result.success:
            validation = result.data
            if validation["valid"]:
                print(f"✅ Index for {repo} is valid")
                print(f"   Files: {validation.get('file_count', 0)}")
                print(f"   Symbols: {validation.get('symbol_count', 0)}")
            else:
                print(f"⚠️ Index for {repo} has issues:")
                for issue in validation.get("issues", []):
                    print(f"   - {issue}")
                if args.fix:
                    print("   Attempting fixes...")
            return 0
        else:
            print(f"❌ Validation failed: {result.error}")
            return 1
            
    async def _handle_list(self, args) -> int:
        """Handle the list command."""
        command = ListIndexesCommand()
        result = await command.execute(
            format=args.format,
            filter=args.filter
        )
        
        if not result.success:
            print(f"❌ Failed to list indexes: {result.error}")
            return 1
            
        indexes = result.data.get("indexes", [])
        
        if args.format == "json":
            print(json.dumps(indexes, indent=2))
        elif args.format == "simple":
            for idx in indexes:
                print(f"{idx['repo']} - {idx['path']}")
        else:  # table format
            if not indexes:
                print("No indexes found")
            else:
                print(f"{'Repository':<30} {'Location':<15} {'Size':<10} {'Files':<10}")
                print("-" * 70)
                for idx in indexes:
                    print(f"{idx['repo']:<30} {idx['location_type']:<15} "
                          f"{idx.get('size_mb', 0):.1f}MB{'':<6} {idx.get('file_count', 0):<10}")
                    
        return 0
        
    async def _handle_migrate(self, args) -> int:
        """Handle the migrate command."""
        command = MigrateIndexCommand()
        result = await command.execute(
            from_env=args.from_env,
            to_env=args.to_env,
            repo=args.repo
        )
        
        if result.success:
            migrated = result.data.get("migrated", [])
            failed = result.data.get("failed", [])
            
            print(f"✅ Migration complete")
            print(f"   Migrated: {len(migrated)} indexes")
            if failed:
                print(f"   Failed: {len(failed)} indexes")
                for f in failed:
                    print(f"     - {f['repo']}: {f['error']}")
            return 0 if not failed else 1
        else:
            print(f"❌ Migration failed: {result.error}")
            return 1
            
    async def _handle_sync(self, args) -> int:
        """Handle the sync command."""
        command = SyncIndexCommand()
        repo = args.repo or self._get_current_repo()
        
        result = await command.execute(
            repo=repo,
            incremental=args.incremental
        )
        
        if result.success:
            sync_data = result.data
            print(f"✅ Sync complete for {repo}")
            print(f"   Files added: {sync_data.get('files_added', 0)}")
            print(f"   Files updated: {sync_data.get('files_updated', 0)}")
            print(f"   Files removed: {sync_data.get('files_removed', 0)}")
            return 0
        else:
            print(f"❌ Sync failed: {result.error}")
            return 1
            
    async def _handle_diagnose(self, args) -> int:
        """Handle the diagnose command."""
        diagnostics = MCPDiagnostics()
        results = await diagnostics.run_diagnostics()
        
        # Print report
        diagnostics.print_report(results)
        
        # Apply fixes if requested
        if args.fix and results["suggested_fixes"]:
            print("\nApplying fixes...")
            applied = 0
            for fix in results["suggested_fixes"]:
                if self._apply_fix(fix):
                    applied += 1
                    print(f"✅ Applied: {fix['fix']}")
                else:
                    print(f"❌ Failed: {fix['fix']}")
                    
            print(f"\nApplied {applied}/{len(results['suggested_fixes'])} fixes")
            
        return 0 if not results["issues_found"] else 1
        
    async def _handle_preflight(self, args) -> int:
        """Handle the preflight command."""
        validator = PreFlightValidator()
        results = await validator.validate_all()
        
        # Print summary
        validator.print_summary(results)
        
        # Determine exit code
        if args.strict:
            return 0 if results["overall_status"] == "passed" else 1
        else:
            return 0 if results["can_proceed"] else 1
            
    async def _handle_info(self, args) -> int:
        """Handle the info command."""
        repo = args.repo or self._get_current_repo()
        discovery = IndexDiscovery(Path.cwd() if not args.repo else Path(args.repo))
        
        info = discovery.get_index_info()
        
        print(f"Index Information for {repo}")
        print("=" * 50)
        print(f"Enabled: {'Yes' if info['enabled'] else 'No'}")
        print(f"Has Index: {'Yes' if info['has_local_index'] else 'No'}")
        
        if info['has_local_index']:
            print(f"Location: {info['found_at']}")
            
            # Get detailed stats
            try:
                conn = sqlite3.connect(info['found_at'])
                file_count = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
                symbol_count = conn.execute("SELECT COUNT(*) FROM symbols").fetchone()[0]
                conn.close()
                
                print(f"Files: {file_count}")
                print(f"Symbols: {symbol_count}")
            except:
                pass
                
        if info.get('metadata'):
            print("\nMetadata:")
            for key, value in info['metadata'].items():
                print(f"  {key}: {value}")
                
        if info.get('search_paths'):
            print(f"\nSearch Paths ({len(info['search_paths'])}):")
            for i, path in enumerate(info['search_paths'][:5]):
                print(f"  {i+1}. {path}")
                
        return 0
        
    async def _handle_clean(self, args) -> int:
        """Handle the clean command."""
        # Find indexes to clean
        to_clean = []
        
        path_config = IndexPathConfig()
        for search_path in path_config.get_search_paths():
            if search_path.exists():
                for db_file in search_path.glob("**/code_index.db"):
                    # Check age if specified
                    if args.older_than:
                        age_days = (datetime.now() - datetime.fromtimestamp(db_file.stat().st_mtime)).days
                        if age_days < args.older_than:
                            continue
                            
                    # Check if valid
                    try:
                        conn = sqlite3.connect(str(db_file))
                        conn.execute("SELECT 1 FROM sqlite_master LIMIT 1")
                        conn.close()
                    except:
                        to_clean.append(db_file)
                        
        if args.dry_run:
            print(f"Would clean {len(to_clean)} indexes:")
            for path in to_clean:
                print(f"  - {path}")
        else:
            print(f"Cleaning {len(to_clean)} indexes...")
            for path in to_clean:
                try:
                    path.unlink()
                    print(f"  ✅ Removed {path}")
                except Exception as e:
                    print(f"  ❌ Failed to remove {path}: {e}")
                    
        return 0
        
    def _get_current_repo(self) -> str:
        """Get the current repository name."""
        try:
            result = subprocess.run(
                ["git", "config", "--get", "remote.origin.url"],
                capture_output=True,
                text=True,
                check=True
            )
            url = result.stdout.strip()
            # Extract repo name from URL
            if "/" in url:
                return url.split("/")[-1].replace(".git", "")
        except:
            pass
            
        # Fall back to directory name
        return Path.cwd().name
        
    def _apply_fix(self, fix: Dict[str, Any]) -> bool:
        """Apply a suggested fix."""
        try:
            for command in fix.get("commands", []):
                if command.startswith("export "):
                    # Handle environment variable
                    parts = command[7:].split("=", 1)
                    if len(parts) == 2:
                        os.environ[parts[0]] = parts[1]
                elif command.startswith("echo "):
                    # Handle file creation
                    parts = command.split(">", 1)
                    if len(parts) == 2:
                        content = parts[0].replace("echo ", "").strip().strip("'\"")
                        filename = parts[1].strip()
                        Path(filename).write_text(content)
                        
            return True
        except Exception:
            return False


def main():
    """Main entry point."""
    cli = ClaudeIndexCLI()
    exit_code = asyncio.run(cli.run())
    sys.exit(exit_code)


if __name__ == "__main__":
    main()