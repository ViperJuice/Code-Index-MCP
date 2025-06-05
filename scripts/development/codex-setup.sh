#!/bin/bash

# Code-Index-MCP Setup Script
# This script sets up everything needed for the Code-Index-MCP project in a blank container
# Assumes no internet access after this script runs
# Assumes Node.js and Python are already installed

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Check if running as root (for system package installation)
check_privileges() {
    if [[ $EUID -eq 0 ]]; then
        log "Running as root - can install system packages"
        SUDO=""
    else
        log "Running as regular user - will use sudo for system packages"
        SUDO="sudo"
    fi
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check Python version
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        log "Python version: $PYTHON_VERSION"
        
        # Check if version is 3.8 or higher
        if python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
            success "Python version is compatible"
        else
            error "Python 3.8+ required, found $PYTHON_VERSION"
            exit 1
        fi
    else
        error "Python3 not found"
        exit 1
    fi
    
    # Check Node.js version
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version)
        log "Node.js version: $NODE_VERSION"
        
        # Extract major version (remove 'v' prefix)
        NODE_MAJOR=$(echo $NODE_VERSION | sed 's/v\([0-9]*\).*/\1/')
        if [[ $NODE_MAJOR -ge 16 ]]; then
            success "Node.js version is compatible"
        else
            warning "Node.js 16+ recommended, found $NODE_VERSION"
        fi
    else
        warning "Node.js not found - some features may not work"
    fi
    
    # Check pip
    if ! command -v pip3 &> /dev/null; then
        error "pip3 not found"
        exit 1
    fi
}

# Install system dependencies
install_system_deps() {
    log "Installing system dependencies..."
    
    # Detect package manager
    if command -v apt-get &> /dev/null; then
        PKG_MANAGER="apt-get"
        PKG_UPDATE="$SUDO apt-get update"
        PKG_INSTALL="$SUDO apt-get install -y"
    elif command -v yum &> /dev/null; then
        PKG_MANAGER="yum"
        PKG_UPDATE="$SUDO yum update -y"
        PKG_INSTALL="$SUDO yum install -y"
    elif command -v dnf &> /dev/null; then
        PKG_MANAGER="dnf"
        PKG_UPDATE="$SUDO dnf update -y"
        PKG_INSTALL="$SUDO dnf install -y"
    elif command -v apk &> /dev/null; then
        PKG_MANAGER="apk"
        PKG_UPDATE="$SUDO apk update"
        PKG_INSTALL="$SUDO apk add"
    else
        warning "No supported package manager found - skipping system dependencies"
        return
    fi
    
    log "Using package manager: $PKG_MANAGER"
    
    # Update package lists
    log "Updating package lists..."
    $PKG_UPDATE
    
    # Install system dependencies based on Dockerfile
    log "Installing build dependencies..."
    case $PKG_MANAGER in
        "apt-get")
            $PKG_INSTALL build-essential git curl libcurl4-openssl-dev \
                        libffi-dev libssl-dev python3-dev \
                        sqlite3 libsqlite3-dev \
                        redis-tools
            ;;
        "yum"|"dnf")
            $PKG_INSTALL gcc gcc-c++ make git curl libcurl-devel \
                        libffi-devel openssl-devel python3-devel \
                        sqlite sqlite-devel \
                        redis
            ;;
        "apk")
            $PKG_INSTALL build-base git curl curl-dev \
                        libffi-dev openssl-dev python3-dev \
                        sqlite sqlite-dev \
                        redis
            ;;
    esac
    
    success "System dependencies installed"
}

# Create directory structure
setup_directories() {
    log "Setting up directory structure..."
    
    # Create data directories
    mkdir -p data
    mkdir -p logs
    mkdir -p backup
    mkdir -p test_results
    mkdir -p htmlcov
    
    # Create configuration directories if they don't exist
    mkdir -p config
    
    success "Directory structure created"
}

# Install Python dependencies
install_python_deps() {
    log "Installing Python dependencies..."
    
    # Upgrade pip first
    log "Upgrading pip..."
    python3 -m pip install --upgrade pip setuptools wheel
    
    # Install core dependencies from pyproject.toml
    log "Installing core dependencies..."
    python3 -m pip install --no-cache-dir \
        "fastapi>=0.110" \
        "uvicorn[standard]>=0.29" \
        "watchdog>=4.0" \
        "tree-sitter>=0.20.0" \
        "tree-sitter-languages>=1.8.0" \
        "jedi>=0.19.0"
    
    # Install development and testing dependencies
    if [[ -f "requirements.txt" ]]; then
        log "Installing requirements from requirements.txt..."
        python3 -m pip install --no-cache-dir -r requirements.txt
    else
        log "Installing essential testing and development dependencies..."
        python3 -m pip install --no-cache-dir \
            "pytest>=7.4.0" \
            "pytest-asyncio>=0.21.0" \
            "pytest-cov>=4.1.0" \
            "pytest-timeout>=2.1.0" \
            "pytest-mock>=3.11.1" \
            "pytest-benchmark>=4.0.0" \
            "pytest-xdist>=3.3.1" \
            "black>=23.7.0" \
            "isort>=5.12.0" \
            "flake8>=6.1.0" \
            "mypy>=1.5.1" \
            "coverage[toml]>=7.3.0" \
            "hypothesis>=6.82.0" \
            "redis>=4.5.0" \
            "pyjwt>=2.8.0" \
            "passlib[bcrypt]>=1.7.4" \
            "python-multipart>=0.0.6" \
            "cryptography>=41.0.4" \
            "httpx>=0.24.1" \
            "aiofiles>=23.2.1" \
            "psutil>=5.9.0" \
            "prometheus-client>=0.17.0"
    fi
    
    # Install the project in development mode
    if [[ -f "pyproject.toml" ]]; then
        log "Installing project in development mode..."
        python3 -m pip install -e .
    fi
    
    success "Python dependencies installed"
}

