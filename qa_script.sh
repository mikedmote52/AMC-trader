#!/bin/bash
# AMC-TRADER One-Minute QA Script
# Quick verification of production system

BASE="${BASE:-https://amc-trader.onrender.com}"

echo "🧪 AMC-TRADER QUICK QA VERIFICATION"
echo "=================================="
echo "Base URL: $BASE"
echo ""

# 1. Health shows knobs reflected
echo "1️⃣ CONFIGURATION VERIFICATION"
echo "-----------------------------"
curl -s "$BASE/discovery/health" \
| jq '{price_bounds,dollar_volume_min_m,universe,performance,timings_ms,cache_status}' \
| head -20

echo ""
echo "2️⃣ CANDIDATES RESPONSE TIME TEST"
echo "--------------------------------"
echo "Testing cached response time..."
time curl -s "$BASE/discovery/candidates?limit=100" \
| jq '{n: (.candidates|length), updated_at, scanned, total, duration_ms, cached}' 2>/dev/null || echo "❌ Request failed or timed out"

echo ""
echo "3️⃣ TRADE-READY FAST PATH"
echo "------------------------"
curl -s "$BASE/discovery/candidates/trade-ready?limit=50" \
| jq '{n: (.candidates|length), top: [.candidates[:5][]?|{symbol,score,action}] }' 2>/dev/null || echo "❌ Trade-ready endpoint failed"

echo ""
echo "4️⃣ TOP 10 CANDIDATES SNAPSHOT"
echo "-----------------------------"
curl -s "$BASE/discovery/candidates?limit=10" \
| jq '.candidates[]? | {symbol, price, score, action, thesis}' 2>/dev/null || echo "❌ Candidates snapshot failed"

echo ""
echo "5️⃣ PROGRESS/WORKER STATUS"
echo "------------------------"
curl -s "$BASE/discovery/progress" \
| jq '{status, updated_at, candidates_found, trade_ready, monitor, duration_ms}' 2>/dev/null || echo "❌ Progress endpoint failed"

echo ""
echo "✅ QA SCRIPT COMPLETE"
echo ""
echo "EXPECTED RESULTS:"
echo "- price_bounds: min=0.5, max=100"
echo "- universe.universe_k_limit: 3000"
echo "- Response time: <5 seconds (cached: <200ms)"
echo "- Non-zero candidates during market hours"
echo "- Trade-ready candidates with score ≥75"
echo ""