#!/bin/bash
# Test script to verify /contenders endpoint fix deployment

API="https://amc-trader.onrender.com"

echo "=== Testing AMC-TRADER /contenders endpoint fix ==="
echo

# 1. Trigger discovery to ensure we have candidates
echo "1. Triggering discovery..."
CANDIDATES_FOUND=$(curl -s -X POST "$API/discovery/trigger?strategy=legacy_v0&limit=10" | jq -r '.candidates_found')
echo "   Discovery found: $CANDIDATES_FOUND candidates"

# 2. Check if raw endpoint exists (indicates deployment)
echo
echo "2. Testing /contenders/raw endpoint..."
RAW_RESPONSE=$(curl -s "$API/discovery/contenders/raw?strategy=legacy_v0")
if echo "$RAW_RESPONSE" | grep -q "detail.*Not Found"; then
    echo "   ❌ /contenders/raw not deployed yet"
    DEPLOYMENT_READY=false
else
    RAW_COUNT=$(echo "$RAW_RESPONSE" | jq -r '.count')
    echo "   ✅ /contenders/raw deployed, shows $RAW_COUNT candidates"
    DEPLOYMENT_READY=true
fi

# 3. Test main contenders endpoint
echo
echo "3. Testing /contenders endpoint..."
CONTENDERS_COUNT=$(curl -s "$API/discovery/contenders?strategy=legacy_v0" | jq 'length')
echo "   /contenders returns: $CONTENDERS_COUNT candidates"

# 4. Check debug diagnostics
echo
echo "4. Checking Redis data via debug..."
DEBUG_DATA=$(curl -s "$API/discovery/contenders/debug?strategy=legacy_v0" | jq -r '.data_diagnostics')
REDIS_COUNT=$(echo "$DEBUG_DATA" | jq -r '.items_found')
echo "   Redis contains: $REDIS_COUNT candidates"

# Summary
echo
echo "=== SUMMARY ==="
echo "Discovery Pipeline: $CANDIDATES_FOUND candidates found"
echo "Redis Storage: $REDIS_COUNT candidates stored"
echo "Contenders Endpoint: $CONTENDERS_COUNT candidates returned"
echo

if [ "$DEPLOYMENT_READY" = true ]; then
    echo "✅ Deployment appears to be complete"
    if [ "$CONTENDERS_COUNT" -gt 0 ]; then
        echo "✅ SUCCESS: /contenders endpoint is now returning candidates!"
    else
        echo "⚠️  Issue persists: /contenders still returning 0 despite Redis having data"
    fi
else
    echo "⏳ Waiting for deployment to complete..."
fi

echo
echo "Expected result after deployment:"
echo "  - /contenders/raw should return $REDIS_COUNT candidates"
echo "  - /contenders should return $REDIS_COUNT candidates (no filtering)"