# Hybrid V1 Gate Enhancement - Validation Commands

## Overview
This update adds observability and flexibility to the hybrid_v1 discovery gates while preserving default behavior. All new features are **disabled by default** to maintain backward compatibility.

## New Features (All Disabled by Default)
1. **Session-aware thresholds** - Different gates for premarket/regular/afterhours
2. **VWAP proximity** - Allow stocks within X% of VWAP
3. **Mid-float path** - Rescue quality 75M-150M float stocks
4. **Soft-pass tolerance** - Allow near-misses with catalyst
5. **Enhanced observability** - Gate rejection tracking in trace

## API Changes

### New Endpoint: PATCH /discovery/calibration/hybrid_v1
Unified endpoint for updating thresholds and weights:
```bash
# Update thresholds only
curl -s -X PATCH "$API/discovery/calibration/hybrid_v1" \
  -H "Content-Type: application/json" \
  -d '{"thresholds": {"vwap_proximity_pct": 0.5}}'

# Update weights only  
curl -s -X PATCH "$API/discovery/calibration/hybrid_v1" \
  -H "Content-Type: application/json" \
  -d '{"weights": {"volume_momentum": 0.40, "squeeze": 0.30}}'
```

### Legacy Endpoint Still Works
```bash
# PATCH /calibration/hybrid_v1/weights still works for backward compatibility
curl -s -X PATCH "$API/discovery/calibration/hybrid_v1/weights" \
  -H "Content-Type: application/json" \
  -d '{"volume_momentum": 0.35}'
```

## Validation Commands

### 1. Enable VWAP Proximity (0.5%)
Allow stocks within 0.5% of VWAP to pass:
```bash
curl -s -X PATCH "$API/discovery/calibration/hybrid_v1" \
  -H "Content-Type: application/json" \
  -d '{"thresholds": {"vwap_proximity_pct": 0.5}}'
```

### 2. Enable Premarket Session Overrides
Relax thresholds during premarket hours:
```bash
curl -s -X PATCH "$API/discovery/calibration/hybrid_v1" \
  -H "Content-Type: application/json" \
  -d '{"thresholds": {"session_overrides": {"premarket": {"enabled": true}}}}'
```

### 3. Enable Mid-Float Alternative Path
Capture quality 75M-150M float stocks:
```bash
curl -s -X PATCH "$API/discovery/calibration/hybrid_v1" \
  -H "Content-Type: application/json" \
  -d '{"thresholds": {"mid_float_path": {"enabled": true}}}'
```

### 4. Enable Soft-Pass with 10 Slots
Allow up to 10 near-misses with catalysts:
```bash
curl -s -X PATCH "$API/discovery/calibration/hybrid_v1" \
  -H "Content-Type: application/json" \
  -d '{"thresholds": {"max_soft_pass": 10}}'
```

### 5. View Gate Rejection Histogram
See why candidates are being rejected:
```bash
curl -s "$API/discovery/test?strategy=hybrid_v1&relaxed=true&limit=500" \
| jq '.trace.rejections.strategy_scoring // [] | 
      group_by(.reason) | 
      map({reason: .[0].reason, count: length}) | 
      sort_by(-.count)'
```

### 6. Check Current Configuration
View active thresholds and session:
```bash
curl -s "$API/discovery/calibration/hybrid_v1/config" | jq '{
  active_preset: .active_preset,
  vwap_proximity: .thresholds.vwap_proximity_pct,
  mid_float_enabled: .thresholds.mid_float_path.enabled,
  max_soft_pass: .thresholds.max_soft_pass,
  session_overrides: .thresholds.session_overrides
}'
```

### 7. Test Discovery with Enhanced Trace
Run discovery and see detailed rejection reasons:
```bash
curl -s "$API/discovery/test?strategy=hybrid_v1&limit=300&relaxed=true" | jq '{
  candidates: .items | length,
  rejected_at_gates: (.trace.rejections.strategy_scoring // [] | length),
  rejection_reasons: (.trace.rejections.strategy_scoring // [] | 
    group_by(.reason) | 
    map({reason: .[0].reason, count: length}))
}'
```

### 8. View Candidates with Metadata
See which candidates used soft-pass or mid-float:
```bash
curl -s "$API/discovery/contenders?strategy=hybrid_v1&limit=25" | jq '.candidates[] | {
  symbol: .symbol,
  score: .score,
  soft_pass: .soft_pass,
  mid_alt: .mid_alt,
  relvol: .factors.relvol_30,
  atr: .factors.atr_pct
}'
```

## Common Scenarios

### Quiet Market Hours (Before 10 AM)
Enable relaxed gates temporarily:
```bash
# Enable VWAP proximity and reduce thresholds
curl -s -X PATCH "$API/discovery/calibration/hybrid_v1" \
  -H "Content-Type: application/json" \
  -d '{
    "thresholds": {
      "vwap_proximity_pct": 1.0,
      "min_relvol_30": 2.0,
      "min_atr_pct": 0.03,
      "max_soft_pass": 5
    }
  }'
```

### Premarket Discovery (4-9:30 AM ET)
Enable premarket overrides:
```bash
curl -s -X PATCH "$API/discovery/calibration/hybrid_v1" \
  -H "Content-Type: application/json" \
  -d '{
    "thresholds": {
      "session_overrides": {
        "premarket": {"enabled": true}
      },
      "mid_float_path": {"enabled": true},
      "max_soft_pass": 10
    }
  }'
```

### Reset to Defaults
Clear all custom settings:
```bash
curl -s -X POST "$API/discovery/calibration/hybrid_v1/reset"
```

## Monitoring & Observability

### Gate Failure Analysis
```bash
# Get detailed gate failure breakdown
curl -s "$API/discovery/test?strategy=hybrid_v1&limit=1000&relaxed=true" | jq '
  .trace.rejections.strategy_scoring // [] |
  group_by(.reason) |
  map({
    reason: .[0].reason,
    count: length,
    examples: [.[:3][].symbol]
  }) |
  sort_by(-.count)'
```

### Session Detection Check
```bash
# Check which session is currently active
curl -s "$API/discovery/calibration/status" | jq '.strategy.session // "regular"'
```

## Testing Suite
Run the included test suite:
```bash
python test_hybrid_v1_gates.py
```

## Acceptance Criteria
✅ Default behavior unchanged (all features disabled)
✅ Trace includes gate rejection reasons with session context
✅ VWAP proximity allows stocks within tolerance
✅ Mid-float path admits quality 75-150M float stocks
✅ Soft-pass limited by max_soft_pass setting
✅ Session overrides apply when enabled
✅ /calibration/hybrid_v1 endpoint handles thresholds
✅ Legacy /calibration/hybrid_v1/weights still works

## Production Deployment Notes
1. Deploy with all features disabled (current config)
2. Monitor gate rejection histogram to understand bottlenecks
3. Selectively enable features based on market conditions
4. Use session overrides for premarket/afterhours only
5. Keep max_soft_pass low (≤10) to maintain quality