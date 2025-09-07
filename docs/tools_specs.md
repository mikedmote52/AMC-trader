# AMC-TRADER Tools Specification

**Version**: 2.0  
**Date**: 2025-09-06  
**Focus**: Comprehensive provider architecture and tool integration contracts

## Overview

This document defines the complete technical specifications for all data providers, APIs, and enrichment tools in the AMC-TRADER discovery system. The architecture supports both hybrid_v1 and legacy_v0 strategies with robust error handling, anti-fabrication policies, and session-aware processing.

## Core Trading APIs

### FINRA Short Interest Provider

**Purpose**: Official short interest and daily short volume data from FINRA regulatory sources

**Endpoint**: `https://api.finra.org/data/group/otcmarket/name`  
**Authentication**: None (public API)  

**Function Signatures**:
```python
class FINRAShortProvider:
    async def get_short_interest(self, symbol: str) -> Dict[str, Any]:
        """
        Get latest bi-monthly short interest data
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            
        Returns:
            {
                'short_interest_shares': int,
                'shares_outstanding': int, 
                'short_interest_pct': float,
                'report_date': str (ISO),
                'asof': str (ISO),
                'source': 'finra',
                'staleness_policy_pass': bool,
                'latency_sec': float,
                'confidence': float  # Derived from data age and completeness
            }
        """
    
    async def get_daily_short_volume(self, symbol: str) -> Dict[str, Any]:
        """
        Get latest daily short volume ratio data
        
        Args:
            symbol: Stock symbol
            
        Returns:
            {
                'short_volume': int,
                'total_volume': int,
                'svr': float,  # Short volume ratio (0-100%)
                'trade_date': str (ISO),
                'asof': str (ISO), 
                'source': 'finra',
                'staleness_policy_pass': bool,
                'latency_sec': float
            }
        """
    
    def calculate_dtcr(self, short_interest_shares: int, adv30: float) -> float:
        """Calculate Days to Cover Ratio"""
```

**Schema**:
```json
{
  "type": "object",
  "properties": {
    "short_interest_pct": {"type": "number", "minimum": 0, "maximum": 100},
    "shares_outstanding": {"type": "integer", "minimum": 0},
    "staleness_policy_pass": {"type": "boolean"},
    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    "latency_sec": {"type": "number", "minimum": 0}
  },
  "required": ["short_interest_pct", "staleness_policy_pass", "confidence"]
}
```

**Retry Policy**:
- Rate limit: 60 calls/minute via token bucket
- Backoff: Exponential with 1s base, 2x multiplier, max 16s
- Circuit breaker: 3 failures → 5 minute timeout
- Max retries: 3 attempts for 429/500 errors

**Latency Budget**: P95 ≤ 2000ms, P99 ≤ 5000ms  
**Rate Limits**: 60 requests/minute with burst tolerance  
**Staleness Policy**: Short interest ≤20 days, daily volume ≤36 hours

### Alpha Vantage Options Provider

**Purpose**: ATM options data with implied volatility analysis

**Endpoint**: `https://www.alphavantage.co/query`  
**Authentication**: API Key via ALPHAVANTAGE_API_KEY environment variable

**Function Signatures**:
```python
class AlphaVantageOptionsProvider:
    async def get_atm_options_data(self, symbol: str, stock_price: float) -> Dict[str, Any]:
        """
        Get ATM options data with IV percentile calculation
        
        Args:
            symbol: Stock symbol
            stock_price: Current stock price for ATM strike identification
            
        Returns:
            {
                'atm_call_mid': float,
                'atm_put_mid': float,
                'atm_iv': float,  # Implied volatility from Black-Scholes
                'iv_percentile': float,  # 252-day IV percentile
                'expiry_date': str (ISO),
                'strike': float,
                'asof': str (ISO),
                'source': 'alphavantage',
                'staleness_policy_pass': bool,
                'latency_sec': float,
                'confidence': float,  # Based on bid-ask spreads and age
                'data_age_hours': float
            }
        """
```

