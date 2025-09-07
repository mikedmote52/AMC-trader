# AMC-TRADER System Validation Report
**Date:** September 7, 2025  
**Validation Engine:** AMC-TRADER Validation Engine  
**System Version:** trace_v3 (commit: 5a51e7560ce25bdb460461e2409fff449740b6cc)

## Executive Summary

**CRITICAL FINDING:** The AMC-TRADER system exhibits significant inconsistencies between its backend discovery pipeline and frontend API endpoints. While the system reports healthy status and Redis contains 8 candidates, the `/contenders` endpoint consistently returns empty arrays, indicating a fundamental disconnection between the discovery process and candidate retrieval mechanisms.

**Overall System Status:** DEGRADED - Not ready for live trading  
**Primary Issue:** Discovery-to-API pipeline failure  
**Risk Level:** HIGH - Trading decisions would be based on incomplete data

## Detailed Findings

### 1. System Health vs. Functional Reality

**Status Reported:**
- Health endpoint: `"status": "healthy"`
- All components (env, database, redis, polygon, alpaca): `"ok": true`
- Discovery diagnostics: `"candidates_found": 8`
- Processing status: `"completed"`

**Actual Functionality:**
- `/discovery/contenders`: Returns empty array `[]`
- `/discovery/contenders?strategy=hybrid_v1`: Returns empty array `[]`
- Strategy validation shows legacy_v0 finds 6 candidates, hybrid_v1 finds 0

**Analysis:** The system's health checks are inadequate. They verify component connectivity but fail to validate end-to-end functionality.

### 2. Discovery Pipeline Performance

**Universe Processing:**
- Initial universe: 1,725 stocks (latest run)
- Final candidates: 0 (hybrid_v1 strategy)
- Processing time: ~80 seconds
- Memory inconsistency: Discovery claims 8 candidates found, but pipeline trace shows 0

**Pipeline Stage Breakdown:**
```
universe (1,725) → classify (1,725) → compression_calc (395) → 
squeeze_detection (15) → strategy_scoring (5) → quality_filter (0)
```

**Key Rejection Reasons:**
- `dollar_vol_min`: 8,625 stocks rejected
- `price_cap`: 1,016 stocks rejected  
- `low_squeeze_score_*`: Multiple candidates (4-1 per threshold)
- `hybrid_v1_score_*_below_min`: All 5 final candidates rejected for low scores
- `hybrid_v1_gate_relvol30_below_afterhours`: 2-3 candidates rejected

### 3. Hybrid V1 Strategy Configuration Issues

**Configuration Mismatch:**
- System reports effective strategy: `"hybrid_v1"`
- Environment strategy: `"legacy_v0"` 
- Force strategy: `"hybrid_v1"`
- Configuration endpoint returns: `"strategy": "legacy_v0"`

**Critical Configuration Gaps:**
- No active preset: `"preset": null`
- Empty resolved weights: `{}`
- No thresholds loaded: `{}`
- Missing entry rules: `{}`

**Expected vs. Actual Configuration:**
```json
Expected (from active.json):
{
  "weights": {
    "volume_momentum": 0.35,
    "squeeze": 0.25,
    "catalyst": 0.20,
    "options": 0.10,
    "technical": 0.10
  },
  "thresholds": {
    "min_relvol_30": 0.5,
    "min_atr_pct": 0.02
  }
}

Actual (from API):
{
  "resolved_weights": {},
  "thresholds": {}
}
```

### 4. Polygon Pro Mode Status

**Configuration Evidence:**
- Health check shows: `"polygon": {"ok": true}`
- Environment variables set: `POLYGON_API_KEY`, `USE_POLYGON_WS=true`
- No explicit Polygon Pro confirmation in system responses

**Data Source Analysis:**
- Universe size (1,725 stocks) suggests active data ingestion
- Processing includes real-time elements (afterhours session detection)
- No apparent data source failures in traces

### 5. Header and System State Reporting

**Missing Expected Headers:**
- `X-System-State`: Not present
- `X-Reason-Stats`: Not present
- `X-Strategy-Applied`: Not present

**Available Headers:**
- `x-amc-env: amc-trader`
- `x-amc-trades-handler: default`
- `x-render-origin-server: uvicorn`

**System Identity:**
```json
{
  "env": "unknown",
  "service": "amc-trader", 
  "handler": "default"
}
```

### 6. Redis vs. API Inconsistency

**Discovery Process Claims:**
- `"published_to_redis": true`
- `"candidates_found": 8` (diagnostics)
- `"candidates_found": 0` (trigger response)

**API Endpoint Results:**
- All `/contenders` calls return `[]`
- No candidates available for consumption

