# AMC-TRADER Learning System Architecture
## Isolated, Self-Correcting Intelligence Engine

### Current State Analysis

The learning system is **partially integrated** but not properly isolated. Current issues:

1. **Tight Coupling**: Learning modules directly imported into discovery/thesis systems
2. **No Isolation**: Learning failures could crash core trading functions
3. **Limited Data**: No historical trading data being collected systematically
4. **No Feedback Loops**: Recommendations aren't tracked through to outcomes

### Proposed Architecture: Isolated Learning Branch

## 1. Branch Structure
```
feature/learning-intelligence/
├── learning_engine/
│   ├── core/
│   │   ├── pattern_analyzer.py          # Historical pattern analysis
│   │   ├── outcome_tracker.py           # Trade outcome tracking
│   │   ├── thesis_validator.py          # Thesis accuracy validation
│   │   └── market_regime_detector.py    # Market condition analysis
│   ├── intelligence/
│   │   ├── adaptive_parameters.py       # Dynamic parameter tuning
│   │   ├── confidence_calibrator.py     # Confidence score calibration
│   │   ├── risk_profiler.py             # Risk pattern identification
│   │   └── performance_attributor.py    # Attribution analysis
│   ├── api/
│   │   ├── learning_routes.py           # Isolated API endpoints
│   │   ├── feedback_collector.py        # Data collection endpoints
│   │   └── insights_provider.py         # Intelligence delivery
│   ├── database/
│   │   ├── learning_schema.sql          # Isolated database schema
│   │   ├── migrations/                  # Schema migrations
│   │   └── backup_restore.py            # Data backup/restore
│   └── tests/
│       ├── test_learning_isolation.py   # Isolation testing
│       ├── test_feedback_loops.py       # End-to-end testing
│       └── mock_trading_data.py         # Test data generation
```

## 2. Data Flow Architecture

### Core Data Pipeline
```
Discovery System → Learning Data Collector → Learning Database
     ↓                       ↓                       ↓
Thesis Generator ← Intelligence Provider ← Pattern Analyzer
     ↓                       ↓                       ↓
Trade Execution → Outcome Tracker → Performance Attribution
```

### Isolation Mechanisms
1. **API-Only Communication**: No direct imports between systems
2. **Event-Driven Updates**: Async message queues for data transfer
3. **Circuit Breaker Pattern**: Learning failures don't affect trading
4. **Separate Database**: Isolated learning schema with replication

## 3. Learning Data Model

