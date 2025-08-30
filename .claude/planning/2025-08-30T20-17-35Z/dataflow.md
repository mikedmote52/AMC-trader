---
run_id: 2025-08-30T20-17-35Z
version: 1
---

# AMC-TRADER Data Flow Analysis

## Primary Discovery Pipeline
```
Polygon API → Discovery Job → Redis Cache → FastAPI → React UI
    ↓              ↓             ↓           ↓         ↓
Price/Volume   Scoring      Contenders   JSON API   Display
Historical     VIGL Match   + Traces     Response   Components
```

### Discovery Job Data Flow
1. **Input**: Polygon grouped daily aggregates (`/v2/aggs/grouped/locale/us/market/stocks/{date}`)
2. **Processing**: 
   - Bulk filtering (price caps, volume minimums)
   - Compression analysis (Bollinger bandwidth percentiles)
   - VIGL pattern scoring (volume_spike * 0.40 + short_interest * 0.30 + catalyst * 0.15)
3. **Output**: 
   - `amc:discovery:contenders.latest` → Array of scored opportunities
   - `amc:discovery:explain.latest` → Pipeline trace data

### API Response Pipeline
```
Redis → FastAPI Route → JSON Response → React Component → UI Display
   ↓         ↓              ↓              ↓              ↓
Cached    /discovery/   Standardized   TopRecommend   Cards with
Data      contenders    Schema         Component      Buy buttons
```

## Portfolio Data Flow
```
Alpaca API → FastAPI Sync → Portfolio State → React Components
     ↓            ↓             ↓               ↓
Position      Account       Holdings JSON    PortfolioTiles
Data          Summary       + Thesis         + P&L Display
```

### Holdings Sync Process
1. **Trigger**: User action or scheduled sync
2. **Data**: `GET /v2/positions` from Alpaca
3. **Enhancement**: Thesis generator adds AI analysis
4. **Storage**: In-memory with API response caching
5. **Frontend**: Real-time P&L and recommendation display

## Trade Execution Flow
```
React UI → Trade Modal → FastAPI Validation → Alpaca API → Order Status
    ↓          ↓             ↓                   ↓            ↓
User Click  Form Data    Guardrails Check   Order Submit   Confirmation
```

### Order Processing Steps
1. **Frontend**: TradeModal collects symbol, action, quantity
2. **API**: `/trades/execute` validates against guardrails
3. **Risk**: Price cap check, position size limits, kill switch
4. **Execution**: Alpaca order submission with bracket stops
5. **Response**: Order confirmation or error details

## Data Shapes

### Discovery Contender
```json
{
  "symbol": "QUBT",
  "score": 0.847,
  "price": 3.95,
  "volume_spike": 25.7,
  "thesis": "EXTREME SQUEEZE ALERT: QUBT showing VIGL-like pattern...",
  "confidence": 0.89,
  "factors": {
    "vigl_similarity": 0.89,
    "volume_spike_ratio": 25.7,
    "compression_percentile": 5.2
  }
}
```

### Portfolio Position
```json
{
  "symbol": "UP",
  "qty": "100",
  "market_value": "1050.00",
  "unrealized_pl": "107.50",
  "unrealized_pl_pct": 0.1071,
  "avg_entry_price": "9.50",
  "last_price": "10.50"
}
```

## Cache TTL Strategy
- Discovery results: 600s (10 minutes) - Balance freshness vs API limits
- Pipeline traces: 600s - Debug data lifecycle matches results
- Job locks: 240s (4 minutes) - Prevent overlapping discovery runs