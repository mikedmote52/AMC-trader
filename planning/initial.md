# AMC-TRADER Squeeze Detection Enhancement Plan

**Version**: 2.0  
**Date**: 2025-09-06  
**Focus**: Comprehensive detector architecture and advanced gating system  

## Executive Summary

This plan details the comprehensive enhancement of AMC-TRADER's squeeze detection system, moving from the current basic implementation to a sophisticated multi-detector architecture with advanced gating, confidence weighting, and real-time calibration capabilities. The system will integrate multiple free-data providers while maintaining strict data quality standards and providing regime-aware scoring for optimal market conditions adaptation.

## Current System Analysis

### Existing Architecture
- **Discovery Pipeline**: FastAPI backend with Redis caching, 15-minute execution cycles
- **Current Detectors**: `volume_momentum.py` and `squeeze.py` implemented as stubs
- **Scoring Strategy**: Hybrid V1 with configurable weights (35% volume_momentum, 25% squeeze, 20% catalyst, 10% options, 10% technical)
- **Data Sources**: Polygon Live (high confidence), FINRA Short Interest, Alpha Vantage Options
- **Configuration**: Active calibration system in `/calibration/active.json` with preset switching

### Current Limitations
1. **Incomplete Detector Suite**: Missing catalyst, options, technical, and vigl_pattern detectors
2. **Basic Gating**: No hard/soft gate distinction or confidence reduction mechanisms
3. **Session Agnostic**: No market session awareness (premarket, regular, afterhours)
4. **Limited Provider Integration**: Manual provider switching without circuit breakers
5. **No Experimental Framework**: Lacks A/B testing and shadow testing capabilities

## Architecture Enhancement Plan

### 1. Complete Detector Architecture

#### A. Catalyst News Detector (`catalyst_news.py`)

**Purpose**: Detect news sentiment, social media rank, and event-driven catalysts

**Data Sources**:
- News APIs (when available) with confidence weighting
- Social media sentiment scores
- Event calendars (earnings, FDA approvals, etc.)

**Core Components**:
```python
class CatalystDetector:
    def __init__(self, config=None):
        self.weights = {
            'news_sentiment': 0.4,     # Recent news sentiment score
            'social_momentum': 0.3,    # Social media activity rank  
            'event_proximity': 0.2,    # Upcoming catalyst events
            'unusual_activity': 0.1    # Unusual volume/options activity
        }
    
    async def analyze(self, symbol: str, enriched_data: Dict, providers: Dict) -> Dict:
        # News sentiment analysis (0-1 score)
        # Social media rank detection
        # Event calendar proximity scoring
        # Unusual activity detection
        pass
```

**Scoring Logic**:
- **News Sentiment**: 0-1 based on recent article tone, volume, and source credibility
- **Social Media Momentum**: Rank percentile of mention frequency and sentiment
- **Event Proximity**: Distance-weighted scoring for upcoming catalysts (earnings, approvals)
- **Unusual Activity**: Volume/options anomaly detection vs historical patterns

**Confidence Factors**:
- News source credibility (Reuters=0.9, Twitter=0.4)
- Data freshness penalties (-10% per hour beyond 24hr threshold)
- Source diversity bonus (+15% for multiple confirming sources)

#### B. Options Flow Detector (`options_flow.py`)

**Purpose**: Analyze options flow, gamma walls, and unusual activity patterns

**Data Integration**:
- Alpha Vantage Options API (ATM IV, call/put ratios)
- Derived gamma calculation from options chain
- Unusual options activity detection

**Core Components**:
```python
class OptionsFlowDetector:
    def __init__(self, config=None):
        self.weights = {
            'gamma_potential': 0.4,    # Gamma squeeze potential
            'call_put_flow': 0.3,      # Call/put ratio and flow
            'iv_expansion': 0.2,       # IV percentile and expansion
            'unusual_activity': 0.1    # Options volume anomalies
        }
        
    async def analyze(self, symbol: str, enriched_data: Dict, providers: Dict) -> Dict:
        # Calculate gamma exposure levels
        # Analyze call/put flow patterns  
        # IV expansion potential scoring
        # Detect unusual options activity
        pass
```

**Scoring Components**:
- **Gamma Potential**: Distance to nearest gamma wall, dealer positioning
- **Call/Put Flow**: Ratio analysis with volume weighting (>2.0 ratio = bullish signal)
- **IV Expansion**: Low IV percentile (<30%) with catalyst proximity
- **Unusual Activity**: Options volume vs 30-day average (>3x = strong signal)

