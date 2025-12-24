#\!/bin/bash

# Docker Setup Script for Code-Index-MCP
# This script helps set up and run the MCP server in Docker

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
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

# Check Docker is installed
check_docker() {
    log "Checking Docker installation..."
    
    if \! command -v docker &> /dev/null; then
        error "Docker is not installed"
        echo "Please install Docker from https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    if \! docker ps &> /dev/null; then
        error "Docker daemon is not running or you don't have permissions"
        echo "Try: sudo usermod -aG docker $USER && newgrp docker"
        exit 1
    fi
    
    success "Docker is installed and running"
}

# Check Docker Compose
check_docker_compose() {
    log "Checking Docker Compose..."
    
    if \! command -v docker-compose &> /dev/null; then
        # Try docker compose (v2)
        if docker compose version &> /dev/null; then
            alias docker-compose="docker compose"
            success "Docker Compose v2 is available"
        else
            error "Docker Compose is not installed"
            echo "Please install Docker Compose from https://docs.docker.com/compose/install/"
            exit 1
        fi
    else
        success "Docker Compose is installed"
    fi
}

# Create environment file
create_env_file() {
    log "Setting up environment configuration..."
    
    if [[ -f ".env" ]]; then
        warning ".env file already exists"
        read -p "Do you want to create a new .env file? (y/N) " -n 1 -r
        echo
        if [[ \! $REPLY =~ ^[Yy]$ ]]; then
            log "Keeping existing .env file"
            return
        fi
        cp .env .env.backup
        log "Backed up existing .env to .env.backup"
    fi
    
    cat > .env << 'EOF'
# Code-Index-MCP Docker Configuration

# Core Settings
LOG_LEVEL=INFO
DEBUG=false

# MCP Server Settings
MCP_WORKSPACE_ROOT=/workspace
DATABASE_URL=sqlite:///./code_index.db

# Semantic Search (Optional - get key from https://www.voyageai.com/)
VOYAGE_AI_API_KEY=
SEMANTIC_SEARCH_ENABLED=false
SEMANTIC_EMBEDDING_MODEL=voyage-code-3
SEMANTIC_COLLECTION_NAME=code-embeddings

# Reranking Settings
RERANKING_ENABLED=true
RERANKER_TYPE=hybrid

# Redis Cache (Optional)
REDIS_URL=redis://redis:6379
CACHE_TTL=3600

# Security (Change in production\!)
JWT_SECRET_KEY=change-this-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8080"]