**Schema**:
```json
{
  "type": "object", 
  "properties": {
    "atm_iv": {"type": "number", "minimum": 0.01, "maximum": 5.0},
    "iv_percentile": {"type": "number", "minimum": 0, "maximum": 100},
    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    "data_age_hours": {"type": "number", "minimum": 0}
  },
  "required": ["atm_iv", "iv_percentile", "confidence"]
}
```

**Retry Policy**:
- Rate limit: 5 calls/minute (strict enforcement)
- Backoff: Fixed 12-second delay between requests
- Circuit breaker: 2 failures → 3 minute timeout
- Max retries: 2 attempts (due to strict rate limits)

**Latency Budget**: P95 ≤ 5000ms, P99 ≤ 8000ms  
**Rate Limits**: 5 requests/minute, no burst tolerance  
**Staleness Policy**: Options data ≤24 hours

### Polygon Live Market Data

**Purpose**: Real-time market data integration (already implemented)

**Endpoint**: Via existing Polygon WebSocket and REST integration  
**Authentication**: Polygon API key

**Function Signatures**:
```python
class PolygonProvider:
    async def get_quote_data(self, symbol: str) -> Dict[str, Any]:
        """Real-time bid/ask and last price data"""
        
    async def get_bar_data(self, symbol: str, timespan: str = "minute") -> Dict[str, Any]:
        """OHLCV bar data with volume analysis"""
        
    async def get_technical_indicators(self, symbol: str) -> Dict[str, Any]:
        """VWAP, ATR, EMA calculations"""
```

**Latency Budget**: P95 ≤ 500ms, P99 ≤ 1000ms  
**Rate Limits**: 1000 requests/minute with burst handling

## Data Enrichers

### Borrow Stress Proxy Calculator

**Purpose**: Statistical proxy calculation for borrow cost estimation

**Dependencies**: FINRA short data, volume metrics, regulatory flags

**Function Signatures**:
```python
class BorrowProxyProvider:
    def calculate_borrow_stress(
        self, 
        svr: float,
        dtcr: float,
        ftd_flag: bool = False,
        threshold_security: bool = False,
        short_interest_pct: float = 0.0
    ) -> Dict[str, Any]:
        """
        Calculate composite borrow stress score using statistical proxies
        
        Args:
            svr: Short Volume Ratio (0-100%)
            dtcr: Days to Cover Ratio 
            ftd_flag: Fails to Deliver regulatory flag
            threshold_security: Threshold security designation
            short_interest_pct: Short interest percentage
            
        Returns:
            {
                'borrow_stress_score': float,  # 0-100 composite score
                'confidence': float,           # 0-1 confidence in estimate
                'stress_level': str,           # 'LOW', 'MODERATE', 'HIGH', 'EXTREME'
                'contributing_factors': List[str],
                'components': Dict[str, float],  # Individual component scores
                'methodology': str,
                'staleness_policy_pass': bool,
                'latency_sec': float
            }
        """
```

**Processing Pipeline**:
1. **SVR Analysis** (30% weight): Score based on short volume thresholds
2. **DTCR Analysis** (25% weight): Days to cover ratio evaluation  
3. **Short Interest** (20% weight): Percentage-based scoring
4. **Regulatory Flags** (25% weight): FTD and threshold security flags

**Error Handling**: Always returns result (proxy calculation), confidence indicates reliability

### Volume Momentum Enricher

**Purpose**: Multi-dimensional volume and momentum pattern analysis

**Dependencies**: Polygon market data, historical volume averages

**Function Signatures**:
```python
class VolumeMomentumDetector:
    def analyze(self, symbol: str, enriched_data: Dict) -> Dict[str, Any]:
        """
        Analyze volume spikes, VWAP reclaim, and momentum patterns
        
        Args:
            symbol: Stock symbol
            enriched_data: Market data including price, volume, VWAP, ATR
            
        Returns:
            {
                'score': float,              # 0-1 composite momentum score
                'confidence': float,         # 0-1 data quality confidence
                'signals': List[str],        # Detected pattern signals
                'metrics': Dict,             # Raw calculation metrics
                'pattern_strength': str,     # 'MINIMAL', 'WEAK', 'MODERATE', 'STRONG', 'EXPLOSIVE'
                'components': {
                    'relvol_score': float,   # Relative volume component
                    'vwap_score': float,     # VWAP reclaim component
                    'uptrend_score': float,  # Uptrend momentum component  
                    'atr_score': float       # ATR expansion component
                }
            }
        """
```

