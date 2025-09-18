# AMC-TRADER Learning System Separation Plan
## Safe Isolation Strategy with Zero Risk to Core Trading Functions

## Executive Summary

The learning system will be **completely isolated** from core trading operations through:

1. **Separate Git Branch**: `feature/learning-intelligence`
2. **API-Only Integration**: No direct imports or coupling
3. **Circuit Breaker Protection**: Learning failures cannot affect trading
4. **Separate Database**: Isolated schema with optional replication
5. **Gradual Rollout**: Shadow mode → A/B testing → Full deployment

## Phase 1: Foundation Setup (Week 1-2)

### Step 1: Create Isolated Branch
```bash
# Create and switch to learning branch
git checkout -b feature/learning-intelligence

# Create learning system directory structure
mkdir -p learning_engine/{core,intelligence,api,database,tests}
mkdir -p learning_engine/database/migrations
```

### Step 2: Database Isolation
```sql
-- Create separate learning database schema
CREATE SCHEMA learning;

-- Grant limited permissions
GRANT USAGE ON SCHEMA learning TO amc_learning_user;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA learning TO amc_learning_user;

-- Core learning tables (isolated from main schema)
CREATE TABLE learning.discovery_decisions (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    discovery_timestamp TIMESTAMP NOT NULL,
    discovery_features JSONB NOT NULL,
    discovery_score FLOAT NOT NULL,
    action_tag VARCHAR(20) NOT NULL,
    market_conditions JSONB,
    universe_size INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE learning.thesis_decisions (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    thesis_timestamp TIMESTAMP NOT NULL,
    recommendation VARCHAR(20) NOT NULL,
    confidence_score FLOAT NOT NULL,
    thesis_text TEXT,
    reasoning JSONB,
    ai_generated BOOLEAN DEFAULT FALSE,
    market_regime VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE learning.trade_outcomes (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    entry_timestamp TIMESTAMP NOT NULL,
    exit_timestamp TIMESTAMP,
    entry_price FLOAT NOT NULL,
    exit_price FLOAT,
    position_size_pct FLOAT,
    return_pct FLOAT,
    holding_period_days INTEGER,
    max_favorable_excursion FLOAT,
    max_adverse_excursion FLOAT,
    exit_reason VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Step 3: Circuit Breaker Implementation
```python
# learning_engine/core/circuit_breaker.py
class LearningCircuitBreaker:
    """Protects core systems from learning system failures"""

    def __init__(self):
        self.failure_threshold = 3
        self.timeout_seconds = 300  # 5 minutes
        self.failure_count = 0
        self.last_failure = None
        self.circuit_open = False

    async def call_learning_api(self, endpoint: str, data: Dict, timeout: float = 2.0):
        """Make learning API call with protection"""

        # Check if circuit is open
        if self.circuit_open:
            if self._should_try_again():
                self.circuit_open = False
                self.failure_count = 0
            else:
                return {"status": "circuit_open", "fallback": True}

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(f"http://localhost:8000/learning{endpoint}", json=data)

                if response.status_code == 200:
                    # Success - reset failure count
                    self.failure_count = 0
                    return response.json()
                else:
                    raise httpx.HTTPStatusError(f"HTTP {response.status_code}", request=None, response=response)

        except Exception as e:
            self._record_failure()
            logger.warning(f"Learning API call failed: {e}")
            return {"status": "error", "fallback": True, "error": str(e)}

    def _record_failure(self):
        """Record a failure and potentially open circuit"""
        self.failure_count += 1
        self.last_failure = datetime.now()

        if self.failure_count >= self.failure_threshold:
            self.circuit_open = True
            logger.warning(f"Learning circuit breaker OPEN after {self.failure_count} failures")

    def _should_try_again(self) -> bool:
        """Check if enough time has passed to try again"""
        if not self.last_failure:
            return True

        time_since_failure = (datetime.now() - self.last_failure).total_seconds()
        return time_since_failure >= self.timeout_seconds

