#!/bin/bash
set -euo pipefail

# Production Deployment Script for MCP Server
# This script handles the complete production deployment process

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DEPLOYMENT_ENV=${DEPLOYMENT_ENV:-production}
NAMESPACE=${NAMESPACE:-mcp-system}
DEPLOYMENT_NAME=${DEPLOYMENT_NAME:-code-index-mcp}
DOCKER_REGISTRY=${DOCKER_REGISTRY:-ghcr.io}
DOCKER_IMAGE=${DOCKER_IMAGE:-$DOCKER_REGISTRY/your-org/code-index-mcp}
ROLLBACK_ON_FAILURE=${ROLLBACK_ON_FAILURE:-true}
HEALTH_CHECK_RETRIES=${HEALTH_CHECK_RETRIES:-10}
HEALTH_CHECK_INTERVAL=${HEALTH_CHECK_INTERVAL:-30}

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
    for tool in kubectl docker helm jq curl; do
        if ! command -v $tool &> /dev/null; then
            log_error "$tool is required but not installed"
            exit 1
        fi
    done
    
    # Check Kubernetes connectivity
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    
    # Check namespace exists
    if ! kubectl get namespace $NAMESPACE &> /dev/null; then
        log_warning "Namespace $NAMESPACE does not exist, creating..."
        kubectl create namespace $NAMESPACE
    fi
    
    log_success "Prerequisites check passed"
}

create_backup() {
    log_info "Creating backup of current deployment..."
    
    BACKUP_DIR="backups/$(date +%Y%m%d-%H%M%S)"
    mkdir -p $BACKUP_DIR
    
    # Backup current deployment
    kubectl get deployment $DEPLOYMENT_NAME -n $NAMESPACE -o yaml > $BACKUP_DIR/deployment.yaml 2>/dev/null || true
    kubectl get service -n $NAMESPACE -o yaml > $BACKUP_DIR/services.yaml 2>/dev/null || true
    kubectl get configmap -n $NAMESPACE -o yaml > $BACKUP_DIR/configmaps.yaml 2>/dev/null || true
    kubectl get ingress -n $NAMESPACE -o yaml > $BACKUP_DIR/ingress.yaml 2>/dev/null || true
    
    # Save current image version
    CURRENT_IMAGE=$(kubectl get deployment $DEPLOYMENT_NAME -n $NAMESPACE -o jsonpath="{.spec.template.spec.containers[0].image}" 2>/dev/null || echo "none")
    echo $CURRENT_IMAGE > $BACKUP_DIR/current_image.txt
    
    log_success "Backup created in $BACKUP_DIR"
    echo $BACKUP_DIR
}

pre_deployment_checks() {
    log_info "Running pre-deployment checks..."
    
    # Check if image exists
    if ! docker manifest inspect $DOCKER_IMAGE:$VERSION &> /dev/null; then
        log_error "Docker image $DOCKER_IMAGE:$VERSION not found"
        exit 1
    fi
    
    # Check resource availability
    AVAILABLE_CPU=$(kubectl top nodes -n $NAMESPACE --no-headers | awk '{sum+=$3} END {print 100-sum}')
    AVAILABLE_MEM=$(kubectl top nodes -n $NAMESPACE --no-headers | awk '{sum+=$5} END {print 100-sum}')
    
    if (( $(echo "$AVAILABLE_CPU < 20" | bc -l) )); then
        log_warning "Low CPU availability: ${AVAILABLE_CPU}%"
    fi
    
    if (( $(echo "$AVAILABLE_MEM < 20" | bc -l) )); then
        log_warning "Low memory availability: ${AVAILABLE_MEM}%"
    fi
    
    log_success "Pre-deployment checks completed"
}

update_configuration() {
    log_info "Updating configuration..."
    
    # Update ConfigMaps
    if [ -f "k8s/configmap.yaml" ]; then
        kubectl apply -f k8s/configmap.yaml
    fi
    
    # Update Secrets (if changed)
    if [ -f "k8s/secrets.yaml" ]; then
        kubectl apply -f k8s/secrets.yaml
    fi
    
    # Update environment-specific configs
    if [ -f "k8s/environments/$DEPLOYMENT_ENV/config.yaml" ]; then
        kubectl apply -f k8s/environments/$DEPLOYMENT_ENV/config.yaml
    fi
    
    log_success "Configuration updated"
}

