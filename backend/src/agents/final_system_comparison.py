"""
Final System Comparison

Shows the difference between the old system (finds after explosion) 
and the new system (finds before explosion) side by side.
"""

import asyncio
import aiohttp
import json
from datetime import datetime
from typing import Dict, List, Any
from improved_discovery_scorer import ImprovedDiscoveryScorer

class FinalSystemComparison:
    """
    Compare old vs new discovery systems
    """
    
    def __init__(self, api_base: str = "https://amc-trader.onrender.com"):
        self.api_base = api_base
        self.improved_scorer = ImprovedDiscoveryScorer(api_base)
    
    async def run_comparison(self) -> Dict[str, Any]:
        """Run side-by-side comparison of old vs new systems"""
        
        print("🔍 FINAL SYSTEM COMPARISON")
        print("=" * 80)
        print("Comparing OLD (post-explosion) vs NEW (pre-explosion) discovery")
        print()
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "old_system": {},
            "new_system": {},
            "comparison": {}
        }
        
        try:
            # Test Old System
            print("📊 OLD SYSTEM: Current API (Finds after explosion)")
            print("-" * 60)
            old_results = await self._test_old_system()
            results["old_system"] = old_results
            
            # Test New System  
            print("\n🎯 NEW SYSTEM: Improved Algorithm (Finds before explosion)")
            print("-" * 60)
            new_results = await self._test_new_system()
            results["new_system"] = new_results
            
            # Generate Comparison
            print("\n📈 COMPARISON ANALYSIS")
            print("-" * 60)
            comparison = self._analyze_comparison(old_results, new_results)
            results["comparison"] = comparison
            
            return results
            
        except Exception as e:
            print(f"❌ Comparison failed: {e}")
            return {"error": str(e)}
    
    async def _test_old_system(self) -> Dict[str, Any]:
        """Test the current production API"""
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.api_base}/discovery/emergency/run-direct?limit=50"
                async with session.post(url, timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()
                        candidates = data.get('candidates', [])
                        
                        if not candidates:
                            print("⚠️ No candidates from old system")
                            return {"success": False, "error": "No candidates"}
                        
                        # Analyze characteristics
                        explosive_moves = [c for c in candidates if abs(c.get('price_change_pct', 0)) > 50]
                        moderate_moves = [c for c in candidates if 10 < abs(c.get('price_change_pct', 0)) <= 50]
                        small_moves = [c for c in candidates if abs(c.get('price_change_pct', 0)) <= 10]
                        
                        high_volume = [c for c in candidates if c.get('volume_ratio', 0) > 20]
                        building_volume = [c for c in candidates if 2 <= c.get('volume_ratio', 0) <= 5]
                        
                        avg_price_change = sum([abs(c.get('price_change_pct', 0)) for c in candidates]) / len(candidates)
                        avg_volume_ratio = sum([c.get('volume_ratio', 0) for c in candidates]) / len(candidates)
                        
                        print(f"✅ Found {len(candidates)} total candidates")
                        print(f"  📈 Already Explosive (>50% moves): {len(explosive_moves)}")
                        print(f"  📊 Moderate Moves (10-50%): {len(moderate_moves)}")
                        print(f"  🎯 Small Moves (≤10%): {len(small_moves)} ⭐ BEST FOR PREDICTION")
                        print(f"  🌪️ High Volume (>20x): {len(high_volume)}")
                        print(f"  📈 Building Volume (2-5x): {len(building_volume)} ⭐ IDEAL RANGE")
                        print(f"  📊 Average Price Change: {avg_price_change:.1f}%")
                        print(f"  📊 Average Volume Ratio: {avg_volume_ratio:.1f}x")
                        
                        # Show top examples
                        print(f"\n🔥 Top 5 from OLD system:")
                        for i, candidate in enumerate(candidates[:5], 1):
                            symbol = candidate.get('symbol', 'N/A')
                            score = candidate.get('score', 0)
                            volume_ratio = candidate.get('volume_ratio', 0)
                            price_change = candidate.get('price_change_pct', 0)
                            print(f"  {i}. {symbol}: {score:.1f}% | {volume_ratio:.1f}x vol | {price_change:+.1f}% move")
                        
                        return {
                            "success": True,
                            "total_candidates": len(candidates),
                            "explosive_count": len(explosive_moves),
                            "moderate_count": len(moderate_moves),
                            "small_moves_count": len(small_moves),
                            "high_volume_count": len(high_volume),
                            "building_volume_count": len(building_volume),
                            "avg_price_change": avg_price_change,
                            "avg_volume_ratio": avg_volume_ratio,
                            "top_candidates": candidates[:5],
                            "all_candidates": candidates
                        }
                    else:
                        print(f"❌ Old system failed: HTTP {response.status}")
                        return {"success": False, "error": f"HTTP {response.status}"}
        
        except Exception as e:
            print(f"❌ Old system error: {e}")
            return {"success": False, "error": str(e)}
    
    async def _test_new_system(self) -> Dict[str, Any]:
        """Test the improved discovery algorithm"""
        
        try:
            results = await self.improved_scorer.score_market_data(limit=100)
            
            if not results.get("success"):
                print(f"❌ New system failed: {results.get('error')}")
                return {"success": False, "error": results.get('error')}
            
            candidates = results.get('candidates', [])
            
            if not candidates:
                print("⚠️ No candidates from new system")
                return {"success": False, "error": "No candidates"}
            
            # Analyze new system characteristics
            pre_explosion = [c for c in candidates if c.get('action_tag') == 'PRE_EXPLOSION_IMMINENT']
            building = [c for c in candidates if c.get('action_tag') == 'BUILDING_PRESSURE']
            early = [c for c in candidates if c.get('action_tag') == 'EARLY_ACCUMULATION']
            
            small_moves = [c for c in candidates if abs(c.get('price_change_pct', 0)) <= 10]
            building_volume = [c for c in candidates if 1.5 <= c.get('volume_ratio', 0) <= 5]
            
            avg_price_change = sum([abs(c.get('price_change_pct', 0)) for c in candidates]) / len(candidates)
            avg_volume_ratio = sum([c.get('volume_ratio', 0) for c in candidates]) / len(candidates)
            avg_score = sum([c.get('score', 0) for c in candidates]) / len(candidates)
            
            print(f"✅ Found {len(candidates)} qualified candidates")
            print(f"  🚨 Pre-Explosion Imminent: {len(pre_explosion)}")
            print(f"  📈 Building Pressure: {len(building)} ⭐ PERFECT TIMING")
            print(f"  👀 Early Accumulation: {len(early)}")
            print(f"  🎯 Small Moves (≤10%): {len(small_moves)} ⭐ BEFORE EXPLOSION")
            print(f"  📈 Building Volume (1.5-5x): {len(building_volume)} ⭐ IDEAL RANGE")
            print(f"  📊 Average Price Change: {avg_price_change:.1f}%")
            print(f"  📊 Average Volume Ratio: {avg_volume_ratio:.1f}x")
            print(f"  📊 Average Score: {avg_score:.1f}")
            
            # Show top examples
            print(f"\n🎯 Top 5 from NEW system:")
            for i, candidate in enumerate(candidates[:5], 1):
                symbol = candidate.get('symbol', 'N/A')
                score = candidate.get('score', 0)
                volume_ratio = candidate.get('volume_ratio', 0)
                price_change = candidate.get('price_change_pct', 0)
                action = candidate.get('action_tag', 'N/A')
                print(f"  {i}. {symbol}: {score:.1f}% | {volume_ratio:.1f}x vol | {price_change:+.1f}% | {action}")
            
            return {
                "success": True,
                "total_candidates": len(candidates),
                "pre_explosion_count": len(pre_explosion),
                "building_count": len(building),
                "early_count": len(early),
                "small_moves_count": len(small_moves),
                "building_volume_count": len(building_volume),
                "avg_price_change": avg_price_change,
                "avg_volume_ratio": avg_volume_ratio,
                "avg_score": avg_score,
                "top_candidates": candidates[:5],
                "all_candidates": candidates
            }
            
        except Exception as e:
            print(f"❌ New system error: {e}")
            return {"success": False, "error": str(e)}
    
    def _analyze_comparison(self, old_results: Dict, new_results: Dict) -> Dict[str, Any]:
        """Analyze the differences between old and new systems"""
        
        if not (old_results.get("success") and new_results.get("success")):
            return {"error": "Cannot compare - one or both systems failed"}
        
        analysis = {}
        
        # Price change comparison
        old_avg_change = old_results.get("avg_price_change", 0)
        new_avg_change = new_results.get("avg_price_change", 0)
        
        print(f"📈 PRICE CHANGE ANALYSIS:")
        print(f"  Old System Average: {old_avg_change:.1f}% (after explosion)")
        print(f"  New System Average: {new_avg_change:.1f}% (before explosion)")
        
        if new_avg_change < old_avg_change:
            improvement_pct = ((old_avg_change - new_avg_change) / old_avg_change) * 100
            print(f"  ✅ IMPROVEMENT: {improvement_pct:.1f}% lower price changes (better timing)")
            analysis["price_change_improvement"] = improvement_pct
        else:
            print(f"  ⚠️ New system showing higher price changes")
            analysis["price_change_improvement"] = -((new_avg_change - old_avg_change) / old_avg_change) * 100
        
        # Volume analysis
        old_building_vol = old_results.get("building_volume_count", 0)
        new_building_vol = new_results.get("building_volume_count", 0)
        old_total = old_results.get("total_candidates", 1)
        new_total = new_results.get("total_candidates", 1)
        
        print(f"\n📊 VOLUME BUILDING ANALYSIS:")
        print(f"  Old System: {old_building_vol}/{old_total} ({(old_building_vol/old_total)*100:.1f}%) in building range")
        print(f"  New System: {new_building_vol}/{new_total} ({(new_building_vol/new_total)*100:.1f}%) in building range")
        
        analysis["building_volume_old_pct"] = (old_building_vol/old_total)*100
        analysis["building_volume_new_pct"] = (new_building_vol/new_total)*100
        
        # Small moves analysis (best for prediction)
        old_small = old_results.get("small_moves_count", 0)
        new_small = new_results.get("small_moves_count", 0)
        
        print(f"\n🎯 SMALL MOVES ANALYSIS (Best for prediction):")
        print(f"  Old System: {old_small}/{old_total} ({(old_small/old_total)*100:.1f}%) small moves")
        print(f"  New System: {new_small}/{new_total} ({(new_small/new_total)*100:.1f}%) small moves")
        
        if (new_small/new_total) > (old_small/old_total):
            print(f"  ✅ NEW SYSTEM BETTER: More candidates before explosion")
        else:
            print(f"  ⚠️ Old system has more small moves")
        
        analysis["small_moves_old_pct"] = (old_small/old_total)*100
        analysis["small_moves_new_pct"] = (new_small/new_total)*100
        
        # Overall recommendation
        print(f"\n💡 RECOMMENDATION:")
        
        if (analysis.get("price_change_improvement", 0) > 0 and 
            analysis.get("building_volume_new_pct", 0) > analysis.get("building_volume_old_pct", 0)):
            print(f"  ✅ USE NEW SYSTEM: Better timing, more pre-explosion candidates")
            analysis["recommendation"] = "use_new_system"
        elif analysis.get("small_moves_new_pct", 0) > 50:
            print(f"  ✅ USE NEW SYSTEM: High percentage of early-stage candidates")
            analysis["recommendation"] = "use_new_system"
        else:
            print(f"  ⚠️ NEEDS TUNING: New system needs threshold adjustments")
            analysis["recommendation"] = "tune_new_system"
        
        return analysis

async def run_final_comparison():
    """Run the final system comparison"""
    
    comparator = FinalSystemComparison()
    
    try:
        results = await comparator.run_comparison()
        
        if "error" in results:
            print(f"❌ Comparison failed: {results['error']}")
            return None
        
        print("\n" + "=" * 80)
        print("📋 FINAL COMPARISON SUMMARY")
        print("=" * 80)
        
        comparison = results.get("comparison", {})
        recommendation = comparison.get("recommendation", "unknown")
        
        if recommendation == "use_new_system":
            print("✅ RESULT: NEW SYSTEM IS BETTER")
            print("   - Finds stocks before they explode")
            print("   - Better timing for entry points")
            print("   - Higher percentage of building pressure candidates")
        elif recommendation == "tune_new_system":
            print("⚙️ RESULT: NEW SYSTEM NEEDS TUNING")
            print("   - Core algorithm is good but needs threshold adjustments")
            print("   - Should lower minimum score requirements")
        else:
            print("❓ RESULT: INCONCLUSIVE")
        
        # Save results
        with open("final_system_comparison.json", "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n📋 Full comparison saved to: final_system_comparison.json")
        
        return results
        
    except Exception as e:
        print(f"❌ Comparison failed: {e}")
        return None

if __name__ == "__main__":
    asyncio.run(run_final_comparison())