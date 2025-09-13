"""
True Universe Filtering Test
Shows complete filtering from raw Polygon universe (thousands) to final candidates
"""
import os
import sys
import asyncio
import json
from datetime import datetime
from typing import Dict, List, Any

# Add parent directories to path
sys.path.append('/Users/michaelmote/Desktop/AMC-TRADER/backend/src')

from services.universe_loader import UniverseLoader
from improved_discovery_scorer import ImprovedDiscoveryScorer

class TrueUniverseFilterTest:
    """
    Test filtering starting from the complete stock universe
    """
    
    def __init__(self):
        self.api_key = os.getenv('POLYGON_API_KEY', 'c8SZM3s6nkdRGHqk8MqsJqKo_gXNYMGo')
        self.scorer = ImprovedDiscoveryScorer()
        
    async def run_complete_universe_test(self) -> Dict[str, Any]:
        """Run filtering test starting from raw stock universe"""
        
        print("🌍 TRUE UNIVERSE FILTERING TEST")
        print("=" * 80)
        print("Starting from RAW stock universe (Polygon data)")
        print("Filtering down to explosive opportunity candidates")
        print()
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "universe_stats": {},
            "filtering_stages": {},
            "final_candidates": []
        }
        
        try:
            # Stage 1: Load Raw Universe from Polygon
            print("📊 STAGE 1: Loading Raw Stock Universe")
            print("-" * 60)
            
            async with UniverseLoader(self.api_key) as loader:
                raw_universe, universe_stats = await loader.load_and_filter_universe()
            
            print(f"✅ Raw universe loaded: {len(raw_universe)} stocks")
            print(f"  📊 Total fetched from Polygon: {universe_stats.get('total_fetched', 0)}")
            print(f"  💰 After price filter ($1-$100): {universe_stats.get('after_price_filter', 0)}")
            print(f"  🏢 After fund exclusion: {universe_stats.get('after_fund_filter', 0)}")
            print(f"  📈 After volume filter: {universe_stats.get('after_volume_filter', 0)}")
            print(f"  ✅ Final qualifying universe: {len(raw_universe)}")
            
            results["universe_stats"] = {
                "raw_universe_size": len(raw_universe),
                "polygon_total": universe_stats.get('total_fetched', 0),
                "after_price_filter": universe_stats.get('after_price_filter', 0),
                "after_fund_filter": universe_stats.get('after_fund_filter', 0),
                "after_volume_filter": universe_stats.get('after_volume_filter', 0)
            }
            
            if len(raw_universe) < 100:
                print("⚠️ WARNING: Universe seems too small - may indicate data issues")
                
            # Stage 2: Apply Discovery Filters
            print(f"\n🔍 STAGE 2: Applying Discovery Filters")
            print("-" * 60)
            
            # Convert universe format for scorer
            universe_symbols = [stock[0] for stock in raw_universe]  # Extract symbols
            print(f"🎯 Processing {len(universe_symbols)} symbols through discovery scorer...")
            
            # Use the improved scorer to process the universe
            discovery_results = await self.scorer.score_market_data(
                symbol_list=universe_symbols[:1000]  # Limit to first 1000 for API rate limits
            )
            
            if not discovery_results.get("success"):
                print(f"❌ Discovery scoring failed: {discovery_results.get('error')}")
                return {"error": "Discovery scoring failed"}
            
            candidates = discovery_results.get('candidates', [])
            print(f"✅ Discovery filtering complete: {len(candidates)} candidates")
            
            # Stage 3: Analysis of Filtering Effectiveness
            print(f"\n📈 STAGE 3: Filtering Analysis")
            print("-" * 60)
            
            # Categorize candidates
            pre_explosion = [c for c in candidates if c.get('action_tag') == 'PRE_EXPLOSION_IMMINENT']
            building = [c for c in candidates if c.get('action_tag') == 'BUILDING_PRESSURE']
            early = [c for c in candidates if c.get('action_tag') == 'EARLY_ACCUMULATION']
            
            print(f"🚨 Pre-Explosion Imminent: {len(pre_explosion)}")
            print(f"📈 Building Pressure: {len(building)}")
            print(f"👀 Early Accumulation: {len(early)}")
            print(f"📊 Total final candidates: {len(candidates)}")
            
            # Calculate filtering efficiency
            if len(raw_universe) > 0:
                survival_rate = (len(candidates) / len(raw_universe)) * 100
                concentration_ratio = len(raw_universe) / len(candidates) if len(candidates) > 0 else 0
                
                print(f"\n📊 FILTERING EFFICIENCY:")
                print(f"  🌍 Started with: {len(raw_universe):,} stocks")
                print(f"  🎯 Final candidates: {len(candidates)}")
                print(f"  📈 Survival rate: {survival_rate:.3f}%")
                print(f"  🔍 Concentration ratio: {concentration_ratio:.1f}:1")
                
                results["filtering_stages"] = {
                    "raw_universe": len(raw_universe),
                    "final_candidates": len(candidates),
                    "survival_rate_pct": survival_rate,
                    "concentration_ratio": concentration_ratio,
                    "pre_explosion_count": len(pre_explosion),
                    "building_pressure_count": len(building),
                    "early_accumulation_count": len(early)
                }
            
            # Stage 4: Show Top Candidates
            print(f"\n🎯 STAGE 4: Top Final Candidates")
            print("-" * 60)
            
            if candidates:
                print("🔥 TOP 10 FILTERED CANDIDATES:")
                for i, candidate in enumerate(candidates[:10], 1):
                    symbol = candidate.get('symbol', 'N/A')
                    score = candidate.get('score', 0)
                    volume_ratio = candidate.get('volume_ratio', 0)
                    price_change = candidate.get('price_change_pct', 0)
                    action = candidate.get('action_tag', 'N/A')
                    print(f"  {i:2}. {symbol:8} | Score: {score:5.1f} | Vol: {volume_ratio:6.1f}x | Move: {price_change:+6.1f}% | {action}")
                
                results["final_candidates"] = candidates[:10]
            else:
                print("⚠️ No candidates survived the filtering process")
                print("   This could indicate:")
                print("   - Scoring thresholds are too strict")
                print("   - Market conditions don't meet criteria")
                print("   - Data quality issues")
            
            return results
            
        except Exception as e:
            print(f"❌ Universe filtering test failed: {e}")
            return {"error": str(e)}

