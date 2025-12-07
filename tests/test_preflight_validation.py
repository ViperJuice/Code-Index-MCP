"""
Tests for Pre-Flight Validation System

These tests verify that the pre-flight validation correctly identifies
MCP configuration issues before operations begin.
"""

import json
import os
import sqlite3
from unittest.mock import AsyncMock, patch

import pytest

from mcp_server.core.preflight_validator import MCPHealthCheck, PreFlightValidator
from mcp_server.utils.mcp_health_check import MCPDiagnostics, quick_mcp_check


class TestPreFlightValidator:
    """Test pre-flight validation functionality."""

    @pytest.fixture
    def validator(self):
        """Create a validator instance."""
        return PreFlightValidator()

    @pytest.fixture
    def mock_environment(self):
        """Set up mock environment variables."""
        original_env = os.environ.copy()

        # Set up test environment
        os.environ["MCP_INHERIT_CONFIG"] = "true"
        os.environ["MCP_PROPAGATE_TOOLS"] = "true"
        os.environ["MCP_SUB_AGENT_ACCESS"] = "false"

        yield

        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)

    @pytest.mark.asyncio
    async def test_validate_all(self, validator, mock_environment):
        """Test running all validation checks."""
        with patch.multiple(
            validator,
            _validate_mcp_tools=AsyncMock(return_value={"status": "passed", "critical": True}),
            _validate_index_availability=AsyncMock(
                return_value={"status": "passed", "critical": True}
            ),
            _validate_configuration=AsyncMock(return_value={"status": "passed", "critical": False}),
            _validate_environment=AsyncMock(return_value={"status": "passed", "critical": False}),
            _validate_dependencies=AsyncMock(return_value={"status": "passed", "critical": False}),
            _validate_permissions=AsyncMock(return_value={"status": "passed", "critical": False}),
        ):
            results = await validator.validate_all()

            assert results["overall_status"] == "passed"
            assert results["can_proceed"] is True
            assert len(results["checks"]) == 6
            assert results["duration_ms"] > 0

    @pytest.mark.asyncio
    async def test_validate_mcp_tools_success(self, validator, mock_environment):
        """Test successful MCP tools validation."""
        # Set up tool registry
        tool_registry = {"version": "1.0", "tools": {"symbol_lookup": {}, "search_code": {}}}
        os.environ["MCP_TOOL_REGISTRY"] = json.dumps(tool_registry)

        result = await validator._validate_mcp_tools()

        assert result["status"] == "passed"
        assert result["critical"] is True
        assert result["details"]["tool_count"] >= 0
        assert result["details"]["inheritance_enabled"] is True

    @pytest.mark.asyncio
    async def test_validate_mcp_tools_sub_agent_failure(self, validator):
        """Test MCP tools validation failure in sub-agent."""
        os.environ["MCP_SUB_AGENT_ACCESS"] = "true"
        os.environ["MCP_INHERIT_CONFIG"] = "false"

        result = await validator._validate_mcp_tools()

        assert result["status"] == "failed"
        assert "Sub-agent detected but inheritance not enabled" in result["issues"]

    @pytest.mark.asyncio
    async def test_validate_index_availability(self, validator, tmp_path):
        """Test index availability validation."""
        # Create test index
        index_dir = tmp_path / ".mcp-index"
        index_dir.mkdir()
        index_path = index_dir / "code_index.db"

        # Create valid SQLite database
        conn = sqlite3.connect(str(index_path))
        conn.execute("CREATE TABLE files (id INTEGER PRIMARY KEY, path TEXT)")
        conn.execute("INSERT INTO files (path) VALUES ('test.py')")
        conn.commit()
        conn.close()

        # Create config
        config_file = tmp_path / ".mcp-index.json"
        config_file.write_text(json.dumps({"enabled": True}))

        with patch("mcp_server.utils.index_discovery.Path.cwd", return_value=tmp_path):
            result = await validator._validate_index_availability()

        assert result["status"] == "passed"
        assert result["details"]["index_enabled"] is True
        assert result["details"]["has_index"] is True
        assert result["details"]["file_count"] == 1

    @pytest.mark.asyncio
    async def test_validate_configuration(self, validator, tmp_path):
        """Test configuration validation."""
        # Create valid .mcp.json
        config = {
            "mcpServers": {
                "code-index-mcp": {
                    "command": "node",
                    "args": ["server.js"],
                    "inherit_env": True,
                    "sub_agent_access": True,
                }
            }
        }

        config_file = tmp_path / ".mcp.json"
        config_file.write_text(json.dumps(config))

        with patch("pathlib.Path.cwd", return_value=tmp_path):
            result = await validator._validate_configuration()

        assert result["status"] == "passed"
        assert "code-index-mcp" in result["details"]["servers"]
        assert not result["issues"]

    @pytest.mark.asyncio
    async def test_validate_environment(self, validator):
        """Test environment validation."""
        result = await validator._validate_environment()

        assert result["status"] == "passed"
        assert "python_version" in result["details"]
        assert "environment_type" in result["details"]

    @pytest.mark.asyncio
    async def test_validate_dependencies(self, validator):
        """Test dependencies validation."""
        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            # Mock successful command execution
            mock_proc = AsyncMock()
            mock_proc.returncode = 0
            mock_subprocess.return_value = mock_proc

            result = await validator._validate_dependencies()

            assert result["status"] in ["passed", "warning"]
            assert "git_available" in result["details"]

    @pytest.mark.asyncio
    async def test_critical_failure_blocks_proceed(self, validator):
        """Test that critical failures prevent proceeding."""
        with patch.multiple(
            validator,
            _validate_mcp_tools=AsyncMock(
                return_value={
                    "status": "failed",
                    "critical": True,
                    "issues": ["No MCP tools found"],
                }
            ),
            _validate_index_availability=AsyncMock(
                return_value={"status": "passed", "critical": True}
            ),
            _validate_configuration=AsyncMock(return_value={"status": "passed", "critical": False}),
            _validate_environment=AsyncMock(return_value={"status": "passed", "critical": False}),
            _validate_dependencies=AsyncMock(return_value={"status": "passed", "critical": False}),
            _validate_permissions=AsyncMock(return_value={"status": "passed", "critical": False}),
        ):
            results = await validator.validate_all()

            assert results["overall_status"] == "failed"
            assert results["can_proceed"] is False

    def test_generate_recommendations(self, validator):
        """Test recommendation generation."""
        checks = {
            "mcp_tools": {
                "status": "failed",
                "details": {"is_sub_agent": True},
                "issues": ["Sub-agent detected but inheritance not enabled"],
            },
            "index_availability": {
                "status": "failed",
                "details": {"index_enabled": False},
                "issues": ["MCP indexing not enabled"],
            },
        }

        recommendations = validator._generate_recommendations(checks)

        assert len(recommendations) >= 2
        assert any("MCP_INHERIT_CONFIG=true" in r for r in recommendations)
        assert any(".mcp-index.json" in r for r in recommendations)


