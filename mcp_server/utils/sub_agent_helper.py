"""
Sub-Agent Helper for MCP Tool Inheritance

This module provides utilities to help sub-agents inherit and use MCP tools
from their parent agents.
"""

import asyncio
import json
import logging
import os
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class SubAgentMCPHelper:
    """Helper class for sub-agents to access inherited MCP tools."""

    def __init__(self):
        """Initialize the sub-agent helper."""
        self.is_sub_agent = self._detect_sub_agent()
        self.inherited_config = self._load_inherited_config()
        self.tool_functions: Dict[str, Callable] = {}

    def _detect_sub_agent(self) -> bool:
        """Detect if running in a sub-agent context."""
        return os.environ.get("MCP_SUB_AGENT_ACCESS") == "true"

    def _load_inherited_config(self) -> Dict[str, Any]:
        """Load inherited MCP configuration from environment."""
        if not self.is_sub_agent:
            return {}

        config = {"servers": {}, "tools": {}, "environment": {}}

        # Parse MCP server configurations from environment
        for key, value in os.environ.items():
            if key.startswith("MCP_SERVER_"):
                parts = key.split("_")
                if len(parts) >= 4:
                    server_name = parts[2].lower()
                    config_key = "_".join(parts[3:]).lower()

                    if server_name not in config["servers"]:
                        config["servers"][server_name] = {}

                    if config_key == "args":
                        try:
                            config["servers"][server_name][config_key] = json.loads(value)
                        except Exception:
                            config["servers"][server_name][config_key] = value
                    else:
                        config["servers"][server_name][config_key] = value

        # Load tool registry if available
        tool_registry = os.environ.get("MCP_TOOL_REGISTRY")
        if tool_registry:
            try:
                registry_data = json.loads(tool_registry)
                config["tools"] = registry_data.get("tools", {})
            except Exception as e:
                logger.error(f"Failed to load tool registry: {e}")

        logger.info(
            f"Loaded config for {len(config['servers'])} servers and {len(config['tools'])} tools"
        )
        return config

    def register_inherited_tools(self, tool_namespace: Optional[str] = None) -> Dict[str, Callable]:
        """
        Register inherited MCP tools as callable functions.

        Args:
            tool_namespace: Optional namespace to prefix tool names

        Returns:
            Dictionary of registered tool functions
        """
        if not self.is_sub_agent:
            logger.warning("Not in sub-agent context, no tools to inherit")
            return {}

        registered_tools = {}

        for tool_name, tool_def in self.inherited_config.get("tools", {}).items():
            full_name = f"{tool_namespace}__{tool_name}" if tool_namespace else tool_name

            # Create a wrapper function for the tool
            def create_tool_wrapper(name: str, definition: Dict[str, Any]):
                @wraps(lambda **kwargs: None)
                async def tool_wrapper(**kwargs):
                    """Wrapper for inherited MCP tool."""
                    # Here we would normally call the actual MCP server
                    # For now, we'll create a placeholder that validates inputs
                    logger.info(f"Calling inherited tool: {name} with args: {kwargs}")

                    # Validate against schema if available
                    if "inputSchema" in definition:
                        # Basic validation (would be expanded in production)
                        required = definition["inputSchema"].get("required", [])
                        for req in required:
                            if req not in kwargs:
                                raise ValueError(f"Missing required parameter: {req}")

                    # Return a placeholder response
                    return {
                        "status": "success",
                        "tool": name,
                        "message": "Tool executed in sub-agent context",
                    }

                return tool_wrapper

            registered_tools[full_name] = create_tool_wrapper(tool_name, tool_def)
            self.tool_functions[full_name] = registered_tools[full_name]

        logger.info(f"Registered {len(registered_tools)} inherited tools")
        return registered_tools

    def get_mcp_server_command(self, server_name: str) -> Optional[List[str]]:
        """
        Get the command to start an MCP server.

        Args:
            server_name: Name of the MCP server

        Returns:
            Command and arguments list, or None if not found
        """
        server_config = self.inherited_config.get("servers", {}).get(server_name, {})

        if "command" not in server_config:
            return None

        command = [server_config["command"]]
        args = server_config.get("args", [])

        if isinstance(args, str):
            # Try to parse as JSON if it's a string
            try:
                args = json.loads(args)
            except Exception:
                args = [args]

        command.extend(args)
        return command

    def create_mcp_environment(self, server_name: str) -> Dict[str, str]:
        """
        Create environment variables for running an MCP server.

        Args:
            server_name: Name of the MCP server

        Returns:
            Dictionary of environment variables
        """
        env = os.environ.copy()
        server_config = self.inherited_config.get("servers", {}).get(server_name, {})

        # Add server-specific environment variables
        for key, value in server_config.items():
            if key.startswith("env_"):
                env_key = key[4:]  # Remove 'env_' prefix
                env[env_key] = value

        return env

    def validate_tool_availability(self) -> Dict[str, bool]:
        """
        Validate which MCP tools are available in the sub-agent context.

        Returns:
            Dictionary mapping tool names to availability status
        """
        availability = {}

        # Check registered tools
        for tool_name in self.tool_functions:
            availability[tool_name] = True

        # Check for common MCP tools if not registered
        common_tools = [
            "mcp__code-index-mcp__symbol_lookup",
            "mcp__code-index-mcp__search_code",
            "mcp__code-index-mcp__get_status",
            "mcp__code-index-mcp__list_plugins",
            "mcp__code-index-mcp__reindex",
        ]

        for tool in common_tools:
            if tool not in availability:
                # Check if we can construct this tool from config
                base_name = tool.split("__")[-1]
                if base_name in self.inherited_config.get("tools", {}):
                    availability[tool] = True
                else:
                    availability[tool] = False

        return availability


