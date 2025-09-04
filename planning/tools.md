# AMC-TRADER Monitoring and Learning Infrastructure Specification

## Overview

This specification defines comprehensive monitoring and learning infrastructure for AMC-TRADER focused on discovery pipeline tracking, learning system integration, buy-the-dip detection, and intelligent alerting. The system builds upon existing components while ensuring no disruption to current functionality.

## 1. Discovery Pipeline Monitoring

### 1.1 Real-time Flow Tracking API

**Endpoint**: `GET /monitoring/discovery/pipeline`
**Function Signature**: `get_pipeline_status() -> PipelineStatusResponse`

```json
{
  "pipeline_id": "discovery_20250903_143022",
  "status": "running|completed|failed",
  "start_time": "2025-09-03T14:30:22Z",
  "end_time": "2025-09-03T14:35:18Z",
  "stages": [
    {
      "stage_name": "universe_loading",
      "status": "completed",
      "symbols_input": 2847,
      "symbols_output": 2847,
      "duration_ms": 245,
      "errors": []
    },
    {
      "stage_name": "price_filtering",
      "status": "completed", 
      "symbols_input": 2847,
      "symbols_output": 1249,
      "criteria": {
        "price_min": 0.01,
        "price_max": 10.00,
        "eliminated_count": 1598,
        "elimination_reasons": {
          "price_too_high": 1432,
          "price_too_low": 166
        }
      },
      "duration_ms": 1823,
      "errors": []
    },
    {
      "stage_name": "volume_filtering",
      "status": "completed",
      "symbols_input": 1249,
      "symbols_output": 87,
      "criteria": {
        "volume_spike_min": 10.0,
        "volume_spike_target": 20.9,
        "eliminated_count": 1162,
        "elimination_reasons": {
          "insufficient_volume_spike": 1162
        }
      },
      "duration_ms": 3456,
      "errors": []
    },
    {
      "stage_name": "squeeze_detection",
      "status": "completed",
      "symbols_input": 87,
      "symbols_output": 12,
      "criteria": {
        "vigl_threshold": 0.65,
        "wolf_risk_max": 0.5,
        "eliminated_count": 75,
        "elimination_reasons": {
          "low_vigl_score": 42,
          "high_wolf_risk": 33
        }
      },
      "duration_ms": 2145,
      "errors": []
    },
    {
      "stage_name": "final_ranking",
      "status": "completed",
      "symbols_input": 12,
      "symbols_output": 8,
      "final_candidates": [
        {
          "symbol": "QUBT",
          "composite_score": 8.7,
          "vigl_score": 0.78,
          "volume_spike_ratio": 23.4,
          "price": 2.94,
          "elimination_stage": null
        }
      ],
      "duration_ms": 567,
      "errors": []
    }
  ],
  "pipeline_health_score": 0.95,
  "fallback_detected": false,
  "total_duration_ms": 8236
}
```

**Authentication**: Bearer token from existing system
**Rate Limits**: 100 requests/minute
**Latency Budget**: P50: <500ms, P95: <1500ms, P99: <3000ms

### 1.2 Pipeline Health Monitoring Service

**Class**: `DiscoveryPipelineMonitor`
**Function Signature**: `monitor_pipeline_execution(pipeline_run: PipelineRun) -> HealthMetrics`

**Retry Policy**:
- Exponential backoff: 1s, 2s, 4s, 8s
- Circuit breaker: 5 failures in 60 seconds triggers 5-minute cooldown
- Fallback: Return cached health metrics if monitoring fails

**Error Handling**:
```python
class PipelineMonitoringError(Exception):
    pass

class PipelineHealthAlert(Exception):
    severity: str  # INFO, WARNING, CRITICAL, EMERGENCY
    component: str
    message: str
    recommended_action: str
```

### 1.3 Alert System for Pipeline Failures

**Endpoint**: `POST /monitoring/discovery/alerts`
**Function Signature**: `trigger_pipeline_alert(alert: PipelineAlert) -> AlertResponse`

```json
{
  "alert_id": "discovery_failure_20250903_143045",
  "severity": "CRITICAL",
  "component": "volume_filtering",
  "title": "Discovery Pipeline Failure",
  "message": "Volume filtering stage failed - no candidates found for 3 consecutive runs",
  "details": {
    "pipeline_run_id": "discovery_20250903_143022",
    "failed_stage": "volume_filtering",
    "error_code": "NO_VOLUME_SPIKE_CANDIDATES",
    "consecutive_failures": 3,
    "last_successful_run": "2025-09-03T14:15:22Z"
  },
  "recommended_actions": [
    "Check volume spike thresholds - current: 10.0x minimum",
    "Verify Polygon API data quality",
    "Consider temporary threshold relaxation"
  ],
  "escalation_required": true,
  "created_at": "2025-09-03T14:30:45Z"
}
```

