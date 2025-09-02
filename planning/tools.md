# AMC-TRADER Tools Specification

## Executive Summary

This specification defines comprehensive tools for AMC-TRADER including short interest data integration, portfolio health tracking, and thesis management systems. The architecture integrates real FINRA short interest data to replace placeholder values, while maintaining existing VIGL pattern detection, squeeze analysis, and learning system capabilities.

## Short Interest Data Integration System

### ShortInterestService API
- **Endpoint**: `/data/short-interest/{symbol}`
- **Authentication**: Internal service (no external auth required)
- **Function Signature**: `get_short_interest(symbol: str, use_cache: bool = True) -> Optional[ShortInterestData]`
- **Schema**:
```json
{
  "symbol": "VIGL",
  "short_interest_ratio": 0.245,
  "short_interest_shares": 1500000,
  "shares_outstanding": 15000000,
  "float_shares": 8500000,
  "settlement_date": "2025-01-15",
  "data_source": "yahoo_finance",
  "confidence_level": "high",
  "last_updated": "2025-01-17T14:30:00Z",
  "ttl_expires": "2025-02-16T14:30:00Z"
}
```
- **Retry Policy**: Exponential backoff: 1s, 2s, 4s, 8s (max 4 retries)
- **Latency Budget**: P50: 500ms, P95: 1500ms, P99: 3000ms
- **Rate Limits**: 10 requests/second, 10,000 daily limit

### Bulk Short Interest API
- **Endpoint**: `/data/short-interest/bulk`
- **Authentication**: Internal service
- **Function Signature**: `get_bulk_short_interest(symbols: List[str]) -> Dict[str, ShortInterestData]`
- **Schema**:
```json
{
  "symbols_requested": ["VIGL", "QUBT", "CRWV"],
  "symbols_found": 3,
  "symbols_cached": 2,
  "symbols_fresh": 1,
  "processing_time_ms": 1247,
  "data": {
    "VIGL": { /* ShortInterestData object */ },
    "QUBT": { /* ShortInterestData object */ },
    "CRWV": { /* ShortInterestData object */ }
  },
  "errors": [],
  "cache_performance": {
    "hit_rate": 0.67,
    "avg_age_days": 3.2
  }
}
```
- **Retry Policy**: Circuit breaker pattern with 5-failure threshold, 5-minute cooldown
- **Latency Budget**: P50: 2000ms, P95: 5000ms, P99: 10000ms (50 symbols)
- **Rate Limits**: 25 symbols per request maximum

### FINRA Schedule Service
- **Endpoint**: `/data/finra/schedule`
- **Authentication**: Internal service
- **Function Signature**: `get_finra_schedule() -> FINRAScheduleData`
- **Schema**:
```json
{
  "next_reporting_date": "2025-01-31",
  "next_settlement_date": "2025-02-04",
  "days_until_refresh": 14,
  "is_reporting_day": false,
  "should_refresh_today": true,
  "last_refresh_date": "2025-01-17",
  "refresh_schedule": {
    "mandatory_days": ["monday", "wednesday", "friday"],
    "finra_days": [15, "end_of_month"],
    "grace_period_hours": 6
  }
}
```
- **Retry Policy**: 2 attempts with 1-second delay
- **Latency Budget**: P50: 50ms, P95: 100ms, P99: 200ms
- **Rate Limits**: 60 requests/minute

## Short Interest Data Enrichers

### Yahoo Finance Data Fetcher
- **Purpose**: Primary data source for real-time short interest information
- **Dependencies**: [yfinance library, Redis cache, HTTP connection pool]
- **Processing Pipeline**:
  1. Validate symbol format and check cache
  2. Establish HTTP connection with timeout controls
  3. Parse Yahoo Finance stock info for short interest metrics  
  4. Validate and normalize data (convert percentages to decimals)
  5. Calculate implied values (shares short from percentage * float)
  6. Store in Redis with appropriate TTL based on data freshness
- **Error Handling**: 
  - Network timeouts: Exponential backoff retry
  - Rate limits: Circuit breaker with cooldown
  - Invalid data: Log error and use fallback methodology
  - Symbol not found: Cache negative result to prevent repeated lookups

