#!/bin/bash
#
# Production deployment script for Code-Index-MCP
# This script handles the complete production deployment process
#

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DEPLOYMENT_ENV="${DEPLOYMENT_ENV:-production}"
DOCKER_REGISTRY="${DOCKER_REGISTRY:-}"
VERSION="${VERSION:-latest}"
NAMESPACE="${NAMESPACE:-code-index-mcp}"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check required tools
    local required_tools=("docker" "docker-compose" "git")
    if [[ "$DEPLOYMENT_ENV" == "kubernetes" ]]; then
        required_tools+=("kubectl" "helm")
    fi
    
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            log_error "$tool is not installed"
            exit 1
        fi
    done
    
    # Check Docker daemon
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi
    
    # Check environment variables
    if [[ -z "${DATABASE_URL:-}" ]]; then
        log_error "DATABASE_URL environment variable is not set"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

build_images() {
    log_info "Building Docker images..."
    
    cd "$PROJECT_ROOT"
    
    # Build production image
    docker build \
        -f Dockerfile.production \
        -t code-index-mcp:${VERSION} \
        -t code-index-mcp:latest \
        --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
        --build-arg VERSION=${VERSION} \
        .
    
    # Tag for registry if specified
    if [[ -n "$DOCKER_REGISTRY" ]]; then
        docker tag code-index-mcp:${VERSION} ${DOCKER_REGISTRY}/code-index-mcp:${VERSION}
        docker tag code-index-mcp:latest ${DOCKER_REGISTRY}/code-index-mcp:latest
    fi
    
    log_success "Docker images built successfully"
}

run_tests() {
    log_info "Running production tests..."
    
    # Run smoke tests
    docker run --rm \
        -e DATABASE_URL="$DATABASE_URL" \
        code-index-mcp:${VERSION} \
        python -m pytest tests/test_smoke.py -v
    
    # Run health check
    docker run --rm \
        --name code-index-mcp-test \
        -d \
        -p 8000:8000 \
        code-index-mcp:${VERSION}
    
    sleep 5
    
    # Check health endpoint
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        log_success "Health check passed"
    else
        log_error "Health check failed"
        docker stop code-index-mcp-test
        exit 1
    fi
    
    docker stop code-index-mcp-test
    
    log_success "Production tests passed"
}

push_images() {
    if [[ -z "$DOCKER_REGISTRY" ]]; then
        log_warning "No Docker registry specified, skipping push"
        return
    fi
    
    log_info "Pushing images to registry..."
    
    docker push ${DOCKER_REGISTRY}/code-index-mcp:${VERSION}
    docker push ${DOCKER_REGISTRY}/code-index-mcp:latest
    
    log_success "Images pushed to registry"
}

deploy_docker_compose() {
    log_info "Deploying with Docker Compose..."
    
    cd "$PROJECT_ROOT"
    
    # Create deployment directory
    DEPLOY_DIR="/opt/code-index-mcp"
    sudo mkdir -p "$DEPLOY_DIR"
    
    # Copy necessary files
    sudo cp docker-compose.production.yml "$DEPLOY_DIR/docker-compose.yml"
    sudo cp .env.production "$DEPLOY_DIR/.env" || true
    
    # Deploy
    cd "$DEPLOY_DIR"
    sudo docker-compose down || true
    sudo docker-compose up -d
    
    # Wait for services to be ready
    sleep 10
    
    # Check deployment
    if sudo docker-compose ps | grep -q "Up"; then
        log_success "Docker Compose deployment successful"
    else
        log_error "Docker Compose deployment failed"
        sudo docker-compose logs
        exit 1
    fi
}

deploy_kubernetes() {
    log_info "Deploying to Kubernetes..."
    
    cd "$PROJECT_ROOT/k8s"
    
    # Create namespace
    kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
    
    # Apply configurations
    kubectl apply -n "$NAMESPACE" -f configmap.yaml
    kubectl apply -n "$NAMESPACE" -f secrets.yaml
    kubectl apply -n "$NAMESPACE" -f deployment.yaml
    kubectl apply -n "$NAMESPACE" -f service.yaml
    kubectl apply -n "$NAMESPACE" -f ingress.yaml
    
    # Wait for deployment
    kubectl rollout status deployment/code-index-mcp -n "$NAMESPACE" --timeout=300s
    
    # Check pods
    if kubectl get pods -n "$NAMESPACE" | grep -q "Running"; then
        log_success "Kubernetes deployment successful"
    else
        log_error "Kubernetes deployment failed"
        kubectl describe pods -n "$NAMESPACE"
        exit 1
    fi
}