**Processing Pipeline**:
1. **RelVol Analysis** (40% weight): 30-day and 5-day relative volume comparison
2. **VWAP Reclaim** (30% weight): Price position relative to VWAP with proximity scoring
3. **Uptrend Momentum** (20% weight): Consecutive up days and 5-day price change
4. **ATR Expansion** (10% weight): Volatility breakout detection

**Validation Rules**:
- RelVol data must be >0 for valid scoring
- VWAP must be positive for reclaim analysis
- ATR percentage must be >0 for volatility analysis

### Squeeze Pattern Detector

**Purpose**: Multi-factor squeeze opportunity identification using enhanced VIGL pattern matching

**Dependencies**: Short interest, float data, volume analysis, borrow stress

**Function Signatures**:
```python
class SqueezeDetector:
    def detect_vigl_pattern(self, symbol: str, squeeze_data: Dict) -> SqueezeResult:
        """
        Detect VIGL-style squeeze patterns with confidence weighting
        
        Args:
            symbol: Stock symbol
            squeeze_data: {
                'price': float,
                'volume': float,
                'avg_volume_30d': float,
                'short_interest': float,  # Percentage
                'float': int,            # Shares outstanding
                'borrow_rate': float,    # If available
                'market_cap': float
            }
            
        Returns:
            SqueezeResult with squeeze_score, pattern_match, confidence, thesis
        """
```

**Validation Rules**:
- Never fabricate missing data (returns confidence adjustment instead)
- Price range: $1.00 - $15.00 (VIGL-compatible range)
- Volume spike: ≥3x average required for consideration
- Float size: ≤75M shares (small float path) OR ≥150M shares (large float path)

## Signal Generators

### Catalyst News Detector

**Purpose**: News sentiment and social media momentum analysis

**Calculation Method**: Multi-source aggregation with credibility weighting

**Function Signatures**:
```python
class CatalystNewsDetector:
    async def analyze(self, symbol: str, enriched_data: Dict, providers: Dict) -> Dict[str, Any]:
        """
        Analyze news sentiment and social momentum
        
        Args:
            symbol: Stock symbol
            enriched_data: Market context data
            providers: Available news/social data sources
            
        Returns:
            {
                'score': float,           # 0-1 catalyst strength score
                'confidence': float,      # 0-1 data quality confidence
                'signals': List[str],     # Detected catalyst signals
                'components': {
                    'news_sentiment': float,    # Recent news sentiment (40% weight)
                    'social_momentum': float,   # Social media activity (30% weight)
                    'event_proximity': float,   # Upcoming catalysts (20% weight)
                    'unusual_activity': float   # Volume/options anomalies (10% weight)
                }
            }
        """
```

**Input Requirements**:
- News API access (when available) with source credibility scoring
- Social media sentiment feeds with activity ranking
- Event calendar data (earnings, FDA approvals, etc.)
- Volume and options anomaly detection

**Update Frequency**: Every 15 minutes during market hours, hourly after hours

### Options Flow Detector

**Purpose**: Gamma squeeze potential and unusual options activity detection

**Calculation Method**: Black-Scholes derived gamma exposure with flow analysis

