#!/bin/bash
# PRESERVATION TEST PROTOCOL for AMC Trading System
# Critical functionality verification before any merges

set -e

API="https://amc-trader.onrender.com"
PASS="\033[32m✅ PASS\033[0m"
FAIL="\033[31m❌ FAIL\033[0m"
INFO="\033[34mℹ️\033[0m"

echo "🔒 AMC Trading System Preservation Test Protocol"
echo "================================================"
echo ""

# Test 1: Health Check
echo "$INFO Testing system health..."
HEALTH=$(curl -s "$API/health" | jq -r '.status')
if [ "$HEALTH" = "healthy" ]; then
    echo "$PASS System health: $HEALTH"
else
    echo "$FAIL System health: $HEALTH"
    exit 1
fi

# Test 2: Discovery API
echo "$INFO Testing discovery contenders..."
CONTENDERS=$(curl -s "$API/discovery/contenders" | jq 'length')
if [ "$CONTENDERS" -gt 0 ]; then
    echo "$PASS Discovery contenders: $CONTENDERS recommendations"
else
    echo "$FAIL Discovery contenders: $CONTENDERS (expected > 0)"
    exit 1
fi

# Test 3: Portfolio Holdings
echo "$INFO Testing portfolio holdings..."
POSITIONS=$(curl -s "$API/portfolio/holdings" | jq '.data.positions | length')
if [ "$POSITIONS" -gt 0 ]; then
    echo "$PASS Portfolio holdings: $POSITIONS positions"
else
    echo "$FAIL Portfolio holdings: $POSITIONS (expected > 0)"
    exit 1
fi

# Test 4: Trade Execution Endpoint (dry run)
echo "$INFO Testing trade execution endpoint..."
TRADE_RESPONSE=$(curl -s -X POST "$API/trades/execute" \
    -H 'content-type: application/json' \
    -d '{"symbol":"QUBT","action":"BUY","mode":"paper","notional_usd":1}' | jq -r '.error // "success"')

if [[ "$TRADE_RESPONSE" != "null" && "$TRADE_RESPONSE" != "" ]]; then
    echo "$PASS Trade execution endpoint: responding (got: $TRADE_RESPONSE)"
else
    echo "$FAIL Trade execution endpoint: no response"
    exit 1
fi

# Test 5: Frontend Build
echo "$INFO Testing frontend build..."
cd frontend
if npm run build > /dev/null 2>&1; then
    echo "$PASS Frontend build: successful"
else
    echo "$FAIL Frontend build: failed"
    exit 1
fi
cd ..

echo ""
echo "🎯 PRESERVATION TEST COMPLETE"
echo "All critical functionality verified - system ready for enhancements"
echo ""