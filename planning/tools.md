# AMC-TRADER Portfolio Health & Thesis Tracking Tools Specification

## Executive Summary

This specification defines a comprehensive portfolio health and thesis tracking system for AMC-TRADER that integrates with existing VIGL pattern detection, squeeze analysis, and thesis generation capabilities. The system focuses on portfolio-level health metrics, position-level health scoring with intelligent thesis tracking, projected outcome calculations for learning system optimization, and smart risk-based organization.

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

## Success Metrics

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