## 2. Learning System Integration

### 2.1 Recommendation Tracking API

**Endpoint**: `POST /learning/recommendations/track`
**Function Signature**: `track_recommendation(recommendation: RecommendationData) -> TrackingResponse`

```json
{
  "tracking_id": "rec_track_20250903_QUBT_143045",
  "symbol": "QUBT",
  "discovery_date": "2025-09-03T14:30:45Z",
  "recommendation_data": {
    "composite_score": 8.7,
    "vigl_score": 0.78,
    "volume_spike_ratio": 23.4,
    "price_at_discovery": 2.94,
    "thesis": "Explosive volume surge with tight squeeze metrics matching VIGL pattern",
    "confidence": 0.87,
    "pattern_features": {
      "atr_pct": 0.085,
      "momentum_5d": 0.34,
      "compression_pct": 0.22,
      "wolf_risk": 0.31
    }
  },
  "bought": false,
  "tracking_period_days": 30,
  "performance_checkpoints": [1, 7, 14, 30],
  "alert_thresholds": {
    "missed_opportunity_pct": 25.0,
    "major_move_pct": 50.0
  }
}
```

### 2.2 Performance Monitoring Service

**Class**: `RecommendationPerformanceTracker`
**Function Signature**: `track_30day_performance(tracking_id: str) -> PerformanceData`

**Database Schema**:
```sql
CREATE TABLE recommendation_tracking (
    tracking_id VARCHAR(50) PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    discovery_date TIMESTAMP NOT NULL,
    discovery_price DECIMAL(10,4) NOT NULL,
    composite_score FLOAT NOT NULL,
    vigl_score FLOAT NOT NULL,
    pattern_features JSONB NOT NULL,
    bought BOOLEAN DEFAULT false,
    
    -- Performance tracking
    price_1d DECIMAL(10,4),
    price_7d DECIMAL(10,4), 
    price_14d DECIMAL(10,4),
    price_30d DECIMAL(10,4),
    
    return_1d DECIMAL(8,4),
    return_7d DECIMAL(8,4),
    return_14d DECIMAL(8,4),
    return_30d DECIMAL(8,4),
    
    peak_price DECIMAL(10,4),
    peak_return DECIMAL(8,4),
    days_to_peak INTEGER,
    max_drawdown DECIMAL(8,4),
    
    -- Learning classification
    outcome_category VARCHAR(20), -- explosive, strong, moderate, poor, failed
    missed_opportunity BOOLEAN DEFAULT false,
    learning_notes TEXT,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_rec_tracking_symbol ON recommendation_tracking(symbol);
CREATE INDEX idx_rec_tracking_discovery_date ON recommendation_tracking(discovery_date);
CREATE INDEX idx_rec_tracking_outcome ON recommendation_tracking(outcome_category);
CREATE INDEX idx_rec_tracking_bought ON recommendation_tracking(bought);
```

### 2.3 Missed Opportunity Alert System

**Endpoint**: `GET /learning/missed-opportunities`
**Function Signature**: `get_missed_opportunities(days_back: int = 7) -> List[MissedOpportunity]`

```json
{
  "missed_opportunities": [
    {
      "tracking_id": "rec_track_20250901_CRWV_091234",
      "symbol": "CRWV", 
      "discovery_date": "2025-09-01T09:12:34Z",
      "discovery_price": 1.85,
      "peak_price": 4.32,
      "peak_return_pct": 133.5,
      "days_to_peak": 3,
      "composite_score": 7.2,
      "vigl_score": 0.71,
      "why_missed": "Below composite score threshold (7.5 required)",
      "learning_opportunity": "Consider lowering composite threshold during high-volume periods",
      "similar_patterns": ["VIGL_20240615", "AEVA_20240722"],
      "recommended_action": "Add CRWV pattern to explosive winner training data"
    }
  ],
  "summary": {
    "total_missed": 3,
    "total_potential_return": 287.3,
    "avg_discovery_to_peak_days": 4.2,
    "pattern_insights": [
      "3/3 missed opportunities had volume spikes >15x average",
      "2/3 had VIGL scores >0.7 but below current threshold",
      "All occurred in $1-3 price range"
    ]
  }
}
```

## 3. Buy-the-Dip Detection

### 3.1 Portfolio Holdings Monitoring

**Endpoint**: `GET /dip-detection/portfolio-analysis`
**Function Signature**: `analyze_portfolio_dips() -> DipAnalysisResponse`