#### C. Technical Indicators Detector (`technicals.py`)

**Purpose**: EMA crosses, RSI bands, support/resistance, momentum oscillators

**Technical Indicators**:
- EMA 9/20 crossover detection
- RSI 60-70 band analysis
- VWAP reclaim confirmation
- Support/resistance level testing

**Core Components**:
```python
class TechnicalDetector:
    def __init__(self, config=None):
        self.weights = {
            'ema_momentum': 0.4,       # 9/20 EMA cross and slope
            'rsi_positioning': 0.3,    # RSI band analysis
            'vwap_reclaim': 0.2,      # VWAP reclaim strength
            'breakout_quality': 0.1    # Support/resistance breaks
        }
    
    def analyze(self, symbol: str, enriched_data: Dict) -> Dict:
        # EMA crossover detection and momentum
        # RSI band positioning (60-70 target)
        # VWAP reclaim strength analysis
        # Key level breakout confirmation
        pass
```

#### D. VIGL Pattern Detector (`vigl_pattern_detector.py`)

**Purpose**: Updated VIGL similarity detection with confidence weighting

**Pattern Matching**:
- Float size similarity (target: 15M shares)
- Volume surge matching (target: 20.9x average)
- Short interest correlation (target: 18%)
- Price range compatibility ($2.94 historical entry)

**Enhanced Similarity Algorithm**:
```python
def calculate_vigl_similarity(enriched_data: Dict) -> Dict:
    """Calculate similarity to VIGL pattern with confidence weighting"""
    vigl_profile = {
        'float_shares': 15_200_000,
        'volume_multiple': 20.9,
        'short_interest_pct': 18.0,
        'entry_price': 2.94
    }
    
    # Multi-dimensional similarity scoring
    # Confidence weighting based on data quality
    # Historical pattern correlation analysis
```

### 2. Advanced Gating System

#### Hard Gates (Must Pass - Zero Score if Failed)

**Gate Implementation**:
```python
class HardGateValidator:
    def __init__(self, config: Dict):
        self.gates = {
            'min_relvol_30': config.get('min_relvol_30', 2.5),
            'min_atr_pct': config.get('min_atr_pct', 0.04),
            'vwap_reclaim': config.get('require_vwap_reclaim', True),
            'rsi_band': config.get('rsi_band', [60, 70]),
            'ema_cross_bullish': True
        }
    
    def validate(self, enriched_data: Dict) -> Tuple[bool, List[str]]:
        """Returns (passed, failed_gates)"""
        failures = []
        
        # RelVol Gate
        if enriched_data.get('relvol_30', 0) < self.gates['min_relvol_30']:
            failures.append(f"relvol_30_insufficient_{enriched_data.get('relvol_30')}")
        
        # ATR Gate
        if enriched_data.get('atr_pct', 0) < self.gates['min_atr_pct']:
            failures.append(f"atr_expansion_insufficient_{enriched_data.get('atr_pct')}")
        
        # VWAP Reclaim Gate
        if self.gates['vwap_reclaim']:
            price = enriched_data.get('price', 0)
            vwap = enriched_data.get('vwap', 0)
            if not vwap or price < vwap * 0.995:  # Must be within 0.5% of VWAP
                failures.append("vwap_reclaim_failed")
        
        return len(failures) == 0, failures
```

**Gate Categories**:
1. **Volume Gates**: RelVol ≥ 2.5x, volume spike ≥ 1.5x
2. **Volatility Gates**: ATR ≥ 4%, expanding volatility required  
3. **Momentum Gates**: VWAP reclaim, 9/20 EMA bullish cross
4. **Quality Gates**: RSI 60-70 band, not overbought condition

#### Soft Gates (Confidence Reduction)

**Soft Gate Penalties**:
```python
class SoftGateValidator:
    def __init__(self, config: Dict):
        self.penalties = {
            'data_age_hourly': -0.10,      # -10% per hour beyond staleness
            'missing_provider': -0.15,     # -15% per unavailable key metric
            'low_confidence_data': -0.20,  # -20% for confidence < 0.5
            'session_mismatch': -0.10      # -10% for non-optimal session
        }
    
    def calculate_confidence_adjustment(self, enriched_data: Dict, providers: Dict) -> float:
        """Calculate confidence reduction from soft gate failures"""
        adjustment = 1.0
        
        # Data age penalties
        data_age = enriched_data.get('data_age_minutes', 0)
        if data_age > 60:  # Beyond 1 hour
            hours_over = (data_age - 60) / 60
            adjustment += self.penalties['data_age_hourly'] * hours_over
        
        # Missing provider penalties
        required_providers = ['finra_short', 'polygon_live', 'alpha_vantage_options']
        missing_count = sum(1 for p in required_providers if not providers.get(p))
        adjustment += self.penalties['missing_provider'] * missing_count
        
        return max(0.1, adjustment)  # Minimum 10% confidence
```

