#!/usr/bin/env python3
"""
Enhanced Learning Engine for AMC-TRADER
Mission: Restore explosive growth edge through adaptive pattern learning

Learning System Architecture:
1. Discovery Pattern Learning - Learn what patterns produce explosive winners
2. Thesis Accuracy Learning - Improve recommendation accuracy over time  
3. Market Regime Learning - Adapt to changing market conditions
4. Performance Attribution - Link discoveries to actual outcomes
5. Pattern Memory - Store and recall successful explosive patterns
"""

import os
import json
import asyncio
import asyncpg
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import statistics as stats
from ..shared.database import get_db_pool

@dataclass
class ExplosivePattern:
    """Historical explosive pattern with performance data"""
    symbol: str
    discovery_date: datetime
    pattern_features: Dict[str, float]
    outcome_return_pct: Optional[float] = None
    days_to_peak: Optional[int] = None
    max_drawdown: Optional[float] = None
    pattern_confidence: float = 0.5
    market_regime: str = "unknown"
    
class LearningEngine:
    """
    Advanced learning system that adapts discovery algorithms and thesis generation
    based on historical performance patterns and market conditions.
    
    Core Learning Loops:
    1. Discovery Pattern Learning - What signals preceded +324% winners?
    2. Market Condition Adaptation - How do winning patterns change with market cycles?
    3. Thesis Validation - Track thesis accuracy vs actual performance  
    4. Risk Factor Evolution - Learn new risk indicators from failures
    5. Performance Attribution - What factors drive explosive vs poor performance?
    """
    
    def __init__(self):
        self.explosive_patterns = deque(maxlen=1000)  # Store last 1000 patterns
        self.market_regimes = {}
        self.pattern_memory = {}
        self.thesis_accuracy_tracker = {}
        
    async def initialize_learning_database(self):
        """Initialize enhanced learning system database tables"""
        pool = await get_db_pool()
        if not pool:
            return False
            
        async with pool.acquire() as conn:
            # Enhanced explosive patterns table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS explosive_patterns (
                    id SERIAL PRIMARY KEY,
                    symbol VARCHAR(10) NOT NULL,
                    discovery_date TIMESTAMP NOT NULL,
                    pattern_features JSONB NOT NULL,
                    vigl_score FLOAT NOT NULL,
                    volume_spike_ratio FLOAT NOT NULL,
                    price_momentum_1d FLOAT NOT NULL,
                    price_momentum_5d FLOAT NOT NULL,
                    atr_pct FLOAT NOT NULL,
                    compression_pct FLOAT NOT NULL,
                    wolf_risk_score FLOAT NOT NULL,
                    market_regime VARCHAR(20),
                    outcome_return_pct FLOAT,
                    peak_return_pct FLOAT,
                    days_to_peak INTEGER,
                    max_drawdown FLOAT,
                    pattern_success BOOLEAN,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)
            
            # Market regime tracking table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS market_regimes (
                    id SERIAL PRIMARY KEY,
                    regime_date DATE NOT NULL UNIQUE,
                    regime_type VARCHAR(20) NOT NULL,
                    vix_level FLOAT,
                    market_trend VARCHAR(20),
                    explosive_success_rate FLOAT,
                    avg_pattern_return FLOAT,
                    pattern_confidence_adjustment FLOAT,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)
            
            # Thesis accuracy tracking table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS thesis_accuracy (
                    id SERIAL PRIMARY KEY,
                    symbol VARCHAR(10) NOT NULL,
                    thesis_date TIMESTAMP NOT NULL,
                    recommendation VARCHAR(20) NOT NULL,
                    confidence_score FLOAT NOT NULL,
                    predicted_direction VARCHAR(10),
                    actual_return_1d FLOAT,
                    actual_return_7d FLOAT,
                    actual_return_30d FLOAT,
                    accuracy_score FLOAT,
                    market_regime VARCHAR(20),
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)
            
            # Discovery performance tracking
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS discovery_performance (
                    id SERIAL PRIMARY KEY,
                    discovery_date TIMESTAMP NOT NULL,
                    discovery_parameters JSONB NOT NULL,
                    symbols_discovered INTEGER NOT NULL,
                    avg_7d_return FLOAT,
                    avg_30d_return FLOAT,
                    success_rate FLOAT,
                    explosive_winners INTEGER DEFAULT 0,
                    total_tracked INTEGER DEFAULT 0,
                    parameter_effectiveness FLOAT,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)
            
            # Pattern feature importance tracking
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS pattern_features (
                    id SERIAL PRIMARY KEY,
                    feature_name VARCHAR(50) NOT NULL,
                    feature_weight FLOAT NOT NULL,
                    success_correlation FLOAT NOT NULL,
                    market_regime VARCHAR(20),
                    last_updated TIMESTAMP DEFAULT NOW(),
                    UNIQUE(feature_name, market_regime)
                );
            """)
            
            # Create indexes for performance
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_explosive_patterns_symbol ON explosive_patterns(symbol);",
                "CREATE INDEX IF NOT EXISTS idx_explosive_patterns_date ON explosive_patterns(discovery_date);",
                "CREATE INDEX IF NOT EXISTS idx_explosive_patterns_success ON explosive_patterns(pattern_success);",
                "CREATE INDEX IF NOT EXISTS idx_market_regimes_date ON market_regimes(regime_date);",
                "CREATE INDEX IF NOT EXISTS idx_thesis_accuracy_symbol ON thesis_accuracy(symbol);",
                "CREATE INDEX IF NOT EXISTS idx_discovery_performance_date ON discovery_performance(discovery_date);",
            ]
            
            for index_sql in indexes:
                await conn.execute(index_sql)
        
        return True
    
    async def learn_from_explosive_winner(self, symbol: str, discovery_features: Dict, 
                                        outcome_return: float, days_held: int):
        """Learn from actual explosive winners to improve pattern detection"""
        
        # Store explosive pattern for future reference
        pattern = ExplosivePattern(
            symbol=symbol,
            discovery_date=datetime.now(),
            pattern_features=discovery_features,
            outcome_return_pct=outcome_return,
            days_to_peak=days_held,
            pattern_confidence=self._calculate_pattern_confidence(discovery_features, outcome_return)
        )
        
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO explosive_patterns 
                (symbol, discovery_date, pattern_features, vigl_score, volume_spike_ratio,
                 price_momentum_1d, price_momentum_5d, atr_pct, compression_pct, 
                 wolf_risk_score, outcome_return_pct, days_to_peak, pattern_success)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
            """, 
                symbol, pattern.discovery_date, json.dumps(discovery_features),
                discovery_features.get('vigl_score', 0.0),
                discovery_features.get('volume_spike_ratio', 0.0),
                discovery_features.get('momentum_1d', 0.0),
                discovery_features.get('momentum_5d', 0.0),
                discovery_features.get('atr_pct', 0.0),
                discovery_features.get('compression_pct', 0.0),
                discovery_features.get('wolf_risk', 0.0),
                outcome_return, days_held, outcome_return > 50.0
            )
        
        # Update feature importance weights
        await self._update_feature_importance(discovery_features, outcome_return)
        
        return pattern
    
    async def get_adaptive_discovery_parameters(self, current_market_regime: str = None) -> Dict:
        """Get discovery parameters adapted to current market conditions and historical performance"""
        
        # Default parameters from existing system
        base_params = {
            'explosive_price_min': 0.10,
            'explosive_price_max': 25.00,
            'explosive_volume_min': 5.0,
            'explosive_volume_target': 15.0,
            'explosive_momentum_min': 0.08,
            'explosive_atr_min': 0.06,
            'wolf_risk_threshold': 0.6,
            'vigl_threshold': 0.65
        }
        
        # Get current market regime if not provided
        if not current_market_regime:
            current_market_regime = await self._detect_current_market_regime()
        
        # Fetch adaptive parameters based on historical performance
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Get feature weights for current market regime
            feature_weights = await conn.fetch("""
                SELECT feature_name, feature_weight, success_correlation 
                FROM pattern_features 
                WHERE market_regime = $1 OR market_regime IS NULL
                ORDER BY success_correlation DESC
            """, current_market_regime)
            
            # Get recent discovery performance to adapt thresholds
            recent_performance = await conn.fetchrow("""
                SELECT avg(success_rate) as avg_success_rate,
                       avg(explosive_winners::float / NULLIF(total_tracked, 0)) as explosive_rate
                FROM discovery_performance 
                WHERE discovery_date >= $1
            """, datetime.now() - timedelta(days=30))
        
        # Adapt parameters based on recent performance
        adapted_params = base_params.copy()
        
        if recent_performance:
            success_rate = recent_performance['avg_success_rate'] or 0.0
            explosive_rate = recent_performance['explosive_rate'] or 0.0
            
            # If recent success rate is low, make parameters more selective
            if success_rate < 0.3:
                adapted_params['vigl_threshold'] = min(0.75, base_params['vigl_threshold'] + 0.1)
                adapted_params['explosive_volume_min'] = base_params['explosive_volume_min'] * 1.2
                adapted_params['wolf_risk_threshold'] = base_params['wolf_risk_threshold'] * 0.9
                
            # If explosive rate is low, adjust price range and momentum thresholds
            if explosive_rate < 0.1:
                adapted_params['explosive_price_max'] = 15.0  # Focus on smaller caps
                adapted_params['explosive_momentum_min'] = 0.10  # Require stronger momentum
        
        # Apply market regime adjustments
        regime_adjustments = {
            'bull_market': {'vigl_threshold': -0.05, 'volume_min': -1.0},
            'bear_market': {'vigl_threshold': 0.10, 'volume_min': 2.0, 'wolf_risk_threshold': -0.1},
            'volatile': {'atr_min': 0.02, 'volume_target': 5.0},
            'low_volatility': {'atr_min': -0.02, 'momentum_min': -0.02}
        }
        
        if current_market_regime in regime_adjustments:
            adjustments = regime_adjustments[current_market_regime]
            for param, adjustment in adjustments.items():
                if param == 'vigl_threshold':
                    adapted_params['vigl_threshold'] = max(0.2, min(0.9, 
                        adapted_params['vigl_threshold'] + adjustment))
                elif param == 'volume_min':
                    adapted_params['explosive_volume_min'] = max(1.0, 
                        adapted_params['explosive_volume_min'] + adjustment)
                # Add other parameter adjustments as needed
        
        return adapted_params
    
    async def learn_from_thesis_outcome(self, symbol: str, thesis_data: Dict, 
                                      actual_returns: Dict[str, float]):
        """Learn from thesis prediction accuracy to improve future recommendations"""
        
        recommendation = thesis_data.get('recommendation', 'HOLD')
        confidence = thesis_data.get('confidence', 0.5)
        predicted_direction = 'UP' if recommendation in ['BUY_MORE'] else 'DOWN' if recommendation == 'LIQUIDATE' else 'NEUTRAL'
        
        # Calculate accuracy score based on prediction vs outcome
        accuracy_score = self._calculate_thesis_accuracy(
            predicted_direction, actual_returns, confidence
        )
        
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO thesis_accuracy 
                (symbol, thesis_date, recommendation, confidence_score, predicted_direction,
                 actual_return_1d, actual_return_7d, actual_return_30d, accuracy_score)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
                symbol, datetime.now(), recommendation, confidence, predicted_direction,
                actual_returns.get('1d', 0.0), actual_returns.get('7d', 0.0),
                actual_returns.get('30d', 0.0), accuracy_score
            )
        
        # Update thesis model weights based on accuracy
        await self._update_thesis_model_weights(thesis_data, accuracy_score)
    
    async def get_pattern_similarity_score(self, current_features: Dict) -> float:
        """Calculate similarity to historical explosive winners"""
        
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Get successful explosive patterns
            explosive_winners = await conn.fetch("""
                SELECT pattern_features, outcome_return_pct 
                FROM explosive_patterns 
                WHERE pattern_success = true AND outcome_return_pct > 50.0
                ORDER BY outcome_return_pct DESC 
                LIMIT 50
            """)
        
        if not explosive_winners:
            return 0.5  # Default similarity
        
        similarities = []
        for winner in explosive_winners:
            winner_features = json.loads(winner['pattern_features'])
            similarity = self._calculate_feature_similarity(current_features, winner_features)
            # Weight by outcome performance
            weight = min(winner['outcome_return_pct'] / 100.0, 3.0)  # Cap at 300% weight
            similarities.append(similarity * weight)
        
        # Return weighted average similarity
        return sum(similarities) / len(similarities)
    
    async def detect_market_regime_change(self) -> Dict:
        """Detect if market regime has changed and update parameters accordingly"""
        
        current_regime = await self._detect_current_market_regime()
        
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Get last recorded regime
            last_regime = await conn.fetchrow("""
                SELECT regime_type, regime_date 
                FROM market_regimes 
                ORDER BY regime_date DESC 
                LIMIT 1
            """)
        
        regime_changed = False
        if not last_regime or last_regime['regime_type'] != current_regime:
            regime_changed = True
            
            # Record new regime
            async with pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO market_regimes (regime_date, regime_type)
                    VALUES ($1, $2)
                    ON CONFLICT (regime_date) 
                    DO UPDATE SET regime_type = $2
                """, datetime.now().date(), current_regime)
        
        return {
            'current_regime': current_regime,
            'previous_regime': last_regime['regime_type'] if last_regime else None,
            'regime_changed': regime_changed,
            'change_date': datetime.now() if regime_changed else last_regime['regime_date']
        }
    
    def _calculate_pattern_confidence(self, features: Dict, outcome: float) -> float:
        """Calculate confidence score for a pattern based on features and outcome"""
        base_confidence = 0.5
        
        # Outcome-based confidence adjustment
        if outcome > 100:
            outcome_adj = 0.4
        elif outcome > 50:
            outcome_adj = 0.3
        elif outcome > 25:
            outcome_adj = 0.2
        elif outcome > 0:
            outcome_adj = 0.1
        else:
            outcome_adj = -0.2
        
        # Feature-based confidence
        vigl_score = features.get('vigl_score', 0.5)
        volume_spike = features.get('volume_spike_ratio', 1.0)
        momentum = features.get('momentum_5d', 0.0)
        
        feature_adj = (vigl_score - 0.5) * 0.2 + min(volume_spike / 10.0, 0.1) + abs(momentum) * 0.1
        
        return max(0.0, min(1.0, base_confidence + outcome_adj + feature_adj))
    
    async def _update_feature_importance(self, features: Dict, outcome: float):
        """Update feature importance weights based on successful patterns"""
        
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            for feature_name, feature_value in features.items():
                if isinstance(feature_value, (int, float)):
                    # Calculate correlation between feature value and outcome
                    correlation = min(abs(feature_value) * outcome / 100.0, 1.0)
                    
                    await conn.execute("""
                        INSERT INTO pattern_features (feature_name, feature_weight, success_correlation)
                        VALUES ($1, $2, $3)
                        ON CONFLICT (feature_name, market_regime)
                        DO UPDATE SET 
                            feature_weight = (pattern_features.feature_weight * 0.9) + ($2 * 0.1),
                            success_correlation = (pattern_features.success_correlation * 0.9) + ($3 * 0.1),
                            last_updated = NOW()
                    """, feature_name, feature_value, correlation)
    
    def _calculate_feature_similarity(self, current: Dict, historical: Dict) -> float:
        """Calculate similarity between two feature sets"""
        
        common_features = set(current.keys()) & set(historical.keys())
        if not common_features:
            return 0.0
        
        similarities = []
        for feature in common_features:
            curr_val = current[feature]
            hist_val = historical[feature]
            
            if isinstance(curr_val, (int, float)) and isinstance(hist_val, (int, float)):
                # Normalize similarity (closer values = higher similarity)
                max_val = max(abs(curr_val), abs(hist_val), 1.0)
                similarity = 1.0 - abs(curr_val - hist_val) / max_val
                similarities.append(similarity)
        
        return sum(similarities) / len(similarities) if similarities else 0.0

    async def analyze_winning_patterns(self) -> Dict[str, Any]:
        """
        Advanced pattern analysis to identify what makes explosive winners
        Returns actionable insights for discovery optimization
        """

        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Analyze successful patterns (7-day returns > 25%)
            winning_patterns = await conn.fetch("""
                SELECT
                    cf.symbol,
                    cf.score,
                    cf.volume_momentum_score,
                    cf.squeeze_score,
                    cf.catalyst_score,
                    cf.sentiment_score,
                    cf.options_score,
                    cf.technical_score,
                    cf.price,
                    cf.rel_vol,
                    to.return_7d,
                    to.return_30d,
                    mr.regime_type
                FROM learning_intelligence.candidate_features cf
                JOIN learning_intelligence.trade_outcomes to ON cf.id = to.candidate_id
                LEFT JOIN learning_intelligence.market_regimes mr ON DATE(cf.created_at) = mr.regime_date
                WHERE to.return_7d > 25.0
                ORDER BY to.return_7d DESC
                LIMIT 100
            """)

            # Analyze losing patterns (7-day returns < -10%)
            losing_patterns = await conn.fetch("""
                SELECT
                    cf.volume_momentum_score,
                    cf.squeeze_score,
                    cf.catalyst_score,
                    cf.sentiment_score,
                    cf.options_score,
                    cf.technical_score,
                    cf.price,
                    cf.rel_vol,
                    to.return_7d
                FROM learning_intelligence.candidate_features cf
                JOIN learning_intelligence.trade_outcomes to ON cf.id = to.candidate_id
                WHERE to.return_7d < -10.0
                LIMIT 100
            """)

            if not winning_patterns:
                return {"error": "Insufficient winning pattern data"}

            # Calculate feature effectiveness
            feature_analysis = self._analyze_feature_patterns(winning_patterns, losing_patterns)

            # Identify optimal ranges
            optimal_ranges = self._calculate_optimal_ranges(winning_patterns)

            # Generate scoring weight recommendations
            weight_recommendations = self._generate_weight_recommendations(feature_analysis)

            return {
                "pattern_count": {
                    "winners": len(winning_patterns),
                    "losers": len(losing_patterns)
                },
                "feature_effectiveness": feature_analysis,
                "optimal_ranges": optimal_ranges,
                "weight_recommendations": weight_recommendations,
                "top_performing_patterns": [
                    {
                        "symbol": p['symbol'],
                        "return_7d": p['return_7d'],
                        "score": p['score'],
                        "regime": p['regime_type'],
                        "key_features": self._extract_key_features(p)
                    }
                    for p in winning_patterns[:10]
                ]
            }

    def _analyze_feature_patterns(self, winners: list, losers: list) -> Dict[str, Any]:
        """Analyze feature effectiveness between winners and losers"""

        feature_names = [
            'volume_momentum_score', 'squeeze_score', 'catalyst_score',
            'sentiment_score', 'options_score', 'technical_score', 'rel_vol'
        ]

        analysis = {}

        for feature in feature_names:
            winner_values = [p[feature] or 0.0 for p in winners]
            loser_values = [p[feature] or 0.0 for p in losers if losers]

            if winner_values:
                winner_avg = sum(winner_values) / len(winner_values)
                loser_avg = sum(loser_values) / len(loser_values) if loser_values else 0.0

                # Calculate effectiveness score (higher = more predictive of success)
                effectiveness = winner_avg - loser_avg

                analysis[feature] = {
                    "winner_avg": round(winner_avg, 3),
                    "loser_avg": round(loser_avg, 3),
                    "effectiveness_score": round(effectiveness, 3),
                    "winner_min": round(min(winner_values), 3),
                    "winner_max": round(max(winner_values), 3),
                    "predictive_power": "high" if effectiveness > 0.2 else "medium" if effectiveness > 0.1 else "low"
                }

        return analysis

    def _calculate_optimal_ranges(self, winners: list) -> Dict[str, Any]:
        """Calculate optimal value ranges for each feature based on winners"""

        feature_names = [
            'volume_momentum_score', 'squeeze_score', 'catalyst_score',
            'sentiment_score', 'options_score', 'technical_score', 'rel_vol', 'price'
        ]

        ranges = {}

        for feature in feature_names:
            values = [p[feature] or 0.0 for p in winners if p[feature] is not None]

            if values:
                values.sort()
                n = len(values)

                # Calculate percentiles for optimal ranges
                p25 = values[int(n * 0.25)]
                p50 = values[int(n * 0.50)]
                p75 = values[int(n * 0.75)]
                p90 = values[int(n * 0.90)]

                ranges[feature] = {
                    "optimal_min": round(p25, 3),
                    "optimal_target": round(p75, 3),
                    "exceptional": round(p90, 3),
                    "median": round(p50, 3)
                }

        return ranges

    def _generate_weight_recommendations(self, feature_analysis: Dict) -> Dict[str, Any]:
        """Generate scoring weight recommendations based on feature effectiveness"""

        # Current weights (from the system)
        current_weights = {
            'volume_momentum': 0.35,
            'squeeze': 0.25,
            'catalyst': 0.20,
            'sentiment': 0.10,  # Note: sentiment is part of catalyst in the actual system
            'options': 0.10,
            'technical': 0.10
        }

        # Map feature analysis to weight categories
        effectiveness_scores = {
            'volume_momentum': feature_analysis.get('volume_momentum_score', {}).get('effectiveness_score', 0),
            'squeeze': feature_analysis.get('squeeze_score', {}).get('effectiveness_score', 0),
            'catalyst': feature_analysis.get('catalyst_score', {}).get('effectiveness_score', 0),
            'sentiment': feature_analysis.get('sentiment_score', {}).get('effectiveness_score', 0),
            'options': feature_analysis.get('options_score', {}).get('effectiveness_score', 0),
            'technical': feature_analysis.get('technical_score', {}).get('effectiveness_score', 0)
        }

        # Calculate total effectiveness
        total_effectiveness = sum(effectiveness_scores.values())

        if total_effectiveness > 0:
            # Normalize effectiveness scores to generate new weights
            recommended_weights = {}
            for component, effectiveness in effectiveness_scores.items():
                if component in current_weights:
                    # Blend current weight with effectiveness-based weight
                    effectiveness_weight = effectiveness / total_effectiveness
                    blended_weight = (current_weights[component] * 0.7) + (effectiveness_weight * 0.3)
                    recommended_weights[component] = round(blended_weight, 3)
        else:
            recommended_weights = current_weights

        # Ensure weights sum to 1.0
        weight_sum = sum(recommended_weights.values())
        if weight_sum > 0:
            recommended_weights = {k: round(v / weight_sum, 3) for k, v in recommended_weights.items()}

        return {
            "current_weights": current_weights,
            "recommended_weights": recommended_weights,
            "weight_changes": {
                k: round(recommended_weights.get(k, 0) - current_weights.get(k, 0), 3)
                for k in current_weights.keys()
            },
            "rationale": "Based on analysis of successful explosive patterns"
        }

    def _extract_key_features(self, pattern: Dict) -> Dict[str, Any]:
        """Extract the most significant features from a winning pattern"""

        features = {}

        # Volume features
        if pattern.get('rel_vol', 0) > 3.0:
            features['high_volume'] = f"{pattern['rel_vol']:.1f}x average"

        # Score components
        if pattern.get('squeeze_score', 0) > 0.7:
            features['squeeze_setup'] = f"{pattern['squeeze_score']:.2f}"

        if pattern.get('volume_momentum_score', 0) > 0.8:
            features['strong_momentum'] = f"{pattern['volume_momentum_score']:.2f}"

        if pattern.get('catalyst_score', 0) > 0.6:
            features['catalyst_present'] = f"{pattern['catalyst_score']:.2f}"

        # Price characteristics
        if pattern.get('price', 0) < 5.0:
            features['low_price'] = f"${pattern['price']:.2f}"

        return features
    
    def _calculate_thesis_accuracy(self, predicted_direction: str, 
                                 actual_returns: Dict[str, float], confidence: float) -> float:
        """Calculate accuracy score for thesis prediction"""
        
        # Use 7-day return as primary accuracy measure
        actual_7d = actual_returns.get('7d', 0.0)
        
        if predicted_direction == 'UP':
            accuracy = 1.0 if actual_7d > 5.0 else max(0.0, actual_7d / 5.0)
        elif predicted_direction == 'DOWN':
            accuracy = 1.0 if actual_7d < -5.0 else max(0.0, -actual_7d / 5.0)
        else:  # NEUTRAL
            accuracy = 1.0 if abs(actual_7d) < 5.0 else max(0.0, 1.0 - abs(actual_7d) / 10.0)
        
        # Weight accuracy by confidence - higher confidence predictions should be more accurate
        confidence_weight = 0.5 + (confidence * 0.5)
        
        return accuracy * confidence_weight
    
    async def _update_thesis_model_weights(self, thesis_data: Dict, accuracy_score: float):
        """Update thesis generation model weights based on accuracy feedback"""
        # This would implement reinforcement learning updates to thesis generation
        # For now, store the feedback for future model improvement
        pass
    
    async def _detect_current_market_regime(self) -> str:
        """Detect current market regime using market indicators and discovery patterns"""

        try:
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                # Analyze recent discovery patterns for regime indicators
                recent_data = await conn.fetchrow("""
                    SELECT
                        AVG(cf.score) as avg_score,
                        AVG(cf.rel_vol) as avg_rel_vol,
                        AVG(cf.volume_momentum_score) as avg_volume_momentum,
                        AVG(cf.squeeze_score) as avg_squeeze,
                        COUNT(*) as sample_size,
                        COUNT(CASE WHEN cf.action_tag = 'trade_ready' THEN 1 END) as trade_ready_count
                    FROM learning_intelligence.candidate_features cf
                    JOIN learning_intelligence.discovery_events de ON cf.discovery_event_id = de.id
                    WHERE de.event_timestamp >= NOW() - INTERVAL '7 days'
                """)

                if not recent_data or recent_data['sample_size'] < 10:
                    return "insufficient_data"

                avg_score = recent_data['avg_score'] or 0.0
                avg_rel_vol = recent_data['avg_rel_vol'] or 1.0
                avg_squeeze = recent_data['avg_squeeze'] or 0.0
                trade_ready_ratio = (recent_data['trade_ready_count'] or 0) / recent_data['sample_size']

                # Market regime detection logic
                if avg_score > 0.8 and trade_ready_ratio > 0.3:
                    regime = "explosive_bull"
                elif avg_rel_vol > 3.0 and avg_squeeze > 0.7:
                    regime = "squeeze_setup"
                elif avg_score < 0.6 and trade_ready_ratio < 0.1:
                    regime = "low_opportunity"
                elif avg_rel_vol > 5.0:
                    regime = "high_volatility"
                elif avg_rel_vol < 1.5:
                    regime = "low_volatility"
                else:
                    regime = "normal_market"

                # Store regime detection
                await conn.execute("""
                    INSERT INTO learning_intelligence.market_regimes
                    (regime_date, regime_type, explosive_success_rate, avg_pattern_return, detection_confidence)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (regime_date)
                    DO UPDATE SET
                        regime_type = $2,
                        explosive_success_rate = $3,
                        avg_pattern_return = $4,
                        detection_confidence = $5
                """, datetime.now().date(), regime, trade_ready_ratio, avg_score, 0.8)

                return regime

        except Exception as e:
            logger.warning(f"Market regime detection failed: {e}")
            return "unknown"

# Factory function for easy import
async def get_learning_engine() -> LearningEngine:
    """Get initialized learning engine instance"""
    engine = LearningEngine()
    await engine.initialize_learning_database()
    return engine