```json
{
  "analysis_timestamp": "2025-09-03T14:30:45Z",
  "portfolio_positions": [
    {
      "symbol": "QUBT",
      "current_price": 2.45,
      "entry_price": 2.94,
      "current_return_pct": -16.7,
      "position_size_usd": 1500.00,
      "days_held": 5,
      "original_thesis": "Explosive volume surge with tight squeeze metrics matching VIGL pattern",
      "thesis_strength": "STRONG",
      "dip_analysis": {
        "is_dip_buy_candidate": true,
        "dip_severity": "MODERATE",
        "thesis_still_valid": true,
        "catalyst_timeline": "Expected move within 7-14 days",
        "support_levels": [2.40, 2.20, 1.95],
        "resistance_levels": [2.85, 3.25, 3.70],
        "volume_analysis": "Still above 5x average - thesis intact",
        "risk_reward_ratio": 3.2,
        "recommended_action": "BUY_MORE",
        "recommended_size_pct": 0.15,
        "max_dip_allocation": 2500.00
      }
    }
  ],
  "summary": {
    "total_positions": 8,
    "dip_buy_candidates": 3,
    "strong_thesis_positions": 5,
    "total_dip_opportunity_usd": 3750.00
  }
}
```

### 3.2 Thesis Strength Evaluation Service

**Class**: `ThesisStrengthEvaluator`
**Function Signature**: `evaluate_thesis_strength(symbol: str, original_thesis: str) -> ThesisEvaluation`

**Processing Pipeline**:
1. Fetch current market conditions
2. Analyze volume patterns vs thesis predictions
3. Check catalyst timeline progress
4. Evaluate technical pattern integrity
5. Cross-reference with similar historical patterns
6. Generate strength score (0.0-1.0)

