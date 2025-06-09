#!/bin/bash
# MCP Index Download Script
# Downloads the latest index artifact from GitHub Actions

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo -e "${RED}Error: GitHub CLI (gh) is not installed${NC}"
    echo "Please install it from: https://cli.github.com/"
    exit 1
fi

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo -e "${RED}Error: Not in a git repository${NC}"
    exit 1
fi

echo -e "${GREEN}MCP Index Downloader${NC}"
echo "===================="

# Get repository info
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
echo "Repository: $REPO"

# List available artifacts
echo -e "\n${YELLOW}Checking for available index artifacts...${NC}"

ARTIFACTS=$(gh api \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  /repos/$REPO/actions/artifacts \
  --jq '.artifacts[] | select(.name | startswith("mcp-index-")) | {id: .id, name: .name, created_at: .created_at, size_mb: (.size_in_bytes / 1048576 | floor)}' \
  | jq -s 'sort_by(.created_at) | reverse | .[0:5]')

if [ -z "$ARTIFACTS" ] || [ "$ARTIFACTS" = "[]" ]; then
    echo -e "${RED}No index artifacts found${NC}"
    echo "The repository may not have MCP indexing set up yet."
    exit 1
fi

# Display available artifacts
echo -e "\nRecent index artifacts:"
echo "$ARTIFACTS" | jq -r '.[] | "  \(.name) - \(.size_mb)MB - \(.created_at)"'

# Get the most recent artifact
LATEST=$(echo "$ARTIFACTS" | jq -r '.[0]')
ARTIFACT_ID=$(echo "$LATEST" | jq -r '.id')
ARTIFACT_NAME=$(echo "$LATEST" | jq -r '.name')
ARTIFACT_SIZE=$(echo "$LATEST" | jq -r '.size_mb')

echo -e "\n${YELLOW}Downloading latest artifact:${NC} $ARTIFACT_NAME (${ARTIFACT_SIZE}MB)"

# Create temporary directory
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

# Download artifact
gh api \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  /repos/$REPO/actions/artifacts/$ARTIFACT_ID/zip \
  > "$TEMP_DIR/artifact.zip"

# Extract artifact
cd "$TEMP_DIR"
unzip -q artifact.zip

# Verify checksum if available
if [ -f "mcp-index-archive.tar.gz.sha256" ]; then
    echo -e "\n${YELLOW}Verifying checksum...${NC}"
    if sha256sum -c mcp-index-archive.tar.gz.sha256 > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Checksum verified${NC}"
    else
        echo -e "${RED}✗ Checksum verification failed${NC}"
        exit 1
    fi
fi

# Extract index
echo -e "\n${YELLOW}Extracting index...${NC}"
mkdir -p "$OLDPWD/.mcp-index"
tar -xzf mcp-index-archive.tar.gz -C "$OLDPWD/.mcp-index/"

cd "$OLDPWD"

# Display metadata
if [ -f ".mcp-index/.index_metadata.json" ]; then
    echo -e "\n${GREEN}Index metadata:${NC}"
    jq -r 'to_entries | .[] | "  \(.key): \(.value)"' .mcp-index/.index_metadata.json
fi

echo -e "\n${GREEN}✓ Index downloaded successfully!${NC}"
echo "The index is now available in .mcp-index/"
echo ""
echo "To use this index:"
echo "1. Make sure you have the MCP extension installed"
echo "2. The extension will automatically detect and use this index"
echo ""
echo "To update the index later, run this script again."