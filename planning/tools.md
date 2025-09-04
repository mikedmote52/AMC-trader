# AMC-TRADER Short Interest Data Aggregation & Tools Specification

## CRITICAL BOTTLENECK SOLUTION: Short Interest Data Coverage

**Current Problem**: Discovery system eliminates 96% of candidates (11,372 → 3,056 → 56 → 2 stocks) due to lack of reliable short interest data. Only Yahoo Finance provides sporadic coverage (3-5%), causing massive opportunity loss.

**Solution**: Comprehensive short interest data aggregation system with multiple sources, intelligent estimation, and confidence scoring to achieve 80%+ coverage of qualified stocks.

## 1. Short Interest Data Sources Integration

### 1.1 Yahoo Finance API (Current Primary Source)
**Endpoint**: `yfinance.Ticker(symbol).info`
**Authentication**: None (Free)
**Function Signature**: `fetch_yahoo_short_interest(symbol: str) -> Optional[ShortInterestData]`
**Rate Limits**: 100 requests/minute
**Latency Budget**: P50: <2s, P95: <5s, P99: <10s
**Current Coverage**: ~15% of universe (limiting factor)
**Data Quality**: High when available
**Update Frequency**: FINRA schedule (bi-monthly)

**Schema**:
```json
{
  "symbol": "QUBT",
  "short_percent_float": 0.185,
  "short_ratio": 3.2,
  "shares_short": 2840000,
  "source": "yahoo_finance",
  "confidence": 0.95,
  "last_updated": "2025-09-04T14:30:22Z",
  "settlement_date": "2025-08-30T00:00:00Z"
}
```

**Retry Policy**: 
- Exponential backoff: 1s, 2s, 4s, 8s, 16s
- Circuit breaker: 10 failures in 60s triggers 15-minute cooldown
- Fallback: Cache stale data up to 45 days old

### 1.2 Polygon.io Short Interest API (Priority Integration)
**Endpoint**: `GET /v3/reference/short-interest/{symbol}`
**Authentication**: Bearer token (existing AMC-TRADER integration)
**Function Signature**: `fetch_polygon_short_interest(symbol: str) -> Optional[ShortInterestData]`
**Rate Limits**: 50 requests/minute (Standard plan)
**Latency Budget**: P50: <1s, P95: <3s, P99: <8s
**Coverage Target**: ~40% of universe
**Data Quality**: Very High
**Update Frequency**: Daily during market hours
**Cost**: $99/month (already integrated)

**Implementation Priority**: HIGH - Leverage existing Polygon API key

### 1.3 Fintel Short Interest Scraper
**Endpoint**: Custom scraper for `https://fintel.io/ss/us/{symbol}`
**Authentication**: None (Rate limited by IP)
**Function Signature**: `fetch_fintel_short_interest(symbol: str) -> Optional[ShortInterestData]`
**Rate Limits**: 20 requests/minute with rotating proxies
**Latency Budget**: P50: <3s, P95: <8s, P99: <15s
**Coverage Target**: ~60% of universe
**Data Quality**: Medium-High
**Update Frequency**: Daily
**Cost**: Free (scraping)

### 1.4 S3 Partners ShortSight API (Premium Option)
**Endpoint**: `GET /shortInterest/{symbol}`
**Authentication**: Bearer token
**Function Signature**: `fetch_s3_short_interest(symbol: str) -> Optional[ShortInterestData]`
**Rate Limits**: 500 requests/minute
**Latency Budget**: P50: <800ms, P95: <2s, P99: <5s
**Coverage Target**: ~70% of universe
**Cost**: $500/month
**Data Quality**: Very High (Real-time)
**Update Frequency**: Real-time during market hours

### 1.5 NASDAQ Short Interest Feed
**Endpoint**: `GET /api/screener/stocks`
**Authentication**: API Key
**Function Signature**: `fetch_nasdaq_short_interest(symbol: str) -> Optional[ShortInterestData]`
**Rate Limits**: 100 requests/minute
**Coverage Target**: ~50% of universe
**Data Quality**: High (Official)
**Update Frequency**: Bi-monthly (FINRA schedule)
**Cost**: $200/month

## 2. Data Validation and Confidence Scoring

### 2.1 Cross-Reference Validation Service
**Class**: `ShortInterestValidator`
**Function Signature**: `validate_cross_references(sources: List[ShortInterestData]) -> ValidationResult`