**Schema for Thesis Tracking**:
```sql
CREATE TABLE thesis_strength_history (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    evaluation_date TIMESTAMP NOT NULL,
    original_thesis TEXT NOT NULL,
    thesis_date TIMESTAMP NOT NULL,
    strength_score DECIMAL(4,3) NOT NULL,
    
    -- Evaluation factors
    volume_thesis_match DECIMAL(4,3),
    catalyst_timeline_status VARCHAR(20),
    technical_pattern_integrity DECIMAL(4,3),
    market_regime_alignment DECIMAL(4,3),
    
    -- Current conditions
    current_price DECIMAL(10,4),
    entry_price DECIMAL(10,4),
    volume_vs_avg DECIMAL(8,2),
    days_since_entry INTEGER,
    
    evaluation_notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 3.3 Buy-More Alert Generation

**Endpoint**: `POST /dip-detection/alerts/buy-more`
**Function Signature**: `generate_buy_more_alert(dip_candidate: DipCandidate) -> BuyMoreAlert`

```json
{
  "alert_id": "buy_more_QUBT_20250903_143045",
  "alert_type": "BUY_MORE_OPPORTUNITY",
  "symbol": "QUBT",
  "priority": "HIGH",
  "current_price": 2.45,
  "entry_price": 2.94,
  "dip_percentage": -16.7,
  "thesis_validation": {
    "original_thesis": "Explosive volume surge with tight squeeze metrics matching VIGL pattern",
    "thesis_strength": "STRONG",
    "validation_factors": [
      "Volume still 12.5x average (thesis: >10x) ✓",
      "Short interest increased to 22% (thesis: >18%) ✓", 
      "Float remains tight at 15.2M shares ✓",
      "No fundamental deterioration detected ✓"
    ],
    "invalidating_factors": []
  },
  "buy_more_recommendation": {
    "recommended_action": "BUY_MORE",
    "confidence": 0.82,
    "recommended_size_usd": 225.00,
    "recommended_size_pct": 15.0,
    "price_targets": {
      "support_level": 2.40,
      "entry_range_low": 2.35,
      "entry_range_high": 2.50
    },
    "risk_management": {
      "stop_loss": 2.15,
      "take_profit_1": 3.25,
      "take_profit_2": 4.15,
      "max_position_size_usd": 2500.00,
      "risk_reward_ratio": 3.2
    }
  },
  "catalyst_timeline": "Expected catalyst within 7-14 days based on pattern analysis",
  "historical_precedent": "Similar to VIGL pattern day 5-7 before +324% move",
  "created_at": "2025-09-03T14:30:45Z"
}
```

## 4. Alert System Architecture

### 4.1 Multi-Channel Alert Delivery

**Service**: `AlertDistributionService`
**Channels**: WebSocket, HTTP Push, Database Storage, Redis Pub/Sub

**Function Signature**: `distribute_alert(alert: Alert, channels: List[str]) -> DistributionResult`

**WebSocket Schema**:
```json
{
  "type": "alert",
  "channel": "discovery|learning|dip_detection|system_health",
  "severity": "INFO|WARNING|CRITICAL|EMERGENCY",
  "alert_data": {
    // Specific alert payload based on type
  },
  "timestamp": "2025-09-03T14:30:45Z",
  "requires_acknowledgment": true
}
```

### 4.2 Alert Aggregation and Prioritization

**Endpoint**: `GET /alerts/dashboard`
**Function Signature**: `get_alert_dashboard() -> AlertDashboard`

```json
{
  "dashboard_timestamp": "2025-09-03T14:30:45Z",
  "alert_summary": {
    "total_active_alerts": 7,
    "critical_alerts": 2,
    "warning_alerts": 3,
    "info_alerts": 2,
    "unacknowledged_alerts": 4
  },
  "priority_alerts": [
    {
      "alert_id": "discovery_failure_20250903_143045",
      "severity": "CRITICAL",
      "component": "Discovery Pipeline",
      "message": "Volume filtering stage failed - no candidates found",
      "age_minutes": 15,
      "requires_immediate_action": true,
      "estimated_revenue_impact_usd": 2500.00
    }
  ],
  "alert_categories": {
    "discovery_health": {
      "active_count": 3,
      "trend": "worsening",
      "last_24h_count": 12
    },
    "learning_opportunities": {
      "active_count": 2,
      "missed_opportunities_value_usd": 1250.00,
      "trend": "stable"
    },
    "buy_the_dip": {
      "active_count": 2,
      "total_opportunity_usd": 3750.00,
      "highest_confidence": 0.87
    }
  }
}
```

### 4.3 Alert Routing and Escalation

**Configuration**:
```json
{
  "alert_routing_rules": [
    {
      "condition": "severity == 'EMERGENCY'",
      "channels": ["websocket", "push_notification", "email"],
      "escalation_delay_minutes": 0
    },
    {
      "condition": "severity == 'CRITICAL' AND component == 'discovery'",
      "channels": ["websocket", "database"],
      "escalation_delay_minutes": 5,
      "escalation_channels": ["push_notification"]
    },
    {
      "condition": "alert_type == 'MISSED_OPPORTUNITY' AND potential_return > 50.0",
      "channels": ["websocket", "database"],
      "escalation_delay_minutes": 15
    }
  ],
  "escalation_chain": [
    {
      "level": 1,
      "delay_minutes": 5,
      "channels": ["push_notification"]
    },
    {
      "level": 2, 
      "delay_minutes": 15,
      "channels": ["email", "sms"]
    }
  ]
}
```

## 5. Integration Points

### 5.1 Existing System Integration

**Discovery Job Integration**:
- Hook into existing `discover.py` pipeline stages
- Add monitoring wrapper around `select_candidates()` function
- Preserve existing Redis cache keys and API contracts

**Database Integration**:
- Extend existing `recommendations` table with tracking fields
- Add new monitoring tables alongside existing schema
- Use existing connection pool and transaction patterns

**API Integration**:
- Add new routes to existing FastAPI routers
- Use existing authentication middleware
- Maintain existing response formats with extensions

### 5.2 Data Flow Integration Points

```python
# Example integration wrapper for existing discovery job
class MonitoredDiscoveryPipeline:
    def __init__(self, original_discovery_func):
        self.original_func = original_discovery_func
        self.monitor = DiscoveryPipelineMonitor()
        self.tracker = RecommendationPerformanceTracker()
    
    async def execute_monitored_discovery(self):
        pipeline_run = await self.monitor.start_pipeline_run()
        
        try:
            # Execute original discovery with monitoring
            candidates = await self.original_func()
            
            # Track new recommendations
            for candidate in candidates:
                await self.tracker.track_recommendation(candidate)
            
            await self.monitor.complete_pipeline_run(pipeline_run, candidates)
            return candidates
            
        except Exception as e:
            await self.monitor.fail_pipeline_run(pipeline_run, e)
            raise
```

## 6. Performance and Reliability Requirements

### 6.1 Latency Budgets

- **Discovery Pipeline Monitoring**: P95 < 200ms overhead
- **Recommendation Tracking**: P95 < 500ms
- **Alert Generation**: P95 < 1000ms
- **Dashboard API**: P95 < 2000ms
- **Buy-the-Dip Analysis**: P95 < 3000ms

### 6.2 Throughput Requirements

- **Pipeline Status Checks**: 100 requests/minute
- **Alert Distribution**: 1000 alerts/minute
- **Performance Tracking Updates**: 500 updates/minute
- **Database Writes**: 200 writes/minute sustained

### 6.3 Reliability Standards

- **System Uptime**: 99.9% during market hours
- **Data Accuracy**: 99.5% correlation with source systems
- **Alert Delivery**: 99.8% successful delivery rate
- **Monitoring Overhead**: <5% CPU impact on discovery pipeline

### 6.4 Error Handling Strategy

```python
class MonitoringError(Exception):
    """Base exception for monitoring system errors"""
    pass

