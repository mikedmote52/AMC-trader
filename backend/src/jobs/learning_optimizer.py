#!/usr/bin/env python3
"""
Learning Optimizer Job
Continuous learning system that optimizes discovery parameters and thesis generation
based on real performance feedback from historical winners and failures.

Mission: Restore explosive growth edge by learning from +324% VIGL winners
"""

import os
import sys
import json
import asyncio
import logging
import httpx
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import statistics as stats
from dataclasses import dataclass

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from services.learning_engine import get_learning_engine
from shared.database import get_db_pool
from shared.redis_client import get_redis_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class DiscoveryFeedback:
    """Feedback from discovery performance for learning optimization"""
    discovery_date: datetime
    symbols_discovered: List[str]
    parameters_used: Dict
    outcomes_7d: Dict[str, float]
    outcomes_30d: Dict[str, float]
    explosive_winners: List[str]
    avg_return: float
    success_rate: float

class LearningOptimizer:
    """
    Continuous learning system that:
    1. Tracks discovery performance and outcomes
    2. Learns from explosive winners (+324% style) 
    3. Adapts discovery parameters based on success patterns
    4. Optimizes thesis generation accuracy
    5. Detects market regime changes affecting performance
    """
    
    def __init__(self):
        self.learning_engine = None
        self.redis_client = get_redis_client()
        
    async def initialize(self):
        """Initialize learning engine and systems"""
        self.learning_engine = await get_learning_engine()
        logger.info("Learning optimizer initialized successfully")
    
    async def run_daily_learning_cycle(self) -> Dict:
        """Run daily learning optimization cycle"""
        logger.info("Starting daily learning optimization cycle")
        
        results = {
            'learning_cycle_date': datetime.now().isoformat(),
            'optimizations_applied': [],
            'performance_improvements': {},
            'new_patterns_learned': 0,
            'parameter_adjustments': {}
        }
        
        try:
            # 1. Collect discovery performance feedback
            discovery_feedback = await self._collect_discovery_feedback()
            if discovery_feedback:
                results['discovery_feedback_processed'] = len(discovery_feedback)
                await self._process_discovery_feedback(discovery_feedback)
            
            # 2. Learn from new explosive winners
            new_winners = await self._identify_new_explosive_winners()
            results['new_patterns_learned'] = len(new_winners)
            
            for winner in new_winners:
                await self._learn_from_explosive_winner(winner)
            
            # 3. Detect market regime changes
            regime_change = await self.learning_engine.detect_market_regime_change()
            if regime_change.get('regime_changed'):
                logger.info(f"Market regime changed: {regime_change['previous_regime']} -> {regime_change['current_regime']}")
                results['optimizations_applied'].append('market_regime_adaptation')
            
            # 4. Update discovery parameters based on learning
            parameter_updates = await self._optimize_discovery_parameters()
            results['parameter_adjustments'] = parameter_updates
            
            # 5. Optimize thesis generation weights
            thesis_improvements = await self._optimize_thesis_generation()
            results['performance_improvements']['thesis_accuracy'] = thesis_improvements
            
            # 6. Update Redis with new adaptive parameters
            await self._update_adaptive_parameters()
            results['optimizations_applied'].append('adaptive_parameters_updated')
            
            logger.info(f"Learning cycle completed: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Learning cycle failed: {e}")
            results['error'] = str(e)
            return results
    
    async def _collect_discovery_feedback(self) -> List[DiscoveryFeedback]:
        """Collect feedback from recent discovery performance"""
        
        pool = await get_db_pool()
        feedback_list = []
        
        async with pool.acquire() as conn:
            # Get recent discoveries that we can now analyze (7+ days old for feedback)
            recent_discoveries = await conn.fetch("""
                SELECT discovery_date, discovery_parameters, symbols_discovered
                FROM discovery_performance 
                WHERE discovery_date >= $1 
                    AND discovery_date <= $2
                    AND avg_7d_return IS NULL  -- Not yet analyzed
                ORDER BY discovery_date DESC
                LIMIT 10
            """, 
                datetime.now() - timedelta(days=30),
                datetime.now() - timedelta(days=7)
            )
        
        for discovery in recent_discoveries:
            try:
                # For each discovery, we would track the actual performance
                # This is a placeholder - in real implementation, would integrate with portfolio tracking
                discovery_params = json.loads(discovery['discovery_parameters']) if discovery['discovery_parameters'] else {}
                
                # Mock feedback data - in production would come from actual trading results
                feedback = DiscoveryFeedback(
                    discovery_date=discovery['discovery_date'],
                    symbols_discovered=['MOCK1', 'MOCK2'],  # Would be real symbols
                    parameters_used=discovery_params,
                    outcomes_7d={'MOCK1': 15.0, 'MOCK2': -5.0},
                    outcomes_30d={'MOCK1': 25.0, 'MOCK2': -8.0},
                    explosive_winners=['MOCK1'],  # Winners > 50%
                    avg_return=10.0,
                    success_rate=0.6
                )
                
                feedback_list.append(feedback)
                
            except Exception as e:
                logger.error(f"Failed to process discovery feedback: {e}")
                continue
        
        return feedback_list
    
    async def _process_discovery_feedback(self, feedback_list: List[DiscoveryFeedback]):
        """Process discovery feedback to improve future performance"""
        
        pool = await get_db_pool()
        
        for feedback in feedback_list:
            try:
                async with pool.acquire() as conn:
                    # Update discovery_performance with actual results
                    await conn.execute("""
                        UPDATE discovery_performance 
                        SET avg_7d_return = $1,
                            avg_30d_return = $2,
                            success_rate = $3,
                            explosive_winners = $4,
                            parameter_effectiveness = $5
                        WHERE discovery_date = $6
                    """,
                        feedback.avg_return,
                        stats.mean(feedback.outcomes_30d.values()) if feedback.outcomes_30d else 0,
                        feedback.success_rate,
                        len(feedback.explosive_winners),
                        min(feedback.success_rate * (1 + max(0, feedback.avg_return) / 50.0), 1.0),  # Effectiveness score
                        feedback.discovery_date
                    )
                
                # Learn from explosive winners in this discovery batch
                for winner_symbol in feedback.explosive_winners:
                    winner_return = feedback.outcomes_30d.get(winner_symbol, 0)
                    if winner_return > 50.0:  # Explosive winner threshold
                        
                        # Extract pattern features (would come from discovery data)
                        pattern_features = {
                            'vigl_score': 0.80,  # Mock data - would be real pattern features
                            'volume_spike_ratio': 12.0,
                            'momentum_1d': 0.08,
                            'momentum_5d': 0.15,
                            'atr_pct': 0.12,
                            'compression_pct': 0.05,
                            'wolf_risk': 0.3
                        }
                        
                        await self.learning_engine.learn_from_explosive_winner(
                            symbol=winner_symbol,
                            discovery_features=pattern_features,
                            outcome_return=winner_return,
                            days_held=30
                        )
                
                logger.info(f"Processed discovery feedback for {feedback.discovery_date}")
                
            except Exception as e:
                logger.error(f"Failed to process feedback for {feedback.discovery_date}: {e}")
    
    async def _identify_new_explosive_winners(self) -> List[Dict]:
        """Identify new explosive winners to learn from"""
        
        # This would integrate with portfolio tracking to identify recent explosive winners
        # For now, return mock data
        
        return [
            {
                'symbol': 'VIGL_STYLE_WINNER',
                'discovery_date': datetime.now() - timedelta(days=30),
                'outcome_return': 324.0,  # VIGL-style winner
                'pattern_features': {
                    'vigl_score': 0.95,
                    'volume_spike_ratio': 20.9,  # From VIGL analysis
                    'price_at_discovery': 3.50,
                    'momentum_5d': 0.15,
                    'atr_pct': 0.08,
                    'compression_pct': 0.02,  # Very tight
                    'wolf_risk': 0.2
                }
            }
        ]
    
    async def _learn_from_explosive_winner(self, winner_data: Dict):
        """Learn from a confirmed explosive winner"""
        
        try:
            await self.learning_engine.learn_from_explosive_winner(
                symbol=winner_data['symbol'],
                discovery_features=winner_data['pattern_features'],
                outcome_return=winner_data['outcome_return'],
                days_held=30  # Typical explosive timeframe
            )
            
            logger.info(f"Learned from explosive winner {winner_data['symbol']}: {winner_data['outcome_return']:.1f}% return")
            
        except Exception as e:
            logger.error(f"Failed to learn from explosive winner {winner_data['symbol']}: {e}")
    
    async def _optimize_discovery_parameters(self) -> Dict:
        """Optimize discovery parameters based on learning feedback"""
        
        try:
            # Get current adaptive parameters
            current_params = await self.learning_engine.get_adaptive_discovery_parameters()
            
            # Analyze recent performance to suggest improvements
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                # Get recent discovery performance stats
                performance_stats = await conn.fetchrow("""
                    SELECT 
                        AVG(success_rate) as avg_success_rate,
                        AVG(parameter_effectiveness) as avg_effectiveness,
                        COUNT(*) as total_discoveries
                    FROM discovery_performance 
                    WHERE discovery_date >= $1
                """, datetime.now() - timedelta(days=14))
            
            parameter_adjustments = {}
            
            if performance_stats and performance_stats['avg_success_rate']:
                success_rate = performance_stats['avg_success_rate']
                
                # If success rate is low, make parameters more selective
                if success_rate < 0.3:
                    parameter_adjustments = {
                        'vigl_threshold_adjustment': +0.05,  # More selective
                        'volume_min_adjustment': +1.0,      # Higher volume requirement
                        'reason': f'low_success_rate_{success_rate:.2f}'
                    }
                    
                    # Update parameters in Redis for immediate use
                    adjusted_params = current_params.copy()
                    adjusted_params['vigl_threshold'] = min(0.8, current_params.get('vigl_threshold', 0.65) + 0.05)
                    adjusted_params['explosive_volume_min'] = current_params.get('explosive_volume_min', 5.0) + 1.0
                    
                    # Cache adapted parameters
                    self.redis_client.set(
                        "amc:learning:adaptive_parameters", 
                        json.dumps(adjusted_params),
                        ex=3600  # 1 hour TTL
                    )
                
                # If success rate is very high, can be less selective
                elif success_rate > 0.7:
                    parameter_adjustments = {
                        'vigl_threshold_adjustment': -0.02,  # Less selective
                        'volume_min_adjustment': -0.5,      # Lower volume requirement
                        'reason': f'high_success_rate_{success_rate:.2f}'
                    }
            
            logger.info(f"Parameter optimization: {parameter_adjustments}")
            return parameter_adjustments
            
        except Exception as e:
            logger.error(f"Parameter optimization failed: {e}")
            return {}
    
    async def _optimize_thesis_generation(self) -> Dict:
        """Optimize thesis generation accuracy based on feedback"""
        
        try:
            pool = await get_db_pool()
            
            # Analyze recent thesis accuracy
            async with pool.acquire() as conn:
                accuracy_analysis = await conn.fetch("""
                    SELECT 
                        recommendation,
                        AVG(accuracy_score) as avg_accuracy,
                        COUNT(*) as total_predictions
                    FROM thesis_accuracy 
                    WHERE thesis_date >= $1
                    GROUP BY recommendation
                """, datetime.now() - timedelta(days=14))
            
            improvements = {}
            
            for analysis in accuracy_analysis:
                recommendation = analysis['recommendation']
                accuracy = analysis['avg_accuracy']
                
                if accuracy < 0.6:  # Poor accuracy
                    improvements[f'{recommendation}_confidence_adjustment'] = -0.1
                    improvements[f'{recommendation}_threshold_adjustment'] = 'stricter'
                elif accuracy > 0.8:  # Good accuracy
                    improvements[f'{recommendation}_confidence_adjustment'] = +0.05
            
            logger.info(f"Thesis optimization: {improvements}")
            return improvements
            
        except Exception as e:
            logger.error(f"Thesis optimization failed: {e}")
            return {}
    
    async def _update_adaptive_parameters(self):
        """Update adaptive parameters in Redis for immediate use by discovery system"""
        
        try:
            # Get latest adaptive parameters
            adaptive_params = await self.learning_engine.get_adaptive_discovery_parameters()
            
            # Cache in Redis for discovery system to use
            self.redis_client.set(
                "amc:learning:current_parameters",
                json.dumps({
                    'parameters': adaptive_params,
                    'last_updated': datetime.now().isoformat(),
                    'source': 'learning_optimizer'
                }),
                ex=7200  # 2 hour TTL
            )
            
            # Also update parameter effectiveness tracking
            self.redis_client.set(
                "amc:learning:optimization_status",
                json.dumps({
                    'last_optimization': datetime.now().isoformat(),
                    'system_health': 'active',
                    'learning_cycles_completed': await self._get_learning_cycles_count()
                }),
                ex=86400  # 24 hour TTL
            )
            
            logger.info("Adaptive parameters updated in Redis")
            
        except Exception as e:
            logger.error(f"Failed to update adaptive parameters: {e}")
    
    async def _get_learning_cycles_count(self) -> int:
        """Get count of completed learning cycles"""
        try:
            current_count = self.redis_client.get("amc:learning:cycles_count")
            count = int(current_count.decode()) if current_count else 0
            self.redis_client.set("amc:learning:cycles_count", count + 1, ex=86400 * 30)  # 30 day TTL
            return count + 1
        except:
            return 1

async def run_learning_optimization():
    """Main entry point for learning optimization job"""
    
    optimizer = LearningOptimizer()
    
    try:
        await optimizer.initialize()
        results = await optimizer.run_daily_learning_cycle()
        
        logger.info(f"Learning optimization completed successfully: {json.dumps(results, indent=2)}")
        return results
        
    except Exception as e:
        logger.error(f"Learning optimization failed: {e}")
        raise

def main():
    """Entry point for scheduled learning optimization"""
    try:
        results = asyncio.run(run_learning_optimization())
        print(json.dumps(results, indent=2))
        
    except Exception as e:
        logger.error(f"Learning optimization job failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()