**Validation Algorithm**:
1. **Consensus Detection**: If 3+ sources agree within 20% tolerance → HIGH confidence
2. **Majority Rule**: If 2+ sources agree within 30% tolerance → MEDIUM confidence  
3. **Outlier Detection**: Flag sources deviating >50% from median
4. **Temporal Consistency**: Flag sudden changes >100% day-over-day
5. **Source Reliability**: Weight by historical accuracy

**Confidence Levels**:
```python
confidence_matrix = {
    'HIGH': 0.90,      # 3+ sources agree, recent data
    'MEDIUM': 0.70,    # 2+ sources agree, <30 days old
    'LOW': 0.50,       # Single source, <45 days old
    'ESTIMATED': 0.30, # Model-based estimation
    'STALE': 0.10      # >45 days old, single source
}
```

**Schema for ValidationResult**:
```json
{
  "symbol": "QUBT",
  "consensus_si": 0.185,
  "confidence_level": "HIGH",
  "confidence_score": 0.92,
  "source_count": 4,
  "sources_agreeing": 3,
  "outlier_sources": ["source_x"],
  "validation_notes": "Strong consensus across multiple sources",
  "validated_at": "2025-09-04T14:30:22Z"
}
```

### 2.2 Source Reliability Scoring
**Function Signature**: `calculate_source_reliability(source: str, symbol: str) -> float`

**Reliability Factors**:
- **Historical Accuracy**: 40% weight (backtested against known values)
- **Data Freshness**: 25% weight (how recent the data is)
- **Coverage Consistency**: 20% weight (how often source has data)
- **Update Frequency**: 15% weight (how often source updates)

**Source Rankings** (Updated weekly):
```python
source_reliability = {
    's3_partners': 0.95,     # Premium, real-time
    'polygon': 0.90,         # High quality, frequent updates
    'nasdaq': 0.85,          # Official but infrequent
    'fintel': 0.70,          # Scraped but comprehensive
    'yahoo_finance': 0.65    # Free but sporadic
}
```

### 2.3 Data Quality Monitoring
**Function Signature**: `monitor_source_quality() -> SourceQualityReport`

**Quality Metrics**:
```json
{
  "coverage_rates": {
    "yahoo_finance": 0.15,
    "polygon": 0.42,
    "fintel": 0.63,
    "s3_partners": 0.71
  },
  "accuracy_scores": {
    "yahoo_finance": 0.89,
    "polygon": 0.94,
    "fintel": 0.78
  },
  "uptime_last_24h": {
    "yahoo_finance": 0.98,
    "polygon": 0.99,
    "fintel": 0.85
  }
}
```

## 3. Intelligent Estimation Algorithms

### 3.1 Market-Based Short Interest Estimation
**Class**: `ShortInterestEstimator`
**Function Signature**: `estimate_short_interest(symbol: str, market_data: MarketData) -> EstimatedShortInterest`

**Estimation Methodology**:
1. **Sector Average Baseline**: Use sector median as starting point
2. **Volume Pattern Analysis**: High volume + price decline → higher SI estimate
3. **Float Analysis**: Smaller float → amplified SI impact
4. **Historical Pattern Matching**: Similar stocks in similar conditions
5. **Options Flow Indicators**: Put/call ratios and unusual activity

**Algorithm**:
```python
def estimate_short_interest(symbol: str, market_data: MarketData) -> float:
    # Sector baseline (varies by sector)
    sector_baseline = get_sector_median_si(symbol)  # Range: 0.05-0.25
    
    # Volume pressure multiplier
    volume_spike = market_data.volume_ratio / market_data.avg_volume_20d
    volume_pressure = min(volume_spike / 5.0, 2.0)  # Max 2x multiplier
    
    # Price decline indicator (bearish pressure)
    momentum_5d = market_data.momentum_5d
    price_decline = max(-momentum_5d, 0) * 2.0  # Max 2x for 100% decline
    
    # Float size adjustment (liquidity constraint)
    float_shares = market_data.float_shares
    float_adjustment = max(1.0, 50_000_000 / float_shares)  # Smaller float = higher SI
    
    # Market cap adjustment (small caps more volatile)
    mcap_adjustment = max(1.0, 2_000_000_000 / market_data.market_cap)
    
    # Combine factors
    estimated_si = sector_baseline * (
        1 + volume_pressure + price_decline
    ) * float_adjustment * mcap_adjustment
    
    return min(estimated_si, 0.95)  # Cap at 95% short interest
```