### Historical Average Calculator
- **Purpose**: Generate reliable fallback short interest estimates using historical patterns
- **Dependencies**: [PostgreSQL historical data, Redis cache, Symbol classification service]
- **Processing Pipeline**:
  1. Query historical short interest data for symbol (last 90 days)
  2. Calculate weighted moving average (recent data weighted higher)
  3. Apply sector-based adjustments for missing symbols
  4. Generate confidence score based on data availability and volatility
  5. Store computed averages with moderate TTL (7 days)
- **Error Handling**: Fall back to sector averages if insufficient historical data

### Sector Average Fallback
- **Purpose**: Tertiary fallback using industry classification and sector short interest norms
- **Dependencies**: [Polygon sector classification, Industry short interest benchmarks]
- **Processing Pipeline**:
  1. Classify symbol by sector using Polygon reference data
  2. Retrieve current sector short interest averages
  3. Apply size-based adjustments (small-cap vs large-cap variations)
  4. Generate conservative confidence score for estimated data
  5. Cache sector averages with daily refresh cycle
- **Error Handling**: Use conservative 15% default if all classification fails

## Core Trading APIs

### Portfolio Health API
- **Endpoint**: `/portfolio/health`
- **Authentication**: Bearer token (Alpaca API integration)
- **Function Signature**: `get_portfolio_health() -> PortfolioHealthResponse`
- **Schema**:
```json
{
  "overall_health_score": 85.2,
  "risk_level": "MODERATE",
  "concentration_risk": 28.5,
  "sector_diversification_score": 72.1,
  "position_health_distribution": {
    "healthy": 12,
    "at_risk": 3,
    "critical": 2
  },
  "portfolio_momentum": "BULLISH",
  "cash_utilization": 0.92,
  "projected_monthly_return": 8.4,
  "health_alerts": ["HIGH_CONCENTRATION_UP", "THESIS_BREAKDOWN_PTNM"],
  "timestamp": "2024-08-30T20:17:35Z"
}
```
- **Retry Policy**: 3 attempts with exponential backoff (1s, 2s, 4s)
- **Latency Budget**: P50: 200ms, P95: 500ms, P99: 1000ms
- **Rate Limits**: 60 requests/minute per user

### Position Health Scoring API
- **Endpoint**: `/positions/{symbol}/health`
- **Authentication**: Bearer token
- **Function Signature**: `get_position_health(symbol: str, include_projections: bool = True) -> PositionHealthResponse`
- **Schema**:
```json
{
  "symbol": "UP",
  "health_score": 92.1,
  "health_status": "EXCELLENT",
  "thesis_status": "CONFIRMED",
  "vigl_pattern_match": {
    "similarity": 0.87,
    "pattern_type": "VIGL_SQUEEZE",
    "confidence": 0.92
  },
  "performance_metrics": {
    "unrealized_pl_pct": 85.5,
    "vs_spy_performance": 78.2,
    "momentum_score": 0.81,
    "volatility_score": 0.65
  },
  "risk_assessment": {
    "stop_loss_distance": -8.2,
    "position_size_risk": "OPTIMAL",
    "sector_risk": "LOW",
    "correlation_risk": 0.23
  },
  "projected_outcomes": {
    "30_day_target": 12.5,
    "90_day_target": 25.0,
    "stop_loss_probability": 0.15,
    "thesis_success_probability": 0.83
  }
}
```
- **Retry Policy**: 2 attempts with 500ms delay
- **Latency Budget**: P50: 150ms, P95: 300ms, P99: 500ms
- **Rate Limits**: 120 requests/minute per user