run_migrations() {
    log_info "Running database migrations..."
    
    if [[ "$DEPLOYMENT_ENV" == "kubernetes" ]]; then
        # Run as Kubernetes job
        kubectl run migrations \
            --image=code-index-mcp:${VERSION} \
            --rm -i --restart=Never \
            -n "$NAMESPACE" \
            -- python -m mcp_server.storage.migrations
    else
        # Run with Docker
        docker run --rm \
            -e DATABASE_URL="$DATABASE_URL" \
            code-index-mcp:${VERSION} \
            python -m mcp_server.storage.migrations
    fi
    
    log_success "Migrations completed"
}

setup_monitoring() {
    log_info "Setting up monitoring..."
    
    if [[ "$DEPLOYMENT_ENV" == "kubernetes" ]]; then
        # Deploy Prometheus ServiceMonitor
        cat <<EOF | kubectl apply -f -
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: code-index-mcp
  namespace: $NAMESPACE
spec:
  selector:
    matchLabels:
      app: code-index-mcp
  endpoints:
  - port: metrics
    interval: 30s
EOF
    else
        # Ensure Prometheus scrape config exists
        PROMETHEUS_CONFIG="/etc/prometheus/prometheus.yml"
        if [[ -f "$PROMETHEUS_CONFIG" ]]; then
            log_info "Adding Prometheus scrape config..."
            # Add scrape config if not exists
            if ! grep -q "code-index-mcp" "$PROMETHEUS_CONFIG"; then
                cat <<EOF | sudo tee -a "$PROMETHEUS_CONFIG"
  - job_name: 'code-index-mcp'
    static_configs:
    - targets: ['localhost:8000']
EOF
                # Reload Prometheus
                sudo systemctl reload prometheus || true
            fi
        fi
    fi
    
    log_success "Monitoring setup completed"
}

verify_deployment() {
    log_info "Verifying deployment..."
    
    # Get service URL
    if [[ "$DEPLOYMENT_ENV" == "kubernetes" ]]; then
        SERVICE_URL=$(kubectl get ingress -n "$NAMESPACE" -o jsonpath='{.items[0].spec.rules[0].host}')
    else
        SERVICE_URL="localhost:8000"
    fi
    
    # Check endpoints
    local endpoints=("/health" "/api/v1/status" "/metrics")
    
    for endpoint in "${endpoints[@]}"; do
        if curl -f "http://${SERVICE_URL}${endpoint}" > /dev/null 2>&1; then
            log_success "Endpoint ${endpoint} is responding"
        else
            log_warning "Endpoint ${endpoint} is not responding"
        fi
    done
    
    # Run smoke test
    log_info "Running smoke test..."
    curl -X POST "http://${SERVICE_URL}/api/v1/reindex" \
        -H "Content-Type: application/json" \
        -d '{"paths": ["/tmp/test"], "recursive": false}' || true
    
    log_success "Deployment verification completed"
}

create_backup() {
    log_info "Creating backup of previous deployment..."
    
    BACKUP_DIR="/var/backups/code-index-mcp"
    sudo mkdir -p "$BACKUP_DIR"
    
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE="${BACKUP_DIR}/backup_${TIMESTAMP}.tar.gz"
    
    # Backup database
    if [[ "$DEPLOYMENT_ENV" == "kubernetes" ]]; then
        kubectl exec -n "$NAMESPACE" deployment/code-index-mcp -- \
            sqlite3 /app/data/index.db .dump > "${BACKUP_DIR}/db_${TIMESTAMP}.sql"
    else
        docker exec code-index-mcp \
            sqlite3 /app/data/index.db .dump > "${BACKUP_DIR}/db_${TIMESTAMP}.sql" || true
    fi
    
    # Create tarball
    sudo tar -czf "$BACKUP_FILE" -C "$BACKUP_DIR" "db_${TIMESTAMP}.sql" 2>/dev/null || true
    
    log_success "Backup created: $BACKUP_FILE"
}

main() {
    log_info "Starting Code-Index-MCP production deployment..."
    log_info "Environment: $DEPLOYMENT_ENV"
    log_info "Version: $VERSION"
    
    # Deployment steps
    check_prerequisites
    create_backup
    build_images
    run_tests
    push_images
    
    # Deploy based on environment
    if [[ "$DEPLOYMENT_ENV" == "kubernetes" ]]; then
        deploy_kubernetes
    else
        deploy_docker_compose
    fi
    
    run_migrations
    setup_monitoring
    verify_deployment
    
    log_success "Deployment completed successfully!"
    log_info "Service is available at: http://${SERVICE_URL:-localhost:8000}"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --env)
            DEPLOYMENT_ENV="$2"
            shift 2
            ;;
        --version)
            VERSION="$2"
            shift 2
            ;;
        --registry)
            DOCKER_REGISTRY="$2"
            shift 2
            ;;
        --namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --env ENV          Deployment environment (docker-compose|kubernetes)"
            echo "  --version VERSION  Version to deploy"
            echo "  --registry URL     Docker registry URL"
            echo "  --namespace NS     Kubernetes namespace"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Run main deployment
main