async def run_universe_filter_test():
    """Execute the complete universe filtering test"""
    
    tester = TrueUniverseFilterTest()
    
    try:
        results = await tester.run_complete_universe_test()
        
        print("\n" + "=" * 80)
        print("📋 UNIVERSE FILTERING TEST COMPLETE")
        print("=" * 80)
        
        if "error" in results:
            print(f"❌ Test failed: {results['error']}")
            return None
        
        universe_stats = results.get("universe_stats", {})
        filtering_stats = results.get("filtering_stages", {})
        
        print("✅ SUMMARY:")
        print(f"  🌍 Polygon universe: {universe_stats.get('polygon_total', 0):,} total stocks")
        print(f"  🔍 After basic filters: {universe_stats.get('raw_universe_size', 0):,} stocks") 
        print(f"  🎯 Discovery candidates: {filtering_stats.get('final_candidates', 0)} stocks")
        print(f"  📈 Filtering efficiency: {filtering_stats.get('concentration_ratio', 0):.1f}:1 concentration")
        
        if filtering_stats.get('final_candidates', 0) > 0:
            print(f"  ✅ SUCCESS: Found {filtering_stats.get('final_candidates', 0)} opportunity candidates")
            print(f"     - Pre-explosion: {filtering_stats.get('pre_explosion_count', 0)}")
            print(f"     - Building pressure: {filtering_stats.get('building_pressure_count', 0)}")
            print(f"     - Early accumulation: {filtering_stats.get('early_accumulation_count', 0)}")
        else:
            print(f"  ⚠️ NO CANDIDATES: Filtering too aggressive or poor market conditions")
        
        # Save complete results
        with open("universe_filter_test_results.json", "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n📋 Complete results saved to: universe_filter_test_results.json")
        
        return results
        
    except Exception as e:
        print(f"❌ Universe filter test failed: {e}")
        return None

if __name__ == "__main__":
    asyncio.run(run_universe_filter_test())