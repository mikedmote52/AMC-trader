- API=https://amc-trader.onrender.com

# AMC-TRADER Hybrid Scoring System

## Overview
AMC-TRADER now supports two scoring strategies:
- **legacy_v0**: Original VIGL-based pattern detection
- **hybrid_v1**: New 5-subscore system with advanced gatekeeping

## Configuration

### Environment Variables
```bash
SCORING_STRATEGY=hybrid_v1  # or legacy_v0 (default)
```

### Strategy Configuration (calibration/active.json)
```json
{
  "scoring": {
    "strategy": "legacy_v0",
    "hybrid_v1": {
      "weights": {
        "volume_momentum": 0.35,
        "squeeze": 0.25,
        "catalyst": 0.20,
        "options": 0.10,
        "technical": 0.10
      },
      "thresholds": {
        "min_relvol_30": 2.5,
        "min_atr_pct": 0.04,
        "rsi_band": [60, 70],
        "require_vwap_reclaim": true
      },
      "entry_rules": {
        "watchlist_min": 70,
        "trade_ready_min": 75
      }
    }
  }
}
```

## API Usage

### Discovery Endpoints
```bash
# Get candidates with specific strategy
curl -s "$API/discovery/contenders?strategy=hybrid_v1" | jq .

# Test discovery with strategy
curl -s "$API/discovery/test?strategy=hybrid_v1&limit=5" | jq .

# Trigger discovery with strategy
curl -s -X POST "$API/discovery/trigger?strategy=hybrid_v1&limit=10" | jq .

# Validate both strategies side-by-side
curl -s "$API/discovery/strategy-validation" | jq .
```

### Response Format
```json
{
  "candidates": [...],
  "count": 5,
  "strategy": "hybrid_v1",
  "timestamp": "2025-01-XX"
}
```

## Hybrid V1 Strategy Details

### Scoring Components (0-1.0 each)
1. **Volume & Momentum (35%)**: RelVol, uptrend days, VWAP reclaim, ATR
2. **Squeeze (25%)**: Float tightness, short interest, borrow fees, utilization
3. **Catalyst (20%)**: News detection, social media rank
4. **Options (10%)**: Call/put ratio, IV percentile
5. **Technical (10%)**: EMA cross, RSI bands

### Gatekeeping Rules
- RelVol ≥ 2.5x (30-day average)
- ATR ≥ 4% (volatility expansion)
- VWAP reclaim required (momentum confirmation)
- Squeeze path: Small float (≤75M) OR Large float (≥150M) with strong metrics

### Action Tags
- **trade_ready**: Score ≥ 75% (immediate execution candidates)
- **watchlist**: Score ≥ 70% (monitoring candidates)

## Testing & Validation

### Basic Health Check
```bash
# 1. Verify health (should include tag/commit/build now)
curl -s "$API/health" | jq .

# 2. Verify whoami (new endpoint)
curl -s "$API/_whoami" | jq .

# 3. Trigger a small test trade (should return error details if blocked)
curl -s -X POST "$API/trades/execute" \
  -H 'content-type: application/json' \
  -d '{"symbol":"QUBT","action":"BUY","mode":"live","notional_usd":10}' | jq .
```

### Strategy Testing
```bash
# Compare strategies side-by-side
curl -s "$API/discovery/strategy-validation" | jq .

# Test hybrid_v1 specifically
curl -s "$API/discovery/test?strategy=hybrid_v1&relaxed=true&limit=100" | jq .

# Validate individual symbols
curl -s "$API/discovery/audit/VIGL?strategy=hybrid_v1" | jq .
```

## Deployment & Rollout

### Phase 1: Canary Testing
1. Deploy with `SCORING_STRATEGY=legacy_v0` (default)
2. Test hybrid_v1 via query parameters
3. Monitor via `/discovery/strategy-validation`

### Phase 2: Production Switch
1. Set `SCORING_STRATEGY=hybrid_v1` in environment
2. Monitor candidate quality and count
3. Rollback trigger: flip env var back to `legacy_v0`

## Live Operations & Tuning

### One-Click Preset Switching
```bash
# Switch to catalyst-heavy preset
curl -s -X PATCH "$API/discovery/calibration/hybrid_v1/preset?name=catalyst_heavy" | jq .

# Switch to squeeze-aggressive preset  
curl -s -X PATCH "$API/discovery/calibration/hybrid_v1/preset?name=squeeze_aggressive" | jq .

# Back to balanced default
curl -s -X PATCH "$API/discovery/calibration/hybrid_v1/preset?name=balanced_default" | jq .
```