deploy_application() {
    log_info "Deploying application version $VERSION..."
    
    # Update deployment manifest with new image
    sed "s|image: .*|image: $DOCKER_IMAGE:$VERSION|g" k8s/deployment.yaml > /tmp/deployment.yaml
    
    # Apply deployment strategy based on environment
    if [ "$DEPLOYMENT_ENV" == "production" ]; then
        # Blue-Green deployment for production
        deploy_blue_green
    else
        # Rolling update for other environments
        deploy_rolling_update
    fi
}

deploy_rolling_update() {
    log_info "Performing rolling update..."
    
    # Apply the deployment
    kubectl apply -f /tmp/deployment.yaml
    
    # Wait for rollout to complete
    if ! kubectl rollout status deployment/$DEPLOYMENT_NAME -n $NAMESPACE --timeout=600s; then
        log_error "Rollout failed"
        if [ "$ROLLBACK_ON_FAILURE" == "true" ]; then
            rollback_deployment
        fi
        exit 1
    fi
    
    log_success "Rolling update completed"
}

deploy_blue_green() {
    log_info "Performing blue-green deployment..."
    
    # Create green deployment
    GREEN_DEPLOYMENT="${DEPLOYMENT_NAME}-green"
    sed "s|name: $DEPLOYMENT_NAME|name: $GREEN_DEPLOYMENT|g" /tmp/deployment.yaml > /tmp/deployment-green.yaml
    
    # Deploy green
    kubectl apply -f /tmp/deployment-green.yaml
    
    # Wait for green deployment
    if ! kubectl rollout status deployment/$GREEN_DEPLOYMENT -n $NAMESPACE --timeout=600s; then
        log_error "Green deployment failed"
        kubectl delete deployment $GREEN_DEPLOYMENT -n $NAMESPACE
        exit 1
    fi
    
    # Run health checks on green
    if ! health_check_deployment $GREEN_DEPLOYMENT; then
        log_error "Health check failed on green deployment"
        kubectl delete deployment $GREEN_DEPLOYMENT -n $NAMESPACE
        exit 1
    fi
    
    # Switch traffic to green
    kubectl patch service $DEPLOYMENT_NAME -n $NAMESPACE -p "{\"spec\":{\"selector\":{\"app\":\"$GREEN_DEPLOYMENT\"}}}"
    
    # Wait for traffic switch
    sleep 30
    
    # Verify traffic switch
    if ! health_check_service; then
        log_error "Service health check failed after traffic switch"
        # Switch back to blue
        kubectl patch service $DEPLOYMENT_NAME -n $NAMESPACE -p "{\"spec\":{\"selector\":{\"app\":\"$DEPLOYMENT_NAME\"}}}"
        kubectl delete deployment $GREEN_DEPLOYMENT -n $NAMESPACE
        exit 1
    fi
    
    # Delete blue deployment
    kubectl delete deployment $DEPLOYMENT_NAME -n $NAMESPACE --ignore-not-found=true
    
    # Rename green to blue
    kubectl get deployment $GREEN_DEPLOYMENT -n $NAMESPACE -o json | \
        jq ".metadata.name=\"$DEPLOYMENT_NAME\" | .metadata.labels.app=\"$DEPLOYMENT_NAME\" | .spec.selector.matchLabels.app=\"$DEPLOYMENT_NAME\" | .spec.template.metadata.labels.app=\"$DEPLOYMENT_NAME\"" | \
        kubectl apply -f -
    
    # Delete green deployment
    kubectl delete deployment $GREEN_DEPLOYMENT -n $NAMESPACE --ignore-not-found=true
    
    # Update service selector back to original
    kubectl patch service $DEPLOYMENT_NAME -n $NAMESPACE -p "{\"spec\":{\"selector\":{\"app\":\"$DEPLOYMENT_NAME\"}}}"
    
    log_success "Blue-green deployment completed"
}

