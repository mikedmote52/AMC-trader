# AMC-TRADER Learning System Data Flow & Feedback Loops

## Current System Analysis

### Existing Data Flow (Fragmented)
```
Discovery System → (direct import) → Learning Routes
Thesis Generator → (direct import) → Learning System
Portfolio Changes → (manual) → No systematic tracking
Trade Outcomes → (none) → No outcome collection
```

**Problems**:
- No systematic data collection
- Direct imports create coupling
- No outcome tracking
- Learning insights not fed back to discovery

## Proposed Complete Data Flow

### 1. Discovery-to-Learning Pipeline
```
AlphaStack Discovery Engine
         ↓ (API call - isolated)
Learning Data Collector API
         ↓
Discovery Decision Database
         ↓ (batch processing)
Pattern Analysis Engine
         ↓
Adaptive Parameter Generator
         ↓ (API response)
Discovery Parameter Updates
```

**Data Points Captured**:
- Full discovery feature vectors (all 6 scoring components)
- Market conditions at discovery time
- Score distributions and rankings
- Action tags assigned (trade_ready/monitor/watchlist)
- Universe size and filtering statistics

### 2. Thesis-to-Learning Pipeline
```
Thesis Generator
         ↓ (API call - isolated)
Thesis Decision Collector
         ↓
Thesis Accuracy Database
         ↓ (daily evaluation)
Thesis Validation Engine
         ↓
Confidence Calibration Updates
         ↓ (API response)
Thesis Confidence Adjustments
```

**Data Points Captured**:
- Thesis recommendations (BUY/SELL/HOLD)
- Confidence scores assigned
- Reasoning provided
- AI vs rule-based thesis source
- Market regime at thesis time

### 3. Trade-to-Learning Pipeline
```
Portfolio Manager / Trade Execution
         ↓ (webhook/API call)
Trade Outcome Collector
         ↓
Performance Attribution Database
         ↓ (continuous analysis)
Performance Attribution Engine
         ↓
Strategy Optimization Updates
         ↓ (API response)
Risk Management Adjustments
```

**Data Points Captured**:
- Entry/exit prices and timing
- Position sizes and duration
- Actual returns (1d, 7d, 30d)
- Maximum favorable/adverse excursions
- Exit reasons (stop loss/profit target/manual)

## 2. Complete Feedback Loop Architecture

### Learning Data Collection Layer
```python
# learning_engine/api/data_collector.py
class LearningDataCollector:
    """Isolated data collection for all learning inputs"""

    async def collect_discovery_data(self, discovery_result: Dict):
        """Collect discovery results for pattern analysis"""
        await self.db.store_discovery_data({
            "timestamp": datetime.now(),
            "universe_size": discovery_result["universe_size"],
            "candidates": discovery_result["candidates"],
            "filtering_stats": discovery_result["pipeline_stats"],
            "market_conditions": await self.get_market_conditions(),
            "scoring_distribution": self.calculate_score_distribution(discovery_result)
        })

    async def collect_thesis_decision(self, thesis_result: Dict):
        """Collect thesis decisions for accuracy tracking"""
        await self.db.store_thesis_decision({
            "symbol": thesis_result["symbol"],
            "recommendation": thesis_result["recommendation"],
            "confidence": thesis_result["confidence"],
            "reasoning": thesis_result["thesis"],
            "market_regime": await self.detect_market_regime(),
            "source": thesis_result.get("ai_generated", False)
        })

    async def collect_trade_outcome(self, trade_result: Dict):
        """Collect actual trade outcomes for performance attribution"""
        await self.db.store_trade_outcome({
            "symbol": trade_result["symbol"],
            "entry_price": trade_result["entry_price"],
            "exit_price": trade_result.get("exit_price"),
            "position_size": trade_result["position_size"],
            "returns": await self.calculate_returns(trade_result),
            "holding_period": trade_result.get("holding_period"),
            "exit_reason": trade_result.get("exit_reason")
        })
```

