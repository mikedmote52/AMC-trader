---
run_id: 2025-08-30T20-17-35Z
analysis_date: 2025-08-30
system: AMC-TRADER  
focus: Enhanced Market Data Tools & Trading Execution Specifications
---

# AMC-TRADER Tools Specification

## Core Trading APIs

### Enhanced Market Data Tools

#### 1. Expanded Universe Data Source API
**Endpoint**: `/discovery/universe/expand`  
**Authentication**: Polygon API Key required  
**Function Signature**: `expand_universe(price_range: tuple, market_cap_range: tuple, min_volume: int) -> List[str]`

**Schema**:
```json
{
  "request": {
    "price_range": [0.50, 50.0],
    "market_cap_range": [10000000, 1000000000],
    "min_volume": 500000,
    "exclude_otc": true,
    "min_float": 5000000,
    "max_float": 75000000
  },
  "response": {
    "symbols": ["QUBT", "WULF", "MARA", "..."],
    "count": 1247,
    "filters_applied": {...},
    "refresh_timestamp": "2025-08-30T20:17:35Z"
  }
}
```

**Retry Policy**: 
- Exponential backoff: 1s, 2s, 4s, 8s, 16s
- Circuit breaker: 5 failures within 60s triggers 300s cooldown
- Fallback: Return cached universe from Redis `amc:universe:cached` (24hr TTL)

**Latency Budget**: P50: 2s, P95: 5s, P99: 8s  
**Rate Limits**: 5 requests/minute per API key
**Concurrency**: Max 2 parallel expansion requests

#### 2. Real-time Volume Spike Detection API
**Endpoint**: `/market-data/volume-spikes`  
**Authentication**: Polygon API Key + Redis access  
**Function Signature**: `detect_volume_spikes(symbols: List[str], spike_threshold: float = 5.0) -> List[VolumeSpike]`

**Schema**:
```json
{
  "request": {
    "symbols": ["QUBT", "MARA", "RIOT"],
    "spike_threshold": 10.0,
    "lookback_minutes": 30,
    "min_volume": 100000
  },
  "response": {
    "spikes": [
      {
        "symbol": "QUBT",
        "current_volume": 15670000,
        "avg_volume_30d": 785000,
        "spike_ratio": 19.96,
        "dollar_volume": 89500000,
        "detection_time": "2025-08-30T20:15:00Z",
        "confidence": 0.94
      }
    ],
    "alerts_triggered": 3,
    "processing_time_ms": 847
  }
}
```

**Retry Policy**:
- Real-time data: No retries, return cached data on failure
- Circuit breaker: 3 consecutive failures = 60s cooldown
- Graceful degradation: Use 5-minute delayed data if real-time fails

**Latency Budget**: P50: 300ms, P95: 800ms, P99: 1.2s
**Rate Limits**: 100 requests/minute during market hours
**Cache Strategy**: Redis TTL 30s for volume spike data

#### 3. Small-cap Screening and Filtering Tools  
**Endpoint**: `/screening/small-cap-filter`
**Authentication**: Polygon API Key  
**Function Signature**: `filter_small_caps(criteria: SmallCapCriteria) -> FilteredResults`

**Schema**:
```json
{
  "request": {
    "market_cap_max": 1000000000,
    "market_cap_min": 50000000,
    "price_range": [2.0, 25.0],
    "float_max": 50000000,
    "volume_min_30d": 500000,
    "exclude_sectors": ["REIT", "FUND"],
    "short_interest_min": 0.15
  },
  "response": {
    "filtered_symbols": [...],
    "total_screened": 4567,
    "passed_filters": 127,
    "filter_stats": {
      "price_filtered": 2340,
      "volume_filtered": 1200,
      "float_filtered": 900
    }
  }
}
```

**Retry Policy**: 
- Batch processing with checkpoints every 500 symbols
- Auto-resume on failure from last checkpoint
- Exponential backoff: 500ms, 1s, 2s, 4s

**Latency Budget**: P50: 15s, P95: 45s, P99: 90s
**Rate Limits**: 2 full scans per hour
**Processing**: Async with status updates via WebSocket

#### 4. Historical Pattern Matching Data Enricher
**Endpoint**: `/enrichment/pattern-match`
**Authentication**: Internal API key  
**Function Signature**: `enrich_with_patterns(symbol: str, patterns: List[str]) -> PatternMatchResult`

