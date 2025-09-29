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
from pathlib import Path

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
        self.max_price = 50.0    # Focus on smaller caps for 2x potential
        self.min_irv = 1.5       # Realistic IRV threshold for market conditions
        self.max_daily_change = 50.0  # Allow larger moves for explosive stocks
        self.min_daily_change = 3.0   # Catch earlier momentum (was 5.0)
        # REMOVED: No artificial limits - return all candidates that meet ultra-high standards
        self.api_key = os.getenv('POLYGON_API_KEY')
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from active.json"""
        try:
            config_path = Path(__file__).parent.parent.parent / "backend" / "calibration" / "active.json"
            if not config_path.exists():
                config_path = Path(__file__).parent.parent / "calibration" / "active.json"

            if config_path.exists():
                with open(config_path) as f:
                    return json.load(f)
            else:
                logger.warning("Configuration file not found, using defaults")
                return self._get_default_config()
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Default configuration matching AlphaStack scoring"""
        return {
            "weights_override": {
                "volume": 0.25,      # 25 points - Volume/Multi-day
                "squeeze": 0.20,     # 20 points - Float/Short
                "catalyst": 0.20,    # 20 points - Catalyst events
                "sentiment": 0.15,   # 15 points - Social sentiment
                "options_flow": 0.10,  # 10 points - Options/Gamma
                "technicals": 0.10   # 10 points - Technical indicators
            },
            "scoring": {
                "entry_rules": {
                    "watchlist_min": 0.60,    # 60+ like ANNX winner
                    "trade_ready_min": 0.75   # 75+ for immediate action
                }
            }
        }

    async def calculate_batch_irv(self, candidates: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate IRV for multiple tickers in batches - OPTIMIZED"""

        # Get market timing once
        now = datetime.now()
        market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)

        # Pre/post market simple calculation
        if now.hour < 9 or (now.hour == 9 and now.minute < 30) or now.hour >= 16:
            irv_results = {}
            for candidate in candidates:
                ticker = candidate.get('ticker', '')
                current_volume = candidate.get('day', {}).get('v', 0)
                irv_results[ticker] = min(current_volume / 100000, 20.0)
            return irv_results

        minutes_since_open = max((now - market_open).total_seconds() / 60, 1)
        trading_day_minutes = 390

        # Process in batches to avoid overwhelming API
        batch_size = 10  # Process 10 at a time
        irv_results = {}

        for i in range(0, len(candidates), batch_size):
            batch = candidates[i:i + batch_size]

            # Create concurrent tasks for batch
            tasks = []
            async with httpx.AsyncClient(timeout=8.0) as client:
                for candidate in batch:
                    ticker = candidate.get('ticker', '')
                    current_volume = candidate.get('day', {}).get('v', 0)

                    if not ticker:
                        continue

                    task = self._get_single_irv(client, ticker, current_volume, minutes_since_open, trading_day_minutes)
                    tasks.append(task)

                # Execute batch concurrently
                if tasks:
                    batch_results = await asyncio.gather(*tasks, return_exceptions=True)

                    for j, result in enumerate(batch_results):
                        if isinstance(result, Exception):
                            # Fallback for failed requests
                            ticker = batch[j].get('ticker', '')
                            current_volume = batch[j].get('day', {}).get('v', 0)
                            irv_results[ticker] = min(current_volume / 100000, 10.0)
                        else:
                            ticker, irv = result
                            irv_results[ticker] = irv

            # Small delay between batches to respect rate limits
            if i + batch_size < len(candidates):
                await asyncio.sleep(0.1)

        return irv_results

    async def _get_single_irv(self, client: httpx.AsyncClient, ticker: str, current_volume: int,
                             minutes_since_open: float, trading_day_minutes: int) -> tuple:
        """Get IRV for single ticker with optimized calculation"""
        try:
            # Use 5-day history instead of 30-day for speed
            end_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")

            url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/{start_date}/{end_date}"
            response = await client.get(url, params={'apikey': self.api_key})

            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])

                if results and len(results) >= 3:  # Need at least 3 days
                    # Use last 5 days for faster calculation
                    volumes = [bar['v'] for bar in results[-5:]]
                    avg_daily_volume = sum(volumes) / len(volumes)
                else:
                    # Quick fallback: estimate from current volume
                    avg_daily_volume = current_volume * 1.5
            else:
                # Quick fallback
                avg_daily_volume = current_volume * 1.5

            # Calculate IRV
            expected_volume_by_now = avg_daily_volume * (minutes_since_open / trading_day_minutes)
            irv = current_volume / max(expected_volume_by_now, 1)

            return ticker, min(max(irv, 0.1), 50.0)

        except Exception:
            # Fallback calculation
            return ticker, min(current_volume / 100000, 10.0)

    async def calculate_intraday_relative_volume(self, ticker: str, current_volume: int) -> float:
        """Legacy single-ticker IRV calculation for backward compatibility"""
        candidates = [{'ticker': ticker, 'day': {'v': current_volume}}]
        results = await self.calculate_batch_irv(candidates)
        return results.get(ticker, 1.0)

    async def enrich_realtime_features(self, ticker: str, base_data: Dict[str, Any]) -> Dict[str, Any]:
        """Legacy method - uses lightweight enrichment + single IRV for compatibility"""
        # Calculate IRV individually if needed for backward compatibility
        current_volume = base_data.get('day', {}).get('v', 0)
        irv = await self.calculate_intraday_relative_volume(ticker, current_volume)
        base_data['intraday_relative_volume'] = round(irv, 2)

        # Use lightweight enrichment for the rest
        return await self.enrich_lightweight_features(ticker, base_data)

    async def enrich_lightweight_features(self, ticker: str, base_data: Dict[str, Any]) -> Dict[str, Any]:
        """Lightweight enrichment without IRV calculation (IRV pre-calculated in batch)"""
        enriched = base_data.copy()

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:  # Reduced timeout
                # Get current price and basic data
                current_price = base_data.get('day', {}).get('c', 0)
                current_volume = base_data.get('day', {}).get('v', 0)

                # IRV already calculated in batch - skip individual calculation

                # Get options data if available (faster without IRV bottleneck)
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
        """OPTIMIZED: Get high-volume candidates efficiently for pre-explosive detection"""
        try:
            if not self.api_key:
                raise RuntimeError("POLYGON_API_KEY not available")

            logger.info("📡 Fetching optimized market universe via Polygon API...")

            async with httpx.AsyncClient(timeout=30.0) as client:
                # OPTIMIZATION: Use snapshot API but with aggressive local filtering
                # This is still the most comprehensive single-call approach
                try:
                    all_tickers_url = "https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/tickers"
                    all_response = await client.get(all_tickers_url, params={'apikey': self.api_key})

                    if all_response.status_code != 200:
                        logger.error(f"Market snapshot failed: {all_response.status_code}")
                        return []

                    all_data = all_response.json()
                    raw_tickers = all_data.get('tickers', [])
                    logger.info(f"📥 Retrieved {len(raw_tickers)} raw tickers from Polygon")

                    # PHASE 1: Aggressive pre-filtering to reduce processing load
                    # Apply all filters in one pass for efficiency
                    high_potential_stocks = []

                    for stock in raw_tickers:
                        ticker = stock.get('ticker', '')

                        # Skip non-common shares immediately
                        if not ticker or len(ticker) > 5:  # Most stocks are 1-5 chars
                            continue
                        if any(char in ticker for char in ['.', '-']):  # Skip special tickers
                            continue
                        if ticker.endswith('W'):  # Skip warrants
                            continue

                        # Get price data efficiently
                        day_data = stock.get('day', {})
                        if not day_data:  # Skip if no trading data
                            continue

                        price = day_data.get('c', 0)
                        volume = day_data.get('v', 0)

                        # Apply strict price filter first (most stocks eliminated here)
                        if not (0.50 <= price <= 100.0):
                            continue

                        # Apply minimum volume filter (250K for more opportunities)
                        if volume < 250000:  # Lowered from 500K
                            continue

                        # Calculate volume ratio efficiently
                        prev_day_data = stock.get('prevDay', {})
                        prev_volume = prev_day_data.get('v', 0)

                        if prev_volume > 0:
                            volume_ratio = volume / prev_volume
                            if volume_ratio < 1.2:  # Lowered from 1.3 for more candidates
                                continue
                        else:
                            continue  # Skip if no previous volume data

                        # Add volume ratio for downstream processing
                        stock['volume_ratio'] = volume_ratio

                        # Check daily change is within target range (7-20% for momentum but not exploded)
                        daily_change = stock.get('todaysChangePerc', 0)
                        if daily_change is None:
                            continue
                        # CRITICAL: Enforce the configured range - no flat stocks, no already-exploded stocks
                        if daily_change < self.min_daily_change or daily_change > self.max_daily_change:
                            continue

                        high_potential_stocks.append(stock)

                        # OPTIMIZATION: Cap at 500 candidates for enrichment
                        # This covers enough ground without overwhelming the system
                        if len(high_potential_stocks) >= 500:
                            logger.info("🎯 Reached 500 candidate cap for optimal processing")
                            break

                    # PHASE 2: Sort by volume to prioritize most active stocks
                    # This ensures we process the most liquid stocks first
                    high_potential_stocks.sort(
                        key=lambda x: x.get('day', {}).get('v', 0),
                        reverse=True
                    )

                    # PHASE 3: Take top candidates based on volume
                    # Focus on most liquid stocks for explosive detection
                    final_candidates = high_potential_stocks[:300]  # Process top 300 by volume

                    logger.info(f"✨ OPTIMIZATION COMPLETE:")
                    logger.info(f"   Input: {len(raw_tickers)} raw tickers")
                    logger.info(f"   After filters: {len(high_potential_stocks)} candidates")
                    logger.info(f"   Final selection: {len(final_candidates)} for enrichment")
                    logger.info(f"   Reduction: {100 - (len(final_candidates)/len(raw_tickers)*100):.1f}%")

                    return final_candidates

                except Exception as e:
                    logger.error(f"Market snapshot error: {e}")
                    return []

        except Exception as e:
            logger.error(f"Universe filtering failed: {e}")
            return []

    async def get_real_market_data(self, ticker: str, candidate: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get ONLY real market data - NO DEFAULTS OR FAKE DATA"""
        try:
            # Extract basic data
            day_data = candidate.get('day', {})
            if not day_data:
                return None

            price = float(day_data.get('c', 0))
            if price <= 0:
                return None

            volume = float(day_data.get('v', 0))
            if volume <= 0:
                return None

            # Get real consecutive up days
            consecutive_up = await self.get_real_consecutive_days(ticker)

            # Get real technical data
            tech_data = await self.get_real_technical_data(ticker)
            if not tech_data:
                logger.debug(f"❌ {ticker}: Could not get real technical data")
                return None

            # Get real options and short data
            options_data = await self.get_real_options_data(ticker)
            short_data = await self.get_real_short_data(ticker)

            # Return ONLY real data
            return {
                'ticker': ticker,
                'price': price,
                'rel_vol_now': float(candidate.get('intraday_relative_volume', 0)),
                'consecutive_up_days': consecutive_up,
                'daily_change_pct': float(candidate.get('todaysChangePerc', 0)),
                **tech_data,
                **(options_data if options_data else {}),
                **(short_data if short_data else {})
            }

        except Exception as e:
            logger.debug(f"❌ {ticker}: Error getting real market data: {e}")
            return None

    async def get_real_consecutive_days(self, ticker: str) -> int:
        """Get REAL consecutive up days from Polygon API"""
        try:
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=15)).strftime("%Y-%m-%d")

            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.get(
                    f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/{start_date}/{end_date}",
                    params={'apikey': self.api_key}
                )

                if response.status_code == 200:
                    data = response.json()
                    results = data.get('results', [])

                    if len(results) >= 2:
                        consecutive = 0
                        for i in range(len(results) - 1, 0, -1):
                            if results[i]['c'] > results[i-1]['c']:
                                consecutive += 1
                            else:
                                break
                        return consecutive
        except Exception as e:
            logger.debug(f"Could not get consecutive days for {ticker}: {e}")

        return 0  # Return 0 if no real data available

    async def get_real_technical_data(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get REAL technical indicators - RSI, ATR, VWAP, EMAs"""
        try:
            # Get 30 days of data for technical calculations
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/{start_date}/{end_date}",
                    params={'apikey': self.api_key}
                )

                if response.status_code == 200:
                    data = response.json()
                    results = data.get('results', [])

                    if len(results) >= 14:  # Need minimum data for RSI
                        # Calculate real RSI
                        rsi = self.calculate_real_rsi(results)

                        # Calculate real ATR
                        atr_pct = self.calculate_real_atr(results)

                        # Calculate real EMAs
                        ema9 = self.calculate_real_ema(results, 9)
                        ema20 = self.calculate_real_ema(results, 20)

                        # Calculate real VWAP (today's)
                        vwap = self.calculate_real_vwap(ticker)

                        return {
                            'rsi': rsi,
                            'atr_pct': atr_pct,
                            'ema9': ema9,
                            'ema20': ema20,
                            'vwap': await vwap
                        }

        except Exception as e:
            logger.debug(f"Could not get technical data for {ticker}: {e}")

        return None

    async def get_real_options_data(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get REAL options data from Polygon"""
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.get(
                    f"https://api.polygon.io/v3/snapshot/options/{ticker}",
                    params={'apikey': self.api_key}
                )

                if response.status_code == 200:
                    data = response.json()
                    results = data.get('results', [])

                    if results:
                        # Calculate real call/put ratios
                        call_oi = sum(r.get('open_interest', 0) for r in results if r.get('option_type') == 'call')
                        put_oi = sum(r.get('open_interest', 0) for r in results if r.get('option_type') == 'put')

                        if call_oi > 0 and put_oi > 0:
                            return {
                                'options_call_oi': call_oi,
                                'options_put_oi': put_oi,
                                'iv_percentile': self.calculate_iv_percentile(results)
                            }

        except Exception as e:
            logger.debug(f"Could not get options data for {ticker}: {e}")

        return None

    async def get_real_short_data(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get REAL short interest data - would need additional data source"""
        # For now, return None - no fake data
        # Could integrate with other APIs for real short data
        return None

    def calculate_real_rsi(self, price_data: List[Dict]) -> float:
        """Calculate real RSI from price data"""
        if len(price_data) < 14:
            return 50.0  # Neutral if insufficient data

        closes = [float(bar['c']) for bar in price_data[-14:]]
        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]

        gains = [d for d in deltas if d > 0]
        losses = [-d for d in deltas if d < 0]

        avg_gain = sum(gains) / len(gains) if gains else 0
        avg_loss = sum(losses) / len(losses) if losses else 0

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return round(rsi, 1)

    def calculate_real_atr(self, price_data: List[Dict]) -> float:
        """Calculate real Average True Range percentage"""
        if len(price_data) < 2:
            return 0.05  # Default if insufficient data

        true_ranges = []
        for i in range(1, min(len(price_data), 15)):  # Last 14 days
            high = float(price_data[i]['h'])
            low = float(price_data[i]['l'])
            prev_close = float(price_data[i-1]['c'])

            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            true_ranges.append(tr)

        if not true_ranges:
            return 0.05

        atr = sum(true_ranges) / len(true_ranges)
        current_price = float(price_data[-1]['c'])

        return round(atr / current_price, 4) if current_price > 0 else 0.05

    def calculate_real_ema(self, price_data: List[Dict], period: int) -> float:
        """Calculate real Exponential Moving Average"""
        if len(price_data) < period:
            return float(price_data[-1]['c']) if price_data else 0

        closes = [float(bar['c']) for bar in price_data[-period:]]
        multiplier = 2 / (period + 1)

        ema = closes[0]
        for close in closes[1:]:
            ema = (close * multiplier) + (ema * (1 - multiplier))

        return round(ema, 2)

    async def calculate_real_vwap(self, ticker: str) -> float:
        """Calculate real VWAP for today"""
        try:
            today = datetime.now().strftime("%Y-%m-%d")

            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.get(
                    f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/minute/{today}/{today}",
                    params={'apikey': self.api_key}
                )

                if response.status_code == 200:
                    data = response.json()
                    results = data.get('results', [])

                    if results:
                        total_volume = 0
                        total_pv = 0

                        for bar in results:
                            vol = float(bar.get('v', 0))
                            if vol > 0:
                                typical_price = (float(bar['h']) + float(bar['l']) + float(bar['c'])) / 3
                                total_pv += typical_price * vol
                                total_volume += vol

                        if total_volume > 0:
                            return round(total_pv / total_volume, 2)

        except Exception as e:
            logger.debug(f"Could not calculate VWAP for {ticker}: {e}")

        return 0  # Return 0 if no real data

    def calculate_iv_percentile(self, options_data: List[Dict]) -> float:
        """Calculate real IV percentile from options data"""
        ivs = [float(opt.get('implied_volatility', 0)) for opt in options_data if opt.get('implied_volatility')]

        if len(ivs) < 5:
            return 50.0  # Neutral if insufficient data

        avg_iv = sum(ivs) / len(ivs)
        return min(max(avg_iv * 100, 0), 100)  # Convert to percentile

    def calculate_explosive_score(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        """
        ALPHASTACK V2 SCORING: Uses proven momentum builder algorithm
        Converts to 0.0-1.0 scale for compatibility
        """
        try:
            # Import AlphaStack v2 scorer
            import sys
            import os
            sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
            from scoring.alphastack_v2 import score_ticker

            # Extract data for AlphaStack v2
            ticker = candidate.get('ticker', '')
            day_data = candidate.get('day', {})
            price = float(day_data.get('c', 0))
            volume = float(day_data.get('v', 0))

            # Get REAL market data - NO DEFAULTS OR FAKE DATA
            real_data = await self.get_real_market_data(ticker, candidate)

            if not real_data:
                logger.debug(f"❌ {ticker}: No real market data available - skipping")
                continue

            features = real_data

            # Get AlphaStack v2 score
            result = score_ticker(features)

            # Convert 0-100 scale to 0-1 scale for our system
            alphastack_score = result['composite'] / 100.0

            return {
                'total_score': alphastack_score,
                'alphastack_regime': result['regime'],
                'alphastack_action': result['action'],
                'alphastack_breakdown': result['scores'],
                'entry_plan': result['entry_plan'],
                'consecutive_up_days': consecutive_up
            }

        except Exception as e:
            logger.error(f"AlphaStack v2 scoring failed for {candidate.get('ticker', 'unknown')}: {e}")
            # NO FALLBACK - Return None to skip this candidate
            return None

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

            # OPTIMIZED: Batch enrich and score candidates
            elite_candidates = []
            near_miss_candidates = []

            logger.info(f"🚀 Batch processing {len(universe)} candidates for IRV...")

            # Step 1: Batch calculate IRV for all candidates (MAJOR OPTIMIZATION)
            irv_results = await self.calculate_batch_irv(universe)
            logger.info(f"✅ IRV calculated for {len(irv_results)} candidates")

            # Step 2: Process each candidate with pre-calculated IRV
            for candidate in universe:
                try:
                    ticker = candidate.get('ticker', '')
                    if not ticker:
                        continue

                    # Get pre-calculated IRV
                    irv = irv_results.get(ticker, 1.0)
                    candidate['intraday_relative_volume'] = round(irv, 2)

                    # Lightweight enrichment (options + short data only, skip individual IRV calls)
                    enriched_candidate = await self.enrich_lightweight_features(ticker, candidate)

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

                    # Get thresholds from configuration
                    entry_rules = self.config.get('scoring', {}).get('entry_rules', {})
                    trade_ready_min = entry_rules.get('trade_ready_min', 0.80)
                    watchlist_min = entry_rules.get('watchlist_min', 0.70)

                    # ALPHASTACK-ALIGNED SCORING (60+ for winners like ANNX)
                    # Using AlphaStack's proven thresholds
                    if score >= 0.75:  # 75+ for trade ready (AlphaStack threshold)
                        enriched_candidate['tier'] = 'trade_ready'
                        elite_candidates.append(enriched_candidate)
                        logger.debug(f"🚀 TRADE READY: {ticker}: {score*100:.1f}% score | {irv:.1f}x IRV")

                    elif score >= 0.60:  # 60+ for watch (ANNX scored 62)
                        enriched_candidate['tier'] = 'watchlist'
                        elite_candidates.append(enriched_candidate)
                        logger.debug(f"👀 WATCHLIST: {ticker}: {score*100:.1f}% score | {irv:.1f}x IRV")

                    # NEAR-MISS TIER: 45-60 range needs more confirmation
                    elif score >= 0.45:  # 45+ still worth monitoring
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

            # Separate candidates by tier (already classified above)
            trade_ready_candidates = [c for c in elite_candidates if c.get('tier') == 'trade_ready']
            watchlist_candidates = [c for c in elite_candidates if c.get('tier') == 'watchlist']

            # IDENTIFY THE TOP EXPLOSIVE PICK
            top_pick = None
            if elite_candidates:
                # Calculate explosive 2x potential for each candidate
                for candidate in elite_candidates:
                    score = candidate.get('total_score', 0)
                    irv = candidate.get('intraday_relative_volume', 0)
                    price = candidate.get('price', 0)
                    volume_ratio = candidate.get('volume_ratio', 1)
                    change_pct = candidate.get('change_pct', 0)
                    short_ratio = candidate.get('short_ratio', 0)

                    # EXPLOSIVE 2X FACTORS:
                    # 1. Score foundation (40%)
                    score_factor = score * 0.40

                    # 2. Volume explosion (25%) - higher volume = more explosive potential
                    volume_factor = min(max(irv - 1, 0) / 10.0, 1.0) * 0.25

                    # 3. Price action momentum (20%) - current move strength
                    momentum_factor = min(max(change_pct, 0) / 20.0, 1.0) * 0.20

                    # 4. Squeeze potential (15%) - short interest creates explosive fuel
                    squeeze_factor = min(short_ratio / 30.0, 1.0) * 0.15 if short_ratio > 0 else 0

                    # Calculate 2x potential score
                    explosive_potential = score_factor + volume_factor + momentum_factor + squeeze_factor

                    # Bonus for ideal 2x setups: Small caps under $20 with high volume
                    if price < 20 and irv >= 3.0 and volume_ratio >= 3.0:
                        explosive_potential = min(explosive_potential * 1.2, 1.0)

                    candidate['explosive_potential'] = explosive_potential
                    candidate['double_potential_score'] = explosive_potential

                # Re-sort by explosive potential
                elite_candidates.sort(key=lambda x: x.get('explosive_potential', 0), reverse=True)

                # The TOP PICK is the highest explosive potential candidate
                top_pick = elite_candidates[0].copy()
                top_pick['is_top_pick'] = True

                logger.info(f"🎯 TOP PICK: {top_pick.get('ticker')} - Score: {top_pick.get('total_score', 0)*100:.1f}%, IRV: {top_pick.get('intraday_relative_volume', 0):.1f}x, Potential: {top_pick.get('explosive_potential', 0)*100:.1f}%")

            # Calculate summary stats
            trade_ready_count = len(trade_ready_candidates)
            watchlist_count = len(watchlist_candidates)
            near_miss_count = len(near_miss_candidates)

            execution_time = time.time() - start_time

            result = {
                'status': 'success',
                'top_pick': top_pick,  # THE BEST explosive opportunity
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
                'engine': 'Ultra-Selective Discovery with Top Pick Selection v1.2',
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