### Pattern Analysis Layer
```python
# learning_engine/core/pattern_analyzer.py
class PatternAnalyzer:
    """Analyzes patterns to identify what works"""

    async def analyze_discovery_effectiveness(self) -> Dict:
        """Analyze which discovery patterns lead to successful trades"""

        # Get all discoveries from last 90 days
        discoveries = await self.db.get_discoveries(days_back=90)

        # Get corresponding trade outcomes
        outcomes = await self.db.get_trade_outcomes_for_discoveries(discoveries)

        # Analyze feature importance
        feature_analysis = {}
        for feature in ["volume_momentum", "squeeze", "catalyst", "sentiment", "options", "technical"]:
            feature_analysis[feature] = {
                "correlation_with_success": self.calculate_correlation(feature, outcomes),
                "optimal_threshold": self.find_optimal_threshold(feature, outcomes),
                "current_weight": self.get_current_weight(feature),
                "suggested_weight": self.calculate_optimal_weight(feature, outcomes)
            }

        return {
            "feature_analysis": feature_analysis,
            "overall_discovery_success_rate": self.calculate_success_rate(outcomes),
            "market_regime_performance": self.analyze_by_market_regime(outcomes),
            "recommendations": self.generate_optimization_recommendations(feature_analysis)
        }

    async def analyze_thesis_accuracy(self) -> Dict:
        """Analyze thesis prediction accuracy over time"""

        theses = await self.db.get_thesis_decisions(days_back=90)

        accuracy_analysis = {}
        for thesis in theses:
            actual_outcome = await self.get_actual_outcome(thesis["symbol"], thesis["timestamp"])
            accuracy_score = self.calculate_accuracy(thesis["recommendation"], actual_outcome)

            accuracy_analysis[thesis["id"]] = {
                "predicted": thesis["recommendation"],
                "actual": actual_outcome["direction"],
                "accuracy": accuracy_score,
                "confidence_was": thesis["confidence"],
                "confidence_should_be": self.calculate_calibrated_confidence(accuracy_score)
            }

        return {
            "overall_accuracy": np.mean([a["accuracy"] for a in accuracy_analysis.values()]),
            "confidence_calibration": self.analyze_confidence_calibration(accuracy_analysis),
            "ai_vs_rules_accuracy": self.compare_ai_vs_rules(accuracy_analysis),
            "recommendations": self.generate_thesis_improvements(accuracy_analysis)
        }
```

### Intelligence Generation Layer
```python
# learning_engine/intelligence/adaptive_parameters.py
class AdaptiveParametersEngine:
    """Generates optimized parameters based on learning"""

    async def generate_discovery_parameters(self, market_regime: str = None) -> Dict:
        """Generate optimized discovery parameters based on historical performance"""

        # Get pattern analysis results
        pattern_analysis = await self.pattern_analyzer.analyze_discovery_effectiveness()

        # Current parameters
        current_params = await self.get_current_discovery_parameters()

        # Calculate optimizations
        optimized_params = {}
        for component, analysis in pattern_analysis["feature_analysis"].items():
            current_weight = analysis["current_weight"]
            suggested_weight = analysis["suggested_weight"]

            # Gradual adjustment (max 10% change per day)
            max_change = 0.10
            weight_change = min(max_change, abs(suggested_weight - current_weight))
            direction = 1 if suggested_weight > current_weight else -1

            optimized_params[f"{component}_weight"] = current_weight + (weight_change * direction)

        # Market regime adjustments
        if market_regime:
            regime_adjustments = await self.get_regime_adjustments(market_regime)
            for param, adjustment in regime_adjustments.items():
                if param in optimized_params:
                    optimized_params[param] *= adjustment

        return {
            "optimized_parameters": optimized_params,
            "confidence": pattern_analysis["overall_discovery_success_rate"],
            "expected_improvement": self.calculate_expected_improvement(current_params, optimized_params),
            "market_regime": market_regime,
            "last_updated": datetime.now().isoformat()
        }

    async def generate_confidence_adjustments(self) -> Dict:
        """Generate confidence score adjustments based on accuracy analysis"""

        accuracy_analysis = await self.pattern_analyzer.analyze_thesis_accuracy()

        confidence_adjustments = {}

        # Overall calibration adjustment
        overall_accuracy = accuracy_analysis["overall_accuracy"]
        overall_confidence = accuracy_analysis["confidence_calibration"]["average_confidence"]

        global_adjustment = overall_accuracy / overall_confidence if overall_confidence > 0 else 1.0

        # Per-recommendation-type adjustments
        for rec_type in ["BUY_MORE", "HOLD", "TRIM", "LIQUIDATE"]:
            type_accuracy = accuracy_analysis["confidence_calibration"].get(f"{rec_type}_accuracy", 0.5)
            type_confidence = accuracy_analysis["confidence_calibration"].get(f"{rec_type}_confidence", 0.5)

            type_adjustment = type_accuracy / type_confidence if type_confidence > 0 else 1.0
            confidence_adjustments[rec_type] = min(2.0, max(0.5, type_adjustment))

        return {
            "global_confidence_multiplier": min(2.0, max(0.5, global_adjustment)),
            "per_recommendation_adjustments": confidence_adjustments,
            "calibration_quality": accuracy_analysis["confidence_calibration"]["calibration_score"],
            "recommendations": self.generate_confidence_recommendations(accuracy_analysis)
        }
```

