# PR: Hybrid V1 Observability + Calibration Enhancements

## Summary
Adds comprehensive observability and flexible calibration to Hybrid V1 discovery gates while preserving all existing behavior as defaults. All new features are **disabled by default** and config-driven.

## New Endpoints

### 1. Primary Calibration Endpoint
```bash
PATCH /calibration/hybrid_v1
# Body: {"thresholds": {...}} and/or {"weights": {...}}
```

### 2. Alias Endpoint (prevents 404s)
```bash
PATCH /discovery/calibration/hybrid_v1
# Maps to same handler as above
```

### 3. Enhanced Status Endpoint
```bash
GET /calibration/status
# Returns: effective_strategy, preset, weights_hash, thresholds_snapshot, emergency_flag, last_updated
```

### 4. Session-Aware Queries
```bash
GET /contenders?strategy=hybrid_v1&session=premarket
GET /test?strategy=hybrid_v1&session=afterhours
# session = premarket|regular|afterhours (default: regular)
```

## Configuration Changes

Added to `calibration/active.json` under `scoring.hybrid_v1.thresholds` (all disabled by default):

```json
{
  "session_overrides": {
    "premarket": {"enabled": false, "min_relvol_30": 2.0, "min_atr_pct": 0.03, "require_vwap_reclaim": false},
    "afterhours": {"enabled": false, "min_relvol_30": 1.8, "min_atr_pct": 0.03, "require_vwap_reclaim": false},
    "regular": {"enabled": false}
  },
  "vwap_proximity_pct": 0.0,
  "mid_float_path": {
    "enabled": false,
    "float_min": 75000000, "float_max": 150000000,
    "short_interest_min": 0.12, "borrow_fee_min": 0.10, "utilization_min": 0.75,
    "require_one_of": {"news_catalyst": true, "social_rank_min": 0.85, "call_put_ratio_min": 2.5}
  },
  "soft_gate_tolerance": 0.10,
  "max_soft_pass": 0
}
```

## Example PATCH Bodies

### Enable VWAP Proximity
```bash
curl -X PATCH "$API/calibration/hybrid_v1" \
  -H "Content-Type: application/json" \
  -d '{"thresholds": {"vwap_proximity_pct": 0.5}}'
```

### Enable Premarket Session
```bash
curl -X PATCH "$API/discovery/calibration/hybrid_v1" \
  -H "Content-Type: application/json" \
  -d '{"thresholds": {"session_overrides": {"premarket": {"enabled": true}}}}'
```

### Enable Mid-Float Path
```bash
curl -X PATCH "$API/calibration/hybrid_v1" \
  -H "Content-Type: application/json" \
  -d '{"thresholds": {"mid_float_path": {"enabled": true}}}'
```

### Enable Soft-Pass (5 slots)
```bash
curl -X PATCH "$API/calibration/hybrid_v1" \
  -H "Content-Type: application/json" \
  -d '{"thresholds": {"max_soft_pass": 5}}'
```

## Reason Histogram Query

View gate rejection breakdown:
```bash
curl -s "$API/test?strategy=hybrid_v1&limit=500" | \
jq '[.trace.rejections.strategy_scoring[]? | select(.reason)] | group_by(.reason) | map({reason: .[0].reason, count: length}) | sort_by(-.count)'
```

## Enhanced Features (All Default-Disabled)

1. **Session-Aware Thresholds**: Different gates for premarket/regular/afterhours
2. **VWAP Proximity**: Allow stocks within X% of VWAP instead of requiring above
3. **Mid-Float Alternative Path**: Rescue 75-150M float stocks with catalyst signals
4. **Soft-Pass Tolerance**: Near-miss candidates with strong catalysts
5. **Gate Rejection Tracking**: Push detailed reasons to trace for observability

## Observability Enhancements

- Gate failures push to `trace.strategy_scoring` with session context
- Enhanced `/contenders` response includes strategy metadata
- `/calibration/status` provides configuration snapshot
- Detailed rejection reasons: `relvol30_below_regular`, `no_vwap_reclaim_premarket`, etc.

## Backward Compatibility

✅ **Zero Breaking Changes**
- All existing endpoints preserved
- All default behavior identical 
- All schemas unchanged
- Function signatures preserved (`_hybrid_v1_gate_check` still returns `(bool, str)`)

## Testing

Included minimal test suite (`test_hybrid_v1_minimal.py`) verifies:
- ✅ All features disabled by default
- ✅ Baseline candidates still pass
- ✅ VWAP proximity works when enabled  
- ✅ Mid-float path works when enabled
- ✅ Soft-pass works when enabled

## Production Readiness

Deploy with confidence - all enhancements are opt-in:
1. Current behavior preserved exactly
2. Comprehensive observability available immediately  
3. Selective feature enablement based on market conditions
4. Emergency controls remain functional

## Expected Impact

**Immediate**: Enhanced visibility into gate rejection reasons
**Optional**: Surgical tuning for quiet market conditions
**Quality**: Maintained through catalyst requirements and caps