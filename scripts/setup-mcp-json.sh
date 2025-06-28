#!/bin/bash
# MCP.json Setup Script - Automatically configures MCP for your environment

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Print functions
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Detect environment
detect_environment() {
    # Check if we're in a dev container
    if [ -f /.dockerenv ] || [ -n "$CODESPACES" ] || [ -n "$REMOTE_CONTAINERS" ]; then
        echo "devcontainer"
        return
    fi
    
    # Check if Docker is available
    if command -v docker >/dev/null 2>&1; then
        # Check if we can actually use Docker
        if docker ps >/dev/null 2>&1; then
            echo "docker"
            return
        else
            print_warn "Docker is installed but not accessible. May need sudo or Docker Desktop running."
        fi
    fi
    
    # Check if we're in WSL
    if grep -qi microsoft /proc/version 2>/dev/null; then
        if command -v docker.exe >/dev/null 2>&1; then
            echo "wsl-docker"
        else
            echo "wsl"
        fi
        return
    fi
    
    # Default to native
    echo "native"
}

# Check for API key
check_api_key() {
    if [ -n "$VOYAGE_AI_API_KEY" ]; then
        print_success "Voyage AI API key detected"
        return 0
    elif [ -f .env ] && grep -q "VOYAGE_AI_API_KEY" .env; then
        print_info "Voyage AI API key found in .env file"
        return 0
    else
        print_warn "No Voyage AI API key found. Semantic search will be disabled."
        print_info "Get your free API key at: https://www.voyageai.com/"
        return 1
    fi
}

# Main setup function
setup_mcp_json() {
    print_info "Detecting your environment..."
    
    ENV=$(detect_environment)
    print_info "Detected environment: $ENV"
    
    # Map environment to template
    case $ENV in
        devcontainer)
            TEMPLATE="native.json"
            print_info "Using native Python execution (already in container)"
            ;;
        docker)
            if check_api_key; then
                TEMPLATE="docker-standard.json"
                print_info "Using Docker with semantic search enabled"
            else
                TEMPLATE="docker-minimal.json"
                print_info "Using Docker minimal version (no API key)"
            fi
            ;;
        wsl-docker)
            TEMPLATE="wsl-docker.json"
            print_info "Using Docker via WSL integration"
            ;;
        wsl|native)
            TEMPLATE="native.json"
            print_info "Using native Python execution"
            ;;
        *)
            TEMPLATE="auto-detect.json"
            print_warn "Unknown environment, using auto-detection"
            ;;
    esac
    
    # Backup existing .mcp.json if it exists
    if [ -f .mcp.json ]; then
        print_info "Backing up existing .mcp.json to .mcp.json.backup"
        cp .mcp.json .mcp.json.backup
    fi
    
    # Copy the appropriate template
    if [ -f ".mcp.json.templates/$TEMPLATE" ]; then
        cp ".mcp.json.templates/$TEMPLATE" .mcp.json
        print_success "Created .mcp.json for $ENV environment"
    else
        print_error "Template not found: .mcp.json.templates/$TEMPLATE"
        exit 1
    fi
    
    # Show next steps
    echo
    print_info "Next steps:"
    
    case $ENV in
        docker|wsl-docker)
            echo "1. Ensure Docker Desktop is running"
            echo "2. Build the Docker image (if using local images):"
            echo "   docker build -f docker/dockerfiles/Dockerfile.minimal -t mcp-index:minimal ."
            echo "3. Open your project in Claude Code"
            ;;
        devcontainer|native|wsl)
            echo "1. Install dependencies (if not already done):"
            echo "   pip install -e ."
            echo "2. Open your project in Claude Code"
            ;;
    esac
    
    if ! check_api_key >/dev/null 2>&1; then
        echo
        echo "To enable semantic search:"
        echo "1. Get an API key from https://www.voyageai.com/"
        echo "2. Set it: export VOYAGE_AI_API_KEY=your-key"
        echo "3. Re-run this script"
    fi
}

# Interactive mode
interactive_setup() {
    echo "MCP.json Configuration Setup"
    echo "============================"
    echo
    echo "Available configurations:"
    echo "1. Auto-detect (recommended)"
    echo "2. Docker - Minimal (no API key needed)"
    echo "3. Docker - Standard (with semantic search)"
    echo "4. Docker - Sidecar (for nested containers)"
    echo "5. Native Python"
    echo "6. WSL with Docker"
    echo
    
    read -p "Select configuration (1-6) [1]: " choice
    choice=${choice:-1}
    
    case $choice in
        1) setup_mcp_json ;;
        2) cp .mcp.json.templates/docker-minimal.json .mcp.json ;;
        3) cp .mcp.json.templates/docker-standard.json .mcp.json ;;
        4) cp .mcp.json.templates/docker-sidecar.json .mcp.json ;;
        5) cp .mcp.json.templates/native.json .mcp.json ;;
        6) cp .mcp.json.templates/wsl-docker.json .mcp.json ;;
        *) print_error "Invalid choice"; exit 1 ;;
    esac
    
    print_success "Configuration complete!"
}

# Main execution
if [ "$1" = "--interactive" ] || [ "$1" = "-i" ]; then
    interactive_setup
else
    setup_mcp_json
fi