### Decision Tracking Table
```sql
CREATE TABLE learning_decisions (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    discovery_timestamp TIMESTAMP NOT NULL,
    discovery_features JSONB NOT NULL,        -- Full discovery data snapshot
    thesis_data JSONB,                        -- Generated thesis
    confidence_score FLOAT NOT NULL,
    decision_type VARCHAR(20) NOT NULL,       -- BUY/SELL/HOLD/IGNORE
    decision_source VARCHAR(50) NOT NULL,     -- discovery/thesis/manual
    market_conditions JSONB,                  -- VIX, sector, regime
    position_size_pct FLOAT,                  -- Actual position size taken
    entry_price FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Outcome Tracking Table
```sql
CREATE TABLE learning_outcomes (
    id SERIAL PRIMARY KEY,
    decision_id INTEGER REFERENCES learning_decisions(id),
    symbol VARCHAR(10) NOT NULL,
    evaluation_date TIMESTAMP NOT NULL,
    price_at_evaluation FLOAT NOT NULL,
    return_1d FLOAT, return_7d FLOAT, return_30d FLOAT,
    max_favorable_excursion FLOAT,            -- Best return achieved
    max_adverse_excursion FLOAT,              -- Worst drawdown
    volatility_realized FLOAT,                -- Actual volatility
    volume_pattern_accuracy FLOAT,            -- Volume prediction accuracy
    catalyst_materialized BOOLEAN,            -- Did catalyst occur?
    thesis_accuracy_score FLOAT,              -- How accurate was thesis?
    position_closed BOOLEAN DEFAULT FALSE,
    exit_price FLOAT,
    exit_reason VARCHAR(50),                   -- stop_loss/profit_target/manual
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Pattern Performance Table
```sql
CREATE TABLE pattern_performance (
    id SERIAL PRIMARY KEY,
    pattern_signature VARCHAR(100) NOT NULL,  -- Unique pattern identifier
    pattern_features JSONB NOT NULL,          -- Feature vector
    success_rate FLOAT NOT NULL,              -- % of successful trades
    avg_return FLOAT NOT NULL,                -- Average return
    avg_holding_period FLOAT,                 -- Days held on average
    max_return FLOAT,                         -- Best return achieved
    max_drawdown FLOAT,                       -- Worst drawdown
    confidence_calibration FLOAT,             -- How well calibrated
    market_regime VARCHAR(20),                -- Bull/bear/neutral
    last_updated TIMESTAMP DEFAULT NOW()
);
```

## 4. Intelligence Components

### A. Pattern Analyzer
```python
class PatternAnalyzer:
    """Identifies successful vs failed patterns from historical data"""

    async def analyze_discovery_patterns(self) -> Dict:
        """Find patterns in discovery features that led to success"""

    async def analyze_thesis_accuracy(self) -> Dict:
        """Measure thesis prediction accuracy over time"""

    async def identify_failure_modes(self) -> Dict:
        """Identify common failure patterns to avoid"""
```

### B. Adaptive Parameters Engine
```python
class AdaptiveParametersEngine:
    """Dynamically adjusts discovery/scoring parameters based on performance"""

    async def get_optimized_discovery_params(self, market_regime: str) -> Dict:
        """Return discovery parameters optimized for current conditions"""

    async def get_confidence_adjustments(self) -> Dict:
        """Return confidence score adjustments based on historical accuracy"""

    async def suggest_threshold_changes(self) -> Dict:
        """Suggest changes to scoring thresholds based on performance"""
```

### C. Performance Attributor
```python
class PerformanceAttributor:
    """Links trading performance to specific discovery features"""

    async def attribute_returns_to_features(self) -> Dict:
        """Identify which features drive returns"""

    async def calculate_feature_importance(self) -> Dict:
        """Calculate predictive importance of each feature"""

    async def detect_regime_shifts(self) -> Dict:
        """Detect when market conditions change effectiveness"""
```

## 5. Integration Points (API-Only)

### Discovery System Integration
```python
# In discovery system (NO DIRECT IMPORTS)
@router.post("/discovery/log-candidates")
async def log_discovery_candidates():
    """Log discovery results to learning system via API"""
    candidates = await run_discovery()

    # Send to learning system asynchronously
    await send_to_learning_api(
        endpoint="/learning/collect/discovery-data",
        data={"candidates": candidates, "timestamp": datetime.now()}
    )
```

### Thesis System Integration
```python
# In thesis system (NO DIRECT IMPORTS)
@router.post("/thesis/log-decision")
async def log_thesis_decision():
    """Log thesis decision to learning system"""
    thesis = await generate_thesis(symbol, data)

    # Send to learning system
    await send_to_learning_api(
        endpoint="/learning/collect/thesis-decision",
        data={"symbol": symbol, "thesis": thesis}
    )
```

### Learning System API
```python
# Isolated learning API
@router.post("/learning/collect/discovery-data")
async def collect_discovery_data(data: DiscoveryData):
    """Collect discovery data for learning"""

@router.post("/learning/collect/thesis-decision")
async def collect_thesis_decision(data: ThesisDecision):
    """Collect thesis decisions for tracking"""

@router.post("/learning/collect/trade-outcome")
async def collect_trade_outcome(data: TradeOutcome):
    """Collect actual trade outcomes for learning"""

@router.get("/learning/intelligence/adaptive-params")
async def get_adaptive_parameters():
    """Provide optimized parameters based on learning"""

@router.get("/learning/intelligence/pattern-insights")
async def get_pattern_insights():
    """Provide pattern-based insights"""
```

## 6. Feedback Loop Implementation

### Daily Learning Cycle
```python
async def daily_learning_cycle():
    """Daily learning and adaptation cycle"""

    # 1. Collect overnight outcomes
    outcomes = await collect_price_outcomes()

    # 2. Update pattern performance
    await update_pattern_performance(outcomes)

    # 3. Recalibrate confidence scores
    await recalibrate_confidence_scores()

    # 4. Update adaptive parameters
    new_params = await calculate_adaptive_parameters()

    # 5. Generate intelligence report
    intelligence = await generate_daily_intelligence()

    # 6. Update discovery system parameters (via API)
    await update_discovery_parameters(new_params)
```

### Weekly Deep Learning
```python
async def weekly_deep_analysis():
    """Weekly comprehensive analysis and model updates"""

    # 1. Pattern discovery - find new successful patterns
    new_patterns = await discover_new_patterns()

    # 2. Feature importance analysis
    feature_importance = await analyze_feature_importance()

    # 3. Market regime analysis
    regime_changes = await detect_regime_changes()

    # 4. Model recalibration
    await recalibrate_all_models()

    # 5. Generate strategy recommendations
    strategies = await generate_strategy_recommendations()
```

## 7. Self-Correction Mechanisms

### A. Confidence Calibration
```python
class ConfidenceCalibrator:
    """Ensures confidence scores match actual success rates"""

    async def calibrate_discovery_confidence(self):
        """Adjust discovery confidence to match actual performance"""

    async def calibrate_thesis_confidence(self):
        """Adjust thesis confidence based on prediction accuracy"""
```

### B. Parameter Optimization
```python
class ParameterOptimizer:
    """Continuously optimizes system parameters"""

    async def optimize_scoring_weights(self):
        """Optimize the 6-component scoring weights"""

    async def optimize_threshold_values(self):
        """Optimize buy/sell/hold thresholds"""

    async def optimize_risk_parameters(self):
        """Optimize position sizing and risk management"""
```

### C. Failure Mode Detection
```python
class FailureModeDetector:
    """Detects and prevents repeated failure patterns"""

    async def detect_systematic_failures(self):
        """Identify patterns that consistently lose money"""

    async def detect_overconfidence_bias(self):
        """Detect when system is overconfident"""

    async def detect_market_regime_mismatch(self):
        """Detect when system is miscalibrated for current market"""
```

## 8. Safety Mechanisms

### Circuit Breaker Pattern
```python
class LearningCircuitBreaker:
    """Prevents learning system failures from affecting trading"""

    def __init__(self):
        self.failure_count = 0
        self.last_failure = None
        self.circuit_open = False

    async def call_learning_api(self, endpoint: str, data: Dict):
        """Call learning API with circuit breaker protection"""
        if self.circuit_open:
            return {"status": "circuit_open", "fallback": True}

        try:
            result = await self._make_api_call(endpoint, data)
            self.failure_count = 0  # Reset on success
            return result
        except Exception as e:
            self.failure_count += 1
            if self.failure_count >= 3:
                self.circuit_open = True
                self.last_failure = datetime.now()

            return {"status": "error", "fallback": True, "error": str(e)}
```

### Graceful Degradation
```python
class LearningFallback:
    """Provide fallback intelligence when learning system unavailable"""

    def get_fallback_parameters(self) -> Dict:
        """Return conservative default parameters"""
        return {
            "discovery_threshold": 0.75,  # Higher threshold for safety
            "confidence_multiplier": 0.8,  # Reduce confidence
            "position_size_limit": 0.02   # Smaller positions
        }

    def get_fallback_insights(self) -> Dict:
        """Return basic insights when learning unavailable"""
        return {
            "recommendation": "Use conservative parameters",
            "confidence": 0.5,
            "reason": "Learning system unavailable"
        }
```

## 9. Deployment Strategy

### Phase 1: Isolated Development (Week 1-2)
1. Create feature branch `feature/learning-intelligence`
2. Implement core learning database schema
3. Build basic data collection APIs
4. Create circuit breaker integration points

### Phase 2: Data Collection (Week 3-4)
1. Deploy data collection endpoints
2. Begin collecting discovery and thesis data
3. Implement outcome tracking
4. Build basic pattern analysis

### Phase 3: Intelligence Generation (Week 5-6)
1. Implement adaptive parameter engine
2. Build confidence calibration
3. Create pattern insights
4. Test feedback loops

### Phase 4: Integration Testing (Week 7-8)
1. Test isolation boundaries
2. Verify circuit breaker functionality
3. Test graceful degradation
4. Performance testing

### Phase 5: Gradual Rollout (Week 9-10)
1. Deploy to staging environment
2. Shadow mode testing (collect but don't act)
3. A/B testing with small percentage
4. Full production deployment

## 10. Monitoring and Observability

### Learning System Health Dashboard
```python
class LearningHealthMonitor:
    """Monitor learning system health and performance"""

    async def get_health_metrics(self) -> Dict:
        return {
            "data_collection_rate": await self.get_collection_rate(),
            "pattern_analysis_latency": await self.get_analysis_latency(),
            "prediction_accuracy": await self.get_prediction_accuracy(),
            "circuit_breaker_status": await self.get_circuit_status(),
            "database_health": await self.get_db_health()
        }
```

### Performance Metrics
- **Data Collection Success Rate**: >99%
- **API Response Time**: <200ms
- **Prediction Accuracy**: Track over time
- **Pattern Discovery Rate**: New patterns per week
- **System Uptime**: >99.9%

This architecture ensures the learning system can evolve and improve the trading system while maintaining complete isolation and safety boundaries.