#!/bin/bash
# MCP Index Docker Installation Script
# Detects OS, installs Docker if needed, and sets up MCP Index

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
MCP_VERSION="${MCP_VERSION:-latest}"
MCP_VARIANT="${MCP_VARIANT:-minimal}"
DOCKER_REGISTRY="${DOCKER_REGISTRY:-ghcr.io}"
MCP_IMAGE="${DOCKER_REGISTRY}/code-index-mcp/mcp-index"

# Functions
print_banner() {
    echo -e "${BLUE}"
    echo "╔═══════════════════════════════════════════╗"
    echo "║        MCP Index Docker Installer         ║"
    echo "║   Fast, local-first code indexing tool    ║"
    echo "╚═══════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if [ -f /etc/os-release ]; then
            . /etc/os-release
            OS=$ID
            VER=$VERSION_ID
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        VER=$(sw_vers -productVersion)
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        OS="windows"
        VER="unknown"
    else
        OS="unknown"
        VER="unknown"
    fi
    
    print_info "Detected OS: $OS $VER"
}

check_docker() {
    if command -v docker &> /dev/null; then
        DOCKER_VERSION=$(docker --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
        print_info "Docker is installed (version $DOCKER_VERSION)"
        return 0
    else
        return 1
    fi
}

install_docker() {
    print_warn "Docker is not installed"
    
    read -p "Would you like to install Docker? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_error "Docker is required for MCP Index. Please install Docker manually."
        exit 1
    fi
    
    case $OS in
        ubuntu|debian)
            print_info "Installing Docker on $OS..."
            curl -fsSL https://get.docker.com | sudo sh
            sudo usermod -aG docker $USER
            print_warn "You need to log out and back in for Docker permissions to take effect"
            ;;
        fedora|centos|rhel)
            print_info "Installing Docker on $OS..."
            sudo dnf install -y docker
            sudo systemctl start docker
            sudo systemctl enable docker
            sudo usermod -aG docker $USER
            ;;
        macos)
            print_info "Please install Docker Desktop from:"
            echo "https://www.docker.com/products/docker-desktop/"
            exit 1
            ;;
        windows)
            print_info "Please install Docker Desktop from:"
            echo "https://www.docker.com/products/docker-desktop/"
            exit 1
            ;;
        *)
            print_error "Unsupported OS for automatic Docker installation"
            print_info "Please install Docker manually from: https://docs.docker.com/get-docker/"
            exit 1
            ;;
    esac
}

choose_variant() {
    echo
    echo "Choose MCP Index variant:"
    echo "1) minimal  - Zero configuration, BM25 search only (recommended for start)"
    echo "2) standard - AI-powered semantic search (requires Voyage AI key)"
    echo "3) full     - Production stack with monitoring"
    echo
    
    read -p "Select variant [1-3] (default: 1): " -n 1 -r
    echo
    
    case $REPLY in
        2)
            MCP_VARIANT="standard"
            print_info "Selected: standard (semantic search)"
            
            # Check for API key
            if [ -z "$VOYAGE_AI_API_KEY" ]; then
                print_warn "Semantic search requires a Voyage AI API key"
                echo "Get your free API key at: https://www.voyageai.com/"
                echo "Pricing: ~\$0.05 per 1M tokens (free tier: 50M tokens/month)"
                echo
                read -p "Enter your Voyage AI API key (or press Enter to skip): " API_KEY
                if [ ! -z "$API_KEY" ]; then
                    export VOYAGE_AI_API_KEY="$API_KEY"
                    echo "export VOYAGE_AI_API_KEY='$API_KEY'" >> ~/.bashrc
                    print_info "API key saved to ~/.bashrc"
                fi
            fi
            ;;
        3)
            MCP_VARIANT="full"
            print_info "Selected: full (production stack)"
            ;;
        *)
            MCP_VARIANT="minimal"
            print_info "Selected: minimal (zero configuration)"
            ;;
    esac
}

pull_image() {
    print_info "Pulling MCP Index image: ${MCP_IMAGE}:${MCP_VARIANT}"
    docker pull "${MCP_IMAGE}:${MCP_VARIANT}"
}

