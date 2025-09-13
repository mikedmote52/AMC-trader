"""
Discovery System Debugger

Specialized agent for debugging and optimizing the AMC-TRADER discovery system
to ensure it's properly searching the universe of stocks and identifying explosive opportunities.
"""

import asyncio
import logging
import json
import aiohttp
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class DiscoverySystemDebugger:
    """
    Specialized debugger for the AMC-TRADER discovery system
    """
    
    def __init__(self, api_base: str = "https://amc-trader.onrender.com"):
        self.api_base = api_base
        self.logger = logging.getLogger(__name__)
        self.debug_results = {}
        
    async def comprehensive_discovery_debug(self) -> Dict[str, Any]:
        """Comprehensive debugging of the discovery system"""
        
        print("🔍 AMC-TRADER Discovery System Debug Analysis")
        print("=" * 60)
        
        debug_report = {
            "timestamp": datetime.now().isoformat(),
            "system_connectivity": {},
            "discovery_pipeline": {},
            "stock_universe": {},
            "filtering_analysis": {},
            "explosive_opportunities": {},
            "recommendations": []
        }
        
        # 1. System Connectivity Analysis
        print("\n📡 PHASE 1: System Connectivity Analysis")
        print("-" * 40)
        
        connectivity_results = await self._analyze_system_connectivity()
        debug_report["system_connectivity"] = connectivity_results
        
        # 2. Discovery Pipeline Analysis
        print("\n🔍 PHASE 2: Discovery Pipeline Analysis")
        print("-" * 40)
        
        pipeline_results = await self._analyze_discovery_pipeline()
        debug_report["discovery_pipeline"] = pipeline_results
        
        # 3. Stock Universe Coverage Analysis
        print("\n🌍 PHASE 3: Stock Universe Coverage Analysis")
        print("-" * 40)
        
        universe_results = await self._analyze_stock_universe()
        debug_report["stock_universe"] = universe_results
        
        # 4. Filtering Algorithm Analysis
        print("\n⚡ PHASE 4: Filtering Algorithm Analysis")
        print("-" * 40)
        
        filtering_results = await self._analyze_filtering_algorithms()
        debug_report["filtering_analysis"] = filtering_results
        
        # 5. Explosive Opportunities Detection
        print("\n💥 PHASE 5: Explosive Opportunities Detection")
        print("-" * 40)
        
        opportunities_results = await self._analyze_explosive_opportunities()
        debug_report["explosive_opportunities"] = opportunities_results
        
        # 6. Generate Recommendations
        print("\n💡 PHASE 6: System Optimization Recommendations")
        print("-" * 40)
        
        recommendations = await self._generate_recommendations(debug_report)
        debug_report["recommendations"] = recommendations
        
        return debug_report
    
    async def _analyze_system_connectivity(self) -> Dict[str, Any]:
        """Analyze system connectivity and API availability"""
        
        results = {
            "api_health": {},
            "endpoints_status": {},
            "data_providers": {},
            "ui_backend_connection": {}
        }
        
        async with aiohttp.ClientSession() as session:
            # Test core API health
            print("🔍 Testing core API health...")
            try:
                async with session.get(f"{self.api_base}/health", timeout=30) as response:
                    if response.status == 200:
                        health_data = await response.json()
                        results["api_health"] = {
                            "status": "healthy",
                            "response_time": response.headers.get('X-Response-Time', 'unknown'),
                            "components": health_data.get("components", {}),
                            "tag": health_data.get("tag", "unknown")
                        }
                        print(f"  ✅ API Health: {health_data.get('status', 'unknown')}")
                        
                        # Check data provider connections
                        components = health_data.get("components", {})
                        for provider, status in components.items():
                            status_icon = "✅" if status.get("ok") else "❌"
                            print(f"  {status_icon} {provider.title()}: {'Connected' if status.get('ok') else 'Failed'}")
                            
                    else:
                        results["api_health"] = {"status": "failed", "http_code": response.status}
                        print(f"  ❌ API Health Check Failed: HTTP {response.status}")
                        
            except Exception as e:
                results["api_health"] = {"status": "error", "error": str(e)}
                print(f"  ❌ API Health Check Error: {e}")
            
            # Test critical discovery endpoints
            print("\n🔍 Testing discovery endpoints...")
            discovery_endpoints = [
                "/discovery/contenders",
                "/discovery/trigger", 
                "/discovery/status",
                "/discovery/diagnostics"
            ]
            
            for endpoint in discovery_endpoints:
                try:
                    if endpoint == "/discovery/trigger":
                        # POST request for trigger
                        async with session.post(f"{self.api_base}{endpoint}?strategy=hybrid_v1&limit=5", timeout=30) as response:
                            status = response.status
                            if status == 200:
                                data = await response.json()
                                job_id = data.get("job_id", "unknown")
                                print(f"  ✅ {endpoint}: Job triggered ({job_id})")
                                results["endpoints_status"][endpoint] = {"status": "working", "job_id": job_id}
                            else:
                                print(f"  ⚠️  {endpoint}: HTTP {status}")
                                results["endpoints_status"][endpoint] = {"status": "failed", "http_code": status}
                    else:
                        # GET request for others
                        async with session.get(f"{self.api_base}{endpoint}?limit=10", timeout=30) as response:
                            status = response.status
                            if status == 200:
                                print(f"  ✅ {endpoint}: Working")
                                results["endpoints_status"][endpoint] = {"status": "working"}
                            elif status == 202:
                                print(f"  ⏳ {endpoint}: Queued (async processing)")
                                results["endpoints_status"][endpoint] = {"status": "queued"}
                            else:
                                print(f"  ❌ {endpoint}: HTTP {status}")
                                results["endpoints_status"][endpoint] = {"status": "failed", "http_code": status}
                                
                except Exception as e:
                    print(f"  ❌ {endpoint}: Error - {e}")
                    results["endpoints_status"][endpoint] = {"status": "error", "error": str(e)}
        
        return results
    
    async def _analyze_discovery_pipeline(self) -> Dict[str, Any]:
        """Analyze the discovery pipeline functionality"""
        
        results = {
            "job_queue_status": {},
            "worker_health": {},
            "strategies_available": {},
            "processing_performance": {}
        }
        
        print("🔍 Analyzing discovery job processing...")
        
        async with aiohttp.ClientSession() as session:
            # Trigger test discovery jobs for both strategies
            strategies = ["hybrid_v1", "legacy_v0"]
            
            for strategy in strategies:
                print(f"  🧪 Testing {strategy} strategy...")
                
                try:
                    # Trigger discovery job
                    trigger_start = time.time()
                    async with session.post(f"{self.api_base}/discovery/trigger?strategy={strategy}&limit=3", timeout=30) as response:
                        trigger_time = time.time() - trigger_start
                        
                        if response.status == 200:
                            job_data = await response.json()
                            job_id = job_data.get("job_id", "unknown")
                            
                            print(f"    ✅ Job triggered: {job_id} ({trigger_time:.2f}s)")
                            
                            # Wait and check job status
                            await asyncio.sleep(5)
                            
                            status_start = time.time()
                            async with session.get(f"{self.api_base}/discovery/status?job_id={job_id}", timeout=30) as status_response:
                                status_time = time.time() - status_start
                                
                                if status_response.status == 200:
                                    status_data = await status_response.json()
                                    job_status = status_data.get("status", "unknown")
                                    progress = status_data.get("progress", 0)
                                    
                                    print(f"    📊 Status: {job_status} (Progress: {progress}%, {status_time:.2f}s)")
                                    
                                    results["strategies_available"][strategy] = {
                                        "trigger_success": True,
                                        "trigger_time": trigger_time,
                                        "job_id": job_id,
                                        "status": job_status,
                                        "progress": progress
                                    }
                                    
                                    # If job is stuck, note it
                                    if job_status == "queued" and progress == 0:
                                        print(f"    ⚠️  Job appears stuck in queue")
                                        results["job_queue_status"]["stuck_jobs"] = results["job_queue_status"].get("stuck_jobs", 0) + 1
                                    
                                else:
                                    print(f"    ❌ Status check failed: HTTP {status_response.status}")
                                    
                        else:
                            print(f"    ❌ Trigger failed: HTTP {response.status}")
                            results["strategies_available"][strategy] = {
                                "trigger_success": False,
                                "http_code": response.status
                            }
                            
                except Exception as e:
                    print(f"    ❌ Strategy test error: {e}")
                    results["strategies_available"][strategy] = {
                        "trigger_success": False,
                        "error": str(e)
                    }
        
        return results
    
    async def _analyze_stock_universe(self) -> Dict[str, Any]:
        """Analyze stock universe coverage and data availability"""
        
        results = {
            "universe_size": {},
            "data_coverage": {},
            "market_segments": {},
            "data_freshness": {}
        }
        
        print("🔍 Analyzing stock universe coverage...")
        
        # Check if we can get any discovery results to analyze universe
        async with aiohttp.ClientSession() as session:
            try:
                # Try to get recent discovery results or diagnostics
                async with session.get(f"{self.api_base}/discovery/diagnostics", timeout=30) as response:
                    if response.status == 200:
                        diagnostics_data = await response.json()
                        print("  ✅ Discovery diagnostics available")
                        results["universe_size"] = diagnostics_data.get("universe_stats", {})
                    else:
                        print(f"  ⚠️  Discovery diagnostics not available: HTTP {response.status}")
                
                # Try to trigger a diagnostic discovery to see what we get
                async with session.post(f"{self.api_base}/discovery/trigger?strategy=hybrid_v1&limit=100&relaxed=true", timeout=30) as response:
                    if response.status == 200:
                        job_data = await response.json()
                        job_id = job_data.get("job_id")
                        print(f"  ✅ Large sample discovery triggered: {job_id}")
                        
                        # Wait longer for large sample
                        await asyncio.sleep(15)
                        
                        async with session.get(f"{self.api_base}/discovery/status?job_id={job_id}", timeout=30) as status_response:
                            if status_response.status == 200:
                                status_data = await status_response.json()
                                if status_data.get("status") == "completed":
                                    candidates = status_data.get("result", {}).get("candidates", [])
                                    
                                    print(f"  📊 Sample discovery returned {len(candidates)} candidates")
                                    
                                    if candidates:
                                        # Analyze the candidates to understand universe coverage
                                        symbols = [c.get("symbol") for c in candidates if c.get("symbol")]
                                        scores = [c.get("score", 0) for c in candidates if "score" in c]
                                        
                                        results["data_coverage"]["sample_symbols"] = symbols[:10]  # First 10
                                        results["data_coverage"]["score_range"] = {
                                            "min": min(scores) if scores else 0,
                                            "max": max(scores) if scores else 0,
                                            "avg": sum(scores) / len(scores) if scores else 0
                                        }
                                        
                                        print(f"  📈 Score range: {results['data_coverage']['score_range']['min']:.2f} - {results['data_coverage']['score_range']['max']:.2f}")
                                        print(f"  🎯 Sample symbols: {', '.join(symbols[:5])}")
                                        
                                    else:
                                        print("  ❌ No candidates returned from sample discovery")
                                        
                                else:
                                    print(f"  ⏳ Sample discovery still processing: {status_data.get('status')}")
                            
            except Exception as e:
                print(f"  ❌ Universe analysis error: {e}")
        
        return results
    
    async def _analyze_filtering_algorithms(self) -> Dict[str, Any]:
        """Analyze filtering algorithms for explosive opportunity detection"""
        
        results = {
            "hybrid_v1_analysis": {},
            "legacy_v0_analysis": {},
            "filter_effectiveness": {},
            "threshold_analysis": {}
        }
        
        print("🔍 Analyzing filtering algorithms...")
        
        # Test known explosive stocks to see if they would be detected
        test_symbols = [
            "TSLA",  # High volatility, growth stock
            "NVDA",  # AI/semiconductor momentum
            "AMZN",  # Large cap with momentum potential
            "MSTR",  # Bitcoin proxy with high volatility
            "COIN",  # Crypto-related volatility
            "RBLX",  # Gaming/metaverse growth
            "PLTR",  # Data analytics growth
            "ROKU",  # Streaming/tech volatility
        ]
        
        print("  🧪 Testing algorithm effectiveness on known volatile stocks...")
        
        async with aiohttp.ClientSession() as session:
            for symbol in test_symbols[:3]:  # Test first 3 to avoid overwhelming
                try:
                    # Use audit endpoint if available to test individual symbols
                    async with session.get(f"{self.api_base}/discovery/audit/{symbol}?strategy=hybrid_v1", timeout=30) as response:
                        if response.status == 200:
                            audit_data = await response.json()
                            score = audit_data.get("score", 0)
                            components = audit_data.get("subscores", {})
                            
                            print(f"    📊 {symbol}: Score {score:.2f}")
                            
                            if components:
                                print(f"      - Volume/Momentum: {components.get('volume_momentum', 0):.2f}")
                                print(f"      - Squeeze: {components.get('squeeze', 0):.2f}")
                                print(f"      - Catalyst: {components.get('catalyst', 0):.2f}")
                            
                            results["hybrid_v1_analysis"][symbol] = {
                                "score": score,
                                "components": components,
                                "meets_threshold": score >= 70
                            }
                            
                        elif response.status == 404:
                            print(f"    ❌ {symbol}: Audit endpoint not available")
                        else:
                            print(f"    ⚠️  {symbol}: HTTP {response.status}")
                            
                except Exception as e:
                    print(f"    ❌ {symbol}: Error - {e}")
        
        return results
    
    async def _analyze_explosive_opportunities(self) -> Dict[str, Any]:
        """Analyze the system's ability to detect explosive opportunities"""
        
        results = {
            "current_candidates": {},
            "opportunity_characteristics": {},
            "detection_gaps": {},
            "optimization_potential": {}
        }
        
        print("🔍 Analyzing explosive opportunity detection...")
        
        async with aiohttp.ClientSession() as session:
            # Try to get current best candidates
            try:
                async with session.post(f"{self.api_base}/discovery/trigger?strategy=hybrid_v1&limit=20", timeout=30) as response:
                    if response.status == 200:
                        job_data = await response.json()
                        job_id = job_data.get("job_id")
                        
                        # Wait for processing
                        await asyncio.sleep(10)
                        
                        async with session.get(f"{self.api_base}/discovery/status?job_id={job_id}", timeout=30) as status_response:
                            if status_response.status == 200:
                                status_data = await status_response.json()
                                
                                if status_data.get("status") == "completed":
                                    candidates = status_data.get("result", {}).get("candidates", [])
                                    
                                    if candidates:
                                        print(f"  📈 Found {len(candidates)} current candidates")
                                        
                                        # Analyze top candidates
                                        top_candidates = sorted(candidates, key=lambda x: x.get("score", 0), reverse=True)[:5]
                                        
                                        for i, candidate in enumerate(top_candidates, 1):
                                            symbol = candidate.get("symbol", "UNKNOWN")
                                            score = candidate.get("score", 0)
                                            action_tag = candidate.get("action_tag", "none")
                                            
                                            print(f"    {i}. {symbol}: Score {score:.2f} ({action_tag})")
                                            
                                            # Analyze what makes this explosive
                                            subscores = candidate.get("subscores", {})
                                            if subscores:
                                                high_components = [k for k, v in subscores.items() if v > 0.7]
                                                if high_components:
                                                    print(f"       Strong in: {', '.join(high_components)}")
                                        
                                        results["current_candidates"]["top_candidates"] = top_candidates
                                        results["current_candidates"]["total_found"] = len(candidates)
                                        
                                        # Analyze opportunity characteristics
                                        high_score_count = len([c for c in candidates if c.get("score", 0) >= 75])
                                        trade_ready_count = len([c for c in candidates if c.get("action_tag") == "trade_ready"])
                                        
                                        results["opportunity_characteristics"] = {
                                            "high_score_candidates": high_score_count,
                                            "trade_ready_candidates": trade_ready_count,
                                            "average_score": sum(c.get("score", 0) for c in candidates) / len(candidates),
                                            "score_distribution": {
                                                "90+": len([c for c in candidates if c.get("score", 0) >= 90]),
                                                "80-89": len([c for c in candidates if 80 <= c.get("score", 0) < 90]),
                                                "70-79": len([c for c in candidates if 70 <= c.get("score", 0) < 80]),
                                                "60-69": len([c for c in candidates if 60 <= c.get("score", 0) < 70]),
                                                "<60": len([c for c in candidates if c.get("score", 0) < 60])
                                            }
                                        }
                                        
                                        print(f"  🎯 Trade-ready candidates: {trade_ready_count}")
                                        print(f"  📊 Average score: {results['opportunity_characteristics']['average_score']:.2f}")
                                        
                                    else:
                                        print("  ❌ No candidates found in current discovery")
                                        results["detection_gaps"]["no_candidates"] = True
                                        
                                else:
                                    print(f"  ⏳ Discovery still processing: {status_data.get('status')}")
                                    
            except Exception as e:
                print(f"  ❌ Opportunity analysis error: {e}")
        
        return results
    
    async def _generate_recommendations(self, debug_report: Dict[str, Any]) -> List[str]:
        """Generate system optimization recommendations"""
        
        recommendations = []
        
        print("🔍 Generating optimization recommendations...")
        
        # Analyze system connectivity issues
        connectivity = debug_report.get("system_connectivity", {})
        if connectivity.get("api_health", {}).get("status") != "healthy":
            recommendations.append("🔧 Fix API health issues - core system not responding properly")
        
        # Analyze discovery pipeline issues
        pipeline = debug_report.get("discovery_pipeline", {})
        strategies = pipeline.get("strategies_available", {})
        
        stuck_jobs = 0
        for strategy_name, strategy_data in strategies.items():
            if strategy_data.get("status") == "queued" and strategy_data.get("progress", 0) == 0:
                stuck_jobs += 1
        
        if stuck_jobs > 0:
            recommendations.append("⚡ Critical: Restart RQ workers - discovery jobs are stuck in queue")
            recommendations.append("🔄 Clear Redis job queue to remove stuck jobs")
        
        # Analyze stock universe coverage
        universe = debug_report.get("stock_universe", {})
        data_coverage = universe.get("data_coverage", {})
        
        if not data_coverage.get("sample_symbols"):
            recommendations.append("🌍 Expand stock universe coverage - no symbols being processed")
        
        if data_coverage.get("score_range", {}).get("max", 0) < 50:
            recommendations.append("📈 Optimize scoring algorithms - maximum scores too low for opportunity detection")
        
        # Analyze explosive opportunities
        opportunities = debug_report.get("explosive_opportunities", {})
        opportunity_chars = opportunities.get("opportunity_characteristics", {})
        
        trade_ready = opportunity_chars.get("trade_ready_candidates", 0)
        if trade_ready == 0:
            recommendations.append("💥 Critical: No trade-ready explosive opportunities detected")
            recommendations.append("🎯 Lower thresholds or expand filtering criteria for opportunity detection")
        
        avg_score = opportunity_chars.get("average_score", 0)
        if avg_score < 30:
            recommendations.append("📊 Scoring system needs calibration - average scores too low")
        
        # System-wide recommendations
        if len(recommendations) == 0:
            recommendations.append("✅ System appears functional - monitor for candidate quality")
        else:
            recommendations.insert(0, "🚨 Critical issues detected requiring immediate attention")
        
        # Always add optimization recommendations
        recommendations.extend([
            "🔍 Implement real-time monitoring of discovery job completion rates",
            "📈 Add universe size tracking to ensure comprehensive stock coverage",
            "⚡ Optimize filtering algorithms for better explosive opportunity detection",
            "🎯 Add manual override for testing specific high-potential symbols"
        ])
        
        for i, rec in enumerate(recommendations, 1):
            print(f"  {i}. {rec}")
        
        return recommendations

