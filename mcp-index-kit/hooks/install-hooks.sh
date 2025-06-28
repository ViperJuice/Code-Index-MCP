#!/bin/bash
# Install MCP Index Git Hooks
# This script installs git hooks for automatic index management

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo -e "${RED}Error: Not in a git repository${NC}"
    exit 1
fi

GIT_DIR=$(git rev-parse --git-dir)
HOOKS_DIR="$GIT_DIR/hooks"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${BLUE}MCP Index Git Hooks Installer${NC}"
echo "=============================="
echo

# Function to install a hook
install_hook() {
    local hook_name=$1
    local source_file="$SCRIPT_DIR/$hook_name"
    local target_file="$HOOKS_DIR/$hook_name"
    
    if [ ! -f "$source_file" ]; then
        echo -e "${RED}✗ Source hook not found: $source_file${NC}"
        return 1
    fi
    
    # Check if hook already exists
    if [ -f "$target_file" ]; then
        # Check if it's our hook
        if grep -q "MCP Index" "$target_file" 2>/dev/null; then
            echo -e "${YELLOW}⚠️  $hook_name: Already installed (updating)${NC}"
        else
            # Backup existing hook
            backup_file="$target_file.backup.$(date +%Y%m%d_%H%M%S)"
            cp "$target_file" "$backup_file"
            echo -e "${YELLOW}⚠️  $hook_name: Existing hook backed up to ${backup_file##*/}${NC}"
        fi
    fi
    
    # Copy hook
    cp "$source_file" "$target_file"
    chmod +x "$target_file"
    echo -e "${GREEN}✓ $hook_name: Installed successfully${NC}"
}

# Install each hook
echo "Installing git hooks..."
echo

install_hook "pre-push"
install_hook "post-merge"
install_hook "post-checkout"

echo
echo -e "${GREEN}✅ Git hooks installed successfully!${NC}"
echo

# Check for configuration
if [ ! -f ".mcp-index.json" ]; then
    echo -e "${YELLOW}⚠️  No .mcp-index.json found${NC}"
    echo "   The hooks are installed but won't run without configuration."
    echo "   Run 'mcp-index init' to create configuration."
else
    # Check configuration
    ENABLED=$(jq -r '.enabled // true' .mcp-index.json 2>/dev/null || echo "true")
    AUTO_UPLOAD=$(jq -r '.auto_upload // true' .mcp-index.json 2>/dev/null || echo "true")
    AUTO_DOWNLOAD=$(jq -r '.auto_download // true' .mcp-index.json 2>/dev/null || echo "true")
    
    echo "Configuration status:"
    echo -e "  Index management: $([ "$ENABLED" = "true" ] && echo "${GREEN}enabled${NC}" || echo "${RED}disabled${NC}")"
    echo -e "  Auto upload:      $([ "$AUTO_UPLOAD" = "true" ] && echo "${GREEN}enabled${NC}" || echo "${RED}disabled${NC}")"
    echo -e "  Auto download:    $([ "$AUTO_DOWNLOAD" = "true" ] && echo "${GREEN}enabled${NC}" || echo "${RED}disabled${NC}")"
fi

echo
echo "What the hooks do:"
echo "  • pre-push:      Uploads index changes before pushing"
echo "  • post-merge:    Downloads latest index after pulling"
echo "  • post-checkout: Checks index compatibility when switching branches"
echo
echo "To uninstall, run: $0 --uninstall"
echo

# Handle uninstall
if [ "$1" = "--uninstall" ]; then
    echo -e "${YELLOW}Uninstalling git hooks...${NC}"
    
    for hook in pre-push post-merge post-checkout; do
        hook_file="$HOOKS_DIR/$hook"
        if [ -f "$hook_file" ] && grep -q "MCP Index" "$hook_file" 2>/dev/null; then
            rm -f "$hook_file"
            echo -e "${GREEN}✓ Removed $hook${NC}"
            
            # Restore backup if exists
            backup=$(ls -t "$hook_file.backup."* 2>/dev/null | head -1)
            if [ -n "$backup" ]; then
                mv "$backup" "$hook_file"
                echo -e "${GREEN}✓ Restored original $hook${NC}"
            fi
        fi
    done
    
    echo -e "${GREEN}✅ Git hooks uninstalled${NC}"
fi