**Schema**:
```json
{
  "request": {
    "symbol": "QUBT",
    "patterns": ["VIGL", "CRWV", "AEVA"],
    "lookback_days": 252,
    "similarity_threshold": 0.75
  },
  "response": {
    "symbol": "QUBT",
    "pattern_matches": [
      {
        "pattern": "VIGL",
        "similarity_score": 0.87,
        "matched_date": "2023-11-15",
        "outcome_30d": 0.324,
        "confidence": "HIGH",
        "factors": {
          "volume_match": 0.92,
          "price_pattern_match": 0.81,
          "float_similarity": 0.88
        }
      }
    ],
    "enrichment_timestamp": "2025-08-30T20:17:35Z"
  }
}
```

**Retry Policy**:
- Pattern analysis: 3 retries with jitter (±20%)
- Database lookups: 2 retries for historical data
- Fallback: Return basic metrics if enrichment fails

**Latency Budget**: P50: 1.5s, P95: 4s, P99: 8s
**Rate Limits**: 50 enrichments/minute
**Cache Strategy**: Redis TTL 3600s for pattern matches

---

## Trading Execution Enhancements

### 1. Integrated Stop-Loss/Profit-Taking Order Tools
**Endpoint**: `/trading/bracket-orders`
**Authentication**: Alpaca API Key + 2FA  
**Function Signature**: `create_bracket_order(symbol: str, side: str, qty: int, stop_loss_pct: float, take_profit_pct: float) -> BracketOrderResult`

**Schema**:
```json
{
  "request": {
    "symbol": "QUBT",
    "side": "buy",
    "qty": 100,
    "order_type": "market",
    "stop_loss_pct": 0.08,
    "take_profit_pct": 0.25,
    "time_in_force": "day"
  },
  "response": {
    "parent_order_id": "abc123",
    "stop_loss_order_id": "def456", 
    "take_profit_order_id": "ghi789",
    "status": "submitted",
    "estimated_fill_price": 12.45,
    "risk_amount": 9.96,
    "profit_target": 155.63
  }
}
```

**Retry Policy**:
- Order submission: No retries (financial safety)
- Order status checks: 3 retries with 100ms intervals
- Connection failures: Immediate fallback to backup API endpoint

**Latency Budget**: P50: 150ms, P95: 400ms, P99: 800ms
**Rate Limits**: Alpaca account limits (200 orders/day)
**Safety Checks**: Position size validation, duplicate order prevention

### 2. One-Click Bracket Order API
**Endpoint**: `/trading/one-click-bracket`  
**Authentication**: Alpaca API Key + session token  
**Function Signature**: `one_click_bracket(symbol: str, confidence: float, account_risk_pct: float = 0.02) -> QuickOrderResult`

**Schema**:
```json
{
  "request": {
    "symbol": "QUBT",
    "confidence": 0.87,
    "account_risk_pct": 0.02,
    "max_position_value": 10000,
    "squeeze_score": 0.94
  },
  "response": {
    "calculated_position": {
      "shares": 80,
      "entry_price": 12.45,
      "position_value": 996,
      "stop_loss_price": 11.45,
      "take_profit_price": 15.56
    },
    "order_ids": {
      "parent": "abc123",
      "stop_loss": "def456",
      "take_profit": "ghi789"
    },
    "risk_metrics": {
      "account_risk_pct": 0.02,
      "max_loss_usd": 80.00,
      "reward_risk_ratio": 3.125
    }
  }
}
```

**Retry Policy**: 
- Pre-flight validation: 2 retries for account balance/margin
- Order execution: Single attempt (no retries for safety)
- Status confirmation: 5 retries with exponential backoff

**Latency Budget**: P50: 200ms, P95: 500ms, P99: 1s
**Rate Limits**: 20 one-click orders per hour
**Safety Features**: Circuit breaker on account loss > 5%

### 3. Risk Management Validation Tools  
**Endpoint**: `/trading/risk-validation`
**Authentication**: Internal service key  
**Function Signature**: `validate_trade_risk(trade_request: TradeRequest) -> RiskValidationResult`