health_check_deployment() {
    local deployment=$1
    log_info "Running health checks on $deployment..."
    
    # Get a pod from the deployment
    POD=$(kubectl get pods -n $NAMESPACE -l app=$deployment -o jsonpath="{.items[0].metadata.name}")
    
    if [ -z "$POD" ]; then
        log_error "No pods found for deployment $deployment"
        return 1
    fi
    
    # Check pod readiness
    kubectl wait --for=condition=ready pod/$POD -n $NAMESPACE --timeout=300s
    
    # Run internal health check
    kubectl exec -n $NAMESPACE $POD -- curl -f http://localhost:8000/health || return 1
    
    # Check metrics endpoint
    kubectl exec -n $NAMESPACE $POD -- curl -f http://localhost:8000/metrics || return 1
    
    log_success "Health checks passed for $deployment"
    return 0
}

health_check_service() {
    log_info "Running service health checks..."
    
    # Get service endpoint
    SERVICE_URL=$(kubectl get ingress -n $NAMESPACE -o jsonpath="{.items[0].spec.rules[0].host}")
    
    if [ -z "$SERVICE_URL" ]; then
        SERVICE_URL="localhost"
        kubectl port-forward -n $NAMESPACE service/$DEPLOYMENT_NAME 8080:8000 &
        PF_PID=$!
        sleep 5
        SERVICE_URL="http://localhost:8080"
    fi
    
    # Perform health checks
    local retry_count=0
    while [ $retry_count -lt $HEALTH_CHECK_RETRIES ]; do
        if curl -f "${SERVICE_URL}/health" &> /dev/null; then
            log_success "Service health check passed"
            [ ! -z "${PF_PID:-}" ] && kill $PF_PID 2>/dev/null || true
            return 0
        fi
        
        retry_count=$((retry_count + 1))
        log_warning "Health check attempt $retry_count/$HEALTH_CHECK_RETRIES failed, retrying..."
        sleep $HEALTH_CHECK_INTERVAL
    done
    
    [ ! -z "${PF_PID:-}" ] && kill $PF_PID 2>/dev/null || true
    return 1
}

run_smoke_tests() {
    log_info "Running smoke tests..."
    
    # Get service URL
    SERVICE_URL=$(kubectl get ingress -n $NAMESPACE -o jsonpath="{.items[0].spec.rules[0].host}")
    SERVICE_URL="https://${SERVICE_URL}"
    
    # Test endpoints
    endpoints=("/health" "/ready" "/status" "/metrics")
    for endpoint in "${endpoints[@]}"; do
        if ! curl -f "${SERVICE_URL}${endpoint}" &> /dev/null; then
            log_error "Smoke test failed for ${endpoint}"
            return 1
        fi
        log_info "✓ ${endpoint}"
    done
    
    # Test API functionality
    if ! curl -f "${SERVICE_URL}/search?q=test&semantic=false" &> /dev/null; then
        log_error "API functionality test failed"
        return 1
    fi
    
    log_success "All smoke tests passed"
}

update_monitoring() {
    log_info "Updating monitoring configuration..."
    
    # Update Prometheus rules
    if [ -f "monitoring/prometheus/alerts.yml" ]; then
        kubectl create configmap prometheus-alerts -n $NAMESPACE \
            --from-file=monitoring/prometheus/alerts.yml \
            --dry-run=client -o yaml | kubectl apply -f -
    fi
    
    # Update Grafana dashboards
    if [ -d "monitoring/grafana/dashboards" ]; then
        kubectl create configmap grafana-dashboards -n $NAMESPACE \
            --from-file=monitoring/grafana/dashboards/ \
            --dry-run=client -o yaml | kubectl apply -f -
    fi
    
    # Reload Prometheus
    kubectl exec -n $NAMESPACE deployment/prometheus -- kill -HUP 1 2>/dev/null || true
    
    log_success "Monitoring configuration updated"
}

