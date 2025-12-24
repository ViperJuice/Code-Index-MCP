#!/bin/bash
# Commands to build and test MCP Docker images
# Run this once Docker is available in your environment

set -e

echo "🐳 MCP Docker Build and Test Commands"
echo "===================================="
echo ""
echo "These commands will work once Docker is accessible."
echo ""

# Check if Docker is available
if command -v docker &> /dev/null; then
    echo "✅ Docker is available!"
    DOCKER_AVAILABLE=true
else
    echo "⚠️  Docker not found. Showing commands to run later:"
    DOCKER_AVAILABLE=false
fi

echo ""
echo "📦 Step 1: Build the Docker images"
echo "----------------------------------"
echo ""
echo "# Build minimal image (no API keys required):"
echo "docker build -f docker/dockerfiles/Dockerfile.minimal -t mcp-index:minimal ."
echo ""
echo "# Build standard image (includes semantic search):"
echo "docker build -f docker/dockerfiles/Dockerfile.standard -t mcp-index:standard ."
echo ""
echo "# Build full production image:"
echo "docker build -f docker/dockerfiles/Dockerfile.full -t mcp-index:full ."
echo ""

echo "🧪 Step 2: Test the images"
echo "--------------------------"
echo ""
echo "# Test minimal version (no configuration needed):"
echo "docker run -it --rm -v \$(pwd):/workspace mcp-index:minimal"
echo ""
echo "# Test standard version with semantic search:"
echo "docker run -it --rm \\"
echo "  -v \$(pwd):/workspace \\"
echo "  -e VOYAGE_AI_API_KEY=your-voyage-ai-key \\"
echo "  mcp-index:standard"
echo ""
echo "# Test with specific directory:"
echo "docker run -it --rm -v /path/to/your/code:/workspace mcp-index:minimal"
echo ""

echo "🔧 Step 3: Create helper alias (optional)"
echo "----------------------------------------"
echo ""
echo "# Add to your ~/.bashrc or ~/.zshrc:"
echo "alias mcp-index='docker run -it --rm -v \$(pwd):/workspace mcp-index:minimal'"
echo "alias mcp-index-ai='docker run -it --rm -v \$(pwd):/workspace -e VOYAGE_AI_API_KEY mcp-index:standard'"
echo ""

echo "📋 Step 4: Use with Claude Code"
echo "-------------------------------"
echo ""
echo "# Copy the Docker MCP configuration:"
echo "cp .mcp.json.docker .mcp.json"
echo ""
echo "# Or create a new .mcp.json with this content:"
echo "cat > .mcp.json << 'EOF'"
cat .mcp.json.docker
echo "EOF"
echo ""

echo "🚀 Step 5: Test MCP protocol"
echo "----------------------------"
echo ""
echo "# Send a test command to the MCP server:"
echo "echo '{\"jsonrpc\": \"2.0\", \"method\": \"initialize\", \"params\": {\"capabilities\": {}}, \"id\": 1}' | \\"
echo "  docker run -i --rm -v \$(pwd):/workspace mcp-index:minimal"
echo ""

if [ "$DOCKER_AVAILABLE" = true ]; then
    echo "🎉 Docker is available! You can run these commands now."
    echo ""
    read -p "Would you like to build the minimal image now? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Building minimal image..."
        docker build -f docker/dockerfiles/Dockerfile.minimal -t mcp-index:minimal .
    fi
else
    echo "📝 Save these commands for when Docker is available."
    echo ""
    echo "To make Docker available in WSL2:"
    echo "1. Ensure Docker Desktop is running on Windows"
    echo "2. In Docker Desktop: Settings → Resources → WSL Integration"
    echo "3. Enable integration with your WSL2 distro"
    echo "4. Restart your WSL2 terminal (exit and reopen)"
    echo "5. Run this script again"
fi