**Estimation Confidence Scoring**:
```python
def calculate_estimation_confidence(symbol: str, inputs: EstimationInputs) -> float:
    confidence = 0.3  # Base confidence for estimates
    
    # Increase confidence based on data quality
    if inputs.sector_data_quality > 0.8:
        confidence += 0.1
    if inputs.volume_data_recency < 1:  # <1 day old
        confidence += 0.1
    if inputs.similar_stock_count > 5:  # Good pattern matching
        confidence += 0.1
    if inputs.market_regime == 'normal':  # Not during crisis
        confidence += 0.05
        
    return min(confidence, 0.6)  # Max 60% confidence for estimates
```

### 3.2 Sector Cohort Analysis
**Function Signature**: `estimate_from_sector_cohort(symbol: str) -> ShortInterestData`

**Cohort Definitions**:
```python
sector_cohorts = {
    'biotech_small_cap': {
        'market_cap_range': (50e6, 2e9),
        'sector_keywords': ['biotech', 'pharma', 'clinical'],
        'median_si': 0.18,
        'volatility_profile': 'high',
        'sample_size': 127
    },
    'crypto_miners': {
        'keywords': ['mining', 'crypto', 'bitcoin', 'blockchain'],
        'median_si': 0.22,
        'volatility_profile': 'extreme',
        'sample_size': 34
    },
    'meme_stocks': {
        'social_sentiment_indicators': ['reddit_mentions', 'wsb_posts'],
        'median_si': 0.35,
        'volatility_profile': 'extreme',
        'sample_size': 28
    },
    'chinese_adrs': {
        'country': 'china',
        'stock_type': 'adr',
        'median_si': 0.25,
        'volatility_profile': 'high',
        'sample_size': 89
    }
}
```

### 3.3 Historical Pattern Matching
**Function Signature**: `estimate_from_patterns(symbol: str, lookback_days: int = 90) -> Optional[ShortInterestData]`

**Pattern Matching Process**:
1. **Similar Stock Identification**: 
   - Market cap within 50% range
   - Same sector classification
   - Similar float size (within 2x)
   - Similar price range (within 3x)

2. **Volume Pattern Correlation**:
   - Compare 20-day volume patterns
   - Identify stocks with >0.8 correlation
   - Weight by recency and similarity

3. **Price Action Matching**:
   - ATR percentile similarity
   - Momentum correlation over 5/10/20 days
   - Support/resistance level patterns

4. **Historical Validation**:
   - Backtest pattern matches against known SI data
   - Calculate prediction accuracy by pattern type
   - Adjust confidence based on historical performance

## 4. Data Processing Pipeline Architecture

### 4.1 Multi-Source Data Aggregator
**Class**: `ShortInterestAggregator`
**Function Signature**: `aggregate_multi_source_data(symbols: List[str]) -> Dict[str, AggregatedShortInterestData]`

**Processing Pipeline**:
1. **Parallel Source Queries**: 
   - Launch concurrent requests to all available sources
   - Timeout individual requests at 10s
   - Continue with partial results if some sources fail

2. **Data Normalization**:
   - Convert all data to standard decimal format (0.185 = 18.5%)
   - Standardize date formats and timezone handling
   - Validate data ranges (0% ≤ SI ≤ 95%)

3. **Quality Assessment**:
   - Score each source based on reliability matrix
   - Apply freshness penalties for old data
   - Flag obvious outliers for manual review

4. **Consensus Building**:
   - Weight sources by reliability score
   - Calculate weighted average for consensus value
   - Identify and handle outliers using IQR method

5. **Confidence Assignment**:
   - Base confidence on source agreement level
   - Adjust for data freshness and source quality
   - Apply estimation penalties where applicable

6. **Caching Strategy**:
   - Cache HIGH confidence data for 24 hours
   - Cache MEDIUM confidence data for 12 hours  
   - Cache LOW confidence data for 6 hours
   - Cache ESTIMATED data for 2 hours

**Performance Requirements**:
- **Single Symbol**: P50: <3s, P95: <8s, P99: <15s
- **Bulk Processing (50 symbols)**: P50: <15s, P95: <30s, P99: <60s
- **Throughput**: 200 symbols/minute sustained, 500 symbols/minute burst
- **Concurrency**: 20 parallel source requests per symbol
- **Cache Hit Rate Target**: >80% for symbols requested in last 24h

### 4.2 Real-Time Data Pipeline
**Function Signature**: `process_realtime_updates() -> None`