class TestMCPHealthCheck:
    """Test MCP health check functionality."""

    @pytest.mark.asyncio
    async def test_check_mcp_available_success(self):
        """Test successful MCP availability check."""
        os.environ["MCP_SERVER_TEST_COMMAND"] = "test"

        available, message = await MCPHealthCheck.check_mcp_available()

        assert available is True
        assert "MCP servers configured" in message

        del os.environ["MCP_SERVER_TEST_COMMAND"]

    @pytest.mark.asyncio
    async def test_check_mcp_available_sub_agent_failure(self):
        """Test MCP availability check failure in sub-agent."""
        os.environ["MCP_SUB_AGENT_ACCESS"] = "true"
        os.environ["MCP_INHERIT_CONFIG"] = "false"

        available, message = await MCPHealthCheck.check_mcp_available()

        assert available is False
        assert "inheritance not enabled" in message

        del os.environ["MCP_SUB_AGENT_ACCESS"]
        del os.environ["MCP_INHERIT_CONFIG"]

    @pytest.mark.asyncio
    async def test_check_index_available(self, tmp_path):
        """Test index availability check."""
        # Create test index
        index_dir = tmp_path / ".mcp-index"
        index_dir.mkdir()
        index_path = index_dir / "code_index.db"
        index_path.touch()

        # Create config
        config_file = tmp_path / ".mcp-index.json"
        config_file.write_text(json.dumps({"enabled": True}))

        with patch("mcp_server.utils.index_discovery.Path.cwd", return_value=tmp_path):
            available, message = await MCPHealthCheck.check_index_available()

        assert available is True
        assert "Index available" in message


