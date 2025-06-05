#!/bin/bash
# Install MCP tools globally for easy access to any codebase

# Create a global command
sudo tee /usr/local/bin/claude-mcp-anywhere <<'EOF'
#!/bin/bash
# Launch Claude Code with MCP for any directory

TARGET_DIR="${1:-$(pwd)}"
TARGET_DIR="$(realpath "$TARGET_DIR")"

# If Code-Index-MCP is installed locally, use it
if [ -d "/home/jenner/Code/Code-Index-MCP" ]; then
    export PYTHONPATH="/home/jenner/Code/Code-Index-MCP:$PYTHONPATH"
    export CODEX_WORKSPACE_DIR="$TARGET_DIR"
    cd /home/jenner/Code/Code-Index-MCP
    exec claude --mcp-config <(cat <<JSON
{
  "mcpServers": {
    "code-index": {
      "command": "python",
      "args": ["-m", "mcp_server", "--transport", "stdio"],
      "cwd": "/home/jenner/Code/Code-Index-MCP",
      "env": {
        "CODEX_WORKSPACE_DIR": "$TARGET_DIR",
        "PYTHONPATH": "/home/jenner/Code/Code-Index-MCP"
      }
    }
  }
}
JSON
)
else
    # Use Docker
    exec claude --mcp-config <(cat <<JSON
{
  "mcpServers": {
    "code-index": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-v", "$TARGET_DIR:/workspace",
        "-v", "$HOME/.mcp:/root/.mcp",
        "-e", "CODEX_WORKSPACE_DIR=/workspace",
        "ghcr.io/code-index-mcp/mcp-server:latest",
        "python", "-m", "mcp_server", "--transport", "stdio"
      ]
    }
  }
}
JSON
)
fi
EOF

sudo chmod +x /usr/local/bin/claude-mcp-anywhere

echo "Installed! Now you can use 'claude-mcp-anywhere /path/to/any/codebase'"