**Root Cause Hypothesis:**
1. Redis key mismatch between discovery writer and API reader
2. Strategy-based filtering removing all candidates during API retrieval
3. Time-based expiration clearing candidates between discovery and API calls
4. Configuration override preventing API from reading discovery results

## Strategy Comparison Analysis

**Legacy V0 Performance:**
- Candidates found: 6
- Average score: 0.141
- Sample symbols: ARRY, OLMA, WOOF
- Scoring method: VIGL pattern matching

**Hybrid V1 Performance:**
- Candidates found: 0
- Average score: 0.0
- All candidates rejected below minimum thresholds
- Scoring method: 5-subscore weighted system

**Gate Analysis:**
- `min_relvol_30` gate failing during afterhours session
- Score-based rejections: 26.0%, 33.1%, 11.1%, 9.9%, 22.1%, 17.0%
- No candidates achieving minimum score threshold

## Performance Benchmarks

**Discovery Latency:**
- Current: ~80 seconds (exceeds 15s safety limit)
- Target: <8 seconds
- Status: FAILED

**Candidate Generation:**
- Current: 0 (hybrid_v1) / 6 (legacy_v0)
- Target: 25-40 per scan
- Status: FAILED

**API Response Times:**
- Health endpoint: <1 second
- Contenders endpoint: <1 second
- Strategy validation: ~3 seconds
- Status: ACCEPTABLE

## Critical Issues Identified

### 1. Configuration System Failure (CRITICAL)
The hybrid_v1 strategy configuration is not loading properly. The system shows empty weights, thresholds, and rules despite active.json containing valid configuration.

### 2. Discovery-to-API Pipeline Break (CRITICAL) 
Discovery processes claim success but API endpoints return no data, indicating a fundamental pipeline failure.

### 3. Inconsistent System State Reporting (HIGH)
Health checks pass while core functionality fails, creating false confidence in system readiness.

### 4. Strategy Performance Degradation (HIGH)
Hybrid_v1 strategy produces zero candidates while legacy_v0 produces 6, suggesting calibration issues.

### 5. Session-Based Gate Failures (MEDIUM)
Afterhours session detection incorrectly rejecting valid candidates.

## Recommended Immediate Fixes

### 1. Configuration Loading Emergency Fix
```bash
# Force configuration reload
curl -s -X POST "https://amc-trader.onrender.com/discovery/calibration/hybrid_v1/reset"

# Verify configuration loaded
curl -s "https://amc-trader.onrender.com/discovery/calibration/hybrid_v1/config"
```

### 2. Strategy Fallback Implementation
```bash
# Force legacy_v0 strategy until hybrid_v1 fixed
curl -s -X POST "https://amc-trader.onrender.com/discovery/calibration/emergency/force-legacy"
```

### 3. Pipeline Validation Test
```bash
# Test full pipeline with relaxed constraints
curl -s "https://amc-trader.onrender.com/discovery/test?strategy=hybrid_v1&relaxed=true&limit=100"
```

### 4. Redis State Investigation
- Investigate Redis key naming conventions
- Verify data persistence between discovery runs
- Check TTL settings on candidate cache

## Risk Assessment for Live Trading

**Current Risk Level: UNACCEPTABLE**

**Specific Risks:**
1. **Zero Signal Generation**: No trading opportunities identified
2. **False System Confidence**: Health checks mask functional failures
3. **Strategy Inconsistency**: Hybrid_v1 completely non-functional
4. **Data Pipeline Integrity**: Discovery results not reaching trading logic
5. **Configuration Drift**: Active configuration not loaded into runtime system

**Trading Readiness: NOT READY**

The system cannot be used for live trading until the discovery-to-API pipeline is fully functional and hybrid_v1 strategy produces valid candidates.

## Next Steps

### Immediate Actions (0-24 hours)
1. Investigate configuration loading mechanism
2. Debug Redis key management and data flow
3. Implement temporary fallback to legacy_v0 strategy
4. Add end-to-end health checks

### Short-term Fixes (1-7 days)
1. Repair hybrid_v1 configuration loading
2. Fix discovery-to-API pipeline
3. Implement proper system state headers
4. Add configuration validation endpoints

### Long-term Improvements (1-4 weeks)
1. Comprehensive pipeline monitoring
2. Configuration hot-reloading capabilities
3. Multi-strategy validation framework
4. Enhanced error reporting and alerting

## Conclusion

The AMC-TRADER system shows concerning disconnects between reported health and actual functionality. While individual components appear healthy, the end-to-end discovery pipeline is completely broken for the hybrid_v1 strategy. The system requires immediate attention to configuration loading and data flow mechanisms before it can be considered ready for live trading operations.

**Status: SYSTEM NOT READY FOR LIVE TRADING**  
**Priority: CRITICAL REPAIR REQUIRED**  
**ETA for Readiness: 24-48 hours with focused debugging**