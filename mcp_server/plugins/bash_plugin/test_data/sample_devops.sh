#!/bin/bash

# DevOps deployment script
# Author: DevOps Team
# Description: Automated deployment script for microservices

set -euo pipefail  # Error handling

# Configuration variables
APP_NAME="microservice-api"
ENVIRONMENT="${ENVIRONMENT:-staging}"
VERSION="${VERSION:-latest}"
DOCKER_REGISTRY="registry.company.com"
NAMESPACE="apps"

# Logging setup
LOG_FILE="/var/log/deploy-${APP_NAME}.log"
readonly LOG_LEVEL="${LOG_LEVEL:-INFO}"

# Function: Log messages with timestamp
function log_message() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" | tee -a "$LOG_FILE"
}

# Function: Check prerequisites
check_prerequisites() {
    log_message "INFO" "Checking prerequisites..."
    
    # Check if docker is available
    if ! command -v docker &> /dev/null; then
        log_message "ERROR" "Docker is not installed"
        exit 1
    fi
    
    # Check if kubectl is available
    if ! command -v kubectl &> /dev/null; then
        log_message "ERROR" "kubectl is not installed"
        exit 1
    fi
    
    # Verify cluster connectivity
    if ! kubectl cluster-info &> /dev/null; then
        log_message "ERROR" "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    
    log_message "INFO" "Prerequisites check passed"
}

# Function: Build Docker image
function build_image() {
    local image_tag="${DOCKER_REGISTRY}/${APP_NAME}:${VERSION}"
    
    log_message "INFO" "Building Docker image: $image_tag"
    
    # Build the image
    if docker build -t "$image_tag" .; then
        log_message "INFO" "Image built successfully"
    else
        log_message "ERROR" "Failed to build Docker image"
        exit 1
    fi
    
    # Push to registry
    log_message "INFO" "Pushing image to registry..."
    if docker push "$image_tag"; then
        log_message "INFO" "Image pushed successfully"
    else
        log_message "ERROR" "Failed to push image to registry"
        exit 1
    fi
}

# Function: Deploy to Kubernetes
deploy_to_kubernetes() {
    local deployment_file="k8s/${ENVIRONMENT}/deployment.yaml"
    
    log_message "INFO" "Deploying to Kubernetes environment: $ENVIRONMENT"
    
    # Check if deployment file exists
    if [[ ! -f "$deployment_file" ]]; then
        log_message "ERROR" "Deployment file not found: $deployment_file"
        exit 1
    fi
    
    # Apply the deployment
    if kubectl apply -f "$deployment_file" -n "$NAMESPACE"; then
        log_message "INFO" "Deployment applied successfully"
    else
        log_message "ERROR" "Failed to apply deployment"
        exit 1
    fi
    
    # Wait for rollout to complete
    log_message "INFO" "Waiting for deployment rollout..."
    if kubectl rollout status deployment/"$APP_NAME" -n "$NAMESPACE" --timeout=300s; then
        log_message "INFO" "Deployment completed successfully"
    else
        log_message "ERROR" "Deployment rollout failed"
        exit 1
    fi
}

# Function: Run health checks
function run_health_checks() {
    log_message "INFO" "Running health checks..."
    
    local service_url=$(kubectl get service "$APP_NAME" -n "$NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
    
    if [[ -z "$service_url" ]]; then
        log_message "WARN" "Could not get service URL, using port-forward"
        kubectl port-forward service/"$APP_NAME" 8080:80 -n "$NAMESPACE" &
        local port_forward_pid=$!
        service_url="localhost:8080"
        sleep 5
    fi
    
    # Health check with retry
    local max_retries=5
    local retry_count=0
    
    while [[ $retry_count -lt $max_retries ]]; do
        if curl -f "http://${service_url}/health" &> /dev/null; then
            log_message "INFO" "Health check passed"
            [[ -n "${port_forward_pid:-}" ]] && kill "$port_forward_pid" 2>/dev/null || true
            return 0
        else
            log_message "WARN" "Health check failed, retrying in 10 seconds..."
            sleep 10
            ((retry_count++))
        fi
    done
    
    log_message "ERROR" "Health checks failed after $max_retries attempts"
    [[ -n "${port_forward_pid:-}" ]] && kill "$port_forward_pid" 2>/dev/null || true
    exit 1
}

# Function: Cleanup old deployments
cleanup_old_deployments() {
    log_message "INFO" "Cleaning up old deployments..."
    
    # Keep only the last 3 replica sets
    local old_rs=$(kubectl get rs -n "$NAMESPACE" -l app="$APP_NAME" --sort-by=.metadata.creationTimestamp -o name | head -n -3)
    
    if [[ -n "$old_rs" ]]; then
        echo "$old_rs" | xargs kubectl delete -n "$NAMESPACE"
        log_message "INFO" "Cleaned up old replica sets"
    else
        log_message "INFO" "No old replica sets to clean up"
    fi
}

# Function: Send notification
send_notification() {
    local status="$1"
    local webhook_url="${SLACK_WEBHOOK_URL:-}"
    
    if [[ -n "$webhook_url" ]]; then
        local payload=$(cat <<EOF
{
    "text": "Deployment $status",
    "attachments": [
        {
            "color": "$([[ "$status" == "SUCCESS" ]] && echo "good" || echo "danger")",
            "fields": [
                {"title": "Application", "value": "$APP_NAME", "short": true},
                {"title": "Environment", "value": "$ENVIRONMENT", "short": true},
                {"title": "Version", "value": "$VERSION", "short": true}
            ]
        }
    ]
}
EOF
)
        
        curl -X POST -H 'Content-type: application/json' \
             --data "$payload" \
             "$webhook_url" &> /dev/null
        
        log_message "INFO" "Notification sent"
    fi
}

# Function: Main deployment workflow
main() {
    log_message "INFO" "Starting deployment of $APP_NAME version $VERSION to $ENVIRONMENT"
    
    # Trap to ensure cleanup and notification on exit
    trap 'send_notification "FAILED"' ERR
    trap 'log_message "INFO" "Deployment process completed"' EXIT
    
    # Execute deployment steps
    check_prerequisites
    build_image
    deploy_to_kubernetes
    run_health_checks
    cleanup_old_deployments
    
    send_notification "SUCCESS"
    log_message "INFO" "Deployment completed successfully!"
}

# Script execution
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi