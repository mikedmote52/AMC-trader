#!/usr/bin/env python3
"""
Live Discovery System Trace
Shows complete filtering pipeline from universe to explosive candidates
"""
import asyncio
import logging
import sys
import os
from datetime import datetime
from typing import Dict, List, Any, Optional

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add backend paths
backend_path = os.path.join(os.path.dirname(__file__), 'backend', 'src')
sys.path.insert(0, backend_path)

class DiscoveryTracer:
    """
    Traces the complete discovery pipeline step-by-step
    """

    def __init__(self):
        self.trace_log = []

    def log_step(self, step: str, count: int, details: str = ""):
        """Log each filtering step"""
        message = f"STEP {len(self.trace_log) + 1}: {step} - {count} stocks"
        if details:
            message += f" ({details})"

        self.trace_log.append({
            'step': step,
            'count': count,
            'details': details,
            'timestamp': datetime.now().isoformat()
        })

        print(f"\n🔍 {message}")
        logger.info(message)

    async def run_complete_discovery_trace(self):
        """
        Run complete discovery pipeline with full tracing
        """
        print("=" * 80)
        print("🚀 AMC-TRADER DISCOVERY SYSTEM - LIVE TRACE")
        print("=" * 80)

        try:
            # Step 1: Get initial universe
            print("\n📊 PHASE 1: BUILDING STOCK UNIVERSE")
            universe = await self._get_discovery_universe()
            self.log_step("Initial Universe", len(universe), "All explosive-potential candidates")

            if not universe:
                print("❌ CRITICAL: No universe available")
                return

            # Step 2: Get live market data
            print("\n📈 PHASE 2: FETCHING LIVE MARKET DATA")
            market_data = await self._get_live_market_data(universe)
            self.log_step("Market Data Retrieved", len(market_data), f"Live data for {len(market_data)}/{len(universe)} stocks")

            if not market_data:
                print("❌ CRITICAL: No market data available")
                return

            # Step 3: Apply basic filters
            print("\n🔍 PHASE 3: APPLYING BASIC FILTERS")
            basic_filtered = await self._apply_basic_filters(market_data)
            self.log_step("Basic Filters Applied", len(basic_filtered), "Price, volume, and liquidity filters")

            # Step 4: Calculate momentum scores
            print("\n⚡ PHASE 4: CALCULATING MOMENTUM SCORES")
            scored_stocks = await self._calculate_momentum_scores(basic_filtered)
            self.log_step("Momentum Scoring", len(scored_stocks), "Price movement and volume analysis")

            # Step 5: Apply explosive thresholds
            print("\n💥 PHASE 5: APPLYING EXPLOSIVE THRESHOLDS")
            explosive_candidates = await self._apply_explosive_thresholds(scored_stocks)
            self.log_step("Explosive Threshold Filter", len(explosive_candidates), "≥5% move OR ≥2x volume surge")

            # Step 6: Rank and select final candidates
            print("\n🎯 PHASE 6: FINAL RANKING AND SELECTION")
            final_candidates = await self._rank_and_select(explosive_candidates, limit=10)
            self.log_step("Final Selection", len(final_candidates), "Top explosive candidates by score")

            # Display results
            await self._display_results(final_candidates)

            # Show complete trace
            self._display_complete_trace()

        except Exception as e:
            print(f"\n❌ Discovery trace failed: {e}")
            logger.error(f"Discovery trace failed: {e}")

    async def _get_discovery_universe(self) -> List[str]:
        """Get the discovery universe"""
        try:
            # Import the discovery system
            from discovery.polygon_explosive_discovery import PolygonExplosiveDiscovery
            discovery = PolygonExplosiveDiscovery()

            # Get the universe
            universe = await discovery._get_real_universe()

            print(f"📋 Universe Sources:")
            print(f"   • Liquid subset: ~45 stocks")
            print(f"   • Additional candidates: ~35 stocks")
            print(f"   • Total unique: {len(universe)} stocks")
            print(f"   • Sample: {', '.join(universe[:10])}")

            return universe

        except Exception as e:
            print(f"   ❌ Failed to get universe: {e}")
            # Fallback universe
            fallback = [
                'QUBT', 'IONQ', 'RGTI', 'BBAI', 'SOUN', 'LUNR',
                'MARA', 'RIOT', 'CLSK', 'HUT', 'BITF', 'COIN',
                'PLTR', 'SNOW', 'CRWD', 'ZS', 'NET', 'DDOG',
                'RIVN', 'LCID', 'SOFI', 'HOOD', 'RBLX', 'SPCE'
            ]
            print(f"   🔄 Using fallback universe: {len(fallback)} stocks")
            return fallback

    async def _get_live_market_data(self, universe: List[str]) -> List[Dict[str, Any]]:
        """Get live market data for universe"""
        try:
            from services.mcp_polygon_bridge import mcp_polygon_bridge

            print(f"📡 Fetching live data for {len(universe)} stocks...")

            # Get market snapshot
            snapshot_data = await mcp_polygon_bridge.get_market_snapshot(
                tickers=universe[:20],  # Limit for performance
                market_type='stocks'
            )

            if snapshot_data.get('status') == 'OK' and snapshot_data.get('tickers'):
                tickers = snapshot_data['tickers']
                print(f"   ✅ Retrieved data for {len(tickers)} stocks")

                # Show sample data
                if tickers:
                    sample = tickers[0]
                    symbol = sample.get('ticker', 'UNKNOWN')
                    day_data = sample.get('day', {})
                    price = day_data.get('c', 0)
                    volume = day_data.get('v', 0)
                    change_pct = sample.get('todaysChangePerc', 0)

                    print(f"   📊 Sample: {symbol} @ ${price:.2f} ({change_pct:+.2f}%, {volume:,} vol)")

                return tickers
            else:
                print(f"   ❌ No market data: {snapshot_data.get('error', 'Unknown error')}")
                return []

        except Exception as e:
            print(f"   ❌ Market data failed: {e}")
            return []

    async def _apply_basic_filters(self, market_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply basic filters (price, volume, liquidity)"""
        filtered_stocks = []

        print(f"🔍 Applying basic filters:")
        print(f"   • Price range: $0.50 - $500.00")
        print(f"   • Minimum dollar volume: $1M")
        print(f"   • Valid market data required")

        rejected_reasons = {
            'low_price': 0,
            'high_price': 0,
            'low_volume': 0,
            'missing_data': 0
        }

        for ticker_data in market_data:
            symbol = ticker_data.get('ticker', 'UNKNOWN')
            day_data = ticker_data.get('day', {})

            # Extract data
            price = day_data.get('c', 0)
            volume = day_data.get('v', 0)

            # Apply filters
            if price < 0.50:
                rejected_reasons['low_price'] += 1
                continue
            elif price > 500.00:
                rejected_reasons['high_price'] += 1
                continue
            elif price * volume < 1_000_000:  # $1M minimum dollar volume
                rejected_reasons['low_volume'] += 1
                continue
            elif not price or not volume:
                rejected_reasons['missing_data'] += 1
                continue

            filtered_stocks.append(ticker_data)

        # Show rejection breakdown
        total_rejected = sum(rejected_reasons.values())
        print(f"   📉 Rejected: {total_rejected} stocks")
        for reason, count in rejected_reasons.items():
            if count > 0:
                print(f"     - {reason.replace('_', ' ').title()}: {count}")

        print(f"   ✅ Passed basic filters: {len(filtered_stocks)} stocks")

        return filtered_stocks

    async def _calculate_momentum_scores(self, filtered_stocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Calculate momentum scores for each stock"""
        scored_stocks = []

        print(f"⚡ Calculating momentum scores:")
        print(f"   • Price movement weight: 40%")
        print(f"   • Volume surge weight: 35%")
        print(f"   • Technical position: 25%")

        score_distribution = {'high': 0, 'medium': 0, 'low': 0}

        for ticker_data in filtered_stocks:
            symbol = ticker_data.get('ticker', 'UNKNOWN')
            day_data = ticker_data.get('day', {})
            prev_data = ticker_data.get('prevDay', {})

            # Get values
            current_price = day_data.get('c', 0)
            current_volume = day_data.get('v', 0)
            prev_close = prev_data.get('c', 0)
            prev_volume = prev_data.get('v', 0)

            # Calculate change metrics
            price_change_pct = 0
            volume_ratio = 1.0

            if prev_close > 0:
                price_change_pct = ((current_price - prev_close) / prev_close) * 100

            if prev_volume > 0:
                volume_ratio = current_volume / prev_volume

            # Calculate component scores
            momentum_score = min(100, abs(price_change_pct) * 5)  # Price movement
            volume_score = min(100, (volume_ratio - 1) * 50)      # Volume surge
            technical_score = 50  # Baseline technical score

            # Composite score
            composite_score = (
                momentum_score * 0.40 +
                volume_score * 0.35 +
                technical_score * 0.25
            )

            # Add to ticker data
            enhanced_ticker = ticker_data.copy()
            enhanced_ticker.update({
                'price_change_pct': price_change_pct,
                'volume_ratio': volume_ratio,
                'momentum_score': momentum_score,
                'volume_score': volume_score,
                'technical_score': technical_score,
                'composite_score': composite_score
            })

            scored_stocks.append(enhanced_ticker)

            # Track distribution
            if composite_score >= 70:
                score_distribution['high'] += 1
            elif composite_score >= 40:
                score_distribution['medium'] += 1
            else:
                score_distribution['low'] += 1

        print(f"   📊 Score distribution:")
        print(f"     - High (≥70): {score_distribution['high']} stocks")
        print(f"     - Medium (40-69): {score_distribution['medium']} stocks")
        print(f"     - Low (<40): {score_distribution['low']} stocks")

        return scored_stocks

    async def _apply_explosive_thresholds(self, scored_stocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply explosive movement thresholds"""
        explosive_candidates = []

        print(f"💥 Applying explosive thresholds:")
        print(f"   • Minimum price move: ≥5.0%")
        print(f"   • Strong price move: ≥10.0%")
        print(f"   • Minimum volume surge: ≥2.0x")
        print(f"   • Strong volume surge: ≥5.0x")

        movement_categories = {
            'explosive_price': 0,  # ≥20%
            'strong_price': 0,     # ≥10%
            'moderate_price': 0,   # ≥5%
            'explosive_volume': 0, # ≥5x
            'strong_volume': 0,    # ≥2x
            'no_movement': 0
        }

        for ticker_data in scored_stocks:
            symbol = ticker_data.get('ticker', 'UNKNOWN')
            price_change_pct = abs(ticker_data.get('price_change_pct', 0))
            volume_ratio = ticker_data.get('volume_ratio', 1.0)

            # Check explosive criteria
            explosive_price = price_change_pct >= 20.0
            strong_price = price_change_pct >= 10.0
            moderate_price = price_change_pct >= 5.0

            explosive_volume = volume_ratio >= 5.0
            strong_volume = volume_ratio >= 2.0

            # Categorize movement
            if explosive_price:
                movement_categories['explosive_price'] += 1
            elif strong_price:
                movement_categories['strong_price'] += 1
            elif moderate_price:
                movement_categories['moderate_price'] += 1
            else:
                movement_categories['no_movement'] += 1

            if explosive_volume:
                movement_categories['explosive_volume'] += 1
            elif strong_volume:
                movement_categories['strong_volume'] += 1

            # Include if meets explosive criteria
            if moderate_price or strong_volume:
                # Determine action tag
                if explosive_price or (strong_price and strong_volume):
                    action_tag = 'explosive'
                elif strong_price or explosive_volume:
                    action_tag = 'momentum'
                else:
                    action_tag = 'watch'

                ticker_data['action_tag'] = action_tag
                explosive_candidates.append(ticker_data)

        print(f"   📈 Movement breakdown:")
        print(f"     - Explosive price (≥20%): {movement_categories['explosive_price']}")
        print(f"     - Strong price (≥10%): {movement_categories['strong_price']}")
        print(f"     - Moderate price (≥5%): {movement_categories['moderate_price']}")
        print(f"     - Explosive volume (≥5x): {movement_categories['explosive_volume']}")
        print(f"     - Strong volume (≥2x): {movement_categories['strong_volume']}")
        print(f"     - No significant movement: {movement_categories['no_movement']}")

        return explosive_candidates

    async def _rank_and_select(self, explosive_candidates: List[Dict[str, Any]], limit: int = 10) -> List[Dict[str, Any]]:
        """Rank candidates and select top performers"""
        print(f"🎯 Final ranking and selection:")
        print(f"   • Ranking by composite score")
        print(f"   • Selecting top {limit} candidates")

        # Sort by composite score
        ranked_candidates = sorted(
            explosive_candidates,
            key=lambda x: x.get('composite_score', 0),
            reverse=True
        )

        # Select top candidates
        final_candidates = ranked_candidates[:limit]

        # Show action tag distribution
        action_distribution = {}
        for candidate in final_candidates:
            tag = candidate.get('action_tag', 'unknown')
            action_distribution[tag] = action_distribution.get(tag, 0) + 1

        print(f"   📊 Final distribution:")
        for tag, count in action_distribution.items():
            print(f"     - {tag.title()}: {count}")

        return final_candidates

    async def _display_results(self, final_candidates: List[Dict[str, Any]]):
        """Display final explosive candidates"""
        print("\n" + "=" * 80)
        print("🚀 FINAL EXPLOSIVE CANDIDATES")
        print("=" * 80)

        if not final_candidates:
            print("❌ No explosive candidates found")
            return

        for i, candidate in enumerate(final_candidates, 1):
            symbol = candidate.get('ticker', 'UNKNOWN')
            day_data = candidate.get('day', {})

            price = day_data.get('c', 0)
            price_change_pct = candidate.get('price_change_pct', 0)
            volume = day_data.get('v', 0)
            volume_ratio = candidate.get('volume_ratio', 1.0)
            composite_score = candidate.get('composite_score', 0)
            action_tag = candidate.get('action_tag', 'unknown')

            print(f"\n#{i} {symbol} - {action_tag.upper()}")
            print(f"   Price: ${price:.2f} ({price_change_pct:+.2f}%)")
            print(f"   Volume: {volume:,} ({volume_ratio:.1f}x)")
            print(f"   Score: {composite_score:.1f}/100")

            # Show component scores
            momentum = candidate.get('momentum_score', 0)
            vol_score = candidate.get('volume_score', 0)
            technical = candidate.get('technical_score', 0)
            print(f"   Components: Momentum={momentum:.1f}, Volume={vol_score:.1f}, Technical={technical:.1f}")

    def _display_complete_trace(self):
        """Display complete filtering trace"""
        print("\n" + "=" * 80)
        print("📊 COMPLETE DISCOVERY PIPELINE TRACE")
        print("=" * 80)

        for i, step in enumerate(self.trace_log, 1):
            print(f"\nStep {i}: {step['step']}")
            print(f"   Count: {step['count']} stocks")
            if step['details']:
                print(f"   Details: {step['details']}")

        # Calculate efficiency
        if len(self.trace_log) >= 2:
            initial = self.trace_log[0]['count']
            final = self.trace_log[-1]['count']
            efficiency = (final / initial * 100) if initial > 0 else 0

            print(f"\n📈 Pipeline Efficiency:")
            print(f"   • Started with: {initial} stocks")
            print(f"   • Ended with: {final} stocks")
            print(f"   • Selectivity: {efficiency:.2f}%")

async def main():
    """Run the complete discovery trace"""
    tracer = DiscoveryTracer()
    await tracer.run_complete_discovery_trace()

if __name__ == "__main__":
    asyncio.run(main())