**Function Signatures**:
```python
class OptionsFlowDetector:
    async def analyze(self, symbol: str, enriched_data: Dict, providers: Dict) -> Dict[str, Any]:
        """
        Analyze options flow patterns and gamma potential
        
        Returns:
            {
                'score': float,           # 0-1 options opportunity score
                'confidence': float,      # 0-1 data reliability
                'signals': List[str],     # Options pattern signals
                'components': {
                    'gamma_potential': float,    # Gamma squeeze potential (40% weight)
                    'call_put_flow': float,     # Call/put ratio analysis (30% weight)
                    'iv_expansion': float,      # IV percentile positioning (20% weight)
                    'unusual_activity': float   # Options volume anomalies (10% weight)
                }
            }
        """
```

**Input Requirements**:
- ATM options chain data (calls and puts)
- Historical IV data for percentile calculation
- Options volume vs historical averages
- Call/put ratio trending analysis

### Technical Indicators Detector

**Purpose**: EMA crossovers, RSI positioning, and momentum confirmation

**Calculation Method**: Traditional technical analysis with squeeze-optimized parameters

**Function Signatures**:
```python
class TechnicalDetector:
    def analyze(self, symbol: str, enriched_data: Dict) -> Dict[str, Any]:
        """
        Technical analysis for momentum confirmation
        
        Returns:
            {
                'score': float,           # 0-1 technical strength score
                'confidence': float,      # 0-1 data quality confidence  
                'signals': List[str],     # Technical pattern signals
                'components': {
                    'ema_momentum': float,      # 9/20 EMA cross and slope (40% weight)
                    'rsi_positioning': float,   # RSI 60-70 band analysis (30% weight)
                    'vwap_reclaim': float,     # VWAP reclaim strength (20% weight)
                    'breakout_quality': float   # Support/resistance breaks (10% weight)
                }
            }
        """
```

**Input Requirements**:
- 50+ periods of OHLCV data for EMA calculation
- Price and volume for VWAP calculation  
- 14-period RSI calculation
- Support/resistance level identification

**Update Frequency**: Real-time during market hours with 1-minute bar updates

## Integration Specifications

### Provider Management System

**Rate Limiting Implementation**:
```python
class ProviderManager:
    def __init__(self):
        self.rate_limits = {
            'finra_short': TokenBucket(capacity=60, refill_rate=1.0),      # 60/minute
            'alpha_vantage_options': TokenBucket(capacity=5, refill_rate=0.083),  # 5/minute  
            'polygon_live': TokenBucket(capacity=100, refill_rate=5.0)     # 300/minute
        }
        
        self.circuit_breakers = {
            'finra_short': CircuitBreaker(
                failure_threshold=3,
                timeout_seconds=300,
                success_threshold=2
            ),
            'alpha_vantage_options': CircuitBreaker(
                failure_threshold=2, 
                timeout_seconds=180,
                success_threshold=1
            ),
            'polygon_live': CircuitBreaker(
                failure_threshold=5,
                timeout_seconds=120,
                success_threshold=3
            )
        }
```

**Retry Policies and Backoff Strategies**:

**FINRA Provider**:
- Base delay: 1000ms
- Multiplier: 2.0x
- Max delay: 16000ms
- Jitter: ±25% random variation
- Max attempts: 3
- Retryable errors: 429, 500, 502, 503, 504
- Non-retryable: 400, 401, 403, 404

**Alpha Vantage Provider**:
- Base delay: 12000ms (fixed due to strict rate limits)
- No exponential backoff (respect 5/minute limit)
- Max attempts: 2
- Retryable errors: 429, 500, 502, 503  
- Circuit breaker: 2 consecutive failures = 3-minute timeout

**Polygon Provider**:
- Base delay: 500ms
- Multiplier: 1.5x
- Max delay: 5000ms
- Jitter: ±20% random variation
- Max attempts: 4
- High success rate expected (premium service)

**Error Classification and Recovery**:
```python
class ErrorHandler:
    RETRYABLE_ERRORS = {
        'rate_limited': {'backoff': 'exponential', 'max_attempts': 3},
        'server_error': {'backoff': 'exponential', 'max_attempts': 3},
        'timeout': {'backoff': 'linear', 'max_attempts': 2},
        'network_error': {'backoff': 'exponential', 'max_attempts': 4}
    }
    
    NON_RETRYABLE_ERRORS = {
        'authentication': {'action': 'alert_admin'},
        'not_found': {'action': 'skip_symbol'},
        'bad_request': {'action': 'log_and_skip'},
        'forbidden': {'action': 'circuit_break'}
    }
```