### 3. Session-Aware Thresholds

#### Market Session Adaptations

**Session Configuration**:
```python
SESSION_CONFIGS = {
    'premarket': {
        'active_hours': '04:00-09:30 ET',
        'threshold_adjustments': {
            'min_relvol_30': 3.0,          # Higher volume requirement
            'min_atr_pct': 0.05,           # Higher volatility requirement
            'require_vwap_reclaim': False,  # VWAP less reliable
            'min_dollar_volume': 2_000_000  # Higher liquidity requirement
        },
        'weight_adjustments': {
            'volume_momentum': 0.45,        # Emphasize volume in premarket
            'technical': 0.05               # Reduce technical reliability
        }
    },
    'regular': {
        'active_hours': '09:30-16:00 ET',
        'threshold_adjustments': {
            # Standard thresholds as configured
        }
    },
    'afterhours': {
        'active_hours': '16:00-20:00 ET',
        'threshold_adjustments': {
            'min_relvol_30': 2.8,          # Slightly higher volume
            'min_dollar_volume': 1_000_000, # Moderate liquidity
            'require_momentum_confirmation': True
        },
        'discovery_frequency': '30min'      # Reduce frequency
    },
    'overnight': {
        'active_hours': '20:00-04:00 ET',
        'status': 'SUSPENDED',              # No active discovery
        'emergency_only': True
    }
}
```

#### Session Detection Logic

```python
class SessionManager:
    def get_current_session(self) -> str:
        """Detect current market session based on ET timezone"""
        now = datetime.now(timezone.utc)
        et_time = now.astimezone(pytz.timezone('US/Eastern'))
        hour_minute = et_time.hour + et_time.minute / 60.0
        
        if 4.0 <= hour_minute < 9.5:
            return 'premarket'
        elif 9.5 <= hour_minute < 16.0:
            return 'regular'  
        elif 16.0 <= hour_minute < 20.0:
            return 'afterhours'
        else:
            return 'overnight'
    
    def get_session_config(self, session: str) -> Dict:
        """Get session-specific configuration"""
        return SESSION_CONFIGS.get(session, SESSION_CONFIGS['regular'])
```

### 4. Free-Data Integration Strategy

#### Provider Management System

**Token Bucket Implementation**:
```python
class ProviderManager:
    def __init__(self):
        self.rate_limits = {
            'finra_short': TokenBucket(capacity=60, refill_rate=1),  # 60/min
            'alpha_vantage_options': TokenBucket(capacity=5, refill_rate=0.083),  # 5/min
            'polygon_live': TokenBucket(capacity=100, refill_rate=5)  # 100/min
        }
        
        self.circuit_breakers = {
            'finra_short': CircuitBreaker(failure_threshold=3, timeout=300),
            'alpha_vantage_options': CircuitBreaker(failure_threshold=2, timeout=180),
            'polygon_live': CircuitBreaker(failure_threshold=5, timeout=120)
        }
    
    async def fetch_with_retry(self, provider: str, request_func, *args, **kwargs):
        """Fetch data with rate limiting and circuit breaker protection"""
        # Check rate limit
        if not self.rate_limits[provider].consume():
            raise RateLimitExceeded(f"Rate limit exceeded for {provider}")
        
        # Check circuit breaker
        if self.circuit_breakers[provider].is_open():
            raise CircuitBreakerOpen(f"Circuit breaker open for {provider}")
        
        try:
            result = await request_func(*args, **kwargs)
            self.circuit_breakers[provider].record_success()
            return result
        except Exception as e:
            self.circuit_breakers[provider].record_failure()
            raise
```

#### Fallback Chain Strategy

**Data Source Priority**:
1. **Primary**: Fresh data from configured provider
2. **Cache**: Recent cached data (within staleness threshold)
3. **Skip**: Never fabricate or use default values

