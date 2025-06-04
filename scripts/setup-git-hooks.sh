#!/bin/bash
# Setup script for MCP git hooks

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}Setting up MCP Git hooks...${NC}"

# Get git root directory
GIT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
if [ -z "$GIT_ROOT" ]; then
    echo "Error: Not in a git repository"
    exit 1
fi

# Configure git to use our hooks directory
git config core.hooksPath .githooks

# Ensure hooks are executable
chmod +x "$GIT_ROOT/.githooks/pre-push" 2>/dev/null || true
chmod +x "$GIT_ROOT/.githooks/post-commit" 2>/dev/null || true

# Create local config file if needed
if [ ! -f "$HOME/.mcp/config" ]; then
    mkdir -p "$HOME/.mcp"
    cat > "$HOME/.mcp/config" <<EOF
# MCP Git Hooks Configuration
# Uncomment to disable features

# Enable automatic indexing on commit
#export ENABLE_MCP_AUTO_INDEX=false

# Enable index push to remote
#export ENABLE_MCP_INDEX_PUSH=false

# Custom index directory
#export MCP_INDEX_DIR=/path/to/custom/index

# Index branch name
#export MCP_INDEX_BRANCH=mcp-index
EOF
    echo -e "${GREEN}Created config file: $HOME/.mcp/config${NC}"
fi

echo -e "${GREEN}✓ Git hooks configured successfully!${NC}"
echo
echo -e "${YELLOW}How it works:${NC}"
echo "1. ${BLUE}On commit${NC}: Indexes changed files in background"
echo "2. ${BLUE}On push to main${NC}: Updates index and optionally pushes to 'mcp-index' branch"
echo
echo -e "${YELLOW}Configuration:${NC}"
echo "- Edit ~/.mcp/config to customize behavior"
echo "- Indexes stored in: ~/.mcp/indexes/$(basename "$GIT_ROOT")"
echo
echo -e "${YELLOW}To download indexes from remote:${NC}"
echo "git fetch origin mcp-index"
echo "git checkout origin/mcp-index -- mcp-index-latest.tar.gz"
echo "tar -xzf mcp-index-latest.tar.gz -C ~/.mcp/indexes/$(basename "$GIT_ROOT")"