# Global circuit breaker instance
learning_circuit_breaker = LearningCircuitBreaker()
```

## Phase 2: Data Collection Layer (Week 3-4)

### Step 1: Learning API Service (Isolated)
```python
# learning_engine/api/learning_routes.py
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Optional
import asyncio

router = APIRouter()

class DiscoveryData(BaseModel):
    timestamp: str
    universe_size: int
    candidates: list
    pipeline_stats: Dict
    scoring_distribution: Dict

class ThesisDecision(BaseModel):
    symbol: str
    recommendation: str
    confidence: float
    thesis: str
    ai_generated: bool = False

class TradeOutcome(BaseModel):
    symbol: str
    entry_price: float
    exit_price: Optional[float] = None
    return_pct: Optional[float] = None
    holding_period_days: Optional[int] = None

@router.post("/collect/discovery-data")
async def collect_discovery_data(data: DiscoveryData, background_tasks: BackgroundTasks):
    """Collect discovery data for learning (async processing)"""
    try:
        # Process in background to avoid blocking discovery system
        background_tasks.add_task(process_discovery_data, data)

        return {"status": "accepted", "message": "Discovery data queued for processing"}
    except Exception as e:
        logger.error(f"Error collecting discovery data: {e}")
        return {"status": "error", "message": str(e)}

@router.post("/collect/thesis-decision")
async def collect_thesis_decision(data: ThesisDecision, background_tasks: BackgroundTasks):
    """Collect thesis decisions for learning"""
    try:
        background_tasks.add_task(process_thesis_decision, data)

        return {"status": "accepted", "message": "Thesis decision queued for processing"}
    except Exception as e:
        logger.error(f"Error collecting thesis decision: {e}")
        return {"status": "error", "message": str(e)}

@router.post("/collect/trade-outcome")
async def collect_trade_outcome(data: TradeOutcome, background_tasks: BackgroundTasks):
    """Collect trade outcomes for learning"""
    try:
        background_tasks.add_task(process_trade_outcome, data)

        return {"status": "accepted", "message": "Trade outcome queued for processing"}
    except Exception as e:
        logger.error(f"Error collecting trade outcome: {e}")
        return {"status": "error", "message": str(e)}

async def process_discovery_data(data: DiscoveryData):
    """Process discovery data asynchronously"""
    try:
        # Store in learning database
        await learning_db.store_discovery_data(data.dict())

        # Trigger pattern analysis if enough new data
        await trigger_pattern_analysis_if_needed()

    except Exception as e:
        logger.error(f"Error processing discovery data: {e}")
```

### Step 2: Integration Points (Zero Risk)
```python
# backend/src/routes/discovery_unified.py (MODIFIED - NO IMPORTS)
async def run_enhanced_discovery(limit: int = 50, trace: bool = False):
    """Enhanced discovery with optional learning integration"""

    # Run discovery system as normal
    result = await run_discovery_job(limit)

    # Optional learning integration (fire-and-forget)
    if os.getenv("LEARNING_INTEGRATION_ENABLED", "false").lower() == "true":
        asyncio.create_task(send_discovery_to_learning(result))

    return result

async def send_discovery_to_learning(discovery_result: Dict):
    """Send discovery data to learning system (isolated)"""
    try:
        # Use circuit breaker for protection
        response = await learning_circuit_breaker.call_learning_api(
            "/collect/discovery-data",
            {
                "timestamp": datetime.now().isoformat(),
                "universe_size": discovery_result.get("universe_size", 0),
                "candidates": discovery_result.get("candidates", []),
                "pipeline_stats": discovery_result.get("pipeline_stats", {}),
                "scoring_distribution": calculate_score_distribution(discovery_result)
            },
            timeout=1.0  # Very short timeout
        )

        if response.get("status") == "accepted":
            logger.debug("Discovery data sent to learning system")
        else:
            logger.debug(f"Learning system unavailable: {response.get('status')}")

    except Exception as e:
        # Fail silently - never let learning issues affect discovery
        logger.debug(f"Learning integration failed (ignored): {e}")