### Service Level Objectives (SLOs)

**FINRA Short Interest Provider**:
- **Latency**: P50 ≤ 800ms, P95 ≤ 2000ms, P99 ≤ 5000ms
- **Availability**: ≥95% success rate during market hours
- **Data Quality**: Short interest confidence ≥0.90 for data ≤20 days old
- **Staleness**: Short interest ≤20 days, daily volume ≤36 hours

**Alpha Vantage Options Provider**:
- **Latency**: P50 ≤ 3000ms, P95 ≤ 5000ms, P99 ≤ 8000ms  
- **Availability**: ≥90% success rate (accounting for strict rate limits)
- **Data Quality**: IV confidence ≥0.70 for spreads <10%
- **Staleness**: Options data ≤24 hours

**Polygon Market Data Provider**:
- **Latency**: P50 ≤ 200ms, P95 ≤ 500ms, P99 ≤ 1000ms
- **Availability**: ≥99% success rate (premium real-time service)
- **Data Quality**: Quote confidence ≥0.95 for live market hours
- **Staleness**: Real-time data ≤10 seconds, bars ≤2 minutes

**Borrow Proxy Calculator**:
- **Latency**: P50 ≤ 50ms, P95 ≤ 100ms, P99 ≤ 200ms (local calculation)
- **Availability**: ≥99.9% (no external dependencies)
- **Data Quality**: Confidence ≤0.80 (inherent proxy uncertainty)
- **Staleness**: Always current (calculated on demand)

### Caching and Storage Contracts

**Redis Storage Patterns**:
```python
class CacheManager:
    def __init__(self):
        self.key_patterns = {
            'short_interest': 'amc:si:{symbol}',           # TTL: 12 hours
            'options_iv': 'amc:options:{symbol}',          # TTL: 1 hour  
            'market_data': 'amc:quote:{symbol}',           # TTL: 30 seconds
            'squeeze_score': 'amc:squeeze:{symbol}',       # TTL: 5 minutes
            'discovery_results': 'amc:discovery:v2:contenders.latest:{strategy}',  # TTL: 10 minutes
            'provider_health': 'amc:health:{provider}',    # TTL: 1 minute
        }
        
        self.ttl_policies = {
            'short_interest': 43200,      # 12 hours (bi-monthly data)
            'daily_volume': 129600,       # 36 hours (daily data)
            'options_data': 3600,         # 1 hour (options volatility)
            'market_quotes': 30,          # 30 seconds (real-time)
            'technical_indicators': 300,   # 5 minutes (calculated data)
            'discovery_contenders': 600,   # 10 minutes (discovery results)
            'provider_status': 60         # 1 minute (health checks)
        }
```

**Cache Warming Strategies**:
- **Universe Pre-loading**: Warm cache for 500+ symbol universe during off-hours
- **Provider Health**: Continuously monitor and cache provider status
- **Technical Indicators**: Pre-calculate for discovery universe every 5 minutes
- **Fallback Chain**: Primary → Cache → Skip (never fabricate)

**Database Storage Requirements**:
```sql
-- Provider performance tracking
CREATE TABLE provider_metrics (
    provider_name VARCHAR(50),
    symbol VARCHAR(10), 
    request_timestamp TIMESTAMP,
    latency_ms INTEGER,
    success BOOLEAN,
    error_type VARCHAR(50),
    confidence_score DECIMAL(4,3)
);

-- Audit trail for compliance
CREATE TABLE discovery_audit (
    run_id UUID,
    timestamp TIMESTAMP,
    strategy VARCHAR(20),
    candidates_found INTEGER,
    total_symbols_scanned INTEGER,
    configuration_hash VARCHAR(64),
    execution_time_ms INTEGER
);
```

### Error Handling and Recovery

**Error Classifications**:

**Transient Errors** (Retry with backoff):
- HTTP 429 (Rate Limited): Respect retry-after header
- HTTP 500-504 (Server Errors): Exponential backoff  
- Network timeouts: Linear backoff with jitter
- Connection errors: Exponential backoff

**Rate Limiting Errors** (Special handling):
- FINRA: 1-second fixed backoff, resume normal operations
- Alpha Vantage: 12-second fixed backoff, strict queue management
- Polygon: Brief exponential backoff, high tolerance

**Authentication Errors** (Admin alerts):
- Invalid API keys: Immediate admin notification
- Expired credentials: Circuit breaker activation
- Permission denied: Log and skip requests

**Data Quality Errors** (Confidence reduction):
- Stale data: Reduce confidence based on age
- Missing fields: Skip symbol or use partial data with confidence penalty
- Invalid ranges: Reject data point, continue with others

**Recovery Procedures**:
```python
class RecoveryManager:
    async def handle_provider_failure(self, provider: str, error: Exception):
        """Coordinated recovery from provider failures"""
        
        if isinstance(error, RateLimitError):
            await self._backoff_strategy(provider)
        elif isinstance(error, AuthenticationError):
            await self._alert_admin(provider, error)
            self._activate_circuit_breaker(provider)
        elif isinstance(error, DataQualityError):
            await self._reduce_confidence(provider, error.symbol)
        else:
            await self._exponential_backoff(provider)
    
    async def _graceful_degradation(self, failed_providers: List[str]):
        """Maintain discovery operations with reduced provider set"""
        
        remaining_providers = set(self.all_providers) - set(failed_providers)
        
        if 'polygon_live' in remaining_providers:
            # Core market data available - continue with reduced scoring
            return {'mode': 'reduced_scoring', 'confidence_penalty': 0.2}
        elif len(remaining_providers) >= 2:
            # Multiple sources available - continue with higher uncertainty  
            return {'mode': 'high_uncertainty', 'confidence_penalty': 0.4}
        else:
            # Insufficient data sources - suspend discovery
            return {'mode': 'suspended', 'reason': 'insufficient_providers'}
```

### Monitoring and Observability

**Metrics Collection**:
```python
class MetricsCollector:
    def __init__(self):
        self.metrics = {
            # Provider performance
            'provider_latency_histogram': Histogram('provider_request_latency_seconds'),
            'provider_error_counter': Counter('provider_errors_total'), 
            'provider_success_rate': Gauge('provider_success_rate'),
            
            # Data quality
            'confidence_distribution': Histogram('data_confidence_score'),
            'staleness_gauge': Gauge('data_age_seconds'),
            'missing_data_counter': Counter('missing_data_points_total'),
            
            # Discovery pipeline  
            'discovery_execution_time': Histogram('discovery_execution_seconds'),
            'candidates_found': Gauge('discovery_candidates_total'),
            'gate_rejection_counter': Counter('gate_rejections_total'),
            
            # System health
            'circuit_breaker_state': Gauge('circuit_breaker_open'),
            'cache_hit_rate': Gauge('cache_hit_ratio'),
            'active_connections': Gauge('provider_connections_active')
        }
```

**Health Check Endpoints**:
```python
@router.get("/health/providers")
async def provider_health_check():
    """Comprehensive provider connectivity and performance check"""
    
    health_status = {}
    
    for provider_name in ['finra_short', 'alpha_vantage_options', 'polygon_live']:
        status = await check_provider_health(provider_name)
        health_status[provider_name] = {
            'status': status.state,  # 'healthy', 'degraded', 'down'
            'last_success': status.last_success_time,
            'success_rate_1h': status.success_rate_1hour,
            'avg_latency_ms': status.avg_latency_ms,
            'circuit_breaker_open': status.circuit_breaker_open,
            'rate_limit_remaining': status.rate_limit_remaining
        }
    
    overall_health = determine_overall_health(health_status)
    
    return {
        'overall_status': overall_health,
        'providers': health_status,
        'discovery_capability': assess_discovery_capability(health_status),
        'timestamp': datetime.utcnow().isoformat()
    }
```

