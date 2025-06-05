#!/bin/bash
# Setup Code-Index-MCP for Claude Code terminal usage

echo "Setting up Code-Index-MCP for terminal Claude Code usage..."

# Option 1: Environment variable approach (if Claude Code supports it)
export MCP_SERVERS='{"code-index":{"command":"python","args":["-m","mcp_server","--transport","stdio"],"cwd":"'$(pwd)'"}}'

# Option 2: Create a launcher function
claude-mcp() {
    # Start MCP server in background
    echo "Starting Code-Index-MCP server..."
    cd /home/jenner/Code/Code-Index-MCP
    python -m mcp_server --transport stdio &
    MCP_PID=$!
    
    # Give it a moment to start
    sleep 2
    
    # Run Claude Code
    claude "$@"
    
    # Clean up MCP server when done
    kill $MCP_PID 2>/dev/null
}

# Option 3: Alias for quick access
alias claude-index='cd /home/jenner/Code/Code-Index-MCP && python -m mcp_server --transport websocket --port 8765 & claude'

echo ""
echo "Setup complete! You can now use Code-Index-MCP with Claude Code in the terminal:"
echo ""
echo "1. Source this script: source setup-claude-terminal.sh"
echo "2. Use one of these methods:"
echo "   - claude-mcp          # Launches Claude with MCP server"
echo "   - claude-index        # Quick alias"
echo ""
echo "For dev containers:"
echo "   docker run -it -v \$(pwd):/workspace ghcr.io/code-index-mcp/mcp-server:latest"