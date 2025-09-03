#!/usr/bin/env python3
"""
Recommendation Tracker - Zero Disruption Learning System
Tracks ALL discovery recommendations (bought/unbought) for 30 days
Identifies missed opportunities and feeds learning system
"""

import asyncio
import json
import logging
import httpx
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from ..shared.database import get_db_pool
from ..shared.redis_client import get_redis_client

logger = logging.getLogger(__name__)

@dataclass
class RecommendationRecord:
    """Complete recommendation tracking record"""
    symbol: str
    recommendation_date: str
    discovery_price: float
    discovery_score: float
    discovery_reason: str
    thesis: str
    confidence: float
    
    # Portfolio status
    was_bought: bool
    buy_price: Optional[float]
    position_size: Optional[float]
    
    # Performance tracking
    performance_1h: Optional[float]
    performance_4h: Optional[float] 
    performance_1d: Optional[float]
    performance_3d: Optional[float]
    performance_7d: Optional[float]
    performance_14d: Optional[float]
    performance_30d: Optional[float]
    
    # Classification
    outcome_classification: str  # EXPLOSIVE, STRONG, MODERATE, POOR, FAILED
    peak_return: Optional[float]
    days_to_peak: Optional[int]
    
    # Learning data
    missed_opportunity: bool
    learning_insights: List[str]