**Alerting Thresholds**:
- Provider success rate <90% → Warning alert
- Provider success rate <75% → Critical alert  
- Discovery latency P95 >30 seconds → Performance alert
- Data confidence average <70% → Data quality alert
- Circuit breaker open >5 minutes → Infrastructure alert

### Testing and Validation Contracts

**Mock Provider Interfaces**:
```python
class MockFINRAProvider:
    """Test implementation for FINRA provider with controlled data"""
    
    def __init__(self, test_scenarios: Dict):
        self.scenarios = test_scenarios  # 'success', 'rate_limit', 'stale_data', etc.
    
    async def get_short_interest(self, symbol: str) -> Dict:
        scenario = self.scenarios.get(symbol, 'success')
        
        if scenario == 'rate_limit':
            await asyncio.sleep(0.1)  # Simulate delay
            raise RateLimitError("Mock rate limit exceeded")
        elif scenario == 'stale_data':
            return self._generate_stale_data(symbol)
        else:
            return self._generate_fresh_data(symbol)
```

**Integration Test Scenarios**:
1. **Happy Path**: All providers healthy, fresh data, normal discovery
2. **Rate Limiting**: Simulate API rate limits, verify backoff behavior  
3. **Provider Failures**: Test circuit breaker activation and recovery
4. **Stale Data**: Verify confidence reduction and staleness policies
5. **Network Issues**: Test timeout handling and retry logic
6. **Data Quality**: Test with missing fields, invalid ranges, corrupted data

**Load Testing Parameters**:
- **Discovery Load**: 500 symbols × 15-minute intervals during market hours
- **Provider Load**: FINRA 60/min, Alpha Vantage 5/min, Polygon 300/min
- **Concurrent Discovery**: 3 strategies running simultaneously (legacy_v0, hybrid_v1, test)
- **Cache Performance**: 10,000 concurrent symbol lookups
- **Failover Testing**: Provider failure during peak load conditions

**Quality Assurance Validation**:
```python
class QualityValidator:
    def validate_discovery_results(self, results: List[Dict]) -> Dict:
        """Comprehensive validation of discovery output"""
        
        validation = {
            'total_candidates': len(results),
            'score_distribution': self._analyze_score_distribution(results),
            'data_quality_check': self._check_data_integrity(results), 
            'anti_fabrication_audit': self._audit_for_fake_data(results),
            'confidence_validation': self._validate_confidence_scores(results),
            'duplicate_detection': self._check_for_duplicates(results)
        }
        
        # Flag suspicious patterns
        if validation['anti_fabrication_audit']['fake_patterns'] > 0:
            validation['alert'] = 'FAKE_DATA_DETECTED'
        
        return validation
```

### Security and Compliance Specifications

**API Key Management**:
```python
class APIKeyManager:
    def __init__(self):
        self.key_rotation_schedule = {
            'alpha_vantage': timedelta(days=90),  # Quarterly rotation
            'polygon': timedelta(days=180),       # Semi-annual rotation
        }
        
    async def rotate_api_key(self, provider: str):
        """Secure API key rotation with zero downtime"""
        
        # Generate new key through provider portal (manual step)
        new_key = await self._fetch_new_key(provider)
        
        # Test new key functionality
        test_success = await self._test_key_functionality(provider, new_key)
        
        if test_success:
            # Update environment variable
            old_key = os.environ.get(f'{provider.upper()}_API_KEY')
            os.environ[f'{provider.upper()}_API_KEY'] = new_key
            
            # Verify production functionality
            prod_test = await self._test_production_calls(provider)
            
            if prod_test:
                # Archive old key securely
                await self._archive_old_key(provider, old_key)
                await self._log_rotation_success(provider)
            else:
                # Rollback on failure
                os.environ[f'{provider.upper()}_API_KEY'] = old_key
                raise KeyRotationError(f"Production test failed for {provider}")
```