def calculate_score_distribution(discovery_result: Dict) -> Dict:
    """Calculate score distribution for learning analysis"""
    candidates = discovery_result.get("candidates", [])

    if not candidates:
        return {"error": "no_candidates"}

    scores = [c.get("score", 0) for c in candidates]

    return {
        "min_score": min(scores),
        "max_score": max(scores),
        "avg_score": sum(scores) / len(scores),
        "score_variance": np.var(scores),
        "trade_ready_count": len([c for c in candidates if c.get("action_tag") == "trade_ready"]),
        "monitor_count": len([c for c in candidates if c.get("action_tag") == "monitor"])
    }
```

## Phase 3: Intelligence Generation (Week 5-6)

### Step 1: Pattern Analysis Engine
```python
# learning_engine/core/pattern_analyzer.py
class PatternAnalyzer:
    """Analyzes historical patterns to identify successful strategies"""

    async def analyze_discovery_effectiveness(self, days_back: int = 90) -> Dict:
        """Analyze which discovery patterns lead to successful trades"""

        # Get discovery data
        discoveries = await self.learning_db.get_discoveries(days_back=days_back)

        # Get corresponding outcomes
        outcomes = await self.learning_db.get_outcomes_for_discoveries(discoveries)

        # Feature correlation analysis
        feature_correlations = {}
        for feature in ["volume_momentum", "squeeze", "catalyst", "sentiment", "options", "technical"]:
            correlations = self.calculate_feature_outcome_correlation(feature, discoveries, outcomes)
            feature_correlations[feature] = correlations

        # Success pattern identification
        successful_patterns = self.identify_successful_patterns(discoveries, outcomes)

        # Failure pattern identification
        failure_patterns = self.identify_failure_patterns(discoveries, outcomes)

        return {
            "analysis_period_days": days_back,
            "total_discoveries": len(discoveries),
            "total_outcomes": len(outcomes),
            "feature_correlations": feature_correlations,
            "successful_patterns": successful_patterns,
            "failure_patterns": failure_patterns,
            "overall_success_rate": self.calculate_overall_success_rate(outcomes),
            "recommendations": self.generate_discovery_recommendations(feature_correlations)
        }

    def calculate_feature_outcome_correlation(self, feature: str, discoveries: list, outcomes: list) -> Dict:
        """Calculate correlation between feature values and trade outcomes"""

        # Match discoveries to outcomes
        feature_outcome_pairs = []
        for discovery in discoveries:
            matching_outcomes = [o for o in outcomes if o["symbol"] == discovery["symbol"]]
            if matching_outcomes:
                feature_value = discovery["discovery_features"].get(feature, 0)
                avg_return = np.mean([o["return_pct"] for o in matching_outcomes if o["return_pct"]])
                feature_outcome_pairs.append((feature_value, avg_return))

        if len(feature_outcome_pairs) < 10:  # Need minimum data
            return {"error": "insufficient_data", "pairs": len(feature_outcome_pairs)}

        features, returns = zip(*feature_outcome_pairs)
        correlation = np.corrcoef(features, returns)[0, 1]

        # Optimal threshold analysis
        optimal_threshold = self.find_optimal_threshold(feature_outcome_pairs)

        return {
            "correlation": correlation,
            "sample_size": len(feature_outcome_pairs),
            "optimal_threshold": optimal_threshold,
            "current_weight": self.get_current_feature_weight(feature),
            "suggested_weight": self.calculate_optimal_weight(correlation, optimal_threshold)
        }
