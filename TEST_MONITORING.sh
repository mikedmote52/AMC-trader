#!/bin/bash

# AMC-TRADER Monitoring System Test Suite
# Test all new monitoring features with your live API

API="https://amc-trader.onrender.com"

echo "🚀 AMC-TRADER MONITORING SYSTEM TEST SUITE"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test function
test_endpoint() {
    local name="$1"
    local method="$2"
    local endpoint="$3"
    local data="$4"
    
    echo -e "${BLUE}Testing: ${name}${NC}"
    echo "Endpoint: ${method} ${API}${endpoint}"
    
    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" "${API}${endpoint}")
    else
        response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST "${API}${endpoint}" \
            -H "Content-Type: application/json" \
            -d "${data}")
    fi
    
    http_status=$(echo "$response" | grep "HTTP_STATUS" | cut -d: -f2)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_status" = "200" ]; then
        echo -e "${GREEN}✅ Success (HTTP ${http_status})${NC}"
        echo "$body" | jq '.' 2>/dev/null || echo "$body"
    else
        echo -e "${RED}❌ Failed (HTTP ${http_status})${NC}"
        echo "$body" | jq '.' 2>/dev/null || echo "$body"
    fi
    echo ""
    echo "---"
    echo ""
}

# ==== SECTION 1: SYSTEM HEALTH & STATUS ====
echo -e "${YELLOW}📊 SECTION 1: SYSTEM HEALTH & STATUS${NC}"
echo "======================================="
echo ""

test_endpoint \
    "Monitoring System Status" \
    "GET" \
    "/monitoring/status"

test_endpoint \
    "Comprehensive Dashboard" \
    "GET" \
    "/monitoring/dashboard"

# ==== SECTION 2: DISCOVERY PIPELINE MONITORING ====
echo -e "${YELLOW}🔍 SECTION 2: DISCOVERY PIPELINE MONITORING${NC}"
echo "=============================================="
echo "Track how 10,325+ stocks get filtered to final candidates"
echo ""

test_endpoint \
    "Discovery Pipeline Health" \
    "GET" \
    "/monitoring/discovery/health"

test_endpoint \
    "Discovery Flow Statistics (Last 24h)" \
    "GET" \
    "/monitoring/discovery/flow-stats?hours_back=24&limit=5"

test_endpoint \
    "Discovery Pipeline Alerts" \
    "GET" \
    "/monitoring/discovery/alerts?limit=10"

# ==== SECTION 3: LEARNING SYSTEM & MISSED OPPORTUNITIES ====
echo -e "${YELLOW}📈 SECTION 3: LEARNING SYSTEM & MISSED OPPORTUNITIES${NC}"
echo "======================================================"
echo "Track recommendations you didn't buy that performed well"
echo ""

test_endpoint \
    "Missed Opportunities (30 days)" \
    "GET" \
    "/monitoring/recommendations/missed-opportunities?days_back=30&min_performance=15"

test_endpoint \
    "Learning System Insights" \
    "GET" \
    "/monitoring/recommendations/performance-insights"

# ==== SECTION 4: BUY-THE-DIP DETECTION ====
echo -e "${YELLOW}💎 SECTION 4: BUY-THE-DIP OPPORTUNITIES${NC}"
echo "=========================================="
echo "Find underperforming holdings with strong thesis"
echo ""

test_endpoint \
    "Current Dip Opportunities" \
    "GET" \
    "/monitoring/dip-analysis/opportunities?min_drop_pct=10&days_back=7"

test_endpoint \
    "Dip Analysis History" \
    "GET" \
    "/monitoring/dip-analysis/history?days_back=30"

# ==== SECTION 5: ALERT SYSTEM ====
echo -e "${YELLOW}🚨 SECTION 5: ALERT NOTIFICATIONS${NC}"
echo "===================================="
echo ""

test_endpoint \
    "System Alerts (All Sources)" \
    "GET" \
    "/monitoring/alerts/system?limit=20"

test_endpoint \
    "Missed Opportunity Alerts" \
    "GET" \
    "/monitoring/alerts/missed-opportunities?limit=10"

# ==== SECTION 6: TRIGGER ACTIONS ====
echo -e "${YELLOW}⚡ SECTION 6: TRIGGER MONITORING ACTIONS${NC}"
echo "=========================================="
echo ""

echo -e "${BLUE}Trigger Buy-the-Dip Analysis${NC}"
echo "This will analyze your current portfolio for dip opportunities"
read -p "Run dip analysis? (y/n): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    test_endpoint \
        "Trigger Dip Analysis" \
        "POST" \
        "/monitoring/dip-analysis/run" \
        "{}"
fi

echo ""
echo -e "${BLUE}Initialize Monitoring System${NC}"
echo "This will ensure all monitoring tables are created"
read -p "Initialize monitoring? (y/n): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    test_endpoint \
        "Initialize Monitoring" \
        "POST" \
        "/monitoring/initialize" \
        "{}"
fi

# ==== SUMMARY ====
echo ""
echo -e "${YELLOW}📋 TESTING COMPLETE!${NC}"
echo "===================="
echo ""
echo "Key things to look for:"
echo "1. Discovery Health Score - Should be > 0.7 for healthy pipeline"
echo "2. Universe Size - Should be 5000+ stocks (or 100+ for fallback)"
echo "3. Missed Opportunities - Stocks you didn't buy that gained 15%+"
echo "4. Dip Opportunities - Current holdings down 10%+ with strong thesis"
echo "5. Active Alerts - Critical issues requiring attention"
echo ""
echo "💡 TIP: Save interesting stock symbols from missed opportunities"
echo "        and dip analysis for manual review!"
echo ""
echo "📊 Monitor continuously at: ${API}/monitoring/dashboard"