### Enhanced Thesis Tracking API
- **Endpoint**: `/thesis/{symbol}`
- **Authentication**: Bearer token
- **Function Signature**: `get_enhanced_thesis(symbol: str, include_ai: bool = True) -> ThesisResponse`
- **Schema**:
```json
{
  "symbol": "QUBT",
  "thesis_type": "ENTRY_CONFIRMED",
  "ai_generated": true,
  "investment_thesis": "QUBT quantum computing breakthrough with institutional validation. Revenue acceleration + patent portfolio expansion creating sustainable moat.",
  "key_catalysts": [
    "Q4 earnings beat expectations",
    "IBM partnership announcement",
    "Quantum advantage demonstration"
  ],
  "risk_factors": [
    "Technology competition risk",
    "Market volatility in tech sector",
    "Execution risk on scaling"
  ],
  "price_targets": {
    "conservative": 12.50,
    "base_case": 18.75,
    "bull_case": 28.00,
    "stop_loss": 8.92
  },
  "timeline": "3-6 months for initial targets",
  "confidence_score": 0.78,
  "learning_metadata": {
    "decision_logged": true,
    "outcome_tracking": true,
    "pattern_classification": "TECH_CATALYST",
    "historical_similar_trades": 3
  },
  "last_updated": "2024-08-30T20:17:35Z"
}
```
- **Retry Policy**: 3 attempts with exponential backoff
- **Latency Budget**: P50: 300ms, P95: 800ms, P99: 1500ms (includes AI processing)
- **Rate Limits**: 30 requests/minute per user (AI-enhanced), 60/min for cached

### Smart Position Organization API
- **Endpoint**: `/portfolio/positions/organized`
- **Authentication**: Bearer token
- **Function Signature**: `get_organized_positions(sort_by: str = "health_priority") -> OrganizedPositionsResponse`
- **Schema**:
```json
{
  "organization_type": "health_priority",
  "categories": {
    "urgent_action": {
      "positions": ["PTNM", "FINV"],
      "total_value": 1250.00,
      "avg_health_score": 25.3,
      "recommended_action": "REVIEW_IMMEDIATELY"
    },
    "profit_taking": {
      "positions": ["UP", "WULF"],
      "total_value": 4320.00,
      "avg_health_score": 88.7,
      "recommended_action": "CONSIDER_TRIMMING"
    },
    "hold_monitor": {
      "positions": ["QUBT", "GMAB", "KSS"],
      "total_value": 2180.00,
      "avg_health_score": 67.2,
      "recommended_action": "MONITOR_THESIS"
    }
  },
  "sorting_metadata": {
    "primary_sort": "health_score",
    "secondary_sort": "thesis_confidence",
    "filters_applied": ["exclude_cash"],
    "last_updated": "2024-08-30T20:17:35Z"
  }
}
```
- **Retry Policy**: 2 attempts with 300ms delay
- **Latency Budget**: P50: 100ms, P95: 200ms, P99: 400ms
- **Rate Limits**: 30 requests/minute per user

## Data Enrichers

### Portfolio Health Calculator
- **Purpose**: Real-time portfolio health scoring with multi-dimensional risk analysis
- **Dependencies**: [Alpaca Positions API, Polygon Market Data, Redis Cache, VIGL Pattern Detection]
- **Processing Pipeline**:
  1. Fetch current positions from Alpaca broker
  2. Enrich with real-time price data from Polygon
  3. Calculate position-level health scores
  4. Aggregate portfolio-level health metrics
  5. Apply VIGL pattern scoring weights
  6. Generate health alerts and recommendations
- **Error Handling**: Graceful degradation with cached data, fallback to basic metrics if AI unavailable

### VIGL Pattern Health Integrator
- **Purpose**: Integrate VIGL squeeze detection scores into position health calculations
- **Dependencies**: [SqueezeDetector Service, Historical Pattern Database, Thesis Generator]
- **Processing Pipeline**:
  1. Retrieve VIGL pattern confidence scores
  2. Map pattern similarity to health multipliers
  3. Apply historical pattern success rates
  4. Weight by current market conditions
  5. Generate pattern-specific health insights
- **Error Handling**: Default to standard health calculation if VIGL data unavailable

### Thesis Performance Tracker
- **Purpose**: Track thesis accuracy and update confidence scoring based on outcomes
- **Dependencies**: [Learning System Database, Performance Analytics, Market Data]
- **Processing Pipeline**:
  1. Monitor position performance vs thesis predictions
  2. Calculate thesis accuracy metrics
  3. Update confidence scoring algorithms
  4. Log learning data for system improvement
  5. Generate thesis status updates
- **Error Handling**: Queue failed updates for retry, maintain thesis history integrity