```

### Step 2: Adaptive Parameter Engine
```python
# learning_engine/intelligence/adaptive_parameters.py
class AdaptiveParametersEngine:
    """Generates optimized parameters based on learning insights"""

    async def generate_discovery_parameters(self, market_regime: str = None) -> Dict:
        """Generate discovery parameters optimized by learning"""

        # Get current pattern analysis
        pattern_analysis = await self.pattern_analyzer.analyze_discovery_effectiveness()

        if pattern_analysis.get("error"):
            return self.get_conservative_fallback_parameters()

        # Calculate weight optimizations
        current_weights = self.get_current_discovery_weights()
        optimized_weights = {}

        for feature, analysis in pattern_analysis["feature_correlations"].items():
            if "suggested_weight" in analysis:
                current_weight = current_weights.get(feature, 0.15)
                suggested_weight = analysis["suggested_weight"]

                # Gradual adjustment (max 5% change per day)
                max_change = 0.05
                weight_change = min(max_change, abs(suggested_weight - current_weight))
                direction = 1 if suggested_weight > current_weight else -1

                optimized_weights[feature] = current_weight + (weight_change * direction)

        # Normalize weights to sum to 1.0
        total_weight = sum(optimized_weights.values())
        if total_weight > 0:
            optimized_weights = {k: v/total_weight for k, v in optimized_weights.items()}

        # Market regime adjustments
        if market_regime:
            regime_adjustments = self.get_market_regime_adjustments(market_regime)
            for feature, adjustment in regime_adjustments.items():
                if feature in optimized_weights:
                    optimized_weights[feature] *= adjustment

        return {
            "optimized_weights": optimized_weights,
            "confidence": pattern_analysis["overall_success_rate"],
            "expected_improvement": self.calculate_expected_improvement(current_weights, optimized_weights),
            "market_regime": market_regime or "normal",
            "sample_size": pattern_analysis["total_outcomes"],
            "last_updated": datetime.now().isoformat()
        }

    def get_conservative_fallback_parameters(self) -> Dict:
        """Return conservative parameters when learning data insufficient"""
        return {
            "optimized_weights": {
                "volume_momentum": 0.25,
                "squeeze": 0.20,
                "catalyst": 0.15,
                "sentiment": 0.15,
                "options": 0.12,
                "technical": 0.13
            },
            "confidence": 0.5,
            "expected_improvement": 0.0,
            "market_regime": "normal",
            "sample_size": 0,
            "fallback": True,
            "reason": "insufficient_learning_data"
        }
```

## Phase 4: Safe Integration (Week 7-8)

### Step 1: Discovery System Enhancement (Optional)
```python
# backend/src/routes/discovery_unified.py (SAFE ADDITION)
@router.get("/enhanced-with-learning")
async def enhanced_discovery_with_learning(limit: int = Query(50, le=500)):
    """Discovery enhanced with learning intelligence (optional)"""

    try:
        # Get learning-optimized parameters
        learning_params = await get_learning_optimized_parameters()

        if learning_params.get("success") and not learning_params.get("fallback"):
            # Use learning-optimized discovery
            result = await run_discovery_with_params(limit, learning_params["data"])
            result["enhanced_by_learning"] = True
            result["learning_confidence"] = learning_params["data"]["confidence"]
        else:
            # Fallback to standard discovery
            result = await run_discovery_job(limit)
            result["enhanced_by_learning"] = False
            result["fallback_reason"] = learning_params.get("reason", "learning_unavailable")

        return result

    except Exception as e:
        # Always fallback to standard discovery on any error
        logger.warning(f"Learning-enhanced discovery failed, using standard: {e}")
        result = await run_discovery_job(limit)
        result["enhanced_by_learning"] = False
        result["error"] = str(e)
        return result

async def get_learning_optimized_parameters() -> Dict:
    """Get discovery parameters optimized by learning system"""

    try:
        response = await learning_circuit_breaker.call_learning_api(
            "/intelligence/discovery-parameters",
            {},
            timeout=2.0
        )

        if response.get("status") == "circuit_open":
            return {"success": False, "fallback": True, "reason": "circuit_breaker_open"}

        if "optimized_weights" in response:
            return {"success": True, "data": response}
        else:
            return {"success": False, "fallback": True, "reason": "invalid_response"}

    except Exception as e:
        return {"success": False, "fallback": True, "reason": str(e)}
