#!/bin/bash

# BMS Price Bounds Live Validation Script
# Quick validation commands for the deployed system

API_BASE="https://amc-trader.onrender.com"

echo "🧪 BMS Price Bounds Live Validation"
echo "=================================="

echo ""
echo "1️⃣ Check health shows price bounds:"
curl -s "${API_BASE}/discovery/health" | jq '.price_bounds, .dollar_volume_min_m, .options_required'

echo ""
echo "2️⃣ Pull candidates and check max price:"
MAX_PRICE=$(curl -s "${API_BASE}/discovery/candidates?limit=50" | jq '[.candidates[] | .price] | max')
echo "Maximum candidate price: \$${MAX_PRICE}"

echo ""
echo "3️⃣ Check for sub-\$2 candidates (if any):"
curl -s "${API_BASE}/discovery/candidates?limit=100" | jq '[.candidates[] | select(.price < 2.0) | {symbol, price, score}]'

echo ""
echo "4️⃣ Verify no candidates above \$100:"
HIGH_PRICE_COUNT=$(curl -s "${API_BASE}/discovery/candidates?limit=100" | jq '[.candidates[] | select(.price > 100.0)] | length')
echo "Candidates above \$100: ${HIGH_PRICE_COUNT} (should be 0)"

echo ""
echo "5️⃣ Check price distribution of candidates:"
curl -s "${API_BASE}/discovery/candidates?limit=20" | jq '[.candidates[] | {symbol, price: (.price | tostring + " USD"), bms_score}] | sort_by(.price)'

echo ""
echo "✅ Validation complete!"
echo "Expected results:"
echo "- Price bounds: min: 0.5, max: 100" 
echo "- No candidates above \$100"
echo "- Sub-\$2 candidates only if they have ≥\$10M volume"
echo "- Max price should be ≤ \$100"