**Schema**:
```json
{
  "request": {
    "symbol": "QUBT",
    "side": "buy",
    "quantity": 100,
    "price": 12.45,
    "account_value": 25000,
    "existing_positions": [...]
  },
  "response": {
    "approved": true,
    "risk_score": 0.23,
    "validations": {
      "position_size_check": "PASS",
      "correlation_check": "PASS", 
      "sector_concentration": "PASS",
      "volatility_check": "WARN"
    },
    "recommendations": [
      "Consider reducing position size due to high volatility",
      "Set stop-loss at 8% below entry"
    ],
    "max_recommended_shares": 80
  }
}
```

**Retry Policy**: 
- Risk calculations: 1 retry with fresh data
- Account data: 2 retries for balance/positions
- No retries on validation failures (safety first)

**Latency Budget**: P50: 100ms, P95: 250ms, P99: 500ms  
**Rate Limits**: Unlimited (internal service)
**Validation Rules**: Position size, correlation, sector limits

### 4. Order Status Tracking and Notifications
**Endpoint**: `/trading/order-status` (WebSocket)  
**Authentication**: JWT token + session validation  
**Function Signature**: `subscribe_order_updates(order_ids: List[str]) -> WebSocketStream`

**Schema**:
```json
{
  "subscription": {
    "order_ids": ["abc123", "def456"],
    "include_fills": true,
    "include_cancellations": true
  },
  "status_update": {
    "order_id": "abc123",
    "status": "filled",
    "filled_qty": 100,
    "avg_fill_price": 12.42,
    "timestamp": "2025-08-30T20:18:00Z",
    "commission": 0.00,
    "notification_sent": true
  }
}
```

**Retry Policy**:
- WebSocket reconnection: Exponential backoff (1s to 30s)
- Message delivery: 3 retry attempts
- Fallback: HTTP polling every 5s if WebSocket fails

**Latency Budget**: Real-time (<100ms for status updates)
**Rate Limits**: 1000 status updates per minute
**Notification Channels**: WebSocket, push notifications, email

---

## Discovery Pipeline Tools

### 1. Shadow Testing Framework for New Patterns  
**Endpoint**: `/discovery/shadow-test`
**Authentication**: Admin API key  
**Function Signature**: `run_shadow_test(test_config: ShadowTestConfig) -> ShadowTestResult`

**Schema**:
```json
{
  "request": {
    "test_name": "enhanced_vigl_v2",
    "test_duration_days": 30,
    "patterns_to_test": ["VIGL_V2", "CRWV_ENHANCED"],
    "control_pattern": "VIGL_V1",
    "sample_size": 100,
    "confidence_threshold": 0.75
  },
  "response": {
    "test_id": "shadow_test_001",
    "status": "running",
    "progress": {
      "days_completed": 5,
      "samples_processed": 23,
      "preliminary_results": {
        "v2_accuracy": 0.78,
        "v1_accuracy": 0.72,
        "improvement": 0.06
      }
    }
  }
}
```

**Retry Policy**:
- Test execution: No retries (maintain test integrity)
- Data collection: 3 retries with exponential backoff
- Result aggregation: 2 retries with validation

**Latency Budget**: Test setup: P50: 5s, Status check: P50: 200ms
**Rate Limits**: 2 concurrent shadow tests maximum
**Data Retention**: Test results kept 365 days

### 2. Regime Detection and Threshold Adjustment Tools
**Endpoint**: `/discovery/regime-detection`  
**Authentication**: Internal service key
**Function Signature**: `detect_market_regime() -> RegimeAnalysis`

**Schema**:
```json
{
  "response": {
    "current_regime": "HIGH_VOLATILITY",
    "regime_confidence": 0.89,
    "regime_duration_days": 12,
    "adjusted_thresholds": {
      "volume_spike_min": 15.0,
      "price_range": [1.0, 30.0],
      "short_interest_min": 0.10,
      "compression_max": 0.40
    },
    "regime_indicators": {
      "vix_level": 28.5,
      "market_breadth": 0.34,
      "sector_rotation": "high"
    },
    "next_adjustment": "2025-08-31T09:30:00Z"
  }
}
```

**Retry Policy**: 
- Market data collection: 2 retries with 1s delay
- Regime calculation: 1 retry with fresh data
- Threshold updates: No retries (applied immediately)

**Latency Budget**: P50: 800ms, P95: 2s, P99: 5s
**Rate Limits**: Updates every 30 minutes during market hours
**Cache Strategy**: Current regime cached 15 minutes

