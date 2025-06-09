#!/bin/bash
#
# Health check script for Code-Index-MCP
# Verifies all components are functioning correctly
#

set -euo pipefail

# Configuration
SERVICE_URL="${SERVICE_URL:-http://localhost:8000}"
TIMEOUT="${TIMEOUT:-30}"
VERBOSE="${VERBOSE:-false}"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Health check results
CHECKS_PASSED=0
CHECKS_FAILED=0
CHECKS_WARNING=0

# Functions
check_endpoint() {
    local endpoint=$1
    local expected_status=${2:-200}
    local description=$3
    
    if [[ "$VERBOSE" == "true" ]]; then
        echo -n "Checking $description... "
    fi
    
    response=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" "${SERVICE_URL}${endpoint}")
    
    if [[ "$response" == "$expected_status" ]]; then
        echo -e "${GREEN}✓${NC} $description"
        ((CHECKS_PASSED++))
        return 0
    else
        echo -e "${RED}✗${NC} $description (HTTP $response)"
        ((CHECKS_FAILED++))
        return 1
    fi
}

check_json_endpoint() {
    local endpoint=$1
    local json_path=$2
    local expected_value=$3
    local description=$4
    
    if [[ "$VERBOSE" == "true" ]]; then
        echo -n "Checking $description... "
    fi
    
    response=$(curl -s --max-time "$TIMEOUT" "${SERVICE_URL}${endpoint}")
    actual_value=$(echo "$response" | jq -r "$json_path" 2>/dev/null || echo "null")
    
    if [[ "$actual_value" == "$expected_value" ]]; then
        echo -e "${GREEN}✓${NC} $description"
        ((CHECKS_PASSED++))
        return 0
    else
        echo -e "${RED}✗${NC} $description (expected: $expected_value, got: $actual_value)"
        ((CHECKS_FAILED++))
        return 1
    fi
}

check_response_time() {
    local endpoint=$1
    local max_time=$2
    local description=$3
    
    if [[ "$VERBOSE" == "true" ]]; then
        echo -n "Checking $description... "
    fi
    
    response_time=$(curl -s -o /dev/null -w "%{time_total}" --max-time "$TIMEOUT" "${SERVICE_URL}${endpoint}")
    response_time_ms=$(echo "$response_time * 1000" | bc | cut -d. -f1)
    
    if (( response_time_ms <= max_time )); then
        echo -e "${GREEN}✓${NC} $description (${response_time_ms}ms)"
        ((CHECKS_PASSED++))
        return 0
    else
        echo -e "${YELLOW}⚠${NC} $description (${response_time_ms}ms > ${max_time}ms)"
        ((CHECKS_WARNING++))
        return 1
    fi
}

check_database() {
    local description="Database connectivity"
    
    if [[ "$VERBOSE" == "true" ]]; then
        echo -n "Checking $description... "
    fi
    
    # Check if database status endpoint responds
    response=$(curl -s "${SERVICE_URL}/api/v1/status" | jq -r '.database.connected' 2>/dev/null || echo "false")
    
    if [[ "$response" == "true" ]]; then
        echo -e "${GREEN}✓${NC} $description"
        ((CHECKS_PASSED++))
        return 0
    else
        echo -e "${RED}✗${NC} $description"
        ((CHECKS_FAILED++))
        return 1
    fi
}

check_plugins() {
    local description="Plugin system"
    
    if [[ "$VERBOSE" == "true" ]]; then
        echo -n "Checking $description... "
    fi
    
    # Check plugin count
    plugin_count=$(curl -s "${SERVICE_URL}/api/v1/status" | jq -r '.plugins.count' 2>/dev/null || echo "0")
    
    if [[ "$plugin_count" -gt 40 ]]; then
        echo -e "${GREEN}✓${NC} $description ($plugin_count plugins loaded)"
        ((CHECKS_PASSED++))
        return 0
    else
        echo -e "${RED}✗${NC} $description (only $plugin_count plugins loaded)"
        ((CHECKS_FAILED++))
        return 1
    fi
}

check_search_functionality() {
    local description="Search functionality"
    
    if [[ "$VERBOSE" == "true" ]]; then
        echo -n "Checking $description... "
    fi
    
    # Perform test search
    response=$(curl -s -X GET "${SERVICE_URL}/api/v1/search?q=test&limit=1" \
        -H "Content-Type: application/json")
    
    status=$(echo "$response" | jq -r '.status' 2>/dev/null || echo "error")
    
    if [[ "$status" == "success" ]]; then
        echo -e "${GREEN}✓${NC} $description"
        ((CHECKS_PASSED++))
        return 0
    else
        echo -e "${RED}✗${NC} $description"
        ((CHECKS_FAILED++))
        return 1
    fi
}

check_memory_usage() {
    local description="Memory usage"
    
    if [[ "$VERBOSE" == "true" ]]; then
        echo -n "Checking $description... "
    fi
    
    # Get memory metrics
    memory_mb=$(curl -s "${SERVICE_URL}/metrics" | grep '^process_resident_memory_bytes' | awk '{print $2/1024/1024}' | cut -d. -f1)
    
    if [[ -n "$memory_mb" ]] && [[ "$memory_mb" -lt 2048 ]]; then
        echo -e "${GREEN}✓${NC} $description (${memory_mb}MB)"
        ((CHECKS_PASSED++))
        return 0
    elif [[ -n "$memory_mb" ]]; then
        echo -e "${YELLOW}⚠${NC} $description (${memory_mb}MB > 2GB)"
        ((CHECKS_WARNING++))
        return 1
    else
        echo -e "${RED}✗${NC} $description (unable to get metrics)"
        ((CHECKS_FAILED++))
        return 1
    fi
}

main() {
    echo "=================================="
    echo "Code-Index-MCP Health Check"
    echo "=================================="
    echo "Service URL: $SERVICE_URL"
    echo ""
    
    # Basic connectivity
    echo "Basic Connectivity:"
    check_endpoint "/health" 200 "Health endpoint"
    check_endpoint "/api/v1/status" 200 "Status endpoint"
    check_endpoint "/metrics" 200 "Metrics endpoint"
    echo ""
    
    # Component health
    echo "Component Health:"
    check_database
    check_plugins
    check_json_endpoint "/health" ".status" "healthy" "Overall health status"
    echo ""
    
    # Functionality
    echo "Functionality:"
    check_search_functionality
    check_endpoint "/api/v1/languages" 200 "Languages endpoint"
    echo ""
    
    # Performance
    echo "Performance:"
    check_response_time "/health" 100 "Health check response time"
    check_response_time "/api/v1/status" 200 "Status check response time"
    check_memory_usage
    echo ""
    
    # Summary
    echo "=================================="
    echo "Summary:"
    echo -e "${GREEN}Passed:${NC} $CHECKS_PASSED"
    echo -e "${YELLOW}Warnings:${NC} $CHECKS_WARNING"
    echo -e "${RED}Failed:${NC} $CHECKS_FAILED"
    echo ""
    
    # Overall status
    if [[ $CHECKS_FAILED -eq 0 ]]; then
        echo -e "${GREEN}✓ All health checks passed!${NC}"
        exit 0
    else
        echo -e "${RED}✗ Some health checks failed!${NC}"
        exit 1
    fi
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --url)
            SERVICE_URL="$2"
            shift 2
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --verbose|-v)
            VERBOSE="true"
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --url URL        Service URL (default: http://localhost:8000)"
            echo "  --timeout SEC    Request timeout in seconds (default: 30)"
            echo "  --verbose, -v    Verbose output"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Run health checks
main