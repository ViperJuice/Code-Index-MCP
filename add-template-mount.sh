#!/bin/bash
# Quick script to add a template repository to Claude Code MCP

TEMPLATE_PATH="$1"
if [ -z "$TEMPLATE_PATH" ]; then
    echo "Usage: ./add-template-mount.sh /path/to/template-repo"
    exit 1
fi

TEMPLATE_PATH="$(realpath "$TEMPLATE_PATH")"
TEMPLATE_NAME="$(basename "$TEMPLATE_PATH")"

# Create a new MCP config with the additional mount
cat > .mcp-with-template.json <<EOF
{
  "mcpServers": {
    "code-index": {
      "command": "docker",
      "args": [
        "run", 
        "-i", 
        "--rm",
        "-v", "$(pwd):/workspace",
        "-v", "$TEMPLATE_PATH:/templates/$TEMPLATE_NAME",
        "-v", "\${HOME}/.mcp:/root/.mcp",
        "-e", "CODEX_WORKSPACE_DIR=/workspace",
        "-e", "CODEX_TEMPLATE_DIR=/templates/$TEMPLATE_NAME",
        "-e", "CODEX_LOG_LEVEL=INFO",
        "ghcr.io/code-index-mcp/mcp-server:latest",
        "python", "-m", "mcp_server", "--transport", "stdio"
      ]
    }
  }
}
EOF

echo "Created .mcp-with-template.json"
echo "Template will be available at: /templates/$TEMPLATE_NAME"
echo ""
echo "To use it:"
echo "  claude --mcp-config .mcp-with-template.json"