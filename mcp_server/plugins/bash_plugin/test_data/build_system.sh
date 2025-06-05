#!/bin/bash

# Advanced Build System Script
# Description: Comprehensive build automation for multi-component applications
# Author: DevOps Team
# Version: 2.1.0

set -euo pipefail

# Global variables
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
readonly BUILD_DIR="$PROJECT_ROOT/build"
readonly LOG_DIR="$PROJECT_ROOT/logs"
readonly CONFIG_FILE="$PROJECT_ROOT/build.config"

# Build configuration
BUILD_TYPE="${BUILD_TYPE:-release}"
PARALLEL_JOBS="${PARALLEL_JOBS:-$(nproc)}"
VERBOSE="${VERBOSE:-false}"
CLEAN_BUILD="${CLEAN_BUILD:-false}"

# Color codes for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $*" | tee -a "$LOG_DIR/build.log"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*" | tee -a "$LOG_DIR/build.log"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" | tee -a "$LOG_DIR/build.log"
}

log_debug() {
    if [[ "$VERBOSE" == "true" ]]; then
        echo -e "${BLUE}[DEBUG]${NC} $*" | tee -a "$LOG_DIR/build.log"
    fi
}

# Utility functions
check_prerequisites() {
    log_info "Checking build prerequisites..."
    
    local missing_tools=()
    
    # Check required tools
    for tool in git node npm dotnet docker kubectl; do
        if ! command -v "$tool" &> /dev/null; then
            missing_tools+=("$tool")
        fi
    done
    
    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        return 1
    fi
    
    log_info "All prerequisites satisfied"
}

setup_build_environment() {
    log_info "Setting up build environment..."
    
    # Create necessary directories
    mkdir -p "$BUILD_DIR" "$LOG_DIR"
    
    # Load configuration if exists
    if [[ -f "$CONFIG_FILE" ]]; then
        # shellcheck source=/dev/null
        source "$CONFIG_FILE"
        log_info "Loaded configuration from $CONFIG_FILE"
    fi
    
    # Set up environment variables
    export NODE_ENV="${NODE_ENV:-production}"
    export DOTNET_CLI_TELEMETRY_OPTOUT=1
    export DOCKER_BUILDKIT=1
    
    log_debug "Build environment configured"
    log_debug "BUILD_TYPE: $BUILD_TYPE"
    log_debug "PARALLEL_JOBS: $PARALLEL_JOBS"
    log_debug "NODE_ENV: $NODE_ENV"
}