### Smart Position Organizer
- **Purpose**: Risk-based position sorting and grouping with intelligent categorization
- **Dependencies**: [Portfolio Health Calculator, Thesis Tracker, Market Conditions]
- **Processing Pipeline**:
  1. Calculate composite risk scores per position
  2. Apply thesis status weighting
  3. Group by risk categories and sectors
  4. Sort by action priority (urgent → monitor)
  5. Generate organization metadata
- **Error Handling**: Fall back to simple P&L sorting if advanced metrics fail

## Short Interest Signal Generators

### Real-Time Short Interest Validator
- **Calculation Method**:
```python
confidence_score = {
    "high": data_age < 7 and source == "yahoo_finance" and shares_data_complete,
    "medium": data_age < 14 and source in ["yahoo_finance", "historical_avg"],
    "low": data_age < 30 or source == "sector_average",
    "unreliable": data_age > 30 or source == "fallback_default"
}

validation_score = (
    data_freshness_factor * 0.40 +    # Recent data weighted heavily
    source_reliability_factor * 0.30 + # Yahoo Finance > Historical > Sector
    data_completeness_factor * 0.20 +  # All fields present and valid
    cross_reference_factor * 0.10      # Matches expected sector patterns
)
```
- **Input Requirements**: [Raw short interest data, Data source, Timestamp, Sector classification]
- **Update Frequency**: On every data fetch (real-time validation)
- **Validation Rules**: Must validate against sector norms, flag extreme outliers (>3 standard deviations)

### Discovery Pipeline SI Enricher  
- **Calculation Method**:
```python
# Enhanced squeeze scoring with real SI data
def calculate_enhanced_squeeze_score(volume_ratio, real_short_interest, float_shares, confidence_level):
    base_score = calculate_original_squeeze_score(volume_ratio, real_short_interest, float_shares)
    
    # Confidence multiplier based on data quality
    confidence_multiplier = {
        "high": 1.10,     # 10% boost for high-confidence data
        "medium": 1.05,   # 5% boost for medium-confidence data
        "low": 1.00,      # No adjustment for low-confidence data
        "unreliable": 0.90  # 10% penalty for unreliable data
    }
    
    # Real data available bonus (vs placeholder estimates)
    real_data_bonus = 0.05 if confidence_level in ["high", "medium"] else 0.00
    
    enhanced_score = (base_score * confidence_multiplier[confidence_level]) + real_data_bonus
    return min(enhanced_score, 1.0)  # Cap at 1.0
```
- **Input Requirements**: [VIGL pattern data, Real short interest ratio, Float data, Data confidence level]
- **Update Frequency**: During discovery pipeline execution (every 5 minutes during market hours)
- **Validation Rules**: Score enhancement must not exceed 15% of base score, validate SI ratio is 0.0-1.0

### Short Interest Alert Generator
- **Calculation Method**:
```python
# Generate alerts for significant short interest changes
def generate_si_alerts(symbol, current_si, historical_si, volume_spike):
    alerts = []
    
    # Significant increase in short interest (squeeze setup)
    if current_si > historical_si * 1.20:  # 20% increase
        alerts.append({
            "type": "SHORT_INTEREST_SPIKE",
            "severity": "HIGH" if current_si > 0.25 else "MEDIUM",
            "message": f"{symbol}: SI increased to {current_si*100:.1f}% (+{(current_si-historical_si)*100:.1f}%)"
        })
    
    # High SI with volume surge (potential squeeze trigger)
    if current_si > 0.20 and volume_spike > 5.0:  # >20% SI + >5x volume
        alerts.append({
            "type": "SQUEEZE_TRIGGER_DETECTED", 
            "severity": "EXTREME",
            "message": f"{symbol}: {current_si*100:.1f}% SI + {volume_spike:.1f}x volume = SQUEEZE RISK"
        })
    
    return alerts
```
- **Input Requirements**: [Current short interest, Historical baseline, Volume surge ratio, Market context]
- **Update Frequency**: Real-time during market hours when SI data updates
- **Validation Rules**: Alerts must include severity level, validate against false positive patterns

