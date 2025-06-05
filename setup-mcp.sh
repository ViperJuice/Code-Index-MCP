#!/bin/bash
set -e

echo "🚀 Setting up Code-Index-MCP for Claude Code..."

# Check if we're in the right directory
if [ ! -f "mcp_server/__init__.py" ]; then
    echo "❌ Error: Please run this script from the Code-Index-MCP directory"
    exit 1
fi

# Check if Claude Code is available
if ! command -v claude-code >/dev/null 2>&1; then
    echo "ℹ️  Claude Code not found in PATH, but that's okay - you can still use the MCP server"
fi

# Check Docker availability
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    echo "✅ Docker detected - will use containerized version"
    
    # Build image if it doesn't exist
    if ! docker image inspect code-index-mcp:latest >/dev/null 2>&1; then
        echo "🐳 Building Docker image..."
        docker build -t code-index-mcp:latest .
        echo "✅ Docker image built successfully"
    else
        echo "✅ Docker image already exists"
    fi
else
    echo "⚠️  Docker not available - will use local Python version"
    
    # Check Python dependencies
    if ! python -c "import mcp_server" 2>/dev/null; then
        echo "📦 Installing Python dependencies..."
        pip install -r requirements.txt
        pip install -e .
        echo "✅ Python dependencies installed"
    else
        echo "✅ Python dependencies already installed"
    fi
fi

# Verify the MCP server works
echo "🧪 Testing MCP server..."
if timeout 3 ./mcp-with-fallback --help >/dev/null 2>&1; then
    echo "✅ MCP server test successful"
else
    echo "❌ MCP server test failed"
    exit 1
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Restart Claude Code to pick up the MCP configuration"
echo "2. Look for 'code-index' in Claude Code's MCP servers"
echo "3. Try asking Claude: 'Search for main functions in this codebase'"
echo ""
echo "🔧 Configuration file: .mcp.json"
echo "🐳 Uses Docker if available, falls back to local Python"
echo "📊 Supports 11 programming languages with full indexing"