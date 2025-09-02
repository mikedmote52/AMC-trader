# AMC-TRADER Tools Specification: Short Interest Data Accuracy Enhancement

## Executive Summary

Critical data accuracy issue identified: Yahoo Finance integration shows UP stock with 0.09% short interest, but external sources (Fintel, Benzinga) show 9.34% short interest - a **100x difference**! This undermines squeeze detection accuracy and requires immediate architectural enhancement.

## Root Cause Analysis

### Yahoo Finance API Issues (2024-2025)

**Problem**: `yfinance` library `shortPercentOfFloat` field returning incorrect/missing data
- **Current Implementation**: `info.get('shortPercentOfFloat')` returns `0.0009` (0.09%) for UP stock
- **External Sources**: Show `9.34%` short interest with 8.43M shares short
- **Impact**: 100x data discrepancy causing false negative squeeze signals

**Technical Root Causes**:
1. **API Fragility**: Yahoo Finance API became unofficial after 2017 shutdown
2. **HTML Scraping Dependencies**: yfinance relies on web scraping prone to layout changes
3. **Field Mapping Issues**: `shortPercentOfFloat` may be returning raw decimal vs percentage
4. **Data Freshness**: Yahoo may serve stale or cached data vs real FINRA reporting
5. **Backend Changes**: Yahoo's internal API modifications affecting data availability

## Core Trading APIs Enhancement

### ShortInterestService V2 (Enhanced)

**Purpose**: Replace unreliable Yahoo Finance with multi-source hierarchical data validation

**Function Signature**: 
```python
async def get_enhanced_short_interest(symbol: str) -> ShortInterestDataV2
async def get_bulk_short_interest_validated(symbols: List[str]) -> Dict[str, ShortInterestDataV2]
async def validate_short_interest_accuracy(symbol: str, sources: List[str]) -> ValidationReport
```

**Enhanced Schema**:
```json
{
  "type": "object",
  "properties": {
    "symbol": {"type": "string"},
    "short_percent_float": {"type": "number", "minimum": 0, "maximum": 1},
    "short_ratio": {"type": "number", "minimum": 0},
    "shares_short": {"type": "integer", "minimum": 0},
    "float_shares": {"type": "integer", "minimum": 0},
    "settlement_date": {"type": "string", "format": "date-time"},
    "source_consensus": {
      "type": "object",
      "properties": {
        "primary_source": {"type": "string"},
        "validation_sources": {"type": "array", "items": {"type": "string"}},
        "consensus_confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "data_agreement": {"type": "number", "minimum": 0, "maximum": 1},
        "outlier_detection": {"type": "boolean"}
      }
    },
    "validation_metadata": {
      "type": "object",
      "properties": {
        "sources_checked": {"type": "integer"},
        "sources_agreeing": {"type": "integer"},
        "max_variance": {"type": "number"},
        "data_quality_score": {"type": "number", "minimum": 0, "maximum": 1}
      }
    }
  }
}
```

**Multi-Source Data Hierarchy**:
1. **FINRA Official** (Authoritative, Bi-monthly)
2. **Benzinga API** (Professional, Real-time)
3. **ORTEX** (Institutional Grade, $149/month)
4. **S3 Partners** (Leading Industry Source)
5. **Free Web Scraping** (Fintel, Yahoo, MarketWatch, NASDAQ)
6. **Intelligent Estimation** (Sector-based fallback)

**Retry Policy**:
```python
RETRY_CONFIG = {
    'max_attempts': 3,
    'base_delay': 1.0,  # seconds
    'max_delay': 10.0,
    'exponential_base': 2.0,
    'jitter': True,
    'retryable_errors': [
        'ConnectionTimeoutError',
        'RateLimitError',
        'TemporaryAPIError',
        'HTTPError_5xx'
    ],
    'non_retryable_errors': [
        'AuthenticationError',
        'InvalidSymbolError',
        'PermanentAPIError'
    ]
}
```

**Latency Budget**:
- P50: 500ms (single symbol)
- P95: 2000ms (single symbol)  
- P99: 5000ms (single symbol)
- Bulk (10 symbols): P95 < 8000ms

**Rate Limits**:
- Yahoo Finance: 1 request/second
- Benzinga API: 100 requests/minute
- ORTEX: 60 requests/minute
- FINRA: 10 requests/minute
- Web Scraping: 0.5 requests/second