### Self-Correction Implementation
```python
# learning_engine/core/self_corrector.py
class SelfCorrector:
    """Implements self-correction based on performance feedback"""

    async def daily_correction_cycle(self):
        """Run daily self-correction cycle"""

        # 1. Collect latest outcome data
        await self.collect_overnight_outcomes()

        # 2. Update pattern performance metrics
        await self.update_pattern_performance()

        # 3. Recalibrate confidence scores
        confidence_adjustments = await self.adaptive_params.generate_confidence_adjustments()
        await self.apply_confidence_adjustments(confidence_adjustments)

        # 4. Update discovery parameters
        discovery_params = await self.adaptive_params.generate_discovery_parameters()
        await self.update_discovery_parameters(discovery_params)

        # 5. Generate daily intelligence report
        intelligence_report = await self.generate_intelligence_report()
        await self.publish_intelligence_report(intelligence_report)

    async def weekly_deep_correction(self):
        """Run weekly comprehensive correction cycle"""

        # 1. Deep pattern analysis
        new_patterns = await self.discover_new_patterns()

        # 2. Feature importance recalculation
        feature_importance = await self.recalculate_feature_importance()

        # 3. Market regime analysis
        regime_changes = await self.detect_regime_changes()

        # 4. Model retraining
        await self.retrain_prediction_models()

        # 5. Strategy optimization
        strategy_recommendations = await self.optimize_trading_strategies()

        # 6. Publish weekly intelligence
        await self.publish_weekly_intelligence({
            "new_patterns": new_patterns,
            "feature_importance": feature_importance,
            "regime_changes": regime_changes,
            "strategy_recommendations": strategy_recommendations
        })

    async def detect_systematic_failures(self):
        """Detect and correct systematic failure modes"""

        # Get recent poor performance patterns
        failures = await self.db.get_failed_trades(days_back=30)

        # Group by failure type
        failure_patterns = self.group_failures_by_pattern(failures)

        corrections = []
        for pattern, instances in failure_patterns.items():
            if len(instances) >= 3:  # Systematic if 3+ occurrences
                correction = await self.generate_pattern_correction(pattern, instances)
                corrections.append(correction)

                # Automatically apply critical corrections
                if correction["severity"] == "critical":
                    await self.apply_correction_immediately(correction)

        return corrections
```

## 3. API Integration Points (Isolated)

### Discovery System Integration
```python
# In discovery_unified.py (NO DIRECT IMPORTS)
async def run_enhanced_discovery(limit: int = 50):
    """Enhanced discovery with learning integration"""

    # Run discovery as normal
    result = await run_discovery_job(limit)

    # Send to learning system asynchronously (fire-and-forget)
    asyncio.create_task(send_discovery_data_to_learning(result))

    return result

async def send_discovery_data_to_learning(discovery_result: Dict):
    """Send discovery data to learning system via API"""
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                "http://localhost:8000/learning/collect/discovery-data",
                json=discovery_result,
                timeout=5.0  # Short timeout to prevent blocking
            )
    except Exception as e:
        logger.warning(f"Failed to send discovery data to learning: {e}")
        # Fail silently - don't let learning issues affect discovery
```

### Thesis System Integration
```python
# In thesis.py (NO DIRECT IMPORTS)
async def generate_entry_thesis(symbol: str, discovery_data: Dict):
    """Generate thesis with learning integration"""

    # Generate thesis as normal
    thesis_result = await thesis_gen.generate_entry_thesis_for_discovery(symbol, discovery_data)

    # Send to learning system
    asyncio.create_task(send_thesis_data_to_learning(symbol, thesis_result))

    return thesis_result

async def send_thesis_data_to_learning(symbol: str, thesis_result: Dict):
    """Send thesis data to learning system"""
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                "http://localhost:8000/learning/collect/thesis-decision",
                json={"symbol": symbol, "thesis": thesis_result},
                timeout=5.0
            )
    except Exception as e:
        logger.warning(f"Failed to send thesis data to learning: {e}")
```