### Cache Performance Optimizer
- **Calculation Method**:
```python
# Dynamic TTL calculation based on data quality and market conditions
def calculate_optimal_ttl(data_source, data_age, symbol_volatility, market_conditions):
    base_ttl = {
        "yahoo_finance": 2592000,    # 30 days for fresh Yahoo data
        "historical_avg": 1209600,   # 14 days for computed averages  
        "sector_average": 604800,    # 7 days for sector estimates
        "fallback_default": 3600     # 1 hour for emergency defaults
    }
    
    # Adjust for data staleness
    staleness_factor = max(0.1, 1.0 - (data_age / 30))  # Reduce TTL for stale data
    
    # Adjust for symbol volatility (high volatility = shorter cache)
    volatility_factor = max(0.5, 1.0 - symbol_volatility)
    
    # Market condition adjustment (volatile markets = shorter cache)
    market_factor = 0.7 if market_conditions == "high_volatility" else 1.0
    
    optimal_ttl = base_ttl[data_source] * staleness_factor * volatility_factor * market_factor
    return int(optimal_ttl)
```
- **Input Requirements**: [Data source type, Data age in days, Symbol volatility score, Market conditions]
- **Update Frequency**: On every cache store operation
- **Validation Rules**: TTL must be between 1 hour and 30 days, validate market conditions enum

## Enhanced Integration Architecture  

### Discovery Pipeline Integration
- **Integration Point**: `backend/src/jobs/discover.py` lines 1112-1121
- **Data Flow**: Discovery job → ShortInterestService → Real SI data → Enhanced squeeze scoring
- **Performance Impact**: < 2 seconds additional latency, >95% cache hit rate target
- **Fallback Strategy**: Continue with conservative 15% default if service unavailable

### SqueezeDetector Enhancement  
- **Integration Point**: `backend/src/services/squeeze_detector.py` lines 118-124
- **Enhanced Logic**: Real short interest data replaces hardcoded 25-30% defaults
- **Confidence Scoring**: Data quality impacts final squeeze score (±15% adjustment)
- **Pattern Validation**: Cross-reference SI data with historical squeeze patterns

### Frontend Data Pipeline
- **API Updates**: `/discovery/squeeze-candidates` returns real SI data with metadata
- **Response Enhancement**: Include data source, confidence level, settlement date
- **UI Integration**: Replace "25.0% short interest" placeholders with dynamic values
- **Error Handling**: Graceful fallback display when real data unavailable

### Redis Caching Integration
- **Cache Strategy**: Hierarchical caching with dynamic TTL based on data quality
- **Key Namespace**: `amc:short_interest:*` for all SI-related cache data
- **Memory Management**: Target <100MB total cache size for 5000 symbols
- **Performance Monitoring**: Track hit rates, latency, memory usage

## Signal Generators

### Portfolio Health Score Generator
- **Calculation Method**:
```python
health_score = (
    position_performance_score * 0.35 +
    risk_management_score * 0.25 +
    diversification_score * 0.20 +
    thesis_confirmation_score * 0.15 +
    momentum_score * 0.05
)

# With VIGL pattern boost
if vigl_pattern_detected:
    health_score += vigl_confidence * 0.10
```
- **Input Requirements**: [Position P&L, Sector allocation, Thesis status, VIGL scores, Market momentum]
- **Update Frequency**: Real-time during market hours, every 5 minutes after hours
- **Validation Rules**: Score must be 0-100, validate input data quality, flag anomalies

### Position Health Status Generator
- **Calculation Method**:
```python
position_health = {
    "EXCELLENT": health_score >= 85 and pl_pct > 10,
    "GOOD": health_score >= 70 or (pl_pct > 5 and thesis_confirmed),
    "MODERATE": health_score >= 50 or (pl_pct > -5 and thesis_intact),
    "AT_RISK": health_score >= 30 or (pl_pct > -15 and stop_loss_safe),
    "CRITICAL": health_score < 30 or pl_pct < -20
}
```
- **Input Requirements**: [Health score, P&L percentage, Thesis status, Stop loss distance]
- **Update Frequency**: Every position update (real-time)
- **Validation Rules**: Single status per position, thesis status must be valid enum

