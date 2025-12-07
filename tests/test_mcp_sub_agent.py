"""
Tests for MCP Sub-Agent Tool Inheritance

These tests verify that sub-agents can properly inherit and use MCP tools
from their parent agents, addressing the 83% failure rate issue.
"""

import asyncio
import json
import os
from unittest.mock import MagicMock, Mock, patch

import pytest

from mcp_server.core.mcp_config_propagator import MCPConfigPropagator, MCPToolRegistryPropagator
from mcp_server.utils.sub_agent_helper import (
    SubAgentMCPHelper,
    SubAgentToolBridge,
    inherit_mcp_tools,
)


class TestMCPConfigPropagator:
    """Test MCP configuration propagation."""

    @pytest.fixture
    def sample_mcp_config(self, tmp_path):
        """Create a sample .mcp.json configuration."""
        config = {
            "mcpServers": {
                "code-index-mcp": {
                    "command": "node",
                    "args": ["/path/to/mcp-server.js"],
                    "env": {"INDEX_PATH": "/workspaces/.indexes", "LOG_LEVEL": "info"},
                }
            }
        }

        config_path = tmp_path / ".mcp.json"
        with open(config_path, "w") as f:
            json.dump(config, f)

        return config_path

    def test_config_loading(self, sample_mcp_config):
        """Test loading MCP configuration from file."""
        propagator = MCPConfigPropagator(sample_mcp_config)

        assert propagator.config is not None
        assert "mcpServers" in propagator.config
        assert "code-index-mcp" in propagator.config["mcpServers"]

    def test_environment_propagation(self, sample_mcp_config):
        """Test generation of propagation environment variables."""
        propagator = MCPConfigPropagator(sample_mcp_config)
        env_vars = propagator.get_propagation_env()

        # Check basic propagation flags
        assert env_vars["MCP_INHERIT_CONFIG"] == "true"
        assert env_vars["MCP_PROPAGATE_TOOLS"] == "true"
        assert env_vars["MCP_SUB_AGENT_ACCESS"] == "true"

        # Check server configuration propagation
        assert env_vars["MCP_SERVER_CODE-INDEX-MCP_COMMAND"] == "node"
        assert "MCP_SERVER_CODE-INDEX-MCP_ARGS" in env_vars
        assert env_vars["MCP_SERVER_CODE-INDEX-MCP_ENV_INDEX_PATH"] == "/workspaces/.indexes"

    def test_tool_registry_serialization(self):
        """Test serialization of tool registry."""
        propagator = MCPConfigPropagator()

        tools = [
            {
                "name": "symbol_lookup",
                "description": "Look up symbol definitions",
                "inputSchema": {
                    "type": "object",
                    "properties": {"symbol": {"type": "string"}},
                    "required": ["symbol"],
                },
            }
        ]

        serialized = propagator.serialize_tool_registry(tools)
        data = json.loads(serialized)

        assert data["version"] == "1.0"
        assert len(data["tools"]) == 1
        assert data["tools"][0]["name"] == "symbol_lookup"

    def test_environment_application(self, sample_mcp_config):
        """Test applying and restoring environment variables."""
        original_env = os.environ.copy()

        propagator = MCPConfigPropagator(sample_mcp_config)
        propagator.apply_to_environment()

        # Check environment was modified
        assert os.environ.get("MCP_INHERIT_CONFIG") == "true"
        assert "MCP_CONFIG_PATH" in os.environ

        # Restore environment
        propagator.restore_environment()

        # Check environment was restored
        for key, value in original_env.items():
            assert os.environ.get(key) == value

    def test_validation(self, sample_mcp_config):
        """Test configuration validation."""
        propagator = MCPConfigPropagator(sample_mcp_config)
        results = propagator.validate_propagation()

        assert results["config_found"] is True
        assert results["config_valid"] is True
        assert results["servers_configured"] is True
        assert results["env_vars_set"] is True
        assert results["inheritance_enabled"] is True


