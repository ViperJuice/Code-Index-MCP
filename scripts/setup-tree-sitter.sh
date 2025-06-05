#!/bin/bash
# Tree-sitter Language Parser Setup Script
# Installs and configures Tree-sitter parsers for Code-Index-MCP

set -euo pipefail

echo "Setting up Tree-sitter language parsers..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if pip is available
if ! command -v pip &> /dev/null; then
    echo -e "${RED}Error: pip is not available. Please install pip first.${NC}"
    exit 1
fi

# Function to install a package with error handling
install_package() {
    local package="$1"
    echo -e "${YELLOW}Installing $package...${NC}"
    
    if pip install "$package" --quiet; then
        echo -e "${GREEN}✓ Successfully installed $package${NC}"
    else
        echo -e "${RED}✗ Failed to install $package${NC}"
        return 1
    fi
}

# Function to check if a package is available
check_package() {
    local package="$1"
    echo -e "${YELLOW}Checking $package...${NC}"
    
    if python -c "import $package" 2>/dev/null; then
        echo -e "${GREEN}✓ $package is available${NC}"
        return 0
    else
        echo -e "${RED}✗ $package is not available${NC}"
        return 1
    fi
}

echo "Installing core Tree-sitter dependencies..."

# Core Tree-sitter packages
install_package "tree-sitter>=0.20.0"
install_package "tree-sitter-languages>=1.7.0"

echo -e "\nInstalling language-specific parsers..."

# Language parsers
PARSERS=(
    "tree-sitter-c-sharp>=0.20.0"
    "tree-sitter-bash>=0.20.0"
    "tree-sitter-haskell>=0.14.0"
    "tree-sitter-scala>=0.19.0"
    "tree-sitter-lua>=0.0.14"
    "tree-sitter-yaml>=0.5.0"
    "tree-sitter-toml>=0.5.1"
    "tree-sitter-json>=0.19.0"
    "tree-sitter-markdown>=0.7.1"
    "tree-sitter-csv>=0.1.1"
)

FAILED_PARSERS=()

for parser in "${PARSERS[@]}"; do
    parser_name=$(echo "$parser" | cut -d'>' -f1)
    if ! install_package "$parser"; then
        FAILED_PARSERS+=("$parser_name")
    fi
done

echo -e "\nVerifying installations..."

# Check core packages
check_package "tree_sitter"
check_package "tree_sitter_languages"

# Check language parsers
PARSER_MODULES=(
    "tree_sitter_c_sharp"
    "tree_sitter_bash"
    "tree_sitter_haskell"
    "tree_sitter_scala"
    "tree_sitter_lua"
    "tree_sitter_yaml"
    "tree_sitter_toml"
    "tree_sitter_json"
    "tree_sitter_markdown"
    "tree_sitter_csv"
)

UNAVAILABLE_MODULES=()

for module in "${PARSER_MODULES[@]}"; do
    if ! check_package "$module"; then
        UNAVAILABLE_MODULES+=("$module")
    fi
done

echo -e "\n${GREEN}Tree-sitter setup completed!${NC}"

if [ ${#FAILED_PARSERS[@]} -gt 0 ]; then
    echo -e "\n${YELLOW}Warning: Some parsers failed to install:${NC}"
    for parser in "${FAILED_PARSERS[@]}"; do
        echo -e "  ${RED}✗ $parser${NC}"
    done
fi

if [ ${#UNAVAILABLE_MODULES[@]} -gt 0 ]; then
    echo -e "\n${YELLOW}Warning: Some modules are not available:${NC}"
    for module in "${UNAVAILABLE_MODULES[@]}"; do
        echo -e "  ${RED}✗ $module${NC}"
    done
    echo -e "\n${YELLOW}Note: These parsers will be handled gracefully with fallback options.${NC}"
fi

echo -e "\n${GREEN}Setup complete! You can now use Tree-sitter with multiple language support.${NC}"