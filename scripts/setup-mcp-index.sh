#!/bin/bash
# MCP Index Setup Script
# Downloads pre-built indexes from GitHub releases or builds locally

set -e

# Configuration
REPO_OWNER=$(git config --get remote.origin.url | sed -n 's/.*github.com[:/]\(.*\)\/\(.*\)\.git/\1/p')
REPO_NAME=$(git config --get remote.origin.url | sed -n 's/.*github.com[:/]\(.*\)\/\(.*\)\.git/\2/p')
MCP_INDEX_DIR="${MCP_INDEX_DIR:-$HOME/.mcp/indexes/$REPO_NAME}"
FORCE_REBUILD="${FORCE_REBUILD:-false}"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}MCP Index Setup for $REPO_OWNER/$REPO_NAME${NC}"

# Function to download index from release
download_index() {
    local tag=$1
    echo -e "${YELLOW}Checking for pre-built index...${NC}"
    
    # Get the latest release if no tag specified
    if [ -z "$tag" ]; then
        tag=$(curl -s "https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/releases/latest" | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')
    fi
    
    if [ -z "$tag" ]; then
        echo -e "${YELLOW}No releases found. Will build index locally.${NC}"
        return 1
    fi
    
    # Find index asset in release
    local asset_url=$(curl -s "https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/releases/tags/$tag" | \
        grep -E "browser_download_url.*mcp-index.*\.tar\.gz" | \
        cut -d '"' -f 4 | head -n 1)
    
    if [ -z "$asset_url" ]; then
        echo -e "${YELLOW}No index found in release $tag${NC}"
        return 1
    fi
    
    # Download the index
    echo -e "${GREEN}Downloading index from release $tag...${NC}"
    mkdir -p "$MCP_INDEX_DIR"
    local temp_file=$(mktemp)
    
    if curl -L "$asset_url" -o "$temp_file" --progress-bar; then
        echo -e "${GREEN}Extracting index...${NC}"
        tar -xzf "$temp_file" -C "$MCP_INDEX_DIR"
        rm "$temp_file"
        echo -e "${GREEN}✓ Index downloaded successfully!${NC}"
        return 0
    else
        echo -e "${RED}Failed to download index${NC}"
        rm -f "$temp_file"
        return 1
    fi
}

# Function to build index locally
build_index_locally() {
    echo -e "${YELLOW}Building index locally...${NC}"
    
    # Check if MCP server is installed
    if ! python -m mcp_server --version &> /dev/null; then
        echo -e "${YELLOW}Installing MCP server...${NC}"
        pip install -e . || pip install code-index-mcp
    fi
    
    # Build the index
    mkdir -p "$MCP_INDEX_DIR"
    python -m mcp_server index build \
        --output "$MCP_INDEX_DIR" \
        --include-embeddings \
        --show-progress
    
    echo -e "${GREEN}✓ Index built successfully!${NC}"
}

# Function to verify index
verify_index() {
    if [ -f "$MCP_INDEX_DIR/code_index.db" ]; then
        local size=$(du -sh "$MCP_INDEX_DIR" | cut -f1)
        local files=$(find "$MCP_INDEX_DIR" -type f | wc -l)
        echo -e "${GREEN}Index verified:${NC}"
        echo "  Location: $MCP_INDEX_DIR"
        echo "  Size: $size"
        echo "  Files: $files"
        return 0
    else
        return 1
    fi
}

# Main logic
main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --force-rebuild)
                FORCE_REBUILD=true
                shift
                ;;
            --tag)
                TAG="$2"
                shift 2
                ;;
            --help)
                echo "Usage: $0 [--force-rebuild] [--tag <release-tag>]"
                echo "  --force-rebuild  Build index locally even if download available"
                echo "  --tag           Specific release tag to download from"
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Check if index already exists
    if verify_index && [ "$FORCE_REBUILD" != "true" ]; then
        echo -e "${GREEN}Index already exists. Use --force-rebuild to rebuild.${NC}"
        exit 0
    fi
    
    # Try to download pre-built index
    if [ "$FORCE_REBUILD" != "true" ] && download_index "$TAG"; then
        verify_index
    else
        # Fall back to building locally
        build_index_locally
        verify_index
    fi
    
    # Export environment variable for MCP server
    echo
    echo -e "${GREEN}Setup complete! To use this index:${NC}"
    echo "export MCP_INDEX_PATH=\"$MCP_INDEX_DIR\""
    echo "python -m mcp_server"
}

# Run main function
main "$@"