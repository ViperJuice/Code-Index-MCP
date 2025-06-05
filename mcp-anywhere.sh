#!/bin/bash
# MCP-Anywhere: Index any codebase from anywhere

# Get the target directory (default to current directory)
TARGET_DIR="${1:-$(pwd)}"
TARGET_DIR="$(realpath "$TARGET_DIR")"

# Create a temporary MCP config for this specific directory
cat > /tmp/mcp-dynamic-$$.json <<EOF
{
  "mcpServers": {
    "code-index": {
      "command": "docker",
      "args": [
        "run", 
        "-i", 
        "--rm",
        "-v", "$TARGET_DIR:/workspace",
        "-v", "$HOME/.mcp:/root/.mcp",
        "-e", "CODEX_WORKSPACE_DIR=/workspace",
        "-e", "CODEX_LOG_LEVEL=INFO",
        "ghcr.io/code-index-mcp/mcp-server:latest",
        "python", "-m", "mcp_server", "--transport", "stdio"
      ]
    }
  }
}
EOF

echo "Starting Claude Code with MCP indexing for: $TARGET_DIR"
echo "Inside container, files will be at: /workspace"
echo ""

# Launch Claude Code with the dynamic config
claude --mcp-config /tmp/mcp-dynamic-$$.json

# Clean up
rm -f /tmp/mcp-dynamic-$$.json