class TestMCPDiagnostics:
    """Test MCP diagnostics functionality."""

    @pytest.fixture
    def diagnostics(self):
        """Create diagnostics instance."""
        return MCPDiagnostics()

    @pytest.mark.asyncio
    async def test_run_diagnostics(self, diagnostics):
        """Test running full diagnostics."""
        with patch.multiple(
            diagnostics,
            _diagnose_tool_availability=AsyncMock(return_value={"status": "ok", "issues": []}),
            _diagnose_configuration=AsyncMock(return_value={"status": "ok", "issues": []}),
            _diagnose_index_access=AsyncMock(return_value={"status": "ok", "issues": []}),
            _diagnose_sub_agent_setup=AsyncMock(return_value={"status": "ok", "issues": []}),
            _diagnose_environment=AsyncMock(return_value={"status": "ok", "issues": []}),
        ):
            results = await diagnostics.run_diagnostics()

            assert "timestamp" in results
            assert len(results["diagnostics"]) == 5
            assert results["issues_found"] == []

    @pytest.mark.asyncio
    async def test_diagnose_tool_availability(self, diagnostics):
        """Test tool availability diagnosis."""
        os.environ["MCP_INHERIT_CONFIG"] = "true"
        os.environ["MCP_SERVER_TEST_COMMAND"] = "test"

        result = await diagnostics._diagnose_tool_availability()

        assert result["status"] == "ok"
        assert result["details"]["mcp_env_vars"] > 0
        assert len(result["details"]["server_commands"]) > 0

        del os.environ["MCP_INHERIT_CONFIG"]
        del os.environ["MCP_SERVER_TEST_COMMAND"]

    @pytest.mark.asyncio
    async def test_diagnose_configuration_missing(self, diagnostics):
        """Test configuration diagnosis with missing config."""
        with patch("pathlib.Path.exists", return_value=False):
            result = await diagnostics._diagnose_configuration()

        assert result["status"] == "issues_found"
        assert "No .mcp.json configuration file found" in result["issues"]

    @pytest.mark.asyncio
    async def test_generate_fixes(self, diagnostics):
        """Test fix generation."""
        diagnostics_results = {
            "tool_availability": {
                "issues": ["Sub-agent detected but config propagation not enabled"]
            },
            "configuration": {"issues": ["No .mcp.json configuration file found"]},
            "index_access": {"issues": ["MCP indexing not enabled"]},
        }

        fixes = diagnostics._generate_fixes(diagnostics_results)

        assert len(fixes) >= 3
        assert any("MCP_INHERIT_CONFIG=true" in str(fix["commands"]) for fix in fixes)
        assert any(".mcp.json" in fix["fix"] for fix in fixes)
        assert any(".mcp-index.json" in str(fix["commands"]) for fix in fixes)


class TestQuickCheck:
    """Test quick check functionality."""

    @pytest.mark.asyncio
    async def test_quick_mcp_check_success(self):
        """Test successful quick MCP check."""
        os.environ["MCP_TOOL_REGISTRY"] = json.dumps({"tools": {}})

        result = await quick_mcp_check()
        assert result is True

        del os.environ["MCP_TOOL_REGISTRY"]

    @pytest.mark.asyncio
    async def test_quick_mcp_check_sub_agent(self):
        """Test quick MCP check for sub-agent."""
        os.environ["MCP_SUB_AGENT_ACCESS"] = "true"
        os.environ["MCP_INHERIT_CONFIG"] = "true"

        result = await quick_mcp_check()
        assert result is True

        os.environ["MCP_INHERIT_CONFIG"] = "false"
        result = await quick_mcp_check()
        assert result is False

        del os.environ["MCP_SUB_AGENT_ACCESS"]
        del os.environ["MCP_INHERIT_CONFIG"]


class TestIntegration:
    """Integration tests for pre-flight validation."""

    @pytest.mark.asyncio
    async def test_full_validation_flow(self, tmp_path):
        """Test complete validation flow."""
        # Set up environment
        os.environ["MCP_INHERIT_CONFIG"] = "true"
        os.environ["MCP_PROPAGATE_TOOLS"] = "true"

        # Create config files
        mcp_config = {
            "mcpServers": {
                "code-index-mcp": {"command": "node", "inherit_env": True, "sub_agent_access": True}
            }
        }

        config_file = tmp_path / ".mcp.json"
        config_file.write_text(json.dumps(mcp_config))

        index_config = tmp_path / ".mcp-index.json"
        index_config.write_text(json.dumps({"enabled": True}))

        # Create index
        index_dir = tmp_path / ".mcp-index"
        index_dir.mkdir()
        index_path = index_dir / "code_index.db"

        conn = sqlite3.connect(str(index_path))
        conn.execute("CREATE TABLE files (id INTEGER PRIMARY KEY)")
        conn.close()

        # Run validation
        with patch("pathlib.Path.cwd", return_value=tmp_path):
            validator = PreFlightValidator()
            results = await validator.validate_all()

        # Should have warnings but can proceed
        assert results["can_proceed"] is True
        assert len(results["recommendations"]) >= 0

        # Clean up
        del os.environ["MCP_INHERIT_CONFIG"]
        del os.environ["MCP_PROPAGATE_TOOLS"]