### Projected Outcome Calculator
- **Calculation Method**:
```python
# Monte Carlo simulation with historical pattern data
projected_return = (
    base_case_probability * base_case_return +
    bull_case_probability * bull_case_return +
    bear_case_probability * bear_case_return
)

# VIGL pattern historical success rate adjustment
if vigl_pattern_match > 0.8:
    projected_return *= 1.324  # Historical VIGL average return
```
- **Input Requirements**: [Current price, Historical volatility, Thesis targets, Market conditions, Pattern classification]
- **Update Frequency**: Daily after market close, on significant price moves (>5%)
- **Validation Rules**: Projections must include confidence intervals, validate against historical ranges

### Learning System Decision Logger
- **Calculation Method**:
```python
decision_value = {
    "confidence_weighted_return": actual_return * original_confidence,
    "thesis_accuracy_score": 1.0 if thesis_confirmed else 0.0,
    "pattern_success_rate": pattern_wins / pattern_total_decisions,
    "system_improvement_factor": new_accuracy / baseline_accuracy
}
```
- **Input Requirements**: [Original decision data, Current outcomes, Time held, Market context]
- **Update Frequency**: On position close or major milestone (50% gain/loss)
- **Validation Rules**: All decisions must be logged, outcome data must be complete

## Integration Architecture

### AMC-TRADER API Compatibility
- **Base URL**: https://amc-trader.onrender.com
- **Existing Endpoints**: Maintain full compatibility with `/portfolio/holdings`, `/discovery/contenders`
- **New Endpoints**: Add health and thesis endpoints with consistent response format
- **Authentication**: Integrate with existing Alpaca API key management
- **Data Flow**: Preserve existing Redis caching strategy, add health cache layer

### Live Trading Safety Integration
- **Position Size Validation**: Integrate with existing risk management rules
- **Stop Loss Automation**: Connect to Alpaca bracket order system
- **Thesis Breakdown Alerts**: Real-time notifications for critical health changes
- **Paper vs Live Mode**: Separate health thresholds for paper (aggressive) vs live (conservative)

### Learning System Integration Points
- **Decision Logging**: 
  ```python
  await LearningSystem.log_decision(
      symbol=symbol,
      decision_type="THESIS_UPDATE",
      recommendation_source="portfolio_health_system",
      confidence_score=health_score / 100,
      metadata={
          "health_status": position_health,
          "vigl_pattern": vigl_match,
          "thesis_source": "ai_enhanced"
      }
  )
  ```
- **Outcome Tracking**:
  ```python
  await LearningSystem.log_outcome(
      symbol=symbol,
      outcome_type="thesis_confirmation" if confirmed else "thesis_failure",
      return_pct=actual_return,
      days_held=days_held,
      market_conditions={
          "initial_health_score": original_health,
          "final_health_score": current_health,
          "thesis_accuracy": thesis_accuracy
      }
  )
  ```

## Security and Compliance

### API Key Rotation Strategy
- **Alpaca Keys**: Rotate every 90 days, maintain 2-key overlap period
- **Polygon Keys**: Monitor usage, rotate on 80% limit approach
- **Claude API**: Separate keys for production/development environments
- **Redis Auth**: Environment-specific passwords, rotate monthly

### Secure Credential Storage
- **Production**: Environment variables with encrypted secrets
- **Development**: Local .env files (git-ignored)
- **Staging**: Separate credential set for testing
- **Backup Keys**: Encrypted offline storage for emergency access

### Audit Logging Requirements
- **Decision Logging**: All portfolio health decisions with full context
- **Performance Tracking**: Complete audit trail of thesis updates
- **Error Logging**: Detailed error context for debugging and compliance
- **Access Logging**: All API access with user context and timestamps

## Testing Requirements

### Short Interest Service Testing Specifications
- **Data Fetcher Tests**:
  ```python
  test_yahoo_finance_data_fetch_success()
  test_yahoo_finance_timeout_retry_logic()
  test_yahoo_finance_rate_limit_handling() 
  test_data_validation_and_normalization()
  test_cache_hit_miss_scenarios()
  test_fallback_chain_execution()
  test_historical_average_calculation()
  test_sector_average_fallback()
  ```
- **Integration Tests**:
  ```python
  test_discovery_pipeline_si_integration()
  test_squeeze_detector_enhanced_scoring()
  test_redis_cache_performance_requirements()
  test_finra_schedule_date_calculation()
  test_bulk_request_processing()
  test_circuit_breaker_functionality()
  test_error_handling_and_graceful_degradation()
  ```