## Data Enrichers

### ShortInterestValidationEnricher

**Purpose**: Cross-validate short interest data across multiple sources
**Dependencies**: All short interest data sources
**Processing Pipeline**:
1. **Parallel Fetch**: Query 3-5 sources simultaneously
2. **Consensus Analysis**: Calculate median, detect outliers
3. **Confidence Scoring**: Weight by source reliability and agreement
4. **Fallback Logic**: Progressive degradation when sources fail

**Error Handling Strategy**:
```python
class ValidationStrategy:
    def handle_source_failure(self, source: str, error: Exception):
        if isinstance(error, RateLimitError):
            return self.exponential_backoff(source)
        elif isinstance(error, DataParseError):
            return self.try_alternative_parser(source)
        elif isinstance(error, AuthenticationError):
            return self.disable_source_temporarily(source)
        else:
            return self.log_and_continue(source, error)
```

### DataQualityEnricher  

**Purpose**: Monitor and alert on data quality issues like the UP stock 100x discrepancy
**Processing Pipeline**:
1. **Variance Detection**: Flag when sources disagree by >50%
2. **Historical Comparison**: Compare against last-known-good values
3. **Outlier Analysis**: Statistical detection of anomalous readings
4. **Alert Generation**: Real-time notifications for data quality issues

## Signal Generators

### ShortSqueezePotentialSignal

**Calculation Method**:
```python
def calculate_squeeze_potential(data: ShortInterestDataV2) -> float:
    """Enhanced squeeze scoring with validated data"""
    # Base short interest score (validated data)
    si_score = min(data.short_percent_float / 0.30, 1.0)  # 30% = max score
    
    # Data quality adjustment
    quality_multiplier = data.validation_metadata.data_quality_score
    
    # Consensus confidence boost
    consensus_boost = data.source_consensus.consensus_confidence * 0.2
    
    return (si_score * quality_multiplier) + consensus_boost
```

**Input Requirements**:
- Validated short interest percentage
- Days to cover ratio
- Float size
- Recent volume patterns
- Data quality metrics

**Update Frequency**: Every 30 minutes during market hours

**Validation Rules**:
```python
VALIDATION_CHECKS = {
    'data_freshness': timedelta(days=14),  # FINRA reporting cycle
    'minimum_sources': 2,  # At least 2 sources must agree
    'maximum_variance': 0.50,  # 50% max disagreement between sources
    'confidence_threshold': 0.60,  # 60% minimum confidence
    'outlier_detection': True  # Flag statistical outliers
}
```

## Integration Specifications

### Enhanced Discovery Pipeline Integration

**Current Issue**: `/discovery/squeeze-candidates` returns null short_interest_data
**Solution**: Replace ShortInterestService with enhanced multi-source version

**API Updates**:
```python
# New endpoint for short interest validation
@router.get("/discovery/short-interest-validated")
async def get_validated_short_interest(symbols: str) -> Dict[str, ShortInterestDataV2]:
    symbol_list = symbols.split(',')
    service = await get_enhanced_short_interest_service()
    return await service.get_bulk_short_interest_validated(symbol_list)

# Enhanced existing endpoint
@router.get("/discovery/squeeze-candidates")
async def get_squeeze_candidates_enhanced() -> List[CandidateV2]:
    # Now includes validated short interest data
    candidates = await discovery_service.get_candidates_with_validated_si()
    return candidates
```

### Monitoring and Observability

**Data Quality Dashboard**:
```python
MONITORING_METRICS = {
    'source_availability': {
        'yahoo_finance': 'gauge',
        'benzinga_api': 'gauge', 
        'ortex_api': 'gauge',
        'finra_scraper': 'gauge'
    },
    'data_accuracy': {
        'variance_detected': 'counter',
        'outliers_flagged': 'counter',
        'consensus_failures': 'counter'
    },
    'performance': {
        'fetch_latency_p95': 'histogram',
        'validation_time': 'histogram',
        'cache_hit_rate': 'gauge'
    }
}
```

**Alert Thresholds**:
- Source availability < 80%: Warning
- Data variance > 100%: Critical (like UP stock issue)
- Consensus confidence < 50%: Warning
- Validation failures > 10/hour: Critical

## Testing Requirements