**Fallback Implementation**:
```python
class DataFallbackManager:
    async def get_short_interest_data(self, symbol: str) -> Optional[Dict]:
        """Get short interest with fallback chain"""
        
        # Try FINRA primary
        try:
            data = await self.provider_manager.fetch('finra_short', symbol)
            if self._validate_freshness(data, max_age_hours=48):  # SI data bi-monthly
                return self._enrich_with_metadata(data, 'finra_primary', confidence=0.95)
        except Exception as e:
            logger.warning(f"FINRA primary failed for {symbol}: {e}")
        
        # Try cache fallback
        cached_data = await self.cache_manager.get(f"si:{symbol}")
        if cached_data and self._validate_freshness(cached_data, max_age_hours=72):
            return self._enrich_with_metadata(cached_data, 'cache', confidence=0.7)
        
        # No fallback - return None (never fabricate)
        logger.info(f"No valid short interest data for {symbol}")
        return None
```

### 5. Confidence Scoring System

#### Composite Confidence Calculation

**Formula**:
```
composite_confidence = min(
    data_confidence * provider_weight * freshness_factor,
    session_adjustment_factor,
    soft_gate_adjustment
)
```

**Provider Confidence Weights**:
- **FINRA**: 0.95 (regulatory source, high reliability)
- **Polygon**: 0.98 (real-time market data, very reliable)
- **Alpha Vantage**: 0.75 (third-party aggregator, good reliability)
- **Borrow Proxy**: 0.60 (derived calculations, moderate reliability)

**Freshness Factors**:
```python
def calculate_freshness_factor(data_age_minutes: int, max_age_minutes: int) -> float:
    """Calculate freshness factor with exponential decay"""
    if data_age_minutes <= max_age_minutes:
        return 1.0
    
    # Exponential decay beyond threshold
    decay_ratio = data_age_minutes / max_age_minutes
    return max(0.1, math.exp(-0.5 * (decay_ratio - 1)))
```

### 6. Experimental Framework

#### Shadow Testing Strategy

**Dual-Write Implementation**:
```python
class ShadowTestingManager:
    def __init__(self):
        self.strategies = ['legacy_v0', 'unified_detectors']
        self.redis_keys = {
            'legacy_v0': 'amc:discovery:contenders:legacy_v0',
            'unified_detectors': 'amc:discovery:contenders:unified'
        }
        
    async def run_parallel_discovery(self, universe: List[str]) -> Dict:
        """Run both strategies in parallel for comparison"""
        results = {}
        
        # Execute both strategies
        for strategy in self.strategies:
            try:
                start_time = time.time()
                candidates = await self._run_strategy(strategy, universe)
                execution_time = time.time() - start_time
                
                results[strategy] = {
                    'candidates': candidates,
                    'count': len(candidates),
                    'execution_time': execution_time,
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                # Write to strategy-specific Redis key
                await self._store_results(strategy, results[strategy])
                
            except Exception as e:
                logger.error(f"Strategy {strategy} failed: {e}")
                results[strategy] = {'error': str(e)}
        
        # Store comparison metadata
        await self._store_comparison(results)
        return results
```

#### A/B Testing Framework

**Traffic Splitting**:
```python
class ABTestingManager:
    def __init__(self, test_config: Dict):
        self.test_config = test_config
        self.traffic_split = test_config.get('traffic_split', {'legacy_v0': 80, 'unified': 20})
        
    def get_strategy_for_request(self, request_id: str) -> str:
        """Determine strategy based on consistent hashing"""
        hash_value = hash(request_id) % 100
        
        cumulative_weight = 0
        for strategy, weight in self.traffic_split.items():
            cumulative_weight += weight
            if hash_value < cumulative_weight:
                return strategy
        
        return 'legacy_v0'  # Fallback
```

**Success Metrics Tracking**:
- **Candidate Quality**: Overlap with manually validated opportunities (≥75% target)
- **Latency Performance**: 90th percentile discovery time (<30s target)
- **Error Rates**: System errors (<5% threshold for rollback)
- **Coverage**: Percentage of legacy_v0 symbols evaluated (≥90% target)

### 7. Performance Targets & Monitoring

#### Key Performance Indicators

**Operational Metrics**:
- **Discovery Latency**: <30s (90th percentile)
- **Data Freshness**: ≥80% within staleness thresholds
- **System Availability**: 99% uptime during market hours
- **Provider Success Rate**: ≥95% for critical providers

**Quality Metrics**:
- **Candidate Coverage**: ≥90% of legacy_v0 symbols evaluated
- **Manual Validation Overlap**: ≥75% correlation with expert validation
- **False Positive Rate**: <20% (based on 7-day follow-up analysis)
- **Discovery Consistency**: <15% variance between discovery runs

