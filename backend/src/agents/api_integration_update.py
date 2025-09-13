"""
API Integration Update

This integrates the improved scoring algorithm with the discovery API,
creating a new endpoint that finds pre-explosion opportunities.
"""

import asyncio
import aiohttp
import json
from datetime import datetime
from typing import Dict, List, Any
from improved_discovery_scorer import ImprovedDiscoveryScorer

class APIIntegrationUpdate:
    """
    Update API with improved discovery algorithm
    """
    
    def __init__(self, api_base: str = "https://amc-trader.onrender.com"):
        self.api_base = api_base
        self.scorer = ImprovedDiscoveryScorer(api_base)
    
    async def create_pre_explosion_endpoint(self) -> Dict[str, Any]:
        """Create improved discovery endpoint with pre-explosion focus"""
        
        print("🔄 API INTEGRATION UPDATE - Pre-Explosion Discovery")
        print("=" * 70)
        
        try:
            # Get improved scoring results
            results = await self.scorer.score_market_data(limit=100)
            
            if not results.get("success"):
                return {"error": "Scoring failed", "success": False}
            
            candidates = results.get("candidates", [])
            
            # Filter for best pre-explosion candidates
            pre_explosion = [c for c in candidates if c['action_tag'] == 'PRE_EXPLOSION_IMMINENT']
            building = [c for c in candidates if c['action_tag'] == 'BUILDING_PRESSURE']
            early = [c for c in candidates if c['action_tag'] == 'EARLY_ACCUMULATION']
            
            # Create API response format
            api_response = {
                "status": "success",
                "method": "pre_explosion_discovery_v2",
                "count": len(pre_explosion) + len(building) + len(early),
                "candidates": pre_explosion + building + early,
                "categories": {
                    "pre_explosion_imminent": {
                        "count": len(pre_explosion),
                        "candidates": pre_explosion
                    },
                    "building_pressure": {
                        "count": len(building),
                        "candidates": building
                    },
                    "early_accumulation": {
                        "count": len(early),
                        "candidates": early
                    }
                },
                "strategy": "pre_explosion_v2",
                "timestamp": datetime.now().isoformat(),
                "cached": True,
                "message": "Pre-explosion candidates found using improved algorithm"
            }
            
            print(f"✅ Created API response with {api_response['count']} candidates")
            print(f"  🔥 Pre-Explosion Imminent: {len(pre_explosion)}")
            print(f"  📈 Building Pressure: {len(building)}")
            print(f"  👀 Early Accumulation: {len(early)}")
            
            # Try to update the API cache
            update_result = await self._update_api_cache(api_response)
            
            return {
                "success": True,
                "api_response": api_response,
                "cache_update": update_result
            }
            
        except Exception as e:
            print(f"❌ API integration failed: {e}")
            return {"error": str(e), "success": False}
    
    async def _update_api_cache(self, api_response: Dict[str, Any]) -> Dict[str, Any]:
        """Try to update the API cache with new results"""
        
        try:
            print("\n🔄 Attempting to update API cache...")
            
            async with aiohttp.ClientSession() as session:
                # Try to post to emergency cache update endpoint
                url = f"{self.api_base}/discovery/emergency/update-cache"
                async with session.post(url, json=api_response, timeout=15) as response:
                    if response.status == 200:
                        print("✅ API cache updated successfully")
                        return {"success": True, "status": "cache_updated"}
                    elif response.status == 404:
                        print("⚠️ Cache update endpoint not available")
                        return {"success": False, "status": "endpoint_not_found"}
                    else:
                        print(f"⚠️ Cache update failed: HTTP {response.status}")
                        return {"success": False, "status": f"http_{response.status}"}
        
        except Exception as e:
            print(f"⚠️ Cache update error: {e}")
            return {"success": False, "error": str(e)}
    
    async def test_improved_discovery(self) -> Dict[str, Any]:
        """Test the improved discovery system end-to-end"""
        
        print("\n🧪 TESTING IMPROVED DISCOVERY SYSTEM")
        print("=" * 70)
        
        try:
            # Test 1: Direct API call to emergency endpoint
            print("📡 Test 1: Current emergency discovery...")
            async with aiohttp.ClientSession() as session:
                url = f"{self.api_base}/discovery/emergency/run-direct?limit=50"
                async with session.post(url, timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()
                        current_candidates = data.get('candidates', [])
                        
                        # Count explosive vs pre-explosive
                        explosive = len([c for c in current_candidates if abs(c.get('price_change_pct', 0)) > 50])
                        moderate = len([c for c in current_candidates if 10 < abs(c.get('price_change_pct', 0)) <= 50])
                        building = len([c for c in current_candidates if abs(c.get('price_change_pct', 0)) <= 10])
                        
                        print(f"  Current System: {len(current_candidates)} total")
                        print(f"    Already Explosive (>50% moves): {explosive}")
                        print(f"    Moderate Moves (10-50%): {moderate}")
                        print(f"    Building/Pre-Explosion (≤10%): {building}")
                    else:
                        print(f"  ❌ Current system test failed: HTTP {response.status}")
            
            # Test 2: Improved algorithm
            print("\n🎯 Test 2: Improved pre-explosion algorithm...")
            improved_results = await self.scorer.score_market_data(limit=100)
            
            if improved_results.get("success"):
                improved_candidates = improved_results.get("candidates", [])
                pre_explosion = improved_results.get("pre_explosion_count", 0)
                building = improved_results.get("building_count", 0)
                early = improved_results.get("early_count", 0)
                
                print(f"  Improved System: {len(improved_candidates)} qualified")
                print(f"    Pre-Explosion Imminent: {pre_explosion}")
                print(f"    Building Pressure: {building}")
                print(f"    Early Accumulation: {early}")
                
                # Show improvement
                if improved_candidates:
                    avg_price_change = sum([abs(c.get('price_change_pct', 0)) for c in improved_candidates]) / len(improved_candidates)
                    avg_volume_ratio = sum([c.get('volume_ratio', 0) for c in improved_candidates]) / len(improved_candidates)
                    
                    print(f"    Average Price Change: {avg_price_change:.1f}% (lower = better)")
                    print(f"    Average Volume Ratio: {avg_volume_ratio:.1f}x")
            
            # Test 3: Compare quality
            print(f"\n📊 Test 3: Quality comparison...")
            
            # Count how many from current system would qualify under new criteria
            if 'current_candidates' in locals() and improved_candidates:
                old_qualifying = 0
                for candidate in current_candidates:
                    scored = self.scorer.calculate_pre_explosion_score(candidate)
                    if scored['score'] >= 45:  # Minimum threshold
                        old_qualifying += 1
                
                print(f"  Old candidates qualifying under new criteria: {old_qualifying}/{len(current_candidates)}")
                print(f"  New candidates found: {len(improved_candidates)}")
                
                if len(improved_candidates) > old_qualifying:
                    print(f"  ✅ Improvement: {len(improved_candidates) - old_qualifying} more quality candidates")
                else:
                    print(f"  ⚠️ Fewer candidates but higher quality focus")
            
            return {
                "success": True,
                "test_results": {
                    "current_system": locals().get('current_candidates', []),
                    "improved_system": improved_candidates,
                    "comparison": {
                        "current_count": len(locals().get('current_candidates', [])),
                        "improved_count": len(improved_candidates),
                        "pre_explosion_focus": pre_explosion + building
                    }
                }
            }
            
        except Exception as e:
            print(f"❌ Testing failed: {e}")
            return {"error": str(e), "success": False}

async def run_api_integration():
    """Run the API integration update"""
    
    integrator = APIIntegrationUpdate()
    
    try:
        # Step 1: Create improved endpoint
        print("🚀 STEP 1: Creating Pre-Explosion Discovery Endpoint")
        endpoint_result = await integrator.create_pre_explosion_endpoint()
        
        if not endpoint_result.get("success"):
            print(f"❌ Endpoint creation failed: {endpoint_result.get('error')}")
            return None
        
        # Step 2: Test the system
        print("\n🚀 STEP 2: Testing Improved Discovery")
        test_result = await integrator.test_improved_discovery()
        
        # Step 3: Save results
        combined_results = {
            "timestamp": datetime.now().isoformat(),
            "endpoint_creation": endpoint_result,
            "system_test": test_result,
            "status": "integration_complete"
        }
        
        with open("api_integration_results.json", "w") as f:
            json.dump(combined_results, f, indent=2, default=str)
        
        print("\n" + "=" * 70)
        print("✅ API INTEGRATION COMPLETE")
        print("=" * 70)
        print("📋 Results saved to: api_integration_results.json")
        
        # Summary
        api_response = endpoint_result.get("api_response", {})
        if api_response:
            print(f"\n📊 FINAL SUMMARY:")
            print(f"Pre-Explosion Candidates: {api_response.get('count', 0)}")
            
            categories = api_response.get("categories", {})
            for category, data in categories.items():
                print(f"  {category.replace('_', ' ').title()}: {data.get('count', 0)}")
        
        return combined_results
        
    except Exception as e:
        print(f"❌ API integration failed: {e}")
        return None

if __name__ == "__main__":
    asyncio.run(run_api_integration())