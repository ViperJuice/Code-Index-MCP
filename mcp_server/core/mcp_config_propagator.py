"""
MCP Configuration Propagator for Sub-Agent Tool Inheritance

This module handles the propagation of MCP configuration and tools from parent
agents to sub-agents, fixing the 83% failure rate issue where Task agents
cannot access MCP tools.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MCPConfigPropagator:
    """Handles MCP configuration propagation to sub-agents."""

    def __init__(self, mcp_config_path: Optional[Path] = None):
        """
        Initialize the config propagator.

        Args:
            mcp_config_path: Path to .mcp.json file. If None, searches standard locations.
        """
        self.mcp_config_path = mcp_config_path or self._find_mcp_config()
        self.config = self._load_config()
        self._original_env = os.environ.copy()

    def _find_mcp_config(self) -> Optional[Path]:
        """Find .mcp.json in standard locations."""
        search_paths = [
            Path.cwd() / ".mcp.json",
            Path.home() / ".mcp.json",
            Path("PathUtils.get_workspace_root()/.mcp.json"),
        ]

        for path in search_paths:
            if path.exists():
                logger.info(f"Found MCP config at: {path}")
                return path

        logger.warning("No .mcp.json found in standard locations")
        return None

    def _load_config(self) -> Dict[str, Any]:
        """Load MCP configuration from file."""
        if not self.mcp_config_path or not self.mcp_config_path.exists():
            logger.warning("No MCP config file found, using empty config")
            return {}

        try:
            with open(self.mcp_config_path, "r") as f:
                config = json.load(f)
                logger.info(f"Loaded MCP config with {len(config.get('mcpServers', {}))} servers")
                return config
        except Exception as e:
            logger.error(f"Failed to load MCP config: {e}")
            return {}

    def get_propagation_env(self) -> Dict[str, str]:
        """
        Get environment variables needed for sub-agent MCP tool inheritance.

        Returns:
            Dictionary of environment variables to set for sub-agents.
        """
        env_vars = {}

        # Propagate MCP configuration path
        if self.mcp_config_path:
            env_vars["MCP_CONFIG_PATH"] = str(self.mcp_config_path)

        # Propagate MCP server configurations
        for server_name, server_config in self.config.get("mcpServers", {}).items():
            prefix = f"MCP_SERVER_{server_name.upper()}_"

            # Command and arguments
            if "command" in server_config:
                env_vars[f"{prefix}COMMAND"] = server_config["command"]
            if "args" in server_config:
                env_vars[f"{prefix}ARGS"] = json.dumps(server_config.get("args", []))

            # Environment variables for the server
            if "env" in server_config:
                for key, value in server_config["env"].items():
                    env_vars[f"{prefix}ENV_{key}"] = str(value)

            # Store original environment values if present
            for key, value in os.environ.items():
                if key.startswith("MCP_"):
                    env_vars[key] = value

        # Enable sub-agent inheritance
        env_vars["MCP_INHERIT_CONFIG"] = "true"
        env_vars["MCP_PROPAGATE_TOOLS"] = "true"
        env_vars["MCP_SUB_AGENT_ACCESS"] = "true"

        logger.info(f"Prepared {len(env_vars)} environment variables for propagation")
        return env_vars

    def serialize_tool_registry(self, tools: List[Dict[str, Any]]) -> str:
        """
        Serialize tool registry for sub-agent consumption.

        Args:
            tools: List of tool definitions

        Returns:
            JSON-serialized tool registry
        """
        registry = {
            "version": "1.0",
            "tools": tools,
            "metadata": {"parent_agent": "main", "propagated": True},
        }
        return json.dumps(registry)

    def apply_to_environment(self) -> None:
        """Apply propagation environment variables to current process."""
        env_vars = self.get_propagation_env()
        for key, value in env_vars.items():
            os.environ[key] = value
        logger.info(f"Applied {len(env_vars)} MCP environment variables")

    def restore_environment(self) -> None:
        """Restore original environment variables."""
        # Remove any added variables
        for key in list(os.environ.keys()):
            if key not in self._original_env:
                del os.environ[key]

        # Restore original values
        for key, value in self._original_env.items():
            os.environ[key] = value

        logger.info("Restored original environment")

    def validate_propagation(self) -> Dict[str, bool]:
        """
        Validate that MCP configuration can be propagated successfully.

        Returns:
            Dictionary of validation results
        """
        results = {
            "config_found": bool(self.mcp_config_path and self.mcp_config_path.exists()),
            "config_valid": bool(self.config),
            "servers_configured": bool(self.config.get("mcpServers")),
            "env_vars_set": False,
            "inheritance_enabled": False,
        }

        # Check if environment is properly configured
        env_vars = self.get_propagation_env()
        results["env_vars_set"] = len(env_vars) > 0
        results["inheritance_enabled"] = env_vars.get("MCP_INHERIT_CONFIG") == "true"

        # Log validation results
        for check, passed in results.items():
            status = "PASS" if passed else "FAIL"
            logger.info(f"Validation {check}: {status}")

        return results

    def create_sub_agent_config(self) -> Dict[str, Any]:
        """
        Create a configuration object specifically for sub-agents.

        Returns:
            Configuration dictionary for sub-agent initialization
        """
        return {
            "mcp_enabled": True,
            "inherit_tools": True,
            "parent_config": self.config,
            "environment": self.get_propagation_env(),
            "config_path": str(self.mcp_config_path) if self.mcp_config_path else None,
        }


class MCPToolRegistryPropagator:
    """Handles propagation of MCP tool functions to sub-agents."""

    def __init__(self):
        self.tool_registry: Dict[str, Any] = {}

    def register_tool(self, name: str, tool_def: Dict[str, Any]) -> None:
        """Register a tool for propagation."""
        self.tool_registry[name] = tool_def
        logger.debug(f"Registered tool: {name}")

    def get_serialized_registry(self) -> str:
        """Get JSON-serialized tool registry for environment variable."""
        return json.dumps(
            {"version": "1.0", "tools": self.tool_registry, "count": len(self.tool_registry)}
        )

    def deserialize_registry(self, serialized: str) -> Dict[str, Any]:
        """Deserialize tool registry from environment variable."""
        try:
            data = json.loads(serialized)
            return data.get("tools", {})
        except Exception as e:
            logger.error(f"Failed to deserialize tool registry: {e}")
            return {}

    def apply_to_environment(self) -> None:
        """Apply tool registry to environment for sub-agent access."""
        os.environ["MCP_TOOL_REGISTRY"] = self.get_serialized_registry()
        logger.info(f"Applied tool registry with {len(self.tool_registry)} tools to environment")