#### Monitoring Implementation

**Real-time Dashboards**:
```python
class MonitoringCollector:
    def collect_discovery_metrics(self, results: Dict) -> Dict:
        """Collect comprehensive discovery metrics"""
        return {
            'execution_metrics': {
                'total_candidates': len(results.get('candidates', [])),
                'execution_time_ms': results.get('execution_time', 0) * 1000,
                'hard_gate_failures': results.get('gate_failures', {}).get('hard', 0),
                'soft_gate_penalties': results.get('gate_failures', {}).get('soft', 0)
            },
            'data_quality': {
                'avg_confidence': self._calculate_avg_confidence(results),
                'provider_success_rates': self._get_provider_success_rates(),
                'freshness_score': self._calculate_freshness_score(results)
            },
            'detector_performance': {
                'volume_momentum_avg': self._get_detector_avg_score('volume_momentum'),
                'squeeze_avg': self._get_detector_avg_score('squeeze'),
                'catalyst_avg': self._get_detector_avg_score('catalyst'),
                'options_avg': self._get_detector_avg_score('options'),
                'technical_avg': self._get_detector_avg_score('technical')
            }
        }
```

### 8. Implementation Roadmap

#### Phase 1: Foundation (Week 1-2)
1. **Complete Missing Detectors**: Implement catalyst_news.py, options_flow.py, technicals.py, vigl_pattern_detector.py
2. **Advanced Gating System**: Hard/soft gate validation with confidence adjustments
3. **Session Manager**: Market session detection and threshold adaptation
4. **Provider Manager**: Rate limiting and circuit breakers

#### Phase 2: Integration (Week 3)
1. **Unified Discovery Pipeline**: Integrate all detectors with new gating system
2. **Confidence Scoring**: Implement composite confidence calculation
3. **Shadow Testing**: Parallel strategy execution for comparison
4. **Monitoring Framework**: Real-time metrics collection and dashboards

#### Phase 3: Testing & Validation (Week 4)
1. **A/B Testing Framework**: Traffic splitting and success metrics tracking
2. **Performance Optimization**: Latency improvements and caching strategies  
3. **Quality Assurance**: Manual validation correlation testing
4. **Documentation**: Operational runbooks and troubleshooting guides

#### Phase 4: Production Rollout (Week 5-6)
1. **Canary Deployment**: 10% traffic to unified system
2. **Gradual Rollout**: Increase to 50%, then 100% based on success metrics
3. **Performance Monitoring**: 24/7 monitoring with automatic rollback triggers
4. **Optimization Feedback Loop**: Continuous calibration based on results

### 9. Risk Management

#### Technical Risks

**Risk**: New detector failures causing system-wide issues
**Mitigation**: Circuit breakers per detector, automatic fallback to legacy_v0

**Risk**: Provider API failures disrupting discovery
**Mitigation**: Comprehensive fallback chains, never fabricate missing data

**Risk**: Performance degradation from complex scoring
**Mitigation**: Async processing, Redis caching, timeout controls

#### Operational Risks

**Risk**: False positive increase degrading trade quality
**Mitigation**: Conservative rollout with 75% overlap requirement

**Risk**: Discovery latency impacting real-time trading
**Mitigation**: <30s SLA with automatic degradation mode

**Risk**: Configuration drift causing inconsistent results
**Mitigation**: Version-controlled calibration with rollback capabilities

### 10. Success Criteria

#### Go-Live Requirements
- [ ] All 5 detectors implemented and tested (volume_momentum, squeeze, catalyst, options, technical)
- [ ] Hard/soft gating system operational with <5% error rate
- [ ] Session-aware thresholds tested across all market sessions  
- [ ] Provider integration with 95% success rate for critical providers
- [ ] Shadow testing shows ≥75% overlap with legacy_v0 results
- [ ] Performance targets met: <30s discovery time, 99% uptime
- [ ] Monitoring dashboards operational with real-time alerting

#### 30-Day Success Metrics
- [ ] Discovery consistency <15% variance between runs
- [ ] Manual validation correlation ≥75%
- [ ] False positive rate <20% based on 7-day follow-up
- [ ] System availability ≥99% during market hours
- [ ] Provider success rates ≥95% for critical data sources

This comprehensive plan provides the foundation for transforming AMC-TRADER's squeeze detection from basic pattern matching to a sophisticated, multi-dimensional analysis system capable of identifying explosive opportunities across various market conditions while maintaining strict data quality and operational reliability standards.