### Portfolio Manager Integration
```python
# New: portfolio_tracker.py
class PortfolioTracker:
    """Track portfolio changes and send to learning system"""

    async def track_position_change(self, symbol: str, change_type: str, change_data: Dict):
        """Track any position change and send to learning"""

        trade_data = {
            "symbol": symbol,
            "change_type": change_type,  # OPEN/CLOSE/MODIFY
            "timestamp": datetime.now().isoformat(),
            "change_data": change_data
        }

        # Send to learning system
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    "http://localhost:8000/learning/collect/trade-outcome",
                    json=trade_data,
                    timeout=5.0
                )
        except Exception as e:
            logger.warning(f"Failed to send trade data to learning: {e}")
```

## 4. Learning Intelligence Delivery

### Real-time Intelligence API
```python
# learning_engine/api/intelligence_provider.py
@router.get("/learning/intelligence/current-recommendations")
async def get_current_recommendations():
    """Get current learning-based recommendations"""

    intelligence = await intelligence_engine.generate_current_intelligence()

    return {
        "discovery_parameter_adjustments": intelligence["discovery_params"],
        "confidence_calibration": intelligence["confidence_adjustments"],
        "market_regime_insights": intelligence["market_regime"],
        "pattern_alerts": intelligence["pattern_alerts"],
        "risk_warnings": intelligence["risk_warnings"],
        "performance_attribution": intelligence["performance_insights"]
    }

@router.get("/learning/intelligence/adaptive-discovery-params")
async def get_adaptive_discovery_params():
    """Get discovery parameters optimized by learning"""

    current_regime = await market_regime_detector.get_current_regime()

    optimized_params = await adaptive_params.generate_discovery_parameters(current_regime)

    return {
        "success": True,
        "data": optimized_params,
        "applies_to_regime": current_regime,
        "confidence": optimized_params["confidence"],
        "expected_improvement": optimized_params["expected_improvement"]
    }
```

### Discovery System Consumption
```python
# In discovery system - consume learning intelligence
async def get_learning_enhanced_parameters():
    """Get discovery parameters enhanced by learning system"""

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "http://localhost:8000/learning/intelligence/adaptive-discovery-params",
                timeout=2.0  # Fast timeout for real-time use
            )

            if response.status_code == 200:
                learning_data = response.json()
                if learning_data["success"]:
                    return learning_data["data"]["optimized_parameters"]
    except Exception as e:
        logger.warning(f"Failed to get learning parameters: {e}")

    # Fallback to default parameters
    return get_default_discovery_parameters()
```

## 5. Data Flow Monitoring

### Health Monitoring Dashboard
```python
class LearningDataFlowMonitor:
    """Monitor the health of learning data flows"""

    async def get_data_flow_health(self) -> Dict:
        """Get comprehensive data flow health metrics"""

        return {
            "discovery_data_flow": {
                "collections_today": await self.count_discovery_collections_today(),
                "avg_latency_ms": await self.get_avg_discovery_latency(),
                "success_rate_24h": await self.get_discovery_success_rate()
            },
            "thesis_data_flow": {
                "collections_today": await self.count_thesis_collections_today(),
                "avg_latency_ms": await self.get_avg_thesis_latency(),
                "success_rate_24h": await self.get_thesis_success_rate()
            },
            "trade_data_flow": {
                "collections_today": await self.count_trade_collections_today(),
                "avg_latency_ms": await self.get_avg_trade_latency(),
                "success_rate_24h": await self.get_trade_success_rate()
            },
            "intelligence_delivery": {
                "requests_today": await self.count_intelligence_requests_today(),
                "avg_response_time_ms": await self.get_avg_intelligence_response_time(),
                "cache_hit_rate": await self.get_intelligence_cache_hit_rate()
            },
            "learning_effectiveness": {
                "patterns_discovered_this_week": await self.count_new_patterns(),
                "parameter_adjustments_this_week": await self.count_parameter_adjustments(),
                "accuracy_improvement_this_month": await self.calculate_accuracy_improvement()
            }
        }
```

This comprehensive data flow architecture ensures that every decision, outcome, and insight flows through the learning system while maintaining complete isolation and safety for the core trading operations.