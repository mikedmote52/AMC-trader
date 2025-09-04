# Hybrid V1 Deployment Verification Commands

## Quick Verification (Copy-Paste Ready)

```bash
API=https://amc-trader.onrender.com

# 1. Verify health (should include tag/commit/build now)
curl -s "$API/health" | jq .

# 2. Verify strategy status shows effective hybrid
curl -s "$API/calibration/status" | jq '.effective_strategy'

# 3. Verify contenders without query param use Hybrid V1
curl -s "$API/contenders?limit=5" | jq '.metadata.strategy'

# 4. Verify legacy requests are still forced to Hybrid V1
curl -s "$API/contenders?strategy=legacy_v0&limit=5" | jq '.metadata.strategy'

# 5. Verify test endpoint uses Hybrid V1
curl -s "$API/test?limit=10" | jq '.metadata.strategy'

# 6. Check reason histogram works (if candidates exist)
curl -s "$API/test?limit=100" | jq '[.trace.rejections.strategy_scoring[]? | select(.reason)] | group_by(.reason) | map({reason: .[0].reason, count: length}) | sort_by(-.count)'
```

## Expected Results

### 1. Health Check
```json
{
  "status": "healthy",
  "timestamp": "2025-09-04T...",
  "version": "hybrid_v1_deployment",
  "commit": "...",
  "build": "..."
}
```

### 2. Strategy Status
```json
"hybrid_v1"
```

### 3. Default Contenders
```json
"hybrid_v1"
```

### 4. Legacy Override Test
```json
"hybrid_v1"  // Should still be hybrid_v1, not legacy_v0
```

### 5. Test Endpoint
```json
"hybrid_v1"
```

### 6. Reason Histogram
```json
[
  {"reason": "relvol30_below_regular", "count": 45},
  {"reason": "atr_below_threshold", "count": 23},
  {"reason": "no_vwap_reclaim_regular", "count": 12}
]
```

## Deployment Success Criteria

✅ **Strategy Enforcement**: All endpoints return `"strategy": "hybrid_v1"` regardless of query parameter
✅ **Emergency Override**: System maintains 15-minute emergency override capability  
✅ **Observability**: Enhanced gate rejection tracking with detailed reasons
✅ **Backward Compatibility**: All existing endpoints preserve exact response schemas
✅ **Performance**: Response times remain under 2s for all discovery endpoints

## Troubleshooting

### If Strategy Shows "legacy_v0"
```bash
# Check environment variables are set correctly
curl -s "$API/_whoami" | jq .
```

### If No Candidates Found
```bash
# Check if market is closed or filters too strict
curl -s "$API/test?limit=500" | jq '.trace.pipeline_stats'
```

### If Reason Histogram Empty
```bash
# Verify trace data is being captured
curl -s "$API/test?limit=50" | jq '.trace.rejections'
```