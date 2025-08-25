#!/bin/bash

# AMC Trading System - Failure Cases Tests
# Tests environment variable validation and proper error responses

set -euo pipefail

# Ensure we're using bash (needed for associative arrays)
if [ -z "${BASH_VERSION:-}" ]; then
    echo "This script requires bash" >&2
    exit 1
fi

BASE_URL="${BASE_URL:-http://localhost:8000}"
CURL_TIMEOUT=10
EXIT_CODE=0

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date '+%H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[$(date '+%H:%M:%S')] ERROR: $1${NC}" >&2
    EXIT_CODE=1
}

warn() {
    echo -e "${YELLOW}[$(date '+%H:%M:%S')] WARNING: $1${NC}"
}

# Critical environment variables that should cause service failure
CRITICAL_ENV_VARS=(
    "ALPACA_API_KEY"
    "ALPACA_SECRET_KEY"
    "ALPACA_BASE_URL"
    "CLAUDE_API_KEY"
    "POLYGON_API_KEY"
)

# Store original environment variables in temporary files
BACKUP_DIR="/tmp/amc_env_backup_$$"

backup_env() {
    mkdir -p "$BACKUP_DIR"
    for var in "${CRITICAL_ENV_VARS[@]}"; do
        if [ -n "${!var:-}" ]; then
            echo "${!var}" > "$BACKUP_DIR/$var"
        fi
    done
    log "Backed up environment variables to $BACKUP_DIR"
}

restore_env() {
    for var in "${CRITICAL_ENV_VARS[@]}"; do
        if [ -f "$BACKUP_DIR/$var" ]; then
            export "$var=$(cat "$BACKUP_DIR/$var")"
        else
            unset "$var" 2>/dev/null || true
        fi
    done
    rm -rf "$BACKUP_DIR" 2>/dev/null || true
    log "Restored environment variables"
}

# Test helper function
test_health_failure() {
    local missing_var="$1"
    local description="Health check with missing $missing_var"
    
    log "Testing: $description"
    
    response=$(curl -s -w "\n%{http_code}" -X GET \
        --max-time "$CURL_TIMEOUT" \
        "$BASE_URL/health" 2>/dev/null || true)
    
    if [ -z "$response" ]; then
        error "No response from health endpoint when $missing_var is missing"
        return 1
    fi
    
    status_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | sed '$d')
    
    # Expect 503 Service Unavailable when critical env vars are missing
    if [ "$status_code" != "503" ]; then
        error "$description - Expected status 503, got $status_code"
        echo "Response body: $body"
        return 1
    fi
    
    log "✓ $description - Status $status_code (expected failure)"
    
    # Validate error response structure
    if ! echo "$body" | jq -e '.status' >/dev/null 2>&1; then
        error "Health error response missing 'status' field"
        return 1
    fi
    
    if ! echo "$body" | jq -e '.components' >/dev/null 2>&1; then
        error "Health error response missing 'components' field"
        return 1
    fi
    
    status=$(echo "$body" | jq -r '.status')
    if [ "$status" != "unhealthy" ]; then
        error "Expected status 'unhealthy', got '$status'"
        return 1
    fi
    
    # Check that the specific component is marked as false
    local component_key
    case "$missing_var" in
        "ALPACA_API_KEY"|"ALPACA_SECRET_KEY"|"ALPACA_BASE_URL")
            component_key="alpaca_connection"
            ;;
        "CLAUDE_API_KEY")
            component_key="claude_api"
            ;;
        "POLYGON_API_KEY")
            component_key="market_data"
            ;;
        *)
            component_key="unknown"
            ;;
    esac
    
    component_status=$(echo "$body" | jq -r ".components.$component_key // \"not_found\"")
    if [ "$component_status" != "false" ] && [ "$component_status" != "unhealthy" ]; then
        error "Expected component '$component_key' to be false/unhealthy, got '$component_status'"
        return 1
    fi
    
    log "✓ Component '$component_key' correctly marked as unhealthy"
    return 0
}

# Wait for service to restart/reload
wait_for_service_reload() {
    log "Waiting for service to reload configuration..."
    sleep 5
}

# Test that service is healthy with all env vars present
test_baseline_health() {
    log "=== Baseline Health Test ==="
    
    response=$(curl -s -w "\n%{http_code}" -X GET \
        --max-time "$CURL_TIMEOUT" \
        "$BASE_URL/health" 2>/dev/null || true)
    
    if [ -z "$response" ]; then
        warn "Service appears to be down - cannot establish baseline"
        return 0  # Don't fail the test suite if service is down
    fi
    
    status_code=$(echo "$response" | tail -n 1)
    
    if [ "$status_code" == "200" ]; then
        log "✓ Baseline: Service is healthy with all environment variables"
    else
        warn "Baseline: Service not healthy (status: $status_code) - continuing with failure tests"
    fi
}

# Main test execution
main() {
    log "AMC Trading System - Environment Failure Tests"
    log "Testing proper error handling for missing critical environment variables"
    
    # Backup original environment
    backup_env
    
    # Test baseline health
    test_baseline_health
    
    # Test each critical environment variable
    for var in "${CRITICAL_ENV_VARS[@]}"; do
        log "=== Testing Missing $var ==="
        
        # Unset the specific environment variable
        if [ -n "${!var:-}" ]; then
            unset "$var"
            log "Unset $var"
        else
            warn "$var was already unset"
        fi
        
        wait_for_service_reload
        
        # Test that health endpoint returns 503
        if ! test_health_failure "$var"; then
            error "Failed test for missing $var"
        fi
        
        # Restore the environment variable
        if [ -n "${ORIGINAL_VALUES[$var]:-}" ]; then
            export "$var=${ORIGINAL_VALUES[$var]}"
            log "Restored $var"
        fi
        
        wait_for_service_reload
        
        echo  # Add spacing between tests
    done
    
    # Restore all environment variables
    restore_env
    
    # Final verification that service is healthy again
    log "=== Final Health Verification ==="
    wait_for_service_reload
    
    response=$(curl -s -w "\n%{http_code}" -X GET \
        --max-time "$CURL_TIMEOUT" \
        "$BASE_URL/health" 2>/dev/null || true)
    
    if [ -n "$response" ]; then
        status_code=$(echo "$response" | tail -n 1)
        if [ "$status_code" == "200" ]; then
            log "✓ Service restored to healthy state"
        else
            warn "Service not fully restored (status: $status_code)"
        fi
    fi
    
    # Final Results
    log "=== Failure Test Results ==="
    if [ $EXIT_CODE -eq 0 ]; then
        log "All failure case tests passed!"
    else
        error "Some failure case tests failed!"
    fi
    
    exit $EXIT_CODE
}

# Handle script interruption
cleanup() {
    log "Script interrupted, restoring environment..."
    restore_env
    exit 1
}

trap cleanup INT TERM

# Run main function
main "$@"