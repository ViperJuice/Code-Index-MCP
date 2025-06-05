"""
Simple settings for MCP server.
"""

import os
from pathlib import Path

# Base paths
PROJECT_ROOT = Path(__file__).parent.parent
WORKSPACE_DIR = Path(os.getenv("CODEX_WORKSPACE_DIR", os.getcwd()))

# Database
DB_PATH = PROJECT_ROOT / "code_index.db"
DB_URL = f"sqlite:///{DB_PATH}"

# Server settings
MCP_HOST = os.getenv("MCP_HOST", "localhost")
MCP_PORT = int(os.getenv("MCP_PORT", "8765"))

# Logging
LOG_LEVEL = os.getenv("CODEX_LOG_LEVEL", "INFO")

# File watching
WATCH_ENABLED = os.getenv("CODEX_WATCH_ENABLED", "true").lower() == "true"
WATCH_DEBOUNCE_SECONDS = float(os.getenv("CODEX_WATCH_DEBOUNCE", "1.0"))

# Indexing
MAX_FILE_SIZE = int(os.getenv("CODEX_MAX_FILE_SIZE", str(10 * 1024 * 1024)))  # 10MB
EXCLUDED_DIRS = {
    ".git", ".svn", ".hg", ".bzr", "_darcs",
    "node_modules", "__pycache__", ".pytest_cache",
    ".tox", ".eggs", "*.egg-info", ".mypy_cache",
    "venv", "env", ".venv", ".env",
    "build", "dist", "target", "out",
    ".idea", ".vscode", ".vs"
}

# Plugin settings
PLUGIN_DIR = PROJECT_ROOT / "plugins"
ENABLE_PLUGINS = os.getenv("CODEX_ENABLE_PLUGINS", "true").lower() == "true"

# Performance
BATCH_SIZE = int(os.getenv("CODEX_BATCH_SIZE", "100"))
CACHE_SIZE = int(os.getenv("CODEX_CACHE_SIZE", "1000"))

# MCP specific
MCP_PROTOCOL_VERSION = "2024-11-05"
MCP_SERVER_NAME = "code-index-mcp"
MCP_SERVER_VERSION = "1.0.0"

# Transport settings
WEBSOCKET_MAX_SIZE = int(os.getenv("MCP_WEBSOCKET_MAX_SIZE", str(10 * 1024 * 1024)))  # 10MB
WEBSOCKET_PING_INTERVAL = int(os.getenv("MCP_WEBSOCKET_PING_INTERVAL", "30"))
WEBSOCKET_PING_TIMEOUT = int(os.getenv("MCP_WEBSOCKET_PING_TIMEOUT", "10"))


class Settings:
    """Simple settings class for compatibility."""
    
    def __init__(self):
        self.workspace_dir = WORKSPACE_DIR
        self.db_path = DB_PATH
        self.mcp_host = MCP_HOST
        self.mcp_port = MCP_PORT
        self.log_level = LOG_LEVEL
        self.watch_enabled = WATCH_ENABLED
        self.plugin_dir = PLUGIN_DIR
        self.enable_plugins = ENABLE_PLUGINS


# Create a default instance
settings = Settings()