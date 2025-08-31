#!/usr/bin/env python3
"""
Feedback Integration System
Auto-logs all trades with pattern data and tracks outcomes for continuous learning.

Mission: Create seamless feedback loops to maintain explosive growth edge.
"""

import os
import json
import asyncio
import hashlib
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import logging

from .pattern_learner import get_pattern_learner
from ..shared.database import get_db_pool
from ..shared.redis_client import get_redis_client

logger = logging.getLogger(__name__)

@dataclass
class TradeEntry:
    """Trade entry record for pattern learning"""
    symbol: str
    entry_timestamp: datetime
    entry_price: float
    entry_data: Dict
    pattern_hash: str
    discovery_source: str
    position_size: float
    confidence: float

@dataclass
class TradeExit:
    """Trade exit record for outcome learning"""
    symbol: str
    exit_timestamp: datetime
    exit_price: float
    exit_reason: str
    days_held: int
    max_price_achieved: float
    return_pct: float
    pattern_success: bool

class FeedbackIntegrator:
    """
    Seamless feedback integration that:
    1. Auto-logs all trade entries with pattern data
    2. Tracks position outcomes and performance
    3. Feeds learning back to pattern detection
    4. Updates confidence scoring based on results
    5. Maintains continuous learning loop
    """
    
    def __init__(self):
        self.redis_client = get_redis_client()
        self.active_positions = {}  # In-memory tracking
        self.pattern_learner = None
        
    async def initialize(self):
        """Initialize feedback integration system"""
        self.pattern_learner = await get_pattern_learner()
        await self._load_active_positions()
        logger.info("Feedback integration system initialized")
        
    async def log_trade_entry(self, symbol: str, trade_data: Dict) -> Dict:
        """
        Log trade entry with all pattern data for future learning.
        Called automatically when trades are executed.
        """
        try:
            entry_price = trade_data.get('entry_price', 0.0)
            if entry_price <= 0:
                return {'success': False, 'error': 'Invalid entry price'}
            
            # Extract discovery/pattern data
            discovery_data = trade_data.get('discovery_data', {})
            pattern_data = trade_data.get('pattern_data', {})
            
            # Create comprehensive entry record
            entry_record = {
                'symbol': symbol,
                'entry_timestamp': datetime.now(),
                'entry_price': entry_price,
                'position_size': trade_data.get('position_size', 0),
                'entry_data': {
                    'volume_spike': discovery_data.get('volume_spike', pattern_data.get('volume_spike', 1.0)),
                    'short_interest': pattern_data.get('short_interest', 0.0),
                    'float_shares': pattern_data.get('float_shares', pattern_data.get('float', 50000000)),
                    'squeeze_score': pattern_data.get('squeeze_score', discovery_data.get('squeeze_score', 0.0)),
                    'vigl_similarity': pattern_data.get('vigl_similarity', discovery_data.get('vigl_similarity', 0.0)),
                    'pattern_score': discovery_data.get('score', pattern_data.get('pattern_score', 0.0)),
                    'discovery_reason': discovery_data.get('reason', 'Unknown'),
                    'sector': trade_data.get('sector', 'Unknown'),
                    'market_time': self._get_market_time(),
                    'discovery_date': discovery_data.get('discovery_date', datetime.now().date())
                },
                'pattern_hash': self._generate_entry_hash(discovery_data, pattern_data),
                'discovery_source': trade_data.get('source', 'manual'),
                'confidence': trade_data.get('confidence', 0.6),
                'thesis_data': trade_data.get('thesis_data', {}),
                'trade_metadata': {
                    'broker': trade_data.get('broker', 'alpaca'),
                    'order_type': trade_data.get('order_type', 'market'),
                    'execution_time': trade_data.get('execution_time'),
                    'slippage': trade_data.get('slippage', 0.0)
                }
            }
            
            # Store in database
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO squeeze_patterns 
                    (symbol, pattern_date, volume_spike, short_interest, float_shares,
                     entry_price, pattern_score, squeeze_score, vigl_similarity,
                     pattern_hash, sector, notes, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, NOW())
                    ON CONFLICT (symbol, pattern_date) DO NOTHING
                """,
                    symbol, entry_record['entry_data']['discovery_date'],
                    entry_record['entry_data']['volume_spike'],
                    entry_record['entry_data']['short_interest'],
                    entry_record['entry_data']['float_shares'],
                    entry_price,
                    entry_record['entry_data']['pattern_score'],
                    entry_record['entry_data']['squeeze_score'],
                    entry_record['entry_data']['vigl_similarity'],
                    entry_record['pattern_hash'],
                    entry_record['entry_data']['sector'],
                    f"Trade entry logged - Discovery: {entry_record['entry_data']['discovery_reason']}"
                )
            
            # Add to active position tracking
            self.active_positions[symbol] = TradeEntry(
                symbol=symbol,
                entry_timestamp=entry_record['entry_timestamp'],
                entry_price=entry_price,
                entry_data=entry_record['entry_data'],
                pattern_hash=entry_record['pattern_hash'],
                discovery_source=entry_record['discovery_source'],
                position_size=entry_record['position_size'],
                confidence=entry_record['confidence']
            )
            
            # Cache in Redis for quick access
            self.redis_client.setex(
                f"position:entry:{symbol}",
                86400 * 30,  # 30 day TTL
                json.dumps(entry_record, default=str)
            )
            
            logger.info(f"Trade entry logged: {symbol} @ ${entry_price:.2f}")
            
            return {
                'success': True,
                'entry_logged': True,
                'pattern_hash': entry_record['pattern_hash'],
                'tracking_active': True,
                'learning_enabled': True
            }
            
        except Exception as e:
            logger.error(f"Error logging trade entry for {symbol}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def log_trade_exit(self, symbol: str, exit_data: Dict) -> Dict:
        """
        Log trade exit and trigger learning from outcome.
        Called automatically when positions are closed.
        """
        try:
            # Get entry data
            if symbol not in self.active_positions:
                # Try to load from Redis
                cached_entry = self.redis_client.get(f"position:entry:{symbol}")
                if not cached_entry:
                    return {'success': False, 'error': 'No entry data found for position'}
                
                entry_data = json.loads(cached_entry.decode())
            else:
                entry_data = asdict(self.active_positions[symbol])
            
            entry_price = entry_data['entry_price']
            exit_price = exit_data.get('exit_price', 0.0)
            
            if exit_price <= 0:
                return {'success': False, 'error': 'Invalid exit price'}
            
            # Calculate performance metrics
            return_pct = ((exit_price - entry_price) / entry_price) * 100
            entry_timestamp = datetime.fromisoformat(entry_data['entry_timestamp']) if isinstance(entry_data['entry_timestamp'], str) else entry_data['entry_timestamp']
            days_held = (datetime.now() - entry_timestamp).days
            max_price = exit_data.get('max_price_achieved', max(exit_price, entry_price))
            max_gain_pct = ((max_price - entry_price) / entry_price) * 100
            
            # Determine success criteria
            pattern_success = return_pct >= 50.0  # VIGL-style explosive success
            explosive_success = return_pct >= 100.0
            
            # Create exit record
            exit_record = TradeExit(
                symbol=symbol,
                exit_timestamp=datetime.now(),
                exit_price=exit_price,
                exit_reason=exit_data.get('exit_reason', 'Manual'),
                days_held=days_held,
                max_price_achieved=max_price,
                return_pct=return_pct,
                pattern_success=pattern_success
            )
            
            # Update database with outcome
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                await conn.execute("""
                    UPDATE squeeze_patterns 
                    SET exit_price = $1, 
                        max_price = $2,
                        outcome_pct = $3,
                        max_gain_pct = $4,
                        days_held = $5,
                        success = $6,
                        explosive = $7,
                        closed_at = NOW(),
                        updated_at = NOW(),
                        notes = COALESCE(notes, '') || $8
                    WHERE symbol = $9 AND pattern_hash = $10
                """,
                    exit_price, max_price, return_pct, max_gain_pct, days_held,
                    pattern_success, explosive_success,
                    f" | Exit: {exit_data.get('exit_reason', 'Manual')} after {days_held} days",
                    symbol, entry_data['pattern_hash']
                )
            
            # Trigger pattern learning from outcome
            if self.pattern_learner:
                learning_result = await self.pattern_learner.learn_from_outcome(
                    symbol=symbol,
                    entry_data=entry_data['entry_data'],
                    exit_data={
                        'price': exit_price,
                        'max_price': max_price,
                        'days_held': days_held,
                        'exit_reason': exit_data.get('exit_reason', 'Manual')
                    }
                )
            else:
                learning_result = {'learning_success': False, 'error': 'Pattern learner not available'}
            
            # Clean up tracking
            if symbol in self.active_positions:
                del self.active_positions[symbol]
            
            self.redis_client.delete(f"position:entry:{symbol}")
            
            # Store exit record in Redis for analysis
            self.redis_client.setex(
                f"position:exit:{symbol}:{datetime.now().isoformat()}",
                86400 * 90,  # 90 day TTL
                json.dumps(asdict(exit_record), default=str)
            )
            
            # Generate performance summary
            performance_summary = {
                'symbol': symbol,
                'return_pct': return_pct,
                'max_gain_pct': max_gain_pct,
                'days_held': days_held,
                'pattern_success': pattern_success,
                'explosive_success': explosive_success,
                'exit_reason': exit_data.get('exit_reason', 'Manual'),
                'learning_triggered': learning_result.get('learning_success', False)
            }
            
            logger.info(f"Trade exit logged: {symbol} {return_pct:+.1f}% after {days_held} days - Learning: {learning_result.get('learning_success', False)}")
            
            # Generate alerts for significant outcomes
            if explosive_success and return_pct > 200:
                await self._generate_explosive_outcome_alert(symbol, performance_summary)
            elif return_pct < -25:
                await self._generate_loss_alert(symbol, performance_summary)
            
            return {
                'success': True,
                'exit_logged': True,
                'performance_summary': performance_summary,
                'learning_result': learning_result,
                'pattern_updated': learning_result.get('improved_detection', False)
            }
            
        except Exception as e:
            logger.error(f"Error logging trade exit for {symbol}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def update_position_tracking(self, symbol: str, current_price: float, additional_data: Dict = None) -> Dict:
        """
        Update position tracking with current price and performance.
        Called periodically to track unrealized performance.
        """
        try:
            if symbol not in self.active_positions:
                # Try to load from Redis
                cached_entry = self.redis_client.get(f"position:entry:{symbol}")
                if not cached_entry:
                    return {'success': False, 'error': 'Position not being tracked'}
                
                entry_data = json.loads(cached_entry.decode())
                entry_price = entry_data['entry_price']
            else:
                entry_price = self.active_positions[symbol].entry_price
            
            # Calculate current performance
            current_return = ((current_price - entry_price) / entry_price) * 100
            days_held = (datetime.now() - datetime.fromisoformat(entry_data['entry_timestamp']) if isinstance(entry_data['entry_timestamp'], str) else self.active_positions[symbol].entry_timestamp).days
            
            # Update tracking data
            tracking_update = {
                'symbol': symbol,
                'current_price': current_price,
                'current_return_pct': current_return,
                'days_held': days_held,
                'unrealized_status': self._classify_performance(current_return, days_held),
                'updated_at': datetime.now().isoformat(),
                'additional_data': additional_data or {}
            }
            
            # Cache updated tracking
            self.redis_client.setex(
                f"position:tracking:{symbol}",
                86400,  # 1 day TTL
                json.dumps(tracking_update, default=str)
            )
            
            # Update max price in database if new high
            if current_return > 0:
                pool = await get_db_pool()
                async with pool.acquire() as conn:
                    await conn.execute("""
                        UPDATE squeeze_patterns 
                        SET current_price = $1,
                            max_price = GREATEST(COALESCE(max_price, entry_price), $1),
                            max_gain_pct = GREATEST(
                                COALESCE(max_gain_pct, 0), 
                                (($1 - entry_price) / entry_price) * 100
                            ),
                            updated_at = NOW()
                        WHERE symbol = $2 AND closed_at IS NULL
                    """, current_price, symbol)
            
            # Generate alerts for significant moves
            alerts_generated = []
            if current_return >= 100 and days_held <= 30:
                alerts_generated.append(await self._generate_milestone_alert(symbol, current_return, 'DOUBLE'))
            elif current_return >= 200 and days_held <= 45:
                alerts_generated.append(await self._generate_milestone_alert(symbol, current_return, 'TRIPLE'))
            elif current_return <= -20:
                alerts_generated.append(await self._generate_milestone_alert(symbol, current_return, 'LOSS'))
            
            return {
                'success': True,
                'tracking_updated': True,
                'performance': tracking_update,
                'alerts_generated': len(alerts_generated)
            }
            
        except Exception as e:
            logger.error(f"Error updating position tracking for {symbol}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_active_positions_performance(self) -> Dict:
        """Get performance summary of all actively tracked positions"""
        try:
            performance_data = {}
            
            for symbol in self.active_positions:
                tracking_key = f"position:tracking:{symbol}"
                cached_tracking = self.redis_client.get(tracking_key)
                
                if cached_tracking:
                    tracking_data = json.loads(cached_tracking.decode())
                    performance_data[symbol] = tracking_data
                else:
                    # Basic performance from entry data
                    entry = self.active_positions[symbol]
                    performance_data[symbol] = {
                        'symbol': symbol,
                        'entry_price': entry.entry_price,
                        'days_held': (datetime.now() - entry.entry_timestamp).days,
                        'confidence': entry.confidence,
                        'status': 'tracking_incomplete'
                    }
            
            # Summary statistics
            if performance_data:
                returns = [pos.get('current_return_pct', 0) for pos in performance_data.values() if pos.get('current_return_pct')]
                avg_return = sum(returns) / len(returns) if returns else 0
                winners = len([r for r in returns if r > 0])
                losers = len([r for r in returns if r < 0])
            else:
                avg_return = 0
                winners = 0
                losers = 0
            
            summary = {
                'total_positions': len(performance_data),
                'avg_return_pct': avg_return,
                'winners': winners,
                'losers': losers,
                'win_rate': winners / len(returns) if returns else 0,
                'positions': performance_data
            }
            
            return {'success': True, 'performance_summary': summary}
            
        except Exception as e:
            logger.error(f"Error getting active positions performance: {e}")
            return {'success': False, 'error': str(e)}
    
    async def trigger_periodic_learning_update(self) -> Dict:
        """
        Trigger periodic learning updates based on accumulated position data.
        Should be called daily to process recent outcomes.
        """
        try:
            # Get recent exits from last 24 hours
            exit_keys = self.redis_client.keys(f"position:exit:*")
            recent_exits = []
            
            for key in exit_keys:
                exit_data = self.redis_client.get(key)
                if exit_data:
                    exit_record = json.loads(exit_data.decode())
                    exit_timestamp = datetime.fromisoformat(exit_record['exit_timestamp'])
                    if exit_timestamp >= datetime.now() - timedelta(hours=24):
                        recent_exits.append(exit_record)
            
            if not recent_exits:
                return {'success': True, 'message': 'No recent exits to process'}
            
            # Analyze recent performance patterns
            explosive_winners = [e for e in recent_exits if e['explosive_success']]
            pattern_failures = [e for e in recent_exits if e['return_pct'] < -20]
            
            # Update pattern evolution if significant changes
            if len(explosive_winners) >= 2 or len(pattern_failures) >= 3:
                evolution_update = await self.pattern_learner.detect_pattern_evolution(7)  # 7 days
                
                if evolution_update.get('evolution_detected'):
                    await self._generate_evolution_alert(evolution_update)
            
            # Generate periodic learning summary
            learning_summary = {
                'analysis_date': datetime.now().isoformat(),
                'recent_exits': len(recent_exits),
                'explosive_winners': len(explosive_winners),
                'pattern_failures': len(pattern_failures),
                'avg_return': sum(e['return_pct'] for e in recent_exits) / len(recent_exits),
                'learning_health': 'good' if len(explosive_winners) > len(pattern_failures) else 'needs_attention'
            }
            
            # Cache learning summary
            self.redis_client.setex(
                "learning:periodic_summary",
                86400,  # 1 day TTL
                json.dumps(learning_summary, default=str)
            )
            
            logger.info(f"Periodic learning update: {len(recent_exits)} exits processed, {len(explosive_winners)} explosive winners")
            
            return {
                'success': True,
                'learning_summary': learning_summary,
                'evolution_detected': len(explosive_winners) >= 2 or len(pattern_failures) >= 3
            }
            
        except Exception as e:
            logger.error(f"Error in periodic learning update: {e}")
            return {'success': False, 'error': str(e)}
    
    def _generate_entry_hash(self, discovery_data: Dict, pattern_data: Dict) -> str:
        """Generate unique hash for entry pattern identification"""
        combined_data = {
            'volume_spike': discovery_data.get('volume_spike', pattern_data.get('volume_spike', 1.0)),
            'squeeze_score': pattern_data.get('squeeze_score', discovery_data.get('squeeze_score', 0.0)),
            'discovery_reason': discovery_data.get('reason', 'Unknown'),
            'pattern_score': discovery_data.get('score', pattern_data.get('pattern_score', 0.0))
        }
        
        import hashlib
        entry_string = json.dumps(combined_data, sort_keys=True)
        return hashlib.sha256(entry_string.encode()).hexdigest()[:16]
    
    def _get_market_time(self) -> str:
        """Get current market time period"""
        from datetime import datetime
        try:
            import pytz
            et = pytz.timezone('US/Eastern')
            now = datetime.now(et)
            hour = now.hour
            
            if hour < 9:
                return "premarket"
            elif 9 <= hour < 10:
                return "open"
            elif 10 <= hour < 14:
                return "midday"
            elif 14 <= hour < 16:
                return "close"
            else:
                return "afterhours"
        except:
            return "unknown"
    
    def _classify_performance(self, return_pct: float, days_held: int) -> str:
        """Classify current position performance"""
        if return_pct >= 100:
            return 'EXPLOSIVE_WINNER'
        elif return_pct >= 50:
            return 'STRONG_WINNER'
        elif return_pct >= 25:
            return 'MODERATE_WINNER'
        elif return_pct >= 10:
            return 'SMALL_WINNER'
        elif return_pct >= -5:
            return 'FLAT'
        elif return_pct >= -15:
            return 'SMALL_LOSS'
        elif return_pct >= -25:
            return 'MODERATE_LOSS'
        else:
            return 'MAJOR_LOSS'
    
    async def _load_active_positions(self):
        """Load active positions from Redis/database on startup"""
        try:
            position_keys = self.redis_client.keys("position:entry:*")
            
            for key in position_keys:
                entry_data = self.redis_client.get(key)
                if entry_data:
                    data = json.loads(entry_data.decode())
                    symbol = data['symbol']
                    
                    self.active_positions[symbol] = TradeEntry(
                        symbol=symbol,
                        entry_timestamp=datetime.fromisoformat(data['entry_timestamp']) if isinstance(data['entry_timestamp'], str) else data['entry_timestamp'],
                        entry_price=data['entry_price'],
                        entry_data=data['entry_data'],
                        pattern_hash=data['pattern_hash'],
                        discovery_source=data['discovery_source'],
                        position_size=data['position_size'],
                        confidence=data['confidence']
                    )
            
            logger.info(f"Loaded {len(self.active_positions)} active positions for tracking")
            
        except Exception as e:
            logger.error(f"Error loading active positions: {e}")
    
    async def _generate_explosive_outcome_alert(self, symbol: str, performance: Dict):
        """Generate alert for explosive outcome"""
        try:
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO pattern_alerts (alert_type, pattern_type, alert_level, message, details)
                    VALUES ('EXPLOSIVE_OUTCOME', 'TRADE_RESULT', 'INFO', $1, $2)
                """,
                    f"🚀 EXPLOSIVE OUTCOME: {symbol} achieved {performance['return_pct']:.0f}% return in {performance['days_held']} days",
                    json.dumps(performance)
                )
        except Exception as e:
            logger.error(f"Error generating explosive outcome alert: {e}")
    
    async def _generate_loss_alert(self, symbol: str, performance: Dict):
        """Generate alert for significant loss"""
        try:
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO pattern_alerts (alert_type, pattern_type, alert_level, message, details)
                    VALUES ('SIGNIFICANT_LOSS', 'TRADE_RESULT', 'WARNING', $1, $2)
                """,
                    f"⚠️ SIGNIFICANT LOSS: {symbol} lost {abs(performance['return_pct']):.0f}% - Pattern analysis needed",
                    json.dumps(performance)
                )
        except Exception as e:
            logger.error(f"Error generating loss alert: {e}")
    
    async def _generate_milestone_alert(self, symbol: str, return_pct: float, milestone: str):
        """Generate milestone achievement alert"""
        try:
            messages = {
                'DOUBLE': f"📈 MILESTONE: {symbol} doubled ({return_pct:.0f}%) - Consider profit taking",
                'TRIPLE': f"🎯 MILESTONE: {symbol} tripled ({return_pct:.0f}%) - Exceptional performance",
                'LOSS': f"⚠️ MILESTONE: {symbol} down {abs(return_pct):.0f}% - Review exit strategy"
            }
            
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO pattern_alerts (alert_type, pattern_type, alert_level, message, details)
                    VALUES ('MILESTONE', 'PERFORMANCE', 'INFO', $1, $2)
                """,
                    messages.get(milestone, f"{symbol} milestone {milestone}"),
                    json.dumps({'symbol': symbol, 'return_pct': return_pct, 'milestone': milestone})
                )
        except Exception as e:
            logger.error(f"Error generating milestone alert: {e}")
    
    async def _generate_evolution_alert(self, evolution_data: Dict):
        """Generate pattern evolution alert"""
        try:
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO pattern_alerts (alert_type, pattern_type, alert_level, message, details)
                    VALUES ('PATTERN_EVOLUTION', 'SYSTEM', 'WARNING', $1, $2)
                """,
                    "🔄 PATTERN EVOLUTION DETECTED: Trading patterns showing significant changes - Review required",
                    json.dumps(evolution_data)
                )
        except Exception as e:
            logger.error(f"Error generating evolution alert: {e}")

# Factory function
async def get_feedback_integrator() -> FeedbackIntegrator:
    """Get initialized feedback integrator instance"""
    integrator = FeedbackIntegrator()
    await integrator.initialize()
    return integrator