- **Load Tests**:
  ```python
  test_concurrent_api_calls_under_load()
  test_cache_memory_usage_under_stress()
  test_api_latency_under_sustained_load() 
  test_discovery_pipeline_performance_impact()
  ```

### Unit Test Specifications  
- **Health Calculator Tests**:
  ```python
  test_portfolio_health_calculation()
  test_position_health_scoring()
  test_vigl_pattern_integration()
  test_thesis_performance_tracking()
  ```
- **Integration Tests**:
  ```python
  test_alpaca_position_data_flow()
  test_learning_system_integration()
  test_redis_cache_performance()
  test_ai_thesis_generation_fallbacks()
  ```

### Load Testing Parameters
- **Portfolio Health API**: 100 concurrent users, 1000 requests/minute
- **Position Health API**: 50 concurrent users, 500 requests/minute
- **Thesis API**: 20 concurrent users, 200 requests/minute (AI-limited)
- **Response Time SLA**: 95% of requests under P95 latency targets

### Mock Service Specifications
- **Mock Alpaca API**: Complete position data with realistic P&L
- **Mock Polygon API**: Historical and real-time price data simulation
- **Mock AI Service**: Deterministic thesis generation for testing
- **Mock Learning System**: Outcome tracking and decision logging simulation

## Monitoring and Observability

### Short Interest Data Monitoring

#### Key Performance Indicators
- **Data Quality Metrics**:
  - Short interest cache hit rate: Target >90%
  - Data freshness average: Target <7 days
  - API success rate: Target >95%
  - Confidence level distribution: Monitor "high"/"medium" vs "low"/"unreliable"
  
- **Performance Metrics**:
  - API response latency: P95 <1500ms
  - Discovery pipeline SI coverage: Target >80% of symbols with real data
  - Cache memory usage: Target <100MB
  - Fallback usage rate: Target <20%

#### Alert Configuration
```python
ALERT_THRESHOLDS = {
    "cache_hit_rate_low": {"threshold": 0.85, "duration": "5m"},
    "api_success_rate_low": {"threshold": 0.90, "duration": "2m"}, 
    "data_freshness_high": {"threshold": 10.0, "duration": "1d"},  # days
    "circuit_breaker_open": {"threshold": 1, "duration": "1m"},
    "fallback_usage_high": {"threshold": 0.30, "duration": "10m"},
    "discovery_si_coverage_low": {"threshold": 0.70, "duration": "15m"}
}
```

#### Operational Dashboards
- **Short Interest Data Health**: Real-time cache performance, API status, data quality scores
- **Discovery Pipeline Enhancement**: SI data coverage per discovery run, squeeze score improvements
- **Service Reliability**: Error rates, circuit breaker status, fallback activation frequency
- **Data Source Performance**: Yahoo Finance API latency/success, historical vs fresh data usage

### Health Score Monitoring
- **Portfolio Health Alerts**: < 70 score triggers review, < 50 triggers intervention
- **Position Health Alerts**: CRITICAL status triggers immediate notification
- **Thesis Breakdown Alerts**: Confidence drop > 20 points triggers review
- **Performance Degradation**: API response time > 2x baseline triggers scaling

### Learning System Metrics
- **Decision Accuracy**: Track portfolio health system recommendation success rate
- **Thesis Accuracy**: Monitor AI thesis prediction vs actual outcomes
- **Pattern Success Rates**: VIGL and other pattern performance tracking
- **System Improvement**: Overall learning system effectiveness measurement

### Error Rate Monitoring
- **API Error Thresholds**: > 5% error rate triggers immediate investigation
- **Data Quality Issues**: Position data inconsistencies flagged and resolved
- **AI Service Availability**: Claude API failures trigger fallback thesis generation
- **Cache Performance**: Redis cache hit rates monitored for optimization

## Performance Requirements

### Latency Budgets
- **Portfolio Overview**: P50: 200ms, P95: 500ms, P99: 1000ms
- **Position Details**: P50: 150ms, P95: 300ms, P99: 500ms
- **AI Thesis Generation**: P50: 800ms, P95: 2000ms, P99: 5000ms
- **Learning Integration**: P50: 100ms, P95: 200ms, P99: 500ms