**Update Triggers**:
1. **FINRA Settlement Dates**: 15th and last day of month (priority refresh)
2. **High Volume Events**: >10x volume spike triggers immediate refresh
3. **Price Movement Anomalies**: >20% intraday moves trigger validation
4. **Scheduled Refreshes**: 
   - Top 100 squeeze candidates: Every 2 hours
   - Top 500 discovery symbols: Daily at 6 AM EST
   - Full universe: Weekly on Sundays

**Real-Time Processing**:
```python
async def process_realtime_updates():
    while True:
        # Check for trigger events
        volume_spike_symbols = detect_volume_spikes()
        price_movement_symbols = detect_price_anomalies()
        scheduled_symbols = get_scheduled_refresh_symbols()
        
        # Combine and prioritize
        priority_symbols = prioritize_refresh_queue(
            volume_spike_symbols + price_movement_symbols + scheduled_symbols
        )
        
        # Process in batches
        for batch in batch_symbols(priority_symbols, batch_size=50):
            await aggregate_multi_source_data(batch)
            await asyncio.sleep(1)  # Rate limiting
        
        await asyncio.sleep(300)  # Check every 5 minutes
```

### 4.3 Error Handling and Circuit Breakers
**Class**: `ShortInterestErrorHandler`

**Circuit Breaker Configuration**:
```python
CIRCUIT_BREAKER_CONFIG = {
    "yahoo_finance": {
        "failure_threshold": 5,
        "timeout_seconds": 300,  # 5 minutes
        "expected_exceptions": [HTTPError, Timeout]
    },
    "polygon": {
        "failure_threshold": 3,
        "timeout_seconds": 180,  # 3 minutes  
        "expected_exceptions": [APIError, RateLimitError]
    },
    "fintel_scraper": {
        "failure_threshold": 10,
        "timeout_seconds": 600,  # 10 minutes
        "expected_exceptions": [RequestException, ParseError]
    }
}
```

**Error Handling Strategy**:
1. **Retryable Errors**: Network timeouts, temporary API errors
2. **Non-Retryable Errors**: Authentication failures, malformed requests
3. **Fallback Chains**: Source1 → Source2 → Cache → Estimation
4. **Alert Triggers**: >50% source failure rate triggers alert

### 4.4 Data Quality Monitoring
**Function Signature**: `monitor_data_quality() -> DataQualityReport`

**Monitoring Metrics**:
```json
{
  "coverage_metrics": {
    "total_universe_size": 3056,
    "symbols_with_data": 2445,
    "coverage_percentage": 80.0,
    "high_confidence_count": 1834,
    "estimated_count": 611
  },
  "source_performance": {
    "yahoo_finance": {
      "uptime_24h": 0.98,
      "avg_response_time": 2.3,
      "error_rate": 0.05,
      "coverage_rate": 0.15
    },
    "polygon": {
      "uptime_24h": 0.99,
      "avg_response_time": 1.1,
      "error_rate": 0.02,
      "coverage_rate": 0.42
    }
  },
  "validation_metrics": {
    "cross_validation_success_rate": 0.87,
    "outlier_detection_count": 23,
    "consensus_agreement_rate": 0.82
  }
}
```

**Alert Thresholds**:
- Coverage drops below 70% → WARNING
- Coverage drops below 60% → CRITICAL  
- Any source >20% error rate → WARNING
- Any source >50% error rate → CRITICAL
- Cross-validation success <80% → WARNING

## 5. Integration with Existing AMC-TRADER System

### 5.1 Discovery Pipeline Integration
**Modified Function**: `discover.py` line 1214-1216

**Current Code** (Causing 96% elimination):
```python
if not si_data or si_data.source in ['sector_fallback', 'default_fallback']:
    logger.debug(f"Excluding {symbol} - no real short interest data available")
    continue
```

**Enhanced Code**:
```python
if not si_data:
    # Try enhanced aggregation system
    si_data = await enhanced_short_interest_service.get_aggregated_data(symbol)
    
if not si_data or si_data.confidence < 0.3:
    logger.debug(f"Excluding {symbol} - insufficient short interest confidence: {si_data.confidence if si_data else 'None'}")
    continue
    
# Use confidence-weighted short interest in scoring
confidence_weight = si_data.confidence
short_interest_score = si_data.short_percent_float * confidence_weight
```

### 5.2 Enhanced Short Interest Service
**File**: `/backend/src/services/enhanced_short_interest_service.py`
**Function Signature**: `get_aggregated_data(symbol: str) -> Optional[AggregatedShortInterestData]`