### 3. Pattern Confidence Scoring APIs
**Endpoint**: `/discovery/confidence-scoring`
**Authentication**: Internal API key  
**Function Signature**: `calculate_pattern_confidence(pattern_data: PatternData) -> ConfidenceScore`

**Schema**:
```json
{
  "request": {
    "symbol": "QUBT",
    "pattern_type": "VIGL_ENHANCED",
    "market_data": {
      "volume_spike": 19.8,
      "price": 12.45,
      "short_interest": 0.28,
      "float": 15000000
    },
    "historical_context": {...}
  },
  "response": {
    "confidence_score": 0.87,
    "confidence_tier": "HIGH",
    "contributing_factors": {
      "volume_match": 0.94,
      "price_range_match": 0.82,
      "float_similarity": 0.88,
      "timing_factors": 0.79
    },
    "risk_adjustments": {
      "wolf_risk": 0.23,
      "market_regime": 0.15
    },
    "final_adjusted_score": 0.84
  }
}
```

**Retry Policy**:
- Pattern calculations: 1 retry with validation
- Historical lookups: 2 retries with cache fallback
- Score aggregation: No retries (deterministic)

**Latency Budget**: P50: 400ms, P95: 1.2s, P99: 2.5s
**Rate Limits**: 200 scoring requests per minute
**Accuracy Target**: 85% correlation with actual outcomes

### 4. Winner Analysis Tools (June-July Focus)
**Endpoint**: `/analytics/winner-analysis`
**Authentication**: Research API key
**Function Signature**: `analyze_period_winners(start_date: str, end_date: str) -> WinnerAnalysis`

**Schema**:
```json
{
  "request": {
    "start_date": "2024-06-01",
    "end_date": "2024-07-31", 
    "min_return_threshold": 0.20,
    "analysis_types": ["pattern", "timing", "catalysts"]
  },
  "response": {
    "period_summary": {
      "total_winners": 47,
      "avg_return": 0.386,
      "median_return": 0.247,
      "max_return": 1.245
    },
    "pattern_analysis": {
      "vigl_like": 12,
      "breakout": 18,
      "squeeze": 8,
      "momentum": 9
    },
    "common_characteristics": {
      "avg_volume_spike": 18.2,
      "avg_price_range": [3.45, 18.90],
      "avg_float": 22500000,
      "most_common_sectors": ["Tech", "Biotech", "Energy"]
    },
    "actionable_insights": [...],
    "pattern_updates": {
      "recommended_thresholds": {...},
      "new_patterns_identified": [...]
    }
  }
}
```

**Retry Policy**:
- Historical data collection: 3 retries with 2s backoff
- Pattern analysis: 1 retry with validation
- Insight generation: No retries (computational)

**Latency Budget**: P50: 8s, P95: 25s, P99: 60s
**Rate Limits**: 5 analyses per hour (computationally expensive)
**Output**: Automated pattern updates and threshold recommendations

---

## API Requirements

### Polygon API Rate Limit Optimization
**Strategy**: Intelligent request batching and caching
- **Batch Size**: 50 symbols per grouped request
- **Cache TTL**: 30s for real-time data, 5min for historical
- **Rate Limiting**: 5 requests/second with burst allowance
- **Fallback**: Cached data when rate limited
- **Monitoring**: Track usage per endpoint, auto-scaling

### Alpaca API Bracket Order Integration  
**Features**: Native OCO (One-Cancels-Other) support
- **Order Types**: Market, limit, stop-loss, take-profit
- **Risk Management**: Automatic position sizing based on account risk
- **Error Handling**: Graceful degradation, order status validation
- **Notifications**: Real-time order status via WebSocket
- **Safety**: Duplicate order prevention, maximum loss limits

### Redis Cache Invalidation Strategies
**Cache Hierarchies**:
```
Level 1: Real-time data (30s TTL)
├── amc:market:volume_spikes.{timestamp}
├── amc:market:prices.latest  
└── amc:discovery:live_candidates

Level 2: Analysis results (10min TTL)  
├── amc:discovery:contenders.latest
├── amc:patterns:confidence_scores
└── amc:analysis:regime_detection

Level 3: Historical data (1hr TTL)
├── amc:patterns:historical_matches
├── amc:analytics:winner_analysis  
└── amc:universe:expanded_symbols
```

