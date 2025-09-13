"""
Comprehensive Discovery System Test Runner

This tests the entire discovery pipeline showing:
1. Initial universe size
2. Each filter stage and survival counts
3. Final candidates with scores
4. Threshold analysis and recommendations
"""

import asyncio
import aiohttp
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

class SystemTestRunner:
    """
    Run comprehensive tests of the discovery system
    """
    
    def __init__(self, api_base: str = "https://amc-trader.onrender.com"):
        self.api_base = api_base
        self.logger = logging.getLogger(__name__)
    
    async def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run comprehensive test showing each filter stage"""
        
        print("🧪 COMPREHENSIVE DISCOVERY SYSTEM TEST")
        print("=" * 80)
        print(f"Testing API: {self.api_base}")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print()
        
        test_results = {
            "timestamp": datetime.now().isoformat(),
            "api_base": self.api_base,
            "test_stages": {},
            "final_analysis": {}
        }
        
        try:
            # Stage 1: Test API Health
            print("🏥 STAGE 1: API Health Check")
            print("-" * 40)
            health_result = await self._test_api_health()
            test_results["test_stages"]["health"] = health_result
            
            # Stage 2: Test Emergency Discovery (No Filters)
            print("\n🔍 STAGE 2: Emergency Discovery (Raw Data)")
            print("-" * 40)
            raw_discovery = await self._test_emergency_discovery()
            test_results["test_stages"]["raw_discovery"] = raw_discovery
            
            # Stage 3: Test Regular Discovery Endpoints
            print("\n📡 STAGE 3: Regular Discovery Endpoints")
            print("-" * 40)
            regular_discovery = await self._test_regular_discovery()
            test_results["test_stages"]["regular_discovery"] = regular_discovery
            
            # Stage 4: Test with Different Strategies
            print("\n🎯 STAGE 4: Strategy Comparison")
            print("-" * 40)
            strategy_comparison = await self._test_strategy_comparison()
            test_results["test_stages"]["strategy_comparison"] = strategy_comparison
            
            # Stage 5: Filter Analysis
            print("\n🔬 STAGE 5: Filter Breakdown Analysis")
            print("-" * 40)
            filter_analysis = await self._analyze_filter_stages()
            test_results["test_stages"]["filter_analysis"] = filter_analysis
            
            # Stage 6: Threshold Testing
            print("\n⚙️ STAGE 6: Threshold Effectiveness Test")
            print("-" * 40)
            threshold_test = await self._test_threshold_effectiveness()
            test_results["test_stages"]["threshold_test"] = threshold_test
            
            # Final Analysis
            print("\n📊 FINAL ANALYSIS")
            print("-" * 40)
            final_analysis = await self._generate_final_analysis(test_results)
            test_results["final_analysis"] = final_analysis
            
            return test_results
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            test_results["error"] = str(e)
            return test_results
    
    async def _test_api_health(self) -> Dict[str, Any]:
        """Test basic API health"""
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_base}/health", timeout=10) as response:
                    if response.status == 200:
                        health_data = await response.json()
                        print(f"✅ API Health: {health_data.get('status', 'unknown')}")
                        
                        components = health_data.get('components', {})
                        for component, status in components.items():
                            icon = "✅" if status.get('ok') else "❌"
                            print(f"  {icon} {component}: {'OK' if status.get('ok') else 'FAILED'}")
                        
                        return {
                            "success": True,
                            "status": health_data.get('status'),
                            "components": components,
                            "tag": health_data.get('tag'),
                            "commit": health_data.get('commit')
                        }
                    else:
                        print(f"❌ API Health Check Failed: HTTP {response.status}")
                        return {"success": False, "error": f"HTTP {response.status}"}
        
        except Exception as e:
            print(f"❌ API Health Check Error: {e}")
            return {"success": False, "error": str(e)}
    
    async def _test_emergency_discovery(self) -> Dict[str, Any]:
        """Test emergency discovery to see raw data"""
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.api_base}/discovery/emergency/run-direct?limit=50", timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()
                        candidates = data.get('candidates', [])
                        
                        print(f"✅ Emergency Discovery: {len(candidates)} raw candidates found")
                        
                        # Analyze raw data characteristics
                        if candidates:
                            volume_ratios = [c.get('volume_ratio', 0) for c in candidates]
                            price_changes = [abs(c.get('price_change_pct', 0)) for c in candidates]
                            scores = [c.get('score', 0) for c in candidates]
                            
                            print(f"  📊 Volume Ratios: {min(volume_ratios):.1f}x - {max(volume_ratios):.1f}x")
                            print(f"  📈 Price Changes: {min(price_changes):.1f}% - {max(price_changes):.1f}%")
                            print(f"  🎯 Scores: {min(scores):.1f} - {max(scores):.1f}")
                            
                            # Show top 5 candidates
                            print(f"  🔥 Top 5 Candidates:")
                            for i, candidate in enumerate(candidates[:5], 1):
                                symbol = candidate.get('symbol', 'N/A')
                                score = candidate.get('score', 0)
                                volume_ratio = candidate.get('volume_ratio', 0)
                                price_change = candidate.get('price_change_pct', 0)
                                print(f"    {i}. {symbol}: {score:.1f}% | {volume_ratio:.1f}x vol | {price_change:+.1f}%")
                        
                        return {
                            "success": True,
                            "count": len(candidates),
                            "candidates": candidates,
                            "method": data.get('method'),
                            "cached": data.get('cached')
                        }
                    else:
                        print(f"❌ Emergency Discovery Failed: HTTP {response.status}")
                        return {"success": False, "error": f"HTTP {response.status}"}
        
        except Exception as e:
            print(f"❌ Emergency Discovery Error: {e}")
            return {"success": False, "error": str(e)}
    
    async def _test_regular_discovery(self) -> Dict[str, Any]:
        """Test regular discovery endpoints"""
        
        endpoints_to_test = [
            "/discovery/contenders",
            "/discovery/candidates", 
            "/discovery/test"
        ]
        
        results = {}
        
        for endpoint in endpoints_to_test:
            try:
                async with aiohttp.ClientSession() as session:
                    url = f"{self.api_base}{endpoint}?strategy=hybrid_v1&limit=20"
                    async with session.get(url, timeout=15) as response:
                        
                        if response.status == 200:
                            data = await response.json()
                            candidates = data.get('candidates', data.get('items', []))
                            count = len(candidates) if isinstance(candidates, list) else data.get('count', 0)
                            
                            print(f"✅ {endpoint}: {count} candidates")
                            results[endpoint] = {
                                "success": True,
                                "count": count,
                                "status": data.get('status'),
                                "response_data": data
                            }
                            
                        elif response.status == 202:
                            print(f"⏳ {endpoint}: Processing (queued)")
                            job_data = await response.json()
                            results[endpoint] = {
                                "success": False,
                                "status": "queued",
                                "job_id": job_data.get('job_id'),
                                "message": "RQ worker processing"
                            }
                            
                        elif response.status == 404:
                            print(f"❌ {endpoint}: Not Found")
                            results[endpoint] = {
                                "success": False,
                                "error": "Endpoint not implemented"
                            }
                            
                        else:
                            print(f"❌ {endpoint}: HTTP {response.status}")
                            results[endpoint] = {
                                "success": False,
                                "error": f"HTTP {response.status}"
                            }
            
            except Exception as e:
                print(f"❌ {endpoint}: Error - {e}")
                results[endpoint] = {
                    "success": False,
                    "error": str(e)
                }
        
        return results
    
    async def _test_strategy_comparison(self) -> Dict[str, Any]:
        """Compare different discovery strategies"""
        
        strategies = ["legacy_v0", "hybrid_v1"]
        comparison_results = {}
        
        for strategy in strategies:
            try:
                async with aiohttp.ClientSession() as session:
                    # Try emergency endpoint with strategy parameter
                    url = f"{self.api_base}/discovery/emergency/run-direct?limit=20&strategy={strategy}"
                    async with session.post(url, timeout=20) as response:
                        
                        if response.status == 200:
                            data = await response.json()
                            candidates = data.get('candidates', [])
                            
                            print(f"✅ Strategy {strategy}: {len(candidates)} candidates")
                            
                            if candidates:
                                scores = [c.get('score', 0) for c in candidates]
                                avg_score = sum(scores) / len(scores)
                                trade_ready = len([c for c in candidates if c.get('action_tag') == 'trade_ready'])
                                
                                print(f"  📊 Average Score: {avg_score:.1f}")
                                print(f"  🎯 Trade Ready: {trade_ready}/{len(candidates)}")
                            
                            comparison_results[strategy] = {
                                "success": True,
                                "count": len(candidates),
                                "candidates": candidates[:5],  # Save top 5
                                "avg_score": sum([c.get('score', 0) for c in candidates]) / len(candidates) if candidates else 0
                            }
                            
                        else:
                            print(f"❌ Strategy {strategy}: HTTP {response.status}")
                            comparison_results[strategy] = {
                                "success": False,
                                "error": f"HTTP {response.status}"
                            }
            
            except Exception as e:
                print(f"❌ Strategy {strategy}: Error - {e}")
                comparison_results[strategy] = {
                    "success": False,
                    "error": str(e)
                }
        
        return comparison_results
    
    async def _analyze_filter_stages(self) -> Dict[str, Any]:
        """Analyze how filters reduce candidate count at each stage"""
        
        print("🔬 Simulating Filter Pipeline:")
        
        # Get raw data first
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.api_base}/discovery/emergency/run-direct?limit=100", timeout=30) as response:
                    if response.status != 200:
                        return {"success": False, "error": "Could not get raw data"}
                    
                    data = await response.json()
                    raw_candidates = data.get('candidates', [])
        
        except Exception as e:
            return {"success": False, "error": str(e)}
        
        if not raw_candidates:
            return {"success": False, "error": "No raw candidates to analyze"}
        
        print(f"  📥 Initial Universe: {len(raw_candidates)} candidates")
        
        # Simulate filter stages
        filter_stages = {}
        current_candidates = raw_candidates.copy()
        
        # Stage 1: Price Filter
        price_filtered = [c for c in current_candidates if 0.1 <= c.get('price', 0) <= 500]
        filter_stages["price_filter"] = {
            "survivors": len(price_filtered),
            "eliminated": len(current_candidates) - len(price_filtered),
            "criteria": "Price between $0.10 - $500"
        }
        print(f"  💰 Price Filter: {len(price_filtered)} survive (eliminated {len(current_candidates) - len(price_filtered)})")
        current_candidates = price_filtered
        
        # Stage 2: Volume Filter  
        volume_filtered = [c for c in current_candidates if c.get('volume_ratio', 0) >= 1.5]
        filter_stages["volume_filter"] = {
            "survivors": len(volume_filtered),
            "eliminated": len(current_candidates) - len(volume_filtered),
            "criteria": "Volume ratio >= 1.5x"
        }
        print(f"  📊 Volume Filter: {len(volume_filtered)} survive (eliminated {len(current_candidates) - len(volume_filtered)})")
        current_candidates = volume_filtered
        
        # Stage 3: Liquidity Filter
        liquidity_filtered = [c for c in current_candidates if c.get('dollar_volume', 0) >= 100000]
        filter_stages["liquidity_filter"] = {
            "survivors": len(liquidity_filtered),
            "eliminated": len(current_candidates) - len(liquidity_filtered),
            "criteria": "Dollar volume >= $100K"
        }
        print(f"  💵 Liquidity Filter: {len(liquidity_filtered)} survive (eliminated {len(current_candidates) - len(liquidity_filtered)})")
        current_candidates = liquidity_filtered
        
        # Stage 4: Score Filter (70% threshold)
        score_filtered = [c for c in current_candidates if c.get('score', 0) >= 70]
        filter_stages["score_filter_70"] = {
            "survivors": len(score_filtered),
            "eliminated": len(current_candidates) - len(score_filtered),
            "criteria": "Score >= 70%"
        }
        print(f"  🎯 Score Filter (70%): {len(score_filtered)} survive (eliminated {len(current_candidates) - len(score_filtered)})")
        current_candidates = score_filtered
        
        # Stage 5: Score Filter (50% threshold) 
        score_filtered_50 = [c for c in liquidity_filtered if c.get('score', 0) >= 50]
        filter_stages["score_filter_50"] = {
            "survivors": len(score_filtered_50),
            "eliminated": len(liquidity_filtered) - len(score_filtered_50),
            "criteria": "Score >= 50%"
        }
        print(f"  🎯 Score Filter (50%): {len(score_filtered_50)} survive (eliminated {len(liquidity_filtered) - len(score_filtered_50)})")
        
        # Final survivors
        final_survivors = current_candidates
        print(f"  ✅ Final Survivors: {len(final_survivors)} candidates")
        
        if final_survivors:
            print(f"  🔥 Top Final Candidates:")
            for i, candidate in enumerate(final_survivors[:3], 1):
                symbol = candidate.get('symbol', 'N/A')
                score = candidate.get('score', 0)
                volume_ratio = candidate.get('volume_ratio', 0)
                print(f"    {i}. {symbol}: {score:.1f}% score, {volume_ratio:.1f}x volume")
        
        return {
            "success": True,
            "initial_count": len(raw_candidates),
            "filter_stages": filter_stages,
            "final_survivors": len(final_survivors),
            "final_candidates": final_survivors[:10],  # Top 10
            "survival_rate": len(final_survivors) / len(raw_candidates) * 100 if raw_candidates else 0
        }
    
    async def _test_threshold_effectiveness(self) -> Dict[str, Any]:
        """Test different score thresholds to find optimal settings"""
        
        print("⚙️ Testing Score Thresholds:")
        
        # Get raw candidates for threshold testing
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.api_base}/discovery/emergency/run-direct?limit=100", timeout=30) as response:
                    if response.status != 200:
                        return {"success": False, "error": "Could not get data for threshold testing"}
                    
                    data = await response.json()
                    candidates = data.get('candidates', [])
        
        except Exception as e:
            return {"success": False, "error": str(e)}
        
        if not candidates:
            return {"success": False, "error": "No candidates for threshold testing"}
        
        # Test different thresholds
        thresholds = [30, 40, 50, 60, 70, 80, 90]
        threshold_results = {}
        
        for threshold in thresholds:
            survivors = [c for c in candidates if c.get('score', 0) >= threshold]
            survival_rate = len(survivors) / len(candidates) * 100
            
            print(f"  📊 Threshold {threshold}%: {len(survivors)} candidates ({survival_rate:.1f}% survival)")
            
            threshold_results[f"threshold_{threshold}"] = {
                "threshold": threshold,
                "survivors": len(survivors),
                "survival_rate": survival_rate,
                "top_candidates": [
                    {
                        "symbol": c.get('symbol'),
                        "score": c.get('score'),
                        "volume_ratio": c.get('volume_ratio')
                    }
                    for c in survivors[:3]
                ]
            }
        
        # Find optimal threshold (sweet spot)
        optimal_threshold = None
        for threshold in [50, 60, 70]:
            if f"threshold_{threshold}" in threshold_results:
                survivors = threshold_results[f"threshold_{threshold}"]["survivors"]
                if 3 <= survivors <= 20:  # Sweet spot: 3-20 candidates
                    optimal_threshold = threshold
                    break
        
        print(f"  🎯 Recommended Threshold: {optimal_threshold}% (produces manageable candidate count)")
        
        return {
            "success": True,
            "threshold_results": threshold_results,
            "recommended_threshold": optimal_threshold,
            "total_candidates_tested": len(candidates)
        }
    
    async def _generate_final_analysis(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate final analysis and recommendations"""
        
        analysis = {
            "system_health": "unknown",
            "discovery_working": False,
            "filter_effectiveness": "unknown",
            "recommendations": [],
            "issues_found": []
        }
        
        # Analyze API health
        health_result = test_results.get("test_stages", {}).get("health", {})
        if health_result.get("success"):
            analysis["system_health"] = "healthy"
            print("✅ API Health: GOOD")
        else:
            analysis["system_health"] = "unhealthy"
            analysis["issues_found"].append("API health check failed")
            print("❌ API Health: FAILED")
        
        # Analyze discovery functionality
        emergency_result = test_results.get("test_stages", {}).get("raw_discovery", {})
        if emergency_result.get("success") and emergency_result.get("count", 0) > 0:
            analysis["discovery_working"] = True
            print(f"✅ Discovery Working: Found {emergency_result.get('count')} candidates")
        else:
            analysis["discovery_working"] = False
            analysis["issues_found"].append("Discovery system not finding candidates")
            print("❌ Discovery: NOT WORKING")
        
        # Analyze filter effectiveness
        filter_result = test_results.get("test_stages", {}).get("filter_analysis", {})
        if filter_result.get("success"):
            survival_rate = filter_result.get("survival_rate", 0)
            final_survivors = filter_result.get("final_survivors", 0)
            
            if final_survivors == 0:
                analysis["filter_effectiveness"] = "too_strict"
                analysis["recommendations"].append("Lower score thresholds - filters are eliminating all candidates")
                print("⚠️ Filter Analysis: TOO STRICT - No survivors")
            elif final_survivors > 50:
                analysis["filter_effectiveness"] = "too_loose" 
                analysis["recommendations"].append("Raise score thresholds - too many candidates passing")
                print("⚠️ Filter Analysis: TOO LOOSE - Too many survivors")
            else:
                analysis["filter_effectiveness"] = "optimal"
                print(f"✅ Filter Analysis: OPTIMAL - {final_survivors} final candidates")
        
        # Analyze threshold effectiveness
        threshold_result = test_results.get("test_stages", {}).get("threshold_test", {})
        if threshold_result.get("success"):
            recommended = threshold_result.get("recommended_threshold")
            if recommended:
                analysis["recommendations"].append(f"Use {recommended}% score threshold for optimal results")
                print(f"✅ Threshold Analysis: Use {recommended}% threshold")
            else:
                analysis["recommendations"].append("Consider lowering thresholds - current settings too strict")
                print("⚠️ Threshold Analysis: All thresholds too strict")
        
        # Generate specific recommendations
        if not analysis["recommendations"]:
            if analysis["discovery_working"]:
                analysis["recommendations"].append("System working well - no changes needed")
            else:
                analysis["recommendations"].append("Check API connectivity and data sources")
        
        return analysis