class PipelineMonitoringError(MonitoringError):
    """Pipeline monitoring specific errors"""
    pass

class LearningSystemError(MonitoringError):
    """Learning system specific errors"""
    pass

class AlertDeliveryError(MonitoringError):
    """Alert delivery specific errors"""
    pass

# Error handling patterns
async def with_monitoring_fallback(func, fallback_value=None):
    """Execute function with monitoring, fallback on error"""
    try:
        return await func()
    except MonitoringError as e:
        logger.warning(f"Monitoring error: {e}")
        return fallback_value
    except Exception as e:
        logger.error(f"Unexpected monitoring error: {e}")
        return fallback_value
```

### 6.5 Circuit Breaker Configuration

```python
CIRCUIT_BREAKER_CONFIG = {
    "pipeline_monitoring": {
        "failure_threshold": 5,
        "timeout": 300,  # 5 minutes
        "expected_exception": PipelineMonitoringError
    },
    "alert_delivery": {
        "failure_threshold": 3,
        "timeout": 60,   # 1 minute
        "expected_exception": AlertDeliveryError
    },
    "performance_tracking": {
        "failure_threshold": 10,
        "timeout": 600,  # 10 minutes
        "expected_exception": LearningSystemError
    }
}
```

## 7. Security and Compliance

### 7.1 Authentication and Authorization

- **API Security**: Bearer token authentication using existing system
- **Role-Based Access**: Admin, Trader, Read-Only access levels
- **Rate Limiting**: Per-endpoint limits with user-specific overrides
- **Audit Logging**: All monitoring actions logged with user attribution

### 7.2 Data Privacy and Security

- **Sensitive Data**: Trading positions and P&L data encrypted at rest
- **API Keys**: Stored in secure credential management system
- **Network Security**: HTTPS only, no HTTP fallback
- **Input Validation**: All inputs validated against strict schemas

## 8. Deployment and Scaling

### 8.1 Deployment Strategy

- **Blue-Green Deployment**: Zero-downtime updates
- **Feature Flags**: Gradual rollout of monitoring features
- **Health Checks**: Comprehensive health check endpoints
- **Rollback Plan**: Automated rollback triggers on error rate spikes

### 8.2 Scaling Considerations

- **Horizontal Scaling**: Stateless services with load balancing
- **Database Scaling**: Read replicas for dashboard queries
- **Cache Optimization**: Redis caching for frequently accessed data
- **Background Processing**: Async task queue for heavy operations

## 9. Testing Requirements

### 9.1 Unit Testing

- **Coverage Target**: 90% code coverage for new monitoring components
- **Mock Services**: Comprehensive mocks for external dependencies
- **Error Simulation**: Test all error handling paths
- **Performance Tests**: Load testing for all critical paths

### 9.2 Integration Testing

- **End-to-End Workflows**: Complete pipeline monitoring flows
- **Alert Delivery Testing**: Multi-channel alert distribution
- **Database Integration**: Transaction handling and rollback scenarios
- **API Contract Testing**: Maintain existing API compatibility

### 9.3 Chaos Engineering

- **Failure Injection**: Simulate discovery pipeline failures
- **Network Partitions**: Test resilience to connectivity issues  
- **Database Failures**: Verify graceful degradation
- **Load Testing**: Sustained high-load scenarios

## 10. Implementation Roadmap

### Phase 1: Foundation (Week 1-2)
- Discovery pipeline monitoring infrastructure
- Basic alert system setup
- Database schema extensions
- Core monitoring APIs

### Phase 2: Learning Integration (Week 3-4)
- Recommendation tracking system
- Performance monitoring service
- Missed opportunity detection
- Learning feedback loops

### Phase 3: Advanced Features (Week 5-6)
- Buy-the-dip detection
- Advanced alert routing
- Dashboard integration
- Performance optimization

### Phase 4: Production Hardening (Week 7-8)
- Security audit and hardening
- Performance tuning
- Comprehensive testing
- Production deployment

This specification provides a comprehensive foundation for implementing robust monitoring and learning infrastructure while ensuring seamless integration with the existing AMC-TRADER system.