### Throughput Requirements
- **Peak Trading Hours**: 200 requests/second portfolio data
- **Market Open Surge**: 500 requests/second for 10 minutes
- **After Hours**: 50 requests/second steady state
- **Weekend/Maintenance**: 10 requests/second minimum

### Resource Utilization Constraints
- **Memory Usage**: < 2GB RAM per service instance
- **CPU Usage**: < 70% average, < 90% peak during market hours
- **Database Connections**: < 50 concurrent connections per service
- **Redis Memory**: < 500MB for portfolio health cache data

## Implementation Phases

### Phase 1: Core Health Scoring (Week 1-2)
- Implement portfolio and position health calculators
- Integrate with existing Alpaca position data
- Basic health score UI integration
- Unit tests and initial performance optimization

### Phase 2: VIGL Pattern Integration (Week 3-4)
- Connect health scoring to existing VIGL squeeze detection
- Pattern-based health score weighting
- Enhanced thesis status tracking
- Integration testing with squeeze alert system

### Phase 3: AI Thesis Enhancement (Week 5-6)
- Full AI-powered thesis generation integration
- Learning system decision logging
- Projected outcome calculations
- Performance analytics dashboard integration

### Phase 4: Smart Organization & Analytics (Week 7-8)
- Risk-based position sorting and grouping
- Advanced portfolio analytics
- Learning system feedback loops
- Production deployment and monitoring

## Implementation Phases

### Phase 0: Short Interest Data Integration (Week 1-2)
- Implement ShortInterestService with Yahoo Finance integration
- Deploy Redis caching with hierarchical fallback strategy
- Integrate real SI data into discovery pipeline
- Replace hardcoded 30% defaults with dynamic data
- Comprehensive testing and performance validation

### Phase 0.5: Discovery Enhancement (Week 2-3)  
- Enhanced SqueezeDetector with real SI confidence scoring
- Frontend API updates to display real short interest percentages
- FINRA schedule integration for optimal refresh timing
- Monitoring dashboard deployment for SI data quality
- Production rollout with feature flags and rollback capability

## Success Metrics

### Short Interest Data Quality Improvements
- **Data Accuracy**: >80% of discovery candidates use real FINRA data (vs 0% placeholder)
- **Cache Performance**: >90% cache hit rate during market hours  
- **Data Freshness**: <7 days average age for short interest data
- **Service Reliability**: >99% uptime during market hours with <1500ms P95 latency
- **Discovery Enhancement**: >15% improvement in squeeze detection accuracy

### Business Impact Validation
- **User Experience**: Eliminate "placeholder short interest" complaints
- **Squeeze Detection Quality**: More accurate ranking based on real SI data
- **System Performance**: <10% discovery pipeline latency increase
- **Data Confidence**: 70%+ of displayed short interest marked as "high confidence"
- **Frontend Integration**: Real-time SI data displayed with source attribution

### Portfolio Management Effectiveness
- **Health Score Accuracy**: 80%+ correlation with actual portfolio performance
- **Early Warning System**: Identify 90%+ of positions before -15% loss
- **Thesis Accuracy**: 70%+ of AI thesis predictions achieve targets within timeframe
- **Risk Management**: Reduce portfolio drawdowns by 25% through health-based alerts

### Learning System Integration
- **Decision Logging Coverage**: 100% of portfolio health decisions logged
- **Outcome Tracking**: 95%+ of closed positions tracked for learning
- **System Improvement**: 10%+ quarterly improvement in recommendation accuracy
- **Pattern Recognition**: Identify new profitable patterns with 65%+ success rate

### Operational Performance
- **API Reliability**: 99.9% uptime during market hours
- **Response Time**: Meet P95 latency targets 98% of time
- **Data Quality**: < 1% position data inconsistencies
- **User Engagement**: 40%+ increase in portfolio review frequency

This comprehensive tools specification provides the foundation for implementing a robust portfolio health and thesis tracking system that leverages the existing AMC-TRADER infrastructure while adding sophisticated learning and analysis capabilities.