class RecommendationTracker:
    """
    Tracks all discovery recommendations for learning
    ZERO IMPACT on existing trading - only monitors outcomes
    """
    
    def __init__(self):
        self.redis = get_redis_client()
        self.tracking_prefix = "amc:tracker:rec:"
        
    async def save_recommendation(self, candidate: Dict, from_portfolio: bool = False) -> str:
        """
        Save a new recommendation for tracking
        Called automatically when discovery generates candidates
        """
        try:
            symbol = candidate.get('symbol', '')
            if not symbol:
                return ""
            
            # Check if we already have this recommendation today
            rec_id = f"{symbol}_{datetime.now().strftime('%Y%m%d')}"
            existing_key = f"{self.tracking_prefix}{rec_id}"
            
            if self.redis.exists(existing_key):
                logger.debug(f"Recommendation {rec_id} already tracked today")
                return rec_id
            
            # Create recommendation record
            record = RecommendationRecord(
                symbol=symbol,
                recommendation_date=datetime.now().isoformat(),
                discovery_price=candidate.get('price', 0.0),
                discovery_score=candidate.get('squeeze_score', candidate.get('score', 0.0)),
                discovery_reason=candidate.get('reason', candidate.get('squeeze_pattern', '')),
                thesis=candidate.get('thesis', ''),
                confidence=candidate.get('confidence', 0.0),
                
                # Portfolio status (check if currently held)
                was_bought=from_portfolio,
                buy_price=None,
                position_size=None,
                
                # Performance tracking (to be updated)
                performance_1h=None,
                performance_4h=None,
                performance_1d=None,
                performance_3d=None,
                performance_7d=None,
                performance_14d=None,
                performance_30d=None,
                
                # Classification (to be determined)
                outcome_classification="PENDING",
                peak_return=None,
                days_to_peak=None,
                
                # Learning data
                missed_opportunity=False,
                learning_insights=[]
            )
            
            # Store in Redis with 35-day expiration
            self.redis.setex(existing_key, 35 * 86400, json.dumps(asdict(record)))
            
            # Store in database for permanent tracking
            await self._store_in_database(record)
            
            # Add to tracking queue for performance monitoring
            self.redis.lpush("amc:tracker:queue", rec_id)
            
            logger.info(f"Recommendation tracked: {symbol} at ${record.discovery_price:.2f}")
            return rec_id
            
        except Exception as e:
            logger.error(f"Failed to save recommendation (non-critical): {e}")
            return ""
    
    async def update_performance(self, symbol: str, date_str: str = None) -> bool:
        """
        Update performance data for a recommendation
        Called by background job - non-blocking
        """
        try:
            if not date_str:
                date_str = datetime.now().strftime('%Y%m%d')
            
            rec_id = f"{symbol}_{date_str}"
            key = f"{self.tracking_prefix}{rec_id}"
            
            # Get existing record
            record_data = self.redis.get(key)
            if not record_data:
                return False
            
            record = RecommendationRecord(**json.loads(record_data))
            
            # Get current price
            current_price = await self._get_current_price(symbol)
            if not current_price:
                return False
            
            # Calculate performance based on time elapsed
            rec_time = datetime.fromisoformat(record.recommendation_date)
            elapsed = datetime.now() - rec_time
            
            performance_pct = ((current_price - record.discovery_price) / record.discovery_price) * 100
            
            # Update appropriate time interval
            if elapsed <= timedelta(hours=1):
                record.performance_1h = performance_pct
            elif elapsed <= timedelta(hours=4):
                record.performance_4h = performance_pct
            elif elapsed <= timedelta(days=1):
                record.performance_1d = performance_pct
            elif elapsed <= timedelta(days=3):
                record.performance_3d = performance_pct
            elif elapsed <= timedelta(days=7):
                record.performance_7d = performance_pct
            elif elapsed <= timedelta(days=14):
                record.performance_14d = performance_pct
            elif elapsed <= timedelta(days=30):
                record.performance_30d = performance_pct
            
            # Update peak return if this is higher
            if record.peak_return is None or performance_pct > record.peak_return:
                record.peak_return = performance_pct
                record.days_to_peak = elapsed.days
            
            # Classify outcome after 30 days
            if elapsed >= timedelta(days=30) and record.outcome_classification == "PENDING":
                record.outcome_classification = self._classify_outcome(record.performance_30d)
                
                # Check if this was a missed opportunity
                if not record.was_bought and record.performance_30d > 15:
                    record.missed_opportunity = True
                    record.learning_insights.append(f"MISSED: {symbol} gained {record.performance_30d:.1f}% in 30 days")
                    
                    # Generate alert
                    await self._generate_missed_opportunity_alert(record)
            
            # Save updated record
            self.redis.setex(key, 35 * 86400, json.dumps(asdict(record)))
            await self._update_database_record(record)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update performance for {symbol}: {e}")
            return False
    
    def _classify_outcome(self, performance_30d: float) -> str:
        """Classify recommendation outcome based on 30-day performance"""
        if performance_30d is None:
            return "NO_DATA"
        elif performance_30d >= 50:
            return "EXPLOSIVE"
        elif performance_30d >= 20:
            return "STRONG"
        elif performance_30d >= 10:
            return "MODERATE"
        elif performance_30d >= -5:
            return "POOR"
        else:
            return "FAILED"
    
    async def _get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price from existing price service"""
        try:
            # Use existing Polygon integration
            async with httpx.AsyncClient() as client:
                # Try to get from existing API endpoint first
                response = await client.get(f"https://amc-trader.onrender.com/debug/polygon/{symbol}")
                if response.status_code == 200:
                    data = response.json()
                    return data.get('price', data.get('c'))
                
                # Fallback to direct Polygon call if needed
                import os
                api_key = os.getenv("POLYGON_API_KEY")
                if api_key:
                    polygon_url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/prev?apikey={api_key}"
                    response = await client.get(polygon_url)
                    if response.status_code == 200:
                        data = response.json()
                        results = data.get('results', [])
                        if results:
                            return results[0].get('c')
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get price for {symbol}: {e}")
            return None
    
    async def _store_in_database(self, record: RecommendationRecord):
        """Store recommendation in database for permanent tracking"""
        try:
            pool = await get_db_pool()
            if not pool:
                return
                
            async with pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO monitoring.recommendation_tracking 
                    (symbol, recommendation_date, discovery_price, discovery_score, discovery_reason,
                     thesis, confidence, was_bought, buy_price, position_size,
                     performance_1h, performance_4h, performance_1d, performance_3d, 
                     performance_7d, performance_14d, performance_30d,
                     outcome_classification, peak_return, days_to_peak,
                     missed_opportunity, learning_insights)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22)
                """, 
                    record.symbol,
                    datetime.fromisoformat(record.recommendation_date),
                    record.discovery_price,
                    record.discovery_score, 
                    record.discovery_reason,
                    record.thesis,
                    record.confidence,
                    record.was_bought,
                    record.buy_price,
                    record.position_size,
                    record.performance_1h,
                    record.performance_4h,
                    record.performance_1d,
                    record.performance_3d,
                    record.performance_7d,
                    record.performance_14d,
                    record.performance_30d,
                    record.outcome_classification,
                    record.peak_return,
                    record.days_to_peak,
                    record.missed_opportunity,
                    json.dumps(record.learning_insights)
                )
        except Exception as e:
            logger.error(f"Failed to store recommendation in database (non-critical): {e}")
    
    async def _update_database_record(self, record: RecommendationRecord):
        """Update existing database record"""
        try:
            pool = await get_db_pool()
            if not pool:
                return
                
            async with pool.acquire() as conn:
                await conn.execute("""
                    UPDATE monitoring.recommendation_tracking 
                    SET performance_1h = $3, performance_4h = $4, performance_1d = $5,
                        performance_3d = $6, performance_7d = $7, performance_14d = $8, 
                        performance_30d = $9, outcome_classification = $10,
                        peak_return = $11, days_to_peak = $12, missed_opportunity = $13,
                        learning_insights = $14
                    WHERE symbol = $1 AND recommendation_date = $2
                """, 
                    record.symbol,
                    datetime.fromisoformat(record.recommendation_date),
                    record.performance_1h,
                    record.performance_4h,
                    record.performance_1d,
                    record.performance_3d,
                    record.performance_7d,
                    record.performance_14d,
                    record.performance_30d,
                    record.outcome_classification,
                    record.peak_return,
                    record.days_to_peak,
                    record.missed_opportunity,
                    json.dumps(record.learning_insights)
                )
        except Exception as e:
            logger.error(f"Failed to update database record (non-critical): {e}")
    
    async def _generate_missed_opportunity_alert(self, record: RecommendationRecord):
        """Generate alert for missed opportunity"""
        try:
            alert_data = {
                'type': 'MISSED_OPPORTUNITY',
                'timestamp': datetime.now().isoformat(),
                'symbol': record.symbol,
                'performance': record.performance_30d,
                'discovery_price': record.discovery_price,
                'current_return': f"+{record.performance_30d:.1f}%",
                'message': f"MISSED: {record.symbol} gained {record.performance_30d:.1f}% in 30 days (not bought)",
                'learning_impact': 'HIGH'
            }
            
            # Store alert
            alert_key = "amc:tracker:alerts:missed"
            self.redis.lpush(alert_key, json.dumps(alert_data))
            self.redis.ltrim(alert_key, 0, 49)  # Keep last 50 alerts
            self.redis.expire(alert_key, 604800)  # 7 days
            
            # Publish for real-time notifications
            self.redis.publish("amc:alerts:missed_opportunity", json.dumps(alert_data))
            
            logger.info(f"Missed opportunity alert: {record.symbol} +{record.performance_30d:.1f}%")
            
        except Exception as e:
            logger.error(f"Failed to generate missed opportunity alert: {e}")
    
    async def get_missed_opportunities(self, days: int = 30) -> List[Dict]:
        """Get missed opportunities from the last N days"""
        try:
            pool = await get_db_pool()
            if not pool:
                return []
                
            async with pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT * FROM monitoring.recommendation_tracking 
                    WHERE missed_opportunity = true 
                    AND recommendation_date >= $1
                    ORDER BY performance_30d DESC
                    LIMIT 20
                """, datetime.now() - timedelta(days=days))
                
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get missed opportunities: {e}")
            return []
    
    async def get_learning_insights(self) -> Dict:
        """Generate learning insights from tracked recommendations"""
        try:
            pool = await get_db_pool()
            if not pool:
                return {}
                
            async with pool.acquire() as conn:
                # Overall performance stats
                stats = await conn.fetchrow("""
                    SELECT 
                        COUNT(*) as total_recommendations,
                        AVG(performance_30d) as avg_30d_performance,
                        COUNT(*) FILTER (WHERE outcome_classification = 'EXPLOSIVE') as explosive_count,
                        COUNT(*) FILTER (WHERE outcome_classification = 'STRONG') as strong_count,
                        COUNT(*) FILTER (WHERE missed_opportunity = true) as missed_count,
                        AVG(discovery_score) as avg_discovery_score
                    FROM monitoring.recommendation_tracking 
                    WHERE outcome_classification != 'PENDING'
                """)
                
                return {
                    'total_tracked': stats['total_recommendations'],
                    'avg_30d_performance': round(stats['avg_30d_performance'] or 0, 2),
                    'explosive_rate': round((stats['explosive_count'] or 0) / max(stats['total_recommendations'], 1), 3),
                    'success_rate': round(((stats['explosive_count'] or 0) + (stats['strong_count'] or 0)) / max(stats['total_recommendations'], 1), 3),
                    'missed_opportunities': stats['missed_count'],
                    'avg_discovery_score': round(stats['avg_discovery_score'] or 0, 3),
                    'learning_status': 'ACTIVE'
                }
        except Exception as e:
            logger.error(f"Failed to generate learning insights: {e}")
            return {'learning_status': 'ERROR', 'error': str(e)}

# Background job for performance updates
async def update_recommendation_performance():
    """Background job to update recommendation performance"""
    tracker = RecommendationTracker()
    
    while True:
        try:
            # Get recommendations from queue
            rec_id = tracker.redis.rpop("amc:tracker:queue")
            if rec_id:
                rec_id = rec_id.decode() if isinstance(rec_id, bytes) else rec_id
                symbol = rec_id.split('_')[0]
                date_str = rec_id.split('_')[1] if '_' in rec_id else None
                
                await tracker.update_performance(symbol, date_str)
            else:
                # No items in queue, wait a bit
                await asyncio.sleep(60)
                
        except Exception as e:
            logger.error(f"Performance update job error: {e}")
            await asyncio.sleep(60)

# Global tracker instance
_recommendation_tracker = None

def get_recommendation_tracker() -> RecommendationTracker:
    """Get singleton recommendation tracker instance"""
    global _recommendation_tracker
    if _recommendation_tracker is None:
        _recommendation_tracker = RecommendationTracker()
    return _recommendation_tracker