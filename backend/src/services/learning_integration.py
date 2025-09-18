#!/usr/bin/env python3
"""
Learning Integration Service - Circuit Breaker Protected
Safely integrates discovery system with learning engine without risk to main operations
"""

import asyncio
import logging
import time
import json
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

class CircuitBreaker:
    """
    Circuit breaker to protect main system from learning system failures
    3-failure threshold opens circuit for 5 minutes
    """

    def __init__(self, failure_threshold: int = 3, recovery_timeout: int = 300):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def can_execute(self) -> bool:
        """Check if execution is allowed"""
        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        else:  # HALF_OPEN
            return True

    def record_success(self):
        """Record successful execution"""
        self.failure_count = 0
        self.state = "CLOSED"

    def record_failure(self):
        """Record failed execution"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(f"Circuit breaker OPEN after {self.failure_count} failures")

class LearningIntegration:
    """
    Safe integration with learning system using circuit breaker pattern
    Fire-and-forget data collection that never blocks main system
    """

    def __init__(self):
        self.circuit_breaker = CircuitBreaker()
        self.learning_enabled = True
        self.max_timeout = 2.0  # Maximum 2 second timeout

    async def collect_discovery_data(self, discovery_result: Dict[str, Any]):
        """
        Collect discovery data for learning (fire-and-forget)
        Never blocks main discovery system
        """
        if not self.learning_enabled or not self.circuit_breaker.can_execute():
            return

        # Fire and forget - don't await
        asyncio.create_task(self._safe_collect_discovery_data(discovery_result))

    async def _safe_collect_discovery_data(self, discovery_result: Dict[str, Any]):
        """
        Safely collect discovery data with timeout and error handling
        """
        try:
            # Import learning system only when needed
            from ..routes.learning import LearningSystem
            from ..services.learning_engine import get_learning_engine

            start_time = time.time()

            # Collect data with timeout
            await asyncio.wait_for(
                self._process_discovery_data(discovery_result),
                timeout=self.max_timeout
            )

            # Record success
            self.circuit_breaker.record_success()

            elapsed = time.time() - start_time
            logger.info(f"✅ Learning data collected in {elapsed:.3f}s")

        except asyncio.TimeoutError:
            logger.warning(f"Learning data collection timeout ({self.max_timeout}s)")
            self.circuit_breaker.record_failure()
        except Exception as e:
            logger.warning(f"Learning data collection failed: {e}")
            self.circuit_breaker.record_failure()

    async def _process_discovery_data(self, discovery_result: Dict[str, Any]):
        """
        Process discovery result and store learning data
        """
        from ..routes.learning import LearningSystem
        from ..services.learning_engine import get_learning_engine

        if discovery_result.get('status') != 'success':
            return

        candidates = discovery_result.get('candidates', [])
        if not candidates:
            return

        # Initialize learning engine
        learning_engine = await get_learning_engine()

        # Extract discovery event data
        discovery_event = {
            'event_timestamp': datetime.now(),
            'universe_size': discovery_result.get('universe_size', 0),
            'candidates_found': len(candidates),
            'execution_time_ms': discovery_result.get('execution_time_sec', 0) * 1000,
            'market_conditions': {
                'discovery_method': discovery_result.get('method', 'unknown'),
                'pipeline_stats': discovery_result.get('pipeline_stats', {}),
                'trade_ready_count': discovery_result.get('trade_ready_count', 0),
                'monitor_count': discovery_result.get('monitor_count', 0)
            },
            'scoring_distribution': self._calculate_score_distribution(candidates)
        }

        # Store discovery event in learning database
        await self._store_discovery_event(discovery_event)

        # Store individual candidate features for pattern learning
        for candidate in candidates:
            await self._store_candidate_features(discovery_event, candidate)

        # Log decisions for basic learning system compatibility
        for candidate in candidates:
            await LearningSystem.log_decision(
                symbol=candidate['symbol'],
                decision_type='discovery_found',
                recommendation_source='alphastack_discovery',
                confidence_score=candidate.get('confidence', 0.5),
                price_at_decision=candidate.get('price', 0.0),
                market_time=self._get_market_time(),
                reasoning=f"Discovered via AlphaStack with score {candidate.get('score', 0.0):.3f}",
                metadata={
                    'subscores': candidate.get('subscores', {}),
                    'action_tag': candidate.get('action_tag', 'monitor'),
                    'risk_flags': candidate.get('risk_flags', [])
                }
            )

    async def _store_discovery_event(self, event_data: Dict[str, Any]):
        """Store discovery event in learning database"""
        try:
            from ..shared.database import get_db_pool

            pool = await get_db_pool()
            if not pool:
                return

            async with pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO learning_intelligence.discovery_events
                    (event_timestamp, universe_size, candidates_found, execution_time_ms,
                     market_conditions, scoring_distribution)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """,
                    event_data['event_timestamp'],
                    event_data['universe_size'],
                    event_data['candidates_found'],
                    event_data['execution_time_ms'],
                    json.dumps(event_data['market_conditions']),
                    json.dumps(event_data['scoring_distribution'])
                )
        except Exception as e:
            logger.warning(f"Failed to store discovery event: {e}")

    async def _store_candidate_features(self, discovery_event: Dict, candidate: Dict):
        """Store candidate features for pattern learning"""
        try:
            from ..shared.database import get_db_pool

            pool = await get_db_pool()
            if not pool:
                return

            subscores = candidate.get('subscores', {})

            async with pool.acquire() as conn:
                # First get the discovery event ID (latest one)
                event_row = await conn.fetchrow("""
                    SELECT id FROM learning_intelligence.discovery_events
                    ORDER BY event_timestamp DESC LIMIT 1
                """)

                if not event_row:
                    return

                await conn.execute("""
                    INSERT INTO learning_intelligence.candidate_features
                    (discovery_event_id, symbol, score, action_tag, volume_momentum_score,
                     squeeze_score, catalyst_score, sentiment_score, options_score,
                     technical_score, price, volume, rel_vol)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                """,
                    event_row['id'],
                    candidate['symbol'],
                    candidate.get('score', 0.0),
                    candidate.get('action_tag', 'monitor'),
                    subscores.get('volume_momentum', 0.0),
                    subscores.get('squeeze', 0.0),
                    subscores.get('catalyst', 0.0),
                    subscores.get('sentiment', 0.0),
                    subscores.get('options', 0.0),
                    subscores.get('technical', 0.0),
                    candidate.get('price', 0.0),
                    candidate.get('volume', 0),
                    candidate.get('rel_vol', 1.0)
                )
        except Exception as e:
            logger.warning(f"Failed to store candidate features for {candidate.get('symbol')}: {e}")

    def _calculate_score_distribution(self, candidates: list) -> Dict[str, Any]:
        """Calculate score distribution statistics"""
        if not candidates:
            return {}

        scores = [c.get('score', 0.0) for c in candidates]

        return {
            'min_score': min(scores),
            'max_score': max(scores),
            'avg_score': sum(scores) / len(scores),
            'score_ranges': {
                'trade_ready': len([s for s in scores if s >= 0.75]),
                'watchlist': len([s for s in scores if 0.7 <= s < 0.75]),
                'monitor': len([s for s in scores if s < 0.7])
            }
        }

    def _get_market_time(self) -> str:
        """Determine current market time"""
        now = datetime.now()
        hour = now.hour

        if hour < 9:
            return "premarket"
        elif 9 <= hour < 16:
            return "market_hours"
        elif 16 <= hour < 20:
            return "afterhours"
        else:
            return "closed"

    async def track_trade_outcome(self, symbol: str, entry_price: float,
                                exit_price: float, days_held: int):
        """
        Track actual trade outcomes for learning
        Called when positions are closed
        """
        if not self.learning_enabled or not self.circuit_breaker.can_execute():
            return

        # Fire and forget
        asyncio.create_task(self._safe_track_outcome(symbol, entry_price, exit_price, days_held))

    async def _safe_track_outcome(self, symbol: str, entry_price: float,
                                exit_price: float, days_held: int):
        """Safely track trade outcome with timeout protection"""
        try:
            from ..routes.learning import LearningSystem

            return_pct = ((exit_price - entry_price) / entry_price) * 100
            outcome_type = "gain" if return_pct > 0 else "loss" if return_pct < 0 else "neutral"

            # Find the original decision for this symbol
            from ..shared.database import get_db_pool
            pool = await get_db_pool()

            if pool:
                async with pool.acquire() as conn:
                    decision = await conn.fetchrow("""
                        SELECT id FROM learning_decisions
                        WHERE symbol = $1 AND decision_type = 'discovery_found'
                        ORDER BY created_at DESC LIMIT 1
                    """, symbol)

                    if decision:
                        await LearningSystem.log_outcome(
                            symbol=symbol,
                            decision_id=decision['id'],
                            outcome_type=outcome_type,
                            price_at_outcome=exit_price,
                            return_pct=return_pct,
                            days_held=days_held
                        )

            self.circuit_breaker.record_success()
            logger.info(f"✅ Tracked outcome for {symbol}: {return_pct:.2f}% in {days_held} days")

        except Exception as e:
            logger.warning(f"Failed to track outcome for {symbol}: {e}")
            self.circuit_breaker.record_failure()

# Global instance
learning_integration = LearningIntegration()

async def collect_discovery_data(discovery_result: Dict[str, Any]):
    """
    Public function to collect discovery data for learning
    Safe to call from discovery system - never blocks
    """
    await learning_integration.collect_discovery_data(discovery_result)

async def track_trade_outcome(symbol: str, entry_price: float, exit_price: float, days_held: int):
    """
    Public function to track trade outcomes
    Safe to call from trading system - never blocks
    """
    await learning_integration.track_trade_outcome(symbol, entry_price, exit_price, days_held)