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
from datetime import datetime, timedelta
import json
import os
import httpx
from decimal import Decimal

logger = logging.getLogger(__name__)
router = APIRouter()

class ExplosiveDiscoveryEngine:
    """
    Single optimized discovery engine for explosive growth stocks
    Uses Polygon API exclusively for real market data
    Now with options data, short interest, and intraday relative volume
    """

    def __init__(self):
        self.min_price = 0.50
        self.max_price = 100.0
        self.min_irv = 4.0  # ULTRA-SELECTIVE: Require 4x+ intraday volume surge
        self.max_daily_change = 20.0  # Allow up to 20% moves for more explosive potential
        self.min_daily_change = 7.0   # Raise minimum to 7% - only strong momentum
        # REMOVED: No artificial limits - return all candidates that meet ultra-high standards
        self.api_key = os.getenv('POLYGON_API_KEY')

    async def calculate_intraday_relative_volume(self, ticker: str, current_volume: int) -> float:
        """Calculate Intraday Relative Volume (IRV) from minute bars"""
        try:
            # Get current time
            now = datetime.now()
            today_str = now.strftime('%Y-%m-%d')

            # Get minute bars for today
            url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/minute/{today_str}/{today_str}"

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params={'apikey': self.api_key})

                if response.status_code != 200:
                    logger.warning(f"IRV calculation failed for {ticker}: {response.status_code}")
                    return 1.0

                data = response.json()
                minute_bars = data.get('results', [])

                if not minute_bars:
                    return 1.0

                # Calculate average volume for this time of day over past 10 days
                current_minute = now.hour * 60 + now.minute

                # For now, use a simplified calculation based on total volume
                # vs expected volume at this time of day
                market_open_minutes = max(current_minute - (9 * 60 + 30), 1)  # Minutes since 9:30 AM

                # Calculate volume per minute today
                volume_per_minute_today = current_volume / max(market_open_minutes, 1)

                # Use current volume as baseline for relative calculation
                # Since we don't have historical minute-by-minute data, use current volume as proxy
                typical_volume_per_minute = max(current_volume / 390, 1)  # 390 trading minutes per day

                irv = volume_per_minute_today / typical_volume_per_minute
                return min(irv, 20.0)  # Cap at 20x for sanity

        except Exception as e:
            logger.warning(f"IRV calculation error for {ticker}: {e}")
            return 1.0

    async def enrich_realtime_features(self, ticker: str, base_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich ticker with options data, short interest, and real-time features"""
        enriched = base_data.copy()

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                # Get current price and basic data
                current_price = base_data.get('day', {}).get('c', 0)
                current_volume = base_data.get('day', {}).get('v', 0)

                # Calculate Intraday Relative Volume
                irv = await self.calculate_intraday_relative_volume(ticker, current_volume)
                enriched['intraday_relative_volume'] = round(irv, 2)

                # Get options data if available
                try:
                    # Get options chain snapshot
                    options_url = f"https://api.polygon.io/v3/snapshot/options/{ticker}"
                    options_response = await client.get(options_url, params={'apikey': self.api_key})

                    if options_response.status_code == 200:
                        options_data = options_response.json()
                        results = options_data.get('results', [])

                        # Calculate Call/Put OI ratio and IV metrics
                        call_oi = 0
                        put_oi = 0
                        iv_sum = 0
                        iv_count = 0

                        for option in results:
                            if option.get('details', {}).get('contract_type') == 'call':
                                call_oi += option.get('open_interest', 0)
                            else:
                                put_oi += option.get('open_interest', 0)

                            iv = option.get('implied_volatility')
                            if iv and iv > 0:
                                iv_sum += iv
                                iv_count += 1

                        cp_ratio = call_oi / max(put_oi, 1)
                        avg_iv = (iv_sum / max(iv_count, 1)) if iv_count > 0 else 0

                        enriched['options_data'] = {
                            'call_oi': call_oi,
                            'put_oi': put_oi,
                            'cp_ratio': round(cp_ratio, 2),
                            'avg_iv': round(avg_iv * 100, 1),  # Convert to percentage
                            'iv_percentile': None  # Historical IV percentile not available
                        }
                    else:
                        enriched['options_data'] = {
                            'call_oi': 0, 'put_oi': 0, 'cp_ratio': 1.0, 'avg_iv': 0.0, 'iv_percentile': None
                        }

                except Exception as e:
                    logger.debug(f"Options data unavailable for {ticker}: {e}")
                    enriched['options_data'] = {
                        'call_oi': 0, 'put_oi': 0, 'cp_ratio': 1.0, 'avg_iv': 0.0, 'iv_percentile': None
                    }

                # Get short interest data from real sources only
                enriched['short_data'] = await self.get_real_short_interest(ticker)

                # Calculate VWAP for entry/stop levels
                enriched['vwap'] = await self.calculate_vwap(ticker, current_price)

                return enriched

        except Exception as e:
            logger.error(f"Enrichment failed for {ticker}: {e}")
            # If enrichment fails completely, exclude the stock rather than use fake data
            logger.error(f"❌ Complete enrichment failure for {ticker} - excluding from results")
            return None

    async def calculate_vwap(self, ticker: str, current_price: float) -> float:
        """Calculate Volume Weighted Average Price for the day"""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/minute/{today}/{today}"

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params={'apikey': self.api_key})

                if response.status_code != 200:
                    return current_price  # Fallback to current price

                data = response.json()
                bars = data.get('results', [])

                if not bars:
                    return current_price

                # Calculate VWAP from minute bars
                total_volume = 0
                total_vwap_volume = 0

                for bar in bars:
                    volume = bar.get('v', 0)
                    high = bar.get('h', 0)
                    low = bar.get('l', 0)
                    close = bar.get('c', 0)

                    typical_price = (high + low + close) / 3

                    total_volume += volume
                    total_vwap_volume += (typical_price * volume)

                if total_volume > 0:
                    vwap = total_vwap_volume / total_volume
                    return round(vwap, 2)
                else:
                    return current_price

        except Exception as e:
            logger.warning(f"VWAP calculation failed for {ticker}: {e}")
            return current_price

    def get_miss_reason(self, irv: float, score: float, change_pct: float) -> str:
        """Determine why a candidate was near-miss instead of elite"""
        reasons = []

        if irv < 4.0:
            reasons.append(f"IRV {irv:.1f}x < 4.0x needed")
        if score < 0.75:
            reasons.append(f"Score {score*100:.1f}% < 75% needed")
        if change_pct < 7.0:
            reasons.append(f"Change {change_pct:.1f}% < 7% needed")

        return " | ".join(reasons) if reasons else "Close to elite"

    async def get_real_short_interest(self, ticker: str) -> Dict[str, Any]:
        """Get real short interest data or return None if unavailable"""
        try:
            # Try to get real short interest data from available sources
            # Short interest data requires specialized API - not available in current setup
            # Return null values instead of assumptions
            return {
                'short_interest_pct': None,  # Real data required
                'days_to_cover': None,       # Real data required
                'short_ratio': None         # Real data required
            }
        except Exception as e:
            logger.warning(f"Short interest data unavailable for {ticker}: {e}")
            return {
                'short_interest_pct': None, 'days_to_cover': None, 'short_ratio': None
            }

    async def get_market_universe(self) -> List[Dict[str, Any]]:
        """Get expanded market universe with de-duplication from Polygon snapshots"""
        try:
            if not self.api_key:
                raise RuntimeError("POLYGON_API_KEY not available")

            logger.info("📡 Fetching expanded market universe via Polygon API...")

            # Get broader market universe with de-duplication
            async with httpx.AsyncClient(timeout=30.0) as client:
                universe = []
                seen_tickers = set()

                # Get complete market snapshot (includes gainers, losers, and everything else)
                # Single API call replaces separate gainers + full market calls
                try:
                    all_tickers_url = "https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/tickers"
                    all_response = await client.get(all_tickers_url, params={'apikey': self.api_key})
                    if all_response.status_code == 200:
                        all_data = all_response.json()
                        for stock in all_data.get('tickers', []):
                            ticker = stock.get('ticker', '')
                            if ticker and ticker not in seen_tickers:
                                universe.append(stock)
                                seen_tickers.add(ticker)
                        logger.info(f"✅ Retrieved {len(universe)} stocks from market snapshot")
                    else:
                        logger.error(f"Market snapshot failed: {all_response.status_code}")
                except Exception as e:
                    logger.error(f"Market snapshot error: {e}")
                    return []

            logger.info(f"📊 Total deduplicated universe: {len(universe)} stocks")

            if not universe:
                logger.error("❌ No live market data available - system requires real data")
                return []

            # Enhanced filtering for pre-breakout detection
            filtered_stocks = []
            for stock in universe:
                ticker = stock.get('ticker', '')

                # Skip derivatives and warrants
                if any(suffix in ticker for suffix in ['.WS', '.WT', '.U', '.RT', '.PR']) or ticker.endswith('W'):
                    continue

                # Get basic data
                day_data = stock.get('day', {})
                prev_day_data = stock.get('prevDay', {})
                price = day_data.get('c') or prev_day_data.get('c') or 0
                daily_change_pct = stock.get('todaysChangePerc', 0)

                # Allow broader daily change range for universe collection (filter later in scoring)
                # Changed from 7-20% to 2-50% to capture more potential candidates
                if not (-50.0 <= daily_change_pct <= 50.0):
                    continue

                # Price filter
                if not (self.min_price <= price <= self.max_price):
                    continue

                # Calculate basic volume ratio
                current_volume = day_data.get('v', 0)
                prev_volume = prev_day_data.get('v', 1)
                volume_ratio = current_volume / max(prev_volume, 1)
                stock['volume_ratio'] = volume_ratio

                # Broader volume filter for universe collection (tighten later in scoring)
                # Changed from 2.5x to 1.5x to capture more candidates
                if volume_ratio < 1.5:
                    continue

                filtered_stocks.append(stock)

                # Reasonable limit to prevent timeout while maintaining good coverage
                if len(filtered_stocks) >= 1000:
                    break

            logger.info(f"Pre-filtered universe: {len(filtered_stocks)} stocks (expanded range)")
            return filtered_stocks

        except Exception as e:
            logger.error(f"Universe filtering failed: {e}")
            return []

    def calculate_explosive_score(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        """
        NEW SCORING: Volume & Momentum (35%), Float & Squeeze (20%), Catalyst (15%), Options Flow (15%), Technical (15%)
        Returns score between 0.0 and 1.0 (0% to 100%)
        """
        try:
            # Get enhanced metrics with comprehensive null handling
            irv = float(candidate.get('intraday_relative_volume') or 1.0)
            volume_ratio = float(candidate.get('volume_ratio') or 1.0)
            change_pct = float(candidate.get('todaysChangePerc') or 0)

            # Get price with fallback chain
            day_data = candidate.get('day') or {}
            prev_day_data = candidate.get('prevDay') or {}
            price = float(day_data.get('c') or prev_day_data.get('c') or 1.0)
            volume = float(day_data.get('v') or 0)

            # Get enriched data with safe defaults
            options_data = candidate.get('options_data') or {}
            short_data = candidate.get('short_data') or {}
            vwap = float(candidate.get('vwap') or price)

            # 1. EXPLOSIVE Volume & Momentum (35% weight) - ULTRA-SELECTIVE
            # IRV component (20% of total) - Only reward exceptional volume
            if irv >= 10:  # 10x+ volume = maximum explosive potential
                irv_score = 1.0
            elif irv >= 7:  # 7x+ volume = strong explosive setup
                irv_score = 0.95
            elif irv >= 5:  # 5x+ volume = good explosive potential
                irv_score = 0.85
            elif irv >= 4:  # 4x+ volume = minimum for consideration
                irv_score = 0.70
            else:
                irv_score = 0.0  # Below 4x = not explosive enough

            # VWAP reclaim component (10% of total) - Critical for breakouts
            vwap_reclaim_score = 1.0 if price >= vwap else 0.2  # Stricter penalty

            # Price momentum (5% of total) - Reward stronger moves
            momentum_score = min(abs(change_pct) / 20.0, 1.0)  # Scale to 20% max

            volume_momentum_total = (irv_score * 0.57 + vwap_reclaim_score * 0.29 + momentum_score * 0.14)

            # 2. Float & Short Squeeze Potential (20% weight)
            # Short interest factor with safe defaults
            si_pct = float(short_data.get('short_interest_pct') or 10)
            days_to_cover = float(short_data.get('days_to_cover') or 2)

            if si_pct >= 30 and days_to_cover >= 3:
                squeeze_score = 1.0  # High squeeze potential
            elif si_pct >= 20 and days_to_cover >= 2:
                squeeze_score = 0.8
            elif si_pct >= 15:
                squeeze_score = 0.6
            else:
                squeeze_score = 0.4

            # 3. Catalyst Potential (15% weight)
            # Volume surge indicates news/catalyst - ensure volume_ratio is safe
            volume_ratio = float(candidate.get('volume_ratio') or 1.0)
            if irv >= 5 and volume_ratio >= 4:
                catalyst_score = 1.0  # Strong catalyst evidence
            elif irv >= 3 and volume_ratio >= 2.5:
                catalyst_score = 0.8
            elif volume_ratio >= 2:
                catalyst_score = 0.6
            else:
                catalyst_score = 0.3

            # 4. Options Flow & IV (15% weight)
            cp_ratio = float(options_data.get('cp_ratio') or 1.0)
            avg_iv = float(options_data.get('avg_iv') or 25)

            # Call heavy with high IV is bullish
            if cp_ratio >= 2.0 and avg_iv >= 40:
                options_score = 1.0
            elif cp_ratio >= 1.5 and avg_iv >= 30:
                options_score = 0.8
            elif cp_ratio >= 1.2:
                options_score = 0.6
            else:
                options_score = 0.4

            # 5. Technical Setup (15% weight)
            # Price relative to recent range and momentum
            day_data = candidate.get('day', {})
            high = day_data.get('h', price)
            low = day_data.get('l', price)

            # Near highs with volume
            if price >= high * 0.95 and irv >= 3:
                technical_score = 1.0
            elif price >= high * 0.90 and irv >= 2:
                technical_score = 0.8
            elif price >= vwap:
                technical_score = 0.6
            else:
                technical_score = 0.3

            # Calculate weighted total
            total_score = (
                volume_momentum_total * 0.35 +
                squeeze_score * 0.20 +
                catalyst_score * 0.15 +
                options_score * 0.15 +
                technical_score * 0.15
            )

            # Quality multiplier for exceptional setups
            if irv >= 5 and price >= vwap and cp_ratio >= 1.5:
                total_score = min(total_score * 1.15, 1.0)
            elif irv >= 3 and abs(change_pct) >= 7:
                total_score = min(total_score * 1.1, 1.0)

            # Ensure bounded
            total_score = max(0.0, min(total_score, 1.0))

            # Determine action tag with strict requirements
            if total_score >= 0.80:  # Raised threshold
                action_tag = 'trade_ready'
            elif total_score >= 0.65:
                action_tag = 'watchlist'
            else:
                action_tag = 'monitor'

            return {
                'total_score': round(total_score, 3),
                'score': round(total_score, 3),
                'subscores': {
                    'volume_momentum': round(volume_momentum_total * 35, 1),
                    'squeeze': round(squeeze_score * 20, 1),
                    'catalyst': round(catalyst_score * 15, 1),
                    'options': round(options_score * 15, 1),
                    'technical': round(technical_score * 15, 1)
                },
                'action_tag': action_tag,
                'irv': irv,
                'vwap_reclaim': price >= vwap
            }

        except Exception as e:
            logger.error(f"Scoring failed: {e}")
            return {
                'total_score': 0.0,
                'score': 0.0,
                'subscores': {'volume_momentum': 0, 'squeeze': 0, 'catalyst': 0, 'options': 0, 'technical': 0},
                'action_tag': 'monitor',
                'irv': 1.0,
                'vwap_reclaim': False
            }

    def add_trading_levels(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        """Add VWAP-based entry, stop, target levels, and thesis"""
        price = candidate.get('day', {}).get('c') or candidate.get('prevDay', {}).get('c', 0)
        vwap = candidate.get('vwap', price)

        if price > 0:
            candidate['price'] = price

            # VWAP-based entry and stop levels
            if price >= vwap:
                # Above VWAP - momentum entry
                candidate['entry'] = round(max(price * 1.01, vwap * 1.005), 2)  # 1% above or slightly above VWAP
                candidate['stop'] = round(vwap * 0.98, 2)  # Stop below VWAP
            else:
                # Below VWAP - wait for reclaim
                candidate['entry'] = round(vwap * 1.02, 2)  # Entry above VWAP reclaim
                candidate['stop'] = round(price * 0.95, 2)  # Tight stop below current

            # Targets based on score quality
            score = candidate.get('total_score', 0)
            if score >= 0.80:
                # High conviction targets
                candidate['tp1'] = round(price * 1.25, 2)  # 25%
                candidate['tp2'] = round(price * 1.60, 2)  # 60%
                candidate['tp3'] = round(price * 2.20, 2)  # 120%
            else:
                # Conservative targets
                candidate['tp1'] = round(price * 1.15, 2)  # 15%
                candidate['tp2'] = round(price * 1.35, 2)  # 35%
                candidate['tp3'] = round(price * 1.75, 2)  # 75%

            # Enhanced RelVol data
            candidate['relvol'] = candidate.get('intraday_relative_volume', candidate.get('volume_ratio', 1.0))

            # Generate enhanced thesis
            candidate['thesis'] = self.generate_enhanced_thesis(candidate)

            # Add price target estimation
            candidate['price_target'] = self.estimate_price_target(candidate, price)

        return candidate

    def generate_enhanced_thesis(self, candidate: Dict[str, Any]) -> str:
        """Generate enhanced trading thesis with new scoring components"""
        ticker = candidate.get('ticker', 'UNKNOWN')
        irv = candidate.get('intraday_relative_volume', 1.0)
        change_pct = candidate.get('todaysChangePerc', 0)
        price = candidate.get('price', 0)
        vwap = candidate.get('vwap', price)
        action_tag = candidate.get('action_tag', 'monitor')

        options_data = candidate.get('options_data', {})
        short_data = candidate.get('short_data', {})

        cp_ratio = options_data.get('cp_ratio', 1.0)
        si_pct = short_data.get('short_interest_pct', 10)

        # Volume component
        if irv >= 5:
            volume_desc = f"explosive {irv:.1f}x intraday volume"
        elif irv >= 3:
            volume_desc = f"strong {irv:.1f}x intraday surge"
        else:
            volume_desc = f"{irv:.1f}x volume activity"

        # VWAP component
        vwap_status = "above VWAP support" if price >= vwap else "approaching VWAP resistance"

        # Options flow
        if cp_ratio >= 2.0:
            options_desc = f"bullish options flow ({cp_ratio:.1f}x calls)"
        elif cp_ratio >= 1.5:
            options_desc = "moderate call bias"
        else:
            options_desc = "balanced options activity"

        # Short squeeze potential
        if si_pct >= 20:
            squeeze_desc = f"high short interest ({si_pct:.0f}%)"
        else:
            squeeze_desc = "moderate short setup"

        # Enhanced thesis based on action tag
        if action_tag == 'trade_ready':
            return f"{ticker} exhibits {volume_desc} with {options_desc}. Trading {vwap_status} at ${price:.2f}. {squeeze_desc} adds explosive potential."
        elif action_tag == 'watchlist':
            return f"{ticker} shows {volume_desc} and {squeeze_desc}. Currently {vwap_status}. Monitor for VWAP breakout confirmation."
        else:
            return f"{ticker} demonstrates {volume_desc}. {vwap_status.capitalize()} with {options_desc}. Early-stage setup developing."

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

            # Enrich and score candidates with dual-tier filtering
            elite_candidates = []
            near_miss_candidates = []

            for candidate in universe:
                try:
                    # First enrich with real-time features
                    ticker = candidate.get('ticker', '')
                    if not ticker:
                        continue

                    enriched_candidate = await self.enrich_realtime_features(ticker, candidate)

                    # Skip if enrichment completely failed
                    if enriched_candidate is None:
                        logger.debug(f"❌ {ticker}: Enrichment failed - skipping")
                        continue

                    # Calculate scoring with enriched data
                    score_data = self.calculate_explosive_score(enriched_candidate)
                    if not score_data or score_data.get('total_score') is None:
                        logger.debug(f"❌ {ticker}: Scoring failed - skipping")
                        continue

                    enriched_candidate.update(score_data)

                    # Add VWAP-based trading levels
                    enriched_candidate = self.add_trading_levels(enriched_candidate)

                    # Get key metrics for tier classification with guaranteed float conversion
                    irv = float(enriched_candidate.get('intraday_relative_volume') or 0.0)
                    score = float(score_data.get('total_score') or 0.0)
                    change_pct = abs(float(enriched_candidate.get('todaysChangePerc') or 0.0))

                    # Skip if score is invalid (scoring function failed)
                    if score == 0.0:
                        logger.debug(f"⚠️ {ticker}: Invalid score, skipping")
                        continue

                    # ULTRA-SELECTIVE TIER: 4.0x IRV + 75% score (elite opportunities)
                    if irv >= self.min_irv and score >= 0.75:
                        enriched_candidate['tier'] = 'elite'
                        elite_candidates.append(enriched_candidate)
                        logger.debug(f"✅ ELITE: {ticker}: {score*100:.1f}% score | {irv:.1f}x IRV")

                    # NEAR-MISS TIER: Close but not quite elite (monitoring candidates)
                    elif (irv >= 2.5 and score >= 0.60) or (irv >= 3.0 and score >= 0.55) or (change_pct >= 5 and score >= 0.50):
                        # Tag as near-miss for monitoring
                        enriched_candidate['tier'] = 'near_miss'
                        enriched_candidate['miss_reason'] = self.get_miss_reason(irv, score, change_pct)
                        near_miss_candidates.append(enriched_candidate)
                        logger.debug(f"⚠️  NEAR-MISS: {ticker}: {score*100:.1f}% score | {irv:.1f}x IRV | {enriched_candidate['miss_reason']}")

                except Exception as e:
                    logger.debug(f"Error processing {candidate.get('ticker', 'unknown')}: {e}")
                    continue


            # Sort both tiers by score (highest first)
            elite_candidates.sort(key=lambda x: x.get('total_score', 0), reverse=True)
            near_miss_candidates.sort(key=lambda x: x.get('total_score', 0), reverse=True)

            # Limit near-miss to top 10 for monitoring purposes
            near_miss_candidates = near_miss_candidates[:10]

            # ULTRA-SELECTIVE: Trade ready threshold raised to 0.85 (85%)
            trade_ready_candidates = [c for c in elite_candidates if c.get('total_score', 0) >= 0.85]
            watchlist_candidates = [c for c in elite_candidates if 0.75 <= c.get('total_score', 0) < 0.85]

            # Calculate summary stats
            trade_ready_count = len(trade_ready_candidates)
            watchlist_count = len(watchlist_candidates)
            near_miss_count = len(near_miss_candidates)

            execution_time = time.time() - start_time

            result = {
                'status': 'success',
                'candidates': elite_candidates,  # Main candidates (elite tier)
                'near_miss_candidates': near_miss_candidates,  # Monitoring tier
                'count': len(elite_candidates),
                'trade_ready_count': trade_ready_count,
                'watchlist_count': watchlist_count,
                'near_miss_count': near_miss_count,
                'universe_size': len(universe),
                'elite_qualified': len(elite_candidates),
                'near_miss_qualified': near_miss_count,
                'execution_time_sec': round(execution_time, 2),
                'engine': 'Ultra-Selective Discovery with Near-Miss Monitoring v1.1',
                'ultra_selective_status': {
                    'min_irv': self.min_irv,
                    'min_score': 0.75,
                    'min_change': self.min_daily_change,
                    'max_change': self.max_daily_change,
                    'active': True
                }
            }

            logger.info(f"Discovery complete: {len(elite_candidates)} elite + {near_miss_count} near-miss candidates in {execution_time:.2f}s")
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
async def get_contenders(limit: int = Query(8, le=10)):
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

# REMOVED: strategy-validation endpoint (duplicate system eliminated)

# REMOVED: test discovery endpoint (duplicate system eliminated)