# Build functions
build_frontend() {
    log_info "Building frontend application..."
    
    local frontend_dir="$PROJECT_ROOT/frontend"
    if [[ ! -d "$frontend_dir" ]]; then
        log_warn "Frontend directory not found, skipping frontend build"
        return 0
    fi
    
    cd "$frontend_dir"
    
    # Install dependencies
    log_info "Installing frontend dependencies..."
    npm ci --silent
    
    # Run linting
    if npm run lint &>/dev/null; then
        log_info "Frontend linting passed"
    else
        log_warn "Frontend linting failed, continuing build"
    fi
    
    # Run tests
    if [[ "$BUILD_TYPE" != "quick" ]]; then
        log_info "Running frontend tests..."
        npm run test -- --watchAll=false --ci
    fi
    
    # Build application
    log_info "Building frontend application..."
    npm run build
    
    # Copy artifacts
    cp -r dist/* "$BUILD_DIR/frontend/"
    
    log_info "Frontend build completed successfully"
}

build_backend() {
    log_info "Building backend application..."
    
    local backend_dir="$PROJECT_ROOT/backend"
    if [[ ! -d "$backend_dir" ]]; then
        log_warn "Backend directory not found, skipping backend build"
        return 0
    fi
    
    cd "$backend_dir"
    
    # Restore packages
    log_info "Restoring backend packages..."
    dotnet restore --verbosity minimal
    
    # Run tests
    if [[ "$BUILD_TYPE" != "quick" ]]; then
        log_info "Running backend tests..."
        dotnet test --no-restore --logger "console;verbosity=minimal"
    fi
    
    # Build application
    log_info "Building backend application..."
    dotnet build --no-restore --configuration Release
    
    # Publish application
    log_info "Publishing backend application..."
    dotnet publish --no-build --configuration Release --output "$BUILD_DIR/backend"
    
    log_info "Backend build completed successfully"
}

build_docker_images() {
    log_info "Building Docker images..."
    
    local dockerfile_frontend="$PROJECT_ROOT/Dockerfile.frontend"
    local dockerfile_backend="$PROJECT_ROOT/Dockerfile.backend"
    
    # Build frontend image
    if [[ -f "$dockerfile_frontend" ]]; then
        log_info "Building frontend Docker image..."
        docker build -f "$dockerfile_frontend" -t "myapp-frontend:latest" "$PROJECT_ROOT"
    fi
    
    # Build backend image
    if [[ -f "$dockerfile_backend" ]]; then
        log_info "Building backend Docker image..."
        docker build -f "$dockerfile_backend" -t "myapp-backend:latest" "$PROJECT_ROOT"
    fi
    
    log_info "Docker images built successfully"
}

# Database functions
run_database_migrations() {
    log_info "Running database migrations..."
    
    local migrations_dir="$PROJECT_ROOT/database/migrations"
    if [[ ! -d "$migrations_dir" ]]; then
        log_info "No migrations directory found, skipping migrations"
        return 0
    fi
    
    # Run migrations using Entity Framework
    cd "$PROJECT_ROOT/backend"
    dotnet ef database update --verbose
    
    log_info "Database migrations completed"
}

# Quality assurance functions
run_security_scan() {
    log_info "Running security scan..."
    
    # Frontend security scan
    if command -v npm-audit &> /dev/null; then
        cd "$PROJECT_ROOT/frontend"
        npm audit --audit-level moderate
    fi
    
    # Backend security scan
    if command -v dotnet &> /dev/null; then
        cd "$PROJECT_ROOT/backend"
        dotnet list package --vulnerable --include-transitive
    fi
    
    log_info "Security scan completed"
}

run_performance_tests() {
    log_info "Running performance tests..."
    
    local performance_dir="$PROJECT_ROOT/tests/performance"
    if [[ ! -d "$performance_dir" ]]; then
        log_info "No performance tests directory found, skipping performance tests"
        return 0
    fi
    
    cd "$performance_dir"
    
    # Run load tests using Artillery or similar tool
    if command -v artillery &> /dev/null; then
        artillery run load-test.yml
    fi
    
    log_info "Performance tests completed"
}

# Deployment functions
deploy_to_staging() {
    log_info "Deploying to staging environment..."
    
    # Deploy using Kubernetes
    if command -v kubectl &> /dev/null; then
        kubectl apply -f "$PROJECT_ROOT/k8s/staging/" --namespace=staging
        kubectl rollout status deployment/myapp-backend --namespace=staging
        kubectl rollout status deployment/myapp-frontend --namespace=staging
    fi
    
    log_info "Staging deployment completed"
}

deploy_to_production() {
    log_info "Deploying to production environment..."
    
    # Confirmation prompt
    read -p "Are you sure you want to deploy to production? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Production deployment cancelled"
        return 0
    fi
    
    # Deploy using Kubernetes
    if command -v kubectl &> /dev/null; then
        kubectl apply -f "$PROJECT_ROOT/k8s/production/" --namespace=production
        kubectl rollout status deployment/myapp-backend --namespace=production
        kubectl rollout status deployment/myapp-frontend --namespace=production
    fi
    
    log_info "Production deployment completed"
}

# Cleanup functions
cleanup_build_artifacts() {
    log_info "Cleaning up build artifacts..."
    
    if [[ "$CLEAN_BUILD" == "true" ]]; then
        rm -rf "$BUILD_DIR"
        log_info "Build directory cleaned"
    fi
    
    # Clean Docker images
    if command -v docker &> /dev/null; then
        docker image prune -f
        log_info "Docker images pruned"
    fi
    
    log_info "Cleanup completed"
}

# Error handling
handle_error() {
    local exit_code=$?
    log_error "Build failed with exit code $exit_code"
    log_error "Last command: $BASH_COMMAND"
    
    # Send notification
    if command -v curl &> /dev/null && [[ -n "${SLACK_WEBHOOK:-}" ]]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"Build failed: $BASH_COMMAND\"}" \
            "$SLACK_WEBHOOK"
    fi
    
    cleanup_build_artifacts
    exit $exit_code
}

# Signal handling
handle_interrupt() {
    log_warn "Build interrupted by user"
    cleanup_build_artifacts
    exit 130
}

# Help function
show_help() {
    cat << EOF
Usage: $0 [OPTIONS] [TARGET]

Advanced Build System for Multi-Component Applications

OPTIONS:
    -h, --help              Show this help message
    -v, --verbose           Enable verbose output
    -c, --clean             Clean build artifacts before building
    -t, --type TYPE         Build type: quick, release, debug (default: release)
    -j, --jobs JOBS         Number of parallel jobs (default: $(nproc))
    
TARGETS:
    all                     Build all components (default)
    frontend                Build only frontend
    backend                 Build only backend
    docker                  Build Docker images
    test                    Run all tests
    security                Run security scans
    performance             Run performance tests
    deploy-staging          Deploy to staging
    deploy-production       Deploy to production
    clean                   Clean all build artifacts

ENVIRONMENT VARIABLES:
    BUILD_TYPE              Build type (quick, release, debug)
    PARALLEL_JOBS          Number of parallel jobs
    VERBOSE                Enable verbose output (true/false)
    CLEAN_BUILD            Clean before build (true/false)
    NODE_ENV               Node.js environment
    SLACK_WEBHOOK          Slack webhook for notifications

EXAMPLES:
    $0                      # Build all components
    $0 frontend             # Build only frontend
    $0 --clean --verbose    # Clean build with verbose output
    $0 --type debug frontend # Debug build of frontend
    
EOF
}

# Main execution function
main() {
    # Set up error handling
    trap handle_error ERR
    trap handle_interrupt INT TERM
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -v|--verbose)
                VERBOSE="true"
                shift
                ;;
            -c|--clean)
                CLEAN_BUILD="true"
                shift
                ;;
            -t|--type)
                BUILD_TYPE="$2"
                shift 2
                ;;
            -j|--jobs)
                PARALLEL_JOBS="$2"
                shift 2
                ;;
            all|frontend|backend|docker|test|security|performance|deploy-staging|deploy-production|clean)
                TARGET="$1"
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Default target
    TARGET="${TARGET:-all}"
    
    log_info "Starting build process..."
    log_info "Target: $TARGET"
    log_info "Build type: $BUILD_TYPE"
    
    # Setup
    setup_build_environment
    check_prerequisites
    
    # Execute target
    case $TARGET in
        all)
            build_frontend
            build_backend
            build_docker_images
            ;;
        frontend)
            build_frontend
            ;;
        backend)
            build_backend
            ;;
        docker)
            build_docker_images
            ;;
        test)
            build_frontend
            build_backend
            run_security_scan
            run_performance_tests
            ;;
        security)
            run_security_scan
            ;;
        performance)
            run_performance_tests
            ;;
        deploy-staging)
            deploy_to_staging
            ;;
        deploy-production)
            deploy_to_production
            ;;
        clean)
            cleanup_build_artifacts
            ;;
        *)
            log_error "Unknown target: $TARGET"
            show_help
            exit 1
            ;;
    esac
    
    log_info "Build process completed successfully!"
}

# Execute main function if script is run directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi