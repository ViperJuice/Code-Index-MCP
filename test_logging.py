#!/usr/bin/env python3
"""Test the logging and error handling infrastructure."""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_server.core import (
    get_logger, 
    MCPError, 
    PluginError, 
    IndexError, 
    ConfigError
)

def test_logging():
    """Test logging functionality."""
    logger = get_logger(__name__)
    
    print("Testing logging levels...")
    logger.debug("This is a DEBUG message")
    logger.info("This is an INFO message")
    logger.warning("This is a WARNING message")
    logger.error("This is an ERROR message")
    
    print("\nTesting logger from different module...")
    test_logger = get_logger("test.module")
    test_logger.info("Testing logger with custom name")

def test_errors():
    """Test custom error classes."""
    print("\n\nTesting error classes...")
    
    # Test MCPError
    try:
        raise MCPError("Basic MCP error")
    except MCPError as e:
        print(f"MCPError: {e}")
    
    # Test MCPError with details
    try:
        raise MCPError("MCP error with details", {"code": 500, "reason": "test"})
    except MCPError as e:
        print(f"MCPError with details: {e}")
    
    # Test PluginError
    try:
        raise PluginError("python_plugin", "Failed to parse file")
    except PluginError as e:
        print(f"PluginError: {e}")
    
    # Test IndexError
    try:
        raise IndexError("Invalid syntax", "/path/to/file.py")
    except IndexError as e:
        print(f"IndexError: {e}")
    
    # Test ConfigError
    try:
        raise ConfigError("Invalid value", "log_level")
    except ConfigError as e:
        print(f"ConfigError: {e}")

if __name__ == "__main__":
    test_logging()
    test_errors()
    
    print("\n\nCheck mcp_server.log for log output.")