#!/usr/bin/env python3
"""
Portfolio Learning Integration
Automatically tracks portfolio positions and calculates outcomes for learning system
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from decimal import Decimal

logger = logging.getLogger(__name__)

class PortfolioLearningTracker:
    """
    Tracks portfolio positions and automatically calculates trade outcomes
    Integrates with learning system when positions are closed
    """

    def __init__(self):
        self.tracking_enabled = True
        self.check_interval = 300  # Check every 5 minutes
        self.min_days_for_outcome = 1  # Minimum 1 day for outcome tracking

    async def monitor_positions(self):
        """
        Monitor portfolio positions and detect closed positions for outcome calculation
        """
        if not self.tracking_enabled:
            return

        try:
            # Get tracked positions that are still open
            tracked_positions = await self._get_tracked_positions()

            if not tracked_positions:
                logger.info("No tracked positions to monitor")
                return

            # Get current portfolio positions from broker
            current_positions = await self._get_current_portfolio_positions()
            current_symbols = {pos.get('symbol') for pos in current_positions}

            # Check for closed positions
            for tracked_pos in tracked_positions:
                symbol = tracked_pos['symbol']

                # If position is no longer in current portfolio, it was closed
                if symbol not in current_symbols:
                    await self._process_closed_position(tracked_pos)

            # Update existing positions with current prices for unrealized tracking
            for tracked_pos in tracked_positions:
                symbol = tracked_pos['symbol']
                current_pos = next((p for p in current_positions if p.get('symbol') == symbol), None)

                if current_pos:
                    await self._update_position_current_price(tracked_pos, current_pos)

        except Exception as e:
            logger.error(f"Portfolio monitoring failed: {e}")

    async def _get_tracked_positions(self) -> List[Dict[str, Any]]:
        """
        Get positions that are being tracked for learning outcomes
        """
        try:
            from ..shared.database import get_db_pool

            pool = await get_db_pool()
            if not pool:
                return []

            async with pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT id, symbol, action, entry_price, quantity, entry_time,
                           alpaca_order_id, discovery_source, exit_price, exit_time,
                           outcome_recorded
                    FROM learning_intelligence.position_tracking
                    WHERE learning_tracked = TRUE
                    AND outcome_recorded = FALSE
                    AND action = 'BUY'  -- Only track buy positions for now
                    ORDER BY entry_time DESC
                """)

                return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get tracked positions: {e}")
            return []

    async def _get_current_portfolio_positions(self) -> List[Dict[str, Any]]:
        """
        Get current portfolio positions from Alpaca broker
        """
        try:
            from ..services.broker_alpaca import AlpacaBroker

            broker = AlpacaBroker()
            positions = await broker.get_positions()

            return positions

        except Exception as e:
            logger.error(f"Failed to get current portfolio positions: {e}")
            return []

    async def _process_closed_position(self, tracked_position: Dict[str, Any]):
        """
        Process a closed position and calculate learning outcome
        """
        try:
            symbol = tracked_position['symbol']
            entry_price = float(tracked_position['entry_price'])
            entry_time = tracked_position['entry_time']

            # Get exit price from recent market data
            exit_price = await self._get_exit_price(symbol)
            exit_time = datetime.now()

            if exit_price <= 0:
                logger.warning(f"Could not determine exit price for {symbol}")
                return

            # Calculate outcome metrics
            return_pct = ((exit_price - entry_price) / entry_price) * 100
            days_held = (exit_time - entry_time).days

            # Update position tracking record
            await self._update_position_outcome(
                tracked_position['id'],
                exit_price,
                exit_time,
                return_pct,
                days_held
            )

            # Send to learning system
            await self._send_outcome_to_learning_system(
                symbol=symbol,
                entry_price=entry_price,
                exit_price=exit_price,
                days_held=days_held,
                return_pct=return_pct,
                discovery_source=tracked_position['discovery_source']
            )

            logger.info(f"✅ Processed closed position {symbol}: {return_pct:+.2f}% in {days_held} days")

        except Exception as e:
            logger.error(f"Failed to process closed position {tracked_position.get('symbol')}: {e}")

    async def _get_exit_price(self, symbol: str) -> float:
        """
        Get the most recent price for a symbol (exit price)
        """
        try:
            from ..services.polygon_client import poly_singleton

            # Try to get the most recent price
            try:
                m = await poly_singleton.agg_last_minute(symbol)
                return float(m.get("price") or 0.0)
            except Exception:
                # Fallback to previous day price
                p = await poly_singleton.prev_day(symbol)
                return float(p.get("price") or 0.0)

        except Exception as e:
            logger.warning(f"Failed to get exit price for {symbol}: {e}")
            return 0.0

    async def _update_position_outcome(self, position_id: int, exit_price: float,
                                     exit_time: datetime, return_pct: float, days_held: int):
        """
        Update position tracking record with outcome data
        """
        try:
            from ..shared.database import get_db_pool

            pool = await get_db_pool()
            if not pool:
                return

            async with pool.acquire() as conn:
                await conn.execute("""
                    UPDATE learning_intelligence.position_tracking
                    SET exit_price = $1, exit_time = $2, return_pct = $3,
                        days_held = $4, outcome_recorded = TRUE, updated_at = NOW()
                    WHERE id = $5
                """, exit_price, exit_time, return_pct, days_held, position_id)

        except Exception as e:
            logger.error(f"Failed to update position outcome for ID {position_id}: {e}")

    async def _update_position_current_price(self, tracked_position: Dict[str, Any],
                                           current_position: Dict[str, Any]):
        """
        Update position with current price for unrealized tracking
        """
        try:
            current_price = float(current_position.get('current_price', 0))
            if current_price <= 0:
                return

            entry_price = float(tracked_position['entry_price'])
            unrealized_return_pct = ((current_price - entry_price) / entry_price) * 100

            # Log significant moves for learning
            if abs(unrealized_return_pct) > 10:  # 10%+ moves
                logger.info(f"📊 {tracked_position['symbol']}: {unrealized_return_pct:+.1f}% unrealized")

        except Exception as e:
            logger.warning(f"Failed to update current price for {tracked_position.get('symbol')}: {e}")

    async def _send_outcome_to_learning_system(self, symbol: str, entry_price: float,
                                             exit_price: float, days_held: int,
                                             return_pct: float, discovery_source: bool):
        """
        Send trade outcome to learning system for pattern analysis
        """
        try:
            from ..services.learning_integration import track_trade_outcome

            # Only send if it was from discovery system
            if discovery_source:
                await track_trade_outcome(symbol, entry_price, exit_price, days_held)

                # Also log to learning analytics
                from ..routes.learning_analytics import log_explosive_winner

                # Log if it was a significant winner (>25% return)
                if return_pct > 25:
                    await log_explosive_winner(
                        symbol=symbol,
                        entry_price=entry_price,
                        exit_price=exit_price,
                        days_held=days_held,
                        return_pct=return_pct,
                        pattern_features={
                            'discovery_source': True,
                            'return_category': 'explosive' if return_pct > 50 else 'strong'
                        }
                    )

        except Exception as e:
            logger.warning(f"Failed to send outcome to learning system for {symbol}: {e}")

# Global instance
portfolio_tracker = PortfolioLearningTracker()

async def monitor_portfolio_for_learning():
    """
    Public function to monitor portfolio positions for learning
    Safe to call periodically - never blocks main operations
    """
    await portfolio_tracker.monitor_positions()

async def start_portfolio_monitoring():
    """
    Start continuous portfolio monitoring for learning
    """
    logger.info("🔍 Starting portfolio learning monitoring")

    while True:
        try:
            await monitor_portfolio_for_learning()
            await asyncio.sleep(portfolio_tracker.check_interval)
        except Exception as e:
            logger.error(f"Portfolio monitoring error: {e}")
            await asyncio.sleep(60)  # Wait 1 minute on error

if __name__ == "__main__":
    # For testing
    async def test_monitor():
        await monitor_portfolio_for_learning()
        print("✅ Portfolio monitoring test completed")

    asyncio.run(test_monitor())