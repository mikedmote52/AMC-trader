#!/usr/bin/env python3
"""
Test script for the Caching Performance Agent
"""

import asyncio
import json
import time
import logging
from caching_performance_agent import CachingPerformanceAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_caching_agent():
    """Test the Caching Performance Agent functionality"""
    
    print("=" * 60)
    print("CACHING PERFORMANCE AGENT TEST")
    print("=" * 60)
    
    # Initialize the agent
    agent = CachingPerformanceAgent()
    
    print("\n1. READING DISCOVERY RESULTS")
    print("-" * 40)
    
    # Read discovery results
    discovery_data = await agent.read_discovery_results()
    if discovery_data:
        print(f"✅ Successfully read discovery results")
        print(f"   - Timestamp: {discovery_data.get('timestamp', 'N/A')}")
        print(f"   - Strategy: {discovery_data.get('strategy', 'N/A')}")
        print(f"   - Candidates: {discovery_data.get('count', 0)}")
        print(f"   - Total scanned: {discovery_data.get('meta', {}).get('total_scanned', 0)}")
    else:
        print("❌ Failed to read discovery results")
        return
    
    print("\n2. IMPLEMENTING CACHING STRATEGY")
    print("-" * 40)
    
    # Test different caching strategies
    cache_key = "test_discovery_2025-01-09"
    
    # Cache the discovery results
    success = await agent.cache_discovery_results(discovery_data, cache_key)
    if success:
        print(f"✅ Successfully cached discovery results with key: {cache_key}")
    else:
        print("❌ Failed to cache discovery results")
        return
    
    # Test cache retrieval (should be a hit)
    print("\n3. TESTING CACHE RETRIEVAL")
    print("-" * 40)
    
    cached_data = await agent.get_cached_discovery_results(cache_key)
    if cached_data:
        print("✅ Cache HIT - Successfully retrieved cached data")
        print(f"   - Retrieved {len(cached_data.get('candidates', []))} candidates")
    else:
        print("❌ Cache MISS - Failed to retrieve cached data")
    
    # Test cache miss with invalid key
    invalid_data = await agent.get_cached_discovery_results("invalid_key")
    if not invalid_data:
        print("✅ Cache MISS - Correctly returned None for invalid key")
    
    # Test multiple cache operations for metrics
    print("\n4. GENERATING CACHE METRICS")
    print("-" * 40)
    
    # Perform multiple cache operations
    for i in range(10):
        test_key = f"test_batch_{i}"
        await agent.cache_discovery_results(discovery_data, test_key)
        
        # Mix of hits and misses
        if i % 2 == 0:
            await agent.get_cached_discovery_results(test_key)  # Hit
        else:
            await agent.get_cached_discovery_results(f"miss_key_{i}")  # Miss
    
    # Get cache statistics
    stats = agent.get_cache_stats()
    print(f"✅ Cache Statistics Generated:")
    print(f"   - Total Requests: {stats['metrics']['total_requests']}")
    print(f"   - Cache Hits: {stats['metrics']['hits']}")
    print(f"   - Cache Misses: {stats['metrics']['misses']}")
    print(f"   - Hit Ratio: {stats['metrics']['hit_ratio']:.2%}")
    print(f"   - Avg Response Time: {stats['metrics']['avg_response_time_ms']:.2f}ms")
    
    print("\n5. PERFORMANCE MONITORING")
    print("-" * 40)
    
    # Monitor performance
    performance_data = await agent.monitor_performance()
    
    print("✅ Performance Monitoring Results:")
    print(f"   - Cache Size: {performance_data['cache_metrics']['cache_size_mb']:.2f}MB")
    print(f"   - Hit Ratio: {performance_data['cache_metrics']['hit_ratio']:.2%}")
    print(f"   - Response Time: {performance_data['cache_metrics']['avg_response_time_ms']:.2f}ms")
    
    # Display Redis info
    redis_info = performance_data.get('redis_info', {})
    if redis_info:
        print(f"   - Redis Memory: {redis_info.get('used_memory_mb', 0):.2f}MB")
        print(f"   - Connected Clients: {redis_info.get('connected_clients', 0)}")
        print(f"   - Total Commands: {redis_info.get('total_commands_processed', 0)}")
    
    # Display alerts
    alerts = performance_data.get('alerts', [])
    if alerts:
        print(f"\n⚠️  Performance Alerts ({len(alerts)}):")
        for alert in alerts:
            print(f"   - {alert.alert_type}: {alert.message} (Severity: {alert.severity})")
    else:
        print("✅ No performance alerts")
    
    # Display recommendations
    recommendations = performance_data.get('recommendations', [])
    if recommendations:
        print(f"\n💡 Optimization Recommendations ({len(recommendations)}):")
        for rec in recommendations:
            print(f"   - {rec}")
    else:
        print("✅ No optimization recommendations")
    
    print("\n6. TESTING DIFFERENT CACHING STRATEGIES")
    print("-" * 40)
    
    # Test market data strategy
    market_data = {"VIGL": {"price": 4.52, "volume": 2500000}, "QUBT": {"price": 12.34, "volume": 1800000}}
    success = await agent.cache_with_strategy("market_snapshot", market_data, "market_data")
    print(f"✅ Market data caching: {'Success' if success else 'Failed'}")
    
    # Test analytics strategy  
    analytics_data = {"trend_analysis": "bullish", "confidence": 0.85, "indicators": ["volume_surge", "squeeze_potential"]}
    success = await agent.cache_with_strategy("trend_analysis", analytics_data, "analytics")
    print(f"✅ Analytics data caching: {'Success' if success else 'Failed'}")
    
    print("\n7. CACHE OPTIMIZATION")
    print("-" * 40)
    
    # Run optimization
    await agent.optimize_cache_performance()
    print("✅ Cache optimization completed")
    
    print("\n8. FINAL PERFORMANCE SUMMARY")
    print("-" * 40)
    
    final_stats = agent.get_cache_stats()
    final_performance = await agent.monitor_performance()
    
    print("📊 FINAL METRICS SUMMARY:")
    print(f"   - Total Cache Operations: {final_stats['metrics']['total_requests']}")
    print(f"   - Overall Hit Ratio: {final_stats['metrics']['hit_ratio']:.2%}")
    print(f"   - Average Response Time: {final_stats['metrics']['avg_response_time_ms']:.2f}ms")
    print(f"   - Cache Memory Usage: {final_performance['cache_metrics']['cache_size_mb']:.2f}MB")
    print(f"   - Redis Connection: {'✅ Active' if final_stats['redis_connection'] else '❌ Inactive'}")
    
    # Performance analysis
    print("\n🔍 PERFORMANCE ANALYSIS:")
    if final_stats['metrics']['hit_ratio'] >= 0.8:
        print("   ✅ Excellent cache hit ratio - caching strategy is effective")
    elif final_stats['metrics']['hit_ratio'] >= 0.6:
        print("   ⚠️  Good cache hit ratio - consider optimizing TTL settings")
    else:
        print("   ❌ Poor cache hit ratio - review caching strategy")
    
    if final_stats['metrics']['avg_response_time_ms'] <= 50:
        print("   ✅ Excellent response times - cache is performing optimally")
    elif final_stats['metrics']['avg_response_time_ms'] <= 100:
        print("   ⚠️  Good response times - monitor for degradation")
    else:
        print("   ❌ High response times - consider optimization")
    
    print("\n" + "=" * 60)
    print("CACHING PERFORMANCE AGENT TEST COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_caching_agent())