**Invalidation Triggers**:
- Market open/close events
- Significant volume spikes (>10x average)
- Manual cache flush via admin endpoint
- Failed data quality checks

### Database Migration Requirements for Enhanced Data

**New Tables**:
```sql
-- Enhanced pattern storage
CREATE TABLE pattern_matches (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    pattern_type VARCHAR(50) NOT NULL,
    similarity_score DECIMAL(5,4),
    matched_date DATE,
    outcome_7d DECIMAL(6,4),
    outcome_30d DECIMAL(6,4),
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_symbol_pattern (symbol, pattern_type),
    INDEX idx_similarity (similarity_score DESC)
);

-- Shadow testing results
CREATE TABLE shadow_tests (
    id SERIAL PRIMARY KEY,
    test_name VARCHAR(100) NOT NULL,
    test_config JSON,
    status VARCHAR(20) DEFAULT 'running',
    start_date DATE,
    end_date DATE,
    results JSON,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Market regime history
CREATE TABLE market_regimes (
    id SERIAL PRIMARY KEY,
    regime_type VARCHAR(30) NOT NULL,
    confidence DECIMAL(5,4),
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    indicators JSON,
    threshold_adjustments JSON
);

-- Enhanced discovery audit trail  
CREATE TABLE discovery_runs (
    id SERIAL PRIMARY KEY,
    run_timestamp TIMESTAMP DEFAULT NOW(),
    universe_size INTEGER,
    candidates_found INTEGER,
    avg_confidence DECIMAL(5,4),
    regime_type VARCHAR(30),
    processing_time_ms INTEGER,
    trace_data JSON
);
```

**Migration Strategy**:
1. **Phase 1**: Add new tables (no downtime)
2. **Phase 2**: Populate historical data (background job)
3. **Phase 3**: Update application to use new tables
4. **Phase 4**: Archive old data after 90-day validation period

**Data Retention**: 
- Pattern matches: 2 years
- Shadow tests: 1 year  
- Market regimes: 5 years
- Discovery runs: 6 months

**Backup Strategy**:
- Daily incremental backups
- Weekly full backups  
- Cross-region replication for disaster recovery
- Point-in-time recovery capability (7 days)

---

## Performance Requirements

### Latency Budgets
- **Real-time alerts**: <200ms end-to-end
- **Discovery pipeline**: <45s for full universe scan
- **Pattern matching**: <2s for single symbol
- **Order execution**: <500ms for bracket orders
- **API responses**: P95 <2s, P99 <5s

### Throughput Requirements  
- **Market data ingestion**: 1000 updates/second
- **Pattern detection**: 100 symbols/minute  
- **Order processing**: 50 orders/minute
- **API requests**: 500 requests/minute peak
- **WebSocket connections**: 100 concurrent users

### Concurrency and Connection Pooling
- **Polygon API**: 5 connections max, connection pooling
- **Alpaca API**: 3 connections, separate pool for orders  
- **Redis**: 20 connection pool, cluster-aware
- **PostgreSQL**: 50 connection pool with pgbouncer
- **WebSocket**: 100 concurrent connections per instance

### Resource Utilization Constraints
- **CPU**: 70% average, 90% peak (auto-scaling trigger)
- **Memory**: 80% average, 95% peak
- **Network**: 100 Mbps sustained, 500 Mbps burst
- **Disk I/O**: 80% utilization threshold
- **API Rate Limits**: 80% of provider limits maintained

## Monitoring and Observability

### Key Performance Indicators
```yaml
discovery_pipeline:
  - candidates_found_per_run
  - processing_time_percentiles  
  - pattern_match_accuracy
  - false_positive_rate

trading_execution:
  - order_fill_rate
  - average_slippage
  - bracket_order_success_rate
  - risk_management_rejections

system_health:
  - api_response_times
  - cache_hit_rates
  - error_rates_by_endpoint
  - resource_utilization
```

### Alerting Thresholds
- **Critical**: Discovery pipeline down >5 minutes
- **Warning**: Pattern confidence <75% for >1 hour  
- **Info**: Cache hit rate <80%
- **Escalation**: Trading API errors >5% in 10 minutes

This comprehensive tools specification provides the technical foundation for enhancing AMC-TRADER's monthly profit optimization through improved squeeze detection, expanded discovery capabilities, and robust trading execution tools.