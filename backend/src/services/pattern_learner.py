#!/usr/bin/env python3
"""
Pattern Learning Service
Maintains explosive growth edge by learning from squeeze patterns like VIGL's +324% success.

Mission: Learn from outcomes, adapt thresholds, and identify similar patterns for explosive returns.
"""

import os
import json
import hashlib
import asyncio
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import math
import statistics as stats
import numpy as np
from collections import defaultdict

from ..shared.database import get_db_pool

@dataclass
class PatternMatch:
    """Pattern similarity match result"""
    symbol: str
    similarity_score: float
    historical_pattern: Dict
    expected_return: float
    confidence: float
    risk_factors: List[str]

@dataclass 
class PatternUpdate:
    """Pattern weight update result"""
    pattern_hash: str
    old_weight: float
    new_weight: float
    boost_factor: float
    reason: str

class PatternLearner:
    """
    Advanced pattern learning system that maintains explosive growth edge through:
    1. Learning from VIGL-style squeeze outcomes 
    2. Adapting detection thresholds based on success/failure
    3. Finding similar patterns to historical explosive winners
    4. Evolving pattern recognition over time
    """
    
    def __init__(self):
        self.pattern_cache = {}
        self.similarity_cache = {}
        self.pattern_weights = defaultdict(float)
        
    async def initialize_pattern_memory(self):
        """Initialize pattern memory database and load reference patterns"""
        pool = await get_db_pool()
        if not pool:
            return False
            
        try:
            async with pool.acquire() as conn:
                # Execute pattern memory schema
                with open('/Users/michaelmote/Desktop/AMC-TRADER/backend/src/shared/pattern_memory_schema.sql', 'r') as f:
                    schema_sql = f.read()
                    await conn.execute(schema_sql)
                
                # Load pattern weights from database
                await self._load_pattern_weights(conn)
                
                return True
                
        except Exception as e:
            print(f"Failed to initialize pattern memory: {e}")
            return False
    
    async def learn_from_outcome(self, symbol: str, entry_data: Dict, exit_data: Dict) -> Dict:
        """
        Learn from trading outcome to improve future pattern detection.
        
        Core learning loop: Entry Pattern → Outcome → Weight Adjustment → Better Detection
        """
        try:
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                # Calculate performance metrics
                entry_price = entry_data.get('price', 0.0)
                exit_price = exit_data.get('price', 0.0)
                days_held = exit_data.get('days_held', 0)
                
                if entry_price <= 0:
                    return {'error': 'Invalid entry price'}
                
                return_pct = ((exit_price - entry_price) / entry_price) * 100
                success = return_pct >= 50.0  # VIGL-style explosive success threshold
                explosive = return_pct >= 100.0  # True explosive winner
                
                # Create pattern hash for identification
                pattern_features = {
                    'volume_spike': entry_data.get('volume_spike', 1.0),
                    'short_interest': entry_data.get('short_interest', 0.0),
                    'float_shares': entry_data.get('float_shares', 50000000),
                    'price_range': self._classify_price_range(entry_price),
                    'squeeze_score': entry_data.get('squeeze_score', 0.0),
                    'vigl_similarity': entry_data.get('vigl_similarity', 0.0)
                }
                
                pattern_hash = self._generate_pattern_hash(pattern_features)
                
                # Store pattern outcome
                await conn.execute("""
                    INSERT INTO squeeze_patterns 
                    (symbol, pattern_date, volume_spike, short_interest, float_shares,
                     entry_price, exit_price, max_price, outcome_pct, max_gain_pct,
                     pattern_score, squeeze_score, vigl_similarity, success, explosive,
                     days_held, pattern_hash, sector, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, NOW())
                    ON CONFLICT (symbol, pattern_date) 
                    DO UPDATE SET 
                        exit_price = $7, outcome_pct = $9, success = $14, explosive = $15,
                        days_held = $16, updated_at = NOW()
                """,
                    symbol, entry_data.get('discovery_date', datetime.now().date()),
                    pattern_features['volume_spike'], pattern_features['short_interest'], 
                    pattern_features['float_shares'], entry_price, exit_price, 
                    exit_data.get('max_price', exit_price), return_pct, return_pct,
                    entry_data.get('pattern_score', 0.6), pattern_features['squeeze_score'],
                    pattern_features['vigl_similarity'], success, explosive, days_held,
                    pattern_hash, entry_data.get('sector', 'Unknown')
                )
                
                # Learn from the outcome - adjust pattern weights
                pattern_update = await self._update_pattern_weights(
                    pattern_features, success, return_pct, explosive
                )
                
                # Update pattern evolution tracking
                await self._update_pattern_evolution(pattern_features, success, return_pct)
                
                # Generate alerts if significant learning occurs
                if explosive and return_pct > 200:
                    await self._generate_explosive_winner_alert(symbol, return_pct, pattern_features)
                elif not success and return_pct < -20:
                    await self._generate_pattern_failure_alert(symbol, return_pct, pattern_features)
                
                return {
                    'learning_success': True,
                    'pattern_hash': pattern_hash,
                    'outcome': {
                        'return_pct': return_pct,
                        'success': success,
                        'explosive': explosive,
                        'days_held': days_held
                    },
                    'pattern_update': pattern_update,
                    'improved_detection': return_pct > 25.0  # Will improve future detection if profitable
                }
                
        except Exception as e:
            print(f"Error learning from outcome for {symbol}: {e}")
            return {'learning_success': False, 'error': str(e)}
    
    async def find_similar_patterns(self, current_data: Dict, min_similarity: float = 0.80) -> List[PatternMatch]:
        """
        Find historical patterns similar to current opportunity.
        Returns top matches with expected outcomes based on similarity.
        """
        try:
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                # Get successful historical patterns
                historical_patterns = await conn.fetch("""
                    SELECT symbol, volume_spike, short_interest, float_shares, entry_price,
                           outcome_pct, max_gain_pct, squeeze_score, vigl_similarity,
                           pattern_hash, days_held, sector, created_at
                    FROM squeeze_patterns
                    WHERE success = TRUE AND outcome_pct >= 25.0
                    ORDER BY outcome_pct DESC
                    LIMIT 100
                """)
                
                if not historical_patterns:
                    return []
                
                current_features = self._extract_pattern_features(current_data)
                pattern_matches = []
                
                for pattern in historical_patterns:
                    historical_features = {
                        'volume_spike': pattern['volume_spike'],
                        'short_interest': pattern['short_interest'],
                        'float_shares': pattern['float_shares'],
                        'price_range': self._classify_price_range(pattern['entry_price']),
                        'squeeze_score': pattern['squeeze_score'],
                        'vigl_similarity': pattern['vigl_similarity']
                    }
                    
                    # Calculate multi-dimensional similarity
                    similarity = self._calculate_pattern_similarity(current_features, historical_features)
                    
                    if similarity >= min_similarity:
                        # Calculate confidence based on similarity and historical performance
                        confidence = min(similarity * (pattern['outcome_pct'] / 100.0), 1.0)
                        
                        # Identify risk factors
                        risk_factors = self._identify_risk_factors(current_features, historical_features)
                        
                        match = PatternMatch(
                            symbol=pattern['symbol'],
                            similarity_score=similarity,
                            historical_pattern={
                                'symbol': pattern['symbol'],
                                'entry_price': float(pattern['entry_price']),
                                'outcome_pct': pattern['outcome_pct'],
                                'max_gain_pct': pattern['max_gain_pct'],
                                'days_held': pattern['days_held'],
                                'volume_spike': pattern['volume_spike'],
                                'sector': pattern['sector'],
                                'created_at': pattern['created_at'].isoformat()
                            },
                            expected_return=pattern['outcome_pct'] * similarity,  # Scale by similarity
                            confidence=confidence,
                            risk_factors=risk_factors
                        )
                        
                        pattern_matches.append(match)
                
                # Sort by expected return (similarity-weighted outcome)
                pattern_matches.sort(key=lambda x: x.expected_return, reverse=True)
                
                # Store similarity calculations for future reference
                if pattern_matches:
                    await self._cache_similarity_results(current_data, pattern_matches[:10])
                
                return pattern_matches[:20]  # Return top 20 matches
                
        except Exception as e:
            print(f"Error finding similar patterns: {e}")
            return []
    
    async def get_adaptive_thresholds(self, pattern_type: str = 'squeeze') -> Dict:
        """
        Get adaptive detection thresholds based on recent pattern performance.
        Automatically adjusts to maintain explosive winner detection edge.
        """
        try:
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                # Get recent pattern performance (last 60 days)
                recent_performance = await conn.fetchrow("""
                    SELECT 
                        AVG(outcome_pct) as avg_return,
                        AVG(volume_spike) as avg_volume_spike,
                        AVG(short_interest) as avg_short_interest,
                        COUNT(*) FILTER (WHERE success = TRUE) as success_count,
                        COUNT(*) as total_count,
                        COUNT(*) FILTER (WHERE explosive = TRUE) as explosive_count
                    FROM squeeze_patterns
                    WHERE created_at >= NOW() - INTERVAL '60 days'
                """)
                
                if not recent_performance or recent_performance['total_count'] == 0:
                    # No recent data - return default thresholds
                    return self._get_default_thresholds()
                
                success_rate = recent_performance['success_count'] / recent_performance['total_count']
                explosive_rate = recent_performance['explosive_count'] / recent_performance['total_count']
                
                # Base thresholds
                thresholds = {
                    'volume_spike_min': 15.0,
                    'short_interest_min': 0.10,
                    'squeeze_score_min': 0.70,
                    'vigl_similarity_min': 0.60,
                    'confidence_threshold': 0.75
                }
                
                # Adaptive adjustments based on recent performance
                if success_rate < 0.30:  # Low recent success rate
                    # Make thresholds more selective
                    thresholds['volume_spike_min'] *= 1.25  # Require higher volume
                    thresholds['short_interest_min'] *= 1.2  # Require more short interest
                    thresholds['squeeze_score_min'] = min(0.85, thresholds['squeeze_score_min'] * 1.1)
                    thresholds['confidence_threshold'] = min(0.90, thresholds['confidence_threshold'] * 1.1)
                    adjustment_reason = f"Tightened thresholds due to low success rate ({success_rate:.1%})"
                    
                elif success_rate > 0.70 and explosive_rate > 0.20:  # High success with good explosive rate
                    # Can be slightly more aggressive
                    thresholds['volume_spike_min'] *= 0.90  # Allow slightly lower volume
                    thresholds['squeeze_score_min'] *= 0.95  # Lower squeeze requirement
                    thresholds['confidence_threshold'] *= 0.95  # Lower confidence requirement
                    adjustment_reason = f"Relaxed thresholds due to high success ({success_rate:.1%}) and explosive rate ({explosive_rate:.1%})"
                    
                else:
                    adjustment_reason = "Thresholds maintained based on acceptable performance"
                
                # Pattern-specific adjustments from successful patterns
                if recent_performance['avg_volume_spike'] and recent_performance['avg_volume_spike'] > 25:
                    # Historical explosive winners had very high volume
                    thresholds['volume_spike_target'] = recent_performance['avg_volume_spike'] * 0.8
                else:
                    thresholds['volume_spike_target'] = 20.9  # VIGL reference
                
                return {
                    'thresholds': thresholds,
                    'performance_basis': {
                        'success_rate': success_rate,
                        'explosive_rate': explosive_rate,
                        'avg_return': recent_performance['avg_return'],
                        'total_patterns': recent_performance['total_count'],
                        'analysis_period_days': 60
                    },
                    'adjustment_reason': adjustment_reason,
                    'last_updated': datetime.now().isoformat()
                }
                
        except Exception as e:
            print(f"Error getting adaptive thresholds: {e}")
            return {'thresholds': self._get_default_thresholds(), 'error': str(e)}
    
    async def detect_pattern_evolution(self, days_back: int = 90) -> Dict:
        """
        Detect how patterns are evolving over time.
        Critical for maintaining edge as market conditions change.
        """
        try:
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                # Analyze pattern performance over time windows
                evolution_data = await conn.fetch("""
                    SELECT 
                        DATE_TRUNC('week', created_at) as week,
                        AVG(volume_spike) as avg_volume_spike,
                        AVG(short_interest) as avg_short_interest,
                        AVG(outcome_pct) as avg_return,
                        COUNT(*) FILTER (WHERE success = TRUE)::float / COUNT(*) as success_rate,
                        COUNT(*) as pattern_count
                    FROM squeeze_patterns
                    WHERE created_at >= NOW() - INTERVAL '%s days'
                    GROUP BY DATE_TRUNC('week', created_at)
                    ORDER BY week DESC
                """ % days_back)
                
                if len(evolution_data) < 4:
                    return {'evolution_detected': False, 'reason': 'Insufficient data for trend analysis'}
                
                # Analyze trends
                recent_weeks = evolution_data[:4]  # Last 4 weeks
                older_weeks = evolution_data[4:8] if len(evolution_data) >= 8 else evolution_data[4:]
                
                if not older_weeks:
                    return {'evolution_detected': False, 'reason': 'Need more historical data'}
                
                # Calculate trend changes
                recent_avg_volume = stats.mean([w['avg_volume_spike'] for w in recent_weeks if w['avg_volume_spike']])
                older_avg_volume = stats.mean([w['avg_volume_spike'] for w in older_weeks if w['avg_volume_spike']])
                
                recent_success_rate = stats.mean([w['success_rate'] for w in recent_weeks if w['success_rate']])
                older_success_rate = stats.mean([w['success_rate'] for w in older_weeks if w['success_rate']])
                
                recent_avg_return = stats.mean([w['avg_return'] for w in recent_weeks if w['avg_return']])
                older_avg_return = stats.mean([w['avg_return'] for w in older_weeks if w['avg_return']])
                
                # Detect significant changes
                volume_change = (recent_avg_volume - older_avg_volume) / older_avg_volume if older_avg_volume > 0 else 0
                success_change = recent_success_rate - older_success_rate
                return_change = (recent_avg_return - older_avg_return) / abs(older_avg_return) if older_avg_return != 0 else 0
                
                evolution_alerts = []
                
                # Volume requirement evolution
                if volume_change > 0.50:  # 50% increase in required volume
                    evolution_alerts.append({
                        'type': 'VOLUME_INFLATION',
                        'severity': 'HIGH',
                        'message': f'Volume requirements increasing {volume_change:.1%} - market becoming more difficult'
                    })
                elif volume_change < -0.30:  # 30% decrease
                    evolution_alerts.append({
                        'type': 'VOLUME_DEFLATION', 
                        'severity': 'MEDIUM',
                        'message': f'Volume requirements decreasing {volume_change:.1%} - easier conditions'
                    })
                
                # Success rate evolution
                if success_change < -0.20:  # 20% drop in success rate
                    evolution_alerts.append({
                        'type': 'PATTERN_DEGRADATION',
                        'severity': 'CRITICAL',
                        'message': f'Pattern success rate declining by {success_change:.1%} - urgent threshold review needed'
                    })
                elif success_change > 0.15:  # 15% improvement
                    evolution_alerts.append({
                        'type': 'PATTERN_IMPROVEMENT',
                        'severity': 'POSITIVE',
                        'message': f'Pattern success rate improving by {success_change:.1%} - consider loosening thresholds'
                    })
                
                # Return performance evolution
                if return_change < -0.30:  # 30% drop in average returns
                    evolution_alerts.append({
                        'type': 'RETURN_DECLINE',
                        'severity': 'HIGH',
                        'message': f'Average returns declining by {return_change:.1%} - pattern effectiveness decreasing'
                    })
                
                return {
                    'evolution_detected': len(evolution_alerts) > 0,
                    'analysis_period': f'{days_back} days',
                    'trend_analysis': {
                        'volume_trend': {
                            'recent_avg': recent_avg_volume,
                            'historical_avg': older_avg_volume,
                            'change_pct': volume_change
                        },
                        'success_rate_trend': {
                            'recent_avg': recent_success_rate,
                            'historical_avg': older_success_rate,
                            'change': success_change
                        },
                        'return_trend': {
                            'recent_avg': recent_avg_return,
                            'historical_avg': older_avg_return,
                            'change_pct': return_change
                        }
                    },
                    'evolution_alerts': evolution_alerts,
                    'recommended_actions': self._generate_evolution_actions(evolution_alerts)
                }
                
        except Exception as e:
            print(f"Error detecting pattern evolution: {e}")
            return {'evolution_detected': False, 'error': str(e)}
    
    def _extract_pattern_features(self, data: Dict) -> Dict:
        """Extract standardized pattern features from input data"""
        return {
            'volume_spike': data.get('volume_spike', 1.0),
            'short_interest': data.get('short_interest', 0.0),
            'float_shares': data.get('float_shares', data.get('float', 50000000)),
            'price_range': self._classify_price_range(data.get('price', 5.0)),
            'squeeze_score': data.get('squeeze_score', 0.0),
            'vigl_similarity': data.get('vigl_similarity', 0.0)
        }
    
    def _classify_price_range(self, price: float) -> str:
        """Classify price into ranges for pattern matching"""
        if price < 2.0:
            return 'PENNY'
        elif price < 5.0:
            return 'LOW'  # VIGL sweet spot
        elif price < 10.0:
            return 'MEDIUM'
        elif price < 20.0:
            return 'HIGH'
        else:
            return 'LARGE_CAP'
    
    def _generate_pattern_hash(self, features: Dict) -> str:
        """Generate unique hash for pattern identification"""
        feature_string = json.dumps(features, sort_keys=True)
        return hashlib.sha256(feature_string.encode()).hexdigest()[:16]
    
    def _calculate_pattern_similarity(self, current: Dict, historical: Dict) -> float:
        """Calculate cosine similarity between pattern features"""
        # Weighted feature comparison
        weights = {
            'volume_spike': 0.35,      # Most important for squeeze detection
            'short_interest': 0.25,    # Critical for squeeze potential
            'float_shares': 0.15,      # Size matters for explosive moves
            'price_range': 0.10,       # Price range similarity
            'squeeze_score': 0.10,     # Overall squeeze assessment
            'vigl_similarity': 0.05    # Historical pattern match
        }
        
        similarity = 0.0
        total_weight = 0.0
        
        for feature, weight in weights.items():
            if feature in current and feature in historical:
                if feature == 'price_range':
                    # Categorical similarity
                    sim = 1.0 if current[feature] == historical[feature] else 0.3
                elif feature == 'float_shares':
                    # Log-scale similarity for float size
                    curr_log = math.log(max(current[feature], 1))
                    hist_log = math.log(max(historical[feature], 1))
                    max_log = max(curr_log, hist_log)
                    sim = 1.0 - abs(curr_log - hist_log) / max_log if max_log > 0 else 0.0
                else:
                    # Numeric similarity
                    curr_val = current[feature]
                    hist_val = historical[feature]
                    max_val = max(abs(curr_val), abs(hist_val), 1.0)
                    sim = 1.0 - abs(curr_val - hist_val) / max_val
                
                similarity += sim * weight
                total_weight += weight
        
        return similarity / total_weight if total_weight > 0 else 0.0
    
    def _identify_risk_factors(self, current: Dict, historical: Dict) -> List[str]:
        """Identify risk factors by comparing current to historical patterns"""
        risks = []
        
        # Volume risk
        if current.get('volume_spike', 0) < historical.get('volume_spike', 0) * 0.7:
            risks.append('Lower volume than historical pattern')
            
        # Short interest risk  
        if current.get('short_interest', 0) < historical.get('short_interest', 0) * 0.5:
            risks.append('Insufficient short interest for squeeze')
            
        # Float size risk
        if current.get('float_shares', 0) > historical.get('float_shares', 0) * 2.0:
            risks.append('Larger float may limit explosive potential')
            
        # Price range risk
        if current.get('price_range') != historical.get('price_range'):
            risks.append('Different price range than historical pattern')
        
        return risks
    
    async def _update_pattern_weights(self, features: Dict, success: bool, return_pct: float, explosive: bool) -> PatternUpdate:
        """Update pattern detection weights based on outcome"""
        pattern_hash = self._generate_pattern_hash(features)
        
        # Calculate boost factor based on outcome quality
        if explosive and return_pct > 200:
            boost = 1.25  # Exceptional outcome - strong boost
            reason = f"Explosive winner +{return_pct:.0f}% - major weight increase"
        elif success and return_pct > 100:
            boost = 1.15  # Good outcome - moderate boost
            reason = f"Strong winner +{return_pct:.0f}% - weight increase"
        elif success and return_pct > 25:
            boost = 1.05  # Minor success - small boost
            reason = f"Modest winner +{return_pct:.0f}% - minor weight increase"
        elif return_pct < -20:
            boost = 0.85  # Significant loss - weight reduction
            reason = f"Significant loss {return_pct:.0f}% - weight reduction"
        elif return_pct < 0:
            boost = 0.95  # Small loss - minor weight reduction
            reason = f"Small loss {return_pct:.0f}% - minor weight reduction"
        else:
            boost = 1.0  # Neutral outcome
            reason = "Neutral outcome - no weight change"
        
        # Update cached weights
        old_weight = self.pattern_weights.get(pattern_hash, 1.0)
        new_weight = old_weight * boost
        self.pattern_weights[pattern_hash] = new_weight
        
        # Store weight update in database for persistence
        pool = await get_db_pool()
        if pool:
            try:
                async with pool.acquire() as conn:
                    await conn.execute("""
                        INSERT INTO pattern_evolution (evolution_date, pattern_type, total_patterns, 
                                                      successful_patterns, explosive_patterns, success_rate, 
                                                      avg_return, detection_parameters)
                        VALUES (CURRENT_DATE, 'WEIGHT_UPDATE', 1, $1, $2, $3, $4, $5)
                        ON CONFLICT (evolution_date, pattern_type)
                        DO UPDATE SET 
                            total_patterns = pattern_evolution.total_patterns + 1,
                            successful_patterns = pattern_evolution.successful_patterns + $1,
                            explosive_patterns = pattern_evolution.explosive_patterns + $2,
                            detection_parameters = $5
                    """, 
                        1 if success else 0, 1 if explosive else 0,
                        1.0 if success else 0.0, return_pct,
                        json.dumps({'pattern_hash': pattern_hash, 'new_weight': new_weight, 'boost': boost})
                    )
            except Exception as e:
                print(f"Error storing weight update: {e}")
        
        return PatternUpdate(
            pattern_hash=pattern_hash,
            old_weight=old_weight,
            new_weight=new_weight,
            boost_factor=boost,
            reason=reason
        )
    
    async def _load_pattern_weights(self, conn):
        """Load cached pattern weights from database"""
        try:
            weights = await conn.fetch("""
                SELECT detection_parameters
                FROM pattern_evolution
                WHERE pattern_type = 'WEIGHT_UPDATE' 
                AND evolution_date >= CURRENT_DATE - INTERVAL '30 days'
            """)
            
            for weight_record in weights:
                if weight_record['detection_parameters']:
                    data = json.loads(weight_record['detection_parameters'])
                    pattern_hash = data.get('pattern_hash')
                    new_weight = data.get('new_weight', 1.0)
                    if pattern_hash:
                        self.pattern_weights[pattern_hash] = new_weight
                        
        except Exception as e:
            print(f"Error loading pattern weights: {e}")
    
    def _get_default_thresholds(self) -> Dict:
        """Get default detection thresholds"""
        return {
            'volume_spike_min': 15.0,
            'short_interest_min': 0.10,
            'squeeze_score_min': 0.70,
            'vigl_similarity_min': 0.60,
            'confidence_threshold': 0.75,
            'volume_spike_target': 20.9  # VIGL reference
        }
    
    async def _update_pattern_evolution(self, features: Dict, success: bool, return_pct: float):
        """Update pattern evolution tracking"""
        try:
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO pattern_evolution (evolution_date, pattern_type, total_patterns,
                                                  successful_patterns, avg_return, avg_volume_spike,
                                                  avg_short_interest, pattern_confidence)
                    VALUES (CURRENT_DATE, 'SQUEEZE', 1, $1, $2, $3, $4, $5)
                    ON CONFLICT (evolution_date, pattern_type)
                    DO UPDATE SET
                        total_patterns = pattern_evolution.total_patterns + 1,
                        successful_patterns = pattern_evolution.successful_patterns + $1,
                        avg_return = (pattern_evolution.avg_return * pattern_evolution.total_patterns + $2) / (pattern_evolution.total_patterns + 1),
                        avg_volume_spike = (pattern_evolution.avg_volume_spike * pattern_evolution.total_patterns + $3) / (pattern_evolution.total_patterns + 1),
                        avg_short_interest = (pattern_evolution.avg_short_interest * pattern_evolution.total_patterns + $4) / (pattern_evolution.total_patterns + 1)
                """,
                    1 if success else 0, return_pct,
                    features.get('volume_spike', 0), features.get('short_interest', 0),
                    0.8 if success else 0.4
                )
        except Exception as e:
            print(f"Error updating pattern evolution: {e}")
    
    async def _generate_explosive_winner_alert(self, symbol: str, return_pct: float, features: Dict):
        """Generate alert for explosive winner to learn from"""
        try:
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO pattern_alerts (alert_type, pattern_type, alert_level, message, details)
                    VALUES ('EXPLOSIVE_WINNER', 'VIGL_SQUEEZE', 'INFO', $1, $2)
                """,
                    f"🚀 EXPLOSIVE WINNER: {symbol} achieved {return_pct:.0f}% return - pattern learned",
                    json.dumps({
                        'symbol': symbol,
                        'return_pct': return_pct,
                        'features': features,
                        'learning_priority': 'HIGH'
                    })
                )
        except Exception as e:
            print(f"Error generating explosive winner alert: {e}")
    
    async def _generate_pattern_failure_alert(self, symbol: str, return_pct: float, features: Dict):
        """Generate alert for pattern failure to learn from"""
        try:
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO pattern_alerts (alert_type, pattern_type, alert_level, message, details)
                    VALUES ('PATTERN_FAILURE', 'SQUEEZE', 'WARNING', $1, $2)
                """,
                    f"⚠️ PATTERN FAILURE: {symbol} lost {abs(return_pct):.0f}% - analyze failure mode",
                    json.dumps({
                        'symbol': symbol,
                        'return_pct': return_pct,
                        'features': features,
                        'analysis_priority': 'HIGH'
                    })
                )
        except Exception as e:
            print(f"Error generating pattern failure alert: {e}")
    
    async def _cache_similarity_results(self, current_data: Dict, matches: List[PatternMatch]):
        """Cache similarity results for performance optimization"""
        try:
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                for i, match in enumerate(matches):
                    # Store top similarity matches
                    await conn.execute("""
                        INSERT INTO pattern_similarity (pattern_id_1, pattern_id_2, similarity_score, feature_correlation)
                        VALUES (
                            (SELECT id FROM squeeze_patterns WHERE symbol = $1 ORDER BY created_at DESC LIMIT 1),
                            (SELECT id FROM squeeze_patterns WHERE symbol = $2 AND pattern_hash = $3 LIMIT 1),
                            $4, $5
                        )
                        ON CONFLICT (pattern_id_1, pattern_id_2) DO UPDATE SET
                            similarity_score = $4, feature_correlation = $5
                    """,
                        current_data.get('symbol', 'UNKNOWN'), match.symbol, 
                        match.historical_pattern.get('pattern_hash', ''),
                        match.similarity_score, json.dumps({'rank': i + 1})
                    )
        except Exception as e:
            print(f"Error caching similarity results: {e}")
    
    def _generate_evolution_actions(self, alerts: List[Dict]) -> List[str]:
        """Generate recommended actions based on evolution alerts"""
        actions = []
        
        for alert in alerts:
            alert_type = alert.get('type')
            severity = alert.get('severity')
            
            if alert_type == 'PATTERN_DEGRADATION' and severity == 'CRITICAL':
                actions.append("URGENT: Review and tighten detection thresholds immediately")
                actions.append("Analyze failed patterns from last 30 days for common factors")
                
            elif alert_type == 'VOLUME_INFLATION':
                actions.append("Increase minimum volume spike requirement by 20-30%")
                actions.append("Focus on higher-quality volume patterns only")
                
            elif alert_type == 'RETURN_DECLINE':
                actions.append("Reassess market regime - pattern may be losing effectiveness")
                actions.append("Consider switching to alternative pattern detection methods")
                
            elif alert_type == 'PATTERN_IMPROVEMENT':
                actions.append("Consider relaxing thresholds by 10-15% to capture more opportunities")
                actions.append("Increase position sizing confidence for high-similarity patterns")
        
        if not actions:
            actions.append("Continue monitoring - pattern evolution within acceptable bounds")
        
        return actions

# Factory function for easy import
async def get_pattern_learner() -> PatternLearner:
    """Get initialized pattern learner instance"""
    learner = PatternLearner()
    await learner.initialize_pattern_memory()
    return learner