async def run_system_test():
    """Run the comprehensive system test"""
    
    logging.basicConfig(level=logging.INFO)
    
    tester = SystemTestRunner()
    
    try:
        results = await tester.run_comprehensive_test()
        
        print("\n" + "=" * 80)
        print("📋 FINAL TEST SUMMARY")
        print("=" * 80)
        
        final_analysis = results.get("final_analysis", {})
        
        print(f"🏥 System Health: {final_analysis.get('system_health', 'unknown').upper()}")
        print(f"🔍 Discovery Working: {'YES' if final_analysis.get('discovery_working') else 'NO'}")
        print(f"🔬 Filter Effectiveness: {final_analysis.get('filter_effectiveness', 'unknown').upper()}")
        
        recommendations = final_analysis.get("recommendations", [])
        if recommendations:
            print(f"\n💡 RECOMMENDATIONS:")
            for i, rec in enumerate(recommendations, 1):
                print(f"  {i}. {rec}")
        
        issues = final_analysis.get("issues_found", [])
        if issues:
            print(f"\n❌ ISSUES FOUND:")
            for i, issue in enumerate(issues, 1):
                print(f"  {i}. {issue}")
        
        # Save results
        with open("system_test_results.json", "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n📋 Full test results saved to: system_test_results.json")
        
        return results
        
    except Exception as e:
        print(f"❌ System test failed: {e}")
        return None

if __name__ == "__main__":
    asyncio.run(run_system_test())