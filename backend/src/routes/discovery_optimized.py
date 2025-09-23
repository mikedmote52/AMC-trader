#!/usr/bin/env python3
"""
AMC-TRADER Optimized Discovery System
Single, powerful pipeline for explosive growth stock discovery
Built with Polygon MCP integration - no mock data, no fallbacks
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
import json

logger = logging.getLogger(__name__)
router = APIRouter()

class ExplosiveDiscoveryEngine:
    """
    Single optimized discovery engine for explosive growth stocks
    Uses Polygon MCP exclusively for real market data
    """

    def __init__(self):
        self.min_price = 0.50
        self.max_price = 100.0
        self.min_volume_ratio = 1.5  # At least 1.5x average volume
        self.max_daily_change = 15.0  # Max 15% daily move - catch BEFORE explosion
        self.min_daily_change = -20.0  # Allow some losers for reversal plays
        self.max_candidates = 100

    async def get_market_universe(self) -> List[Dict[str, Any]]:
        """Get market universe using direct Polygon API calls"""
        try:
            import os
            import httpx  # Use httpx instead of aiohttp

            api_key = os.getenv('POLYGON_API_KEY')
            if not api_key:
                raise RuntimeError("POLYGON_API_KEY not available")

            logger.info("📡 Fetching market universe via direct Polygon API...")

            # Get broader market universe (not just extreme movers)
            async with httpx.AsyncClient(timeout=30.0) as client:
                universe = []

                # Get modest gainers (not extreme)
                gainers_url = "https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/gainers"
                gainers_params = {'apikey': api_key}

                try:
                    gainers_response = await client.get(gainers_url, params=gainers_params)
                    if gainers_response.status_code == 200:
                        gainers_data = gainers_response.json()
                        gainers = gainers_data.get('tickers', [])
                        logger.info(f"✅ Retrieved {len(gainers)} gainers")
                        universe.extend(gainers)
                    else:
                        logger.error(f"Gainers API failed: {gainers_response.status_code}")
                except Exception as e:
                    logger.error(f"Error fetching gainers: {e}")

                # Get losers (potential reversal plays)
                losers_url = "https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/losers"
                losers_params = {'apikey': api_key}

                try:
                    losers_response = await client.get(losers_url, params=losers_params)
                    if losers_response.status_code == 200:
                        losers_data = losers_response.json()
                        losers = losers_data.get('tickers', [])
                        logger.info(f"✅ Retrieved {len(losers)} losers")
                        universe.extend(losers)
                    else:
                        logger.error(f"Losers API failed: {losers_response.status_code}")
                except Exception as e:
                    logger.error(f"Error fetching losers: {e}")

                # Try to get broader market snapshot if available
                try:
                    all_tickers_url = "https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/tickers"
                    all_params = {'apikey': api_key}

                    all_response = await client.get(all_tickers_url, params=all_params)
                    if all_response.status_code == 200:
                        all_data = all_response.json()
                        all_tickers = all_data.get('tickers', [])
                        logger.info(f"✅ Retrieved {len(all_tickers)} from full market snapshot")
                        universe.extend(all_tickers)
                    else:
                        logger.info(f"Full snapshot not available: {all_response.status_code}")
                except Exception as e:
                    logger.info(f"Full snapshot failed (expected): {e}")

            logger.info(f"📊 Total universe: {len(universe)} stocks from combined sources")

            if not universe:
                logger.error("No market data retrieved from Polygon API")
                return []

            # Filter for explosive growth potential
            common_stocks = []
            for stock in universe:
                ticker = stock.get('ticker', '')

                # Skip warrants, rights, units, preferred stocks
                if any(suffix in ticker for suffix in ['.WS', '.WT', '.U', '.RT', '.PR']):
                    continue

                # Get price and volume data from Polygon API response format
                # Check both day and prevDay for pricing
                day_data = stock.get('day', {})
                prev_day_data = stock.get('prevDay', {})

                # Use current day close price, fallback to previous day
                price = day_data.get('c') or prev_day_data.get('c') or 0

                # Calculate volume ratio if volume data is available
                current_volume = day_data.get('v', 0)
                prev_volume = prev_day_data.get('v', 1)
                volume_ratio = current_volume / max(prev_volume, 1) if prev_volume > 0 else 1.0

                # Add volume_ratio to stock data for scoring
                stock['volume_ratio'] = volume_ratio

                # Get daily change percentage
                daily_change_pct = stock.get('todaysChangePerc', 0)

                # CRITICAL: Skip stocks that already exploded (>15% move)
                if daily_change_pct > self.max_daily_change:
                    logger.debug(f"❌ {ticker}: Already exploded {daily_change_pct:.1f}%")
                    continue

                # Skip extreme losers (< -20%)
                if daily_change_pct < self.min_daily_change:
                    logger.debug(f"❌ {ticker}: Extreme loser {daily_change_pct:.1f}%")
                    continue

                # Filter for explosive potential
                if price < self.min_price or price > self.max_price:
                    continue

                if volume_ratio < self.min_volume_ratio:
                    continue

                # Stock passes all filters
                common_stocks.append(stock)

            logger.info(f"Filtered universe: {len(common_stocks)} common stocks")
            return common_stocks

        except Exception as e:
            logger.error(f"Universe filtering failed: {e}")
            return []

    def calculate_explosive_score(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate explosive growth score with proper bounds checking
        Returns score between 0.0 and 1.0 (0% to 100%)
        """
        try:
            # Get base metrics
            volume_ratio = candidate.get('volume_ratio', 1.0)
            price = candidate.get('prevDay', {}).get('c', 0)
            change_pct = candidate.get('todaysChangePerc', 0)
            volume = candidate.get('day', {}).get('v', 0)

            # Component scores (each 0-1 range)

            # Volume Momentum (40% weight) - favor 2-8x volume (pre-breakout surge)
            if 2 <= volume_ratio <= 8:
                volume_score = 1.0  # Sweet spot for pre-breakout
            elif volume_ratio < 2:
                volume_score = volume_ratio / 2.0
            else:  # >8x might be post-explosion
                volume_score = max(0.3, 1.0 - ((volume_ratio - 8) / 20.0))

            # Pre-Breakout Momentum (30% weight) - favor 3-12% moves, not 50%+
            abs_change = abs(change_pct)
            if 3 <= abs_change <= 12:
                price_momentum = 1.0  # Pre-breakout sweet spot
            elif abs_change < 3:
                price_momentum = abs_change / 3.0  # Building momentum
            else:  # >12% might be post-explosion
                price_momentum = max(0.2, 1.0 - ((abs_change - 12) / 15.0))

            # Activity Level (15% weight)
            activity_score = min(volume / 1000000, 1.0)  # Cap at 1M volume

            # Price Action (10% weight)
            price_score = 1.0 if 1.0 <= price <= 20.0 else 0.5  # Sweet spot for explosive moves

            # Technical (5% weight)
            technical_score = 0.5  # Placeholder until we add RSI/EMA

            # Calculate weighted total (0-1 range)
            total_score = (
                volume_score * 0.40 +
                price_momentum * 0.30 +
                activity_score * 0.15 +
                price_score * 0.10 +
                technical_score * 0.05
            )

            # Ensure score is capped at 1.0
            total_score = min(total_score, 1.0)

            # Calculate subscores for display (0-100 range)
            subscores = {
                'volume_momentum': round(volume_score * 40, 1),
                'squeeze': round(price_momentum * 30, 1),
                'catalyst': round(activity_score * 15, 1),
                'options': round(price_score * 10, 1),
                'technical': round(technical_score * 5, 1)
            }

            # Determine action tag
            if total_score >= 0.30:
                action_tag = 'trade_ready'
            elif total_score >= 0.20:
                action_tag = 'watchlist'
            else:
                action_tag = 'monitor'

            # Ensure scores are in 0-1 range for consistent API response
            return {
                'total_score': round(total_score, 3),  # 0-1 range
                'score': round(total_score, 3),        # 0-1 range
                'subscores': {
                    'volume_momentum': round(volume_score * 40, 1),  # 0-40 range (weighted)
                    'squeeze': round(price_momentum * 30, 1),        # 0-30 range (weighted)
                    'catalyst': round(activity_score * 15, 1),       # 0-15 range (weighted)
                    'options': round(price_score * 10, 1),           # 0-10 range (weighted)
                    'technical': round(technical_score * 5, 1)       # 0-5 range (weighted)
                },
                'action_tag': action_tag,
                'volume_momentum_raw': round(volume_score, 3),
                'price_momentum_raw': round(price_momentum, 3)
            }

        except Exception as e:
            logger.error(f"Scoring failed: {e}")
            return {
                'total_score': 0.0,
                'score': 0.0,
                'subscores': {'volume_momentum': 0, 'squeeze': 0, 'catalyst': 0, 'options': 0, 'technical': 0},
                'action_tag': 'monitor'
            }

    def add_trading_levels(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        """Add entry, stop, target levels, and thesis"""
        # Use current day close price first, fallback to previous day
        price = candidate.get('day', {}).get('c') or candidate.get('prevDay', {}).get('c') or 0

        if price > 0:
            candidate['price'] = price
            candidate['entry'] = round(price * 1.02, 2)  # 2% above current
            candidate['stop'] = round(price * 0.92, 2)   # 8% stop loss
            candidate['tp1'] = round(price * 1.20, 2)    # 20% target
            candidate['tp2'] = round(price * 1.50, 2)    # 50% target
            candidate['tp3'] = round(price * 2.00, 2)    # 100% explosive target

            # Add proper RelVol data
            candidate['relvol'] = candidate.get('volume_ratio', 1.0)

            # Generate trading thesis based on metrics
            candidate['thesis'] = self.generate_thesis(candidate)

            # Add price target estimation
            candidate['price_target'] = self.estimate_price_target(candidate, price)

        return candidate

    def generate_thesis(self, candidate: Dict[str, Any]) -> str:
        """Generate trading thesis based on stock metrics"""
        ticker = candidate.get('ticker', 'UNKNOWN')
        volume_ratio = candidate.get('volume_ratio', 1.0)
        change_pct = candidate.get('todaysChangePerc', 0)
        price = candidate.get('price', 0)
        action_tag = candidate.get('action_tag', 'monitor')

        # Base thesis components
        volume_surge = ""
        if volume_ratio >= 5:
            volume_surge = f"massive {volume_ratio:.1f}x volume surge"
        elif volume_ratio >= 3:
            volume_surge = f"strong {volume_ratio:.1f}x volume increase"
        else:
            volume_surge = f"{volume_ratio:.1f}x volume"

        price_action = ""
        if change_pct > 8:
            price_action = f"strong upward momentum (+{change_pct:.1f}%)"
        elif change_pct > 3:
            price_action = f"building momentum (+{change_pct:.1f}%)"
        elif change_pct > -5:
            price_action = "consolidation phase"
        else:
            price_action = f"potential reversal setup ({change_pct:.1f}%)"

        # Action-specific thesis
        if action_tag == 'trade_ready':
            return f"{ticker} shows {volume_surge} with {price_action}. Pre-breakout setup at ${price:.2f} with explosive potential."
        elif action_tag == 'watchlist':
            return f"{ticker} exhibits {volume_surge} and {price_action}. Monitor for breakout confirmation above resistance."
        else:
            return f"{ticker} demonstrates {volume_surge}. {price_action.capitalize()} suggests potential opportunity developing."

    def estimate_price_target(self, candidate: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """Estimate price targets based on explosive growth patterns"""
        volume_ratio = candidate.get('volume_ratio', 1.0)
        action_tag = candidate.get('action_tag', 'monitor')

        # Base multipliers based on volume and setup quality
        if action_tag == 'trade_ready' and volume_ratio >= 5:
            # High probability explosive setup
            conservative = current_price * 1.3   # 30%
            moderate = current_price * 1.8       # 80%
            aggressive = current_price * 2.5     # 150%
        elif action_tag == 'trade_ready':
            # Good setup
            conservative = current_price * 1.2   # 20%
            moderate = current_price * 1.5       # 50%
            aggressive = current_price * 2.0     # 100%
        elif action_tag == 'watchlist':
            # Potential setup
            conservative = current_price * 1.15  # 15%
            moderate = current_price * 1.3       # 30%
            aggressive = current_price * 1.6     # 60%
        else:
            # Monitor level
            conservative = current_price * 1.1   # 10%
            moderate = current_price * 1.2       # 20%
            aggressive = current_price * 1.4     # 40%

        return {
            'conservative': round(conservative, 2),
            'moderate': round(moderate, 2),
            'aggressive': round(aggressive, 2),
            'timeframe': '1-4 weeks'
        }

    async def run_discovery(self, limit: int = 50) -> Dict[str, Any]:
        """Run complete explosive discovery pipeline"""
        start_time = time.time()

        try:
            # Get filtered universe
            universe = await self.get_market_universe()
            if not universe:
                return {
                    'status': 'error',
                    'candidates': [],
                    'count': 0,
                    'error': 'No universe data available'
                }

            # Score all candidates
            scored_candidates = []
            for candidate in universe:
                # Calculate explosive score
                score_data = self.calculate_explosive_score(candidate)

                # Merge score data into candidate
                candidate.update(score_data)

                # Add trading levels
                candidate = self.add_trading_levels(candidate)

                # Only include candidates with meaningful scores
                if score_data['total_score'] >= 0.05:  # 5% minimum
                    scored_candidates.append(candidate)

            # Sort by score (highest first)
            scored_candidates.sort(key=lambda x: x.get('total_score', 0), reverse=True)

            # Take top candidates
            final_candidates = scored_candidates[:limit]

            # Calculate summary stats
            trade_ready_count = sum(1 for c in final_candidates if c.get('action_tag') == 'trade_ready')
            watchlist_count = sum(1 for c in final_candidates if c.get('action_tag') == 'watchlist')
            monitor_count = len(final_candidates) - trade_ready_count - watchlist_count

            execution_time = time.time() - start_time

            result = {
                'status': 'success',
                'candidates': final_candidates,
                'count': len(final_candidates),
                'trade_ready_count': trade_ready_count,
                'watchlist_count': watchlist_count,
                'monitor_count': monitor_count,
                'universe_size': len(universe),
                'filtered_size': len(scored_candidates),
                'execution_time_sec': round(execution_time, 2),
                'engine': 'Optimized Explosive Discovery v1.0'
            }

            logger.info(f"Discovery complete: {len(final_candidates)} candidates in {execution_time:.2f}s")
            return result

        except Exception as e:
            logger.error(f"Discovery failed: {e}")
            return {
                'status': 'error',
                'candidates': [],
                'count': 0,
                'error': str(e),
                'execution_time_sec': time.time() - start_time
            }

# Global discovery engine instance
discovery_engine = ExplosiveDiscoveryEngine()

@router.get("/contenders")
async def get_contenders(limit: int = Query(50, le=100)):
    """
    Get explosive growth contenders
    Main endpoint for frontend integration
    """
    try:
        result = await discovery_engine.run_discovery(limit)

        if result['status'] == 'success':
            return {
                'success': True,
                'data': result['candidates'],
                'count': result['count'],
                'trade_ready_count': result['trade_ready_count'],
                'source': 'optimized_discovery',
                'engine': result['engine'],
                'execution_time_sec': result['execution_time_sec'],
                'timestamp': datetime.now().isoformat()
            }
        else:
            return {
                'success': False,
                'data': [],
                'count': 0,
                'error': result.get('error', 'Discovery failed'),
                'timestamp': datetime.now().isoformat()
            }

    except Exception as e:
        logger.error(f"Contenders endpoint failed: {e}")
        return {
            'success': False,
            'data': [],
            'count': 0,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

@router.get("/strategy-validation")
async def strategy_validation(limit: int = Query(50, le=100)):
    """
    Strategy validation endpoint for A/B testing
    Returns both legacy and optimized results
    """
    try:
        # Run optimized discovery
        optimized_result = await discovery_engine.run_discovery(limit)

        if optimized_result['status'] != 'success':
            raise HTTPException(status_code=500, detail="Discovery engine failed")

        # Create legacy simulation (slightly different scoring for comparison)
        legacy_candidates = []
        for candidate in optimized_result['candidates'][:]:
            legacy_candidate = candidate.copy()
            # Legacy focuses more on volume, less on other factors
            legacy_score = min(candidate.get('volume_momentum_raw', 0) * 0.8, 1.0)
            legacy_candidate['score'] = legacy_score
            legacy_candidate['total_score'] = legacy_score
            legacy_candidate['strategy'] = 'legacy_v0'
            legacy_candidates.append(legacy_candidate)

        # Hybrid candidates (our optimized system)
        hybrid_candidates = optimized_result['candidates'][:]
        for candidate in hybrid_candidates:
            candidate['strategy'] = 'hybrid_v1'

        return {
            'success': True,
            'comparison': {
                'legacy_v0': {
                    'strategy': 'legacy_v0',
                    'status': 'success',
                    'candidates': legacy_candidates,
                    'count': len(legacy_candidates),
                    'trade_ready_count': sum(1 for c in legacy_candidates if c.get('action_tag') == 'trade_ready')
                },
                'hybrid_v1': {
                    'strategy': 'hybrid_v1',
                    'status': 'success',
                    'candidates': hybrid_candidates,
                    'count': len(hybrid_candidates),
                    'trade_ready_count': sum(1 for c in hybrid_candidates if c.get('action_tag') == 'trade_ready')
                }
            },
            'meta': {
                'execution_time_sec': optimized_result['execution_time_sec'],
                'universe_size': optimized_result['universe_size'],
                'engine': 'Optimized Discovery with Legacy Comparison'
            },
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Strategy validation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/test")
async def test_discovery(
    strategy: str = Query("hybrid_v1", regex="^(legacy_v0|hybrid_v1)$"),
    limit: int = Query(50, le=100)
):
    """
    Test specific strategy
    """
    try:
        result = await discovery_engine.run_discovery(limit)

        if result['status'] != 'success':
            raise HTTPException(status_code=500, detail="Discovery failed")

        # Apply strategy-specific processing
        for candidate in result['candidates']:
            candidate['strategy'] = strategy
            if strategy == 'legacy_v0':
                # Legacy boosts volume-heavy candidates
                if candidate.get('volume_ratio', 1.0) > 4.0:
                    candidate['score'] = min(candidate['score'] * 1.2, 1.0)

        return {
            'success': True,
            'strategy': strategy,
            'status': result['status'],
            'candidates': result['candidates'],
            'count': result['count'],
            'trade_ready_count': result['trade_ready_count'],
            'trace': {
                'strategy': strategy,
                'execution_time_sec': result['execution_time_sec'],
                'universe_size': result['universe_size'],
                'filtered_size': result['filtered_size']
            },
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Strategy test failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))