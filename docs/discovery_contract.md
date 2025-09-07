# Discovery Contract Documentation

## Overview

This document defines the **frozen contract** for the AMC-TRADER discovery pipeline, ensuring perfect alignment between writers (discovery job) and readers (API routes).

## Redis Key Patterns

All Redis keys are managed by `backend/src/utils/redis_keys.py` to ensure consistency.

### Contenders Storage
```
amc:discovery:v2:contenders.latest:{strategy}    # Strategy-specific results
amc:discovery:v2:contenders.latest              # Base fallback results
```

### Metadata Storage  
```
amc:discovery:v2:metadata:{strategy}            # Discovery run metadata
feat:{type}:{symbol}                            # Feature store data
```

### Feature Store Keys
```
feat:quotes:{symbol}        # Live quote data (price, volume, timestamp)
feat:bars_1m:{symbol}       # 1-minute OHLCV bars
feat:vwap:{symbol}          # Volume-weighted average price
```

## API Endpoints

### `/discovery/contenders`

**Route Contract (FROZEN):**
- Reads from `get_contenders_key(strategy)` with fallback to base key
- NO route-level filtering - returns exactly what discovery job wrote
- Score normalization: 0-1 decimal → 0-100 percentage  
- Required headers: `X-System-State`, `X-Reason-Stats`, `Cache-Control: no-store`

**Input:** Query parameter `strategy` (optional)

**Output Schema:**
```json
[
  {
    "symbol": "string",
    "score": "number (0-100)",
    "meta_score": "number (0-100)",
    "features": "object",
    "action_tag": "string (trade_ready|watchlist)",
    "timestamp": "string (ISO)"
  }
]
```

**Required Headers:**
```
X-System-State: HEALTHY|DEGRADED|FAILED
X-Reason-Stats: {"stale": 0, "gate": 0, "error": 0, "scored": N}
Cache-Control: no-store
```

### `/discovery/contenders/raw`

**Production Protection:**
- Requires `X-Admin-Token` header matching `ADMIN_TOKEN` env var
- Returns 403 without valid token in production
- No authentication required in development

**Output:** Unfiltered Redis data (same schema as `/contenders`)

### `/discovery/test`

**Production Protection:**
- Disabled in production (`ENV=prod` → 403)
- Available only in development environments
- Used for strategy testing and debugging

## Strategy Resolution

**Priority Order:**
1. Query parameter `?strategy=X`
2. Environment variable `SCORING_STRATEGY`  
3. Calibration config default
4. No silent overrides

**Supported Strategies:**
- `legacy_v0` - Original VIGL-based scoring
- `hybrid_v1` - 5-subscore system with gatekeeping

## Data Flow Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Discovery     │    │      Redis      │    │   API Routes    │
│      Job        │───▶│   Key Store     │───▶│   (Frozen)      │
│  (Writer)       │    │                 │    │   (Reader)      │  
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

**Key Principles:**
1. **Single Source of Truth:** Discovery job writes, routes read
2. **No Database Persistence:** Discovery pipeline remains Redis-only
3. **Perfect Key Alignment:** Unified key helper ensures consistency
4. **Fail-Closed:** Empty results when Redis unavailable

## Freshness Enforcement

**Polygon Pro Mode Thresholds:**
- **Quotes:** ≤2 seconds during RTH, ≤10 seconds AH
- **1-min Bars:** ≤15 seconds during RTH, ≤60 seconds AH  
- **VWAP:** ≤30 seconds anytime

**Fail-Closed Behavior:**
- Return empty results if >40% of features are stale
- Set `X-System-State: DEGRADED` in headers
- Log structured warnings for monitoring

## Monitoring & Regression Detection

### Watchdog Alerts
**Trigger Conditions:**
1. `raw_count > 0 && served_count == 0` (pipeline regression)
2. Missing required headers (`X-System-State`, etc.)
3. `X-System-State: DEGRADED` during regular trading hours

**Alert Channels:**
- Slack webhook notifications
- Structured logging for ops dashboards
- CI/CD pipeline failures

### CI Gating Tests
**Blocking Conditions:**
1. Contenders regression check fails
2. Required headers missing from responses
3. Invalid JSON response structure
4. Production endpoint protections bypassed

## Security Controls

### Production Hardening
- `/discovery/contenders/raw` requires admin token
- `/discovery/test` disabled (403)
- No sensitive data in logs
- Structured logging for audit trails

### Development Access
- All endpoints available without restrictions
- Debug information accessible
- Test data generation allowed

## Error Handling

**Redis Unavailable:**
```json
[]  // Empty array with headers still set
```

**Invalid Strategy:**
```json
[]  // Falls back to base key, then empty
```

**Feature Store Stale:**
```json
[]  // Fail-closed, empty with X-System-State: DEGRADED
```

## Version History

- **v2**: Current version with strategy suffixes and frozen contract
- **v1**: Legacy version (deprecated, fallback only)

## Usage Examples

### Trigger Discovery
```bash
curl -s -X POST "$API/discovery/trigger?strategy=legacy_v0&limit=200" \
  | jq '{candidates_found}'
```

### Get Contenders  
```bash
curl -s "$API/discovery/contenders?strategy=legacy_v0" \
  | jq 'length'
```

### Check Headers
```bash
curl -i -s "$API/discovery/contenders?strategy=legacy_v0" \
  | grep -E "(X-System-State|X-Reason-Stats|Cache-Control)"
```

### Raw Access (Admin)
```bash
curl -s "$API/discovery/contenders/raw?strategy=legacy_v0" \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  | jq 'length'
```

### Health Check
```bash
curl -s "$API/discovery/ping/polygon" \
  | jq '.overall.polygon_healthy'
```

## Compliance Requirements

1. **Never modify this contract without full regression testing**
2. **Always maintain header consistency** 
3. **Preserve fail-closed behavior** during degraded states
4. **Log all contract changes** with structured metadata
5. **Test strategy alignment** before deploying key changes

This contract is **FROZEN** to prevent the regression where discovery finds candidates but the API returns empty arrays. Any changes must go through full validation with smoke tests and watchdog monitoring.