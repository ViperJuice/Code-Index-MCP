#!/usr/bin/env python3
"""
Startup check module for MCP server.
Provides clear error messages for missing dependencies or configuration issues.
"""

import sys
import os
import subprocess
import json
from pathlib import Path


class StartupChecker:
    """Check system requirements and provide helpful error messages."""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.info = []
    
    def check_python_version(self):
        """Check Python version is 3.8+"""
        version = sys.version_info
        if version < (3, 8):
            self.errors.append(
                f"Python 3.8+ required, but found {version.major}.{version.minor}.{version.micro}\n"
                f"  Please upgrade Python: https://www.python.org/downloads/"
            )
        else:
            self.info.append(f"✓ Python version: {version.major}.{version.minor}.{version.micro}")
    
    def check_dependencies(self):
        """Check if required Python packages are installed."""
        required_packages = [
            ("tree_sitter", "tree-sitter", "Code parsing"),
            ("click", "click", "CLI interface"),
            ("aiohttp", "aiohttp", "WebSocket transport"),
            ("watchdog", "watchdog", "File monitoring"),
        ]
        
        for module_name, package_name, description in required_packages:
            try:
                __import__(module_name)
                self.info.append(f"✓ {description} ({package_name})")
            except ImportError:
                self.errors.append(
                    f"Missing dependency: {package_name} ({description})\n"
                    f"  Install with: pip install {package_name}\n"
                    f"  Or install all: pip install -r requirements.txt"
                )
    
    def check_docker(self):
        """Check if Docker is available (for Docker mode)."""
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                self.info.append(f"✓ Docker available: {version}")
            else:
                self.warnings.append(
                    "Docker not available (needed for Docker mode)\n"
                    "  Install Docker: https://docs.docker.com/get-docker/"
                )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self.warnings.append(
                "Docker not found (needed for Docker mode)\n"
                "  Install Docker: https://docs.docker.com/get-docker/\n"
                "  Or use local Python mode instead"
            )
    
    def check_workspace(self):
        """Check if workspace directory is accessible."""
        workspace = os.environ.get("CODEX_WORKSPACE_DIR", os.getcwd())
        workspace_path = Path(workspace)
        
        if workspace_path.exists() and workspace_path.is_dir():
            file_count = sum(1 for _ in workspace_path.rglob("*") if _.is_file())
            self.info.append(f"✓ Workspace directory: {workspace} ({file_count} files)")
        else:
            self.errors.append(
                f"Workspace directory not found: {workspace}\n"
                f"  Set CODEX_WORKSPACE_DIR environment variable\n"
                f"  Or ensure the path exists"
            )
    
    def check_database(self):
        """Check if database is accessible."""
        db_path = Path("code_index.db")
        if db_path.exists():
            size_mb = db_path.stat().st_size / (1024 * 1024)
            self.info.append(f"✓ Database exists: {db_path} ({size_mb:.1f} MB)")
        else:
            self.info.append("✓ Database will be created on first run")
    
    def check_mcp_config(self):
        """Check MCP configuration if running through MCP client."""
        config_files = [".mcp.json", "mcp-config.json"]
        found_config = None
        
        for config_file in config_files:
            if Path(config_file).exists():
                found_config = config_file
                break
        
        if found_config:
            try:
                with open(found_config) as f:
                    config = json.load(f)
                    if "mcpServers" in config and "code-index" in config["mcpServers"]:
                        self.info.append(f"✓ MCP configuration found: {found_config}")
                    else:
                        self.warnings.append(
                            f"MCP configuration incomplete: {found_config}\n"
                            f"  Missing 'code-index' server configuration"
                        )
            except json.JSONDecodeError:
                self.errors.append(f"Invalid JSON in {found_config}")
        else:
            self.info.append("ℹ No MCP configuration file (OK for direct usage)")
    
    def format_report(self):
        """Format the startup check report."""
        lines = []
        
        lines.append("\n=== MCP Server Startup Check ===\n")
        
        if self.info:
            lines.append("✅ System Information:")
            for msg in self.info:
                lines.append(f"  {msg}")
            lines.append("")
        
        if self.warnings:
            lines.append("⚠️  Warnings:")
            for msg in self.warnings:
                lines.append(f"  {msg}")
            lines.append("")
        
        if self.errors:
            lines.append("❌ Errors Found:")
            for msg in self.errors:
                lines.append(f"  {msg}")
            lines.append("")
            lines.append("Please fix the errors above before starting the server.")
        else:
            lines.append("✅ All checks passed! Server ready to start.")
        
        return "\n".join(lines)
    
    def run_checks(self):
        """Run all startup checks."""
        self.check_python_version()
        self.check_dependencies()
        self.check_docker()
        self.check_workspace()
        self.check_database()
        self.check_mcp_config()
        
        return len(self.errors) == 0


def check_startup():
    """Run startup checks and return success status."""
    checker = StartupChecker()
    success = checker.run_checks()
    
    # Always print to stderr for MCP compatibility
    print(checker.format_report(), file=sys.stderr)
    
    if not success:
        # Return error in MCP-compatible format if running in MCP mode
        if os.environ.get("MCP_MODE"):
            error_response = {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": "Server startup failed",
                    "data": {
                        "errors": checker.errors,
                        "report": checker.format_report()
                    }
                },
                "id": None
            }
            print(json.dumps(error_response))
        sys.exit(1)
    
    return success


if __name__ == "__main__":
    check_startup()