rollback_deployment() {
    log_error "Initiating rollback..."
    
    # Get the backup directory
    LATEST_BACKUP=$(ls -td backups/* | head -1)
    
    if [ -d "$LATEST_BACKUP" ]; then
        # Restore deployment
        kubectl apply -f $LATEST_BACKUP/deployment.yaml
        
        # Wait for rollback
        kubectl rollout status deployment/$DEPLOYMENT_NAME -n $NAMESPACE --timeout=300s
        
        log_success "Rollback completed"
    else
        log_error "No backup found for rollback"
        kubectl rollout undo deployment/$DEPLOYMENT_NAME -n $NAMESPACE
    fi
}

post_deployment_tasks() {
    log_info "Running post-deployment tasks..."
    
    # Clear caches
    kubectl exec -n $NAMESPACE deployment/$DEPLOYMENT_NAME -- curl -X POST http://localhost:8000/cache/clear 2>/dev/null || true
    
    # Run database migrations
    kubectl exec -n $NAMESPACE deployment/$DEPLOYMENT_NAME -- python -m mcp_server.migrations 2>/dev/null || true
    
    # Update deployment annotations
    kubectl annotate deployment $DEPLOYMENT_NAME -n $NAMESPACE \
        deployment.kubernetes.io/revision="$(date +%s)" \
        deployment.mcp/version="$VERSION" \
        deployment.mcp/deployed-by="$USER" \
        deployment.mcp/deployed-at="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        --overwrite
    
    # Send notifications
    send_deployment_notification "success"
    
    log_success "Post-deployment tasks completed"
}

send_deployment_notification() {
    local status=$1
    
    # Slack notification
    if [ ! -z "$SLACK_WEBHOOK" ]; then
        curl -X POST $SLACK_WEBHOOK \
            -H 'Content-Type: application/json' \
            -d "{
                \"text\": \"MCP Server Deployment\",
                \"attachments\": [{
                    \"color\": \"$([ "$status" == "success" ] && echo "good" || echo "danger")\",
                    \"fields\": [
                        {\"title\": \"Environment\", \"value\": \"$DEPLOYMENT_ENV\", \"short\": true},
                        {\"title\": \"Version\", \"value\": \"$VERSION\", \"short\": true},
                        {\"title\": \"Status\", \"value\": \"$status\", \"short\": true},
                        {\"title\": \"Deployed By\", \"value\": \"$USER\", \"short\": true}
                    ]
                }]
            }" 2>/dev/null || true
    fi
    
    # Email notification
    if [ ! -z "$NOTIFICATION_EMAIL" ]; then
        echo "MCP Server deployed to $DEPLOYMENT_ENV (version: $VERSION, status: $status)" | \
            mail -s "MCP Server Deployment Notification" $NOTIFICATION_EMAIL 2>/dev/null || true
    fi
}

cleanup() {
    log_info "Cleaning up..."
    
    # Remove temporary files
    rm -f /tmp/deployment*.yaml
    
    # Kill any port-forward processes
    pkill -f "kubectl port-forward" 2>/dev/null || true
    
    log_success "Cleanup completed"
}

# Main deployment flow
main() {
    log_info "Starting MCP Server deployment to $DEPLOYMENT_ENV"
    log_info "Version: $VERSION"
    
    # Trap for cleanup on exit
    trap cleanup EXIT
    
    # Check version parameter
    if [ -z "${VERSION:-}" ]; then
        log_error "VERSION not specified"
        echo "Usage: VERSION=v1.0.0 $0"
        exit 1
    fi
    
    # Run deployment steps
    check_prerequisites
    BACKUP_DIR=$(create_backup)
    pre_deployment_checks
    update_configuration
    deploy_application
    
    # Post-deployment validation
    if ! health_check_service; then
        log_error "Post-deployment health check failed"
        if [ "$ROLLBACK_ON_FAILURE" == "true" ]; then
            rollback_deployment
        fi
        exit 1
    fi
    
    if ! run_smoke_tests; then
        log_error "Smoke tests failed"
        if [ "$ROLLBACK_ON_FAILURE" == "true" ]; then
            rollback_deployment
        fi
        exit 1
    fi
    
    update_monitoring
    post_deployment_tasks
    
    log_success "Deployment completed successfully!"
    log_info "Backup available at: $BACKUP_DIR"
}

# Run main function
main "$@"