### Live Weight Tuning
```bash
# Tighten catalyst focus (bump to 0.25, lower squeeze to 0.20)
curl -s -X PATCH "$API/discovery/calibration/hybrid_v1/weights" \
     -H "Content-Type: application/json" \
     -d '{"catalyst":0.25,"squeeze":0.20}' | jq .

# Volume-first approach (bump volume_momentum to 0.40)
curl -s -X PATCH "$API/discovery/calibration/hybrid_v1/weights" \
     -H "Content-Type: application/json" \
     -d '{"volume_momentum":0.40,"squeeze":0.20}' | jq .

# Reset to defaults
curl -s -X POST "$API/discovery/calibration/hybrid_v1/reset" | jq .
```

### Emergency Controls
```bash
# EMERGENCY: Force legacy_v0 for 15 minutes
curl -s -X POST "$API/discovery/calibration/emergency/force-legacy" | jq .

# Check system status and active overrides
curl -s "$API/discovery/calibration/status" | jq .

# Update safety limits
curl -s -X POST "$API/discovery/calibration/hybrid_v1/limit?max_candidates=50&max_latency_ms=10000" | jq .
```

### Configuration Inspection
```bash
# Get complete current config including resolved weights
curl -s "$API/discovery/calibration/hybrid_v1/config" | jq .

# Check which preset is active
curl -s "$API/discovery/calibration/status" | jq '.preset'
```

## Available Presets

### 1. balanced_default (Default)
- **Volume/Momentum**: 35% - Balanced volume surge detection
- **Squeeze**: 25% - Standard squeeze opportunity weighting  
- **Catalyst**: 20% - News and social sentiment
- **Options**: 10% - Options flow analysis
- **Technical**: 10% - EMA cross and RSI confirmation

### 2. squeeze_aggressive  
- **Squeeze**: 35% - Heavy focus on short squeeze setups
- **Volume/Momentum**: 30% - Strong volume requirement
- **Catalyst**: 20% - Event-driven moves
- **Options**: 10% - Gamma potential
- **Technical**: 5% - Minimal technical filtering

### 3. catalyst_heavy
- **Catalyst**: 35% - News and social-driven opportunities
- **Volume/Momentum**: 30% - Volume confirmation required
- **Squeeze**: 20% - Moderate squeeze weighting
- **Options**: 10% - Options flow validation  
- **Technical**: 5% - Light technical overlay

## Ops Runbook Commands

### Quick Acceptance Tests (10 min)
```bash
# Health & coverage
curl -s "$API/discovery/diagnostics" | jq .
curl -s "$API/discovery/contenders?strategy=hybrid_v1&limit=50" | jq .

# Gate sanity check
curl -s "$API/discovery/test?strategy=hybrid_v1&relaxed=true&limit=500" | jq '.trace'

# Ranking stability 
curl -s "$API/discovery/strategy-validation" | jq .
```

### Canary Rollout
```bash
# Shadow testing - compare strategies
curl -s "$API/discovery/strategy-validation" | jq '.comparison'

# Partial consumer flip (read-only)
curl -s "$API/discovery/contenders?strategy=hybrid_v1" | jq .meta

# Monitor telemetry
curl -s "$API/discovery/calibration/status" | jq .system_health
```

### Troubleshooting Queries
```bash
# Mix of strategies with subscores
curl -s "$API/discovery/contenders?strategy=hybrid_v1&limit=10" | jq '.candidates[] | {symbol, score, subscores}'

# Gate rejection audit
curl -s "$API/discovery/test?strategy=hybrid_v1&limit=200" | jq '.trace.rejections'

# Single symbol analysis
curl -s "$API/discovery/audit/TSLA?strategy=hybrid_v1" | jq .
```

## Monitoring

### Key Metrics
- Candidate count per strategy (`response.count`)
- Score distribution differences (`response.meta.telemetry.score_distribution`)
- API response times (`response.meta.telemetry.latency_ms`)
- Gate pass/fail ratios (`response.meta.gate_failures`)
- Action tag distribution (`candidates[].action_tag`)
- Preset usage tracking (`response.meta.preset`)
- Weights hash for change detection (`response.meta.weights_hash`)