**Data Privacy and Retention**:
- **PII Handling**: No personal data in market feeds (stock symbols only)
- **Data Retention**: 
  - Raw provider responses: 30 days (debugging)
  - Aggregated metrics: 1 year (performance analysis)
  - Audit trails: 7 years (compliance)
- **Data Purging**: Automated cleanup of expired data
- **Access Logging**: All API calls logged with requester identification

**Audit Trail Requirements**:
```sql
-- Comprehensive audit trail for compliance
CREATE TABLE api_audit_log (
    request_id UUID PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    provider VARCHAR(50) NOT NULL,
    endpoint VARCHAR(200),
    symbol VARCHAR(10),
    response_code INTEGER,
    latency_ms INTEGER,
    user_agent TEXT,
    ip_address INET,
    api_key_hash VARCHAR(64), -- Hashed, not plaintext
    data_confidence DECIMAL(4,3),
    cache_hit BOOLEAN
);

-- Provider performance audit
CREATE TABLE provider_audit (
    audit_id UUID PRIMARY KEY,
    date DATE NOT NULL,
    provider VARCHAR(50) NOT NULL,
    total_requests INTEGER,
    successful_requests INTEGER,
    avg_latency_ms INTEGER,
    error_breakdown JSONB,
    sla_compliance BOOLEAN
);
```

**Regulatory Compliance**:
- **Market Data Usage**: Compliance with exchange data policies
- **Rate Limiting**: Respect provider terms of service  
- **Data Distribution**: Internal use only, no redistribution
- **Incident Reporting**: Mandatory reporting for data breaches
- **Change Management**: Version controlled configuration with approval workflow

## Performance Requirements and Monitoring

**End-to-End Discovery SLAs**:
- **Total Discovery Time**: <30 seconds for 500 symbol universe (P90)
- **Individual Symbol Processing**: <100ms average per symbol
- **Data Freshness**: ≥80% of data within staleness thresholds
- **System Availability**: 99% uptime during market hours (9:30 AM - 4:00 PM ET)

**Resource Utilization Constraints**:
- **Memory**: <2GB for discovery process
- **CPU**: <80% utilization during peak discovery
- **Network**: <100 concurrent provider connections
- **Redis**: <500MB for all cached data

**Scaling Parameters**:
- **Symbol Universe**: Supports up to 2,000 symbols 
- **Discovery Frequency**: 15-minute cycles during market hours
- **Provider Connections**: 50 FINRA, 5 Alpha Vantage, 100 Polygon
- **Concurrent Users**: 20 simultaneous API users

**Emergency Procedures**:
```python
class EmergencyManager:
    async def activate_degraded_mode(self, failure_reason: str):
        """Emergency fallback to ensure continued operations"""
        
        if failure_reason == 'provider_cascade_failure':
            # Use cached data with extended TTL
            await self._extend_cache_ttl(multiplier=3)
            await self._reduce_discovery_frequency(from_15min_to_30min=True)
            
        elif failure_reason == 'discovery_latency_breach':
            # Reduce universe size and complexity
            await self._limit_universe_size(max_symbols=200)  
            await self._disable_complex_detectors(['catalyst_news', 'options_flow'])
            
        elif failure_reason == 'data_quality_degradation':
            # Increase confidence thresholds
            await self._raise_confidence_thresholds(minimum=0.8)
            await self._enable_manual_validation_mode()
        
        await self._notify_operations_team(failure_reason)
```

This comprehensive tools specification provides the foundation for a robust, scalable, and reliable AMC-TRADER discovery system that can identify explosive opportunities while maintaining strict data integrity and operational reliability standards.

## Implementation Priority

**Phase 1 (Immediate)**: Core provider stability and error handling
**Phase 2 (Week 1-2)**: Complete detector implementations with validation  
**Phase 3 (Week 3-4)**: Advanced monitoring and emergency procedures
**Phase 4 (Week 5-6)**: Performance optimization and scaling validation

Each specification includes backward compatibility considerations and can be implemented incrementally without disrupting existing discovery operations.