### Data Accuracy Validation Tests

**Test Case 1: UP Stock Validation**
```python
async def test_up_stock_short_interest_accuracy():
    """Verify UP stock shows correct ~9.34% short interest, not 0.09%"""
    service = get_enhanced_short_interest_service()
    data = await service.get_enhanced_short_interest("UP")
    
    # Should be around 9.34% based on external sources
    assert 0.08 <= data.short_percent_float <= 0.12, f"Expected ~9.34%, got {data.short_percent_float:.3%}"
    assert data.validation_metadata.data_quality_score > 0.7, "Quality score too low"
    assert data.source_consensus.sources_agreeing >= 2, "Need source consensus"
```

**Load Testing Parameters**:
- 100 symbols/minute sustained load
- 1000 symbols/minute burst capacity
- 99.5% availability during market hours
- <2s P95 response time under load

**Chaos Engineering**:
- Yahoo Finance API failure simulation
- Rate limiting enforcement testing
- Network partition recovery testing
- Data source intermittent failures

## Error Handling and Circuit Breakers

### Circuit Breaker Configuration

```python
CIRCUIT_BREAKER_CONFIG = {
    'failure_threshold': 5,  # Open after 5 failures
    'success_threshold': 3,  # Close after 3 successes  
    'timeout': 60,  # 60 seconds
    'recovery_timeout': 300,  # 5 minutes
    'half_open_max_calls': 2
}
```

### Fallback Mechanisms

**Degraded Operation Modes**:
1. **Single Source Mode**: When only 1 data source available
2. **Cache-Only Mode**: Serve stale data with warnings
3. **Estimation Mode**: Use sector-based intelligent estimates
4. **Alert Mode**: Flag all data as low-confidence

## Security and Compliance

**API Key Rotation**:
- Benzinga API: 30-day rotation cycle
- ORTEX: 90-day rotation cycle
- Rate limiting tokens: Daily refresh

**Data Encryption**:
- In-transit: TLS 1.3 for all API calls
- At-rest: AES-256 for cached short interest data
- Redis: AUTH + SSL/TLS encryption

**Audit Logging**:
```python
AUDIT_EVENTS = [
    'short_interest_fetch',
    'data_validation_failure',
    'source_consensus_disagreement',
    'cache_miss_critical_symbol',
    'api_rate_limit_exceeded'
]
```

## Implementation Timeline & Rollback Plan

### Phase 1 (Week 1-2): Enhanced Data Sources
- Implement Benzinga API integration
- Add FINRA official data scraping
- Create multi-source validation framework
- Deploy shadow testing alongside existing system

### Phase 2 (Week 3): Validation & Testing  
- Validate UP stock shows correct 9.34% short interest
- Test all high short interest symbols for accuracy
- Performance testing under load
- A/B test with 25% of discovery traffic

### Phase 3 (Week 4): Full Deployment
- Switch 100% of short interest fetching to enhanced service
- Monitor for 100x discrepancy issues
- Real-time alerting for data quality problems
- Sunset old Yahoo-only implementation

### Emergency Rollback Procedure
```bash
# If enhanced service fails, immediate rollback
redis-cli RENAME amc:short_interest:enhanced amc:short_interest:backup
redis-cli RENAME amc:short_interest:legacy amc:short_interest:enhanced
export SHORT_INTEREST_ENHANCED=false
systemctl restart amc-discovery-service
# Verify legacy service working: should return to 0.09% for UP (known issue)
```

## Success Metrics

**Data Accuracy Targets**:
- Eliminate 100x discrepancies (0 occurrences/month)
- <10% variance between consensus sources
- >90% data quality score for top 100 symbols
- 99.5% short interest data availability during market hours

**Performance SLAs**:
- Single symbol: P95 < 2000ms
- Bulk 10 symbols: P95 < 8000ms  
- Cache hit rate: >80%
- Source availability: >95% each

**Business Impact**:
- Increase squeeze detection accuracy by 40%+
- Reduce false negative signals (like missing UP squeeze potential)
- Enable confident short interest thresholds for discovery pipeline
- Provide competitive advantage through data quality

This enhanced short interest architecture addresses the critical 100x data accuracy issue while building a robust, multi-source validation system that ensures AMC-TRADER has the most accurate short interest data available for squeeze detection and trading decisions.