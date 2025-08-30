#!/usr/bin/env python3
"""
Pattern Memory Integration Service
Integrates pattern memory system with existing discovery algorithm to maintain explosive edge.

Mission: Connect pattern learning feedback loops with real-time discovery for continuous improvement.
"""

import os
import json
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import logging

from .pattern_learner import get_pattern_learner
from .feedback_integration import get_feedback_integrator
from ..shared.database import get_db_pool
from ..shared.redis_client import get_redis_client

logger = logging.getLogger(__name__)

class PatternMemoryIntegrator:
    """
    Integrates pattern memory with discovery algorithm:
    1. Provides adaptive thresholds based on historical performance
    2. Enhances pattern scoring with historical similarity
    3. Auto-logs discoveries for continuous learning
    4. Provides real-time pattern evolution feedback
    """
    
    def __init__(self):
        self.redis_client = get_redis_client()
        self.pattern_learner = None
        self.feedback_integrator = None
        self.adaptive_params_cache = {}
        self.similarity_cache = {}
        
    async def initialize(self):
        """Initialize pattern memory integration"""
        self.pattern_learner = await get_pattern_learner()
        self.feedback_integrator = await get_feedback_integrator()
        await self._load_adaptive_parameters()
        logger.info("Pattern memory integration initialized")
    
    async def enhance_discovery_scoring(self, candidates: List[Dict]) -> List[Dict]:
        """
        Enhance discovery candidates with pattern memory insights.
        Called by discovery algorithm to improve scoring accuracy.
        """
        try:
            if not candidates:
                return candidates
            
            enhanced_candidates = []
            
            for candidate in candidates:
                try:
                    # Get historical pattern similarity
                    similarity_boost = await self._get_pattern_similarity_boost(candidate)
                    
                    # Apply adaptive threshold adjustments
                    threshold_adjustment = await self._get_threshold_adjustment(candidate)
                    
                    # Calculate enhanced score
                    original_score = candidate.get('score', 0.0)
                    vigl_score = candidate.get('vigl_score', 0.0)
                    
                    # Pattern memory composite scoring
                    memory_enhanced_score = self._calculate_memory_enhanced_score(
                        original_score, vigl_score, similarity_boost, threshold_adjustment
                    )
                    
                    # Add pattern memory metadata
                    enhanced_candidate = candidate.copy()
                    enhanced_candidate.update({
                        'memory_enhanced_score': memory_enhanced_score,
                        'pattern_similarity_boost': similarity_boost,
                        'threshold_adjustment': threshold_adjustment,
                        'memory_enhanced': True,
                        'historical_similarity': await self._get_top_historical_matches(candidate, limit=3)
                    })
                    
                    # Override original score with memory-enhanced score
                    enhanced_candidate['score'] = memory_enhanced_score
                    
                    enhanced_candidates.append(enhanced_candidate)
                    
                except Exception as e:
                    logger.error(f"Error enhancing candidate {candidate.get('symbol', 'UNKNOWN')}: {e}")
                    # Keep original candidate if enhancement fails
                    enhanced_candidates.append(candidate)
            
            # Sort by memory-enhanced scores
            enhanced_candidates.sort(key=lambda x: x.get('memory_enhanced_score', x.get('score', 0)), reverse=True)
            
            logger.info(f"Enhanced {len(enhanced_candidates)} discovery candidates with pattern memory")
            return enhanced_candidates
            
        except Exception as e:
            logger.error(f"Error in discovery enhancement: {e}")
            return candidates  # Return original candidates if enhancement fails
    
    async def log_discovery_batch(self, discovery_candidates: List[Dict], discovery_metadata: Dict) -> Dict:
        """
        Auto-log discovery batch for pattern learning.
        Called after each discovery run to maintain learning feedback.
        """
        try:
            logged_count = 0
            learning_entries = []
            
            for candidate in discovery_candidates:
                symbol = candidate.get('symbol')
                if not symbol:
                    continue
                
                # Prepare learning entry data
                learning_entry = {
                    'symbol': symbol,
                    'discovery_timestamp': datetime.now(),
                    'pattern_data': {
                        'vigl_score': candidate.get('vigl_score', 0.0),
                        'squeeze_score': candidate.get('squeeze_score', 0.0),
                        'volume_spike': candidate.get('volume_spike', 1.0),
                        'short_interest': candidate.get('factors', {}).get('short_interest', 0.0),
                        'float_shares': candidate.get('factors', {}).get('float_shares', 50000000),
                        'compression_pct': candidate.get('compression_pct', 0.0),
                        'atr_pct': candidate.get('atr_pct', 0.0),
                        'wolf_risk': candidate.get('wolf_risk', 0.0),
                        'pattern_score': candidate.get('score', 0.0),
                        'memory_enhanced_score': candidate.get('memory_enhanced_score', 0.0)
                    },
                    'discovery_metadata': {
                        'discovery_run_id': discovery_metadata.get('run_id', 'unknown'),
                        'discovery_source': 'automated_discovery',
                        'market_time': discovery_metadata.get('market_time', 'unknown'),
                        'discovery_reason': candidate.get('reason', 'pattern_match'),
                        'thesis': candidate.get('thesis', f'{symbol} discovery candidate')
                    }
                }
                
                learning_entries.append(learning_entry)
                logged_count += 1
            
            # Store discovery batch in database for tracking
            if learning_entries:
                await self._store_discovery_batch(learning_entries)
            
            # Cache discovery data for potential trade logging
            discovery_cache_data = {
                'discovery_timestamp': datetime.now().isoformat(),
                'candidates': discovery_candidates,
                'metadata': discovery_metadata,
                'logged_count': logged_count
            }
            
            self.redis_client.setex(
                f"discovery:batch:{datetime.now().strftime('%Y%m%d_%H%M')}",
                86400 * 7,  # 7 day TTL
                json.dumps(discovery_cache_data, default=str)
            )
            
            logger.info(f"Logged discovery batch: {logged_count} candidates")
            
            return {
                'success': True,
                'logged_candidates': logged_count,
                'learning_entries': len(learning_entries),
                'discovery_batch_cached': True
            }
            
        except Exception as e:
            logger.error(f"Error logging discovery batch: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_discovery_optimization_feedback(self) -> Dict:
        """
        Get optimization feedback for discovery algorithm based on recent pattern performance.
        Provides adaptive recommendations to maintain explosive edge.
        """
        try:
            # Get recent pattern evolution analysis
            evolution_data = await self.pattern_learner.detect_pattern_evolution(30)
            
            # Get adaptive thresholds
            adaptive_thresholds = await self.pattern_learner.get_adaptive_thresholds('squeeze')
            
            # Analyze recent discovery performance
            performance_analysis = await self._analyze_recent_discovery_performance()
            
            # Generate optimization recommendations
            optimization_feedback = {
                'timestamp': datetime.now().isoformat(),
                'evolution_analysis': evolution_data,
                'adaptive_thresholds': adaptive_thresholds.get('thresholds', {}),
                'performance_analysis': performance_analysis,
                'optimization_recommendations': self._generate_optimization_recommendations(
                    evolution_data, adaptive_thresholds, performance_analysis
                ),
                'system_health': self._assess_discovery_system_health(performance_analysis)
            }
            
            # Cache optimization feedback
            self.redis_client.setex(
                "discovery:optimization_feedback",
                3600,  # 1 hour TTL
                json.dumps(optimization_feedback, default=str)
            )
            
            return {
                'success': True,
                'optimization_feedback': optimization_feedback,
                'recommendations_count': len(optimization_feedback['optimization_recommendations'])
            }
            
        except Exception as e:
            logger.error(f"Error getting discovery optimization feedback: {e}")
            return {'success': False, 'error': str(e)}
    
    async def integrate_trade_execution(self, symbol: str, trade_data: Dict) -> Dict:
        """
        Integrate with trade execution to auto-log trades with discovery context.
        Called when trades are executed to maintain learning loop.
        """
        try:
            # Get discovery context for this symbol
            discovery_context = await self._get_discovery_context(symbol)
            
            # Enhance trade data with discovery pattern information
            enhanced_trade_data = trade_data.copy()
            enhanced_trade_data.update({
                'discovery_data': discovery_context.get('discovery_data', {}),
                'pattern_data': discovery_context.get('pattern_data', {}),
                'source': 'pattern_memory_integration'
            })
            
            # Log trade entry with pattern context
            if self.feedback_integrator:
                entry_result = await self.feedback_integrator.log_trade_entry(symbol, enhanced_trade_data)
            else:
                entry_result = {'success': False, 'error': 'Feedback integrator not available'}
            
            return {
                'success': entry_result.get('success', False),
                'trade_logged': entry_result.get('entry_logged', False),
                'pattern_tracking_active': entry_result.get('tracking_active', False),
                'discovery_context_included': bool(discovery_context),
                'integration_complete': True
            }
            
        except Exception as e:
            logger.error(f"Error integrating trade execution for {symbol}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _get_pattern_similarity_boost(self, candidate: Dict) -> float:
        """Get pattern similarity boost based on historical explosive winners"""
        try:
            symbol = candidate.get('symbol', 'UNKNOWN')
            
            # Check cache first
            cache_key = f"similarity:{symbol}"
            if cache_key in self.similarity_cache:
                return self.similarity_cache[cache_key]
            
            # Prepare pattern data for similarity analysis
            current_data = {
                'symbol': symbol,
                'volume_spike': candidate.get('volume_spike', 1.0),
                'short_interest': candidate.get('factors', {}).get('short_interest', 0.0),
                'float_shares': candidate.get('factors', {}).get('float_shares', 50000000),
                'squeeze_score': candidate.get('squeeze_score', 0.0),
                'price': candidate.get('price', 5.0),
                'vigl_similarity': candidate.get('vigl_similarity', 0.0)
            }
            
            # Find similar historical patterns
            similar_patterns = await self.pattern_learner.find_similar_patterns(
                current_data, min_similarity=0.70
            )
            
            if not similar_patterns:
                boost = 0.0
            else:
                # Calculate boost based on best matches
                top_matches = similar_patterns[:3]  # Top 3 matches
                avg_expected_return = sum(match.expected_return for match in top_matches) / len(top_matches)
                avg_similarity = sum(match.similarity_score for match in top_matches) / len(top_matches)
                
                # Convert to boost factor (0.0 to 0.3 range)
                boost = min(0.3, (avg_expected_return / 100.0) * avg_similarity)
            
            # Cache result
            self.similarity_cache[cache_key] = boost
            
            return boost
            
        except Exception as e:
            logger.error(f"Error getting pattern similarity boost: {e}")
            return 0.0
    
    async def _get_threshold_adjustment(self, candidate: Dict) -> float:
        """Get threshold adjustment based on adaptive learning"""
        try:
            # Get cached adaptive parameters
            adaptive_params = await self._get_cached_adaptive_parameters()
            
            if not adaptive_params:
                return 0.0
            
            # Calculate adjustment based on how candidate compares to adaptive thresholds
            vigl_score = candidate.get('vigl_score', 0.0)
            volume_spike = candidate.get('volume_spike', 1.0)
            squeeze_score = candidate.get('squeeze_score', 0.0)
            
            adaptive_vigl_threshold = adaptive_params.get('vigl_threshold', 0.65)
            adaptive_volume_threshold = adaptive_params.get('explosive_volume_min', 5.0)
            adaptive_squeeze_threshold = adaptive_params.get('squeeze_score_min', 0.70)
            
            # Calculate how much candidate exceeds adaptive thresholds
            vigl_excess = max(0, vigl_score - adaptive_vigl_threshold) / adaptive_vigl_threshold
            volume_excess = max(0, volume_spike - adaptive_volume_threshold) / adaptive_volume_threshold
            squeeze_excess = max(0, squeeze_score - adaptive_squeeze_threshold) / adaptive_squeeze_threshold
            
            # Weighted adjustment (0.0 to 0.2 range)
            adjustment = min(0.2, (vigl_excess * 0.4 + volume_excess * 0.3 + squeeze_excess * 0.3) * 0.2)
            
            return adjustment
            
        except Exception as e:
            logger.error(f"Error getting threshold adjustment: {e}")
            return 0.0
    
    def _calculate_memory_enhanced_score(self, original_score: float, vigl_score: float, 
                                       similarity_boost: float, threshold_adjustment: float) -> float:
        """Calculate memory-enhanced composite score"""
        # Base score with pattern memory enhancements
        base_score = original_score
        
        # Apply similarity boost (historical pattern matching)
        similarity_enhanced = base_score + (base_score * similarity_boost)
        
        # Apply threshold adjustment (adaptive learning)
        threshold_enhanced = similarity_enhanced + threshold_adjustment
        
        # Apply VIGL pattern weighting
        vigl_weighted = threshold_enhanced * (1.0 + (vigl_score * 0.2))
        
        # Ensure score stays in reasonable range
        final_score = min(max(vigl_weighted, 0.0), 1.0)
        
        return round(final_score, 4)
    
    async def _get_top_historical_matches(self, candidate: Dict, limit: int = 3) -> List[Dict]:
        """Get top historical pattern matches for candidate"""
        try:
            symbol = candidate.get('symbol', 'UNKNOWN')
            current_data = {
                'symbol': symbol,
                'volume_spike': candidate.get('volume_spike', 1.0),
                'short_interest': candidate.get('factors', {}).get('short_interest', 0.0),
                'float_shares': candidate.get('factors', {}).get('float_shares', 50000000),
                'squeeze_score': candidate.get('squeeze_score', 0.0),
                'price': candidate.get('price', 5.0)
            }
            
            similar_patterns = await self.pattern_learner.find_similar_patterns(
                current_data, min_similarity=0.60
            )
            
            top_matches = []
            for match in similar_patterns[:limit]:
                top_matches.append({
                    'historical_symbol': match.symbol,
                    'similarity_score': round(match.similarity_score, 3),
                    'expected_return': round(match.expected_return, 1),
                    'historical_return': match.historical_pattern.get('outcome_pct', 0),
                    'days_to_peak': match.historical_pattern.get('days_held', 0)
                })
            
            return top_matches
            
        except Exception as e:
            logger.error(f"Error getting top historical matches: {e}")
            return []
    
    async def _store_discovery_batch(self, learning_entries: List[Dict]):
        """Store discovery batch in database for tracking"""
        try:
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                for entry in learning_entries:
                    symbol = entry['symbol']
                    pattern_data = entry['pattern_data']
                    discovery_metadata = entry['discovery_metadata']
                    
                    await conn.execute("""
                        INSERT INTO squeeze_patterns 
                        (symbol, pattern_date, volume_spike, short_interest, float_shares,
                         entry_price, pattern_score, squeeze_score, vigl_similarity,
                         pattern_hash, sector, notes, created_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, NOW())
                        ON CONFLICT (symbol, pattern_date) DO NOTHING
                    """,
                        symbol, entry['discovery_timestamp'].date(),
                        pattern_data.get('volume_spike', 1.0),
                        pattern_data.get('short_interest', 0.0),
                        pattern_data.get('float_shares', 50000000),
                        0.0,  # No entry price yet - this is just discovery
                        pattern_data.get('pattern_score', 0.0),
                        pattern_data.get('squeeze_score', 0.0),
                        pattern_data.get('vigl_similarity', 0.0),
                        f"discovery_{datetime.now().strftime('%Y%m%d')}_{symbol}",
                        'Unknown',
                        f"Discovery logged - {discovery_metadata.get('discovery_reason', 'pattern_match')}"
                    )
                    
        except Exception as e:
            logger.error(f"Error storing discovery batch: {e}")
    
    async def _analyze_recent_discovery_performance(self) -> Dict:
        """Analyze recent discovery performance for optimization"""
        try:
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                # Get recent discovery performance (last 30 days)
                performance_data = await conn.fetchrow("""
                    SELECT 
                        COUNT(*) as total_discoveries,
                        COUNT(*) FILTER (WHERE success = TRUE) as successful_discoveries,
                        COUNT(*) FILTER (WHERE explosive = TRUE) as explosive_discoveries,
                        AVG(outcome_pct) FILTER (WHERE outcome_pct IS NOT NULL) as avg_return,
                        AVG(squeeze_score) as avg_squeeze_score,
                        AVG(vigl_similarity) as avg_vigl_similarity
                    FROM squeeze_patterns
                    WHERE created_at >= NOW() - INTERVAL '30 days'
                        AND notes LIKE 'Discovery logged%'
                """)
            
            if not performance_data or performance_data['total_discoveries'] == 0:
                return {'analysis_available': False, 'reason': 'Insufficient discovery data'}
            
            total = performance_data['total_discoveries']
            success_rate = (performance_data['successful_discoveries'] or 0) / total
            explosive_rate = (performance_data['explosive_discoveries'] or 0) / total
            
            return {
                'analysis_available': True,
                'total_discoveries': total,
                'success_rate': round(success_rate, 3),
                'explosive_rate': round(explosive_rate, 3),
                'avg_return': round(performance_data['avg_return'] or 0, 1),
                'avg_squeeze_score': round(performance_data['avg_squeeze_score'] or 0, 3),
                'avg_vigl_similarity': round(performance_data['avg_vigl_similarity'] or 0, 3),
                'analysis_period_days': 30
            }
            
        except Exception as e:
            logger.error(f"Error analyzing recent discovery performance: {e}")
            return {'analysis_available': False, 'error': str(e)}
    
    def _generate_optimization_recommendations(self, evolution_data: Dict, adaptive_thresholds: Dict, 
                                             performance_analysis: Dict) -> List[Dict]:
        """Generate optimization recommendations based on analysis"""
        recommendations = []
        
        # Pattern evolution recommendations
        if evolution_data.get('evolution_detected'):
            for alert in evolution_data.get('evolution_alerts', []):
                if alert.get('severity') == 'CRITICAL':
                    recommendations.append({
                        'type': 'CRITICAL_ADJUSTMENT',
                        'recommendation': 'Immediate threshold review required',
                        'reason': alert.get('message'),
                        'priority': 'HIGH'
                    })
        
        # Performance-based recommendations
        if performance_analysis.get('analysis_available'):
            success_rate = performance_analysis.get('success_rate', 0)
            explosive_rate = performance_analysis.get('explosive_rate', 0)
            
            if success_rate < 0.3:
                recommendations.append({
                    'type': 'THRESHOLD_TIGHTENING',
                    'recommendation': 'Tighten detection thresholds - success rate too low',
                    'current_success_rate': success_rate,
                    'target_success_rate': 0.4,
                    'priority': 'HIGH'
                })
            
            if explosive_rate < 0.1:
                recommendations.append({
                    'type': 'PATTERN_REFINEMENT', 
                    'recommendation': 'Refine explosive pattern detection - missing big winners',
                    'current_explosive_rate': explosive_rate,
                    'target_explosive_rate': 0.15,
                    'priority': 'MEDIUM'
                })
        
        # Adaptive threshold recommendations
        performance_basis = adaptive_thresholds.get('performance_basis', {})
        if performance_basis.get('success_rate', 0) > 0.7:
            recommendations.append({
                'type': 'THRESHOLD_RELAXATION',
                'recommendation': 'Consider relaxing thresholds - high success rate indicates conservative settings',
                'current_performance': performance_basis,
                'priority': 'LOW'
            })
        
        return recommendations
    
    def _assess_discovery_system_health(self, performance_analysis: Dict) -> Dict:
        """Assess overall discovery system health"""
        if not performance_analysis.get('analysis_available'):
            return {'status': 'UNKNOWN', 'reason': 'Insufficient data'}
        
        success_rate = performance_analysis.get('success_rate', 0)
        explosive_rate = performance_analysis.get('explosive_rate', 0)
        avg_return = performance_analysis.get('avg_return', 0)
        
        # Health scoring
        if success_rate >= 0.6 and explosive_rate >= 0.15 and avg_return >= 30:
            status = 'EXCELLENT'
            health_score = 0.9
        elif success_rate >= 0.4 and explosive_rate >= 0.10 and avg_return >= 15:
            status = 'GOOD'
            health_score = 0.7
        elif success_rate >= 0.3 and explosive_rate >= 0.05:
            status = 'FAIR'
            health_score = 0.5
        else:
            status = 'NEEDS_ATTENTION'
            health_score = 0.3
        
        return {
            'status': status,
            'health_score': health_score,
            'key_metrics': {
                'success_rate': success_rate,
                'explosive_rate': explosive_rate,
                'avg_return': avg_return
            },
            'assessment_date': datetime.now().isoformat()
        }
    
    async def _get_discovery_context(self, symbol: str) -> Dict:
        """Get discovery context for a symbol from cached discovery data"""
        try:
            # Search recent discovery batches for this symbol
            discovery_keys = self.redis_client.keys("discovery:batch:*")
            
            for key in discovery_keys:
                batch_data = self.redis_client.get(key)
                if batch_data:
                    batch = json.loads(batch_data.decode())
                    
                    for candidate in batch.get('candidates', []):
                        if candidate.get('symbol') == symbol:
                            return {
                                'discovery_data': candidate,
                                'pattern_data': {
                                    'vigl_score': candidate.get('vigl_score', 0.0),
                                    'squeeze_score': candidate.get('squeeze_score', 0.0),
                                    'volume_spike': candidate.get('volume_spike', 1.0)
                                },
                                'discovery_metadata': batch.get('metadata', {})
                            }
            
            return {}
            
        except Exception as e:
            logger.error(f"Error getting discovery context for {symbol}: {e}")
            return {}
    
    async def _load_adaptive_parameters(self):
        """Load adaptive parameters into cache"""
        try:
            if self.pattern_learner:
                adaptive_data = await self.pattern_learner.get_adaptive_thresholds('squeeze')
                self.adaptive_params_cache = adaptive_data.get('thresholds', {})
                
        except Exception as e:
            logger.error(f"Error loading adaptive parameters: {e}")
    
    async def _get_cached_adaptive_parameters(self) -> Dict:
        """Get cached adaptive parameters"""
        if not self.adaptive_params_cache:
            await self._load_adaptive_parameters()
        
        return self.adaptive_params_cache

# Factory function
async def get_pattern_memory_integrator() -> PatternMemoryIntegrator:
    """Get initialized pattern memory integrator instance"""
    integrator = PatternMemoryIntegrator()
    await integrator.initialize()
    return integrator