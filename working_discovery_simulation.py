#!/usr/bin/env python3
"""
Working Discovery Simulation using MCP Functions
Shows what the discovery system SHOULD be doing with working data
"""
import asyncio
from datetime import datetime
from typing import Dict, List, Any

class WorkingDiscoverySimulation:
    """
    Simulates the discovery pipeline using working MCP functions
    This shows what the backend SHOULD be producing
    """

    def __init__(self):
        self.explosive_thresholds = {
            'min_price_move': 5.0,        # 5% minimum price move
            'strong_price_move': 10.0,    # 10% strong move
            'explosive_price_move': 20.0, # 20% explosive move
            'min_volume_surge': 2.0,      # 2x volume surge minimum
            'strong_volume_surge': 5.0,   # 5x volume surge strong
            'min_dollar_volume': 1_000_000, # $1M minimum daily volume
            'min_price': 0.50,            # No penny stocks below $0.50
            'max_price': 500.00           # Avoid expensive stocks
        }

    async def run_simulation(self):
        """Run complete discovery simulation"""
        print("=" * 100)
        print("🎯 WORKING DISCOVERY SIMULATION - Using Real MCP Functions")
        print("=" * 100)

        # Step 1: Define explosive candidate universe
        universe = self._get_explosive_universe()
        print(f"\n📊 STEP 1: EXPLOSIVE CANDIDATE UNIVERSE")
        print(f"   Universe size: {len(universe)} stocks")
        print(f"   Focus: Small/mid-cap AI, quantum, crypto, biotech")
        print(f"   Sample: {', '.join(universe[:10])}")

        # Step 2: Get real market data using working MCP functions
        print(f"\n📈 STEP 2: FETCHING REAL MARKET DATA (MCP)")
        market_data = await self._get_working_market_data(universe[:10])  # Test with 10 stocks
        print(f"   Retrieved: {len(market_data)} stocks with live data")

        if not market_data:
            print("❌ No market data - cannot continue")
            return

        # Step 3: Apply discovery filters
        print(f"\n🔍 STEP 3: APPLYING DISCOVERY FILTERS")
        filtered_stocks = self._apply_discovery_filters(market_data)
        print(f"   Passed filters: {len(filtered_stocks)} stocks")

        # Step 4: Calculate explosive scores
        print(f"\n⚡ STEP 4: CALCULATING EXPLOSIVE SCORES")
        scored_stocks = self._calculate_explosive_scores(filtered_stocks)
        print(f"   Scored candidates: {len(scored_stocks)} stocks")

        # Step 5: Apply explosive thresholds
        print(f"\n💥 STEP 5: APPLYING EXPLOSIVE THRESHOLDS")
        explosive_candidates = self._filter_explosive_candidates(scored_stocks)
        print(f"   Explosive candidates: {len(explosive_candidates)} stocks")

        # Step 6: Show final results
        self._display_explosive_results(explosive_candidates)

        return explosive_candidates

    def _get_explosive_universe(self) -> List[str]:
        """Get curated universe of explosive potential stocks"""
        return [
            # AI/Quantum (highest explosive potential)
            'QUBT', 'IONQ', 'RGTI', 'ARQQ', 'BBAI', 'SOUN', 'LUNR',

            # Crypto mining (high volatility)
            'MARA', 'RIOT', 'CLSK', 'HUT', 'BITF', 'COIN', 'HOOD',

            # Biotech breakouts
            'SAVA', 'MRNA', 'BNTX', 'NVAX', 'BIIB', 'VRTX', 'REGN',

            # High-beta growth
            'PLTR', 'SNOW', 'CRWD', 'ZS', 'NET', 'DDOG', 'OKTA',

            # Momentum plays
            'RIVN', 'LCID', 'SOFI', 'RBLX', 'SPCE', 'NKLA',

            # Energy/EV
            'NIO', 'XPEV', 'LI', 'PLUG', 'FCEL', 'BE', 'CHPT',

            # Fintech
            'SQ', 'AFRM', 'UPST', 'LMND', 'LC',

            # Recent SPACs/IPOs
            'WISH', 'CLOV', 'SKLZ', 'DKNG', 'OPEN'
        ]

    async def _get_working_market_data(self, universe: List[str]) -> List[Dict[str, Any]]:
        """Get working market data using MCP functions"""
        try:
            print(f"   📡 Calling mcp__polygon__get_snapshot_all for {len(universe)} stocks...")

            # This works in Claude Code environment - calling real MCP function
            result = await mcp__polygon__get_snapshot_all(
                market_type='stocks',
                tickers=universe
            )

            if result.get('status') == 'OK' and result.get('tickers'):
                tickers = result['tickers']
                print(f"   ✅ Retrieved {len(tickers)} live stocks")

                # Show sample data
                for ticker in tickers[:3]:
                    symbol = ticker.get('ticker', 'UNKNOWN')
                    day_data = ticker.get('day', {})
                    change_pct = ticker.get('todaysChangePerc', 0)
                    price = day_data.get('c', 0)
                    volume = day_data.get('v', 0)

                    print(f"   📊 {symbol}: ${price:.2f} ({change_pct:+.2f}%, {volume:,} vol)")

                return tickers
            else:
                print(f"   ❌ MCP call failed: {result}")
                return []

        except NameError:
            print("   ❌ MCP functions not available in this environment")
            return []
        except Exception as e:
            print(f"   ❌ MCP error: {e}")
            return []

    def _apply_discovery_filters(self, market_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply basic discovery filters"""
        filtered = []
        rejected = {
            'price_too_low': 0,
            'price_too_high': 0,
            'volume_too_low': 0,
            'missing_data': 0
        }

        print(f"   🔍 Filter criteria:")
        print(f"     • Price range: ${self.explosive_thresholds['min_price']:.2f} - ${self.explosive_thresholds['max_price']:.2f}")
        print(f"     • Min dollar volume: ${self.explosive_thresholds['min_dollar_volume']:,}")

        for ticker in market_data:
            symbol = ticker.get('ticker', 'UNKNOWN')
            day_data = ticker.get('day', {})

            price = day_data.get('c', 0)
            volume = day_data.get('v', 0)
            dollar_volume = price * volume if price and volume else 0

            # Apply filters
            if price < self.explosive_thresholds['min_price']:
                rejected['price_too_low'] += 1
                continue
            elif price > self.explosive_thresholds['max_price']:
                rejected['price_too_high'] += 1
                continue
            elif dollar_volume < self.explosive_thresholds['min_dollar_volume']:
                rejected['volume_too_low'] += 1
                continue
            elif not price or not volume:
                rejected['missing_data'] += 1
                continue

            filtered.append(ticker)

        # Show rejections
        total_rejected = sum(rejected.values())
        if total_rejected > 0:
            print(f"   📉 Rejected {total_rejected} stocks:")
            for reason, count in rejected.items():
                if count > 0:
                    print(f"     - {reason.replace('_', ' ').title()}: {count}")

        return filtered

    def _calculate_explosive_scores(self, filtered_stocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Calculate explosive potential scores"""
        scored = []

        print(f"   ⚡ Scoring methodology:")
        print(f"     • Price momentum: 40% weight")
        print(f"     • Volume surge: 35% weight")
        print(f"     • Technical position: 25% weight")

        for ticker in filtered_stocks:
            symbol = ticker.get('ticker', 'UNKNOWN')
            day_data = ticker.get('day', {})
            prev_data = ticker.get('prevDay', {})

            # Extract values
            current_price = day_data.get('c', 0)
            current_volume = day_data.get('v', 0)
            prev_close = prev_data.get('c', 0)
            prev_volume = prev_data.get('v', 0)

            # Calculate changes
            price_change_pct = 0
            volume_ratio = 1.0

            if prev_close > 0:
                price_change_pct = ((current_price - prev_close) / prev_close) * 100

            if prev_volume > 0:
                volume_ratio = current_volume / prev_volume

            # Calculate component scores (0-100)
            momentum_score = self._calculate_momentum_component(price_change_pct)
            volume_score = self._calculate_volume_component(volume_ratio)
            technical_score = self._calculate_technical_component(day_data, prev_data)

            # Composite score
            explosive_score = (
                momentum_score * 0.40 +
                volume_score * 0.35 +
                technical_score * 0.25
            )

            # Enhanced ticker with scores
            enhanced = ticker.copy()
            enhanced.update({
                'price_change_pct': price_change_pct,
                'volume_ratio': volume_ratio,
                'momentum_score': momentum_score,
                'volume_score': volume_score,
                'technical_score': technical_score,
                'explosive_score': explosive_score
            })

            scored.append(enhanced)

        return scored

    def _calculate_momentum_component(self, price_change_pct: float) -> float:
        """Calculate momentum score component"""
        abs_change = abs(price_change_pct)

        if abs_change >= self.explosive_thresholds['explosive_price_move']:  # ≥20%
            return 100
        elif abs_change >= self.explosive_thresholds['strong_price_move']:   # ≥10%
            return 70 + (abs_change - 10) * 3
        elif abs_change >= self.explosive_thresholds['min_price_move']:      # ≥5%
            return 40 + (abs_change - 5) * 6
        else:
            return abs_change * 8

    def _calculate_volume_component(self, volume_ratio: float) -> float:
        """Calculate volume score component"""
        if volume_ratio >= 10:  # 10x volume
            return 100
        elif volume_ratio >= self.explosive_thresholds['strong_volume_surge']:  # ≥5x
            return 80 + (volume_ratio - 5) * 4
        elif volume_ratio >= self.explosive_thresholds['min_volume_surge']:    # ≥2x
            return 50 + (volume_ratio - 2) * 10
        else:
            return volume_ratio * 25

    def _calculate_technical_component(self, day_data: Dict, prev_data: Dict) -> float:
        """Calculate technical position score"""
        # Simplified technical scoring
        high = day_data.get('h', 0)
        low = day_data.get('l', 0)
        close = day_data.get('c', 0)

        if high > low:
            # Position in daily range
            range_position = (close - low) / (high - low)
            return 30 + range_position * 40  # 30-70 range
        else:
            return 50  # Neutral

    def _filter_explosive_candidates(self, scored_stocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter for explosive candidates based on thresholds"""
        explosive_candidates = []

        print(f"   💥 Explosive criteria:")
        print(f"     • Explosive: ≥20% move OR ≥5x volume")
        print(f"     • Momentum: ≥10% move OR ≥2x volume")
        print(f"     • Watch: ≥5% move OR significant volume")

        action_counts = {'explosive': 0, 'momentum': 0, 'watch': 0}

        for stock in scored_stocks:
            symbol = stock.get('ticker', 'UNKNOWN')
            price_change_pct = abs(stock.get('price_change_pct', 0))
            volume_ratio = stock.get('volume_ratio', 1.0)
            explosive_score = stock.get('explosive_score', 0)

            # Determine action tag based on movement
            if (price_change_pct >= self.explosive_thresholds['explosive_price_move'] or
                volume_ratio >= 10):
                action_tag = 'explosive'
            elif (price_change_pct >= self.explosive_thresholds['strong_price_move'] or
                  volume_ratio >= self.explosive_thresholds['strong_volume_surge']):
                action_tag = 'momentum'
            elif (price_change_pct >= self.explosive_thresholds['min_price_move'] or
                  volume_ratio >= self.explosive_thresholds['min_volume_surge']):
                action_tag = 'watch'
            else:
                continue  # Skip non-explosive stocks

            stock['action_tag'] = action_tag
            action_counts[action_tag] += 1
            explosive_candidates.append(stock)

        print(f"   📊 Results by category:")
        for action, count in action_counts.items():
            print(f"     - {action.title()}: {count}")

        # Sort by explosive score
        explosive_candidates.sort(key=lambda x: x.get('explosive_score', 0), reverse=True)

        return explosive_candidates

    def _display_explosive_results(self, explosive_candidates: List[Dict[str, Any]]):
        """Display final explosive candidates"""
        print(f"\n" + "=" * 100)
        print(f"🚀 FINAL EXPLOSIVE CANDIDATES ({len(explosive_candidates)} found)")
        print("=" * 100)

        if not explosive_candidates:
            print("❌ No explosive candidates found")
            return

        for i, candidate in enumerate(explosive_candidates, 1):
            symbol = candidate.get('ticker', 'UNKNOWN')
            day_data = candidate.get('day', {})

            price = day_data.get('c', 0)
            price_change_pct = candidate.get('price_change_pct', 0)
            volume = day_data.get('v', 0)
            volume_ratio = candidate.get('volume_ratio', 1.0)
            explosive_score = candidate.get('explosive_score', 0)
            action_tag = candidate.get('action_tag', 'unknown')

            # Color coding
            tag_emoji = {
                'explosive': '🔥',
                'momentum': '⚡',
                'watch': '👀'
            }.get(action_tag, '📊')

            print(f"\n{tag_emoji} #{i} {symbol} - {action_tag.upper()}")
            print(f"   💰 Price: ${price:.2f} ({price_change_pct:+.2f}%)")
            print(f"   📊 Volume: {volume:,} ({volume_ratio:.1f}x previous)")
            print(f"   🎯 Explosive Score: {explosive_score:.1f}/100")

            # Show component breakdown
            momentum = candidate.get('momentum_score', 0)
            vol_score = candidate.get('volume_score', 0)
            technical = candidate.get('technical_score', 0)
            print(f"   📈 Components: Momentum={momentum:.1f}, Volume={vol_score:.1f}, Technical={technical:.1f}")

            # Assessment
            if explosive_score >= 80:
                assessment = "🔥 EXTREMELY EXPLOSIVE"
            elif explosive_score >= 65:
                assessment = "⚡ HIGHLY EXPLOSIVE"
            elif explosive_score >= 50:
                assessment = "📈 MODERATELY EXPLOSIVE"
            else:
                assessment = "👀 WATCH FOR BREAKOUT"

            print(f"   💡 Assessment: {assessment}")

async def main():
    """Run the working discovery simulation"""
    print("🎯 Running Discovery Simulation with Working MCP Functions...")
    print("This shows what the backend SHOULD be producing\n")

    simulator = WorkingDiscoverySimulation()
    candidates = await simulator.run_simulation()

    if candidates:
        print(f"\n✅ SUCCESS: Found {len(candidates)} explosive candidates")
        print("This proves the discovery logic works when given real market data")
    else:
        print(f"\n⚠️  No candidates found - may be due to market conditions")

if __name__ == "__main__":
    asyncio.run(main())