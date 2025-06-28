#!/usr/bin/env python3
"""
Setup MCP environment configuration from templates.

This script generates environment-specific configuration files from templates,
ensuring proper paths for the current environment.
"""

import os
import sys
import json
import shutil
from pathlib import Path
from string import Template
import argparse
import logging

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mcp_server.core.path_utils import PathUtils

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def expand_template_vars(template_str: str, env_vars: dict) -> str:
    """
    Expand template variables in the format ${VAR:-default}.
    
    Args:
        template_str: Template string with variables
        env_vars: Dictionary of environment variables
        
    Returns:
        Expanded string
    """
    import re
    
    def replace_var(match):
        var_expr = match.group(1)
        if ":-" in var_expr:
            var_name, default = var_expr.split(":-", 1)
            return env_vars.get(var_name, default)
        else:
            return env_vars.get(var_expr, f"${{{var_expr}}}")
    
    # Match ${VAR} or ${VAR:-default}
    pattern = r'\$\{([^}]+)\}'
    return re.sub(pattern, replace_var, template_str)


def setup_mcp_config(force: bool = False):
    """
    Generate .mcp.json from template.
    
    Args:
        force: Overwrite existing config if True
    """
    template_path = project_root / ".mcp.json.template"
    config_path = project_root / ".mcp.json"
    
    if not template_path.exists():
        logger.error(f"Template not found: {template_path}")
        return False
        
    if config_path.exists() and not force:
        logger.warning(f"Config already exists: {config_path}")
        logger.info("Use --force to overwrite")
        return False
    
    # Prepare environment variables
    env_vars = {
        "MCP_WORKSPACE_ROOT": str(PathUtils.get_workspace_root()),
        "MCP_INDEX_STORAGE_PATH": str(PathUtils.get_index_storage_path()),
        "MCP_REPO_REGISTRY": str(PathUtils.get_repo_registry_path()),
        "MCP_PYTHON_PATH": PathUtils.get_python_executable(),
        "MCP_LOG_PATH": str(PathUtils.get_log_path()),
        "MCP_TEMP_PATH": str(PathUtils.get_temp_path()),
        "MCP_DATA_PATH": str(PathUtils.get_data_path()),
        "MCP_ENABLE_MULTI_REPO": os.environ.get("MCP_ENABLE_MULTI_REPO", "true"),
        "MCP_ENABLE_MULTI_PATH": os.environ.get("MCP_ENABLE_MULTI_PATH", "true"),
        "SEMANTIC_SEARCH_ENABLED": os.environ.get("SEMANTIC_SEARCH_ENABLED", "true"),
        "VOYAGE_AI_API_KEY": os.environ.get("VOYAGE_AI_API_KEY", "")
    }
    
    # Also include existing environment variables
    env_vars.update(os.environ)
    
    # Read template
    with open(template_path, 'r') as f:
        template_content = f.read()
    
    # Expand variables
    expanded_content = expand_template_vars(template_content, env_vars)
    
    # Parse to validate JSON
    try:
        config_data = json.loads(expanded_content)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON after expansion: {e}")
        logger.debug(f"Expanded content:\n{expanded_content}")
        return False
    
    # Write config
    with open(config_path, 'w') as f:
        json.dump(config_data, f, indent=2)
    
    logger.info(f"✓ Created: {config_path}")
    return True


def setup_docker_env():
    """Setup Docker-specific environment files."""
    docker_env_path = project_root / ".env.docker"
    
    env_content = f"""# Docker environment configuration
MCP_WORKSPACE_ROOT=/app
MCP_INDEX_STORAGE_PATH=PathUtils.get_workspace_root() / .indexes
MCP_REPO_REGISTRY=PathUtils.get_workspace_root() / PathUtils.get_repo_registry_path()
MCP_PYTHON_PATH=/usr/local/bin/python
MCP_LOG_PATH=PathUtils.get_log_path()
MCP_TEMP_PATH=/tmp
MCP_DATA_PATH=PathUtils.get_workspace_root() / data
MCP_ENABLE_MULTI_REPO=true
MCP_ENABLE_MULTI_PATH=true
SEMANTIC_SEARCH_ENABLED=true
"""
    
    with open(docker_env_path, 'w') as f:
        f.write(env_content)
    
    logger.info(f"✓ Created: {docker_env_path}")


def setup_native_env():
    """Setup native environment files."""
    native_env_path = project_root / ".env.native"
    
    env_content = f"""# Native environment configuration
MCP_WORKSPACE_ROOT={PathUtils.get_workspace_root()}
MCP_INDEX_STORAGE_PATH={PathUtils.get_index_storage_path()}
MCP_REPO_REGISTRY={PathUtils.get_repo_registry_path()}
MCP_PYTHON_PATH={PathUtils.get_python_executable()}
MCP_LOG_PATH={PathUtils.get_log_path()}
MCP_TEMP_PATH={PathUtils.get_temp_path()}
MCP_DATA_PATH={PathUtils.get_data_path()}
MCP_ENABLE_MULTI_REPO=true
MCP_ENABLE_MULTI_PATH=true
SEMANTIC_SEARCH_ENABLED=true
"""
    
    with open(native_env_path, 'w') as f:
        f.write(env_content)
    
    logger.info(f"✓ Created: {native_env_path}")


def create_directories():
    """Create necessary directories."""
    dirs_to_create = [
        PathUtils.get_index_storage_path(),
        PathUtils.get_log_path(),
        PathUtils.get_data_path(),
        PathUtils.get_temp_path() / "mcp-indexes"
    ]
    
    for dir_path in dirs_to_create:
        PathUtils.ensure_directory(dir_path)
        logger.info(f"✓ Directory: {dir_path}")


def show_environment_info():
    """Display current environment information."""
    logger.info("\nEnvironment Information:")
    logger.info("=" * 60)
    
    info = PathUtils.get_environment_info()
    for key, value in info.items():
        logger.info(f"{key:20}: {value}")


def main():
    """Main setup function."""
    parser = argparse.ArgumentParser(description="Setup MCP environment")
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Overwrite existing configuration"
    )
    parser.add_argument(
        "--docker",
        action="store_true",
        help="Setup Docker environment files"
    )
    parser.add_argument(
        "--native",
        action="store_true",
        help="Setup native environment files"
    )
    parser.add_argument(
        "--info",
        action="store_true",
        help="Show environment information only"
    )
    
    args = parser.parse_args()
    
    if args.info:
        show_environment_info()
        return
    
    logger.info("MCP Environment Setup")
    logger.info("=" * 60)
    
    # Create directories
    logger.info("\nCreating directories...")
    create_directories()
    
    # Setup configuration
    logger.info("\nSetting up configuration...")
    success = setup_mcp_config(force=args.force)
    
    # Setup environment files if requested
    if args.docker:
        logger.info("\nSetting up Docker environment...")
        setup_docker_env()
        
    if args.native:
        logger.info("\nSetting up native environment...")
        setup_native_env()
    
    # Show final info
    logger.info("\nSetup complete!")
    show_environment_info()
    
    if success:
        logger.info("\n✓ MCP is ready to use!")
        logger.info("\nTo use in a different environment:")
        logger.info("1. Set environment variables as needed")
        logger.info("2. Run: python scripts/setup_environment.py")
    

if __name__ == "__main__":
    main()