# Setup Tree-sitter grammars
setup_tree_sitter() {
    log "Setting up Tree-sitter grammars..."
    
    # Create a simple Python script to initialize tree-sitter
    cat > init_tree_sitter.py << 'EOF'
#!/usr/bin/env python3
"""Initialize Tree-sitter grammars for the project."""

try:
    import tree_sitter_languages
    from tree_sitter import Language
    
    # Test loading common languages
    languages = ['python', 'javascript', 'c', 'cpp', 'html', 'css', 'dart']
    
    for lang in languages:
        try:
            language = tree_sitter_languages.get_language(lang)
            print(f"✅ {lang} grammar loaded successfully")
        except Exception as e:
            print(f"⚠️  Failed to load {lang} grammar: {e}")
    
    print("Tree-sitter setup completed")
    
except ImportError as e:
    print(f"❌ Tree-sitter not available: {e}")
    exit(1)
EOF
    
    python3 init_tree_sitter.py
    rm init_tree_sitter.py
    
    success "Tree-sitter grammars initialized"
}

# Create configuration files
create_config_files() {
    log "Creating configuration files..."
    
    # Create .env file if it doesn't exist
    if [[ ! -f ".env" ]]; then
        log "Creating default .env file..."
        cat > .env << 'EOF'
# Code-Index-MCP Configuration

# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=false
LOG_LEVEL=INFO

# Security
JWT_SECRET_KEY=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# Database
DATABASE_URL=sqlite:///./data/code_index.db

# Cache Configuration
REDIS_URL=redis://localhost:6379
CACHE_TTL=3600

# Features Toggle
SEMANTIC_SEARCH_ENABLED=false
METRICS_ENABLED=true
SECURITY_ENABLED=true

# API Keys (optional)
VOYAGE_AI_API_KEY=
QDRANT_URL=http://localhost:6333

# CORS
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8080"]

# Monitoring
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090
EOF
        success "Created .env file"
    else
        log ".env file already exists"
    fi
    
    # Create pytest configuration if it doesn't exist
    if [[ ! -f "pytest.ini" ]]; then
        log "Creating pytest.ini..."
        cat > pytest.ini << 'EOF'
[tool:pytest]
testpaths = tests
python_files = test_*.py *_test.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --tb=short
    --strict-markers
    --disable-warnings
    --color=yes
    --durations=10
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow tests
    benchmark: Benchmark tests
    real_world: Real world tests
    semantic: Semantic search tests
    redis: Redis-dependent tests
    dormant: Dormant features tests
filterwarnings =
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
EOF
        success "Created pytest.ini"
    else
        log "pytest.ini already exists"
    fi
}

# Setup permissions and ownership
setup_permissions() {
    log "Setting up permissions..."
    
    # Make directories writable
    chmod -R 755 data logs backup test_results htmlcov 2>/dev/null || true
    
    # Make any shell scripts executable
    find . -name "*.sh" -type f -exec chmod +x {} \; 2>/dev/null || true
    
    success "Permissions set"
}

# Validate installation
validate_installation() {
    log "Validating installation..."
    
    # Test Python imports
    log "Testing Python imports..."
    python3 -c "
import sys
print(f'Python version: {sys.version}')

# Test core imports
try:
    import fastapi
    import uvicorn
    import watchdog
    import tree_sitter
    import tree_sitter_languages
    import jedi
    print('✅ Core dependencies imported successfully')
except ImportError as e:
    print(f'❌ Core import failed: {e}')
    sys.exit(1)

# Test optional imports
optional_imports = {
    'redis': 'Redis support',
    'pytest': 'Testing framework',
    'black': 'Code formatting',
    'mypy': 'Type checking',
}

for module, description in optional_imports.items():
    try:
        __import__(module)
        print(f'✅ {description} available')
    except ImportError:
        print(f'⚠️  {description} not available')
"
    
    # Test project structure
    log "Checking project structure..."
    required_dirs=("mcp_server" "tests")
    for dir in "${required_dirs[@]}"; do
        if [[ -d "$dir" ]]; then
            success "$dir directory found"
        else
            error "$dir directory missing"
        fi
    done
    
    # Test if the project can be imported
    log "Testing project import..."
    python3 -c "
try:
    from mcp_server import gateway
    print('✅ Project can be imported')
except ImportError as e:
    print(f'⚠️  Project import issue: {e}')
"
    
    success "Installation validation completed"
}