```

### Step 2: Intelligence Delivery API
```python
# learning_engine/api/intelligence_provider.py
@router.get("/intelligence/discovery-parameters")
async def get_discovery_parameters():
    """Provide discovery parameters optimized by learning"""

    try:
        current_regime = await market_regime_detector.get_current_regime()

        optimized_params = await adaptive_params_engine.generate_discovery_parameters(current_regime)

        return {
            "status": "success",
            "optimized_weights": optimized_params["optimized_weights"],
            "confidence": optimized_params["confidence"],
            "expected_improvement": optimized_params["expected_improvement"],
            "market_regime": optimized_params["market_regime"],
            "sample_size": optimized_params["sample_size"],
            "last_updated": optimized_params["last_updated"]
        }

    except Exception as e:
        logger.error(f"Error generating discovery parameters: {e}")
        return {
            "status": "error",
            "error": str(e),
            "fallback_recommendation": "use_default_parameters"
        }

@router.get("/intelligence/market-insights")
async def get_market_insights():
    """Provide current market insights from learning analysis"""

    try:
        insights = await intelligence_engine.generate_market_insights()

        return {
            "status": "success",
            "market_regime": insights["current_regime"],
            "confidence_adjustments": insights["confidence_recommendations"],
            "pattern_alerts": insights["pattern_alerts"],
            "risk_warnings": insights["risk_warnings"],
            "performance_summary": insights["recent_performance"]
        }

    except Exception as e:
        logger.error(f"Error generating market insights: {e}")
        return {
            "status": "error",
            "error": str(e)
        }
```

## Phase 5: Gradual Rollout (Week 9-10)

### Step 1: Shadow Mode Testing
```python
# learning_engine/testing/shadow_mode.py
class ShadowModeTester:
    """Test learning system in shadow mode (collect data, don't affect trading)"""

    async def run_shadow_mode_test(self, duration_days: int = 7):
        """Run learning system in shadow mode for testing"""

        logger.info(f"Starting shadow mode test for {duration_days} days")

        # Enable data collection but disable parameter application
        await self.enable_shadow_mode()

        test_results = {
            "start_time": datetime.now(),
            "data_collection_events": 0,
            "intelligence_generations": 0,
            "errors": [],
            "performance_metrics": {}
        }

        # Monitor for specified duration
        end_time = datetime.now() + timedelta(days=duration_days)
        while datetime.now() < end_time:
            await asyncio.sleep(3600)  # Check hourly

            # Collect metrics
            daily_metrics = await self.collect_shadow_metrics()
            test_results["performance_metrics"][datetime.now().date().isoformat()] = daily_metrics

            # Check for errors
            recent_errors = await self.get_recent_errors()
            test_results["errors"].extend(recent_errors)

        # Generate shadow mode report
        shadow_report = await self.generate_shadow_report(test_results)

        logger.info(f"Shadow mode test completed: {shadow_report['summary']}")

        return shadow_report

    async def enable_shadow_mode(self):
        """Enable shadow mode - collect data but don't affect trading"""
        await self.set_config("LEARNING_MODE", "shadow")
        await self.set_config("LEARNING_APPLY_PARAMETERS", "false")
        await self.set_config("LEARNING_DATA_COLLECTION", "true")
```

### Step 2: A/B Testing Framework
```python
# learning_engine/testing/ab_testing.py
class LearningABTester:
    """A/B test learning system against baseline"""

    async def run_ab_test(self, test_percentage: float = 0.1, duration_days: int = 14):
        """Run A/B test with learning system on small percentage of traffic"""

        logger.info(f"Starting A/B test: {test_percentage*100}% traffic for {duration_days} days")

        # Configure A/B test
        await self.configure_ab_test(test_percentage)

        test_results = {
            "test_group_performance": [],
            "control_group_performance": [],
            "statistical_significance": None,
            "recommendation": "continue_testing"
        }

        # Run test for duration
        end_time = datetime.now() + timedelta(days=duration_days)
        while datetime.now() < end_time:
            await asyncio.sleep(86400)  # Check daily

            # Collect daily results
            daily_results = await self.collect_daily_ab_results()
            test_results["test_group_performance"].append(daily_results["test_group"])
            test_results["control_group_performance"].append(daily_results["control_group"])

            # Check statistical significance
            significance = await self.check_statistical_significance(test_results)
            test_results["statistical_significance"] = significance

            # Early stopping if clear winner
            if significance["p_value"] < 0.01 and significance["effect_size"] > 0.1:
                logger.info("Early stopping: statistically significant improvement detected")
                break

        # Generate final A/B test report
        final_report = await self.generate_ab_report(test_results)

        return final_report

    async def configure_ab_test(self, test_percentage: float):
        """Configure A/B test with specified traffic percentage"""

        # Set up traffic splitting
        await self.set_config("LEARNING_AB_TEST_ENABLED", "true")
        await self.set_config("LEARNING_AB_TEST_PERCENTAGE", str(test_percentage))

        # Randomization seed for consistent splitting
        import random
        random.seed(42)  # Consistent randomization
