#!/bin/bash

# Docker Deployment Setup Script for Code-Index-MCP
# This script helps set up a containerized deployment environment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check Docker daemon
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running. Please start Docker."
        exit 1
    fi
    
    print_status "Prerequisites check passed!"
}

# Generate secure passwords
generate_password() {
    openssl rand -base64 32 | tr -d "=+/" | cut -c1-25
}

# Setup environment file
setup_environment() {
    print_status "Setting up environment configuration..."
    
    if [ -f ".env.production" ]; then
        print_warning ".env.production already exists. Backing up to .env.production.backup"
        cp .env.production .env.production.backup
    fi
    
    # Copy template
    cp .env.production.template .env.production
    
    # Generate secure values
    DB_PASSWORD=$(generate_password)
    REDIS_PASSWORD=$(generate_password)
    GRAFANA_PASSWORD=$(generate_password)
    SECRET_KEY=$(generate_password)
    JWT_SECRET=$(generate_password)
    API_KEY=$(generate_password)
    
    # Update environment file
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s/your_secure_db_password_here/$DB_PASSWORD/g" .env.production
        sed -i '' "s/your_secure_redis_password_here/$REDIS_PASSWORD/g" .env.production
        sed -i '' "s/your_secure_grafana_password_here/$GRAFANA_PASSWORD/g" .env.production
        sed -i '' "s/your_very_secure_secret_key_here/$SECRET_KEY/g" .env.production
        sed -i '' "s/your_jwt_secret_key_here/$JWT_SECRET/g" .env.production
        sed -i '' "s/your_api_key_here/$API_KEY/g" .env.production
    else
        # Linux
        sed -i "s/your_secure_db_password_here/$DB_PASSWORD/g" .env.production
        sed -i "s/your_secure_redis_password_here/$REDIS_PASSWORD/g" .env.production
        sed -i "s/your_secure_grafana_password_here/$GRAFANA_PASSWORD/g" .env.production
        sed -i "s/your_very_secure_secret_key_here/$SECRET_KEY/g" .env.production
        sed -i "s/your_jwt_secret_key_here/$JWT_SECRET/g" .env.production
        sed -i "s/your_api_key_here/$API_KEY/g" .env.production
    fi
    
    print_status "Environment configuration created with secure passwords"
    print_warning "Please review and update .env.production with your specific settings"
}

# Create necessary directories
create_directories() {
    print_status "Creating necessary directories..."
    
    directories=(
        "logs"
        "logs/nginx"
        "uploads"
        "data"
        "repositories"
        "monitoring/prometheus"
        "monitoring/grafana/dashboards"
        "monitoring/grafana/datasources"
        "database"
        "redis"
    )
    
    for dir in "${directories[@]}"; do
        mkdir -p "$dir"
        print_status "Created directory: $dir"
    done
}

# Create monitoring configuration
setup_monitoring() {
    print_status "Setting up monitoring configuration..."
    
    # Create Prometheus configuration if it doesn't exist
    if [ ! -f "monitoring/prometheus.yml" ]; then
        cat > monitoring/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'mcp-server'
    static_configs:
      - targets: ['mcp-server:8001']
    metrics_path: '/metrics'
EOF
        print_status "Created Prometheus configuration"
    fi
    
    # Create Grafana datasource
    cat > monitoring/grafana/datasources/prometheus.yml << 'EOF'
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
EOF
    print_status "Created Grafana datasource configuration"
}

# Build images
build_images() {
    print_status "Building Docker images..."
    
    docker-compose -f docker-compose.production.yml build
    
    print_status "Docker images built successfully"
}

# Start services
start_services() {
    print_status "Starting services..."
    
    docker-compose -f docker-compose.production.yml up -d
    
    print_status "Services started successfully"
}

# Wait for services to be ready
wait_for_services() {
    print_status "Waiting for services to be ready..."
    
    # Wait for MCP server
    echo -n "Waiting for MCP server"
    for i in {1..30}; do
        if curl -f http://localhost:8000/health &> /dev/null; then
            echo -e " ${GREEN}✓${NC}"
            break
        fi
        echo -n "."
        sleep 2
    done
    
    # Check if services are running
    docker-compose -f docker-compose.production.yml ps
}

# Display information
display_info() {
    print_status "Deployment completed successfully!"
    echo ""
    echo "Service URLs:"
    echo "  - API Server: http://localhost:8000"
    echo "  - Metrics: http://localhost:8001/metrics"
    echo "  - Grafana: http://localhost:3000 (admin/$GRAFANA_PASSWORD)"
    echo "  - Prometheus: http://localhost:9090"
    echo ""
    echo "Credentials have been saved to .env.production"
    echo ""
    echo "Next steps:"
    echo "  1. Review and update .env.production with your domain and settings"
    echo "  2. Configure SSL certificates in nginx/ssl/"
    echo "  3. Update nginx/nginx.conf with your domain name"
    echo "  4. Import Grafana dashboards from monitoring/grafana/dashboards/"
    echo ""
    echo "Useful commands:"
    echo "  - View logs: docker-compose -f docker-compose.production.yml logs -f"
    echo "  - Stop services: docker-compose -f docker-compose.production.yml down"
    echo "  - Restart services: docker-compose -f docker-compose.production.yml restart"
}

# Main function
main() {
    print_status "Starting Docker deployment setup..."
    
    check_prerequisites
    setup_environment
    create_directories
    setup_monitoring
    
    read -p "Do you want to build and start the services now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        build_images
        start_services
        wait_for_services
        display_info
    else
        print_status "Setup completed. Run 'docker-compose -f docker-compose.production.yml up -d' to start services."
    fi
}

# Run main function
main