# Create startup script
create_startup_script() {
    log "Creating startup script..."
    
    cat > start-server.sh << 'EOF'
#!/bin/bash
# Start the Code-Index-MCP server

set -euo pipefail

# Check if virtual environment should be activated
if [[ -d "venv" ]]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Load environment variables
if [[ -f ".env" ]]; then
    echo "Loading environment variables..."
    export $(grep -v '^#' .env | xargs)
fi

# Create data directory if it doesn't exist
mkdir -p data

# Start the server
echo "Starting Code-Index-MCP server..."
exec python3 -m uvicorn mcp_server.gateway:app \
    --host "${HOST:-0.0.0.0}" \
    --port "${PORT:-8000}" \
    --reload
EOF
    
    chmod +x start-server.sh
    success "Created start-server.sh"
}

# Create test runner script
create_test_script() {
    log "Creating test runner script..."
    
    cat > run-tests.sh << 'EOF'
#!/bin/bash
# Run tests for Code-Index-MCP

set -euo pipefail

# Activate virtual environment if it exists
if [[ -d "venv" ]]; then
    source venv/bin/activate
fi

# Default to unit tests if no argument provided
TEST_TYPE=${1:-unit}

case $TEST_TYPE in
    "unit")
        echo "Running unit tests..."
        python3 -m pytest tests -v -m "not integration and not slow and not benchmark"
        ;;
    "integration")
        echo "Running integration tests..."
        python3 -m pytest tests -v -m "integration"
        ;;
    "all")
        echo "Running all tests with coverage..."
        python3 -m pytest tests -v --cov=mcp_server --cov-report=term-missing --cov-report=html
        ;;
    "quick")
        echo "Running quick smoke tests..."
        python3 -m pytest tests -v -k "test_" --maxfail=5 -x
        ;;
    *)
        echo "Usage: $0 [unit|integration|all|quick]"
        exit 1
        ;;
esac
EOF
    
    chmod +x run-tests.sh
    success "Created run-tests.sh"
}

# Create maintenance script
create_maintenance_script() {
    log "Creating maintenance script..."
    
    cat > maintenance.sh << 'EOF'
#!/bin/bash
# Maintenance script for Code-Index-MCP

set -euo pipefail

# Function to clean up
cleanup() {
    echo "Cleaning up temporary files..."
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    find . -type f -name "*.pyo" -delete 2>/dev/null || true
    find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
    echo "✅ Cleanup completed"
}

# Function to check health
health_check() {
    echo "Performing health check..."
    
    # Check if server is running
    if pgrep -f "uvicorn.*mcp_server" > /dev/null; then
        echo "✅ Server is running"
    else
        echo "⚠️  Server is not running"
    fi
    
    # Check disk space
    echo "Disk usage:"
    df -h . | tail -1
    
    # Check memory usage
    echo "Memory usage:"
    free -h 2>/dev/null || vm_stat 2>/dev/null || echo "Memory info not available"
}

# Function to backup data
backup() {
    echo "Creating backup..."
    BACKUP_DIR="backup/$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    # Backup database
    if [[ -f "data/code_index.db" ]]; then
        cp "data/code_index.db" "$BACKUP_DIR/"
        echo "✅ Database backed up"
    fi
    
    # Backup logs
    if [[ -d "logs" ]]; then
        cp -r logs "$BACKUP_DIR/"
        echo "✅ Logs backed up"
    fi
    
    echo "✅ Backup completed in $BACKUP_DIR"
}

# Main menu
case "${1:-help}" in
    "cleanup")
        cleanup
        ;;
    "health")
        health_check
        ;;
    "backup")
        backup
        ;;
    "help"|*)
        echo "Usage: $0 [cleanup|health|backup]"
        echo "  cleanup - Remove temporary files"
        echo "  health  - Check system health"
        echo "  backup  - Backup data and logs"
        ;;
esac
EOF
    
    chmod +x maintenance.sh
    success "Created maintenance.sh"
}

# Main execution
main() {
    log "Starting Code-Index-MCP setup..."
    
    check_privileges
    check_prerequisites
    install_system_deps
    setup_directories
    install_python_deps
    setup_tree_sitter
    create_config_files
    setup_permissions
    create_startup_script
    create_test_script
    create_maintenance_script
    validate_installation
    
    success "Setup completed successfully!"
    
    log "Next steps:"
    echo "  1. Review and update .env file with your configuration"
    echo "  2. Start the server: ./start-server.sh"
    echo "  3. Run tests: ./run-tests.sh"
    echo "  4. Check health: ./maintenance.sh health"
    echo ""
    log "Available scripts:"
    echo "  - start-server.sh   : Start the MCP server"
    echo "  - run-tests.sh      : Run test suite"
    echo "  - maintenance.sh    : System maintenance"
    echo ""
    log "Make commands (if Makefile available):"
    echo "  - make install      : Install dependencies"
    echo "  - make test         : Run tests"
    echo "  - make lint         : Run code quality checks"
    echo "  - make help         : Show all available commands"
}

# Execute main function
main "$@"