create_launcher() {
    LAUNCHER_PATH="/usr/local/bin/mcp-index"
    
    print_info "Creating launcher script..."
    
    # Create the launcher script
    cat > /tmp/mcp-index << 'EOF'
#!/bin/bash
# MCP Index Docker Launcher

# Default settings
MCP_VARIANT="${MCP_VARIANT:-minimal}"
MCP_IMAGE="${MCP_IMAGE:-ghcr.io/code-index-mcp/mcp-index}"
WORKSPACE="${WORKSPACE:-$(pwd)}"

# Handle commands
case "$1" in
    setup)
        echo "Running MCP Index setup wizard..."
        docker run -it --rm -v "$WORKSPACE:/workspace" "${MCP_IMAGE}:${MCP_VARIANT}" --setup
        ;;
    upgrade)
        echo "Upgrading MCP Index..."
        docker pull "${MCP_IMAGE}:${MCP_VARIANT}"
        ;;
    *)
        # Run MCP server with all arguments passed through
        docker run -i --rm \
            -v "$WORKSPACE:/workspace" \
            -v "$HOME/.mcp-index:/app/.mcp-index" \
            -e VOYAGE_AI_API_KEY="${VOYAGE_AI_API_KEY:-}" \
            -e MCP_ARTIFACT_SYNC="${MCP_ARTIFACT_SYNC:-true}" \
            "${MCP_IMAGE}:${MCP_VARIANT}" "$@"
        ;;
esac
EOF
    
    # Install the launcher
    if [ -w /usr/local/bin ]; then
        mv /tmp/mcp-index /usr/local/bin/mcp-index
        chmod +x /usr/local/bin/mcp-index
    else
        sudo mv /tmp/mcp-index /usr/local/bin/mcp-index
        sudo chmod +x /usr/local/bin/mcp-index
    fi
    
    print_info "Launcher installed at: /usr/local/bin/mcp-index"
}

setup_mcp_json() {
    print_info "Creating .mcp.json template..."
    
    cat > .mcp.json << EOF
{
  "mcpServers": {
    "code-index": {
      "command": "docker",
      "args": [
        "run", 
        "-i", 
        "--rm",
        "-v", "\${workspace}:/workspace",
        "-v", "\${HOME}/.mcp-index:/app/.mcp-index",
        "-e", "VOYAGE_AI_API_KEY=\${VOYAGE_AI_API_KEY:-}",
        "-e", "MCP_ARTIFACT_SYNC=\${MCP_ARTIFACT_SYNC:-true}",
        "${MCP_IMAGE}:${MCP_VARIANT}"
      ]
    }
  }
}
EOF
    
    print_info "Created .mcp.json for Claude Code integration"
}

print_next_steps() {
    echo
    echo -e "${GREEN}✅ MCP Index Docker installation complete!${NC}"
    echo
    echo "Next steps:"
    echo "1. Test the installation:"
    echo "   mcp-index --version"
    echo
    echo "2. Index your current directory:"
    echo "   mcp-index"
    echo
    
    if [ "$MCP_VARIANT" == "standard" ] || [ "$MCP_VARIANT" == "full" ]; then
        echo "3. Configure semantic search:"
        echo "   export VOYAGE_AI_API_KEY='your-key-here'"
        echo "   Get your key at: https://www.voyageai.com/"
        echo
    fi
    
    echo "4. For Claude Code integration:"
    echo "   - Copy .mcp.json to your project root"
    echo "   - Claude will automatically use the Docker version"
    echo
    echo "Documentation: https://github.com/Code-Index-MCP/docs/DOCKER_GUIDE.md"
}

# Main installation flow
main() {
    print_banner
    detect_os
    
    # Check if Docker is installed
    if ! check_docker; then
        install_docker
    fi
    
    # Choose variant
    choose_variant
    
    # Pull the image
    pull_image
    
    # Create launcher script
    create_launcher
    
    # Create .mcp.json template
    setup_mcp_json
    
    # Print next steps
    print_next_steps
}

# Run main function
main "$@"