---
run_id: 2025-08-30T20-17-35Z
version: 1
---

# AMC-TRADER API Contracts

## Discovery Endpoints

### `GET /discovery/contenders`
**Used by**: `TopRecommendations.tsx:25`
**Response Shape**:
```json
[
  {
    "symbol": "QUBT",
    "score": 0.847,
    "price": 3.95,
    "thesis": "EXTREME SQUEEZE ALERT: QUBT showing VIGL-like pattern with 25.7x volume spike...",
    "confidence": 0.89,
    "factors": {
      "vigl_similarity": 0.89,
      "volume_spike_ratio": 25.7,
      "atr_percent": 8.2,
      "compression_percentile": 5.2,
      "rs_5d_percent": 12.4
    }
  }
]
```

### `GET /discovery/squeeze-candidates`
**Used by**: `SqueezeMonitor.tsx:48`
**Response Shape**:
```json
[
  {
    "symbol": "VIGL",
    "squeeze_score": 0.87,
    "volume_spike": 20.9,
    "short_interest": 0.18,
    "price": 4.12,
    "pattern_type": "VIGL_SQUEEZE",
    "confidence": 0.89,
    "detected_at": "2025-08-30T20:15:00Z"
  }
]
```

### `GET /discovery/explain`
**Purpose**: Pipeline trace data for debugging
**Response Shape**:
```json
{
  "ts": "2025-08-30T20:15:00Z",
  "count": 7,
  "trace": {
    "stages": ["universe", "compression_filter", "vigl_filter"],
    "counts_in": {"universe": 8400, "compression_filter": 127},
    "counts_out": {"universe": 8400, "compression_filter": 45},
    "rejections": {
      "compression_filter": {"price_cap": 3200, "dollar_vol_min": 1800}
    }
  }
}
```

## Portfolio Endpoints

### `GET /portfolio/holdings`
**Used by**: Portfolio components
**Response Shape**:
```json
[
  {
    "symbol": "UP",
    "qty": "100",
    "side": "long",
    "market_value": "1050.00",
    "unrealized_pl": "107.50",
    "unrealized_pl_pct": 0.1071,
    "avg_entry_price": "9.50",
    "last_price": "10.50"
  }
]
```

### `GET /portfolio/enhanced`
**Used by**: Portfolio tiles with thesis
**Response Shape**:
```json
[
  {
    "symbol": "UP",
    "position": {/* position data */},
    "thesis": {
      "recommendation": "TRIM",
      "confidence": 0.85,
      "thesis": "🚀 UP: TRIM POSITION - Lock in spectacular +107% gains...",
      "reasoning": "Exceptional +107% gains are rare and unsustainable..."
    }
  }
]
```

## Trade Execution

### `POST /trades/execute`
**Used by**: `TradeModal.tsx`
**Request Shape**:
```json
{
  "symbol": "QUBT",
  "action": "BUY",
  "mode": "live",
  "qty": 10,
  "bracket": true,
  "stop_loss_pct": 0.08,
  "take_profit_pct": 0.25
}
```

**Response Shape**:
```json
{
  "success": true,
  "order_id": "abc123",
  "symbol": "QUBT",
  "action": "BUY",
  "qty": 10,
  "filled_price": 3.97,
  "status": "filled"
}
```

## System Endpoints

### `GET /health`
**Response Shape**:
```json
{
  "status": "healthy",
  "components": {
    "database": {"ok": true},
    "redis": {"ok": true},
    "polygon": {"ok": true},
    "alpaca": {"ok": true}
  },
  "tag": "trace_v3",
  "commit": "abc123",
  "build": "build456"
}
```

## Error Response Format
**Standard across all endpoints**:
```json
{
  "success": false,
  "error": "PRICE_CAP_EXCEEDED",
  "detail": "Price $125.00 exceeds limit $100.00",
  "tag": "trace_v3"
}
```

## Frontend Integration Notes
- All API calls use `getJSON()` helper from `src/lib/api.ts`
- Polling intervals: 15s for critical data, 60s for portfolio updates
- Error handling: Display user-friendly messages, retry capability
- TypeScript interfaces match API response shapes