class TestSubAgentMCPHelper:
    """Test sub-agent MCP helper functionality."""

    @pytest.fixture
    def sub_agent_env(self):
        """Set up sub-agent environment."""
        original_env = os.environ.copy()

        # Set up sub-agent environment
        os.environ["MCP_SUB_AGENT_ACCESS"] = "true"
        os.environ["MCP_SERVER_CODE-INDEX-MCP_COMMAND"] = "node"
        os.environ["MCP_SERVER_CODE-INDEX-MCP_ARGS"] = '["server.js"]'
        os.environ["MCP_SERVER_CODE-INDEX-MCP_ENV_INDEX_PATH"] = "/indexes"

        # Set up tool registry
        tool_registry = {
            "version": "1.0",
            "tools": {
                "symbol_lookup": {
                    "description": "Look up symbols",
                    "inputSchema": {"required": ["symbol"]},
                },
                "search_code": {
                    "description": "Search code",
                    "inputSchema": {"required": ["query"]},
                },
            },
        }
        os.environ["MCP_TOOL_REGISTRY"] = json.dumps(tool_registry)

        yield

        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)

    def test_sub_agent_detection(self, sub_agent_env):
        """Test detection of sub-agent context."""
        helper = SubAgentMCPHelper()
        assert helper.is_sub_agent is True

    def test_inherited_config_loading(self, sub_agent_env):
        """Test loading inherited configuration from environment."""
        helper = SubAgentMCPHelper()

        assert "code-index-mcp" in helper.inherited_config["servers"]
        assert helper.inherited_config["servers"]["code-index-mcp"]["command"] == "node"

        assert "symbol_lookup" in helper.inherited_config["tools"]
        assert "search_code" in helper.inherited_config["tools"]

    @pytest.mark.asyncio
    async def test_tool_registration(self, sub_agent_env):
        """Test registration of inherited tools."""
        helper = SubAgentMCPHelper()
        tools = helper.register_inherited_tools()

        assert len(tools) == 2
        assert "symbol_lookup" in tools
        assert "search_code" in tools

        # Test tool execution
        result = await tools["symbol_lookup"](symbol="test_symbol")
        assert result["status"] == "success"
        assert result["tool"] == "symbol_lookup"

    @pytest.mark.asyncio
    async def test_tool_validation(self, sub_agent_env):
        """Test validation of required parameters."""
        helper = SubAgentMCPHelper()
        tools = helper.register_inherited_tools()

        # Should raise error for missing required parameter
        with pytest.raises(ValueError) as exc_info:
            await tools["symbol_lookup"]()

        assert "Missing required parameter: symbol" in str(exc_info.value)

    def test_tool_availability_check(self, sub_agent_env):
        """Test checking tool availability."""
        helper = SubAgentMCPHelper()
        helper.register_inherited_tools()

        availability = helper.validate_tool_availability()

        assert availability["symbol_lookup"] is True
        assert availability["search_code"] is True

        # Check for common MCP tools
        assert "mcp__code-index-mcp__symbol_lookup" in availability

    def test_mcp_server_command_retrieval(self, sub_agent_env):
        """Test retrieving MCP server command."""
        helper = SubAgentMCPHelper()

        command = helper.get_mcp_server_command("code-index-mcp")
        assert command == ["node", "server.js"]

        # Test non-existent server
        assert helper.get_mcp_server_command("non-existent") is None


class TestSubAgentToolBridge:
    """Test sub-agent tool bridge functionality."""

    @pytest.fixture
    def mock_helper(self):
        """Create a mock helper."""
        helper = Mock(spec=SubAgentMCPHelper)
        helper.get_mcp_server_command.return_value = ["node", "server.js"]
        helper.create_mcp_environment.return_value = os.environ.copy()
        return helper

    @pytest.mark.asyncio
    async def test_mcp_server_startup(self, mock_helper):
        """Test starting an MCP server."""
        bridge = SubAgentToolBridge(mock_helper)

        with patch("asyncio.create_subprocess_exec") as mock_create:
            mock_proc = MagicMock()
            mock_proc.returncode = None
            mock_create.return_value = mock_proc

            result = await bridge.ensure_mcp_server("test-server")
            assert result is True
            assert "test-server" in bridge.server_processes

    @pytest.mark.asyncio
    async def test_mcp_server_cleanup(self, mock_helper):
        """Test cleaning up MCP server processes."""
        bridge = SubAgentToolBridge(mock_helper)

        # Add a mock process
        mock_proc = MagicMock()
        mock_proc.returncode = None
        mock_proc.wait = asyncio.coroutine(lambda: None)
        bridge.server_processes["test-server"] = mock_proc

        await bridge.cleanup()

        mock_proc.terminate.assert_called_once()