async def run_discovery_system_debug():
    """Run comprehensive discovery system debugging"""
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    debugger = DiscoverySystemDebugger()
    
    try:
        debug_report = await debugger.comprehensive_discovery_debug()
        
        print("\n" + "=" * 60)
        print("🎯 DISCOVERY SYSTEM DEBUG SUMMARY")
        print("=" * 60)
        
        # System status
        api_health = debug_report.get("system_connectivity", {}).get("api_health", {})
        if api_health.get("status") == "healthy":
            print("✅ API System: HEALTHY")
        else:
            print("❌ API System: UNHEALTHY")
        
        # Discovery pipeline status
        strategies = debug_report.get("discovery_pipeline", {}).get("strategies_available", {})
        working_strategies = len([s for s in strategies.values() if s.get("trigger_success")])
        print(f"📊 Discovery Strategies: {working_strategies}/{len(strategies)} working")
        
        # Opportunity detection
        opportunities = debug_report.get("explosive_opportunities", {}).get("opportunity_characteristics", {})
        trade_ready = opportunities.get("trade_ready_candidates", 0)
        total_candidates = opportunities.get("total_found", 0) if opportunities else 0
        
        if trade_ready > 0:
            print(f"💥 Explosive Opportunities: {trade_ready} trade-ready candidates found")
        elif total_candidates > 0:
            print(f"⚠️  Explosive Opportunities: {total_candidates} candidates found, none trade-ready")
        else:
            print("❌ Explosive Opportunities: NO CANDIDATES DETECTED")
        
        # Critical recommendations
        recommendations = debug_report.get("recommendations", [])
        critical_recs = [r for r in recommendations if "Critical" in r or "🚨" in r]
        
        if critical_recs:
            print(f"\n🚨 CRITICAL ACTIONS REQUIRED:")
            for rec in critical_recs:
                print(f"   • {rec}")
        
        # Save debug report
        with open("discovery_debug_report.json", "w") as f:
            json.dump(debug_report, f, indent=2, default=str)
        
        print(f"\n📋 Full debug report saved to: discovery_debug_report.json")
        
        return debug_report
        
    except Exception as e:
        print(f"❌ Debug analysis failed: {e}")
        return None

if __name__ == "__main__":
    print("🚀 AMC-TRADER Discovery System Debugger")
    print("=" * 60)
    
    asyncio.run(run_discovery_system_debug())