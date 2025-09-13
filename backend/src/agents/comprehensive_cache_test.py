#!/usr/bin/env python3
"""
Comprehensive caching performance test integrating with existing AMC-TRADER Redis infrastructure
"""

import asyncio
import json
import time
import sys
import os
from datetime import datetime
from pathlib import Path

# Add the parent directories to the path so we can import from the services
sys.path.append('/Users/michaelmote/Desktop/AMC-TRADER/backend/src')

from shared.redis_client import get_redis_client, SqueezeCache, get_dynamic_ttl
from agents.caching_performance_agent import CachingPerformanceAgent


async def comprehensive_cache_performance_test():
    """Run comprehensive cache performance tests with integration"""
    
    print("=" * 80)
    print("AMC-TRADER COMPREHENSIVE CACHING PERFORMANCE TEST")
    print("=" * 80)
    
    # Initialize components
    redis_client = get_redis_client()
    squeeze_cache = SqueezeCache()
    caching_agent = CachingPerformanceAgent(redis_client=redis_client)
    
    # Test data
    discovery_data_path = "/Users/michaelmote/Desktop/AMC-TRADER/backend/src/data/discovery_results.json"
    
    test_results = {
        'test_timestamp': datetime.now().isoformat(),
        'redis_connectivity': False,
        'discovery_data_available': False,
        'cache_performance': {},
        'squeeze_cache_performance': {},
        'dynamic_ttl_analysis': {},
        'integration_tests': {},
        'performance_bottlenecks': [],
        'recommendations': []
    }
    
    print("\\n1. TESTING REDIS CONNECTIVITY")
    print("-" * 50)
    
    try:
        redis_client.ping()
        test_results['redis_connectivity'] = True
        print("✅ Redis connection successful")
        
        redis_info = redis_client.info()
        print(f"   - Redis Version: {redis_info.get('redis_version', 'unknown')}")
        print(f"   - Used Memory: {redis_info.get('used_memory_human', 'unknown')}")
        print(f"   - Connected Clients: {redis_info.get('connected_clients', 0)}")
        
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return test_results
    
    print("\\n2. TESTING DISCOVERY DATA AVAILABILITY")
    print("-" * 50)
    
    discovery_data = await caching_agent.read_discovery_results()
    if discovery_data:
        test_results['discovery_data_available'] = True
        print("✅ Discovery data loaded successfully")
        print(f"   - Candidates: {discovery_data.get('count', 0)}")
        print(f"   - Strategy: {discovery_data.get('strategy', 'unknown')}")
        print(f"   - Timestamp: {discovery_data.get('timestamp', 'unknown')}")
    else:
        print("❌ No discovery data available")
        return test_results
    
    print("\\n3. TESTING BASIC CACHE OPERATIONS")
    print("-" * 50)
    
    start_time = time.time()
    
    # Test basic caching
    cache_key = f"perf_test_{int(time.time())}"
    cache_success = await caching_agent.cache_discovery_results(discovery_data, cache_key)
    cache_time = (time.time() - start_time) * 1000
    
    if cache_success:
        print(f"✅ Cache write successful ({cache_time:.2f}ms)")
        
        # Test cache read
        start_time = time.time()
        cached_data = await caching_agent.get_cached_discovery_results(cache_key)
        read_time = (time.time() - start_time) * 1000
        
        if cached_data:
            print(f"✅ Cache read successful ({read_time:.2f}ms)")
            test_results['cache_performance'] = {
                'write_time_ms': cache_time,
                'read_time_ms': read_time,
                'data_integrity': len(cached_data.get('candidates', [])) == len(discovery_data.get('candidates', []))
            }
        else:
            print("❌ Cache read failed")
    else:
        print("❌ Cache write failed")
    
    print("\\n4. TESTING SQUEEZE CACHE INTEGRATION")
    print("-" * 50)
    
    # Test with sample stock data
    sample_stocks = [
        {'symbol': 'VIGL', 'volume_spike': 12.5, 'volatility': 0.15},
        {'symbol': 'QUBT', 'volume_spike': 4.2, 'volatility': 0.08},
        {'symbol': 'ACHR', 'volume_spike': 2.1, 'volatility': 0.05},
        {'symbol': 'RGTI', 'volume_spike': 8.7, 'volatility': 0.12},
        {'symbol': 'IONQ', 'volume_spike': 1.8, 'volatility': 0.03}
    ]
    
    squeeze_cache_results = {}
    
    for stock in sample_stocks:
        symbol = stock['symbol']
        metrics = {'volume_spike': stock['volume_spike'], 'volatility': stock['volatility']}
        
        # Calculate dynamic TTL
        ttl = get_dynamic_ttl(symbol, metrics)
        
        # Cache with squeeze system
        sample_data = {'price': 10.0, 'volume': 1000000, 'metrics': metrics}
        cache_success = squeeze_cache.set_with_dynamic_ttl(symbol, sample_data, metrics)
        
        # Test retrieval
        cached_result = squeeze_cache.get_with_metrics(symbol)
        
        squeeze_cache_results[symbol] = {
            'ttl_assigned': ttl,
            'cache_success': cache_success,
            'cache_hit': cached_result['cache_hit'],
            'volume_spike': stock['volume_spike'],
            'volatility': stock['volatility']
        }
        
        status = "✅" if cache_success and cached_result['cache_hit'] else "❌"
        print(f"{status} {symbol}: TTL={ttl}s, Volume={stock['volume_spike']:.1f}x, Vol={stock['volatility']:.1%}")
    
    test_results['squeeze_cache_performance'] = squeeze_cache_results
    
    print("\\n5. DYNAMIC TTL ANALYSIS")
    print("-" * 50)
    
    ttl_categories = {'squeeze': 0, 'volatile': 0, 'active': 0, 'normal': 0, 'quiet': 0}
    
    for symbol, data in squeeze_cache_results.items():
        ttl = data['ttl_assigned']
        if ttl <= 30:
            ttl_categories['squeeze'] += 1
        elif ttl <= 60:
            ttl_categories['volatile'] += 1
        elif ttl <= 120:
            ttl_categories['active'] += 1
        elif ttl <= 300:
            ttl_categories['normal'] += 1
        else:
            ttl_categories['quiet'] += 1
    
    test_results['dynamic_ttl_analysis'] = ttl_categories
    
    print("TTL Distribution:")
    for category, count in ttl_categories.items():
        print(f"   - {category.capitalize()}: {count} stocks")
    
    print("\\n6. PERFORMANCE STRESS TEST")
    print("-" * 50)
    
    # Stress test with multiple operations
    stress_start = time.time()
    operations = 100
    successful_ops = 0
    total_response_time = 0
    
    for i in range(operations):
        op_start = time.time()
        
        # Mix of cache operations
        if i % 3 == 0:
            # Cache write
            test_key = f"stress_test_{i}"
            success = await caching_agent.cache_discovery_results(discovery_data, test_key)
        elif i % 3 == 1:
            # Cache read (hit)
            success = await caching_agent.get_cached_discovery_results(cache_key) is not None
        else:
            # Cache read (miss)
            success = await caching_agent.get_cached_discovery_results(f"miss_{i}") is None
        
        op_time = (time.time() - op_start) * 1000
        total_response_time += op_time
        
        if success:
            successful_ops += 1
    
    stress_total_time = (time.time() - stress_start) * 1000
    avg_response_time = total_response_time / operations
    operations_per_second = operations / (stress_total_time / 1000)
    
    print(f"✅ Stress Test Results:")
    print(f"   - Operations: {operations}")
    print(f"   - Successful: {successful_ops} ({successful_ops/operations:.1%})")
    print(f"   - Average Response: {avg_response_time:.2f}ms")
    print(f"   - Operations/sec: {operations_per_second:.1f}")
    
    test_results['stress_test'] = {
        'total_operations': operations,
        'successful_operations': successful_ops,
        'success_rate': successful_ops / operations,
        'avg_response_time_ms': avg_response_time,
        'operations_per_second': operations_per_second
    }
    
    print("\\n7. PERFORMANCE MONITORING")
    print("-" * 50)
    
    # Get comprehensive performance data
    performance_data = await caching_agent.monitor_performance()
    
    print("Cache Metrics:")
    cache_metrics = performance_data['cache_metrics']
    print(f"   - Hit Ratio: {cache_metrics.get('hit_ratio', 0):.2%}")
    print(f"   - Average Response Time: {cache_metrics.get('avg_response_time_ms', 0):.2f}ms")
    print(f"   - Total Requests: {cache_metrics.get('total_requests', 0)}")
    
    print("Redis Metrics:")
    redis_metrics = performance_data['redis_info']
    print(f"   - Memory Usage: {redis_metrics.get('used_memory_mb', 0):.2f}MB")
    print(f"   - Connected Clients: {redis_metrics.get('connected_clients', 0)}")
    print(f"   - Total Commands: {redis_metrics.get('total_commands_processed', 0)}")
    
    # Check for alerts
    alerts = performance_data.get('alerts', [])
    if alerts:
        print(f"\\n⚠️  Performance Alerts ({len(alerts)}):")
        for alert in alerts:
            print(f"   - {alert.alert_type}: {alert.message}")
    
    test_results['performance_monitoring'] = performance_data
    
    print("\\n8. BOTTLENECK ANALYSIS")
    print("-" * 50)
    
    bottlenecks = []
    
    # Analyze response times
    if avg_response_time > 100:
        bottlenecks.append({
            'type': 'high_latency',
            'description': f'Average response time ({avg_response_time:.2f}ms) exceeds 100ms threshold',
            'severity': 'high'
        })
    
    # Analyze hit ratio
    hit_ratio = cache_metrics.get('hit_ratio', 0)
    if hit_ratio < 0.8:
        bottlenecks.append({
            'type': 'low_hit_ratio',
            'description': f'Cache hit ratio ({hit_ratio:.2%}) below 80% target',
            'severity': 'medium'
        })
    
    # Analyze memory usage
    memory_mb = redis_metrics.get('used_memory_mb', 0)
    if memory_mb > 100:
        bottlenecks.append({
            'type': 'high_memory',
            'description': f'Redis memory usage ({memory_mb:.2f}MB) approaching limits',
            'severity': 'medium'
        })
    
    test_results['performance_bottlenecks'] = bottlenecks
    
    if bottlenecks:
        print(f"⚠️  Identified {len(bottlenecks)} potential bottlenecks:")
        for bottleneck in bottlenecks:
            print(f"   - {bottleneck['type']}: {bottleneck['description']}")
    else:
        print("✅ No significant performance bottlenecks detected")
    
    print("\\n9. OPTIMIZATION RECOMMENDATIONS")
    print("-" * 50)
    
    recommendations = []
    
    # TTL optimization
    if ttl_categories['squeeze'] > 0:
        recommendations.append("Continue using dynamic TTL for squeeze candidates - showing good performance")
    
    # Hit ratio optimization
    if hit_ratio < 0.9:
        recommendations.append("Consider implementing cache warming for frequently accessed discovery data")
    
    # Memory optimization
    if memory_mb > 50:
        recommendations.append("Implement aggressive cache eviction for old discovery results")
    
    # Performance optimization
    if avg_response_time > 50:
        recommendations.append("Consider Redis pipelining for batch operations")
    
    # Integration optimization
    recommendations.append("Integrate caching agent with existing squeeze detection workflow")
    recommendations.append("Implement cache warming for hot stocks identified by discovery engine")
    
    test_results['recommendations'] = recommendations
    
    print("💡 Optimization Recommendations:")
    for i, rec in enumerate(recommendations, 1):
        print(f"   {i}. {rec}")
    
    print("\\n10. INTEGRATION VERIFICATION")
    print("-" * 50)
    
    # Test integration with existing systems
    integration_tests = {}
    
    # Test squeeze cache statistics
    try:
        squeeze_stats = squeeze_cache.get_cache_statistics()
        integration_tests['squeeze_cache_stats'] = True
        print(f"✅ Squeeze cache integration: {squeeze_stats.get('total_cached_symbols', 0)} symbols cached")
    except Exception as e:
        integration_tests['squeeze_cache_stats'] = False
        print(f"❌ Squeeze cache integration failed: {e}")
    
    # Test dynamic TTL calculation
    try:
        test_metrics = {'volume_spike': 5.0, 'volatility': 0.08}
        dynamic_ttl = get_dynamic_ttl('TEST', test_metrics)
        integration_tests['dynamic_ttl'] = True
        print(f"✅ Dynamic TTL calculation: {dynamic_ttl}s for test metrics")
    except Exception as e:
        integration_tests['dynamic_ttl'] = False
        print(f"❌ Dynamic TTL calculation failed: {e}")
    
    test_results['integration_tests'] = integration_tests
    
    print("\\n" + "=" * 80)
    print("COMPREHENSIVE TEST SUMMARY")
    print("=" * 80)
    
    print(f"\\n📊 OVERALL PERFORMANCE METRICS:")
    print(f"   - Redis Connectivity: {'✅ Active' if test_results['redis_connectivity'] else '❌ Failed'}")
    print(f"   - Discovery Data: {'✅ Available' if test_results['discovery_data_available'] else '❌ Missing'}")
    print(f"   - Cache Hit Ratio: {hit_ratio:.2%}")
    print(f"   - Average Response Time: {avg_response_time:.2f}ms")
    print(f"   - Operations/Second: {operations_per_second:.1f}")
    print(f"   - Success Rate: {successful_ops/operations:.1%}")
    
    print(f"\\n🔧 SYSTEM HEALTH:")
    print(f"   - Performance Bottlenecks: {len(bottlenecks)}")
    print(f"   - Optimization Recommendations: {len(recommendations)}")
    print(f"   - Integration Tests Passed: {sum(integration_tests.values())}/{len(integration_tests)}")
    
    print(f"\\n📈 DYNAMIC CACHING ANALYSIS:")
    print(f"   - Squeeze Detection TTL: {ttl_categories['squeeze']} stocks (≤30s)")
    print(f"   - High Volatility TTL: {ttl_categories['volatile']} stocks (≤60s)")
    print(f"   - Active Trading TTL: {ttl_categories['active']} stocks (≤120s)")
    
    # Performance grade
    if hit_ratio >= 0.8 and avg_response_time <= 50 and successful_ops/operations >= 0.95:
        grade = "A - Excellent"
    elif hit_ratio >= 0.6 and avg_response_time <= 100 and successful_ops/operations >= 0.9:
        grade = "B - Good"
    elif hit_ratio >= 0.4 and avg_response_time <= 200:
        grade = "C - Acceptable"
    else:
        grade = "D - Needs Improvement"
    
    print(f"\\n🏆 OVERALL PERFORMANCE GRADE: {grade}")
    
    # Save detailed results
    results_file = "/Users/michaelmote/Desktop/AMC-TRADER/backend/src/data/cache_performance_report.json"
    with open(results_file, 'w') as f:
        json.dump(test_results, f, indent=2, default=str)
    
    print(f"\\n📄 Detailed results saved to: {results_file}")
    
    return test_results


if __name__ == "__main__":
    asyncio.run(comprehensive_cache_performance_test())