class TestMCPToolRegistryPropagator:
    """Test MCP tool registry propagation."""

    def test_tool_registration(self):
        """Test registering tools in the registry."""
        propagator = MCPToolRegistryPropagator()

        tool_def = {"description": "Test tool", "inputSchema": {"type": "object"}}

        propagator.register_tool("test_tool", tool_def)
        assert "test_tool" in propagator.tool_registry

    def test_registry_serialization(self):
        """Test serializing and deserializing the tool registry."""
        propagator = MCPToolRegistryPropagator()

        propagator.register_tool("tool1", {"description": "Tool 1"})
        propagator.register_tool("tool2", {"description": "Tool 2"})

        serialized = propagator.get_serialized_registry()
        data = json.loads(serialized)

        assert data["version"] == "1.0"
        assert data["count"] == 2
        assert "tool1" in data["tools"]
        assert "tool2" in data["tools"]

        # Test deserialization
        deserialized = propagator.deserialize_registry(serialized)
        assert len(deserialized) == 2
        assert "tool1" in deserialized


class TestIntegration:
    """Integration tests for the full sub-agent flow."""

    @pytest.fixture
    def full_setup(self, tmp_path):
        """Set up a complete test environment."""
        # Create MCP config
        config = {
            "mcpServers": {
                "code-index-mcp": {
                    "command": "python",
                    "args": ["-m", "mcp_server"],
                    "env": {"INDEX_PATH": str(tmp_path / "indexes")},
                }
            }
        }

        config_path = tmp_path / ".mcp.json"
        with open(config_path, "w") as f:
            json.dump(config, f)

        return config_path

    def test_full_propagation_flow(self, full_setup):
        """Test the complete flow from parent to sub-agent."""
        # Parent agent setup
        propagator = MCPConfigPropagator(full_setup)
        tool_registry = MCPToolRegistryPropagator()

        # Register some tools
        tool_registry.register_tool(
            "symbol_lookup",
            {"description": "Look up symbol", "inputSchema": {"required": ["symbol"]}},
        )

        # Apply to environment
        propagator.apply_to_environment()
        tool_registry.apply_to_environment()

        # Sub-agent inherits tools
        helper = inherit_mcp_tools()

        assert helper is not None
        assert helper.is_sub_agent is True
        assert len(helper.tool_functions) > 0

        # Validate tools are available
        availability = helper.validate_tool_availability()
        assert availability["symbol_lookup"] is True

        # Clean up
        propagator.restore_environment()


@pytest.mark.integration
class TestRealWorldScenarios:
    """Test real-world scenarios that were failing."""

    def test_task_agent_mcp_access(self, full_setup):
        """Test the specific scenario where Task agents couldn't access MCP tools."""
        # Simulate main agent setting up environment
        propagator = MCPConfigPropagator(full_setup)
        propagator.apply_to_environment()

        # Simulate Task agent trying to access MCP
        os.environ["CLAUDE_AGENT_TYPE"] = "task"  # Simulate task agent

        helper = inherit_mcp_tools()
        assert helper is not None

        # Check that MCP tools are available
        availability = helper.validate_tool_availability()
        mcp_tools = [k for k in availability.keys() if k.startswith("mcp__")]

        assert len(mcp_tools) > 0, "No MCP tools available in Task agent"

        # Clean up
        propagator.restore_environment()
        del os.environ["CLAUDE_AGENT_TYPE"]