```

### Step 3: Production Deployment
```python
# learning_engine/deployment/production_deploy.py
class ProductionDeployer:
    """Handle safe production deployment of learning system"""

    async def deploy_to_production(self):
        """Deploy learning system to production with safety checks"""

        # Pre-deployment checks
        safety_checks = await self.run_safety_checks()

        if not safety_checks["all_passed"]:
            raise Exception(f"Safety checks failed: {safety_checks['failures']}")

        # Gradual rollout
        await self.gradual_rollout()

        # Post-deployment monitoring
        await self.enable_production_monitoring()

        logger.info("Learning system successfully deployed to production")

    async def run_safety_checks(self) -> Dict:
        """Run comprehensive safety checks before deployment"""

        checks = {
            "database_isolation": await self.check_database_isolation(),
            "circuit_breaker_functional": await self.test_circuit_breaker(),
            "api_response_times": await self.check_api_performance(),
            "fallback_mechanisms": await self.test_fallback_mechanisms(),
            "error_handling": await self.test_error_handling(),
            "data_integrity": await self.check_data_integrity()
        }

        all_passed = all(checks.values())
        failures = [check for check, passed in checks.items() if not passed]

        return {
            "all_passed": all_passed,
            "individual_checks": checks,
            "failures": failures
        }

    async def gradual_rollout(self):
        """Gradually increase learning system usage"""

        rollout_stages = [
            {"percentage": 5, "duration_hours": 24},
            {"percentage": 25, "duration_hours": 48},
            {"percentage": 50, "duration_hours": 72},
            {"percentage": 100, "duration_hours": None}
        ]

        for stage in rollout_stages:
            logger.info(f"Rolling out to {stage['percentage']}% of traffic")

            await self.set_config("LEARNING_ROLLOUT_PERCENTAGE", str(stage["percentage"]))

            if stage["duration_hours"]:
                # Monitor for specified duration
                await self.monitor_rollout_stage(stage["duration_hours"])

                # Check for issues
                issues = await self.check_for_rollout_issues()
                if issues["critical_issues"]:
                    await self.rollback_deployment()
                    raise Exception(f"Critical issues detected: {issues['critical_issues']}")
```

## Risk Mitigation & Safety Measures

### 1. Complete Isolation Checklist
- [ ] No direct imports between systems
- [ ] Separate database schema with isolated permissions
- [ ] API-only communication with circuit breakers
- [ ] Separate Git branch until proven stable
- [ ] Independent deployment pipeline
- [ ] Separate monitoring and alerting

### 2. Failure Modes & Protections
- [ ] Learning API timeouts (1-2 seconds max)
- [ ] Circuit breaker opens after 3 failures
- [ ] Graceful degradation to default parameters
- [ ] Learning failures logged but ignored
- [ ] Core trading systems unaffected by learning issues

### 3. Data Protection
- [ ] Learning database isolated from trading data
- [ ] No PII or sensitive trading data in learning system
- [ ] Backups and recovery procedures separate
- [ ] Access controls and audit logging

### 4. Performance Safeguards
- [ ] Learning calls are async/background only
- [ ] Short timeouts prevent blocking
- [ ] Learning intelligence cached for performance
- [ ] Circuit breaker prevents cascade failures

This separation plan ensures the learning system can evolve and improve trading performance while maintaining **zero risk** to core trading operations.