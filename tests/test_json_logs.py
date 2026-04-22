"""Tests for JSON logging formatter (SL-4.1 / SL-4.2)."""

import json
import logging
import os
import sys
from io import StringIO
from unittest.mock import patch


def test_json_formatter_in_prod_mode(tmp_path):
    """JSON format when MCP_ENVIRONMENT=production."""
    from mcp_server.core.logging import JSONFormatter

    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="hello world",
        args=(),
        exc_info=None,
    )
    output = formatter.format(record)
    parsed = json.loads(output)
    assert parsed["level"] == "INFO"
    assert parsed["name"] == "test.logger"
    assert parsed["message"] == "hello world"
    assert "timestamp" in parsed


def test_setup_logging_uses_json_in_production(tmp_path):
    """setup_logging installs JSONFormatter when MCP_ENVIRONMENT=production."""
    log_file = str(tmp_path / "test.log")
    stream = StringIO()

    with patch.dict(
        os.environ, {"MCP_ENVIRONMENT": "production", "MCP_LOG_FORMAT": ""}, clear=False
    ):
        # Reset root logger handlers to isolate this test
        root = logging.getLogger()
        original_handlers = root.handlers[:]
        root.handlers.clear()

        handler = logging.StreamHandler(stream)
        root.addHandler(handler)

        import importlib

        from mcp_server.core import logging as mcp_logging

        importlib.reload(mcp_logging)
        from mcp_server.core.logging import JSONFormatter, setup_logging

        setup_logging(log_level="INFO", log_file=log_file)

        # Check that at least one handler uses JSONFormatter
        json_used = any(
            isinstance(h.formatter, JSONFormatter) for h in logging.getLogger().handlers
        )
        assert json_used, "JSONFormatter not found in production mode handlers"

        # Restore
        root.handlers = original_handlers


def test_setup_logging_uses_json_format_env_var(tmp_path):
    """setup_logging installs JSONFormatter when MCP_LOG_FORMAT=json."""
    log_file = str(tmp_path / "test.log")

    with patch.dict(
        os.environ, {"MCP_ENVIRONMENT": "development", "MCP_LOG_FORMAT": "json"}, clear=False
    ):
        import importlib

        import mcp_server.core.logging as mcp_logging
        from mcp_server.core.logging import JSONFormatter, setup_logging

        importlib.reload(mcp_logging)
        from mcp_server.core.logging import JSONFormatter, setup_logging

        root = logging.getLogger()
        original_handlers = root.handlers[:]
        root.handlers.clear()

        setup_logging(log_level="INFO", log_file=log_file)

        json_used = any(
            isinstance(h.formatter, JSONFormatter) for h in logging.getLogger().handlers
        )
        assert json_used, "JSONFormatter not found when MCP_LOG_FORMAT=json"

        root.handlers = original_handlers


def test_setup_logging_plain_text_in_dev(tmp_path):
    """setup_logging uses plain-text formatter in development (default)."""
    log_file = str(tmp_path / "test.log")

    env = {k: v for k, v in os.environ.items()}
    env.pop("MCP_ENVIRONMENT", None)
    env.pop("NODE_ENV", None)
    env.pop("ENVIRONMENT", None)
    env.pop("ENV", None)
    env.pop("MCP_LOG_FORMAT", None)

    with patch.dict(os.environ, env, clear=True):
        import importlib

        import mcp_server.core.logging as mcp_logging
        from mcp_server.core.logging import JSONFormatter, setup_logging

        importlib.reload(mcp_logging)
        from mcp_server.core.logging import JSONFormatter, setup_logging

        root = logging.getLogger()
        original_handlers = root.handlers[:]
        root.handlers.clear()

        setup_logging(log_level="INFO", log_file=log_file)

        json_used = any(
            isinstance(h.formatter, JSONFormatter) for h in logging.getLogger().handlers
        )
        assert not json_used, "JSONFormatter should NOT be used in development mode"

        root.handlers = original_handlers


def test_json_formatter_output_is_valid_json():
    """JSONFormatter.format() returns valid JSON string."""
    from mcp_server.core.logging import JSONFormatter

    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="my.module",
        level=logging.ERROR,
        pathname="",
        lineno=42,
        msg="something failed",
        args=(),
        exc_info=None,
    )
    output = formatter.format(record)
    parsed = json.loads(output)
    assert parsed["message"] == "something failed"
    assert parsed["level"] == "ERROR"
    assert parsed["name"] == "my.module"