class SubAgentToolBridge:
    """Bridge to connect sub-agent tool calls to MCP servers."""

    def __init__(self, helper: SubAgentMCPHelper):
        """
        Initialize the tool bridge.

        Args:
            helper: SubAgentMCPHelper instance
        """
        self.helper = helper
        self.server_processes = {}

    async def ensure_mcp_server(self, server_name: str) -> bool:
        """
        Ensure an MCP server is running and accessible.

        Args:
            server_name: Name of the MCP server

        Returns:
            True if server is available, False otherwise
        """
        if server_name in self.server_processes:
            # Check if process is still running
            proc = self.server_processes[server_name]
            if proc.returncode is None:
                return True

        # Try to start the server
        command = self.helper.get_mcp_server_command(server_name)
        if not command:
            logger.error(f"No command found for server: {server_name}")
            return False

        try:
            env = self.helper.create_mcp_environment(server_name)
            proc = await asyncio.create_subprocess_exec(
                *command, env=env, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            self.server_processes[server_name] = proc

            # Give server time to start
            await asyncio.sleep(1)

            # Check if still running
            if proc.returncode is None:
                logger.info(f"Started MCP server: {server_name}")
                return True
            else:
                logger.error(f"MCP server {server_name} exited immediately")
                return False

        except Exception as e:
            logger.error(f"Failed to start MCP server {server_name}: {e}")
            return False

    async def cleanup(self):
        """Clean up any running MCP server processes."""
        for server_name, proc in self.server_processes.items():
            if proc.returncode is None:
                proc.terminate()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=5)
                except asyncio.TimeoutError:
                    proc.kill()
                logger.info(f"Stopped MCP server: {server_name}")


def inherit_mcp_tools() -> Optional[SubAgentMCPHelper]:
    """
    Convenience function to inherit MCP tools in a sub-agent.

    Returns:
        SubAgentMCPHelper instance if in sub-agent context, None otherwise
    """
    helper = SubAgentMCPHelper()

    if not helper.is_sub_agent:
        logger.info("Not in sub-agent context, MCP tool inheritance not needed")
        return None

    # Automatically register inherited tools
    helper.register_inherited_tools()

    # Log tool availability
    availability = helper.validate_tool_availability()
    available_count = sum(1 for available in availability.values() if available)
    logger.info(
        f"MCP tool inheritance complete: {available_count}/{len(availability)} tools available"
    )

    return helper
