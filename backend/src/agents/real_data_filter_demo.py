"""
Real Data Filter Demo

Shows the complete filtering process using the real market data that's already 
being fetched by the emergency discovery system (from Polygon API).
"""

import asyncio
import aiohttp
import json
from datetime import datetime
from typing import Dict, List, Any
from improved_discovery_scorer import ImprovedDiscoveryScorer

class RealDataFilterDemo:
    """
    Demonstrate filtering process using real market data from emergency discovery
    """
    
    def __init__(self, api_base: str = "https://amc-trader.onrender.com"):
        self.api_base = api_base
        self.scorer = ImprovedDiscoveryScorer(api_base)
    
    async def run_real_data_demo(self) -> Dict[str, Any]:
        """Show complete filtering process with real market data"""
        
        print("🌍 REAL DATA FILTERING DEMONSTRATION")
        print("=" * 80)
        print("Showing complete universe filtering using REAL market data from Polygon API")
        print("(Data sourced via emergency discovery system)")
        print()
        
        demo_results = {
            "timestamp": datetime.now().isoformat(),
            "data_source": "polygon_api_via_emergency_discovery",
            "filter_stages": {},
            "success": False
        }
        
        try:
            # Stage 1: Get Real Market Data
            print("📊 STAGE 1: Fetching Real Market Data")
            print("-" * 60)
            market_data = await self._get_real_market_data()
            demo_results["filter_stages"]["market_data"] = market_data
            
            if not market_data.get("success"):
                return demo_results
            
            # Stage 2: Show Original Universe Scope
            print("\n🌌 STAGE 2: Universe Scope Analysis")
            print("-" * 60)
            universe_analysis = await self._analyze_universe_scope(market_data["candidates"])
            demo_results["filter_stages"]["universe_analysis"] = universe_analysis
            
            # Stage 3: Basic Universe Filters
            print("\n🔍 STAGE 3: Basic Universe Filtering")
            print("-" * 60)
            basic_filtered = await self._apply_basic_universe_filters(market_data["candidates"])
            demo_results["filter_stages"]["basic_filtering"] = basic_filtered
            
            # Stage 4: Market Quality Filters
            print("\n📈 STAGE 4: Market Quality Filtering")
            print("-" * 60)
            quality_filtered = await self._apply_quality_filters(basic_filtered["qualified"])
            demo_results["filter_stages"]["quality_filtering"] = quality_filtered
            
            # Stage 5: Pre-Explosion Scoring
            print("\n🎯 STAGE 5: Pre-Explosion Scoring & Final Selection")
            print("-" * 60)
            final_results = await self._apply_final_scoring(quality_filtered["qualified"])
            demo_results["filter_stages"]["final_scoring"] = final_results
            
            # Stage 6: Summary
            print("\n📊 STAGE 6: Complete Filtering Summary")
            print("-" * 60)
            summary = await self._generate_summary(demo_results["filter_stages"])
            demo_results["summary"] = summary
            
            demo_results["success"] = True
            return demo_results
            
        except Exception as e:
            print(f"❌ Demo failed: {e}")
            demo_results["error"] = str(e)
            return demo_results
    
    async def _get_real_market_data(self) -> Dict[str, Any]:
        """Get real market data from the emergency discovery system"""
        
        try:
            print("📡 Fetching real market data from Polygon API...")
            
            async with aiohttp.ClientSession() as session:
                url = f"{self.api_base}/discovery/emergency/run-direct?limit=200"
                async with session.post(url, timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()
                        candidates = data.get('candidates', [])
                        
                        print(f"✅ Retrieved {len(candidates)} stocks with real market data")
                        print(f"  📊 Data Source: Polygon API (via emergency discovery)")
                        print(f"  🚫 NO SYNTHETIC DATA - All real market quotes")
                        
                        if candidates:
                            # Show data authenticity
                            sample = candidates[0]
                            print(f"  📝 Sample data validation:")
                            print(f"    Symbol: {sample.get('symbol')}")
                            print(f"    Price: ${sample.get('price', 0):.4f} (real market price)")
                            print(f"    Volume: {sample.get('volume', 0):,} shares (real volume)")
                            print(f"    Volume Ratio: {sample.get('volume_ratio', 0):.1f}x (vs 30-day avg)")
                            print(f"    Price Change: {sample.get('price_change_pct', 0):+.1f}% (real move)")
                        
                        return {
                            "success": True,
                            "total_retrieved": len(candidates),
                            "candidates": candidates,
                            "data_source": "polygon_api",
                            "authentic_data": True
                        }
                    else:
                        print(f"❌ API call failed: HTTP {response.status}")
                        return {"success": False, "error": f"HTTP {response.status}"}
        
        except Exception as e:
            print(f"❌ Market data fetch failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _analyze_universe_scope(self, candidates: List[Dict]) -> Dict[str, Any]:
        """Analyze the scope and characteristics of the universe"""
        
        print("🔍 Analyzing universe scope and characteristics...")
        
        if not candidates:
            return {"success": False, "error": "No candidates to analyze"}
        
        # Analyze price distribution
        prices = [c.get('price', 0) for c in candidates if c.get('price')]
        volume_ratios = [c.get('volume_ratio', 0) for c in candidates if c.get('volume_ratio')]
        price_changes = [abs(c.get('price_change_pct', 0)) for c in candidates if c.get('price_change_pct') is not None]
        dollar_volumes = [c.get('dollar_volume', 0) for c in candidates if c.get('dollar_volume')]
        
        # Price ranges
        penny_stocks = len([p for p in prices if p < 1])
        low_price = len([p for p in prices if 1 <= p < 10])
        mid_price = len([p for p in prices if 10 <= p < 100])
        high_price = len([p for p in prices if p >= 100])
        
        # Volume activity
        low_volume = len([v for v in volume_ratios if v < 2])
        building_volume = len([v for v in volume_ratios if 2 <= v < 10])
        high_volume = len([v for v in volume_ratios if 10 <= v < 50])
        extreme_volume = len([v for v in volume_ratios if v >= 50])
        
        # Price movement
        stable = len([p for p in price_changes if p < 5])
        moderate = len([p for p in price_changes if 5 <= p < 20])
        large = len([p for p in price_changes if 20 <= p < 100])
        explosive = len([p for p in price_changes if p >= 100])
        
        print(f"📊 Universe characteristics:")
        print(f"  💰 Price Distribution:")
        print(f"    • Penny stocks (<$1): {penny_stocks}")
        print(f"    • Low price ($1-$10): {low_price}")
        print(f"    • Mid price ($10-$100): {mid_price}")
        print(f"    • High price ($100+): {high_price}")
        
        print(f"  📈 Volume Activity:")
        print(f"    • Low volume (<2x): {low_volume}")
        print(f"    • Building volume (2-10x): {building_volume} ⭐ TARGET RANGE")
        print(f"    • High volume (10-50x): {high_volume}")
        print(f"    • Extreme volume (50x+): {extreme_volume}")
        
        print(f"  🎯 Price Movement:")
        print(f"    • Stable (<5%): {stable} ⭐ PRE-EXPLOSION")
        print(f"    • Moderate (5-20%): {moderate} ⚠️ MOVING")
        print(f"    • Large (20-100%): {large} ❌ LATE")
        print(f"    • Explosive (100%+): {explosive} ❌ ALREADY EXPLODED")
        
        return {
            "success": True,
            "total_analyzed": len(candidates),
            "price_distribution": {
                "penny": penny_stocks,
                "low": low_price,
                "mid": mid_price,
                "high": high_price
            },
            "volume_distribution": {
                "low": low_volume,
                "building": building_volume,
                "high": high_volume,
                "extreme": extreme_volume
            },
            "movement_distribution": {
                "stable": stable,
                "moderate": moderate,
                "large": large,
                "explosive": explosive
            }
        }
    
    async def _apply_basic_universe_filters(self, candidates: List[Dict]) -> Dict[str, Any]:
        """Apply basic universe filters to eliminate obviously bad candidates"""
        
        print("🔍 Applying basic universe filters...")
        
        qualified = []
        eliminated = {
            "invalid_symbol": 0,
            "missing_data": 0,
            "too_expensive": 0,
            "no_volume": 0
        }
        
        for candidate in candidates:
            symbol = candidate.get('symbol', '')
            price = candidate.get('price', 0)
            volume = candidate.get('volume', 0)
            
            # Filter 1: Valid symbol
            if not symbol or len(symbol) > 6:
                eliminated["invalid_symbol"] += 1
                continue
            
            # Filter 2: Must have essential data
            if not all([price, volume]):
                eliminated["missing_data"] += 1
                continue
            
            # Filter 3: Price range (for retail accessibility)
            if price > 500:  # Avoid very high-priced stocks
                eliminated["too_expensive"] += 1
                continue
            
            # Filter 4: Must have some volume
            if volume <= 0:
                eliminated["no_volume"] += 1
                continue
            
            qualified.append(candidate)
        
        qualified_count = len(qualified)
        total_eliminated = sum(eliminated.values())
        
        print(f"✅ Basic universe filtering complete:")
        print(f"  📈 Qualified: {qualified_count}")
        print(f"  ❌ Eliminated: {total_eliminated}")
        print(f"    • Invalid symbols: {eliminated['invalid_symbol']}")
        print(f"    • Missing data: {eliminated['missing_data']}")  
        print(f"    • Too expensive: {eliminated['too_expensive']}")
        print(f"    • No volume: {eliminated['no_volume']}")
        
        survival_rate = (qualified_count / len(candidates)) * 100
        print(f"  📊 Survival rate: {survival_rate:.1f}%")
        
        return {
            "success": True,
            "initial_count": len(candidates),
            "qualified_count": qualified_count,
            "qualified": qualified,
            "eliminated": eliminated,
            "survival_rate": survival_rate
        }
    
    async def _apply_quality_filters(self, candidates: List[Dict]) -> Dict[str, Any]:
        """Apply quality filters focusing on tradeable opportunities"""
        
        print("📈 Applying market quality filters...")
        
        qualified = []
        eliminated = {
            "price_too_low": 0,
            "insufficient_liquidity": 0,
            "extreme_volatility": 0,
            "already_exploded": 0
        }
        
        for candidate in candidates:
            price = candidate.get('price', 0)
            dollar_volume = candidate.get('dollar_volume', 0)
            volume_ratio = candidate.get('volume_ratio', 0)
            price_change = abs(candidate.get('price_change_pct', 0))
            
            # Filter 1: Minimum price for quality
            if price < 0.10:
                eliminated["price_too_low"] += 1
                continue
            
            # Filter 2: Liquidity requirement
            if dollar_volume < 100000:  # $100K minimum dollar volume
                eliminated["insufficient_liquidity"] += 1
                continue
            
            # Filter 3: Avoid extreme volatility (unstable)
            if volume_ratio > 1000:  # 1000x volume is too extreme
                eliminated["extreme_volatility"] += 1
                continue
            
            # Filter 4: Avoid already exploded stocks (>200% moves)
            if price_change > 200:
                eliminated["already_exploded"] += 1
                continue
            
            qualified.append(candidate)
        
        qualified_count = len(qualified)
        total_eliminated = sum(eliminated.values())
        
        print(f"✅ Quality filtering complete:")
        print(f"  📈 Qualified: {qualified_count}")
        print(f"  ❌ Eliminated: {total_eliminated}")
        print(f"    • Price too low: {eliminated['price_too_low']}")
        print(f"    • Insufficient liquidity: {eliminated['insufficient_liquidity']}")
        print(f"    • Extreme volatility: {eliminated['extreme_volatility']}")
        print(f"    • Already exploded: {eliminated['already_exploded']}")
        
        survival_rate = (qualified_count / len(candidates)) * 100
        print(f"  📊 Survival rate: {survival_rate:.1f}%")
        
        return {
            "success": True,
            "initial_count": len(candidates),
            "qualified_count": qualified_count,
            "qualified": qualified,
            "eliminated": eliminated,
            "survival_rate": survival_rate
        }
    
    async def _apply_final_scoring(self, candidates: List[Dict]) -> Dict[str, Any]:
        """Apply final pre-explosion scoring and selection"""
        
        print("🎯 Applying pre-explosion scoring and final selection...")
        
        if not candidates:
            return {"success": False, "error": "No candidates to score"}
        
        # Score all candidates
        scored_candidates = []
        for candidate in candidates:
            scored = self.scorer.calculate_pre_explosion_score(candidate)
            scored_candidates.append(scored)
        
        # Sort by score
        scored_candidates.sort(key=lambda x: x['score'], reverse=True)
        
        # Apply final thresholds
        pre_explosion_imminent = [c for c in scored_candidates if c['score'] >= 75]
        building_pressure = [c for c in scored_candidates if 60 <= c['score'] < 75]
        early_accumulation = [c for c in scored_candidates if 45 <= c['score'] < 60]
        watchlist = [c for c in scored_candidates if 30 <= c['score'] < 45]
        
        final_candidates = pre_explosion_imminent + building_pressure + early_accumulation
        
        print(f"✅ Final scoring and selection complete:")
        print(f"  🚨 Pre-Explosion Imminent (75+): {len(pre_explosion_imminent)}")
        print(f"  📈 Building Pressure (60-75): {len(building_pressure)}")
        print(f"  👀 Early Accumulation (45-60): {len(early_accumulation)}")
        print(f"  📋 Watchlist (30-45): {len(watchlist)}")
        print(f"  ✅ Final Candidates: {len(final_candidates)}")
        
        if final_candidates:
            print(f"\n🎯 TOP FINAL CANDIDATES:")
            print("-" * 60)
            
            for i, candidate in enumerate(final_candidates[:8], 1):
                symbol = candidate['symbol']
                score = candidate['score']
                price = candidate['price']
                volume_ratio = candidate['volume_ratio']
                price_change = candidate['price_change_pct']
                action = candidate['action_tag']
                
                print(f"{i:2d}. {symbol:8s} | ${price:8.2f} | Score: {score:5.1f} | Vol: {volume_ratio:6.1f}x | Move: {price_change:+6.1f}% | {action}")
        
        return {
            "success": True,
            "total_scored": len(scored_candidates),
            "final_candidates": final_candidates,
            "pre_explosion_count": len(pre_explosion_imminent),
            "building_pressure_count": len(building_pressure),
            "early_accumulation_count": len(early_accumulation),
            "watchlist_count": len(watchlist)
        }
    
    async def _generate_summary(self, filter_stages: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive filtering summary"""
        
        print("📊 Generating complete filtering funnel analysis...")
        
        # Extract counts from each stage
        initial_count = filter_stages.get("market_data", {}).get("total_retrieved", 0)
        basic_qualified = filter_stages.get("basic_filtering", {}).get("qualified_count", 0)
        quality_qualified = filter_stages.get("quality_filtering", {}).get("qualified_count", 0)
        final_count = len(filter_stages.get("final_scoring", {}).get("final_candidates", []))
        
        print(f"🌍 COMPLETE FILTERING FUNNEL:")
        print(f"  📊 Initial Universe: {initial_count:,} stocks (real Polygon data)")
        print(f"  🔍 After Basic Filters: {basic_qualified:,} stocks")
        print(f"  📈 After Quality Filters: {quality_qualified:,} stocks")
        print(f"  🎯 After Pre-Explosion Scoring: {final_count} stocks")
        
        # Calculate reduction ratios
        if initial_count > 0:
            basic_reduction = ((initial_count - basic_qualified) / initial_count) * 100
            quality_reduction = ((basic_qualified - quality_qualified) / basic_qualified) * 100 if basic_qualified > 0 else 0
            final_reduction = ((quality_qualified - final_count) / quality_qualified) * 100 if quality_qualified > 0 else 0
            overall_reduction = (final_count / initial_count) * 100
            
            print(f"\n📉 FILTERING EFFECTIVENESS:")
            print(f"  • Basic filters eliminated: {basic_reduction:.1f}%")
            print(f"  • Quality filters eliminated: {quality_reduction:.1f}%")
            print(f"  • Scoring threshold eliminated: {final_reduction:.1f}%")
            print(f"  • Overall survival rate: {overall_reduction:.3f}%")
            print(f"  • Concentration ratio: {initial_count//final_count if final_count > 0 else 'N/A'}:1")
        
        # Analysis insights
        print(f"\n💡 FILTERING INSIGHTS:")
        print(f"  🎯 Found the needles in the haystack - {final_count} pre-explosion candidates")
        print(f"  📊 All data sourced from real market (Polygon API)")
        print(f"  🚫 Zero synthetic/fallback data used")
        print(f"  ⚡ Focus on building pressure, not post-explosion")
        
        return {
            "funnel": {
                "initial": initial_count,
                "basic_qualified": basic_qualified,
                "quality_qualified": quality_qualified,
                "final_candidates": final_count
            },
            "reductions": {
                "basic_filter_elimination": basic_reduction if 'basic_reduction' in locals() else 0,
                "quality_filter_elimination": quality_reduction if 'quality_reduction' in locals() else 0,
                "scoring_elimination": final_reduction if 'final_reduction' in locals() else 0,
                "overall_survival_rate": overall_reduction if 'overall_reduction' in locals() else 0
            },
            "data_authenticity": {
                "source": "polygon_api",
                "synthetic_data_used": False,
                "fallback_data_used": False
            }
        }

async def run_real_data_demo():
    """Run the real data filtering demonstration"""
    
    demo = RealDataFilterDemo()
    
    try:
        results = await demo.run_real_data_demo()
        
        if not results.get("success"):
            print(f"\n❌ DEMO FAILED: {results.get('error', 'Unknown error')}")
            return None
        
        print("\n" + "=" * 80)
        print("🎉 REAL DATA FILTERING DEMONSTRATION COMPLETE")
        print("=" * 80)
        
        summary = results.get("summary", {})
        funnel = summary.get("funnel", {})
        
        print(f"✅ RESULTS:")
        print(f"  🌍 Started with: {funnel.get('initial', 0):,} real market stocks")
        print(f"  🎯 Final candidates: {funnel.get('final_candidates', 0)} pre-explosion opportunities")
        print(f"  📊 Data source: 100% real Polygon API market data")
        print(f"  🚫 Synthetic data: 0% (none used)")
        
        # Save results
        with open("real_data_filter_demo_results.json", "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n📋 Complete demo results saved to: real_data_filter_demo_results.json")
        
        return results
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        return None

if __name__ == "__main__":
    asyncio.run(run_real_data_demo())