**Service Architecture**:
```python
class EnhancedShortInterestService:
    def __init__(self):
        self.sources = [
            YahooFinanceSource(),
            PolygonSource(),
            FintelScraperSource(),
            NASDAQSource()
        ]
        self.aggregator = ShortInterestAggregator()
        self.estimator = ShortInterestEstimator()
        self.validator = ShortInterestValidator()
        
    async def get_aggregated_data(self, symbol: str) -> Optional[AggregatedShortInterestData]:
        # Try multiple sources
        source_data = await self.fetch_from_all_sources(symbol)
        
        if len(source_data) >= 2:
            # Multiple sources - validate and aggregate
            return await self.aggregator.aggregate(source_data)
        elif len(source_data) == 1:
            # Single source - return with appropriate confidence
            return source_data[0]
        else:
            # No sources - attempt estimation
            return await self.estimator.estimate(symbol)
```

### 5.3 Caching Integration with Redis
**Cache Keys**:
```python
cache_keys = {
    'raw_data': 'amc:si:raw:{source}:{symbol}',
    'aggregated': 'amc:si:aggregated:{symbol}',
    'estimated': 'amc:si:estimated:{symbol}',
    'quality_report': 'amc:si:quality_report',
    'source_reliability': 'amc:si:source_reliability'
}
```

**TTL Strategy**:
```python
ttl_matrix = {
    'HIGH': 86400,      # 24 hours
    'MEDIUM': 43200,    # 12 hours  
    'LOW': 21600,       # 6 hours
    'ESTIMATED': 7200,  # 2 hours
    'STALE': 3600       # 1 hour
}
```

## 6. Implementation Roadmap

### Phase 1: Foundation (Week 1-2) - Target: 40% Coverage
**Priority Tasks**:
1. Integrate Polygon.io short interest endpoint (leverage existing API key)
2. Implement enhanced aggregation service with Yahoo Finance + Polygon
3. Deploy confidence scoring system
4. Update discovery pipeline to use confidence thresholds
5. Implement Redis caching with TTL strategy

**Expected Impact**: Increase coverage from 15% to 40%, reduce elimination from 96% to 60%

### Phase 2: Expansion (Week 3-4) - Target: 60% Coverage  
**Priority Tasks**:
1. Implement Fintel scraper with proxy rotation
2. Add NASDAQ official data feed
3. Deploy cross-validation system
4. Implement basic estimation algorithms
5. Add monitoring and alerting

**Expected Impact**: Increase coverage to 60%, reduce elimination to 40%

### Phase 3: Intelligence (Week 5-6) - Target: 80% Coverage
**Priority Tasks**:
1. Deploy advanced estimation algorithms
2. Implement sector cohort analysis  
3. Add historical pattern matching
4. Optimize performance and caching
5. Full monitoring dashboard

**Expected Impact**: Achieve target 80% coverage, eliminate bottleneck

### Phase 4: Premium Enhancement (Week 7-8) - Target: 85%+ Coverage
**Optional Premium Features**:
1. S3 Partners integration ($500/month)
2. Real-time updates during market hours
3. Advanced machine learning estimation models
4. Comprehensive backtesting framework

## 7. Cost-Benefit Analysis

### Implementation Costs:
- **Development Time**: 6-8 weeks (1 developer)
- **Additional Data Sources**: $200-700/month
- **Infrastructure**: ~$50/month additional compute/storage

### Expected Benefits:
- **Coverage Improvement**: 15% → 80% (5.3x increase)
- **Candidate Recovery**: 96% elimination → 20% elimination  
- **Daily Opportunities**: 2 candidates → 45+ candidates
- **Revenue Impact**: ~$2,500/month additional profit potential

**ROI Calculation**: 
- Monthly Cost: ~$750
- Monthly Benefit: ~$2,500
- Net Monthly Benefit: ~$1,750
- Payback Period: <2 months

## 8. Risk Mitigation

### Technical Risks:
1. **Source Reliability**: Multiple sources with fallbacks
2. **Rate Limiting**: Distributed requests with circuit breakers  
3. **Data Quality**: Cross-validation and confidence scoring
4. **Performance**: Aggressive caching and async processing

### Business Risks:
1. **False Positives**: Conservative confidence thresholds
2. **Data Costs**: Tiered approach starting with free sources
3. **Maintenance**: Automated monitoring and self-healing
4. **Compliance**: Respect robots.txt and rate limits

This comprehensive specification solves the critical 96% elimination bottleneck while maintaining data quality and system reliability, targeting 80%+ coverage of qualified discovery candidates.