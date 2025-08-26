#!/bin/bash

# AMC Trading System - Smoke Tests
# Black-box acceptance checks for core functionality

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
API="${API:-https://amc-trader.onrender.com}"
CURL_TIMEOUT=30
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

# Test helper function
test_endpoint() {
    local method="$1"
    local endpoint="$2"
    local expected_status="$3"
    local description="$4"
    local data="${5:-}"
    
    log "Testing: $description"
    
    if [ -n "$data" ]; then
        response=$(curl -s -w "\n%{http_code}" -X "$method" \
            -H "Content-Type: application/json" \
            -d "$data" \
            --max-time "$CURL_TIMEOUT" \
            "$BASE_URL$endpoint" 2>/dev/null || true)
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" \
            --max-time "$CURL_TIMEOUT" \
            "$BASE_URL$endpoint" 2>/dev/null || true)
    fi
    
    if [ -z "$response" ]; then
        error "No response from $endpoint"
        return 1
    fi
    
    status_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$status_code" != "$expected_status" ]; then
        error "$description - Expected status $expected_status, got $status_code"
        echo "Response body: $body"
        return 1
    fi
    
    log "✓ $description - Status $status_code"
    
    # Return the response body for further processing
    echo "$body"
}

# Test 1: Health Check
log "=== Health Check Test ==="
health_response=$(test_endpoint "GET" "/health" "200" "Health endpoint check")

if [ $? -eq 0 ]; then
    # Validate health response structure
    if ! echo "$health_response" | jq -e '.status' >/dev/null 2>&1; then
        error "Health response missing 'status' field"
    fi
    
    if ! echo "$health_response" | jq -e '.components' >/dev/null 2>&1; then
        error "Health response missing 'components' field"
    fi
    
    status=$(echo "$health_response" | jq -r '.status')
    if [ "$status" != "healthy" ]; then
        error "System not healthy: status=$status"
    fi
else
    error "Health check failed"
fi

# Test 2: Discovery Run
log "=== Discovery Test ==="
discovery_response=$(test_endpoint "POST" "/discovery/run" "200" "Run discovery once")

if [ $? -eq 0 ]; then
    # Validate discovery response
    if ! echo "$discovery_response" | jq -e '.opportunities' >/dev/null 2>&1; then
        error "Discovery response missing 'opportunities' field"
    fi
    
    opportunities=$(echo "$discovery_response" | jq '.opportunities | length')
    log "Discovery found $opportunities opportunities"
else
    error "Discovery run failed"
fi

# Test 3: Recommendations
log "=== Recommendations Test ==="
recommendations_response=$(test_endpoint "GET" "/recommendations" "200" "Get trading recommendations")

if [ $? -eq 0 ]; then
    # Validate recommendations response structure
    if ! echo "$recommendations_response" | jq -e '.recommendations' >/dev/null 2>&1; then
        error "Recommendations response missing 'recommendations' field"
    fi
    
    rec_count=$(echo "$recommendations_response" | jq '.recommendations | length')
    log "Found $rec_count recommendations"
else
    error "Recommendations fetch failed"
fi

# Test 4: Holdings
log "=== Holdings Test ==="
holdings_response=$(test_endpoint "GET" "/holdings" "200" "Get current holdings")

if [ $? -eq 0 ]; then
    # Validate holdings response structure
    if ! echo "$holdings_response" | jq -e '.holdings' >/dev/null 2>&1; then
        error "Holdings response missing 'holdings' field"
    fi
    
    holdings_count=$(echo "$holdings_response" | jq '.holdings | length')
    log "Found $holdings_count holdings"
else
    error "Holdings fetch failed"
fi

# Test 5: Shadow Trade Execution
log "=== Shadow Trade Test ==="
shadow_trade_data='{
    "symbol": "AAPL",
    "action": "BUY",
    "quantity": 10,
    "mode": "shadow"
}'

shadow_response=$(test_endpoint "POST" "/trades/execute" "200" "Execute shadow trade" "$shadow_trade_data")

if [ $? -eq 0 ]; then
    # Validate shadow trade response
    if ! echo "$shadow_response" | jq -e '.trade_id' >/dev/null 2>&1; then
        error "Shadow trade response missing 'trade_id' field"
    fi
    
    if ! echo "$shadow_response" | jq -e '.mode' >/dev/null 2>&1; then
        error "Shadow trade response missing 'mode' field"
    fi
    
    mode=$(echo "$shadow_response" | jq -r '.mode')
    if [ "$mode" != "shadow" ]; then
        error "Expected shadow mode, got: $mode"
    fi
    
    trade_id=$(echo "$shadow_response" | jq -r '.trade_id')
    log "Shadow trade executed with ID: $trade_id"
else
    error "Shadow trade execution failed"
fi

# Test 6: Paper Trading Tests
log "=== Paper Trading Tests ==="

echo "[paper] health"
code=$(curl -s -o /dev/null -w "%{http_code}" "$API/health")
if [ "$code" != "200" ]; then
    error "Paper health check failed - Expected 200, got $code"
else
    log "✓ Paper health check passed"
fi

echo "[paper] shadow path"
resp=$(curl -s -X POST "$API/trades/execute" -H 'content-type: application/json' -d '{"symbol":"AAPL","qty":1,"price":1,"mode":"shadow"}')
if echo "$resp" | jq -e '.mode=="shadow"' >/dev/null 2>&1; then
    log "✓ Shadow trade path validated"
else
    error "Shadow trade path validation failed"
    echo "Response: $resp"
fi

echo "[paper] killswitch block when LIVE_TRADING=1 + KILL_SWITCH=1"
# This assumes envs set accordingly in a staging service; skip if not configured.
resp=$(curl -s -o /tmp/trade.out -w "%{http_code}" -X POST "$API/trades/execute" -H 'content-type: application/json' -d '{"symbol":"AAPL","side":"buy","qty":1}')
if [ "$resp" -ne 400 ]; then 
    warn "Expected 400 for killswitch, got $resp (may not be configured)"
else
    log "✓ Killswitch protection working"
fi
if [ -f /tmp/trade.out ]; then
    cat /tmp/trade.out
fi

echo "[paper] position cap block"
resp=$(curl -s -X POST "$API/trades/execute" -H 'content-type: application/json' -d '{"symbol":"AAPL","qty":1000,"price":1000}')
if echo "$resp" | jq -e '.error=="max_position_exceeded"' >/dev/null 2>&1; then
    log "✓ Position cap protection working"
else
    warn "Position cap test may not be configured or exceeded threshold not reached"
    echo "Response: $resp"
fi

# Final Results
log "=== Test Results ==="
if [ $EXIT_CODE -eq 0 ]; then
    log "All smoke tests passed!"
else
    error "Some smoke tests failed!"
fi

exit $EXIT_CODE
